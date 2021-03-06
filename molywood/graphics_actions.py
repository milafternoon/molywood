import os
import numpy as np

# TODO add text labels generated on-the-fly
def postprocessor(script):
    """
    This is the key function that controls composition
    of the previously rendered scenes. It first applies
    overlays if requested, and then copies/moves/composes
    individual frames so that an initial set of
    scene1...png, sceneX...png files is converted
    into movie_name...png files that can then
    be merged into a file using ffmpeg.
    :param script: Script instance, the master object controlling the movie layout
    :return: None
    """
    try:
        layout_dirs = script.directives['layout']  # layout controls composition of panels
    except KeyError:
        layout_dirs = None
    for scene in script.scenes:
        for action in scene.actions:
            if 'add_overlay' in action.action_type:
                compose_overlay(action)
        
    if len(script.scenes) == 1:  # simplest case: one scene
        scene = script.scenes[0].name
        for fr in range(script.scenes[0].total_frames):
            os.system('mv {}-{}.png {}-{}.png'.format(scene, fr, script.name, fr))
            
    elif layout_dirs and len(script.scenes) > 1:  # here we parse multiple scenes: insets should go earlier!
        # if one has less frames than the other, copy last frame (N-n) times to make counts equal:
        if not all([sc.total_frames == script.scenes[0].total_frames for sc in script.scenes]):
            equalize_frames(script)
        nrows = int(layout_dirs['rows'])
        ncols = int(layout_dirs['columns'])
        labels_matrix = [[] for _ in range(nrows)]
        all_scenes = [sc.name for sc in script.scenes]
        positions = {}
        for scene in all_scenes:
            try:
                positions[tuple(int(x) for x in script.directives[scene]['position'].split(','))] = scene
            except KeyError:
                raise ValueError('The position for scene {} in the global layout is not specified'.format(scene))
        for r in range(nrows):
            for c in range(ncols):
                try:
                    scene_name = positions[(r, c)]
                except KeyError:
                    labels_matrix[r].append('')
                else:
                    labels_matrix[r].append(scene_name)
        convert_command = ''
        for r in range(nrows):
            convert_command += ' \( '
            for c in range(ncols):
                convert_command += str(labels_matrix[r][c]) + '-{}.png '
            convert_command += ' +append \) '
        convert_command += ' -append '
        for fr in range(script.scenes[0].total_frames):
            frames = [fr] * (nrows*ncols)
            os.system(script.convert + ' ' + convert_command.format(*frames) + '{}-{}.png'.format(script.name, fr))
            

