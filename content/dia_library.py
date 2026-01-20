from src.common import *
import streamlit as st
import threading
import os

from pathlib import Path
from src.result_files import *
from src.run_subprocess import *
from datetime import datetime

#from nuxl_rescore import run_pipeline
params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()

st.title("DIA library generation", 
         help="Generate spectral libraries from identification results for DIA analysis. Used OpenNuXL identification files. ref: https://github.com/timosachsenberg/NuXLDIA"
        )

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

# result directory path in current session state
result_dir: Path = Path(st.session_state.workspace, "result-files")

session_idXML_files = [
        f.name
        for f in Path(st.session_state.workspace, "result-files").iterdir()
        if (
            f.name.endswith(".idXML")
            and not any(x in f.name for x in ["RT_feat", "_perc.idXML", "RT_Int_feat", "updated_feat", "_sse_perc_" ])
        )
    ]

#st.info(f"Found {len(session_idXML_files)} files in result-files directory.", icon="ℹ️")
#st.write(session_idXML_files)


if not session_idXML_files:
    st.error("No valid .idXML files found in the result-files directory. please run NuXL search-engine")

if "selected-mzML-files" not in st.session_state:
    st.session_state["selected-mzML-files"] = params.get("selected-mzML-files", [])

mzML_files_ = [f.name for f in Path(st.session_state.workspace, "mzML-files").iterdir()]

# form to take input from user
with st.form("library_generation_form", clear_on_submit=False):
    # --- Select mzML/raw files ---
    selected_mzML_files = st.multiselect(
        "Choose mzML/raw file(s)",
        [f for f in mzML_files_ if not (f.endswith(".csv") or f.endswith(".mgf"))],
        help="If file not here, please upload via File Upload and run the NuXL search engine first.",
    )

    # Let user provide a library name tag
    library_name_input = st.text_input(
      "Library output file name tag",
      help="This will be name of the file generated as library: please specify the name"
    )

    uploaded_file = st.file_uploader(
      "Upload library file from MSFragger (optional)",
      type=["tsv"],  # or restrict: ["tsv", "csv", "txt"]
      help="This will used for iRT alignment in DIA analysis. Please upload a library file from MSFragger."
    )

    iRT_calibration_model = st.radio(
      "iRT calibration model",
      options=["linear", "piecewise"],
      index=0,
      help="Select the functional form used for iRT calibration."
      )    
    #run_FileInfo = st.checkbox("Run mzML FileInfo", value = True, help="If checked, FileInfo will be run on the selected mzML files to provide additional information in log.")

    # Submit button
    submit_button = st.form_submit_button("Generate Library", type="primary")

# Create a flag to terminate the subprocess
terminate_flag = threading.Event()
terminate_flag.set()

# Function to terminate the subprocess
def terminate_subprocess():
      """Set flag to terminate subprocess."""
      global terminate_flag
      terminate_flag.set()

