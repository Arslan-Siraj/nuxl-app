from pathlib import Path
import streamlit as st
import pandas as pd
from src.common import *
from src.fileupload import *
from src.captcha_ import *

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

#title of page
st.title("📂 File Upload")

#directories of current session state : "mzML-files", "fasta-files"
mzML_dir: Path = Path(st.session_state.workspace, "mzML-files")
fasta_dir: Path = Path(st.session_state.workspace, "fasta-files")

#tabs on page
tabs = ["mzML/raw files", "Fasta files"]
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
    load_example_mzML_files()

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
    load_example_fasta_files()

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

save_params(params)
