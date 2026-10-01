# THRESHER Single-Linkage Clustering — Concept Guide

> How THRESHER groups study genomes at one candidate phylothreshold: where the step sits in
> CORE, what it takes as input, the linkage rule and its graph formulation, and the
> pre-correction counts it produces.

## Where it sits in CORE

After hierarchical clustering partitions the study genomes into hierarchical clustering groups,
each group runs the candidate threshold scan. Single-linkage clustering is the first operation
at every candidate threshold in the scan, where it uses the candidate threshold as the cutoff to link
genomes, which are then mapped onto the group phylogeny. Phylogenetic correction follows and
adjusts the strain composition to restore monophyly if there is dicrepancy between the linked sets (SNP-only strains) and the the clades of the strains in the phylogeny.

## Input and implementation

Single-linkage clustering takes the study SNP matrix as input and is performed by
`thresher_input.R`.

At a given cutoff, the code retains the pairs of the group's SNP matrix whose `gsnp` value is at
or below the cutoff. Every genome appearing in those links belongs to a strain and is labeled
`clone` (clone is a strain with no less than 2 genomes under our definition). Genomes with no link at that cutoff, together with the group's overlimit genomes, are
labeled `singleton`. Linked sets are then merged into strains by iterating over the genomes. When none of a genome's linked partners carries a strain ID, the whole set receives a new one, and when any of them already does, the set takes the smallest ID already assigned. Singletons are
appended afterwards with IDs continuing from the last strain, so that every genome in the group
receives an assignment.

## The linkage rule

At each candidate phylothreshold $\tau^{\,k} \in \{\tau_{\text{floor}}^{\,k}, \ldots, \tau_{\text{ceil}}^{\,k}\}$
within hierarchical clustering group $H_k$, two retained genomes are linked when their SNP
distance does not exceed $\tau$,

$$g_i \sim_\tau g_j \iff d(g_i, g_j) \leq \tau, \qquad g_i, g_j \in HG'$$

defining a graph $\mathcal{G}_\tau = (HG', E_\tau)$ with edge set
$E_\tau = \{\, (g_i, g_j) : g_i \sim_\tau g_j,\ i \neq j \,\}$.

The single-linkage strains at $\tau$ are the connected components of $\mathcal{G}_\tau$, obtained
by iterative label propagation in which each genome is assigned the smallest identifier over its
transitive closure,

$$\text{strain}(g) = \min_{g' \in TC_\tau(g)} \text{id}(g').$$

## Clones, singletons, and pre-correction counts

A component of at least two genomes is a clone, and a genome with no link at $\tau$ is a singleton.
The overlimit genomes $HG_{\text{over}}$ set aside earlier in CORE are appended as singletons, so
that every study genome in the group receives an assignment. This yields the
pre-phylogeny-correction counts

$$n^{\text{pre}}_{\text{clone}} = \big|\{\, C : |C| \geq 2 \,\}\big|, \qquad
n^{\text{pre}}_{\text{single}} = \big|\{\, C : |C| = 1 \,\}\big|,$$

where each $C$ ranges over the strains assigned at $\tau$.