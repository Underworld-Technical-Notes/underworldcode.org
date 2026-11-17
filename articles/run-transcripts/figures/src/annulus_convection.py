"""Figures and records for UWTN 2026-019, "A Transcript for Every Run".

Runs a short annulus convection model, deliberately rejects one step, replays
another and takes one step that solves everything twice, then renders the
transcript the run leaves. Run it from this directory:

    python annulus_convection.py

The figures go to the note's figures/ folder:

    run-transcript.svg/pdf   time down the page, dt across it
    run-chart.svg/pdf        the run as a chart
    run-chart-key.svg/pdf    the chart with the key on the page

and the run's own records stay here, beside this script:

    transcript.log           the text transcript the run wrote
    transcript.jsonl         the machine-readable transcript
    chart.txt                the chart, in text
    key.md                   what each part solved, as implemented
    replay_check.txt         the replayed step against its first take

The run directory itself goes under ./transcripts/, which is not kept.
Everything here is Underworld3's own machinery: the transcript is written
without being asked, and the figures are rendered from it afterwards.
"""

import os

import numpy as np
import sympy

import underworld3 as uw

params = uw.Params(
    uw_cell_size=0.1,       # mesh resolution, as a fraction of the outer radius
    uw_n_steps=14,          # timesteps before the demonstrations
    uw_dt_fraction=0.5,     # accuracy factor on estimate_dt()
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.dirname(HERE)          # the note's figures/ folder

# --- the model, in the units it is quoted in -------------------------------
SHELL_THICKNESS = uw.quantity(2200, "km")
KAPPA = uw.quantity(1e-6, "m**2/s")
ETA = uw.quantity(1e22, "Pa*s")
DELTA_T = uw.quantity(2500, "K")
RHO0 = uw.quantity(3300, "kg/m**3")
ALPHA = uw.quantity(3e-5, "1/K")
GRAVITY = uw.quantity(9.81, "m/s**2")

R_OUTER, R_INNER = 1.0, 0.55

uw.reset_default_model()
model = uw.get_default_model()
model.set_reference_quantities(
    shell_thickness=SHELL_THICKNESS,
    thermal_diffusivity=KAPPA,
    mantle_viscosity=ETA,
    temperature_contrast=DELTA_T,
)
# The transcript is on by default and lands in a stamped run directory; this
# script copies the record out beside itself afterwards.
os.environ.setdefault("UW_TRANSCRIPT", os.path.join(HERE, "transcripts"))

mesh = uw.meshing.Annulus(
    radiusInner=R_INNER, radiusOuter=R_OUTER,
    cellSize=params.uw_cell_size, degree=1, qdegree=3,
)
v = uw.discretisation.MeshVariable("v", mesh, mesh.dim, degree=2)
p = uw.discretisation.MeshVariable("p", mesh, 1, degree=1)
T = uw.discretisation.MeshVariable("T", mesh, 1, degree=3)

stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
stokes.constitutive_model.Parameters.shear_viscosity_0 = ETA
stokes.tolerance = 1.0e-8
stokes.petsc_options.delValue("ksp_monitor")
# Rotated free-slip: exact on a circle, where a penalty condition leaks.
stokes.add_rotated_freeslip_bc(0.0, "Upper")
stokes.add_rotated_freeslip_bc(0.0, "Lower")

radius = sympy.sqrt(mesh.X.dot(mesh.X))
# The buoyancy as the force it is; the Rayleigh number falls out of the
# non-dimensionalisation rather than being typed in.
# Name the coefficient rather than letting the product collapse into an
# anonymous number. Python multiplies the three quantities at assignment, so
# without this the run records a bare -0.97119 kg/(K m^2 s^2) and nothing
# saying where it came from.
BUOYANCY = uw.expression(
    r"\rho_0 \alpha g",
    RHO0 * ALPHA * GRAVITY,
    "buoyancy coefficient: reference density x thermal expansivity x gravity",
)
stokes.bodyforce = -BUOYANCY * T.sym[0] * mesh.X / radius

adv = uw.systems.AdvDiffusion(mesh, u_Field=T, V_fn=v.sym)
adv.constitutive_model = uw.constitutive_models.DiffusionModel
adv.constitutive_model.Parameters.diffusivity = KAPPA
adv.add_dirichlet_bc(1.0, "Lower")
adv.add_dirichlet_bc(0.0, "Upper")
adv.tolerance = 1.0e-8
adv.petsc_options.delValue("ksp_monitor")

# Conductive profile with a mode-5 perturbation.
scale = float(model.get_fundamental_scales()["length"].to("m").magnitude)
X = np.asarray(T.coords)[:, :2] / scale
r = np.sqrt((X**2).sum(axis=1))
th = np.arctan2(X[:, 1], X[:, 0])
shell = (r - R_INNER) / (R_OUTER - R_INNER)
T.array[:, 0, 0] = (1.0 - shell) + 0.1 * np.sin(5.0 * th) * np.sin(np.pi * shell)
adv.Unknowns.DuDt.initialise_history()
stokes.solve(zero_init_guess=True)

v_rms_fn = sympy.sqrt(v.sym.dot(v.sym))
area = float(uw.maths.Integral(mesh, sympy.sympify(1.0)).evaluate())


def v_rms():
    return float(uw.maths.Integral(mesh, v_rms_fn).evaluate()) / area


# --- the run ---------------------------------------------------------------
model.tracker.time = uw.quantity(0.0, "Myr")
model.tracker.step = 0
model.tracker.v_rms = v_rms()
model.record_every = 1
model.record_limit = int(params.uw_n_steps) + 4

for _ in range(int(params.uw_n_steps)):
    dt = params.uw_dt_fraction * adv.estimate_dt()
    with model.step(dt, label="convect"):
        adv.solve(timestep=dt, zero_init_guess=False)
        stokes.solve(zero_init_guess=False)
        model.tracker.v_rms = v_rms()

# The temperature at the end of the last ordinary step, to compare with the
# same step taken again after the rewind below.
T_first_take = np.array(T.array[:, 0, 0], copy=True)


class StepRejected(Exception):
    """Raised inside a step block to abandon it."""


# A step fifty times too large, rejected on a diagnostic after it ran.
snapshot = model.save_state()
reckless = 50.0 * params.uw_dt_fraction * adv.estimate_dt()
try:
    with model.step(reckless, label="too big"):
        adv.solve(timestep=reckless, zero_init_guess=False)
        stokes.solve(zero_init_guess=False)
        if v_rms() > 4.0 * model.tracker.v_rms:
            raise StepRejected("v_rms jumped")
except StepRejected:
    model.load_state(snapshot)

# Back one step, and take it again: a replay reproduces it exactly.
target = model.rewind()
with model.step(target.dt, label="replay"):
    adv.solve(timestep=target.dt, zero_init_guess=False)
    stokes.solve(zero_init_guess=False)
    model.tracker.v_rms = v_rms()

# Is the replay the step it replaced? Written beside the records.
dT = float(np.max(np.abs(np.asarray(T.array[:, 0, 0]) - T_first_take)))
with open(os.path.join(HERE, "replay_check.txt"), "w", encoding="utf-8") as handle:
    handle.write(f"max |T(replay) - T(first take)| after step {target.index}: {dT:.3e}\n")
uw.pprint(f"replay: max |dT| = {dT:.3e}", clean_display=False)

# One step with the transport solved twice — a predictor/corrector written
# without noticing that the history advances on every solve.
dt = params.uw_dt_fraction * adv.estimate_dt()
with model.step(dt, label="taken twice"):
    adv.solve(timestep=dt, zero_init_guess=False)
    stokes.solve(zero_init_guess=False)
    adv.solve(timestep=dt, zero_init_guess=False)
    stokes.solve(zero_init_guess=False)

# --- the renderings --------------------------------------------------------
# From the RECORD on disk rather than from the live model: the in-memory
# transcript holds what the run can still undo, so the abandoned step and the
# backtracks — the rows worth looking at — are only in the file.
import shutil

# Close the record first, so it ends with the run's terminator; otherwise the
# renderers read it as a run still going, or one that was interrupted.
run_dir = os.path.dirname(model.transcript_file)
model.announce_transcript()
record = os.path.join(run_dir, "transcript.jsonl")
for name in ("transcript.log", "transcript.jsonl"):
    shutil.copyfile(os.path.join(run_dir, name), os.path.join(HERE, name))

title = "Annulus convection — run transcript"
uw.transcript_diagram(record, out=os.path.join(FIGURES, "run-transcript.svg"), title=title)
uw.transcript_diagram(record, out=os.path.join(FIGURES, "run-transcript.pdf"), title=title)

chart_title = "Annulus convection — transcript"
uw.transcript_figure(record, out=os.path.join(FIGURES, "run-chart.svg"), title=chart_title)
uw.transcript_figure(record, out=os.path.join(FIGURES, "run-chart.pdf"), title=chart_title)

chart = uw.transcript_table(record)
with open(os.path.join(HERE, "chart.txt"), "w", encoding="utf-8") as handle:
    handle.write(chart + "\n")

# The key: what each part solved, as implemented — Markdown with LaTeX for the
# post, and the chart with the key on the page.
uw.transcript_key(record, out=os.path.join(HERE, "key.md"))
uw.transcript_figure(record, out=os.path.join(FIGURES, "run-chart-key.svg"), title=chart_title, key=True)
uw.transcript_figure(record, out=os.path.join(FIGURES, "run-chart-key.pdf"), title=chart_title, key=True)

uw.pprint(chart, clean_display=False)
uw.pprint(f"figures written to {FIGURES}, records to {HERE}", clean_display=False)
