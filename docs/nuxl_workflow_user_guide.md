# NuXL Workflow

The **NuXL Workflow** performs the initial NuXL search for protein–nucleic acid cross-link identification. It uses one MS input file and one FASTA database, runs OpenNuXL, applies Percolator/FDR reporting, and generates CSM-level cross-link identification files.

Use this workflow when user want to search `.mzML` or `.raw` MS data against a FASTA database and generate NuXL cross-link identifications for downstream analysis, result visualization, or rescoring.

> ℹ️ **Info:** This workflow should normally be run before the NuXL Rescoring Workflow and before DIA library generation.

📌 **Jump to section:** [1. Files](#1-files) | [2. Configure](#2-configure) | [3. Run](#3-run)

---

## 1. Files

![Files-Tab NuXL](images/nuxl_files.png)

📁 The **Files** tab is used to make MS files and FASTA databases available for the NuXL workflow.

Click **Sync files from workspace** to make the current workspace files available for this workflow.

#### MS files

The workflow needs one MS input file.

Supported file types:

```text
.mzML
.raw
```

> ⚠️ **Warning:** NuXL expects exactly one MS input file for one workflow run.

The selected MS file should contain the spectra that will be searched by OpenNuXL.

#### FASTA databases

The workflow also needs one FASTA protein database.

Supported file types:

```text
.fasta
```

> ⚠️ **Warning:** NuXL expects exactly one FASTA database for one workflow run.

The FASTA file should contain the protein sequences used for database search. If the wrong FASTA database is selected, the identifications may be incomplete or incorrect.

#### Download files

The **Download files** button can be used to download files that are available in the workflow input area.

---

## 2. Configure

![Config-Tab NuXL](images/nuxl_config.png)


The **Configure** tab is used to select the input files and define the NuXL search parameters.

#### MS data

📄 This option selects the MS file for the NuXL search.

Example:

```text
example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9.mzML
```

#### FASTA database

📄 This option selects the FASTA database used for the NuXL search.

Example:

```text
example_Ecoli_SwPr_canon_20220310_4400seq_MQ2030contaminants.fasta
```

#### NuXL parameter table

| Parameter | Default shown | Description |
| --- | --- | --- |
| `MS data` | selected `.mzML` file | MS input file used for the NuXL search. |
| `FASTA database` | selected `.fasta` file | Protein database used for matching peptide sequences. |
| `enzyme` | `Trypsin/P` | Digestion enzyme used for peptide generation. |
| `missed cleavages` | `2` | Maximum number of missed enzymatic cleavages allowed per peptide. |
| `peptide min length` | `6` | Minimum peptide length considered during the search. |
| `peptide max length` | `1000000` | Maximum peptide length considered during the search. |
| `precursor mass tolerance` | `6.00` | Allowed precursor mass deviation. |
| `precursor mass tolerance unit` | `ppm` | Unit for precursor mass tolerance. |
| `fragment mass tolerance` | `20.00` | Allowed fragment ion mass deviation. |
| `fragment mass tolerance unit` | `ppm` | Unit for fragment mass tolerance. |
| `select the suitable preset` | `RNA-UV (U)` | NuXL preset describing the nucleic-acid cross-linking chemistry/modification setting. |
| `length of oligonucleotide` | `2` | Oligonucleotide length considered by NuXL. |
| `select fixed modifications` | none selected | Fixed peptide modifications applied to all matching residues. |
| `select variable modifications` | `Oxidation (M)` | Variable peptide modifications considered during the search. |
| `variable modification max per peptide` | `2` | Maximum number of variable modifications allowed per peptide. |
| `scoring method` | `slow` | NuXL scoring mode used during the search. |
| `precursor min charge` | `2` | Minimum precursor charge considered. |
| `precursor max charge` | `5` | Maximum precursor charge considered. |
| `peptide FDR` | `0.01` | Peptide-level FDR threshold. |
| `XL FDR` | `[0.01, 0.1, 1.0]` | Cross-link FDR thresholds used for output reporting. |

> ℹ️ **Info:** The default values are the values shown in the Configure tab screenshot. Some options and descriptions are loaded from the OpenMS NuXL parameter configuration.

#### Load default parameters

⚠️ This button resets the Configure tab to the default workflow settings. Use this if parameters were changed and you want to return to the default setup.

#### Export parameters

⬇️ This button downloads the currently selected workflow parameters. Use this if you want to save or reuse the analysis settings.

#### Import parameters

⬆️ This allows you to upload a previously exported parameter file.

#### Method summary

🧾 This button generates a text summary of the selected workflow parameters and method information.

---

## 3. Run

![Run-Tab NuXL](images/nuxl_run.png)


🚀 The **Run** tab is used to start, monitor, and stop the NuXL search.

After the workflow is configured, this tab shows the execution controls and the live workflow log.

#### Summary

🧾 The **Summary** panel contains a short overview of the selected workflow settings and method information. It can be expanded to check the current setup before or during execution.

#### Log details

📜 The **Log details** dropdown controls which type of workflow messages are shown in the log window. `all` is shows the full workflow progress and is useful for checking what the workflow is doing.

#### Lines to show

📏 The **lines to show** dropdown controls how many log lines are displayed.

#### Stop Workflow

⛔ The **Stop Workflow** button stops the currently running NuXL analysis.

#### Live workflow log

📜 The log window shows the current progress of the NuXL workflow.

> ℹ️ **Info:** The live log helps track the current analysis step and is useful for troubleshooting if the workflow fails.

#### When the workflow finishes

![Results output NuXL](images/nuxl_out.png)


✅ When the workflow completes successfully, the NuXL output files become available for download, visualization, and are also available in the Results page.

The download folder contains identification files and the NuXL search parameter log.

Typical output files include:

```text
sample_perc_0.0100_XLs.idXML
sample_perc_0.1000_XLs.idXML
sample_perc_1.0000_XLs.idXML
sample_perc_proteins0.0100_XLs.tsv
sample_perc_proteins0.1000_XLs.tsv
sample_nuxl_search_parameters_YYYYMMDD_HHMMSS.txt
```

The most important files are:

| Output file | Purpose |
| --- | --- |
| `_perc_0.0100_XLs.idXML` | 1% FDR cross-link identifications. |
| `_perc_0.1000_XLs.idXML` | 10% FDR cross-link identifications. |
| `_perc_1.0000_XLs.idXML` | 100% FDR cross-link identifications. |
| `_perc_proteins0.0100_XLs.tsv` | Protein report for 1% FDR. |
| `_perc_proteins0.1000_XLs.tsv` | Protein report for 10% FDR. |
| `_nuxl_search_parameters_*.txt` | Log file containing selected search parameters. |

> ℹ️ **Info:** The `_perc_0.0100_XLs.idXML` output is commonly used for downstream result inspection. The initial NuXL `without_fdr_perc.idXML` file (e-g  `example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9.idXML`) can also be used as input for the NuXL Rescoring Workflow.

---
