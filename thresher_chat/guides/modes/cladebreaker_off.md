# THRESHER CladeBreaker OFF Mode — Guide

> Explains what CladeBreaker OFF mode does, when to use it, what it requires as input, what it
> produces, and which parameters change the result. Rationale, decision logic, and
> interpretation only; the complete option list and output file inventory are in
> `docs/usage_cladebreaker_off.md` in the THRESHER repository.

Command: `thresher cladebreaker-off`

---

## 1. What CladeBreaker OFF mode does

CladeBreaker OFF re-determines strains from a completed run with CladeBreaker disabled. It
reuses that run's SNP matrices, hierarchical clustering groups, and phylogenies, then re-scans
the candidate phylothresholds and re-selects an endpoint for every group using phylogenetic
correction alone.

CladeBreaker is the step that treats a matched public genome falling inside a study clade as
evidence that the clade spans more than one strain, and splits it. Its premise is that study
strains are hyperlocal: a publicly available genome from elsewhere should not sit inside one.
Disabling it removes that constraint, so strains are bounded by SNP single linkage and the
group phylogeny only.

Two properties matter:

- **Phylothresholds are re-inferred, not just strain membership.** CladeBreaker changes the
  strain composition at every candidate threshold, so the plateau, peak, discrepancy, and
  public endpoints can all land on different values once it is off.
- **The output is a comparison, not a new analysis directory.** Results carry Full Pipeline
  names, but the directory holds only the CORE results layer — no SNP matrices, phylogenies,
  annotations, or metadata — so it cannot serve as the `--thresher_output` for any other mode.
  Later modes still start from the original Full Pipeline or New Full run.

---

## 2. When to use CladeBreaker OFF mode

Use CladeBreaker OFF when:

- public genomes may plausibly belong to the same strains as the study genomes — isolates from
  the same institution, region, or outbreak deposited earlier, or a lineage well represented in
  GenBank. CladeBreaker would split study strains that are genuinely one strain, and this mode
  shows what the data say without that assumption;
- the strain count under CladeBreaker looks inflated, or strain composition plots show public
  genomes sitting inside study clades;
- the effect of CladeBreaker on a dataset needs to be quantified, by reading the two runs side
  by side.

Do not use CladeBreaker OFF when:

| Situation | Use instead |
|---|---|
| CladeBreaker should stay off and no prior run exists | `thresher full` with `--use_cladebreaker False` |
| Transmission clusters are needed under the uncorrected strains | `thresher full` with `--use_cladebreaker False`, which runs EPI |
| A different endpoint behind transmission clusters, CladeBreaker unchanged | `thresher redo-endpoint` |
| Genomes are being added | `thresher new-snps` or `thresher new-full` |
| No completed run exists | `thresher full` |

CladeBreaker OFF answers a diagnostic question about an existing analysis. When the uncorrected
strains are the ones to report, and transmission clusters are part of the report, run Full
Pipeline with `--use_cladebreaker False` so the result is a complete, reusable analysis.

---

## 3. Input required by CladeBreaker OFF mode

### 3.1 The completed prior run (`--thresher_output`)

The only required input. No metadata table and no genome assemblies are needed, because nothing
is annotated, aligned, or compared again. A Full Pipeline or New Full output directory must
contain:

| Required content | Path in the prior run |
|---|---|
| Hierarchical clustering groups | `thresher/input/hierarchical_clustering_groups.RDS` |
| The prior per-threshold CORE record | `thresher/input/thresher_input.RDS` |
| Study SNP matrix | `mummer4_study/study_snp_matrix.RDS` |
| Public SNP matrix | `mummer4_public/public_snp_matrix.RDS` |
| Group phylogenies | `iqtree/group_tree/iqtree_group.txt` and the trees in that directory |
| Core-gene phylogeny, used by QC | `iqtree/core_gene_tree/core_gene_tree.contree` |

The validator checks the first five and stops with the missing files listed; the core-gene tree
is required by the QC step, so a directory lacking it fails later in the run rather than at
validation.

A New SNPs output and another CladeBreaker OFF output are not valid starting points: neither
contains the SNP matrices and phylogenies this mode reads.

### 3.2 System requirements

Light. No databases, no internet access beyond creating conda environments, and no operating
system or RAM check — this mode has no `--force` flag. Pass `--conda_prefix` pointing at the
prior run's environments to skip environment creation entirely.

### 3.3 Minimal invocation

```bash
thresher cladebreaker-off \
  --thresher_output thresher_run \
  -o thresher_run_cladebreaker_off \
  -t 16 \
  --conda_prefix thresher_run/conda_envs_2026_01_15_120000
```

---

## 4. What CladeBreaker OFF mode computes

### 4.1 Reused versus recomputed

