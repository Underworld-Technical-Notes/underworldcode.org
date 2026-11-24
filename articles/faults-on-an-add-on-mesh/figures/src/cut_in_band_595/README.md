# The cut-in-band evaluation (underworld3 #595)

The evaluation behind the ladder's construction: a fault cut along the centre
line of a placed band. The cut either snaps band vertices onto the line, or
runs through a row of the band's own vertices.
[underworld3 #595](https://github.com/underworldcode/underworld3/issues/595)
reports it. Louis recalled it on 2026-11-03, when the ladder was ruled equant:
"we looked at whether to cut the band in the centre using the original nodes of
the fault and found that this was best ... One cell either side of that gives a
good mesh".

The scripts and caches were copied on 2026-11-04 from
`~/+Simulations/ribbon_network_2d/` on wombat, where they were run on
2026-08-17. The scripts are unchanged. Their `OUT` path is still that
directory, and they import each other.

## The numbers, from the caches

`python audit_cached.py` repeats the audit from the four `.npz` caches with
numpy alone:

| | default band + cut | band three nodes across + cut |
|---|---|---|
| min angle after the cut | 13.0° | 28.8° |
| band cells, before → after | 104 → 144 | 132 → 132 |
| mid-fault slip (pair mean, \|s\| ≤ 0.15) | 0.4286 | 0.4315 |
| no-opening, max \|jump in v_n\| | 5.6e-17 | 5.6e-17 |

The min angle before the cut, 32.2° and 28.8°, was printed at build time and
is not in the caches. #595's mid-fault slip for the default band, 0.4290, is
`single_cut_free.npz`. That run is the same configuration, with the cut
sampled at the host cell size of 0.030, as in `cut_audit.npz`. The two scripts
average the pair jumps slightly differently. The matched-law slit gives 0.2258.

## The scripts

| file | what it is |
|---|---|
| `single_fault_resolution.py` | one fault of the #544 crossing geometry, placed as a band with `place_thin_volume`; `build_single` is used by the others |
| `single_fault_cut.py` | the default band, cut along its centre line by `add_fault`; caches `single_cut_{free,matched}.npz` |
| `cut_audit.py` | the audit of the cut: doubled vertices, no-opening, quality, label; caches `cut_audit.npz` |
| `cut_ladder.py` | the band meshed transfinite three nodes across, by a monkeypatched assembly, and cut at its spine's own vertices; caches `cut_ladder.npz` |
| `crossing_common.py`, `isotropic_stress_reference.py`, `compliance_algebra.py`, `viz.py` | geometry, measurement and rendering they import |
| `audit_cached.py` | added here: the table above from the caches |

How they were run, from the original README:

```bash
pixi run --manifest-path ~/+Underworld/underworld3-pixi/pixi.toml \
         -e amr-dev python -u <script>.py
```

That was the library of mid-August 2026. The three-across band that
`cut_ladder.py` patches in is now the library's own ladder
(`_occ_ladder_assembly_2d` in `underworld3.utilities.place_surface`, whose
docstring cites #595). The solves have not been repeated on `development`.

`cut_audit.py` was edited after its cache was made. It now samples the cut at
0.011 and writes `cut_audit_fine.npz`. At that spacing, #595 reports that the
same mesh trips the inversion guard. The cache here, `cut_audit.npz`, is the
run that snapped a rail. Its stored cut line is sampled at 0.030.

## Not measured

"No benefit to more cells in the fault itself" was not measured as a count of
cells across a cut band. The nearest numbers come from the same study.
`single_fault_resolution.py` swept the cells across an uncut band. About four
across gave a mid-fault slip of 0.428–0.433; the default, about two across,
gave 0.394–0.413. The three-across cut band's 0.4315 lies in the first range.
Those caches (`single_w*.npz`), and the one-element ladder band
(`single_fault_ladder.py`), remain on wombat.

## The original write-up

From `~/+Simulations/ribbon_network_2d/README.md`, as written on 2026-08-17:

> ## The cut-in-band configuration (2026-08-17, with Louis live)
>
> Louis's proposal: cut the default band along its centre-line — the slit
> carries the slip exactly (contact pairing), the band carries the fault's
> volume physics, the tips end inside weak material so nothing pins.
>
> **Measured, isolated fault, isotropic 1e-3:**
>
> | configuration | mid-fault slip | note |
> |---|---|---|
> | band only, w/4 | 0.428–0.433 | the resolved reference |
> | band only, default 0.9w | 0.394–0.413 | |
> | default band + cut, FREE slit | 0.4290 | pairing = the fault |
> | default band + cut, matched-law slit | 0.2258 | pairing = the slit's SHARE only |
> | 3-across transfinite band + cut | 0.4315 | the clean version |
> | pure contact | 0.449 | |
>
> The law decides what the pairing means: free slit → the pairing is the
> fault; matched slit → the band takes about half and the pairing
> under-reads. (This is why the listric hybrid measured offsets across the
> zone, never the contact jumps.)
>
> **The audit found one real defect (#595), spotted by Louis in the
> shading:** cutting the default band snapped ONE rail vertex onto the
> centre-line (band pinched shut at that point; quality 32° -> 13°; zone
> 104 -> 144 cells). No snap parameter prevents it. Prevention that works:
> the 3-across transfinite band — rails + an exact centre-line vertex row —
> with the cut sampled AT the spine's vertices. Nothing snaps, quality
> unchanged (28.8° before and after), zone census unchanged (132 -> 132),
> slip 0.4315, leak 5.6e-17.
>
> Instruments, settled across the session:
> - **cut present**: the contact pairing (exact, machine-zero opening);
> - **no cut**: P0 cell strain rate MAPPED to the fault's midline nodes
>   (Louis's recipe; adjacency average kills the P1 ringing that made both
>   the raw nodal read and the band integral noisy);
> - never `uw.function.evaluate` on a derivative composite, never probes
>   through a union, never peak-slip at a crossing.
>
> Scripts: `single_fault_cut.py`, `cut_audit.py`, `cut_ladder.py`,
> `fault_node_slip.py`; caches `single_cut_*.npz`, `cut_audit*.npz`,
> `cut_ladder.npz`.

`fault_node_slip.py` is not copied: it is the no-cut instrument, not part of
the cut comparison.
