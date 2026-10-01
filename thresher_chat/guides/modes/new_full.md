# THRESHER New Full Mode — Guide

> Explains what New Full mode does, when to use it, what it requires as input, what it
> produces, and which parameters change the result. Rationale, decision logic, and
> interpretation only; the complete option list, metadata specification, and output file
> inventory are in `docs/usage_new_full.md` in the THRESHER repository.

Command: `thresher new-full`


## What New Full mode does

New Full adds genomes to a completed analysis (produced by Full Pipeline or New Full) and re-infers 
everything that depends on the dataset as a whole. It merges the new genomes with the existing ones, 
rebuilds the core-gene phylogeny and the hierarchical clustering groups, re-infers the phylothreshold 
of every group under all four endpoint methods (plateau, peak, discrepancy, public), and re-determines 
strains across the combined dataset. When the prior run defined transmission clusters, those are
updated as well.

The result is equivalent to running Full Pipeline on all genomes at once, but the expensive
per-genome work already done is reused: assembly metrics, MLST, annotation, WhatsGNU matching,
and pairwise SNP distances are computed only for the new genomes, and the pan-genome graph is
merged rather than rebuilt from scratch.

Three properties matter for planning:

- **Phylothresholds move.** Adding genomes changes group membership and group diversity, so
  phylothresholds, strain composition, and strain IDs can all differ from the prior run. This
  is the point of the mode, and the reason it is not interchangeable with New SNPs.
- **Output names match Full Pipeline.** A New Full output directory can serve as the
  `--thresher_output` for a later New Full run, and as the starting point for Redo Endpoint and
  CladeBreaker OFF. Additions can therefore be made incrementally over time.
- **The prior run is read, not modified.** Results are written to a new `--output` directory;
  the original run stays intact.

## When to use New Full mode

Use New Full when:

- the new genomes could change the population structure, such as a large batch, or genomes from
  genetic backgrounds absent from the original dataset;
- surveillance has continued long enough that the phylothresholds inferred from the earlier
  sampling window no longer describe the dataset;
- the output must remain compatible with further New Full additions.

Do not use New Full when:

| Situation | Use instead |
|---|---|
| A few genomes added, phylothresholds and phylogenies deliberately held fixed | `thresher new-snps` |
| No genomes added, only a different endpoint behind transmission clusters | `thresher redo-endpoint` |
| No genomes added, strains without CladeBreaker | `thresher cladebreaker-off` |
| No completed prior run exists | `thresher full` |

New SNPs answers "where do these new genomes fall in the strains I already defined?" New Full
answers "what are the phylothresholds and resulting strains once these genomes are part of the dataset?" 
When the new genomes are few and closely related to existing result, both usually agree and New SNPs is far 
less computationally expensive. When they are numerous or divergent, only New Full gives a defensible answer.

---

## Input required by New Full mode

### The completed prior run (`--thresher_output`)

A Full Pipeline or New Full output directory. THRESHER checks it before starting and stops with
a list of missing files if anything required is absent. It must contain:

| Required content | Path in the prior run |
|---|---|
| Strain tables for all four endpoints | `thresher/output/{plateau,peak,discrepancy,public}_strains.RDS` |
| Study and public SNP matrices | `mummer4_study/study_snp_matrix.RDS`, `mummer4_public/public_snp_matrix.RDS` |
| Pan-genome graph and core alignment | `panaroo/` |
| Bakta annotation for every original genome | `bakta_annotation/{genome_name}/{genome_name}.gff3` |
| WhatsGNU top-genome results for the original genomes | `whatsgnu/` |
| Transmission clusters, if they are to be updated | `thresher/output/clusters_summary.RDS` and `.csv` |

- The prior run must be for the same species. For `sau`, it must also contain `blastx/mrsa/`,
  since the MRSA results are merged rather than recomputed for the original genomes.
