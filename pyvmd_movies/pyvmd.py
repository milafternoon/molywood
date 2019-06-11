import sys
from subprocess import call
import os

if __name__ == "__main__":
    import tcl_actions
    import graphics_actions
else:
    import pyvmd_movies.tcl_actions as tcl_actions
    import pyvmd_movies.graphics_actions as graphics_actions


class Script:
    """
    Main class that will combine all information
    and render the movie (possibly with multiple
    panels, overlays etc.)
    """
    allowed_globals = ['global', 'layout']
    allowed_params = {'global': ['fps', 'keepframes', 'draft', 'name', 'render'],
                      'layout': ['columns', 'rows'],
                      '_default': ['visualization', 'structure', 'trajectory', 'position', 'resolution', 'pdb_code']}
    
    def __init__(self, scriptfile=None):
        self.name = 'movie'
        self.scenes = []
        self.directives = {}
        self.fps = 20
        self.draft, self.do_render, self.keepframes = False, True, False
        self.scriptfile = scriptfile
        self.vmd, self.remove, self.compose, self.convert = 4 * [None]
        self.setup_os_commands()
        if self.scriptfile:
            self.from_file()

    def render(self):
        """
        The final fn that renders the movie (runs
        the TCL script, then uses combine and/or
        ffmpeg to assemble the movie frame by frame)
        :return: None
        """
        # the part below controls TCL/VMD rendering
        for scene in self.scenes:
            tcl_script = scene.tcl()  # this generates the TCL code, below we save it as a script and run VMD
            if scene.run_vmd:
                with open('script_{}.tcl'.format(scene.name), 'w') as out:
                    out.write(tcl_script)
                ddev = '-dispdev none' if not self.draft else ''
                if not self.do_render and not self.draft:
                    raise RuntimeError("render=false is only compatible with draft=true")
                os.system('{} {} -e script_{}.tcl -startup ""'.format(self.vmd, ddev, scene.name))
                if self.do_render:
                    if os.name == 'posix':
                        os.system('for i in $(ls {}-*tga); do convert $i $(echo $i | sed "s/tga/png/g"); '
                             'rm $i; done'.format(scene.name))
                    else:
                        to_convert = [x for x in os.listdir('.') if x.startswith(scene.name) and x.endswith('tga')]
                        for tgafile in to_convert:
                            pngfile = tgafile.replace('tga', 'png')
                            call('{} {} {}'.format(self.convert, tgafile, pngfile))
                if not self.draft:
                    if os.name == 'posix':
                        os.system('for i in $(ls {}-*png); do rm $(echo $i | sed "s/png/dat/g"); done'.format(scene.name))
                    else:
                        os.system('del {}*dat'.format(scene.name))
            for action in scene.actions:
                action.generate_graph()  # here we generate matplotlib figs on-the-fly
        # at this stage, each scene should have all its initial frames rendered
        if self.do_render:
            graphics_actions.postprocessor(self)
            os.system('ffmpeg -y -framerate {} -i {}-%d.png -profile:v high -crf 20 -pix_fmt yuv420p '
                 '-vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" {}.mp4'.format(self.fps, self.name, self.name))
        if not self.keepframes:
            for sc in self.scenes:
                if '/' in sc.name or '\\' in sc.name or '~' in sc.name:
                    raise RuntimeError('For security reasons, cleanup of scenes that contain path-like elements '
                                       '(slashes, backslashes, tildes) is prohibited.\n\n'
                                       'Error triggered by: {}'.format(sc.name))
                else:
                    if any([x for x in os.listdir('.') if x.startswith(sc.name) and x.endswith('png')]):
                        os.system('{} {}-[0-9]*.png'.format(self.remove, sc.name))
                    if any([x for x in os.listdir('.') if x.startswith('overlay') and x.endswith('png')
                            and sc.name in x]):
                        os.system('{} overlay[0-9]*-{}-[0-9]*.png'.format(self.remove, sc.name))
                    if any([x for x in os.listdir('.') if x.startswith('script') and x.endswith('tcl')
                            and sc.name in x]):
                        os.system('{} script_{}.tcl'.format(self.remove, sc.name))
            if '/' in self.name or '\\' in self.name or '~' in self.name:
                raise RuntimeError('For security reasons, cleanup of scenes that contain path-like elements '
                                   '(slashes, backslashes, tildes) is prohibited.\n\n'
                                   'Error triggered by: {}'.format(self.name))
            else:
                if any([x for x in os.listdir('.') if x.startswith(self.name) and x.endswith('png')]):
                    os.system('{} {}-[0-9]*.png'.format(self.remove, self.name))
    
    def show_script(self):
        """
        Shows a sequence of scenes currently
        buffered in the object for rendering
        :return: None
        """
        for subscript in self.scenes:
            print('\n\n\tScene {}: \n\n'.format(subscript.name))
            subscript.show_script()

    def from_file(self):
        """
        Reads the full movie script from an input file
        and runs parser/setter functions
        :return: None
        """
        script = [line.strip() for line in open(self.scriptfile, 'r')]
        current_sub = '_default'
        subscripts = {current_sub: []}
        multiline = None
        master_setup = []
        for line in script:
            excl = line.find('!')
            if excl >= 0:
                line = line[:excl].strip()
            if line.startswith('#'):  # beginning of a subscript
                current_sub = line.strip('#').strip()
                subscripts[current_sub] = []
            elif line.startswith('$'):  # global directives
                master_setup.append(line.strip('$').strip())
            elif line:  # regular content of subscript
                if line.startswith('{'):  # with a possibility of multi-actions wrapped into curly brackets
                    multiline = ' ' + line
                elif multiline and '}' not in line:
                    multiline += ' ' + line
                elif multiline and '}' in line:
                    multiline += ' ' + line
                    for act in multiline.strip('\{\} ').split(';'):
                        if not all(len(x.split('=')) == 2 for x in Action.split_input_line(act)[1:]):
                            raise RuntimeError("Have you forgotten to add a semicolon in action: \n\n{}?\n".format(act))
                    subscripts[current_sub].append(multiline)
                    multiline = None
                else:
                    subscripts[current_sub].append(line)
        if multiline:
            raise RuntimeError("Error: not all curly brackets {} were closed, revise your input")
        Script.allowed_globals.extend(list(subscripts.keys()))
        for sc in subscripts.keys():
            Script.allowed_params[sc] = Script.allowed_params['_default']
        self.directives = self.parse_directives(master_setup)
        self.scenes = self.parse_scenes(subscripts)
        self.prepare()
    
    def setup_os_commands(self):
        """
        Paths to VMD, imagemagick utilities, OS-specific
        versions of rm/del, ls/dir, which/where, ffmpeg etc.
        have to be determined to allow for Linux/OSX/Win
        compatibility
        :return: None
        """
        if os.name == 'posix':
            self.remove = 'rm'
            self.vmd = 'vmd'
            self.compose, self.convert = 'composite', 'convert'
        elif os.name == 'nt':
            import pathlib
            self.remove = 'del'
            for pfiles in [x for x in os.listdir('C:\\') if x.startswith('Program Files')]:
                for file in pathlib.Path('C:\\{}'.format(pfiles)).glob('**/vmd.exe'):
                    self.vmd = str(file)
            if not self.vmd:
                raise RuntimeError("VMD was not found in any of the Program Files directories, check your installation")
            if call('where ffmpeg') != 0:
                raise RuntimeError('ffmpeg not found, please make sure it was added to the system path during '
                                   'installation (see README)')
            if call('where magick') == 0:
                self.compose, self.convert = 'magick composite', 'magick convert'
            else:
                raise RuntimeError('imagemagick not found, please make sure it was added to the system path during '
                                   'installation (see README)')
        else:
            raise RuntimeError('OS type could not be detected')
        
    @staticmethod
    def parse_directives(directives):
        """
        Reads global directives that affect
        the main object (layout, fps, draftmode
        etc.) based on $-prefixed entries
        :param directives:
        :return:
        """
        dirs = {}
        for directive in directives:
            entries = directive.split()
            if entries[0] not in Script.allowed_globals:
                raise RuntimeError("'{}' is not an allowed global directive. Allowed "
                                   "global directives are: {}".format(entries[0], ", ".join(Script.allowed_globals)))
            dirs[entries[0]] = {}
            for entry in entries[1:]:
                try:
                    key, value = entry.split('=')
                except ValueError:
                    raise RuntimeError("Entries should contain parameters formatted as 'key=value' pairs,"
                                       "'{}' in line '{}' does not follow that specification".format(entry, directive))
                else:
                    allowed = Script.allowed_params[entries[0]]
                    if key not in allowed:
                        raise RuntimeError("'{}' is not a parameter compatible with the directive {}. Allowed "
                                           "parameters include: {}".format(key, entries[0],
                                                                           ", ".join(list(allowed))))
                    dirs[entries[0]][key] = value
        return dirs
    
    def parse_scenes(self, scenes):
        """
        Reads info on individual scenes and initializes
        Scene objects, appending them to the main
        object's scene list
        :param scenes: dict, contains scene_name: description bindings
        :return: list of Scene objects
        """
        objects = []
        pos, res, tcl, py, struct, traj = [1, 1], [1000, 1000], None, None, None, None
        for sub in scenes.keys():
            if scenes[sub]:
                if sub in self.directives.keys():
                    try:
                        tcl = self.directives[sub]['visualization']
                    except KeyError:
                        pass
                    else:
                        tcl = self.check_path(tcl)
                        tcl = self.check_tcl(tcl)
                    try:
                        pos = [int(x) for x in self.directives[sub]['position'].split(',')]
                    except KeyError:
                        pass
                    try:
                        res = [int(x) for x in self.directives[sub]['resolution'].split(',')]
                    except KeyError:
                        pass
                    try:
                        py = self.directives[sub]['python']
                    except KeyError:
                        pass
                    try:
                        struct = self.directives[sub]['structure']
                    except KeyError:
                        try:
                            pdb = self.directives[sub]['pdb_code']
                        except KeyError:
                            pass
                        else:
                            if os.name == 'nt':
                                raise RuntimeError("direct download of PDB files currently not supported on Windows")
                            pdb = pdb.upper()
                            if not pdb.upper() + '.pdb' in os.listdir('.'):
                                if os.system('which wget') == 0:
                                    result = os.system('wget https://files.rcsb.org/download/{}.pdb'.format(pdb))
                                elif os.system('which curl') == 0:
                                    result = os.system('curl -O https://files.rcsb.org/download/{}.pdb'.format(pdb))
                                else:
                                    raise RuntimeError("You need wget or curl to directly download PDB files")
                                if result != 0:
                                    raise RuntimeError("Download failed, check your PDB code and internet connection")
                            struct = '{}.pdb'.format(pdb)
                    else:
                        struct = self.check_path(struct)
                    try:
                        traj = self.directives[sub]['trajectory']
                    except KeyError:
                        pass
                    else:
                        traj = self.check_path(traj)
                objects.append(Scene(self, sub, tcl, py, res, pos, struct, traj))
                for action in scenes[sub]:
                    objects[-1].add_action(action)
        return objects

    def prepare(self):
        """
        Once text input is parsed, this fn sets
        global parameters such as fps, draft mode
        or whether to keep frames
        :return: None
        """
        try:
            self.fps = float(self.directives['global']['fps'])
        except KeyError:
            pass
        try:
            self.draft = True if self.directives['global']['draft'].lower() in ['y', 't', 'yes', 'true'] else False
        except KeyError:
            pass
        try:
            self.do_render = False if self.directives['global']['render'].lower() in ['n', 'f', 'no', 'false'] else True
        except KeyError:
            pass
        try:
            self.keepframes = True if self.directives['global']['keepframes'].lower() in ['y', 't', 'yes', 'true'] \
                else False
        except KeyError:
            pass
        try:
            self.name = self.directives['global']['name']
        except KeyError:
            pass
        for scene in self.scenes:
            scene.calc_framenum()
    
    def check_path(self, filename):
        if os.path.isfile(filename):
            return filename
        elif not os.path.isfile(filename) and '/' in self.scriptfile:
            prefix = '/'.join(self.scriptfile.split('/')[:-1]) + '/'
            if os.path.isfile(prefix + filename):
                return prefix + filename
            else:
                raise RuntimeError('File {} could not been found neither in the local directory '
                                   'nor in {}'.format(filename, prefix))
        else:
            raise RuntimeError('File {} not found, please make sure there are no typos in the name'.format(filename))
    
    @staticmethod
    def check_tcl(tcl_file):
        """
        If the files to be read by VMD were saved as
        absolute paths and then transferred to another
        machine, this fn will identify missing paths
        and look for the files in the working dir,
        creating another file if needed
        :param tcl_file: str, path to the VMD visualization state
        :return: str, new (or same) path to the VMD visualization state
        """
        inp = [line for line in open(tcl_file)]
        modded = False
        for n in range(len(inp)):
            if inp[n].strip().startswith('mol') and inp[n].split()[1] in ['new', 'addfile'] \
                    and inp[n].split()[2].startswith('/'):
                if not os.path.isfile(inp[n].split()[2]):
                    if os.path.isfile(inp[n].split()[2].split('/')[-1]):
                        print('Warning: absolute path {} was substituted with a relative path to the local file {}; '
                              'the modified .vmd file will be '
                              'backed up'.format(inp[n].split()[2], inp[n].split()[2].split('/')[-1]))
                        inp[n] = ' '.join(inp[n].split()[:2]) + " {} ".format(inp[n].split()[2].split('/')[-1]) \
                                 + ' '.join(inp[n].split()[3:])
                        modded = True
        if modded:
            with open(tcl_file + '.localcopy', 'w') as new_tcl:
                for line in inp:
                    new_tcl.write(line)
            return tcl_file + '.localcopy'
        else:
            return tcl_file
                


