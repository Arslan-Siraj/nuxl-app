import streamlit as st
#from src.common import *
from src.nuxl_result_files import *
from src.nuxl_result_files_v import readAndProcessIdXML_v, read_protein_table_v
import plotly.graph_objects as go
from src.nuxl_view import plot_ms2_spectrum, plot_ms2_spectrum_full, download_table, show_fig
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, ColumnsAutoSizeMode
from pyopenms import *
import re
import io
import zipfile

from src.common.common import (
    page_setup,
    save_params,
    v_space,
    show_table,
    TK_AVAILABLE,
    tk_directory_dialog,
)

params = page_setup()

##################################

# Optimized helper functions for this versioned page.
# These names end with _v so the existing page and helpers remain untouched.
@st.cache_resource(show_spinner="Loading mzML MS2 spectra...")
def load_ms2_peak_map_v(mzml_path_str: str, file_mtime: float):
    """
    Load an mzML file once, keep only MS2 spectra, normalize intensities,
    and index spectra by native ID for fast row-selection lookup.
    """
    mzml_path = Path(mzml_path_str).resolve()

    if not mzml_path.is_file():
        return None

    try:
        exp = MSExperiment()
        MzMLFile().load(str(mzml_path), exp)

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

    return load_ms2_peak_map_v(str(mzml_path), mzml_path.stat().st_mtime)


def selected_rows_to_records_v(selected_rows):
    """Normalize AgGrid selected_rows output across st-aggrid versions."""
    if selected_rows is None:
        return []

    if isinstance(selected_rows, pd.DataFrame):
        return selected_rows.to_dict("records")

    if isinstance(selected_rows, list):
        return selected_rows

    return []

#def clean_filename_with_regex_v(filename):
    # Pattern to match "_perc_X.XXXX_XLs.idXML" or "_X.XXXX_XLs.idXML"
#    pattern = r"(_perc_\d\.\d{4}_XLs\.idXML|_\d\.\d{4}_XLs\.idXML)"
#    return re.sub(pattern, "", filename)

def clean_filename_with_regex_v(filename):
    # Remove feature prefixes at the beginning of the filename
    prefix_pattern = r"^(RDDF_|RT_feat_|RT_Int_feat_|Int_feat_|updated_feat_)"

    # Remove score/XL suffix patterns
    suffix_pattern = r"(_perc_\d\.\d{4}_XLs\.idXML|_\d\.\d{4}_XLs\.idXML)"

    filename = re.sub(prefix_pattern, "", filename)
    filename = re.sub(suffix_pattern, "", filename)

    return filename


def is_one_hundred_percent_xl_file_v(filename: str) -> bool:
    """Hide protein/report tabs for 1.0000 XL idXML files."""
    return filename.endswith("_1.0000_XLs.idXML") or filename.endswith("_perc_1.0000_XLs.idXML")


def annotation_matches_filter_v(annotation: str, ion_filter: str) -> bool:
    annotation = str(annotation).strip()
    if not annotation:
        return False
    if ion_filter == "all_annotated_peaks":
        return True
    if ion_filter == "exclude_b_y_ions":
        return not (annotation.startswith("b") or annotation.startswith("y"))
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
        except ValueError:
            continue
    return parsed_values


def create_result_zip_buffer_v(file_paths: list[Path]) -> io.BytesIO:
    """Create an in-memory ZIP buffer for existing result files."""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            file_path = Path(file_path)
            if file_path.is_file():
                zipf.write(file_path, arcname=file_path.name)

    buffer.seek(0)
    return buffer


def show_result_zip_download_button_v(
    file_paths: list[Path],
    label: str,
    zip_filename: str,
    key: str,
) -> None:
    """Show a Streamlit download button for selected result files.

    This avoids embedding a large base64 ZIP string into the Streamlit page,
    which is slow for large result sets.
    """
    existing_file_paths = [Path(p) for p in file_paths if Path(p).is_file()]

    if not existing_file_paths:
        st.warning("No files available for download.")
        return

    st.download_button(
        label=label,
        data=create_result_zip_buffer_v(existing_file_paths),
        file_name=zip_filename,
        mime="application/zip",
        key=key,
    )


