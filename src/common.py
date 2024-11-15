import json
import os
import shutil
import sys
import uuid
import time
from typing import Any
from pathlib import Path
from streamlit.components.v1 import html

import streamlit as st
import pandas as pd

try:
    from tkinter import Tk, filedialog

    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

from src.captcha_ import captcha_control

# Detect system platform
OS_PLATFORM = sys.platform


# set these variables according to your project
APP_NAME = "NuXL"
REPOSITORY_NAME = "nuxl-app"


def load_params(default: bool = False) -> dict[str, Any]:
    """
    Load parameters from a JSON file and return a dictionary containing them.

    If a 'params.json' file exists in the workspace, load the parameters from there.
    Otherwise, load the default parameters from 'assets/default-params.json'.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly. Also make sure that all items from
    the parameters dictionary are accessible from the session state as well.

    Args:
        default (bool): Load default parameters. Defaults to True.

    Returns:
        dict[str, Any]: A dictionary containing the parameters.
    """
    # Construct the path to the parameter file
    path = Path(st.session_state.workspace, "params.json")

    # Load the parameters from the file, or from the default file if the parameter file does not exist
    if path.exists() and not default:
        with open(path, "r") as f:
            params = json.load(f)
    else:
        with open("assets/default-params.json", "r") as f:
            params = json.load(f)

    # Return the parameter dictionary
    return params


def save_params(params: dict[str, Any]) -> None:
    """
    Save the given dictionary of parameters to a JSON file.

    If a 'params.json' file already exists in the workspace, overwrite it with the new parameters.
    Otherwise, create a new 'params.json' file in the workspace directory and save the parameters there.

    Additionally, check if any parameters have been modified by the user during the current session
    and update the values in the parameter dictionary accordingly.

    This function should be run at the end of each page, if the parameters dictionary has been modified directly.
    Note that session states with the same keys will override any direct changes!

    Args:
        params (dict[str, Any]): A dictionary containing the parameters to be saved.

    Returns:
        None
    """
    # Update the parameter dictionary with any modified parameters from the current session
    for key, value in st.session_state.items():
        if key in params.keys():
            params[key] = value

    # Save the parameter dictionary to a JSON file in the workspace directory
    path = Path(st.session_state.workspace, "params.json")
    with open(path, "w") as outfile:
        json.dump(params, outfile, indent=4)



