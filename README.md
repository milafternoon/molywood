### What does `pyvmd` do?

`pyvmd` automatizes the most tedious steps in generation of molecular
movies, i.e. scripting in TCL, rendering, generating overlays and
combining frames, as well as merging frames into the final movie.

We try to simplify the movie making syntax to supersede the existing
TCL UserAni library, and add extended functionalities such as
animating trajectory data with matplotlib, adding insets or
making multi-panel movies.

The basic idea behind the functionalities of `pyvmd`, as well as the
general structure of the code, are illustrated in `script_structure.svg`.

### Requirements

The internal workflow is as follows: generate the TCL script > run VMD
to render frames > post-process using imagemagick > combine frames
using ffmpeg. Therefore, full automation requires that `python3`, `VMD`,
`imagemagick` and `ffmpeg` be installed on the system you're using
to produce the movie. The good news is that it can be done externally,
e.g. on a remote workstation, once you set up the visualization state
locally.

Note:
+ It is recommended to use `python3` from the Anaconda distribution
as it contains `numpy` and `matplotlib` as a pre-installed package.
+ `VMD` can be obtained at `https://www.ks.uiuc.edu/Research/vmd/`.
+ `imagemagick` is installed by default on most Linux distributions;
run e.g. `convert` to make sure it is available on your machine.
+ `ffmpeg` can be installed e.g. from the Ubuntu repository by
typing `sudo apt-get install ffmpeg`.

### Usage

To use `pyvmd`, one needs:

1. a visualization state generated by VMD (user should define the
preferred representations as well as set the camera angle, and then
go to File > Save Visualization State);
1. a 'movie script', i.e. a textfile containing directives, including
a reference to the VMD visualization state (see examples and the
explanations below).

Sample movie scripts are available in the `examples` directory.

`pyvmd` can be run from the console as:

 `python pyvmd.py examples/simple_movie/script.txt`

### List of available action keywords and parameters:

+ animate (frames=init_frame:final_frame, t=...s, \[smooth=...\])
+ rotate (axis=x/y/z, angle=..., t=...s, \[sigmoid=**t**/f/sls\])
+ zoom_in/zoom_out (scale=..., t=...s, \[sigmoid=**t**/f/sls\])
+ make_transparent/make_opaque (material=..., t=...s,  \[sigmoid=**t**/f/sls\])
+ center_view (selection='...')
+ show_figure (t=...s, \[figure_index=..., datafile=...\])
+ do_nothing (t=...s)
+ add_overlay (t=...s, \[figure_index=..., datafile=..., origin=0,0
relative_size=1 frames=init_frame:final_frame\])
+ add_label(label=..., atom_index=..., \[label_color=...\])
+ remove_label(id=...)
+ highlight (selection=..., t=..., \[color=..., mode=u/d/ud\])

(Square brackets denote optional parameters. Values in bold font
indicate defaults when parameters are optional)

### List of available global keywords and parameters:

+ global (\[fps=20, draft=t/**f**, keepframes=t/**f**, name=**movie**\])
+ layout (\[rows=**1**, columns=**1**\])
+ figure (\[files=figure1.png,figure2.png,...\])
+ scene_identifier (\[visualization=..., structure=..., trajectory=...,
position=**0,0**, resolution=**1000,1000**\])

(instead of scene_identifier, you should put the actual identifier
of the scene in question, e.g. `scene_1` in the example below)

### Notes on input formatting:

+ A hash `#` marks the *beginning* of a scene input section, and should
be followed by a single-word scene identifier,  e.g. `# scene_1`
+ Single actions have to be specified on a single line, starting with
a keyword and followed by any number of whitespace-separated
 `parameter=value` pairs (note: no spaces encircling the `=` sign)
+ Multiple actions (e.g. rotation and zoom_in) can be performed
simultaneously if they are encircled in curly brackets and separated
with semicolons, e.g. `{rotate t=1s angle=50; zoom_in t=1s scale=2}`;
they can also be split over several lines for clarity. Note that here,
the second `t=1s` parameter specification will overwrite the first, so
that time might as well only be specified once
+ A line starting with a `$` sign specifies global keywords, e.g.
`$ global fps=20`
+ true/false values can be specified as `true/false`, `yes/no` or in
shorthand notation (`t/f`, `y/n`)

### Notes on extra graphics features

+ External figures (e.g. ending credits) can be featured in the movies.
The external graphics file has to be listed in the global `figure`
directive (e.g. `$ figure files=graph.png`), and its index in the list
has to be specified as a parameter in `show_figure` action (e.g.
`show_figure t=4s figure_index=0`). In this way, multiple graphics files
can be accessed independently by any `scene` object.
+ Note that it is *the user* who is responsible for setting correct
resolutions for the individual scenes. By default, each scene is
rendered in a resolution of 1000x1000 (200x200 in the `draft` mode);
if e.g. a source figure isn't exactly rectangular, it will be scaled to
fit in the rectangle, but its aspect ratio (shape) will not be affected.
+ Insets and overlays will be added soon
+ Dynamic figure generation through matplotlib will be added soon

#### Notes on individual actions

+ `animate` runs the trajectory from `init_frame` to `final_frame`,
adjusting the playback speed to the time specified with `t`;
`smooth=X` sets the smoothing of all VMD representations to X
+ `rotate` rotates the scene by `angle` degrees about `axis` in time `t`.
`sigmoid=t` gives a smooth transition, while `sigmoid=f` gives a
constant-velocity one; optionally, `sigmoid=sls` performs a smooth-
linear-smooth transition (preferable for e.g. multiple full rotations)
+ `zoom_in`/`zoom_out` scales the view by a factor of `scale` in time `t`.
`sigmoid` works like for `rotation`.
+ `make_transparent`/`make_opaque` change the opacity of a selected
`material` to make it fully transparent or fully opaque in time `t`.
`sigmoid` works like for `rotation`.
+ `center_view` is an instantaneous action that sets the geometric
center of `selection` (VMD-compatible) as the new camera center to
which zoom will converge; useful when zooming onto e.g. a reaction center
+ `show_figure` just shows an image instead of a VMD render during time
`t`; the image is specified using `figure_index` in conjunction with
 the globally defined list of figure paths, `$ figure files=...`
 + `do_nothing` renders the VMD scene for time `t` without doing
 anything else
 + `add_overlay` allows to add an inset to the scene, with the position
 specified through `origin` (0,0  corresponds to the bottom left corner,
 as in a regular Cartesian coordinate system), and size through
 `relative_size` (1 means fit into the whole  scene, 0.1 means fit into
 a rectangle 10% of the scene size).
    + The content of the overlay can be  an external figure (specified
    through `figure_index`), or an on-the-fly  generated matplotlib line
    plot (based on a data file speficied with the `datafile` parameter).
    + If `frames` are simultaneously specified  e.g. in `animate` or
    in `add_overlay` itself, a dot will follow the values on the plot.
    + If the  data file starts with a single line formatted as
    `# x axis label; y axis label`, `x axis label` and `y axis label`
    will be used to label the corresponding axes of the plot.
    + Mulitple overlays can be added to a scene simultaneously; adding
    many `add_overlay` commands separated by semicolons and encircled
    in curly brackets works just as any other multiple action (see
    `Notes on input formatting` above).