########################

### main content of page

# Make sure "selected-result-files" is in session state
if "selected-result-files" not in st.session_state:
    st.session_state["selected-result-files"] = params.get("selected-result-files", [])

# result directory path in current session state
result_dir: Path = Path(st.session_state.workspace, "result-files")

#title of page
st.title("📊 Result Viewer")

#tabs on page
tabs = ["View Results", "Result files", "Upload result files"]
tabs = st.tabs(tabs)

#with View Results tab
with tabs[0]:

    #make sure load all example result files
    #load_example_result_files()
    # take all .idXML files in current session files; .idXML is CSMs
    workspace_path = Path(st.session_state.workspace)
    result_files_path_v = workspace_path / "result-files"
    session_files = [
        f.name
        for f in sorted(result_files_path_v.iterdir())
        if f.name.endswith(".idXML") and "_XLs" in f.name
    ]

    if not session_files:
        st.warning("There is no output file available in workspace.")
    else:
        # select box to select .idXML file to see the results
        selected_file = st.selectbox(
            "choose a currently protocol file to view",
            session_files,
        )

        #print("selected_file: ", selected_file)

        #current workspace session path
        is_one_hundred_percent_file = bool(
            selected_file and is_one_hundred_percent_xl_file_v(selected_file)
        )

        #tabs on page to show different results
        if is_one_hundred_percent_file:
            tabs_ = st.tabs(["CSMs Table"])
        else:
            tabs_ = st.tabs(["CSMs Table", "PRTs Table", "PRTs Summary", "Crosslink efficiency", "Precursor adducts summary"])

        ## selected .idXML file
        if selected_file:
            #with CSMs Table
            with tabs_[0]:
                #st.write("CSMs Table")
                #take all CSMs as dataframe
                CSM_= readAndProcessIdXML_v(workspace_path / "result-files" /f"{selected_file}")

                ##TODO setup more better/effiecient
                # Remove the out pattern of idxml
                #file_name_wout_out = remove_substrings(selected_file, nuxl_out_pattern)
                file_name_wout_out = clean_filename_with_regex_v(selected_file)
                #print("file_name_wout_out: ", file_name_wout_out)
            
                if file_name_wout_out == "Example": 
                    file_name_wout_out = "Example_RNA_UV_XL"

                mzml_path = (
                    Path.cwd().parent
                    / str(st.session_state.workspace)
                    / "mzML-files"
                    / f"{file_name_wout_out}.mzML"
                )

                st.info(f"Path: {mzml_path}")

                if CSM_ is None: 
                    st.warning("No CSMs found in selected idXML file")
                else:
                
                    if CSM_['NuXL:NA'].str.contains('none').any():
                        st.warning("nonXL CSMs found")  
                    else:
                    
                        # Use the complete dataframe in AgGrid to preserve the original
                        # table appearance, column content, side bar behavior, and autosizing.
                        # The speed improvement is kept by caching idXML/protein parsing and
                        # loading mzML only after a row is selected.
                        gb = GridOptionsBuilder.from_dataframe(CSM_[list(CSM_.columns.values)])

                        # configure selection
                        gb.configure_selection(selection_mode="single", use_checkbox=True)
                        gb.configure_side_bar()
                        gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10)
                        gridOptions = gb.build()

                        data = AgGrid(
                            CSM_,
                            gridOptions=gridOptions,
                            enable_enterprise_modules=True,
                            allow_unsafe_jscode=True,
                            update_mode=GridUpdateMode.SELECTION_CHANGED,
                            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                        )

                        #download table
                        download_table(CSM_, f"{os.path.splitext(selected_file)[0]}")
                        #select row by user
                        selected_row = selected_rows_to_records_v(data.get("selected_rows"))

                        ion_annotation_filter_options_v = [
                            "all_annotated_peaks",
                            "exclude_b_y_ions",
                            "only_b_ions",
                            "only_y_ions",
                            "only_MI_ions",
                            "only_precursor_ions",
                        ]

                        ion_annotation_filter_labels_v = {
                            "all_annotated_peaks": "All",
                            "exclude_b_y_ions": "Exclude b/y-ions",
                            "only_b_ions": "b-ions only",
                            "only_y_ions": "y-ions only",
                            "only_MI_ions": "MI-ions only",
                            "only_precursor_ions": "Precursor-ions only",
                        }

                        ion_annotation_filter = st.radio(
                            "Annotated peaks to display",
                            options=ion_annotation_filter_options_v,
                            format_func=lambda option: ion_annotation_filter_labels_v.get(option, option),
                            index=0,
                            horizontal=True,
                            key=f"ion_annotation_filter_radio_v3_{selected_file}",
                            help=(
                                "Choose which annotations ions to display from the radio button. If the "
                                "corresponding mzML MS2 spectrum is available, all experimental peaks "
                                "are still shown and only the selected annotations are labeled. If "
                                "mzML is not available, only the selected annotated idXML peaks are shown."
                            ),
                        )

                        if selected_row:
                            selected_spec_id_v = selected_row[0]["SpecId"]
                            full_selected_row_v = CSM_.loc[
                                CSM_["SpecId"] == selected_spec_id_v
                            ].iloc[0]

                            # Create annotation features from idXML.
                            idxml_mz_values = split_peak_values_v(
                                full_selected_row_v.get("mz_values", ""),
                                float,
                            )
                            idxml_intensity_values = split_peak_values_v(
                                full_selected_row_v.get("intensities", ""),
                                float,
                            )
                            idxml_annotations = split_peak_values_v(
                                full_selected_row_v.get("ions", ""),
                                str,
                            )

                            idxml_peak_rows = []
                            for mz, intensity, annotation in zip(
                                idxml_mz_values,
                                idxml_intensity_values,
                                idxml_annotations,
                            ):
                                if annotation_matches_filter_v(annotation, ion_annotation_filter):
                                    idxml_peak_rows.append(
                                        {
                                            "mzarray": mz,
                                            "intarray": intensity,
                                            "anotarray": annotation,
                                        }
                                    )

                            annotation_data = []
                            ms2_peak_data = None

                            ms2_peak_map_v = get_cached_ms2_peak_map_v(mzml_path)

                            if ms2_peak_map_v is None:
                                st.warning(
                                    f"The corresponding {file_name_wout_out}.mzML file could not be found. "
                                    "Please re-upload the mzML file to visualize all experimental peaks."
                                )
                            else:
                                ms2_peak_data = ms2_peak_map_v.get(selected_spec_id_v)

                            if ms2_peak_data is not None:
                                # Use all experimental MS2 peaks from mzML, but only show
                                # labels for the selected annotation type.
                                mz_full, inten_full = ms2_peak_data

                                annotation_dict = {
                                    round(mz, 6): filtered_annotation_v(annotation, ion_annotation_filter)
                                    for mz, annotation in zip(idxml_mz_values, idxml_annotations)
                                }

                                for intensity, mz in zip(inten_full, mz_full):
                                    mz_r = round(float(mz), 6)
                                    annotation_data.append(
                                        {
                                            "mzarray": mz,
                                            "intarray": intensity,
                                            "anotarray": annotation_dict.get(mz_r, " "),
                                        }
                                    )

                            else:
                                # mzML/MS2 spectrum is not available. Show only the selected
                                # annotated peaks that are stored in the idXML.
                                annotation_data = idxml_peak_rows
                        
                            # Check if the lists are not empty
                            if annotation_data:
                                # Create the DataFrame
                                annotation_df = pd.DataFrame(annotation_data)
                                #annotation_df.to_csv(str(full_selected_row_v['ScanNr']) + "_idxml_annot_full.csv")
                                # title of spectra
                                spectra_name = os.path.splitext(selected_file)[0] +" Scan# " + str({full_selected_row_v['ScanNr']}).strip('{}') + " Pep: " + str({full_selected_row_v['Peptide']}).strip('{}\'') +  " + " +str ({full_selected_row_v['NuXL:NA']}).strip('{}\'')
                                # generate ms2 spectra
                                fig = plot_ms2_spectrum_full(annotation_df, spectra_name, "black")
                                #show figure
                                show_fig(fig,  f"{os.path.splitext(selected_file)[0]}_scan_{str({full_selected_row_v['ScanNr']}).strip('{}')}")

                            else:
                                # if any list empty
                                st.warning("Annotation not available for this peptide")
                                
            if not is_one_hundred_percent_file:
                #with PRTs Table
                with tabs_[1]:
                    # Extracting components from the input filename to show the result of corresponding proteins file
                    parts = selected_file.split('_')
                    prefix = '_'.join(parts[:-2])  # Joining all parts except the last two
                    perc_value = parts[-2]  # Extracting the same FDR file

                    # Creating the new filename as same as selected idXML file
                    new_filename = f"{prefix}_proteins{perc_value}_XLs.tsv"

                    #path of corresponding protein file
                    protein_path = workspace_path / "result-files" /f"{new_filename}"

                    #if file exist
                    if protein_path.exists():
                        #st.write("PRTs Table")
                        #take list of dataframs different results 
                        PRTs_section= read_protein_table_v(protein_path)
                        #from 1st dataframe PRTs_List; shown on page with download button
                        show_table(PRTs_section[0], f"{os.path.splitext(new_filename)[0]}_PRTS_list")
            
                        #with PRTs Summary
                        with tabs_[2]:       
                                #st.write("Protein summary")
                                #from wnd dataframe PRTs_summary; shown on page with download button
                                show_table(PRTs_section[2], f"{os.path.splitext(new_filename)[0]}_PRTS_summary")
                
                        #with Crosslink efficiency
                        with tabs_[3]:
                                #st.write("Crosslink efficiency (AA freq. / AA freq. in all CSMs)")
                                #from 3rd dataframe PRTs_efficiency
                                prts_efficiency = PRTs_section[3]

                                #create crosslink efficiency plot
                                efficiency_fig = go.Figure(data=[go.Bar(x=prts_efficiency["AA"], y=prts_efficiency["Crosslink efficiency"], marker_color='rgb(55, 83, 109)')])
                                #update the layout of plot
                                efficiency_fig.update_layout(
                                    #title='Crosslink efficiency',
                                    xaxis_title='Amino acids',
                                    yaxis_title='Crosslink efficiency (AA freq. / AA freq. in all CSMs)',
                                    font=dict(family='Arial', size=12, color='rgb(0,0,0)'),
                                    paper_bgcolor='rgb(255, 255, 255)',
                                    plot_bgcolor='rgb(255, 255, 255)'
                                )
                                #show figure, with download
                                show_fig(efficiency_fig, f"{os.path.splitext(new_filename)[0]}_efficiency")
                                #show button of download table from where above plot came
                                download_table(prts_efficiency, f"{os.path.splitext(new_filename)[0]}_efficiency")

                        #with Precursor adducts summary
                        with tabs_[4]:
                                    #st.write("Precursor adduct summary")
                                    #show_table(PRTs_section[4])
                                    #from 4th dataframe mass_adducts efficiency
                                    precursor_summary = PRTs_section[4]

                                    #create mass adducts efficiency plot
                                    adducts_fig = go.Figure(data=[go.Pie(
                                        labels=precursor_summary["Precursor adduct:"],
                                        values=precursor_summary["PSMs(%)"],
                                        hoverinfo='label+percent',
                                        textinfo='label+percent',
                                        #title='Percentage of PSMs for Each Index Precursor'
                                    )])

                                    n_items = len(precursor_summary)

                                    base_height = 350          # minimum readable height
                                    per_item_height = 22       # legend-driven scaling

                                    dynamic_height = max(
                                        base_height,
                                        base_height + n_items * per_item_height
                                    )

                                    adducts_fig.update_layout(
                                        height=dynamic_height,
                                        margin=dict(l=15, r=15, t=15, b=15),
                                    )

                                    #show figure, with download
                                    show_fig(adducts_fig , f"{os.path.splitext(new_filename)[0]}_adduct_summary")
                                    v_space(1)
                                    #show button of download table from where above plot came
                                    download_table(precursor_summary, f"{os.path.splitext(new_filename)[0]}_adduct_summary")

                    #if the same protein file not available
                    else:
                        match = re.search(r"proteins([\d.]+)_XLs", protein_path.name)
                        value = match.group(1) if match else None
                        if float(value)>0.1000:
                            warning_message = f"Proteins are not reported at {value}. Protein reports are only generated at 1% and 10% FDR, and only if XL FDR thresholds (0.01 and 0.10) or higher are specified."
                        else:
                            warning_message = f"{protein_path.name} file not exist in current workspace, please rerun analysis or upload."

                        # Display the warning message across all tabs
                        for i, tab in enumerate(tabs_, start=1):
                            with tab:
                                if i != 1:  # Skip CSM 
                                     st.warning(warning_message)

        _ ="""
        tabs_ = st.tabs(["CSMs", "Proteins"])
        if selected_file:
            with tabs_[0]:
                st.write("CSMs Table")
                #st.write("Path of selected file: ", workspace_path / "result-files" /f"{selected_file}_0.0100_XLs.idXML")
                CSM_= readAndProcessIdXML_v(workspace_path / "result-files" /f"{selected_file}")
                show_table(CSM_, os.path.splitext(selected_file)[0])

            with tabs_[1]:
                # Extracting components from the input filename
                parts = selected_file.split('_')
                prefix = '_'.join(parts[:-2])  # Joining all parts except the last two
                perc_value = parts[-2]  # Extracting the percentage value

                # Creating the new filename
                new_filename = f"{prefix}_proteins{perc_value}_XLs.tsv"

                #st.write("Path of selected file: ", workspace_path / "result-files" /f"{selected_file}_proteins0.0100_XLs.tsv")
                protein_path = workspace_path / "result-files" /f"{new_filename}"

                if protein_path.exists():
                    st.write("PRTs Table")
                    PRTs_section= read_protein_table_v(protein_path)
                    show_table(PRTs_section[0], f"{os.path.splitext(new_filename)[0]}_PRTS_list")

                    st.write("Protein summary")
                    show_table(PRTs_section[2], f"{os.path.splitext(new_filename)[0]}_PRTS_summary")

                    col1, col2 = st.columns(2)

                    # Display the plots in the columns
                    with col1:
                        st.write("Crosslink efficiency (AA freq. / AA freq. in all CSMs)")
                        #show_table(PRTs_section[3])

                        prts_efficiency = PRTs_section[3]
        
                        efficiency_fig = go.Figure(data=[go.Bar(x=prts_efficiency["AA"], y=prts_efficiency["Crosslink efficiency"], marker_color='rgb(55, 83, 109)')])

                        efficiency_fig.update_layout(
                            #title='Crosslink efficiency',
                            xaxis_title='Amino acids',
                            yaxis_title='Crosslink efficiency',
                            font=dict(family='Arial', size=12, color='rgb(0,0,0)'),
                            paper_bgcolor='rgb(255, 255, 255)',
                            plot_bgcolor='rgb(255, 255, 255)'
                        )

                        show_fig(efficiency_fig, f"{os.path.splitext(new_filename)[0]}_efficiency")
                        download_table(prts_efficiency, f"{os.path.splitext(new_filename)[0]}_efficiency")

                    with col2:
                        st.write("Precursor adduct summary")
                        #show_table(PRTs_section[4])

                        #print(PRTs_section[4])
                        precursor_summary = PRTs_section[4]

                        adducts_fig = go.Figure(data=[go.Pie(
                            labels=precursor_summary["Precursor adduct:"],
                            values=precursor_summary["PSMs(%)"],
                            hoverinfo='label+percent',
                            textinfo='label+percent',
                            #title='Percentage of PSMs for Each Index Precursor'
                        )])

                        show_fig(adducts_fig , f"{os.path.splitext(new_filename)[0]}_adduct_summary")
                        download_table(precursor_summary, f"{os.path.splitext(new_filename)[0]}_adduct_summary")

                else:
                    st.warning(f"{protein_path.name} file not exist in current workspace")
                """
