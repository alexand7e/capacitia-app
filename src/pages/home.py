"""Lógica da página inicial (Home)."""

import streamlit as st
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.loaders import load_all_data
from src.components.module_cards import render_module_card
from src.utils.constants import TEXTS, MODULES

def calculate_kpis(data: dict) -> dict:
    """Calcula KPIs para cada módulo."""
    kpis = {}
    
    # KPIs Servidores
    if data.get('servidores') and data['servidores'].get('dados') is not None:
        df_dados = data['servidores']['dados']
        df_visao = data['servidores']['visao']
        kpis['servidores'] = {
            'participantes': len(df_dados) if df_dados is not None else 0,
            'eventos': len(df_visao) - 1 if df_visao is not None else 0,  # -1 para remover TOTAL GERAL
            'extra': f"🏆 {df_dados['orgao'].nunique() if df_dados is not None else 0} Secretarias",
        }
    else:
        kpis['servidores'] = {'participantes': 0, 'eventos': 0, 'extra': ''}
    
    # KPIs Saúde
    if data.get('saude') and data['saude'].get('dados') is not None:
        df_saude = data['saude']['dados']
        lotes_count = df_saude['lote'].nunique() if df_saude is not None and 'lote' in df_saude.columns else 0
        kpis['saude'] = {
            'participantes': len(df_saude) if df_saude is not None else 0,
            'eventos': lotes_count,
            'extra': f'📅 {lotes_count} Lotes',
        }
    else:
        kpis['saude'] = {'participantes': 0, 'eventos': 0, 'extra': ''}
    
    # KPIs Autonomia Digital
    if data.get('autonomia_digital'):
        df_inscricoes = data['autonomia_digital'].get('inscricoes')
        df_avaliacoes = data['autonomia_digital'].get('avaliacoes')
        # Contar eventos únicos por projeto de extensão
        eventos_count = 0
        if df_inscricoes is not None:
            projeto_col = [c for c in df_inscricoes.columns if 'projeto' in c.lower() and 'extensao' in c.lower()][0] if any('projeto' in c.lower() and 'extensao' in c.lower() for c in df_inscricoes.columns) else None
            if projeto_col:
                eventos_count = df_inscricoes[projeto_col].dropna().nunique()
            else:
                eventos_count = 1  # Fallback
        
        kpis['autonomia_digital'] = {
            'participantes': len(df_inscricoes) if df_inscricoes is not None else 0,
            'eventos': eventos_count,
            'extra': '🎯 Inclusão Digital',
        }
    else:
        kpis['autonomia_digital'] = {'participantes': 0, 'eventos': 0, 'extra': ''}
    
    return kpis

def render_home_page():
    """Renderiza a página inicial."""
    # Carregar dados
    with st.spinner("Carregando dados..."):
        data = load_all_data()
        kpis = calculate_kpis(data)
    
    # Hero Section
    st.markdown("""
    <div class="hero">
        <h1 style="font-size: 48px; font-weight: 800; margin-bottom: 16px; text-align: center;">
            🚀 CapacitIA
        </h1>
        <h2 style="font-size: 24px; font-weight: 600; color: var(--muted); text-align: center; margin-bottom: 8px;">
            Plataforma Unificada de Capacitação e Inteligência
        </h2>
        <p style="font-size: 16px; color: var(--muted); text-align: center; line-height: 1.6;">
            Transformando o serviço público através da capacitação e inovação tecnológica
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Cards dos Módulos (3 colunas)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_module_card('servidores', kpis.get('servidores', {}))
    
    with col2:
        render_module_card('saude', kpis.get('saude', {}))
    
    with col3:
        render_module_card('autonomia_digital', kpis.get('autonomia_digital', {}))
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botão de Visão Unificada
    st.markdown("""
    <div style="text-align: center; margin: 32px 0;">
    </div>
    """, unsafe_allow_html=True)
    
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
        kpis.get('servidores', {}).get('participantes', 0) +
        kpis.get('saude', {}).get('participantes', 0) +
        kpis.get('autonomia_digital', {}).get('participantes', 0)
    )
    
    total_eventos = (
        kpis.get('servidores', {}).get('eventos', 0) +
        kpis.get('saude', {}).get('eventos', 0) +
        kpis.get('autonomia_digital', {}).get('eventos', 0)
    )
    
    with col1:
        st.metric("Total de Participantes", f"{total_participantes:,}")
    
    with col2:
        st.metric("Total de Eventos", total_eventos)
    
    with col3:
        st.metric("Módulos Ativos", "3")
    
    with col4:
        st.metric("Secretarias Envolvidas", kpis.get('servidores', {}).get('extra', '0').split()[1] if 'Secretarias' in kpis.get('servidores', {}).get('extra', '') else '0')

