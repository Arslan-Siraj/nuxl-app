import os
import streamlit as st
from streamlit_plotly_events import plotly_events
import subprocess
from src.common import *
from src.view import *
from src.fileupload import *
from src.result_files import *
from src.ini2dec import *
import threading
from src.captcha_ import *
from src.run_subprocess import *
import textwrap
from datetime import datetime
import ast

params = page_setup()

# If run in hosted mode, show captcha as long as it has not been solved
if 'controllo' not in st.session_state or params["controllo"] == False:
    # Apply captcha by calling the captcha_control function
    captcha_control()        

### main content of page

# title of page
st.title("⚙️ Run Analysis")

######################## Take NuXL configurations ini read #################################
# Define the sections you want to extract
# will capture automaticaly if add new section as decoy_factor 
sections = [
    "fixed",
    "variable",
    "presets",
    "enzyme",
    "scoring",
    "variable_max_per_peptide",
    "length",
    "mass_tolerance", # will store in config dict both precursor_mass_tolerance_unit, and fragmant_mass_tolerance_unit
    "mass_tolerance_unit", # will store in config dict both precursor_mass_tolerance, and fragmant_mass_tolerance
    "min_size",
    "max_size",
    "missed_cleavages",
    "peptideFDR", 
    "xlFDR",
    "min_charge", 
    "max_charge"
]

# current directory
current_dir = os.getcwd()
# take .ini config path
config_path = os.path.join(current_dir, 'assets', 'OpenMS_NuXL.ini')
# take NuXL config dictionary 
# (will give every section as 1 entry: 
# entry = {
        #"name": node_name,
        #"default": node_default,
        #"description": node_desc,
        #"restrictions": restrictions_list
        # })
NuXL_config=ini2dict(config_path, sections)

#print(NuXL_config)

# make sure "selected-mzML-files" is in session state
if "selected-mzML-files" not in st.session_state:
    st.session_state["selected-mzML-files"] = params.get("selected-mzML-files", [])

# make sure "selected-fasta-files" is in session state
if "selected-fasta-files" not in st.session_state:
    st.session_state["selected-fasta-files"] = params.get("selected-fasta-files", [])

# make sure mzML example files in current session state
#load_example_mzML_files()

# take mzML files from current session file
mzML_files_ = [f.name for f in Path(st.session_state.workspace, "mzML-files").iterdir()]

#delete_files(directory = Path(st.session_state.workspace, "mzML-files"), remove_files_end_with = '.raw.mzML')

# make sure fasta example files in current session state
#load_example_fasta_files()

# take fasta files from current session file
fasta_files = [f.name for f in Path(st.session_state.workspace,"fasta-files").iterdir()]

# put Trypsin as first enzyme
if 'Trypsin/P' in NuXL_config['enzyme']['restrictions']:
    NuXL_config['enzyme']['restrictions'].remove('Trypsin/P')
    NuXL_config['enzyme']['restrictions'].insert(0, 'Trypsin/P')

mzML_file_path = None
database_file_path = None