#with "Result files" 
with tabs[1]:
    #make sure to load all results example files
    #load_example_result_files()

    result_file_paths_v = [
        f
        for f in sorted(Path(result_dir).iterdir())
        if f.is_file()
    ]

    if not result_file_paths_v:
        st.warning("There is no output file available in workspace.")
    else:
        v_space(2)
        #  all result files currently in workspace
        df = pd.DataFrame(
            {"file name": [f.name for f in result_file_paths_v]})
        st.markdown("##### All result files available in workspace:")

        show_table(df)
        v_space(1)
        # Remove files
        copy_local_result_files_from_directory(result_dir)
        with st.expander("🗑️ Remove result files"):
            #take all example result files name
            list_result_examples = list_result_example_files()
            #take all session result files
            session_files = [
                        f.name
                        for f in sorted(result_dir.iterdir())
                        if f.is_file() # dont show directories, because we only want files
                    ]
            #filter out the example result files
            Final_list = [item for item in session_files if item not in list_result_examples]

            #multiselect for result files selection
            to_remove = st.multiselect("select result files", options=Final_list)

            c1, c2 = st.columns(2)
            ### remove selected files from workspace
            if c2.button("Remove **selected**", type="primary", disabled=not any(to_remove)):
                remove_selected_result_files(to_remove)
                st.rerun() 

            ### remove all files from workspace
            if c1.button("⚠️ Remove **all**", disabled=not any(result_dir.iterdir())):
                remove_all_result_files() 
                st.rerun() 


        with st.expander("⬇️ Download result files"):
            #multiselect for result files selection
            to_download = st.multiselect(
                "select result files for download",
                options=[f.name for f in result_file_paths_v],
            )

            c1, c2 = st.columns(2)

            selected_download_paths_v = [
                Path(result_dir) / file_name
                for file_name in to_download
            ]

            with c2:
                if to_download:
                    show_result_zip_download_button_v(
                        selected_download_paths_v,
                        "Download selected",
                        "selected_result_files.zip",
                        key="download_selected_result_files_v",
                    )
                else:
                    st.button(
                        "Download selected",
                        type="primary",
                        disabled=True,
                        key="download_selected_result_files_disabled_v",
                    )

            with c1:
                show_result_zip_download_button_v(
                    result_file_paths_v,
                    "⚠️ Download all",
                    "all_result_files.zip",
                    key="download_all_result_files_v",
                )

#with "Upload result files"
with tabs[2]:
    #form to upload file
    with st.form("Upload .idXML and .tsv", clear_on_submit=True):
        files = st.file_uploader(
            "NuXL result files", accept_multiple_files=(st.session_state.location == "local"), type=['.idXML', '.tsv'], help="Input file (Valid formats: 'idXML', 'tsv') should be _XLs output file")
        cols = st.columns(3)
        if cols[1].form_submit_button("Add files to workspace", type="primary"):
            if not files:
                st.warning("Upload some files first.")
            else:
                save_uploaded_result(files)
            st.rerun()

# At the end of each page, always save parameters (including any changes via widgets with key)
save_params(params)

