# THRESHER New SNPs Mode — Guide

> Explains what New SNPs mode does, when to use it, what it requires as input, what it
> produces, and which parameters change the result. Rationale, decision logic, and
> interpretation only; the complete option list, metadata specification, and output file
> inventory are in `docs/usage_new_snps.md` in the THRESHER repository.

Command: `thresher new-snps`

## What New SNPs mode does

New SNPs places new genomes into the strains a previous run already defined. It computes
pairwise SNP distances between the new genomes and existing genomes in a previous run, merges them 
into the prior study SNP matrix, and applies the phylothresholds from the prior run to decide which 
existing strain each new genome joins. Strain assignments are updated for all four endpoint methods
(plateau, peak, discrepancy, public). When the prior run defined transmission clusters, those
are updated too.

What New SNPs deliberately does not do:

- **It does not re-infer phylothresholds.** The thresholds of the prior run are reused as given.
- **It does not rebuild any phylogenies.** No modification or changes made in annotation, WhatsGNU matching,
  public genome retrieval, pan-genome, core-gene tree, group trees, or hierarchical
  clustering. Therefore no phylogenetic correction and no CladeBreaker implementation will be changed.
  Strain assignment is based on single-linkage using SNP distance alone.
- **It does not produce a reusable analysis directory.** Results carry `new_` prefixes and
  `_new_snps` suffixes precisely because they are not interchangeable with Full Pipeline output
  and cannot serve as the starting point for another mode.

The trade-off is speed for comphrehensive analysis and updated phylothresholds. New SNPs takes minutes to hours 
instead of a full rerun, at the cost of strain definitions that were optimized for the earlier dataset rather than the expanded one.

## When to use New SNPs mode

Use New SNPs when:

- a small number of genomes arrive and the question is where they fall in the strains already
  defined in the previous run;
- continuity and stability are prioritized. Strain and cluster IDs from the prior run need to be preserved,
  so a report built on the earlier analysis stays unchanged.

Do not use New SNPs when:

| Situation | Use instead |
|---|---|
| Many new genomes, or genomes from backgrounds absent in the prior dataset | `thresher new-full` |
| Phylothresholds should reflect the expanded dataset | `thresher new-full` |
| No genomes added, different endpoint behind transmission clusters | `thresher redo-endpoint` |
| No genomes added, strains without CladeBreaker | `thresher cladebreaker-off` |
| No completed prior run exists | `thresher full` |

New SNPs answers "where do these new genomes fall in the strains I already defined?" New Full
answers "what are the phylothresholds and resulting strains once these genomes are part of the dataset?" 
When the new genomes are few and closely related to existing result, both usually agree and New SNPs is far 
less computationally expensive. When they are numerous or divergent, only New Full gives a defensible answer.

## Input required by New SNPs mode

### The completed prior run (`--thresher_output`)

A Full Pipeline or New Full output directory. THRESHER checks it before starting and stops with
a list of missing files if anything required is absent.

| Required content | Path in the prior run |
|---|---|
| Strain tables for all four endpoints, with their group phylothresholds | `thresher/output/{plateau,peak,discrepancy,public}_strains.RDS` |
| Study SNP matrix | `mummer4_study/study_snp_matrix.RDS` |
| Transmission clusters, if they are to be updated | `thresher/output/clusters_summary.RDS` and `.csv` |
| MRSA results, for `sau` | `blastx/mrsa/` |

- A **New SNPs output is not a valid prior run**: it contains `new_`-prefixed results rather
  than the strain tables this mode reads. Always point `--thresher_output` at the Full Pipeline
  or New Full directory, even when adding a second batch after an earlier New SNPs run.
- Transmission clusters are updated only when `clusters_summary.RDS` exists in the prior run,
  that is, when it was run with `--epi_mode True`. Otherwise New SNPs updates strains only.
- The prior run must be for the same species.

### Original metadata (`--original_metadata`)

The same metadata table used for the prior run. The original assembly files must still exist at
the recorded paths: every new genome is compared against every original genome with MUMmer4, so
those files are read again.

### New genomes and new metadata (`--new_metadata`)

Same format as the original table: tab-delimited, no header, 3 or 5 columns (genome name,
GenBank accession or `new`, genome path, and for transmission clusters patient ID and
collection date in `yyyy-mm-dd`). At least one new genome is required.

- Genome names must be unique across both tables and must not duplicate an original genome name.
- New assemblies must belong to the same species as the original ones and must have passed
  quality control; fragmented assemblies lower alignment coverage and make SNP distances
  unreliable, and here there is no phylogeny to catch the consequences.
- When the prior run defined transmission clusters, supply 5-column metadata with complete
  patient IDs and collection dates for the new genomes.

### Species (`--species`)

`sau`, `sepi`, `cdiff`, or `kp`, matching the prior run. The species selects the PubMLST
database and enables MRSA detection for `sau`.

### System requirements

Lighter than the other modes. No Bakta or WhatsGNU database is used, so there is no 40 GB
memory requirement, no database download, and no `--force` flag. Internet access is needed only
to create conda environments; pass `--conda_prefix` pointing at the prior run's environments to
skip that too.