- A **New SNPs output is not a valid prior run.** New SNPs writes `new_`-prefixed result names
  and holds phylothresholds fixed; start from the Full Pipeline or New Full directory it was
  derived from.
- Transmission clusters are updated only when `clusters_summary.RDS` exists in the prior run,
  that is, when that run was executed with `--epi_mode True`. Otherwise New Full reports strains
  only.

### Original metadata (`--original_metadata`)

The same metadata table used for the prior run, in the same 3- or 5-column format. The original
assembly files must still exist at the recorded paths: the new genomes are compared against
them with MUMmer4, so the paths are read again even though the original per-genome results are
reused. Moving or deleting the original assemblies breaks the run.

### New genomes and new metadata (`--new_metadata`)

Same format as the original table: tab-delimited, no header, 3 or 5 columns
(genome name, GenBank accession or `new`, genome path, and for transmission clusters patient ID
and collection date in `yyyy-mm-dd`). At least one new genome is required.

- Genome names must be unique across the original and new tables, must not be pure numbers, and
  are sanitized if they contain characters outside letters, digits, `.`, `_`, and `-`.
- All new assemblies must belong to the same species as the original ones and must have passed
  quality control. Mixed-species input breaks the Panaroo merge in the same way it breaks
  Panaroo in Full Pipeline.
- When the prior run defined transmission clusters, supply 5-column metadata with complete
  patient IDs and collection dates for the new genomes; the clusters cannot be updated without
  them.

### Species and databases

`--species` must match the prior run: `sau`, `sepi`, `cdiff`, or `kp`. Pass
`--bakta_db_path` and `--whatsgnu_db_path` pointing at the databases the prior run used, and
`--conda_prefix` pointing at its environments, so that New Full neither re-downloads tens of
gigabytes nor rebuilds conda environments. Without those flags the databases are downloaded
again into the new output directory.

### System requirements

Same as Full Pipeline: Linux, at least 40 GB of RAM for WhatsGNU, internet access for database
downloads and public genome retrieval, and about 10 GB of RAM per thread for Bakta. `--force`
bypasses the OS and RAM checks and risks failures mid-run.

### Quick Start

```bash
thresher new-full \
  --original_metadata original_metadata.txt \
  --new_metadata new_metadata.txt \
  --thresher_output thresher_run \
  --species sau \
  -o thresher_run_new_full \
  -t 4 \
  --bakta_db_path thresher_run/bakta_db \
  --whatsgnu_db_path path/to/whatsgnu/db
```

## What New Full mode computes

### Reused versus recomputed

| Step | Original genomes | New genomes |
|---|---|---|
| Assembly scan, MLST, MRSA (`sau`), Bakta annotation, WhatsGNU | Reused from the prior run | Computed, then merged with the prior results |
| Public genome retrieval | Prior downloads reused | New WhatsGNU matches downloaded from NCBI Datasets and added |
| MUMmer4 SNP distances | Original-versus-original distances carried forward | New-versus-original and new-versus-new computed; study and public matrices merged |
| Pan-genome | Prior graph reused | Panaroo run on new genomes, then `panaroo-merge` with the prior graph and `panaroo-msa` for the merged core alignment |
| Core-gene phylogeny, hierarchical clustering, Snippy alignments, group phylogenies | Recomputed on the combined dataset | Recomputed on the combined dataset |
| CORE: phylothresholds and strains under all four endpoints | Re-inferred | Re-inferred |
| QC tables and Multi-SNP-Threshold Plots | Regenerated | Regenerated |
| EPI: transmission clusters | Updated when the prior run had them | Updated when the prior run had them |

### Rule files

Rules carrying a `_new_full` suffix handle the merge logic; rules with a `_new` suffix are
shared with New SNPs; the rest are the same rules Full Pipeline uses.

