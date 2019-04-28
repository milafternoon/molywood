import numpy as np


def sigmoid_increments(n_points, abruptness):
    """
    Returns stepwise increments that result in logistic
    growth from 0 to sum over n_points
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: np.array, array of increments
    """
    scale_range = (-5, 5)
    points = np.linspace(*scale_range, n_points)
    increments = np.array([logistic_deriv(x, abruptness) for x in points])
    return increments
    

def sigmoid_norm_sum(cumsum, n_points, abruptness=1):
    """
    Yields n_points increments that sum to cumsum
    :param cumsum: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    """
    increments = sigmoid_increments(n_points, abruptness)
    return cumsum*increments/np.sum(increments)


def sigmoid_norm_prod(cumprod, n_points, abruptness=1):
    """
    Yields n_points increments that multiply to cumprod
    :param cumprod: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    """
    increments = 1 + sigmoid_increments(n_points, abruptness)
    prod = np.prod(increments)
    exponent = np.log(cumprod)/np.log(prod)
    return increments**exponent


def logistic(x, k):
    return 1/(1+np.exp(-k*x))


def logistic_deriv(x, k):
    logi = logistic(x, k)
    return logi*(1-logi)


def gen_loop(action):
    iterators = gen_iterators(action)
    command = gen_command(action)
    rendermethod = 'Snapshot' if action.scene.script.draft else 'TachyonInternal'
    extension = 'png' if action.scene.script.draft else 'tga'
    resolution = '-res {} {}'.format(*action.scene.resolution) if not action.scene.script.draft else ''
    code = "\n\nset fr {}\n".format(action.initframe)
    for act in iterators.keys():
        code = code + 'set {} [list {}]\n'.format(act, iterators[act])
    code = code + 'for {{set i 0}} {{$i < {}}} {{incr i}} {{'.format(action.framenum)
    code = code + 'puts "rendering frame: $fr\n'
    for act in command.keys():
        code = code + command[act]
    code = code + 'render {} {}-$fr.{} {}\nincr fr\n\}'.format(rendermethod, action.scene.name, extension, resolution)
    return code


def gen_iterators(action):
    """
    to serve both Action and SimultaneousAction, we return
    a dictionary with three-letter labels and a list of
    values already formatted as a string
    :param action: Action or SimultaneousAction, object to extract info from
    :return: dict, formatted as label: iterator
    """
    iterators = {}
    try:
        sigmoid = action.parameters['sigmoid']
        sigmoid = True if sigmoid.lower() in ['true', 't', 'y', 'yes'] else False
    except KeyError:
        sigmoid = False
    try:
        abruptness = float(action.parameters['abruptness'])
    except KeyError:
        abruptness = 1
    if 'rotate' in action.action_type:
        arr = sigmoid_norm_sum(action.parameters['angle'], action.framenum, abruptness)
        iterators['rot'] = ' '.join(list(arr))
    return iterators
    

def gen_command(action):
    """
    We assume action_type is either a list of strings
    or a single string, so that one does not need to care
    whether we're dealing with a single action or many;
    we return a dict formatted consistently with gen_iterators()
    :param action: either Action or SimultaneousAction
    :return: dict, formatted as label: TCL command
    """
    commands = {}
    if 'rotate' in action.action_type:
        axis = action.parameters['axis']
        commands['rot'] = "set t [lindex $rot $i]\nrotate {} by $t\n".format(axis)
    if 'make_transparent' in action.action_type:
        # TODO first duplicate material and set opacity?
        pass
    if 'zoom_in' in action.action_type:
        commands['zin'] = "set t [lindex $zin $i]\nscale by $t\n"
    elif 'zoom_out' in action.action_type:
        commands['zou'] = "set t [lindex $zou $i]\nscale by $t\n"
    return commands
