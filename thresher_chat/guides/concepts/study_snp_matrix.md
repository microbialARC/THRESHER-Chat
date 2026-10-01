# THRESHER Study SNP Matrix — Concept Guide

> The comprehensive all-versus-all SNP distance matrix: how it is computed, how pairwise
> distances are made symmetric, how alignment coverage sets each pair's quality label, and why
> the exhaustive comparison is worth its cost.

## What the study SNP matrix is

The study SNP matrix quantifies the genomic distance between every pair of study genomes. It is
generated at the PREP stage from all study genome assemblies provided by the user, by
`study_snp_matrix.R` or `study_snp_matrix_new.R` depending on the mode.

The matrix is a data frame with seven columns: `subject`, `query`, `snp`, `gsnp`,
`AlignedBases_reference`, `AlignedBases_query`, and `snp_quality`.

```r
sum_snp_df_unique <- data.frame(
  subject = unique_comparisons$subject,
  query   = unique_comparisons$query,
  snp     = rowMeans(cbind(sum_snp_dt$snp[forward_idx],  sum_snp_dt$snp[reverse_idx]),  na.rm = TRUE),
  gsnp    = rowMeans(cbind(sum_snp_dt$gsnp[forward_idx], sum_snp_dt$gsnp[reverse_idx]), na.rm = TRUE),
  AlignedBases_reference = AlignedBases_reference_entry,
  AlignedBases_query     = AlignedBases_query_entry,
  snp_quality            = snp_quality
)
```

## Pairwise comparison

Pairwise SNP distances are computed with the `dnadiff()` wrapper in MUMmer v4.0.0rc, taking
the gSNP count from the `dnadiff()` report as the raw distance between two genomes.

Let $SG = \{sg_1, sg_2, \ldots, sg_n\}$ be the set of $n$ study genomes. For each ordered pair
$(sg_i, sg_j)$ with $i \neq j$, MUMmer performs a whole-genome alignment with $sg_i$ as
reference and $sg_j$ as query, from which it reports the number of SNPs in the alignment and
the proportion of the genome covered by those alignments. Constructing the matrix therefore
requires all $n(n-1)$ directed comparisons, yielding an asymmetric raw distance matrix whose
entries are

$$SD_{\text{raw}}(sg_i, sg_j) = \text{gSNP}(sg_i \rightarrow sg_j), \qquad i \neq j$$

## Symmetric distance

Whole-genome alignment is not perfectly symmetric, as the assignment of reference and query
affects which regions align. The two directed distances for a pair are therefore averaged to
give a single symmetric distance:

$$SD_{\text{final}}(sg_i, sg_j) = \frac{SD_{\text{raw}}(sg_i, sg_j) + SD_{\text{raw}}(sg_j, sg_i)}{2}$$

## Alignment coverage and SNP quality

Each directed alignment also yields an alignment coverage, the fraction of the reference genome
covered by alignments to the query:

$$AC(sg_i, sg_j) = \frac{\text{aligned length of } sg_i \text{ against } sg_j}{\text{length of } sg_i}, \qquad i \neq j$$

A SNP distance is meaningful only when coverage is high enough that it reflects divergence
across the whole genome rather than a small aligned fraction, which would understate the true
difference between two assemblies. For each pair, both directed coverages are therefore
evaluated against a configurable alignment-coverage threshold (default 0.80). The pair is
labeled "good" quality only if both $AC(sg_i, sg_j)$ and $AC(sg_j, sg_i)$ meet or exceed the
threshold, and "poor" otherwise.

Poor-quality pairs are retained but flagged, and are highlighted in red font in the SNP-distance
heatmap accompanying the strain-composition visualization, so that low-coverage comparisons
remain visible to the user.

As a safeguard, if a study genome is of poor quality against all other study genomes in its
group, it is automatically treated as a singleton and excluded from the subsequent analysis of
that group. This is expected to be exceedingly rare, since THRESHER requires stringent assembly
quality at input. In practice, it arises when a genome of a different species is included, as
only such a genome would fail to align well against every other member of the group. The
singleton fallback therefore also acts as a check against this kind of input error.


## Cost and design rationale

Distances are computed in parallel across available cores, and redundant directional comparisons
are collapsed so that each unordered pair contributes a single averaged distance and a single
quality label.

All-versus-all pairwise comparison is computationally expensive, with complexity $O(n^2)$, and
is deliberately exhaustive because of the emphasis on accuracy. Its advantage is that each
distance is reference-free. The study SNP matrix is the input to single-linkage clustering, so
an accurate SNP value matters in the first place, and the complexity is worth the running time.