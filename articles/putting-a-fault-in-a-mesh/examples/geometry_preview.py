"""Geometry preview for the S-fault 2-D rig — adjust the dials by eye.

No solving, no meshing: the traces, their ±w/2 band rails (exactly what
the curved 2-D ladder will build), the viscosity layer, and the drive.

    ../run geometry_preview.py      →  s_fault_geometry.png
"""
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
OUT = "/Users/lmoresi/+Simulations/s_fault_rig"

# ----------------------------------------------------------------- dials
THETA = np.deg2rad(40.0)     # strike of the diagonal baseline
C = np.array([0.5, 0.5])     # baseline centre
A = 0.05                     # S half-step (lateral offset amplitude)
LAM = 0.10                   # bend length scale (tanh)
S_MAIN = (-0.42, 0.42)       # main-trace arc range (blind tips)
S_BRANCH = (0.06, 0.42)      # branch: through-line at t = -A
W = 0.03                     # band width — the COARSE case (fine: 0.01)
S_F = 0.01                   # rung spacing — the COARSE case (fine: 0.005)
# Protocol: every finite-w result runs at BOTH resolutions and is
# compared to the THIN-FAULT (split-node) reference on the same traces.
# Rheology: STRONG everywhere on the +t side (above/left) of the fault
# LINE — the trace continued to the box edges (the fault is a terrane
# boundary; only the modelled segment slips).
# -----------------------------------------------------------------------

es = np.array([np.cos(THETA), np.sin(THETA)])
et = np.array([-np.sin(THETA), np.cos(THETA)])


def main_trace(s):
    s = np.atleast_1d(s)
    return C + s[:, None] * es + (A * np.tanh(s / LAM))[:, None] * et


def branch_trace(s):
    s = np.atleast_1d(s)
    return C + s[:, None] * es - A * et


