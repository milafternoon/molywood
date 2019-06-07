### What does `pyvmd` do?

PyVMD is there to make cool molecular movies for you.

Specifically, `pyvmd` automatizes the most tedious steps in generation of these
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

If any dependencies are missing on your machine (or on the workstation
you don't have root access to), you can also automatically
batch-download them by creating a local `conda` environment.
To this end, run the following commands from your console:

`conda env create -f environment.yml`

`source activate pyvmd`

and then run `source deactivate pyvmd` once you're done.

### Usage

Sample movie scripts are available in the `examples` directory: try
them first to see how the library works.

`pyvmd` can be run from the console (e.g. in the `examples/simple_movie`
directory) as:

 `python ../../pyvmd.py script.txt`

In general, to run `pyvmd` the following files are needed:

1. either (a) a visualization state generated by VMD, or (b) a structure
file; (a) is the preferred way - user may define the representations
as well as set the camera angle as desired, and then go to File > Save
Visualization State); in option (b), a default representation is used,
and a compatible trajectory file can be provided.
1. a 'movie script', i.e. a simple text file containing directives,
including a reference to the VMD visualization state (see examples and
the explanations below).

### List of available action keywords and parameters:

###### Instantaneous actions:

+ center_view (selection='...')
+ fit_trajectory (selection='...')
+ add_label (label='...' atom_index=... \[label_color=...
text_size=... alias=...\])
+ add_distance (selection1='...' selection2='...' \[label_color=...
text_size=... alias=...\])
+ remove_label (\[alias=... remove_all=**n**\])
+ remove_distance (\[alias=... remove_all=**n**\])

###### Finite-time actions:

+ animate (frames=init_frame:final_frame t=...s \[smooth=...\])
+ rotate (axis=x/y/z angle=... t=...s \[sigmoid=**t**/f/sls\])
+ zoom_in/zoom_out (scale=... t=...s \[sigmoid=**t**/f/sls\])
+ make_transparent/make_opaque (material=... t=...s  \[sigmoid=**t**/f/sls\])
+ show_figure (t=...s \[figure=... datafile=... dataframes=init_frame:final_frame\])
+ do_nothing (t=...s)
+ add_overlay (t=...s \[figure=... datafile=... origin=0,0 text=...
relative_size=1 dataframes=init_frame:final_frame aspect_ratio=... 2D=t/**f**\]
textsize=\[24\] sigmoid=\[t/**f**\])
+ highlight (selection=... t=... \[color=**red** mode=u/d/**ud**
style=**newcartoon**/licorice/surf/quicksurf alias=...\])


(Note that **only** finite-time actions can be combined using curly
brackets. Also, all finite-time require the t=...s keyword. Above,
square brackets denote optional parameters. Values in bold font
indicate defaults when parameters are optional.)

### List of available global keywords and parameters:

