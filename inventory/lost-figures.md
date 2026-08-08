# The figures that went missing, and where they were found

Sixteen image references across eight posts pointed at a server that is gone.
**All sixteen are now recovered.** This file records what happened, because the
route matters more than the outcome for anyone doing the same again.

## The pattern

Every broken reference was an image still addressed to
`underworldcode.ghost.io` — the hosted Ghost CDN used before the site moved to
its own droplet in 2020. Fifteen were on that host; the sixteenth was a stale
`www.underworldcode.org/content/images/2019/09/` path from the same era. The
Stage 0 mirror of `www.underworldcode.org` is otherwise complete.

That is also why the Internet Archive was no help. The Archive holds pages, and
the pages were fine; it was the images' *host* that vanished, and it was never
crawled.

Count by reference, not by filename. Several posts show the same picture twice
under two different URLs, and an earlier pass counted basenames — which made
three surviving figures look lost while they sat in the mirror under a
different year directory.

## Where they came from

### Three were never lost

The post referenced a dead copy in one place and a re-uploaded copy in another,
so the picture is already in the mirror. Point the conversion at the live path.

| post | file | use instead |
|---|---|---|
| `craton-formation-and-the-onset-of-plate-tectonics` | `CratonsLithosphere.png` | `assets/content/images/2020/11/CratonsLithosphere.png` |
| `untitled` (Modelling Drips and Delamination) | `schematic-1.png` | `assets/content/images/2020/08/schematic-1.png` |
| `shear-bands-with-dilatancy-modelled-with-underworld` | `ModelComparison.png` | `assets/content/images/2020/08/ModelComparison.png` |

### Six from the author's own copies

| post | file | source |
|---|---|---|
| `craton-formation-and-the-onset-of-plate-tectonics` | `CratonFormationMovieFrames-2.png` | Beall et al., *Indestructible Cratons*, publicity figures |
| `alaska-moho-model-reproducible-research-with-containers` | `MohoSurfaceGradient-ClusteredGrids.png` | Miller & Moresi, SRL 2018, notebook figures |
| `getting-started-60-seconds-to-underworld` | `Docker_hello_world.png`, `timer_60_seconds.png` | local originals |
| `underworld-and-docker-part-1` | `dockeredNotebook.png` | local original |
| `underworld-and-docker-part-2` | `Kitematic3.png` | local original |

### Seven from the pre-Ghost site

`github.com/underworldcode/underworldcode.github.io.retired` — the Jekyll site
that preceded Ghost. These posts *predate Ghost entirely*, so the figures were
never on the CDN that died; they were committed alongside their posts, in the
repository, the whole time.

| post | file | in the retired repo |
|---|---|---|
| `viscoelasticity` | `stressHistory_dAlpha-1.png` | `images/posts/ViscoelasticGraphs/stressHistory_dAlpha.png` |
| `untitled` | `comparison.png` | `images/posts/DripDelamination/comparison.png` |
| `untitled` | `triggereddripping.png` | `images/posts/DripDelamination/triggereddripping.png` |
| `untitled` | `timescales.png` | `images/posts/DripDelamination/timescales.png` |
| `underworld-and-docker-part-2` | `Kitematic2.png` | `images/posts/Kitematic/Kitematic2.png` |
| `underworld-and-docker-part-2` | `Kitematic4.png` | `images/posts/Kitematic/Kitematic4.png` |
| `underworld-and-docker-part-2` | `Kitematic6.png` | `images/posts/Kitematic/`**`Kitematic7.png`** |

**The last row is the one to be careful about.** Ghost's `Kitematic6.png` is the
retired site's `Kitematic7.png` — the import renumbered them, and the retired
site's own `Kitematic5.png`/`Kitematic6.png` are a *different* figure (the pair
showing volume mounting, which survived the import as `Kitematic6i.png` and
`Kitematic6ii.png` and is live today). The mapping was made on the caption —
"launching a new terminal from the notebook home screen" — and confirmed by
looking at the image, not by matching the number.

## A bonus: captions Ghost dropped

Three of the delamination figures lost their captions in the Ghost import. The
retired site still has them, and they should be restored with the images:

| file | caption |
|---|---|
| `comparison.png` | Deformation of drip and delamination end-members (from Beall et al. 2017). |
| `triggereddripping.png` | Comparison of 'triggered dripping' and delamination models (from Beall et al. 2017). |
| `timescales.png` | Time-scales for various instability mechanisms (from Beall et al. 2017). |

## Worth knowing for the backfill

The retired repository holds the **original markdown source** of 26 posts from
September 2015 to October 2018, with their figures. For that era it plays the
same role the `underworld3` repository plays for the recent notes: the author's
intent before an import mangled it. Converting those posts should start there
and use the Ghost HTML as the check, not the other way round.

## The lesson, which is in the contribution guide

Sixteen figures were at risk because the articles referred to images on someone
else's server instead of carrying them. The ones that were never at risk are
precisely the ones committed next to their post. That is why figures are
committed alongside articles here, screenshots included.
