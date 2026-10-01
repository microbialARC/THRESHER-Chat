# THRESHER Overview — Guide

> Top-level summary of THRESHER: what it is, why it infers phylothresholds, its stages, its
> five modes, and where detailed information lives. This guide holds rationale and decision
> logic only. Exact CLI options, input formats, and output specifications are in the THRESHER
> repository documentation (`README.md`, `docs/`): https://github.com/microbialARC/THRESHER


## What THRESHER is
THRESHER is a command-line tool for bacterial genomic epidemiology, developed at the
Center for Microbial Medicine, Children's Hospital of Philadelphia. From quality-controlled
genome assemblies of a single species, THRESHER determines strains. When patient identifiers
and collection dates are provided, it also identifies transmission clusters, which are
strains detected in more than one patient. 
In plain language, THRESHER sorts bacterial genomes into groups of close relatives called strains. It does not use one fixed rule for how similar two genomes must be. Instead, it learns that rule from the data and checks every group against the bacteria's phylogenetic tree. When THRESHER also knows which patient each sample came from and when, it reports the families shared by more than one patient.

- Supported species: *Staphylococcus aureus* (`sau`), *Staphylococcus epidermidis* (`sepi`),
  *Clostridioides difficile* (`cdiff`), *Klebsiella pneumoniae* (`kp`).
- Implementation: Snakemake workflows with Python and R. The bioinformatics tools used in each step in the workflow
  are installed into its own conda environment, which makes runs reproducible, parallel, and resumable. Each mode is 
  invoked directly as `thresher <mode>`.
- 
```bash
thresher -h
```

## Why THRESHER uses phylothresholds instead of a fixed SNP cutoff

A fixed SNP cutoff applies one number to every dataset. The SNP distance separating related
isolates varies with species, lineage, surveillance period, outbreak duration, sampling
quality, and dataset size. A single cutoff therefore likely merges distinct strains or splits one
strain, and transmission clusters and outbreak sizes are over- or underestimated.

A phylothreshold is a SNP threshold inferred from the dataset itself and corrected for
phylogenetic topology. THRESHER derives it in four steps:

1. Partition genomes into hierarchical clustering groups and infer a phylothreshold
   separately for each group, because lineages in one dataset differ in diversity.
2. At every candidate threshold, link genomes by SNP single linkage and reconcile the
   groupings with the group phylogeny.
3. Apply CladeBreaker, which uses matched publicly available genomes to constrain strain
   boundaries under the assumption that study strains are hyperlocal.
4. Select each group's final phylothreshold under four endpoint methods.

All four endpoints and all intermediate results are reported, so users evaluate convergence
across hypotheses rather than accept a single number.

## THRESHER stages: INPUT, PREP, CORE, EPI

| Stage | Purpose |
|---|---|
| INPUT | Validates the metadata table, genome files, and parameters before computation starts. |
| PREP | Annotates genomes (Bakta), builds the core-gene alignment and phylogeny (Panaroo, IQ-TREE), assigns MLST, computes all-versus-all study SNP distances (MUMmer4), matches closest public genomes (WhatsGNU, NCBI Datasets) and study–public SNP distances, and partitions genomes into hierarchical clustering groups with a phylogeny per group (Snippy, IQ-TREE). |
| CORE | Scans candidate phylothresholds within each group, correcting SNP-only strain composition with the group phylogeny and applying CladeBreaker, then selects the group phylothreshold and strain composition under all four endpoint methods. |
| EPI | Optional. With patient identifiers and collection dates, reports strains spanning more than one patient as transmission clusters and draws the Transmission Cluster Plot and Cluster Persistence Plot. |

For *S. aureus*, THRESHER additionally labels strains and transmission clusters as MRSA or MSSA.


## Strains, clones, singletons, and transmission clusters in THRESHER

