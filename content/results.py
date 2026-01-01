import streamlit as st
from src.common import *
from src.result_files import *
import plotly.graph_objects as go
from src.view import plot_ms2_spectrum, plot_ms2_spectrum_full
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, ColumnsAutoSizeMode
from src.captcha_ import *
from pyopenms import *
import re

params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()


##################################

#TODO move to src folder
def process_mzML_file(filepath):
    """
    Loads an mzML file, extracts MS2 spectra, and normalizes the peak intensities.

    Parameters:
    filepath (str): The file path to the mzML file.

    Returns:
    MSExperiment: An MSExperiment object containing the normalized MS2 spectra.
    """
    print("process mzML file: ", filepath)

    try:
        # Initialize an MSExperiment object
        exp = MSExperiment()
        
        # Load the mzML file into the MSExperiment object
        MzMLFile().load(filepath, exp)

        # Create a new MSExperiment object to store MS2 spectra
        MS2 = MSExperiment()
        
        # Iterate over all spectra in the experiment
        for spec in exp:
            # Check if the spectrum is an MS2 spectrum
            if spec.getMSLevel() == 2:
                # Add the MS2 spectrum to the MS2 experiment object
                MS2.addSpectrum(spec)

        # Normalize peak intensities in the MS2 spectra
        normalizer = Normalizer()  # Create a Normalizer object
        param = normalizer.getParameters()  # Get the default parameters
        param.setValue("method", "to_one")  # Set normalization method to "to_one"
        normalizer.setParameters(param)  # Apply the parameters to the normalizer
        normalizer.filterPeakMap(MS2)  # Normalize the peaks in the MS2 spectra

        return MS2  # Return the MSExperiment object containing normalized MS2 spectra

    except Exception as e:
        return None  # Return None if any exception occurs

def get_mz_intensities_from_ms2(MS2_spectras, native_id):
    """
    Extracts m/z values and corresponding intensities from an MS2 spectrum with a specified native ID.

    Parameters:
    MS2_spectras (MSExperiment): An MSExperiment object containing MS2 spectra.
    native_id (str): The native ID of the desired MS2 spectrum.

    Returns:
    tuple: A tuple containing two arrays:
        - mz (list): List of m/z values.
        - intensities (list): List of corresponding intensity values.

    If the specified native ID is not found, the function returns None.
    """
    # Iterate through all spectra in the provided MS2_spectras object
    for spectrum in MS2_spectras.getSpectra():
        # Check if the current spectrum's native ID matches the specified native ID
        if spectrum.getNativeID() == native_id:
            # Extract m/z values and corresponding intensities from the spectrum
            mz, intensities = spectrum.get_peaks()
            # Return the m/z values and intensities as a tuple
            return mz, intensities
    
    # If the native ID is not found, return None
    return None

#def clean_filename_with_regex(filename):
    # Pattern to match "_perc_X.XXXX_XLs.idXML" or "_X.XXXX_XLs.idXML"
#    pattern = r"(_perc_\d\.\d{4}_XLs\.idXML|_\d\.\d{4}_XLs\.idXML)"
#    return re.sub(pattern, "", filename)

