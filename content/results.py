import streamlit as st
from src.nuxl_result_files import *
from src.nuxl_result_files_v import readAndProcessIdXML_v, read_protein_table_v

import pandas as pd
import plotly.graph_objects as go

from src.nuxl_view import (
    plot_ms2_spectrum,
    plot_ms2_spectrum_full,
    download_table,
    show_fig,
)

from st_aggrid import (
    GridOptionsBuilder,
    AgGrid,
    GridUpdateMode,
    ColumnsAutoSizeMode,
)

import pyopenms as poms
import re
import io
import zipfile
import os
from pathlib import Path

from src.common.common import (
    page_setup,
    save_params,
    v_space,
    show_table,
    TK_AVAILABLE,
    tk_directory_dialog,
)


params = page_setup()


# ============================================================
# Performance helpers
# ============================================================

@st.cache_resource(show_spinner="Loading mzML MS2 spectra...", max_entries=4)
def load_ms2_peak_map_v(mzml_path_str: str, file_mtime: float):
    """
    Load an mzML file once, keep only MS2 spectra, normalize intensities,
    and index spectra by native ID for fast row-selection lookup.

    file_mtime is part of the cache key so replacing the mzML automatically
    invalidates the cached spectrum map.
    """
    mzml_path = Path(mzml_path_str).resolve()

    if not mzml_path.is_file():
        return None

    try:
        exp = poms.MSExperiment()
        poms.MzMLFile().load(str(mzml_path), exp)

        ms2_peak_map = {}

        for spec in exp:
            if spec.getMSLevel() != 2:
                continue

            mz, intensities = spec.get_peaks()

            if len(intensities) > 0:
                max_intensity = float(max(intensities))
                if max_intensity > 0:
                    intensities = intensities / max_intensity

            ms2_peak_map[spec.getNativeID()] = (mz, intensities)

        return ms2_peak_map

    except Exception as e:
        st.exception(e)
        return None


def get_cached_ms2_peak_map_v(mzml_path: Path):
    """Return cached native_id -> (mz, intensity) MS2 peak data."""
    mzml_path = Path(mzml_path).resolve()

    if not mzml_path.is_file():
        return None

    return load_ms2_peak_map_v(
        str(mzml_path),
        mzml_path.stat().st_mtime,
    )


def selected_rows_to_records_v(selected_rows):
    """Normalize AgGrid selected_rows output across st-aggrid versions."""
    if selected_rows is None:
        return []

    if isinstance(selected_rows, pd.DataFrame):
        return selected_rows.to_dict("records")

    if isinstance(selected_rows, list):
        return selected_rows

    return []


# These three columns can be extremely large because every CSM may contain
# hundreds of comma-separated peak values. They stay in the full server-side
# dataframe but are NEVER transmitted to AgGrid.
CSM_AGGRID_EXCLUDED_COLUMNS_V = (
    "intensities",
    "mz_values",
    "ions",
)


@st.cache_resource(show_spinner="Reading idXML...", max_entries=8)
def get_csm_view_assets_v(
    idxml_path_str: str,
    file_mtime: float,
):
    """
    Load/cache the full CSM dataframe and prepare a lighter browser dataframe.

    This wrapper is intentionally cache_resource even though the existing
    readAndProcessIdXML_v helper uses its own cache. Once this wrapper has
    loaded a file, subsequent Streamlit reruns reuse the exact dataframe
    object instead of repeatedly obtaining/serializing a large dataframe.

    Returns:
        full_df
            Complete CSM dataframe, including intensities/mz_values/ions.

        grid_df
            Same data except the three large per-peak columns are removed.

        specid_to_position
            Fast SpecId -> first dataframe row position lookup.
    """
    idxml_path = Path(idxml_path_str)

    full_df = readAndProcessIdXML_v(idxml_path)

    if full_df is None:
        return None, None, {}

    grid_df = full_df.drop(
        columns=list(CSM_AGGRID_EXCLUDED_COLUMNS_V),
        errors="ignore",
    )

    specid_to_position = {}

    if "SpecId" in full_df.columns:
        for position, spec_id in enumerate(full_df["SpecId"]):
            # Preserve the old behavior for duplicate SpecIds: first row wins.
            specid_to_position.setdefault(str(spec_id), position)

    return full_df, grid_df, specid_to_position


