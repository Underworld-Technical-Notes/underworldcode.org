"""Geometry for the split-anatomy figure (cetz draws, Python computes).

The same CONFORMING mesh as band-anatomy (a): the curved trace runs
along a row of edges. The chain has nine vertices: two tips (shared)
and seven interior (duplicated by the split). The "after" panel is
EXPLODED for display — the Minus block under the trace translated down
— because the real copies are geometrically coincident.
"""
import json
import os

import anatomy_mesh as M

DELTA = 0.09          # display-only explosion offset

coords, tris, vid = M.grid()
bent = M.conforming(coords)
ch = M.chain(vid)
tips = [ch[0], ch[-1]]
interior = ch[1:-1]
cent = M.centroids(bent, tris)

# Minus side = cells touching the chain from below, within the span;
# everything else, including the cells beyond the tips, stays welded
side = []
for k, t in enumerate(tris):
    touches = any(v in ch for v in t)
    below = cent[k][1] < M.curve(cent[k][0])[1]
    side.append(-1 if (below and touches and M.X0 < cent[k][0] < M.X1) else +1)

# Exploded: the replicas and the whole Minus block strictly inside the
# span move down together; the tips and the columns at the tips stay,
# so the cells at the two ends shear — the pinned tip
exploded = [list(c) for c in bent]
replicas = {}
for v in interior:
    replicas[v] = len(exploded)
    exploded.append([bent[v][0], bent[v][1] - DELTA])
for v, (x, y) in enumerate(coords):
    if y < 0.5 - 1e-9 and M.X0 + 1e-9 < x < M.X1 - 1e-9:
        exploded[v][1] -= DELTA
moved_tris = [[replicas.get(v, v) for v in t] if s < 0 else list(t)
              for t, s in zip(tris, side)]

out = dict(coords=bent, exploded=exploded, tris=tris, moved_tris=moved_tris,
           side=side, chain=ch, tips=tips, interior=interior,
           replicas=replicas, delta=DELTA)
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "split-anatomy-data.json"), "w") as f:
    json.dump(out, f)
print("wrote split-anatomy-data.json:",
      f"{len(bent)} verts, {len(tris)} tris, chain {len(ch)},",
      f"replicas {len(replicas)}")
