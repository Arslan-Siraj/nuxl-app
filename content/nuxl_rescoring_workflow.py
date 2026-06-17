import streamlit as st
from src.common.common import page_setup
from src.nuxl_rescoring_workflow import Workflow

params = page_setup()

wf = Workflow()

st.title('Rescoring Workflow')

t = st.tabs(["📁 **File Upload**", "⚙️ **Configure**", "🚀 **Run**"])
with t[0]:
    wf.show_file_upload_section()

with t[1]:
    wf.show_parameter_section()

with t[2]:
    wf.show_execution_section()