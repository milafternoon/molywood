import sys
import os

if __name__ == "__main__":
    import tcl_actions
    import process_graphics
else:
    import pyvmd_movies.tcl_actions as tcl_actions
    import pyvmd_movies.process_graphics as process_graphics


class Script:
    """
    Main class that will combine all information
    and render the movie (possibly with multiple
    panels, overlays etc.)
    """
    def __init__(self, scriptfile=None):
        self.name = 'movie'
        self.scenes = []
        self.directives = {}
        self.fps = 20
        self.draft = False
        self.keepframes = True
        if scriptfile:
            self.from_file(scriptfile)

    def render(self):
        """
        The final fn that renders the movie (runs
        the TCL script, then uses combine and/or
        ffmpeg to assemble the movie frame by frame)
        :return: None
        """
        # the part below controls TCL/VMD rendering
        for scene in self.scenes:
            tcl_script = scene.tcl()
            with open('script_{}.tcl'.format(scene.name), 'w') as out:
                out.write(tcl_script)
            os.system('vmd -dispdev none -e script_{}.tcl'.format(scene.name))
        os.system('for i in $(ls *tga); do convert $i $(echo $i | sed "s/tga/png/g"); rm $i; '
                  'rm $(echo $i | sed "s/tga/dat/g"); done')
        # here we do simple picture rendering
        # at this stage, each scene should have all its initial frames rendered
        process_graphics.postprocessor(self)
        os.system('ffmpeg -y -framerate {} -i {}-%d.png -profile:v high '
                  '-crf 20 -pix_fmt yuv420p -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" movie.mp4'.format(self.fps, self.name))
        if not self.keepframes:
            os.system('rm {}*.png'.format('scene_1-'))
    
    def show_script(self):
        """
        Shows a sequence of scenes currently
        buffered in the object for rendering
        :return: None
        """
        for subscript in self.scenes:
            print('\n\n\tScene {}: \n\n'.format(subscript.name))
            subscript.show_script()

    def from_file(self, filename):
        """
        Reads the full movie script from an input file
        and runs parser/setter functions
        :param filename: str, name of the file
        :return: None
        """
        script = [line.strip() for line in open(filename, 'r')]
        current_sub = '_default'
        subscripts = {current_sub: []}
        multiline = None
        master_setup = []
        for line in script:
            if line.startswith('#'):  # beginning of a subscript
                current_sub = line.strip('#').strip()
                subscripts[current_sub] = []
            elif line.startswith('$'):  # global directives
                master_setup.append(line.strip('$').strip())
            elif line:  # regular content of subscript
                if line.startswith('{'):  # with a possibility of multi-actions wrapped into curly brackets
                    multiline = line
                elif multiline and '}' not in line:
                    multiline += line
                elif multiline and '}' in line:
                    subscripts[current_sub].append(multiline + line)
                    multiline = None
                else:
                    subscripts[current_sub].append(line)
        self.directives = self.parse_directives(master_setup)
        self.scenes = self.parse_scenes(subscripts)
        self.prepare()
        
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
            dirs[entries[0]] = {}
            for entry in entries[1:]:
                key, value = entry.split('=')
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
        pos, res, tcl, py, fig = [1, 1], [1000, 1000], None, None, None
        for sub in scenes.keys():
            if scenes[sub]:
                if sub in self.directives.keys():
                    try:
                        tcl = self.directives[sub]['visualization']
                    except KeyError:
                        pass
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
                        fig = self.directives[sub]['figure']  # TODO possibly have many figures, or global list of figs?
                    except KeyError:
                        pass
                if not (fig or py or tcl):
                    raise ValueError("Scene {} does not specify any graphical content".format(scenes[sub].name))
                objects.append(Scene(self, sub, tcl, py, fig, res, pos))
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
            self.keepframes = True if self.directives['global']['keepframes'].lower() in ['y', 't', 'yes', 'true'] \
                else False
        except KeyError:
            pass
        for scene in self.scenes:
            scene.calc_framenum()
            if self.draft:
                scene.resolution = [200, 200]
        

