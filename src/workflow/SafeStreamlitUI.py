from collections import deque
from datetime import datetime
from pathlib import Path

import streamlit as st

from .StreamlitUI import (
    StreamlitUI as BaseStreamlitUI,
    _clean_terminal_output,
    _filter_display_log_lines,
)
from ._log_status import classify_log_outcome


class StreamlitUI(BaseStreamlitUI):
    """
    Stable execution UI for long-running NuXLApp workflows.

    All normal file-upload/parameter/result functionality is inherited from
    the existing StreamlitUI. Only Run-tab execution/log behavior is replaced.

    The parent WorkflowManager.show_execution_section() is the auto-refreshing
    fragment. Therefore this class deliberately does NOT create another nested
    live-log fragment.
    """

    LIVE_LOG_MAX_LINES = 500
    STATIC_LOG_MAX_LINES = 1000

    def _read_tail(
        self,
        log_path: Path,
        max_lines: int,
    ) -> list[str]:
        if not log_path.exists():
            return []

        try:
            with open(
                log_path,
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:
                return list(
                    deque(
                        handle,
                        maxlen=max_lines,
                    )
                )
        except OSError:
            return []

    def _read_display_log(
        self,
        log_path: Path,
        log_lines_count,
    ) -> str:
        """Read and clean a bounded part of the workflow log."""
        if log_lines_count == "all":
            max_lines = self.STATIC_LOG_MAX_LINES
        else:
            try:
                max_lines = max(
                    1,
                    int(log_lines_count),
                )
            except (TypeError, ValueError):
                max_lines = self.STATIC_LOG_MAX_LINES

        lines = self._read_tail(
            log_path,
            max_lines,
        )
        lines = _filter_display_log_lines(lines)

        return _clean_terminal_output(
            "".join(lines)
        )

    def _render_live_log_fragment(
        self,
        log_path_string: str,
        get_status_function=None,
    ) -> None:
        """
        Render the current live-log tail.

        This is intentionally a normal method. The surrounding
        WorkflowManager.show_execution_section() fragment refreshes every five
        seconds.
        """
        log_path = Path(log_path_string)

        if not log_path.exists():
            st.info(
                "Waiting for workflow log output..."
            )
            return

        lines = self._read_tail(
            log_path,
            self.LIVE_LOG_MAX_LINES,
        )

        if not lines:
            st.info(
                "Waiting for workflow log output..."
            )
            return

        display_lines = _filter_display_log_lines(
            lines
        )
        display_content = _clean_terminal_output(
            "".join(display_lines)
        )

        if display_content:
            self._render_resizable_log(
                display_content
            )
        else:
            st.info(
                "Waiting for workflow log output..."
            )

        try:
            modified_time = datetime.fromtimestamp(
                log_path.stat().st_mtime
            ).strftime("%H:%M:%S")

            is_online = st.session_state.get(
                "settings", {}
            ).get(
                "online_deployment",
                False,
            )

            time_label = (
                "CET/CEST"
                if is_online
                else "local time"
            )

            st.caption(
                (
                    "Live workflow log."
                ),
                help=(
                    "Long-running workflows may take time to produce output. "
                    f"If nothing updated, please wait. "
                    f"Last fetched: {modified_time} {time_label}"
                ),
            )
        except OSError:
            pass

    def execution_section(
        self,
        start_workflow_function,
        get_status_function=None,
        stop_workflow_function=None,
    ) -> None:
        """
        Render Start/Stop, status and logs.

        Only an active workflow is automatically refreshed. Completed workflow
        output remains static.
        """

        with st.expander("**Summary**"):
            st.markdown(
                self.export_parameters_markdown()
            )

        # -------------------------------------------------------------
        # Read current status
        # -------------------------------------------------------------
        if get_status_function:
            try:
                status = get_status_function() or {}
            except Exception:
                status = {}
        else:
            status = {}

        is_running = status.get(
            "running",
            False,
        )

        job_status = status.get(
            "status",
            "idle",
        )

        # Local PID fallback
        try:
            pid_exists = (
                self.executor.pid_dir.exists()
                and bool(
                    list(
                        self.executor.pid_dir.iterdir()
                    )
                )
            )
        except OSError:
            pid_exists = False

        if not is_running and pid_exists:
            is_running = True
            job_status = "running"

        log_path = Path(
            self.workflow_dir,
            "logs",
            "all.log",
        )

        # =============================================================
        # ACTIVE WORKFLOW
        # =============================================================
        if is_running:
            self._render_running_workflow(
                log_path_string=str(log_path),
                get_status_function=get_status_function,
                stop_workflow_function=stop_workflow_function,
            )
            return

        # =============================================================
        # NOT RUNNING: START BUTTON
        # =============================================================
        c1, _ = st.columns(2)

        if c1.button(
            "Start Workflow",
            type="primary",
            use_container_width=True,
            key="workflow-start-button",
        ):
            start_workflow_function()

            # We are inside the outer Run fragment.
            # Refresh only this fragment, never the complete app.
            st.rerun(scope="fragment")
            return

        # =============================================================
        # STATIC TERMINAL STATE
        # =============================================================
        if job_status in {
            "canceled",
            "cancelled",
        }:
            st.warning(
                "**Workflow was cancelled.**"
            )

        elif job_status == "failed":
            st.error(
                "**Workflow failed.**"
            )

        if not log_path.exists():
            return

        try:
            log_time = datetime.fromtimestamp(
                log_path.stat().st_ctime
            ).strftime("%Y-%m-%d %H:%M")
        except OSError:
            log_time = "unknown"

        st.markdown(
            f"**Workflow log file: {log_time} CET**"
        )

        lines = self._read_tail(
            log_path,
            self.STATIC_LOG_MAX_LINES,
        )

        content = "".join(lines)

        outcome = classify_log_outcome(
            content
        )

        job_result = status.get("result")

        if (
            job_status == "finished"
            and isinstance(job_result, dict)
            and job_result.get("success") is False
        ):
            st.error(
                "**Workflow completed with errors.**"
            )

        elif job_status == "failed":
            st.error(
                "**Workflow failed.**"
            )

        elif job_status in {
            "canceled",
            "cancelled",
        }:
            st.warning(
                "**Workflow was cancelled.**"
            )

        elif outcome == "finished":
            st.success(
                "**Workflow completed successfully.**"
            )

        elif outcome == "cancelled":
            st.warning(
                "**Workflow was cancelled.**"
            )

        else:
            st.error(
                "**Errors occurred, check log file.**"
            )

        display_lines = _filter_display_log_lines(
            lines
        )

        display_content = _clean_terminal_output(
            "".join(display_lines)
        )

        self._render_resizable_log(
            display_content
        )