with st.form("fasta-upload", clear_on_submit=False):

    # selected mzML file from mzML files list
    selected_mzML_file = st.selectbox(
        "choose mzML/raw file",
        [item for item in mzML_files_ if not (item.endswith(".csv") or item.endswith(".mgf"))]
        ,
        help="If file not here, please upload at File Upload"
    )

    # select fasta file from mzML files list
    selected_fasta_file = st.selectbox(
        "choose fasta file",
        [f.name for f in Path(st.session_state.workspace,
                            "fasta-files").iterdir()],
        help="If file not here, please upload at File Upload"
    )

    # take full path of mzML file
    if selected_mzML_file:
        mzML_file_path = str(Path(st.session_state.workspace, "mzML-files", selected_mzML_file))

    # take full path of fasta file
    if selected_fasta_file:
        database_file_path = str(Path(st.session_state.workspace, "fasta-files", selected_fasta_file))

    # take all variables settings from config dictionary/ take all user configuration
    cols=st.columns(2)
    with cols[0]:
        cols_=st.columns(2)
        with cols_[0]:
            Enzyme = st.selectbox('enzyme', NuXL_config['enzyme']['restrictions'], help=NuXL_config['enzyme']['description'])
        with cols_[1]:
            Missed_cleavages = str(st.number_input("missed cleavages",value=int(NuXL_config['missed_cleavages']['default']), min_value=1, max_value=20, help=NuXL_config['missed_cleavages']['description'] + " default: "+ NuXL_config['missed_cleavages']['default']))

    with cols[1]:
        cols_=st.columns(2)
        with cols_[0]:
            peptide_min = str(st.number_input('peptide min length', value=int(NuXL_config['min_size']['default']), min_value=1, max_value=100, help=NuXL_config['min_size']['description'] + " default: "+ NuXL_config['min_size']['default']))

        with cols_[1]:
            peptide_max= str(st.number_input('peptide max length', value=int(NuXL_config['max_size']['default']), min_value=3, max_value=1000000, help=NuXL_config['max_size']['description'] + " default: "+ NuXL_config['max_size']['default']))

    cols=st.columns(2)
    with cols[0]:
        cols_=st.columns(2)
        with cols_[0]:
            Precursor_MT = str(st.number_input("precursor mass tolerance",value=float(NuXL_config['precursor_mass_tolerance']['default']), help=NuXL_config['precursor_mass_tolerance']['description'] + " default: "+ NuXL_config['precursor_mass_tolerance']['default']))
            if float(Precursor_MT) <= 0:
                st.error("Precursor mass tolerance must be a positive integer")

        with cols_[1]:
            Precursor_MT_unit = cols_[1].radio(
            "precursor mass tolerance unit",
            NuXL_config['precursor_mass_tolerance_unit']['restrictions'], 
            help=NuXL_config['precursor_mass_tolerance_unit']['description']  + " default: "+ NuXL_config['precursor_mass_tolerance_unit']['default'],
            key="Precursor_MT_unit"
            )

    with cols[1]:
        cols_=st.columns(2)
        with cols_[0]:
            Fragment_MT = str(st.number_input("fragment mass tolerance",value=float(NuXL_config['fragment_mass_tolerance']['default']), help=NuXL_config['fragment_mass_tolerance']['description'] + " default: "+ NuXL_config['fragment_mass_tolerance']['default']))
            if float(Fragment_MT) <= 0:
                st.error("Fragment mass tolerance must be a positive integer")

        with cols_[1]:
            Fragment_MT_unit = cols_[1].radio(
            "fragment mass tolerance unit",
            NuXL_config['precursor_mass_tolerance_unit']['restrictions'], 
            help=NuXL_config['fragment_mass_tolerance_unit']['description']+ " default: "+ NuXL_config['fragment_mass_tolerance_unit']['default'],
            key="Fragment_MT_unit"
            )

    cols=st.columns(2)
    with cols[0]:
        preset = st.selectbox('select the suitable preset',NuXL_config['presets']['restrictions'], help=NuXL_config['presets']['description'] + " default: "+ NuXL_config['presets']['default'])
    with cols[1]:
        length = str(st.number_input("length of oligonucleotide",value=int(NuXL_config['length']['default']), help=NuXL_config['length']['description'] + " default: "+ NuXL_config['length']['default']))
        if int(length) <= -1:
            st.error("Length must be a positive integer.")

    cols=st.columns(2)
    with cols[0]:
        fixed_modification = st.multiselect('select fixed modifications:', NuXL_config['fixed']['restrictions'], help=NuXL_config['fixed']['description'] + " default: "+ NuXL_config['fixed']['default'])

    with cols[1]: 
        variable_modification = st.multiselect('select variable modifications:', NuXL_config['variable']['restrictions'], help=NuXL_config['variable']['description'] + " default: Oxidation (M)" , default = "Oxidation (M)")
        
    cols=st.columns(2)
    with cols[0]:
        Variable_max_per_peptide  = str(st.number_input("variable modification max per peptide",value=int(NuXL_config['variable_max_per_peptide']['default']), help=NuXL_config['variable_max_per_peptide']['description'] + " default: "+ NuXL_config['variable_max_per_peptide']['default']))
        if int(Variable_max_per_peptide) <= -1:
            st.error("variable modification max per peptide must be a positive integer")

    with cols[1]:
        scoring = cols[1].radio(
            "scoring method",
            [NuXL_config['scoring']['restrictions'][1], NuXL_config['scoring']['restrictions'][0]],
            help=NuXL_config['scoring']['description'] + " default: "+ NuXL_config['scoring']['default'],
            key="scoring"
            )
 
    with st.expander("**Advanced parameters**"):
        
        cols=st.columns(2)
        with cols[0]:
            inner_cols_2=st.columns(2)
            with inner_cols_2[0]:
               charge_min = str(st.number_input('precursor min charge', min_value=1, max_value=10, value=int(NuXL_config['min_charge']['default']), help=NuXL_config['min_charge']['description'] + " default: "+ NuXL_config['min_charge']['default']))
            with inner_cols_2[1]:
                charge_max = str(st.number_input('precursor max charge', value=int(NuXL_config['max_charge']['default']), min_value=1, max_value=10, help=NuXL_config['max_charge']['description'] + " default: "+ NuXL_config['max_charge']['default']))
                
        with cols[1]:
            inner_cols_1=st.columns(2)
            with inner_cols_1[0]:
                peptideFDR = str(st.number_input(
                            "peptide FDR",
                            value=float(NuXL_config['peptideFDR']['default']),  # Default value as float
                            help=NuXL_config['peptideFDR']['description'] +
                                " Default: " + str(NuXL_config['peptideFDR']['default']),
                            min_value=0.0,  # Minimum value
                            max_value=1.0,  # Maximum value
                            step=0.01,  # Step size
                ))
            #st.selectbox('peptide FDR',NuXL_config['peptideFDR']['restrictions'], help=NuXL_config['peptideFDR']['description'] + " default: "+ NuXL_config['peptideFDR']['default'])
            with inner_cols_1[1]:
                XLFDR_input =  st.text_area(
                                    "XL FDR",
                                    value=str([0.01, 0.1, 1.0]),  # Default value
                                    help=NuXL_config['xlFDR']['description'] + " or use single float (e-g 0.01). " + "For protein level reporting important to select (0.01 and 1.0). "
                                        " Default: " + '[0.01, 0.1, 1.0]'
                                ) 
            
                try:
                    # Attempt to parse the input as a Python list
                    parsed_value = ast.literal_eval(XLFDR_input)  # Safely evaluate the input

                    # Check if input is a list of floats
                    if isinstance(parsed_value, list):
                        if not all(isinstance(value, (int, float)) for value in parsed_value):
                            raise ValueError("All elements in the list must be numeric.")
                        if not all(0.00 <= value <= 1.00 for value in parsed_value):
                            raise ValueError("All values in the list must be between 0.00 and 1.00.")
                        XLFDR = [str(value) for value in parsed_value]  # Ensure floats
                    # Check if input is a single float
                    elif isinstance(parsed_value, (int, float)):
                        if not (0.00 <= parsed_value <= 1.00):
                            raise ValueError("The value must be between 0.00 and 1.00.")
                        XLFDR = [str(parsed_value)]  # Wrap the single value in a list
                    else:
                        raise ValueError("Input must be a list of numbers or a single number.")

                except (ValueError, SyntaxError) as e:
                    # Invalid input: Display an error message
                    st.error(f"Invalid XL FDR format: {e} Please provide input in the format [0.01, 0.1, 1.0] or a single float between 0.00 and 1.00.")
    
    submit_button = st.form_submit_button("Run-analysis", type="primary",  disabled=mzML_file_path is None or database_file_path is None)

