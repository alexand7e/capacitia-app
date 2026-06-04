"""Dashboard Visão Unificada - Todos os Módulos."""

import streamlit as st
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sys
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.loaders import load_all_data
from components.kpi_cards import render_kpi_card
from utils.constants import COLORS
from utils.helpers import style_fig

_PAGE = Path(__file__).parent.parent

st.set_page_config(
    page_title="Visão Unificada - CapacitIA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

with open(_PAGE / "styles" / "main.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

all_data = load_all_data()

st.title("📊 Visão Unificada - CapacitIA")
st.markdown("Análise consolidada de todos os módulos do CapacitIA")


def _extrair_ano_saude(data_str):
    m = re.search(r'de (\d{4})', str(data_str))
    return m.group(1) if m else None


def _preparar_dados():
    sv = all_data['servidores']['dados'].copy() if all_data['servidores']['dados'] is not None else pd.DataFrame()
    sa = all_data['saude']['dados'].copy() if all_data['saude']['dados'] is not None else pd.DataFrame()
    ad = all_data['autonomia_digital']['inscricoes'].copy() if all_data['autonomia_digital']['inscricoes'] is not None else pd.DataFrame()

    if not sa.empty and 'ano' not in sa.columns:
        sa['ano'] = sa['data'].apply(_extrair_ano_saude)
    if not ad.empty and 'ano' not in ad.columns:
        ad['ano'] = pd.to_datetime(ad['data_inscricao'], errors='coerce').dt.year.astype(str)

    return sv, sa, ad


sv, sa, ad = _preparar_dados()

# ── Filtros ──
anos_disponiveis = set()
if not sv.empty and 'ano' in sv.columns:
    anos_disponiveis.update(sv['ano'].dropna().unique())
if not sa.empty and 'ano' in sa.columns:
    anos_disponiveis.update(sa['ano'].dropna().unique())
if not ad.empty and 'ano' in ad.columns:
    anos_disponiveis.update(ad['ano'].dropna().unique())
anos_disponiveis = sorted(a for a in anos_disponiveis if a in ('2025', '2026'))

filtro_ano = st.selectbox(
    "📅 Filtrar por Ano",
    ["Todos os Anos"] + anos_disponiveis,
    index=0,
    key="filtro_ano_vu",
)

comparar = st.checkbox("⚖️ Comparar 2025 vs 2026", key="comparar_anos")


def _filtrar_ano(df, ano_col, ano):
    if ano_col not in df.columns:
        return df
    if ano == "Todos os Anos":
        return df
    return df[df[ano_col].astype(str) == str(ano)]


if comparar:
    # ── Modo Comparativo ──
    st.markdown("## ⚖️ Comparativo 2025 vs 2026")

    sv_25 = sv[sv['ano'].astype(str) == '2025'] if not sv.empty else pd.DataFrame()
    sv_26 = sv[sv['ano'].astype(str) == '2026'] if not sv.empty else pd.DataFrame()
    sa_25 = sa[sa['ano'].astype(str) == '2025'] if not sa.empty else pd.DataFrame()
    sa_26 = sa[sa['ano'].astype(str) == '2026'] if not sa.empty else pd.DataFrame()
    ad_25 = ad[ad['ano'].astype(str) == '2025'] if not ad.empty else pd.DataFrame()
    ad_26 = ad[ad['ano'].astype(str) == '2026'] if not ad.empty else pd.DataFrame()

    def _calc(sv_d, sa_d, ad_d):
        tot_part = len(sv_d) + len(sa_d) + len(ad_d)
        tot_eventos_sv = sv_d['evento'].nunique() if not sv_d.empty and 'evento' in sv_d.columns else 0
        tot_lotes_sa = sa_d['lote'].nunique() if not sa_d.empty and 'lote' in sa_d.columns else 0
        tot_ad = len(ad_d)
        tot_eventos = tot_eventos_sv + tot_lotes_sa + (1 if tot_ad > 0 else 0)
        sec = sv_d['orgao'].nunique() if not sv_d.empty and 'orgao' in sv_d.columns else 0
        cert = (sv_d['certificado'] == 'Sim').sum() if not sv_d.empty and 'certificado' in sv_d.columns else 0
        taxa = (cert / len(sv_d) * 100) if len(sv_d) > 0 else 0
        return tot_part, tot_eventos, sec, taxa

    p25, e25, s25, t25 = _calc(sv_25, sa_25, ad_25)
    p26, e26, s26, t26 = _calc(sv_26, sa_26, ad_26)

    def pct(a, b):
        if a == 0:
            return "—"
        return f"{(b - a) / a * 100:+.1f}%"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 2025")
        render_kpi_card("Participantes", f"{p25:,}")
        render_kpi_card("Eventos", str(e25))
        render_kpi_card("Secretarias", str(s25))
        render_kpi_card("Taxa Certificação", f"{t25:.1f}%")
    with col2:
        st.markdown("### 2026")
        render_kpi_card("Participantes", f"{p26:,}")
        render_kpi_card("Eventos", str(e26))
        render_kpi_card("Secretarias", str(s26))
        render_kpi_card("Taxa Certificação", f"{t26:.1f}%")
    with col3:
        st.markdown("### Δ Variação")
        render_kpi_card("Participantes", pct(p25, p26), change=f"{p25} → {p26}")
        render_kpi_card("Eventos", pct(e25, e26), change=f"{e25} → {e26}")
        render_kpi_card("Secretarias", pct(s25, s26), change=f"{s25} → {s26}")
        render_kpi_card("Taxa Certificação", pct(t25, t26), change=f"{t25:.1f}% → {t26:.1f}%")

    # ── Gráficos comparativos ──
    st.markdown("## 📈 Gráficos Comparativos")

    labels = ["Servidores", "Saúde", "Autonomia Digital"]
    vals_25 = [len(sv_25), len(sa_25), len(ad_25)]
    vals_26 = [len(sv_26), len(sa_26), len(ad_26)]

    fig_inscritos = go.Figure()
    fig_inscritos.add_trace(go.Bar(name="2025", x=labels, y=vals_25, marker_color="#034EA2"))
    fig_inscritos.add_trace(go.Bar(name="2026", x=labels, y=vals_26, marker_color="#FDB913"))
    fig_inscritos.update_layout(
        title="Inscritos por Módulo",
        barmode="group",
        yaxis_title="Nº de Inscritos",
    )
    style_fig(fig_inscritos, height=400)

    # Certificados (apenas servidores)
    cert_25 = (sv_25['certificado'] == 'Sim').sum() if not sv_25.empty and 'certificado' in sv_25.columns else 0
    cert_26 = (sv_26['certificado'] == 'Sim').sum() if not sv_26.empty and 'certificado' in sv_26.columns else 0
    taxa_sv_25 = cert_25 / len(sv_25) * 100 if len(sv_25) > 0 else 0
    taxa_sv_26 = cert_26 / len(sv_26) * 100 if len(sv_26) > 0 else 0

    fig_cert = go.Figure()
    fig_cert.add_trace(go.Bar(name="2025", x=["Certificados", "Taxa (%)"], y=[cert_25, round(taxa_sv_25, 1)], marker_color="#034EA2"))
    fig_cert.add_trace(go.Bar(name="2026", x=["Certificados", "Taxa (%)"], y=[cert_26, round(taxa_sv_26, 1)], marker_color="#FDB913"))
    fig_cert.update_layout(
        title="Certificados (Servidores)",
        barmode="group",
        yaxis_title="Quantidade",
    )
    style_fig(fig_cert, height=400)

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(fig_inscritos, width='stretch')
    with col_b:
        st.plotly_chart(fig_cert, width='stretch')

    # Tabela de crescimento
    st.markdown("### 📋 Crescimento Percentual por Módulo")
    data_tabela = {
        "Módulo": labels,
        "2025": vals_25,
        "2026": vals_26,
        "Δ%": [
            f"{((b - a) / a * 100):+.1f}%" if a > 0 else "—"
            for a, b in zip(vals_25, vals_26)
        ],
    }
    st.dataframe(
        pd.DataFrame(data_tabela),
        width='stretch',
        hide_index=True,
        column_config={
            "2025": st.column_config.NumberColumn(format="%d"),
            "2026": st.column_config.NumberColumn(format="%d"),
        },
    )

else:
    # ── Modo Normal (único ano ou todos) ──
    sv_f = _filtrar_ano(sv, 'ano', filtro_ano) if filtro_ano != "Todos os Anos" else sv
    sa_f = _filtrar_ano(sa, 'ano', filtro_ano) if filtro_ano != "Todos os Anos" else sa
    ad_f = _filtrar_ano(ad, 'ano', filtro_ano) if filtro_ano != "Todos os Anos" else ad

    total_participantes = len(sv_f) + len(sa_f) + len(ad_f)
    total_eventos_sv = sv_f['evento'].nunique() if not sv_f.empty and 'evento' in sv_f.columns else 0
    total_lotes_sa = sa_f['lote'].nunique() if not sa_f.empty and 'lote' in sa_f.columns else 0
    total_ad_eventos = 1 if not ad_f.empty else 0
    total_eventos = total_eventos_sv + total_lotes_sa + total_ad_eventos

    secretarias_count = sv_f['orgao'].nunique() if not sv_f.empty and 'orgao' in sv_f.columns else 0

    if not sv_f.empty and 'certificado' in sv_f.columns:
        certificados = (sv_f['certificado'] == 'Sim').sum()
        taxa = (certificados / len(sv_f) * 100) if len(sv_f) > 0 else 0
    else:
        taxa = 0

    st.markdown("## 📈 Indicadores Principais")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card("Total de Participantes", f"{total_participantes:,}", "👥")
    with col2:
        render_kpi_card("Total de Eventos", str(total_eventos), "📅")
    with col3:
        render_kpi_card("Secretarias Envolvidas", str(secretarias_count), "🏢")
    with col4:
        render_kpi_card("Taxa de Certificação", f"{taxa:.1f}%", "✅")

if st.button("🏠 Voltar à Home"):
    st.switch_page("app.py")