| Component | Source |
|---|---|
| Study and public SNP matrices | Reused from the prior run |
| Hierarchical clustering groups | Reused from the prior run |
| Core-gene and group phylogenies | Reused from the prior run |
| Threshold scan across the candidate range | **Recomputed** with CladeBreaker disabled |
| Phylothresholds and strains for all four endpoints | **Recomputed** |
| Multi-SNP-Threshold Plots, QC plots and tables, strain composition plots | **Recomputed** from the uncorrected strains |
| Transmission clusters, MLST, MRSA, core-gene tree plots, SNP distance plot | Not produced |

### 4.2 What changes inside the scan

At each candidate threshold, THRESHER links genomes by SNP single linkage and reconciles the
result with the group phylogeny, keeping corrections whose clade support meets
`--correction_bootstrap`. With CladeBreaker enabled, a corrected clade containing a matched
public genome is then split. With CladeBreaker off, that final step is skipped, so:

- a strain can span a clade that also contains public genomes;
- strains are generally fewer and larger, and phylothresholds generally equal or higher;
- public genomes stay on the group phylogeny as context but are excluded from strain membership
  in the strain composition plots.

### 4.3 Rule files

| Step | Rule file |
|---|---|
| Threshold scan with CladeBreaker disabled | `thresher_input_cladebreaker_off.smk` |
| Endpoint selection, all four methods | `thresher_strain_cladebreaker_off.smk` (rules `thresher_{plateau,peak,discrepancy,public}_cladebreaker_off`) |
| QC plots and tables | `thresher_QC_cladebreaker_off.smk` |
| Multi-SNP-Threshold Plots | `thresher_MSTP.smk`, shared with Full Pipeline |
| Strain composition plots | `plot_strain_compositions_cladebreaker_off.smk` |

The endpoint rules call the same scripts as Full Pipeline, so the endpoint definitions are
identical; only the compositions they choose from differ.

---

## 5. Output of CladeBreaker OFF mode

Paths are relative to the CladeBreaker OFF `--output` directory. File names match Full Pipeline,
which makes side-by-side comparison straightforward.

| Output | Contents |
|---|---|
| `thresher/output/{plateau,peak,discrepancy,public}_strains.csv` and `.RDS` | Uncorrected strains: `strain_id` (`<group>_<number>`) and `genome` |
| `thresher/output/group_{plateau,peak,discrepancy,public}.csv` | Phylothreshold per group for each endpoint, with `plateau_length` recorded in the plateau table |
| `thresher/output/MSTP/Group{Group_ID}_MSTP.pdf`, `MSTP.RDS` | Multi-SNP-Threshold Plot per group, with the uncorrected endpoints annotated |
| `thresher/output/QC/{endpoint}_qc_plot.pdf`, `_qc_table.csv` | Between-strain SNP versus phylogenetic distance, computed against the prior run's core-gene tree |
| `plots/strain_compositions/{endpoint}/Group{Group_ID}_{endpoint}_strain_composition.pdf`, `{endpoint}_strain_tree_snp.RDS` | Group phylogeny beside the SNP heatmap, showing the uncorrected clones |
| `thresher/input/thresher_input.RDS` | The re-scanned per-threshold record, computed without CladeBreaker |

**Not produced:** transmission clusters and cluster plots, MLST and MRSA summaries, core-gene
tree plots, the SNP distance plot, and any updated SNP matrices, phylogenies, or hierarchical
clustering. Those are either unchanged in the prior run or outside this mode's scope.

**Not chainable:** because the directory lacks the SNP matrices, group trees, and metadata that
other modes read, it cannot be passed as `--thresher_output` to Redo Endpoint, New SNPs, New
Full, or another CladeBreaker OFF run. Keep using the original Full Pipeline or New Full
directory for those, and treat this output as the uncorrected counterpart of it.

---

## 6. Parameters that change CladeBreaker OFF results

Settings are not inherited from the prior run. To attribute every difference to CladeBreaker
alone, repeat the threshold parameters the prior run used; anything left out falls back to its
default.

| Parameter | Default | Effect on the result | When to adjust |
|---|---|---|---|
| `--thresher_output` | required | Supplies the SNP matrices, groups, and phylogenies the scan runs on | Must be a Full Pipeline or New Full output |
| `--threshold_ceiling` | 500 | Upper bound of the re-scanned range | Raise when uncorrected endpoints sit at or near the ceiling, which is more likely without CladeBreaker since strains extend further; keep it equal to the prior run when comparing |
| `--threshold_floor` | 5 | Lower bound of the re-scanned range; the effective floor of a group is the larger of this value and the smallest SNP distance observed in that group | Rarely useful to change; keep it equal to the prior run when comparing |
| `--singleton_threshold` | 100 | Groups whose smallest SNP distance is at or above this value become all singletons | Keep equal to the prior run; changing it alters which groups have a phylothreshold at all |
| `--plateau_length` | 15 | Required stable run for the plateau endpoint | Keep equal to the prior run when comparing; shorten only when groups now report `No Plateau Found` |
| `--correction_bootstrap` | 0 | Minimum clade support for a phylogenetic correction to be applied — the only correction left once CladeBreaker is off, so it carries more weight here | Keep equal to the prior run for a clean comparison; raise afterwards to test how much the uncorrected strains depend on weakly supported clades |

