# Installation Guide

## Why This Installation Approach

THRESHER uses a two-stage installation design. The first stage (`bash install.sh`) installs only the orchestration layer: a conda environment named `thresher` containing Snakemake and THRESHER's Python scripts. The bioinformatics tools (bakta, mummer4, IQ-TREE, WhatsGNU, etc.) are not installed at this point.

The second stage happens automatically the first time you run a function. Snakemake reads the conda environment YAML files bundled with THRESHER and installs only the tools required for that specific function. This means Strain Identifier and Genome Profiler each pull different tool sets, so you never install tools you do not use.

This design keeps the initial installation fast and minimizes disk space. The tradeoff is that the first run of each function requires an internet connection and takes longer while tools download.

## Prerequisites

- **conda** (Miniconda or Anaconda): Required for environment management. THRESHER creates and manages its own conda environment named `thresher`. If you are unsure whether conda is installed, run `conda --version` in your terminal.
- **Git**: Required to clone the repository from GitHub.
- **Internet connection**: Required during installation and during the first run of each function (for Snakemake to download bioinformatics tools).

## Installation Steps

The installation commands are documented in the THRESHER repository at `docs/installation.md`. The three steps are:

1. Clone the repository: `git clone https://github.com/microbialARC/THRESHER`

    and then

    `cd THRESHER`
2. Run the installation script: `bash install.sh`
3. Activate the environment: `conda activate thresher`

After activation, run `thresher -h` to verify the installation and see available commands.

## What install.sh Does

The installation script performs three actions:

1. Creates a conda environment named `thresher` using the bundled `thresher.yml` specification file.
2. Activates the environment.
3. Installs the THRESHER Python package (via `pip install .`) into that environment, which registers the `thresher` command-line entry point.

It does not install any bioinformatics tools. Those are handled by Snakemake at runtime.

## What Gets Installed Later (At First Run)

When you run a THRESHER function for the first time, Snakemake creates separate conda environments for each rule that requires external tools. For example:

- Strain Identifier's full pipeline will install tools for genome annotation (bakta), pairwise genome comparison (mummer4), phylogenetic tree building (IQ-TREE), and database queries (WhatsGNU).
- Each tool gets its own isolated conda environment under the directory you specified or the default `<OUTPUT>/conda_envs_<YYYY_MM_DD_HHMMSS>`. This ensures that tool dependencies do not conflict with each other or with your base environment.

Subsequent runs reuse these environments using `--conda_prefix` to specify the directory, so only the first run is slow.

## Common Installation Issues

- **conda not found**: Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
- **Permission errors during install.sh**: Ensure you have write access to your conda installation directory. Do not run install.sh with `sudo`.
- **Environment already exists**: If reinstalling, remove the existing environment first with `conda env remove -n thresher`, then re-run `bash install.sh` or use `--force` flag in the install.sh script by running `bash install.sh --force`.
- **First run takes a long time**: This is expected. Snakemake is downloading and installing bioinformatics tools into isolated conda environments. Subsequent runs will be faster.
- **First run fails with network errors**: Ensure you have an active internet connection. Snakemake needs to download tool packages from conda channels.

## Verifying Installation

After installation, run:

```bash
conda activate thresher
thresher -h
```

This should display the THRESHER help message listing available commands (strain_identifier, genome_profiler, etc.). If you see the help output, installation was successful.