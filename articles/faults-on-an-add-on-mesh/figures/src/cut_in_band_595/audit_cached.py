"""The numbers in underworld3 #595, from the cached runs in this folder.

Needs numpy only. The runs themselves were made on 2026-08-17 (see the
README); this script re-reads their caches and repeats the audit.

    python audit_cached.py
"""
import os

import numpy as np

from cut_audit import audit

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with np.load(os.path.join(HERE, name), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


for name, what in (("cut_audit.npz", "default band, cut along its centre-line"),
                   ("cut_ladder.npz", "band three nodes across, cut at its spine")):
    print(f"===== {what} ({name})")
    audit(load(name))

for law in ("free", "matched"):
    z = load(f"single_cut_{law}.npz")
    s = np.abs(z["slip"])
    mid = np.abs(z["l"]) <= 0.15
    print(f"default band + cut, {law} slit: mid-fault slip {s[mid].mean():.4f}, "
          f"no-opening leak {float(z['leak']):.2e}")