def rails(P, w):
    """±w/2 offsets along per-vertex mitred normals — the ladder rails."""
    t = np.gradient(P, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.column_stack([-t[:, 1], t[:, 0]])
    return P + 0.5 * w * n, P - 0.5 * w * n


def as_line(P, z=0.0):
    return pv.lines_from_points(
        np.column_stack([P, np.full(len(P), z)]))


def band_poly(Pp, Pm, z=0.0):
    """Quad-strip fill (a single non-convex polygon mis-triangulates)."""
    n = len(Pp)
    pts = np.column_stack([np.vstack([Pp, Pm]), np.full(2 * n, z)])
    faces = []
    for i in range(n - 1):
        faces += [4, i, i + 1, n + i + 1, n + i]
    return pv.PolyData(pts, faces=np.asarray(faces))


sm = np.linspace(*S_MAIN, 200)
sb = np.linspace(*S_BRANCH, 120)
Pm = main_trace(sm)
Pb = branch_trace(sb)
Rp, Rm = rails(Pm, W)
Bp, Bm = rails(Pb, W)

# closest approach branch-tip -> main trace (the stop-short gap)
tip = Pb[0]
gap = float(np.min(np.linalg.norm(Pm - tip, axis=1)))
n_below = (S_MAIN[1] - S_MAIN[0]) / S_F
print(f"main arc ~{S_MAIN[1] - S_MAIN[0]:.2f} ({n_below:.0f} rungs at "
      f"s_f={S_F}), step 2A={2 * A}, gap(tip->main)={gap:.3f} "
      f"(={gap / S_F:.1f} elements)")

def box_exit(p, d):
    """Where the ray p + t·d leaves the unit box (t > 0)."""
    ts = []
    for k, lim in ((0, 0.0), (0, 1.0), (1, 0.0), (1, 1.0)):
        if abs(d[k]) > 1e-12:
            t = (lim - p[k]) / d[k]
            q = p + t * d
            if t > 1e-9 and -1e-9 <= q[1 - k] <= 1 + 1e-9:
                ts.append(t)
    return p + min(ts) * d


def dashed(p0, p1, z, dash=0.018):
    segs, L = [], float(np.linalg.norm(p1 - p0))
    d = (p1 - p0) / L
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        segs.append((p0 + s * d, p0 + e * d))
        s = e + 0.6 * dash
    pts, lines = [], []
    for a, b in segs:
        lines += [2, len(pts), len(pts) + 1]
        pts += [[a[0], a[1], z], [b[0], b[1], z]]
    out = pv.PolyData(np.asarray(pts))
    out.lines = np.asarray(lines)
    return out


pl = pv.Plotter(off_screen=True, window_size=(1200, 1200))
pl.set_background("white")

# STRONG REGION: +t side of the fault line (trace + tangent
# continuations; tanh is saturated at the tips so line == asymptote).
# Rendered from the same implicit rule the rig will paint with:
# t_coord > A tanh(s_coord/λ).
NG = 500
gx, gy = np.meshgrid(np.linspace(0, 1, NG), np.linspace(0, 1, NG),
                     indexing="xy")
rel = np.stack([gx - C[0], gy - C[1]], axis=-1)
s_co = rel @ es
t_co = rel @ et
strong = (t_co > A * np.tanh(s_co / LAM)).astype(float)
img = pv.ImageData(dimensions=(NG, NG, 1),
                   spacing=(1 / (NG - 1), 1 / (NG - 1), 1.0),
                   origin=(0.0, 0.0, -0.004))
img.point_data["strong"] = strong.ravel(order="C")
pl.add_mesh(img.threshold(0.5, scalars="strong"), color="#efe3cf",
            lighting=False)

# box outline
box = pv.PolyData(np.array([[0, 0, 0.004], [1, 0, 0.004],
                            [1, 1, 0.004], [0, 1, 0.004]]))
box.lines = np.array([5, 0, 1, 2, 3, 0])
pl.add_mesh(box, color="black", line_width=2, lighting=False)

# bands (what the curved ladder will build), rails, traces
for Pp_, Pm_, col in ((Rp, Rm, "lightsteelblue"), (Bp, Bm, "#b8cfe0")):
    pl.add_mesh(band_poly(Pp_, Pm_, z=-0.002), color=col, opacity=0.75,
                lighting=False)
for R in (Rp, Rm, Bp, Bm):
    pl.add_mesh(as_line(R, z=0.001), color="steelblue", line_width=1.2,
                lighting=False)
pl.add_mesh(as_line(Pm, z=0.002), color="crimson", line_width=4,
            lighting=False)
# dotted continuations of the fault LINE to the box edges (the terrane
# boundary continues; only the solid segment is modelled as slipping)
tan0 = (Pm[0] - Pm[1])
tan0 /= np.linalg.norm(tan0)
tan1 = (Pm[-1] - Pm[-2])
tan1 /= np.linalg.norm(tan1)
for tip, d in ((Pm[0], tan0), (Pm[-1], tan1)):
    pl.add_mesh(dashed(tip, box_exit(tip, d), z=0.002),
                color="crimson", line_width=3, lighting=False)
pl.add_mesh(as_line(Pb, z=0.002), color="#8b0000", line_width=4,
            lighting=False)
for tp in (Pm[0], Pm[-1], Pb[0], Pb[-1]):
    pl.add_mesh(pv.PolyData(np.array([[tp[0], tp[1], 0.003]])),
                color="black", point_size=10,
                render_points_as_spheres=True, lighting=False)

# drive arrows: v = 2 V t ê_s (plate-motion-frame shear)
for sgn in (+1.0, -1.0):
    cen = C + sgn * 0.33 * et - sgn * 0.10 * es
    arr = pv.Arrow(start=np.array([*cen, 0.003]),
                   direction=np.array([*(sgn * es), 0.0]),
                   scale=0.14, tip_radius=0.06, shaft_radius=0.02)
    pl.add_mesh(arr, color="black", lighting=False)

labels = {
    "main (tanh S)": Pm[128] + 0.05 * et,
    "branch (through-line)": Pb[70] - 0.075 * et,
    "STRONG (eta x contrast)": np.array([0.16, 0.955]),
    f"w = {W}": Pm[36] - 0.055 * et,
    f"gap = {gap:.3f}": Pb[0] - 0.05 * et - 0.03 * es,
    f"2A = {2 * A}": Pm[100] + 0.09 * et,
}
pts = np.array([[q[0], q[1], 0.005] for q in labels.values()])
pl.add_point_labels(pts, list(labels.keys()), font_size=17,
                    text_color="black", shape=None, always_visible=True,
                    show_points=False)

pl.view_xy()
pl.camera.parallel_projection = True
pl.camera.focal_point = (0.5, 0.5, 0.0)
pl.camera.parallel_scale = 0.56
pl.screenshot(f"{OUT}/s_fault_geometry.png")
pl.close()
print(f"wrote {OUT}/s_fault_geometry.png")
