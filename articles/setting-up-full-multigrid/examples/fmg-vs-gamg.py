"""FMG against GAMG: when the choice does not matter, and when it does.

Same mesh and same discretisation each time; the only differences are the
viscosity structure and which preconditioner the velocity block uses.
"""
import time, numpy as np, sympy, underworld3 as uw

def run(pc, contrast, refinement=2, cell=1/8):
    mesh = uw.meshing.UnstructuredSimplexBox(
        minCoords=(0.,0.), maxCoords=(1.,1.), cellSize=cell,
        qdegree=3, refinement=refinement)
    x, y = mesh.X.coords_sym if hasattr(mesh.X,"coords_sym") else mesh.X
    v = uw.discretisation.MeshVariable("U", mesh, mesh.dim, degree=2)
    p = uw.discretisation.MeshVariable("P", mesh, 1, degree=1)
    stokes = uw.systems.Stokes(mesh, velocityField=v, pressureField=p)
    stokes.constitutive_model = uw.constitutive_models.ViscousFlowModel
    # A viscous layer across the middle: contrast=1 is the easy case.
    eta = 1.0 + (contrast - 1.0) * sympy.exp(-(((y - 0.5) / 0.08) ** 2))
    stokes.constitutive_model.Parameters.shear_viscosity_0 = eta
    stokes.bodyforce = sympy.Matrix([0, -sympy.sin(sympy.pi * x) * sympy.cos(sympy.pi * y)])
    for wall, comps in (("Left",(0,)),("Right",(0,)),("Bottom",(1,)),("Top",(1,))):
        stokes.add_dirichlet_bc((0.,)*mesh.dim, wall, comps)
    stokes.preconditioner = pc
    stokes.tolerance = 1e-6
    t0 = time.time()
    stokes.solve()
    dt = time.time() - t0
    ksp = stokes.snes.getKSP()
    try:
        its = ksp.getPC().getFieldSplitSubKSP()[0].getIterationNumber()
    except Exception:
        its = -1
    print("  %-5s contrast %-7g  %6.2f s   velocity its %s   levels %d"
          % (pc, contrast, dt, its, len(mesh.dm_hierarchy)), flush=True)
    return dt

for contrast in (1.0, 1.0e4):
    print("viscosity contrast %g" % contrast, flush=True)
    for pc in ("gamg", "fmg"):
        run(pc, contrast)
