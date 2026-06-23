import streamlit as st
from src.common.common import page_setup
from src.nuxl_workflow import Workflow

params = page_setup()

wf = Workflow()

st.title('⚙️ Run NuXL Search Engine', 
         help="Run NuXL search engine to analyze protein-RNA/DNA cross-linking samples. ref: https://doi.org/10.1093/nar/gkaf727"
        )

t = st.tabs(["📁 **Files**", "⚙️ **Configure**", "🚀 **Run**"])
with t[0]:
    wf.show_file_upload_section()

with t[1]:
    wf.show_parameter_section()

with t[2]:
    wf.show_execution_section()