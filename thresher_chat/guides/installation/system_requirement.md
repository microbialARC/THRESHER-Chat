# System Requirements and Dependencies — Guide

> This document is ingested by the THRESHER-Chat RAG pipeline.
> It explains THRESHER's dependency architecture, what happens during and after
> installation, and why certain system resources are required.
> For the exact installation commands, see the installation guide.

---

## 1. System Requirements

THRESHER requires the following to run:

- **Operating System:** Linux (Ubuntu, CentOS, RHEL, or HPC cluster with Linux nodes)
- **Minimum RAM:** 40 GB for Full Pipeline and New Full modes. This is driven by
  the WhatsGNU database, which must be loaded into memory during Genome Profiler
  and Cladebreaker steps. Future versions will reduce this requirement by
  optimizing WhatsGNU database access. Other modes (Cladebreaker OFF, Redo
  Endpoint, New SNPs) require less RAM because they skip the WhatsGNU step.
- **Internet connection:** Required during installation and during Cladebreaker
  steps that download publicly available genomes from NCBI.
- **Conda:** Miniconda or Anaconda must be installed before running `install.sh`.
- **GNU parallel:** Must be installed system-wide before running `install.sh`.
  On Ubuntu/Debian: `sudo apt install parallel`.
  On Fedora/RHEL: `sudo dnf install parallel`.

THRESHER is publicly available on GitHub: https://github.com/microbialARC/THRESHER

To install:
```bash
git clone https://github.com/microbialARC/THRESHER
cd THRESHER
bash install.sh
conda activate thresher
thresher -h
```

---

## 2. Why Installation Is Two Stages

THRESHER's dependency installation happens in two distinct stages. Understanding
this prevents confusion when the first pipeline run takes longer than expected.

### Stage 1: `install.sh` (runs once, takes minutes)

The installation script creates a single conda environment called `thresher` with
only four core dependencies: Python 3.12, pandas, Snakemake, and PyYAML. These
are defined in `THRESHER/thresher.yml`. This environment is lightweight and fast
to create because it only contains what is needed to launch Snakemake and parse
pipeline configuration.

The `install.sh` script also:
- Checks that conda and GNU parallel are available
- Detects if a `thresher` environment already exists (use `--force` to reinstall)
- Installs the THRESHER Python package via `pip install`

### Stage 2: First pipeline run (automatic, takes longer)

When you run a THRESHER pipeline for the first time, Snakemake automatically
creates additional isolated conda environments for each bioinformatics tool.
This is controlled by Snakemake's `--use-conda` mechanism. Each environment is
defined by a YAML file in `thresher/workflow/envs/` and is only created once —
subsequent runs reuse the existing environments.

This two-stage design is intentional: it keeps the initial install fast and
ensures each tool runs in a conflict-free environment with pinned versions.

---

## 3. Tool Environments and What They Provide

Each Snakemake rule runs inside its own conda environment. The table below lists
every environment, the tool it provides, which THRESHER module uses it, and what
it does in the pipeline.

| Environment YAML | Tool | Used By | Purpose |
|---|---|---|---|
| `thresher.yml` | Snakemake, pandas, Python 3.12 | All modules | Core orchestration — launches the pipeline and manages workflow |
| `mummer4.yaml` | MUMmer4 4.0.0rc1, Perl-BioPerl | Strain Identifier | SNP distance calculation |
| `snippy.yaml` | Snippy 4.6.0, samtools, BWA, freebayes | Strain Identifier |  Core genome alignment |
| `iqtree.yaml` | IQ-TREE 2.3.6 | Strain Identifier | Maximum likelihood phylogenetic tree construction |
| `R_env.yaml` | R 4.4+, ape, phytools, ggtree, ggplot2 | Strain Identifier, Genome Profiler, Evolution Simulator | Phylothreshold computation, statistical analysis, and visualization |
| `mlst.yaml` | mlst 2.23.0 | Strain Identifier | Multi-locus sequence typing for species confirmation |
| `bakta.yaml` | Bakta 1.11.4, PyHMMER, Aragorn, Infernal | Strain Identifier, Genome Profiler | Genome annotation — identifies genes, CDS, rRNA, tRNA, and MGEs |
| `whatsgnu.yaml` | WhatsGNU 1.5.0 | Genome Profiler, Strain Identifier (Cladebreaker) | Protein novelty scoring against GenBank database — estimates mutation probability |
| `blast.yaml` | BLAST 2.16.0 | Genome Profiler, Strain Identifier (Species: Staphylococcus aureus) | Sequence similarity search for MGE identification |
| `fastani.yaml` | FastANI 1.34 | Strain Identifier | Average nucleotide identity for species-level classification |
| `datasets.yaml` | NCBI datasets CLI 18.9.0 | Strain Identifier (Cladebreaker) | Downloads publicly available genomes from NCBI for phylogenetic correction |
| `panaroo.yaml` | Panaroo 1.5.1, Python 3.9 | Strain Identifier | Pan-genome analysis — identifies core and accessory genes |
| `assmbly_scan.yaml` | assembly-scan 1.0.0 | Strain Identifier | Genome assembly quality metrics (N50, contigs, total length) |
| `evo_simulator.yaml` | Python 3.12, NumPy, BioPython, snp-dists | Evolution Simulator | Bacterial evolution simulation with mutation and recombination |

