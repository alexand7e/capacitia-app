"""Dashboard CapacitIA Servidores - Migrado do app_servidores_original.py"""

import unicodedata
import re
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
import numpy as np
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_servidores_data
from src.utils.constants import DESCRIPTIONS, COLORS
from src.utils.helpers import (
    fmt_int_br, _col_like, _normalize_org, drop_empty_labels, nz,
    _parse_ptbr_number, _find_header_row, clean_secretarias
)

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="CapacitIA Servidores",
    page_icon="👥",
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
# Carrega o CSS principal do arquivo externo
with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()

st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# =========================
# DATA LOAD
# =========================
df_dados, df_visao, df_secretarias_raw, df_cargos_raw, df_min, df_orgaos_parceiros = load_servidores_data()

if df_dados is None:
    st.error("Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.")
    st.stop()

# Definir variável global para identificar formato dos dados
is_parquet = 'cargo' in df_cargos_raw.columns if df_cargos_raw is not None else False

# =========================
# HELPERS
# =========================
def style_fig(fig, height=420):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title=None, yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    ); return fig

def df_panel(df: pd.DataFrame, title: str, key: str, max_rows: int = 22, min_h: int = 260, max_h: int = 640):
    st.markdown(f'<div class="panel"><h3>{title}</h3>', unsafe_allow_html=True)
    h = min(max(min_h, 60 + 28 * min(len(df), max_rows)), max_h)
    st.dataframe(df, use_container_width=True, height=h)
    st.markdown('</div>', unsafe_allow_html=True)



def count_secretarias_unicas(
    df_secretarias: pd.DataFrame,
    *,
    only_with_inscritos: bool = True,     # conta só quem tem inscrito > 0 (KPI "atendidas")
    drop_genericos: bool = True,          # remove rótulos genéricos
    alias: dict | None = None             # mapa opcional para unificar nomes (ex.: {"INVESTE": "INVESTEPI"})
) -> int:
    df = df_secretarias.copy()

    # Remove linhas-meta (se existirem)
    mask_meta = df.astype(str).apply(
        lambda s: s.str.upper().str.contains("TOTAL|ATIVIDADE/EVENTO", na=False)
    ).any(axis=1)
    df = df[~mask_meta]

    # Filtro por inscritos > 0 (quando o KPI é "atendidas")
    inscritos_col = None
    if 'n_inscritos' in df.columns:
        inscritos_col = 'n_inscritos'
    elif "Nº INSCRITOS" in df.columns:
        inscritos_col = "Nº INSCRITOS"
    
    if only_with_inscritos and inscritos_col:
        insc = pd.to_numeric(df[inscritos_col], errors="coerce").fillna(0)
        df = df[insc > 0]

    # Normaliza rótulos
    col = "SECRETARIA/ÓRGÃO"
    s = df[col].map(_normalize_org)

    # Remove vazios e placeholders
    invalid = {"", "NAN", "NONE", "NAT"}
    if drop_genericos:
        invalid |= {"ORGAO EXTERNO"}   # adicione outros se quiser

    s = s[~s.isin(invalid)]

    # Aplica aliases (opcional) para unificar grafias
    if alias:
        s = s.replace(alias)

    return int(s.nunique())




# =========================
# SECRETARIA-ÓRGÃO (limpeza + filtro oculto)
# =========================
df_secretarias = clean_secretarias(df_secretarias_raw)

# "filtros" ocultos
secre_opts = sorted(df_secretarias["SECRETARIA/ÓRGÃO"].dropna().unique().tolist())
secre_sel = secre_opts
topn = 10

# dataframe filtrado que os gráficos usam
df_f = df_secretarias[df_secretarias["SECRETARIA/ÓRGÃO"].isin(secre_sel)].copy()
if "Nº EVASÃO" in df_f.columns:
    inscritos_col_temp = 'n_inscritos' if 'n_inscritos' in df_f.columns else 'Nº INSCRITOS'
    evasao_col_temp = 'n_evasao' if 'n_evasao' in df_f.columns else 'Nº EVASÃO'
    
    num_insc = pd.to_numeric(df_f[inscritos_col_temp], errors="coerce")
    num_evas = pd.to_numeric(df_f[evasao_col_temp], errors="coerce")
    df_f["Evasão (%)"] = (num_evas / num_insc.replace(0, pd.NA)) * 100

# =========================
# KPIs a partir do "TOTAL GERAL" (VISÃO ABERTA)
# =========================
def get_totais_visao(df_visao: pd.DataFrame):
    # Verifica se está no formato padronizado (Parquet)
    if 'n_inscritos' in df_visao.columns and 'n_certificados' in df_visao.columns:
        # Formato padronizado dos arquivos Parquet
        mask_total = df_visao.astype(str).apply(lambda s: s.str.contains("TOTAL GERAL", case=False, na=False)).any(axis=1)
        if mask_total.any():
            row = df_visao.loc[mask_total].iloc[0]
            val_ins = row.get('n_inscritos', 0)
            val_cer = row.get('n_certificados', 0)
            return int(round(float(val_ins))), int(round(float(val_cer)))
        else:
            # Somar todas as linhas exceto TOTAL GERAL
            df_sem_total = df_visao[~mask_total] if mask_total.any() else df_visao
            tot_insc = pd.to_numeric(df_sem_total['n_inscritos'], errors="coerce").fillna(0).sum()
            tot_cert = pd.to_numeric(df_sem_total['n_certificados'], errors="coerce").fillna(0).sum()
            return int(round(tot_insc)), int(round(tot_cert))
    
    # Formato original do Excel
    # acha a linha TOTAL GERAL
    mask_total = df_visao.astype(str).apply(lambda s: s.str.contains("TOTAL GERAL", case=False, na=False)).any(axis=1)
    col_ins = _col_like(df_visao, "INSCRIT") or "Nº INSCRITOS"
    col_cer = _col_like(df_visao, "CERTIFIC") or "Nº CERTIFICADOS"

    if mask_total.any():
        row = df_visao.loc[mask_total].iloc[0]

        # 1) tentar pelas colunas nomeadas
        val_ins = _parse_ptbr_number(row.get(col_ins)) if col_ins in df_visao.columns else np.nan
        val_cer = _parse_ptbr_number(row.get(col_cer)) if col_cer in df_visao.columns else np.nan

        # 2) se ainda NaN, escaneia a linha e pega os dois últimos números
        if pd.isna(val_ins) or pd.isna(val_cer):
            nums = [_parse_ptbr_number(v) for v in row.tolist()]
            nums = [n for n in nums if pd.notna(n)]
            if len(nums) >= 2:
                if pd.isna(val_ins): val_ins = nums[-2]
                if pd.isna(val_cer): val_cer = nums[-1]

        # 3) fallback final: somar as colunas na planilha toda
        if pd.isna(val_ins) or pd.isna(val_cer):
            ins_col = col_ins if col_ins in df_visao.columns else _col_like(df_visao, "INSCRIT")
            cer_col = col_cer if col_cer in df_visao.columns else _col_like(df_visao, "CERTIFIC")
            ins_sum = pd.to_numeric(df_visao[ins_col], errors="coerce").fillna(0).sum() if ins_col else 0
            cer_sum = pd.to_numeric(df_visao[cer_col], errors="coerce").fillna(0).sum() if cer_col else 0
            return int(round(ins_sum)), int(round(cer_sum))

        return int(round(float(val_ins))), int(round(float(val_cer)))

    # sem TOTAL GERAL: usa soma
    ins_col = col_ins if col_ins in df_visao.columns else _col_like(df_visao, "INSCRIT")
    cer_col = col_cer if col_cer in df_visao.columns else _col_like(df_visao, "CERTIFIC")
    tot_insc = pd.to_numeric(df_visao[ins_col], errors="coerce").fillna(0).sum() if ins_col else 0
    tot_cert = pd.to_numeric(df_visao[cer_col], errors="coerce").fillna(0).sum() if cer_col else 0
    return int(round(tot_insc)), int(round(tot_cert))


