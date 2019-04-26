class Script:
    """
    Main class that will combine all information
    and render the movie (possibly with multiple
    panels, overlays etc.)
    """
    def __init__(self):
        self.subscripts = []
        self.directives = {}
        self.fps = 20
        
    def render(self, draft=False, framerate=20, keepframes=False):
        """
        The final fn that renders the movie (runs
        the TCL script, then uses combine and/or
        ffmpeg to assemble the movie frame by frame)
        :param draft: bool, use screenshots to get a quick-and-dirty version
        :param framerate: int, will use the desired framerate
        :param keepframes: bool, whether to keep frames after compiling the movie
        :return: None
        """
        pass
    
    def show_script(self):
        """
        Shows a sequence of scenes currently
        buffered in the object for rendering
        :return: None
        """
        for subscript in self.subscripts:
            print('\n\n\tScene {}: \n\n'.format(subscript.name))
            subscript.show_script()

    def from_file(self, filename):
        """
        Reads the full movie script from an input file
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
                    multiline = multiline + line
                elif multiline and '}' in line:
                    subscripts[current_sub].append(multiline + line)
                    multiline = None
                else:
                    subscripts[current_sub].append(line)
        self.directives = self.parse_directives(master_setup)
        self.subscripts = self.parse_subscripts(subscripts)
        
    @staticmethod
    def parse_directives(directives):
        dirs = {}
        for directive in directives:
            entries = directive.split()
            dirs[entries[0]] = {}
            for entry in entries[1:]:
                key, value = entry.split('=')
                dirs[entries[0]][key] = value
        return dirs
    
    def parse_subscripts(self, subscripts):
        objects = []
        struct, traj, tcl = None, None, None
        for sub in subscripts.keys():
            if subscripts[sub]:
                if sub in self.directives.keys():
                    try:
                        struct = self.directives[sub]['structure']
                    except KeyError:
                        pass
                    try:
                        traj = self.directives[sub]['trajectory']
                    except KeyError:
                        pass
                    try:
                        tcl = self.directives[sub]['visualization']
                    except KeyError:
                        pass
                objects.append(Scene(self, sub, struct, traj, tcl))
                for action in subscripts[sub]:
                    objects[-1].add_action(action)
        return objects
        

class Scene:
    """
    A Scene instance is restricted to a single
    molecular system, and hence has to be initialized
    with a valid input file
    """
    def __init__(self, script, name, molecule_file=None, traj=None, tcl=None, fps=20):
        self.script = script
        self.name = name
        self.system = molecule_file
        self.traj = traj
        self.visualization = tcl
        self.actions = []
    
    def add_traj(self, traj):
        """
        Allows to add a trajectory to VMD after the
        object was initialized
        :param traj: str, trajectory filename
        :return: None
        """
        self.traj = traj
    
    def add_action(self, description):
        """
        Adds an action to the subscript
        :param description: str, description of the action
        :return: None
        """
        if not description.startswith('{'):
            self.actions.append(Action(self, description))
        else:
            self.actions.append(SimultaneousAction(self, description))

    def show_script(self):
        """
        Shows actions scheduled for rendering
        within the current subscript
        :return:
        """
        for action in self.actions:
            print(action)
            
    def tcl(self):
        if self.system:
            filetype = self.system.split('.')[-1]
            code = 'mol new {} type {} first 0 last -1 step 1 ' \
                          'filebonds 1 autobonds 1 waitfor all'.format(self.system, filetype)
            if self.traj:
                trajtype = self.traj.split('.')[-1]
                code = code + 'mol addfile {} type {} first 0 last -1 step 1 ' \
                              'filebonds 1 autobonds 1 waitfor all'.format(self.traj, trajtype)
        elif self.visualization:
            code = open(self.visualization, 'r').readlines()
        else:
            raise ValueError('Either "structure" or "visualization" has to be specified for {}'.format(self.name))
        for action in self.actions:
            code = code + action.tcl()
        return code
        
        
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
        self.parameters = None  # will be a dict of action parameters
        self.initframe = None  # should contain an initial frame number in the overall movie's numbering
    
    def __repr__(self):
        return self.description
    
    def tcl(self):
        """
        Should produce the TCL code that will
        produce the action in question
        :return: str, TCL code
        """
        code = "set fr {}".format(self.initframe)
    
    def parser(self, command):
        """
        Parses a single command from the text input
        and converts into action parameters
        :param command: str, description of the action
        :return: None
        """
        pass
        
        
class SimultaneousAction:
    """
    Intended to represent a number of actions
    that take place simultaneously (e.g. zoom
    and rotation)
    """
    def __init__(self, scene, description):
        self.scene = scene
        self.description = description