"""Measure which convention every exact solution in `uw.analytic` obeys.

This generates the table in the note. Nothing here reads a published paper or a
vendored C kernel: every number is formed from the solution's own symbolic
fields by differentiation, so a solution that agrees with a wrong source still
fails. That is the whole point of the exercise.

The negative-control column is the one that makes the table mean anything. It
re-measures the momentum residual with the body force negated. A gate that
cannot fail is not a gate, and a table of small numbers with no such column is
an assertion that small numbers are small.

    pixi run -e amr-dev python convention_audit.py

Run against underworld3 `development` at commit `0addec15`
(0addec1595f8d7a59b99e15b42455267a73dab86, 2026-08-15). `uw.__version__`
reports 0.0.0 for every build, so the commit is the only thing that
identifies what these numbers came from.
"""

import numpy as np
import sympy

import underworld3 as uw
from underworld3.analytic import _validation as V


def build_meshes():
    """One coarse box per dimension. Resolution is irrelevant here.

    The residuals are symbolic identities sampled at points; they do not
    converge with resolution, they either hold or they do not. The mesh exists
    only to carry the coordinate system the solutions are written on.
    """

    return {
        2: uw.meshing.StructuredQuadBox(
            elementRes=(4, 4),
            minCoords=(0.0, 0.0),
            maxCoords=(1.0, 1.0),
            qdegree=3,
        ),
        3: uw.meshing.StructuredQuadBox(
            elementRes=(2, 2, 2),
            minCoords=(0.0, 0.0, 0.0),
            maxCoords=(1.0, 1.0, 1.0),
            qdegree=2,
        ),
    }


def stokes_solutions():
    """Every registered Stokes solution that exposes symbolic fields.

    `symbolic = False` marks a solution reached through a compiled third-party
    package rather than a SymPy expression tree; there is nothing to
    differentiate, so it cannot be measured this way.
    """

    for name in sorted(uw.analytic.available()):
        cls = getattr(uw.analytic, name)
        if not getattr(cls, "symbolic", False):
            continue
        if not uw.analytic.is_available(name):
            continue
        if not hasattr(cls, "dim"):
            continue
        yield name, cls


def trace_check(solution, points):
    r"""Relative size of $\mathrm{tr}\,\sigma + d\,p$.

    Zero says the exposed stress is the TOTAL stress under
    $\sigma = \tau - p\mathbf I$ with a traceless deviator. It is scaled by the
    pressure because that is the term being cancelled.
    """

    dim = solution.dim
    trace = sum(solution.fn_stress[i, i] for i in range(dim))
    residual = V.sample(solution, trace + dim * solution.fn_pressure, points)
    pressure = V.sample(solution, solution.fn_pressure, points)

    return float(np.max(np.abs(residual))) / max(float(np.max(np.abs(pressure))), 1e-300)


def constitutive_check(solution, points):
    r"""Relative size of $\sigma + p\mathbf I - 2\eta\dot\varepsilon$.

    Note what this can and cannot say. For a solution that published only one
    of stress and strain rate, `set_fields` derived the other from exactly this
    identity, so the check is structural rather than evidential -- and the
    signature is visible in the output: an EXACT zero where it is structural,
    order 1e-16 where two separately derived quantities happen to agree.
    """

    dim = solution.dim
    worst = 0.0
    scale = 0.0

    for i in range(dim):
        for j in range(dim):
            deviator = solution.fn_stress[i, j] + (solution.fn_pressure if i == j else 0)
            constitutive = 2 * solution.fn_viscosity * solution.fn_strainrate[i, j]

            difference = V.sample(solution, deviator - constitutive, points)
            magnitude = V.sample(solution, constitutive, points)

            worst = max(worst, float(np.max(np.abs(difference))))
            scale = max(scale, float(np.max(np.abs(magnitude))))

    return worst / max(scale, 1e-300)


def momentum_with_flipped_bodyforce(solution, points):
    r"""The negative control: $\nabla\cdot\sigma - \mathbf f$.

    A solution driven entirely through its boundary has no body force to flip,
    so this returns the same number as the un-flipped residual. That is a
    property of the problem rather than a gap in the check, and the note says
    so where it happens.
    """

    original = solution.fn_bodyforce
    solution.fn_bodyforce = sympy.Matrix([[-component for component in original]])

    try:
        return V.momentum_residual(solution, points)
    finally:
        solution.fn_bodyforce = original


def main():
    meshes = build_meshes()
    rows = []

    for name, cls in stokes_solutions():
        solution = cls(meshes[cls.dim])

        if not hasattr(solution, "fn_stress"):
            continue

        points = solution.sample_points(10)

        rows.append(
            (
                name,
                "deviatoric" if cls.stress_is_deviatoric else "total",
                trace_check(solution, points),
                constitutive_check(solution, points),
                V.momentum_residual(solution, points),
                momentum_with_flipped_bodyforce(solution, points),
                V.incompressibility_residual(solution, points),
                V.strainrate_consistency(solution, points),
            )
        )

    header = (
        "solution",
        "source stress",
        "tr(sigma) + d p",
        "sigma + pI - 2 eta edot",
        "momentum + f",
        "momentum - f",
        "div u",
        "edot vs grad u",
    )

    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))

    for row in rows:
        cells = [row[0], row[1]] + [f"{value:.1e}" for value in row[2:]]
        print("| " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
