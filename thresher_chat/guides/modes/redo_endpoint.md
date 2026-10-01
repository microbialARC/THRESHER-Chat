# THRESHER Redo Endpoint Mode — Guide

> Explains what Redo Endpoint mode does, when to use it, what it requires as input, what it
> produces, and which parameters change the result. Rationale, decision logic, and
> interpretation only; the complete option list and output file inventory are in
> `docs/usage_redo_endpoint.md` in the THRESHER repository.

Command: `thresher redo-endpoint`

## What Redo Endpoint mode does

Redo Endpoint rebuilds transmission clusters from a completed run using a different endpoint
method. Every mode that determines strains already reports all four endpoints (plateau, peak,
discrepancy, public), but only one of them is used to determine the transmission clusters and 
to produce the cluster plots. Redo Endpoint reads the strain composition of the endpoint chosen
with `--endpoint`, regroups those strains by patient, and regenerates the cluster summary, 
cluster plots, and persistence plot.

Nothing is recomputed. No genome is annotated, aligned, or compared, no phylogeny is inferred,
and no phylothreshold is re-inferred. The strains for the requested endpoint were determined in
the prior run and are used exactly as they are. This is the cheapest mode in THRESHER,
typically finishing in minutes.

Two properties follow from that:

- **It can add transmission clusters to a strain-only run.** Clusters are built from the strain
  tables and the metadata, not from an earlier cluster summary, so a run executed with
  `--epi_mode False` gains clusters here as long as 5-column metadata is available.
- **The output is a cluster result, not an analysis directory.** It contains cluster summaries
  and plots only, so it cannot be passed as `--thresher_output` to any other mode.

## When to use Redo Endpoint mode

Use Redo Endpoint when:

- the strain definitions are settled and the question is how the choice of endpoint changes the 
  landscape of transmission clusters, such as how many clusters, which patients are linked, how long
  they persist;
- a run was executed with `--epi_mode False` but patient identifiers and collection dates are
  available;
- all four endpoints need to be compared as transmission results, which means running this mode
  once per endpoint into separate output directories.

Do not use Redo Endpoint when:

| Situation | Use instead |
|---|---|
| Anything that changes strain composition: threshold floor or ceiling, singleton threshold, plateau length, correction bootstrap | `thresher full` |
| Strains without CladeBreaker | `thresher cladebreaker-off`, then `thresher full` with `--use_cladebreaker False` if clusters are needed |
| Genomes are being added | `thresher new-snps` or `thresher new-full` |
| No completed run exists | `thresher full` |

Changing `--plateau_length` is a common point of confusion: it changes which phylothreshold the
plateau endpoint selects, so it belongs to a run that determines strains, not to this mode.

## Input required by Redo Endpoint mode

No genome assemblies are read, and no species flag is needed.

### The completed prior run (`--thresher_output`)

A Full Pipeline or New Full output directory containing:

| Required content | Path in the prior run |
|---|---|
| Strain tables for all four endpoints | `thresher/output/{plateau,peak,discrepancy,public}_strains.RDS` |
| MLST results, used to annotate clusters | `mlst/summary/mlst_results.csv` |
| MRSA strain calls, optional | `blastx/mrsa/output/summary/blastx_MRSA_strains.csv` |

Validation checks the four strain tables and stops with the missing files listed. The MLST file
is required by the rule itself, so a directory without it fails once the run starts.

- A **New SNPs output is not valid**: its strain tables carry `new_` prefixes.
- A **CladeBreaker OFF output is not valid**: it has the four strain tables but no MLST results.
- When the MRSA strain summary is absent, the `AMR` column is filled with `N/A` and the MRSA
  annotation is left off the cluster plots. This is the normal case for a New Full prior run,
  which writes per-endpoint MRSA tables (`blastx_MRSA_{endpoint}_strains.csv`) rather than the
  single `blastx_MRSA_strains.csv` this mode looks for.