class Scene:
    """
    A Scene instance is restricted to a single
    molecular system, and hence has to be initialized
    with a valid input file
    """
    def __init__(self, script, name, tcl=None, py=None, resolution=(1000, 1000), position=(1, 1),
                 structure=None, trajectory=None):
        self.script = script
        self.name = name
        self.visualization = tcl
        self.actions = []
        self.resolution = resolution
        self.position = position
        self.py_code = py
        self.structure = structure
        self.trajectory = trajectory
        self.run_vmd = False
        self.total_frames = 0
        self.tachyon = None
        self.counters = {'hl': 0, 'overlay': 0, 'make_transparent': 0, 'make_opaque': 0, 'rot': 0}
        self.labels = {'Atoms': [], 'Bonds': []}
    
    def add_action(self, description):
        """
        Adds an action to the subscript
        :param description: str, description of the action
        :return: None
        """
        if not description.strip().startswith('{'):
            self.actions.append(Action(self, description))
        else:
            self.actions.append(SimultaneousAction(self, description.strip('{} ')))

    def show_script(self):
        """
        Shows actions scheduled for rendering
        within the current subscript
        :return:
        """
        for action in self.actions:
            print(action)
    
    def calc_framenum(self):
        """
        Once the fps rate is known, we can go through all actions
        and set integer frame counts as needed. Note: some actions
        can be instantaneous (e.g. recenter camera), so that
        not all will have a non-zero framenum
        :return: None
        """
        fps = self.script.fps
        cumsum = 0
        for action in self.actions:
            action.initframe = cumsum
            try:
                action.framenum = int(float(action.parameters['t'])*fps)
            except KeyError:
                action.framenum = 0
            cumsum += action.framenum
        self.total_frames = cumsum
            
    def tcl(self):
        """
        This is the top-level function that produces
        an executable TCL script based on the corresponding
        action.generate() functions
        :return: str, TCL code
        """
        if self.visualization or self.structure:
            self.run_vmd = True
            if self.visualization:
                code = [line for line in open(self.visualization, 'r').readlines() if not line.startswith('#')]
                code = ''.join(code)
            else:
                code = 'mol new {} type {} first 0 last -1 step 1 filebonds 1 ' \
                       'autobonds 1 waitfor all\n'.format(self.structure, self.structure.split('.')[-1])
                if self.trajectory:
                    code += 'mol addfile {} type {} first 0 last -1 step 1 filebonds 1 ' \
                            'autobonds 1 waitfor all\n'.format(self.trajectory, self.trajectory.split('.')[-1])
                code += 'mol delrep 0 top\nmol representation NewCartoon 0.300000 10.000000 4.100000 0\n' \
                        'mol color Structure\nmol selection {all}\nmol material Opaque\nmol addrep top\n' \
                        'color Display Background white\n'
            code += 'axes location off\n'
            if not self.script.draft:
                code += 'render options Tachyon \"$env(TACHYON_BIN)\" -aasamples 12 %s -format ' \
                        'TARGA -o %s.tga -res {} {}\n'.format(*self.resolution)
            else:
                code += 'display resize {res}\nafter 100\ndisplay update\nafter 100\n' \
                        'display resize {res}'.format(res=' '.join(str(x) for x in self.resolution))
            action_code = ''
            for ac in self.actions:
                action_code += ac.generate_tcl()
            if action_code:
                code += action_code
        else:
            code = ''
        return code + '\nexit\n'
        
        
