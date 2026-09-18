// Three representations of one fault on one mesh (cetz draws; the
// geometry comes from generate-band-anatomy-data.py and
// generate-split-anatomy-data.py over the shared anatomy_mesh.py).
//   (a) the non-conforming paint, the trace across the flat grid
//   (b) the ribbon, on the mesh bent so the trace runs along its edges
//   (c) the split, on the bent mesh, exploded for display
// No captions in the drawing: they live in the figure caption.
#import "@preview/cetz:0.3.4"

#set page(width: auto, height: auto, margin: 10pt)
#set text(font: ("Noto Sans", "Helvetica", "Arial"), size: 5pt)

#let band = json("band-anatomy-data.json")
#let split = json("split-anatomy-data.json")

#let mesh-fill = rgb("#f4f6f9")
#let band-fill = rgb("#c9e6c9")
#let fill-plus = rgb("#dce8fc")
#let fill-minus = rgb("#fce4ec")
#let mesh-stroke = rgb("#8899aa")
#let fault-col = rgb("#c62828")
#let dir-col = rgb("#1b5e20")
#let tip-col = rgb("#1a1a1a")
#let note-col = rgb("#555555")

#let cells(oy, coords, tris, fill-of) = {
  import cetz.draw: *
  let P(v) = (coords.at(v).at(0), coords.at(v).at(1) + oy)
  for (k, t) in tris.enumerate() {
    line(P(t.at(0)), P(t.at(1)), P(t.at(2)), close: true,
         fill: fill-of(k), stroke: (paint: mesh-stroke, thickness: 0.3pt))
  }
}

#let directors(oy, cent, keys, dirs) = {
  import cetz.draw: *
  for k in keys {
    let c = (cent.at(k).at(0), cent.at(k).at(1) + oy)
    let d = dirs.at(str(k))
    let h = 0.055
    line((c.at(0) - h * d.at(0), c.at(1) - h * d.at(1)),
         (c.at(0) + h * d.at(0), c.at(1) + h * d.at(1)),
         stroke: (paint: dir-col, thickness: 0.7pt))
  }
}

#let GAP = 1.35
#let YA = GAP
#let YB = 2 * GAP
#let YC = 0.0

#cetz.canvas(length: 1.55cm, {
  import cetz.draw: *

  // ---- (b) the ribbon on the bent mesh -------------------------------------
  cells(YA, band.bent, band.tris,
        k => if band.band_a.contains(k) { band-fill } else { mesh-fill })
  directors(YA, band.cent_a, band.band_a, band.dir_a)
  let Pa(v) = (band.bent.at(v).at(0), band.bent.at(v).at(1) + YA)
  for i in range(band.chain.len() - 1) {
    line(Pa(band.chain.at(i)), Pa(band.chain.at(i + 1)),
         stroke: (paint: fault-col, thickness: 0.9pt))
  }
  for v in band.chain {
    circle(Pa(v), radius: 0.028, fill: fault-col, stroke: none)
  }
  content((-0.3, YA + 0.95), [(b)])
  content((3.5, YA + 0.5), text(fill: fault-col)[$Gamma$])
  line((3.12, YA + 0.25), (3.12, YA + 0.75), stroke: (paint: dir-col, thickness: 0.5pt))
  line((3.07, YA + 0.25), (3.17, YA + 0.25), stroke: (paint: dir-col, thickness: 0.5pt))
  line((3.07, YA + 0.75), (3.17, YA + 0.75), stroke: (paint: dir-col, thickness: 0.5pt))
  content((3.28, YA + 0.5), text(fill: dir-col, size: 4.5pt)[$w$])

  // ---- (a) the same trace on the flat grid ---------------------------------
  cells(YB, band.flat, band.tris,
        k => if band.band_b.contains(k) { band-fill } else { mesh-fill })
  directors(YB, band.cent_b, band.band_b, band.dir_b)
  for i in range(band.curve.len() - 1) {
    line((band.curve.at(i).at(0), band.curve.at(i).at(1) + YB),
         (band.curve.at(i + 1).at(0), band.curve.at(i + 1).at(1) + YB),
         stroke: (paint: fault-col, thickness: 0.9pt))
  }
  content((-0.3, YB + 0.95), [(a)])
  content((3.5, YB + 0.5), text(fill: fault-col)[$Gamma$])

  // ---- (c) the split on the bent mesh, exploded ----------------------------
  let touches(t) = t.any(v => split.chain.contains(v))
  cells(YC, split.exploded, split.moved_tris,
        k => if split.side.at(k) < 0 { fill-minus }
             else if touches(split.tris.at(k)) { fill-plus } else { mesh-fill })
  let Pc(v) = (split.exploded.at(v).at(0), split.exploded.at(v).at(1) + YC)
  let lower(v) = if str(v) in split.replicas { split.replicas.at(str(v)) } else { v }
  for i in range(split.chain.len() - 1) {
    line(Pc(split.chain.at(i)), Pc(split.chain.at(i + 1)),
         stroke: (paint: fault-col, thickness: 0.9pt))
    line(Pc(lower(split.chain.at(i))), Pc(lower(split.chain.at(i + 1))),
         stroke: (paint: fault-col, thickness: 0.9pt, dash: "densely-dashed"))
  }
  for v in split.interior {
    circle(Pc(v), radius: 0.028, fill: fault-col, stroke: none)
  }
  for (orig, rep) in split.replicas {
    circle(Pc(rep), radius: 0.028, fill: white,
           stroke: (paint: fault-col, thickness: 0.8pt))
  }
  for v in split.tips {
    circle(Pc(v), radius: 0.04, fill: white, stroke: (paint: tip-col, thickness: 0.9pt))
    circle(Pc(v), radius: 0.014, fill: tip-col, stroke: none)
  }
  content((-0.3, YC + 0.95), [(c)])
  content((0.42, YC + 0.38), text(size: 4pt)[tip])
  content((2.58, YC + 0.38), text(size: 4pt)[tip])
  content((3.5, YC + 0.66), text(fill: fault-col, size: 4.5pt)[$Gamma^+$])
  content((3.5, YC + 0.34), text(fill: fault-col, size: 4.5pt)[$Gamma^-$])
  line((1.5, YC + 0.66), (1.85, YC + 0.95), stroke: (paint: note-col, thickness: 0.3pt))
  content((2.25, YC + 1.02), text(size: 4pt)[$v^+$ (original)])
  line((1.5, YC + 0.49), (1.85, YC + 0.12), stroke: (paint: note-col, thickness: 0.3pt))
  content((2.25, YC + 0.05), text(size: 4pt)[$v^-$ (replica)])
})
