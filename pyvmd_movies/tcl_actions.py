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
    increments = np.array(1) + sigmoid_increments(n_points, abruptness)
    prod = np.prod(increments)
    exponent = np.log(cumprod)/np.log(prod)
    return increments**exponent


def sigmoid_norm_sum_linear_mid(cumsum, n_points, abruptness=1, fraction_linear=0.4):
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
    hence the name). We mostly use three-letter names for
    variables/dict entries according to the convention:
    center_view -> ctr;
    rotate -> rot;
    zoom_in/zoom_out -> zin/zou;
    animate -> ani etc.
    :param action: Action or SimultaneousAction, object to extract info from
    :return: str, formatted TCL code
    """
    setup = gen_setup(action)
    iterators = gen_iterators(action)
    command = gen_command(action)
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
        if action.scene.script.draft:
            code += '  render snapshot {sc}-$fr.tga\n  incr fr\n}}'.format(sc=action.scene.name)
        else:
            code += '  render Tachyon {sc}-$fr.dat\n  \"$env(TACHYON_BIN)\" ' \
                    '-aasamples 12 {sc}-$fr.dat -format TARGA -o {sc}-$fr.tga -res {rs}' \
                    '\n  incr fr\n}}'.format(sc=action.scene.name, rs=' '.join(str(x) for x in action.scene.resolution),
                                             tc=action.scene.tachyon)
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
            setups['ani'] = 'foreach nmol [molinfo list] {{\nset nrep [molinfo $nmol get numreps]\n' \
                            'for {{set i 0}} {{$i < $nrep}} {{incr i}} {{\n' \
                            'mol smoothrep $mtop $i {}\n}}\n'.format(smooth)  # TODO smooth for all mols (distances?)
    if 'add_label' in action.action_type:
        try:
            label_color = action.parameters['label_color']
        except KeyError:
            label_color = 'black'
        try:
            tsize = action.parameters['text_size']
        except KeyError:
            tsize = 1.0
        else:
            check_if_convertible(tsize, float, 'text_size')
        try:
            alias = action.parameters['alias']
        except KeyError:
            alias = 'label{}'.format(len(action.scene.labels['Atoms'])+1)
        action.scene.labels['Atoms'].append(alias)
        atom_index = action.parameters['atom_index']
        label = action.parameters['label']
        check_if_convertible(atom_index, int, 'atom_index')
        setups['adl'] = 'set nlab [llength [label list Atoms]]\nlabel add Atoms 0/{}\nlabel textsize {}\n' \
                        'label textthickness 3\ncolor Labels Atoms {}\nlabel textformat Atoms $nlab "{}"\n' \
                        '\n'.format(atom_index, tsize, label_color, label)
    if 'remove_label' in action.action_type or 'remove_distance' in action.action_type:
        lab_type = 'Atoms' if 'remove_label' in action.action_type else 'Bonds'
        remove_all = False
        try:
            alias = action.parameters['alias']
        except KeyError:
            alias = ''
            try:
                remove_all = action.parameters['all']
            except KeyError:
                raise RuntimeError('To remove a label, either "all=t" or "alias=..." have to be specified')
            else:
                if remove_all in ['y', 't', 'yes', 'true']:
                    remove_all = True
                else:
                    raise RuntimeError('To remove a label, either "all=t" or "alias=..." have to be specified')
        if alias:
            try:
                alias_index = action.scene.labels[lab_type].index(alias)
            except ValueError:
                raise RuntimeError('"{}" is not a valid alias; to remove a label, alias has to match a previously added'
                                   'one'.format(alias))
            else:
                action.scene.labels[lab_type].pop(alias_index)
                setups['rml'] = 'label delete {} {}\n'.format(lab_type, alias_index)
        elif remove_all:
            nlab = len(action.scene.labels[lab_type])
            setups['rml'] = nlab * 'label delete {} 0\n'.format(lab_type)
            action.scene.labels[lab_type] = []
    if 'add_distance' in action.action_type:
        try:
            label_color = action.parameters['label_color']
        except KeyError:
            label_color = 'black'
        try:
            tsize = action.parameters['text_size']
        except KeyError:
            tsize = 1.0
        else:
            check_if_convertible(tsize, float, 'text_size')
        try:
            alias = action.parameters['alias']
        except KeyError:
            alias = 'label{}'.format(len(action.scene.labels['Bonds'])+1)
        action.scene.labels['Bonds'].append(alias)
        sel1 = action.parameters['selection1']
        sel2 = action.parameters['selection2']  # TODO might not work with display none?
        setups['add'] = 'save_vp 1\n'
        setups['add'] += 'proc geom_center {selection} {\n    set gc [veczero]\n' \
                         '    foreach coord [$selection get {x y z}] {\n       set gc [vecadd $gc $coord]}\n    ' \
                         'return [vecscale [expr 1.0 /[$selection num]] $gc]}\n\n'
        setups['add'] += 'proc retr_vp {view_num} {\n  global viewpoints  \n  foreach mol [molinfo list] {\n' \
                         '    molinfo $mol set rotate_matrix   $viewpoints($view_num,0,0)' \
                         '\n    molinfo $mol set center_matrix   $viewpoints($view_num,0,1)' \
                         '\n    molinfo $mol set scale_matrix   $viewpoints($view_num,0,2)' \
                         '\n    molinfo $mol set global_matrix   $viewpoints($view_num,0,3)\n  }\n}\n\n'
        setups['add'] += 'set newmol{} [mol new atoms 2]\nmol representation Lines\nmol selection all\n' \
                         'mol addrep $newmol{}\nlabel add Bonds 1/0 1/1\ncolor Labels Bonds {}\n' \
                         'label textsize {}\nlabel textthickness 3\nmol top 0\n\n'.format(alias, alias, label_color,
                                                                                          tsize)
        setups['add'] += 'proc reposition_dummies {{molind}} {{  animate dup $molind\n' \
                         '  set sel [atomselect $molind "index 0"]\n  set ssel [atomselect 0 "{}"]\n' \
                         '  $sel set {{x y z}} [list [geom_center $ssel]]\n  set ssel [atomselect 0 "{}"]\n' \
                         '  set sel [atomselect $molind "index 1"]\n  $sel set {{x y z}} [list [geom_center $ssel]]\n' \
                         '}}\n\nreposition_dummies $newmol{}\n\n'.format(sel1, sel2, alias)
        setups['add'] += 'display resetview\n'
        setups['add'] += 'retr_vp 1\n'  # re-align all after display resetview
    if 'highlight' in action.action_type:
        colors = {'black': 16, 'red': 1, 'blue': 0, 'orange': 3, 'yellow': 4, 'green': 7, 'white': 8}
        hls = [action.highlights[x] for x in action.highlights.keys()]
        hl_labels = list(action.highlights.keys())
        for lb, hl in zip(hl_labels, hls):
            setups[lb] = ''
            mode = hl['mode'] if 'mode' in hl.keys() else 'ud'
            if mode in ['u', 'ud']:
                setups[lb] += 'material add copy Opaque\nset mat{} [lindex [material list] end]\n' \
                              'material change opacity $mat{} 0\n'.format(lb, lb)
            try:
                color_key = hl['color']
            except KeyError:
                color_key = 'red'
            try:
                style = hl['style'].lower()  # parse as lowercase to avoid confusion among users
            except KeyError:
                style = 'newcartoon'
            style_params = {'newcartoon': ['NewCartoon', '0.32 20 4.1 0'], 'surf': ['Surf', '1.4 0.0'],
                            'quicksurf': ['QuickSurf', '1.05 1.3 0.5 3.0'], 'licorice': ['Licorice', '0.31 12.0 12.0'],
                            'vdw': ['VDW', '1.05 20.0'], 'tube': ['Tube', '0.40 20.0']}
            if style not in style_params.keys():
                raise RuntimeError('{} is not a valid style; "NewCartoon", "Surf", "QuickSurf", "VDW", "Tube" '
                                   'and "Licorice" are available'.format(style))
            if color_key in colors.keys():
                cl = 'ColorID {}'.format(colors[color_key])
            else:
                try:
                    cl = 'ColorID {}'.format(int(color_key))
                except ValueError:
                    avail_schemes = {"name": "Name", "type": "Type", "resname": "ResName", "restype": "ResType",
                                     "resid": "ResID", "element": "Element", "molecule": "Molecule",
                                     "structure": "Structure", "chain": "Chain", "beta": "Beta",
                                     "occupancy": "Occupancy", "mass": "Mass", "charge": "Charge", "pos": "Pos"}
                    if color_key.lower() in avail_schemes.keys():
                        cl = avail_schemes[color_key]
                    else:
                        raise RuntimeError('{} is not a valid color description'.format(color_key))
            if mode in ['u', 'ud']:
                sel = hl['selection']
                setups[lb] += 'mol representation {} {}\nmol color {}\n' \
                              'mol material $mat{}\nmol selection {{{}}}\n' \
                              'mol addrep top\n'.format(*style_params[style], cl, lb, sel)
    if 'fit_trajectory' in action.action_type:
        sel = action.parameters['selection']  # TODO smoothly transition current frame?
        setups['fit'] = 'set fit_reference [atomselect top "{}" frame 0]\nset fit_compare [atomselect top "{}"]\n' \
                        'set fit_system [atomselect top "all"]\nset num_steps [molinfo top get numframes]\n' \
                        'for {{set frame 0}} {{$frame < $num_steps}} {{incr frame}} {{\n' \
                        '    $fit_compare frame $frame\n    $fit_system frame $frame\n' \
                        '    set fit_matrix [measure fit $fit_compare $fit_reference]\n' \
                        '    $fit_system move $fit_matrix }}\n\n'.format(sel, sel)
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
    sigmoid, sls, abruptness = check_sigmoid(action.parameters)
    if 'rotate' in action.action_type:
        for rkey in action.rots.keys():
            angle = action.rots[rkey]['angle']
            check_if_convertible(angle, float, 'smooth')
            if sigmoid:
                arr = sigmoid_norm_sum(float(angle), action.framenum, abruptness)
            elif sls:
                arr = sigmoid_norm_sum_linear_mid(float(angle), action.framenum, abruptness)
            else:
                arr = np.ones(action.framenum) * float(angle)/action.framenum
            iterators[rkey] = ' '.join([str(round(el, num_precision)) for el in arr])
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
    if 'make_transparent' in action.action_type or 'make_opaque' in action.action_type:
        for t_ch in action.transp_changes.keys():
            try:
                until = action.parameters['limit']
            except KeyError:
                until = 0 if 'transparent' in t_ch else 1
            else:
                check_if_convertible(until, float, 'limit')
                until = float(until)
            try:
                start = action.parameters['start']
            except KeyError:
                start = 1 if 'transparent' in t_ch else 0
            else:
                check_if_convertible(start, float, 'start')
                start = float(start)
            sigmoid, sls, abruptness = check_sigmoid(action.transp_changes[t_ch])
            if sigmoid:
                if 'transparent' in t_ch:
                    arr = start - np.cumsum(sigmoid_norm_sum(start-until, action.framenum, abruptness))
                else:
                    arr = start + np.cumsum(sigmoid_norm_sum(until-start, action.framenum, abruptness))
            else:
                arr = np.linspace(start, until, action.framenum)
            iterators[t_ch] = ' '.join([str(round(el, num_precision)) for el in arr])
    if 'animate' in action.action_type:
        animation_frames = [x for x in action.parameters['frames'].split(':')]
        for val in animation_frames:
            check_if_convertible(val, int, 'frames')
        arr = np.linspace(int(animation_frames[0]), int(animation_frames[1]), action.framenum).astype(int)
        iterators['ani'] = ' '.join([str(int(el)) for el in arr])
    if 'highlight' in action.action_type:
        hls = [action.highlights[x] for x in action.highlights.keys()]
        hl_labels = list(action.highlights.keys())
        for lb, hl in zip(hl_labels, hls):
            try:
                mode = hl['mode']
            except KeyError:
                mode = 'ud'
            if mode == 'u':
                arr = np.cumsum(sigmoid_norm_sum(1, action.framenum, abruptness))
            elif mode == 'd':
                arr = np.cumsum(sigmoid_norm_sum(1, action.framenum, abruptness))[::-1]
            elif mode == 'ud':
                margin = int(0.25 * action.framenum)
                arr = np.cumsum(sigmoid_norm_sum(1, margin, abruptness))
                arr = np.concatenate((arr, np.ones(action.framenum - 2*margin), arr[::-1]))
            else:
                raise RuntimeError('"mode" should be "u", "d" or "ud"')
            iterators[lb] = ' '.join([str(round(el, num_precision)) for el in arr])
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
        for rkey in action.rots.keys():
            axis = action.rots[rkey]['axis']
            if axis.lower() not in 'xyz':
                raise RuntimeError("'axis' must be either 'x', 'y' or 'z', {} was given instead".format(axis))
            commands[rkey] = "set t [lindex ${} $i]\n  rotate {} by $t\n".format(rkey, axis.lower())
    if 'make_transparent' in action.action_type or 'make_opaque' in action.action_type:
        for t_ch in action.transp_changes.keys():
            material = action.transp_changes[t_ch]['material']
            commands[t_ch] = "set t [lindex ${} $i]\n  material change opacity {} $t\n".format(t_ch, material)
    if 'zoom_in' in action.action_type:
        commands['zin'] = "set t [lindex $zin $i]\n  scale by $t\n"
    elif 'zoom_out' in action.action_type:
        commands['zou'] = "set t [lindex $zou $i]\n  scale by $t\n"
    if 'animate' in action.action_type:
        commands['ani'] = "set t [lindex $ani $i]\n  animate goto $t\n"
        if len(action.scene.labels['Bonds']) > 0:
            for alias in action.scene.labels['Bonds']:
                commands['ani'] += 'reposition_dummies $newmol{}\n'.format(alias)
    if 'highlight' in action.action_type:
        hls = [action.highlights[x] for x in action.highlights.keys()]
        hl_labels = list(action.highlights.keys())
        for lb, hl in zip(hl_labels, hls):
            mode = hl['mode'] if 'mode' in hl.keys() else 'ud'
            if mode == 'd':
                try:
                    _ = hl['alias']
                except KeyError:
                    raise RuntimeError('When mode=d, an alias has to be supplied to specify which highlight'
                                       'has to be turned off.')
            commands[lb] = "set t [lindex ${} $i]\n  material change opacity $mat{} $t\n".format(lb, lb)
    return commands


def check_if_convertible(string, object_type, param_name):
    try:
        _ = object_type(string)
    except ValueError:
        raise RuntimeError("'{}' must be {}, instead '{}' was given".format(param_name, object_type, string))


def check_sigmoid(params_dict):
    try:
        sigmoid = params_dict['sigmoid']
        sls = True if sigmoid.lower() == 'sls' else False  # sls stands for smooth-linear-smooth
        sigmoid = True if sigmoid.lower() in ['true', 't', 'y', 'yes'] else False
    except KeyError:
        sigmoid = True
        sls = False
    try:
        abruptness = float(params_dict['abruptness'])
    except KeyError:
        abruptness = 1
    else:
        check_if_convertible(abruptness, float, 'abruptness')
    return sigmoid, sls, abruptness
