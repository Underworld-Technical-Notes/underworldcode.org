# The whole-annulus movie of earth_recipe_movie

Added on Kaiju on 2026-11-17 for UWTN 2026-022, beside `earth_recipe_movie_meshfixedT_0-799_web.mp4`. Louis, to the
notes workbench: "since the annulus movie will also be in the note, this is the best orientation". No new runs. The
files already in this folder are unchanged.

| file | what | bytes | sha256 |
|---|---|---|---|
| `earth_recipe_movie_nicefixed_0-799_web.mp4` | the whole-annulus movie, steps 0-799 | 13,123,275 | f77feec7e5c8afd73b46636df88765799d50f0b7b58529ae697014c3a82efb93 |
| `movie-annulus-still-step460.png` | its frame at step 460 (1920 x 1080) | 937,928 | e9b9485881c2c01e6667999ef63a60e8bf5b48079bf3626157a5098528ae1c8f |

## v2: the files the note uses (re-rendered 17 Nov, 16:22)

Louis, 17 Nov: "Re-render is my preference." The note uses v2 only. The v1 files above stay as they were.

| file | what | bytes | sha256 |
|---|---|---|---|
| `earth_recipe_movie_nicefixed_0-799_web_v2.mp4` | the whole-annulus movie, steps 0-799, re-rendered | 13,128,649 | 250ec6cc37dfdfd06619972f8e6a230fe81434009daff2dce3328a9921b4df70 |
| `movie-annulus-still-step460_v2.png` | its frame at step 460 (1920 x 1080) | 938,668 | 8c16b1d3469e9ce1e5153af2486dcfcbe713844c100feb769ed4c127b2935e06 |

What changed from v1. Nothing else differs; the rest of this README describes both versions:
- **Exact unit conversions in the frame labels.** One time unit is 266,497 Myr (v1: 2.67e5) and one velocity unit is
  1.08819e-3 cm/yr (v1: 1.09e-3). The labels now agree with README.md: step 460 reads 515.1 Myr (v1: 516.1), and
  the run spans 3.2 to 1,102.6 Myr (v1: 3.2 to 1,104.7). The plate speeds and the velocity strip are 0.17 % lower
  than v1's. Rounded to the label's one decimal, they mostly read the same.
- **The legend at the bottom right** reads "T (blue cold, red hot)   melange layer: green   oceanic-crust line: orange
  fault: black" (v1: "crust: green").

How v2 was made:
- Frames: `launch/movies/movie_frames_v2.py`, a copy of movie_frames.py with only those three changes, style
  "nicefixed". It was run as a 32-task array, `launch/movies/nicefixed_v2_job.sh` (job 4828), into
  `movies/out/earth_recipe_movie/nicefixed_v2/`.
- Encode: `launch/movies/nicefixed_v2_encode.sh` (job 4860).
  - Full quality: libx264, yuv420p, CRF 18, 12 fps, `movies/out/earth_recipe_movie/earth_recipe_movie_nicefixed_v2_0-799.mp4`,
    24,406,313 bytes.
  - The web copy: CRF 24, `web/earth_recipe_movie_nicefixed_v2_0-799_web.mp4`.
  - The shipped file is that web copy, remuxed with its index at the front (`-c copy -movflags +faststart`, no
    re-encode).
- The still is a byte-identical copy of `nicefixed_v2/frame_00460.png`.
- Stream of `earth_recipe_movie_nicefixed_0-799_web_v2.mp4`: H.264 High, yuv420p (progressive), 1920 x 1080, SAR 1:1,
  DAR 16:9, 12 fps, 800 frames, 66.67 s, 1,574 kb/s, CRF 24, index at the front.
- Its labels at step 460: "515.1 Myr   step 460", "subducting plate 1.4 cm/yr   overriding plate 0.0 cm/yr   trench
  -20.3°", "trench rollback 2228 km 19.8°".

## Which of the two annulus movies, and why

Two whole-annulus movies were made from the run's checkpoints on 12-13 Nov. Their frames are drawn by the same
function (`launch/movies/movie_frames.py`, `frame_nice`) and differ only in the left panel:

