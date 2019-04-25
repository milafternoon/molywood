class Script:
    """
    Main class that will combine all information
    and render the movie (possibly with multiple
    panels, overlays etc.)
    """
    def __init__(self):
        self.subscripts = []
        self.directives = {}
    
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
            print('Subscript {}: \n\n'.format(subscript.name))
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
        struct, traj = None, None
        for sub in subscripts.keys():
            if sub in self.directives.keys():
                try:
                    struct = self.directives[sub]['structure']
                except KeyError:
                    pass
                try:
                    traj = self.directives[sub]['trajectory']
                except KeyError:
                    pass
            objects.append(Subscript(sub, struct, traj))
            for action in subscripts[sub]:
                objects[-1].add_action(action)
        return objects
        

class Subscript:
    """
    A Subscript instance is restricted to a single
    molecular system, and hence has to be initialized
    with a valid input file
    """
    def __init__(self, name, molecule_file=None, traj=None):
        self.name = name
        self.system = molecule_file
        self.traj = traj
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
            self.actions.append(Action(description))
        else:
            self.actions.append(SimultaneousAction(description))

    def show_script(self):
        """
        Shows actions scheduled for rendering
        within the current subscript
        :return:
        """
        for action in self.actions:
            print(action)
        
        
class Action:
    """
    Intended to represent a single action in
    a movie, e.g. a rotation, change of material
    or zoom-in
    """
    def __init__(self, description):
        self.description = description
        self.action_type = None
        self.nframes = 50
        self.modificators = None
        self.initframe = []  # should contain an initial frame number in the overall movie's numbering
    
    def __repr__(self):
        return self.description
    
    def tcl(self):
        """
        Should produce the TCL code that will
        produce the action in question
        :return: str, TCL code
        """
        pass
    
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
    def __init__(self, description):
        self.description = description