"""What each treatment costs.

The note compares four ways of imposing free slip on accuracy. This measures the
other half of the choice: what each one costs to solve, and what its surface
traction costs to recover once solved.

Two numbers per treatment, because they are paid at different times:

  * the SOLVE. The rotated constraint changes the operator; the multiplier adds a
    field and enlarges the saddle point; the weak forms add a boundary term to a
    system that is otherwise the plain Stokes one.
  * the RECOVERY of the surface traction. The weak forms have to project
    `n.sigma.n` out of the solution, which is a second (scalar, symmetric) solve.
    The rotated constraint and the multiplier read theirs off the state the solve
    already returned, which is arithmetic on the boundary trace and no solve at
    all.

Method: each configuration is built and solved once UNTIMED (JIT compilation,
PETSc setup and the first-touch allocations are not what is being measured), then
timed `repeats` times. Runs are sequential by construction -- concurrent PETSc
solves contend for memory bandwidth and inflate each other by tens of per cent.

    python3 timing.py            # the table
    python3 timing.py 0.05       # at one cell size

Run against underworld3 `bugfix/multiplier-traction`.
"""
import sys
import time

import numpy as np
import sympy

import underworld3 as uw

import stress as S

REPEATS = 3
# Big enough that a solve is seconds rather than hundredths: at 10k nodes the
# four treatments were separated by less than the run-to-run spread.
CELLS = (0.05, 0.03, 0.02, 0.0125)
MODES = ("penalty_node", "nitsche", "constraint", "rotated")


def _time(call, repeats=REPEATS):
    """Median of `repeats` timings, and the spread, in seconds.

    One UNTIMED call first. The first recovery in a process compiles its
    projection: timed cold it read 1.145 s where the same call reads 0.038 s
    warm, which is a measurement of the JIT and not of the method.
    """
    call()
    got = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        got.append(time.perf_counter() - start)
    return float(np.median(got)), float(np.max(got) - np.min(got))


def solve_cost(mode, cell):
    """Seconds to solve, and the nonlinear/linear iteration counts."""
    mesh, stokes, v, exact = S.build(mode, cell=cell)
    stokes.solve()                       # untimed: JIT, setup, first touch
    assert S.converged(stokes)
    iterations = stokes.snes.getIterationNumber()
    median, spread = _time(stokes.solve)
    return mesh, stokes, v, exact, median, iterations


def recovery_cost(mesh, stokes, mode):
    """Seconds to get sigma_nn on the boundary, by the route that treatment has."""
    if mode == "rotated":
        return _time(lambda: stokes.boundary_normal_traction("Upper"))
    if mode == "constraint":
        # The whole traction, h + r(u.n - g). Reading it is an expression build
        # plus a boundary-trace evaluation -- no solve.
        return _time(lambda: S.multiplier_traction(stokes, stokes.u))
    # The weak forms: project n.sigma.n and read its trace. A scalar solve.
    return _time(lambda: S.recovered_traction(mesh, stokes))


def table(cells=CELLS, modes=MODES):
    print("seconds, median of %d timed repeats after one untimed warm-up" % REPEATS)
    print()
    print("| cell size | velocity nodes | " + " | ".join(
        "%s: solve / recover" % m for m in modes) + " |")
    print("|---" * (len(modes) + 2) + "|")
    for cell in cells:
        row, nodes = [], None
        for mode in modes:
            mesh, stokes, v, exact, solve, its = solve_cost(mode, cell)
            nodes = len(v.coords) if nodes is None else nodes
            recover, _s = recovery_cost(mesh, stokes, mode)
            row.append("%.2f / %.3f" % (solve, recover))
        print("| %.3f | %d | %s |" % (cell, nodes, " | ".join(row)), flush=True)


if __name__ == "__main__":
    cells = (float(sys.argv[1]),) if sys.argv[1:] else CELLS
    table(cells=cells)