### Original metadata (`--original_metadata`)

The metadata table from the prior run, tab-delimited and with **exactly 5 columns**: genome
name, GenBank accession, genome path, patient ID, collection date in `yyyy-mm-dd`. Transmission
clusters are defined by patients and dates, so a 3-column table is rejected. The genome paths
are not opened; only the names, patient IDs, and dates are used.

### Endpoint (`--endpoint`)

One of `plateau` (default), `peak`, `discrepancy`, or `public`. An unrecognized value is
replaced by `plateau` with a printed notice rather than stopping the run, so check
`config/config_{prefix}.yaml` in the output if there is any doubt about which endpoint was used.

### System requirements

The system requirement for redo endpoint mode is minimal. No databases, no downloads beyond creating 
conda environments, no OS or RAM check, and no `--threads` option. The workload is a single R step. 
Pass `--conda_prefix` pointing at the prior run's environments to skip environment creation.

### Quick Start

```bash
thresher redo-endpoint \
  --thresher_output thresher_run \
  --original_metadata original_metadata.txt \
  --endpoint discrepancy \
  -o thresher_run_discrepancy_clusters \
  --conda_prefix /path/to/conda/envs
```

## What Redo Endpoint mode computes

1. The strain table for the requested endpoint is loaded from the prior run.
2. Each strain is matched to its genomes' patients and collection dates from the metadata, and
   annotated with the MLST grouping and, when available, the MRSA or MSSA call (if species is *S. aureus*).
3. Strains carrying genomes from more than one patient become transmission clusters. Clusters
   are numbered sequentially within this run.
4. Cluster plots and a persistence plot are drawn for the resulting clusters.

Because cluster numbering starts fresh, cluster IDs from different Redo Endpoint runs and from
the prior run are not comparable. Compare clusters by their genomes and patients.

Rule files: `plot_cluster_plots_redo_endpoint.smk` (cluster summary and cluster plots) and
`plot_persistence_plot_redo_endpoint.smk` (persistence plot).

## Output of Redo Endpoint mode

Paths are relative to the Redo Endpoint `--output` directory. Names carry the `_redo_endpoint`
suffix so results cannot be confused with the prior run's.

| Output | Contents |
|---|---|
| `files/clusters_summary_redo_endpoint.csv` and `.RDS` | Transmission clusters under the selected endpoint |
| `plots/Cluster{cluster_id}.pdf` | One plot per cluster, showing the patients involved, the cluster ID, the MLST grouping, and, for *S. aureus* with MRSA results available, the MRSA or MSSA label |
| `plots/ClusterPlots_redo_endpoint.RDS` | All cluster plots as R objects |
| `plots/PersistencePlot_redo_endpoint.pdf` and `.RDS` | Cluster persistence across the study period |
| `config/config_{prefix}.yaml` | The parameters this run used, including the endpoint actually applied |

Cluster summary columns:

| Column | Content |
|---|---|
| `cluster` | Cluster ID, numbered within this run |
| `strain` | Strain ID from the prior run's strain table for this endpoint |
| `MLST` | Broader MLST grouping, for example clonal complex in *S. aureus* |
| `AMR` | MRSA or MSSA when the prior run's MRSA strain summary exists, otherwise `N/A` |
| `genomes` | Genome names in the cluster, separated by a pipe character |
| `patients` | Patient IDs in the cluster, separated by a pipe character |
| `first_seen`, `last_seen` | Earliest and latest collection dates in the cluster, formatted `yy-mm-dd` |
| `persistence` | Days between `first_seen` and `last_seen` |

When no strain spans more than one patient, the summary contains `No Clusters Found` and no
cluster plots are drawn. Under a strict endpoint this is a real result, not an error.

**Not produced:** strain tables, group phylothresholds, Multi-SNP-Threshold Plots, QC plots and
tables, strain composition plots, SNP matrices, or phylogenies. All of those belong to the prior
run and are unchanged by the choice of endpoint for clusters.

