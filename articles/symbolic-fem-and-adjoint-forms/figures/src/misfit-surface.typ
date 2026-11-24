// The misfit as a surface over the parameter plane. One forward solve puts
// us at one point; the adjoint gives the tangent plane there, hence the
// downhill direction; a few steps reach the minimum. House style: uwfig.typ.
#import "@preview/cetz:0.3.4"
#import "uwfig.typ": *

#set page(width: auto, height: auto, margin: 8pt)
#set text(font: ("Noto Sans", "Helvetica", "Arial"), size: 8pt, fill: ink)

#let d = json("misfit-surface-data.json")
#let pt(p) = (p.at(0), p.at(1))

#cetz.canvas(length: 1.6cm, {
  import cetz.draw: *
  // the parameter plane and its axes
  line(..d.base.map(pt), close: true, stroke: (paint: mesh-grey, thickness: 0.4pt), fill: tint-solid.transparentize(60%))
  line(pt(d.axes.o), pt(d.axes.x), ..styles.leader, mark: (end: "stealth", fill: ink, scale: 0.5))
  line(pt(d.axes.o), pt(d.axes.y), ..styles.leader, mark: (end: "stealth", fill: ink, scale: 0.5))
  line(pt(d.axes.o), pt(d.axes.z), ..styles.leader, mark: (end: "stealth", fill: ink, scale: 0.5))
  content(pt(d.axes.x), $m_1$, anchor: "north-west", padding: 2pt)
  label(pt(d.axes.y), $m_2$, align-to: "south")
  content(pt(d.axes.z), $J$, anchor: "south", padding: 2pt)
  // the foot of the current point: coordinates read off the two axes
  line(pt(d.foot_x), pt(d.foot), stroke: (paint: ink, thickness: 0.5pt, dash: (1.5pt, 2pt)))
  line(pt(d.foot_y), pt(d.foot), stroke: (paint: ink, thickness: 0.5pt, dash: (1.5pt, 2pt)))
  circle(pt(d.foot), radius: 0.03, fill: ink, stroke: none)
  // the surface: a grid of lines, thin
  for l in d.lines { line(..l.map(pt), stroke: (paint: velocity.transparentize(35%), thickness: 0.4pt)) }
  // the minimum, and the foot of the current point
  circle(pt(d.minimum), radius: 0.045, fill: ink, stroke: none)
  let (qx, qy) = pt(d.minimum)
  label((qx, qy + 0.10), $m^*$, align-to: "south")
  // the tangent plane, and the descent path
  line(..d.patch.map(pt), close: true, fill: tint-fluid.transparentize(25%), ..styles.interface)
  line(..d.path.map(pt), stroke: (paint: ink, thickness: 0.6pt, dash: (2pt, 2pt)))
  for p in d.path.slice(1) { circle(pt(p), radius: 0.03, fill: white, stroke: ink + 0.5pt) }
  line(pt(d.arrow.at(0)), pt(d.arrow.at(1)), ..styles.fvec)
  circle(pt(d.point), radius: 0.055, fill: force, stroke: white + 0.6pt)
  let (px, py) = pt(d.point)
  label((px, py + 0.26), $J(m)$, align-to: "south")
  let (ax, ay) = pt(d.arrow.at(1))
  label((ax + 0.06, ay - 0.06), text(fill: force, $-nabla_m J$), align-to: "north-west")
})
