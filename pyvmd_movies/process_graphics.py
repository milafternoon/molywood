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
        os.system('for i in $(ls {}-*png); do mv $i $(echo $i | sed "s/{}/{}/g"); done'.format(scene, scene,
                                                                                               script.name))
    elif layout_dirs and len(script.scenes) > 1:  # here we have multiple scenes, but should insets go earlier?
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
                    pass
                else:
                    labels_matrix[r].append(scene_name)
        # here comes the convert along the lines of:
        # convert \( c-bwr-front-scale8-frame$i.png o-bwr-front-scale8-frame$i.png b-bwr-front-scale8-frame$i.png -append \) \( c-bwr-back-scale8-frame$i.png o-bwr-back-scale8-frame$i.png b-bwr-back-scale8-frame$i.png -append \) +append frame$i.png
            
# TODO add simple composing of frames using compose and layout
# TODO implement a basic fn that just copies a specified image
# TODO think of adding insets
