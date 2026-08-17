"""
NuXLApp resource-limited runner for nuxl_rescore.

This wrapper does NOT modify the installed nuxl_rescore package.

It limits:
1. DeepLC multiprocessing
2. MS2PIP multiprocessing
3. TensorFlow / BLAS / OpenMP thread fan-out

The scientific workflow, models, features, and Percolator execution remain
unchanged. Only computational parallelism is constrained.
"""

from __future__ import annotations

import multiprocessing
import os
import sys


# -------------------------------------------------------------------------
# Resource configuration
# -------------------------------------------------------------------------

def _get_process_limit() -> int:
    """
    Maximum number of Python worker processes allowed for NuXL rescoring.

    Can be overridden by setting:
        NUXL_RESCORE_MAX_PROCESSES

    Default = 1, which is safest for hosted Docker deployments.
    """
    value = os.environ.get("NUXL_RESCORE_MAX_PROCESSES", "2")

    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 1

    return max(1, value)


MAX_PROCESSES = _get_process_limit()


# -------------------------------------------------------------------------
# Limit native numerical-library thread fan-out.
#
# IMPORTANT:
# Use direct assignment, NOT setdefault().
#
# A Docker/base environment may already contain values such as
# OPENBLAS_NUM_THREADS=32. setdefault() would leave that unchanged.
# -------------------------------------------------------------------------

_THREAD_LIMITS = {
    "OMP_NUM_THREADS": "1",
    "OMP_THREAD_LIMIT": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "BLIS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "NUMEXPR_MAX_THREADS": "1",
    "TF_NUM_INTRAOP_THREADS": "1",
    "TF_NUM_INTEROP_THREADS": "1",
    "TF_CPP_MIN_LOG_LEVEL": "2",
    "MALLOC_ARENA_MAX": "2",
}

for _name, _value in _THREAD_LIMITS.items():
    os.environ[_name] = _value


# -------------------------------------------------------------------------
# DeepLC protection
#
# DeepLC 1.2.1 uses multiprocessing.cpu_count() when n_jobs is not supplied.
# nuxl_rescore 0.2.0 does not pass n_jobs.
#
# Therefore make cpu_count() report only the allowed number of processes
# inside THIS subprocess.
#
# This does not modify Python globally or change the installed packages.
# -------------------------------------------------------------------------

_REAL_CPU_COUNT = multiprocessing.cpu_count


def _limited_cpu_count() -> int:
    try:
        available = _REAL_CPU_COUNT()
    except Exception:
        available = 1

    if available is None:
        available = 1

    return max(1, min(int(available), MAX_PROCESSES))


multiprocessing.cpu_count = _limited_cpu_count


# -------------------------------------------------------------------------
# NuXL-rescore MS2PIP protection
# -------------------------------------------------------------------------

def _patch_ms2pip_limits() -> None:
    """
    Patch nuxl_rescore's MS2PIP configuration in memory.

    nuxl_rescore 0.2.0 initializes:
        processes = 32
        num_cpu   = 32

    We leave the package files untouched and replace only the values used
    during this process.
    """

    import nuxl_rescore.ms2pip_features as ms2pip_features

    # First patch the module-level configuration.
    try:
        section = ms2pip_features.CONFIG.setdefault("ms2rescore", {})
        section["processes"] = MAX_PROCESSES
        section["num_cpu"] = MAX_PROCESSES
    except Exception:
        pass

    # nuxl_rescore's initialize function recreates CONFIG and puts 32 back
    # into it, so wrap that function as well.
    original_initialize = ms2pip_features.initilize_CONFIG

    def limited_initialize_CONFIG(
        mgf_file: str,
        out_pin_file: str,
        psm_file: str,
    ):
        config = original_initialize(
            mgf_file,
            out_pin_file,
            psm_file,
        )

        section = config.setdefault("ms2rescore", {})
        section["processes"] = MAX_PROCESSES
        section["num_cpu"] = MAX_PROCESSES

        # Keep module-level CONFIG synchronized as expected by nuxl_rescore.
        ms2pip_features.CONFIG = config

        print(
            "NuXLApp resource guard: "
            f"MS2PIP processes={MAX_PROCESSES}, "
            f"num_cpu={MAX_PROCESSES}",
            flush=True,
        )

        return config

    ms2pip_features.initilize_CONFIG = limited_initialize_CONFIG


# -------------------------------------------------------------------------
# Run original NuXL-rescore CLI
# -------------------------------------------------------------------------

def main() -> None:
    print(
        "NuXLApp resource guard enabled: "
        f"maximum Python processes={MAX_PROCESSES}",
        flush=True,
    )

    print(
        "NuXLApp resource guard: "
        "TensorFlow/BLAS/OpenMP threads=1",
        flush=True,
    )

    # Patch MS2PIP after our multiprocessing limit has already been installed.
    _patch_ms2pip_limits()

    # Run exactly the original nuxl_rescore CLI.
    from nuxl_rescore.main import main as nuxl_rescore_main

    nuxl_rescore_main()


if __name__ == "__main__":
    main()