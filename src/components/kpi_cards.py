"""Componente de cards de KPI."""

import streamlit as st
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.constants import COLORS

def render_kpi_card(label: str, value: str, icon: str = "", change: str = ""):
    """Renderiza um card de KPI estilizado."""
    kpi_style = f"""
    <style>
    .kpi-card {{
        background: {COLORS['background']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 24px;
        text-align: center;
    }}
    .kpi-icon {{
        font-size: 32px;
        margin-bottom: 8px;
    }}
    .kpi-value {{
        font-size: 36px;
        font-weight: 800;
        color: {COLORS['primary']};
        margin: 8px 0;
    }}
    .kpi-label {{
        font-size: 14px;
        color: {COLORS['muted']};
        margin-top: 4px;
    }}
    .kpi-change {{
        font-size: 12px;
        color: {COLORS['secondary']};
        margin-top: 4px;
    }}
    </style>
    """
    
    st.markdown(kpi_style, unsafe_allow_html=True)
    
    kpi_html = f"""
    <div class="kpi-card">
        {f'<div class="kpi-icon">{icon}</div>' if icon else ''}
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {f'<div class="kpi-change">{change}</div>' if change else ''}
    </div>
    """
    
    st.markdown(kpi_html, unsafe_allow_html=True)

