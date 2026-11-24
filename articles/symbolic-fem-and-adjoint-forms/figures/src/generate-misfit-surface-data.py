"""Geometry for the misfit-surface figure (cetz draws, Python computes).

J(m1, m2) is a bowl over the parameter plane, drawn as a grid of surface
lines in an oblique projection. One point on it is where the model has been
solved; the adjoint gives the gradient there, drawn as the tangent plane and
the downhill direction in the parameter plane; a few gradient steps lead to
the minimum, where the model fits the observations.
"""
import json, math, os

A, B, C = 0.62, 0.38, 0.22          # bowl: J = A x^2 + B y^2 + C x y  (x, y from the minimum)
MIN = (1.35, 1.1)                  # m* in the parameter plane
X0, X1, Y0, Y1 = 0.0, 2.4, 0.0, 2.2
NX, NY = 9, 9
ZS = 0.36                          # vertical scale for J

def J(m1, m2):
    x, y = m1 - MIN[0], m2 - MIN[1]
    return A * x * x + B * y * y + C * x * y

def grad(m1, m2):
    x, y = m1 - MIN[0], m2 - MIN[1]
    return (2 * A * x + C * y, 2 * B * y + C * x)

# oblique projection: m1 to the right, m2 back-and-up, J straight up
def P(m1, m2, z):
    return [m1 + 0.55 * m2, 0.46 * m2 + ZS * z]

lines = []
for i in range(NX + 1):
    m1 = X0 + (X1 - X0) * i / NX
    lines.append([P(m1, Y0 + (Y1 - Y0) * k / 40, J(m1, Y0 + (Y1 - Y0) * k / 40)) for k in range(41)])
for j in range(NY + 1):
    m2 = Y0 + (Y1 - Y0) * j / NY
    lines.append([P(X0 + (X1 - X0) * k / 40, m2, J(X0 + (X1 - X0) * k / 40, m2)) for k in range(41)])

m = (0.62, 0.42)                   # the current parameters
z = J(*m); g = grad(*m)
# tangent plane patch, +-h in each parameter
h = 0.20
patch = [P(m[0] + sx * h, m[1] + sy * h, z + g[0] * sx * h + g[1] * sy * h)
         for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
# gradient-descent path in the parameter plane, drawn on the surface
path = [m]; p = m
for _ in range(6):
    gx, gy = grad(*p)
    p = (p[0] - 0.36 * gx, p[1] - 0.36 * gy)
    path.append(p)
path_surf = [P(a, b, J(a, b)) for a, b in path]
# the descent direction at m, in the base plane (z = 0) and on the surface
gn = math.hypot(*g); d = (-g[0] / gn * 0.42, -g[1] / gn * 0.42)
out = dict(lines=lines, point=P(*m, z), foot=P(*m, 0), patch=patch,
           foot_x=P(m[0], Y0, 0), foot_y=P(X0, m[1], 0),
           arrow=[P(*m, z), P(m[0] + d[0], m[1] + d[1], z + g[0] * d[0] + g[1] * d[1])],
           base_arrow=[P(*m, 0), P(m[0] + d[0], m[1] + d[1], 0)],
           path=path_surf, minimum=P(*MIN, 0.0), minimum_foot=P(*MIN, 0),
           axes=dict(o=P(X0, Y0, 0), x=P(X1 + 0.15, Y0, 0), y=P(X0, Y1 + 0.15, 0), z=P(X0, Y0, 1.6)),
           base=[P(X0, Y0, 0), P(X1, Y0, 0), P(X1, Y1, 0), P(X0, Y1, 0)])
here = os.path.dirname(os.path.abspath(__file__))
json.dump(out, open(os.path.join(here, "misfit-surface-data.json"), "w"))
print("J at m:", round(z, 3), "grad:", [round(v, 2) for v in g], "steps:", len(path))
