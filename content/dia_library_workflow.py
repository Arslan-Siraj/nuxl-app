import streamlit as st
from src.common.common import page_setup
from src.spectral_library_workflow import Workflow

params = page_setup()

wf = Workflow()

st.title("⚙️ Spectral library generation", 
         help="Generate spectral libraries from identification results for DIA analysis. Used OpenNuXL identification files. ref: https://github.com/timosachsenberg/NuXLDIA"
        )

t = st.tabs(["📁 **File Upload**", "⚙️ **Configure**", "🚀 **Run**"])
with t[0]:
    wf.show_file_upload_section()

with t[1]:
    wf.show_parameter_section()

with t[2]:
    wf.show_execution_section()