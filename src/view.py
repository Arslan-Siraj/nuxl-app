import numpy as np
import pandas as pd
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import matplotlib.pyplot as plt
from pyopenms import *

@st.cache_resource
def plot_ms2_spectrum(spec, title, color):
    """
    Takes a pandas Series (spec) and generates a needle plot with m/z and intensity dimension, also annotate ions.

    Args:
        spec: Pandas Series representing the mass spectrum with 
              "mzarray" {ions m/z ratio}, "intarray" {ion intensities} and "anotarray" {ions annotation} columns.
        title: Title of the plot.
        color: Color of the line in the plot.

    Returns:
        A Plotly Figure object representing the needle plot of the mass spectrum.
    """

    # Every Peak is represented by three dots in the line plot: (x, 0), (x, y), (x, 0)
    def create_spectra(x, y, zero=0):
        x = np.repeat(x, 3)
        y = np.repeat(y, 3)
        y[::3] = y[2::3] = zero
        return pd.DataFrame({"mz": x, "intensity": y})

    df = create_spectra(spec["mzarray"], spec["intarray"])
    fig = px.line(df, x="mz", y="intensity")
    fig.update_traces(line_color=color,  line_width=1)
    fig.update_layout(
        showlegend=True,
        title_text=title,
        xaxis_title="m/z",
        yaxis_title="intensity",
        plot_bgcolor="rgb(255,255,255)",
    )
    fig.layout.template = "plotly_white"
    fig.update_yaxes(fixedrange=True)

    # Annotate every line with a string
    for mz, intensity, annotation in zip(spec["mzarray"], spec["intarray"], spec["anotarray"]):
        if intensity < 0.3:
            yshift_ = 60  # Adjust this value for peaks with high intensity
        else:
            yshift_ = 20  # Adjust this value for peaks with low intensity

        # change the annotation colour according to ion-type
        if "MI" in annotation:
            annotation_color = '#ff0000' 
        elif "y" in annotation:
            annotation_color = 'green' 
        elif "[M" in annotation:
            annotation_color = 'darkmagenta'
        else:
            annotation_color = 'blue'  # Default color for other annotations

        #add annotations
        fig.add_annotation(
            x=mz,
            y=intensity,
            text=annotation,
            showarrow=False,
            arrowhead=1,
            arrowcolor=color,
            font=dict(size=12, color=annotation_color),
            xshift=0,
            yshift=yshift_,
            textangle=90 #verticle
        )

    return fig

@st.cache_resource
def plot_ms2_spectrum_full(spec, title, base_color):
    """
    Takes a pandas Series (spec) and generates a needle plot with m/z and intensity dimension, also annotates ions.
    
    Args:
        spec: Pandas Series representing the mass spectrum with 
              "mzarray" {ions m/z ratio}, "intarray" {ion intensities} and "anotarray" {ions annotation} columns.
        title: Title of the plot.
        base_color: Base color for the line.

    Returns:
        A Plotly Figure object representing the needle plot of the mass spectrum.
    """
    
    # Every Peak is represented by three dots in the line plot: (x, 0), (x, y), (x, 0)
    def create_spectra(x, y, zero=0):
        x = np.repeat(x, 3)
        y = np.repeat(y, 3)
        y[::3] = y[2::3] = zero
        return pd.DataFrame({"mz": x, "intensity": y})

    df = create_spectra(spec["mzarray"], spec["intarray"])

    # Create a scatter plot with the base color
    fig = go.Figure()

    # Add base line with a meaningful name
    fig.add_trace(go.Scatter(
        x=df["mz"], y=df["intensity"], 
        mode='lines', 
        line=dict(color=base_color, width=1),
        name='Annotated peaks'  
    ))

    # Annotate every line with a string if annotation exists
    for mz, intensity, annotation in zip(spec["mzarray"], spec["intarray"], spec["anotarray"]):
        if pd.isna(annotation) or annotation.strip() == "":
            continue  # Skip annotation if it's missing or empty

        if intensity < 0.3:
            yshift_ = 60  # Adjust this value for peaks with high intensity
        else:
            yshift_ = 20  # Adjust this value for peaks with low intensity

        # Change the annotation color according to ion-type
        if "MI" in annotation:
            annotation_color = '#ff0000'  # Red for MI
        elif "y" in annotation:
            annotation_color = 'green'  # Green for y
        elif "[M" in annotation:
            annotation_color = 'darkmagenta'  # Dark Magenta for M
        else:
            annotation_color = 'blue'  # Default color for other annotations

        # Add annotation
        fig.add_annotation(
            x=mz,
            y=intensity,
            text=annotation,
            showarrow=False,
            arrowhead=1,
            arrowcolor=annotation_color,
            font=dict(size=12, color=annotation_color),
            xshift=0,
            yshift=yshift_,
            textangle=90  # Vertical
        )

        # Add a vertical line at the position of the peak with the annotation color
        fig.add_trace(go.Scatter(
            x=[mz, mz],
            y=[0, intensity],
            mode='lines',
            line=dict(color=annotation_color, width=1),
            showlegend=False
        ))

    fig.update_layout(
        showlegend=True,
        title_text=title,
        xaxis_title="m/z",
        yaxis_title="intensity",
        plot_bgcolor="rgb(255,255,255)",
    )
    fig.layout.template = "plotly_white"
    fig.update_yaxes(fixedrange=True)

    return fig


