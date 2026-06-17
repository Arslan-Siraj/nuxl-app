import ast
import os
import shutil
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.workflow.WorkflowManager import WorkflowManager


NUXL_SECTIONS = [
    "fixed",
    "variable",
    "presets",
    "enzyme",
    "scoring",
    "variable_max_per_peptide",
    "length",
    "mass_tolerance",
    "mass_tolerance_unit",
    "min_size",
    "max_size",
    "missed_cleavages",
    "peptideFDR",
    "xlFDR",
    "min_charge",
    "max_charge",
]


def ini2dict(path: str | Path, sections: list[str]) -> dict[str, dict[str, Any]]:
    """
    Read selected OpenMS/NuXL ParamXML sections into a dictionary used to build
    Streamlit parameter widgets.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    config_dict: dict[str, dict[str, Any]] = {}

    precursor_mass_tolerance = {}
    fragment_mass_tolerance = {}
    precursor_mass_tolerance_unit = {}
    fragment_mass_tolerance_unit = {}

    for section_name in sections:
        matched_nodes = (
            root.findall(f".//ITEMLIST[@name='{section_name}']")
            or root.findall(f".//ITEM[@name='{section_name}']")
        )

        entry: dict[str, Any] = {
            "name": section_name,
            "default": "",
            "description": "",
            "restrictions": [],
        }

        for node in matched_nodes:
            node_name = str(node.get("name") or "")
            node_default = str(node.get("value") or "")
            node_desc = str(node.get("description") or "")
            node_rest = str(node.get("restrictions") or "")

            restrictions_list = [
                item.strip()
                for item in node_rest.split(",")
                if item and item.strip()
            ]

            entry = {
                "name": node_name,
                "default": node_default,
                "description": node_desc,
                "restrictions": restrictions_list,
            }

            if "Precursor mass tolerance" in node_desc:
                entry["name"] = "precursor_mass_tolerance"
                precursor_mass_tolerance = entry

            if "Fragment mass tolerance" in node_desc:
                entry["name"] = "fragment_mass_tolerance"
                fragment_mass_tolerance = entry

            if "Unit of precursor mass tolerance" in node_desc:
                entry["name"] = "precursor_mass_tolerance_unit"
                precursor_mass_tolerance_unit = entry

            if "Unit of fragment mass tolerance" in node_desc:
                entry["name"] = "fragment_mass_tolerance_unit"
                fragment_mass_tolerance_unit = entry

        config_dict[section_name] = entry

        if section_name == "mass_tolerance":
            config_dict["precursor_mass_tolerance"] = precursor_mass_tolerance
            config_dict["fragment_mass_tolerance"] = fragment_mass_tolerance

        if section_name == "mass_tolerance_unit":
            config_dict["precursor_mass_tolerance_unit"] = precursor_mass_tolerance_unit
            config_dict["fragment_mass_tolerance_unit"] = fragment_mass_tolerance_unit

    return config_dict


class Workflow(WorkflowManager):
    """
    NuXL workflow for one mzML/raw input file and one FASTA database.
    """

    def __init__(self) -> None:
        super().__init__("NuXL Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        tabs = st.tabs(["MS data", "FASTA database"])

        with tabs[0]:
            self.ui.upload_widget(
                key="mzML-files",
                name="MS data",
                file_types=["mzML", "raw"],
                fallback=[
                    str(f)
                    for f in Path("example-data", "mzML").glob("*.mzML")
                ],
            )

        with tabs[1]:
            self.ui.upload_widget(
                key="fasta-files",
                name="FASTA database",
                file_types=["fasta", "fa"],
                fallback=[
                    str(f)
                    for f in Path("example-data", "fasta").glob("*.fasta")
                ],
            )

    @st.fragment
    def configure(self) -> None:
        self.ui.select_input_file(
            "mzML-files",
            name="MS data",
            multiple=False,
        )

        self.ui.select_input_file(
            "fasta-files",
            name="FASTA database",
            multiple=False,
        )

        config_path = Path("assets", "OpenMS_NuXL.ini")
        if not config_path.exists():
            st.error(f"NuXL configuration file not found: `{config_path}`")
            return

        nuxl_config = ini2dict(config_path, NUXL_SECTIONS)

        if "Trypsin/P" in nuxl_config["enzyme"]["restrictions"]:
            nuxl_config["enzyme"]["restrictions"].remove("Trypsin/P")
            nuxl_config["enzyme"]["restrictions"].insert(0, "Trypsin/P")

        st.markdown("### NuXL search parameters")

        # Row 1: enzyme + missed cleavages | peptide min + peptide max
        cols = st.columns(2)

        with cols[0]:
            inner = st.columns(2)

            with inner[0]:
                self._nuxl_select(
                    nuxl_config,
                    key="peptide:enzyme",
                    config_key="enzyme",
                    label="enzyme",
                )

            with inner[1]:
                self._nuxl_number(
                    nuxl_config,
                    key="peptide:missed_cleavages",
                    config_key="missed_cleavages",
                    label="missed cleavages",
                    min_value=0,
                    max_value=20,
                )

        with cols[1]:
            inner = st.columns(2)

            with inner[0]:
                self._nuxl_number(
                    nuxl_config,
                    key="peptide:min_size",
                    config_key="min_size",
                    label="peptide min length",
                    min_value=1,
                    max_value=100,
                )

            with inner[1]:
                self._nuxl_number(
                    nuxl_config,
                    key="peptide:max_size",
                    config_key="max_size",
                    label="peptide max length",
                    min_value=3,
                    max_value=1_000_000,
                )

        # Row 2: precursor tolerance + unit | fragment tolerance + unit
        cols = st.columns(2)

        with cols[0]:
            inner = st.columns(2)

            with inner[0]:
                self._nuxl_number(
                    nuxl_config,
                    key="precursor:mass_tolerance",
                    config_key="precursor_mass_tolerance",
                    label="precursor mass tolerance",
                    min_value=0.0,
                    step_size=1.0,
                )

            with inner[1]:
                self._nuxl_select(
                    nuxl_config,
                    key="precursor:mass_tolerance_unit",
                    config_key="precursor_mass_tolerance_unit",
                    label="precursor mass tolerance unit",
                )

        with cols[1]:
            inner = st.columns(2)

            with inner[0]:
                self._nuxl_number(
                    nuxl_config,
                    key="fragment:mass_tolerance",
                    config_key="fragment_mass_tolerance",
                    label="fragment mass tolerance",
                    min_value=0.0,
                    step_size=1.0,
                )

            with inner[1]:
                self._nuxl_select(
                    nuxl_config,
                    key="fragment:mass_tolerance_unit",
                    config_key="fragment_mass_tolerance_unit",
                    label="fragment mass tolerance unit",
                )

        # Row 3: preset | length
        cols = st.columns(2)

        with cols[0]:
            self._nuxl_select(
                nuxl_config,
                key="NuXL:presets",
                config_key="presets",
                label="select the suitable preset",
            )

        with cols[1]:
            self._nuxl_number(
                nuxl_config,
                key="NuXL:length",
                config_key="length",
                label="length of oligonucleotide",
                min_value=0,
            )

        # Row 4: fixed modifications | variable modifications
        cols = st.columns(2)

        with cols[0]:
            self._nuxl_multiselect(
                nuxl_config,
                key="modifications:fixed",
                config_key="fixed",
                label="select fixed modifications:",
                default=[],
            )

        with cols[1]:
            self._nuxl_multiselect(
                nuxl_config,
                key="modifications:variable",
                config_key="variable",
                label="select variable modifications:",
                default=["Oxidation (M)"],
            )

        # Row 5: variable max per peptide | scoring
        cols = st.columns(2)

        with cols[0]:
            self._nuxl_number(
                nuxl_config,
                key="modifications:variable_max_per_peptide",
                config_key="variable_max_per_peptide",
                label="variable modification max per peptide",
                min_value=0,
            )

        with cols[1]:
            self._nuxl_select(
                nuxl_config,
                key="NuXL:scoring",
                config_key="scoring",
                label="scoring method",
            )

        with st.expander("**Advanced parameters**"):
            cols = st.columns(2)

            with cols[0]:
                inner = st.columns(2)

                with inner[0]:
                    self._nuxl_number(
                        nuxl_config,
                        key="precursor:min_charge",
                        config_key="min_charge",
                        label="precursor min charge",
                        min_value=1,
                        max_value=10,
                    )

                with inner[1]:
                    self._nuxl_number(
                        nuxl_config,
                        key="precursor:max_charge",
                        config_key="max_charge",
                        label="precursor max charge",
                        min_value=1,
                        max_value=10,
                    )

            with cols[1]:
                inner = st.columns(2)

                with inner[0]:
                    self._nuxl_number(
                        nuxl_config,
                        key="report:peptideFDR",
                        config_key="peptideFDR",
                        label="peptide FDR",
                        min_value=0.0,
                        max_value=1.0,
                        step_size=0.01,
                    )

                with inner[1]:
                    self.ui.input_widget(
                        "report:xlFDR",
                        default="[0.01, 0.1, 1.0]",
                        name="XL FDR",
                        widget_type="textarea",
                        help=(
                            nuxl_config["xlFDR"]["description"]
                            + " Use either a single float, e.g. 0.01, "
                            + "or a list, e.g. [0.01, 0.1, 1.0]."
                        ),
                    )

    def execution(self) -> bool:
        # Reload parameters from params.json so local multiprocessing and queue
        # execution both use the latest values saved by the Streamlit widgets.
        self.params = self.parameter_manager.get_parameters_from_json()

        if not self.params.get("mzML-files"):
            self.logger.log("ERROR: No mzML/raw file selected.")
            return False

        if not self.params.get("fasta-files"):
            self.logger.log("ERROR: No FASTA database selected.")
            return False

        in_ms = self.file_manager.get_files(self.params["mzML-files"])
        database = self.file_manager.get_files(self.params["fasta-files"])

        if len(in_ms) != 1:
            self.logger.log("ERROR: NuXL expects exactly one mzML/raw file.")
            return False

        if len(database) != 1:
            self.logger.log("ERROR: Please select exactly one FASTA database.")
            return False

        if in_ms[0].endswith(".raw.mzML"):
            self.logger.log(
                "ERROR: .raw.mzML files are not supported. "
                "Please select .raw or .mzML."
            )
            return False

        out_idxml = self.file_manager.get_files(
            in_ms,
            set_file_type="idXML",
            set_results_dir="nuxl-search",
        )

        result_dir = Path(out_idxml[0]).parent
        protocol_name = Path(in_ms[0]).stem

        self.logger.log(f"MS input file: {in_ms[0]}")
        self.logger.log(f"FASTA database: {database[0]}")
        self.logger.log(f"NuXL output file: {out_idxml[0]}")

        try:
            xlfdr = self._parse_xlfdr(self.params.get("report:xlFDR", "[0.01, 0.1, 1.0]"))
        except ValueError as exc:
            self.logger.log(f"ERROR: Invalid XL FDR parameter: {exc}")
            return False

        xl_peptidelevel_fdr = ["1.0"] * len(xlfdr)

        thermo_executable = self._thermo_raw_file_parser_path()
        percolator_executable = self._percolator_path()

        custom_params: dict[str, Any] = {
            "ThermoRaw_executable": thermo_executable,
            "NuXL:presets": self.params.get("NuXL:presets"),
            "NuXL:length": self.params.get("NuXL:length"),
            "NuXL:scoring": self.params.get("NuXL:scoring"),
            "precursor:mass_tolerance": self.params.get("precursor:mass_tolerance"),
            "precursor:mass_tolerance_unit": self.params.get("precursor:mass_tolerance_unit"),
            "fragment:mass_tolerance": self.params.get("fragment:mass_tolerance"),
            "fragment:mass_tolerance_unit": self.params.get("fragment:mass_tolerance_unit"),
            "peptide:min_size": self.params.get("peptide:min_size"),
            "peptide:max_size": self.params.get("peptide:max_size"),
            "peptide:missed_cleavages": self.params.get("peptide:missed_cleavages"),
            "peptide:enzyme": self.params.get("peptide:enzyme"),
            "modifications:variable_max_per_peptide": self.params.get(
                "modifications:variable_max_per_peptide"
            ),
            "report:peptideFDR": self.params.get("report:peptideFDR"),
            "report:xlFDR": xlfdr,
            "report:xl_peptidelevel_FDR": xl_peptidelevel_fdr,
        }

        if percolator_executable:
            custom_params["percolator_executable"] = percolator_executable

        variable_mods = self.params.get("modifications:variable", [])
        fixed_mods = self.params.get("modifications:fixed", [])

        if variable_mods:
            custom_params["modifications:variable"] = variable_mods

        if fixed_mods:
            custom_params["modifications:fixed"] = fixed_mods

        # Remove parameters that were not captured for any reason.
        custom_params = {
            key: value
            for key, value in custom_params.items()
            if value is not None and value != ""
        }

        self.logger.log("Running OpenNuXL...")

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
            self._write_search_parameter_log(
                result_dir=result_dir,
                protocol_name=protocol_name,
                mzml_file=in_ms[0],
                database_file=database[0],
                success=False,
            )
            return False

        self._move_ambiguous_mass_file_to_results(
            protocol_name=protocol_name,
            input_file=in_ms[0],
            result_dir=result_dir,
        )

        self._write_search_parameter_log(
            result_dir=result_dir,
            protocol_name=protocol_name,
            mzml_file=in_ms[0],
            database_file=database[0],
            success=True,
        )

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
                "size MB": [
                    round(p.stat().st_size / (1024 * 1024), 3)
                    for p in files
                ],
            }
        )

        selection = st.dataframe(
            df,
            selection_mode="multi-row",
            on_select="rerun",
            use_container_width=True,
            key="nuxl-result-table",
        )

        selected_rows = selection["selection"]["rows"]
        if selected_rows:
            selected_files = [files[i] for i in selected_rows]
            st.info(
                "Selected files:\n\n"
                + "\n\n".join(file.name for file in selected_files)
            )

        self.ui.zip_and_download_files(result_dir)

    def _clean_options(self, options: list[str]) -> list[str]:
        return [
            option.strip()
            for option in options
            if option and option.strip() not in {"None", "none", "nan"}
        ]

    def _as_number(self, value: Any) -> int | float | str:
        try:
            value = str(value)
            if "." in value:
                return float(value)
            return int(value)
        except Exception:
            return value

    def _nuxl_select(self, config, key, config_key, label) -> None:
        entry = config[config_key]
        options = self._clean_options(entry["restrictions"])

        if not options:
            self.ui.input_widget(
                key=key,
                default=entry["default"],
                name=label,
                help=entry["description"],
                widget_type="text",
            )
            return

        default = entry["default"]
        if default not in options:
            default = options[0]

        self.ui.input_widget(
            key=key,
            default=default,
            name=label,
            help=entry["description"],
            widget_type="selectbox",
            options=options,
        )

    def _nuxl_number(
        self,
        config,
        key,
        config_key,
        label,
        min_value=None,
        max_value=None,
        step_size=1,
    ) -> None:
        entry = config[config_key]
        default = self._as_number(entry["default"])

        self.ui.input_widget(
            key=key,
            default=default,
            name=label,
            help=entry["description"],
            widget_type="number",
            min_value=min_value,
            max_value=max_value,
            step_size=step_size,
        )

    def _nuxl_multiselect(
        self,
        config,
        key,
        config_key,
        label,
        default,
    ) -> None:
        entry = config[config_key]
        options = self._clean_options(entry["restrictions"])

        self.ui.input_widget(
            key=key,
            default=default,
            name=label,
            help=entry["description"],
            widget_type="multiselect",
            options=options,
        )

    def _parse_xlfdr(self, value: Any) -> list[str]:
        try:
            parsed = ast.literal_eval(str(value))
        except Exception as exc:
            raise ValueError(
                "Use either a single number, e.g. 0.01, "
                "or a list, e.g. [0.01, 0.1, 1.0]."
            ) from exc

        if isinstance(parsed, (int, float)):
            parsed = [parsed]

        if not isinstance(parsed, list):
            raise ValueError("XL FDR must be a number or a list of numbers.")

        if not all(isinstance(v, (int, float)) for v in parsed):
            raise ValueError("All XL FDR values must be numeric.")

        if not all(0.0 <= float(v) <= 1.0 for v in parsed):
            raise ValueError("All XL FDR values must be between 0.0 and 1.0.")

        return [str(v) for v in parsed]

    def _thermo_raw_file_parser_path(self) -> str:
        local_path = Path.cwd() / "_thirdparty" / "ThermoRawFileParser" / "ThermoRawFileParser.exe"
        docker_path = Path("/thirdparty/ThermoRawFileParser/ThermoRawFileParser.exe")

        if local_path.exists():
            return str(local_path)

        if docker_path.exists():
            return str(docker_path)

        # Keep the Docker path as default because this is what the deployed NuXLApp uses.
        return str(docker_path)

    def _percolator_path(self) -> str | None:
        local_path = Path.cwd() / "_thirdparty" / "Percolator" / "percolator.exe"

        if local_path.exists():
            return str(local_path)

        return None

    def _move_ambiguous_mass_file_to_results(
        self,
        protocol_name: str,
        input_file: str,
        result_dir: Path,
    ) -> None:
        """
        OpenNuXL may write an ambiguous-masses CSV next to the mzML file.
        Move it into the workflow result directory when present.
        """
        input_dir = Path(input_file).parent

        candidates = [
            input_dir / f"{protocol_name}.mzML.ambigious_masses.csv",
            input_dir / f"{protocol_name}.mzML.ambiguous_masses.csv",
            input_dir / f"{protocol_name}.ambigious_masses.csv",
            input_dir / f"{protocol_name}.ambiguous_masses.csv",
        ]

        for candidate in candidates:
            if candidate.exists():
                target = result_dir / candidate.name
                shutil.move(str(candidate), str(target))
                self.logger.log(f"Moved ambiguous masses file to results: {target}")
                return

    def _write_search_parameter_log(
        self,
        result_dir: Path,
        protocol_name: str,
        mzml_file: str,
        database_file: str,
        success: bool,
    ) -> None:
        time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = result_dir / f"{protocol_name}_nuxl_search_parameters_{time_stamp}.txt"

        try:
            openms_version = st.session_state.get("settings", {}).get("openms-version", "unknown")
            app_version = st.session_state.get("settings", {}).get("version", "unknown")
        except Exception:
            openms_version = "unknown"
            app_version = "unknown"

        search_param = textwrap.dedent(
            f"""\
            ======= versions ==========
            OpenMS version: {openms_version}
            NuXLApp version: {app_version}

            ======= Search Parameters ==========
            Selected mzML/raw File: {mzml_file}
            Selected FASTA File: {database_file}

            Enzyme: {self.params.get("peptide:enzyme")}
            Missed Cleavages: {self.params.get("peptide:missed_cleavages")}
            Peptide Min Length: {self.params.get("peptide:min_size")}
            Peptide Max Length: {self.params.get("peptide:max_size")}

            Precursor Mass Tolerance: {self.params.get("precursor:mass_tolerance")} {self.params.get("precursor:mass_tolerance_unit")}
            Precursor Min Charge: {self.params.get("precursor:min_charge")}
            Precursor Max Charge: {self.params.get("precursor:max_charge")}

            Fragment Mass Tolerance: {self.params.get("fragment:mass_tolerance")} {self.params.get("fragment:mass_tolerance_unit")}

            Preset: {self.params.get("NuXL:presets")}
            Oligonucleotide Length: {self.params.get("NuXL:length")}
            Scoring Method: {self.params.get("NuXL:scoring")}

            Fixed Modifications: {", ".join(self.params.get("modifications:fixed", [])) or "None"}
            Variable Modifications: {", ".join(self.params.get("modifications:variable", [])) or "None"}
            Variable Max Modifications per Peptide: {self.params.get("modifications:variable_max_per_peptide")}

            Peptide FDR: {self.params.get("report:peptideFDR")}
            XL FDR: {self.params.get("report:xlFDR")}

            Workflow success: {success}
            """
        )

        with open(log_file_path, "w", encoding="utf-8") as handle:
            handle.write(search_param)

        self.logger.log(f"Wrote NuXL parameter log: {log_file_path}")