- **"nice"** (`web/earth_recipe_movie_nice_0-799_web.mp4`, 13,430,832 bytes, not shipped). Both panels turn with the
  trench: every frame is rotated so that the trench of that step is at the top of the annulus. The annulus therefore
  turns from frame to frame, and the rollback does not show as motion.
- **"nicefixed"** (shipped). The left panel stands still in the planet's frame, with the same rotation in every frame:
  the trench's first position is at the top, and the trench moves away from it as it rolls back. The panel adds a
  "start" tick, an arc from the start to the trench, the rollback in km and degrees, and the outline of the close-up's
  window. The right panel is the same as in "nice".

The shipped one is "nicefixed". It puts the trench's starting position at the top, as the redrawn insets of
trench-mesh.png now do, and it shows the 2,228 km rollback directly.

The two panels follow different orientation rules:
- **The whole annulus (left)** never turns. The top of the panel is theta_0 = -0.449 deg: the trench of the fault
  fitted at the end of step 0 (`state_00000.json`, faults[0]["theta"] = -0.0078392 rad). The run's prescribed
  starting trench, uw_theta_trench, is 0. The trench rolls back clockwise, to the right in the frame, to -20.3 deg
  (step 460), and then returns part of the way.
- **The trench window (right) follows the trench.** Each frame is rotated so that the trench of that step is at the
  top centre of the window. The window does not stand still in the planet's frame, and it is never re-centred the way
  meshfixedT is. The trench is always at the top centre.

## What each frame shows

Each frame is 1920 x 1080 px (16 x 9 in at 120 dpi) on a white background, one frame per model step. Positions
below are the matplotlib axes, as fractions of the frame: [left, bottom, width, height].

### Left panel, [0.0, 0.06, 0.5, 0.86]: the whole annulus

- The panel is square, with equal aspect, spanning +-1.08 r_o.
- Temperature T, from the base mesh's T field: colour map RdBu_r, 0 (blue, cold) to 1 (red, hot), smooth (gouraud)
  shading.