@st.cache_resource(show_spinner="Preparing table download...", max_entries=4)
def create_csm_download_payload_v(
    idxml_path_str: str,
    file_mtime: float,
    table_format: str,
):
    """
    Serialize the COMPLETE CSM dataframe once per file/version/format.

    This prevents full df.to_csv() work from repeating whenever Streamlit
    reruns because a row is selected or an ion-filter radio button changes.
    """
    full_df, _, _ = get_csm_view_assets_v(
        idxml_path_str,
        file_mtime,
    )

    if full_df is None:
        return b""

    separator = "\t" if table_format == "tsv" else ","

    return full_df.to_csv(
        sep=separator,
    ).encode("utf-8")


def show_csm_download_button_v(
    idxml_path: Path,
    download_name: str,
):
    """
    Show the same full CSM CSV/TSV download as before, but use cached
    serialization.

    The download still includes intensities, mz_values and ions.
    """
    table_format = st.session_state.get("table-format", "csv")

    if table_format not in ("csv", "tsv"):
        return

    extension = "tsv" if table_format == "tsv" else "csv"

    payload = create_csm_download_payload_v(
        str(idxml_path.resolve()),
        idxml_path.stat().st_mtime,
        table_format,
    )

    st.download_button(
        label="Download Table",
        data=payload,
        file_name=download_name.replace(" ", "-") + f".{extension}",
        help=f"download table in {extension} format",
        key=f"download_csm_table_v_{download_name}_{extension}",
    )


def clean_filename_with_regex_v(filename):
    # Remove feature prefixes at the beginning of the filename.
    prefix_pattern = r"^(RDDF_|RT_feat_|RT_Int_feat_|Int_feat_|updated_feat_)"

    # Remove score/XL suffix patterns.
    suffix_pattern = r"(_perc_\d\.\d{4}_XLs\.idXML|_\d\.\d{4}_XLs\.idXML)"

    filename = re.sub(prefix_pattern, "", filename)
    filename = re.sub(suffix_pattern, "", filename)

    return filename


def is_one_hundred_percent_xl_file_v(filename: str) -> bool:
    """Hide protein/report tabs for 1.0000 XL idXML files."""
    return (
        filename.endswith("_1.0000_XLs.idXML")
        or filename.endswith("_perc_1.0000_XLs.idXML")
    )


def annotation_matches_filter_v(annotation: str, ion_filter: str) -> bool:
    annotation = str(annotation).strip()

    if not annotation:
        return False

    if ion_filter == "all_annotated_peaks":
        return True

    if ion_filter == "exclude_b_y_ions":
        return not (
            annotation.startswith("b")
            or annotation.startswith("y")
        )

    if ion_filter == "only_b_y_ions":
        return (
            annotation.startswith("b")
            or annotation.startswith("y")
        )

    if ion_filter == "only_b_ions":
        return annotation.startswith("b")

    if ion_filter == "only_y_ions":
        return annotation.startswith("y")

    if ion_filter == "only_MI_ions":
        return annotation.startswith("MI")

    if ion_filter == "only_precursor_ions":
        return annotation.startswith("[M")

    return True


def filtered_annotation_v(annotation: str, ion_filter: str) -> str:
    annotation = str(annotation).strip()

    if annotation_matches_filter_v(annotation, ion_filter):
        return annotation

    return " "


def split_peak_values_v(value: object, cast_type=str) -> list:
    if value is None:
        return []

    parsed_values = []

    for item in str(value).split(","):
        item = item.strip()

        if not item:
            continue

        try:
            parsed_values.append(cast_type(item))
        except (ValueError, TypeError):
            continue

    return parsed_values


