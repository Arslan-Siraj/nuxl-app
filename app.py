import streamlit as st
from pathlib import Path
import json
# For some reason the windows version only works if this is imported here
import pyopenms

if "settings" not in st.session_state:
        with open("settings.json", "r") as f:
            st.session_state.settings = json.load(f)

if __name__ == '__main__':
    pages = {
        str(st.session_state.settings["app-name"]) : [
            st.Page(Path("content", "quickstart.py"), title="Quickstart", icon="👋"),
            st.Page(Path("content", "documentation.py"), title="Documentation", icon="📖"),
        ],
        "NuXL Search Engine": [
            st.Page(Path("content", "nuxl_workflow.py"), title="NuXL search engine", icon="⚙️"),
        ],
        "NuXL Rescoring Workflow": [
            st.Page(Path("content", "nuxl_rescoring_workflow.py"), title="NuXL rescoring workflow", icon="⚙️"),
        ],
        "DIA library generation": [
            st.Page(Path("content", "dia_library_workflow.py"), title="DIA library generation", icon="⚙️"),
        ],
    }

    pg = st.navigation(pages)
    pg.run()