### Why so many environments?

Bioinformatics tools frequently have conflicting dependencies. For example,
Bakta requires Python 3.11 with specific library versions, while Panaroo
requires Python 3.9, and the core pipeline uses Python 3.12. Installing all
tools into a single environment would create unresolvable dependency conflicts.

Snakemake's `--use-conda` mechanism solves this by giving each tool its own
isolated environment. The tradeoff is disk space (each environment is
self-contained) and first-run time (all environments must be created once).
After the first run, environments are cached and reused.

---

## 4. What to Expect at First Run

When you launch a THRESHER pipeline for the first time after installation:

1. **Snakemake will create conda environments** — you will see messages like
   "Creating conda environment from thresher/workflow/envs/mummer4.yaml..."
   for each tool. This is normal and expected.

2. **First run takes significantly longer** — environment creation can add
   30–60 minutes depending on internet speed and conda solver performance.
   Subsequent runs skip this step entirely.

3. **Large downloads may occur** — some environments (particularly Bakta and
   Snippy) have hundreds of pinned dependencies and require significant
   downloads. The Bakta environment alone includes over 100 packages.

4. **WhatsGNU database download** — if running Full Pipeline or modes that
   use Cladebreaker, the WhatsGNU database for the target species will be
   downloaded. This database can be several gigabytes and must fit in RAM
   during execution, which is why 40 GB RAM is required.

---

## 5. Common Dependency Issues

### "conda: command not found"
Conda is not installed or not in your PATH. Install Miniconda first, then
restart your terminal or run `source ~/.bashrc`.

### "GNU parallel is not installed"
GNU parallel must be installed system-wide before running `install.sh`.
On Ubuntu/Debian: `sudo apt install parallel`.
On Fedora/RHEL: `sudo dnf install parallel`.
On HPC systems: try `module load parallel` before running the pipeline.

### "Detected existing conda environment 'thresher' but --force flag not set"
A `thresher` conda environment already exists. If you want to reinstall,
run: `bash install.sh --force`. If the environment is corrupted, remove it
first with `conda env remove -n thresher` and rerun `bash install.sh`.

### Snakemake environment creation fails
If a specific tool environment fails to create (e.g., solver timeout or
network error), Snakemake will report which YAML file failed. You can retry
the pipeline run — Snakemake will only attempt to create the environments
that haven't been successfully built yet.

### Out of memory during WhatsGNU step
The WhatsGNU database must be loaded entirely into memory. If your system
has less than 40 GB RAM, the process will be killed by the OS (OOM). On HPC
systems, request a node with sufficient memory. This requirement applies
only to modes that use WhatsGNU (Full Pipeline, New Full, and any mode
with Cladebreaker enabled).

### Disk space
Disk usage has three major components:

1. **Conda environments** — all tool environments combined require approximately
   10–20 GB in the Snakemake `.snakemake/conda/` directory within your working
   directory.

2. **Bakta database** — required for genome annotation. If you do not provide a
   pre-downloaded Bakta database, THRESHER will download it automatically on
   first run. The full Bakta database is approximately 30–40 GB.

3. **WhatsGNU database** — required for protein novelty scoring during Genome
   Profiler and Cladebreaker steps. If you do not provide a pre-downloaded
   WhatsGNU database, THRESHER will download it automatically. The WhatsGNU
   database is approximately 30–40 GB depending on the target species.

If you do not provide either database, THRESHER will download both from
scratch, adding 60–80 GB to your disk usage on top of the conda environments.
On HPC systems with limited home directory quotas, point database storage to
a scratch or project filesystem with sufficient space.

To avoid repeated downloads across projects, you can download the databases
once and provide their paths in the THRESHER configuration. Refer to the
THRESHER documentation for the exact configuration parameters.