@st.cache_resource(show_spinner=False, max_entries=4)
def create_result_zip_buffer_cached_v(file_signature):
    """
    Create an in-memory ZIP from a hashable file signature.

    file_signature is a tuple of:
        (absolute_path, mtime, size)
    entries.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(
        buffer,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as zipf:
        for path_str, _mtime, _size in file_signature:
            file_path = Path(path_str)

            if file_path.is_file():
                zipf.write(
                    file_path,
                    arcname=file_path.name,
                )

    buffer.seek(0)

    return buffer.getvalue()


def show_result_zip_download_button_v(
    file_paths: list[Path],
    label: str,
    zip_filename: str,
    key: str,
) -> None:
    """Show a cached ZIP download for selected result files."""
    existing_file_paths = [
        Path(p).resolve()
        for p in file_paths
        if Path(p).is_file()
    ]

    if not existing_file_paths:
        st.warning("No files available for download.")
        return

    file_signature = tuple(
        (
            str(p),
            p.stat().st_mtime,
            p.stat().st_size,
        )
        for p in existing_file_paths
    )

    st.download_button(
        label=label,
        data=create_result_zip_buffer_cached_v(file_signature),
        file_name=zip_filename,
        mime="application/zip",
        key=key,
    )


def is_RDDF_csm_level_result_v(
    result_filename: str,
    fdr_value: str | None,
) -> bool:
    """
    Return True for RDDF rescoring outputs at CSM-level FDR thresholds.
    """
    if not str(result_filename).startswith("RDDF_"):
        return False

    try:
        return float(fdr_value) in (0.0100, 0.1000)
    except (TypeError, ValueError):
        return False


# ============================================================
# Main page
# ============================================================

if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get(
        "selected-result-files",
        [],
    )


result_dir: Path = Path(
    st.session_state.workspace,
    "result-files",
)


st.title("📊 Result Viewer")


# IMPORTANT:
# Do not use top-level st.tabs() here.
#
# Streamlit 1.38 computes every tab body on every rerun. That means clicking
# "Upload result files" still executes the expensive result viewer first.
#
# A radio selector gives true conditional execution: only the selected section
# below is run.
main_view = st.radio(
    "Result viewer section",
    options=[
        "View Results",
        "Result files",
        "Upload result files",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="results_main_view_v",
)


# ============================================================
# View Results
# ============================================================

if main_view == "View Results":

    workspace_path = Path(
        st.session_state.workspace
    )

    result_files_path_v = (
        workspace_path
        / "result-files"
    )

    session_files = [
        f.name
        for f in sorted(
            result_files_path_v.iterdir()
        )
        if (
            f.name.endswith(".idXML")
            and "_XLs" in f.name
        )
    ]

    if not session_files:
        st.warning(
            "There is no output file available in workspace."
        )

    else:
        selected_file = st.selectbox(
            "choose a currently protocol file to view",
            session_files,
        )

        is_one_hundred_percent_file = bool(
            selected_file
            and is_one_hundred_percent_xl_file_v(
                selected_file
            )
        )

        # Inner result tabs are kept because they are part of the existing UI.
        if is_one_hundred_percent_file:
            tabs_ = st.tabs(
                [
                    "CSMs Table",
                ]
            )
        else:
            tabs_ = st.tabs(
                [
                    "CSMs Table",
                    "PRTs Table",
                    "PRTs Summary",
                    "Crosslink efficiency",
                    "Precursor adducts summary",
                ]
            )

        if selected_file:

            # ------------------------------------------------
            # CSM Table
            # ------------------------------------------------

            with tabs_[0]:

                csm_path_v = (
                    workspace_path
                    / "result-files"
                    / selected_file
                )

                (
                    CSM_,
                    CSM_grid_v,
                    csm_specid_to_position_v,
                ) = get_csm_view_assets_v(
                    str(csm_path_v.resolve()),
                    csm_path_v.stat().st_mtime,
                )

                file_name_wout_out = (
                    clean_filename_with_regex_v(
                        selected_file
                    )
                )

                if file_name_wout_out == "Example":
                    file_name_wout_out = (
                        "Example_RNA_UV_XL"
                    )

                workspace = Path(
                    str(st.session_state.workspace)
                )

                if (
                    workspace.parts
                    and workspace.parts[0] == ".."
                ):
                    workspace = Path(
                        *workspace.parts[1:]
                    )

                mzml_path = (
                    Path.cwd().parent
                    / workspace
                    / "mzML-files"
                    / f"{file_name_wout_out}.mzML"
                )

                if CSM_ is None:
                    st.warning(
                        "No CSMs found in selected idXML file"
                    )

                else:
                    if (
                        "NuXL:NA" in CSM_.columns
                        and CSM_["NuXL:NA"]
                        .astype(str)
                        .str.contains("none")
                        .any()
                    ):
                        st.warning(
                            "nonXL CSMs found"
                        )

                    else:

                        # ----------------------------------------
                        # AgGrid
                        # ----------------------------------------

                        # CSM_grid_v never includes:
                        #   intensities
                        #   mz_values
                        #   ions
                        #
                        # The full CSM_ still contains them.
                        gb = GridOptionsBuilder.from_dataframe(
                            CSM_grid_v
                        )

                        gb.configure_selection(
                            selection_mode="single",
                            use_checkbox=True,
                        )

                        gb.configure_side_bar()

                        gb.configure_pagination(
                            enabled=True,
                            paginationAutoPageSize=False,
                            paginationPageSize=10,
                        )

                        gridOptions = gb.build()

                        # FIT_CONTENTS is kept for smaller FDR files but disabled
                        # for 1.0000 because scanning/width-measuring a huge grid
                        # is expensive.
                        aggrid_extra_v = {}

                        if not is_one_hundred_percent_file:
                            aggrid_extra_v[
                                "columns_auto_size_mode"
                            ] = (
                                ColumnsAutoSizeMode
                                .FIT_CONTENTS
                            )

                        data = AgGrid(
                            CSM_grid_v,
                            gridOptions=gridOptions,
                            enable_enterprise_modules=True,
                            allow_unsafe_jscode=True,
                            update_mode=(
                                GridUpdateMode
                                .SELECTION_CHANGED
                            ),
                            **aggrid_extra_v,
                        )

                        # Full table download is preserved.
                        show_csm_download_button_v(
                            csm_path_v,
                            os.path.splitext(
                                selected_file
                            )[0],
                        )

                        selected_row = (
                            selected_rows_to_records_v(
                                data.get(
                                    "selected_rows"
                                )
                            )
                        )

                        # ----------------------------------------
                        # Ion filter
                        # ----------------------------------------

                        ion_annotation_filter_options_v = [
                            "all_annotated_peaks",
                            "only_b_ions",
                            "only_y_ions",
                            "only_b_y_ions",
                            "exclude_b_y_ions",
                            "only_MI_ions",
                            "only_precursor_ions",
                        ]

                        ion_annotation_filter_labels_v = {
                            "all_annotated_peaks":
                                "All",

                            "only_b_ions":
                                "b-ions only",

                            "only_y_ions":
                                "y-ions only",

                            "only_b_y_ions":
                                "b/y-ions only",

                            "exclude_b_y_ions":
                                "Exclude b/y-ions",

                            "only_MI_ions":
                                "MI-ions only",

                            "only_precursor_ions":
                                "Precursor-ions only",
                        }

                        ion_annotation_filter = st.radio(
                            "Annotated peaks to display",
                            options=(
                                ion_annotation_filter_options_v
                            ),
                            format_func=lambda option:
                                ion_annotation_filter_labels_v.get(
                                    option,
                                    option,
                                ),
                            index=0,
                            horizontal=True,
                            key=(
                                "ion_annotation_"
                                "filter_radio_v3_"
                                f"{selected_file}"
                            ),
                            help=(
                                "Choose which annotation ions to display. "
                                "If the corresponding mzML MS2 spectrum is "
                                "available, all experimental peaks are still "
                                "shown and only the selected annotations are "
                                "labeled. If mzML is not available, only the "
                                "selected annotated idXML peaks are shown."
                            ),
                        )

                        # ----------------------------------------
                        # Selected spectrum
                        # ----------------------------------------

                        if selected_row:

                            selected_spec_id_v = (
                                selected_row[0]["SpecId"]
                            )

                            selected_position_v = (
                                csm_specid_to_position_v
                                .get(
                                    str(
                                        selected_spec_id_v
                                    )
                                )
                            )

                            if (
                                selected_position_v
                                is not None
                            ):
                                full_selected_row_v = (
                                    CSM_.iloc[
                                        selected_position_v
                                    ]
                                )

                            else:
                                # Defensive fallback that preserves the old
                                # dataframe-search behavior.
                                full_selected_row_v = (
                                    CSM_.loc[
                                        CSM_["SpecId"]
                                        == selected_spec_id_v
                                    ]
                                    .iloc[0]
                                )

                            idxml_mz_values = (
                                split_peak_values_v(
                                    full_selected_row_v.get(
                                        "mz_values",
                                        "",
                                    ),
                                    float,
                                )
                            )

                            idxml_intensity_values = (
                                split_peak_values_v(
                                    full_selected_row_v.get(
                                        "intensities",
                                        "",
                                    ),
                                    float,
                                )
                            )

                            idxml_annotations = (
                                split_peak_values_v(
                                    full_selected_row_v.get(
                                        "ions",
                                        "",
                                    ),
                                    str,
                                )
                            )

                            idxml_peak_rows = []

                            for (
                                mz,
                                intensity,
                                annotation,
                            ) in zip(
                                idxml_mz_values,
                                idxml_intensity_values,
                                idxml_annotations,
                            ):

                                if (
                                    annotation_matches_filter_v(
                                        annotation,
                                        ion_annotation_filter,
                                    )
                                ):
                                    idxml_peak_rows.append(
                                        {
                                            "mzarray": mz,
                                            "intarray": intensity,
                                            "anotarray": annotation,
                                        }
                                    )

                            annotation_data = []
                            ms2_peak_data = None

                            # mzML is loaded only after row selection.
                            ms2_peak_map_v = (
                                get_cached_ms2_peak_map_v(
                                    mzml_path
                                )
                            )

                            if ms2_peak_map_v is None:
                                st.warning(
                                    "The corresponding "
                                    f"{file_name_wout_out}.mzML "
                                    "file could not be found. "
                                    "Please re-upload the mzML file "
                                    "to visualize all experimental peaks."
                                )

                            else:
                                ms2_peak_data = (
                                    ms2_peak_map_v.get(
                                        selected_spec_id_v
                                    )
                                )

                            if ms2_peak_data is not None:

                                (
                                    mz_full,
                                    inten_full,
                                ) = ms2_peak_data

                                annotation_dict = {
                                    round(mz, 6):
                                    filtered_annotation_v(
                                        annotation,
                                        ion_annotation_filter,
                                    )
                                    for (
                                        mz,
                                        annotation,
                                    ) in zip(
                                        idxml_mz_values,
                                        idxml_annotations,
                                    )
                                }

                                for (
                                    intensity,
                                    mz,
                                ) in zip(
                                    inten_full,
                                    mz_full,
                                ):

                                    mz_r = round(
                                        float(mz),
                                        6,
                                    )

                                    annotation_data.append(
                                        {
                                            "mzarray": mz,
                                            "intarray": intensity,
                                            "anotarray":
                                                annotation_dict.get(
                                                    mz_r,
                                                    " ",
                                                ),
                                        }
                                    )

                            else:
                                # mzML/MS2 spectrum unavailable:
                                # use selected annotated idXML peaks.
                                annotation_data = (
                                    idxml_peak_rows
                                )

                            if annotation_data:

                                annotation_df = (
                                    pd.DataFrame(
                                        annotation_data
                                    )
                                )

                                spectra_name = (
                                    os.path.splitext(
                                        selected_file
                                    )[0]
                                    + " Scan# "
                                    + str(
                                        {
                                            full_selected_row_v[
                                                "ScanNr"
                                            ]
                                        }
                                    ).strip("{}")
                                    + " Pep: "
                                    + str(
                                        {
                                            full_selected_row_v[
                                                "Peptide"
                                            ]
                                        }
                                    ).strip("{}'")
                                    + " + "
                                    + str(
                                        {
                                            full_selected_row_v[
                                                "NuXL:NA"
                                            ]
                                        }
                                    ).strip("{}'")
                                )

                                fig = (
                                    plot_ms2_spectrum_full(
                                        annotation_df,
                                        spectra_name,
                                        "black",
                                    )
                                )

                                show_fig(
                                    fig,
                                    (
                                        f"{os.path.splitext(selected_file)[0]}"
                                        "_scan_"
                                        + str(
                                            {
                                                full_selected_row_v[
                                                    "ScanNr"
                                                ]
                                            }
                                        ).strip("{}")
                                    ),
                                )

                            else:
                                st.warning(
                                    "Annotation not available for this peptide"
                                )

            # ------------------------------------------------
            # Protein result tabs
            # ------------------------------------------------

            if not is_one_hundred_percent_file:

                with tabs_[1]:

                    parts = selected_file.split("_")

                    prefix = "_".join(
                        parts[:-2]
                    )

                    perc_value = parts[-2]

                    new_filename = (
                        f"{prefix}_proteins"
                        f"{perc_value}_XLs.tsv"
                    )

                    protein_path = (
                        workspace_path
                        / "result-files"
                        / new_filename
                    )

                    if protein_path.exists():

                        PRTs_section = (
                            read_protein_table_v(
                                protein_path
                            )
                        )

                        show_table(
                            PRTs_section[0],
                            (
                                f"{os.path.splitext(new_filename)[0]}"
                                "_PRTS_list"
                            ),
                        )

                        with tabs_[2]:

                            show_table(
                                PRTs_section[2],
                                (
                                    f"{os.path.splitext(new_filename)[0]}"
                                    "_PRTS_summary"
                                ),
                            )

                        with tabs_[3]:

                            prts_efficiency = (
                                PRTs_section[3]
                            )

                            efficiency_fig = (
                                go.Figure(
                                    data=[
                                        go.Bar(
                                            x=(
                                                prts_efficiency[
                                                    "AA"
                                                ]
                                            ),
                                            y=(
                                                prts_efficiency[
                                                    "Crosslink efficiency"
                                                ]
                                            ),
                                            marker_color=(
                                                "rgb(55, 83, 109)"
                                            ),
                                        )
                                    ]
                                )
                            )

                            efficiency_fig.update_layout(
                                xaxis_title=(
                                    "Amino acids"
                                ),
                                yaxis_title=(
                                    "Crosslink efficiency "
                                    "(AA freq. / AA freq. in all CSMs)"
                                ),
                                font=dict(
                                    family="Arial",
                                    size=12,
                                    color="rgb(0,0,0)",
                                ),
                                paper_bgcolor=(
                                    "rgb(255, 255, 255)"
                                ),
                                plot_bgcolor=(
                                    "rgb(255, 255, 255)"
                                ),
                            )

                            show_fig(
                                efficiency_fig,
                                (
                                    f"{os.path.splitext(new_filename)[0]}"
                                    "_efficiency"
                                ),
                            )

                            download_table(
                                prts_efficiency,
                                (
                                    f"{os.path.splitext(new_filename)[0]}"
                                    "_efficiency"
                                ),
                            )

                        with tabs_[4]:

                            precursor_summary = (
                                PRTs_section[4]
                            )

                            adducts_fig = (
                                go.Figure(
                                    data=[
                                        go.Pie(
                                            labels=(
                                                precursor_summary[
                                                    "Precursor adduct:"
                                                ]
                                            ),
                                            values=(
                                                precursor_summary[
                                                    "PSMs(%)"
                                                ]
                                            ),
                                            hoverinfo="label+percent",
                                            textinfo="label+percent",
                                        )
                                    ]
                                )
                            )

                            n_items = len(
                                precursor_summary
                            )

                            base_height = 350
                            per_item_height = 22

                            dynamic_height = max(
                                base_height,
                                (
                                    base_height
                                    + n_items
                                    * per_item_height
                                ),
                            )

                            adducts_fig.update_layout(
                                height=dynamic_height,
                                margin=dict(
                                    l=15,
                                    r=15,
                                    t=15,
                                    b=15,
                                ),
                            )

                            show_fig(
                                adducts_fig,
                                (
                                    f"{os.path.splitext(new_filename)[0]}"
                                    "_adduct_summary"
                                ),
                            )

                            v_space(1)

                            download_table(
                                precursor_summary,
                                (
                                    f"{os.path.splitext(new_filename)[0]}"
                                    "_adduct_summary"
                                ),
                            )

                    else:

                        match = re.search(
                            r"proteins([\d.]+)_XLs",
                            protein_path.name,
                        )

                        value = (
                            match.group(1)
                            if match
                            else None
                        )

                        if is_RDDF_csm_level_result_v(
                            selected_file,
                            value,
                        ):

                            warning_message = (
                                "Rescoring workflow "
                                "(output start with **RDDF_**) "
                                "gives output CSMs only."
                            )

                        elif (
                            value is not None
                            and float(value) > 0.1000
                        ):

                            warning_message = (
                                f"Proteins are not reported at {value}. "
                                "Protein reports are only generated at "
                                "1% and 10% FDR, and only if XL FDR "
                                "thresholds (0.01 and 0.10) or higher "
                                "are specified."
                            )

                        else:

                            warning_message = (
                                f"{protein_path.name} file not exist "
                                "in current workspace, please rerun "
                                "analysis or upload."
                            )

                        for i, tab in enumerate(
                            tabs_,
                            start=1,
                        ):
                            with tab:
                                if i != 1:
                                    st.warning(
                                        warning_message
                                    )


# ============================================================
# Result files
# ============================================================

elif main_view == "Result files":

    result_file_paths_v = [
        f
        for f in sorted(
            Path(result_dir).iterdir()
        )
        if f.is_file()
    ]

    if not result_file_paths_v:

        st.warning(
            "There is no output file available in workspace."
        )

    else:

        v_space(2)

        df = pd.DataFrame(
            {
                "file name": [
                    f.name
                    for f in result_file_paths_v
                ]
            }
        )

        st.markdown(
            "##### All result files available in workspace:"
        )

        show_table(df)

        v_space(1)

        copy_local_result_files_from_directory(
            result_dir
        )

        with st.expander(
            "🗑️ Remove result files"
        ):

            list_result_examples = (
                list_result_example_files()
            )

            session_files = [
                f.name
                for f in sorted(
                    result_dir.iterdir()
                )
                if f.is_file()
            ]

            Final_list = [
                item
                for item in session_files
                if item not in list_result_examples
            ]

            to_remove = st.multiselect(
                "select result files",
                options=Final_list,
            )

            c1, c2 = st.columns(2)

            if c2.button(
                "Remove **selected**",
                type="primary",
                disabled=not any(to_remove),
            ):

                remove_selected_result_files(
                    to_remove
                )

                st.rerun()

            if c1.button(
                "⚠️ Remove **all**",
                disabled=not any(
                    result_dir.iterdir()
                ),
            ):

                remove_all_result_files()

                st.rerun()

        with st.expander(
            "⬇️ Download result files"
        ):

            to_download = st.multiselect(
                "select result files for download",
                options=[
                    f.name
                    for f in result_file_paths_v
                ],
            )

            c1, c2 = st.columns(2)

            selected_download_paths_v = [
                Path(result_dir)
                / file_name
                for file_name in to_download
            ]

            with c2:

                if to_download:

                    show_result_zip_download_button_v(
                        selected_download_paths_v,
                        "Download selected",
                        "selected_result_files.zip",
                        key=(
                            "download_selected_"
                            "result_files_v"
                        ),
                    )

                else:

                    st.button(
                        "Download selected",
                        type="primary",
                        disabled=True,
                        key=(
                            "download_selected_"
                            "result_files_disabled_v"
                        ),
                    )

            with c1:

                show_result_zip_download_button_v(
                    result_file_paths_v,
                    "⚠️ Download all",
                    "all_result_files.zip",
                    key=(
                        "download_all_"
                        "result_files_v"
                    ),
                )


# ============================================================
# Upload result files
# ============================================================

elif main_view == "Upload result files":

    # This section now executes by itself. The expensive CSM viewer above
    # is not run when this view is selected.
    with st.form(
        "Upload .idXML and .tsv",
        clear_on_submit=True,
    ):

        files = st.file_uploader(
            "NuXL result files",
            accept_multiple_files=(
                st.session_state.location
                == "local"
            ),
            type=[
                ".idXML",
                ".tsv",
            ],
            help=(
                "Input file (Valid formats: 'idXML', 'tsv') "
                "should be _XLs output file"
            ),
        )

        cols = st.columns(3)

        if cols[1].form_submit_button(
            "Add files to workspace",
            type="primary",
        ):

            if not files:

                st.warning(
                    "Upload some files first."
                )

            else:

                save_uploaded_result(
                    files
                )

            st.rerun()


# ============================================================
# Save parameters
# ============================================================

save_params(params)
