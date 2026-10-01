# THRESHER Full Pipeline Mode — Guide

> Explains what Full Pipeline mode does, when to use it, what it requires as input, what it
> produces, and which parameters change the result. Rationale, decision logic, and
> interpretation only; the complete option list, metadata specification, and output file
> inventory are in `docs/usage_full_pipeline.md` in the THRESHER repository.

Command: `thresher full`

## What Full Pipeline mode does

Full Pipeline is THRESHER's end-to-end mode and the only one that starts from genome
assemblies and metadata alone. A single run executes all four stages (INPUT, PREP, CORE, and, when
enabled, EPI) and produces strain compositions under all four endpoint methods (plateau, peak,
discrepancy, public), together with the phylothreshold of every hierarchical clustering
group that meets the criteria for performing CORE stage.

Two properties matter for planning an analysis:

- **All four endpoints are computed in one run.** `--endpoint` does not choose which
  endpoints are evaluated; it selects which endpoint's strain composition drives transmission
  clusters and cluster plots. The endpoint behind clusters can be changed afterwards with
  `thresher redo-endpoint`, without recomputation.
- **Its output directory is the starting point for every other mode.** CladeBreaker OFF, Redo
  Endpoint, New SNPs, and New Full all read a completed Full Pipeline (or New Full) output.


## When to use Full Pipeline mode

Use Full Pipeline when:

- analyzing a dataset for the first time;
- the population structure of the dataset has changed enough that reusing prior phylogenies
  is no longer appropriate and no earlier output exists.

Do not use Full Pipeline when a completed run already answers the question more cheaply:

| Situation | Use instead |
|---|---|
| Same data, different endpoint to identify transmission clusters | `thresher redo-endpoint` |
| Same data, strains without CladeBreaker | `thresher cladebreaker-off` |
| A few added genomes, existing phylothresholds kept | `thresher new-snps` |
| Added genomes with phylothresholds re-inferred from all genomes | `thresher new-full` |

---

## Input required by Full Pipeline mode

### Genome assemblies

- Assemblies must have passed quality control before use. THRESHER does not check the quality of 
  input genome assemblies.
- All assemblies must belong to the declared species. Mixed-species input leaves too few
  shared core genes, Panaroo fails to produce a core gene alignment, and the run terminates
  at that step. WhatsGNU will also fail to find close match to the query study genomes provided as input. 
- At least 4 genomes are required. Groups with fewer than 4 genomes carry no group phylogeny,
  so their strains rest on SNP distances alone without phylogenetic correction or CladeBreaker.

### Metadata table (`--metadata`)

Tab-delimited, no header, either 3 or 5 columns.

| Column | Content | Required for | Notes |
|---|---|---|---|
| 1 | Genome name | All runs | Used as the genome label in every output table and plot |
| 2 | GenBank accession | All runs | Enter `new` (lowercase) when the genome is not deposited |
| 3 | Path to the genome assembly | All runs | Absolute paths are safest |
| 4 | Patient ID | Transmission clusters (EPI) | Any stable identifier |
| 5 | Collection date | Transmission clusters (EPI) | Format `yyyy-mm-dd` |

- **Why the accession column exists.** A study genome already deposited in GenBank can be
  returned as its own closest public match. The accession lets THRESHER exclude that copy, so
  a genome is never matched to itself during CladeBreaker or the public endpoint. See
  `docs/genbank_accession.md` for how to find accessions.
- **3 columns versus 5 columns.** With 3 columns THRESHER reports strains only and forces
  `--epi_mode False` regardless of what was passed. Transmission clusters require both patient
  identifiers and collection dates, since a cluster is defined by a strain spanning more than
  one patient over time.
- An example table is at `docs/example/example_metadata.txt`.

### Species (`--species`)

`sau` (*Staphylococcus aureus*), `sepi` (*Staphylococcus epidermidis*), `cdiff`
(*Clostridioides difficile*), `kp` (*Klebsiella pneumoniae*). The species selects the WhatsGNU
and PubMLST databases, sets the broader MLST grouping reported (clonal complex for *S. aureus*,
MLST clade for *C. difficile*, ST-prefixed sequence type for *K. pneumoniae* and
*S. epidermidis*), and enables MRSA detection for `sau`.

### Databases

