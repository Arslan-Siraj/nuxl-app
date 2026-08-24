"""
NuXLApp resource-limited runner for nuxl_rescore.

This wrapper does NOT modify the installed nuxl_rescore package.

Resource configuration:
- DeepLC: 1 worker
- MS2PIP intensity prediction: 4 CPUs
- MS2Rescore process pool: 1 process
- BLAS / TensorFlow / OpenMP threads: 1
"""

from __future__ import annotations

import os


# -------------------------------------------------------------------------
# Resource limits
# -------------------------------------------------------------------------

DEEPLC_N_JOBS = max(
    1,
    int(os.environ.get("NUXL_DEEPLC_N_JOBS", "1")),
)

MS2PIP_NUM_CPU = max(
    1,
    int(os.environ.get("NUXL_MS2PIP_NUM_CPU", "4")),
)

MS2RESCORE_PROCESSES = max(
    1,
    int(os.environ.get("NUXL_MS2RESCORE_PROCESSES", "1")),
)


# -------------------------------------------------------------------------
# Limit native numerical-library thread fan-out
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
# -------------------------------------------------------------------------

def _patch_deeplc() -> None:
    """
    Force DeepLC to use a limited number of worker processes.

    NuXL-rescore 0.2.0 constructs DeepLC without specifying n_jobs.
    Instead of globally modifying multiprocessing.cpu_count(), patch only
    the DeepLC constructor used by nuxl_rescore.RT_features.
    """

    import nuxl_rescore.RT_features as rt_features
    from deeplc import DeepLC as OriginalDeepLC

    def LimitedDeepLC(*args, **kwargs):
        kwargs["n_jobs"] = DEEPLC_N_JOBS

        
        return OriginalDeepLC(*args, **kwargs)

    rt_features.DeepLC = LimitedDeepLC


# -------------------------------------------------------------------------
# MS2PIP protection
# -------------------------------------------------------------------------

def _patch_ms2pip_limits() -> None:
    """
    Configure NuXL-rescore MS2PIP resources in memory.

    MS2PIP intensity prediction:
        num_cpu = 4

    MS2Rescore feature-generator process pool:
        processes = 1

    The installed nuxl_rescore package is not modified.
    """

    import nuxl_rescore.ms2pip_features as ms2pip_features

    # Patch current module-level CONFIG.
    try:
        section = ms2pip_features.CONFIG.setdefault(
            "ms2rescore",
            {},
        )

        section["num_cpu"] = MS2PIP_NUM_CPU
        section["processes"] = MS2RESCORE_PROCESSES

    except Exception:
        pass

    # NuXL-rescore recreates CONFIG inside initilize_CONFIG(),
    # so wrap that function to reapply our limits afterward.
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

        section = config.setdefault(
            "ms2rescore",
            {},
        )

        # MS2PIP prediction itself
        section["num_cpu"] = MS2PIP_NUM_CPU

        # Separate MS2Rescore FeatureGenerator process count
        section["processes"] = MS2RESCORE_PROCESSES

        # Keep module-level CONFIG synchronized.
        ms2pip_features.CONFIG = config

        return config

    ms2pip_features.initilize_CONFIG = limited_initialize_CONFIG


# -------------------------------------------------------------------------
# Run original NuXL-rescore CLI
# -------------------------------------------------------------------------

def main() -> None:

    _patch_deeplc()
    _patch_ms2pip_limits()

    # Run original NuXL-rescore CLI unchanged.
    from nuxl_rescore.main import main as nuxl_rescore_main

    nuxl_rescore_main()


if __name__ == "__main__":
    main()