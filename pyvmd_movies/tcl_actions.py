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
    """
    increments = sigmoid_increments(n_points, abruptness)
    return cumsum*increments/np.sum(increments)


def sigmoid_norm_prod(cumprod, n_points, abruptness=1):
    """
    Yields n_points increments that multiply to cumprod
    :param cumprod: float, cumulative sum of the increments
    """
    increments = 1 + sigmoid_increments(n_points, abruptness)
    prod = np.prod(increments)
    exponent = np.log(cumprod)/np.log(prod)
    return increments**exponent


def logistic(x, k):
    return 1/(1+np.exp(-k*x))


def logistic_deriv(x, k):
    l = logistic(x, k)
    return l*(1-l)


def gen_loop(action):
    iterators = gen_iterators(action)
    command = gen_command(action)
    # TODO separate into lists of increments and have a single list of iterators that refers to individual lists
    code = 'foreach t [list {}] \{ {}  \nputs "rendering frame: ' \
           '$fr\n"render RENDERMETHOD {}-$fr.RENDER_EXTENSION RENDER_MODIFIERS\nincr fr\}'.format(iterators,
                                                                                                  command,
                                                                                                  action.scene.name)


def gen_iterators(action):
    try:
        time = action.parameters['t']
    except KeyError:
        try:
            nframes = action.parameters['nframes']
        except KeyError:
            raise ValueError('Either "t" or "nframes" should be set for action {}'.format(action.description))
    else:
        nframes = int(float(time)*action.scene.script.fps)
    try:
        sigmoid = action.parameters['sigmoid']
        sigmoid = True if sigmoid.lower() in ['true', 't', 'y', 'yes'] else False
    except KeyError:
        sigmoid = False
    # TODO get range and generate increments
    

def gen_command(action):
    """
    We assume action_type is either a list of strings
    or a single string, so that one does not need to care
    whether we're dealing with a single action or many
    :param action: either Action or SimultaneousAction
    :return: str, TCL command
    """
    command = ''
    if 'rotate' in action.action_type:
        axis = action.parameters['axis']
        command = command + "rotate {} by $t\n".format(axis)
    if 'make_transparent' in action.action_type:
        # TODO first duplicate material and set opacity
        pass
    if 'zoom_in' in action.action_type or 'zoom_out' in action.action_type:
        command = command + "scale by $t"
    return command