def page_setup(page: str = "") -> dict[str, Any]:
    """
    Set up the Streamlit page configuration and determine the workspace for the current session.

    This function should be run at the start of every page for setup and to get the parameters dictionary.

    Args:
        page (str, optional): The name of the current page, by default "".

    Returns:
        dict[str, Any]: A dictionary containing the parameters loaded from the parameter file.
    """
    if "settings" not in st.session_state:
        with open("settings.json", "r") as f:
            st.session_state.settings = json.load(f)

    # Set Streamlit page configurations
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="assets/OpenMS.png",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    # Expand sidebar navigation
    st.markdown(
        """
        <style>
            .stMultiSelect [data-baseweb=select] span{
                max-width: 500px;
                font-size: 1rem;
            }
            div[data-testid='stSidebarNav'] ul {max-height:none}
        </style>
        """,
        unsafe_allow_html=True,
    )

    #st.logo("assets/pyopenms_transparent_background.png")

    # Create google analytics if consent was given
    if (
        ("tracking_consent" not in st.session_state) 
        or (st.session_state.tracking_consent is None)
        or (not st.session_state.settings['online_deployment'])
    ):
        st.session_state.tracking_consent = None
    else:
        if (st.session_state.settings["analytics"]["google-analytics"]["enabled"]) and (
            st.session_state.tracking_consent["google-analytics"] == True
        ):
            html(
                """
                <!DOCTYPE html>
                <html lang="en">
                    <head></head>
                    <body><script>
                    window.parent.gtag('consent', 'update', {
                    'analytics_storage': 'granted'
                    });
                    </script></body>
                </html>
                """,
                width=1,
                height=1,
            )
        if (st.session_state.settings["analytics"]["piwik-pro"]["enabled"]) and (
            st.session_state.tracking_consent["piwik-pro"] == True
        ):
            html(
                """
                <!DOCTYPE html>
                <html lang="en">
                    <head></head>
                    <body><script>
                    var consentSettings = {
                        analytics: { status: 1 } // Set Analytics consent to 'on' (1 for on, 0 for off)
                    };
                    window.parent.ppms.cm.api('setComplianceSettings', { consents: consentSettings }, function() {
                        console.log("PiwikPro Analytics consent set to on.");
                    }, function(error) {
                        console.error("Failed to set PiwikPro analytics consent:", error);
                    });
                    </script></body>
                </html>
                """,
                width=1,
                height=1,
            )

    # Determine the workspace for the current session
    if ("workspace" not in st.session_state) or (
        ("workspace" in st.query_params)
        and (st.query_params.workspace != st.session_state.workspace.name)
    ):
        # Clear any previous caches
        st.cache_data.clear()
        st.cache_resource.clear()
        # Check location
        if not st.session_state.settings["online_deployment"]:
            st.session_state.location = "local"
            st.session_state["previous_dir"] = os.getcwd()
            st.session_state["local_dir"] = ""
        else:
            st.session_state.location = "online"
        # if we run the packaged windows version, we start within the Python directory -> need to change working directory to ..\streamlit-template
        if "windows" in sys.argv:
            os.chdir("../nuxl-app-main")
        # Define the directory where all workspaces will be stored
        workspaces_dir = Path("..", "workspaces-" + REPOSITORY_NAME)
        if "workspace" in st.query_params:
            st.session_state.workspace = Path(workspaces_dir, st.query_params.workspace)
        elif st.session_state.location == "online":
            workspace_id = str(uuid.uuid1())
            st.session_state.workspace = Path(workspaces_dir, workspace_id)
            st.query_params.workspace = workspace_id
        else:
            st.session_state.workspace = Path(workspaces_dir, "default")
            st.query_params.workspace = "default"

        if st.session_state.location != "online":
            # not any captcha so, controllo should be true
            st.session_state["controllo"] = True

    if "workspace" not in st.query_params:
        st.query_params.workspace = st.session_state.workspace.name

    # Make sure the necessary directories exist
    st.session_state.workspace.mkdir(parents=True, exist_ok=True)
    Path(st.session_state.workspace, 
         "mzML-files").mkdir(parents=True, exist_ok=True)

    Path(st.session_state.workspace,
         "fasta-files").mkdir(parents=True, exist_ok=True)
    
    Path(st.session_state.workspace,
         "result-files").mkdir(parents=True, exist_ok=True)
    
    # Render the sidebar
    params = render_sidebar(page)

    # If run in hosted mode, show captcha as long as it has not been solved
    #if not "local" in sys.argv:
    #    if "controllo" not in st.session_state:
    #        # Apply captcha by calling the captcha_control function
    #        captcha_control()
    
    # If run in hosted mode, show captcha as long as it has not been solved
    if 'controllo' not in st.session_state or params["controllo"] == False:
        # Apply captcha by calling the captcha_control function
        captcha_control()  

    return params


