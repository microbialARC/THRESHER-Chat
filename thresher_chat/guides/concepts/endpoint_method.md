# THRESHER Endpoint Methods — Concept Guide

> How THRESHER selects one final phylothreshold for each hierarchical clustering group using the four
> endpoint methods (plateau, peak, discrepancy, public), the hypothesis behind each, how each is
> read from THRESHER's plots, how the result is checked, and how the methods are implemented.

## What an endpoint method does

A hierarchical clustering group contributes its strain composition to the dataset-wide result
only after a single phylothreshold is chosen from its intermediate database $\mathcal{D}_k$, the
record of the group's strain composition at every candidate phylothreshold. An endpoint method
makes this choice, wher**e it analyzes $\mathcal{D}_k$ and returns the group's final phylothreshold
together with its composition $\mathcal{S}(\tau)$.

Four endpoint methods are currently supported. Each reflects a different hypothesis about what
distinguishes one strain from another and, with it, takes a different position on the
sensitivity–specificity trade-off in our simulation. The methods run independently.

| Endpoint | Selects the phylothreshold at which |
|---|---|
| Plateau | The strain composition stays unchanged over a contiguous run of candidate phylothresholds |
| Peak | The number of clones is maximized |
| Discrepancy | The discrepancy is minimized beyond its initial peak |
| Public | The closest distance where a clone in the group first becomes able to absorb a public genome |

The composition at a group's selected phylothreshold is written out as a strain table in which
each strain receives the identifier `<group>_<index>` and is listed against its constituent
genomes. Concatenating these tables over all groups yields the final dataset-wide strain
composition.

**Reading the criteria.** Plateau, peak, and discrepancy can be read on the Multi-SNP-Threshold
Plot (MSTP), whose x-axis shows the candidate phylothresholds increasing from left to right,
bounded by $\tau_{\text{floor}}$ and $\tau_{\text{ceil}}$, and whose three curves track the clone
count (light blue), the singleton count (grey), and the discrepancy (red). The public endpoint is
instead read from the group's phylogeny and its study–public SNP submatrix.

## Plateau

Let $\mathcal{S}(\tau)$ be the strain composition of a group at candidate phylothreshold $\tau$.
For each $\tau$ in the scanned range, an indicator records whether the composition is unchanged
from the preceding phylothreshold,

$$e(\tau) = \mathbb{1}\big[\, \mathcal{S}(\tau) = \mathcal{S}(\tau - 1) \,\big], \qquad \tau = \tau_{\text{floor}}^{\,k}, \ldots, \tau_{\text{ceil}}^{\,k}$$

where the two compositions are compared as partitions of the study genomes $HG$, independent of
strain labeling or ordering.

A plateau is a run of consecutive phylothresholds over which the composition does not change: an
integer interval $[a, b]$ with $e(\tau) = 1$ for all $\tau \in [a, b]$, of length $b - a + 1$.
With $L$ the required plateau length (default 15), the plateau endpoint is the start of the
earliest run that reaches this length,

$$\tau_{\text{plateau}} = \min\big\{\, a : e(\tau) = 1 \text{ for all } \tau \in [a, b],\ b - a > L \,\big\}$$

and the group's reported composition is $\mathcal{S}(\tau_{\text{plateau}})$, since the
composition is shared across the run. On the MSTP, the plateau is the shaded stretch from $a$ to
$b$, and $\tau_{\text{plateau}}$ sits at its start.

**Outcomes reported as labels rather than phylothresholds:**

- **`Singletons`**: the group was resolved without a scan, or its smallest retained SNP distance
  already exceeds the singleton threshold $\tau_{\text{single}}$ (default 100), so it contains no
  clones. The label is also used when a qualifying plateau exists but its shared composition
  consists entirely of singletons, as no clone is present to anchor a phylothreshold.
- **`No Plateau Found`**: no run reaches length $L$; the composition at the largest tested
  phylothreshold is reported.

The selected or labeled outcome for every group is recorded in the per-group plateau table.

## Peak

Let $n^{\text{post}}_{\text{clone}}(\tau)$ be the number of clones after phylogenetic correction
at candidate phylothreshold $\tau$. The peak endpoint is the first phylothreshold attaining the
maximum clone count,

$$\tau_{\text{peak}} = \min\Big\{\, \tau : n^{\text{post}}_{\text{clone}}(\tau) = \max_{\tau'}\, n^{\text{post}}_{\text{clone}}(\tau') \,\Big\}$$

and the group's reported composition is $\mathcal{S}(\tau_{\text{peak}})$. When several
candidates tie at the maximum, the smallest is taken. On the MSTP, $\tau_{\text{peak}}$ is the top
of the clone-count curve.

When the group forms no clone at any tested phylothreshold, because it was resolved without a
scan, or its composition consists entirely of singletons throughout the scan — the clone count is
zero, no peak phylothreshold is defined, and the all-singleton composition is reported.

The selected phylothreshold for every group is recorded in the per-group peak table.


## Discrepancy

