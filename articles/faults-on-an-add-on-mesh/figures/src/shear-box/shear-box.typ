// The simple-shear test of UWTN 2026-022: a unit box, v = (y - 1/2, 0) on every
// wall, a straight frictionless fault from (0.30, 0.45) to (0.70, 0.55).
// House style from uwfig.typ (the underworld3 uw-line-diagrams skill).
// Regenerate:  typst compile --format png --ppi 300 shear-box.typ ../../shear-box.png
//              typst compile shear-box.typ ../../shear-box.pdf
#import "@preview/cetz:0.3.4"
#import "uwfig.typ": *
#set page(width: auto, height: auto, margin: 2mm)
#set text(font: ("Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"), size: 8pt, fill: ink)

#cetz.canvas(length: 55mm, {
  import cetz.draw: *
  // a direct label with a white backing (uwfig.typ's label, inlined)
  let lbl(pos, body) = content(pos, box(fill: white.transparentize(15%), inset: 2pt, radius: 2pt, text(8pt, fill: ink, body)))

  // the domain
  rect((0, 0), (1, 1), fill: tint-fluid, stroke: none)

  // wall velocity u = y - 1/2: top and bottom walls, arrows along the wall
  let a = 0.16
  for x in (0.2, 0.5, 0.8) {
    line((x - a / 2, 1.06), (x + a / 2, 1.06), ..styles.vvec)
    line((x + a / 2, -0.06), (x - a / 2, -0.06), ..styles.vvec)
  }
  // side walls: the linear profile u = y - 1/2, drawn outside each wall
  let b = 0.14
  for x0 in (-0.15, 1.15) {
    line((x0, 0.02), (x0, 0.98), ..styles.leader)
    line((x0 + (0.02 - 0.5) * b * 2, 0.02), (x0 + (0.98 - 0.5) * b * 2, 0.98),
         stroke: (paint: velocity, thickness: 0.5pt))
    for y in (0.1, 0.25, 0.75, 0.9) {
      line((x0, y), (x0 + (y - 0.5) * b * 2, y), ..styles.vvec)
    }
  }

  rect((0, 0), (1, 1), ..styles.boundary)

  // the ladder band, exaggerated in width, and the fault
  let p0 = (0.30, 0.45)
  let p1 = (0.70, 0.55)
  let w = 0.022
  let nx = -0.1 / 0.4123 * w
  let ny = 0.4 / 0.4123 * w
  line((0.30 + nx, 0.45 + ny), (0.70 + nx, 0.55 + ny), (0.70 - nx, 0.55 - ny), (0.30 - nx, 0.45 - ny), close: true,
       fill: tint-solid, stroke: (paint: ink, thickness: 0.25pt))
  line(p0, p1, ..styles.interface)
  circle(p0, radius: 0.012, fill: white, stroke: (paint: ink, thickness: 0.5pt))
  circle(p1, radius: 0.012, fill: white, stroke: (paint: ink, thickness: 0.5pt))
  lbl((0.30, 0.36), $(0.30, 0.45)$)
  lbl((0.70, 0.64), $(0.70, 0.55)$)
  lbl((0.5, 0.82), [frictionless fault])
  line((0.5, 0.77), (0.5, 0.515), ..styles.leader)

  lbl((0.5, 1.16), $bold(v) = (y - 1/2, 0)$)

  // axes glyph
  line((-0.36, -0.20), (-0.24, -0.20), ..styles.leader, mark: (end: ">", fill: ink, scale: 0.5))
  line((-0.36, -0.20), (-0.36, -0.08), ..styles.leader, mark: (end: ">", fill: ink, scale: 0.5))
  content((-0.21, -0.20), $x$)
  content((-0.36, -0.05), $y$)
})
