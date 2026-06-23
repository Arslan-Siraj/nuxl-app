import streamlit as st
from src.common.common import page_setup
from src.nuxl_rescoring_workflow import Workflow

params = page_setup()

wf = Workflow()

st.title('⚙️ Rescoring Workflow',
         help="Rescoring with Data-Driven Features from Machine Learning Models. Rescoring refers to the post-processing of initial identification results "
        "to improve discrimination between correct and incorrect matches by "
        "incorporating additional evidence, such as predicted retention time or "
        "fragment ion intensities. Such approaches have been shown to increase "
        "identification confidence and reduce false discovery rates in complex "
        "proteomics and cross-linking mass spectrometry analyses "
        "(see Proteomics 2023, DOI: 10.1002/pmic.202300144)."
        )

t = st.tabs(["📁 **File Upload**", "⚙️ **Configure**", "🚀 **Run**"])
with t[0]:
    wf.show_file_upload_section()

with t[1]:
    wf.show_parameter_section()

with t[2]:
    wf.show_execution_section()