# Figures that went missing, and what became of them

Sixteen image references across eight posts point at a server that is gone. The
captions survived, because they were text in the post body rather than pixels on
a host, and they are what made most of these recognisable.

## The pattern

**Every loss is an image still addressed to `underworldcode.ghost.io`** — the
hosted Ghost CDN used before the site moved to its own droplet in 2020. Fifteen
of the sixteen are on that host; the sixteenth is a stale
`www.underworldcode.org/content/images/2019/09/` path from the same era. The
mirror of `www.underworldcode.org` taken in Stage 0 is otherwise **complete**:
every other image in the corpus was captured.

That also explains why nothing could be recovered from the Internet Archive. The
Archive holds pages, and the pages were fine; it was the images' *host* that
vanished, and it was never crawled.

Counting by reference, not by filename, matters here — several posts show the
same picture twice under two different URLs. An earlier pass counted by
basename and so mistook three surviving figures for lost ones.

## Recovered

Six, from the author's own copies. Staged in `recovered-figures/<slug>/`, named
as the article will reference them.

| post | file | caption | source |
|---|---|---|---|
| `craton-formation-and-the-onset-of-plate-tectonics` | `CratonFormationMovieFrames-2.png` | Snapshots from the movie below that show the initial failure of the cold lid after the heat-pipe mode stops (A), followed by repeated sloughing off of the cold boundary layer in (B) and a slow approach to plate tectonics | Beall et al., *Indestructible Cratons*, publicity figures |
| `alaska-moho-model-reproducible-research-with-containers` | `MohoSurfaceGradient-ClusteredGrids.png` | *(none)* | Miller & Moresi, SRL 2018, notebook figures |
| `getting-started-60-seconds-to-underworld` | `Docker_hello_world.png` | Thanks Docker ! | local original |
| `getting-started-60-seconds-to-underworld` | `timer_60_seconds.png` | Hardly seems fair… | local original |
| `underworld-and-docker-part-1` | `dockeredNotebook.png` | Jupyter notebook running inside a docker container on OS X | local original |
| `underworld-and-docker-part-2` | `Kitematic3.png` | Once Underworld is running, you will see a web-preview under the Home tab. In the windows alpha version this will be blank, but clicking on it will open the correct container in your browser. | local original, confirmed against the caption |

## Not lost after all

Three. The post referenced the dead copy in one place and a re-uploaded copy in
another, so the picture itself is already in the mirror. Point the conversion at
the live path.

| post | file | use instead |
|---|---|---|
| `craton-formation-and-the-onset-of-plate-tectonics` | `CratonsLithosphere.png` | `assets/content/images/2020/11/CratonsLithosphere.png` |
| `untitled` (Modelling Drips and Delamination) | `schematic-1.png` | `assets/content/images/2020/08/schematic-1.png` |
| `shear-bands-with-dilatancy-modelled-with-underworld` | `ModelComparison.png` | `assets/content/images/2020/08/ModelComparison.png` |

## Still gone

Seven. Searched for by name across Dropbox and the whole home directory: no
copy exists locally, and the Archive never held them.

| post | file | caption or context |
|---|---|---|
| `viscoelasticity` | `stressHistory_dAlpha-1.png` | "Viscoelastic stress history term for different relaxation times" — follows the passage where a viscoelastic material shears at constant rate until $t = 4$, then the shearing velocity goes to zero and the stress decays |
| `untitled` | `comparison.png` | no caption; follows "…the vectors rotate, but remain orthogonal. For dripping, many of the vectors are sheared so much that they are sub-parallel." |
| `untitled` | `triggereddripping.png` | no caption; follows "…strain can be measured in the modelled mixed case, compared to delamination, but it would be difficult to tell these two mechanisms apart in tomography" |
| `untitled` | `timescales.png` | no caption; follows "…the time-scale contrasts can be clearly captured by comparing the time it takes for the dense material to first reach a reference displacement (1L)" |
| `underworld-and-docker-part-2` | `Kitematic2.png` | "The web browser opens to the default IP address and port for the virtual machine running the underworld notebooks." |
| `underworld-and-docker-part-2` | `Kitematic4.png` | "Run Kitematic and search for Underworld2" |
| `underworld-and-docker-part-2` | `Kitematic6.png` | "Launching a new terminal from the notebook home screen is a quick way into the virtual machine." (`Kitematic6i.png` and `Kitematic6ii.png` are *different* figures, still live — 6i is the Volumes settings pane) |

### What to do about the seven

The three Kitematic screenshots are of software Docker discontinued. Remaking
them would produce a picture of 2026, not of what the post described, and a
short note saying the screenshot is lost is truer than a reconstruction.

The four science figures are worth a look in the paper directories before
giving up. `BeallEtAl-DripDelam/DripDelamPaper/DripDelam/img/` holds
`Vectors_600_M25.pdf`, `Vectors_750_M35.pdf`, `Vectors_800_M26.pdf` (which
match what `comparison.png` is described as showing) and `tB_compare.pdf`,
`tauGrowth.pdf` (candidates for `timescales.png`) — near relations rather than
the same picture, so this is a judgement for the author, not a substitution to
make automatically.

## The lesson, which is now written into the contribution guide

These were lost because the article referred to an image on someone else's
server instead of carrying it. Figures are committed alongside their articles
for exactly this reason, including the screenshots — whose only other copy is
the gitignored `assets/` mirror.