Parameters that affect run time or bookkeeping but not the result: `-t/--threads`, `--output`,
`--prefix`, `--conda_prefix`.

There is no `--use_cladebreaker` flag in this mode; it is fixed to `False`. There is no
`--endpoint` flag either, since all four endpoints are reported and no transmission clusters are
built.

---

## 7. Comparing CladeBreaker OFF with the original run

Read the two directories together, file by file, for the same endpoint.

1. **`group_{endpoint}.csv`** — how far each group's phylothreshold moved. Higher values without
   CladeBreaker are the expected direction: the scan is no longer stopped by a public genome
   inside a study clade.
2. **`{endpoint}_strains.csv`** — which strains merged. Compare genome membership rather than
   strain IDs, which are assigned within each run. Strains that CladeBreaker had split usually
   reappear here as one.
3. **`Group{Group_ID}_MSTP.pdf`** — where the endpoints moved along the threshold range, and
   whether the uncorrected curve has a clearer stable stretch.
4. **`{endpoint}_qc_plot.pdf` and `_qc_table.csv`** — whether between-strain distances are still
   cleanly separated from within-strain distances. If the uncorrected strains blur that
   separation, they are absorbing genuinely distinct lineages.
5. **`Group{Group_ID}_{endpoint}_strain_composition.pdf`** — where the public genomes sat. A
   public genome deep inside a clade of study genomes that are only a few SNPs apart is the
   case CladeBreaker was built for; a public genome on a long branch at the clade edge is the
   case where CladeBreaker most likely over-split.

What the comparison supports:

| Observation | Reading |
|---|---|
| Identical or near-identical strains | No public genome fell inside a study clade in the tested range, so CladeBreaker made little difference for this dataset and the strain definitions are robust to the assumption |
| Fewer, larger strains without CladeBreaker | CladeBreaker was splitting those strains on public-genome evidence. Whether that is correct depends on whether the matched public genomes could plausibly belong to the same strain — check their provenance before choosing |
| QC separation worse without CladeBreaker | The merged strains span more diversity than the rest of the dataset supports; the corrected result is the safer one |
| QC separation unchanged or better without CladeBreaker | The public-genome constraint was not adding information for this dataset |

Neither run is automatically right. CladeBreaker encodes a hypothesis about the epidemiology of
the strains, and this mode exists so that hypothesis can be tested rather than assumed.

---

## 8. Run time, resources, and interrupted runs

Faster than Full Pipeline and slower than Redo Endpoint. Nothing is annotated, aligned, or
compared again, but the threshold scan is re-run in full, which is the most expensive part of
CORE: cost grows with the number of groups, the number of genomes per group, and the width of
the range between `--threshold_floor` and `--threshold_ceiling`.

Raise `-t/--threads` to scan groups in parallel. An interrupted run resumes from the last
completed step; unlock first, then resume:

```bash
bash <output>/resume/unlock_snakemake_<prefix>.sh
bash <output>/resume/resume_snakemake_<prefix>.sh
```

---

## 9. Common causes of failure or misleading CladeBreaker OFF output

- `--thresher_output` pointing at a New SNPs output, another CladeBreaker OFF output, or a run
  missing the hierarchical clustering groups, either SNP matrix, `thresher_input.RDS`, or the
  group trees: the run stops during validation with the missing files listed.
- A prior directory without `iqtree/core_gene_tree/core_gene_tree.contree`: validation passes
  but the QC step fails, since QC measures phylogenetic distance on the core-gene tree.
- Threshold parameters different from the prior run: differences in the results then reflect
  both the parameter change and CladeBreaker, and the comparison no longer isolates either.
- Expecting transmission clusters: this mode has no EPI stage. Run Full Pipeline with
  `--use_cladebreaker False` when uncorrected clusters are needed.
- Trying to continue from the output: it holds only the CORE results layer. Point subsequent
  modes at the original Full Pipeline or New Full directory.
- Reading fewer strains as automatically better: without CladeBreaker, strains can absorb
  genomes that belong to separate lineages. Confirm the merge in the QC plots and the strain
  composition plots before adopting it.