# out file path
result_dir: Path = Path(st.session_state.workspace, "result-files")

##################################### NuXL command (subprocess) ############################

# result dictionary to capture output of subprocess
result_dict = {}
result_dict["success"] = False
result_dict["log"] = " "

# create terminate flag from even function
terminate_flag = threading.Event()
terminate_flag.set()

# terminate subprocess by terminate flag
def terminate_subprocess():
    global terminate_flag
    terminate_flag.set()

# run analysis 
if submit_button:

    # To terminate subprocess and clear form
    if st.button("Terminate/Clear", key="terminate-button", type="secondary"):
        # terminate subprocess
        terminate_subprocess()
        st.warning("Process terminated. The analysis may not be complete.")

        # clear form
        st.rerun() 

    # with st.spinner("Running analysis... Please wait until analysis done 😑"): #without status/ just spinner button
    with st.status("Running analysis... Please wait until analysis done 😑"):
       
        # create same output file path name as input file path
        mzML_file_name = os.path.basename(mzML_file_path)
        protocol_name = os.path.splitext(mzML_file_name)[0]
        result_path = os.path.join(result_dir, protocol_name + ".idXML")

        if mzML_file_path.endswith(".raw.mzML"):
            st.warning(f"(.raw.mzML) not supported, please select (.raw) or (.mzML) format",  icon="ℹ️")
        
        else:
            # If session state is local
            if st.session_state.location == "local":
              
                OpenNuXL_exec = os.path.join(os.getcwd(),'OpenNuXL')
                perc_exec = os.path.join(os.getcwd(), '_thirdparty', 'Percolator', 'percolator.exe') 
                thermo_exec_path = os.path.join(os.getcwd(), '_thirdparty', 'ThermoRawFileParser', 'ThermoRawFileParser.exe')

                args = [OpenNuXL_exec, "-ThermoRaw_executable", thermo_exec_path, "-in", mzML_file_path, "-database", database_file_path, "-out", result_path, "-NuXL:presets", preset, 
                                "-NuXL:length", length, "-NuXL:scoring", scoring, "-precursor:mass_tolerance",  Precursor_MT, "-precursor:mass_tolerance_unit",  Precursor_MT_unit,
                                "-fragment:mass_tolerance",  Fragment_MT, "-fragment:mass_tolerance_unit",  Fragment_MT_unit, "-threads", str(30),
                                "-peptide:min_size", peptide_min, "-peptide:max_size", peptide_max, "-peptide:missed_cleavages", Missed_cleavages, "-peptide:enzyme", Enzyme,
                                "-modifications:variable_max_per_peptide", Variable_max_per_peptide,"-report:peptideFDR", peptideFDR
                                ]

                args.extend(["-percolator_executable", perc_exec])

            # If session state is online/docker
            else:  

                thermo_exec_path = "/thirdparty/ThermoRawFileParser/ThermoRawFileParser.exe"
                # In docker it executable on path
                args = ["OpenNuXL", "-ThermoRaw_executable", thermo_exec_path, "-in", mzML_file_path, "-database", database_file_path, "-out", result_path, "-NuXL:presets", preset, 
                            "-NuXL:length", length, "-NuXL:scoring", scoring, "-precursor:mass_tolerance",  Precursor_MT, "-precursor:mass_tolerance_unit",  Precursor_MT_unit, 
                            "-fragment:mass_tolerance",  Fragment_MT, "-fragment:mass_tolerance_unit",  Fragment_MT_unit,"-peptide:min_size", peptide_min, "-peptide:max_size",peptide_max, "-peptide:missed_cleavages",Missed_cleavages, "-peptide:enzyme", Enzyme,
                            "-modifications:variable_max_per_peptide", Variable_max_per_peptide,"-report:peptideFDR", peptideFDR                            
                            ]
                
            args.extend(["-report:xlFDR"])
            args.extend(XLFDR)

            # no filtering at peptide level provides so all 1.0 (no filtering)
            XLFDR_all_ones = [1.0] * len(XLFDR)
            XLFDR_all_ones_str = [str(value) for value in XLFDR_all_ones]
            args.extend(["-report:xl_peptidelevel_FDR"])
            args.extend(XLFDR_all_ones_str)

            # If variable modification provided
            if variable_modification: 
                args.extend(["-modifications:variable"])
                args.extend(variable_modification)

            # If fixed modification provided
            if fixed_modification: 
                args.extend(["-modifications:fixed"])
                args.extend(fixed_modification)
            
            # Add any additional variables needed for the subprocess (if any)
            variables = []  

            # want to see the command values and argues
            message = f"Running '{' '.join(args)}'"
            st.info(message)
            st.info(f"Analyzing {mzML_file_name}",  icon="ℹ️")

            # run subprocess command
            run_subprocess(args, variables, result_dict)

            #rename the file .raw.mzML --> .mzML
            rename_files(Path(st.session_state.workspace, "mzML-files"))
            
            # Use st.experimental_thread to run the subprocess asynchronously
            # terminate_flag = threading.Event()
            # thread = threading.Thread(target=run_subprocess, args=(args, variables, result_dict))
            # thread.start()
            # thread.join()<

        delete_files(directory = Path(st.session_state.workspace, "mzML-files"), remove_files_end_with = '.raw.mzML')

    search_param = textwrap.dedent(f"""\
            ======= Search Parameters ==========
            Selected mzML File: {mzML_file_path}
            Selected FASTA File: {database_file_path}
            Enzyme: {Enzyme}
            Missed Cleavages: {Missed_cleavages}
            Peptide Min Length: {peptide_min}
            Peptide Max Length: {peptide_max}
            Precursor Mass Tolerance: {Precursor_MT} {Precursor_MT_unit}
            precursor Min charge: {charge_min}
            precursor Max charge: {charge_max}
            Fragment Mass Tolerance: {Fragment_MT} {Fragment_MT_unit}
            Preset: {preset}
            Oligonucleotide Length: {length}
            Fixed Modifications: {', '.join(fixed_modification) if fixed_modification else 'None'}
            Variable Modifications: {', '.join(variable_modification) if variable_modification else 'None'}
            Variable Max Modifications per Peptide: {Variable_max_per_peptide}
            Scoring Method: {scoring}
            PeptideFDR: {peptideFDR}
            XLFDR: {XLFDR}
            """)
    time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = result_dir / f'{protocol_name}_log_{time_stamp}.txt'

    # Save the log to a text file in the result_dir
    with open(log_file_path, "w") as log_file:
            log_file.write(search_param)
            log_file.write("\n======= NuXL search engine output ========== \n ")
            log_file.write(result_dict["log"])

    # if run_subprocess success (no need if not success because error will show/display in run_subprocess command)
    if result_dict["success"]:
        st.text_area("Analysis Log", value=result_dict["log"], height=300)

        # add .mzML.ambigious_masses.csv in result directory 
        add_this_result_file(f"{protocol_name}.mzML.ambigious_masses.csv", Path(st.session_state.workspace, "mzML-files"))
        
        # remove .mzML.ambigious_masses.csv from mzML directory
        remove_this_mzML_file(f"{protocol_name}.mzML.ambigious_masses.csv")

        # all result files in result-dir
        All_files = [f.name for f in sorted(result_dir.iterdir())]

        # filtered out all current run file from all resul-dir files
        current_analysis_files = [s for s in All_files if protocol_name in s]

        # add list of files to dataframe
        df = pd.DataFrame({"All files corresponding to search mzML/raw in workspace ": current_analysis_files})

        # show table of all list files of current protocol
        show_table(df)

        # check if perc files availabe in some cases could not run percolator e-g if identification hits are so less
        perc_exec = any("_perc_" in string for string in current_analysis_files)

        # just show and download the identification_files of XLs PSMs/PRTs if perc_XLs available otherwise without the percolator identification file
        if perc_exec :
            identification_files = [string for string in current_analysis_files if "_perc_0.0100_XLs"  in string or "_perc_0.1000_XLs" in string or "_perc_1.0000_XLs" in string or "_perc_proteins" in string]
        else:
            identification_files = [string for string in current_analysis_files if "_XLs"  in string or "_proteins" in string]

        # then download link for identification file of above criteria 
        download_selected_result_files(identification_files, f":arrow_down: {protocol_name}_XL_identification_files")

        st.success("⚡️ **Analyzing with NuXL Completed Successfully!** ⚡️")

    else:
        # Display error message
        st.error(
                f"⚠️ **Analysis Failed**\n\n"
                f"This might be due to incorrect or incompatible search parameters.\n"
                f"Please refer at the log file '{protocol_name}_log_{time_stamp}.txt'"
                )

save_params(params)
