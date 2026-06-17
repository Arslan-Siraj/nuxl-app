import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.workflow.WorkflowManager import WorkflowManager


class Workflow(WorkflowManager):
    """
    Spectral library generation workflow for NuXL DIA.

    Inputs
    ------
    - One or more mzML/raw files.
    - Corresponding NuXL idXML result files:
        <basename>_perc_0.0100_XLs.idXML
        <basename>_perc_0.0100_peptides.idXML
    - Optional MSFragger TSV library file for iRT alignment.

    External tools/scripts
    ----------------------
    - TextExporter
    - FileInfo
    - src/nuxl2dia.py
    """

    def __init__(self) -> None:
        super().__init__("NuXL DIA Library Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        tabs = st.tabs(["MS data", "NuXL idXML results", "Optional MSFragger library"])

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
                key="idXML-files",
                name="NuXL idXML result files",
                file_types=["idXML"],
                fallback=None,
            )

        with tabs[2]:
            self.ui.upload_widget(
                key="msfragger-library",
                name="MSFragger library",
                file_types=["tsv"],
                fallback=None,
            )

    @st.fragment
    def configure(self) -> None:
        self.ui.select_input_file(
            "mzML-files",
            name="MS data",
            multiple=True,
        )

        self.ui.select_input_file(
            "idXML-files",
            name="NuXL idXML result files",
            multiple=True,
        )

        msfragger_dir = Path(
            self.workflow_dir,
            "input-files",
            "msfragger-library",
        )

        if msfragger_dir.exists() and any(
            f.name != "external_files.txt" for f in msfragger_dir.iterdir()
        ):
            self.ui.select_input_file(
                "msfragger-library",
                name="MSFragger library",
                multiple=False,
            )
        else:
            st.info(
                "Optional: upload an MSFragger .tsv library on the upload page "
                "to enable iRT alignment."
            )

        st.markdown("### Spectral library generation parameters")

        cols = st.columns(2)

        with cols[0]:
            self.ui.input_widget(
                key="library_name",
                default="",
                name="Library output file name tag",
                widget_type="text",
                help=(
                    "Name tag used for the generated library file. "
                    "If empty, a timestamped name is generated automatically."
                ),
            )

        with cols[1]:
            self.ui.input_widget(
                key="irt_calibration_model",
                default="linear",
                name="iRT calibration model",
                widget_type="selectbox",
                options=["linear", "piecewise"],
                help=(
                    "Functional form for iRT calibration. "
                    "Used only when an MSFragger library TSV is provided."
                ),
            )

        self.ui.input_widget(
            key="run_fileinfo",
            default=True,
            name="Run mzML FileInfo",
            widget_type="checkbox",
            help="Run OpenMS FileInfo on each selected mzML/raw file and include the output in the log.",
        )

    def execution(self) -> bool:
        self.params = self.parameter_manager.get_parameters_from_json()

        selected_mzml = self.params.get("mzML-files")
        selected_idxml = self.params.get("idXML-files")

        if not selected_mzml:
            self.logger.log("ERROR: No mzML/raw files selected.")
            return False

        if not selected_idxml:
            self.logger.log("ERROR: No NuXL idXML result files selected.")
            return False

        mzml_files = self.file_manager.get_files(selected_mzml)
        idxml_files = self.file_manager.get_files(selected_idxml)

        if not mzml_files:
            self.logger.log("ERROR: No mzML/raw files resolved.")
            return False

        if not idxml_files:
            self.logger.log("ERROR: No idXML files resolved.")
            return False

        msfragger_library = self._resolve_optional_msfragger_library()

        library_name = str(self.params.get("library_name", "")).strip()
        if not library_name:
            library_name = f"library_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if msfragger_library and library_name == Path(msfragger_library).stem:
            self.logger.log(
                "ERROR: Library output name cannot be identical to the uploaded "
                "MSFragger library file stem."
            )
            return False

        results_dir = Path(self.workflow_dir, "results", "spectral-library")
        if results_dir.exists():
            shutil.rmtree(results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        output_folder = results_dir / library_name
        if output_folder.exists():
            self.logger.log(
                f"ERROR: Library output folder already exists: {output_folder}"
            )
            return False

        output_folder.mkdir(parents=True)

        matched_idxmls, missing_reports = self._match_required_idxml_files(
            mzml_files=mzml_files,
            idxml_files=idxml_files,
        )

        if missing_reports:
            for report in missing_reports:
                self.logger.log(
                    f"ERROR: Missing NuXL results for '{report['mzML']}': "
                    f"{report['missing']}. Please run NuXL first or exclude "
                    "this mzML/raw file."
                )
            return False

        if not matched_idxmls:
            self.logger.log("ERROR: No matching NuXL idXML files found.")
            return False

        self.logger.log(
            "Corresponding idXML files for selected mzML/raw files:\n"
            + "\n".join(f"- {Path(f).name}" for f in matched_idxmls)
        )

        if not self._run_text_exporter(matched_idxmls, output_folder):
            return False

        if self.params.get("run_fileinfo", True):
            if not self._run_fileinfo(mzml_files):
                return False

        copied_msfragger_library = None
        if msfragger_library:
            copied_msfragger_library = output_folder / Path(msfragger_library).name
            shutil.copy(msfragger_library, copied_msfragger_library)
            self.logger.log(
                f"Copied MSFragger library to output folder: {copied_msfragger_library}"
            )

        if not self._run_nuxl2dia(
            output_folder=output_folder,
            library_name=library_name,
            msfragger_library=copied_msfragger_library,
        ):
            return False

        self._write_library_log(
            output_folder=output_folder,
            library_name=library_name,
            mzml_files=mzml_files,
            matched_idxmls=matched_idxmls,
            msfragger_library=msfragger_library,
        )

        self._zip_output_folder(output_folder)

        self.logger.log("Spectral library generation completed successfully.")
        return True

    @st.fragment
    def results(self) -> None:
        result_dir = Path(self.workflow_dir, "results", "spectral-library")

        if not result_dir.exists():
            st.warning("No spectral library results found. Please run the workflow first.")
            return

        files = sorted([p for p in result_dir.rglob("*") if p.is_file()])

        if not files:
            st.warning("No spectral library result files found.")
            return

        st.metric("Number of result files", len(files))

        df = pd.DataFrame(
            {
                "file": [str(p.relative_to(result_dir)) for p in files],
                "size MB": [
                    round(p.stat().st_size / (1024 * 1024), 3)
                    for p in files
                ],
            }
        )

        st.dataframe(df, use_container_width=True)

        zip_files = sorted(result_dir.glob("*.zip"))
        for zip_file in zip_files:
            with open(zip_file, "rb") as handle:
                st.download_button(
                    label=f"⬇️ Download {zip_file.name}",
                    data=handle,
                    file_name=zip_file.name,
                    mime="application/zip",
                    use_container_width=True,
                )

    def _resolve_optional_msfragger_library(self) -> str | None:
        selected = self.params.get("msfragger-library")
        if selected:
            files = self.file_manager.get_files(selected)
            if files:
                return files[0]
        return None

    def _match_required_idxml_files(
        self,
        mzml_files: list[str],
        idxml_files: list[str],
    ) -> tuple[list[str], list[dict[str, str]]]:
        required_suffixes = {
            "_perc_0.0100_XLs.idXML",
            "_perc_0.0100_peptides.idXML",
        }

        idxml_by_name = {Path(f).name: f for f in idxml_files}
        matched_idxmls: list[str] = []
        missing_reports: list[dict[str, str]] = []

        for mzml_file in mzml_files:
            basename = Path(mzml_file).stem
            expected = {basename + suffix for suffix in required_suffixes}
            found = {
                name
                for name in idxml_by_name
                if name.startswith(basename)
                and any(name.endswith(suffix) for suffix in required_suffixes)
            }

            if found != expected:
                missing = expected - found
                missing_reports.append(
                    {
                        "mzML": basename,
                        "missing": ", ".join(sorted(missing)),
                    }
                )
            else:
                matched_idxmls.extend(
                    idxml_by_name[name]
                    for name in sorted(found)
                )

        return matched_idxmls, missing_reports

    def _run_text_exporter(
        self,
        idxml_files: list[str],
        output_folder: Path,
    ) -> bool:
        self.logger.log("Exporting idXML files to TextExporter format...")

        for idxml_file in idxml_files:
            idxml_path = Path(idxml_file)
            unknown_path = output_folder / f"{idxml_path.stem}.unknown"

            command = [
                self._tool_name("TextExporter"),
                "-in",
                str(idxml_path),
                "-out",
                str(unknown_path),
                "-id:peptides_only",
                "-id:add_hit_metavalues",
                "0",
            ]

            self.logger.log(f"Processing idXML file: {idxml_path.name}")
            if not self.executor.run_command(command):
                self.logger.log(f"ERROR: TextExporter failed for {idxml_path}")
                return False

        return True

    def _run_fileinfo(self, mzml_files: list[str]) -> bool:
        self.logger.log("Running mzML/raw FileInfo...")

        for mzml_file in mzml_files:
            command = [
                self._tool_name("FileInfo"),
                "-in",
                str(mzml_file),
            ]

            self.logger.log(f"Processing MS file with FileInfo: {Path(mzml_file).name}")
            if not self.executor.run_command(command):
                self.logger.log(f"ERROR: FileInfo failed for {mzml_file}")
                return False

        return True

    def _run_nuxl2dia(
        self,
        output_folder: Path,
        library_name: str,
        msfragger_library: Path | None,
    ) -> bool:
        self.logger.log("Generating spectral library with nuxl2dia.py...")

        nuxl2dia_script = Path("src", "nuxl2dia.py").resolve()
        if not nuxl2dia_script.exists():
            self.logger.log(
                f"ERROR: nuxl2dia.py not found at {nuxl2dia_script}. "
                "Place it at project-root/src/nuxl2dia.py."
            )
            return False

        output_tsv = output_folder / f"{library_name}.tsv"

        if msfragger_library:
            unknown_files = sorted(output_folder.glob("*.unknown"))
            if not unknown_files:
                self.logger.log("ERROR: Required .unknown files not found.")
                return False

            command = [
                sys.executable,
                str(nuxl2dia_script),
                "-i",
                *[str(p) for p in unknown_files],
                "-o",
                str(output_tsv),
                "--irt",
                str(self.params.get("irt_calibration_model", "linear")),
                "--irt-ref",
                str(msfragger_library),
                "-v",
            ]

        else:
            unknown_xls = sorted(output_folder.glob("*_XLs.unknown"))
            unknown_peptides = sorted(output_folder.glob("*_peptides.unknown"))

            if not unknown_xls or not unknown_peptides:
                self.logger.log(
                    "ERROR: Required *_XLs.unknown and *_peptides.unknown "
                    "files were not found."
                )
                return False

            command = [
                sys.executable,
                str(nuxl2dia_script),
                "-i",
                *[str(p) for p in unknown_xls],
                *[str(p) for p in unknown_peptides],
                "-o",
                str(output_tsv),
                "-v",
            ]

        return self.executor.run_command(command)

    def _write_library_log(
        self,
        output_folder: Path,
        library_name: str,
        mzml_files: list[str],
        matched_idxmls: list[str],
        msfragger_library: str | None,
    ) -> None:
        log_file = output_folder / f"{library_name}_library_generation.log"

        settings = st.session_state.get("settings", {})
        openms_version = settings.get("openms-version", "unknown")
        app_version = settings.get("version", "unknown")

        with open(log_file, "w", encoding="utf-8") as handle:
            handle.write("===== version info =====\n")
            handle.write(f"OpenMS version: {openms_version}\n")
            handle.write(f"NuXLApp version: {app_version}\n\n")

            handle.write("===== selected mzML/raw files =====\n")
            for file in mzml_files:
                handle.write(f"{file}\n")

            handle.write("\n===== matched idXML files =====\n")
            for file in matched_idxmls:
                handle.write(f"{file}\n")

            handle.write("\n===== parameters =====\n")
            handle.write(f"Library name: {library_name}\n")
            handle.write(
                f"MSFragger iRT reference: {msfragger_library or 'None'}\n"
            )
            handle.write(
                "iRT calibration model: "
                f"{self.params.get('irt_calibration_model', 'linear')}\n"
            )

    def _zip_output_folder(self, output_folder: Path) -> Path:
        zip_path = output_folder.parent / f"{output_folder.name}_library_out_files.zip"

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
            for file in output_folder.rglob("*"):
                if file.is_file():
                    zip_handle.write(file, file.relative_to(output_folder.parent))

        self.logger.log(f"Created ZIP archive: {zip_path}")
        return zip_path

    def _tool_name(self, executable: str) -> str:
        local_path = Path.cwd() / executable
        if os.name == "nt" and local_path.exists():
            return str(local_path)
        return executable