- A strain is a set of study genomes that CORE assigns together at a group's phylothreshold. Strain IDs take the form `<group>_<number>`, for example `1_1`.
- A clone is a strain of at least two genomes. A singleton is a strain of one genome.
- A transmission cluster is a strain whose genomes come from more than one patient, identified in EPI. A strain confined to one patient is not a transmission cluster, even when it contains several genomes from that patient.
- The persistence of a transmission cluster is the number of days between the first and last collection dates of its genomes.

## THRESHER endpoint methods

Each endpoint applies a distinct hypothesis about what evidence defines a strain. Every
mode that determines strains reports all four.

| Endpoint | Selection rule | Hypothesis |
|---|---|---|
| plateau (default) | Start of the first run of consecutive thresholds, at least `--plateau_length` long, over which strain number and composition do not change | A natural gap in divergence separates strains |
| peak | Smallest threshold giving the maximum number of clones after phylogenetic correction | Finest resolution recovering the most distinct clones |
| discrepancy | Lowest discrepancy after the initial discrepancy peak | Strain composition is resolved where strain members are both closely related in SNP distance and consistent with the tree topology |
| public | Smallest good-quality SNP distance between a study genome and a matched public genome, within the tested range | Transmission is hyperlocal where study strains are absent from public databases, so a study genome should never group with a publicly deposited genome of the same species. Thus, the closest public relative marks the strain boundary |

In THRESHER's simulation benchmarks, peak leaned toward specificity, discrepancy toward
sensitivity, and plateau gave an intermediate balance tuned by the plateau length. Start with
plateau, then compare endpoints group by group in the Multi-SNP-Threshold Plot.


## Choosing a THRESHER endpoint method

No THRESHER endpoint is correct for every dataset, because each answers a different question about what a strain is. In THRESHER's simulation benchmarks with known transmission cluster structure, the endpoints spread along a sensitivity–specificity spectrum:

- Peak leaned toward specificity: it grouped fewer unrelated genome pairs but missed more related ones.
- Discrepancy leaned toward sensitivity: it recovered more related pairs but grouped more unrelated ones.
- Plateau gave an intermediate balance that the plateau length tunes. THRESHER's validation identified plateau with length 15 as a well-balanced default.

These patterns come from simulation and are not guaranteed for every dataset. The public endpoint additionally depends on how completely public databases sample the species.

A practical approach is to start with plateau and compare endpoints group by group in the Multi-SNP-Threshold Plot. Where endpoints agree, the strain composition is robust to the choice of hypothesis. Where they disagree, inspect that group's phylogeny and SNP heatmap before deciding. For infection prevention, a sensitivity-oriented endpoint flags more possible links for review, and a specificity-oriented endpoint flags fewer. Redo Endpoint switches the endpoint behind transmission clusters without re-running the pipeline.


## Interpreting THRESHER results: what THRESHER establishes and what the user decides

THRESHER separates two questions.

- The first is whether THRESHER faithfully captures a dataset's genomic structure and infers the phylothreshold and corresponding strains. This is THRESHER's main function.
- The second is whether that structure reflects the biological or epidemiological reality of a setting and serves the purpose at hand. Genomic data alone cannot settle this. The answer rests on the user's knowledge of sampling, setting, and purpose.

A phylothreshold is best read as an attribute of the dataset's genomic structure under a given endpoint hypothesis, not as a verdict. The meaning of "strain" depends on context and purpose. A faithfully inferred phylothreshold can still be too coarse or too fine for a particular investigation, while its groups remain valid strains under another definition. For example, a high plateau phylothreshold can group genomes too broadly to separate clinically meaningful units in one setting, even though those groups remain strains in a broader phylogenetic sense.

THRESHER therefore keeps all evidence for review:

- The Multi-SNP-Threshold Plots (`thresher/output/MSTP/`) show, for each group, how the numbers of clones, singletons, and discrepant genomes and the bootstrap support of strain clades change across tested thresholds, with each endpoint's phylothreshold marked.
- The strain composition plots (`plots/strain_compositions/<endpoint>/`) pair each group's phylogeny with its SNP distance heatmap.
- The QC plots and tables (`thresher/output/QC/`) compare average SNP and phylogenetic distances between strains.
- `plots/SNP_Distance.pdf` shows the overall SNP distance distribution.


