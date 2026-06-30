import re
from pathlib import Path

import streamlit as st
from src.common.common import page_setup

page_setup()

st.title("Documentation")

st.markdown(
    """
    This page provides user guides for the main NuXLApp workflows.

    Select a workflow guide below to learn how to prepare input files, configure
    parameters, run the analysis, and understand the generated output files.
    """
)

cols = st.columns(2)

pages = {
    "NuXL Workflow": Path("docs", "nuxl_workflow_user_guide.md"),
    "Rescoring Workflow": Path("docs", "rescoring_workflow_user_guide.md"),
    "DIA Library Generation": Path("docs", "dia_library_generation_workflow_user_guide.md"),
}

page = cols[0].selectbox(
    "**Workflow user guide**",
    list(pages.keys()),
)


def render_markdown_with_local_images(markdown_content: str, markdown_dir: Path) -> None:
    """
    Render Markdown content and display local Markdown images with st.image().

    Image paths are resolved relative to the Markdown file location.
    This allows the same Markdown image paths to work in GitHub and Streamlit.
    """

    image_pattern = r"!\[(.*?)\]\((.*?)\)"
    parts = re.split(image_pattern, markdown_content)

    i = 0
    while i < len(parts):
        text = parts[i]

        if text.strip():
            st.markdown(text)

        if i + 2 < len(parts):
            alt_text = parts[i + 1]
            image_src = parts[i + 2]

            image_path = markdown_dir / image_src

            if image_path.exists():
                st.image(
                    str(image_path),
                    caption=alt_text,
                    width=950,
                )
            else:
                st.warning(f"Image not found: {image_path}")

        i += 3


md_path = pages[page]

with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

render_markdown_with_local_images(content, md_path.parent)