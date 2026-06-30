# NuXL Rescoring Workflow

The **NuXL Rescoring Workflow** improves NuXL cross-link identifications by using data-driven features such as retention-time prediction and fragment-ion intensity features. It is typically run after the NuXL search workflow todo annotate the data-driven features with addition of NuXL search engine features. Then the percolator is employed, and CSM-level FDR controlled files are generated.

> ℹ️ **Info:** This workflow is intended to be used after a NuXL search has generated the initial NuXL `.idXML` output.

📌 **Jump to section:** [1. Files](#1-files) | [2. Configure](#2-configure) | [3. Run](#3-run)

---

## 1. Files

![Files-Tab Rescoring](docs/images/rescoring_simple_file.png)

📁 User need **initial NuXL idXML file**. This should be the original NuXL search result before Percolator/FDR filtering.

> ⚠️ **Warning:** Do **not** use already filtered or rescored files, such as files containing filtering pattern of NuXL out.

Examples of files that should not be used as rescoring input:

```text
sample_perc_0.0100_XLs.idXML
sample_perc_1.0000_XLs.idXML
RDDF_sample_perc_0.0100_XLs.idXML
```

You can either upload an initial NuXL `.idXML` file directly or sync already available files from the workspace (if you already analyze the sample with NuXL search engine in same workspace. After upload or sync, the available idXML files are shown in the file table.

> ℹ️ **Info:** If the NuXL search was already performed in the same workspace, syncing files from the workspace is usually enough.

If your file is rejected, check that it is the original NuXL idXML output and not a Percolator/FDR or RDDF file (please check the above constraints).

#### Optional input (MGF file)

📄 An **MGF file** (`.mgf`) is needed when **Max correlation features** are enabled. If you use only retention-time features, an MGF file is not required. you could upload the mgf file and view the MGF files on the page, which should be available for selection in configure step.

> ⚠️ **Warning:** If **Max correlation features** are enabled, a matching MGF file should be selected in the Configure step.

---

### 2. Configure

![Configure-Tab Rescoring](docs/images/rescoring_config.png)

#### Choose a file for rescoring

📄 This option selects the NuXL `.idXML` file that will be rescored.

Example:

```text
RNA_UV_Ecoli_S100_LB_bRfrac_9.idXML
```

#### Choose MGF file for max-correlation features

📄 This option selects the `.mgf` file used for max-correlation based rescoring features. The MGF file is required when **Max correlation features** is enabled. The MGF file should correspond to the same experiment/sample as the selected idXML file. If the wrong MGF file is selected, the rescoring may fail or produce unreliable feature values.

> ⚠️ **Warning:** Select the MGF file from the same experiment/sample as the selected idXML file.

Example:

```text
example_RNA_DEB_Ecoli_S30_LB_bRfrac_9.mgf
```

If **Max correlation features** is disabled, this file is not used.

#### Select the suitable protocol

🧪 This option defines the experimental cross-linking protocol used for the sample. The selected protocol determines which retention-time model and calibration settings are used during rescoring. Choose the option that matches the NuXL experiment.

Examples:

```text
RNA_UV     → use for UV cross-linking experiments (model fine-tuned specific for UV, also use UV calibration)
RNA_DEB    → use for DEB cross-linking experiments (model fine-tuned specific for DEB, also use DEB calibration)
RNA_NM     → use for NM cross-linking experiments (model fine-tuned specific for NM, also use NM calibration)
RNA_4SU    → use for 4SU experiments (model fine-tuned specific for 4SU, also use 4SU calibration)
RNA_Other  → use when the experiment does not match the predefined protocols (model fine-tuned generic, cope all modifications, also use all protcol data as calibration)
```

> ℹ️ **Info:** The selected protocol affects the retention-time prediction model and calibration data used during rescoring.

#### Retention time prediction and features

⏱️ This checkbox enables retention-time based rescoring features.
Disable this only if you want to run rescoring without retention-time information.

#### Max correlation features

📈 This checkbox enables fragment-ion intensity or max-correlation based features. When enabled, the workflow uses the selected MGF file to calculate spectral feature information for rescoring.

> ⚠️ **Warning:** If this option is enabled, an MGF file is required.

#### plot pseudo-ROC

📊 This checkbox enables generation of a pseudo-ROC comparison plot. The plot is used to compare identification behavior before and after rescoring. It is useful for visually checking whether rescoring improves the result.

If the required reference files are not available, the workflow may skip the pseudo-ROC plot. This does not necessarily mean the rescoring failed. If you already run the Nuxl search engine on same rescore file and workspace, it should generate plot.

> ℹ️ **Info:** A skipped pseudo-ROC plot does not necessarily mean the rescoring failed.

#### Load default parameters

⚠️ This button resets the configure tab to the default workflow settings.Use this if parameters were changed and you want to return to the recommended default setup.

#### Export parameters

⬇️ This button downloads the currently selected workflow parameters. Use this if you want to save the analysis settings or reuse them later.

#### Import parameters

⬆️ This allows you to upload a previously exported parameter file.
Use this when you want to repeat an analysis with the same settings.

#### Method summary

🧾 This button generates a text summary of the workflow method and selected parameters. Use this for documentation, reporting, or manuscript method descriptions.

#### Recommended configuration

For most analyses, use:

```text
idXML file: initial NuXL idXML file
MGF file: matching MGF file
Protocol: matching experimental protocol
Retention time prediction and features: enabled
Max correlation features: enabled
plot pseudo-ROC: enabled
```

This runs the full rescoring workflow using both retention-time and spectrmax correlation correlation features.

| Feature                         | Description                                                                                                 |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `rt_diff`                       | Absolute difference between the observed and predicted retention time.                                      |
| `rt_diff_best`                  | Best retention time difference, selected as the minimum `rt_diff` for the same peptidoform.                 |
| `observed_retention_time_best`  | Best observed retention time, selected from the entry with the minimum `rt_diff` for the same peptidoform.  |
| `predicted_retention_time_best` | Best predicted retention time, selected from the entry with the minimum `rt_diff` for the same peptidoform. |
| `max_corr_feature (b_y_corr)`                      | Maximum Pearson correlation calculated between predicted and target intensities of b- and y-ions (for first 3-prefix/suffix ions).           |

These features should be annotated in the `idXML` file and used for rescoring in combination with additional features generated by the NuXL search engine.

---

## 3. Run

This section explains the **Run** tab of the NuXL Rescoring Workflow.

![Run-Tab Rescoring](docs/images/rescoring_run.png)

🚀 The **Run** tab is used to start, monitor, and stop the rescoring analysis.After the workflow is configured, this tab shows the execution controls and the live workflow log. Also could download the result files immidiatly.

#### Summary

🧾 The **Summary** panel contains a short overview of the selected workflow settings and method information.It can be expanded to check the current analysis setup before or during execution. Use this section to confirm that the selected input file, protocol, and feature options are correct.Also, give publication ready citation.

#### Log details

📜 The **Log details** dropdown controls which type of workflow messages are shown in the log window. `all` is shows the full workflow progress and is useful for checking what the workflow is doing.

#### Lines to show

📏 The **lines to show** dropdown controls how many log lines are displayed. `all` is useful when you want to see the full workflow history from start to finish.If the log becomes very long, you can choose fewer lines to show only the most recent messages.

#### Stop Workflow

⛔ The **Stop Workflow** button stops the currently running analysis.

> ⚠️ **Warning:** Stop the workflow only if you need to cancel the current run, for example because the wrong input file, MGF file, protocol, or feature settings were selected.

#### Live workflow log

📜 The log window shows the current progress of the rescoring workflow.

> ℹ️ **Info:** The live log helps track the current analysis step and is useful for troubleshooting if the workflow fails.

#### When the workflow finishes

![Output Rescoring](docs/images/out_rescoring.png)

✅ When the workflow completes successfully, the output files become available for download, visulization and are also available in the Results page. The download folder contains, identification files (with `RDDF_` prefix), PseudoROC if generated, and log file. If the PseudoROC plot success, it will also display after log.

For example, this file `RDDF_sample_perc_0.0100_XLs.idXML` can be used in downstream workflows such as DIA library generation with **Use RDDF identifications** enabled.

---
