"""Utilitários de tema: CSS e Plotly."""

from pathlib import Path
import streamlit as st
import plotly.io as pio


def setup_plotly_theme():
    pio.templates["capacit_light"] = pio.templates["plotly_white"]
    pio.templates["capacit_light"].layout.font.family = "Montserrat, Inter, Segoe UI, Arial"
    pio.templates["capacit_light"].layout.colorway = [
        "#034EA2", "#FDB913", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#E53935"
    ]
    pio.templates["capacit_light"].layout.paper_bgcolor = "#FFFFFF"
    pio.templates["capacit_light"].layout.plot_bgcolor = "#F2F2F2"
    pio.templates["capacit_light"].layout.hoverlabel = dict(
        bgcolor="#FFFFFF", font_size=12, font_family="Montserrat, Inter, Segoe UI, Arial"
    )
    pio.templates.default = "capacit_light"


def load_main_css(base_path: Path):
    with open(base_path / "styles" / "main.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
