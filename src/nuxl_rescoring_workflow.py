import json
import os
import shutil
import sys
import textwrap
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

from src.workflow.WorkflowManager import WorkflowManager
from src.nuxl_view import show_fig

RESOURCE_URL = (
    "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/"
    "0.0.1/nuxl_rescore_resource.zip"
)

PROTOCOLS = ["RNA_DEB", "RNA_NM", "RNA_4SU", "RNA_UV", "RNA_Other"]

PROTOCOL_RT_MODEL_DESCRIPTIONS = {
    "RNA_DEB": "specific RT model fine-tuned for RNA DEB protocol",
    "RNA_NM": "specific RT model fine-tuned for RNA NM protocol",
    "RNA_4SU": "specific RT model fine-tuned for RNA 4SU protocol",
    "RNA_UV": "generic RT model fine-tuned across RNA All protocol modifications",
    "RNA_Other": "generic RT model fine-tuned across RNA All protocol modifications",
}

EXCLUDED_IDXML_MARKERS = [
    "0.0100",
    "0.1000",
    "1.0000",
    "RT_feat",
    "RT_Int_feat",
    "updated_feat",
    "_perc",
    "_perc_",
    "_sse_perc_",
    "RDDF_",
]


class Workflow(WorkflowManager):
    """
    NuXL rescoring workflow.

    - Valid initial NuXL idXML files are synced from <workspace>/result-files.
    - The synced idXML list excludes _perc_, 0.0100, 0.1000, 1.0000,
      RT_feat, RT_Int_feat, updated_feat, and _sse_perc_ files.
    - MGF files are uploaded to <workspace>/mzML-files, synced into this workflow, and selected by the user.
    - Rescoring outputs are copied directly to <workspace>/result-files.
    - After successful execution, a ZIP download button appears at the bottom
      of the execution page.
    """

    def __init__(self) -> None:
        super().__init__("NuXL Rescoring Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        st.info(
            "Click **Sync files from workspace** "
            "to make the current workspace files available for this workflow."
        )

        if st.button("Sync files from workspace", type="primary"):
            self._sync_global_idxml_files()
            self._sync_global_mgf_files()
            st.success("Valid initial idXML files and MGF files synced into workflow input folders.")
            st.rerun()

        self._show_available_files(
            key="idXML-files",
            title="idXML files",
            allowed_suffixes={".idxml"},
            help_text=(
                "Initial NuXL search out `.idXML` files available in workspace."
                " These files are NuXL out before percolator apply and FDR estimation."
            ),
        )

        st.divider()
        st.markdown("##### MGF files for max-correlation features")
        st.caption(
            "Uploading `.mgf` here uploads the file "
            "to workspace and also makes it available in this workflow. "
            "Select the required `.mgf` file manually in the Configure tab."
        )
        self._upload_mgf_files()
        self._show_available_files(
            key="ms-files",
            title="MGF files",
            allowed_suffixes={".mgf"},
            help_text=(
                "Available MGF files in workspace. "
            ),
        )

    def _sync_global_idxml_files(self) -> None:
        workspace_dir = Path(self.workflow_dir).parent
        source_dir = workspace_dir / "result-files"
        target_dir = Path(self.workflow_dir, "input-files", "idXML-files")

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

            if source_file.suffix.lower() != ".idxml":
                continue

            if not self._is_valid_initial_idxml_name(source_file.name):
                continue

            shutil.copy2(source_file, target_dir / source_file.name)

        external_file = source_dir / "external_files.txt"
        if external_file.exists():
            target_external_file = target_dir / "external_files.txt"
            lines_to_keep: list[str] = []

            for line in external_file.read_text(encoding="utf-8").splitlines():
                path = Path(line.strip())

                if (
                    path.exists()
                    and path.suffix.lower() == ".idxml"
                    and self._is_valid_initial_idxml_name(path.name)
                ):
                    lines_to_keep.append(str(path))

            if lines_to_keep:
                target_external_file.write_text(
                    "\n".join(lines_to_keep) + "\n",
                    encoding="utf-8",
                )

    def _sync_global_mgf_files(self) -> None:
        workspace_dir = Path(self.workflow_dir).parent
        source_dir = workspace_dir / "mzML-files"
        target_dir = Path(self.workflow_dir, "input-files", "ms-files")

        source_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Remove only previously synced/copied MGF files from this workflow input.
        # Directly uploaded MGF files with the same names can be overwritten by sync,
        # but no non-MGF files are touched.
        for old_file in target_dir.iterdir():
            if old_file.is_file() and old_file.suffix.lower() == ".mgf":
                old_file.unlink()

        for source_file in sorted(source_dir.iterdir()):
            if not source_file.is_file():
                continue

            if source_file.name == "external_files.txt":
                continue

            if source_file.suffix.lower() != ".mgf":
                continue

            shutil.copy2(source_file, target_dir / source_file.name)

        external_file = source_dir / "external_files.txt"
        if external_file.exists():
            target_external_file = target_dir / "external_files.txt"
            lines_to_keep: list[str] = []

            # Preserve existing non-MGF external lines, if any.
            if target_external_file.exists():
                for line in target_external_file.read_text(encoding="utf-8").splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() != ".mgf":
                        lines_to_keep.append(str(path))

            for line in external_file.read_text(encoding="utf-8").splitlines():
                path = Path(line.strip())

                if path.exists() and path.suffix.lower() == ".mgf":
                    lines_to_keep.append(str(path))

            if lines_to_keep:
                # Keep unique lines while preserving order.
                unique_lines = list(dict.fromkeys(lines_to_keep))
                target_external_file.write_text(
                    "\n".join(unique_lines) + "\n",
                    encoding="utf-8",
                )
            elif target_external_file.exists():
                target_external_file.unlink()

    def _upload_mgf_files(self) -> None:
        workspace_dir = Path(self.workflow_dir).parent
        global_mzml_dir = workspace_dir / "mzML-files"
        target_dir = Path(self.workflow_dir, "input-files", "ms-files")

        global_mzml_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = st.file_uploader(
            "Upload MGF files",
            type=["mgf"],
            accept_multiple_files=True,
            help=(
                "Required only when Max correlation features are enabled. "
                "Uploaded MGF files are copied to the global mzML-files folder "
                "and also made available in this workflow for selection."
            ),
            key="rescoring-mgf-upload",
        )

        if uploaded_files:
            saved_files = []

            for uploaded_file in uploaded_files:
                global_file = self._unique_file_path(global_mzml_dir / uploaded_file.name)

                with open(global_file, "wb") as handle:
                    handle.write(uploaded_file.getbuffer())

                workflow_file = target_dir / global_file.name
                shutil.copy2(global_file, workflow_file)
                saved_files.append(global_file.name)

            st.success(
                "Uploaded MGF file(s) to global mzML-files and this workflow: "
                + ", ".join(saved_files)
            )

        existing_mgf_files = [
            file
            for file in sorted(target_dir.iterdir())
            if file.is_file()
            and file.name != "external_files.txt"
            and file.suffix.lower() == ".mgf"
        ]

        if existing_mgf_files:
            if st.button(
                "Clear MGF files from this workflow input",
                type="secondary",
                key="clear-rescoring-mgf-files",
            ):
                for file in existing_mgf_files:
                    file.unlink()

                external_file = target_dir / "external_files.txt"
                if external_file.exists():
                    external_file.unlink()

                st.success(
                    "MGF files cleared from this workflow input. "
                    "Global mzML-files were not deleted."
                )
                st.rerun()

    def _show_available_files(
        self,
        key: str,
        title: str,
        allowed_suffixes: set[str],
        help_text: str | None = None,
    ) -> None:
        input_dir = Path(self.workflow_dir, "input-files", key)

        st.markdown(f"##### {title}")

        if help_text:
            st.caption(help_text)

        if not input_dir.exists():
            st.warning("No files available yet.")
            return

        files: list[str] = [
            file.name
            for file in sorted(input_dir.iterdir())
            if file.is_file()
            and file.name != "external_files.txt"
            and file.suffix.lower() in allowed_suffixes
        ]

        external_file = input_dir / "external_files.txt"
        if external_file.exists():
            files.extend(
                line.strip()
                for line in external_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and Path(line.strip()).suffix.lower() in allowed_suffixes
            )

        if not files:
            st.warning("No files available yet.")
            return

        st.dataframe(pd.DataFrame({"file": files}), use_container_width=True)

    def _is_valid_initial_idxml_name(self, file_name: str) -> bool:
        if not file_name.lower().endswith(".idxml"):
            return False

        return not any(marker in file_name for marker in EXCLUDED_IDXML_MARKERS)

    @st.fragment
    def configure(self) -> None:
        #st.markdown("### Rescoring input")

        idxml_options = self._available_idxml_files()

        if not idxml_options:
            st.error(
                "No valid initial NuXL `.idXML` files were found. "
                "Run NuXL first, then use the Upload tab to sync valid initial idXML files."
            )
        else:
            self.ui.input_widget(
                key="idXML-files",
                default=idxml_options[0],
                name="Choose a file for rescoring",
                widget_type="selectbox",
                options=idxml_options,
                display_file_path=False,
            )

        mgf_files = self._all_uploaded_ms_files()
        if mgf_files:
            mgf_options = ["None"] + [str(p) for p in mgf_files]
            self.ui.input_widget(
                key="mgf-file",
                default=mgf_options[1],
                name="Choose MGF file for max-correlation features",
                widget_type="selectbox",
                options=mgf_options,
                display_file_path=False,
                help=(
                    "Used only when Max correlation features are enabled. "
                    "Select the MGF file manually."
                ),
            )
        else:
            st.info(
                "Optional/required: upload an MGF file on the Upload page or "
                "place it in global mzML-files, then sync, if Max correlation "
                "features are enabled."
            )

        #st.markdown("### Rescoring parameters")

        self.ui.input_widget(
            key="protocol",
            default="RNA_DEB",
            name="Select the suitable protocol",
            widget_type="selectbox",
            options=PROTOCOLS,
            help="Select the protocol used for the crosslinking experiment.",
        )

        cols = st.columns(3)

        with cols[0]:
            self.ui.input_widget(
                key="retention_time_features",
                default=True,
                name="Retention time prediction and features",
                widget_type="checkbox",
                help="Predict and use retention-time features during rescoring.",
            )

        with cols[1]:
            self.ui.input_widget(
                key="max_correlation_features",
                default=True,
                name="Max correlation features",
                widget_type="checkbox",
                help="Use max-correlation features during rescoring.",
            )

        with cols[2]:
            self.ui.input_widget(
                key="plot_pseudoroc",
                default=True,
                name="plot pseudo-ROC",
                widget_type="checkbox",
                help="Generate a pseudo-ROC comparison plot when reference files are available.",
            )

    def show_execution_section(self) -> None:
        """
        Render the normal execution section, but avoid StreamlitUI's default
        export_parameters_markdown() subprocess call.

        On Windows, the default summary can spawn an extra OpenMS helper process
        just to render the Summary box. If memory/pagefile is low, that can fail
        before the workflow starts. Rescoring uses this lightweight summary instead.
        """
        self.ui.export_parameters_markdown = self._safe_export_parameters_markdown

        self.ui.execution_section(
            start_workflow_function=self.start_workflow,
            get_status_function=self.get_workflow_status,
            stop_workflow_function=self.stop_workflow,
        )
        self._render_latest_success_download()

    def _safe_export_parameters_markdown(self) -> str:
        params = self.parameter_manager.get_parameters_from_json()

        rescore_url = "https://github.com/Arslan-Siraj/NuXL_rescore"

        url = f"https://github.com/Arslan-Siraj/{st.session_state.settings['repository-name']}"
        app_name = st.session_state.settings.get("app-name", "NuXLApp")

        try:
            openms_version = st.session_state.get("settings", {}).get("openms-version", "unknown")
            app_version = st.session_state.get("settings", {}).get("version", "unknown")
        except Exception:
            openms_version = "unknown"
            app_version = "unknown"

        lines = [
            (
                f"The protein–nucleic acid rescoring workflow runs in **{app_name} (version {app_version})**"
                f"{f' ([{url}]({url}))' if url else ''}, "
                "a web application based on the OpenMS WebApps framework [1]."
            ),
            (
                "This workflow takes NuXL search-engine output from protein–nucleic acid "
                "cross-link identification [2] and adapts a data-driven rescoring pipeline "
                f"using predicted retention time and fragment-ion intensity features ({rescore_url}) [3]. "
                "These additional features improve discrimination between correct and incorrect "
                "matches and can increase identification confidence with Percolator."
            ),
            "",
            (
                '[1] Müller, Tom David, et al. "OpenMS WebApps: Building User-Friendly '
                'Solutions for MS Analysis." (2025). '
                "[https://doi.org/10.1021/acs.jproteome.4c00872]"
                "(https://doi.org/10.1021/acs.jproteome.4c00872)."
            ),
            "",
            (
                '[2] Welp, et al. "Chemical crosslinking extends and complements UV '
                'crosslinking in analysis of RNA/DNA nucleic acid–protein interaction '
                'sites by mass spectrometry." (2025). '
                "[https://doi.org/10.1093/nar/gkaf727]"
                "(https://doi.org/10.1093/nar/gkaf727)."
            ),
            "",
            (
                '[3] Siraj, Arslan, et al. "Intensity and retention time prediction improves '
                'the rescoring of protein‐nucleic acid cross‐links." (2024). '
                "[https://doi.org/10.1002/pmic.202300144]"
                "(https://doi.org/10.1002/pmic.202300144)."
            ),
            "",
            "**Rescoring parameters**",
        ]

        if not params:
            lines.append("> No parameters saved yet. Configure the workflow first.")
            return "\n".join(lines)

        max_correlation_features = bool(params.get("max_correlation_features", True))

        for key, value in params.items():
            if key == "mgf-file" and not max_correlation_features:
                continue

            if isinstance(value, (list, tuple)):
                clean_value = ", ".join(
                    Path(str(v)).name if Path(str(v)).exists() else str(v)
                    for v in value
                )
            elif isinstance(value, dict):
                clean_value = str(value)
            else:
                clean_value = Path(str(value)).name if Path(str(value)).exists() else str(value)

            lines.append(f"> {key}: **{clean_value}**")

            if key == "protocol":
                rt_model_description = PROTOCOL_RT_MODEL_DESCRIPTIONS.get(
                    str(value),
                    "generic RNA-All retention-time model",
                )
                lines.append(f"> RT model: **{rt_model_description}**")

        return "\n".join(lines)

    def execution(self) -> bool:
        self.params = self.parameter_manager.get_parameters_from_json()

        # Refresh valid initial idXML files and global MGF files when the job starts.
        self._sync_global_idxml_files()
        self._sync_global_mgf_files()

        idxml_file = self.params.get("idXML-files")
        if not idxml_file:
            self.logger.log("ERROR: No idXML file selected for rescoring.")
            return False

        idxml_file = str(idxml_file)
        if not Path(idxml_file).exists():
            self.logger.log(f"ERROR: Selected idXML file does not exist: {idxml_file}")
            return False

        protocol = self.params.get("protocol", "RNA_DEB")
        retention_time_features = bool(self.params.get("retention_time_features", True))
        max_correlation_features = bool(self.params.get("max_correlation_features", True))
        plot_pseudoroc = bool(self.params.get("plot_pseudoroc", True))

        if not retention_time_features and not max_correlation_features:
            self.logger.log("ERROR: Please select at least one feature type for rescoring.")
            return False

        result_dir = Path(self.workflow_dir, "results", "rescoring")
        if result_dir.exists():
            shutil.rmtree(result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)

        try:
            resources = self._ensure_resources()
        except Exception as exc:
            self.logger.log(f"ERROR: Failed to prepare NuXL rescoring resources: {exc}")
            return False

        model_path = None
        calibration_data = None

        if retention_time_features:
            model_path, calibration_data = self._rt_resource_paths(protocol, resources)

        id_stem = Path(idxml_file).stem

        original_100_xls = self._find_reference_idxml(
            selected_idxml_file=idxml_file,
            reference_name=f"{id_stem}_perc_1.0000_XLs.idXML",
            result_dir=result_dir,
        )
        original_1_xls = self._find_reference_idxml(
            selected_idxml_file=idxml_file,
            reference_name=f"{id_stem}_perc_0.0100_XLs.idXML",
            result_dir=result_dir,
        )

        args, expected_100_xls, expected_1_xls = self._build_rescore_command(
            idxml_file=idxml_file,
            result_dir=result_dir,
            resources=resources,
            retention_time_features=retention_time_features,
            max_correlation_features=max_correlation_features,
            model_path=model_path,
            calibration_data=calibration_data,
        )

        if max_correlation_features:
            mgf_path = self._ensure_mgf_for_idxml(idxml_file)
            if mgf_path is None:
                self.logger.log(
                    "ERROR: Max-correlation features require an MGF file selected in Configure."
                )
                return False
            args.extend(["-mgf", str(mgf_path)])

        args.extend(["-perc_exe", self._percolator_path()])
        args.extend(["-perc_adapter", self._percolator_adapter_path()])

        # Limit TensorFlow/NumPy thread fan-out. On Windows, DeepLC/TensorFlow
        # can otherwise spawn many heavy worker processes and exhaust the paging file.
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
        os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
        os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

        self.logger.log(f"Rescoring idXML file: {idxml_file}")
        #self.logger.log(f"Protocol: {protocol}")
        #self.logger.log(f"Retention-time features: {retention_time_features}")
        #self.logger.log(f"Max-correlation features: {max_correlation_features}")
        #self.logger.log(f"Resolved NuXL-rescore command prefix: {self._nuxl_rescore_command_prefix()}")
        #self.logger.log(f"Resolved Percolator: {self._percolator_path()}")
        #self.logger.log(f"Resolved PercolatorAdapter: {self._percolator_adapter_path()}")
        self.logger.log("Running NuXL rescoring...")

        success = self.executor.run_command(args)

        log_file_path = self._write_rescoring_log(
            result_dir=result_dir,
            idxml_file=idxml_file,
            protocol=protocol,
            retention_time_features=retention_time_features,
            max_correlation_features=max_correlation_features,
            model_path=model_path,
            calibration_data=calibration_data,
            resources=resources,
            args=args,
            success=success,
        )

        if not success:
            self.logger.log("ERROR: NuXL rescoring failed.")
            return False

        self._remove_intermediate_files(result_dir)

        pseudoroc_pdf = None
        if plot_pseudoroc:
            pseudoroc_pdf = self._try_generate_pseudoroc_plot(
                idxml_original_100_xls=original_100_xls,
                idxml_rescored_100_xls=expected_100_xls,
                exp_name=id_stem,
                result_dir=result_dir,
            )

        manifest = result_dir / "rescoring_manifest.tsv"
        files_to_report = [log_file_path]
        if expected_1_xls.exists():
            files_to_report.append(expected_1_xls)
        if original_1_xls and original_1_xls.exists():
            files_to_report.append(original_1_xls)

        pd.DataFrame(
            {
                "file": [p.name for p in files_to_report if p.exists()],
                "path": [str(p) for p in files_to_report if p.exists()],
            }
        ).to_csv(manifest, sep="\t", index=False)

        zip_path = self._zip_rescoring_outputs(result_dir)
        global_zip_path = self._copy_rescoring_outputs_to_global_result_files(
            result_dir=result_dir,
            zip_path=zip_path,
        )
        self._write_latest_download_state(
            id_stem=id_stem,
            result_dir=result_dir,
            zip_path=zip_path,
            global_zip_path=global_zip_path,
            idxml_original_100_xls=original_100_xls,
            idxml_rescored_100_xls=expected_100_xls,
            pseudoroc_pdf=pseudoroc_pdf,
        )

        self.logger.log("NuXL rescoring completed successfully.")
        return True

    @st.fragment
    def results(self) -> None:
        result_dir = Path(self.workflow_dir, "results", "rescoring")

        if not result_dir.exists():
            st.warning("No rescoring result directory found. Please run the workflow first.")
            return

        files = sorted([p for p in result_dir.iterdir() if p.is_file()])

        if not files:
            st.warning("No rescoring result files found. Please run the workflow first.")
            return

        st.metric("Number of rescoring result files", len(files))

        df = pd.DataFrame(
            {
                "file": [p.name for p in files],
                "size MB": [round(p.stat().st_size / (1024 * 1024), 3) for p in files],
            }
        )
        st.dataframe(df, use_container_width=True)

        pdf_files = [p for p in files if p.suffix.lower() == ".pdf"]
        if pdf_files:
            st.info("Pseudo-ROC plot PDF files were generated.")
            for pdf in pdf_files:
                with open(pdf, "rb") as handle:
                    st.download_button(
                        label=f"Download {pdf.name}",
                        data=handle,
                        file_name=pdf.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )

        self.ui.zip_and_download_files(result_dir)

    def _available_idxml_files(self) -> list[str]:
        input_dir = Path(self.workflow_dir, "input-files", "idXML-files")
        if not input_dir.exists():
            return []

        options: list[str] = [
            str(p)
            for p in sorted(input_dir.iterdir())
            if p.is_file()
            and p.suffix.lower() == ".idxml"
            and self._is_valid_initial_idxml_name(p.name)
            and p.name != "external_files.txt"
        ]

        external_file = input_dir / "external_files.txt"
        if external_file.exists():
            for line in external_file.read_text(encoding="utf-8").splitlines():
                path = Path(line.strip())
                if (
                    path.exists()
                    and path.suffix.lower() == ".idxml"
                    and self._is_valid_initial_idxml_name(path.name)
                ):
                    options.append(str(path))

        return options

    def _all_uploaded_idxml_files(self) -> list[Path]:
        input_dir = Path(self.workflow_dir, "input-files", "idXML-files")
        files: list[Path] = []

        if input_dir.exists():
            files.extend(
                p
                for p in sorted(input_dir.iterdir())
                if p.is_file()
                and p.suffix.lower() == ".idxml"
                and p.name != "external_files.txt"
            )

            external_file = input_dir / "external_files.txt"
            if external_file.exists():
                for line in external_file.read_text(encoding="utf-8").splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() == ".idxml":
                        files.append(path)

        return files

    def _all_global_idxml_files(self) -> list[Path]:
        global_result_dir = Path(self.workflow_dir).parent / "result-files"
        files: list[Path] = []

        if global_result_dir.exists():
            files.extend(
                p
                for p in sorted(global_result_dir.iterdir())
                if p.is_file() and p.suffix.lower() == ".idxml"
            )

            external_file = global_result_dir / "external_files.txt"
            if external_file.exists():
                for line in external_file.read_text(encoding="utf-8").splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() == ".idxml":
                        files.append(path)

        return files

    def _all_uploaded_ms_files(self) -> list[Path]:
        input_dir = Path(self.workflow_dir, "input-files", "ms-files")
        files: list[Path] = []

        if input_dir.exists():
            files.extend(
                p
                for p in sorted(input_dir.iterdir())
                if p.is_file()
                and p.suffix.lower() == ".mgf"
                and p.name != "external_files.txt"
            )

            external_file = input_dir / "external_files.txt"
            if external_file.exists():
                for line in external_file.read_text(encoding="utf-8").splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() == ".mgf":
                        files.append(path)

        return files

    def _resource_dir(self) -> Path:
        return Path(self.workflow_dir, "resources", "nuxl-rescore-files")

    def _ensure_resources(self) -> dict[str, Path]:
        resource_dir = self._resource_dir()
        resource_dir.mkdir(parents=True, exist_ok=True)

        resource_root = resource_dir / "nuxl_rescore_resource"
        unimod = resource_root / "unimod" / "unimod_to_formula.csv"
        feat_config = resource_root / "features-config.json"

        if not unimod.exists() or not feat_config.exists():
            self.logger.log("NuXL rescoring resources missing. Downloading resources...")
            zip_path = resource_dir / "nuxl_rescore_resource.zip"

            with requests.get(RESOURCE_URL, timeout=500, stream=True) as response:
                response.raise_for_status()
                with open(zip_path, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            handle.write(chunk)

            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(resource_dir)

            zip_path.unlink(missing_ok=True)

        if not unimod.exists():
            raise FileNotFoundError(f"Unimod resource not found: {unimod}")

        if not feat_config.exists():
            raise FileNotFoundError(f"Feature config not found: {feat_config}")

        return {
            "root": resource_root,
            "unimod": unimod,
            "feat_config": feat_config,
        }

    def _rt_resource_paths(self, protocol: str, resources: dict[str, Path]) -> tuple[Path, Path]:
        root = resources["root"]

        if protocol == "RNA_DEB":
            model_path = root / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_DEB"
            calibration_data = root / "calibration_data" / "RNA_DEB.csv"
        elif protocol == "RNA_NM":
            model_path = root / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_NM"
            calibration_data = root / "calibration_data" / "RNA_NM.csv"
        elif protocol == "RNA_4SU":
            model_path = root / "RT_deeplc_model" / "specific_model" / "full_hc_Train_RNA_4SU"
            calibration_data = root / "calibration_data" / "RNA_4SU.csv"
        else:
            model_path = root / "RT_deeplc_model" / "generic_model" / "full_hc_Train_RNA_All"
            calibration_data = root / "calibration_data" / "RNA_All.csv"

        return model_path, calibration_data

    def _nuxl_rescore_command_prefix(self) -> list[str]:
        if os.name == "nt":
            python_candidates = [
                Path.cwd() / "python-3.10.0" / "python.exe",
                Path.cwd() / "python-3.10.0" / "python",
                Path(sys.executable),
            ]

            for python_exe in python_candidates:
                if python_exe.exists():
                    return [str(python_exe), "-m", "nuxl_rescore", "run"]

            return ["python", "-m", "nuxl_rescore", "run"]

        if shutil.which("nuxl_rescore"):
            return ["nuxl_rescore", "run"]

        return [sys.executable, "-m", "nuxl_rescore", "run"]

    def _percolator_path(self) -> str:
        candidates = []

        if os.name == "nt":
            candidates.extend(
                [
                    Path.cwd() / "_thirdparty" / "Percolator" / "percolator.exe",
                    Path.cwd() / "percolator.exe",
                ]
            )

        candidates.extend(
            [
                Path.cwd() / "_thirdparty" / "Percolator" / "percolator",
                Path.cwd() / "percolator",
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return shutil.which("percolator") or "percolator"

    def _percolator_adapter_path(self) -> str:
        candidates = []

        if os.name == "nt":
            candidates.extend(
                [
                    Path.cwd() / "PercolatorAdapter.exe",
                    Path.cwd() / "bin" / "PercolatorAdapter.exe",
                ]
            )

        candidates.extend(
            [
                Path.cwd() / "PercolatorAdapter",
                Path.cwd() / "bin" / "PercolatorAdapter",
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return shutil.which("PercolatorAdapter") or "PercolatorAdapter"

    def _build_rescore_command(
        self,
        idxml_file: str,
        result_dir: Path,
        resources: dict[str, Path],
        retention_time_features: bool,
        max_correlation_features: bool,
        model_path: Path | None,
        calibration_data: Path | None,
    ) -> tuple[list[str], Path, Path]:
        args = self._nuxl_rescore_command_prefix()
        args.extend(["-id", idxml_file])

        stem = Path(idxml_file).stem

        if retention_time_features and not max_correlation_features:
            args.extend(
                [
                    "-calibration",
                    str(calibration_data),
                    "-unimod",
                    str(resources["unimod"]),
                    "-feat_config",
                    str(resources["feat_config"]),
                    "-rt_model",
                    "DeepLC",
                    "-model_path",
                    str(model_path),
                    "-out",
                    str(result_dir),
                ]
            )
            prefix = "RT_feat"

        elif not retention_time_features and max_correlation_features:
            args.extend(
                [
                    "-rt_model",
                    "None",
                    "-ms2pip",
                    "-unimod",
                    str(resources["unimod"]),
                    "-feat_config",
                    str(resources["feat_config"]),
                    "-out",
                    str(result_dir),
                ]
            )
            prefix = "Int_feat"

        else:
            args.extend(
                [
                    "-calibration",
                    str(calibration_data),
                    "-unimod",
                    str(resources["unimod"]),
                    "-rt_model",
                    "DeepLC",
                    "-ms2pip",
                    "-feat_config",
                    str(resources["feat_config"]),
                    "-model_path",
                    str(model_path),
                    "-out",
                    str(result_dir),
                ]
            )
            prefix = "RT_Int_feat"

        expected_100_xls = result_dir / f"{prefix}_{stem}_perc_1.0000_XLs.idXML"
        expected_1_xls = result_dir / f"{prefix}_{stem}_perc_0.0100_XLs.idXML"

        return args, expected_100_xls, expected_1_xls

    def _ensure_mgf_for_idxml(self, idxml_file: str) -> Path | None:
        selected_mgf = self.params.get("mgf-file")

        if selected_mgf and selected_mgf != "None":
            selected_path = Path(str(selected_mgf))

            if selected_path.exists() and selected_path.suffix.lower() == ".mgf":
                return selected_path

            # Fallback if ParameterManager stored only the displayed file name.
            for path in self._all_uploaded_ms_files():
                if path.name == str(selected_mgf):
                    return path

            self.logger.log(f"ERROR: Selected MGF file does not exist: {selected_mgf}")
            return None

        if not self._all_uploaded_ms_files():
            self.logger.log("ERROR: No MGF files are available.")
            return None

        self.logger.log(
            "ERROR: Please select an MGF file in Configure when "
            "Max-correlation features are enabled."
        )
        return None

    def _find_reference_idxml(
        self,
        selected_idxml_file: str,
        reference_name: str,
        result_dir: Path,
    ) -> Path | None:
        selected_dir = Path(selected_idxml_file).parent
        global_result_dir = Path(self.workflow_dir).parent / "result-files"

        candidates = [
            selected_dir / reference_name,
            result_dir / reference_name,
            global_result_dir / reference_name,
        ]

        for path in self._all_uploaded_idxml_files():
            if path.name == reference_name:
                candidates.append(path)

        for path in self._all_global_idxml_files():
            if path.name == reference_name:
                candidates.append(path)

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _remove_intermediate_files(self, result_dir: Path) -> None:
        extensions_to_remove = {
            ".csv",
            ".peprec",
            ".tab",
            ".png",
            ".weights",
        }

        for file_path in result_dir.iterdir():
            if file_path.is_file() and file_path.suffix in extensions_to_remove:
                file_path.unlink()

    def _try_generate_pseudoroc_plot(
        self,
        idxml_original_100_xls: Path | None,
        idxml_rescored_100_xls: Path,
        exp_name: str,
        result_dir: Path,
    ) -> Path | None:
        if not idxml_original_100_xls or not idxml_original_100_xls.exists():
            self.logger.log(
                "WARNING: Pseudo-ROC plot skipped because the original "
                "_perc_1.0000_XLs.idXML reference file was not found."
            )
            return None

        if not idxml_rescored_100_xls.exists():
            self.logger.log(
                "WARNING: Pseudo-ROC plot skipped because the rescored "
                "_perc_1.0000_XLs.idXML file was not found."
            )
            return None

        try:
            from src.view import plot_FDR_plot

            fig, output_pdf = plot_FDR_plot(
                idXML_id=str(idxml_original_100_xls),
                idXML_extra=str(idxml_rescored_100_xls),
                FDR_level=20,
                exp_name=exp_name,
            )

            output_pdf = Path(output_pdf)
            if not output_pdf.exists():
                self.logger.log("WARNING: Pseudo-ROC plot PDF was not generated.")
                return None

            if output_pdf.parent != result_dir:
                target_pdf = self._unique_file_path(result_dir / output_pdf.name)
                shutil.copy2(output_pdf, target_pdf)
                output_pdf = target_pdf

            self.logger.log(f"Generated pseudo-ROC plot PDF: {output_pdf}")
            return output_pdf
        except Exception as exc:
            self.logger.log(f"WARNING: Failed to generate pseudo-ROC plot: {exc}")
            return None

    def _write_rescoring_log(
        self,
        result_dir: Path,
        idxml_file: str,
        protocol: str,
        retention_time_features: bool,
        max_correlation_features: bool,
        model_path: Path | None,
        calibration_data: Path | None,
        resources: dict[str, Path],
        args: list[str],
        success: bool,
    ) -> Path:
        time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        id_file = Path(idxml_file)
        log_file_path = result_dir / f"{id_file.stem}_rescore_out_log_{time_stamp}.txt"

        try:
            settings = st.session_state.get("settings", {})
            app_version = settings.get("version", "unknown")
        except Exception:
            app_version = "unknown"

        args_cmd = " ".join(map(str, args))

        search_param = textwrap.dedent(
            f"""\
            ======= Parameters ==========
            NuXLApp version: {app_version}
            Selected idXML File: {idxml_file}
            Selected MGF File: {self.params.get('mgf-file', 'None')}
            Protocol: {protocol}
            Retention time features: {retention_time_features}
            Max correlation features: {max_correlation_features}
            Model path: {model_path if retention_time_features else 'None'}
            Calibration data: {calibration_data if retention_time_features else 'None'}
            Unimod file: {resources["unimod"]}
            Feature config: {resources["feat_config"]}
            Success: {success}

            ======= Executed command =======
            {args_cmd}
            """
        )

        with open(log_file_path, "w", encoding="utf-8") as handle:
            handle.write(search_param)

        self.logger.log(f"Wrote rescoring log: {log_file_path}")
        return log_file_path

    def _zip_rescoring_outputs(self, result_dir: Path) -> Path:
        zip_path = result_dir / "rescoring_out_files.zip"

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_handle:
            for file_path in sorted(result_dir.iterdir()):
                if not file_path.is_file():
                    continue

                if file_path.resolve() == zip_path.resolve():
                    continue

                zip_handle.write(file_path, arcname=file_path.name)

        self.logger.log(f"Created rescoring ZIP archive: {zip_path}")
        return zip_path

    def _copy_rescoring_outputs_to_global_result_files(
        self,
        result_dir: Path,
        zip_path: Path,
    ) -> Path:
        global_result_dir = Path(self.workflow_dir).parent / "result-files"
        global_result_dir.mkdir(parents=True, exist_ok=True)

        global_zip_path: Path | None = None
        copied_files: list[Path] = []

        for source_file in sorted(result_dir.iterdir()):
            if not source_file.is_file():
                continue

            target_name = self._global_rescoring_output_name(source_file.name)
            target_file = self._unique_file_path(global_result_dir / target_name)

            shutil.copy2(source_file, target_file)
            copied_files.append(target_file)

            if source_file.resolve() == zip_path.resolve():
                global_zip_path = target_file

        if global_zip_path is None:
            target_name = self._global_rescoring_output_name(zip_path.name)
            global_zip_path = self._unique_file_path(global_result_dir / target_name)
            shutil.copy2(zip_path, global_zip_path)
            copied_files.append(global_zip_path)

        self.logger.log(
            "Copied rescoring output file(s) directly to global result-files:\n"
            + "\n".join(f"- {file}" for file in copied_files)
        )

        return global_zip_path

    def _global_rescoring_output_name(self, file_name: str) -> str:
        """
        Rename copied rescoring outputs for the global result-files folder.

        Feature prefixes generated by nuxl_rescore are removed and replaced
        with RDDF_. Log files keep their original names.
        """
        if "_rescore_out_log_" in file_name:
            return file_name

        if file_name == "rescoring_manifest.tsv":
            return file_name

        if file_name == "rescoring_out_files.zip":
            return "RDDF_rescoring_out_files.zip"

        prefixes_to_remove = [
            "RT_Int_feat_",
            "RT_feat_",
            "Int_feat_",
            "updated_feat_",
        ]

        clean_name = file_name

        for prefix in prefixes_to_remove:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]
                break

        if clean_name.startswith("RDDF_"):
            return clean_name

        return f"RDDF_{clean_name}"

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
        id_stem: str,
        result_dir: Path,
        zip_path: Path,
        global_zip_path: Path,
        idxml_original_100_xls: Path | None = None,
        idxml_rescored_100_xls: Path | None = None,
        pseudoroc_pdf: Path | None = None,
    ) -> None:
        state_file = self._latest_download_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "id_stem": id_stem,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "result_dir": str(result_dir),
            "zip_path": str(zip_path),
            "global_zip_path": str(global_zip_path),
            "idxml_original_100_xls": str(idxml_original_100_xls) if idxml_original_100_xls else "",
            "idxml_rescored_100_xls": str(idxml_rescored_100_xls) if idxml_rescored_100_xls else "",
            "pseudoroc_pdf": str(pseudoroc_pdf) if pseudoroc_pdf else "",
        }

        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        self.logger.log(f"Wrote latest rescoring download state: {state_file}")

    def _latest_download_state_file(self) -> Path:
        return Path(
            self.workflow_dir,
            "results",
            "rescoring",
            "latest_rescoring_download.json",
        )

    def _render_pseudoroc_plot_before_download(self, state: dict[str, Any]) -> None:
        """Show the pseudo-ROC figure before the ZIP download button."""
        pseudoroc_pdf = Path(state.get("pseudoroc_pdf") or "")
        idxml_original_100_xls = Path(state.get("idxml_original_100_xls") or "")
        idxml_rescored_100_xls = Path(state.get("idxml_rescored_100_xls") or "")

        if not pseudoroc_pdf.exists():
            return

        if not idxml_original_100_xls.exists() or not idxml_rescored_100_xls.exists():
            self.logger.log(
                "WARNING: Pseudo-ROC plot display skipped because the idXML files were not found."
            )
            return

        try:
            from src.view import plot_FDR_plot

            fig, _ = plot_FDR_plot(
                idXML_id=str(idxml_original_100_xls),
                idXML_extra=str(idxml_rescored_100_xls),
                FDR_level=20,
                exp_name=str(state.get("id_stem") or idxml_rescored_100_xls.stem),
            )
            show_fig(
                fig,
                f"{idxml_rescored_100_xls.stem}_PseudoROC_plot_rescoring",
            )
        except Exception as exc:
            self.logger.log(f"WARNING: Failed to display pseudo-ROC plot: {exc}")

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
        #st.success("⚡️ **NuXL Rescoring Completed Successfully!** ⚡️")
        st.info("Plotting pseudo-ROC curve and preparing download link for rescoring output files ...", icon="ℹ️")
        self._render_pseudoroc_plot_before_download(state)
 
        with open(zip_path, "rb") as handle:
            st.download_button(
                label=f"⬇️ Download {state.get('id_stem', zip_path.stem)}_rescoring_out_files",
                data=handle,
                file_name=zip_path.name,
                mime="application/zip",
                use_container_width=True,
                type="primary",
                key="latest-rescoring-download",
            )

        st.caption("Rescoring output files were copied to the global result-files, could be found on **Results** page. ")
