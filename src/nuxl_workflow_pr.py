import ast
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.workflow.WorkflowManager import WorkflowManager


class Workflow(WorkflowManager):
    def __init__(self) -> None:
        super().__init__("NuXL Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        tabs = st.tabs(["MS data", "FASTA database"])

        with tabs[0]:
            self.ui.upload_widget(
                key="mzML-files",
                name="MS data",
                file_types=["mzML", "raw"],
                fallback=[str(f) for f in Path("example-data", "mzML").glob("*.mzML")],
            )

        with tabs[1]:
            self.ui.upload_widget(
                key="fasta-files",
                name="FASTA database",
                file_types=["fasta", "fa"],
                fallback=[str(f) for f in Path("example-data", "fasta").glob("*.fasta")],
            )

    @st.fragment
    def configure(self) -> None:
        self.ui.select_input_file(
            "mzML-files",
            name="MS data",
            multiple=True,
        )

        self.ui.select_input_file(
            "fasta-files",
            name="FASTA database",
            multiple=False,
        )

        st.markdown("### NuXL parameters")

        self.ui.input_widget(
            "NuXL:presets",
            default="RNA",
            name="Preset",
            widget_type="selectbox",
            options=["RNA", "DNA"],
        )

        self.ui.input_widget(
            "NuXL:length",
            default=4,
            name="Length of oligonucleotide",
            widget_type="number",
            min_value=0,
        )

        self.ui.input_widget(
            "NuXL:scoring",
            default="precursor",
            name="Scoring method",
            widget_type="selectbox",
            options=["precursor", "fragment"],
        )

        cols = st.columns(2)

        with cols[0]:
            self.ui.input_widget(
                "precursor:mass_tolerance",
                default=10.0,
                name="Precursor mass tolerance",
                widget_type="number",
                min_value=0.0,
                step_size=1.0,
            )

            self.ui.input_widget(
                "precursor:mass_tolerance_unit",
                default="ppm",
                name="Precursor mass tolerance unit",
                widget_type="selectbox",
                options=["ppm", "Da"],
            )

        with cols[1]:
            self.ui.input_widget(
                "fragment:mass_tolerance",
                default=20.0,
                name="Fragment mass tolerance",
                widget_type="number",
                min_value=0.0,
                step_size=1.0,
            )

            self.ui.input_widget(
                "fragment:mass_tolerance_unit",
                default="ppm",
                name="Fragment mass tolerance unit",
                widget_type="selectbox",
                options=["ppm", "Da"],
            )

        cols = st.columns(2)

        with cols[0]:
            self.ui.input_widget(
                "peptide:enzyme",
                default="Trypsin/P",
                name="Enzyme",
                widget_type="selectbox",
                options=["Trypsin/P", "Trypsin", "Lys-C", "Arg-C", "no cleavage"],
            )

            self.ui.input_widget(
                "peptide:missed_cleavages",
                default=2,
                name="Missed cleavages",
                widget_type="number",
                min_value=0,
                max_value=20,
            )

            self.ui.input_widget(
                "peptide:min_size",
                default=6,
                name="Peptide min length",
                widget_type="number",
                min_value=1,
            )

            self.ui.input_widget(
                "peptide:max_size",
                default=40,
                name="Peptide max length",
                widget_type="number",
                min_value=1,
            )

        with cols[1]:
            self.ui.input_widget(
                "modifications:variable_max_per_peptide",
                default=3,
                name="Variable modifications max per peptide",
                widget_type="number",
                min_value=0,
            )

            self.ui.input_widget(
                "report:peptideFDR",
                default=1.0,
                name="Peptide FDR",
                widget_type="number",
                min_value=0.0,
                max_value=1.0,
                step_size=0.01,
            )

            self.ui.input_widget(
                "report:xlFDR",
                default="[0.01, 0.1, 1.0]",
                name="XL FDR",
                widget_type="text",
                help="Use either a single value, e.g. 0.01, or a list, e.g. [0.01, 0.1, 1.0].",
            )

        self.ui.input_widget(
            "modifications:variable",
            default=["Oxidation (M)"],
            name="Variable modifications",
            widget_type="multiselect",
            options=[
                "Oxidation (M)",
                "Carbamidomethyl (C)",
                "Phospho (S)",
                "Phospho (T)",
                "Phospho (Y)",
            ],
        )

        self.ui.input_widget(
            "modifications:fixed",
            default=[],
            name="Fixed modifications",
            widget_type="multiselect",
            options=[
                "Carbamidomethyl (C)",
                "Oxidation (M)",
                "Phospho (S)",
                "Phospho (T)",
                "Phospho (Y)",
            ],
        )

    def _parse_xlfdr(self, value) -> list[str]:
        if isinstance(value, list):
            parsed = value
        else:
            parsed = ast.literal_eval(str(value))

        if isinstance(parsed, (int, float)):
            parsed = [parsed]

        if not isinstance(parsed, list):
            raise ValueError("XL FDR must be a float or a list of floats.")

        if not all(isinstance(v, (int, float)) for v in parsed):
            raise ValueError("All XL FDR values must be numeric.")

        if not all(0.0 <= float(v) <= 1.0 for v in parsed):
            raise ValueError("All XL FDR values must be between 0 and 1.")

        return [str(v) for v in parsed]

    def execution(self) -> bool:
        if not self.params.get("mzML-files"):
            self.logger.log("ERROR: No mzML/raw files selected.")
            return False

        if not self.params.get("fasta-files"):
            self.logger.log("ERROR: No FASTA database selected.")
            return False

        in_ms = self.file_manager.get_files(self.params["mzML-files"])
        database = self.file_manager.get_files(self.params["fasta-files"])

        if len(database) != 1:
            self.logger.log("ERROR: Please select exactly one FASTA database.")
            return False

        unsupported = [f for f in in_ms if f.endswith(".raw.mzML")]
        if unsupported:
            self.logger.log(
                "ERROR: .raw.mzML files are not supported: "
                + ", ".join(Path(f).name for f in unsupported)
            )
            return False

        out_idxml = self.file_manager.get_files(
            in_ms,
            set_file_type="idXML",
            set_results_dir="nuxl-search",
        )

        self.logger.log(f"Number of MS input files: {len(in_ms)}")
        self.logger.log(f"FASTA database: {database[0]}")

        xlfdr = self._parse_xlfdr(self.params.get("report:xlFDR", "[0.01, 0.1, 1.0]"))
        xl_peptidelevel_fdr = ["1.0"] * len(xlfdr)

        custom_params = {
            "ThermoRaw_executable": (
                os.path.join(os.getcwd(), "_thirdparty", "ThermoRawFileParser", "ThermoRawFileParser.exe")
                if st.session_state.get("location") == "local"
                else "/thirdparty/ThermoRawFileParser/ThermoRawFileParser.exe"
            ),
            "NuXL:presets": self.params.get("NuXL:presets", "RNA"),
            "NuXL:length": self.params.get("NuXL:length", 4),
            "NuXL:scoring": self.params.get("NuXL:scoring", "precursor"),
            "precursor:mass_tolerance": self.params.get("precursor:mass_tolerance", 10.0),
            "precursor:mass_tolerance_unit": self.params.get("precursor:mass_tolerance_unit", "ppm"),
            "fragment:mass_tolerance": self.params.get("fragment:mass_tolerance", 20.0),
            "fragment:mass_tolerance_unit": self.params.get("fragment:mass_tolerance_unit", "ppm"),
            "peptide:min_size": self.params.get("peptide:min_size", 6),
            "peptide:max_size": self.params.get("peptide:max_size", 40),
            "peptide:missed_cleavages": self.params.get("peptide:missed_cleavages", 2),
            "peptide:enzyme": self.params.get("peptide:enzyme", "Trypsin/P"),
            "modifications:variable_max_per_peptide": self.params.get(
                "modifications:variable_max_per_peptide", 3
            ),
            "report:peptideFDR": self.params.get("report:peptideFDR", 1.0),
            "report:xlFDR": xlfdr,
            "report:xl_peptidelevel_FDR": xl_peptidelevel_fdr,
        }

        variable_mods = self.params.get("modifications:variable", [])
        fixed_mods = self.params.get("modifications:fixed", [])

        if variable_mods:
            custom_params["modifications:variable"] = variable_mods

        if fixed_mods:
            custom_params["modifications:fixed"] = fixed_mods

        if st.session_state.get("location") == "local":
            custom_params["percolator_executable"] = os.path.join(
                os.getcwd(),
                "_thirdparty",
                "Percolator",
                "percolator.exe",
            )

        self.logger.log("Running NuXL search...")

        success = self.executor.run_topp(
            "OpenNuXL",
            input_output={
                "in": in_ms,
                "database": database,
                "out": out_idxml,
            },
            custom_params=custom_params,
        )

        if not success:
            self.logger.log("ERROR: NuXL search failed.")
            return False

        self.logger.log("NuXL search completed successfully.")
        return True

    @st.fragment
    def results(self) -> None:
        result_dir = Path(self.workflow_dir, "results", "nuxl-search")

        if not result_dir.exists():
            st.warning("No NuXL result directory found. Please run the workflow first.")
            return

        files = sorted([p for p in result_dir.iterdir() if p.is_file()])

        if not files:
            st.warning("No NuXL result files found. Please run the workflow first.")
            return

        st.metric("Number of NuXL result files", len(files))

        df = pd.DataFrame(
            {
                "file": [p.name for p in files],
                "size MB": [round(p.stat().st_size / (1024 * 1024), 3) for p in files],
            }
        )

        st.dataframe(df, use_container_width=True)

        self.ui.zip_and_download_files(result_dir)