class Scene:
    """
    A Scene instance is restricted to a single
    molecular system, and hence has to be initialized
    with a valid input file
    """
    def __init__(self, script, name, tcl=None, py=None, fig=None, resolution=(1000, 1000), position=(1, 1)):
        self.tcl_code = script  # TODO enable user to specify resolution globally in a consistent way
        self.name = name
        self.visualization = tcl
        self.actions = []
        self.resolution = resolution
        self.position = position
        self.figure = fig
        self.py_code = py
        self.total_frames = 0
    
    def add_action(self, description):
        """
        Adds an action to the subscript
        :param description: str, description of the action
        :return: None
        """
        if not description.startswith('{'):
            self.actions.append(Action(self, description))
        else:
            self.actions.append(SimultaneousAction(self, description.strip('{}')))

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
        fps = self.tcl_code.fps
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
        action.tcl() functions
        :return: str, TCL code
        """
        if self.visualization:
            code = open(self.visualization, 'r').readlines()
            code = ''.join(code)
            code += 'axes location off\n'
            code += 'render options Tachyon "/usr/local/lib/vmd/tachyon_LINUXAMD64" -aasamples 12 %s -format ' \
                    'TARGA -o %s.tga -res {} {}\n'.format(*self.resolution)
            for action in self.actions:
                code = code + action.generate()
        else:
            code = ''
        return code + '\nexit\n'
        
        
class Action:
    """
    Intended to represent a single action in
    a movie, e.g. a rotation, change of material
    or zoom-in
    """
    def __init__(self, scene, description):
        self.scene = scene
        self.description = description
        self.action_type = None
        self.parameters = {}  # will be a dict of action parameters
        self.initframe = None  # contains the initial frame number in the overall movie's numbering
        self.framenum = None  # total frames count for this action
        self.parse(description)
    
    def __repr__(self):
        return self.description.split()[0]
    
    def generate(self):
        """
        Should produce the TCL code that will
        produce the action in question
        :return: str, TCL code
        """
        if self.action_type in ['do_nothing', 'animate', 'rotate', 'zoom_in', 'zoom_out', 'make_transparent',
                                'make_opaque', 'center_view']:
            return tcl_actions.gen_loop(self)
        elif self.action_type in ['show_figure']:
            process_graphics.gen_fig(self)
            return ''
    
    def parse(self, command):
        """
        Parses a single command from the text input
        and converts into action parameters
        :param command: str, description of the action
        :return: None
        """
        spl = self.split_input_line(command)
        self.action_type = spl[0]
        self.parameters.update({prm.split('=')[0]: prm.split('=')[1].strip("'\"") for prm in spl[1:]})
        if 't' in self.parameters.keys():
            self.parameters['t'] = self.parameters['t'].rstrip('s')

    @staticmethod
    def split_input_line(line):
        """
        a modified string splitter that doesn't split
        words encircled in quotation marks
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
        print(line, words)
        return words
        

class SimultaneousAction(Action):
    """
    Intended to represent a number of actions
    that take place simultaneously (e.g. zoom
    and rotation)
    """
    def __init__(self, scene, description):
        super().__init__(scene, description)
        
    def parse(self, command):
        """
        We simply add action parameters to the
        params dict, assuming there will be no
        conflict of names (need to ensure this
        when setting action syntax); this *is*
        a workaround, but should work fine for
        now - might write a preprocessor later
        to pick up and fix any possible issues
        :param command: str, description of the actions
        :return: None
        """
        actions = [comm.strip() for comm in command.split(';')]
        for action in actions:
            super().parse(action)
        self.action_type = [action.split()[0] for action in actions]


if __name__ == "__main__":
    scr = Script(sys.argv[1])
    # print(scr.scenes[0].tcl())
    scr.render()
