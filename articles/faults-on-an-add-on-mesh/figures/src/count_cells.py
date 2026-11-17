"""Cell counts of the figure's meshes, two ways, in the figure's build order and in the
sweep's (tail_sweep_linear.py, H1). Non-dimensional, the note's fixture: unit box, base
cell size 1/8 with two refinements (h_b = 1/32), fault (0.30, 0.45)-(0.70, 0.55), 80 spine
intervals at S.

The two scripts sample the trace in two algebraically equal forms (uw_trace), which
differ in the last bit.

The figure counts a mesh's cells as the height-0 stratum of its DM; the sweep counts the
cells its plex cell numbering owns. Serial, both should be the whole mesh.

    python count_cells.py -uw_trace figure     # 878, 3006, 3498 (the figure's meshes)
    python count_cells.py -uw_trace sweep      # 878, 3008, 3496 (the tail sweep's)
"""
import numpy as np
import underworld3 as uw
from underworld3.utilities.place_surface import place_fault_ribbon_2d

params = uw.Params(
    uw_n_rungs=80,            # spine intervals at S (the figure's N_FINE)
    uw_trace="sweep",         # "sweep": A + kS (B - A)/L; "figure": A + kS t, t = (B - A)/L
)

A, B = np.array([0.30, 0.45]), np.array([0.70, 0.55])
n = int(params.uw_n_rungs)
L = float(np.linalg.norm(B - A))
S = L / n
if params.uw_trace == "figure":
    trace = A + (np.arange(n + 1) * S)[:, None] * ((B - A) / L)
else:
    trace = A + (np.arange(n + 1) * S)[:, None] * (B - A) / L


def ladder(host, c, split=True):
    for clearance in (0.7, 0.5, 0.3):
        try:
            return place_fault_ribbon_2d(host, [("Fault", trace[::c])], 2 * S * c, margin_rings=1,
                                         clearance=clearance, split=split, mesher="ladder")[0]
        except RuntimeError as err:
            last = err
    raise last


def counts(m):
    """(height-0 stratum, cells the plex numbering owns, cell-type strata)."""
    cS, cE = m.dm.getHeightStratum(0)
    owned = int(np.count_nonzero(m.dm.getCellNumbering().getIndices() >= 0))
    types = {}
    for c in range(cS, cE):
        t = int(m.dm.getCellType(c))
        types[t] = types.get(t, 0) + 1
    return cE - cS, owned, types


def report(order):
    base = uw.meshing.UnstructuredSimplexBox(minCoords=(0, 0), maxCoords=(1, 1), cellSize=1 / 8,
                                             regular=False, qdegree=2, refinement=2)
    lv = base._coarse_level_meshes()[:-1] + [base]
    out = {"1/8": lv[0], "1/16": lv[1], "1/32": lv[2]}
    if order == "figure":          # S open, S split, then S, 2S, 4S (the figure's order)
        ladder(base, 1, split=False)
        ladder(base, 1)
        out["S on 1/32"] = ladder(base, 1)
        out["2S on 1/32"] = ladder(base, 2)
        out["4S on 1/16"] = ladder(lv[1], 4)
    else:                          # 4S, 2S, then S (the sweep's order)
        out["4S on 1/16"] = ladder(lv[1], 4)
        out["2S on 1/32"] = ladder(base, 2)
        out["S on 1/32"] = ladder(base, 1)
    for name in ("1/8", "1/16", "1/32", "4S on 1/16", "2S on 1/32", "S on 1/32"):
        uw.pprint(f"{order:7s} {name:11s} stratum, owned, types: {counts(out[name])}")


uw.pprint(f"trace {params.uw_trace}: largest difference from the other form "
          f"{np.abs(trace - (A + (np.arange(n + 1) * S)[:, None] * (B - A) / L)).max():.2e}, "
          f"{np.abs(trace - (A + (np.arange(n + 1) * S)[:, None] * ((B - A) / L))).max():.2e}")
report("figure")
report("sweep")
