"""Página inicial do CapacitIA Dashboard - Home com seleção de módulos."""

import streamlit as st
from pathlib import Path
import sys

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent))

from src.data.loaders import load_all_data
from src.components.module_cards import render_module_card
from src.utils.constants import TEXTS, DESCRIPTIONS, COLORS

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

# Carrega o CSS da home (se existir)
try:
    with open("styles/home.css", "r", encoding="utf-8") as f:
        home_css = f.read()
except FileNotFoundError:
    home_css = ""

st.markdown(f"<style>{css_content}{home_css}</style>", unsafe_allow_html=True)

# =========================
# CARREGAR DADOS E CALCULAR KPIs
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
        kpis['servidores']['eventos'] = len(df_visao) - 1 if df_visao is not None and len(df_visao) > 0 else 0
        if all_data['servidores']['secretarias'] is not None:
            kpis['servidores']['extra'] = f"🏆 {len(all_data['servidores']['secretarias'])} Secretarias"
    
    # Saúde
    if all_data['saude']['dados'] is not None:
        df_saude = all_data['saude']['dados']
        kpis['saude']['participantes'] = len(df_saude)
        lotes_count = df_saude['lote'].nunique() if 'lote' in df_saude.columns else 0
        kpis['saude']['eventos'] = lotes_count
        # A coluna 'data' contém texto descritivo, não uma data real
        # Usar informação mais útil: número de lotes
        kpis['saude']['extra'] = f"📅 {lotes_count} Lotes"
    
    # Autonomia Digital
    if all_data['autonomia_digital']['inscricoes'] is not None:
        df_inscricoes = all_data['autonomia_digital']['inscricoes']
        df_avaliacoes = all_data['autonomia_digital']['avaliacoes']
        kpis['autonomia_digital']['participantes'] = len(df_inscricoes)
        # Contar eventos únicos por projeto de extensão
        projeto_col = [c for c in df_inscricoes.columns if 'projeto' in c.lower() and 'extensao' in c.lower()][0] if any('projeto' in c.lower() and 'extensao' in c.lower() for c in df_inscricoes.columns) else None
        if projeto_col:
            eventos_unicos = df_inscricoes[projeto_col].dropna().nunique()
            kpis['autonomia_digital']['eventos'] = eventos_unicos
        else:
            kpis['autonomia_digital']['eventos'] = 1  # Fallback
    
    return kpis

# =========================
# PÁGINA INICIAL
# =========================
def main():
    # Hero Section
    st.markdown(f"""
    <div class="hero" style="text-align: center; padding: 48px 24px;">
        <h1 style="font-size: 56px; font-weight: 800; margin-bottom: 16px; color: {COLORS['text']};">
            🚀 CapacitIA
        </h1>
        <h2 style="font-size: 28px; font-weight: 600; color: {COLORS['muted']}; margin-bottom: 12px;">
            Plataforma Unificada de Capacitação e Inteligência
        </h2>
        <p style="font-size: 18px; color: {COLORS['muted']}; line-height: 1.6; max-width: 800px; margin: 0 auto;">
            Transformando o serviço público através da capacitação e inovação tecnológica
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botão de Visão Unificada
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("📊 Ver Visão Unificada - Todos os Módulos", use_container_width=True, type="primary"):
            st.switch_page("pages/1_📊_Visão_Unificada.py")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Seção Informativa
    with st.expander("ℹ️ Sobre o Programa CapacitIA", expanded=False):
        st.markdown(TEXTS['sobre_capacitia'])
    
    # Estatísticas Consolidadas
    st.markdown("### 📊 Estatísticas Consolidadas")
    col1, col2, col3, col4 = st.columns(4)
    
    total_participantes = (
        kpis['servidores']['participantes'] +
        kpis['saude']['participantes'] +
        kpis['autonomia_digital']['participantes']
    )
    
    total_eventos = (
        kpis['servidores']['eventos'] +
        kpis['saude']['eventos'] +
        kpis['autonomia_digital']['eventos']
    )
    
    secretarias_count = 0
    if '🏆' in kpis['servidores']['extra']:
        try:
            secretarias_count = int(kpis['servidores']['extra'].split()[1])
        except:
            pass
    
    with col1:
        st.metric("Total de Participantes", f"{total_participantes:,}")
    
    with col2:
        st.metric("Total de Eventos", total_eventos)
    
    with col3:
        st.metric("Módulos Ativos", "3")
    
    with col4:
        st.metric("Secretarias Envolvidas", secretarias_count)

if __name__ == "__main__":
    main()
