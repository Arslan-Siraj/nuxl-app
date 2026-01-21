import io
import os
import shutil
import base64
import pandas as pd
import streamlit as st
from io import StringIO
from pathlib import Path
from zipfile import ZipFile
from pyopenms import IdXMLFile
from src.common import reset_directory
import zipfile

def add_to_result(filename: str):
    """
    Add the given filename to the list of view.

    Args:
        filename (str): The filename to be added to the list of selected result files.

    Returns:
        None
    """
    # Check if file in params selected result files, if not add it
    if filename not in st.session_state["selected-result-files"]:
        st.session_state["selected-result-files"].append(filename)
        
def load_example_result_files() -> None:
    """
    Copies example result files to the result directory.

    Args:
        None

    Returns:
        None
    """
    result_dir: Path = Path(st.session_state.workspace, "result-files")
    example_data_dir: Path = Path(st.session_state.workspace, "example-data-files")
    # Copy files from example-data/result to workspace result directory, add to selected files
    for f in example_data_dir.iterdir():
        if f.suffix in (".idXML", ".tsv"):
            shutil.copy(f, result_dir)
            add_to_result(f.name)  

def remove_selected_result_files(to_remove: list[str]) -> None:
    """
    Removes selected idXML files from the idXML directory.

    Args:
        to_remove (List[str]): List of result files to remove.

    Returns:
        None
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")

    # remove all given selected files from result workspace directory
    for f in to_remove:
        # deleted files
        Path(result_dir, f).unlink() 
        #st.session_state["selected-result-files"].remove(f)
    st.success("Selected result files removed!")


def remove_all_result_files() -> None:
    """
    Removes all result files from the result directory.
    Args:
        None

    Returns:
        None
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")

    # reset (delete and re-create) result directory in workspace
    reset_directory(result_dir)
    # reset selected result list
    st.session_state["selected-result-files"] = []
    st.success("All result files removed!")

@st.cache_data
def copy_local_result_files_from_directory(local_result_directory: str) -> None:
    """
    Copies local fasta files from a specified directory to the result directory.

    Args:
        local_result_directory (str): Path to the directory containing the result files.

    Returns:
        None
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")

    #st.write("result_dir", local_result_directory)
    # Check if local directory contains result files, if not exit early
    if not any(Path(local_result_directory).glob("*")):
        st.warning("No result files found in specified folder.")
        return
    # Copy all result files to workspace result directory, add to selected files
    files = Path(local_result_directory).glob("*")
    #st.write("files", local_result_directory)
    for f in files:
        #st.write("f", f.name)
        add_to_result(f.name) 
    #st.success("Successfully added local files!")

def save_uploaded_result(uploaded_files: list[bytes]) -> None:
    """
    Saves uploaded result files to the result-files directory.

    Args:
        uploaded_files (List[bytes]): List of uploaded result files (idXML and tsv).

    Returns:
        None
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")

    # A list of files is required, since online allows only single upload, create a list
    if st.session_state.location == "online":
        uploaded_files = [uploaded_files]

    # If no files are uploaded, exit early
    for f in uploaded_files:
        if f is None:
            st.warning("Upload some files first.")
            return
        
    # Write files from buffer to workspace mzML directory, add to selected files
    for f in uploaded_files:
        #check if file not in result_dir and extension with .idXML/.tsv
        if f.name not in [f.name for f in result_dir.iterdir()] and (f.name.endswith(".idXML") or f.name.endswith(".tsv")):
            with open(Path(result_dir, f.name), "wb") as fh:
                fh.write(f.getbuffer())
        #add to selected result files in session 
        add_to_result(Path(f.name).stem)
    st.success("Successfully added uploaded files!")

def add_this_result_file(to_add: str, from_path: Path)-> None:
    """
    add result file (full file name with extension like Example_RNA_UV_XL.mzML.ambigious_masses.csv)

    Args:
        to_add (str): any file want to add in result files.

    Returns:
        None
    """
    result_dir: Path = Path(st.session_state.workspace, "result-files")
    to_add_path = Path(result_dir, to_add)

    ## if file already in result_dir delete it 
    for x in result_dir.iterdir():
        if x == to_add_path:
            to_add_path.unlink()

    # Check if the file exists in the mzML directory
    from_file_path = Path(from_path, to_add)
    if from_file_path.exists():
        #check for not same file
        if to_add not in [f.name for f in result_dir.iterdir()]:
            # Copy the file from path dir to result directory
            shutil.copy(from_file_path, result_dir)

def list_result_example_files() -> None:
    """
    Get all result examples file

    Args:
        None

    Returns:
        List of all result example files names 

    """
    list_result_example_files = []
    #iterate over example-data/idXMLS files
    for f in Path("example-data", "idXMLs").glob("*"):
        #append the name to list with extension
        list_result_example_files.append(f.name)

    return list_result_example_files