def plot_FDR_plot(idXML_id, idXML_extra, exp_name= "FileName", FDR_level=10):
    """
    FDR plot of two input idXML identification files
    idXML_id: without extra feature
    idXML_extra: with extra feature
    FDR_level: 10 for 0.01, 20 for 0.02, 100 for 1.0
    """

    # ---------- Without extra features ----------
    protein_ids = []
    peptide_ids = []
    IdXMLFile().load(idXML_id, protein_ids, peptide_ids)

    Psm_score_list = []
    for pep_id in peptide_ids:
        for hit in pep_id.getHits():
            Psm_score_list.append(float(hit.getScore()))

    list_results = []
    q_values = []
    x = -0.0002
    for _ in range(10001):
        list_results.append(sum(j < x for j in Psm_score_list))
        q_values.append(x)
        x += 0.0001

    # ---------- With extra features ----------
    protein_ids_extra = []
    peptide_ids_extra = []
    IdXMLFile().load(idXML_extra, protein_ids_extra, peptide_ids_extra)

    Psm_score_list_extra = []
    for pep_id in peptide_ids_extra:
        for hit in pep_id.getHits():
            Psm_score_list_extra.append(float(hit.getScore()))

    list_results_extra = []
    q_values_extra = []
    x = -0.0002
    len_3000 = 0

    for i in range(100001):
        values = sum(j < x for j in Psm_score_list_extra)
        list_results_extra.append(values)
        q_values_extra.append(x)
        x += 0.0001
        if i == 3000:
            len_3000 = values

    psms_count_1_per_solely = np.sum(np.array(Psm_score_list) < 0.01)
    psms_count_1_per_extra = np.sum(np.array(Psm_score_list_extra) < 0.01)

     # ---------- Plot ----------
    fig, ax = plt.subplots(figsize=(8, 7))

    ax.plot(q_values, list_results,
            color="red", label="no extra feat", linewidth=1.0)
    ax.plot(q_values_extra, list_results_extra,
            color="blue", label="extra feat", linewidth=1.0)

    ax.axvline(x=0.01, color="green", linewidth=1.0)
    ax.set_title(f"{exp_name}\nNuXL: {psms_count_1_per_solely} +extra: {psms_count_1_per_extra} CSMs at 1% CSM-level FDR", fontsize=12)
    ax.set_xlabel("CSM-level q-value", fontsize=12)
    ax.set_ylabel("no. of CSMs", fontsize=12)

    if FDR_level == 10:
        ax.set_xlim(-0.01, 0.1)
        ax.set_ylim(0, len_3000)
    elif FDR_level == 20:
        ax.set_xlim(-0.01, 0.2) 
        ax.set_ylim(0, len_3000)
    elif FDR_level == 100:
        ax.set_xlim(-0.01, 1.0)    
    
    ax.legend()

    # ---------- Save figure (no os used) ----------
    output_pdf = idXML_extra.replace(".idXML", "") + "_rescore_comparsion.pdf"
    fig.savefig(output_pdf, format="pdf", bbox_inches="tight")

    # ---------- Render in Streamlit ----------
    #st.pyplot(fig)
    return fig, output_pdf
    