### Quick Start

```bash
thresher new-snps \
  --original_metadata original_metadata.txt \
  --new_metadata new_metadata.txt \
  --thresher_output thresher_run \
  --species sau \
  -o thresher_run_new_snps \
  -t 4 \
  --conda_prefix /path/to/conda/envs
```

## What New SNPs mode computes

### Reused versus computed

| Step | Original genomes | New genomes |
|---|---|---|
| MLST | Reused from the prior run | Computed, merged into `mlst/summary/mlst_results.csv` |
| MRSA (`sau`) | Reused | Computed, merged and cross-referenced with the updated strains |
| MUMmer4 SNP distances | Original-versus-original distances carried forward | New-versus-original in both directions and new-versus-new computed, then merged into the study matrix |
| Phylothresholds, hierarchical clustering groups, phylogenies, public genomes | Taken from the prior run unchanged | Not computed |
| Strain assignment | Existing strains kept; new genomes added to them | Assigned by single linkage on SNP distance |
| Transmission clusters | Updated when the prior run had them | Updated when the prior run had them |

### How new genomes are assigned

For each endpoint method independently:

1. Existing strains are visited in sorted order. Each strain takes the phylothreshold of its
   hierarchical clustering group from the prior run.
2. If that group has no phylothreshold (a group whose genomes were all singletons), the
   threshold of the nearest group that does have one is borrowed, found by walking outward from
   the strain by SNP distance.
3. Any new genome within that threshold of a member of the strain joins the strain
   (single linkage). A genome is assigned once and then later strains can only absorb the genomes 
   that are still unassigned.
4. New genomes that join no existing strain are then grouped among themselves by single
   linkage, again using a threshold borrowed from the nearest group, and form new strains.

New strains created this way are numbered with plain integers, not the `<group>_<number>` form
used for strains inherited from the prior run, which makes them easy to spot in the output.
Because no group phylogeny is built for the new genomes, no phylogenetic correction or
CladeBreaker is applied at any point.

### Rule files

Rules with a `_new` suffix are shared with New Full; rules with a `_new_snps` suffix are
specific to this mode.

| Step | Rule file |
|---|---|
| MLST (new genomes, merged summary) | `mlst_new.smk` |
| SNP distances for new genomes | `mummer4_study_new_snps.smk` |
| Merge into the study SNP matrix | `snp_matrix_new_snps.smk` |
| Strain assignment under the prior phylothresholds | `thresher_new_snps.smk` |
| MRSA detection (`sau`, conditional) | `blastx_MRSA_new_snps.smk` |
| Transmission clusters and persistence (conditional) | `plot_cluster_plots_new_snps.smk`, `plot_persistence_plot_new_snps.smk` |

## Output of New SNPs mode

Paths are relative to the New SNPs `--output` directory.

### Updated strain assignments

Three files per endpoint method, in `thresher/output/`:

| File | Contents |
|---|---|
| `new_{endpoint}_genomes.csv` | New genomes only: `strain_id`, `category` (`existing_strain` when the genome joined a strain from the prior run, `new_strain` when it formed one), `genome`. **Open this first** |
| `new_{endpoint}_strains.csv` | The complete updated strain composition, original and new genomes together: `strain_id`, `genome` |
| `new_{endpoint}.RDS` | R object holding both tables and the endpoint name |

Endpoints are `plateau`, `peak`, `discrepancy`, and `public`, so all four assignments are
available regardless of which one the prior run used for clusters.

### Updated SNP distances

`mummer4/study_snp_matrix_new.RDS` is the merged study matrix: original-versus-original
distances carried forward plus the newly computed comparisons. Per-genome MUMmer4 reports and
the generated `dnadiff` scripts sit alongside it under `mummer4/`. No public SNP matrix is
produced, because public genomes are not retrieved in this mode.

### Updated transmission clusters (only when the prior run had them)

| Output | Contents |
|---|---|
| `thresher/output/clusters_summary_new_snps.csv` and `.RDS` | Updated clusters, with the same columns as the Full Pipeline cluster summary: `cluster`, `strain`, `MLST`, `AMR`, `genomes`, `patients`, `first_seen`, `last_seen`, `persistence` |
| `thresher/output/genomes_summary_new_snps.csv` | One row per genome: `genome_name`, `genome_category` (`original` or `new`), `original_strain` (`New-Genome` for added genomes), `new_strain`, `original_cluster` (`New-Genome` for added genomes, `Non-Cluster` when the genome was in none), `new_cluster` (`Non-Cluster` when the genome is in none) |
| `plots/Cluster{cluster_id}.pdf`, `plots/ClusterPlots_new_snps.RDS` | Updated cluster plots |
| `plots/PersistencePlot_new_snps.pdf` and `.RDS` | Updated persistence across the study period |

Cluster identity is preserved where it can be: a cluster whose original genomes all carry over
keeps its ID, and clusters formed by the new genomes continue the numbering from the prior run.
`genomes_summary_new_snps.csv` is the file to read for the practical question — which patients
and strains changed status with this batch.