| Database | Default behavior | Reuse flag |
|---|---|---|
| Bakta | Downloaded into `bakta_db/` in the output directory; `--bakta_db_type` selects `full` (default) or `light` | `--bakta_db_path` |
| WhatsGNU | Downloaded per species into `whatsgnu/db/` in the output directory | `--whatsgnu_db_path` |
| PubMLST | Ships with the mlst conda environment | — |
| Public genomes | Retrieved per run from NCBI Datasets based on WhatsGNU matches | — |

Both databases are large. Pass `--bakta_db_path` and `--whatsgnu_db_path` from an earlier run,
along with `--conda_prefix`, so that repeated analyses neither re-download databases nor
rebuild conda environments.

**AMRFinderPlus database pinning.** Bakta calls AMRFinderPlus, whose database ships separately
and is versioned independently, so a newly downloaded or previously installed Bakta database
can carry a version that the pipeline's AMRFinderPlus build does not accept. THRESHER therefore
pins the release: it reads `amrfinderplus-db/latest/version.txt` under the Bakta database
directory and compares it with the required version, `4.0`/`2025-07-16.1`. When they match, the
database is used as is. When they do not, THRESHER retrieves that release from the NCBI FTP
site with `wget`, builds the BLAST and HMMER indexes locally with `amrfinder_index` because
NCBI ships flat data files only, repoints `latest` at the pinned release, and re-checks the
version, stopping the run if it still does not match. The check runs whether the Bakta database
was downloaded by THRESHER or supplied through `--bakta_db_path`, so a database shared between
runs is verified each time and will be updated in place if its AMRFinderPlus version drifts.

This AMRFinderPlus database release is the one tested with the Bakta version pinned in
`thresher/workflow/envs/bakta.yaml`, and the combination runs without error. Other combinations
of Bakta and AMRFinderPlus database versions can raise errors for which no fix is currently
available, which is why the release is pinned rather than left to resolve at install time.

### System requirements

Full Pipeline checks for Linux and at least 40 GB of RAM, which WhatsGNU needs to load its
database into memory. `--force` bypasses both checks and risks failures mid-run. Internet
access is required for conda environments, database downloads, and public genome retrieval.
Bakta runs one annotation job per thread at roughly 10 GB of RAM each, so set `-t/--threads`
to what memory allows.

### Quick Start

```bash
# Strains and transmission clusters (5-column metadata)
thresher full --metadata metadata.txt --species sau -o thresher_run -t 4

# Strains only (3-column metadata, or 5-column with EPI disabled)
thresher full --metadata metadata.txt --species sau -o thresher_run -t 4 --epi_mode False
```

---

## What Full Pipeline mode computes

Snakemake resolves dependencies and runs independent steps in parallel, so the order below is
for reference, not execution. Rule files are under `thresher/workflow/rules/`.

**INPUT** — `thresher/bin/args_validator.py`, `thresher/bin/config_creator.py`. Validates the
metadata table, genome paths, species, and parameters, then writes `config/config_{prefix}.yaml`
before any computation starts.

**PREP** 

| Step | Rule file | Purpose |
|---|---|---|
| Assembly scan | `assembly_scan.smk` | Assembly metrics; the highest-N50 genome in a group becomes its Snippy reference |
| MLST typing | `mlst.smk` | Sequence types and broader groupings (for example CC in *S. aureus*), used in hierarchical clustering |
| MRSA detection (`sau` only) | `blastx_MRSA.smk` | mecA/mecC search labeling genomes and strains MRSA or MSSA |
| Annotation | `bakta_db.smk`, `bakta_annotation.smk` | Bakta annotation; the database downloads automatically unless `--bakta_db_path` is given |
| Public genome matching | `whatsgnu.smk`, `unique_topgenomes.smk`, `datasets_topgenomes.smk` | WhatsGNU scores annotated proteins against publicly available genomes and returns each study genome's top 20 matches; the deduplicated union is downloaded from NCBI Datasets |
| SNP distances | `mummer4_study.smk`, `mummer4_public.smk`, `snp_matrix.smk` | All-versus-all study SNP distances and study–public distances with MUMmer4 `dnadiff`; each pair's distance is averaged over both alignment directions and flagged when coverage falls below `--snp_coverage_threshold` |
| Pangenome analysis | `panaroo.smk`, `iqtree_core_gene.smk` | Filtered core gene alignment and a midpoint-rooted maximum likelihood core-gene tree (IQ-TREE, GTR+R) |
| Hierarchical clustering | `hierarchical_clustering.smk` | Partitions genomes into hierarchical clustering groups from cophenetic distances and MLST, choosing the group number that maximizes mean silhouette width |
| Group Reference-based phylogenies | `snippy_input.smk`, `snippy_groups.smk`, `iqtree_groups.smk` | Reference-based alignment per group, including the most closely related public genomes, and a group tree (IQ-TREE, GTR+R) |

