# THRESHER CladeBreaker — Concept Guide

> What CladeBreaker assumes, how it partitions a corrected clone's clade using matched public
> genomes, what happens when it is disabled, why it is independent of the public endpoint, and
> what its correct use depends on.
>
> See also the reference implementation: https://github.com/andriesfeder/cladebreaker

## What CladeBreaker is

CladeBreaker is enabled by default, which means the analysis carries the underlying assumption
that the study genomes represent hyperlocal strains that should not be grouped with public
genomes already deposited in public databases. Under that assumption, CladeBreaker serves as the
safeguard that constrains the size of corrected clones using the matched public genomes.

- **Enabled:** a strain clade is not permitted to grow to encompass a public genome, constraining
  each strain to the study population.
- **Disabled:** the public genomes remain in the phylogeny but impose no such constraint, so
  phylogenetic correction can expand a strain clade past them.

In either case, public genomes are never assigned to the same strain as study genomes.

## Clade breaking

Let $g$ denote a study genome ($g \in HG$) and $p$ a matched public genome
($p \in HP$). CladeBreaker acts on each corrected clone accepted during phylogenetic correction
whose clade contains at least one public genome. The public genomes appearing in that clade are

$$HP_C = L(v_C^{\star}) \cap HP.$$

SNP quality is taken from the alignment coverage of the study–public distances: a pairwise
distance is good when its coverage meets a user-configurable threshold $c$ (default 0.80) in
both alignment directions, and poor otherwise,

$$\text{good}(g, p) \iff \min\{\, AC(g, p),\ AC(p, g) \,\} \geq c.$$

**Two safeguards precede clade breaking.** First, a study genome whose distances to every other
study genome in the clade are poor is removed from the clade and reported as a singleton. This
is a safety check that rarely triggers, because genomes are required to pass the user's quality
check and filtering before performing the analysis. Let $HG_{\text{good}} \subseteq C^{\text{tree}}$ be
the study genomes that survive user's quality check, a public genome is retained for breaking only if it
has no poor alignment to any surviving study genome, yielding the valid public set

$$HP_{\text{valid}} = \{\, p \in HP_C : \text{good}(g, p) \text{ for every } g \in HG_{\text{good}} \,\}.$$

**The clade is then partitioned into its largest study-only subclades.** A node $u$ defines the
largest pure-study clade when its own clade contains no valid public genome, but its parent's
clade does,

$$L(u) \cap HP_{\text{valid}} = \emptyset \quad \text{and} \quad L(\mathrm{parent}(u)) \cap HP_{\text{valid}} \neq \emptyset.$$

The clade is treated as "pure-study" when it carries no valid public genome. The study genomes within
each such subclade constitute one separate strain, and any study genome not captured by a
"pure-study" subclade is reported as a singleton.


## Resolving overlaps

Because correction and clade breaking are applied per clone, two corrected strains can come to
share genomes. Overlaps are resolved by single-linkage merging, where among strains that share any
genome, the larger absorbs the smaller through a union of their genomes,
$S_{\text{large}} \leftarrow S_{\text{large}} \cup S_{\text{small}}$, and the pass is repeated
until all strains are disjoint, so that every study genome is assigned to exactly one strain.

The reconciled assignment gives the post-correction counts $n^{\text{post}}_{\text{clone}}$ and
$n^{\text{post}}_{\text{single}}$, together with the mean and median bootstrap support taken over
the clone strains.

## Disabling CladeBreaker

CladeBreaker should be disabled manually when the user has evidence that the matched public
genomes belong to the same strains as the study genomes. In that case no clade breaking is
performed, so the corrected clone keeps every study genome of the clade and drops only the public
genomes, returning $C^{\text{tree}}$.

Users can turn CladeBreaker off from the command-line tool. The CladeBreaker OFF mode re-runs strain identification with CladeBreaker disabled, allowing public genomes to cluster with study genomes. This avoids misidentification when the hyperlocal assumption does not hold, in which when matched public genomes belong to the same strains as the study genomes but CladeBreaker separates them.It reuses the SNP distances and phylogenies from the original run, re-executing only the phylothreshold scan and
endpoint selection.

## CladeBreaker and the public endpoint

The public endpoint and CladeBreaker both use the closely related public genomes retrieved by
WhatsGNU, but whether CladeBreaker is enabled does not affect the phylothreshold chosen under
the public endpoint. The public genomes sit in the phylogeny either way, and CladeBreaker only
controls whether they act as a barrier to the monophyly correction. The study-to-public SNP
distances are computed regardless of CladeBreaker status, so the endpoint can always be
evaluated.

In other words, with CladeBreaker enabled, a public genome blocks the monophyly correction from
expanding a strain clade past it, so strains stay confined to the study population. With it off,
the public genomes are still there but impose no constraint, and the correction can absorb the
originally separated study genomes into a strain clade. In either case, public genomes are not
considered the same strain as study genomes.

## Dependence on the public genome database

The quality and effect of CladeBreaker depend heavily on how comprehensive the public dataset
is. The more publicly available genomes of the species existed at the moment the WhatsGNU database
was built, the better, provided the sampling is not heavily biased. For example, the majority of
genomes collected at the same location over a short time interval could affect the performance of CladeBreaker.
For current available WhatsGNU databases, we checked and confirmed that the sampling is not heavily biased.

## Limitations and correct use

CladeBreaker is enabled by default and encodes a specific assumption, which is that the strains
constituted of study genomes are hyperlocal and should not be grouped with publicly available
genomes already deposited at GenBank. This assumption is reasonable in many surveillance
contexts, but it cannot be verified automatically. Isolates collected at one location are
sometimes deposited across separate BioProjects, and an investigator may not know whether
genomes related to their own have already been submitted. In such cases CladeBreaker cannot
itself determine whether a matched public genome should be excluded, or whether it should be
disabled for correcting strain compositions altogether. Correct use therefore depends on the
user's prior knowledge, and mishandling can lead to misidentification.

It might point to a real biological link that CladeBreaker, by design, would treat as a reason to keep the
strains apart. Public-genome matching can therefore both constrain strain expansion and point to
relationships that reach beyond a single study. Interpreting it correctly takes judgment that
the tool currently leaves to the user, and making this assessment automatic is a direction for
future work.

## Implementation

CladeBreaker is implemented in `thresher_input.R`. The flag is read from the Snakemake
parameters and passed to `get_thresher_input()` alongside the group phylogenies, the study and
study–public SNP matrices, and the threshold parameters:

```r
use_cladebreaker <- snakemake@params[["use_cladebreaker"]]
use_cladebreaker <- as.logical(use_cladebreaker)
```

Within the function, each corrected strain clade is handled in one of two situations. When the
clade contains no public genome — only discrepancy genomes — the clade's genomes are returned
directly as one clone with its bootstrap support. When public genomes were introduced, with or
without discrepancy genomes, behavior depends on the flag:

- **`use_cladebreaker = TRUE`:** the subtree of the strain clade is extracted and its internal
  nodes are traversed. Public genomes are identified by their `GCA_`/`GCF_` accession prefixes.
  Study genomes that are poor against all other study genomes in the clade are collected first,
  then public genomes carrying any poor alignment to a surviving study genome are marked invalid
  and ignored. A node is returned as a strain when its own subtree contains no valid public
  genome and its parent's subtree does, with the clade root returned directly when it has no
  parent. Study genomes not captured by any returned clade are appended as singletons with
  bootstrap support 0.
- **`use_cladebreaker = FALSE`:** no breaking is performed, and the strain is returned as the
  clade's genomes with the `GCA_`/`GCF_` entries removed.
  