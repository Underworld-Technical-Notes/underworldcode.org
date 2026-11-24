"""The movie of the worked example in UWTN 2026-011, and its still.

The frames are the renders made as the run went, one per time step, 950 pixels
square: thermal convection in an annulus at Ra = 1e7 on the lowest viscosity,
a Frank-Kamenetskii viscosity contrast of 1e3, base mesh resolution 32, and a
metric asking for cells up to 8x finer, with the MMPDE mover redistributing the
nodes after every one of 250 steps. The run is underworld3's
scripts/stagnant_lid_adapt_loop.py, in the directory
anim_full_Ra1e7_dEta1e3_res32_R8_mode1; each frame shows the temperature with
the mesh edges drawn over it.

This script makes no new image. It crops each frame to the annulus and encodes
the frames, all of them and in order, as an H.264 MP4 that a browser plays
without a plug-in, and copies one frame out as the still that the PDF and the
site's thumbnail show.

    python encode_movie.py <run_dir>

Needs ffmpeg built with libx264.
"""
import pathlib
import subprocess
import sys

FRAMES = "frame_clean_step%04d.png"

# One time step per frame: the 250 steps play in about ten seconds, the speed
# of the GIF this movie replaces.
FRAME_RATE = 24

# The renderer's camera puts the annulus in pixels 49-900 of every 950-pixel
# frame. Keep 6 pixels of white around it; the crop does not rescale.
CROP = "crop=864:864:43:43"

# x264 quality. The mesh edges are thin, faint lines and are the point of the
# figure; above 23 they visibly soften.
CRF = 23

# Developed plumes, with the mesh drawn in onto the boundary layers and the
# plume margins: the frame the PDF has shown since the note was published.
STILL_STEP = 65

FIGURES = pathlib.Path(__file__).resolve().parent.parent

run_dir = pathlib.Path(sys.argv[1])

# ffmpeg reads a numbered sequence until the first missing number, so a gap
# would end the movie early without an error.
steps = sorted(int(path.stem[-4:]) for path in run_dir.glob("frame_clean_step*.png"))
if not steps or steps != list(range(1, len(steps) + 1)):
    sys.exit("%s does not hold an unbroken sequence of frames from step 1" % run_dir)

# yuv420p is the pixel format every browser decodes. The colour conversion
# uses BT.709 and the file says so; a browser guesses at an untagged file, and
# the colours then drift from the frames'. +faststart puts the index at the
# front of the file, so the movie starts before it has finished downloading.
subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error",
     "-framerate", str(FRAME_RATE), "-i", str(run_dir / FRAMES),
     "-vf", CROP + ",scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,"
                   "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv",
     "-c:v", "libx264", "-preset", "slow", "-crf", str(CRF),
     "-movflags", "+faststart",
     str(FIGURES / "adaptive-convection.mp4")],
    check=True)

subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error",
     "-i", str(run_dir / (FRAMES % STILL_STEP)), "-vf", CROP,
     str(FIGURES / "adaptive-convection-still.png")],
    check=True)

print("%d frames at %d per second -> %s" % (len(steps), FRAME_RATE, FIGURES / "adaptive-convection.mp4"))
print("still from step %d -> %s" % (STILL_STEP, FIGURES / "adaptive-convection-still.png"))