Because public genome availability at NCBI changes over time, expected and actually downloaded
genomes are recorded separately and only downloaded genomes are used downstream.

**CORE** — `thresher_input.smk` scans every candidate phylothreshold from `--threshold_floor`
to `--threshold_ceiling` within each group: SNP single linkage, correction against the group
phylogeny under `--correction_bootstrap`, and CladeBreaker when enabled. The strain composition
at each tested threshold is recorded, and `thresher_plateau.smk`, `thresher_peak.smk`,
`thresher_discrepancy.smk`, and `thresher_public.smk` each select the group's final
phylothreshold. `thresher_MSTP.smk` and `thresher_QC.smk` produce the diagnostics.

**EPI** — `plot_cluster_plots.smk`, `plot_persistence_plot.smk`. Runs when `--epi_mode True`
and patient identifiers and collection dates are present. Strains spanning more than one
patient are reported as transmission clusters, using the strain composition of `--endpoint`.


## Output of Full Pipeline mode

Paths are relative to the run's output directory.

### Output directory layout

| Path | Contents |
|---|---|
| `thresher/output/` | Strains, group phylothresholds, QC, Multi-SNP-Threshold Plots, transmission cluster summary — the results layer |
| `thresher/input/` | Hierarchical clustering groups and the per-threshold CORE record (`thresher_input.RDS`) |
| `plots/` | Core-gene tree plots, SNP distance distribution, strain composition plots, cluster and persistence plots |
| `mlst/`, `blastx/` | Sequence types and, for `sau`, MRSA or MSSA calls |
| `bakta_annotation/`, `panaroo/`, `iqtree/`, `snippy/` | Annotation, pan-genome, phylogenies, group alignments |
| `mummer4_study/`, `mummer4_public/`, `whatsgnu/`, `datasets_topgenomes/`, `assembly_scan/` | SNP distances, public genome matching and downloads, assembly metrics |
| `config/`, `conda_envs_*/`, `resume/` | Run configuration, environments, unlock and resume scripts |

Every mode other than Full Pipeline reads this directory, so keep it intact.

### Strains and phylothresholds

**Strain tables**, one per endpoint method:
`thresher/output/{plateau,peak,discrepancy,public}_strains.csv` (and `.RDS`).

| Column | Content |
|---|---|
| `strain_id` | Strain identifier, formatted `<group>_<number>`, for example `1_1` |
| `genome` | Genome name |

A strain with two or more genomes is a clone; a strain with one genome is a singleton.

**Group phylothreshold tables**, one per endpoint method:
`thresher/output/group_{plateau,peak,discrepancy,public}.csv`. Each has a `group` column and a
column named for the endpoint holding that group's phylothreshold; `group_plateau.csv` also
records the `plateau_length` used.

Values that are not numbers carry meaning:

| Value | Meaning |
|---|---|
| `Singletons` or `NA` | The group has no phylothreshold because every genome in it is a singleton |
| `No Plateau Found` | No run of stable strain composition at least `--plateau_length` long existed in the tested range |
| A public value equal to `--threshold_ceiling` | No good-quality study–public SNP distance was available for that group |

Compare the four tables before settling on one. Where the endpoints agree, the strain
composition is robust to the choice of hypothesis; where they disagree, inspect that group in
the Multi-SNP-Threshold Plot and its strain composition plot.

### Multi-SNP-Threshold Plot (MSTP)

`thresher/output/MSTP/Group{Group_ID}_MSTP.pdf`, with all plots collected in
`thresher/output/MSTP/MSTP.RDS`. One plot per hierarchical clustering group; groups without a
group phylogeny produce none.

- Shared x-axis: every SNP threshold tested, from `--threshold_floor` to `--threshold_ceiling`.
- Lower panel: counts of clones, singletons, and discrepant genomes across the range, with the
  phylothreshold chosen by each endpoint annotated.
- Upper panel: mean and median bootstrap support of the clades formed by the genomes assigned
  to the same clone at each threshold.

This is the primary diagnostic. A wide flat stretch in the lower panel indicates a divergence
gap; a composition that changes at every threshold indicates continuous diversity, in which
case endpoints will disagree and the phylothreshold deserves closer review. Bootstrap support
that falls as the threshold rises indicates strains being merged across poorly supported
clades.

