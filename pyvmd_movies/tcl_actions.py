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
    increments = logistic_deriv(points, abruptness)
    return increments
    

def sigmoid_norm_sum(cumsum, n_points, abruptness=1):
    """
    Yields n_points increments that sum to cumsum
    :param cumsum: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: np.array, array of increments
    """
    increments = sigmoid_increments(n_points, abruptness)
    return cumsum*increments/np.sum(increments)


def sigmoid_norm_prod(cumprod, n_points, abruptness=1):
    """
    Yields n_points increments that multiply to cumprod
    :param cumprod: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: np.array, array of increments
    """
    increments = 1 + sigmoid_increments(n_points, abruptness)
    prod = np.prod(increments)
    exponent = np.log(cumprod)/np.log(prod)
    return increments**exponent


def sigmoid_norm_sum_linear_mid(cumsum, n_points, abruptness=1, fraction_linear=0.8):
    """
    Yields n_points increments that sum to cumsum
    by first starting with smooth sigmoid increments,
    then incrementing linearly, and then stopping
    smoothly again with sigmoid increments
    (e.g. we want to rotate more or less continuously
    by 720deg about an axis, but start and finish smoothly)
    :param cumsum: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :param fraction_linear: float, fraction of the action spent in the linear regime
    :return: np.array, array of increments
    """
    n_points_sigm = int(n_points * (1-fraction_linear))
    n_points_linear = n_points - n_points_sigm
    increments = sigmoid_increments(n_points_sigm, abruptness)
    midpoint = len(increments)//2
    midpoint_increment = increments[midpoint]
    increments = np.concatenate((increments[:midpoint],
                                 np.ones(n_points_linear)*midpoint_increment,
                                 increments[midpoint:]))
    return cumsum * increments / np.sum(increments)


def logistic(x, k):
    """
    The logistic fn used to smoothen transitions
    :param x: abscissa
    :param k: transition abruptness
    :return: float or array, value of the logistic fn
    """
    return 1/(1+np.exp(-k*x))


def logistic_deriv(x, k):
    """
    Derivative of the logistic fn used to smoothen transitions
    (in a discretized version yields single-step increments)
    :param x: abscissa
    :param k: transition abruptness
    :return: float or array, value of the logistic fn derivative
    """
    logi = logistic(x, k)
    return logi*(1-logi)


def gen_loop(action):
    """
    The main fn that generates TCL code (mostly loops,
    hence the name). We use three-letter names for
    variables/dict entries according to the convention:
    center_view -> ctr;
    rotate -> rot;
    zoom_in/zoom_out -> zin/zou;
    make_transparent/make_opaque -> mtr/mop;
    animate -> ani
    :param action: Action or SimultaneousAction, object to extract info from
    :return: str, formatted TCL code
    """
    setup = gen_setup(action)
    iterators = gen_iterators(action)
    command = gen_command(action)
    rendermethod = 'snapshot' if action.scene.script.draft else 'TachyonInternal'
    extension = 'png' if action.scene.script.draft else 'tga'
    resolution = '-res {} {}'.format(*action.scene.resolution) if not action.scene.script.draft else ''
    code = "\n\nset fr {}\n".format(action.initframe)
    for act in setup.keys():
        code = code + setup[act]
    for act in iterators.keys():
        code = code + 'set {} [list {}]\n'.format(act, iterators[act])
    if action.framenum > 0:
        code = code + 'for {{set i 0}} {{$i < {}}} {{incr i}} {{\n'.format(action.framenum)
        code = code + '  puts "rendering frame: $fr"\n'
        for act in command.keys():
            code = code + '  ' + command[act]
        code = code + '  render {} {}-$fr.{} {}\n  incr fr\n}}'.format(rendermethod, action.scene.name,
                                                                     extension, resolution)
    return code


