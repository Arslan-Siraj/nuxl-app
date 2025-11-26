from src.common import *
import streamlit as st
import threading
import os

from pathlib import Path

from src.run_subprocess import *

params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()

# download the files first time in
nuxl_rescore_dir: Path = Path(st.session_state.workspace, "nuxl-rescore-files")

from pathlib import Path
import requests
import io
import zipfile

# GitHub release ZIP URL
zip_url = "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/0.0.1/nuxl_rescore_resource.zip"

# Check if folder is empty
if not any(nuxl_rescore_dir.iterdir()):
    st.info("Resources missing for rescoring. Downloading NuXL rescore resources ...")

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Streamed download
    with requests.get(zip_url, stream=True) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        zip_buffer = io.BytesIO()

        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                zip_buffer.write(chunk)
                downloaded += len(chunk)

                # Update progress bar
                if total_size > 0:
                    percent = int(downloaded * 100 / total_size)
                    progress_bar.progress(percent)
                    status_text.text(f"Downloading... {percent}%")

    status_text.text("Extracting files...")
    zip_buffer.seek(0)

    # Extract ZIP contents
    with zipfile.ZipFile(zip_buffer) as z:
        z.extractall(nuxl_rescore_dir)

    progress_bar.progress(100)
    status_text.text("Done!")
    st.success("Resources downloaded and extracted successfully.")

##################################
# Main Rescoring Page Content
##################################
st.title("Rescoring with Percolator")

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

# result directory path in current session state
result_dir: Path = Path(st.session_state.workspace, "result-files")

session_files = [
        f.name
        for f in Path(st.session_state.workspace, "result-files").iterdir()
        if (
            f.name.endswith(".idXML")
            and not any(x in f.name for x in ["0.0100", "0.1000", "1.0000"])
        )
    ]

unimod = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "unimod" / "unimod_to_formula.csv")
feat_config = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "features-config.json")
output_path = r"/home/arslan/test_rescore/test_out"

with st.form("Rescoring_form", clear_on_submit=False):
    # select box to select .idXML file to see the results
    selected_id_file = st.selectbox("Choose a file for rescoring: ", session_files)
    idXML_file = str(Path(st.session_state.workspace, "result-files", selected_id_file))

    protocol = st.selectbox(
        'Select the suitable protocol',
        ['RNA_DEB', 'RNA_NM', 'RNA_4SU', 'RNA_UV', 'RNA_Other'],
        help="Please select suitable protocol for the crosslinking experiment performed.",
        )
    
    Retention_time_features = st.checkbox("Retention time prediction and features ", value=True, help="Check this box to predict and use retention time features during rescoring.")

    Max_correlation_features = st.checkbox("Max correlation features", value=True, help="Check this box to use max correlation features during rescoring.")
    
    submit_button = st.form_submit_button("Run-Rescoring", type="primary")

# Create a dictionary to capture the output and status of the subprocess
result_dict = {}
result_dict["success"] = False
result_dict["log"] = " "

# Create a flag to terminate the subprocess
terminate_flag = threading.Event()
terminate_flag.set()

# Function to terminate the subprocess
def terminate_subprocess():
    """Set flag to terminate subprocess."""
    global terminate_flag
    terminate_flag.set()

# run analysis 
if submit_button: 

    # Check if the "Extract ids" button is clicked
    if st.button("Terminate/Clear", key="terminate-button", type="secondary"):
        # terminate subprocess
        terminate_subprocess()
        st.warning("Process terminated. The analysis may not be complete.")

        # clear form
        st.rerun() 

    # Display a status message while running the analysis
    with st.status("Running analysis... Please wait until analysis done 😑"):

        # Define the command to run as a subprocess (example: grep or findstr (for windows))
        # 'nt' indicates Windows
        if os.name == 'nt':  
            args = ["Python", "D:\\Nuxl_app_development\\nuxl_rescore_files\\NuXL_rescore\\run.py", "-id", id_file, "-calibration", calibration,
                     "-unimod", unimod, "-feat_config", feat_config, "-model_path", model_path ]
        else: 
            if Retention_time_features:
                if protocol == 'RNA_DEB':
                    model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_DEB")
                    calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_DEB.csv")
                    st.write("Using RNA_DEB specific model and calibration data.")

                elif protocol == 'RNA_NM':
                    model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_NM")
                    calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_NM.csv")
                    st.write("Using RNA_NM specific model and calibration data.")

                elif protocol == 'RNA_4SU':
                    model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_4SU")
                    calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_4SU.csv")
                    st.write("Using RNA_4SU specific model and calibration data.")

                elif protocol == 'RNA_UV' or protocol == "RNA_Other":
                    model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "generic_model" / "full_hc_Train_RNA_All")
                    calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_All.csv")
                    st.write("Using generic RNA_UV and Other model and calibration data.")
            
            st.write(model_path)
            st.write(calibration_data)

            # run the different combinations of features
            if Retention_time_features and not Max_correlation_features:
                st.write("Using ONLY retention time features.")
                # Assume 'posix' for Linux and macOS
                args =["nuxl_rescore", "-id", idXML_file, "-calibration", calibration_data,
                     "-unimod", unimod, "-feat_config", feat_config, "-model_path", model_path, "-out", output_path] 
                
            elif Retention_time_features and Max_correlation_features:
                st.write("Using retention time and max correlation features.")
                # Assume 'posix' for Linux and macOS
                args =["nuxl_rescore", "-id", selected_id_file, "-calibration", calibration_data,
                     "-unimod", unimod, "-feat_config", feat_config, "-model_path", model_path, "-out", output_path]
            #else:
                # Assume 'posix' for Linux and macOS
            #    args =["nuxl_rescore", "-id", selected_id_file, "-calibration", calibration_data,
            #            "-unimod", unimod, "-feat_config", feat_config, "-model_path", model_path, "-out", output_path]

        # Add any additional variables needed for the subprocess (if any)
        variables = []  

        # want to see the command values and argues
        message = f"Running '{' '.join(args)}'"
        st.info(message)

        # run subprocess command
        run_subprocess(args, variables, result_dict)

    # Check if the subprocess was successful
    if result_dict["success"]:
        # Here can add code here to handle the results, e.g., display them to the user

        pass  # Placeholder for result handling
            
# At the end of each page, always save parameters (including any changes via widgets with key)
save_params(params)