def clean_filename_with_regex(filename):
    # Remove feature prefixes at the beginning of the filename
    prefix_pattern = r"^(RT_feat_|RT_Int_feat_|Int_feat_|updated_feat_)"

    # Remove score/XL suffix patterns
    suffix_pattern = r"(_perc_\d\.\d{4}_XLs\.idXML|_\d\.\d{4}_XLs\.idXML)"

    filename = re.sub(prefix_pattern, "", filename)
    filename = re.sub(suffix_pattern, "", filename)

    return filename


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
    session_files = [f.name for f in Path(st.session_state.workspace,"result-files").iterdir() if (f.name.endswith(".idXML") and "_XLs" in f.name)]
    # select box to select .idXML file to see the results
    selected_file = st.selectbox("choose a currently protocol file to view",session_files)

    #print("selected_file: ", selected_file)

    #current workspace session path
    workspace_path = Path(st.session_state.workspace)
    #tabs on page to show different results
    tabs_ = st.tabs(["CSMs Table", "PRTs Table", "PRTs Summary", "Crosslink efficiency", "Precursor adducts summary"])

    ## selected .idXML file
    if selected_file:
        #with CSMs Table
        with tabs_[0]:
            #st.write("CSMs Table")
            #take all CSMs as dataframe
            CSM_= readAndProcessIdXML(workspace_path / "result-files" /f"{selected_file}")

            ##TODO setup more better/effiecient
            # Remove the out pattern of idxml
            #file_name_wout_out = remove_substrings(selected_file, nuxl_out_pattern)
            file_name_wout_out = clean_filename_with_regex(selected_file)
            #print("file_name_wout_out: ", file_name_wout_out)
            
            if file_name_wout_out == "Example": 
                file_name_wout_out = "Example_RNA_UV_XL"

            MS2 = process_mzML_file(os.path.join(Path.cwd().parent ,  str(st.session_state.workspace)[3:] , "mzML-files" ,f"{file_name_wout_out}.mzML"))
            if MS2 is None:
                st.warning("The corresponding " + file_name_wout_out + ".mzML file could not be found. Please re-upload the mzML file to visualize all peaks.")
                            
            if CSM_ is None: 
                st.warning("No CSMs found in selected idXML file")
            else:
                
                if CSM_['NuXL:NA'].str.contains('none').any():
                    st.warning("nonXL CSMs found")  
                else:
                    
                    # provide dataframe
                    gb = GridOptionsBuilder.from_dataframe(CSM_[list(CSM_.columns.values)])

                    # configure selection
                    gb.configure_selection(selection_mode="single", use_checkbox=True)
                    gb.configure_side_bar()
                    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10)
                    gridOptions = gb.build()
                    
                    data = AgGrid(CSM_,
                                gridOptions=gridOptions,
                                enable_enterprise_modules=True,
                                allow_unsafe_jscode=True,
                                update_mode=GridUpdateMode.SELECTION_CHANGED,
                                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)

                    #download table
                    download_table(CSM_, f"{os.path.splitext(selected_file)[0]}")
                    #select row by user
                    selected_row = data["selected_rows"]

                    if selected_row:
                        # Create a dictionary of annotation features
                        annotation_data_idxml = {'mzarray': [float(value) for value in {selected_row[0]['mz_values']}.pop().split(',')],
                                'anotarray': [str(value) for value in {selected_row[0]['ions']}.pop().split(',')]
                            }

                        #print("==>>> length of annotation_data_idxml: ", len(annotation_data_idxml['anotarray']), "\n-------------\n")
                        
                        #annotation_data_idxml_df = pd.DataFrame(annotation_data_idxml)
                        #annotation_data_idxml_df.to_csv(str(selected_row[0]['ScanNr']) + "_idxml_annot.csv")
                            
                        if MS2 is not None:
                            # Extract m/z and intensity data from the selected MS2 spectrum
                            mz_full, inten_full = get_mz_intensities_from_ms2(MS2_spectras=MS2, native_id=selected_row[0]['SpecId'])

                            # Convert annotation_data into a dictionary for efficient matching
                            annotation_dict = {(round(mz, 6)): anot for mz, anot in zip(annotation_data_idxml['mzarray'], annotation_data_idxml['anotarray'])}
                            
                            #print("==>>> annotation_dict idxml: ", annotation_dict , "\n-------------\n")
                            # Annotate the data
                            annotation_data = []
                            for intensity, mz in zip(inten_full, mz_full):
                                mz_r = round(float(mz), 6)

                                annotation = annotation_dict.get(mz_r, ' ')

                                annotation_data.append({
                                    'mzarray': mz,
                                    'intarray': intensity,
                                    'anotarray': annotation
                                }) 

                            #n_non_empty = len([
                            #                    entry for entry in annotation_data if entry['anotarray'] != ' '
                            #                ])
                            #print("==>>> annotated: ", n_non_empty , "\n-------------\n")
                            
                        if MS2 is None:
                            annotation_data = annotation_data_idxml # just provide the annotated peaks
                        
                        # Check if the lists are not empty
                        if annotation_data:
                            # Create the DataFrame
                            annotation_df = pd.DataFrame(annotation_data)
                            annotation_df.to_csv(str(selected_row[0]['ScanNr']) + "_idxml_annot_full.csv")
                            # title of spectra
                            spectra_name = os.path.splitext(selected_file)[0] +" Scan# " + str({selected_row[0]['ScanNr']}).strip('{}') + " Pep: " + str({selected_row[0]['Peptide']}).strip('{}\'') +  " + " +str ({selected_row[0]['NuXL:NA']}).strip('{}\'')
                            # generate ms2 spectra
                            fig = plot_ms2_spectrum_full(annotation_df, spectra_name, "black")
                            #show figure
                            show_fig(fig,  f"{os.path.splitext(selected_file)[0]}_scan_{str({selected_row[0]['ScanNr']}).strip('{}')}")

                        else:
                            # if any list empty
                            st.warning("Annotation not available for this peptide")
                                
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
                PRTs_section= read_protein_table(protein_path)
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

                            #show figure, with download
                            show_fig(adducts_fig , f"{os.path.splitext(new_filename)[0]}_adduct_summary")
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
            CSM_= readAndProcessIdXML(workspace_path / "result-files" /f"{selected_file}")
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
                PRTs_section= read_protein_table(protein_path)
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

    if any(Path(result_dir).iterdir()):
        v_space(2)
        #  all result files currently in workspace
        df = pd.DataFrame(
            {"file name": [f.name for f in Path(result_dir).iterdir()]})
        st.markdown("##### result files in current workspace:")

        show_table(df)
        v_space(1)
        # Remove files
        copy_local_result_files_from_directory(result_dir)
        with st.expander("🗑️ Remove result files"):
            #take all example result files name
            list_result_examples = list_result_example_files()
            #take all session result files
            session_files = [f.name for f in sorted(result_dir.iterdir())]
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
            to_download = st.multiselect("select result files for download",
                                    options=[f.name for f in sorted(result_dir.iterdir())])
            
            c1, c2 = st.columns(2)
            if c2.button("Download **selected**", type="primary", disabled=not any(to_download)):
                #download selected files will display download hyperlink
                download_selected_result_files(to_download, "selected_result_files")
                #st.rerun()

            ### afraid if there are many files in workspace? should we removed this option?
            if c1.button("⚠️ Download **all**", disabled=not any(result_dir.iterdir())):
                #create the zip content of all result files in workspace
                b64_zip_content = create_zip_and_get_base64_()
                #display the download hyperlink
                href = f'<a href="data:application/zip;base64,{b64_zip_content}" download="all_result_files.zip">Download All Files</a>'
                st.markdown(href, unsafe_allow_html=True)

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

