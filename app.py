import streamlit as st
from pathlib import Path
# For some reason the windows version only works if this is imported here
import pyopenms

if __name__ == '__main__':
    pages = {
        "NuXL App " : [
            st.Page(Path("content", "quickstart.py"), title="Quickstart", icon="👋"),
            st.Page(Path("content", "file_upload.py"), title="File Upload", icon="📂"),
            st.Page(Path("content", "analyze.py"), title="Analysis", icon="⚙️"),
            st.Page(Path("content", "rescoring.py"), title="Rescoring", icon="⚙️"),
            st.Page(Path("content", "dia_library.py"), title="DIA Library generation", icon="⚙️"),
            st.Page(Path("content", "results.py"), title="Output", icon="📊"),
        ]
    }

    pg = st.navigation(pages)
    pg.run()