### Strain composition plots

`plots/strain_compositions/{endpoint}/Group{Group_ID}_{endpoint}_strain_composition.pdf`, with
R objects in `{endpoint}_strain_tree_snp.RDS`. Produced for all four endpoints.

- **Left panel, group phylogeny.** Midpoint-rooted maximum likelihood tree. Blue tips are study
  genomes, brown tips are public genomes retrieved for CladeBreaker. Clones are boxed in green
  and labeled with their strain ID. The phylothreshold for that endpoint is printed at the top,
  and the scale bar is in substitutions per site.
- **Right panel, SNP distance heatmap.** Rows follow the tree tips; columns are study genomes.
  The white-to-blue gradient is the pairwise SNP distance. Grey cells are study-to-public
  comparisons, and empty cells mean that public genome was not among that study genome's
  WhatsGNU matches. Green text marks distances meeting `--snp_coverage_threshold`; red text
  marks low-coverage pairs to be interpreted with caution.

Use these plots to check that each clone corresponds to a coherent clade and a block of low SNP
distances, and to see whether a public genome sits inside a study clade, which is where
CladeBreaker acts.

### Quality control plots and tables

`thresher/output/QC/{endpoint}_qc_plot.pdf` and `{endpoint}_qc_table.csv`. Each point is a pair
of strains, plotted by average phylogenetic distance (x) against average SNP distance (y), with
a reference line at 100 SNPs. Blue points are strain pairs within one hierarchical clustering
group, red points are pairs from different groups.

| Column | Content |
|---|---|
| `subject`, `query` | The two strain IDs compared |
| `snp_average_distance` | Mean pairwise SNP distance between their genomes |
| `phylogeny_average_distance` | Mean pairwise branch-length distance on the core-gene phylogeny |
| `same_group` | Whether both strains belong to the same hierarchical clustering group |

A well-supported phylothreshold separates between-strain distances cleanly from within-strain
distances and places between-group pairs further out. Between-strain distances that reach down
into the within-strain range suggest the phylothreshold is too high for that group.

### Transmission clusters (EPI only)

`thresher/output/clusters_summary.csv` (and `.RDS`), built from the strain composition of
`--endpoint`.

| Column | Content |
|---|---|
| `cluster` | Transmission cluster ID |
| `strain` | Strain ID the cluster comes from |
| `MLST` | Broader MLST grouping, for example clonal complex in *S. aureus* |
| `AMR` | MRSA or MSSA for `sau`; `N/A` otherwise |
| `genomes` | Genome names in the cluster, separated by a pipe character |
| `patients` | Patient IDs in the cluster, separated by a pipe character |
| `first_seen`, `last_seen` | Earliest and latest collection dates among the cluster's genomes |
| `persistence` | Days between `first_seen` and `last_seen` |

Plots: `plots/ClusterPlots/Cluster{cluster_id}.pdf` per cluster (collected in
`ClusterPlots.RDS`) and `plots/PersistencePlot.pdf` (`PersistencePlot.RDS`) across the study
period.

A cluster means two or more patients carry genomes of the same strain, which warrants
epidemiological review. It is not proof of direct patient-to-patient transmission: direction
and route cannot be inferred from these data, an unsampled intermediate source may link the
patients, and incomplete sampling can hide links. Long persistence can reflect ongoing
transmission or a persistent reservoir. To see the same data under a different strain
definition, run `thresher redo-endpoint` rather than rerunning Full Pipeline.

### Dataset-level context

| Output | Contents |
|---|---|
| `thresher/input/hierarchical_clustering_groups_simplified.csv` | Per genome: `genome`, `group`, and `overlimit` — `TRUE` when the genome's smallest SNP distance to any other genome in its group is at or above `--singleton_threshold`, in which case it is treated as a singleton and set aside from group-level strain determination |
| `plots/core_gene_tree_group.pdf`, `plots/core_gene_tree_mlst.pdf` | Core-gene phylogeny annotated by hierarchical clustering group and by MLST; use these to check that groups follow the tree structure |
| `plots/SNP_Distance.pdf` | Distribution of pairwise SNP distances among study genomes and between study and public genomes; multiple modes indicate lineage structure that grouping should capture |
| `mlst/summary/mlst_results.csv` | Per genome: `genome`, `ST`, `MLST` (tab-delimited despite the extension); raw calls in `mlst/raw/` |
| `blastx/mrsa/output/summary/blastx_MRSA_genomes.csv`, `blastx_MRSA_strains.csv` | MRSA or MSSA per genome and per strain, `sau` only; raw hits in `blastx/mrsa/output/raw/` |

