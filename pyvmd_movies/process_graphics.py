import os


def postprocessor(script):
    try:
        layout_dirs = script.directives['layout']
    except KeyError:
        layout_dirs = None
    try:
        inset_dirs = script.directives['inset']
    except KeyError:
        inset_dirs = None
        
    if len(script.scenes) == 1 and not layout_dirs:  # simplest case: one scene, no add-ons
        scene = script.scenes[0].name
        for fr in range(script.scenes[0].total_frames):
            os.system('mv {}-fr{}.png {}-{}.png'.format(scene, fr, script.name, fr))
            
    elif layout_dirs and len(script.scenes) > 1:  # here we have multiple scenes, but should insets go earlier?
        # TODO if one has less frames than the other, copy last frame to make counts equal
        # for now we just assume frame counts are equal:
        assert all([sc.total_frames == script.scenes[0].total_frames for sc in script.scenes])
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
                convert_command += labels_matrix[r][c] + '-fr{}.png '
            convert_command += ' +append \) '
        convert_command += ' -append '
        for fr in range(script.scenes[0].total_frames):
            os.system('convert ' + convert_command.format(fr) + '{}-{}.png'.format(script.name, fr))
            

def gen_fig(action):
    """
    If the action is just to show a figure
    (e.g. ending credits), then we copy the
    source file with a proper name
    :param action: Action, object to extract info from
    :return: None
    """
    if action.action_type == 'show_figure':
        for fr in range(action.initframe, action.initframe + action.framenum):
            os.system('convert {} {}-{}.png'.format(action.scene.figure, action.scene.name, fr))
            # TODO think about the resolution (sung along to Beatles)

# TODO think of adding insets; need to be done before postprocessor() is run