## What THRESHER transmission clusters mean for infection prevention and clinical care

A THRESHER transmission cluster means that genomes from two or more patients belong to the same strain at the selected endpoint. The patients' isolates are related closely enough to warrant epidemiological review. The cluster is not proof of direct patient-to-patient transmission.

Genomic data alone cannot determine the direction of transmission (who transmitted to whom) or the route. Linked patients may share an unsampled intermediate source, such as another patient, a healthcare worker, a family member, or the environment. Incomplete sampling can also hide links. Interpret clusters together with epidemiological information such as unit, bed location, overlapping stays, procedures, and staff contacts. Decisions on cohorting, contact tracing, screening, or enhanced precautions remain with the infection prevention and control team under local policy.

The cluster summary reports each cluster's genomes, patients, MLST grouping, first and last collection dates, and persistence. For *S. aureus*, it also reports whether the strain is MRSA or MSSA. A cluster detected over a long period can reflect ongoing transmission or a persistent reservoir rather than a single event. The endpoint choice affects which links are flagged: sensitivity-oriented endpoints flag more possible links, and specificity-oriented endpoints flag fewer.


## Using THRESHER for routine surveillance

THRESHER supports routine surveillance as well as outbreak investigation. A typical sequence is:

- an initial Full Pipeline run,
- New SNPs to place small batches of new isolates quickly against the existing phylothresholds,
- and New Full when many isolates have accumulated or the population structure may have changed, so that phylothresholds are re-inferred from all genomes.

New SNPs output cannot be the input for another run. Each New SNPs run therefore starts from the latest Full Pipeline or New Full output and should list all genomes added since that output was produced. Redo Endpoint lets a team review the same data under a more sensitive or more specific endpoint without recomputation.

THRESHER does not connect directly to laboratory information systems. It reads a tab-delimited metadata table and writes CSV, PDF, and RDS files, which can be exported from and imported into existing systems. THRESHER runs on the user's own Linux system, and patient identifiers and collection dates are used for transmission cluster identification and plots.

## The five THRESHER modes

All modes share the same algorithm and differ in what they recompute and what they reuse.
Full Pipeline is the entry point. Every other mode starts from a completed Full Pipeline or
New Full output directory.

| Mode | Command | Starts from | Phylothresholds | Use it to |
|---|---|---|---|---|
| Full Pipeline | `thresher full` | Genome assemblies and a metadata table | Inferred | Run the first, complete analysis |
| CladeBreaker OFF | `thresher cladebreaker-off` | Completed run output | Re-inferred without CladeBreaker | Re-determine strain composition when a public genome in the group is monophyletic with study genomes after phylogenetic correction |
| Redo Endpoint | `thresher redo-endpoint` | Completed run output and the original 5-column metadata | Unchanged | Rebuild transmission clusters using another endpoint |
| New SNPs | `thresher new-snps` | Completed run output and new genomes | Held fixed | Place a few new genomes into existing strains and clusters using existing phylothresholds |
| New Full | `thresher new-full` | Completed Full Pipeline output and new genomes | Re-inferred from all genomes | Add genomes and update phylothresholds, strains, and clusters |

```bash
thresher full -h
thresher cladebreaker-off -h
thresher redo-endpoint -h
thresher new-snps -h
thresher new-full -h
```

**Decision logic**

- First analysis of a dataset: **Full Pipeline**.
- Strains without CladeBreaker, before any run exists: **Full Pipeline** with `--use_cladebreaker False`.
- Strains without CladeBreaker, after a run exists: **CladeBreaker OFF**, then compare compositions.
- Transmission clusters using a different endpoint: **Redo Endpoint**.
- A few new genomes unlikely to change population structure: **New SNPs**.
- Many new genomes, changed population structure, or phylothresholds that should reflect all genomes: **New Full**.
- Different threshold parameters with CladeBreaker on: rerun **Full Pipeline**; Redo Endpoint does not accept them.

