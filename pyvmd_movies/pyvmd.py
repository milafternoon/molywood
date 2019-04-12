class Script:
    """
    Main class that will combine all information
    and render the movie
    """
    def __init__(self):
        self.subscripts = []
    
    def render(self, draft=False, framerate=20, keepframes=False):
        pass
    
    def show_script(self):
        for subscript in self.subscripts:
            subscript.show_script()


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
        if isinstance(trajs, str):
            self.trajs.append(trajs)
        else:
            self.trajs.extend(trajs)
    
    def from_file(self, filename):
        pass
    
    def add_action(self, description):
        if 'and' not in description:
            self.actions.append(Action(description))
        else:
            self.actions.append(SimultaneousAction(description.split(' and ')))

    def show_script(self):
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
        self.frames = []  # should (?) contain a list of frames in the overall movie's numbering
    
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
        pass
        
        
class SimultaneousAction:
    """
    Intended to represent a number of actions
    that take place simultaneously
    """
    def __init__(self, descriptions):
        self.actions = [Action(description) for description in descriptions]