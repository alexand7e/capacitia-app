"""Dashboard Visão Unificada - Todos os Módulos."""

import streamlit as st
from pathlib import Path
import pandas as pd
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_all_data
from src.components.kpi_cards import render_kpi_card
from src.utils.constants import COLORS

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="Visão Unificada - CapacitIA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CSS GLOBAL
# =========================
with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()
st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# =========================
# CARREGAR DADOS
# =========================
all_data = load_all_data()

# =========================
# HEADER
# =========================
st.title("📊 Visão Unificada - CapacitIA")
st.markdown("Análise consolidada de todos os módulos do CapacitIA")

# =========================
# KPIs CONSOLIDADOS
# =========================
st.markdown("## 📈 Indicadores Principais")

# Calcular totais
total_participantes = (
    (len(all_data['servidores']['dados']) if all_data['servidores']['dados'] is not None else 0) +
    (len(all_data['saude']['dados']) if all_data['saude']['dados'] is not None else 0) +
    (len(all_data['autonomia_digital']['inscricoes']) if all_data['autonomia_digital']['inscricoes'] is not None else 0)
)

total_eventos_servidores = len(all_data['servidores']['visao']) - 1 if all_data['servidores']['visao'] is not None else 0
total_lotes_saude = all_data['saude']['dados']['lote'].nunique() if all_data['saude']['dados'] is not None and 'lote' in all_data['saude']['dados'].columns else 0
total_avaliacoes = len(all_data['autonomia_digital']['avaliacoes']) if all_data['autonomia_digital']['avaliacoes'] is not None else 0
total_eventos = total_eventos_servidores + total_lotes_saude + total_avaliacoes

secretarias_count = len(all_data['servidores']['secretarias']) if all_data['servidores']['secretarias'] is not None else 0

# Taxa de certificação (apenas servidores)
if all_data['servidores']['dados'] is not None:
    df_dados = all_data['servidores']['dados']
    certificados = (df_dados['certificado'] == 'Sim').sum() if 'certificado' in df_dados.columns else 0
    taxa = (certificados / len(df_dados) * 100) if len(df_dados) > 0 else 0
else:
    taxa = 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_kpi_card("Total de Participantes", f"{total_participantes:,}", "👥")

with col2:
    render_kpi_card("Total de Eventos", str(total_eventos), "📅")

with col3:
    render_kpi_card("Secretarias Envolvidas", str(secretarias_count), "🏢")

with col4:
    render_kpi_card("Taxa de Certificação", f"{taxa:.1f}%", "✅")

# =========================
# PLACEHOLDER - Implementação completa em breve
# =========================
st.info("🚧 Esta página está em desenvolvimento. Gráficos comparativos e análises detalhadas serão adicionados em breve.")

# Botão para voltar à home
if st.button("🏠 Voltar à Home"):
    st.switch_page("app.py")

