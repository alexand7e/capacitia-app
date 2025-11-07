"""Dashboard CapacitIA Saúde."""

import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.io as pio
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_saude_data
from src.utils.constants import DESCRIPTIONS, COLORS

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="CapacitIA Saúde",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Plotly theme
pio.templates["capacit_dark"] = pio.templates["plotly_dark"]
pio.templates["capacit_dark"].layout.font.family = "Inter, Segoe UI, Roboto, Arial"
pio.templates["capacit_dark"].layout.colorway = [
    "#7DD3FC", "#34D399", "#FBBF24", "#F472B6", "#60A5FA", "#A78BFA", "#F87171"
]
pio.templates["capacit_dark"].layout.paper_bgcolor = "#0f1220"
pio.templates["capacit_dark"].layout.plot_bgcolor = "#11142a"
pio.templates["capacit_dark"].layout.hoverlabel = dict(
    bgcolor="#0f1220", font_size=12, font_family="Inter, Segoe UI, Roboto, Arial"
)
pio.templates.default = "capacit_dark"

# =========================
# CSS GLOBAL
# =========================
with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()
st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# =========================
# CARREGAR DADOS
# =========================
df_saude = load_saude_data()

if df_saude is None:
    st.error("Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.")
    st.stop()

# =========================
# HEADER
# =========================
st.title("🏥 CapacitIA Saúde")
st.markdown(f"""
<div style="color: {COLORS['muted']}; margin-bottom: 24px;">
{DESCRIPTIONS['saude'].strip()}
</div>
<div style="color: {COLORS['muted']}; font-size: 0.9rem;">
Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# Botão para voltar à home
if st.button("🏠 Voltar à Home", key="btn_home_saude"):
    st.switch_page("app.py")

# =========================
# KPIs PRINCIPAIS
# =========================
st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_participantes = len(df_saude)
total_lotes = df_saude['lote'].nunique() if 'lote' in df_saude.columns else 0
datas_unicas = df_saude['data'].nunique() if 'data' in df_saude.columns else 0
# Extrair ano da primeira data para exibição
ultima_atualizacao = "Maio 2025"
if 'data' in df_saude.columns and len(df_saude) > 0:
    primeira_data = str(df_saude['data'].iloc[0])
    if '2025' in primeira_data:
        ultima_atualizacao = "Maio 2025"
    elif '2026' in primeira_data:
        ultima_atualizacao = "Maio 2026"
taxa_participacao = 100.0  # Assumindo 100% de participação

col1.markdown(f'<div class="kpi"><h4>Total de Participantes</h4><div class="val">{total_participantes:,}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="kpi"><h4>Lotes Realizados</h4><div class="val">{total_lotes}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="kpi"><h4>Última Atualização</h4><div class="val">{ultima_atualizacao}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="kpi"><h4>Taxa de Participação</h4><div class="val">{taxa_participacao:.0f}%</div></div>', unsafe_allow_html=True)

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# FILTROS
# =========================
st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)

with col_f1:
    if 'lote' in df_saude.columns:
        lotes_disponiveis = ["Todos"] + sorted(df_saude['lote'].dropna().unique().tolist())
        lote_selecionado = st.selectbox(
            "📦 Lote",
            lotes_disponiveis,
            index=0,
            key="filtro_lote"
        )
    else:
        lote_selecionado = "Todos"

with col_f2:
    if 'data' in df_saude.columns:
        datas_disponiveis = ["Todas"] + sorted(df_saude['data'].dropna().unique().tolist())
        data_selecionada = st.selectbox(
            "📅 Data",
            datas_disponiveis,
            index=0,
            key="filtro_data"
        )
    else:
        data_selecionada = "Todas"

# Aplicar filtros
df_saude_filtrado = df_saude.copy()
if lote_selecionado != "Todos" and 'lote' in df_saude_filtrado.columns:
    df_saude_filtrado = df_saude_filtrado[df_saude_filtrado['lote'] == lote_selecionado]
if data_selecionada != "Todas" and 'data' in df_saude_filtrado.columns:
    df_saude_filtrado = df_saude_filtrado[df_saude_filtrado['data'] == data_selecionada]

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# ABAS
# =========================
tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "📦 Análise por Lote", "📈 Estatísticas"])

# --------- Visão Geral
with tab1:
    colA, colB = st.columns(2)
    
    with colA:
        st.markdown('<div class="panel"><h3>Participantes por Lote</h3>', unsafe_allow_html=True)
        if 'lote' in df_saude_filtrado.columns:
            participantes_por_lote = df_saude_filtrado.groupby('lote').size().reset_index(name='Total')
            participantes_por_lote = participantes_por_lote.sort_values('Total', ascending=True)
            
            if not participantes_por_lote.empty:
                fig = px.bar(
                    participantes_por_lote, 
                    x='Total', 
                    y='lote', 
                    orientation='h',
                    title=None,
                    text='Total'
                )
                fig.update_traces(texttemplate='%{text}', textposition='outside', cliponaxis=False)
                fig.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title=None,
                    yaxis_title=None
                )
                st.plotly_chart(fig, use_container_width=True, key="saude_lote_bar")
            else:
                st.info("Sem dados para plotar.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with colB:
        st.markdown('<div class="panel"><h3>Distribuição por Lote</h3>', unsafe_allow_html=True)
        if 'lote' in df_saude_filtrado.columns:
            distribuicao_lote = df_saude_filtrado['lote'].value_counts()
            
            if not distribuicao_lote.empty:
                fig_pie = px.pie(
                    values=distribuicao_lote.values,
                    names=distribuicao_lote.index,
                    hole=0.55,
                    title=None
                )
                fig_pie.update_traces(textinfo='percent+label', textposition='inside')
                fig_pie.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02)
                )
                st.plotly_chart(fig_pie, use_container_width=True, key="saude_lote_pie")
            else:
                st.info("Sem dados para plotar.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Timeline de lotes (a coluna 'data' contém texto descritivo, não datas reais)
    st.markdown('<div class="panel"><h3>Distribuição de Participantes por Período e Lote</h3>', unsafe_allow_html=True)
    if 'data' in df_saude_filtrado.columns and 'lote' in df_saude_filtrado.columns:
        timeline = df_saude_filtrado.groupby(['data', 'lote']).size().reset_index(name='Participantes')
        # Não ordenar por data (é texto), mas manter ordem original ou alfabética
        timeline = timeline.sort_values(['lote', 'data'])
        
        if not timeline.empty:
            # Criar gráfico de barras agrupadas em vez de scatter (melhor para texto)
            fig_timeline = px.bar(
                timeline,
                x='data',
                y='Participantes',
                color='lote',
                title=None,
                barmode='group',
                text='Participantes'
            )
            fig_timeline.update_traces(texttemplate='%{text}', textposition='outside', cliponaxis=False)
            fig_timeline.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Período de Capacitação",
                yaxis_title="Participantes",
                xaxis=dict(type='category'),  # Tratar como categoria, não data
                plot_bgcolor='#11142a',
                paper_bgcolor='#0f1220',
                font_color='#e6e7ee'
            )
            # Rotacionar labels do eixo X para melhor leitura
            fig_timeline.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_timeline, use_container_width=True, key="saude_timeline")
        else:
            st.info("Sem dados para visualização.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Análise por Lote
with tab2:
    if 'lote' in df_saude_filtrado.columns:
        lotes_unicos = sorted(df_saude_filtrado['lote'].dropna().unique())
        
        for lote in lotes_unicos:
            with st.expander(f"📦 Lote: {lote}", expanded=False):
                df_lote = df_saude_filtrado[df_saude_filtrado['lote'] == lote]
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Total de Participantes", len(df_lote))
                with col_info2:
                    if 'data' in df_lote.columns:
                        datas_lote = df_lote['data'].unique()
                        st.metric("Datas de Realização", len(datas_lote))
                        if len(datas_lote) > 0:
                            st.caption(f"Período: {datas_lote[0]}")
                
                if 'data' in df_lote.columns:
                    st.markdown("**Datas de realização:**")
                    st.write(", ".join(sorted(df_lote['data'].dropna().unique())))
    else:
        st.info("Coluna 'lote' não encontrada nos dados.")

# --------- Estatísticas
with tab3:
    st.markdown('<div class="panel"><h3>Gráficos de Participação</h3>', unsafe_allow_html=True)
    
    if 'lote' in df_saude_filtrado.columns:
        # Evolução ao longo do tempo (se houver data)
        if 'data' in df_saude_filtrado.columns:
            evolucao = df_saude_filtrado.groupby('data').size().reset_index(name='Participantes')
            evolucao = evolucao.sort_values('data')
            
            if not evolucao.empty:
                fig_evol = px.line(
                    evolucao,
                    x='data',
                    y='Participantes',
                    title="Evolução de Participantes ao Longo do Tempo",
                    markers=True
                )
                fig_evol.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=50, b=10),
                    xaxis_title="Data",
                    yaxis_title="Participantes"
                )
                st.plotly_chart(fig_evol, use_container_width=True, key="saude_evolucao")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Comparativos
    st.markdown('<div class="panel"><h3>Comparativos</h3>', unsafe_allow_html=True)
    if 'lote' in df_saude_filtrado.columns:
        comparativo = df_saude_filtrado.groupby('lote').size().reset_index(name='Total')
        comparativo = comparativo.sort_values('Total', ascending=False)
        
        if not comparativo.empty:
            fig_comp = px.bar(
                comparativo,
                x='lote',
                y='Total',
                title="Comparativo entre Lotes",
                text='Total'
            )
            fig_comp.update_traces(texttemplate='%{text}', textposition='outside', cliponaxis=False)
            fig_comp.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10),
                xaxis_title="Lote",
                yaxis_title="Total de Participantes"
            )
            st.plotly_chart(fig_comp, use_container_width=True, key="saude_comparativo")
    st.markdown('</div>', unsafe_allow_html=True)
