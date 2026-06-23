import json
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


REQUIRED_IDXML_SUFFIXES = {
    "_perc_0.0100_XLs.idXML",
    "_perc_0.0100_peptides.idXML",
}

EXCLUDED_IDXML_MARKERS = [
    "RT_feat",
    "RT_Int_feat",
    "updated_feat",
    "_sse_perc_",
    "_perc.idXML",
]


class Workflow(WorkflowManager):
    """
    NuXL DIA spectral-library generation workflow.

    This workflow follows the same global-workspace style used by the NuXL
    workflow:

    - mzML/raw files are synced from <workspace>/mzML-files
    - only NuXL idXML result files containing _perc_0.0100 are synced from <workspace>/result-files
    - optional MSFragger TSV files can be uploaded directly on this workflow Upload page
    - generated library output files are copied directly to <workspace>/result-files
    - after successful execution, a ZIP download button appears at the bottom
      of the execution page.
    """

    def __init__(self) -> None:
        super().__init__("NuXL DIA Library Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        st.info(
            "Click **Sync files from workspace** "
            "to make the current workspace files available for this workflow."
        )

        if st.button("Sync files from workspace", type="primary"):
            self._sync_global_input_files()
            st.success("mzML/raw and NuXL idXML files synced into workflow input folders.")
            st.rerun()

        self._show_synced_files(
            "mzML-files",
            "MS files",
            help_text=(
                "Available `.mzML` files in workspace. "
                "Select the MS files later in the Configure tab for libray generation. "
            ),
        )

        self._show_synced_files(
            "idXML-files",
            "idXML files",
            help_text=(
                "Available idXML files in workspace. "
                "Only NuXL Percolator out 1% idXML files containing `_perc_0.0100` are shown. "
                "For each selected MS file, the workflow automatically expects the matching "
                "`_perc_0.0100_XLs.idXML` and `_perc_0.0100_peptides.idXML` files."
            ),
        )

        st.divider()
        st.markdown("##### Optional MSFragger TSV library for iRT alignment")
        st.caption(
            "Optional. Upload an MSFragger `.tsv` library for the iRT reference for alignment. If no TSV is selected, DIA library "
            "generation still runs without iRT reference alignment."
        )

        self._upload_optional_msfragger_tsv()

        self._show_synced_files(
            "msfragger-library",
            "MSFragger library files",
            help_text=(
                "Uploaded `.tsv` files available for optional iRT alignment. "
                "Choose one later in the Configure tab, or choose `None` to skip iRT alignment."
            ),
        )

    def _upload_optional_msfragger_tsv(self) -> None:
        target_dir = Path(self.workflow_dir, "input-files", "msfragger-library")
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = st.file_uploader(
            "Upload optional MSFragger library TSV file",
            type=["tsv"],
            accept_multiple_files=True,
            help=(
                "Optional. Upload a library TSV only if you want to use it as "
                "the iRT reference for DIA library generation."
            ),
            key="dia-msfragger-library-tsv-upload",
        )

        if uploaded_files:
            saved_files = []

            for uploaded_file in uploaded_files:
                target_file = target_dir / uploaded_file.name
                with open(target_file, "wb") as handle:
                    handle.write(uploaded_file.getbuffer())
                saved_files.append(uploaded_file.name)

            st.success(
                "Uploaded optional MSFragger TSV file(s): "
                + ", ".join(saved_files)
            )

        existing_tsv_files = [
            file
            for file in sorted(target_dir.iterdir())
            if file.is_file()
            and file.name != "external_files.txt"
            and file.suffix.lower() == ".tsv"
        ]

        if existing_tsv_files:
            if st.button(
                "Clear optional MSFragger TSV files",
                type="secondary",
                key="clear-dia-msfragger-tsv-files",
            ):
                for file in existing_tsv_files:
                    file.unlink()
                st.success("Optional MSFragger TSV files cleared.")
                st.rerun()

    def _sync_global_input_files(self) -> None:
        self._copy_global_folder_to_workflow_input(
            global_folder_name="mzML-files",
            workflow_key="mzML-files",
            allowed_suffixes={".mzml"},
        )

        self._copy_global_folder_to_workflow_input(
            global_folder_name="result-files",
            workflow_key="idXML-files",
            allowed_suffixes={".idxml"},
            file_filter=self._is_valid_library_idxml_name,
        )

    def _copy_global_folder_to_workflow_input(
        self,
        global_folder_name: str,
        workflow_key: str,
        allowed_suffixes: set[str],
        file_filter: Any | None = None,
    ) -> None:
        workspace_dir = Path(self.workflow_dir).parent
        source_dir = workspace_dir / global_folder_name
        target_dir = Path(self.workflow_dir, "input-files", workflow_key)

        source_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        for old_file in target_dir.iterdir():
            if old_file.is_file():
                old_file.unlink()

        for source_file in sorted(source_dir.iterdir()):
            if not source_file.is_file():
                continue

            if source_file.name == "external_files.txt":
                continue

            if source_file.suffix.lower() not in allowed_suffixes:
                continue

            if file_filter is not None and not file_filter(source_file.name):
                continue

            shutil.copy2(source_file, target_dir / source_file.name)

        external_file = source_dir / "external_files.txt"
        if external_file.exists():
            target_external_file = target_dir / "external_files.txt"
            lines_to_keep: list[str] = []

            for line in external_file.read_text(encoding="utf-8").splitlines():
                path = Path(line.strip())
                if not path.exists():
                    continue

                if path.suffix.lower() not in allowed_suffixes:
                    continue

                if file_filter is not None and not file_filter(path.name):
                    continue

                lines_to_keep.append(str(path))

            if lines_to_keep:
                target_external_file.write_text(
                    "\n".join(lines_to_keep) + "\n",
                    encoding="utf-8",
                )

    def _show_synced_files(
        self,
        workflow_key: str,
        title: str,
        help_text: str | None = None,
    ) -> None:
        input_dir = Path(self.workflow_dir, "input-files", workflow_key)

        st.markdown(f"##### {title}")

        if help_text:
            st.caption(help_text)

        if not input_dir.exists():
            st.warning("No files available yet.")
            return

        files = [
            f.name
            for f in sorted(input_dir.iterdir())
            if f.is_file() and f.name != "external_files.txt"
        ]

        external_files = input_dir / "external_files.txt"
        if external_files.exists():
            files.extend(
                line.strip()
                for line in external_files.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )

        if not files:
            st.warning("No files available yet.")
            return

        st.dataframe(pd.DataFrame({"file": files}), use_container_width=True)

    @st.fragment
    def configure(self) -> None:
        self.ui.select_input_file(
            "mzML-files",
            name="MS data",
            multiple=True,
        )

        idxml_files = self._available_input_files(
            key="idXML-files",
            allowed_suffixes={".idxml"},
        )

        if not idxml_files:
            st.error(
                "No NuXL idXML result files are synced yet. Go to the Upload tab "
                "and click **Sync files from global workspace** after running NuXL."
            )
        else:
            st.info(
                f"{len(idxml_files)} NuXL idXML file(s) are available. "
                "They will be matched automatically to the selected mzML/raw files."
            )

        msfragger_files = self._available_input_files(
            key="msfragger-library",
            allowed_suffixes={".tsv"},
        )

        if msfragger_files:
            options = ["None"] + [str(p) for p in msfragger_files]
            self.ui.input_widget(
                key="msfragger-library",
                default="None",
                name="Optional MSFragger library TSV for iRT alignment",
                widget_type="selectbox",
                options=options,
                help="Choose None to skip iRT alignment.",
            )
        else:
            st.info(
                "Optional: place an MSFragger .tsv library in global result-files, "
                "then sync again to enable iRT alignment."
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
                    "Used only when an MSFragger library TSV is selected."
                ),
            )

        self.ui.input_widget(
            key="run_fileinfo",
            default=True,
            name="Run mzML FileInfo",
            widget_type="checkbox",
            help="Run OpenMS FileInfo on each selected mzML/raw file and include output in the workflow log.",
        )

    def show_execution_section(self) -> None:
        self.ui.execution_section(
            start_workflow_function=self.start_workflow,
            get_status_function=self.get_workflow_status,
            stop_workflow_function=self.stop_workflow,
        )
        self._render_latest_success_download()

    def execution(self) -> bool:
        self.params = self.parameter_manager.get_parameters_from_json()

        # Refresh idXML/mzML/TSV files from the global workspace when the job starts.
        # This keeps the workflow aligned with files produced by NuXL immediately before DIA.
        self._sync_global_input_files()

        selected_mzml = self.params.get("mzML-files")

        if not selected_mzml:
            self.logger.log("ERROR: No mzML/raw files selected.")
            return False

        mzml_files = [
            file
            for file in self.file_manager.get_files(selected_mzml)
            if Path(file).suffix.lower() in {".mzml", ".raw"}
        ]
        idxml_files = [str(p) for p in self._available_input_files("idXML-files", {".idxml"})]

        if not mzml_files:
            self.logger.log("ERROR: No mzML/raw files resolved.")
            return False

        if not idxml_files:
            self.logger.log(
                "ERROR: No NuXL idXML result files were found. Run NuXL first, "
                "then sync/run the DIA library workflow."
            )
            return False

        msfragger_library = self._resolve_optional_msfragger_library()

        library_name = str(self.params.get("library_name", "")).strip()
        if not library_name:
            library_name = f"library_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if msfragger_library and library_name == Path(msfragger_library).stem:
            self.logger.log(
                "ERROR: Library output name cannot be identical to the selected "
                "MSFragger library file stem."
            )
            return False

        result_dir = Path(self.workflow_dir, "results", "spectral-library")
        if result_dir.exists():
            shutil.rmtree(result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)

        output_folder = result_dir / library_name
        output_folder.mkdir(parents=True, exist_ok=True)

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
            shutil.copy2(msfragger_library, copied_msfragger_library)
            self.logger.log(
                f"Copied MSFragger library to output folder: {copied_msfragger_library}"
            )

        if not self._run_nuxl2dia(
            output_folder=output_folder,
            library_name=library_name,
            msfragger_library=copied_msfragger_library,
        ):
            return False

        log_file_path = self._write_library_log(
            output_folder=output_folder,
            library_name=library_name,
            mzml_files=mzml_files,
            matched_idxmls=matched_idxmls,
            msfragger_library=msfragger_library,
        )

        exclude_files = set()
        if copied_msfragger_library is not None:
            exclude_files.add(copied_msfragger_library.resolve())

        zip_path = self._zip_output_folder(output_folder, exclude_files=exclude_files)

        global_output_dir, global_zip_path = self._copy_library_outputs_to_global_result_files(
            output_folder=output_folder,
            zip_path=zip_path,
            exclude_files=exclude_files,
        )

        self._write_latest_download_state(
            library_name=library_name,
            output_folder=output_folder,
            zip_path=zip_path,
            global_output_dir=global_output_dir,
            global_zip_path=global_zip_path,
            log_file_path=log_file_path,
        )

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
                "size MB": [round(p.stat().st_size / (1024 * 1024), 3) for p in files],
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

    def _available_input_files(
        self,
        key: str,
        allowed_suffixes: set[str],
    ) -> list[Path]:
        input_dir = Path(self.workflow_dir, "input-files", key)
        files: list[Path] = []

        if input_dir.exists():
            files.extend(
                p
                for p in sorted(input_dir.iterdir())
                if p.is_file()
                and p.name != "external_files.txt"
                and p.suffix.lower() in allowed_suffixes
            )

            external_files = input_dir / "external_files.txt"
            if external_files.exists():
                for line in external_files.read_text(encoding="utf-8").splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() in allowed_suffixes:
                        files.append(path)

        return files

    def _is_valid_library_idxml_name(self, file_name: str) -> bool:
        if not file_name.endswith(".idXML") and not file_name.endswith(".idxml"):
            return False

        # For DIA library generation we only need the 1% Percolator outputs:
        #   <basename>_perc_0.0100_XLs.idXML
        #   <basename>_perc_0.0100_peptides.idXML
        # Hide/sync no 0.1000, 1.0000, non-percolator, feature, or old perc files.
        if "_perc_0.0100" not in file_name:
            return False

        if any(marker in file_name for marker in EXCLUDED_IDXML_MARKERS):
            return False

        return True

    def _resolve_optional_msfragger_library(self) -> str | None:
        selected = self.params.get("msfragger-library")

        if not selected or selected == "None":
            return None

        selected_path = Path(str(selected))
        if selected_path.exists():
            return str(selected_path)

        # Fallback for manually edited params: match by file name in synced TSV files.
        for file in self._available_input_files("msfragger-library", {".tsv"}):
            if file.name == str(selected):
                return str(file)

        return None

    def _match_required_idxml_files(
        self,
        mzml_files: list[str],
        idxml_files: list[str],
    ) -> tuple[list[str], list[dict[str, str]]]:
        idxml_by_name = {Path(f).name: f for f in idxml_files}
        matched_idxmls: list[str] = []
        missing_reports: list[dict[str, str]] = []

        for mzml_file in mzml_files:
            basename = Path(mzml_file).stem
            expected = {basename + suffix for suffix in REQUIRED_IDXML_SUFFIXES}
            found = {
                name
                for name in idxml_by_name
                if name.startswith(basename)
                and any(name.endswith(suffix) for suffix in REQUIRED_IDXML_SUFFIXES)
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
                matched_idxmls.extend(idxml_by_name[name] for name in sorted(expected))

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
            command = [self._tool_name("FileInfo"), "-in", str(mzml_file)]

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
                    "ERROR: Required *_XLs.unknown and *_peptides.unknown files were not found."
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
    ) -> Path:
        log_file = output_folder / f"{library_name}_library_generation.log"

        try:
            settings = st.session_state.get("settings", {})
            openms_version = settings.get("openms-version", "unknown")
            app_version = settings.get("version", "unknown")
        except Exception:
            openms_version = "unknown"
            app_version = "unknown"

        with open(log_file, "w", encoding="utf-8") as handle:
            handle.write("===== version info =====\n")
            handle.write(f"OpenMS version: {openms_version}\n")
            handle.write(f"NuXLApp version: {app_version}\n\n")

            handle.write("===== selected mzML/raw files =====\n")
            for file in mzml_files:
                handle.write(f"{file}\n")

            handle.write("\n===== automatically matched idXML files =====\n")
            for file in matched_idxmls:
                handle.write(f"{file}\n")

            handle.write("\n===== parameters =====\n")
            handle.write(f"Library name: {library_name}\n")
            handle.write(f"MSFragger iRT reference: {msfragger_library or 'None'}\n")
            handle.write(
                "iRT calibration model: "
                f"{self.params.get('irt_calibration_model', 'linear')}\n"
            )

        self.logger.log(f"Wrote spectral-library log: {log_file}")
        return log_file

    def _zip_output_folder(
        self,
        output_folder: Path,
        exclude_files: set[Path] | None = None,
    ) -> Path:
        exclude_files = exclude_files or set()
        zip_path = output_folder.parent / f"{output_folder.name}_library_out_files.zip"

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
            for file in output_folder.rglob("*"):
                if not file.is_file():
                    continue

                if file.resolve() in exclude_files:
                    continue

                zip_handle.write(file, file.relative_to(output_folder.parent))

        self.logger.log(f"Created ZIP archive: {zip_path}")
        return zip_path

    def _copy_library_outputs_to_global_result_files(
        self,
        output_folder: Path,
        zip_path: Path,
        exclude_files: set[Path] | None = None,
    ) -> tuple[Path, Path]:
        """
        Copy generated DIA library output files directly into:

            <workspace>/result-files

        No extra library subfolder is created in result-files. Existing files are
        not deleted; if a same-name file already exists, a numeric suffix is used.
        """
        exclude_files = {p.resolve() for p in (exclude_files or set())}
        global_result_dir = Path(self.workflow_dir).parent / "result-files"
        global_result_dir.mkdir(parents=True, exist_ok=True)

        copied_files: list[Path] = []

        for source_file in sorted(output_folder.rglob("*")):
            if not source_file.is_file():
                continue

            if source_file.resolve() in exclude_files:
                continue

            target_file = self._unique_file_path(global_result_dir / source_file.name)
            shutil.copy2(source_file, target_file)
            copied_files.append(target_file)

        global_zip_path = self._unique_file_path(global_result_dir / zip_path.name)
        shutil.copy2(zip_path, global_zip_path)

        self.logger.log(
            "Copied spectral-library output file(s) directly to global result-files:\n"
            + "\n".join(f"- {file}" for file in copied_files)
        )
        self.logger.log(f"Copied spectral-library ZIP to global result-files: {global_zip_path}")

        return global_result_dir, global_zip_path

    def _ignore_excluded_files(self, exclude_files: set[Path]) -> Any:
        resolved_exclude_files = {p.resolve() for p in exclude_files}

        def ignore(directory: str, names: list[str]) -> set[str]:
            ignored: set[str] = set()
            directory_path = Path(directory)
            for name in names:
                path = directory_path / name
                try:
                    if path.resolve() in resolved_exclude_files:
                        ignored.add(name)
                except FileNotFoundError:
                    pass
            return ignored

        return ignore

    def _unique_output_dir(self, target_dir: Path) -> Path:
        if not target_dir.exists():
            return target_dir

        counter = 1
        while True:
            candidate = target_dir.with_name(f"{target_dir.name}_{counter}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _unique_file_path(self, target_file: Path) -> Path:
        if not target_file.exists():
            return target_file

        counter = 1
        while True:
            candidate = target_file.with_name(
                f"{target_file.stem}_{counter}{target_file.suffix}"
            )
            if not candidate.exists():
                return candidate
            counter += 1

    def _write_latest_download_state(
        self,
        library_name: str,
        output_folder: Path,
        zip_path: Path,
        global_output_dir: Path,
        global_zip_path: Path,
        log_file_path: Path,
    ) -> None:
        state_file = self._latest_download_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "library_name": library_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "output_folder": str(output_folder),
            "zip_path": str(zip_path),
            "global_output_dir": str(global_output_dir),
            "global_zip_path": str(global_zip_path),
            "log_file_path": str(log_file_path),
        }

        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        self.logger.log(f"Wrote latest library download state: {state_file}")

    def _latest_download_state_file(self) -> Path:
        return Path(
            self.workflow_dir,
            "results",
            "spectral-library",
            "latest_library_download.json",
        )

    def _render_latest_success_download(self) -> None:
        log_file = Path(self.workflow_dir, "logs", "minimal.log")
        if not log_file.exists():
            return

        log_content = log_file.read_text(encoding="utf-8", errors="replace")
        if "WORKFLOW FINISHED" not in log_content:
            return

        state_file = self._latest_download_state_file()
        if not state_file.exists():
            return

        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        zip_path = Path(state.get("global_zip_path") or state.get("zip_path") or "")
        if not zip_path.exists():
            fallback_zip = Path(state.get("zip_path") or "")
            if fallback_zip.exists():
                zip_path = fallback_zip
            else:
                return

        st.divider()
        st.success("⚡️ **Library Generation Completed Successfully!** ⚡️")
        st.info("Preparing download link for library output files ...", icon="ℹ️")

        with open(zip_path, "rb") as handle:
            st.download_button(
                label=f"⬇️ {state.get('library_name', zip_path.stem)}_library_out_files",
                data=handle,
                file_name=zip_path.name,
                mime="application/zip",
                use_container_width=True,
                key="latest-dia-library-download",
            )

        global_output_dir = state.get("global_output_dir")
        if global_output_dir:
            st.caption(f"Copied library output files directly to global result-files: `{global_output_dir}`")

    def _tool_name(self, executable: str) -> str:
        local_path = Path.cwd() / executable
        if os.name == "nt" and local_path.exists():
            return str(local_path)
        return executable
    
    
