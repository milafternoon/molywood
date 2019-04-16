class Script:
    """
    Main class that will combine all information
    and render the movie (possibly with multiple
    panels, overlays etc.)
    """
    def __init__(self):
        self.subscripts = []
    
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
            subscript.show_script()

    def from_file(self, filename):
        """
        Reads the full movie script from an input file
        :param filename: str, name of the file
        :return: None
        """
        pass


class Subscript:
    """
    A Subscript instance is restricted to a single
    molecular system, and hence has to be initialized
    with a valid input file
    """
    def __init__(self, molecule_file, trajs=None):
        self.system = molecule_file
        self.trajs = []
        if trajs:
            if isinstance(trajs, str):
                self.trajs = [trajs]
            else:
                self.trajs = trajs
        self.actions = []
    
    def add_trajs(self, trajs):
        """
        Allows to add trajectories to VMD after the
        object was initialized
        :param trajs: str or list of str, trajectory filename(s)
        :return: None
        """
        if isinstance(trajs, str):
            self.trajs.append(trajs)
        else:
            self.trajs.extend(trajs)
    
    def add_action(self, description):
        """
        Adds an action to the subscript
        :param description: str, description of the action
        :return: None
        """
        if 'and' not in description:
            self.actions.append(Action(description))
        else:
            self.actions.append(SimultaneousAction(description.split(' and ')))

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
    def __init__(self, descriptions):
        self.actions = [Action(description) for description in descriptions]