def render_sidebar(page: str = "") -> None:
    """
    Renders the sidebar on the Streamlit app, which includes the workspace switcher,
    the mzML file selector, the logo, and settings.

    Args:
        params (dict): A dictionary containing the initial parameters of the app.
            Used in the sidebar to display the following settings:
            - selected-mzML-files : str
                A string containing the selected mzML files.
            - image-format : str
                A string containing the image export format.
        page (str): A string indicating the current page of the Streamlit app.

    Returns:
        None
    """
    params = load_params()
    with st.sidebar:
        # The main page has workspace switcher
        if page == "main":
            st.markdown("🖥️ **Workspaces**")
            # Define workspaces directory outside of repository
            workspaces_dir = Path("..", "workspaces-"+REPOSITORY_NAME)
            # Online: show current workspace name in info text and option to change to other existing workspace
            if st.session_state.location == "online":
                # Change workspace...
                new_workspace = st.text_input("enter workspace", "")
                if st.button("**Enter Workspace**") and new_workspace:
                    path = Path(
                        workspaces_dir, new_workspace)
                    if path.exists():
                        st.session_state.workspace = path
                    else:
                        st.warning("⚠️ Workspace does not exist.")
                # Display info on current workspace and warning
                st.info(
                    f"""💡 Your workspace ID:

**{st.session_state['workspace'].name}**

You can share this unique workspace ID with other people.

⚠️ Anyone with this ID can access your data!"""
                )
            # Local: user can create/remove workspaces as well and see all available
            elif st.session_state.location == "local":
                # Define callback function to change workspace
                def change_workspace():
                    for key in params.keys():
                        if key in st.session_state.keys():
                            del st.session_state[key]
                    st.session_state.workspace = Path(
                        workspaces_dir, st.session_state["chosen-workspace"]
                    )
                # Get all available workspaces as options
                options = [file.name for file in workspaces_dir.iterdir()
                           if file.is_dir()]
                # Let user chose an already existing workspace
                st.selectbox(
                    "choose existing workspace",
                    options,
                    index=options.index(
                        str(st.session_state.workspace.stem)),
                    on_change=change_workspace,
                    key="chosen-workspace"
                )
                # Create or Remove workspaces
                create_remove = st.text_input(
                    "create/remove workspace", "")
                path = Path(workspaces_dir, create_remove)
                # Create new workspace
                if st.button("**Create Workspace**"):
                    path.mkdir(parents=True, exist_ok=True)
                    st.session_state.workspace = path
                    st.rerun()
                # Remove existing workspace and fall back to default
                if st.button("⚠️ Delete Workspace"):
                    if path.exists():
                        shutil.rmtree(path)
                        st.session_state.workspace = Path(
                            workspaces_dir, "default"
                        )
                        st.rerun()

        # All pages have settings, workflow indicator and logo
        with st.expander("⚙️ **Settings**"):
            img_formats = ["svg", "png", "jpeg", "webp"]
            st.selectbox(
                "image export format",
                img_formats,
                img_formats.index(params["image-format"]), key="image-format"
            )

            table_formats = ["tsv", "csv"] #,"xlsx"
            st.selectbox(
                "table export format",
                table_formats,
                table_formats.index(params["table-format"]), key="table-format"
            )
            # Button to reset parameters, sidebar widgets are settings and will not be resettet!
            if st.button("⚠️ Load default parameters"):
                params = load_params(default=True)

        if page != "main":
            st.info(
                f"**{Path(st.session_state['workspace']).stem}**")
        st.image("assets/OpenMS.png", "powered by")
    return params

def v_space(n: int, col=None) -> None:
    """
    Prints empty strings to create vertical space in the Streamlit app.

    Args:
        n (int): An integer representing the number of empty lines to print.
        col: A streamlit column can be passed to add vertical space there.

    Returns:
        None
    """
    for _ in range(n):
        if col:
            col.write("#")
        else:
            st.write("#")


def display_large_dataframe(
    df, chunk_sizes: list[int] = [10, 100, 1_000, 10_000], **kwargs
):
    """
    Displays a large DataFrame in chunks with pagination controls and row selection.

    Args:
        df: The DataFrame to display.
        chunk_sizes: A list of chunk sizes to choose from.
        ...: Additional keyword arguments to pass to the `st.dataframe` function. See: https://docs.streamlit.io/develop/api-reference/data/st.dataframe

    Returns:
        Index of selected row.
    """

    # Dropdown for selecting chunk size
    chunk_size = st.selectbox("Select Number of Rows to Display", chunk_sizes)

    # Calculate total number of chunks
    total_chunks = (len(df) + chunk_size - 1) // chunk_size

    if total_chunks > 1:
        page = int(st.number_input("Select Page", 1, total_chunks, 1, step=1))
    else:
        page = 1

    # Function to get the current chunk of the DataFrame
    def get_current_chunk(df, chunk_size, chunk_index):
        start = chunk_index * chunk_size
        end = min(
            start + chunk_size, len(df)
        )  # Ensure end does not exceed dataframe length
        return df.iloc[start:end], start, end

    # Display the current chunk
    current_chunk_df, start_row, end_row = get_current_chunk(df, chunk_size, page - 1)

    event = st.dataframe(current_chunk_df, **kwargs)

    st.write(
        f"Showing rows {start_row + 1} to {end_row} of {len(df)} ({get_dataframe_mem_useage(current_chunk_df):.2f} MB)"
    )

    rows = event["selection"]["rows"]
    if not rows:
        return None
    # Calculate the index based on the current page and chunk size
    base_index = (page - 1) * chunk_size
    return base_index + rows[0]


