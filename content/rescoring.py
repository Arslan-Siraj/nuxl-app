from src.common import *
import streamlit as st
import threading
import os

from pathlib import Path
from src.result_files import *
from src.run_subprocess import *

params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()

st.title("Rescoring with Percolator")

# download the files first time in
nuxl_rescore_dir: Path = Path(st.session_state.workspace, "nuxl-rescore-files")

# Check if folder is empty
if not any(nuxl_rescore_dir.iterdir()):
    import requests
    import io
    import zipfile

    # GitHub release ZIP URL
    zip_url = "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/0.0.1/nuxl_rescore_resource.zip"

    st.info("Resources missing for rescoring. Downloading first NuXL rescore resources ...")

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

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

# result directory path in current session state
result_dir: Path = Path(st.session_state.workspace, "result-files")

#make sure load all example result files
load_example_result_files()

session_idXML_files = [
        f.name
        for f in Path(st.session_state.workspace, "result-files").iterdir()
        if (
            f.name.endswith(".idXML")
            and not any(x in f.name for x in ["0.0100", "0.1000", "1.0000","RT_feat"])
        )
    ]

if not session_idXML_files:
    st.error("No valid .idXML files found in the result-files directory. please run NuXL search-engine")

else:
    unimod = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "unimod" / "unimod_to_formula.csv")
    feat_config = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "features-config.json")

    with st.form("Rescoring_form", clear_on_submit=False):
        # select box to select .idXML file to see the results
        selected_id_file = st.selectbox("Choose a file for rescoring: ", session_idXML_files)
        idXML_file = str(Path(st.session_state.workspace, "result-files", selected_id_file))
        st.info(f"Full path: {idXML_file}")

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
                        #st.write("Using RNA_DEB specific model and calibration data.")

                    elif protocol == 'RNA_NM':
                        model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_NM")
                        calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_NM.csv")
                        #st.write("Using RNA_NM specific model and calibration data.")

                    elif protocol == 'RNA_4SU':
                        model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_4SU")
                        calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_4SU.csv")
                        #st.write("Using RNA_4SU specific model and calibration data.")

                    elif protocol == 'RNA_UV' or protocol == "RNA_Other":
                        model_path = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "RT_deeplc_model" / "generic_model" / "full_hc_Train_RNA_All")
                        calibration_data = str(nuxl_rescore_dir / "nuxl_rescore_resource" / "calibration_data" / "RNA_All.csv")
                        #st.write("Using generic RNA_UV and Other model and calibration data.")
                
                #st.write(model_path)
                #st.write(calibration_data)

                # run the different combinations of features
                if Retention_time_features and not Max_correlation_features:
                    st.write("Using ONLY retention time features.")
                    # Assume 'posix' for Linux and macOS
                    args =["nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-feat_config", feat_config, "-rt_model", "DeepLC", "-model_path", model_path, "-out", str(result_dir)] 
                
                elif not Retention_time_features and Max_correlation_features:
                    st.write("Using ONLY max correlation feature.")
                    # Assume 'posix' for Linux and macOS
                    args =["nuxl_rescore", "run", "-id", idXML_file,"-rt_model", "None", "-ms2pip", 
                        "-unimod", unimod, "-feat_config", feat_config, "-out", str(result_dir)] 

                elif Retention_time_features and Max_correlation_features:
                    st.write("Using retention time and max correlation feature.")
                    # Assume 'posix' for Linux and macOS
                    args =["nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-rt_model", "DeepLC", "-ms2pip", "-feat_config", feat_config, "-model_path", model_path, "-out", str(result_dir)]
                else:
                    st.error("Please select at least one feature to use for rescoring.")
                    st.stop()

            # Add any additional variables needed for the subprocess (if any)
            variables = []  

            if Max_correlation_features:
                id_file = Path(selected_id_file)

                mgf_file = id_file.with_suffix(".mgf")
                mzML_file = id_file.with_suffix(".mzML")

                mgf_path = Path(st.session_state.workspace, "mzML-files", mgf_file)
                mzML_path = Path(st.session_state.workspace, "mzML-files", mzML_file)

                print("mgf_file_path:", mgf_path)
                print("mzML_file_path:", mzML_path)

                if not mgf_path.exists():
                    if not mzML_path.exists():
                        st.info("Rescoring with max correlation features requires mzML file.")
                        st.error(
                            f"Required mzML file '{mzML_file}' not found in mzML-files directory."
                        )
                        st.stop()

                    else:
                        st.info("Converting mzML → MGF")
                        args_convert = [
                                        "FileConverter",
                                        "-in", str(mzML_path),
                                        "-out", str(mgf_path)
                                    ]

                        st.info(f"Running: {' '.join(args_convert)}")

                        result = subprocess.run(
                            args_convert,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        if result.returncode != 0:
                            st.error("mzML → MGF conversion failed")
                            st.text(result.stderr)
                            st.stop()
                        else:
                            st.success("mzML → MGF conversion completed")
                
                args.extend(["-mgf", str(mgf_path)])

            # want to see the command values and argues
            message = f"Running '{' '.join(args)}'"
            st.info(message)

            # run subprocess command
            run_subprocess(args, variables, result_dict)

        # Check if the subprocess was successful
        if result_dict["success"]:
            # Here can add code here to handle the results, e.g., display them to the user
            for f in result_dir.glob("peprec*.csv"):
                f.unlink()  # deletes the file
        else:
            # Display error message
            st.error(
                    f"⚠️ **Rescoring Failed**\n\n"
                    f"Please look at the log.\n"
                    )
            
# At the end of each page, always save parameters (including any changes via widgets with key)
save_params(params)

