import re
from pathlib import Path

import streamlit as st
from src.common.common import page_setup


page_setup()

st.title("Documentation")

cols = st.columns(2)

pages = {
    "NuXL Workflow User Tutorial": Path("docs", "nuxl_workflow_user_tutorial.md"),
    "NuXL Rescoring Workflow User Tutorial": Path("docs", "nuxl_rescoring_workflow_user_tutorial.md"),
}

page = cols[0].selectbox(
    "**Content**",
    list(pages.keys()),
)


def render_markdown_with_local_images(markdown_content: str) -> None:
    """
    Render Markdown content and display local Markdown images with st.image().
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
            image_path = Path(parts[i + 2])

            if image_path.exists():
                st.image(
                    str(image_path),
                    caption=alt_text,
                    use_column_width=True,
                )
            else:
                st.warning(f"Image not found: {image_path}")

        i += 3


with open(pages[page], "r", encoding="utf-8") as f:
    content = f.read()

render_markdown_with_local_images(content)