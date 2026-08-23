"""Figure: the surface topography each treatment predicts, against the exact one.

SolCx publishes the exact dynamic topography on the top wall
(`uw.analytic.SolCx.topography_top`, which is -sigma_zz), so the comparison can
be drawn rather than tabulated. Two panels, the same five curves in each, at a
viscosity contrast of 100 and of a million.

The topography is mean-removed in every case: the box is enclosed, so the
pressure and with it the level of sigma_zz is fixed only up to a constant, and
the deviation is the part that is determined and the part topography is built
from.

Three routes are drawn, and they are not the same measurement:

  * the recovered traction, projected out of the solved velocity and pressure,
    which is the only route Nitsche has;
  * the constraint reaction -- `boundary_normal_traction` for the rotated
    constraint and the multiplier field for the constraint method -- which the
    solve returns as an unknown. Its sign convention is the traction holding the
    wall, which is the topography's sign directly;
  * the penalty's own term, kappa (u.n), which is the traction that condition
    holds the wall with. Drawn rather than the projection off the same solve
    because it is what the note recommends reading; the two agree to about one
    per cent, which is invisible here.

Colour carries the treatment and the exact answer is a thick grey line behind
everything, so no curve is identified by colour alone against the reference.

    python3 generate-topography-figure.py

Writes figures/topography.png. Run against underworld3 `development` at commit
`8b7c8b9e`.
"""
import json
import pathlib
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import solcx as C

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "figures" / "topography.png"
# The solves take about ten minutes and the figure is redrawn far more often
# than it is recomputed, so the curves are cached beside the script the way
# `rotated-basis-data.json` is. Delete it, or pass --recompute, to re-solve.
CACHE = HERE / "topography-data.json"

RES = 32
CONTRASTS = (1.0e2, 1.0e6)
MODES = ("dirichlet", "penalty", "nitsche", "constraint", "rotated")

# Validated categorical palette, as in the multigrid note's figure.
COLOUR = {
    "dirichlet": "#0b0b0b",
    "penalty": "#eb6834",
    "nitsche": "#c13ec1",
    "constraint": "#2a78d6",
    "constraint+r": "#2a78d6",
    "rotated": "#1e9e6a",
}
LABEL = {
    "dirichlet": "component Dirichlet",
    "penalty": "penalty, $10^4$",
    "nitsche": r"Nitsche, $\gamma = 10$",
    "constraint": r"multiplier field $\lambda$",
    "constraint+r": r"traction $\lambda + r(\mathbf{u}\cdot\hat{\mathbf{n}} - \tilde{u}_n)$",
    "rotated": "rotated (reaction)",
}
STYLE = {"dirichlet": (0, (4, 2)), "penalty": "-", "nitsche": "-",
         "constraint": "-", "constraint+r": (0, (1, 1.6)), "rotated": "-"}
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e4e3df"
EXACT = "#b9b7b2"


def profile(mode, eta_B):
    """{name: (x, topography)} along the top wall, mean removed, and the exact one.

    The reaction where there is one, the recovered traction otherwise: that is
    what a user of each treatment would actually have. The constraint method
    returns two curves -- the multiplier as the API returns it, and the
    multiplier plus the augmented-Lagrangian share r(u.n - g), which is the
    other half of the traction the momentum row carries (underworld3#607).
    """
    mesh, stokes, v, exact = C.build(mode, res=RES, eta_B=eta_B)
    stokes.solve()
    if not C.converged(stokes):
        print("%-10s eta_B %.0e  diverged" % (mode, eta_B), flush=True)
        return None
    read = C.reaction_traction(stokes, mode, v=v)
    if read is None:
        coords, values = C.recovered_traction(mesh, stokes)
        curves = {mode: -np.asarray(values)}      # h = -sigma_zz
    else:
        coords, values = read
        curves = {mode: np.asarray(values)}
    if mode == "constraint":
        # BOTH curves come from the solver, and neither is assembled here. That
        # matters: this script used to add r(u.n) to what `reaction_traction`
        # returned, which was right while that returned the bare multiplier and
        # became a DOUBLE COUNT the moment it returned `traction()` instead --
        # the corrected curve drew at twice its augmentation share and left the
        # panel. Two copies of one expression, one of them stale. There is now
        # one copy, and it lives in the solver.
        #   multiplier()  -> lambda, the field
        #   traction()    -> lambda + r(u.n - u~_n), the whole boundary load
        curves["constraint+r"] = curves[mode]                    # traction(), as read
        coords_bare, bare = C.trace(stokes, 2, stokes.multiplier("Top"))
        assert np.allclose(coords_bare, coords), "the two traces disagree"
        curves[mode] = np.asarray(bare)                          # the multiplier alone

    order = np.argsort(coords[:, 0])
    x = coords[order, 0]
    truth = exact.topography_top(coords)[order]
    truth = truth - truth.mean()
    out = {}
    for name, values in curves.items():
        got = values[order] - values.mean()
        # The sign convention is checked rather than assumed, and a curve that
        # comes back anti-correlated is drawn AND named rather than flipped.
        correlation = float(np.dot(got, truth)
                            / (np.linalg.norm(got) * np.linalg.norm(truth) + 1e-300))
        print("%-14s eta_B %.0e  max|h| %.4f  corr %+.3f  l2 %.3f"
              % (name, eta_B, np.abs(got).max(), correlation,
                 np.linalg.norm(got - truth) / np.linalg.norm(truth)), flush=True)
        out[name] = (x, got)
    return out, (x, truth)