### Evidence and intermediates

| Output | Contents |
|---|---|
| `mummer4_study/study_snp_matrix.RDS`, `mummer4_public/public_snp_matrix.RDS` | Pairwise SNP distances with alignment coverage, study–study and study–public; per-genome reports alongside them |
| `whatsgnu/whatsgnu_results/{genome_name}_WhatsGNU_topgenomes.txt` | The top 20 public genomes sharing the most identical proteins with each study genome |
| `datasets_topgenomes/expected_download_topgenomes.txt`, `actual_download_topgenomes.txt` | Public genomes requested versus actually retrieved; availability at NCBI changes over time and only downloaded genomes are used |
| `bakta_annotation/{genome_name}/` | Per-genome annotation (`.gff3`, `.faa`) feeding Panaroo and WhatsGNU |
| `panaroo/core_gene_alignment_filtered.aln` | Filtered core gene alignment |
| `iqtree/core_gene_tree/`, `iqtree/group_tree/` | Core-gene and per-group maximum likelihood trees with support values |
| `snippy/output/cleaned_aln/` | Reference-based alignment per group |
| `assembly_scan/` | Assembly metrics; the highest-N50 genome in a group is its Snippy reference |
| `thresher/input/thresher_input.RDS` | The per-threshold CORE record: strain composition at every tested threshold, before endpoint selection |

`thresher_input.RDS`, the SNP matrices, the group alignments and trees, and the annotations are
what allow CladeBreaker OFF, Redo Endpoint, New SNPs, and New Full to skip recomputation.

### Bookkeeping

`config/config_{prefix}.yaml` records every parameter the run used and is the authoritative
record of how a result was produced. `conda_envs_*/` holds the tool environments, reusable
through `--conda_prefix`. `resume/` holds the unlock and resume scripts for an interrupted run.

## Parameters that change Full Pipeline results

| Parameter | Default | Effect on the result | When to adjust |
|---|---|---|---|
| `--endpoint` | `plateau` | Selects the strain composition behind transmission clusters and cluster plots; does not change the strains reported for the other endpoints | When a more sensitive (discrepancy) or more specific (peak) definition suits the investigation. Prefer `thresher redo-endpoint` afterwards rather than rerunning |
| `--plateau_length` | 15 | Required length of the stable run for the plateau endpoint. Longer demands a wider gap in divergence and tends to give lower, more conservative phylothresholds; shorter accepts weaker evidence and raises `No Plateau Found` less often | When many groups report `No Plateau Found`, or when plateau phylothresholds look implausibly high for the species |
| `--threshold_floor` | 5 | Lower bound of the search range | Raise only when very low thresholds are uninformative for the dataset; lowering rarely helps because strains below the floor are already singletons |
| `--threshold_ceiling` | 500 | Upper bound of the search range | Raise for diverse species or long sampling periods when endpoints sit at or near the ceiling; lower to prevent unrelated lineages from merging |
| `--singleton_threshold` | 100 | If the smallest SNP distance in a group is at or above this value, every genome in that group becomes a singleton; also sets the per-genome `overlimit` flag | Lower for clonal datasets where only near-identical genomes should form strains; raise for diverse species where legitimate strains span larger distances |
| `--use_cladebreaker` | `True` | Splits a corrected strain's clade when a matched public genome falls inside it, assuming study strains are hyperlocal | Set `False` when public matches plausibly belong to the same strains, for example earlier isolates from the same facility or region. After a run exists, use `thresher cladebreaker-off` and compare |
| `--correction_bootstrap` | 0 | Minimum bootstrap support for a clade to justify a phylogenetic correction; the group root is always retained | Raise to accept only well-supported corrections; keep at 0 for small groups where high support is hard to reach |
| `--snp_coverage_threshold` | 80 | Alignment coverage below which a pairwise SNP distance is treated as poor quality and excluded from CladeBreaker and the public endpoint | Raise for fragmented assemblies or when many heatmap values appear red; lowering it admits distances that unaligned regions make artificially small |
| `--core_threshold` | 0.95 | Gene frequency required for Panaroo to call a gene core, which sets the core alignment behind the core-gene tree and hierarchical clustering | Lower for diverse datasets where a strict core leaves too little alignment; raise for tightly related datasets |
| `--core_bootstrap_method`, `--core_bootstrap_number` | `ultrafast`, 1000 (100 nonparametric) | Support values on the core-gene tree, which underlies hierarchical clustering groups | Switch to `nonparametric` when support values must be conservative and run time allows |
| `--group_bootstrap_method`, `--group_bootstrap_number` | `ultrafast`, 1000 (100 nonparametric) | Support values on group trees, which gate phylogenetic correction through `--correction_bootstrap` | Same reasoning as the core tree; relevant whenever `--correction_bootstrap` is raised above 0 |
| `--epi_mode` | `True` | Whether transmission clusters and cluster plots are produced | Set `False` when patient data is unavailable; it is forced to `False` with 3-column metadata |
| `--species` | required | Selects the WhatsGNU and PubMLST databases and MRSA detection | Must match the assemblies |
| `--bakta_db_type` | `full` | `light` annotates less completely, which can shift the core gene set and, indirectly, the core-gene tree and groups | Use `light` only when disk or download capacity forces it |