class Action:
    """
    Intended to represent a single action in
    a movie, e.g. a rotation, change of material
    or zoom-in
    """
    allowed_actions = ['do_nothing', 'animate', 'rotate', 'zoom_in', 'zoom_out', 'make_transparent', 'highlight',
                       'make_opaque', 'center_view', 'show_figure', 'add_overlay', 'add_label', 'remove_label',
                       'fit_trajectory', 'add_distance', 'remove_distance']
    
    allowed_params = {'do_nothing': {'t'},
                      'animate': {'frames', 'smooth', 't'},
                      'rotate': {'angle', 'axis', 't', 'sigmoid'},
                      'zoom_in': {'scale', 't', 'sigmoid'},
                      'zoom_out': {'scale', 't', 'sigmoid'},
                      'make_transparent': {'material', 't', 'sigmoid', 'limit', 'start'},
                      'highlight': {'selection', 't', 'color', 'mode', 'style', 'alias'},
                      'make_opaque': {'material', 't', 'sigmoid', 'limit', 'start'},
                      'center_view': {'selection'},
                      'show_figure': {'figure', 't', 'datafile', 'dataframes'},
                      'add_overlay': {'figure', 't', 'origin', 'relative_size', 'dataframes',
                                      'aspect_ratio', 'datafile', '2D', 'text', 'textsize', 'sigmoid'},
                      'add_label': {'label_color', 'atom_index', 'label', 'text_size', 'alias'},
                      'remove_label': {'alias', 'all'},
                      'add_distance': {'selection1', 'selection2', 'label_color', 'text_size', 'alias'},
                      'remove_distance': {'alias', 'all'},
                      'fit_trajectory': {'selection'}
                      }
    
    def __init__(self, scene, description):
        self.scene = scene
        self.description = description
        self.action_type = None
        self.parameters = {}  # will be a dict of action parameters
        self.initframe = None  # contains the initial frame number in the overall movie's numbering
        self.framenum = None  # total frames count for this action
        self.highlights, self.transp_changes, self.rots = {}, {}, {}
        self.parse(description)
    
    def __repr__(self):
        return self.description.split()[0]
    
    def generate_tcl(self):
        """
        Should produce the TCL code that will
        produce the action in question
        :return: str, TCL code
        """
        actions_requiring_tcl = ['do_nothing', 'animate', 'rotate', 'zoom_in', 'zoom_out', 'make_transparent',
                                 'make_opaque', 'center_view', 'add_label', 'remove_label', 'highlight',
                                 'fit_trajectory', 'add_distance', 'remove_distance']
        if set(self.action_type).intersection(set(actions_requiring_tcl)):
            return tcl_actions.gen_loop(self)
        else:
            return ''
    
    def generate_graph(self):
        actions_requiring_genfig = ['show_figure', 'add_overlay']
        if set(self.action_type).intersection(set(actions_requiring_genfig)):
            graphics_actions.gen_fig(self)
    
    def parse(self, command, ignore=()):
        """
        Parses a single command from the text input
        and converts into action parameters
        :param command: str, description of the action
        :param ignore: tuple, list of parameters to ignore while parsing
        :return: None
        """
        spl = self.split_input_line(command)
        if spl[0] not in Action.allowed_actions:
            raise RuntimeError("'{}' is not a valid action. Allowed actions "
                               "are: {}".format(spl[0], ', '.join(list(Action.allowed_actions))))
        if not isinstance(self, SimultaneousAction) and spl[0] == "add_overlay":
            raise RuntimeError("Overlays can only be added simultaneously with another action, not as"
                               "a standalone one")
        self.action_type = [spl[0]]
        try:
            new_dict = {prm.split('=')[0]: prm.split('=')[1].strip("'\"") for prm in spl[1:]
                        if prm.split('=')[0] not in ignore}
        except IndexError:
            raise RuntimeError("Line '{}' is not formatted properly; action name should be followed by keyword=value "
                               "pairs, and no spaces should encircle the '=' sign".format(command))
        for par in new_dict:
            if par not in Action.allowed_params[spl[0]]:
                raise RuntimeError("'{}' is not a valid parameter for action '{}'. Parameters compatible with this "
                                   "action include: {}".format(par, spl[0],
                                                               ', '.join(list(Action.allowed_params[spl[0]]))))
        self.parameters.update(new_dict)
        if 't' in self.parameters.keys():
            self.parameters['t'] = self.parameters['t'].rstrip('s')
        if not isinstance(self, SimultaneousAction):
            if spl[0] == 'highlight':
                try:
                    alias = '_' + self.parameters['alias']
                except KeyError:
                    alias = self.scene.counters['hl']
                self.highlights = {'hl{}'.format(alias): self.parameters}
                self.scene.counters['hl'] += 1
            if spl[0] in ['make_transparent', 'make_opaque']:
                self.transp_changes = {spl[0]: self.parameters}
                self.scene.counters[spl[0]] += 1
            if spl[0] == 'rotate':
                self.rots = {'rot': self.parameters}

    @staticmethod
    def split_input_line(line):
        """
        a modified string splitter that doesn't split
        words encircled in quotation marks; required
        by center_view that requires a VMD-compatible
        selection string
        :param line: str, line to be split
        :return: list of strings, contains individual words
        """
        line = line.strip()
        words = []
        open_quotation = False
        previous = 0
        for current, char in enumerate(line):
            if char in ["'", '"']:
                if not open_quotation:
                    open_quotation = True
                else:
                    open_quotation = False
            if (char == ' ' and not open_quotation) or current == len(line) - 1:
                word = line[previous:current+1].strip()
                if word:
                    words.append(word)
                previous = current
        return words
        