| Step | Rule file |
|---|---|
| Assembly scan (new genomes) | `assembly_scan_new_full.smk` |
| MLST (new genomes, merged summary) | `mlst_new.smk` |
| MRSA detection (`sau`, conditional) | `blastx_MRSA_new_full.smk` |
| Bakta database and annotation (new genomes) | `bakta_db.smk`, `bakta_annotation_new_full.smk` |
| WhatsGNU and public genome retrieval (new genomes) | `whatsgnu_new_full.smk`, `unique_topgenomes_new_full.smk`, `datasets_topgenomes.smk` |
| SNP distances and matrix merge | `mummer4_study_new_full.smk`, `mummer4_public_new_full.smk`, `snp_matrix_new_full.smk` |
| Pan-genome merge and core alignment | `panaroo_new_full.smk` |
| Core-gene tree, grouping, group alignments and trees | `iqtree_core_gene.smk`, `hierarchical_clustering.smk`, `snippy_input_new_full.smk`, `snippy_groups.smk`, `iqtree_groups.smk` |
| CORE and diagnostics | `thresher_input.smk`, `thresher_plateau.smk`, `thresher_peak.smk`, `thresher_discrepancy.smk`, `thresher_public.smk`, `thresher_MSTP.smk`, `thresher_QC.smk` |
| Plots | `plot_core_gene_tree.smk`, `plot_snp.smk` |
| EPI (conditional) | `plot_cluster_plots_new_full.smk`, `plot_persistence_plot_new_full.smk` |

MRSA rules are included only when the prior run contains `blastx/mrsa/`, and the EPI rules only
when it contains `clusters_summary.RDS`.

---

## Output of New Full mode

Paths are relative to the New Full `--output` directory.

### Outputs that carry Full Pipeline names

These files have the same names, columns, and interpretation as in Full Pipeline, now covering
the combined dataset. See the Full Pipeline guide for how to read each one.

| Output | Contents |
|---|---|
| `thresher/output/{plateau,peak,discrepancy,public}_strains.csv` and `.RDS` | Strains for the combined dataset: `strain_id` (`<group>_<number>`) and `genome` |
| `thresher/output/group_{plateau,peak,discrepancy,public}.csv` | Re-inferred phylothreshold per group for each endpoint |
| `thresher/output/MSTP/Group{Group_ID}_MSTP.pdf`, `MSTP.RDS` | Multi-SNP-Threshold Plot per group over the re-scanned threshold range |
| `thresher/output/QC/{endpoint}_qc_plot.pdf`, `_qc_table.csv` | Between-strain SNP versus phylogenetic distance, within and between groups |
| `thresher/input/hierarchical_clustering_groups_simplified.csv`, `.RDS`, `thresher_input.RDS` | New group assignments with the `overlimit` flag, and the per-threshold CORE record |
| `plots/core_gene_tree_group.pdf`, `plots/core_gene_tree_mlst.pdf`, `plots/SNP_Distance.pdf` | Combined-dataset phylogeny and SNP distance distribution |
| `mummer4_study/study_snp_matrix.RDS`, `mummer4_public/public_snp_matrix.RDS` | Merged SNP matrices |
| `mlst/summary/mlst_results.csv` | Sequence types for all genomes, original and new |
| `panaroo/core_gene_alignment_filtered.aln`, `iqtree/`, `snippy/`, `bakta_annotation/`, `whatsgnu/`, `datasets_topgenomes/`, `assembly_scan/` | Merged alignment, phylogenies, and per-genome evidence |
| `thresher/output/clusters_summary.csv` and `.RDS` | Updated transmission clusters, when the prior run had them |

Because these names match, the directory is a valid `--thresher_output` for a later New Full
run and a valid starting point for Redo Endpoint and CladeBreaker OFF.

### Outputs specific to New Full