def get_secretarias_atendidas(df_sec_view: pd.DataFrame) -> int:
    # Verificar se está no formato padronizado (Parquet) ou original (Excel)
    if 'n_inscritos' in df_sec_view.columns:
        # Formato padronizado
        vals = pd.to_numeric(df_sec_view['n_inscritos'], errors="coerce").fillna(0)
    else:
        # Formato original
        inscritos_col = 'n_inscritos' if 'n_inscritos' in df_sec_view.columns else 'Nº INSCRITOS'
        vals = pd.to_numeric(df_sec_view[inscritos_col], errors="coerce").fillna(0)
    return int((vals > 0).sum())

# KPIs serão calculados após aplicação dos filtros


# =========================
# PREP CARGOS
# =========================
# Verifica se está no formato padronizado (Parquet) ou original (Excel)
if 'cargo' in df_cargos_raw.columns:
    # Ranking inicial baseado em dados individuais (df_dados)
    s_rank = (
        df_dados['cargo'].astype(str).str.strip()
    )
    s_rank = s_rank[s_rank != ""]
    df_cargos_rank = s_rank.value_counts()
    df_cargos_rank = pd.DataFrame({"Cargo": df_cargos_rank.index, "Inscritos": df_cargos_rank.values}).set_index("Cargo")

    # df_cargos_ev real: pivot a partir de df_dados (evento x Tipo x cargo)
    tmp_ev = df_dados[['evento', 'formato', 'cargo']].copy()
    tmp_ev['cargo'] = tmp_ev['cargo'].astype(str).str.strip()
    tmp_ev = tmp_ev[tmp_ev['cargo'] != ""]
    tmp_ev['Tipo'] = (
        tmp_ev['formato'].fillna("").astype(str).str.strip().str.title().replace({"Curso": "Curso de IA"})
    )
    tmp_ev['Inscritos'] = 1
    df_cargos_ev = (
        tmp_ev.groupby(['evento', 'Tipo', 'cargo'])['Inscritos'].sum().reset_index()
    )
    df_cargos_ev = (
        df_cargos_ev.pivot_table(index=['evento', 'Tipo'], columns='cargo', values='Inscritos', aggfunc='sum', fill_value=0)
        .reset_index()
    )
    cargo_cols = [c for c in df_cargos_ev.columns if c not in ['evento', 'Tipo']]
