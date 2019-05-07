import os


def postprocessor(script):
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
        labels_matrix = [[] for r in range(nrows)]
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
                convert_command += labels_matrix[r][c] + '-{}.png '
            convert_command += ' +append \) '
        convert_command += ' -append '
        for fr in range(script.scenes[0].total_frames):
            frames = [fr] * (nrows*ncols)
            print('fff', frames, convert_command)
            os.system('convert ' + convert_command.format(*frames) + '{}-{}.png'.format(script.name, fr))
            

def gen_fig(action):
    """
    If the action is just to show a figure
    (e.g. ending credits), then we copy the
    source file with a proper name
    :param action: Action, object to extract info from
    :return: None
    """
    if 'show_figure' in action.action_type:
        fig_file = action.scene.script.figures[int(action.parameters['figure_index'])]
        for fr in range(action.initframe, action.initframe + action.framenum):
            os.system('convert {} -resize {}x{} {}-{}.png'.format(fig_file, *action.scene.resolution,
                                                                  action.scene.name, fr))
    if 'add_overlay' in action.action_type:
        if 'figure_index' in list(action.parameters.keys()):
            fig_file = action.scene.script.figures[int(action.parameters['figure_index'])]
            frames = range(action.initframe, action.initframe + action.framenum)
            scene = action.scene.name
            res = action.scene.resolution
            scaling = float(action.parameters['relative_size'])
            overlay_res = [scaling * r for r in res]
            for fr in frames:
                os.system('convert {} -resize {}x{} overlay-{}-{}.png'.format(fig_file, *overlay_res, scene, fr))
                

def equalize_frames(script):
    nframes = [sc.total_frames for sc in script.scenes]
    names = [sc.name for sc in script.scenes]
    highest = max(nframes)
    for n, nf in enumerate(nframes):
        if nf < highest:
            for i in range(nf, highest):
                os.system('cp {}-{}.png {}-{}.png'.format(names[n], nf-1, names[n], i))


def compose_overlay(action):
    """
    Scales and composes the overlay provided
    that the picture ('overlay-frame_name.png')
    was already produced
    :param action: Action or SimultaneousAction, object to extract data from
    :return: None
    """
    frames = range(action.initframe, action.initframe + action.framenum)
    scene = action.scene.name
    res = action.scene.resolution
    origin_frac = [float(x) for x in action.parameters['origin'].split(',')]
    origin_px = [int(r*o) for r, o in zip(res, origin_frac)]
    for fr in frames:
        print('composing frame {}'.format(fr))
        fig_file = 'overlay-{}-{}.png'.format(scene, fr)  # TODO enable more than one overlay?
        target_fig = '{}-{}.png'.format(scene, fr)
        os.system('composite -gravity SouthWest -compose atop -geometry +{}+{} {} {} {}'.format(*origin_px, fig_file,
                                                                                                target_fig, target_fig))