| Output | Contents |
|---|---|
| `thresher/output/genomes_summary_new_full.csv` | One row per genome: `genome`, `category` (`new` or `original`), `strain`, and `cluster` (`Non-Cluster` when the genome is in no transmission cluster). This is the fastest way to see where the new genomes landed and which original genomes changed strain or cluster |
| `plots/Cluster{cluster_id}.pdf`, `plots/ClusterPlots_new_full.RDS` | Updated cluster plots |
| `plots/PersistencePlot_new_full.pdf` and `.RDS` | Updated persistence across the study period |
| `blastx/mrsa/output/summary/blastx_MRSA_{plateau,peak,discrepancy,public}_strains.csv`, `blastx_MRSA_genomes.csv` | MRSA or MSSA per strain for each endpoint, and per genome (`sau` only) |
| `panaroo_new/final_graph.gml` | Pan-genome graph of the new genomes, kept as a record of what was merged |

The updated transmission clusters follow the endpoint method recorded in the prior run's
`clusters_summary.RDS`, not a value passed on the command line. To change the endpoint, run
`thresher redo-endpoint` on the New Full output.

### What New Full does not produce

New Full does not write the per-group strain composition plots
(`plots/strain_compositions/`). Use the Multi-SNP-Threshold Plots and the QC plots and tables
to judge the re-inferred phylothresholds, and read strain membership from the strain tables and
`genomes_summary_new_full.csv`.

### Comparing a New Full run with the prior run

Strain and cluster IDs are assigned within the new analysis and do not carry over. A strain
labeled `1_1` in the prior run is not necessarily `1_1` here, and group numbering can shift if
the number of hierarchical clustering groups changes. Compare by genome membership, not by ID:

1. Open `genomes_summary_new_full.csv` and check which strain and cluster each original genome
   now belongs to.
2. Compare `group_{endpoint}.csv` with the prior run's to see how far the phylothresholds moved.
3. Where a phylothreshold changed substantially, open that group's Multi-SNP-Threshold Plot to
   see whether the new genomes introduced a different divergence structure or simply extended
   the existing one.

Original genomes changing strain is an expected outcome, not an error: the phylothreshold was
re-inferred from a dataset that now includes the new genomes.

## Parameters that change New Full results

New Full does not inherit the prior run's settings. Every analysis parameter falls back to its
default unless it is passed again, so to keep results comparable, repeat the flags used for the
prior run.

| Parameter | Default | Effect on the result | When to adjust |
|---|---|---|---|
| `--thresher_output` | required | The prior run supplying reused evidence and the starting pan-genome graph | Must be a Full Pipeline or New Full output of the same species |
| `--original_metadata`, `--new_metadata` | required | Which genomes are treated as existing and which as additions | The original table must match the prior run; assemblies in both must still exist |
| `--threshold_floor`, `--threshold_ceiling` | 5, 500 | Bounds of the re-scanned phylothreshold range | Raise the ceiling when added diversity pushes endpoints against it; keep identical to the prior run when comparing phylothresholds |
| `--singleton_threshold` | 100 | Groups whose smallest SNP distance is at or above this value become all singletons; also sets the per-genome `overlimit` flag | Raise for diverse additions; lower for clonal datasets |
| `--plateau_length` | 15 | Required stable run for the plateau endpoint | Shorten when new groups report `No Plateau Found`; lengthen for more conservative phylothresholds |
| `--use_cladebreaker` | `True` | Splits a strain's clade when a matched public genome falls inside it | Set `False` when the public matches plausibly belong to the same strains; compare with `thresher cladebreaker-off` on this output |
| `--correction_bootstrap` | 0 | Minimum support for a clade to justify a phylogenetic correction | Raise to accept only well-supported corrections |
| `--snp_coverage_threshold` | 80 | Coverage below which a pairwise distance is treated as poor quality | Raise when new assemblies are more fragmented than the original set |
| `--core_threshold` | 0.95 | Gene frequency for Panaroo to call a gene core in the merged graph | Lower when the added genomes are divergent enough to shrink the core alignment |
| `--core_bootstrap_method`, `--core_bootstrap_number` | `ultrafast`, 1000 (100 nonparametric) | Support on the rebuilt core-gene tree, which underlies grouping | Match the prior run when comparing groups |
| `--group_bootstrap_method`, `--group_bootstrap_number` | `ultrafast`, 1000 (100 nonparametric) | Support on group trees, which gates phylogenetic correction | Match the prior run; relevant whenever `--correction_bootstrap` is above 0 |
| `--species` | required | Databases and MRSA detection | Must match the prior run |
| `--bakta_db_type` | `full` | `light` annotates less completely, shifting the merged core gene set | Match the prior run so the merged pan-genome stays consistent |
| `--endpoint` | `plateau` | Does not drive the cluster update, which follows the endpoint recorded in the prior run | Use `thresher redo-endpoint` on the New Full output to change the endpoint behind clusters |

