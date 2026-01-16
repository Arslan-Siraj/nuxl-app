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

save_params(params)