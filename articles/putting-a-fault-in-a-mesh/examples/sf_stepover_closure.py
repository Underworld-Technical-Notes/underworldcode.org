"""The stepover closed to the split's floor, against the continuous
control, at superfine: how much of the through-going slip each
representation carries onto the segment beyond the gap.

Four dumps from sf_split_seam_viz.py (-uw_cont_gap_rungs 1 and 0, for
-uw_rep split and ti -uw_eta1 5e-4). The Cont region is the arc beyond
the Main's design tip, S_MAIN[1]; in the continuous control it is the
same arc of the one uncut line.

    ../../uwrun sf_stepover_closure.py
"""
import numpy as np

import rig_geometry as G

RES = "superfine"
W, S_F = G.RES[RES]


def strands(f):
    d = np.load(f, allow_pickle=True)
    labels = list(d["slip_labels"])
    arr = d["slips"]
    segs = [q[~np.isnan(q[:, 0])] for q in
            np.split(arr, np.flatnonzero(np.isnan(arr[:, 0])))]
    segs = [q for q in segs if len(q)]
    return dict(zip(labels, segs))


def line_profile(st):
    """The Main-line family on one arc coordinate: s along ES from C."""
    parts = [st["Main"]] + ([st["Cont"]] if "Cont" in st else [])
    P = np.vstack([q[:, :2] for q in parts])
    v = np.concatenate([q[:, 2] for q in parts])
    ok = np.concatenate([q[:, 3] > 0 if q.shape[1] > 3
                         else np.ones(len(q), bool) for q in parts])
    s_ = (P - np.asarray(G.C)) @ G.ES
    o = np.argsort(s_)
    return s_[o], np.where(ok[o], v[o], np.nan)


def region_mean(s_, v, lo, hi):
    m = (s_ > lo) & (s_ < hi) & np.isfinite(v)
    return float(np.mean(np.abs(v[m]))) if m.any() else float("nan")


s_tip = G.S_MAIN[1]
s_end = s_tip + G.CONT_LEN
rows = []
for rep, eta in (("split", ""), ("ti", "_eta0.0005")):
    out = {}
    for gap in (1, 0):
        f = f"fields_{rep}_{RES}_gather_np1_rank0{eta}_cont{gap}.npz"
        s_, v = line_profile(strands(f))
        out[gap] = (region_mean(s_, v, s_tip + 0.01, s_end - 0.01),
                    region_mean(s_, v, -0.2, 0.2),
                    float(np.nanmax(np.abs(v))))
    seg_closed, main_closed, pk_closed = out[1]
    seg_cont, main_cont, pk_cont = out[0]
    rows.append((rep, seg_closed, seg_cont, seg_closed / seg_cont,
                 main_closed, main_cont, pk_closed, pk_cont))

print(f"{'rep':<6}{'seg closed':>12}{'seg cont':>10}{'ratio':>8}"
      f"{'main closed':>13}{'main cont':>11}{'peak closed':>13}{'peak cont':>11}")
for r in rows:
    print(f"{r[0]:<6}{r[1]:>12.4f}{r[2]:>10.4f}{r[3]:>8.3f}"
          f"{r[4]:>13.4f}{r[5]:>11.4f}{r[6]:>13.4f}{r[7]:>11.4f}")