def gen_fig(action):
    """
    Responsible for frame-by-frame generation of files
    associated with (a) external images and (b)
    on-the-fly generated matplotlib plots
    (essentially any graphics that is not rendered
    by TCL/VMD)
    :param action: Action, object to extract info from
    :return: None
    """
    convert = action.scene.script.convert
    if 'show_figure' in action.action_type:
        if 'figure' in action.parameters.keys():
            fig_file = action.parameters['figure']
            fig_file = action.scene.script.check_path(fig_file)
            for fr in range(action.initframe, action.initframe + action.framenum):
                os.system('{} {} -resize {}x{} {}-{}.png'.format(convert, fig_file, *action.scene.resolution,
                                                                 action.scene.name, fr))
        elif 'datafile' in action.parameters.keys():
            df = action.parameters['datafile']
            df = action.scene.script.check_path(df)
            data_simple_plot(action, df, 'spl')
            for fr in range(action.initframe, action.initframe + action.framenum):
                fig_file = '{}-{}.png'.format(action.scene.name, fr)
                os.system('{} spl-{} -resize {}x{} {}'.format(convert, fig_file, *action.scene.resolution, fig_file))
            
    if 'add_overlay' in action.action_type:
        frames = range(action.initframe, action.initframe + action.framenum)
        scene = action.scene.name
        res = action.scene.resolution
        for ovl in action.overlays.keys():
            if 'figure' in action.overlays[ovl].keys() or 'datafile' in action.overlays[ovl].keys():
                try:
                    scaling = float(action.overlays[ovl]['relative_size'])
                except KeyError:
                    raise RuntimeError("With add_overlay, 'relative_size=... has to be specified")
                else:
                    overlay_res = [scaling * r for r in res]
            if 'figure' in action.overlays[ovl].keys():
                fig_file = action.overlays[ovl]['figure']
                fig_file = action.scene.script.check_path(fig_file)
                for fr in frames:
                    ovl_file = '{}-{}-{}.png'.format(ovl, scene, fr)
                    os.system('{} {} -resize {}x{} {}'.format(convert, fig_file, *overlay_res, ovl_file))
            elif 'datafile' in action.overlays[ovl].keys():
                df = action.overlays[ovl]['datafile']
                df = action.scene.script.check_path(df)
                data_simple_plot(action, df, ovl)
                for fr in frames:
                    fig_file = '{}-{}-{}.png'.format(ovl, scene, fr)
                    os.system('{} {} -resize {}x{} {}'.format(convert, fig_file, *overlay_res, fig_file))
            elif 'text' in action.overlays[ovl].keys():
                text = action.overlays[ovl]['text']
                try:
                    tsize = int(action.overlays[ovl]['textsize'])
                except KeyError:
                    tsize = 24
                try:
                    animation_frames = [float(x) for x in action.overlays[ovl]['dataframes'].split(':')]
                    arr = np.linspace(animation_frames[0], animation_frames[1], action.framenum)
                except KeyError:
                    arr = np.arange(action.framenum)
                for fr in frames:
                    newtext = text.replace('[]', '{:.3f}').format(arr[fr-action.initframe])
                    fig_file = '{}-{}-{}.png'.format(ovl, scene, fr)
                    os.system('{} -size {}x{} xc:transparent -font "AvantGarde-Book" -pointsize {} '
                              '-gravity SouthWest -fill black -annotate +0+0 "{}" '
                              '{}'.format(convert, *res, tsize, newtext, fig_file))
                

def equalize_frames(script):
    """
    If individual scenes have different frame counts,
    this function appends the corresponding last figure
    to the shorter scenes
    :param script: Script instance, the master object controlling the movie layout
    :return: None
    """
    nframes = [sc.total_frames for sc in script.scenes]
    names = [sc.name for sc in script.scenes]
    highest = max(nframes)
    for n, nf in enumerate(nframes):
        if nf < highest:
            for i in range(nf, highest):
                if os.name == 'posix':
                    os.system('cp {}-{}.png {}-{}.png'.format(names[n], nf-1, names[n], i))
                else:
                    os.system('copy {}-{}.png {}-{}.png'.format(names[n], nf - 1, names[n], i))


def compose_overlay(action):
    """
    Introduces the overlay provided that the picture
    ('overlay-frame_name.png') was already produced
    and properly scaled by gen_fig
    :param action: Action or SimultaneousAction, object to extract data from
    :return: None
    """
    assert hasattr(action, 'overlays') and isinstance(action.overlays, dict)
    frames = range(action.initframe, action.initframe + action.framenum)
    scene = action.scene.name
    res = action.scene.resolution
    try:
        sigmoid = action.parameters['sigmoid']
    except KeyError:
        sigmoid = False
    else:
        sigmoid = True if sigmoid.lower() in ['true', 't', 'y', 'yes'] else False
    if sigmoid:
        sgm_frames = int(0.2*action.framenum)
        x = np.linspace(-5, 5, sgm_frames)
        sgm = 1/(1+np.exp(-x))
        opacity = np.concatenate((sgm, np.ones(action.framenum - 2 * sgm_frames), sgm[::-1]))
    else:
        opacity = np.ones(action.framenum)
    for ovl in action.overlays.keys():
        try:
            origin_frac = [float(x) for x in action.overlays[ovl]['origin'].split(',')]
        except KeyError:
            origin_frac = [0, 0]
        origin_px = [int(r*o) for r, o in zip(res, origin_frac)]
        for fr, opa in zip(frames, opacity):
            print('composing frame {}'.format(fr))
            fig_file = '{}-{}-{}.png'.format(ovl, scene, fr)
            target_fig = '{}-{}.png'.format(scene, fr)
            if opa != 1:
                os.system('{} {} -alpha set -channel a -evaluate multiply {} '
                          '+channel {}'.format(action.scene.script.convert, fig_file, opa, fig_file))
            os.system('{} -gravity SouthWest -compose atop -geometry +{}+{} '
                      '{} {} {}'.format(action.scene.script.compose, *origin_px, fig_file, target_fig, target_fig))