def panel(ax, results, truth, title, ylim):
    x, exact = truth
    ax.plot(x, exact, color=EXACT, linewidth=5.0, solid_capstyle="round",
            zorder=1, label="exact")
    for mode, (xs, got) in results.items():
        ax.plot(xs, got, linestyle=STYLE[mode], color=COLOUR[mode],
                linewidth=1.6, zorder=3, label=LABEL[mode])
    ax.axvline(0.5, color=GRID, linewidth=1.0, zorder=0)
    ax.text(0.505, ylim[1] * 0.80, "viscosity step", fontsize=8.5,
            color=INK_MUTED, ha="left", va="top")
    ax.set_xlabel("$x$ along the top wall", fontsize=9.5, color=INK_MUTED)
    ax.set_title(title, fontsize=10.5, color=INK, pad=10)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(*ylim)
    ax.grid(True, which="major", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_MUTED, labelsize=9)


def compute():
    data, truth = {}, {}
    for eta_B in CONTRASTS:
        got = {}
        for mode in MODES:
            out = profile(mode, eta_B)
            if out is None:
                continue
            curves, truth[eta_B] = out
            got.update(curves)
        data[eta_B] = got
    CACHE.write_text(json.dumps(
        {"contrasts": list(CONTRASTS),
         "truth": {str(k): [v[0].tolist(), v[1].tolist()] for k, v in truth.items()},
         "data": {str(k): {m: [c[0].tolist(), c[1].tolist()] for m, c in v.items()}
                  for k, v in data.items()}}))
    return data, truth


def cached():
    raw = json.loads(CACHE.read_text())
    truth = {float(k): (np.array(v[0]), np.array(v[1]))
             for k, v in raw["truth"].items()}
    data = {float(k): {m: (np.array(c[0]), np.array(c[1])) for m, c in v.items()}
            for k, v in raw["data"].items()}
    return data, truth


def main():
    if CACHE.exists() and "--recompute" not in sys.argv:
        data, truth = cached()
        print("drawn from", CACHE.name, "-- pass --recompute to re-solve")
    else:
        data, truth = compute()

    span = max(np.abs(truth[e][1]).max() for e in CONTRASTS)
    ylim = (-1.6 * span, 1.6 * span)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3), sharey=True)
    fig.patch.set_facecolor("white")
    for ax, eta_B in zip(axes, CONTRASTS):
        panel(ax, data[eta_B], truth[eta_B],
              r"$\eta_B/\eta_A = 10^{%d}$" % int(round(np.log10(eta_B))), ylim)
        # Name what left the panel rather than leaving a curve to run off it.
        for mode, (xs, got) in data[eta_B].items():
            if np.abs(got).max() > ylim[1]:
                ax.annotate("%s leaves the panel:\npeaks at %.2f"
                            % (LABEL[mode], np.abs(got).max()),
                            xy=(0.03, ylim[0] * 0.72), fontsize=8.5,
                            color=COLOUR[mode], linespacing=1.35)
        missing = [m for m in MODES if m not in data[eta_B]]
        if missing:
            ax.annotate("does not solve: %s" % ", ".join(LABEL[m] for m in missing),
                        xy=(0.03, ylim[1] * 0.86), fontsize=8.5, color=INK_MUTED)
    axes[0].set_ylabel("surface topography, mean removed",
                       fontsize=9.5, color=INK_MUTED)
    # The legend goes below the panels: at 1e6 every corner of both axes has a
    # curve in it, and a legend inside covered the multiplier's collapse.
    # Both panels, deduplicated: the penalty only converges in the left one and
    # would otherwise be an unlabelled curve.
    handles, labels = [], []
    for ax in axes:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    fig.legend(handles, labels, frameon=False, fontsize=9, labelcolor=INK_MUTED,
               loc="lower center", ncol=3, handlelength=2.6,
               bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.15, 1, 1))
    fig.savefig(OUT, dpi=200, facecolor="white")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