def gen_setup(action):
    """
    Some actions (e.g. centering) require a setup step that
    only has to be performed once; this fn is supposed
    to take care of such thingies
    :param action: Action or SimultaneousAction, object to extract info from
    :return: dict, formatted as label: command
    """
    setups = {}
    if 'center_view' in action.action_type:
        try:
            new_center_selection = action.parameters['selection']
        except KeyError:
            raise ValueError('With center_view, you need to specify a selection (vmd-compatible syntax, in quot marks)')
        else:
            setups['ctr'] = 'set csel [atomselect top "{}"]\nset gc [veczero]\nforeach coord [$csel get {{x y z}}] ' \
                            '{{\n  set gc [vecadd $gc $coord]\n}}\n' \
                            'set cent [vecscale [expr 1.0 /[$csel num]] $gc]\n' \
                            'molinfo top set center [list $cent]\n'.format(new_center_selection)
    return setups


def gen_iterators(action):
    """
    to serve both Action and SimultaneousAction, we return
    a dictionary with three-letter labels and a list of
    values already formatted as a string
    :param action: Action or SimultaneousAction, object to extract info from
    :return: dict, formatted as label: iterator
    """
    iterators = {}
    num_precision = 5
    try:
        sigmoid = action.parameters['sigmoid']
        sls = True if sigmoid.lower() == 'sls' else False  # sls stands for smooth-linear-smooth
        sigmoid = True if sigmoid.lower() in ['true', 't', 'y', 'yes'] else False
    except KeyError:
        sigmoid = True
        sls = False
    try:
        abruptness = float(action.parameters['abruptness'])
    except KeyError:
        abruptness = 1
    if 'rotate' in action.action_type:
        if sigmoid:
            arr = sigmoid_norm_sum(float(action.parameters['angle']), action.framenum, abruptness)
        elif sls:
            arr = sigmoid_norm_sum_linear_mid(float(action.parameters['angle']), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * float(action.parameters['angle'])/action.framenum
        iterators['rot'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'zoom_in' in action.action_type:
        if sigmoid:
            arr = sigmoid_norm_prod(float(action.parameters['scale']), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * float(action.parameters['scale'])**(1/action.framenum)
        iterators['zin'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'zoom_out' in action.action_type:
        if sigmoid:
            arr = sigmoid_norm_prod(1/float(action.parameters['scale']), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * 1/(float(action.parameters['scale'])**(1/action.framenum))
        iterators['zou'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'make_transparent' in action.action_type:
        if sigmoid:
            arr = 1 - np.cumsum(sigmoid_norm_sum(1, action.framenum, abruptness))
        else:
            arr = np.linspace(1, 0, action.framenum)
        iterators['mtr'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'make_opaque' in action.action_type:
        if sigmoid:
            arr = np.cumsum(sigmoid_norm_sum(1, action.framenum, abruptness))
        else:
            arr = np.linspace(0, 1, action.framenum)
        iterators['mop'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'animate' in action.action_type:
        # TODO enable specification of time ONLY, frames ONLY or time AND frames
        try:
            frames = [int(x) for x in action.parameters['frames'].split(':')]
        except KeyError:
            raise ValueError('With "animate", "frames" has to be specified using the syntax begin:end:stride')
        else:
            if len(frames) == 2:
                frames.append(1)
            arr = np.arange(frames[0], frames[1], frames[2])
            iterators['ani'] = ' '.join([str(int(el)) for el in arr])
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
        commands['rot'] = "set t [lindex $rot $i]\n  rotate {} by $t\n".format(axis)
    if 'make_transparent' in action.action_type or 'make_opaque' in action.action_type:
        material = action.parameters['material']
        keyw = 'mtr' if 'make_transparent' in action.action_type else 'mop'
        commands[keyw] = "set t [lindex ${} $i]\n  material change opacity {} $t\n".format(keyw, material)
    if 'zoom_in' in action.action_type:
        commands['zin'] = "set t [lindex $zin $i]\n  scale by $t\n"
    elif 'zoom_out' in action.action_type:
        commands['zou'] = "set t [lindex $zou $i]\n  scale by $t\n"
    if 'animate' in action.action_type:
        commands['ani'] = "set t [lindex $ani $i]\n  animate goto $t\n"
    return commands