+ global (\[fps=20  draft=t/**f** keepframes=t/**f** name=**movie**\])
+ layout (\[rows=**1** columns=**1**\])
+ figure (\[files=figure1.png,figure2.png,...\])
+ scene_identifier (\[visualization=... structure=... trajectory=...
position=**0,0** resolution=**1000,1000**\])

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
they can also be split over several lines for convenience. Note that here,
the second `t=1s` parameter specification will overwrite the first, so
that time might as well only be specified once
+ A line starting with a `$` sign specifies global keywords, e.g.
`$ global fps=20` (see available global keywords above)
+ true/false values can be specified as `true/false`, `yes/no` or in
shorthand notation (`t/f`, `y/n`)

### Notes on extra graphics features

+ External figures (e.g. ending credits) can be featured in the movies.
The external graphics file has to be specified as a parameter in the
`show_figure` action (e.g. `show_figure t=4s figure=picture.png`).
+ Note that it is *the user* who is responsible for setting correct
resolutions for the individual scenes. By default, each scene is
rendered in a resolution of 1000x1000; if e.g. a source figure isn't
exactly rectangular, it will be scaled to
fit in the rectangle, but its aspect ratio (shape) will not be affected.
+ Multiple overlays (insets) can be added to each scene. The inset can
either be a static image (specified with the `figure` keyword in
`add_overlay`), or a dynamically generated matplotlib plot (by
specifying the `datafile` parameter in `add_overlay`). Currently 1D
line plots (generated with plt.plot) and 2D histograms (generated with
plt.hexbin) are supported; the former is default if a `datafile` is
supplied, and the latter can be requested with `2D=t`. The relative
coordinates of the origin (from `0,0` to denote bottom left to `1,1` to
denote upper right corner), inset size relative to the background figure,
and the aspect ratio (X to Y size) can all be specified independently to
position the inset/overlay as desired.
+ When generating figures with matplotlib, axis labels can be specified
directly in the datafile by adding a `# x label; y label` (spaces and
latex-compatible math notation are allowed). In addition, multiple
matplotlib-compatible `keyword=value` pairs can be enumerated after the
`!` character to modify plt.plot/plt.hexbin defaults, e.g.
`! bins='log' cmap='seismic'`, or plot properties, e.g.
`! xlim=-1,2 ylim=0,500` (no spaces around the `=` sign).

### Notes on individual actions

###### Instantaneous actions:

+ `center_view` is an instantaneous action that sets the geometric
center of `selection` (VMD-compatible) as the new camera center to
which zoom will converge; useful when zooming onto e.g. a reaction center
+ `fit_trajectory` uses RMSD-based fitting to instantaneously align a
 trajectory to the reference (first) frame, using the `selection` to
 calculate the optimal alignment
+ `add_label` instantaneously adds a text label anchored to an atom
 specified with `atom_index`, with the labeling text specified through
 the `label` parameter; if desired, text size  and color can be
 specified with `label_color` and `text_size`.
+ `add_distance` instantaneously adds a distance label between
 the centers of geometry of two VMD-compatible selections, specified
 with `selection1` and `selection2`; as above, text size  and color can
 be specified with `label_color` and `text_size`.
+ `remove_label` instantaneously deletes a label specified through
 `alias=...` identical to an `alias` previously specified in `add_label`;
 alternatively, `all=t` removes all existing labels. Note that `alias=...`
 and `all=t` should be mutually exclusive: one either deletes a specific
 label or all of them.
+ `remove_distance` works identically to `remove_label`, but affects
labels added using `add_distance` instead of `add_label`.

###### Finite-time actions:

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
    through `figure_index`), an on-the-fly  generated matplotlib line
    plot (based on a data file speficied with the `datafile` parameter)
    or plain text.
    + If `datafile=...` is specified, a dot will dynamically follow the
     values on the plot. By default, the script will try to use `frames`
     from the accompanying `animate` action to select datapoint indices
     from the `datafile`. To independently select datapoint indices for
     the 1D plot (e.g. when the `datafile` has much more entries than
     the trajectory used in `animate`, one can supply `datafile=...`
     with `dataframes=...` - it will take precendence over `animate`'s
     `frames`.
    + If the  data file starts with a single line formatted as
    `# x axis label; y axis label`, `x axis label` and `y axis label`
    will be used to label the corresponding axes of the plot.
    + If `text="sample text` is used, the text will be displayed at
    a position specified with `origin`.
    + Mulitple overlays can be added to a scene simultaneously; adding
    many `add_overlay` commands separated by semicolons and encircled
    in curly brackets works just as any other multiple action (see
    `Notes on input formatting` above).
 + `highlight` creates a new representation to highlight a subset of
 the system selected by specifying the `selection` parameter. Color can
 be chosen with `color`, using either simple color names (black, red,
 blue, orange, yellow, green and white), VMD-compatible ColorIDs (0-32)
 or a coloring scheme keyword (name, type, element, structure etc.).
 Similarly, `style` can be set to newcartoon, licorice, surf or
 quicksurf (non-case sensitive).
    + By default, highlight appears (fades in from transparency) and
    disappears smoothly over the course of the action. If you want your
    highlight to stay visible, use `mode=u` (up) to make it appear only.
    + To turn off a previously created highlight (possibly after several
    intervening actions), use `mode=d` (down) along with
    `alias=...` identical to a previously set `alias` of the highlight
    to be turned off; you only need to provide an alias to a highlight
    if you first turn it on and want to turn off later.