The cluster update follows the endpoint recorded in the prior run's `clusters_summary.RDS`, not
a value passed on the command line.

### Typing outputs

`mlst/summary/mlst_results.csv` covers all genomes, original and new, with raw calls in
`mlst/raw/`. For `sau`, `blastx/mrsa/output/summary/blastx_MRSA_genomes.csv` and
`blastx_MRSA_{plateau,peak,discrepancy,public}_strains.csv` give MRSA or MSSA per genome and
per updated strain, with raw hits in `blastx/mrsa/output/raw/`.

### What New SNPs does not produce

No `group_{endpoint}.csv` phylothreshold tables, no Multi-SNP-Threshold Plots, no QC plots or
tables, no strain composition plots, no core-gene tree or SNP distance plots, no public SNP
matrix, and no updated hierarchical clustering. Those all depend on re-inference, which this
mode skips by design. For any of them, run New Full.

### Reading the result

1. Open `new_{endpoint}_genomes.csv` for the endpoint of interest. Genomes marked
   `existing_strain` were absorbed into known strains; genomes marked `new_strain` were not
   close enough to anything already defined.
2. Check whether the four endpoints agree on the new genomes. Agreement means the placement is
   insensitive to the strain definition; disagreement means the genomes sit near a boundary and
   the assignment rests on the prior thresholds.
3. If the prior run had clusters, read `genomes_summary_new_snps.csv` to see which genomes
   entered existing clusters and which clusters are new.
4. Treat a batch that produces several `new_strain` genomes as a signal that the dataset has
   moved beyond what the prior analysis described, and rerun with New Full.

## Parameters that change New SNPs results

Most of what determines the answer is fixed by the prior run: phylothresholds, hierarchical
clustering groups, CladeBreaker, and the endpoint behind transmission clusters are read from it
and cannot be changed here.

| Parameter | Default | Effect on the result | When to adjust |
|---|---|---|---|
| `--thresher_output` | required | Supplies the strain compositions and phylothresholds applied to the new genomes; it is the single largest determinant of the output | Must be a Full Pipeline or New Full output of the same species, never a New SNPs output |
| `--original_metadata`, `--new_metadata` | required | Which genomes are treated as existing and which as additions | The original table must match the prior run; assemblies in both must still exist |
| `--snp_coverage_threshold` | 80 | Alignment coverage below which a pairwise SNP distance is treated as poor quality | Raise when the new assemblies are more fragmented than the original set; keep it at the prior run's value so the new distances are judged by the same standard |
| `--species` | required | PubMLST database and MRSA detection | Must match the prior run |

Parameters that affect run time or bookkeeping but not the result: `-t/--threads`, `--output`,
`--prefix`, `--conda_prefix`.

## Changing what New SNPs cannot change

| Goal | Path |
|---|---|
| Strains under a different endpoint | Already produced: read `new_{endpoint}_genomes.csv` for that endpoint |
| Transmission clusters under a different endpoint | Run `thresher redo-endpoint` on the prior run, then add the genomes again |
| Strains without CladeBreaker | Run `thresher cladebreaker-off` on the prior run, then add the genomes again |
| Phylothresholds that account for the new genomes | Run `thresher new-full` |
| Any PREP setting, such as core threshold or bootstrap options | Those belong to the run that built the phylogenies; use `thresher new-full` |

## Run time, resources, and interrupted runs

New SNPs is the fastest mode. The only heavy step is MUMmer4, wher each new genome is compared
against every original genome in both directions and against every other new genome, so cost
grows with the number of new genomes multiplied by the size of the original dataset, not with
the size of the dataset alone. Nothing is annotated, no database is downloaded, and no
phylogeny is inferred.

Raise `-t/--threads` to run the comparisons in parallel. An interrupted run resumes from the
last completed step; unlock first, then resume:

```bash
bash <output>/resume/unlock_snakemake_<prefix>.sh
bash <output>/resume/resume_snakemake_<prefix>.sh
```

## Common causes of failure or misleading New SNPs output

- `--thresher_output` pointing at a New SNPs output, or at a run missing the four strain RDS
  files or the study SNP matrix. The run stops during validation with the missing files listed.
- Original assemblies moved, renamed, or deleted since the prior run: the new-versus-original
  comparisons cannot be made.
- Original metadata that does not match the prior run, or a new genome name that duplicates an
  original one.
- 3-column new metadata when the prior run defined transmission clusters: patient IDs and
  collection dates are required to update them.
- A `sau` prior run without `blastx/mrsa/`, or a species that does not match the prior run.
- Adding genomes that are divergent from everything in the prior dataset. They are assigned
  with a threshold borrowed from the nearest group, which is a weaker basis than an inferred
  phylothreshold. Several `new_strain` assignments in one batch mean New Full is the
  appropriate mode.
- Reading New SNPs assignments as equivalent to a re-inferred analysis, while they carry no
  phylogenetic correction, no CladeBreaker, and thresholds fitted to the earlier dataset. When
  a genome lands close to a threshold, or when the result will be reported, confirm it with
  New Full.