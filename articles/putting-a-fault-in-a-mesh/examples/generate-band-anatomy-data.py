"""Geometry for the band-anatomy figure (cetz draws, Python computes).

(a) the ribbon on the CONFORMING mesh: the trace along the bent row of
    edges, the band the cells either side of it, each with a director
    (the trace normal); no vertex duplicated, every field continuous.
(b) the non-conforming paint on the FLAT grid: the same curve and the
    same width, but the band is whichever cells fall within w/2 of it.
"""
import json
import os

import anatomy_mesh as M

coords, tris, vid = M.grid()
bent = M.conforming(coords)
ch = M.chain(vid)

# (a) the ribbon: the cells that touch the chain, over its span
cent_a = M.centroids(bent, tris)
band_a = [k for k, t in enumerate(tris)
          if any(v in ch for v in t) and M.X0 < cent_a[k][0] < M.X1]
dir_a = {k: M.normal(cent_a[k][0]) for k in band_a}

# (b) the paint: flat grid, cells within w/2 of the curve
cent_b = M.centroids(coords, tris)
band_b, dir_b = [], {}
for k, c in enumerate(cent_b):
    d, x = M.distance_to_curve(c)
    if d <= 0.5 * M.W and M.X0 <= c[0] <= M.X1:
        band_b.append(k)
        dir_b[k] = M.normal(x)

samples = [M.curve(M.X0 + (M.X1 - M.X0) * k / 60) for k in range(61)]
out = dict(flat=coords, bent=bent, tris=tris, cent_a=cent_a, cent_b=cent_b,
           chain=ch, band_a=band_a, dir_a={str(k): v for k, v in dir_a.items()},
           band_b=band_b, dir_b={str(k): v for k, v in dir_b.items()},
           curve=samples, width=M.W)
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "band-anatomy-data.json"), "w") as f:
    json.dump(out, f)
print(f"wrote band-anatomy-data.json: band (a) {len(band_a)} cells, "
      f"band (b) {len(band_b)} cells")
