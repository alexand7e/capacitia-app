"""Página inicial do CapacitIA Dashboard - Home com seleção de módulos."""

import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.data.loaders import load_all_data
from src.components.module_cards import render_module_card
from src.utils.constants import TEXTS, DESCRIPTIONS, COLORS

st.set_page_config(
    page_title="CapacitIA - Plataforma Unificada",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",   # ← sidebar aberta para o usuário ver as páginas
)

with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()

try:
    with open("styles/home.css", "r", encoding="utf-8") as f:
        home_css = f.read()
except FileNotFoundError:
    home_css = ""

st.markdown(f"<style>{css_content}{home_css}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_module_kpis():
    all_data = load_all_data()

    kpis = {
        'servidores':       {'participantes': 0, 'eventos': 0, 'extra': '🏆 0 Secretarias'},
        'saude':            {'participantes': 0, 'eventos': 0, 'extra': '📅 -'},
        'autonomia_digital':{'participantes': 0, 'eventos': 0, 'extra': '🎯 Inclusão Digital'},
    }

    if all_data['servidores']['dados'] is not None:
        df_dados = all_data['servidores']['dados']
        df_visao = all_data['servidores']['visao']
        kpis['servidores']['participantes'] = len(df_dados)
        kpis['servidores']['eventos'] = len(df_visao) - 1 if df_visao is not None and len(df_visao) > 0 else 0
        if all_data['servidores']['secretarias'] is not None:
            kpis['servidores']['extra'] = f"🏆 {len(all_data['servidores']['secretarias'])} Secretarias"

    if all_data['saude']['dados'] is not None:
        df_saude = all_data['saude']['dados']
        kpis['saude']['participantes'] = len(df_saude)
        lotes_count = df_saude['lote'].nunique() if 'lote' in df_saude.columns else 0
        kpis['saude']['eventos'] = lotes_count
        kpis['saude']['extra'] = f"📅 {lotes_count} Lotes"

    if all_data['autonomia_digital']['inscricoes'] is not None:
        df_inscricoes = all_data['autonomia_digital']['inscricoes']
        kpis['autonomia_digital']['participantes'] = len(df_inscricoes)
        projeto_col = next(
            (c for c in df_inscricoes.columns if 'projeto' in c.lower() and 'extensao' in c.lower()),
            None,
        )
        kpis['autonomia_digital']['eventos'] = (
            df_inscricoes[projeto_col].dropna().nunique() if projeto_col else 1
        )

    return kpis


def main():
    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="hero" style="text-align:center;padding:48px 24px;">
        <h1 style="font-size:56px;font-weight:800;margin-bottom:16px;color:{COLORS['text']};">
            🚀 CapacitIA
        </h1>
        <h2 style="font-size:28px;font-weight:600;color:{COLORS['muted']};margin-bottom:12px;">
            Plataforma Unificada de Capacitação e Inteligência
        </h2>
        <p style="font-size:18px;color:{COLORS['muted']};line-height:1.6;max-width:800px;margin:0 auto;">
            Transformando o serviço público através da capacitação e inovação tecnológica
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.spinner("Carregando dados..."):
        kpis = get_module_kpis()

    # ── Cards dos 3 módulos ───────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        render_module_card('servidores', kpis['servidores'])
    with col2:
        render_module_card('saude', kpis['saude'])
    with col3:
        render_module_card('autonomia_digital', kpis['autonomia_digital'])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Botões de navegação rápida ────────────────────────────────────────
    st.markdown("### 🧭 Navegação Rápida")

    nav1, nav2 = st.columns(2)

    with nav1:
        if st.button(
            "📊 Visão Unificada — Todos os Módulos",
            use_container_width=True,
            type="primary",
            key="btn_visao_unificada",
        ):
            st.switch_page("pages/1_📊_Visão_Unificada.py")

    with nav2:
        if st.button(
            "📈 Evolução Temporal — Linha do Tempo",
            use_container_width=True,
            type="primary",
            key="btn_evolucao",
        ):
            st.switch_page("pages/5_📈_Evolução_Temporal.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sobre ─────────────────────────────────────────────────────────────
    with st.expander("ℹ️ Sobre o Programa CapacitIA", expanded=False):
        st.markdown(TEXTS['sobre_capacitia'])

    # ── Estatísticas Consolidadas ──────────────────────────────────────────
    st.markdown("### 📊 Estatísticas Consolidadas")
    col1, col2, col3, col4 = st.columns(4)

    total_participantes = (
        kpis['servidores']['participantes']
        + kpis['saude']['participantes']
        + kpis['autonomia_digital']['participantes']
    )
    total_eventos = (
        kpis['servidores']['eventos']
        + kpis['saude']['eventos']
        + kpis['autonomia_digital']['eventos']
    )
    secretarias_count = 0
    if '🏆' in kpis['servidores']['extra']:
        try:
            secretarias_count = int(kpis['servidores']['extra'].split()[1])
        except Exception:
            pass

    with col1:
        st.metric("Total de Participantes", f"{total_participantes:,}")
    with col2:
        st.metric("Total de Eventos", total_eventos)
    with col3:
        st.metric("Módulos Ativos", "3")
    with col4:
        st.metric("Secretarias Envolvidas", secretarias_count)

    # ── Dica sobre a sidebar ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.info(
        "💡 **Dica:** todas as páginas também ficam disponíveis na **barra lateral esquerda** — "
        "clique no `>` no canto superior esquerdo se ela estiver recolhida."
    )


if __name__ == "__main__":
    main()
