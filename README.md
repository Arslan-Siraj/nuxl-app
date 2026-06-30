# OpenMS NuXL App [![Open Template!](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://openms-template.streamlit.app/)

Welcome to the OpenMS NuXL App, a web application for the NuXL protein-nucleic acid search engine built using [OpenMS](https://openms.de/) and [pyOpenMS](https://pyopenms.readthedocs.io/en/latest/).<br/>
**website:** [https://abi-services.cs.uni-tuebingen.de/nuxl/](https://abi-services.cs.uni-tuebingen.de/nuxl/)

![Protein-Nucleic-acid Cross-linking](assets/NuXL_image.png)

## Main headings

- [Description](#description)
- [How to do analysis](#how-todo-analyis)
- [Access NuXLApp](#access-nuxlapp)
- [Legal pages](#legal-pages-impressum-privacy-policy-terms-of-use)
- [Citation](#citation)
- [Contact](#contact)

---

## Description
NuXL is a dedicated software package designed for the analysis of XL-MS (cross-linking mass spectrometry) data obtained from UV and chemically crosslinked protein–RNA/DNA samples. This powerful tool allows for reliable, FDR-controlled assignment of protein–nucleic acid crosslinking sites in samples treated with UV light or chemical crosslinkers. It offers user-friendly matched spectra visualization, including ion annotations.

Rescoring refers to the post-processing of initial identification results to improve discrimination between correct and incorrect matches by incorporating additional evidence, such as predicted retention time or fragment ion intensities. Such approaches have been shown to increase the identification rate.

👉 With NuXL App users can analyze data with NuXL search engine, run rescoring pipeline, generate DIA library, and result interpretation with cross-link aware visualization.     

---

## How todo analyis?
User can start right away analyzing your data by following the steps below:

### 1. 📁 Upload your files
Upload `.mzML`. `.raw` and `.fasta` files via the **File Upload** tab. The data will be stored in the workspace. With the online hosted web app, user can upload only one file at a time.
Locally there is no limit in files. However, it is recommended to upload large number of files by specifying the path to a directory containing the files.

Your uploaded files will be shown on the same **File Upload** page in  **mzML files** and **Fasta files** tabs. Also user can remove the files from workspace.

Users can download the example files from **Load example file** tab to current workspace.

### 2. ⚙️ Run NuXL search engine

Select the `.mzML/.raw` and `.fasta` files for analysis, configure user settings including NuXL advanced parameters, and start the analysis. Once the analysis completed successfully, the output table will be displayed on the page, along with downloadable links for crosslink identification files for that particular analysis.

👉  checkout the doc: [NuXL search engine user-guide](https://github.com/Arslan-Siraj/nuxl-app/blob/main/docs/nuxl_workflow_user_guide.md)


### 3. ⚙️ Rescoring
Select without FDR-controlled `.idXML` file from output of NuXL search engine. The name of file pattern is `(raw or mzML file_name).idXML`. If the NuxL search engine succesfully run, the file will showup here. After including the features start the analysis. Once the analysis completed successfully, the comparison PseudoROC curve at CSM-level FDR will generated, and available for download.

👉  checkout the doc: [Rescoring user-guide](https://github.com/Arslan-Siraj/nuxl-app/blob/main/docs/rescoring_workflow_user_guide.md)


### 4. ⚙️ DIA spectra library generation
Select the experiments with (`.mzML`) it will extract the identified protein-NA and peptides from NuXL output at 1% CSM-level FDR, available in `.idXML` files. Optionally, user can do iRT alignment by providing MSFragger `library.tsv`, with `linear` or `piecewise` calibration mode. User can see the real-time log of spectral library generation and download the output files.

👉  checkout the doc: [DIA spectral library generation user-guide](https://github.com/Arslan-Siraj/nuxl-app/blob/main/docs/dia_library_generation_workflow_user_guide.md)


### 5. 📊 View your results
Here, user can visualize and explore the output of the search engine. All crosslink output files in the workspace are available on the **View Results** tab.
After selecting any file, user can view the `CSMs Table`, `PRTs Table`, `PRTs Summary`, `Crosslink efficiency` and `Precursor adducts summary`.

Users can manage their result files available in workspace with `Result files` tab.Also Users can upload previously analyzed results files `.idXML and .tsv` to workspace with `Upload result files` tab.

⚠️ Note: Every table and plot can be downloaded, as indicated formats in the side-bar under ⚙️ Settings.

#### How to upload result files (e.g., from external sources/collaborator) for manual inspection and visualization?
At **Upload result files** tab, user can  `upload` the results files and can visualize in **View Results** tab.
In the web app, collaborators can visualize files by sharing a unique workspace ID.

⚠️ Note: In the web app, all users with a unique workspace ID have the same rights.

### 6. 📖 Documentation

Documentation for **users** is included as pages in [this template app](https://abi-services.cs.uni-tuebingen.de/streamlit-template/) (todo link add), indicated by the 📖 icon. This is user guide for the analysis implement in NuXLApp.

---

## Access NuXLApp
### 🔗 1. Try the Online Demo

Explore the hosted version here:  👉 [Live App](https://abi-services.cs.uni-tuebingen.de/streamlit-template/)

### 💻 2. Running NuXL locally: Installation as stand-alone tool windows exec
1. To get started, download and extract the [OpenMS-NuXLApp.zip](https://github.com/Arslan-Siraj/nuxl-app/releases/tag/0.5.0) file from latest successfull action.
2. After installation of `OpenMS-NuXLApp.msi`, The app can then be launched using the corresponding desktop icon.
3. Use app in your default browser. <br/> 

The workspaces for the project will be locally generated in the `workspaces-nuxl-app` directory, and the analysis will run using local resources.

### 🐳 3.Build with Docker

This repository contains two Dockerfiles.

1. `Dockerfile`: This Dockerfile builds all dependencies for the app including Python packages and the OpenMS TOPP tools. Recommended for more complex workflows where you want to use the OpenMS TOPP tools for instance with the **TOPP Workflow Framework**.
2. `Dockerfile_simple`: This Dockerfile builds only the Python packages. Recommended for simple apps using pyOpenMS only.

1. **Install Docker**

   Install Docker from the [official Docker installation guide](https://docs.docker.com/engine/install/)  
   
   <details>
   <summary>Click to expand</summary>
   
   ```bash
   # Remove older Docker versions (if any)
   for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove -y $pkg; done
   ```
   
   </details>

2. **Test Docker**
   
   Verify that Docker is working.
   ```bash
   docker run hello-world
   ```
   When running this command, you should see a hello world message from Docker.
   
3. **Clone the repository**
   ```bash
   git clone https://github.com/OpenMS/streamlit-template.git
   cd streamlit-template
   ```
   
4. **Specify GitHub token (to download Windows executables).**
   
   Create a temporary `.env` file with your Github token.
   
   It should contain only one line:
   `GITHUB_TOKEN=<your-github-token>`

   ℹ️ **Note:** This step is not strictly required, but skipping it will remove the option to download executables from the WebApp.
   
3. **Build & Launch the App**

   To build and start the containers.
   From the project root directory:
   
   ```bash
   docker-compose up -d --build
   ```
     At the end, you should see this:
      ```
      [+] Running 2/2
       ✔ openms-streamlit-template            Built      
       ✔ Container openms-streamlit-template  Started  
      ```
      
      To make sure server started successfully, run `docker compose ps`. You should see `Up` status:
      ```
      CONTAINER ID   IMAGE                       COMMAND                  CREATED         STATUS                 PORTS                                           NAMES
      4abe0603e521   openms_streamlit_template   "/app/entrypoint.sh …"   7 minutes ago   Up 7 minutes           0.0.0.0:8501->8501/tcp, :::8501->8501/tcp       openms-streamlit-template
      ```
   
      To map the port to default streamlit port `8501` and launch.
      
      ```
      docker run -p 8505:8501 openms_streamlit_template
      ```

   ##### Mount a local data directory

   To make a directory of MS files on the host available to the running app
   without uploading or copying them, bind-mount it into the container at
   the path configured by `local_data_dir` in `settings.json` (the Docker
   image defaults this to `/mounted-data`):

   ```
   docker run -p 8501:8501 \
     -v /path/on/host:/mounted-data:ro \
     openms_streamlit_template
   ```

   The upload widget auto-detects the mount: when the directory exists at
   runtime it shows an in-app tree browser; selected files are referenced
   in place via `external_files.txt` (no copy into the workspace volume),
   so the mount can safely be read-only. Omitting `-v` hides the browser
   and falls back to the standard upload UI. To use a different container
   path, change `local_data_dir` in `settings.json` before building.

### 🛰️ 4. Run with Apptainer / Singularity (HPC)

Apptainer (formerly Singularity) is the dominant container runtime on HPC
clusters. CI publishes prebuilt SIFs to GHCR via ORAS, so you can pull a
ready-to-run image with no on-the-fly OCI→SIF conversion and run it as your
user — no root, no `--writable-tmpfs` required:

```bash
apptainer pull --name openms-streamlit-template.sif \
  oras://ghcr.io/openms/streamlit-template/sif:latest
apptainer run \
  --bind /path/to/data:/mounted-data:ro \
  --bind /path/to/workspaces:/workspaces-streamlit-template \
  openms-streamlit-template.sif
```

Available tags follow the same scheme as the Docker images: `latest`,
`main-full`, `main-simple`, `v*-full`, `v*-simple`, and per-commit SHAs.
If a tag hasn't been prebuilt yet (e.g. a PR branch), fall back to on-the-fly
conversion: `apptainer pull docker://ghcr.io/openms/streamlit-template:<tag>`.
Requires apptainer 1.1+ or singularity-ce 3.10+ for the `oras://` transport.

The entrypoint auto-detects the read-only root filesystem (set by apptainer's
default isolation) and switches its runtime state — Redis data directory,
nginx config, PID files — to `/tmp/openms-runtime-$$`, which is always
writable inside an apptainer container. The workspace cleanup cron job is
skipped in this mode; rerun `clean-up-workspaces.py` manually if needed.

---

## ⚖️ Legal pages (Impressum, Privacy Policy, Terms of Use)

Every page shows **Impressum**, **Privacy Policy** and **Terms of Use** links at
the bottom of the sidebar, and the GDPR consent banner links to the privacy
policy. By default these point to the centrally maintained official OpenMS pages
(`https://openms.de/impressum`, `/privacy`, `/terms`).

---

## Citation

**NuXL search engine:**
        Welp, L. M., Wulf, A., Chernev, A., Horokhovskyi, Y., Moshkovskii, S., Dybkov, O., ... & Urlaub, H. (2025). Chemical crosslinking extends and complements UV crosslinking in analysis of RNA/DNA nucleic acid–protein interaction sites by mass spectrometry. Nucleic Acids Research, 53(15), gkaf727. [https://doi.org/10.1093/nar/gkaf727](https://doi.org/10.1093/nar/gkaf727)
     
 **NuXL rescore:**
        Siraj, A., Bouwmeester, R., Declercq, A., Welp, L., Chernev, A., Wulf, A., ... & Sachsenberg, T. (2024). Intensity and retention time prediction improves the rescoring of protein‐nucleic acid cross‐links. Proteomics, 24(8), 2300144.[https://doi.org/10.1002/pmic.202300144](https://doi.org/10.1002/pmic.202300144)
        
**OpenMS WebApp Framework:**
       Müller, T. D., Siraj, A., et al. OpenMS WebApps: Building User-Friendly Solutions for MS Analysis. Journal of Proteome Research (2025). [https://doi.org/10.1021/acs.jproteome.4c00872](https://doi.org/10.1021/acs.jproteome.4c00872)

---

## Contact
For any inquiries or assistance, please feel free to reach out to us.<br/><br/>
[![Discord Shield](https://img.shields.io/discord/832282841836159006?style=flat-square&message=Discord&color=5865F2&logo=Discord&logoColor=FFFFFF&label=Discord)](https://discord.gg/4TAGhqJ7s5)
<br/><br/>


