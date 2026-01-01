from pathlib import Path
import streamlit as st
import pandas as pd
from src.common import *
from src.fileupload import *
from src.captcha_ import *
from src.result_files import *

params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()        

### main content of page

# Make sure "selected-mzML-files" is in session state
if "selected-mzML-files" not in st.session_state:
    st.session_state["selected-mzML-files"] = params["selected-mzML-files"]

# Make sure "selected-fasta-files" is in session state
if "selected-fasta-files" not in st.session_state:
    st.session_state["selected-fasta-files"] = params.get("selected-fasta-files", [])

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

#title of page
st.title("📂 File Upload")

#directories of current session state : "mzML-files", "fasta-files"
mzML_dir: Path = Path(st.session_state.workspace, "mzML-files")
fasta_dir: Path = Path(st.session_state.workspace, "fasta-files")
example_data_dir: Path = Path(st.session_state.workspace, "example-data-files")

#tabs on page
tabs = ["mzML/raw files", "Fasta files", "Load example files"]
tabs = st.tabs(tabs)

#mzML/raw files tab
with tabs[0]:
    #create form of mzML-upload
    with st.form("mzML-upload", clear_on_submit=True):
        if st.session_state.location == "local":
            #create file uploader to take mzML files
            files = st.file_uploader(
                "Upload mzML/raw files", accept_multiple_files=(st.session_state.location == "local"), type=['.mzML', '.raw'], help="Input file (Valid formats: 'mzML' or 'raw')  accept multiples")
        else:
             files = st.file_uploader(
                "Upload mzML/raw files", accept_multiple_files=(st.session_state.location == "local"), type=['.mzML', '.raw'], help="Input file (Valid formats: 'mzML' or 'raw')")
        
        cols = st.columns(3)
        #file uploader submit button
        if cols[1].form_submit_button("Add mzML/raw file to workspace", type="primary"):
            print(files)
            if not files:
                st.warning("Upload some files first.")
            else:
                save_uploaded_mzML(files)

    #load example mzML files to current session state
    #load_example_mzML_files() 

    if any(Path(mzML_dir).iterdir()):
        v_space(2)
        # Display all mzML files currently in workspace
        file_names_ = [f.name for f in Path(mzML_dir).iterdir()]
        df = pd.DataFrame(
            {"file name": [item for item in file_names_ if not (item.endswith(".csv") or item.endswith(".mgf"))]})
        st.markdown("##### mzML/raw files in current workspace:")
        show_table(df)
        v_space(1)
        # Remove files
        mzML_dir: Path = Path(st.session_state.workspace, "mzML-files")
        with st.expander("🗑️ Remove uploaded mzML/raw files"):
            to_remove = st.multiselect("select mzML/raw files",
                                    options=[f.name for f in sorted(mzML_dir.iterdir())])
            
            #st.code(to_remove)
            
            c1, c2 = st.columns(2)
            #Remove selected files
            if c2.button("Remove **selected**", type="primary", disabled=not any(to_remove)):
                remove_selected_mzML_files(to_remove)
                st.rerun()
            #Remove all files
            if c1.button("⚠️ Remove **all**", disabled=not any(mzML_dir.iterdir())):
                remove_all_mzML_files()
                st.rerun()

#fasta files tab
with tabs[1]:
    #create form of fasta-upload
    with st.form("fasta-upload", clear_on_submit=True):
        #create file uploader to take fasta files
        files = st.file_uploader(
            "Upload fasta file", accept_multiple_files=(st.session_state.location == "local"), type=['.fasta'], help="Input file (Valid formats: 'fasta')")
        cols = st.columns(3)
        #file uploader submit button
        if cols[1].form_submit_button("Add fasta to workspace", type="primary"):
            if not files:
                st.warning("Upload some files first.")
            else:
                save_uploaded_fasta(files)

    #load example fasta files to current session state
    #load_example_fasta_files()

    if any(Path(fasta_dir).iterdir()):
        v_space(2)
        # Display all fasta files currently in workspace
        df = pd.DataFrame(
            {"file name": [f.name for f in Path(fasta_dir).iterdir()]})
        st.markdown("##### fasta files in current workspace:")
        show_table(df)
        v_space(1)
        # Remove files
        with st.expander("🗑️ Remove uploaded fasta files"):
            to_remove = st.multiselect("select fasta files",
                                    options=[f.stem for f in sorted(fasta_dir.iterdir())])
            c1, c2 = st.columns(2)
            #Remove selected files
            if c2.button("Remove **selected** from workspace", type="primary", disabled=not any(to_remove)):
                remove_selected_fasta_files(to_remove)
                st.rerun()
            #Remove all files
            if c1.button("⚠️ Remove **all** from workspace", disabled=not any(fasta_dir.iterdir())):
                remove_all_fasta_files()
                st.rerun()

with tabs[2]:

    def function_to_load_example_data():
        import requests
        import io
        import zipfile

        zip_url = "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/0.0.2/RNA_DEB_Protein_NA_XL_example_files.zip"

        st.info("Downloading example data files...")

        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        zip_buffer = io.BytesIO()
        with requests.get(zip_url, timeout=500, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    zip_buffer.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        progress_bar.progress(percent)
                        status_text.text(f"Downloading... {percent}%")

        status_text.text("Extracting files...")
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer) as z:
            for member in z.infolist():
                # Skip directories
                if member.is_dir():
                    continue
                
                # Take only the file name and add prefix
                original_name = Path(member.filename).name
                member_filename = f"example_{original_name}"
                
                # Define target path
                target_path = example_data_dir / member_filename
                
                # Extract and write file
                with z.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())
        
        # copy extracted files to their desired spaces
        load_example_mzML_files()
        load_example_fasta_files()
        load_example_result_files()
        st.rerun()

        progress_bar.progress(100)
        status_text.text("Done!")
        
    # Check if folder is empty
    if not any(Path(example_data_dir).iterdir()):
        if st.button("Load all example data to workspace", type="primary"):
            function_to_load_example_data()
    else:
        st.info("Example files are already loaded in the workspace.")
    
        if any(Path(example_data_dir).iterdir()):
            v_space(1)
            # Display all mzML files currently in workspace
            file_names_ = [f.name for f in Path(example_data_dir).iterdir()]
            df = pd.DataFrame(
                {"file name": [item for item in file_names_ if not (item.endswith(".txt"))]})
            st.markdown("##### These files should be available in workspace: ")
            show_table(df)
            v_space(1)

            if st.button("Reload example data files to workspace", type="primary", help="This will overwrite existing example files in the workspace."):
                function_to_load_example_data()
            
save_params(params)
