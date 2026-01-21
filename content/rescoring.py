from src.common import *
import streamlit as st
import threading
import os

from pathlib import Path
from src.result_files import *
from src.run_subprocess import *
from src.view import plot_FDR_plot
import textwrap
from datetime import datetime

#from nuxl_rescore import run_pipeline
params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()

st.title("Rescoring with Data-Driven Features from Machine Learning Models", 
         help="Rescoring refers to the post-processing of initial identification results "
        "to improve discrimination between correct and incorrect matches by "
        "incorporating additional evidence, such as predicted retention time or "
        "fragment ion intensities. Such approaches have been shown to increase "
        "identification confidence and reduce false discovery rates in complex "
        "proteomics and cross-linking mass spectrometry analyses "
        "(see Proteomics 2023, DOI: 10.1002/pmic.202300144)."
        )

# download the files first time in
nuxl_rescore_dir: Path = Path(st.session_state.workspace, "nuxl-rescore-files")

# Check if folder is empty
if not any(nuxl_rescore_dir.iterdir()):
    import requests
    import io
    import zipfile

    # GitHub release ZIP URL
    zip_url = "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/0.0.1/nuxl_rescore_resource.zip"

    st.info("Resources missing for rescoring. Downloading NuXL rescore resources ...")

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Streamed download
    with requests.get(zip_url, timeout=500, stream=True) as r:
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
    st.rerun()

##################################
# Main Rescoring Page Content
##################################

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

# result directory path in current session state
result_dir: Path = Path(st.session_state.workspace, "result-files")

#make sure load all example result files
#load_example_result_files()