class SimultaneousAction(Action):
    """
    Intended to represent a number of actions
    that take place simultaneously (e.g. zoom
    and rotation)
    """
    def __init__(self, scene, description):
        self.overlays = {}  # need special treatment for overlays as there can be many ('overlay0', 'overlay1', ...)
        self.highlights = {}  # the same goes for highlights ('hl0', 'hl1', ...)
        self.transp_changes = {}  # ...and for make_opaque/make_transparent
        super().__init__(scene, description)
        
    def parse(self, command, ignore=()):
        """
        We simply add action parameters to the
        params dict, assuming there will be no
        conflict of names (need to ensure this
        when setting action syntax); this *is*
        a workaround, but should work fine for
        now - might write a preprocessor later
        to pick up and fix any possible issues
        :param command: str, description of the actions
        :param ignore: tuple, list of parameters to ignore while parsing
        :return: None
        """
        actions = [comm.strip() for comm in command.split(';')]
        igns = []  # ones that we don't want to be overwritten in the 'parameters' dict
        for action in actions:
            if action.split()[0] == 'add_overlay':
                self.parse_many(action, self.overlays, 'overlay')
                igns.append('figure')
            elif action.split()[0] == 'highlight':
                self.parse_many(action, self.highlights, 'hl')
            elif action.split()[0] in ['make_transparent', 'make_opaque']:
                self.parse_many(action, self.transp_changes, action.split()[0])
            elif action.split()[0] == 'rotate':
                self.parse_many(action, self.rots, 'rot')
            elif action.split()[0] in ['fit_trajectory', 'center_view', 'add_label', 'remove_label',
                                       'add_distance', 'remove_distance']:
                raise RuntimeError("{} is an instantaneous action (i.e. doesn't last over finite time interval) and "
                                   "cannot be combined with finite-time ones".format(action.split()[0]))
            super().parse(action, tuple(igns))
        self.action_type = [action.split()[0] for action in actions]
        if 'zoom_in' in self.action_type and 'zoom_out' in self.action_type:
            raise RuntimeError("actions {} are mutually exclusive".format(", ".join(self.action_type)))
    
    def parse_many(self, directive, actions_dict, keyword):
        actions_count = self.scene.counters[keyword]
        self.scene.counters[keyword] += 1
        spl = self.split_input_line(directive)
        try:
            prm_dict = {prm.split('=')[0]: prm.split('=')[1].strip("'\"") for prm in spl[1:]}
        except IndexError:
            raise RuntimeError("Line '{}' is not formatted properly; action name should be followed by keyword=value "
                               "pairs, and no spaces should encircle the '=' sign".format(directive))
        if 'alias' in prm_dict.keys():
            alias = '_' + prm_dict['alias']
        else:
            alias = str(actions_count)
        actions_dict[keyword + alias] = prm_dict
    

if __name__ == "__main__":
    try:
        input_name = sys.argv[1]
    except IndexError:
        print("To run PyVMD, provide the name of the text input file, e.g. "
              "'python path/to/pyvmd.py script.txt'. To see and try out example "
              "input files, go to the 'examples' directory.")
        sys.exit(1)
    else:
        scr = Script(input_name)
        try:
            test_param = sys.argv[2]
        except IndexError:
            scr.render()
        else:
            if test_param == '-test':
                for sscene in scr.scenes:
                    stcl_script = sscene.tcl()
                    if sscene.run_vmd:
                        with open('script_{}.tcl'.format(sscene.name), 'w') as sout:
                            sout.write(stcl_script)
            else:
                print("\n\nWarning: parameters beyond the first will be ignored\n\n")
                scr.render()
