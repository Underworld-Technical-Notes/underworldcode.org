# Figures lost with the old Ghost host

Fifteen figures are still hot-linked to `underworldcode.ghost.io`, the
Ghost(Pro) host the site used before it was self-hosted. The files were never
copied to the droplet, so they are broken on the live site today. One more,
`ModelComparison.png`, 404s on the current host.

**The Internet Archive does not have them.** Every capture of that host is a
~750-byte `warc/revisit` record sharing a digest with a 302, and the earliest
is November 2023 — by which time the host was already gone. It captured the
redirect, never the image.

What survives is the caption and the surrounding text, which is what this
table is for: enough to recognise a figure you may still have, or be able to
remake.

Recovery depends on local copies — original model output, figures from the
corresponding papers, or screenshots that can simply be retaken.

Some are easier than others. The five Docker and Kitematic screenshots are of
software that has itself moved on; remaking them would produce a picture of
2026, not of what the post described, and dropping them with a note may be
truer. The science figures — the craton snapshots, the Moho surface, the
delamination series, the dilatancy comparison — are the ones worth hunting for,
and most have a corresponding paper.

## `getting-started-60-seconds-to-underworld`

Getting started: 60 seconds to Underworld · doi:10.59350/3y92k-n4v30

| file | caption or alt text | context immediately before it |
|---|---|---|
| `Docker_hello_world.png` | Thanks Docker ! | …ou. Type in docker run hello-world and hit enter. After a little number-crunching you should receive a cute message from the good folks at Docker Hub. |
| `timer_60_seconds.png` | Hardly seems fair... | … ready to run. On your marks... Take a deep breath. You are about to become a champion Underworld2 geodynamic numerical modeller. Go! Start the clock. |

## `viscoelasticity`

Viscoelasticity in Underworld2 · doi:10.59350/3atx2-v4j54

| file | caption or alt text | context immediately before it |
|---|---|---|
| `stressHistory_dAlpha-1.png` | Viscoelastic stress history term for different relaxation times | …stic material undergoes simple shear at a constant rate until $t = 4$. The shearing velocity is then taken to zero with the stress decaying with time. |

## `alaska-moho-model-reproducible-research-with-containers`

Alaska Moho Model (Reproducible research with containers) · doi:10.59350/pn8gh-98592

| file | caption or alt text | context immediately before it |
|---|---|---|
| `MohoSurfaceGradient-ClusteredGrids.png` | *(none)* | … |

## `craton-formation-and-the-onset-of-plate-tectonics`

Craton Formation and the Onset of Plate Tectonics · doi:10.59350/c4g09-htk29

| file | caption or alt text | context immediately before it |
|---|---|---|
| `CratonsLithosphere.png` | *(none)* | …relative thickness of crust to lithosphere (also from Crust 1.0) which tends to pick stable zones in blue shades from deforming zones in red. dataset. |
| `CratonFormationMovieFrames-2.png` | Snapshots from the movie below that show the initial failure of the cold lid after the heat-pipe mode stops (A | … to a more sedate form of steadily moving plates, the stresses never reached a level that could deform these remnants of the pre-plate-tectonic state. |

## `untitled`

Modelling Drips and Delamination with Underworld · doi:10.59350/x638s-dpr14

| file | caption or alt text | context immediately before it |
|---|---|---|
| `schematic-1.png` | Modelling Drips and Delamination with Underworld | … $$\eta'_c < 10^{-1}$$), delamination is triggered. If $$D'=0$$, then dripping dominates and the growth time-scale agrees with RTI analytical solution |
| `comparison.png` | comparison | …delamination end-member, the vectors rotate, but remain orthogonal. For drip ping, many of the vectors are sheared so much that they are sub-parallel. |
| `triggereddripping.png` | triggereddripping | …rain can be measured in the modelled mixed case, compared to delamination, but it would be difficult to tell these two mechanisms apart in tomography: |
| `timescales.png` | timescales | …t the time-scale contrasts can be clearly captured by comparing the time it takes for the dense material to first reach a reference displacement (1L): |

## `shear-bands-with-dilatancy-modelled-with-underworld`

Shear Bands with Dilatancy modelled with Underworld · doi:10.59350/awc90-63186

| file | caption or alt text | context immediately before it |
|---|---|---|
| `ModelComparison.png` | *(none)* | …sizes="(min-width: 720px) 720px"> Three snapshots of the total shear strain for a model with low dilatancy (A-C) and a model with high dilatancy (D-F) |

## `underworld-and-docker-part-2`

Underworld and Docker (part 2) · doi:10.59350/4cqwc-rth67

| file | caption or alt text | context immediately before it |
|---|---|---|
| `Kitematic4.png` | Run Kitematic and search for Underworld2 | … time brings up an app-store-like list of available containers. Underworld2 is available through the Docker hub and so can be discovered by searching: |
| `Kitematic3.png` | Once Underworld is running, you will see a web-preview under the Home tab. In the windows alpha version this w | …a if you are using the latest build of a development branch because the container, once created, is an immutable snapshot of that version of the code. |
| `Kitematic2.png` | The web browser opens to the default IP address and port for the virtual machine running the underworld notebo | …on the web-preview it will launch your default browser with the appropriate IP address and port (you can change the port in the settings if you want). |
| `Kitematic6.png` | ‌‌ Launching a new terminal from the notebook home screen is a quick way into the virtual machine. | …session. This brings into a shell in the root directory of the virtual machine running underworld. Try running uname -a , it won't look very mac-like. |

## `underworld-and-docker-part-1`

Underworld and Docker (part 1) · doi:10.59350/y8762-pe280

| file | caption or alt text | context immediately before it |
|---|---|---|
| `dockeredNotebook.png` | Jupyter notebook running inside a docker container on OS X | …This allows us to use our native web browser to access the active docker notebook instance at http://localhost:8888/ (Windows & OS X users see below). |

