"""Figure: what happens to the comparison when the viscosity structure is
concentrated rather than spread through the box.

Run from the repository root:

    python3 articles/setting-up-full-multigrid/examples/layer_figure.py

The numbers are those printed by `fmg-vs-gamg.py solkz layer` and are repeated
here so the figure has a single, checkable source. Both panels are relative to
the same baseline -- FMG on the constant-viscosity problem -- so the two
profiles can be read against each other. At contrast 1 the two profiles ARE the
same problem (eta = 1 everywhere) and the runs agree to the last digit, which is
why the curves start together.

Colour carries the preconditioner and line style carries the viscosity profile,
so neither is distinguished by colour alone. The palette is checked for
colour-vision separation (worst pair dE 24.7, against a target of 8).

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that
identifies what these numbers came from.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "articles/setting-up-full-multigrid/figures/layer-vs-smooth.png"

CONTRAST = [1e0, 1e2, 1e4, 1e6]

# Relative to FMG at contrast 1. `None` = did not converge: GAMG on the band at
# 1e6 ran past 20 000 multigrid cycles per velocity solve without reaching the
# tolerance, so there is no cost to plot -- reporting the work it managed to do
# before being stopped would be reporting a cap, not a method.
WORK = {
    ("fmg", "smooth"):  [1.0, 1.3, 1.6, 1.8],
    ("gamg", "smooth"): [2.2, 3.3, 4.0, 4.0],
    ("fmg", "band"):    [1.0, 1.9, 2.1, 2.5],
    ("gamg", "band"):   [2.2, 8.1, 28.1, None],
}
TIME = {
    ("fmg", "smooth"):  [1.0, 1.1, 1.2, 1.3],
    ("gamg", "smooth"): [1.2, 1.5, 1.7, 1.6],
    ("fmg", "band"):    [1.0, 1.3, 1.4, 1.5],
    ("gamg", "band"):   [1.2, 2.7, 7.7, None],
}

COLOUR = {"fmg": "#2a78d6", "gamg": "#eb6834"}      # validated categorical 1, 2
STYLE = {"smooth": "-", "band": "--"}
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e4e3df"


def panel(ax, data, title):
    for (pc, profile), y in data.items():
        xs = [x for x, v in zip(CONTRAST, y) if v is not None]
        ys = [v for v in y if v is not None]
        ax.plot(xs, ys, STYLE[profile], color=COLOUR[pc], linewidth=2.0,
                marker="o", markersize=5, markerfacecolor="white",
                markeredgewidth=1.6, zorder=3,
                label="%s, %s" % (pc.upper(), profile))
        # An open marker at the last point that converged, with the failure
        # named rather than left as a gap the reader has to interpret.
        if y[-1] is None:
            # Say what the gap means. An unexplained stop reads as missing data.
            ax.annotate("does not converge\nbeyond this point",
                        xy=(xs[-1], ys[-1]), xytext=(10, -2),
                        textcoords="offset points", ha="left", va="top",
                        fontsize=8.5, color=INK_MUTED, linespacing=1.35)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("viscosity contrast", fontsize=9.5, color=INK_MUTED)
    ax.set_title(title, fontsize=10.5, color=INK, pad=10)
    ax.grid(True, which="major", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_MUTED, labelsize=9)
    # Same tick VALUES in both panels so the two can be read against each
    # other, but each panel framed on its own data rather than padded to a
    # shared top -- the time differences are genuinely smaller and should look
    # it without half the panel being empty.
    ax.set_yticks([1, 1.5, 2, 3, 5, 10, 20, 30])
    ax.set_yticklabels(["1", "1.5", "2", "3", "5", "10", "20", "30"])
    finite = [v for y in data.values() for v in y if v is not None]
    ax.set_ylim(min(finite) * 0.88, max(finite) * 1.45)
    ax.minorticks_off()


fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.1), sharex=True)
fig.patch.set_facecolor("white")
panel(axes[0], WORK, "work per unknown, relative to FMG at contrast 1")
panel(axes[1], TIME, "time per unknown, relative to FMG at contrast 1")
# handlelength long enough that the dashed entries are visibly dashed -- the
# line style is half the encoding, so a legend that hides it breaks identity.
axes[0].legend(frameon=False, fontsize=9, labelcolor=INK_MUTED,
               loc="upper left", handlelength=3.4, borderaxespad=0.2)
fig.tight_layout()
fig.savefig(OUT, dpi=200, facecolor="white")
print("wrote", OUT)