success_pipline = False
if submit_button:
    user_library_name = library_name_input.strip()

    if st.button("Terminate/Clear", key="terminate-button", type="secondary"):
      # terminate subprocess
      terminate_subprocess()
      st.warning("Process terminated. The analysis may not be complete.")

      # clear form
      st.rerun() 

    with st.status("Running analysis... Please wait until analysis done 😑"):
      if not selected_mzML_files:
            st.warning("Please select at least one experiment (mzML/raw file) for generating the library.")
      else:
            # Extract base names (without extension) for matching
            mzml_basenames = {os.path.splitext(os.path.basename(f))[0] for f in selected_mzML_files}

            # Define the required NuXL result suffixes per mzML
            required_suffixes = {
                  "_perc_0.0100_XLs.idXML",
                  "_perc_0.0100_peptides.idXML",
            }

            matched_idxmls = []
            missing_reports = []

            # Check each selected mzML basename
            for basename in mzml_basenames:
                  # Find all idXML files corresponding to this mzML
                  found = {
                        f for f in session_idXML_files
                        if os.path.basename(f).startswith(basename)
                        and any(f.endswith(suf) for suf in required_suffixes)
                  }

                  # The expected filenames for this mzML
                  expected = {basename + suf for suf in required_suffixes}

                  if found != expected:
                        # Report missing files for this mzML
                        missing = expected - found
                        missing_reports.append({
                        "mzML": basename,
                        "missing": ", ".join(sorted(missing)),
                        })
                  else:
                        matched_idxmls.extend(found)

            # --- Display errors for missing files ---
            if missing_reports:
                  for report in missing_reports:
                        st.error(
                        f"Missing NuXL results for '{report['mzML']}': {report['missing']}. "
                        "Please run the NuXL search engine first or exclude from selection."
                        )
                  st.stop()  # Stop the app if required files are missing

            console_output = st.empty()

            # Central log buffer
            log_lines: list[str] = []

            def log(msg: str):
                  log_lines.append(msg)
                  console_output.text("".join(log_lines))

            # --- Display matched idXML files ---
            if matched_idxmls:
                  log("====> Corresponding idXML filenames for selected experiment mzML/raw files <====\n")
                  for f in matched_idxmls:
                        log(f"- {f}\n")

                  if not user_library_name:  # If input is empty
                              user_library_name = f"library_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                              log(f"\n====> Library output file name tag is empty!!! tag name generated: {user_library_name} <====\n")

                  output_folder_library = Path(
                              st.session_state.workspace,
                              "result-files",
                              user_library_name
                  )

                  try:
                        if output_folder_library.exists():
                              raise FileExistsError(f"Library output folder already exists: {output_folder_library}")
                        
                        # Create the folder
                        output_folder_library.mkdir(parents=True)
                        log(f"\n====> Output folder created: {output_folder_library} <====\n")

                  except FileExistsError as e:
                        log(f"\n====> ERROR: {e}\n")
                        st.error(f"Library output folder already exists: {output_folder_library}. Please choose a different library output file name tag.")
                        st.stop()

            log("\n====> Exporting idXML files to TextExporter format <====\n")
            
            TextExporter_exec = os.path.join(os.getcwd(),'TextExporter')
            for idxml_file in matched_idxmls:
                  # Input file: from result-files folder
                  idxml_path_in = Path(st.session_state.workspace, "result-files", idxml_file)

                  # Output file: same folder, stem + .unknown
                  idxml_path_out = output_folder_library / (idxml_path_in.stem + ".unknown")
                  # Append current file being processed
                  log(f"--->Processing idxml_file: {idxml_file}\n")
                  
                  if os.name == 'nt':
                        args_convert = [
                                          TextExporter_exec,
                                          "-in", str(idxml_path_in),
                                          "-out", str(idxml_path_out),
                                          "-id:peptides_only",
                                          "-id:add_hit_metavalues","0"
                                    ]
                  else:
                        args_convert = [
                                          "TextExporter",
                                          "-in", str(idxml_path_in),
                                          "-out", str(idxml_path_out),
                                          "-id:peptides_only",
                                          "-id:add_hit_metavalues","0"
                                    ]

                  #st.info(f"Running: {' '.join(args_convert)}")

                  result = subprocess.run(
                        args_convert,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                  )

                  if result.returncode != 0:
                        log("idXML → TextExporter conversion failed")
                        st.error("TextExporter conversion failed")
                        st.stop()
                  else:
                        log(f"{result.stdout}\n")
       

            #--------------- File Info---------------------
            log("====> mzML file Info with FileInfo OpenMS <====\n")

            FileInfo_exec = os.path.join(os.getcwd(), 'FileInfo')
            #st.write(selected_mzML_files)
            for mzml_file in selected_mzML_files:
                  # Input file: from result-files folder
                  mzml_path_in = Path(st.session_state.workspace, "mzML-files", mzml_file)

                  # Append current file being processed
                  log(f"---> Processing mzml file FileInfo: {mzml_file}\n")

                  if os.name == 'nt':
                        args_FileInfo = [
                                          FileInfo_exec,
                                          "-in", str(mzml_path_in)
                                    ]
                  else:
                        args_FileInfo = [
                                          "FileInfo",
                                          "-in", str(mzml_path_in)
                                    ]

                  #st.info(f"Running: {' '.join(args_FileInfo)}")

                  result_FileInfo = subprocess.run(
                              args_FileInfo,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True
                        )

                  if result_FileInfo.returncode != 0:
                              console_output.text("FileInfo failed")
                              st.text(result.stderr)
                              st.error("FileInfo failed")
                              st.stop()
                  else:
                        log(f"{result_FileInfo.stdout}\n")
            
            #-------------------check FileInfo output-----------------
            if "ion mobility: <none> .. <none>" in result_FileInfo.stdout:
                  log("\n====> WARNING: No ion mobility information found in mzML files. Please ensure your data contains ion mobility for library generation. <====\n")
                  st.error("No ion mobility information found in mzML files. Please ensure your data contains ion mobility for library generation.")
                  st.stop()

            #---------------upload the library file from MSFragger---------------------
            if uploaded_file is not None:
                  uploaded_path = output_folder_library / uploaded_file.name

                  # Prevent accidental overwrite
                  if uploaded_path.exists():
                        st.error(f"File already exists in library folder: {uploaded_file.name}")
                        st.stop()

                  # Write file to disk
                  with open(uploaded_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                  log(f"====> Uploaded library file saved {uploaded_path.name} at {uploaded_path} <====\n\n")
  
            #----------------Final library generation--------------------
            log("====> Generating library <==== \n")

            # --- Python interpreter (always correct in Streamlit)
            python_exec = sys.executable

            # --- Script path (src is one level above cwd)
            BASE_DIR = Path(__file__).resolve().parent.parent
            Gen_library_cmd = (BASE_DIR / "src" / "nuxl2dia.py").resolve()
            if uploaded_file is not None:
                  unknown_files = sorted(output_folder_library.glob("*.unknown"))

                  if not unknown_files:
                        st.error("Required .unknown files not found for library generation.")
                        st.stop()

                  # --- Build arguments
                  args_gen_lib = [
                        python_exec,
                        str(Gen_library_cmd),
                        "-i",
                        *map(str, unknown_files),
                        "-o",
                        str(output_folder_library / f"{library_name_input}.tsv"),
                        "--irt",
                        str(iRT_calibration_model),
                        "--irt-ref",
                        str(uploaded_path), 
                        "-v",                        
                  ]
            
            else:
                  log("\n====> No iRT library file uploaded; skipping iRT alignment. <====\n\n")

                  # --- Expand input files explicitly (NO wildcards!)
                  unknown_xls = sorted(output_folder_library.glob("*_XLs.unknown"))
                  unknown_pep = sorted(output_folder_library.glob("*_peptides.unknown"))

                  if not unknown_xls or not unknown_pep:
                        st.error("Required .unknown files not found for library generation.")
                        st.stop()

                  # --- Build arguments
                  args_gen_lib = [
                        python_exec,
                        str(Gen_library_cmd),
                        "-i",
                        *map(str, unknown_xls),
                        *map(str, unknown_pep),
                        "-o",
                        str(output_folder_library / f"{library_name_input}.tsv"),
                        "-v",
                  ]


            #st.info("Running:\n" + " ".join(args_gen_lib))

            with subprocess.Popen(
                  args_gen_lib,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT,  # merge stderr with stdout
                  text=True,
                  bufsize=1
                  ) as proc:
                        for line in proc.stdout:
                              log(line)  # append each line to console_output and log_lines
                        proc.wait()

            if proc.returncode != 0:
                  st.error("Library generation failed")
                  st.stop()
            else:
                  log_file = output_folder_library / f"{library_name_input}_library_generation.log"
                  with open(log_file, "w") as f:
                        f.write("===== version info =====\n")
                        f.write(f"OpenMS version: {st.session_state.settings['openms-version']}\n")
                        f.write(f"NuXLApp version: {st.session_state.settings['version']}\n")
                        f.writelines(log_lines)
                  success_pipline = True

    #--------------- Save log file---------------------
    if success_pipline:
      st.info(f"Preparing download link for library output files ...",  icon="ℹ️")

      download_folder_library(output_folder_library, f":arrow_down: {library_name_input}_library_out_files", zip_name=f"{library_name_input}_library_out_files.zip")
      st.success("⚡️ **Library Generation Completed Successfully!** ⚡️")

save_params(params)