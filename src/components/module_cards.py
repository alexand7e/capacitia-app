"""Componente de cards dos módulos para a página inicial."""

import streamlit as st
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.constants import MODULES, COLORS

def render_module_card(module_key: str, kpis: dict = None):
    """Renderiza um card de módulo estilizado."""
    module = MODULES[module_key]
    
    # KPIs padrão se não fornecidos
    if kpis is None:
        kpis = {
            'participantes': 0,
            'eventos': 0,
            'extra': '',
        }
    
    # Estilos inline para o card
    card_style = f"""
    <style>
    .module-card-{module_key} {{
        background: {COLORS['background']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 32px;
        margin: 16px 0;
        transition: all 0.3s ease;
        box-shadow: 0 4px 24px rgba(0,0,0,.25);
    }}
    .module-card-{module_key}:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 32px rgba(125,211,252,.15);
        border-color: {COLORS['primary']};
    }}
    .module-icon-{module_key} {{
        font-size: 64px;
        text-align: center;
        margin-bottom: 16px;
        animation: pulse 2s ease-in-out infinite;
    }}
    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
    }}
    .module-title-{module_key} {{
        font-size: 24px;
        font-weight: 700;
        color: {COLORS['text']};
        text-align: center;
        margin-bottom: 12px;
    }}
    .module-description-{module_key} {{
        font-size: 14px;
        color: {COLORS['muted']};
        text-align: center;
        margin-bottom: 24px;
        line-height: 1.6;
    }}
    .module-kpis-{module_key} {{
        display: flex;
        justify-content: space-around;
        margin: 24px 0;
        padding: 16px 0;
        border-top: 1px solid {COLORS['border']};
        border-bottom: 1px solid {COLORS['border']};
    }}
    .module-kpi-{module_key} {{
        text-align: center;
    }}
    .module-kpi-value-{module_key} {{
        font-size: 20px;
        font-weight: 700;
        color: {COLORS['primary']};
        display: block;
    }}
    .module-kpi-label-{module_key} {{
        font-size: 12px;
        color: {COLORS['muted']};
        margin-top: 4px;
    }}
    .module-button-{module_key} {{
        width: 100%;
        padding: 12px 24px;
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']});
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        font-size: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        text-decoration: none;
        display: block;
    }}
    .module-button-{module_key}:hover {{
        transform: scale(1.02);
        box-shadow: 0 4px 16px rgba(125,211,252,.3);
    }}
    </style>
    """
    
    st.markdown(card_style, unsafe_allow_html=True)
    
    # Renderizar o card
    card_html = f"""
    <div class="module-card-{module_key}">
        <div class="module-icon-{module_key}">{module['icon']}</div>
        <div class="module-title-{module_key}">{module['name']}</div>
        <div class="module-description-{module_key}">{module['description']}</div>
        <div class="module-kpis-{module_key}">
            <div class="module-kpi-{module_key}">
                <span class="module-kpi-value-{module_key}">📊 {kpis['participantes']:,}</span>
                <span class="module-kpi-label-{module_key}">Participantes</span>
            </div>
            <div class="module-kpi-{module_key}">
                <span class="module-kpi-value-{module_key}">✅ {kpis['eventos']}</span>
                <span class="module-kpi-label-{module_key}">Eventos</span>
            </div>
            {f'<div class="module-kpi-{module_key}"><span class="module-kpi-value-{module_key}">{kpis["extra"]}</span></div>' if kpis.get('extra') else ''}
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)
    
    # Botão de navegação
    button_text = f"🔍 Explorar {module['name']}"
    if st.button(button_text, key=f"btn_{module_key}", use_container_width=True):
        try:
            st.switch_page(f"pages/{module['page']}.py")
        except Exception as e:
            st.error(f"Erro ao navegar: {e}")
            st.info(f"Página: pages/{module['page']}.py")

