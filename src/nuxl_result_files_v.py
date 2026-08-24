"""
Versioned NuXL result-file helpers.

This module intentionally adds only _v functions so the existing
src.nuxl_result_files module can remain unchanged.
"""

from io import StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
from pyopenms import IdXMLFile


@st.cache_resource(
    show_spinner="Reading idXML...",
    max_entries=8,
)
def readAndProcessIdXML_cached_v(
    input_file_str: str,
    file_mtime: float,
    top: int = 1,
):
    """
    Convert an idXML identification file to a dataframe and cache the result.

    The file modification time is part of the cache key, so the cache is
    invalidated automatically when the idXML file changes.

    cache_resource is intentional here because idXML result dataframes can
    become very large, especially for 1.0000 output. The result dataframe is
    treated as read-only by the Result Viewer.
    """
    input_file = Path(input_file_str)

    prot_ids = []
    pep_ids = []

    IdXMLFile().load(
        str(input_file),
        prot_ids,
        pep_ids,
    )

    meta_value_keys = []
    rows = []
    all_columns = None

    if len(pep_ids) == 0:
        return None

    for peptide_id in pep_ids:
        spectrum_id = peptide_id.getMetaValue(
            "spectrum_reference"
        )

        scan_nr = spectrum_id[
            spectrum_id.rfind("=") + 1:
        ]

        hits = peptide_id.getHits()

        for psm_index, h in enumerate(
            hits[:top],
            start=1,
        ):
            charge = h.getCharge()
            score = h.getScore()

            z2 = int(charge == 2)
            z3 = int(charge == 3)
            z4 = int(charge == 4)
            z5 = int(charge == 5)

            label = int(
                "target"
                in h.getMetaValue("target_decoy")
            )

            sequence = h.getSequence().toString()

            if len(meta_value_keys) == 0:
                h.getKeys(meta_value_keys)

                meta_value_keys = [
                    x.decode()
                    for x in meta_value_keys
                ]

                all_columns = [
                    "SpecId",
                    "PSMId",
                    "Label",
                    "Score",
                    "ScanNr",
                    "Peptide",
                    "peplen",
                    "ExpMass",
                    "charge2",
                    "charge3",
                    "charge4",
                    "charge5",
                    "accessions",
                    "intensities",
                    "mz_values",
                    "ions",
                ] + meta_value_keys

            accessions = ";".join(
                [
                    s.decode()
                    for s
                    in h.extractProteinAccessionsSet()
                ]
            )

            peak_annotation = h.getPeakAnnotations()

            intensities = ",".join(
                str(peak.intensity)
                for peak in peak_annotation
            )

            mz_values = ",".join(
                str(peak.mz)
                for peak in peak_annotation
            )

            ions = ",".join(
                str(peak.annotation)
                for peak in peak_annotation
            )

            row = [
                spectrum_id,
                psm_index,
                label,
                score,
                scan_nr,
                sequence,
                str(len(sequence)),
                peptide_id.getMZ(),
                z2,
                z3,
                z4,
                z5,
                accessions,
                intensities,
                mz_values,
                ions,
            ]

            for k in meta_value_keys:
                s = h.getMetaValue(k)

                if isinstance(s, bytes):
                    s = s.decode()

                row.append(s)

            rows.append(row)

            # Preserve previous behavior:
            # only parse the first hit.
            break

    df = pd.DataFrame(
        rows,
        columns=all_columns,
    )

    convert_dict = {
        "SpecId": str,
        "PSMId": int,
        "Label": int,
        "Score": float,
        "ScanNr": int,
        "peplen": int,
    }

    return df.astype(convert_dict)


def readAndProcessIdXML_v(
    input_file,
    top: int = 1,
):
    """
    Cache-safe public wrapper for idXML parsing.
    """
    input_file = Path(input_file)

    return readAndProcessIdXML_cached_v(
        str(input_file.resolve()),
        input_file.stat().st_mtime,
        top,
    )


@st.cache_data(
    show_spinner="Reading protein table..."
)
def read_protein_table_cached_v(
    input_file_str: str,
    file_mtime: float,
):
    """
    Parse a NuXL protein TSV report into section dataframes and cache it.
    """
    input_file = Path(input_file_str)

    section_dfs = []
    current_section = []

    skip_next_line = False
    use_next_line_as_header = False

    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()

            if (
                line.startswith("==")
                and line.endswith("==")
            ):
                if current_section:
                    if use_next_line_as_header:
                        try:
                            section_df = pd.read_csv(
                                StringIO(
                                    "\n".join(
                                        current_section[1:]
                                    )
                                ),
                                delimiter="\t",
                                header=None,
                            )

                            section_df.columns = (
                                current_section[0]
                                .split("\t")
                            )

                        except pd.errors.EmptyDataError:
                            section_df = pd.DataFrame(
                                columns=(
                                    current_section[0]
                                    .split("\t")
                                )
                            )

                        section_dfs.append(
                            section_df
                        )

                        use_next_line_as_header = False

                    else:
                        try:
                            section_df = pd.read_csv(
                                StringIO(
                                    "\n".join(
                                        current_section
                                    )
                                ),
                                delimiter="\t",
                            )

                        except pd.errors.EmptyDataError:
                            section_df = pd.DataFrame()

                        section_dfs.append(
                            section_df
                        )

                    current_section = []
                    skip_next_line = True

            else:
                if not skip_next_line:
                    current_section.append(
                        line
                    )

                skip_next_line = False

                if (
                    line.startswith(
                        "Protein summary"
                    )
                    or line.startswith(
                        "Crosslink efficiency"
                    )
                    or line.startswith(
                        "Precursor adduct summary"
                    )
                ):
                    use_next_line_as_header = True

                if line.startswith(
                    "Crosslink efficiency"
                ):
                    use_next_line_as_header = False

                    header_line = next(f).strip()

                    header = [
                        "AA",
                        "Crosslink efficiency",
                    ]

                    current_section.append(
                        header_line
                    )

                    current_section[0] = (
                        "\t".join(header)
                    )

    if current_section:
        try:
            section_df = pd.read_csv(
                StringIO(
                    "\n".join(
                        current_section
                    )
                ),
                delimiter="\t",
            )

        except pd.errors.EmptyDataError:
            section_df = pd.DataFrame()

        section_dfs.append(
            section_df
        )

    return section_dfs


def read_protein_table_v(
    input_file,
):
    """
    Cache-safe public wrapper for protein TSV parsing.
    """
    input_file = Path(input_file)

    return read_protein_table_cached_v(
        str(input_file.resolve()),
        input_file.stat().st_mtime,
    )