session_idXML_files = [
        f.name
        for f in Path(st.session_state.workspace, "result-files").iterdir()
        if (
            f.name.endswith(".idXML")
            and not any(x in f.name for x in ["0.0100", "0.1000", "1.0000","RT_feat", "RT_Int_feat", "updated_feat", "_perc", "_perc_", "_sse_perc_" ])
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
        #st.info(f"Full path: {idXML_file}")
        
        protocol = st.selectbox(
            'Select the suitable protocol',
            ['RNA_DEB', 'RNA_NM', 'RNA_4SU', 'RNA_UV', 'RNA_Other'],
            help="Please select suitable protocol for the crosslinking experiment performed.",
            )
        
        Retention_time_features = st.checkbox("Retention time prediction and features ", value=True, help="Check this box to predict and use retention time features during rescoring.")

        Max_correlation_features = st.checkbox("Max correlation features", value=True, help="Check this box to use max correlation features during rescoring.")
        
        plot_PseudROC = st.checkbox("plot pseudo-ROC", value=True, help="Check this for pseudo-ROC plot the comparison of rescoring.")

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
        with st.status("Running analysis... Please wait until analysis done ðŸ˜‘"):
 
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
            idXML_file_100_XLs = result_dir / Path(idXML_file).name.replace(".idXML", "_perc_1.0000_XLs.idXML")
            idXML_file_1_XLs = result_dir / Path(idXML_file).name.replace(".idXML", "_perc_0.0100_XLs.idXML")

            nuxl_rescore_exec = os.path.join(os.getcwd(),'python-3.10.0', 'python')
            # run the different combinations of features
            # RT_feat_
            if Retention_time_features and not Max_correlation_features:
                st.write("Adapting ONLY retention time features.")
                if os.name == 'nt':
                    # Assume 'posix' for Linux and macOS
                    args =[nuxl_rescore_exec, "-m", "nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-feat_config", feat_config, "-rt_model", "DeepLC", "-model_path", model_path, "-out", str(result_dir)] 
                else:
                     args =["nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-feat_config", feat_config, "-rt_model", "DeepLC", "-model_path", model_path, "-out", str(result_dir)] 

                idXML_file_extra_100_XLs = result_dir / f"RT_feat_{Path(idXML_file).stem}_perc_1.0000_XLs.idXML"
                idXML_file_extra_1_XLs = result_dir / f"RT_feat_{Path(idXML_file).stem}_perc_0.0100_XLs.idXML"
            
            # Int_feat_
            elif not Retention_time_features and Max_correlation_features:
                st.write("Adapting ONLY max correlation feature.")
                # Assume 'posix' for Linux and macOS
                if os.name == 'nt':
                     args =[nuxl_rescore_exec, "-m", "nuxl_rescore", "run", "-id", idXML_file,"-rt_model", "None", "-ms2pip", 
                        "-unimod", unimod, "-feat_config", feat_config, "-out", str(result_dir)] 

                else:
                    args =["nuxl_rescore", "run", "-id", idXML_file,"-rt_model", "None", "-ms2pip", 
                        "-unimod", unimod, "-feat_config", feat_config, "-out", str(result_dir)] 
                idXML_file_extra_100_XLs = result_dir / f"Int_feat_{Path(idXML_file).stem}_perc_1.0000_XLs.idXML"
                idXML_file_extra_1_XLs = result_dir / f"Int_feat_{Path(idXML_file).stem}_perc_0.0100_XLs.idXML"

            # RT_Int_feat_
            elif Retention_time_features and Max_correlation_features:
                st.write("Adapting retention time and max correlation feature.")
                # Assume 'posix' for Linux and macOS
                if os.name == 'nt':
                    args =[nuxl_rescore_exec, "-m", "nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-rt_model", "DeepLC", "-ms2pip", "-feat_config", feat_config, "-model_path", model_path, "-out", str(result_dir)]
                else:  
                    args =["nuxl_rescore", "run", "-id", idXML_file, "-calibration", calibration_data,
                        "-unimod", unimod, "-rt_model", "DeepLC", "-ms2pip", "-feat_config", feat_config, "-model_path", model_path, "-out", str(result_dir)]
                idXML_file_extra_100_XLs = result_dir / f"RT_Int_feat_{Path(idXML_file).stem}_perc_1.0000_XLs.idXML"
                idXML_file_extra_1_XLs = result_dir / f"RT_Int_feat_{Path(idXML_file).stem}_perc_0.0100_XLs.idXML"

            else:
                st.error("Please select at least one feature to use for rescoring.")
                idXML_file_extra_100_XLs = result_dir / f"updated_{Path(idXML_file).stem}_perc_1.0000_XLs.idXML"
                idXML_file_extra_1_XLs = result_dir / f"updated_{Path(idXML_file).stem}_perc_0.0100_XLs.idXML"
                st.stop()

            # Add any additional variables needed for the subprocess (if any)
            variables = []  

            id_file = Path(selected_id_file)
            if Max_correlation_features:

                mgf_file = id_file.with_suffix(".mgf")
                mzML_file = id_file.with_suffix(".mzML")

                mgf_path = Path(st.session_state.workspace, "mzML-files", mgf_file)
                mzML_path = Path(st.session_state.workspace, "mzML-files", mzML_file)

                #print("mgf_file_path:", mgf_path)
                #print("mzML_file_path:", mzML_path)

                if not mgf_path.exists():
                    if not mzML_path.exists():
                        st.info("Rescoring with max correlation features requires mzML file.")
                        st.error(
                            f"Required mzML file '{mzML_file}' not found in mzML-files directory."
                        )
                        st.stop()

                    else:
                        st.info("Converting mzML â†’ MGF")
                        File_converter_exec = os.path.join(os.getcwd(),'FileConverter')
                        if os.name == 'nt':
                            args_convert = [
                                            File_converter_exec,
                                            "-in", str(mzML_path),
                                            "-out", str(mgf_path)
                                        ]
                        else:
                            args_convert = [
                                            "FileConverter",
                                            "-in", str(mzML_path),
                                            "-out", str(mgf_path)
                                        ]

                        #st.info(f"Running: {' '.join(args_convert)}")

                        result = subprocess.run(
                            args_convert,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        if result.returncode != 0:
                            st.error("mzML â†’ MGF conversion failed")
                            st.text(result.stderr)
                            st.stop()
                        else:
                            st.success("mzML â†’ MGF conversion completed")
                
                args.extend(["-mgf", str(mgf_path)])

            args.extend(["-perc_exe", "percolator"])
            args.extend(["-perc_adapter", "PercolatorAdapter"])

            # want to see the command values and argues
            #message = f"Running '{' '.join(args)}'"
            #st.info(message)
            #st.info("check inputs plot: " + str(idXML_file_100_XLs)+' and '+ str(idXML_file_extra_100_XLs)+' '+ str(Path(idXML_file).stem))
            # run subprocess command
            st.info(f"Rescoring analysis of {selected_id_file}",  icon="â„¹ï¸")
            run_subprocess(args, variables, result_dict)
        
        args_cmd = " ".join(map(str, args))
        search_param = textwrap.dedent(f"""\
            ======= Parameters ==========
            NuXLApp verison: {st.session_state.settings['version']}
            Selected idXML File: {idXML_file}
            Protocol: {protocol}
            Retention time features: {Retention_time_features}
            Max correlation features: {Max_correlation_features}
            Model path: {model_path if Retention_time_features else 'None'}
            Calibration data: {calibration_data if Retention_time_features else 'None'}
            Unimod file: {unimod}
            Feature config: {feat_config}
            ======= Executed command =======
            {args_cmd}
            """)

        time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = result_dir / f'{id_file}_rescore_out_log_{time_stamp}.txt'

        # Save the log to a text file in the result_dir
        with open(log_file_path, "w") as log_file:
                log_file.write(search_param)
                log_file.write("\n======= Rescoring output ========== \n ")
                log_file.write(result_dict["log"])

        # Check if the subprocess was successful
        if result_dict["success"]:
            st.info(f"Rescoring analysis of **{log_file_path.name}** log file written in result folder with name {log_file_path.name}", icon="â„¹ï¸")

            # Here can add code here to handle the results, e.g., display them to the user
            extensions_to_remove = {
                ".csv",
                ".peprec",
                ".tab",
                ".png",
                ".weights",
            }

            for f in result_dir.iterdir():
                if f.is_file() and f.suffix in extensions_to_remove:
                   f.unlink()
            
            files_to_download = [
                log_file_path.name,
                #idXML_file_extra_100_XLs.name,
                idXML_file_extra_1_XLs.name,
            ]

            if plot_PseudROC:
                if not Path(idXML_file_100_XLs).exists():
                    st.warning(
                                f"The reference identification file without rescoring could not be found. "
                                f"Please run the NuXL search engine to enable a direct comparison "
                                f"and generate the Pseudo-ROC plot. "
                                f"It will not be added to the download files: {id_file}_rescoring_out_files"
                            )
                else:
                    #ploting_pseudoROC()
                    st.info(f"Generating Pseudo-ROC plot...",  icon="â„¹ï¸")
                    fig, output_pdf = plot_FDR_plot(
                        idXML_id=str(idXML_file_100_XLs),
                        idXML_extra=str(idXML_file_extra_100_XLs),
                        FDR_level=20,
                        exp_name=str(Path(idXML_file).stem)
                    )

                    #show figure
                    show_fig(fig,  f"{Path(idXML_file_extra_100_XLs).stem}_PseudoROC_plot_rescoring")

                    files_to_download.append(Path(output_pdf).name)
                    #files_to_download.append(idXML_file_100_XLs.name)

            if not Path(idXML_file_1_XLs).exists():
                st.warning(
                            f"The reference identification file without rescoring could not be found. "
                            f"It will not be added to the download files: {id_file}_rescoring_out_files"
                        )
            else:
                files_to_download.append(idXML_file_1_XLs.name)

            st.info(f"Preparing download link for rescoring output files ...",  icon="â„¹ï¸")
            #download_selected_result_files(files_to_download, link_name=f":arrow_down: {id_file}_rescoring_out_files", zip_filename=f"{id_file}_rescoring_out_files")
            download_selected_result_files_new(files_to_download, link_name=f":arrow_down: {id_file}_rescoring_out_files", zip_filename=f"{id_file}_rescoring_out_files")

            st.success("âš¡ï¸ **Rescoring Completed Successfully!** âš¡ï¸")

        else:
            # Display error message
            st.error(
                    f"âš ï¸ **Rescoring Failed**\n\n"
                    f"Please look at the log.\n"
                    )
            
# At the end of each page, always save parameters (including any changes via widgets with key)
save_params(params)


