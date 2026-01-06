from pathlib import Path
import streamlit as st

from src.common import page_setup, v_space

page_setup(page="main")

st.markdown(
        """
        # OpenMS NuXL App
        ### NuXL: A specialized protein nucleic-acid crosslink search engine
        Welcome to the OpenMS NuXL App, a web application for the NuXL protein-nucleic acid search engine built using [OpenMS](https://openms.de/) and [pyOpenMS](https://pyopenms.readthedocs.io/en/latest/).

        """
    )
st.image("assets/NuXL_image.png")
st.markdown(
      """
      Here, we take the NuXL search engine in a simple and easy graphical user interface. NuXL is a dedicated software package designed for the analysis of XL-MS (cross-linking mass spectrometry) data obtained from UV and chemically crosslinked protein–RNA/DNA samples. 
      This powerful tool allows for reliable, FDR-controlled assignment of protein–nucleic acid crosslinking sites in samples treated with UV light or chemical crosslinkers. It offers user-friendly matched spectra visualization, including ion annotations.

      """
)

st.markdown("""
**Reference:**  
Welp, L. M., Sachsenberg, T., Wulf, A., Chernev, A., Horokhovskyi, Y., Neumann, P., ... & Urlaub, H. (2024). *Chemical crosslinking extends and complements UV crosslinking in analysis of RNA/DNA nucleic acid-protein interaction sites by mass spectrometry.* bioRxiv, 2024-08.  
[https://doi.org/10.1101/2024.08.29.610268](https://doi.org/10.1101/2024.08.29.610268)
""")

#In docker, OpenMS-App (executable) can be downloadable from github
if Path("OpenMS-NuXLApp.zip").exists():
      st.markdown(
      """
      ## Installation

      ### Download for Windows

      Simply download, extract the zip file and run the installer (.msi) file to install the app. The app can then be launched using the corresponding desktop icon.
      """)
      with open("OpenMS-NuXLApp.zip", "rb") as file:
            st.download_button(
                        label="Download for Windows",
                        data=file,
                        file_name="OpenMS-NuXLApp.zip",
                        mime="archive/zip",
                        type="primary"
                        )

st.markdown("""
      ## Quickstart 

      You can start right away analyzing your data by following the steps below:

      ### 1. Create a workspace
      On the left side of this page a workspace  defined where all your data including uploaded files will be stored. In the web app, you can share your results via the unique workspace ID. Be careful with sensitive data, anyone with access to this ID can view your data.

      ⚠️ Note: In the web app, all users with a unique workspace ID have the same rights.
            
      ### 2. 📁 Upload your files
      Upload `mzML` and `fasta` files via the **File Upload** tab. The data will be stored in your workspace. With the web app you can upload only one file at a time.
      Locally there is no limit in files. However, it is recommended to upload large number of files by specifying the path to a directory containing the files.

      Your uploaded files will be shown on the same **File Upload** page in  **mzML files** and **Fasta files** tabs. Also you can remove the files from workspace.

      ### 3. ⚙️ Analyze your uploaded data

      Select the `mzML` and `fasta` files for analysis, configure user settings, and start the analysis using the **Run-analysis** button.
      You can terminate the analysis immediately using the **Terminate/Clear** button and you can review the search engine log on the page.
      Once the analysis completed successfully, the output table will be displayed on the page, along with downloadable links for crosslink identification files.

      #### 4. 📊 View your results
      Here, you can visualize and explore the output of the search engine. All crosslink output files in the workspace are available on the **View Results** tab.
      After selecting any file, you can view the `CSMs Table`, `PRTs Table`, `PRTs Summary`, `Crosslink efficiency` and `Precursor adducts summary`.

      Note: Every table and plot can be downloaded, as indicated in the side-bar under ⚙️ Settings.

      #### How to accessing previously analysed results?
      Under the **Result Files** tab, you can manage your results. You can `remove` or `download` files from the output files list.

      #### How to upload result files (e.g., from external sources/collaborator) for manual inspection and visualization?
      At **Upload result files** tab, user can  `upload` the results files and can visualize in **View Results** tab.
      In the web app, collaborators can visualize files by sharing a unique workspace ID.
      
      #### Contact
      For any inquiries or assistance, please feel free to reach out to us.  

      [![Discord Shield](https://img.shields.io/discord/832282841836159006?style=flat-square&message=Discord&color=5865F2&logo=Discord&logoColor=FFFFFF&label=Discord)](https://discord.gg/4TAGhqJ7s5)  [![Gitter](https://img.shields.io/static/v1?style=flat-square&message=on%20Gitter&color=ED1965&logo=Gitter&logoColor=FFFFFF&label=Chat)](https://gitter.im/OpenMS/OpenMS?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)  [![GitHub Issues](https://img.shields.io/badge/Open-GitHub%20Issue-%23121011?style=flat-square&logo=github)](https://github.com/Arslan-Siraj/nuxl-app/issues)

""")