def create_zip_and_get_base64_():
    """
    create decoded zip format of all result-dir files

    Args:
        None

    Returns:
        zip content file 
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")

    # Create a temporary in-memory zip file
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as zip_file:
        for file_path in Path(result_dir).iterdir():
            zip_file.write(file_path, arcname=file_path.name)

    # Reset the buffer's file pointer to the beginning
    buffer.seek(0)

    # Encode the zip file content to base64
    b64_zip_content = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return b64_zip_content

def create_zip_and_get_base64(file_paths):
    """
    create zip file of all selected files

    Args:
       file_paths:  List of result files paths to download.

    Returns:
        zip file content
    """

    # Create a temporary in-memory zip file
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as zip_file:
        for file_path in file_paths:
            zip_file.write(file_path, arcname=file_path.name)
    
    # Reset the buffer's file pointer to the beginning
    buffer.seek(0)
    
    # Encode the zip file content to base64
    b64_zip_content = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return b64_zip_content

def download_selected_result_files(to_download: list[str], link_name: str, zip_filename="selected_files") -> None:
    """
    download selected idXML files from current workspace.

    Args:
        to_download (List[str]): List of result files to download.

    Returns:
        None
    """

    result_dir: Path = Path(st.session_state.workspace, "result-files")
    #make full file paths
    file_paths = [result_dir / f"{file_name}" for file_name in to_download]  # Replace "your_extension" with the actual file extension
    #creta zip content file
    b64_zip_content = create_zip_and_get_base64(file_paths)
    #create href for download
    href = f'<a href="data:application/zip;base64,{b64_zip_content}" download="{zip_filename}.zip">{link_name}</a>'
    #show on page
    st.markdown(href, unsafe_allow_html=True)

###################################### deal with .idXML file ##################################

def strToFloat(df):
    """
    convert every string col into an int or float if possible of given dataframe 

    Args:
        df: dataframe

    Returns:
        df: dataframe modified accordingly
    """
    for col in df:
        try:
            #convert string col to float
            df[col] = [float(i) for i in df[col]]
        except ValueError:
            continue
    return df

def readAndProcessIdXML(input_file, top=1):
    """
    convert the (.idXML) format identification file to dataframe

    Args:
        input_file: idXML file path 
        top: top hits (dafault 1)

    Returns:
        df: dataframe (.idXML -> dataframe)
    """
    prot_ids = []; pep_ids = []
    IdXMLFile().load(str(input_file), prot_ids, pep_ids)
    meta_value_keys = []
    rows = []
    #st.write("len of pep_ids:", len(pep_ids))
    if len(pep_ids)>0:
        for peptide_id in pep_ids:
            spectrum_id = peptide_id.getMetaValue("spectrum_reference")
            scan_nr = spectrum_id[spectrum_id.rfind('=') + 1 : ]

            hits = peptide_id.getHits()

            psm_index = 1
            for h in hits:
                if psm_index > top:
                    break
                charge = h.getCharge()
                score = h.getScore()
                z2 = 0; z3 = 0; z4 = 0; z5 = 0

                if charge == 2:
                    z2 = 1
                if charge == 3:
                    z3 = 1
                if charge == 4:
                    z4 = 1
                if charge == 5:
                    z5 = 1
                if "target" in h.getMetaValue("target_decoy"):
                    label = 1
                else:
                    label = 0
                sequence = h.getSequence().toString()
                if len(meta_value_keys) == 0: # fill meta value keys on first run
                    h.getKeys(meta_value_keys)
                    meta_value_keys = [x.decode() for x in meta_value_keys]
                    all_columns = ['SpecId','PSMId','Label','Score','ScanNr','Peptide','peplen','ExpMass','charge2','charge3','charge4','charge5','accessions', 'intensities', 'mz_values','ions'] + meta_value_keys
                    #print(all_columns)
                # static part
                accessions = ';'.join([s.decode() for s in h.extractProteinAccessionsSet()])

                #get peak annotations
                peak_annotation = h.getPeakAnnotations()
                intensity_values_ = []  # To store peak.intensity values
                mz_values_ = []  # To store peak.mz values
                annotations_ = [] # To store ions annotations

                for peak in peak_annotation:
                    intensity_values_.append(str(peak.intensity))
                    mz_values_.append(str(peak.mz))
                    annotations_.append(str(peak.annotation))

                # change list in to string with , seperate
                intensities = ",".join(intensity_values_)
                mz_values = ",".join(mz_values_)
                ions = ",".join(annotations_)

                row = [spectrum_id, psm_index, label, score, scan_nr, sequence, str(len(sequence)), peptide_id.getMZ(), z2, z3, z4, z5, accessions, intensities, mz_values, ions]
                # scores in meta values
                for k in meta_value_keys:
                    s = h.getMetaValue(k)
                    if type(s) == bytes:
                        s = s.decode()
                    row.append(s)
                rows.append(row)
                psm_index += 1
                break; # parse only first hit
    
        df =pd.DataFrame(rows, columns=all_columns)
        convert_dict = {'SpecId': str,
                        'PSMId': int,
                        'Label': int,
                        'Score': float,
                        'ScanNr': int,
                        'peplen': int                
                    }
        
        df = df.astype(convert_dict)
        return df
    
    else: 
        return None
  
######################### deal with (.tsv) file of proteins #######

def read_protein_table(input_file):
    """
    convert the (.tsv) protein output table to dataframe

    Args:
        input_file: input file of protein output (.tsv) format1

    Returns:
        section_dfs: list of dataframes contain 4 dataframe
    """
    section_dfs = []
    current_section = []
    skip_next_line = False
    use_next_line_as_header = False

    # Read the TSV file line by line
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Check if the line is a section header
            if line.startswith('==') and line.endswith('=='):
                # Save the current section DataFrame to the list
                if current_section:
                    # If the section is 2, 3, or 5, use the next line as the header and remove the current header
                    if use_next_line_as_header:
                        try:
                            section_df = pd.read_csv(StringIO('\n'.join(current_section[1:])), delimiter='\t', header=None)
                            section_df.columns = current_section[0].split('\t')
                        except pd.errors.EmptyDataError:
                            # Handle the EmptyDataError by creating an empty DataFrame with appropriate headers
                            section_df = pd.DataFrame(columns=current_section[0].split('\t'))
                        section_dfs.append(section_df)
                        use_next_line_as_header = False
                    else:
                        try:
                            section_df = pd.read_csv(StringIO('\n'.join(current_section)), delimiter='\t')
                        except pd.errors.EmptyDataError:
                            # Handle the EmptyDataError by creating an empty DataFrame
                            section_df = pd.DataFrame()
                        section_dfs.append(section_df)

                    current_section = []
                    skip_next_line = True
            else:
                # Append the line to the current section content
                if not skip_next_line:
                    current_section.append(line)
                skip_next_line = False

                # Check if the next section should use the next line as the header
                if line.startswith("Protein summary") or line.startswith("Crosslink efficiency") or line.startswith("Precursor adduct summary"):
                    use_next_line_as_header = True

                # Check if section 4, then update header
                if line.startswith("Crosslink efficiency"):
                    use_next_line_as_header = False
                    header_line = next(f).strip()
                    header = ["AA", "Crosslink efficiency"]
                    current_section.append(header_line)
                    current_section[0] = "\t".join(header)

    # Append the last section to the list
    if current_section:
        try:
            section_df = pd.read_csv(StringIO('\n'.join(current_section)), delimiter='\t')
        except pd.errors.EmptyDataError:
            # Handle the EmptyDataError by creating an empty DataFrame
            section_df = pd.DataFrame()
        section_dfs.append(section_df)

    return section_dfs

#########dia page ##########
def download_folder_library(folder_path: Path | str, link_name: str, zip_name: str = "selected_files.zip") -> None:
      """
      Create a Streamlit download link for a folder zipped into a single file.

      Parameters
      ----------
      folder_path : Path or str
            Path to the folder to be zipped and downloaded.
      link_name : str
            Text displayed for the download link.
      zip_name : str, optional
            Name of the downloaded ZIP file.
      """

      folder_path = Path(folder_path)
      if not folder_path.is_dir():
            raise ValueError(f"Provided path is not a directory: {folder_path}")

      # Create an in-memory ZIP file
      buffer = io.BytesIO()
      with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in folder_path.rglob("*"):
                  if file_path.is_file():
                        # Keep relative path in ZIP
                        zipf.write(file_path, arcname=file_path.relative_to(folder_path))

      buffer.seek(0)
      b64_zip_content = base64.b64encode(buffer.read()).decode("utf-8")

      # Generate HTML link for Streamlit
      href = (
            f'<a href="data:application/zip;base64,{b64_zip_content}" '
            f'download="{zip_name}">{link_name}</a>'
      )
      st.markdown(href, unsafe_allow_html=True)



def copy_folder_library_to_results(
    folder_path: Path | str,
    filename_dont_copy=None,
) -> None:
    """
    Create a copy of a folder into the results directory.

    Parameters
    ----------
    folder_path : Path or str
        Path to the folder to be copied to the results directory.
    filename_dont_copy : Path, UploadedFile, or None
        Single file to exclude from copying.
    """

    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        raise ValueError(f"Provided path is not a directory: {folder_path}")

    result_dir = Path(st.session_state.workspace, "result-files")
    result_dir.mkdir(parents=True, exist_ok=True)

    # Resolve excluded filename once
    excluded_name = (
        filename_dont_copy.name
        if filename_dont_copy is not None
        else None
    )

    for item in folder_path.iterdir():
        if excluded_name is not None and item.name == excluded_name:
            continue

        dest = result_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


import stat
def delete_folder_library(folder_path: Path | str) -> None:
    """
    Delete a folder and all of its contents (Linux and Windows safe).
    """
    folder_path = Path(folder_path)

    if not folder_path.exists():
        return

    if not folder_path.is_dir():
        raise ValueError(f"Provided path is not a directory: {folder_path}")

    def _on_rm_error(func, path, exc_info):
        # Windows: clear read-only attribute, POSIX: no-op
        try:
            Path(path).chmod(stat.S_IWRITE)
        except Exception:
            pass
        func(path)

    shutil.rmtree(folder_path, onerror=_on_rm_error)

    