- The isotherm T = 0.5: a grey line (0.3 grey, 0.6 pt).
- Melange markers: dark green dots (#0b5d1e, marker size 0.15). These are the driver's "crust" marker; the frame's own
  legend calls them "crust".
- The oceanic-crust line, the passive "ocrust" marker, 17.4 km under the incoming plate's surface: orange dots
  (#ff8c00, size 0.3).
- The fault: a black line (1.2 pt). It is the fault the step's solver mesh was built on, which is the fit made at the
  end of the step before.
- "start": a grey radial tick (0.55 grey, 1.5 pt) at the top, outside the surface from 1.012 to 1.05 r_o, with the
  word "start" above it (10 pt, #555555).
- The rollback arc: black, 2.0 pt, at 1.03 r_o (just outside the surface), from the start to the trench of that step.
- The close-up's window: a dark grey outline (0.25 grey, 0.8 pt). It is the right panel's square, drawn in the
  planet's frame, so it moves round with the trench.
- In the centre, two lines of 13 pt text (#333333): "trench rollback" and "<km> km   <deg>°". This is
  |theta_trench - theta_0| as km at the surface (r_o x 2900 km x radians) and in degrees.

### Right panel, [0.5475, 0.06, 0.405, 0.72]: the trench window

- The window is a square 0.8 model units across (2,320 km), centred 0.36 (1,044 km) below the trench. It runs from
  0.04 (116 km) above the surface to 0.76 (2,204 km) below it on the centre line, and is turned so the trench of that
  step is at the top centre.
- Temperature T as on the left. Isotherms T = 0.3, 0.5 and 0.7 as grey lines (0.3 grey; 0.6, 0.9 and 0.6 pt).
- Streamlines of the base mesh's velocity: black at 30 % opacity, 0.5 pt, density 1.4, arrow size 0.6, drawn on a
  160 x 160 grid inside the annulus.
- Melange markers: dark green dots (#0b5d1e, size 1.5). The oceanic-crust line: orange dots (#ff8c00, size 2.5).
  Both are drawn only inside the window.
- The fault: black, 2.0 pt.
- The surface: a black arc, 0.8 pt.
- The scale bar: 500 km, black, 3 pt, at the lower left, labelled "500 km" (11 pt).

### Velocity strip, [0.5475, 0.805, 0.405, 0.125], above the right panel

- The surface velocity along the window's surface: the tangential component, in cm/yr, positive toward +theta, which
  is to the left in the frame. It shares the window's horizontal axis, so each point sits above its surface point.
- The curve is a dark line (0.1 grey, 2.0 pt). The y axis runs from -3 to +3, with ticks at -3, 0 and 3.
- A grey zero line, and a grey dotted vertical line at the trench (the window's centre).
- A label at the top left of the strip: "surface velocity, cm/yr (positive to the left)" (11 pt, #555555).

### Header and footer text

- Top left, bold monospace, 18 pt: "<t> Myr   step <s>".
- Bottom left, monospace, 13 pt: "subducting plate <v> cm/yr   overriding plate <v> cm/yr   trench <theta>°". These
  come from the step's record (`plates`, `theta_trench`).
- Bottom right, 11 pt, #555555: "T (blue cold, red hot)   crust: green   oceanic-crust line: orange   fault: black".
  In the note's terms, "crust" here is the melange marker.

### Unit conversions in the frame labels (v1 only; v2 uses the exact ones)

The v1 frame labels use rounded conversions:
- One time unit is 2.67e5 Myr, against 266,497.
- One velocity unit is 1.09e-3 cm/yr, against 1.08819e-3.

So the movie's times read 0.19 % high and its speeds 0.17 % high against the numbers in README.md. For example, step
460 is labelled 516.1 Myr, where README.md gives 515.1 Myr. The trench angle and the rollback (km, degrees) are not
affected.

## Timing

- One frame per model step, steps 0 to 799, at 12 frames per second: 800 frames, 66.67 s.
- The model time step varies from 0.76 to 3.20 Myr (mean 1.38), so the movie is not uniform in model time. It runs
  from 3.2 to 1,102.6 Myr (labelled 3.2 to 1,104.7 Myr).

## Stream

- `earth_recipe_movie_nicefixed_0-799_web.mp4`: H.264 High, yuv420p (progressive), 1920 x 1080, SAR 1:1, DAR 16:9,
  12 fps, 66.67 s, 1,573 kb/s, CRF 24 (the x264 settings in the file).
- It is the Kaiju web copy, remuxed so that its index (moov) is at the front: `ffmpeg -i in.mp4 -c copy -movflags
  +faststart out.mp4`, via `/home/louis/+Claude/kaiju/launch/uwtn/faststart.py`. It was not re-encoded, and the stream
  is unchanged.
- Read with the container's ffmpeg 7.0.2 (`launch/uwtn/stream_info.py`).
- Source: `/home/louis/+Claude/kaiju/movies/out/earth_recipe_movie/web/earth_recipe_movie_nicefixed_0-799_web.mp4`
  (index at the end).
- The full-quality file is `/home/louis/+Claude/kaiju/movies/out/earth_recipe_movie/earth_recipe_movie_nicefixed_0-799.mp4`:
  CRF 18, 24,399,839 bytes, the same frames.
- Made with:
  - `launch/movies/movie_frames.py` style "nicefixed", rendered by `launch/movies/movie_render_job.sh` on 12-13 Nov.
    The script was last changed on 12 Nov at 23:16, before these frames were drawn.
  - `launch/movies/movie_encode_job.sh` (libx264, yuv420p, CRF 18, 12 fps).
  - `launch/movies/encode_web_copy.py` (CRF 24) for the web copy.

## The still

`movie-annulus-still-step460.png` is a byte-identical copy of the movie's own frame
`/home/louis/+Claude/kaiju/movies/out/earth_recipe_movie/nicefixed/frame_00460.png` (1920 x 1080).

- Step 460 is the furthest rollback: trench -20.3 deg, 2,228 km (19.8 deg) from the start. It is the same step as
  trench-mesh.png (c) and movie-still-step460.png.
- Its labels read "516.1 Myr   step 460" (README.md: 515.1 Myr), "subducting plate 1.4 cm/yr   overriding plate 0.0
  cm/yr   trench -20.3°" and "trench rollback 2228 km 19.8°".
