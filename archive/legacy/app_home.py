"""Página inicial do CapacitIA Dashboard - Home com seleção de módulos."""

import streamlit as st
from pathlib import Path
import pandas as pd
import sys

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

from src.data.loaders import load_all_data
from src.components.module_cards import render_module_card
from src.components.kpi_cards import render_kpi_card
from src.utils.constants import DESCRIPTIONS, COLORS

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="CapacitIA - Plataforma Unificada",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CSS GLOBAL
# =========================
# Carrega o CSS principal
with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()

# Carrega o CSS da home
with open("styles/home.css", "r", encoding="utf-8") as f:
    home_css = f.read()

st.markdown(f"<style>{css_content}{home_css}</style>", unsafe_allow_html=True)

# =========================
# CARREGAR DADOS
# =========================
@st.cache_data(show_spinner=False)
def get_module_kpis():
    """Calcula KPIs de cada módulo."""
    all_data = load_all_data()
    
    kpis = {
        'servidores': {
            'participantes': 0,
            'eventos': 0,
            'extra': '🏆 0 Secretarias',
        },
        'saude': {
            'participantes': 0,
            'eventos': 0,
            'extra': '📅 -',
        },
        'autonomia_digital': {
            'participantes': 0,
            'eventos': 0,
            'extra': '🎯 Inclusão Digital',
        },
    }
    
    # Servidores
    if all_data['servidores']['dados'] is not None:
        df_dados = all_data['servidores']['dados']
        df_visao = all_data['servidores']['visao']
        kpis['servidores']['participantes'] = len(df_dados)
        kpis['servidores']['eventos'] = len(df_visao) - 1 if df_visao is not None else 0  # -1 para remover TOTAL GERAL
        if all_data['servidores']['secretarias'] is not None:
            kpis['servidores']['extra'] = f"🏆 {len(all_data['servidores']['secretarias'])} Secretarias"
    
    # Saúde
    if all_data['saude']['dados'] is not None:
        df_saude = all_data['saude']['dados']
        kpis['saude']['participantes'] = len(df_saude)
        kpis['saude']['eventos'] = df_saude['lote'].nunique() if 'lote' in df_saude.columns else 0
        if len(df_saude) > 0 and 'data' in df_saude.columns:
            kpis['saude']['extra'] = f"📅 {df_saude['data'].iloc[0][:7] if pd.notna(df_saude['data'].iloc[0]) else '-'}"
    
    # Autonomia Digital
    if all_data['autonomia_digital']['inscricoes'] is not None:
        df_inscricoes = all_data['autonomia_digital']['inscricoes']
        df_avaliacoes = all_data['autonomia_digital']['avaliacoes']
        kpis['autonomia_digital']['participantes'] = len(df_inscricoes)
        kpis['autonomia_digital']['eventos'] = len(df_avaliacoes) if df_avaliacoes is not None else 0
    
    return kpis

# =========================
# PÁGINA INICIAL
# =========================
def main():
    # Hero Section
    st.markdown("""
    <div class="hero-section fade-in">
        <div class="hero-title">🚀 CapacitIA</div>
        <div class="hero-subtitle">Plataforma Unificada de Capacitação e Inteligência</div>
        <div class="hero-description">
            Transformando o serviço público através da capacitação e inovação tecnológica
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Carregar KPIs
    with st.spinner("Carregando dados..."):
        kpis = get_module_kpis()
    
    # Cards dos Módulos (3 colunas)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_module_card('servidores', kpis['servidores'])
    
    with col2:
        render_module_card('saude', kpis['saude'])
    
    with col3:
        render_module_card('autonomia_digital', kpis['autonomia_digital'])
    
    # Botão de Visão Unificada
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📊 Ver Visão Unificada - Todos os Módulos", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📊_Visão_Unificada.py")
    
    # Seção Informativa
    st.markdown("""
    <div class="info-section fade-in">
        <div class="info-title">Sobre o CapacitIA</div>
        <div class="info-text">
            {}
        </div>
    </div>
    """.format(DESCRIPTIONS['geral'].strip()), unsafe_allow_html=True)
    
    # KPIs Consolidados
    st.markdown("## 📊 Estatísticas Consolidadas")
    
    all_data = load_all_data()
    total_participantes = (
        (len(all_data['servidores']['dados']) if all_data['servidores']['dados'] is not None else 0) +
        (len(all_data['saude']['dados']) if all_data['saude']['dados'] is not None else 0) +
        (len(all_data['autonomia_digital']['inscricoes']) if all_data['autonomia_digital']['inscricoes'] is not None else 0)
    )
    
    total_eventos = (
        kpis['servidores']['eventos'] +
        kpis['saude']['eventos'] +
        kpis['autonomia_digital']['eventos']
    )
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card("Total de Participantes", f"{total_participantes:,}", "👥")
    
    with col2:
        render_kpi_card("Total de Eventos", str(total_eventos), "📅")
    
    with col3:
        secretarias_count = len(all_data['servidores']['secretarias']) if all_data['servidores']['secretarias'] is not None else 0
        render_kpi_card("Secretarias Envolvidas", str(secretarias_count), "🏢")
    
    with col4:
        # Calcular taxa de certificação (apenas servidores)
        if all_data['servidores']['dados'] is not None:
            df_dados = all_data['servidores']['dados']
            certificados = (df_dados['certificado'] == 'Sim').sum() if 'certificado' in df_dados.columns else 0
            taxa = (certificados / len(df_dados) * 100) if len(df_dados) > 0 else 0
            render_kpi_card("Taxa de Certificação", f"{taxa:.1f}%", "✅")
        else:
            render_kpi_card("Taxa de Certificação", "N/A", "✅")

if __name__ == "__main__":
    main()

