from src.common import *
import streamlit as st
import threading
import os

from pathlib import Path
from src.result_files import *
from src.run_subprocess import *
from src.view import plot_FDR_plot

#from nuxl_rescore import run_pipeline
params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()

st.title("DIA library generation", 
         help="Generate spectral libraries from identification results for DIA analysis. Used OpenNuXL identification files"
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

# --- Select mzML/raw files ---
selected_mzML_files = st.multiselect(
    "Choose mzML/raw file(s)",
    [f for f in mzML_files_ if not (f.endswith(".csv") or f.endswith(".mgf"))],
    help="If file not here, please upload via File Upload and run the NuXL search engine first.",
)

if selected_mzML_files:
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
                "Please run the NuXL search engine first."
            )
        st.stop()  # Stop the app if required files are missing

    # --- Display matched idXML files ---
    if matched_idxmls:
        with st.expander("Show crrosponding idXML filenames for selected mzML/raw files"):
            st.text("\n".join(matched_idxmls))

    st.info("Converting idXML with TextExporter to .unknown format for spectral library generation", icon="ℹ️")
    for idxml_file in matched_idxmls:
      # Input file: from result-files folder
      idxml_path_in = Path(st.session_state.workspace, "result-files", idxml_file)

      # Output file: same folder, stem + .unknown
      idxml_path_out = idxml_path_in.with_suffix(".unknown")
      TextExporter_exec = os.path.join(os.getcwd(),'TextExporter')
      if os.name == 'nt':
            args_convert = [
                              TextExporter_exec,
                              "-in", str(idxml_path_in),
                              "-out", str(idxml_path_out)
                        ]
      else:
            args_convert = [
                              "TextExporter",
                              "-in", str(idxml_path_in),
                              "-out", str(idxml_path_out)
                        ]

      #st.info(f"Running: {' '.join(args_convert)}")

      result = subprocess.run(
            args_convert,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
      )

      if result.returncode != 0:
            st.error("idXML → TextExporter conversion failed")
            st.text(result.stderr)
            st.stop()
      else:
            st.text(result.stdout)
    

#include peptides?
# FDR cutoffs?

## validation
save_params(params)
