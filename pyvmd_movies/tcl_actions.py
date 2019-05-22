import numpy as np


def sigmoid_increments(n_points, abruptness):
    """
    Returns stepwise increments that result in logistic
    growth from 0 to sum over n_points
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: numpy.array, array of increments
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
    :return: numpy.array, array of increments
    """
    increments = sigmoid_increments(n_points, abruptness)
    return cumsum*increments/np.sum(increments)


def sigmoid_norm_prod(cumprod, n_points, abruptness=1):
    """
    Yields n_points increments that multiply to cumprod
    :param cumprod: float, cumulative sum of the increments
    :param n_points: int, number of increments
    :param abruptness: float, how fast the transition is
    :return: numpy.array, array of increments
    """
    increments = 1 + sigmoid_increments(n_points, abruptness)
    prod = np.prod(increments)
    exponent = np.log(cumprod)/np.log(prod)
    return increments**exponent


def sigmoid_norm_sum_linear_mid(cumsum, n_points, abruptness=1, fraction_linear=0.6):
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
    :return: numpy.array, array of increments
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
    :return: numpy.array, values of the logistic fn
    """
    return np.array(1/(1+np.exp(-k*x)))


def logistic_deriv(x, k):
    """
    Derivative of the logistic fn used to smoothen transitions
    (in a discretized version yields single-step increments)
    :param x: abscissa
    :param k: transition abruptness
    :return: numpy.array, values of the logistic fn derivative
    """
    logi = logistic(x, k)
    return np.array(logi*(1-logi))


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
    rendermethod = 'Tachyon'
    code = "\n\nset fr {}\n".format(action.initframe)
    for act in setup.keys():
        code = code + setup[act]
    for act in iterators.keys():
        code += 'set {} [list {}]\n'.format(act, iterators[act])
    if action.framenum > 0:
        code += 'for {{set i 0}} {{$i < {}}} {{incr i}} {{\n'.format(action.framenum)
        code += '  puts "rendering frame: $fr"\n'
        for act in command.keys():
            code = code + '  ' + command[act]
        code += '  render {rm} {sc}-$fr.dat\n  "/usr/local/lib/vmd/tachyon_LINUXAMD64" ' \
                '-aasamples 12 {sc}-$fr.dat -format TARGA -o {sc}-$fr.tga -res {rs}' \
                '\n  incr fr\n}}'.format(rm=rendermethod, sc=action.scene.name,
                                         rs=' '.join(str(x) for x in action.scene.resolution))
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
    if 'animate' in action.action_type:
        try:
            smooth = action.parameters['smooth']
        except KeyError:
            pass
        else:
            check_if_convertible(smooth, int, 'smooth')
            setups['ani'] = 'set mtop [molinfo top]\nset nrep [molinfo $mtop get numreps]\n' \
                            'for {{set i 0}} {{$i < $nrep}} {{incr i}} {{\n' \
                            'mol smoothrep $mtop $i {}\n}}\n'.format(smooth)
    if 'add_label' in action.action_type:
        try:
            label_color = action.parameters['color']
        except KeyError:
            label_color = 'black'
        atom_index = action.parameters['atom_index']
        label = action.parameters['label']
        check_if_convertible(atom_index, int, 'atom_index')
        setups['adl'] = 'label add Atoms 0/{}\nlabel textsize 1.5\nlabel textthickness 2\ncolor Labels Atoms {}\n' \
                        'label textformat Atoms 0 "{}"\n\n'.format(atom_index, label_color, label)
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
    else:
        check_if_convertible(abruptness, float, 'abruptness')
    if 'rotate' in action.action_type:
        angle = action.parameters['angle']
        check_if_convertible(angle, float, 'smooth')
        if sigmoid:
            arr = sigmoid_norm_sum(float(angle), action.framenum, abruptness)
        elif sls:
            arr = sigmoid_norm_sum_linear_mid(float(angle), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * float(angle)/action.framenum
        iterators['rot'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'zoom_in' in action.action_type:
        scale = action.parameters['scale']
        check_if_convertible(scale, float, 'scale')
        if sigmoid:
            arr = sigmoid_norm_prod(float(scale), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * float(scale)**(1/action.framenum)
        iterators['zin'] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'zoom_out' in action.action_type:
        scale = action.parameters['scale']
        check_if_convertible(scale, float, 'scale')
        if sigmoid:
            arr = sigmoid_norm_prod(1/float(scale), action.framenum, abruptness)
        else:
            arr = np.ones(action.framenum) * 1/(float(scale)**(1/action.framenum))
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
        animation_frames = [x for x in action.parameters['frames'].split(':')]
        for val in animation_frames:
            check_if_convertible(val, int, 'frames')
        arr = np.linspace(int(animation_frames[0]), int(animation_frames[1]), action.framenum).astype(int)
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
        if axis.lower() not in 'xyz':
            raise RuntimeError("'axis' must be either 'x', 'y' or 'z', {} was given instead".format(axis))
        commands['rot'] = "set t [lindex $rot $i]\n  rotate {} by $t\n".format(axis.lower())
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


def check_if_convertible(string, object_type, param_name):
    try:
        _ = object_type(string)
    except ValueError:
        raise RuntimeError("'{}' must be {}, {} was given instead".format(param_name, object_type, string))