def show_table(df: pd.DataFrame, download_name: str = "") -> None:
    """
    Displays a pandas dataframe using Streamlit's `dataframe` function and
    provides a download button for the same table.

    Args:
        df (pd.DataFrame): The pandas dataframe to display.
        download_name (str): The name to give to the downloaded file. Defaults to empty string.

    Returns:
        df (pd.DataFrame): The possibly edited dataframe.
    """
    # Show dataframe using container width
    st.dataframe(df, use_container_width=True)
    # Show download button with the given download name for the table if name is given
    if download_name:
        if st.session_state["table-format"] == "csv":
            st.download_button(
                "Download Table",
                df.to_csv(sep=",").encode("utf-8"),
                download_name.replace(" ", "-") + ".csv", help="download table in csv format"
            )
        elif st.session_state["table-format"] == "tsv":
            st.download_button(
                "Download Table",
                df.to_csv(sep="\t").encode("utf-8"),
                download_name.replace(" ", "-") + ".tsv", help="download table in tsv format"
            )
        '''elif st.session_state["table-format"] == "xlsx":
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)
            output.seek(0)
            st.download_button(
                "Download Table",
                output,
                download_name.replace(" ", "-") + ".xlsx", help="download table in xlsx format"
            )'''
            
    return df

def download_table(df: pd.DataFrame, download_name: str = "") -> None:
    """
    provides a download button for the dataframe.

    Args:
        df (pd.DataFrame): The pandas dataframe to download.
        download_name (str): The name to give to the downloaded file. Defaults to empty string.

    Returns:
        None
    """
    # Show download button with the given download name for the table if name is given
    if download_name:
        if st.session_state["table-format"] == "csv":
            st.download_button(
                "Download Table",
                df.to_csv(sep=",").encode("utf-8"),
                download_name.replace(" ", "-") + ".csv", help="download table in csv format"
            )
        elif st.session_state["table-format"] == "tsv":
            st.download_button(
                "Download Table",
                df.to_csv(sep="\t").encode("utf-8"),
                download_name.replace(" ", "-") + ".tsv", help="download table in tsv format"
            )
        '''elif st.session_state["table-format"] == "xlsx":
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)
            output.seek(0)
            st.download_button(
                "Download Table",
                output,
                download_name.replace(" ", "-") + ".xlsx", help="download table in xlsx format"
            )'''

def show_fig(fig, download_name: str, container_width: bool = True) -> None:
    """
    Displays a Plotly chart and adds a download button to the plot.

    Args:
        fig (plotly.graph_objs._figure.Figure): The Plotly figure to display.
        download_name (str): The name for the downloaded file.
        container_width (bool, optional): If True, the figure will use the container width. Defaults to True.

    Returns:
        None
    """
    # Display plotly chart using container width and removed controls except for download
    st.plotly_chart(
        fig,
        use_container_width=container_width,
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": [
                "zoom",
                "pan",
                "select",
                "lasso",
                "zoomin",
                "autoscale",
                "zoomout",
                "resetscale",
            ],
            "toImageButtonOptions": {
                "filename": download_name,
                "format": st.session_state["image-format"],
            },
        },
    )


def reset_directory(path: Path) -> None:
    """
    Remove the given directory and re-create it.

    Args:
        path (Path): Path to the directory to be reset.

    Returns:
        None
    """
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

# General warning/error messages
WARNINGS = {
    "missing-mzML": "Upload or select some mzML files first!",
}

ERRORS = {
    "general": "Something went wrong.",
    "workflow": "Something went wrong during workflow execution.",
    "visualization": "Something went wrong during visualization of results.",
}