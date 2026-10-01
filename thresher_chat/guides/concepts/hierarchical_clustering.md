# THRESHER Hierarchical Clustering — Concept Guide

> How THRESHER decides whether a dataset can be analyzed as a whole or must be partitioned into
> hierarchical clustering groups, how the partition is chosen by silhouette width, how groups are
> reconciled with tree topology, and how overlimit genomes are set aside.

## What hierarchical clustering does and why

Hierarchical clustering runs at the PREP stage. A single phylothreshold is unlikely to be
appropriate across highly divergent genomic backgrounds, so THRESHER first determines whether the
dataset can be analyzed as a whole or should be partitioned into groups for independent, parallel
downstream analysis. When partitioning is warranted, genomes are divided by hierarchical
clustering at the partition that maximizes the mean silhouette score. The resulting groups are
shown on the core-gene tree colored by group (`plots/core_gene_tree_group.pdf`).

## The phylogeny it works on

The core-gene maximum-likelihood phylogeny is midpoint-rooted with `midpoint_root()` from the R
package phytools. For every internal node $v$, the descendant tip set $L(v)$ and the node's
support values are recorded.

## Deciding whether to partition

Hierarchical clustering is skipped only when both of the following conditions hold.

### Condition 1: a single typing group spans the tree

Let $T = \{t_1, \ldots, t_m\}$ be the typing labels assigned to the study genomes — Clonal Complex
for *S. aureus*, Sequence Type for *K. pneumoniae*, MLST Clade for *C. difficile* — after
excluding the `Unassigned` label, and let $G \subseteq SG$ be the genomes carrying an assigned
label. Condition 1 holds when exactly one typing label remains,

$$\big|\{\, t \in T : t \neq \text{Unassigned} \,\}\big| = 1,$$

and the smallest clade containing all labeled genomes is the root of the tree. In practice, the
smallest spanning clade is the node with the fewest descendants among all nodes whose descendant
tip set contains $G$. Condition 1 is satisfied only if that node is the root. Intuitively, this
holds when the dataset comprises a single genomic background occupying the entire tree, so no
partitioning into distinct backgrounds is needed.

### Condition 2: no discontinuity in the pairwise SNP distribution

Condition 1 alone is insufficient: a single typing label does not guarantee that the genomes form
one closely related group, because typing groups are not always monophyletic. Among the
*S. aureus* representative genomes, for example, CC1, CC5, and CC8 are paraphyletic, and a single
clonal complex can encompass multiple sequence types separated by thousands of SNPs. Treating
such a typing group as a single group would be inappropriate, so Condition 2 tests directly for
natural discontinuities in genomic distance rather than relying on typing alone.

Condition 2 is evaluated only when Condition 1 holds. The symmetric pairwise SNP distances among
the study genomes, $d_k = SD_{\text{final}}(sg_i, sg_j)$ over all $N = \binom{n}{2}$ pairs, are
summarized by kernel density estimation using `density()` from the R stats package, with a
Gaussian kernel and a fixed bandwidth $h = 1000$ bp. The kernel's variance,

$$\sigma_K^2 = \int t^2 K(t)\, dt,$$

equals 1 for the kernels used by `density()`, so the bandwidth corresponds to the standard
deviation of the kernel. The number of modes in the estimated density is one more than the number
of interior local minima, identified numerically as sign changes in the first difference of the
density. Condition 2 holds when the density is unimodal: a single mode indicates that the genomes
form one continuous cluster, whereas additional modes indicate natural discontinuities in
divergence that warrant separation.

### Outcome

When both conditions hold, hierarchical clustering is skipped and all study genomes are assigned
to a single group. Otherwise, the genomes are partitioned.

## Partitioning by silhouette score

A pairwise distance matrix $D$ is obtained from the core-gene ML phylogeny with
`cophenetic.phylo()` from the R package ape, where

$$D_{ij} = \sum_{e \in \text{path}(i, j)} \ell(e)$$

is the sum of branch lengths $\ell(e)$ along the path between tips $i$ and $j$. Hierarchical
clustering with complete linkage is applied to $D$ using `hclust()` from the R stats package. For
each candidate cluster count $k \in \{2, \ldots, n-1\}$, the genomes are cut into $k$ clusters
and the mean silhouette width is computed,

$$s(i) = \frac{b(i) - a(i)}{\max\{a(i),\, b(i)\}}, \qquad \bar{s}(k) = \frac{1}{n} \sum_{i=1}^{n} s(i)$$

where $a(i)$ is the mean distance from tip $i$ to the other tips of its cluster and $b(i)$ is the
lowest mean distance from $i$ to any other cluster. The dataset is partitioned at the cluster
count that maximizes the mean silhouette width across the tested range,

$$k^{\star} = \underset{k}{\arg\max}\ \bar{s}(k).$$

Because the single-group outcome is decided upstream by Conditions 1 and 2, the silhouette search
considers only genuine partitions ($k \geq 2$).


## Reconciling groups with tree topology

Cuts of a cophenetic tree do not necessarily correspond to monophyletic clades, so each resulting
group is reconciled with tree topology. If a group's genomes do not form an exact clade, the
smallest clade containing all of them is identified, and its additional descendant genomes are
absorbed into the group.


## Separating overlimit genomes

Finally, within each multi-genome group, any genome whose minimum pairwise SNP distance to the
remaining group members is at least the singleton threshold is separated from the group as a
singleton. The singleton threshold is a user-configurable parameter (default 100 bp) and is the
same threshold applied later in CORE. If no within-group pair falls below this threshold, the
entire group is treated as singletons.

## Implementation and outputs

Hierarchical clustering is run by the Snakemake rule `hierarchical_clustering`
(`rules/hierarchical_clustering.smk`), which calls `hierarchical_clustering.R` with the core-gene
tree (`iqtree/core_gene_tree/core_gene_tree.treefile`), the study SNP matrix
(`mummer4_study/study_snp_matrix.RDS`), and the MLST results (`mlst/summary/mlst_results.csv`) as
input and the singleton threshold as a parameter.

Within the script, genome names in the tree and MLST table are sanitized to a consistent format,
and each internal node's label is parsed into its SH-aLRT and bootstrap support, with the root
labeled `Root`. Condition 1 reads the broader MLST grouping column of the MLST results;
Condition 2 estimates the density of the `gsnp` column of the study SNP matrix. The silhouette
search runs from $k = 2$ to one less than the number of tips, and the final cut uses the $k$ with
the highest mean silhouette width. After topology reconciliation, any group left empty is
removed.

The rule writes two outputs to `thresher/input/`:

| Output | Contents |
|---|---|
| `hierarchical_clustering_groups.RDS` | One entry per group: `hc_group`, `genomes`, `all_overlimit` (whether the whole group was treated as singletons), `genomes_overlimit`, and the SH-aLRT and bootstrap support of the group's clade, or of the smallest clade covering it; single-genome groups carry `N/A` support |
| `hierarchical_clustering_groups_simplified.csv` | One row per genome: `genome`, `group`, and `overlimit` |