**Not As Input:** no other mode accepts this directory as `--thresher_output`. Keep pointing
subsequent runs at the original Full Pipeline or New Full directory.

## Parameters that change Redo Endpoint results

| Parameter | Default | Effect on the result | When to adjust |
|---|---|---|---|
| `--endpoint` | `plateau` | Selects which of the prior run's four strain compositions the clusters are built from. The only parameter that changes what the clusters are | Choose the endpoint whose strain definition suits the investigation; run the mode once per endpoint to compare |
| `--thresher_output` | required | Supplies the strain tables, MLST, and MRSA annotation | Must be a Full Pipeline or New Full output |
| `--original_metadata` | required | Supplies the patient IDs and collection dates that define clusters and persistence | Must be the 5-column table matching the prior run's genomes |

Parameters that affect bookkeeping only: `--output`, `--prefix`, `--conda_prefix`.

There are no threshold parameters in this mode. Phylothresholds, CladeBreaker, and grouping are
fixed properties of the prior run.

## Comparing endpoints

Run Redo Endpoint once per endpoint into separate directories, then read the summaries together.

| Observation | Reading |
|---|---|
| The same patients cluster under all four endpoints | The transmission signal is robust to the strain definition and is the strongest evidence this analysis can give |
| Clusters appear only under discrepancy | The linked genomes sit above the stricter endpoints' phylothresholds; treat as a lead to check against epidemiological records rather than as an established link |
| Clusters present under peak but absent under plateau or discrepancy | Unusual, since peak is the more specific endpoint; check that group's Multi-SNP-Threshold Plot in the prior run for an endpoint sitting on an unstable part of the curve |
| Cluster membership grows steadily from peak to discrepancy | The lineage has continuous diversity with no clear divergence gap, so any single phylothreshold is a judgment call; report the range rather than one number |
| Persistence changes markedly between endpoints | A looser definition is absorbing older or newer isolates into the cluster; check `first_seen` and `last_seen` against the sampling window before interpreting a long-persisting reservoir |

Because cluster IDs are assigned within each run, compare the `genomes` and `patients` columns,
not the IDs. The strain IDs also differ between endpoints, since each endpoint selects its own
phylothreshold per group.

Whatever the endpoint, a cluster means two or more patients carry genomes of the same strain.
Direction and route of transmission cannot be inferred from these data, an unsampled
intermediate source may link the patients, and incomplete sampling can hide links.


## Run time, resources, and interrupted runs

This is the fastest mode. Only one R step reading tables the prior run already produced, usually a few
minutes. There is no threading option and no database or network dependency beyond conda
environment creation, which `--conda_prefix` avoids.

If a run is interrupted, unlock and resume:

```bash
bash <output>/resume/unlock_snakemake_<prefix>.sh
bash <output>/resume/resume_snakemake_<prefix>.sh
```

## Common causes of failure or misleading Redo Endpoint output

- `--thresher_output` pointing at a New SNPs output, a CladeBreaker OFF output, or a run missing
  one of the four strain tables: validation stops the run with the missing files listed.
- A prior directory without `mlst/summary/mlst_results.csv`: validation passes, then the cluster
  rule fails on the missing input.
- Metadata with 3 columns, or a table whose genome names do not match the prior run's, so patients
  and dates cannot be attached to the strains.
- An `--endpoint` value that is misspelled: the run silently proceeds with `plateau`. Confirm
  the endpoint in `config/config_{prefix}.yaml`.
- `AMR` reported as `N/A` for an *S. aureus* dataset. The prior run has no
  `blastx_MRSA_strains.csv`, which is expected after New Full. The clusters themselves are
  unaffected.
- Comparing cluster IDs across runs: IDs are assigned per run. Compare genome and patient
  membership.
- Reading a change in cluster count as new evidence: the underlying genomes and SNP distances
  are identical across endpoints. What changed is the definition of a strain, not the data.