Let $\delta(\tau)$ be the discrepancy at candidate phylothreshold $\tau$, computed before
phylogenetic correction, and $\tau_{\text{single}}$ the singleton threshold (default 100 SNPs).
This endpoint places the phylothreshold where the phylogeny and the SNP distances agree most
closely, that is, where $\delta$ is minimized. Because $\delta$ can also be low at very conserved
phylothresholds, where strains are still too finely split for any disagreement to appear, the
minimum is taken only after the initial discrepancy peak. The method has two phases.

**Phase 1: locate the discrepancy peak** within the conserved range, at phylothresholds no
greater than the singleton threshold:

$$\tau_{\delta}^{\ast} = \min\Big\{\, \tau \leq \tau_{\text{single}} : \delta(\tau) = \max_{\tau' \leq \tau_{\text{single}}} \delta(\tau') \,\Big\}$$

**Phase 2: take the minimum after the peak:**

$$\tau_{\text{disc}} = \min\Big\{\, \tau > \tau_{\delta}^{\ast} : \delta(\tau) = \min_{\tau' > \tau_{\delta}^{\ast}} \delta(\tau') \,\Big\}$$

and the group's reported composition is $\mathcal{S}(\tau_{\text{disc}})$. In both phases, ties
resolve to the smallest qualifying phylothreshold: the peak is the most conserved phylothreshold
with the maximum discrepancy, and the endpoint is the smallest post-peak phylothreshold attaining
the minimum, so that strains are no larger than the concordance minimum requires. If every
$\delta$ beyond $\tau_{\text{single}}$ exceeds $\delta(\tau_{\delta}^{\ast})$, the search instead
returns the candidate with the smallest $\delta$, even if it precedes $\tau_{\delta}^{\ast}$. Both
quantities can be read directly from the discrepancy curve on the MSTP.

**Why two phases.** At conserved phylothresholds, single-linkage clustering on SNP distances
groups genomes that the phylogeny does not resolve as monophyletic. Reconciling the two requires
merging these genomes into a common clade, which produces high discrepancy that falls quickly as
the phylothreshold rises and the corrected strains regain monophyly. Across many groups in the
published datasets, this peak occurs at highly conserved phylothresholds. Low discrepancy also
appears sporadically before the peak, when strains are still split too finely for the
disagreement to have emerged. The endpoint is therefore drawn only from the post-peak descent,
where the minimum reflects genuine agreement between the phylogeny and the SNP distances.

When the group's smallest study–study SNP distance already exceeds the singleton threshold, no
range is scanned and the group is reported with its all-singleton composition. Otherwise, the
selected phylothreshold is recorded in the per-group discrepancy table.

## Public

Let $SP_{\text{final}}(g_i, p_j)$ be the symmetric SNP distance between a study genome
$g_i \in HG$ and one of its matched public genomes $p_j \in HP_i$. Only good-quality study–public
distances are used: a good-quality distance gives a reliable estimate of the genetic relatedness
between a study genome and its public match, whereas a distance from a poor-quality alignment
does not correspond to a biologically meaningful phylothreshold and is excluded.

Over the good-quality pairs, let

$$d_{\text{public}} = \min_{g_i \in HG,\ p_j \in HP_i} SP_{\text{final}}(g_i, p_j)$$

be the smallest study-to-public distance in the group. The public endpoint is this distance,
rounded to the nearest integer and constrained to the scanned range,

$$\tau_{\text{public}} = \min\!\big( \max\!\big( d_{\text{public}},\ \tau_{\text{low}} \big),\ \tau_{\text{ceil}} \big)$$

where $\tau_{\text{low}}$ is the smallest phylothreshold tested in the group and
$\tau_{\text{ceil}}$ (default 500) the scan ceiling. The group's reported composition is
$\mathcal{S}(\tau_{\text{public}})$, or the composition at the largest tested phylothreshold not
exceeding $\tau_{\text{public}}$ when no candidate equals it exactly.

**Rationale.** The smallest study-to-public distance marks the point at which the group's strains
stop being exclusive to the study. Below it, no public genome links to a study genome; at
$\tau_{\text{public}}$, a public genome first becomes eligible to be merged with a study strain.
Setting the phylothreshold here uses the boundary against publicly deposited, same-species
genomes as the limit of strain composition, and complements CladeBreaker's assumption that study
strains are hyperlocal and should not share a strain with public genomes. Because strain
composition is determined jointly by SNP distance and tree topology, the phylothreshold at which
a strain first incorporates a public genome need not coincide with $d_{\text{public}}$ itself;
the public endpoint locates the SNP distance at which that incorporation becomes possible.

**Edge cases.** The phylothreshold is capped at $\tau_{\text{ceil}}$, so a distant nearest public
genome cannot push it past the scan. When the group's smallest study–study SNP distance already
exceeds the singleton threshold, its phylothreshold is reported directly. A group with no clone at
any tested phylothreshold has no public boundary to locate and is reported with its all-singleton
composition.

