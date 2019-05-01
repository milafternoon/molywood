### What does `pyvmd` do?

`pyvmd` automatizes the most tedious steps in generation of molecular
movies, i.e. scripting in TCL, rendering, generating overlays and
combining frames, as well as merging frames into the final movie.

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
as it contains `numpy` as a pre-installed package.
+ `VMD` can be obtained at `https://www.ks.uiuc.edu/Research/vmd/`.
+ `imagemagick` is installed by default on most Linux distributions.
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

+ animate (frames=init_frame:final_frame\[:stride\], smoothing)
+ rotate (axis=x/y/z, angle=..., t=...s, \[sigmoid=**t**/f/sls\])
+ zoom_in/zoom_out (scale=..., t=...s, \[sigmoid=**t**/f/sls\])
+ make_transparent/make_opaque (material=..., t=...s,  \[sigmoid=**t**/f/sls\])
+ center_view (selection='...')

(Values in bold font indicate defaults when parameters are optional)

### List of available global keywords and parameters:

+ global (fps=..., draft=t/**f**, keepframes=t/**f**)
+ layout (not implemented yet)
+ scene_identifier (visualization=...)


### Notes on input formatting:

+ A hash (\#) marks the beginning of a scene, and should contain
a single-word scene identifier,  e.g. `# scene_1`
+ Single actions have to be specified on a single line, starting with
a keyword and followed by `parameter=value` pairs (no spaces encircling
the `=` sign)
+ Multiple actions (e.g. rotation and zoom_in) can be performed
simultaneously if they are encircled in curly brackets and separated
with semicolons, e.g. `{rotate t=1s angle=50; zoom_in t=1s scale=2}`;
they can also be split over several lines for clarity
+ A line starting with a `$` sign specifies global keywords, e.g.
`$ global fps=20`
+ true/false values can be specified as `true/false`, `yes/no` or in
shorthand notation (`t/f`, `y/n`)