Parameters that affect run time or bookkeeping but not the result: `-t/--threads`, `--output`,
`--prefix`, `--conda_prefix`, `--bakta_db_path`, `--whatsgnu_db_path`, `--force`.

**A practical approach.** Repeat the prior run's analysis parameters on the first New Full run
so that any change in strains is attributable to the added genomes rather than to settings.
Inspect the Multi-SNP-Threshold Plots and QC plots afterwards, and adjust only in response to
what they show. Most often a ceiling that the added diversity now reaches, or groups newly
collapsing into singletons.

## Changing parameters without rerunning New Full

| Parameter to change | Path |
|---|---|
| Endpoint behind transmission clusters | `thresher redo-endpoint` on the New Full output |
| Threshold floor, ceiling, singleton threshold, plateau length, correction bootstrap, with CladeBreaker disabled | `thresher cladebreaker-off` on the New Full output |
| Any of those with CladeBreaker enabled | Rerun `thresher new-full` |
| Anything in PREP, such as coverage threshold, core threshold, or bootstrap settings | Rerun `thresher new-full` |


## Run time, resources, and interrupted runs

New Full is cheaper than rerunning Full Pipeline on everything, because annotation, MLST,
WhatsGNU, original-versus-original SNP distances, and the original pan-genome graph are not
recomputed. It is still far more expensive than New SNPs: the core-gene tree, hierarchical
clustering, group alignments, group trees, and the full threshold scan all run again on the
combined dataset, and the number of new pairwise comparisons grows with the size of the
original dataset as well as the number of additions.

Raise `-t/--threads` within available memory: Snakemake runs independent jobs in parallel.
Bakta is parallelized across genomes rather than within one — each new genome is annotated by
its own single-threaded job, and Snakemake runs as many of those concurrently as `-t/--threads`
allows. Each job needs about 10 GB of RAM, so set the thread count so that at least 10 GB is
available per thread; above that ratio the annotation jobs are killed by the OOM killer. With
50 GB of RAM, 4 threads runs cleanly and 10 threads does not.

An interrupted run resumes from the last completed step. Unlock first, then resume:

```bash
bash <output>/resume/unlock_snakemake_<prefix>.sh
bash <output>/resume/resume_snakemake_<prefix>.sh
```

For incremental and cummulative surveillance, a workable pattern is New SNPs between batches for a fast answer,
and New Full periodically. Whenever a batch adds unfamiliar genetic backgrounds, New Full can be run to bring the
phylothresholds back in line with the dataset.

## Common causes of failure or misleading New Full output

- Prior directory missing required files, where the run stops during validation with the missing files listed.
  Start from the Full Pipeline or New Full directory instead.
- Original assemblies moved, renamed, or deleted since the prior run so that the new-versus-original
  MUMmer4 comparisons cannot be made.
- Original metadata that does not match the prior run, where genomes present in the table but not in
  the prior output, or renamed genomes, break the reuse of per-genome results.
- 3-column new metadata when the prior run defined transmission clusters. Patient IDs and
  collection dates are required to update them.
- Treating a changed strain composition as instability. Re-inferred phylothresholds are the
  intended behavior of this mode. When the intent was to keep the earlier phylothresholds, New SNPs
  was the right mode.
  