
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


RESOURCE_URL = (
    "https://github.com/Arslan-Siraj/NuXL_rescore_resources/releases/download/"
    "0.0.1/nuxl_rescore_resource.zip"
)

PROTOCOLS = ["RNA_DEB", "RNA_NM", "RNA_4SU", "RNA_UV", "RNA_Other"]

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
]


class Workflow(WorkflowManager):
    """
    NuXL rescoring workflow.

    The workflow uses one initial NuXL idXML file as input. If max-correlation
    features are enabled, an MGF file with the same stem is required; when only
    the corresponding mzML file is present, FileConverter is used to generate
    the MGF file automatically.
    """

    def __init__(self) -> None:
        super().__init__("NuXL Rescoring Workflow", st.session_state["workspace"])

    def upload(self) -> None:
        tabs = st.tabs(["NuXL idXML files", "MS data for max-correlation features"])

        with tabs[0]:
            self.ui.upload_widget(
                key="idXML-files",
                name="NuXL idXML files",
                file_types=["idXML"],
                fallback=None,
            )

        with tabs[1]:
            self.ui.upload_widget(
                key="ms-files",
                name="MS data",
                file_types=["mzML", "mgf"],
                fallback=None,
            )

    @st.fragment
    def configure(self) -> None:
        st.markdown("### Rescoring input")

        idxml_options = self._available_idxml_files()

        if not idxml_options:
            st.error(
                "No valid initial NuXL `.idXML` files were found. "
                "Upload the main NuXL search-engine idXML file first."
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

        st.markdown("### Rescoring parameters")

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

        with st.expander("Resource paths", expanded=False):
            resource_dir = self._resource_dir()
            st.write(f"Resources will be stored in: `{resource_dir}`")
            st.caption(
                "If the resource directory is empty, the workflow downloads "
                "the NuXL rescoring resource ZIP during execution."
            )

    def execution(self) -> bool:
        self.params = self.parameter_manager.get_parameters_from_json()

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
            self.logger.log(
                "ERROR: Please select at least one feature type for rescoring."
            )
            return False

        result_dir = Path(self.workflow_dir, "results", "rescoring")
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
            idxml_file,
            f"{id_stem}_perc_1.0000_XLs.idXML",
            result_dir,
        )
        original_1_xls = self._find_reference_idxml(
            idxml_file,
            f"{id_stem}_perc_0.0100_XLs.idXML",
            result_dir,
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
            mgf_path = self._ensure_mgf_for_idxml(idxml_file, result_dir)
            if mgf_path is None:
                self.logger.log(
                    "ERROR: Max-correlation features require an MGF file, "
                    "or an mzML file that can be converted to MGF, with the same "
                    f"stem as the selected idXML file: {id_stem}"
                )
                return False
            args.extend(["-mgf", str(mgf_path)])

        args.extend(["-perc_exe", self._percolator_path()])
        args.extend(["-perc_adapter", self._percolator_adapter_path()])

        self.logger.log(f"Rescoring idXML file: {idxml_file}")
        self.logger.log(f"Protocol: {protocol}")
        self.logger.log(f"Retention-time features: {retention_time_features}")
        self.logger.log(f"Max-correlation features: {max_correlation_features}")
        self.logger.log(f"Resolved NuXL-rescore command prefix: {self._nuxl_rescore_command_prefix()}")
        self.logger.log(f"Resolved Percolator: {self._percolator_path()}")
        self.logger.log(f"Resolved PercolatorAdapter: {self._percolator_adapter_path()}")
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

        if plot_pseudoroc:
            self._try_generate_pseudoroc_plot(
                idxml_original_100_xls=original_100_xls,
                idxml_rescored_100_xls=expected_100_xls,
                exp_name=id_stem,
            )

        # Keep a compact manifest for the results page.
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
            and p.name.endswith(".idXML")
            and not any(marker in p.name for marker in EXCLUDED_IDXML_MARKERS)
            and p.name != "external_files.txt"
        ]

        external_file = input_dir / "external_files.txt"
        if external_file.exists():
            for line in external_file.read_text().splitlines():
                path = Path(line.strip())
                if (
                    path.exists()
                    and path.name.endswith(".idXML")
                    and not any(marker in path.name for marker in EXCLUDED_IDXML_MARKERS)
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
                and p.name.endswith(".idXML")
                and p.name != "external_files.txt"
            )

            external_file = input_dir / "external_files.txt"
            if external_file.exists():
                for line in external_file.read_text().splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.name.endswith(".idXML"):
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
                and p.suffix.lower() in {".mzml", ".mgf"}
                and p.name != "external_files.txt"
            )

            external_file = input_dir / "external_files.txt"
            if external_file.exists():
                for line in external_file.read_text().splitlines():
                    path = Path(line.strip())
                    if path.exists() and path.suffix.lower() in {".mzml", ".mgf"}:
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
        """
        Resolve the NuXL-rescore command for both local Windows and Linux/Docker.

        Windows/local NuXLApp usually has nuxl_rescore installed inside the
        bundled Python environment, so the correct command is:
            python-3.10.0/python.exe -m nuxl_rescore run

        Linux/Docker usually exposes nuxl_rescore on PATH. If not, fall back to
        the current Python interpreter and module execution.
        """
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
        """Resolve Percolator for Windows/local and Linux/Docker."""
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
        """Resolve OpenMS PercolatorAdapter for Windows/local and Linux/Docker."""
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

    def _file_converter_tool(self) -> str:
        """Resolve OpenMS FileConverter for Windows/local and Linux/Docker."""
        candidates = []

        if os.name == "nt":
            candidates.extend(
                [
                    Path.cwd() / "FileConverter.exe",
                    Path.cwd() / "bin" / "FileConverter.exe",
                ]
            )

        candidates.extend(
            [
                Path.cwd() / "FileConverter",
                Path.cwd() / "bin" / "FileConverter",
            ]
        )

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return shutil.which("FileConverter") or "FileConverter"

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

    def _ensure_mgf_for_idxml(self, idxml_file: str, result_dir: Path) -> Path | None:
        stem = Path(idxml_file).stem
        mgf_name = f"{stem}.mgf"
        mzml_name = f"{stem}.mzML"

        uploaded_ms_files = self._all_uploaded_ms_files()

        for path in uploaded_ms_files:
            if path.name == mgf_name:
                return path

        mzml_path = None
        for path in uploaded_ms_files:
            if path.name == mzml_name:
                mzml_path = path
                break

        if mzml_path is None:
            return None

        mgf_out = result_dir / mgf_name
        self.logger.log(f"Converting mzML to MGF: {mzml_path} -> {mgf_out}")

        success = self.executor.run_topp(
            self._file_converter_tool(),
            input_output={
                "in": [str(mzml_path)],
                "out": [str(mgf_out)],
            },
        )

        if not success:
            self.logger.log("ERROR: mzML to MGF conversion failed.")
            return None

        return mgf_out

    def _find_reference_idxml(
        self,
        selected_idxml_file: str,
        reference_name: str,
        result_dir: Path,
    ) -> Path | None:
        selected_dir = Path(selected_idxml_file).parent
        candidates = [
            selected_dir / reference_name,
            result_dir / reference_name,
        ]

        for path in self._all_uploaded_idxml_files():
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
    ) -> None:
        if not idxml_original_100_xls or not idxml_original_100_xls.exists():
            self.logger.log(
                "WARNING: Pseudo-ROC plot skipped because the original "
                "_perc_1.0000_XLs.idXML reference file was not found."
            )
            return

        if not idxml_rescored_100_xls.exists():
            self.logger.log(
                "WARNING: Pseudo-ROC plot skipped because the rescored "
                "_perc_1.0000_XLs.idXML file was not found."
            )
            return

        try:
            from src.view import plot_FDR_plot

            _, output_pdf = plot_FDR_plot(
                idXML_id=str(idxml_original_100_xls),
                idXML_extra=str(idxml_rescored_100_xls),
                FDR_level=20,
                exp_name=exp_name,
            )
            self.logger.log(f"Generated pseudo-ROC plot: {output_pdf}")
        except Exception as exc:
            self.logger.log(f"WARNING: Failed to generate pseudo-ROC plot: {exc}")

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

        settings = st.session_state.get("settings", {}) if hasattr(st, "session_state") else {}
        app_version = settings.get("version", "unknown")

        args_cmd = " ".join(map(str, args))

        search_param = textwrap.dedent(
            f"""\
            ======= Parameters ==========
            NuXLApp version: {app_version}
            Selected idXML File: {idxml_file}
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
