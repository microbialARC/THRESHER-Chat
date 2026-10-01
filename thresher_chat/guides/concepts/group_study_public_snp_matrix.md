# THRESHER Group Study–Public SNP Matrix — Concept Guide

> How THRESHER measures the distance between study genomes and their closest publicly
> available relatives: which pairs are compared, how the distances and quality labels are
> produced, how the group submatrix is assembled, and which parts of CORE depend on it.

## What it is

The study–public SNP distances exist at two levels.

At the **PREP** stage, the study assemblies and metadata from INPUT are used to query the
WhatsGNU database and retrieve the public genomes most closely related to each study genome.
Pairwise symmetric SNP distances between study genomes and those matched public genomes are
then computed. The resulting table carries the same seven columns as the comprehensive study
SNP matrix — `subject`, `query`, `snp`, `gsnp`, `AlignedBases_reference`, `AlignedBases_query`,
`snp_quality`.

At the **CORE** stage, a group-specific Study-Public SNP submatrix is assembled for each
hierarchical clustering group from the corresponding block of the comprehensive study SNP
matrix together with the study–public distances.


## Which pairs are compared

Let $HG = \{g_1, \ldots, g_n\}$ be the study genomes assigned to group $H_k$ and
$HP = \{p_1, \ldots, p_m\}$ the closely related public genomes matched to them, so that
$HG \cup HP$ is the combined set of study and public genomes in the group.

Study genomes are not compared against every public genome in the group. Each study genome
$g_i$ is compared only with its own closely related public genomes, the subset
$HP_i \subseteq HP$ identified for $g_i$ by WhatsGNU, so that

$$HP = \bigcup_{i=1}^{n} HP_i.$$

Distances between study genomes and unrelated public genomes, and all public–public pairs, are
neither required by the algorithm nor computed. The study–public block is therefore sparse.

## Distance and coverage

For each matched pair — a study genome $g_i$ and one of its public genomes $p_j \in HP_i$ — the
distance is obtained by the same `dnadiff` (MUMmer v4.0.0rc1) procedure used for the study
matrix, aligning the two genomes in both directions and averaging:

$$SP_{\text{raw}}(g_i, p_j) = \text{SNP}(g_i \rightarrow p_j), \qquad p_j \in HP_i$$

$$SP_{\text{final}}(g_i, p_j) = \frac{SP_{\text{raw}}(g_i, p_j) + SP_{\text{raw}}(p_j, g_i)}{2}$$

$$AC(g_i, p_j) = \frac{\text{aligned length of } g_i \text{ against } p_j}{\text{length of } g_i}, \qquad p_j \in HP_i$$

A study–public distance is flagged good when the alignment coverage in both directions meets a
user-configurable threshold (default 80%), and poor otherwise.

## Assembling the group submatrix

Within a group, CORE builds two inputs in parallel: a reference-based maximum-likelihood
phylogeny and the Study-Public SNP matrix.

**Phylogeny.** When the group contains at least four genomes in total ($|HG \cup HP| \geq 4$), a
multiple-sequence alignment is generated with Snippy v4.6.0 from all study genomes and their
matched public genomes, using the study assembly with the highest N50 as the reference. IQ-TREE
v2.3.6 then infers a reference-based maximum-likelihood phylogeny from this alignment, under the
same substitution model and branch-support settings as the core-gene ML phylogeny. Groups with
fewer than four genomes are not given a tree.

**Matrix.** Let $d(g_i, g_j) = SD_{\text{final}}(g_i, g_j)$ be the symmetric SNP distance between
two study genomes, averaged over both alignment directions and taken directly from the
comprehensive study SNP matrix. Collecting the matched pairs into

$$E_{\text{SP}} = \{\, (g_i, p_j) : g_i \in HG,\ p_j \in HP_i \,\},$$

the Study-Public SNP matrix $\mathbf{M}_k$ over the combined genome set
$\Omega_k = HG \cup HP$ is constituted from the extracted study block
$[\, d(g_i, g_j) \,]_{g_i, g_j \in HG}$ together with the study–public block
$[\, SP_{\text{final}}(g_i, p_j) \,]_{(g_i, p_j) \in E_{\text{SP}}}$. Pairs outside
$E_{\text{SP}}$ are not computed, leaving the study–public block sparse.


## What depends on these distances

The study–public distances matter for two parts of CORE.

**CladeBreaker.** CladeBreaker constrains the size of corrected clones using the matched public
genomes, under the assumption that study genomes represent hyperlocal strains that should not be
grouped with genomes already deposited in public databases. The public genomes appearing in a
clone's clade are $HP_C = L(v_C^{\star}) \cap HP$. SNP quality is taken from the alignment
coverage above: a pairwise distance is good when its coverage meets the user-configurable
threshold $c$ (default 0.80) in both alignment directions, and poor otherwise,

$$\text{good}(g, p) \iff \min\{\, AC(g, p),\ AC(p, g) \,\} \geq c.$$

The flag is what lets CladeBreaker discard unreliable public genomes when correcting strain
composition.

**Public endpoint.** Over the good-quality study–public pairs, let

$$d_{\text{public}} = \min_{g_i \in HG,\ p_j \in HP_i} SP_{\text{final}}(g_i, p_j)$$

be the smallest study-to-public distance in the group. The public endpoint is this distance,
rounded to the nearest integer and constrained to the scanned range,

$$\tau_{\text{public}} = \min\!\big( \max\!\big( d_{\text{public}},\ \tau_{\text{low}} \big),\ \tau_{\text{ceil}} \big).$$

## Implementation

The matrix is produced by the Snakemake rule `public_snp_matrix` (script `public_snp_matrix.R`)
or, in New Full mode, `public_snp_matrix_new_full` (script `public_snp_matrix_new_full.R`), which
merges the new distances with the matrix of the prior run. Both write to
`mummer4_public/public_snp_matrix.RDS`; New Full keeps the same output name so its results stay
compatible with subsequent New Full runs.

Both rules take the `dnadiff` reports and the list of actually downloaded public genomes as
input, and the alignment-coverage threshold as a parameter. Public genomes that were requested
but not downloaded are excluded, a study genome's own deposited copy is removed from its
WhatsGNU match list by accession, and redundant directional comparisons are collapsed in
parallel so that each unordered pair contributes a single averaged distance and a single quality
label.