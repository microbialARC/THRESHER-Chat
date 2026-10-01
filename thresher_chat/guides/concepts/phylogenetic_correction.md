# THRESHER Phylogenetic Correction — Concept Guide

> How THRESHER checks each clone from single-linkage clustering against the group phylogeny,
> when correction applies, how the minimum clade and the corrected composition are defined, how
> discrepancy is counted, how bootstrap support gates a correction, and what is recorded on each
> strain.

## What phylogenetic correction does and why

At each candidate phylothreshold, single-linkage clustering groups genomes by SNP distance alone.
Pairwise SNP distances can fail to link all genomes that share the most recent common ancestor
(MRCA), for example, under incomplete alignment coverage or recombination. Phylogenetic
correction therefore checks each clone against the group's tree topology and, where the tree
supports it, expands the clone to the full clade its genomes belong to.

## When it applies

Phylogenetic correction can be applied only in a hierarchical clustering group that meets the
criteria for a group reference-based phylogeny $T_k$: at least four genomes in total, study and
matched public combined ($|HG \cup HP| \geq 4$). Groups below that size have no group tree, and
their strains rest on single-linkage clustering alone.


## The minimum clade and the corrected composition

Let $L(v)$ be the set of tips descending from an internal node $v$, and $b(v)$ its bootstrap
support. The minimum clade for a clone $C$ is the smallest clade containing all of its genomes,

$$v_C^{\star} = \underset{v\,:\,C \subseteq L(v)}{\arg\min}\ \big| L(v) \big|,$$

and the clone's composition after phylogenetic correction is

$$C^{\text{tree}} = L(v_C^{\star}) \cap HG,$$

the study genomes descending from $v_C^{\star}$, with public genomes excluded.

## Discrepancy

The genomes the tree adds to a clone beyond single linkage form the discrepancy set

$$\Delta_C = C^{\text{tree}} \setminus C,$$

and the group's discrepancy at $\tau$ is the total over all clones whose minimum clade is broader
than their SNP cluster,

$$\delta = \sum_{C\,:\,\Delta_C \neq \emptyset} \big| \Delta_C \big|.$$

## The bootstrap gate

A phylogenetic correction is accepted only when the clone's clade is well supported,
$b(v_C^{\star}) \geq \beta_{\min}$, or when the clade is the root of the group tree,
$v_C^{\star} = \mathrm{root}(T_k)$. The support threshold $\beta_{\min}$ is set with
`--correction_bootstrap` (default 0). A clone whose correction is accepted has its membership
expanded to $C^{\text{tree}}$.


## What correction records on each strain

Every strain $S$ in the composition $\mathcal{S}(\tau)$ carries three attributes:

- **Category**: clone or singleton.
- **Correction flag**: whether its composition was modified by phylogenetic correction or
  CladeBreaker, rather than set by SNP single linkage alone.
- **Bootstrap support** $b(S)$: the support of the strain's clade for a clone, and zero for a
  singleton.

When no group phylogeny is available, the correction flag and bootstrap support are recorded as
missing.

## Implementation

Phylogenetic correction is implemented in `thresher_input.R` and runs only when the group's tree
file exists. Within each candidate phylothreshold:

1. **Initialization.** Every strain starts with an empty correction flag and bootstrap support;
   singletons receive support 0.
2. **Minimum clade.** For each clone, in order of strain ID, the script collects the tree's
   internal-node summaries whose descendant genomes include every genome of the clone and keeps
   the one with the fewest genomes. It records the clone's SNP-only genomes, the clade's genomes,
   the clade's bootstrap support, and its node.
3. **Discrepancy.** Clones whose clade differs from their SNP-only membership are retained, and
   the discrepancy is summed over them as the number of study genomes in the clade beyond the
   SNP cluster, with public genomes (`GCA_`/`GCF_`) excluded. The discrepancy is counted over all
   such clones before the bootstrap gate is applied.
4. **Bootstrap gate.** The retained clones are filtered to those whose clade support is at least
   `correction_bootstrap` or whose clade is the root (labeled `Root`). The number that pass is
   recorded as `clones_corrected`.
5. **Hand-off to CladeBreaker.** Each accepted clade with no public genome is returned directly
   as one clone with its bootstrap support. A clade containing public genomes is passed to
   CladeBreaker when it is enabled; when it is disabled, the clade's study genomes are returned as
   one clone with the public genomes removed.

After corrections are applied and overlapping strains are merged, every corrected genome is
flagged `correction = TRUE`, any remaining empty flag is set to `FALSE`, and strains without
a support value take the bootstrap support of their original SNP clade, or 0 when none is found.