else:
    # Formato original do Excel
    EVENTO_COL = df_cargos_raw.columns[0]  # geralmente "Unnamed: 0"
    mask_evento = df_cargos_raw[EVENTO_COL].astype(str).str.contains(r"Masterclass|Workshop|Curso", case=False, na=False)
    df_cargos_ev = df_cargos_raw.loc[mask_evento].copy()
    df_cargos_ev["Tipo"] = (
        df_cargos_ev[EVENTO_COL]
        .str.extract(r"(Masterclass|Workshop|Curso)", expand=False)
        .str.title()
    )
    cargo_cols = [c for c in df_cargos_ev.columns if c not in [EVENTO_COL, "Tipo"]]
    df_cargos_ev[cargo_cols] = df_cargos_ev[cargo_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    totais_por_cargo = df_cargos_ev[cargo_cols].sum().sort_values(ascending=False)
    df_cargos_rank = (
        pd.DataFrame({"Cargo": totais_por_cargo.index, "Inscritos": totais_por_cargo.values})
        .sort_values("Inscritos", ascending=False).set_index("Cargo")
    )

# =========================
# HEADER
# =========================
st.title("👥 CapacitIA Servidores")
st.markdown(f"""
<div style="color: {COLORS['muted']}; margin-bottom: 24px;">
{DESCRIPTIONS['servidores'].strip()}
</div>
<div style="color: {COLORS['muted']}; font-size: 0.9rem;">
Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# Botões de ação
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🏠 Voltar à Home", key="btn_home_servidores", use_container_width=True):
        st.switch_page("app.py")

with col_btn2:
    if st.button("📄 Gerar Relatório PDF", key="btn_gerar_pdf", use_container_width=True, type="primary"):
        with st.spinner("Gerando relatório PDF..."):
            try:
                from src.utils.pdf_gen import gerar_relatorio_capacitia
                
                # Gerar PDF com os dados atuais
                pdf_path = gerar_relatorio_capacitia(
                    df_dados=df_dados,
                    df_visao=df_visao,
                    df_secretarias=df_secretarias,
                    df_cargos=df_cargos_raw,
                    df_orgaos_parceiros=df_orgaos_parceiros,
                    nome_arquivo=f"relatorio_capacitia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
                
                if pdf_path:
                    # Ler o arquivo PDF para download
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                    
                    st.success("✅ Relatório gerado com sucesso!")
                    st.download_button(
                        label="⬇️ Baixar Relatório PDF",
                        data=pdf_bytes,
                        file_name=f"relatorio_capacitia_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        key="download_pdf"
                    )
                else:
                    st.error("❌ Erro ao gerar relatório. Verifique os logs.")
            except ImportError as e:
                st.error(f"❌ Erro: Dependências não instaladas. Execute: pip install reportlab kaleido")
            except Exception as e:
                st.error(f"❌ Erro ao gerar relatório: {str(e)}")



# KPIs serão exibidos após o cálculo com dados filtrados

# =========================
# FILTROS GLOBAIS
# =========================
st.markdown('<div <h3>🔍 Filtros Globais</h3>', unsafe_allow_html=True)

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    # Filtro por tipo de curso
    tipos_disponiveis = ["Todos"] + sorted(df_cargos_ev["Tipo"].dropna().unique().tolist()) if not df_cargos_ev.empty else ["Todos"]
    tipo_selecionado = st.selectbox(
        "📚 Tipo de Curso",
        tipos_disponiveis,
        index=0,
        key="filtro_tipo_curso"
    )

with col_f2:
    # Filtro por órgão externo
    orgaos_disponiveis = ["Todos"] + sorted(df_secretarias["SECRETARIA/ÓRGÃO"].dropna().unique().tolist())
    orgao_selecionado = st.selectbox(
        "🏢 Órgão/Secretaria",
        orgaos_disponiveis,
        index=0,
        key="filtro_orgao"
    )

with col_f3:
    # Filtro por órgão externo (Sim/Não)
    orgao_externo_opcoes = ["Todos", "Sim", "Não"]
    orgao_externo_selecionado = st.selectbox(
        "🌐 Órgão Externo",
        orgao_externo_opcoes,
        index=0,
        key="filtro_orgao_externo"
    )

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# Aplicar filtros aos dados
# A coluna 'orgao_externo' já existe nos dados processados (vem do CSV original)
# Não precisamos criar classificação manual

# Debug: Mostrar distribuição de órgãos externos vs internos
if st.sidebar.checkbox("Debug: Mostrar classificação de órgãos", False):
    classificacao_count = df_f["orgao_externo"].value_counts()
    st.sidebar.write("Distribuição de órgãos externos (dados originais):")
    st.sidebar.write(classificacao_count)
    
    # Mostrar exemplos de órgãos por classificação
    externos_exemplos = df_f[df_f["orgao_externo"] == "Sim"]["orgao"].value_counts().head(5)
    st.sidebar.write("Top 5 órgãos externos:")
    st.sidebar.write(externos_exemplos)
    
    internos_exemplos = df_f[df_f["orgao_externo"] == "Não"]["orgao"].value_counts().head(5)
    st.sidebar.write("Top 5 órgãos internos:")
    st.sidebar.write(internos_exemplos)

# ==========================================
# APLICAÇÃO DOS FILTROS GLOBAIS - VERSÃO CORRIGIDA
# ==========================================

# Começar com cópia dos dados originais
df_dados_filtrado = df_dados.copy() if df_dados is not None else pd.DataFrame()

# 1. Filtro por tipo de curso/evento
if tipo_selecionado != "Todos":
    df_cargos_ev_filtrado = df_cargos_ev[df_cargos_ev["Tipo"] == tipo_selecionado].copy()
    # Aplicar filtro ao df_dados usando a coluna 'formato' que contém os tipos corretos
    if 'formato' in df_dados_filtrado.columns:
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado['formato'] == tipo_selecionado]
    elif 'evento' in df_dados_filtrado.columns:
        # Fallback: usar evento se formato não existir
        eventos_tipo = df_dados_filtrado[df_dados_filtrado['evento'].str.contains(tipo_selecionado, case=False, na=False)]['evento'].unique()
        if len(eventos_tipo) > 0:
            df_dados_filtrado = df_dados_filtrado[df_dados_filtrado['evento'].isin(eventos_tipo)]
else:
    df_cargos_ev_filtrado = df_cargos_ev.copy()

# 2. Filtro por órgão específico
if orgao_selecionado != "Todos":
    df_secretarias_filtrado = df_secretarias[df_secretarias["SECRETARIA/ÓRGÃO"] == orgao_selecionado].copy()
    df_dados_filtrado = df_dados_filtrado[df_dados_filtrado["orgao"] == orgao_selecionado].copy()
    df_f_filtrado = df_f[df_f["SECRETARIA/ÓRGÃO"] == orgao_selecionado].copy()
else:
    df_secretarias_filtrado = df_secretarias.copy()
    df_f_filtrado = df_f.copy()

# 3. Aplicar filtro de órgão externo
if orgao_externo_selecionado != "Todos":
    if 'orgao_externo' in df_dados_filtrado.columns:
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado["orgao_externo"] == orgao_externo_selecionado].copy()
        orgaos_restantes = df_dados_filtrado["orgao"].unique()
        df_secretarias_filtrado = df_secretarias_filtrado[df_secretarias_filtrado["SECRETARIA/ÓRGÃO"].isin(orgaos_restantes)].copy()
        if 'orgao_externo' in df_f.columns:
            df_f_filtrado = df_f_filtrado[df_f_filtrado["orgao_externo"] == orgao_externo_selecionado].copy()

# Recriar df_cargos_ev_filtrado a partir de df_dados_filtrado (dados reais)
if 'cargo' in df_dados_filtrado.columns and len(df_dados_filtrado) > 0:
    tmp_ev_f = df_dados_filtrado[['evento', 'formato', 'cargo']].copy()
    tmp_ev_f['cargo'] = tmp_ev_f['cargo'].astype(str).str.strip()
    tmp_ev_f = tmp_ev_f[tmp_ev_f['cargo'] != ""]
    tmp_ev_f['Tipo'] = (
        tmp_ev_f['formato'].fillna("").astype(str).str.strip().str.title().replace({"Curso": "Curso de IA"})
    )
    tmp_ev_f['Inscritos'] = 1
    df_cargos_ev_filtrado = (
        tmp_ev_f.groupby(['evento', 'Tipo', 'cargo'])['Inscritos'].sum().reset_index()
    )
    df_cargos_ev_filtrado = (
        df_cargos_ev_filtrado.pivot_table(index=['evento', 'Tipo'], columns='cargo', values='Inscritos', aggfunc='sum', fill_value=0)
        .reset_index()
    )
    cargo_cols = [c for c in df_cargos_ev_filtrado.columns if c not in ['evento', 'Tipo']]
else:
    df_cargos_ev_filtrado = pd.DataFrame(columns=['evento', 'Tipo'])
    cargo_cols = []

# ==========================================
# RECALCULAR KPIs COM DADOS FILTRADOS - VERSÃO CORRIGIDA
# ==========================================

# Usar df_dados_filtrado como fonte única de verdade para KPIs
if len(df_dados_filtrado) > 0:
    # Calcular KPIs baseados nos dados individuais filtrados
    tot_insc = len(df_dados_filtrado)
    tot_cert = len(df_dados_filtrado[df_dados_filtrado['certificado'] == 'Sim']) if 'certificado' in df_dados_filtrado.columns else 0
    sec_atendidas = df_dados_filtrado['orgao'].nunique() if 'orgao' in df_dados_filtrado.columns else 0
else:
    # Se não há dados após filtros, KPIs zerados
    tot_insc = 0
    tot_cert = 0
    sec_atendidas = 0

taxa_cert = (tot_cert / tot_insc * 100) if tot_insc > 0 else 0.0

# Aplicar filtros ao df_visao se aplicável
df_visao_filtrado = df_visao.copy()
if tipo_selecionado != "Todos" and 'formato' in df_visao_filtrado.columns:
    df_visao_filtrado = df_visao_filtrado[df_visao_filtrado['formato'].str.contains(tipo_selecionado, case=False, na=False)].copy()

# Exibir informação sobre filtros aplicados
filtros_ativos = []
if tipo_selecionado != "Todos":
    filtros_ativos.append(f"Tipo: {tipo_selecionado}")
if orgao_selecionado != "Todos":
    filtros_ativos.append(f"Órgão: {orgao_selecionado}")
if orgao_externo_selecionado != "Todos":
    filtros_ativos.append(f"Órgão Externo: {orgao_externo_selecionado}")

if filtros_ativos:
    st.info(f"🔍 **Filtros ativos**: {' | '.join(filtros_ativos)} | **Registros encontrados**: {tot_insc}")
else:
    st.info(f"📊 **Visualizando todos os dados** | **Total de registros**: {tot_insc}")

# =========================
# RECALCULAR df_cargos_rank COM DADOS FILTRADOS
# =========================
if len(df_dados_filtrado) > 0 and 'cargo' in df_dados_filtrado.columns:
    s_rank_f = df_dados_filtrado['cargo'].astype(str).str.strip()
    s_rank_f = s_rank_f[s_rank_f != ""]
    df_cargos_rank = s_rank_f.value_counts()
    df_cargos_rank = pd.DataFrame({"Cargo": df_cargos_rank.index, "Inscritos": df_cargos_rank.values}).set_index("Cargo")
else:
    df_cargos_rank = pd.DataFrame(columns=["Inscritos"]).set_index(pd.Index([], name="Cargo"))

# =========================
# EXIBIR KPIs
# =========================
c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi"><h4>Total de Inscritos</h4><div class="val">{fmt_int_br(tot_insc)}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi"><h4>Total de Certificados</h4><div class="val">{fmt_int_br(tot_cert)}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi"><h4>Taxa de Certificação</h4><div class="val">{taxa_cert:.2f}%</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi"><h4>Órgãos Atendidos</h4><div class="val">{sec_atendidas}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# TABS (com remoção de NaN/±inf nos plots)
# =========================



tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Visão Geral", "👥 Cargos", "🏢 Secretarias", "📚 Eventos", "🤝 Órgãos Parceiros"])

# --------- Visão Geral
with tab1:
    colA, colB = st.columns(2)

    modo = st.radio(
        "Visualizar",
        ["Inscritos", "Certificados", "Taxa de Permanência", "Comparativo"],
        horizontal=True, key="rg_sec",
    )

    with colA:
        st.markdown('<div class="panel"><h3>Desempenho por Secretaria</h3>', unsafe_allow_html=True)

        # 🔧 CORREÇÃO: Usar df_dados_filtrado como fonte única de verdade
        if len(df_dados_filtrado) > 0:
            # Agrupar dados individuais filtrados por órgão
            # Contar inscritos e certificados por órgão usando dados individuais
            grp_sec = df_dados_filtrado.groupby('orgao').agg({
                'orgao': 'count',  # Total de inscritos
                'certificado': lambda x: (x == 'Sim').sum()  # Total de certificados
            }).rename(columns={'orgao': 'Inscritos', 'certificado': 'Certificados'})
            
            grp_sec["Taxa de Permanência (%)"] = (
                grp_sec['Certificados'] / grp_sec['Inscritos']
            ).replace([pd.NA, float("inf")], 0).fillna(0) * 100
            
            # Renomear índice para compatibilidade
            grp_sec.index.name = "SECRETARIA/ÓRGÃO"
        else:
            # Se não há dados filtrados, criar DataFrame vazio
            grp_sec = pd.DataFrame(columns=['Inscritos', 'Certificados', 'Taxa de Permanência (%)'])
            grp_sec.index.name = "SECRETARIA/ÓRGÃO"


        if modo == "Inscritos":
            d = nz(grp_sec, ['Inscritos']).head(topn).sort_values('Inscritos')
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame({'Inscritos': []}), x='Inscritos', y=[])
            else:
                fig = px.bar(d, x='Inscritos', y=d.index, orientation="h", title="Top por Inscritos")
                x_max = max(1, d['Inscritos'].max())
                fig.update_traces(text=d['Inscritos'], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Certificados":
            d = nz(grp_sec, ['Certificados']).sort_values('Certificados', ascending=False) \
                                               .head(topn).sort_values('Certificados')
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame({'Certificados': []}), x='Certificados', y=[])
            else:
                fig = px.bar(d, x='Certificados', y=d.index, orientation="h", title="Top por Certificados")
                x_max = max(1, d['Certificados'].max())
                fig.update_traces(text=d['Certificados'], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Taxa de Permanência":
            base = grp_sec[grp_sec['Inscritos'] > 0]
            d = nz(base, ["Taxa de Permanência (%)"]).sort_values("Taxa de Permanência (%)", ascending=False) \
                                                    .head(topn).sort_values("Taxa de Permanência (%)")
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame({"Taxa de Permanência (%)": []}), x="Taxa de Permanência (%)", y=[])
            else:
                fig = px.bar(d, x="Taxa de Permanência (%)", y=d.index, orientation="h", title="Top por Permanência")
                vals = d["Taxa de Permanência (%)"]
                x_max = max(1, vals.max())
                fig.update_traces(text=vals, texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False)
                fig.update_xaxes(ticksuffix="%", range=[0, max(100, x_max) * 1.12])

        else:  # Comparativo
            d = nz(grp_sec, ['Inscritos', 'Certificados']).head(topn)
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame(columns=['Inscritos', 'Certificados']), x=['Inscritos', 'Certificados'], y=[])
            else:
                fig = px.bar(d, x=['Inscritos', 'Certificados'], y=d.index, orientation="h", barmode="group")
                fig.update_traces(texttemplate="%{x}", textposition="outside", cliponaxis=False)

        st.plotly_chart(style_fig(fig), use_container_width=True, key=f"vg_sec_lbl_{modo}_{topn}")
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="panel"><h3>Desempenho por Cargo (Inscritos)</h3>', unsafe_allow_html=True)
        if not df_cargos_rank.empty:
            df_cargos_rank2 = nz(df_cargos_rank, ["Inscritos"])
            d = df_cargos_rank2.head(topn).sort_values("Inscritos")
            if d.empty:
                st.info("Sem dados para o ranking.")
            else:
                fig2 = px.bar(d, x="Inscritos", y=d.index, orientation="h", title=f"Top {topn} Cargos por Inscritos")
                x_max2 = max(1, d["Inscritos"].max())
                fig2.update_traces(text=d["Inscritos"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig2.update_xaxes(range=[0, x_max2 * 1.15])
                st.plotly_chart(style_fig(fig2), use_container_width=True, key=f"vg_cargo_top_lbl_{topn}")
        else:
            st.info("Aba 'CARGOS' vazia ou inválida.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Funil
    st.markdown('<div class="panel"><h3>Funil de Conversão</h3>', unsafe_allow_html=True)
    if tot_insc > 0:
        funil_df = pd.DataFrame({"Etapa": ["Inscritos", "Certificados"], "Total": [tot_insc, tot_cert]})
        funil_df = nz(funil_df, ["Total"])
        if funil_df.empty:
            st.info("Sem dados para montar o funil.")
        else:
            fig_funil = px.funnel(funil_df, x="Total", y="Etapa", title=None)
            st.plotly_chart(style_fig(fig_funil, height=360), use_container_width=True, key="vg_funnel")
    else:
        st.info("Sem dados para montar o funil.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Cargos
with tab2:
    st.markdown('<div class="panel"><h4>Visão de Cargos</h4>', unsafe_allow_html=True)

    tipos_sel = sorted(df_cargos_ev_filtrado["Tipo"].dropna().unique().tolist()) or ["Masterclass","Workshop","Curso de IA"]
    df_ev_view = df_cargos_ev_filtrado[df_cargos_ev_filtrado["Tipo"].isin(tipos_sel)].copy()

    # Verificar quais colunas de cargo existem no DataFrame filtrado
    cargo_cols_existentes = [c for c in cargo_cols if c in df_ev_view.columns]
    tot_view = (df_ev_view[cargo_cols_existentes].sum().sort_values(ascending=False) if not df_ev_view.empty and cargo_cols_existentes else pd.Series(dtype=float))
    df_rank_view = (pd.DataFrame({"Cargo": tot_view.index, "Inscritos": tot_view.values}).set_index("Cargo")
                    if not tot_view.empty else pd.DataFrame())

    col1, col2 = st.columns([1.65, 1])

    # Ranking
    with col1:
        if not df_rank_view.empty:
            df_rank_view = nz(df_rank_view, ["Inscritos"])
            top_df = df_rank_view.head(topn).sort_values("Inscritos")
            if top_df.empty:
                st.info("Sem dados para o ranking.")
            else:
                fig_rank = px.bar(top_df, x="Inscritos", y=top_df.index, orientation="h", title=f"Top {topn} Cargos por Inscritos")
                x_max = max(1, top_df["Inscritos"].max())
                fig_rank.update_traces(text=top_df["Inscritos"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig_rank.update_xaxes(range=[0, x_max * 1.15])
                st.plotly_chart(style_fig(fig_rank, height=460), use_container_width=True, key=f"t2_cargos_rank_{topn}")
        else:
            st.info("Sem dados para o ranking.")

    # Donut
    with col2:
        if not df_rank_view.empty:
            top_part = df_rank_view.head(topn).reset_index()
            top_part = nz(top_part, ["Inscritos"])
            top_part = top_part[top_part["Inscritos"] > 0]
            if top_part.empty:
                st.info("Sem dados para o donut.")
            else:
                fig_pie = px.pie(top_part, values="Inscritos", names="Cargo", hole=0.55)
                fig_pie.update_traces(textinfo="percent", textposition="inside", insidetextorientation="radial")
                fig_pie.update_layout(legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02))
                st.plotly_chart(style_fig(fig_pie, height=460), use_container_width=True, key=f"t2_cargos_pie_{topn}")
        else:
            st.info("Sem dados para o donut.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Stacked por tipo
    st.markdown('<div class="panel"><h3>Inscritos por Cargo e Tipo de Evento</h3>', unsafe_allow_html=True)
    if not df_ev_view.empty and cargo_cols_existentes:
        df_tipo_view = df_ev_view.groupby("Tipo")[cargo_cols_existentes].sum().T.replace([np.inf, -np.inf], 0).fillna(0)
        cols_presentes = [c for c in tipos_sel if c in df_tipo_view.columns]
        if cols_presentes:
            top_idx = df_rank_view.head(topn).index
            stacked_df = df_tipo_view.loc[df_tipo_view.index.intersection(top_idx), cols_presentes]
            stacked_df = stacked_df.loc[stacked_df.sum(axis=1).sort_values().index]
            if stacked_df.empty:
                st.info("Sem dados para o stacked.")
            else:
                fig_stacked = px.bar(stacked_df, x=cols_presentes, y=stacked_df.index, orientation="h", barmode="stack")
                fig_stacked.update_traces(texttemplate="%{x:.0f}", textposition="inside", insidetextanchor="middle")
                st.plotly_chart(style_fig(fig_stacked), use_container_width=True, key=f"t2_cargos_stacked_{topn}")
        else:
            st.info("Tipos selecionados não possuem dados.")
    else:
        st.info("Sem dados para o stacked.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Série por evento
    st.markdown('<div class="panel"><h3>Evolução por Evento</h3>', unsafe_allow_html=True)
    if cargo_cols_existentes and not df_ev_view.empty:
        cargo_escolhido = st.selectbox("Escolha um cargo", cargo_cols_existentes, index=0, key="t2_cargo_series")

        evento_col = "evento" if "evento" in df_ev_view.columns else df_ev_view.columns[0]

        rename_dict = {cargo_escolhido: "Inscritos"}
        if evento_col != "Evento":
            rename_dict[evento_col] = "Evento"

        serie = df_ev_view[[evento_col, "Tipo", cargo_escolhido]].rename(columns=rename_dict)
        serie = nz(serie, ["Inscritos"]) 

        if not serie.empty:
            serie["Tipo"] = serie["Tipo"].astype(str).str.strip().str.title().replace({"Curso": "Curso de IA"})

            top_ev = (
                serie.groupby("Evento")["Inscritos"].sum().sort_values(ascending=False).head(topn).index
            )
            serie = serie[serie["Evento"].isin(top_ev)].copy()

            def _evt_short(s: str, t: str) -> str:
                m = re.search(r"(\d+)\s*[ºª]?\s*(Masterclass|Workshop|Curso(?:\s+de\s+IA)?)", str(s), flags=re.I)
                if m:
                    num = m.group(1)
                    kind = re.sub(r"(?i)^curso(?:\s+de\s+ia)?$", "Curso de IA", m.group(2)).title()
                    return f"{num}° {kind}"
                return " ".join(str(s).split()[:6])

            serie["EVENTO_LABEL"] = serie.apply(lambda r: _evt_short(r["Evento"], r["Tipo"]), axis=1)

            fig_series = px.bar(
                serie, x="Inscritos", y="EVENTO_LABEL", color="Tipo", barmode="group", title=None, orientation="h"
            )
            x_max = max(1, serie["Inscritos"].max())
            fig_series.update_traces(text=serie["Inscritos"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
            fig_series.update_xaxes(range=[0, x_max * 1.15])
            st.plotly_chart(style_fig(fig_series, height=520), use_container_width=True, key=f"t2_cargos_series_{cargo_escolhido}")
        else:
            st.info("Sem dados para a série.")
    else:
        st.info("Nenhuma coluna de cargo encontrada.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Secretarias
with tab3:
    # 🔧 base sem labels vazios/NaN
    df_f_clean = drop_empty_labels(df_f_filtrado, "SECRETARIA/ÓRGÃO")
    
    # Determinar colunas corretas baseadas no formato
    inscritos_col = 'n_inscritos' if 'n_inscritos' in df_f_clean.columns else 'Nº INSCRITOS'
    certificados_col = 'n_certificados' if 'n_certificados' in df_f_clean.columns else 'Nº CERTIFICADOS'

    grp = (
        df_f_clean.groupby('SECRETARIA/ÓRGÃO')[[inscritos_col, certificados_col]]
                .sum()
                .reset_index()
    )
    
    grp = grp.replace([np.inf, -np.inf], pd.NA)
    grp = nz(grp, [inscritos_col, certificados_col])
    grp['Taxa de Certificação (%)'] = (
        grp[certificados_col] / grp[inscritos_col]
    ).replace([np.inf, -np.inf], 0).fillna(0) * 100


    show_sec_table = st.toggle("Mostrar tabela de secretarias", value=False,
                               help="Ative para visualizar o consolidado; por padrão fica oculto.")
    if show_sec_table:
        df_panel(grp.round(2), "Consolidado por Secretaria/Órgão", key=f"tbl_sec_{len(grp)}")

    st.markdown('<div class="panel"><h3>Inscritos X Certificados</h3>', unsafe_allow_html=True)
    cA, cB = st.columns(2)

    with cA:
        top_comp = grp.sort_values(inscritos_col, ascending=False).head(topn)
        if top_comp.empty:
            st.info("Sem dados para o comparativo.")
        else:
            fig_comp = px.bar(top_comp, x=[inscritos_col, certificados_col], y='SECRETARIA/ÓRGÃO',
                              orientation='h', barmode='group', text_auto=True, title=None)
            fig_comp.update_traces(textposition="outside", cliponaxis=False, textfont_size=12)
            st.plotly_chart(style_fig(fig_comp), use_container_width=True, key=f"sec_comp_{topn}")

    with cB:
        top_taxa = grp[grp[inscritos_col] > 0].sort_values('Taxa de Certificação (%)', ascending=False).head(topn)
        top_taxa = nz(top_taxa, ['Taxa de Certificação (%)'])
        if top_taxa.empty:
            st.info("Sem dados para taxa.")
        else:
            fig_taxa = px.bar(top_taxa, x='Taxa de Certificação (%)', y='SECRETARIA/ÓRGÃO',
                              orientation='h', title=f'Top {topn} por Taxa de Certificação',
                              text='Taxa de Certificação (%)')
            fig_taxa.update_traces(texttemplate='%{text:.0f}%', textposition='outside', cliponaxis=False, textfont_size=12)
            fig_taxa.update_xaxes(ticksuffix="%")
            st.plotly_chart(style_fig(fig_taxa), use_container_width=True, key=f"sec_taxa_top_{topn}")

    st.markdown('<div class="panel"><h3>Participação no total de Inscritos</h3>', unsafe_allow_html=True)
    grp_tree = grp.sort_values(inscritos_col, ascending=False).head(max(topn*2, 20))
    grp_tree = nz(grp_tree, [inscritos_col])
    if grp_tree.empty:
        st.info("Sem dados para o treemap.")
    else:
        treemap = px.treemap(grp_tree, path=['SECRETARIA/ÓRGÃO'], values=inscritos_col,
                             color='Taxa de Certificação (%)', custom_data=['Taxa de Certificação (%)'],
                             title='Treemap — maiores contribuições')
        treemap.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[0]:.0f}%", textposition="middle center")
        treemap.update_layout(uniformtext_minsize=12, uniformtext_mode='show')
        st.plotly_chart(style_fig(treemap, height=520), use_container_width=True, key="sec_tree")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Eventos
with tab4:
    if df_visao_filtrado.empty:
        st.info("Aba 'VISÃO ABERTA' vazia ou inválida (após filtros).")
    else:
        ev = df_visao_filtrado.copy()
        
        # Determinar colunas corretas baseadas no formato
        inscritos_col_ev = 'n_inscritos' if 'n_inscritos' in ev.columns else 'Nº INSCRITOS'
        certificados_col_ev = 'n_certificados' if 'n_certificados' in ev.columns else 'Nº CERTIFICADOS'
        
        # garantir numéricos e filtrar NaN/±inf
        ev[inscritos_col_ev] = pd.to_numeric(ev[inscritos_col_ev], errors="coerce")
        ev[certificados_col_ev] = pd.to_numeric(ev[certificados_col_ev], errors="coerce")
        
        ev = nz(ev, [inscritos_col_ev, certificados_col_ev])

        # Detectar coluna de evento dinamicamente
        if is_parquet:
            evento_col_ev = 'evento' if 'evento' in ev.columns else ev.columns[0]
        else:
            evento_col_ev = df_cargos_raw.columns[0]  # Primeira coluna do Excel
        
        ev["Tipo"] = (
            ev[evento_col_ev].astype(str)
            .str.extract(r"(Masterclass|Workshop|Curso)", expand=False)
            .str.title().replace({"Curso": "Curso de IA"})
        ).fillna("Outro")
        ev["Taxa de Certificação (%)"] = (
            ev[certificados_col_ev] / ev[inscritos_col_ev]
        ).replace([pd.NA, float("inf")], 0).fillna(0) * 100
        ev["Evasão (Nº)"] = (ev[inscritos_col_ev] - ev[certificados_col_ev]).clip(lower=0)

        # =========================
        # KPIs DE TURMAS
        # =========================
        st.markdown("### 📊 Métricas de Turmas/Eventos")
        
        total_turmas = len(ev)
        media_participantes = ev[inscritos_col_ev].mean() if total_turmas > 0 else 0
        media_certificados = ev[certificados_col_ev].mean() if total_turmas > 0 else 0
        taxa_cert_eventos = (ev[certificados_col_ev].sum() / ev[inscritos_col_ev].sum() * 100) if ev[inscritos_col_ev].sum() > 0 else 0
        
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        kpi_col1.markdown(f'<div class="kpi"><h4>Total de Turmas</h4><div class="val">{total_turmas}</div></div>', unsafe_allow_html=True)
        kpi_col2.markdown(f'<div class="kpi"><h4>Média Participantes</h4><div class="val">{media_participantes:.1f}</div></div>', unsafe_allow_html=True)
        kpi_col3.markdown(f'<div class="kpi"><h4>Média Certificados</h4><div class="val">{media_certificados:.1f}</div></div>', unsafe_allow_html=True)
        kpi_col4.markdown(f'<div class="kpi"><h4>Taxa Certificação</h4><div class="val">{taxa_cert_eventos:.1f}%</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sep"></div>', unsafe_allow_html=True)
        
        # =========================
        # MÉTRICAS POR TIPO
        # =========================
        st.markdown("### 📚 Análise por Tipo de Evento")
        
        # Calcular métricas por tipo
        metricas_tipo = ev.groupby("Tipo").agg({
            evento_col_ev: 'count',
            inscritos_col_ev: ['sum', 'mean'],
            certificados_col_ev: ['sum', 'mean']
        }).round(1)
        
        metricas_tipo.columns = ['Num_Eventos', 'Total_Inscritos', 'Media_Inscritos', 'Total_Certificados', 'Media_Certificados']
        metricas_tipo['Taxa_Cert'] = (metricas_tipo['Total_Certificados'] / metricas_tipo['Total_Inscritos'] * 100).round(1)
        metricas_tipo = metricas_tipo.reset_index()
        
        # Exibir tabela de métricas
        st.dataframe(
            metricas_tipo,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tipo": st.column_config.TextColumn("Tipo de Evento", width="medium"),
                "Num_Eventos": st.column_config.NumberColumn("Nº Turmas", format="%d"),
                "Total_Inscritos": st.column_config.NumberColumn("Total Participantes", format="%d"),
                "Media_Inscritos": st.column_config.NumberColumn("Média Participantes", format="%.1f"),
                "Total_Certificados": st.column_config.NumberColumn("Total Certificados", format="%d"),
                "Media_Certificados": st.column_config.NumberColumn("Média Certificados", format="%.1f"),
                "Taxa_Cert": st.column_config.NumberColumn("Taxa Cert. (%)", format="%.1f%%"),
            }
        )
        
        st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

        def evento_curto(evento: str, tipo: str) -> str:
            s = str(evento)
            m = re.search(r"(\d+)\s*[ºª]?\s*(?=Masterclass|Workshop|Curso)", s, flags=re.I)
            num = m.group(1) if m else None
            base = "Curso" if "Curso" in tipo else ("Masterclass" if "Masterclass" in tipo else ("Workshop" if "Workshop" in tipo else tipo))
            return f"{num}° {base}" if num else base

        ev["EVENTO_CURTO"] = ev.apply(lambda r: evento_curto(r[evento_col_ev], r["Tipo"]), axis=1)

        # =========================
        # TABELA DETALHADA DE EVENTOS
        # =========================
        st.markdown("### 📋 Detalhamento de Todas as Turmas")
        
        show_ev_table = st.toggle("Mostrar tabela detalhada de eventos", value=True,
                                  help="Visualize todos os eventos com suas métricas individuais")
        if show_ev_table:
            # Preparar dados para exibição
            ev_display = ev.copy()
            ev_display = ev_display.sort_values(inscritos_col_ev, ascending=False)
            
            cols_display = []
            col_config = {}
            
            if evento_col_ev in ev_display.columns:
                cols_display.append(evento_col_ev)
                col_config[evento_col_ev] = st.column_config.TextColumn("Evento", width="large")
            
            if "Tipo" in ev_display.columns:
                cols_display.append("Tipo")
                col_config["Tipo"] = st.column_config.TextColumn("Tipo", width="small")
            
            if inscritos_col_ev in ev_display.columns:
                cols_display.append(inscritos_col_ev)
                col_config[inscritos_col_ev] = st.column_config.NumberColumn("Inscritos", format="%d")
            
            if certificados_col_ev in ev_display.columns:
                cols_display.append(certificados_col_ev)
                col_config[certificados_col_ev] = st.column_config.NumberColumn("Certificados", format="%d")
            
            if "Taxa de Certificação (%)" in ev_display.columns:
                cols_display.append("Taxa de Certificação (%)")
                col_config["Taxa de Certificação (%)"] = st.column_config.NumberColumn("Taxa Cert. (%)", format="%.1f%%")
            
            st.dataframe(
                ev_display[cols_display],
                use_container_width=True,
                hide_index=True,
                column_config=col_config,
                height=400
            )
            
            st.caption(f"📊 Total: {len(ev_display)} turma(s)")
        
        st.markdown('<div class="sep"></div>', unsafe_allow_html=True)
        
        # =========================
        # VISUALIZAÇÕES EXISTENTES
        # =========================
        st.markdown("### 📈 Visualizações Comparativas")


        by_tipo = ev.groupby("Tipo")[[inscritos_col_ev, certificados_col_ev]].sum().replace([np.inf, -np.inf], 0).fillna(0)
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            if not by_tipo.empty:
                pie = px.pie(by_tipo.reset_index(), values=inscritos_col_ev, names="Tipo", hole=0.55)
                pie.update_layout(legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02))
                st.plotly_chart(style_fig(pie, height=460), use_container_width=True, key=f"ev_pie_{len(by_tipo)}")
            else:
                st.info("Sem dados para o donut.")

        with col_right:
            if not ev.empty:
                box = px.box(ev, x="Tipo", y="Taxa de Certificação (%)", title="Taxa de Certificação — distribuição por tipo")
                box.update_yaxes(ticksuffix="%")
                st.plotly_chart(style_fig(box, height=460), use_container_width=True, key="ev_box")
            else:
                st.info("Sem dados para o boxplot.")

        if not by_tipo.empty:
            st.markdown('<div class="panel"><h3>Totais por tipo (Inscritos x Certificados)</h3>', unsafe_allow_html=True)
            by_tipo2 = by_tipo.reset_index().melt(id_vars="Tipo",
                                                  value_vars=[inscritos_col_ev, certificados_col_ev],
                                                  var_name="Métrica", value_name="Total")
            by_tipo2 = nz(by_tipo2, ["Total"])
            if by_tipo2.empty:
                st.info("Sem dados para barras por tipo.")
            else:
                bar_tipo = px.bar(by_tipo2, x="Tipo", y="Total", color="Métrica", barmode="group", title=None)
                bar_tipo.update_traces(texttemplate="%{y}", textposition="outside", cliponaxis=False)
                maxy = max(1, by_tipo2["Total"].max())
                bar_tipo.update_yaxes(range=[0, maxy * 1.15])
                st.plotly_chart(style_fig(bar_tipo, height=420), use_container_width=True, key="ev_bar_tipo")
            st.markdown('</div>', unsafe_allow_html=True)

        if not ev.empty:
            st.markdown('<div class="panel"><h3>Treemap — participação por evento</h3>', unsafe_allow_html=True)
            def rotulo_curto(evento: str, tipo: str) -> str:
                s = str(evento)
                base = s.split(":", 1)[0].strip() or tipo
                m = re.search(r"(\d+)\s*[ºª]?\s*(Masterclass|Workshop|Curso(?:\s+de\s+IA)?)", base, flags=re.I)
                if m:
                    num = m.group(1)
                    kind = m.group(2)
                    kind = re.sub(r"(?i)^curso(?:\s+de\s+ia)?$", "Curso de IA", kind).title()
                    return f"{num}° {kind}"
                return " ".join(base.split()[:4])

            ev_tmp = ev.copy()
            ev_tmp = nz(ev_tmp, [inscritos_col_ev])
            if ev_tmp.empty:
                st.info("Sem dados para o treemap.")
            else:
                ev_tmp["EVENTO_LABEL"] = ev_tmp.apply(lambda r: rotulo_curto(r[evento_col_ev], r["Tipo"]), axis=1)
                col_tm, col_desc = st.columns([4, 1.7], gap="large")
                with col_tm:
                    tmap = px.treemap(
                        ev_tmp.sort_values(inscritos_col_ev, ascending=False).head(max(topn*2, 20)),
                        path=["Tipo", "EVENTO_LABEL"], values=inscritos_col_ev, title=None
                    )
                    tmap.update_traces(
                        textinfo="label+text",
                        texttemplate="%{label}<br>%{percentRoot:.1%}",
                        textposition="middle center",
                        hovertemplate="<b>%{label}</b><br>Inscritos: %{value}<br>Participação: %{percentRoot:.1%}<extra></extra>",
                    )
                    st.plotly_chart(style_fig(tmap, height=520), use_container_width=True, key="ev_treemap_labels_pct")
                with col_desc:
                    st.markdown("""
                    <div class="panel">
                    <h3>O que é essa porcentagem?</h3>
                    <p>É a <b>participação no total de inscritos</b> considerando todos os filtros atuais.</p>
                    <ul>
                        <li><b>Tipo</b> (Curso, Masterclass, Workshop): % do total para cada tipo.</li>
                        <li><b>Evento</b> (ex.: <i>11° Curso</i>): % daquele evento no total.</li>
                    </ul>
                    <p>Passe o mouse para ver <b>inscritos absolutos</b> e a mesma participação (%).</p>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --------- Órgãos Parceiros
with tab5:
    st.markdown('<div class="panel"><h3>🤝 Análise de Órgãos Parceiros</h3>', unsafe_allow_html=True)
    
    if df_orgaos_parceiros is not None and len(df_orgaos_parceiros) > 0:
        # KPIs de órgãos parceiros
        total_parceiros = len(df_orgaos_parceiros)
        total_inscritos_parceiros = df_orgaos_parceiros['n_inscritos'].sum()
        total_certificados_parceiros = df_orgaos_parceiros['n_certificados'].sum()
        taxa_cert_parceiros = (total_certificados_parceiros / total_inscritos_parceiros * 100) if total_inscritos_parceiros > 0 else 0
        
        kpi_p1, kpi_p2, kpi_p3, kpi_p4 = st.columns(4)
        kpi_p1.markdown(f'<div class="kpi"><h4>Órgãos Parceiros</h4><div class="val">{total_parceiros}</div></div>', unsafe_allow_html=True)
        kpi_p2.markdown(f'<div class="kpi"><h4>Total Inscritos</h4><div class="val">{fmt_int_br(total_inscritos_parceiros)}</div></div>', unsafe_allow_html=True)
        kpi_p3.markdown(f'<div class="kpi"><h4>Total Certificados</h4><div class="val">{fmt_int_br(total_certificados_parceiros)}</div></div>', unsafe_allow_html=True)
        kpi_p4.markdown(f'<div class="kpi"><h4>Taxa Certificação</h4><div class="val">{taxa_cert_parceiros:.2f}%</div></div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sep"></div>', unsafe_allow_html=True)
        
        # Gráficos e análises
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.markdown('<div class="panel"><h4>Top Órgãos Parceiros por Inscritos</h4>', unsafe_allow_html=True)
            top_parceiros = df_orgaos_parceiros.head(10).sort_values('n_inscritos')
            if not top_parceiros.empty:
                fig_parceiros = px.bar(
                    top_parceiros, 
                    x='n_inscritos', 
                    y='orgao_parceiro', 
                    orientation='h',
                    title=None,
                    labels={'n_inscritos': 'Inscritos', 'orgao_parceiro': 'Órgão Parceiro'}
                )
                x_max_p = max(1, top_parceiros['n_inscritos'].max())
                fig_parceiros.update_traces(
                    text=top_parceiros['n_inscritos'], 
                    texttemplate="%{x}", 
                    textposition="outside", 
                    cliponaxis=False
                )
                fig_parceiros.update_xaxes(range=[0, x_max_p * 1.15])
                st.plotly_chart(style_fig(fig_parceiros, height=460), use_container_width=True, key="parceiros_bar")
            else:
                st.info("Sem dados para exibir.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_p2:
            st.markdown('<div class="panel"><h4>Taxa de Certificação por Órgão</h4>', unsafe_allow_html=True)
            top_taxa_parceiros = df_orgaos_parceiros[df_orgaos_parceiros['n_inscritos'] > 0].sort_values('taxa_certificacao', ascending=False).head(10).sort_values('taxa_certificacao')
            if not top_taxa_parceiros.empty:
                fig_taxa_parceiros = px.bar(
                    top_taxa_parceiros,
                    x='taxa_certificacao',
                    y='orgao_parceiro',
                    orientation='h',
                    title=None,
                    labels={'taxa_certificacao': 'Taxa de Certificação (%)', 'orgao_parceiro': 'Órgão Parceiro'}
                )
                fig_taxa_parceiros.update_traces(
                    text=top_taxa_parceiros['taxa_certificacao'],
                    texttemplate="%{x:.1f}%",
                    textposition="outside",
                    cliponaxis=False
                )
                fig_taxa_parceiros.update_xaxes(ticksuffix="%", range=[0, 105])
                st.plotly_chart(style_fig(fig_taxa_parceiros, height=460), use_container_width=True, key="parceiros_taxa")
            else:
                st.info("Sem dados para exibir.")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Treemap de participação
        st.markdown('<div class="panel"><h3>Participação dos Órgãos Parceiros</h3>', unsafe_allow_html=True)
        if not df_orgaos_parceiros.empty:
            treemap_parceiros = px.treemap(
                df_orgaos_parceiros.head(20),
                path=['orgao_parceiro'],
                values='n_inscritos',
                color='taxa_certificacao',
                color_continuous_scale='RdYlGn',
                title='Distribuição de Participantes por Órgão Parceiro',
                hover_data={'n_inscritos': True, 'n_certificados': True, 'taxa_certificacao': ':.1f'}
            )
            treemap_parceiros.update_traces(
                texttemplate="<b>%{label}</b><br>%{value} part.<br>%{color:.1f}% cert.",
                textposition="middle center",
                textfont_size=10
            )
            treemap_parceiros.update_layout(height=500)
            st.plotly_chart(style_fig(treemap_parceiros, height=500), use_container_width=True, key="parceiros_treemap")
        else:
            st.info("Sem dados para o treemap.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Tabela detalhada
        st.markdown('<div class="panel"><h3>Tabela Detalhada de Órgãos Parceiros</h3>', unsafe_allow_html=True)
        show_parceiros_table = st.toggle("Mostrar tabela detalhada", value=False, key="toggle_parceiros")
        if show_parceiros_table:
            df_display_parceiros = df_orgaos_parceiros.copy()
            df_display_parceiros = df_display_parceiros.sort_values('n_inscritos', ascending=False)
            st.dataframe(
                df_display_parceiros,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "orgao_parceiro": st.column_config.TextColumn("Órgão Parceiro", width="large"),
                    "n_inscritos": st.column_config.NumberColumn("Inscritos", format="%d"),
                    "n_certificados": st.column_config.NumberColumn("Certificados", format="%d"),
                    "n_turmas": st.column_config.NumberColumn("Turmas", format="%d"),
                    "taxa_certificacao": st.column_config.NumberColumn("Taxa Cert. (%)", format="%.2f%%"),
                    "formatos": st.column_config.TextColumn("Formatos", width="medium"),
                    "eixos": st.column_config.TextColumn("Eixos", width="medium"),
                },
                height=400
            )
            st.caption(f"📊 Total: {len(df_display_parceiros)} órgão(ões) parceiro(s)")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Análise por formato e eixo
        st.markdown('<div class="panel"><h3>Análise por Formato e Eixo</h3>', unsafe_allow_html=True)
        
        # Filtrar dados de órgãos parceiros do df_dados
        if 'orgao_externo' in df_dados.columns:
            df_parceiros_detalhado = df_dados[df_dados['orgao_externo'] == 'Sim'].copy()
            
            if len(df_parceiros_detalhado) > 0:
                col_p3, col_p4 = st.columns(2)
                
                with col_p3:
                    if 'formato' in df_parceiros_detalhado.columns:
                        formato_counts = df_parceiros_detalhado['formato'].value_counts()
                        if not formato_counts.empty:
                            fig_formato_parceiros = px.pie(
                                formato_counts.reset_index(),
                                values='count',
                                names='formato',
                                title='Distribuição por Formato',
                                hole=0.4
                            )
                            st.plotly_chart(style_fig(fig_formato_parceiros, height=400), use_container_width=True, key="parceiros_formato")
                
                with col_p4:
                    if 'eixo' in df_parceiros_detalhado.columns:
                        eixo_counts = df_parceiros_detalhado['eixo'].value_counts()
                        if not eixo_counts.empty:
                            fig_eixo_parceiros = px.pie(
                                eixo_counts.reset_index(),
                                values='count',
                                names='eixo',
                                title='Distribuição por Eixo',
                                hole=0.4
                            )
                            st.plotly_chart(style_fig(fig_eixo_parceiros, height=400), use_container_width=True, key="parceiros_eixo")
        else:
            st.info("Dados detalhados de formato e eixo não disponíveis.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("📊 Nenhum órgão parceiro encontrado nos dados ou arquivo não foi gerado. Execute o processamento de dados para criar o arquivo 'orgaos_parceiros.parquet'.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# RODAPÉ GLOBAL
# =========================
st.markdown("""
<div class="footer">
    <div class="logo">🏛️ Secretaria de Inteligência Artificial do Piauí</div>
    <div>Desenvolvido pela SIA-PI • <span class="year">2025</span></div>
    <div style="margin-top: 8px; font-size: 0.8rem;">Dashboard CapacitIA - Análise de Dados e Capacitação em IA</div>
</div>
""", unsafe_allow_html=True)
