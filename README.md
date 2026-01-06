# OpenMS NuXL App [![Open Template!](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://openms-template.streamlit.app/)

Welcome to the OpenMS NuXL App, a web application for the NuXL protein-nucleic acid search engine built using [OpenMS](https://openms.de/) and [pyOpenMS](https://pyopenms.readthedocs.io/en/latest/).<br/>
**website:** [https://abi-services.cs.uni-tuebingen.de/nuxl/](https://abi-services.cs.uni-tuebingen.de/nuxl/)

## Description
NuXL is a dedicated software package designed for the analysis of XL-MS (cross-linking mass spectrometry) data obtained from UV and chemically crosslinked protein–RNA/DNA samples. This powerful tool allows for reliable, FDR-controlled assignment of protein–nucleic acid crosslinking sites in samples treated with UV light or chemical crosslinkers. It offers user-friendly matched spectra visualization, including ion annotations.

Rescoring refers to the post-processing of initial identification results to improve discrimination between correct and incorrect matches by incorporating additional evidence, such as predicted retention time or fragment ion intensities. Such approaches have been shown to increase the identification rate.

👉 With NuXL App users can analyze data with NuXL search engine, run rescoring pipeline, and result interpretation with cross-link aware visualization.

- **Reference:** 
    - **NuXL search engine:**
        Welp, L. M., Wulf, A., Chernev, A., Horokhovskyi, Y., Moshkovskii, S., Dybkov, O., ... & Urlaub, H. (2025). Chemical crosslinking extends and complements UV crosslinking in analysis of RNA/DNA nucleic acid–protein interaction sites by mass spectrometry. Nucleic Acids Research, 53(15), gkaf727. [https://doi.org/10.1093/nar/gkaf727](https://doi.org/10.1093/nar/gkaf727)
    - **NuXL rescore:**
        Siraj, A., Bouwmeester, R., Declercq, A., Welp, L., Chernev, A., Wulf, A., ... & Sachsenberg, T. (2024). Intensity and retention time prediction improves the rescoring of protein‐nucleic acid cross‐links. Proteomics, 24(8), 2300144.[https://doi.org/10.1002/pmic.202300144](https://doi.org/10.1002/pmic.202300144)
       
  
**powered by:**

<img src="assets/OpenMS_new.png" width=15%>
  
## Running NuXL locally: Installation as stand-alone tool
### Windows
1. To get started, download and extract the [OpenMS-NuXLApp.zip](https://github.com/Arslan-Siraj/nuxl-app/actions) file from latest successfull action.
2. After installation of `OpenMS-NuXLApp.msi`, The app can then be launched using the corresponding desktop icon.
3. Use app in your default browser. <br/> 

The workspaces for the project will be locally generated in the `workspaces-nuxl-app` directory, and the analysis will run using local resources.
   
## Quickstart 

You can start right away analyzing your data by following the steps below:

### 1. Create a workspace
On the left side of this page you can define a workspace where all your data including uploaded files will be stored. Entering a workspace will switch to an existing one or create a new one if it does not exist yet. In the web app, you can share your results via the unique workspace ID. Be careful with sensitive data, anyone with access to this ID can view your data. 

### 2. 📁 Upload your files
Upload `.mzML`. `.raw` and `.fasta` files via the **File Upload** tab. The data will be stored in your workspace. With the web app you can upload only one file at a time.
Locally there is no limit in files. However, it is recommended to upload large number of files by specifying the path to a directory containing the files.

Your uploaded files will be shown on the same **File Upload** page in  **mzML files** and **Fasta files** tabs. Also you can remove the files from workspace.

Users can download the example files from **Load example file** tab to current workspace.

### 3. ⚙️ Analyze your uploaded data

Select the `.mzML/.raw` and `.fasta` files for analysis, configure user settings including NuXL advanced parameters, and start the analysis using the **Run-analysis** button.

You can terminate the analysis immediately using the **Terminate/Clear** button and you can see the real-time log of search engine.
Once the analysis completed successfully, the output table will be displayed on the page, along with downloadable links for crosslink identification files for that particular analysis.

### 4. ⚙️ Rescoring

Select without FDR-controlled `.idXML` file from output of NuXL search engine. The name of file pattern is `(raw or mzML file_name).idXML`. If the NuxL search engine succesfully run, the file will showup here. After including the features start the analysis using the **Run-rescoring** button.

You can terminate the rescoring analysis immediately using the **Terminate/Clear** button and you can see the real-time log of rescoring.
Once the analysis completed successfully, the comparison PseudoROC curve at CSM-level FDR will generated, and available for download.

#### 5. 📊 View your results
Here, you can visualize and explore the output of the search engine. All crosslink output files in the workspace are available on the **View Results** tab.
After selecting any file, you can view the `CSMs Table`, `PRTs Table`, `PRTs Summary`, `Crosslink efficiency` and `Precursor adducts summary`.

Users can manage their result files available in workspace with `Result files` tab.Also Users can upload previously analyzed results files `.idXML and .tsv` to workspace with `Upload result files` tab.

Note: Every table and plot can be downloaded, as indicated formats in the side-bar under ⚙️ Settings.

## How to upload result files (e.g., from external sources/collaborator) for manual inspection and visualization?
At **Upload result files** tab, user can  `upload` the results files and can visualize in **View Results** tab.
In the web app, collaborators can visualize files by sharing a unique workspace ID.

⚠️ Note: In the web app, all users with a unique workspace ID have the same rights.

## Contact
For any inquiries or assistance, please feel free to reach out to us.<br/><br/>
[![Discord Shield](https://img.shields.io/discord/832282841836159006?style=flat-square&message=Discord&color=5865F2&logo=Discord&logoColor=FFFFFF&label=Discord)](https://discord.gg/4TAGhqJ7s5) [![Gitter](https://img.shields.io/static/v1?style=flat-square&message=on%20Gitter&color=ED1965&logo=Gitter&logoColor=FFFFFF&label=Chat)](https://gitter.im/OpenMS/OpenMS?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
<br/><br/>





