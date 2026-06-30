# NuXL DIA Library Workflow

The **NuXL DIA Library Workflow** generates a DIA-compatible spectral library from NuXL identification results. It uses NuXL cross-link and peptide identifications, converts them into library format, and creates output files that can be used for downstream DIA analysis.

Use this workflow when user want to generate a DIA spectral library from NuXL DDA identification results. The workflow can use either original NuXL identifications or RDDF rescored cross-link identifications from the NuXL Rescoring Workflow.

> ℹ️ **Info:** This workflow should normally be run after the NuXL Workflow. If **Use RDDF identifications** is enabled, run the NuXL Rescoring Workflow first.

📌 **Jump to section:** [1. Files](#1-files) | [2. Configure](#2-configure) | [3. Run](#3-run)

---

## 1. Files

![Files-Tab Library](images/library_files.png)

📁 The **Files** tab is used to make MS files, NuXL idXML result files, and optional MSFragger library files available for DIA library generation.

Click **Sync files from workspace** to make the current workspace files available for this workflow.

#### MS files

The workflow needs one or more MS files.

Supported file type:

```text
.mzML
```

The selected MS files are later used in the Configure tab for library generation.

> ⚠️ **Warning:** For each selected MS file, matching NuXL idXML files must be available.

#### idXML files

The workflow uses NuXL idXML result files from the NuXL search output.

For each selected MS file, the workflow expects matching 1% FDR idXML files:

```text
<basename>_perc_0.0100_XLs.idXML
<basename>_perc_0.0100_peptides.idXML
```

If **Use RDDF identifications** is enabled, the workflow expects the rescored cross-link file:

```text
RDDF_<basename>_perc_0.0100_XLs.idXML
```

and still uses the normal peptide file:

```text
<basename>_perc_0.0100_peptides.idXML
```

> ℹ️ **Info:** Only NuXL Percolator 1% idXML files containing `_perc_0.0100` are shown for library generation.

> ⚠️ **Warning:** If the matching idXML pair is missing for a selected MS file, library generation cannot continue.

#### Optional MSFragger TSV library for iRT alignment

📄 An optional MSFragger `.tsv` library can be uploaded for iRT reference alignment.

Supported file type:

```text
.tsv
```

If no MSFragger TSV file is selected, DIA library generation still runs without iRT reference alignment.

> ℹ️ **Info:** This file is optional. Use it only when you want iRT alignment against an external MSFragger library.

---

## 2. Configure

![Configure-Tab Library](images/library_config.png)

The **Configure** tab is used to select MS files and configure library generation options.

#### MS data

📄 This option selects one or more MS files for library generation.

The workflow automatically looks for matching NuXL idXML result files for each selected MS file.

> ⚠️ **Warning:** The selected MS file basename must match the corresponding NuXL idXML output basename.

Example:

```text
example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9.mzML
```

Expected matching idXML files without RDDF:

```text
example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9_perc_0.0100_XLs.idXML
example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9_perc_0.0100_peptides.idXML
```

Expected matching idXML files with RDDF enabled:

```text
RDDF_example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9_perc_0.0100_XLs.idXML
example_RNA_DEB_Ecoli_S30_LB_bRPFfrac_9_perc_0.0100_peptides.idXML
```

#### Optional MSFragger library TSV for iRT alignment

This option selects an optional MSFragger `.tsv` library for iRT alignment.

Default:

```text
None
```

If `None` is selected, the workflow generates the library without iRT reference alignment.

> ℹ️ **Info:** The iRT alignment option is used only when an MSFragger TSV library is selected.

#### Library output file name tag

This text field defines the output name tag for the generated spectral library.

If this field is empty, the workflow automatically generates a timestamped library name.

Example:

```text
library_20260630_013039
```

> ℹ️ **Info:** Leave this field empty if you want the workflow to create an automatic output name.

#### iRT calibration model

This option selects the calibration model used for iRT alignment.

Available options:

```text
linear
piecewise
```

Default:

```text
linear
```

This option is used only when an MSFragger TSV library is selected.

#### Run mzML FileInfo

This checkbox controls whether OpenMS FileInfo is run on each selected MS file.

Default:

```text
enabled
```

When enabled, file information is included in the workflow log.

> ℹ️ **Info:** Keeping this enabled is useful for documentation and troubleshooting.

#### Use RDDF identifications

This checkbox controls whether rescored RDDF cross-link identifications are used.

Default:

```text
disabled
```

When disabled, the workflow uses original NuXL 1% cross-link identifications:

```text
<basename>_perc_0.0100_XLs.idXML
```

When enabled, the workflow uses RDDF rescored cross-link identifications:

```text
RDDF_<basename>_perc_0.0100_XLs.idXML
```

The peptide idXML file is always taken from the original NuXL peptide output:

```text
<basename>_perc_0.0100_peptides.idXML
```

> ⚠️ **Warning:** Enable this option only after the NuXL Rescoring Workflow has generated the matching RDDF cross-link idXML file.

#### Library parameter table

| Parameter | Default shown | Description |
| --- | --- | --- |
| `MS data` | choose an option | One or more `.mzML` files selected for DIA library generation. |
| `Optional MSFragger library TSV for iRT alignment` | `None` | Optional external MSFragger `.tsv` library for iRT alignment. |
| `Library output file name tag` | empty | Custom name tag for the generated library. If empty, a timestamped name is used. |
| `iRT calibration model` | `linear` | Calibration model used only when an MSFragger TSV is selected. |
| `Run mzML FileInfo` | enabled | Runs OpenMS FileInfo on selected MS files and records information in the log. |
| `Use RDDF identifications` | disabled | Uses RDDF rescored cross-link identifications instead of original NuXL cross-link identifications. |

#### Load default parameters

⚠️ This button resets the Configure tab to the default workflow settings.

#### Export parameters

⬇️ This button downloads the currently selected workflow parameters. Use this if you want to save or reuse the analysis settings.

#### Import parameters

⬆️ This allows you to upload a previously exported parameter file.

#### Method summary

🧾 This button generates a text summary of the selected workflow parameters and method information.

---

## 3. Run

![Run-Tab Library](images/library_run.png)

🚀 The **Run** tab is used to start, monitor, and stop the DIA library generation workflow.

After the workflow is configured, this tab shows the execution controls and the live workflow log.

#### Summary

🧾 The **Summary** panel contains a short overview of the selected workflow settings and method information. It can be expanded to check the current setup before or during execution.

#### Log details

📜 The **Log details** dropdown controls which type of workflow messages are shown in the log window.

Recommended setting:

```text
all
```

This shows the full workflow progress.

#### Lines to show

📏 The **lines to show** dropdown controls how many log lines are displayed.

Recommended setting:

```text
all
```

If the log becomes very long, you can choose fewer lines to show only the most recent messages.

#### Stop Workflow

⛔ The **Stop Workflow** button stops the currently running library generation.

> ⚠️ **Warning:** Stop the workflow only if you need to cancel the current run, for example because the wrong MS file, idXML files, or RDDF option was selected.

## Live workflow log

📜 The log window shows the current progress of the library generation workflow.

> ℹ️ **Info:** The workflow automatically matches the required idXML files for each selected MS file.

#### When the workflow finishes

![Output Library](images/library_out.png)

✅ When the workflow completes successfully, the library output files become available for download and are also available in the Results page.

The download folder contains the generated spectral library output files and the library generation log.

Typical output files include:

```text
library_YYYYMMDD_HHMMSS.tsv or given_name.tsv
library_YYYYMMDD_HHMMSS_library_generation.log
all .unknown format file (text files) generated from idXML
```

The most important files are:

| Output file | Purpose |
| --- | --- |
| `.tsv` library file | Main DIA spectral library output. |
| `_library_generation.log` | Log file containing selected files, matched idXML files, parameters, and workflow messages. |
| `.unknown format file (text files) generated from idXML` | all identifications files used. |

> ℹ️ **Info:** The generated library can be downloaded directly after the workflow finishes. The output files are also copied to the Results page.

---