New SNPs writes results under `new_`-prefixed names and cannot serve as the starting point
for another mode. Subsequent runs start from the Full Pipeline or New Full output.


## Installation

```bash
git clone https://github.com/microbialARC/THRESHER
cd THRESHER
bash install.sh
conda activate thresher
thresher -h
```

`install.sh` creates a conda environment named `thresher` and installs the THRESHER package
into it. Snakemake creates additional isolated environments for individual tools on the first
run, which is expected. Full Pipeline and New Full require Linux, at least 40 GB of RAM for
the WhatsGNU database, and internet access for tool and database downloads. Bakta uses about
10 GB of RAM per thread.

## THRESHER codebase layout

| Component | Location |
|---|---|
| CLI entry point and mode routing | `thresher/bin/main.py` |
| Argument parsers, validators, config creation | `thresher/bin/parsers/parser.py`, `thresher/bin/args_validator.py`, `thresher/bin/config_creator.py` |
| Snakefiles, one per mode | `thresher/workflow/Snakefile_full`, `Snakefile_cladebreaker_off`, `Snakefile_redo_endpoint`, `Snakefile_new_snps`, `Snakefile_new_full` |
| Snakemake rules | `thresher/workflow/rules/*.smk` |
| R and Python scripts | `thresher/workflow/scripts/` |
| Conda environment definitions | `thresher/workflow/envs/` |

Mode-specific rules and scripts carry the suffixes `_cladebreaker_off`, `_redo_endpoint`,
`_new_snps`, and `_new_full`.

## Genome Profiler and Evolution Simulator are now SILOSim

THRESHER 0.3.1-beta and earlier included Genome Profiler and Evolution Simulator. Since
0.4.0-beta, THRESHER covers strain and transmission cluster identification only, and these two
modules live in the standalone package SILOSim (https://github.com/microbialARC/SILOSim):
`silosim profiler` infers per-site substitution probabilities and mobile genetic elements from
publicly available genomes, and `silosim simulator` models evolution through substitution,
gene gain and loss, and recombination. The combined release is preserved on the `Legacy`
branch of the THRESHER repository. Questions about running SILOSim are answered from the
SILOSim documentation, not from THRESHER's.

## Naming changes since THRESHER 0.4.0-beta

Older documentation and output directories may use earlier names.

| Earlier name | Current name |
|---|---|
| `thresher strain_identifier <mode>` | `thresher <mode>` |
| `full-pipeline` mode | `full` mode |
| `global` endpoint, global genomes | `public` endpoint, public genomes |
| Comprehensive tree | Core-gene tree |
| `--analysis_mode full` / `lite` | `--epi_mode True` / `False` |
| `Snakefile_strain_identifier_<mode>` | `Snakefile_<mode>` |
| Genome Profiler, Evolution Simulator | SILOSim profiler, SILOSim simulator |

## Knowledge base map

- `guides/modes/` — what each mode computes and reuses, how to choose between them, and how
  to interpret phylothresholds, strains, endpoints, and transmission clusters.
- `guides/concepts/` — the key ideas behind THRESHER, explained one concept per file:
phylothresholds, hierarchical grouping, single linkage, phylogenetic
correction, CladeBreaker, the endpoint methods, and so on. This is where the definitions and equations live.
- Remaining guides — installation and environment troubleshooting, result interpretation,
  validation scope, and FAQs organized by user background.
- THRESHER repository (`README.md`, `docs/`) — exact CLI options, metadata table format,
  required columns, output files, resuming interrupted runs, and conda environment reuse.

Answer questions about definitions, rationale, choice, and interpretation from the guides;
answer questions about commands, inputs, and outputs from the repository documentation.