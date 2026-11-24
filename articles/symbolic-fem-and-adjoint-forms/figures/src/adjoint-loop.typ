// One pass of an inversion: the four steps as a cycle, with the quantity each
// hands to the next. The forward solve's tangent stiffness K is what the
// adjoint solve reuses; the observations enter only as the adjoint's load;
// the gradient is an integral, not a solve. House style: uwfig.typ.
#import "@preview/cetz:0.3.4"
#import "uwfig.typ": *

#set page(width: auto, height: auto, margin: 8pt)
#set text(font: ("Noto Sans", "Helvetica", "Arial"), size: 8pt, fill: ink)

#cetz.canvas(length: 1cm, {
  import cetz.draw: *

  let W = 4.0
  let H = 1.15
  let node(pos, title, sub, name, bg: tint-fluid) = {
    let (x, y) = pos
    rect((x - W / 2, y - H / 2), (x + W / 2, y + H / 2),
         fill: bg, ..styles.interface, radius: 3pt, name: name)
    content((x, y + 0.2), text(weight: "semibold", title))
    content((x, y - 0.22), text(size: 7.5pt, sub))
  }
  // edge with a label beside it; which: "vvec" (field), "fvec" (load), "hand" (ink)
  let hand = (stroke: (paint: ink, thickness: 0.6pt),
              mark: (end: "stealth", fill: ink, scale: 0.6, stroke: (dash: none)))
  let edge(a, b, lbl, which, off, dash: none) = {
    let st = if which == "hand" { hand } else { styles.at(which) }
    if dash != none { st = (stroke: (..st.stroke, dash: dash), mark: st.mark) }
    line(a, b, ..st)
    content((a, 50%, b), box(fill: white, inset: 1.5pt, lbl), anchor: off)
  }

  // ---- the four steps, clockwise from top left
  node((0, 3.2), [1. Solve the model], [$R(u; m) = 0$ by Newton], "fwd")
  node((8, 3.2), [2. Solve the adjoint], [$K^T mu = -(partial J \/ partial u)^T$], "adj")
  node((8, 0), [3. Form the gradient], [$partial J \/ partial m_k + mu^T partial R \/ partial m_k$], "grad")
  node((0, 0), [4. Update the parameters], [$m <- m - alpha nabla_m J$], "upd")

  // ---- what each step hands on
  edge("fwd.east", "adj.west", $K$, "hand", "south")
  edge("adj.south", "grad.north", $mu$, "vvec", "west")
  edge("grad.west", "upd.east", $dif J \/ dif m$, "hand", "north")
  edge("upd.north", "fwd.south", $m$, "hand", "east")
  // the pseudo-load also comes out of the forward problem
  edge("fwd.south-east", "grad.north-west", $partial R \/ partial m_k$, "fvec", "south-west", dash: (3pt, 2.5pt))

  // ---- the observations: the only external input, as the adjoint's load
  content((8, 5.3), text(size: 8pt, [observations $d^"obs"$]), name: "obs")
  line((8, 5.0), "adj.north", ..styles.fvec)
  content((8.15, 4.45), text(size: 7.5pt, fill: force, $partial J \/ partial u$), anchor: "west")
})
