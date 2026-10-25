# Model derivatives: the viscosity floor, and friction on a listric fault

The examples for the technical note *Model Derivatives and Their Uses*
(UWTN 2026-021). Both take the derivative of a prediction with respect to a
parameter from the solver's own adjoint, `stokes.gradient(J, parameters=...)`.

| file | what it does |
|---|---|
| `viscosity_floor.py` | lowers the viscosity floor of a viscoplastic layer step by step, and gives at each floor how much two predictions still depend on it; `python viscosity_floor.py -uw_cell_size 0.025` runs it finer |
| `fault_friction.ipynb` | the fault example as a notebook: four friction coefficients on a listric fault, recovered from the surface uplift rate and the shear stress at five interior points |
| `fault_friction.py` | the same, as a script in jupytext percent format; `python fault_friction.py -uw_check_only 1` runs the gradient check alone |
| `render_fault_friction.py` | PyVista renders of the fault truth: the plane's viscosity, the slip rate, the uplift and the pressure |

The viscosity-floor example takes a few minutes at its default resolution.
The fault example's gradient check takes about three minutes and its
inversion about ten on a laptop. The transcript of a fault run is written to
`transcripts/<started>/`, and `uw.transcript_figure(...)` draws it.

The fault problem is stated in kilometres, pascal seconds and millimetres per
year, and the solver works in units of the depth, the viscosity and the
convergence rate. The observation sets, the noise and the prior are switches
in the parameter block at the top of the notebook.

The note's figures are drawn by the scripts in `../figures/src/`, from the
files these examples write.
