from pathlib import Path
from typing import Optional

from .Logger import Logger
from .ParameterManager import ParameterManager
from .CommandExecutor import CommandExecutor
from .SafeStreamlitUI import StreamlitUI
from .FileManager import FileManager

import multiprocessing
import streamlit as st
import shutil
import time
import traceback
import pandas as pd


class WorkflowManager:
    # Core workflow logic using the above classes
    def __init__(self, name: str, workspace: str):
        self.name = name
        self.workflow_dir = Path(workspace, name.replace(" ", "-").lower())
        self.file_manager = FileManager(self.workflow_dir)
        self.logger = Logger(self.workflow_dir)
        self.parameter_manager = ParameterManager(
            self.workflow_dir,
            workflow_name=name,
        )
        self.executor = CommandExecutor(
            self.workflow_dir,
            self.logger,
            self.parameter_manager,
        )
        self.ui = StreamlitUI(
            self.workflow_dir,
            self.logger,
            self.executor,
            self.parameter_manager,
        )
        self.params = self.parameter_manager.get_parameters_from_json()

        # Initialize queue manager for online mode
        self._queue_manager: Optional['QueueManager'] = None
        if self._is_online_mode():
            self._init_queue_manager()

    def _is_online_mode(self) -> bool:
        """Check if running in online deployment mode."""
        return st.session_state.get("settings", {}).get(
            "online_deployment",
            False,
        )

    def _init_queue_manager(self) -> None:
        """Initialize queue manager for online mode."""
        try:
            from .QueueManager import QueueManager
            self._queue_manager = QueueManager()
        except ImportError:
            pass

    def _prepare_new_run(self) -> None:
        """
        Remove workflow-local output from the previous run.

        IMPORTANT:
        This removes only:
            <workspace>/<workflow>/logs
            <workspace>/<workflow>/results

        It does NOT remove the global workspace result-files directory.

        Clearing the workflow-local result directory immediately when Start is
        clicked prevents stale ZIP/download-state files, plots, and completion
        markers from a previous analysis from remaining visible while the new
        analysis is running.
        """
        shutil.rmtree(
            Path(self.workflow_dir, "logs"),
            ignore_errors=True,
        )
        shutil.rmtree(
            Path(self.workflow_dir, "results"),
            ignore_errors=True,
        )
        Path(self.workflow_dir, "results").mkdir(
            parents=True,
            exist_ok=True,
        )

    def start_workflow(self) -> None:
        """
        Start the workflow.

        Online mode: submit to Redis/RQ.
        Local mode: spawn a multiprocessing.Process.
        """
        # Save the latest widget values before the worker is launched.
        self.parameter_manager.save_parameters()

        # Clear stale workflow-local output BEFORE submitting the new job.
        self._prepare_new_run()

        if self._queue_manager and self._queue_manager.is_available:
            self._start_workflow_queued()
        else:
            self._start_workflow_local()

    def _start_workflow_queued(self) -> None:
        """Submit workflow to Redis queue (online mode)."""
        from .tasks import execute_workflow

        job_id = f"workflow-{self.workflow_dir.name}-{int(time.time())}"

        submitted_id = self._queue_manager.submit_job(
            func=execute_workflow,
            kwargs={
                "workflow_dir": str(self.workflow_dir),
                "workflow_class": self.__class__.__name__,
                "workflow_module": self.__class__.__module__,
            },
            job_id=job_id,
            description=f"Workflow: {self.name}",
        )

        if submitted_id:
            self._queue_manager.store_job_id(
                self.workflow_dir,
                submitted_id,
            )
        else:
            st.warning(
                "Queue submission failed, running locally..."
            )
            self._start_workflow_local()

    def _start_workflow_local(self) -> None:
        """Start workflow as a local process."""
        # _prepare_new_run() already removed old logs/results.
        workflow_process = multiprocessing.Process(
            target=self.workflow_process
        )
        workflow_process.start()

        self.executor.pid_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        Path(
            self.executor.pid_dir,
            str(workflow_process.pid),
        ).touch()

    def workflow_process(self) -> None:
        """
        Local workflow process.

        Logs workflow start/end and executes the workflow-specific execution()
        implementation.
        """
        try:
            self.logger.log("STARTING WORKFLOW")

            # Keep this cleanup for backwards compatibility when a workflow is
            # started through an older/local caller that did not call
            # _prepare_new_run().
            results_dir = Path(self.workflow_dir, "results")
            if results_dir.exists():
                shutil.rmtree(results_dir)
            results_dir.mkdir(parents=True)

            success = self.execution()
            if success:
                self.logger.log("WORKFLOW FINISHED")
            else:
                self.logger.log("ERROR: WORKFLOW FAILED")

        except Exception as e:
            self.logger.log(f"ERROR: {e}")
            self.logger.log(
                "".join(traceback.format_exception(e))
            )

        shutil.rmtree(
            self.executor.pid_dir,
            ignore_errors=True,
        )

    def _terminal_status_from_log(self) -> str | None:
        """
        Recover a terminal status from minimal.log.

        This is used when an RQ job ID still exists but Redis can no longer
        return the job object (for example after result TTL expiry).
        """
        log_file = Path(
            self.workflow_dir,
            "logs",
            "minimal.log",
        )

        if not log_file.exists():
            return None

        try:
            content = log_file.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return None

        if "WORKFLOW FINISHED" in content:
            return "finished"

        if "WORKFLOW CANCELLED" in content:
            return "canceled"

        if (
            "ERROR: WORKFLOW FAILED" in content
            or "ERROR:" in content
        ):
            return "failed"

        return None

    def get_workflow_status(self) -> dict:
        """
        Get current workflow execution status.

        A temporary Redis/RQ lookup failure does NOT make the UI forget an
        active workflow. If the job object has expired after completion, the
        terminal state is recovered from minimal.log.
        """
        if self._queue_manager and self._queue_manager.is_available:
            job_id = self._queue_manager.load_job_id(
                self.workflow_dir
            )

            if job_id:
                job_info = self._queue_manager.get_job_info(job_id)

                if job_info:
                    is_running = job_info.status.value in [
                        "queued",
                        "started",
                    ]

                    return {
                        "running": is_running,
                        "status": job_info.status.value,
                        "progress": job_info.progress,
                        "current_step": job_info.current_step,
                        "job_id": job_id,
                        "queue_position": job_info.queue_position,
                        "queue_length": job_info.queue_length,
                        "enqueued_at": job_info.enqueued_at,
                        "started_at": job_info.started_at,
                        "result": job_info.result,
                        "error": job_info.error,
                    }

                # Job object is temporarily unavailable or expired.
                terminal_status = self._terminal_status_from_log()

                if terminal_status is not None:
                    # The job has already reached a terminal state. It is safe
                    # to remove the stale stored job ID now.
                    try:
                        self._queue_manager.clear_job_id(
                            self.workflow_dir
                        )
                    except Exception:
                        pass

                    return {
                        "running": False,
                        "status": terminal_status,
                        "progress": 1.0,
                        "current_step": None,
                        "job_id": None,
                        "queue_position": None,
                        "queue_length": None,
                        "enqueued_at": None,
                        "started_at": None,
                        "result": None,
                        "error": None,
                    }

                # IMPORTANT:
                # Do not show Start Workflow during a transient Redis status
                # read failure. Keep the workflow in a temporary/unknown active
                # state and retry on the next fragment refresh.
                return {
                    "running": True,
                    "status": "unknown",
                    "progress": None,
                    "current_step": "Checking workflow status...",
                    "job_id": job_id,
                    "queue_position": None,
                    "queue_length": None,
                    "enqueued_at": None,
                    "started_at": None,
                    "result": None,
                    "error": None,
                }

        # Local-mode fallback: check PID files.
        pid_dir = self.executor.pid_dir
        if pid_dir.exists() and list(pid_dir.iterdir()):
            return {
                "running": True,
                "status": "running",
                "progress": None,
                "current_step": None,
                "job_id": None,
                "queue_position": None,
                "queue_length": None,
                "enqueued_at": None,
                "started_at": None,
                "result": None,
                "error": None,
            }

        terminal_status = self._terminal_status_from_log()
        if terminal_status is not None:
            return {
                "running": False,
                "status": terminal_status,
                "progress": 1.0,
                "current_step": None,
                "job_id": None,
                "queue_position": None,
                "queue_length": None,
                "enqueued_at": None,
                "started_at": None,
                "result": None,
                "error": None,
            }

        return {
            "running": False,
            "status": "idle",
            "progress": None,
            "current_step": None,
            "job_id": None,
            "queue_position": None,
            "queue_length": None,
            "enqueued_at": None,
            "started_at": None,
            "result": None,
            "error": None,
        }

    def stop_workflow(self) -> bool:
        """Stop a queued or local workflow."""
        if self._queue_manager and self._queue_manager.is_available:
            job_id = self._queue_manager.load_job_id(
                self.workflow_dir
            )

            if job_id:
                if self._queue_manager.cancel_job(job_id):
                    self.logger.log("WORKFLOW CANCELLED")
                    shutil.rmtree(
                        self.executor.pid_dir,
                        ignore_errors=True,
                    )
                    return True

        return self._stop_local_workflow()

    def _stop_local_workflow(self) -> bool:
        """Stop locally running workflow process."""
        import os
        import signal
        import subprocess

        pid_dir = self.executor.pid_dir
        if not pid_dir.exists():
            return False

        stopped = False

        for pid_file in list(pid_dir.iterdir()):
            try:
                pid = int(pid_file.name)

                if os.name == "nt":
                    result = subprocess.run(
                        [
                            "taskkill",
                            "/PID",
                            str(pid),
                            "/T",
                            "/F",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    if result.returncode == 0:
                        stopped = True
                    else:
                        self.logger.log(
                            f"Failed to stop process {pid} with taskkill: "
                            f"{result.stderr or result.stdout}"
                        )
                else:
                    os.kill(pid, signal.SIGTERM)
                    stopped = True

            except (
                ValueError,
                ProcessLookupError,
                PermissionError,
                OSError,
            ) as e:
                self.logger.log(
                    "Could not stop process from PID file "
                    f"{pid_file.name}: {e}"
                )
            finally:
                pid_file.unlink(missing_ok=True)

        shutil.rmtree(
            pid_dir,
            ignore_errors=True,
        )

        if stopped:
            self.logger.log("WORKFLOW CANCELLED")

        return stopped

    def show_file_upload_section(self) -> None:
        """Show workflow file-upload UI."""
        self.ui.file_upload_section(self.upload)

    def show_parameter_section(self) -> None:
        """Show workflow parameter UI."""
        self.ui.parameter_section(self.configure)

    def _prepare_execution_ui(self) -> None:
        """
        Optional workflow-specific hook called before the Run UI is rendered.

        Subclasses can override this instead of overriding
        show_execution_section().
        """
        pass

    def _render_post_execution(self) -> None:
        """
        Optional workflow-specific hook for successful post-run UI.

        Examples:
        - NuXL ZIP download
        - Rescoring pseudo-ROC + ZIP download
        - DIA library ZIP download

        Subclasses should override this instead of overriding
        show_execution_section().
        """
        pass

    def _workflow_completed_successfully(
        self,
        status: dict,
    ) -> bool:
        """Return True only when the current workflow completed successfully."""
        if status.get("running", False):
            return False

        job_status = status.get("status", "idle")

        if job_status == "finished":
            result = status.get("result")
            if (
                isinstance(result, dict)
                and result.get("success") is False
            ):
                return False
            return True

        if job_status in {
            "failed",
            "canceled",
            "cancelled",
        }:
            return False

        return self._terminal_status_from_log() == "finished"

    @st.fragment
    def show_execution_section(self) -> None:
        """
        Render the Run section.

        The outer Run fragment itself is static. Automatic polling is handled
        only by the running-workflow fragment inside SafeStreamlitUI.

        This prevents completed outputs such as pseudo-ROC plots and download
        buttons from being reconstructed repeatedly.
        """
        self._prepare_execution_ui()

        self.ui.execution_section(
            start_workflow_function=self.start_workflow,
            get_status_function=self.get_workflow_status,
            stop_workflow_function=self.stop_workflow,
        )

        status = self.get_workflow_status()

        if self._workflow_completed_successfully(status):
            self._render_post_execution()

    def show_results_section(self) -> None:
        """Show workflow result UI."""
        self.ui.results_section(self.results)

    def upload(self) -> None:
        """Add file-upload widgets in subclasses."""
        pass

    def configure(self) -> None:
        """Add parameter widgets in subclasses."""
        pass

    def execution(self) -> bool:
        """Run workflow-specific execution steps."""
        return True

    def results(self) -> None:
        """Display workflow-specific result UI."""
        pass