def data_simple_plot(action, datafile, basename):
    """
    Creates a set of simple 1D line plots
    based on a provided data file
    to e.g. accompany the display of an
    animated trajectory
    :param action: Action or SimultaneousAction, object to extract data from
    :param datafile: str, file containing the data to be plotted
    :param basename: str, base name of the image to be produced (e.g. 'overlay1')
    :return: None
    """
    import matplotlib.pyplot as plt
    font = {'size': 18}
    plt.rc('font', **font)
    plt.rc('axes', linewidth=2)
    res = action.scene.resolution
    try:
        asp_ratio = float(action.parameters['aspect_ratio'])
    except KeyError:
        asp_ratio = res[0]/res[1]
    plt.rcParams['figure.figsize'] = [4.8 * asp_ratio, 4.8]
    draw_point = True
    data = np.loadtxt(datafile, comments=['!', '#'])
    assert data.shape[1] == 2
    try:
        labels = [x.strip() for x in open(datafile) if x.strip().startswith('#')][0]
    except IndexError:
        labels = ['Time', 'Value']
    else:
        labels = labels.strip('#').strip().split(';')
    try:
        mpl_kw = [x.strip() for x in open(datafile) if x.strip().startswith('!')][0]
    except IndexError:
        mpl_kw = {}
    else:
        mpl_kw = {x.split('=')[0]: x.split('=')[1] for x in mpl_kw.strip('!').strip().split()}
        for kw in mpl_kw.keys():
            try:
                mpl_kw[kw] = eval(mpl_kw[kw])
            except NameError:
                pass
    if 'xlim' not in mpl_kw.keys():
        xmin, xmax = np.min(data[:, 0]), np.max(data[:, 0])
    else:
        xmin, xmax = mpl_kw['xlim']
    if 'ylim' not in mpl_kw.keys():
        ymin, ymax = np.min(data[:, 1]), np.max(data[:, 1])
    else:
        ymin, ymax = mpl_kw['ylim']
    try:
        animation_frames = [int(x) for x in action.overlays[basename]['dataframes'].split(':')]
        arr = np.linspace(animation_frames[0], animation_frames[1], action.framenum).astype(int)
    except KeyError:
        try:
            animation_frames = [int(x) for x in action.parameters['frames'].split(':')]
            arr = np.linspace(animation_frames[0], animation_frames[1], action.framenum).astype(int)
        except (KeyError, AttributeError):
            draw_point = False
    for fr in range(action.initframe, action.initframe + action.framenum):
        count = fr - action.initframe
        if '2D' in action.overlays[basename].keys() and action.overlays[basename]['2D'].lower() in ['t', 'y',
                                                                                                    'true', 'yes']:
            grid_x = int(np.sqrt(len(data) * asp_ratio) / 2)
            grid_y = int(grid_x / asp_ratio)
            if 'gridsize' not in mpl_kw.keys():
                mpl_kw.update({'gridsize': (grid_x, grid_y)})
            plt.hexbin(*data.T, zorder=0, **mpl_kw)
        else:
            if 'lw' not in mpl_kw.keys() and 'linewidth' not in mpl_kw.keys():
                mpl_kw.update({'lw': 3})
            plt.plot(*data.T, zorder=0, **mpl_kw)
            plt.xlim(1.1 * xmin, 1.1 * xmax)
            plt.ylim(1.1 * ymin, 1.1 * ymax)
        if draw_point:
            plt.scatter(data[arr[count], 0], data[arr[count], 1], c='r', s=250, zorder=1)
        plt.xlabel(labels[0])
        plt.ylabel(labels[1])
        plt.subplots_adjust(left=0.22, right=0.97, top=0.97, bottom=0.18)
        plt.savefig('{}-{}-{}.png'.format(basename, action.scene.name, fr))
        plt.clf()
