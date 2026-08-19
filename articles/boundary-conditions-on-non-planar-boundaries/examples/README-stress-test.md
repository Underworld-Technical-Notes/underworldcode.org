# The stress test: plan and status

The leak tables measure the *constraint*. This is the test that measures what
the constraint is wanted for — the surface normal stress, and through it
dynamic topography.

## Why the current comparison is not enough

`traction.py` compares two methods that both return the traction as an unknown:
the multiplier field `h`, and the reaction of the rotated constraint. They agree
to about 1% at one resolution, but there is **no oracle**, so when the vertex and
midpoint columns behave differently under refinement nothing says which is
right. Its numbers are deliberately not quoted in the note.

## The oracle: Zhong et al. (2008)

`uw.analytic.Zhong2008` is a propagator-matrix solution for a delta-function
load in a shell, and `.response()` returns the surface topography kernel
directly. For the default case — degree 2, load at r = 0.775, isoviscous,
r_inner = 0.55 — it gives

    surface_topography              0.4191904156575601
    cmb_topography                  0.7705825500322292
    surface_geoid                   0.0257906289002894
    surface_characteristic_velocity -0.0100641246068943

with self-gravity variants alongside, referenced to Zhong et al. (2008),
GGG 9, Q10017, doi:10.1029/2008GC002048, after Hager & O'Connell (1981).

This is the right test because the quantity it publishes is the one the note
cares about, rather than a velocity field from which a stress must be inferred.

**It is spherical.** The harmonic degree is a spherical-harmonic degree and the
solution carries a planet radius, so the matching model is a 3-D spherical
shell, not the 2-D annulus the leak tables use. That sets the cost, and it is
the reason this is a separate piece of work rather than another column in an
existing table.

## What has to be built

1. A spherical shell, free slip on both radii, with a delta-function density
   load at r = 0.775 in a single spherical harmonic of degree 2.
2. The same model under each boundary treatment that a shell supports.
3. Surface topography from `sigma_nn`, against 0.41919.

Two things to watch, both already known:

- On a curved boundary, **vertex** values of `sigma_nn` carry the O(h)
  facet-geometry error and **edge-midpoint** values are superconvergent
  (underworld3#414). A pointwise comparison must say which it is using.
- On an enclosed domain the multiplier and the traction are each determined
  only up to a constant, so the comparison is of the *deviation*, which is what
  topography is anyway.

## The supplementary check: SolCx

SolCx is a Cartesian box, so it cannot test anything about curved boundaries and
all four treatments degenerate to the same component constraint there. It is
still a fair test of whether a **penalty or Nitsche form constrains the normal
degrees of freedom it is given**, with the geometry factored out and an exact
answer available. Worth having for that alone.
