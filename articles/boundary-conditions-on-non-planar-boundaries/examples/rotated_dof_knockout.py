"""What the rotated constraint does to the MATRIX, not to the answer.

On an axis-aligned box the per-node rotation Q is the identity, so the rotated
treatment and a component Dirichlet condition are the same arithmetic: agreeing
answers prove nothing about the machinery. Turning the frame makes Q a real
rotation, but the answers still agree -- correctly, since a rigid rotation is an
orthogonal similarity of the discrete problem. Neither run inspects what was
actually eliminated.

This does. Two statements about the assembled system:

  * Q is orthogonal, and at 45 degrees it is nowhere near the identity;
  * the converged Cartesian reaction r = A.u - b at a constrained node is
    PARALLEL TO THE WALL NORMAL. That is the signature of the knockout: the row
    that was struck is the wall-normal momentum balance, so the force the
    constraint had to supply has no tangential part. If the elimination were
    done in the coordinate frame -- the failure a rotated run cannot otherwise
    distinguish -- the reaction would lie along a coordinate axis instead.

The reaction is the solver's own `A.u - b`, stashed at convergence
(`_rotated_freeslip_info["reaction"]`); it is what `boundary_normal_traction`
reads the normal component of.

    python3 rotated_dof_knockout.py

Run against underworld3 `bugfix/multiplier-traction` (PR #617).
"""
import sys

import numpy as np

import underworld3 as uw

from underworld3.utilities import rotated_bc as RB

import solcx_rotated as RT

RES = 16
CORNER = 1.0e-9


def reaction_vectors(stokes, theta, boundary="Top"):
    """The Cartesian nodal reaction at each node of `boundary`, corners dropped.

    Reads the same stashed residual `boundary_normal_traction` uses, but keeps
    both components instead of projecting onto the normal.
    """
    info = stokes._rotated_freeslip_info
    dm = stokes.dm
    dim = stokes.mesh.dim
    rcl = dm.getLocalVec()
    dm.globalToLocal(info["reaction"], rcl)
    rca = np.asarray(rcl.getArray())
    lsec = dm.getLocalSection()
    csec = dm.getCoordinateSection()
    cvec = np.asarray(dm.getCoordinatesLocal().array).reshape(-1, dim)
    v0, v1 = dm.getDepthStratum(0)

    coords, vectors = [], []
    for q, _nrm in RB._boundary_velocity_nodes(stokes, boundary, normal=None):
        lo = lsec.getFieldOffset(q, RB._VELOCITY_FIELD)
        x = RB._point_coord(dm, dim, cvec, csec, v0, v1, q)
        coords.append(x)
        vectors.append(np.array(rca[lo:lo + dim]))
    dm.restoreLocalVec(rcl)
    coords, vectors = np.array(coords), np.array(vectors)

    # A corner belongs to two walls and carries both reactions, so its direction
    # is a sum of two normals and says nothing about either wall.
    material = coords @ RT.rotation(theta)
    keep = (material[:, 0] > CORNER) & (material[:, 0] < 1.0 - CORNER)
    return coords[keep], vectors[keep]


def q_is_orthogonal(stokes):
    """||Q^T Q x - x|| / ||x||, and ||Q x - x|| / ||x||.

    The second is reported by the script but is NOT the discriminator it looks
    like: even on the aligned box Q reorders the local axes so the wall normal
    comes first, so it is never the identity. What separates the two frames is
    the DIRECTION the constraint eliminates, which the reaction shows.
    """
    info = stokes._rotated_freeslip_info
    Q, Qt = info["Q"], info["Qt"]
    x = Q.createVecRight()
    x.setRandom()
    y = Q.createVecLeft()
    Q.mult(x, y)
    z = x.duplicate()
    Qt.mult(y, z)
    z.axpy(-1.0, x)
    orthogonality = z.norm() / x.norm()
    # ||Q x - x||: zero when Q is the identity, O(1) when it turns the frame
    w = y.copy()
    w.axpy(-1.0, x)
    return orthogonality, w.norm() / x.norm()


def check(theta_degrees):
    theta = np.radians(theta_degrees)
    mesh, stokes, v, truth = RT.build("rotated", res=RES, theta=theta)
    stokes.solve()
    n = RT.rotation(theta) @ np.array([0.0, 1.0])
    t = np.array([-n[1], n[0]])

    coords, r = reaction_vectors(stokes, theta)
    magnitude = np.linalg.norm(r, axis=1)
    live = magnitude > 1.0e-30
    tangential = np.abs(r[live] @ t) / magnitude[live]
    along_y = np.abs(r[live] @ np.array([0.0, 1.0])) / magnitude[live]
    along_x = np.abs(r[live] @ np.array([1.0, 0.0])) / magnitude[live]
    orthogonality, _ = q_is_orthogonal(stokes)
    return dict(nodes=int(live.sum()), tangential=float(tangential.max()),
                along_x=float(along_x.mean()), along_y=float(along_y.mean()),
                orthogonality=float(orthogonality))


if __name__ == "__main__":
    print("Rotated free slip on every wall, %d x %d. The reaction is the solver's"
          % (RES, RES))
    print("own A.u - b at convergence.")
    print()
    print("| frame | nodes | ||Q^tQ - I|| | reaction . t | reaction . x | reaction . y |")
    print("|---|---|---|---|---|---|")
    for degrees in (0.0, 45.0):
        got = check(degrees)
        print("| %.0f° | %d | %.1e | %.1e | %.3f | %.3f |"
              % (degrees, got["nodes"], got["orthogonality"], got["tangential"],
                 got["along_x"], got["along_y"]), flush=True)