**Reading the criterion.** In the group phylogeny, study tips are blue and public tips brown,
labeled $g$ and $p$. In the SNP submatrix, only study–study cells are shaded by SNP distance
(darker for larger distances); study–public cells are grey. Computed pairs are annotated with
$SP_{\text{final}}$, the label colored by SNP quality (green, good; red, poor), and pairs neither
required nor computed are left blank. Poor-quality study–public pairs are excluded when
determining $\tau_{\text{public}}$.

The selected phylothreshold for every group is recorded in the per-group public table.

## Endpoint quality control

Each endpoint reflects a different hypothesis about what separates one strain from another, but
all pursue the same balance: a phylothreshold that is neither too sensitive, merging distinct
strains, nor too specific, splitting a single strain. THRESHER reaches this partition in two
layers. Hierarchical clustering first partitions all genomes into groups of related genomic
backgrounds; within each group, the endpoint then defines the strain composition at its selected
phylothreshold. To make both layers visually inspectable, THRESHER produces a quality-control plot
that places each pair of identified strains in two distance spaces at once, so that separation
between strains can be judged directly rather than inferred from the phylothreshold alone.

For an endpoint's final strain composition, every pair of strains is compared by two
between-strain distances, each the mean over all cross-strain genome pairs. For strains $S_a$ and
$S_b$, the average SNP distance is

$$\bar{D}^{\text{SNP}}(S_a, S_b) = \frac{1}{|S_a|\,|S_b|} \sum_{g \in S_a} \sum_{h \in S_b} d(g, h)$$

where $d(g, h)$ is the symmetric SNP distance, and the average phylogenetic distance is

$$\bar{D}^{\text{phylo}}(S_a, S_b) = \frac{1}{|S_a|\,|S_b|} \sum_{g \in S_a} \sum_{h \in S_b} D_T(g, h)$$

where $D_T(g, h)$ is the sum of branch lengths on the path between $g$ and $h$ in the
midpoint-rooted core-gene phylogeny.

The two distances are plotted against each other, one point per strain pair, colored by whether
the pair lies within the same hierarchical clustering group, with the marginal density of each
distance alongside. A well-resolved dataset shows a characteristic pattern:

- **Across-group pairs** (the population-structure layer) sit at large distances, well separated
  from within-group pairs, confirming that hierarchical clustering placed divergent backgrounds in
  different groups.
- **Within-group pairs** (the endpoint layer) are close, since they share a background, but not
  arbitrarily close. Within-group pairs clustering near zero distance flag that the endpoint has
  merged genomes that should have been kept in separate strains.

The plot and its underlying table are generated for all four endpoints, as
`thresher/output/QC/{endpoint}_qc_plot.pdf` and `thresher/output/QC/{endpoint}_qc_table.csv`.
When an endpoint resolves the entire dataset into a single strain, no between-strain pair exists,
and a message is reported in place of the plot.

## Implementation

Each endpoint has its own Snakemake rule — `thresher_plateau.smk`, `thresher_peak.smk`,
`thresher_discrepancy.smk`, `thresher_public.smk` — and its own function: `get_plateau_strains()`,
`get_peak_strains()`, `get_discrepancy_strains()`, and `get_public_strains()`. All four read
`thresher/input/thresher_input.RDS` and the hierarchical clustering groups and process groups in
parallel with `mclapply`. The plateau function also takes the plateau length and singleton
threshold, the discrepancy function the singleton threshold, and the public function the
study–public SNP matrix and the threshold ceiling.

| Endpoint | How the function selects the phylothreshold | Singleton handling |
|---|---|---|
| Plateau | Builds the 0/1 array of $e(\tau)$, run-length encodes it with `rle()`, and takes the first run of ones at least `plateau_length` long; then checks the compositions across the plateau and reports `Singletons` if all are singletons | `Singletons` when the group has one record with no cutoff and only single-genome compositions, or one record whose cutoff is at or above the singleton threshold |
| Peak | Takes the first cutoff with the maximum `after_correction_clones` | `NA` when any of the three singleton conditions holds |
| Discrepancy | Takes the first cutoff with the maximum discrepancy among cutoffs at or below the singleton threshold, then the first cutoff with the minimum discrepancy among cutoffs above it | `Singletons` when the group has a single record |
| Public | Keeps good-quality study–public distances for the group's genomes, rounds the minimum, raises it to the smallest tested cutoff if below, and caps it at the ceiling; uses the ceiling when no good-quality distance remains; for a single-record group, uses that record's cutoff; with no exact match, uses the largest tested cutoff below the value | `NA` when the group has one record with no cutoff and only single-genome compositions |

The three singleton conditions shared across the functions are: the group has a single record,
its cutoff is missing, and every strain composition holds one genome. Plateau and public require
all three; peak treats any one as sufficient.

Each function writes two tables: `{endpoint}_strains.csv` (`strain_id`, `genome`) and
`group_{endpoint}.csv` (`group` and the selected phylothreshold, with `plateau_length` added for
plateau) — and saves an R object containing the strain table, the per-group table, and the
composition details for every group.