Parameters that affect run time or bookkeeping but not the result: `-t/--threads`, `--output`,
`--prefix`, `--conda_prefix`, `--bakta_db_path`, `--whatsgnu_db_path`, `--force`.

**A practical approach.** Run with defaults first. The defaults were selected during THRESHER's
validation across simulated populations and 55 published studies and are a reasonable starting
point for all supported species. Then inspect the Multi-SNP-Threshold Plots, QC plots, and
strain composition plots, and change parameters only in response to something visible there:
endpoints pressed against the ceiling, widespread `No Plateau Found`, groups collapsing into
singletons, or heatmaps dominated by poor-quality alignments. Change one parameter at a time,
keep the runs side by side, and pass `--conda_prefix`, `--bakta_db_path`, and
`--whatsgnu_db_path` from the first run so environments and databases are not rebuilt.

---

## Changing parameters without rerunning Full Pipeline

| Parameter to change | Path |
|---|---|
| `--endpoint` behind transmission clusters | `thresher redo-endpoint` |
| Threshold floor, ceiling, singleton threshold, plateau length, correction bootstrap, with CladeBreaker disabled | `thresher cladebreaker-off` |
| Any of those with CladeBreaker enabled | Rerun `thresher full` |
| Anything in PREP, such as coverage threshold, core threshold, or bootstrap settings | Rerun `thresher full` |

---

## Run time, resources, and interrupted runs

Full Pipeline is THRESHER's most expensive mode. Annotation, public genome matching,
all-versus-all SNP distances, and phylogenetic inference scale unfavorably with genome number,
and datasets of roughly a thousand genomes or more take substantially longer. The exhaustive
comparison is a deliberate trade-off in favor of accuracy.

Raise `-t/--threads` within available memory: Snakemake runs independent jobs in parallel.
Bakta is parallelized across genomes rather than within one — each genome is annotated by its
own single-threaded job, and Snakemake runs as many of those concurrently as `-t/--threads`
allows. Each job needs about 10 GB of RAM, so set the thread count so that at least 10 GB is
available per thread; above that ratio the annotation jobs are killed by the OOM killer. With
50 GB of RAM, 4 threads runs cleanly and 10 threads does not.

An interrupted run resumes from the last completed step. Unlock first, then resume:

```bash
bash <output>/resume/unlock_snakemake_<prefix>.sh
bash <output>/resume/resume_snakemake_<prefix>.sh
```

## Common causes of failure or misleading Full Pipeline output

- Assemblies from more than one species, or contaminated assemblies: Panaroo cannot build a
  core gene alignment and the run stops there.
- Assemblies that have not passed quality control: fragmented genomes lower alignment coverage,
  which removes pairs from CladeBreaker and the public endpoint and leaves red values in the
  heatmaps.
- Fewer than 4 genomes: below the minimum for analysis. Groups with fewer than 4 genomes also
  have no group phylogeny, so their strains rest on SNP distances without phylogenetic
  correction or CladeBreaker.
- `--epi_mode True` with 3-column metadata: no transmission clusters are produced, and the run
  proceeds in strain-only form.
- Less than 40 GB of RAM, or `--force` used to bypass the check: WhatsGNU fails to load its
  database.
- Public genomes that genuinely share strains with the study genomes: CladeBreaker splits those
  strains, underestimating strain size and overestimating strain number. Compare against
  `thresher cladebreaker-off` before concluding.