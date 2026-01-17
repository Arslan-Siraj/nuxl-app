import streamlit as st
import subprocess

SUPPRESSED_PATTERNS = [
    "qt.network.ssl"
    "UserWarning:",
    "WARNING:tensorflow:",
    "Warnings.warn(",
    "from pkg_resources",
    "pkg_resources is deprecated",
    "OPENMS_DATA_PATH",
    "tensorflow/",
    "Could not find cuda drivers",
    "GPU will not be used",
    "NUMA node",
    "cuda",
    "warnings",
    "To enable the following instructions",
    "FutureWarning",
    "x = re.sub(pattern, '', string_)"
]

SUPPRESSED_PATTERNS_out = [
    "Warning: OPENMS_DATA_PATH environment variable already exists"
]

def run_subprocess(args: list[str], variables: list[str], result_dict: dict) -> None:
    """
    Run a subprocess and capture its output.

    Args:
        args (list[str]): The command and its arguments as a list of strings.
        variables (list[str]): Additional variables needed for the subprocess (not used in this code).
        result_dict dict: A dictionary to store the success status (bool) and the captured log (str).

    Returns:
        None
    """

    # Run the subprocess and capture its output
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    # Lists to store the captured standard output and standard error
    stdout_ = []
    stderr_ = []

    # Capture the standard output of the subprocess
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            # Print every line of standard output on the Streamlit page
            #st.text(output.strip())
            # Append the line to store in the log
            #stdout_.append(output.strip())

            line = output.strip()

             # skip empty lines
            if not line:
                continue

            # suppress known non-fatal warnings
            if any(p in line for p in SUPPRESSED_PATTERNS_out):
                #stderr_.append(line)   # keep in log if you want
                continue

            # real errors only
            st.text(line)
            stdout_.append(line)

    # Capture the standard error of the subprocess
    while True:
        error = process.stderr.readline()
        if error == '' and process.poll() is not None:
            break
        if error:
            line = error.strip()

            # suppress known non-fatal warnings
            if any(p in line for p in SUPPRESSED_PATTERNS):
                stderr_.append(line)   # keep in log if you want
                continue

            # real errors only
            st.error(line)
            stderr_.append(line)

    # Check if the subprocess ran successfully (return code 0)
    if process.returncode == 0:
        result_dict["success"] = True
        # Save all lines from standard output to the log
        result_dict["log"] = "\n".join(stdout_)
       
    else:
        result_dict["success"] = False
        # Save all lines from standard error to the log, even if the process encountered an error
        result_dict["log"] = "\n".join(stdout_ + stderr_)
  
