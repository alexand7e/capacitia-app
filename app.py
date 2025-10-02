import unicodedata,re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
import numpy as np

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="Dashboard CapacitIA",
    page_icon="🚀",
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
# tenta achar automaticamente o arquivo (novo ou antigo)
_CANDIDATES = [
    Path(".data/processed") / "RelatorioCapacitia_AtualizadoAgosto.xlsx",
    Path(".data/processed") / "relatorio_capacitia.xlsx",
    Path("RelatorioCapacitia_AtualizadoAgosto.xlsx"),
    Path("relatorio_capacitia.xlsx"),
]
DEFAULT_XLSX = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

@st.cache_data(show_spinner=False)
def load_sheets(path: Path):
    """Carrega dados do Excel (mantido para compatibilidade)."""
    xls = pd.ExcelFile(path)
    df_dados       = pd.read_excel(xls, "DADOS", header=6)
    df_visao       = pd.read_excel(xls, "VISÃO ABERTA", header=6)      # contém a linha TOTAL GERAL
    df_secretarias = pd.read_excel(xls, "SECRETARIA-ÓRGÃO", header=None)  # header dinâmico
    df_cargos_raw  = pd.read_excel(xls, "CARGOS", header=2)
    try:
        df_min     = pd.read_excel(xls, "MINISTRANTECARGA HORÁRIA", header=1)
    except Exception:
        df_min     = None
    return df_dados, df_visao, df_secretarias, df_cargos_raw, df_min

@st.cache_data(show_spinner=False)
def load_parquet_data():
    """Carrega dados dos arquivos Parquet processados."""
    processed_path = Path(".data") / "processed"
    
    try:
        df_dados = pd.read_parquet(processed_path / "dados.parquet")
        df_visao = pd.read_parquet(processed_path / "visao_aberta.parquet")
        df_secretarias = pd.read_parquet(processed_path / "secretarias.parquet")
        df_cargos_raw = pd.read_parquet(processed_path / "cargos.parquet")
        try:
            df_min = pd.read_parquet(processed_path / "ministrantes.parquet")
        except Exception:
            df_min = None
        return df_dados, df_visao, df_secretarias, df_cargos_raw, df_min
    except Exception as e:
        st.error(f"Erro ao carregar arquivos Parquet: {e}")
        return None, None, None, None, None

# Tentar carregar dados Parquet primeiro, depois Excel como fallback
processed_path = Path(".data") / "processed"
parquet_files_exist = all([
    (processed_path / "dados.parquet").exists(),
    (processed_path / "visao_aberta.parquet").exists(),
    (processed_path / "secretarias.parquet").exists(),
    (processed_path / "cargos.parquet").exists()
])

if parquet_files_exist:
    # Usar dados Parquet (mais rápido)
    df_dados, df_visao, df_secretarias_raw, df_cargos_raw, df_min = load_parquet_data()
    if df_dados is None:
        st.error("Erro ao carregar arquivos Parquet. Tentando Excel como fallback...")
        if not DEFAULT_XLSX.exists():
            st.error(f"Arquivo Excel também não encontrado. Verifique estes caminhos:\n{[str(p) for p in _CANDIDATES]}")
            st.stop()
        df_dados, df_visao, df_secretarias_raw, df_cargos_raw, df_min = load_sheets(DEFAULT_XLSX)
        is_parquet = False
    else:
        is_parquet = True
else:
    # Usar Excel como fallback
    if not DEFAULT_XLSX.exists():
        st.error(f"Arquivos Parquet não encontrados e arquivo Excel não encontrado. Verifique estes caminhos:\n{[str(p) for p in _CANDIDATES]}")
        st.stop()
    df_dados, df_visao, df_secretarias_raw, df_cargos_raw, df_min = load_sheets(DEFAULT_XLSX)
    is_parquet = False

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

def _col_like(df, *keywords):
    """Retorna o nome da 1ª coluna cujo título contém todos os keywords (case-insensitive)."""
    up = {c: str(c).upper().replace("\xa0", " ") for c in df.columns}
    for c, name in up.items():
        if all(k.upper() in name for k in keywords):
            return c
    return None

def _normalize_org(s: str) -> str:
    s = "" if pd.isna(s) else str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # remove acentos
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

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

def drop_empty_labels(df: pd.DataFrame, col: str):
    s = df[col].astype(str)
    mask = s.str.strip().ne("") & ~s.str.lower().isin(["nan", "none", "nat"])
    return df.loc[mask].copy()



# =========================
# SECRETARIA-ÓRGÃO (limpeza + filtro oculto)
# =========================
def _find_header_row(df: pd.DataFrame) -> int:
    for i in range(min(15, len(df))):
        row_txt = " ".join([str(v).upper() for v in df.iloc[i].tolist()])
        if "SECRETARIA/ÓRGÃO" in row_txt and "INSCRITOS" in row_txt:
            return i
    return 0

def clean_secretarias(df_secretarias_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_secretarias_raw.copy()
    
    # Verifica se já está no formato padronizado (Parquet)
    if 'secretaria_orgao' in df.columns:
        # Formato padronizado dos arquivos Parquet
        df = df.rename(columns={
            'secretaria_orgao': 'SECRETARIA/ÓRGÃO',
            'n_inscritos': 'Nº INSCRITOS',
            'n_certificados': 'Nº CERTIFICADOS',
            'n_evasao': 'Nº EVASÃO'
        })
        return df[["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS","Nº EVASÃO"] if "Nº EVASÃO" in df.columns else ["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS"]]
    
    # Formato original do Excel
    hdr = _find_header_row(df)
    df = df.iloc[hdr:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df.iloc[1:].copy()

    # remover linhas de seções/totais
    mask_meta = df.astype(str).apply(
        lambda s: s.str.upper().str.contains("ATIVIDADE/EVENTO|TOTAL GERAL|^TOTAL$", na=False)
    ).any(axis=1)
    df = df[~mask_meta].dropna(how="all").copy()

    # normaliza tipos
    col_ins = _col_like(df, "INSCRIT") or "Nº INSCRITOS"
    col_cer = _col_like(df, "CERTIFIC") or "Nº CERTIFICADOS"
    col_eva = _col_like(df, "EVAS")     or "Nº EVASÃO"
    for col in [col_ins, col_cer, col_eva]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # padroniza nome da coluna de órgão
    org_cols = [c for c in df.columns if "SECRETARIA" in str(c).upper() or "ÓRGÃO" in str(c).upper()]
    if not org_cols:
        # Se não encontrar, usar a primeira coluna como fallback
        nome_org_col = df.columns[0]
    else:
        nome_org_col = org_cols[0]
    df[nome_org_col] = df[nome_org_col].astype(str).str.strip()

    # renomeia para nomes "fixos" usados nos gráficos
    df = df.rename(columns={
        nome_org_col: "SECRETARIA/ÓRGÃO",
        col_ins: "Nº INSCRITOS",
        col_cer: "Nº CERTIFICADOS",
        col_eva: "Nº EVASÃO"
    })
    return df[["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS","Nº EVASÃO"] if "Nº EVASÃO" in df.columns else ["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS"]]

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
def _col_like(df, *keywords):
    up = {c: str(c).upper().replace("\xa0", " ") for c in df.columns}
    for c, name in up.items():
        if all(k.upper() in name for k in keywords):
            return c
    return None

def _parse_ptbr_number(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return np.nan
    s = str(x).strip()
    # remove símbolos e espaços; trata milhar . e decimal ,
    s = s.replace("\xa0", " ").replace(" ", "")
    s = re.sub(r"[^\d,.\-]", "", s)          # mantém só dígitos, . , e sinal
    if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return np.nan

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
    # Formato padronizado dos arquivos Parquet
    df_cargos_rank = df_cargos_raw.groupby('cargo')['total_inscritos'].sum().sort_values(ascending=False)
    df_cargos_rank = pd.DataFrame({"Cargo": df_cargos_rank.index, "Inscritos": df_cargos_rank.values}).set_index("Cargo")
    
    # Criar df_cargos_ev baseado nos dados reais de cargos
    # Agrupar por cargo e criar eventos simulados para cada cargo
    cargos_unicos = df_cargos_raw['cargo'].unique()
    eventos_por_cargo = []
    
    for i, cargo in enumerate(cargos_unicos[:10]):  # Limitar a 10 cargos principais
        cargo_data = df_cargos_raw[df_cargos_raw['cargo'] == cargo]
        total_inscritos = cargo_data['total_inscritos'].sum()
        
        # Criar 3 eventos simulados para cada cargo
        for j, tipo in enumerate(['Masterclass', 'Workshop', 'Curso']):
            eventos_por_cargo.append({
                'evento': f'{cargo} - {tipo} {j+1}',
                'Tipo': tipo,
                cargo: int(total_inscritos * [0.3, 0.4, 0.3][j])  # Distribuir proporcionalmente
            })
    
    df_cargos_ev = pd.DataFrame(eventos_por_cargo)
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
# HEADER + KPIs
# =========================
def fmt_int_br(n: int) -> str:
    return str(f"{int(n):,}").replace(",", ".")

st.markdown(f"""
<div class="hero">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
    <div>
      <div style="font-size:2.0rem;font-weight:800;letter-spacing:.3px;">🚀 Dashboard CapacitIA</div>
      <div style="color:#a6accd;">Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

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
    # CORREÇÃO: Usar nome correto da coluna em df_secretarias
    df_secretarias_filtrado = df_secretarias[df_secretarias["SECRETARIA/ÓRGÃO"] == orgao_selecionado].copy()
    # CORREÇÃO: Usar df_dados em vez de df_f
    df_dados_filtrado = df_dados_filtrado[df_dados_filtrado["orgao"] == orgao_selecionado].copy()
    # Manter df_f para compatibilidade com código existente
    df_f_filtrado = df_f[df_f["SECRETARIA/ÓRGÃO"] == orgao_selecionado].copy()
    
    # Aplicar filtro de órgão aos dados de cargos também
    if 'orgao' in df_cargos_raw.columns:
        # Para dados Parquet: filtrar cargos pelo órgão selecionado
        cargos_orgao_filtrado = df_cargos_raw[df_cargos_raw['orgao'] == orgao_selecionado]
        if not cargos_orgao_filtrado.empty:
            # Recriar df_cargos_ev apenas com cargos do órgão selecionado
            cargos_unicos_filtrados = cargos_orgao_filtrado['cargo'].unique()
            eventos_por_cargo_filtrado = []
            
            for cargo in cargos_unicos_filtrados[:10]:  # Limitar a 10 cargos principais
                cargo_data = cargos_orgao_filtrado[cargos_orgao_filtrado['cargo'] == cargo]
                total_inscritos = cargo_data['total_inscritos'].sum()
                
                # Criar 3 eventos simulados para cada cargo
                for j, tipo in enumerate(['Masterclass', 'Workshop', 'Curso']):
                    eventos_por_cargo_filtrado.append({
                        'evento': f'{cargo} - {tipo} {j+1}',
                        'Tipo': tipo,
                        cargo: int(total_inscritos * [0.3, 0.4, 0.3][j])  # Distribuir proporcionalmente
                    })
            
            if eventos_por_cargo_filtrado:
                df_cargos_ev_temp = pd.DataFrame(eventos_por_cargo_filtrado)
                # Aplicar filtro de tipo se necessário
                if tipo_selecionado != "Todos":
                    df_cargos_ev_filtrado = df_cargos_ev_temp[df_cargos_ev_temp["Tipo"] == tipo_selecionado].copy()
                else:
                    df_cargos_ev_filtrado = df_cargos_ev_temp.copy()
            else:
                # Se não há cargos para o órgão selecionado, criar DataFrame vazio
                df_cargos_ev_filtrado = pd.DataFrame(columns=df_cargos_ev.columns)
else:
    df_secretarias_filtrado = df_secretarias.copy()
    df_f_filtrado = df_f.copy()

# 3. Aplicar filtro de órgão externo
if orgao_externo_selecionado != "Todos":
    # CORREÇÃO: Usar df_dados_filtrado em vez de df_f_filtrado para filtro de órgão externo
    if 'orgao_externo' in df_dados_filtrado.columns:
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado["orgao_externo"] == orgao_externo_selecionado].copy()
        
        # Atualizar df_secretarias_filtrado baseado nos órgãos que restaram
        orgaos_restantes = df_dados_filtrado["orgao"].unique()
        df_secretarias_filtrado = df_secretarias_filtrado[df_secretarias_filtrado["SECRETARIA/ÓRGÃO"].isin(orgaos_restantes)].copy()
        
        # Manter df_f_filtrado para compatibilidade (se tiver coluna orgao_externo)
        if 'orgao_externo' in df_f.columns:
            df_f_filtrado = df_f_filtrado[df_f_filtrado["orgao_externo"] == orgao_externo_selecionado].copy()
    
    # Aplicar filtro de órgão externo aos dados de cargos também
    if 'orgao' in df_cargos_raw.columns and len(df_dados_filtrado) > 0:
        # Filtrar cargos pelos órgãos que restaram após o filtro de órgão externo
        orgaos_filtrados = df_dados_filtrado["orgao"].unique()
        cargos_orgao_externo_filtrado = df_cargos_raw[df_cargos_raw["orgao"].isin(orgaos_filtrados)]
        
        if not cargos_orgao_externo_filtrado.empty:
            # Recriar df_cargos_ev apenas com cargos da classificação selecionada
            cargos_unicos_filtrados = cargos_orgao_externo_filtrado['cargo'].unique()
            eventos_por_cargo_filtrado = []
            
            for cargo in cargos_unicos_filtrados[:10]:  # Limitar a 10 cargos principais
                cargo_data = cargos_orgao_externo_filtrado[cargos_orgao_externo_filtrado['cargo'] == cargo]
                total_inscritos = cargo_data['total_inscritos'].sum()
                
                # Criar 3 eventos simulados para cada cargo
                for j, tipo in enumerate(['Masterclass', 'Workshop', 'Curso de IA']):
                    eventos_por_cargo_filtrado.append({
                        'evento': f'{cargo} - {tipo} {j+1}',
                        'Tipo': tipo,
                        cargo: int(total_inscritos * [0.3, 0.4, 0.3][j])  # Distribuir proporcionalmente
                    })
            
            if eventos_por_cargo_filtrado:
                df_cargos_ev_temp = pd.DataFrame(eventos_por_cargo_filtrado)
                # Aplicar filtro de tipo se necessário
                if tipo_selecionado != "Todos":
                    df_cargos_ev_filtrado = df_cargos_ev_temp[df_cargos_ev_temp["Tipo"] == tipo_selecionado].copy()
                else:
                    df_cargos_ev_filtrado = df_cargos_ev_temp.copy()
            else:
                # Se não há cargos para a classificação selecionada, criar DataFrame vazio com estrutura mínima
                df_cargos_ev_filtrado = pd.DataFrame(columns=['evento', 'Tipo'])

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
# Recriar df_cargos_rank baseado nos dados filtrados para que o gráfico "Desempenho por Cargo (Inscritos)" seja afetado pelos filtros
if 'cargo' in df_cargos_raw.columns:
    # Usar df_dados_filtrado para recalcular cargos
    if len(df_dados_filtrado) > 0:
        # Agrupar por cargo usando os dados filtrados
        df_cargos_filtrado = df_cargos_raw[df_cargos_raw['orgao'].isin(df_dados_filtrado['orgao'].unique())].copy()
        
        # Se há filtro de tipo de curso, aplicar também aos cargos
        if tipo_selecionado != "Todos":
            # Mapear tipos de evento para filtrar cargos correspondentes
            evento_mapping = {
                "Masterclass": ["Masterclass"],
                "Workshop": ["Workshop"], 
                "Curso": ["Curso"]
            }
            if tipo_selecionado in evento_mapping:
                # Filtrar cargos baseado no tipo selecionado (simulação)
                # Como não temos ligação direta entre df_dados e df_cargos por tipo,
                # vamos manter todos os cargos dos órgãos filtrados
                pass
        
        if len(df_cargos_filtrado) > 0:
            df_cargos_rank = df_cargos_filtrado.groupby('cargo')['total_inscritos'].sum().sort_values(ascending=False)
            df_cargos_rank = pd.DataFrame({"Cargo": df_cargos_rank.index, "Inscritos": df_cargos_rank.values}).set_index("Cargo")
        else:
            # Se não há dados filtrados, criar DataFrame vazio
            df_cargos_rank = pd.DataFrame(columns=["Inscritos"]).set_index(pd.Index([], name="Cargo"))
    else:
        # Se não há dados filtrados, criar DataFrame vazio
        df_cargos_rank = pd.DataFrame(columns=["Inscritos"]).set_index(pd.Index([], name="Cargo"))
else:
    # Para formato Excel, recalcular baseado em df_cargos_ev_filtrado
    if len(df_cargos_ev_filtrado) > 0:
        totais_por_cargo = df_cargos_ev_filtrado[cargo_cols].sum().sort_values(ascending=False)
        df_cargos_rank = (
            pd.DataFrame({"Cargo": totais_por_cargo.index, "Inscritos": totais_por_cargo.values})
            .sort_values("Inscritos", ascending=False).set_index("Cargo")
        )
    else:
        # Se não há dados filtrados, criar DataFrame vazio
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

def nz(df: pd.DataFrame, required_cols):
    """Remove linhas com NaN/±inf nas colunas exigidas."""
    clean = df.replace([np.inf, -np.inf], pd.NA)
    return clean.dropna(subset=required_cols)

# Definir variável global para identificar formato dos dados
is_parquet = 'cargo' in df_cargos_raw.columns

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Visão Geral", "👥 Cargos", "🏢 Secretarias", "📚 Eventos", "👨‍🏫 Professores"])

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
        
        # Definir coluna de evento baseado no formato
        if 'cargo' in df_cargos_raw.columns:
            # Formato Parquet - usar dados simulados
            evento_col = "evento" if "evento" in df_ev_view.columns else df_ev_view.columns[0]
        else:
            # Formato Excel
            evento_col = df_cargos_raw.columns[0]  # EVENTO_COL equivalente
        
        # Evitar duplicação de colunas no rename
        rename_dict = {cargo_escolhido: "Inscritos"}
        if evento_col != "Evento":
            rename_dict[evento_col] = "Evento"
        
        serie = df_ev_view[[evento_col, "Tipo", cargo_escolhido]].rename(columns=rename_dict)
        serie = nz(serie, ["Inscritos"])
        if serie.empty:
            st.info("Sem dados para a série.")
        else:
            fig_series = px.bar(serie, x="Evento", y="Inscritos", color="Tipo", barmode="group", title=None)
            fig_series.update_layout(bargap=0.02, bargroupgap=0.02)
            fig_series.update_traces(marker_line_width=0)
            fig_series.update_xaxes(tickangle=-35)
            st.plotly_chart(style_fig(fig_series, height=520), use_container_width=True, key=f"t2_cargos_series_{cargo_escolhido}")
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

        def evento_curto(evento: str, tipo: str) -> str:
            s = str(evento)
            m = re.search(r"(\d+)\s*[ºª]?\s*(?=Masterclass|Workshop|Curso)", s, flags=re.I)
            num = m.group(1) if m else None
            base = "Curso" if "Curso" in tipo else ("Masterclass" if "Masterclass" in tipo else ("Workshop" if "Workshop" in tipo else tipo))
            return f"{num}° {base}" if num else base

        ev["EVENTO_CURTO"] = ev.apply(lambda r: evento_curto(r[evento_col_ev], r["Tipo"]), axis=1)

        show_ev_table = st.toggle("Mostrar tabela de eventos", value=False,
                                  help="Ative para visualizar a planilha; por padrão fica oculta.")
        if show_ev_table:
            cols_evento = [c for c in ["Nº",evento_col_ev,"Tipo",inscritos_col_ev,certificados_col_ev,"Evasão (Nº)","Taxa de Certificação (%)"] if c in ev.columns]
            df_panel(ev[cols_evento].reset_index(drop=True), "Eventos (filtrados)", key=f"tbl_evt_{len(ev)}")

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

# =================================================
# 🔒 NOVA ABA 5: Professores (Área Restrita)
# =================================================
with tab5:
    st.markdown('<div class="panel"><h3>Área Restrita — Professores</h3>', unsafe_allow_html=True)

    senha = st.text_input("Digite a senha para acessar os dados:", type="password")

    if senha != "admin123":  
        st.warning("🔒 Área restrita. Informe a senha correta para visualizar os dados.")
    else:
        st.success("✅ Acesso liberado!")

        # -------------------------
        # Função para processar CAPACITIA
        # -------------------------
        def process_capacitia(df, sheet_name):
            dias_semana = ["Segunda-Feira", "Terça-Feira", "Quarta-Feira", "Quinta-Feira", "Sexta-Feira"]
            df = df[dias_semana].copy()

            registros = []
            for dia in dias_semana:
                col = df[dia].dropna().reset_index(drop=True)
                # pares: data, professor
                for i in range(0, len(col)-1, 2):
                    try:
                        data = pd.to_datetime(col[i], errors="coerce", dayfirst=True)
                        prof = str(col[i+1]).strip()
                        if pd.notna(data) and prof not in ["nan", "None", ""]:
                            registros.append({
                                "Professor": prof,
                                "Data": data,
                                "DiaSemana": dia,
                                "Carga Horária": 4,  # cada aula = 4h
                                "Ano": str(data.year),
                                "Origem": sheet_name
                            })
                    except Exception:
                        continue

            return pd.DataFrame(registros)

        # -------------------------
        # Carregar Excel
        # -------------------------
        try:
            excel_path = Path(".data/processed") / "Relatorio_Atualizado_Capacitia.xlsx"
            all_sheets = pd.read_excel(excel_path, sheet_name=None)

            df_list = []
            for sheet, df in all_sheets.items():
                if sheet in ["CAPACITIA ORGAOS REGULARES", "CAPACITIA EXTERNO"]:
                    df_list.append(process_capacitia(df, sheet))
                else:
                    df = df.rename(columns={
                        "Ministrantes": "Professor",
                        "Professores": "Professor"
                    })

                    if "Professor" not in df.columns:
                        continue

                    turma_cols = [c for c in df.columns if str(c).lower().startswith("turma")]
                    if turma_cols:
                        df["Carga Horária"] = df[turma_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

                    if "Carga Horária" not in df.columns:
                        continue

                    df["Ano"] = "2024" if "2024" in sheet else ("2025" if "2025" in sheet else "Outro")
                    df["Origem"] = sheet

                    df_list.append(df[["Professor", "Carga Horária", "Ano"] + [c for c in df.columns if c in ["Data","Secretaria/Órgão"]]])

            if df_list:
                df_profs = pd.concat(df_list, ignore_index=True)
            else:
                df_profs = pd.DataFrame(columns=["Professor","Carga Horária","Ano","Data","DiaSemana","Origem"])

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            df_profs = pd.DataFrame(columns=["Professor","Carga Horária","Ano","Data","DiaSemana","Origem"])

        # ========================
        # GRÁFICOS
        # ========================
        if not df_profs.empty:

            # -------------------------
            # Filtro de Ano (para os 2 primeiros gráficos + Treemap)
            # -------------------------
            anos = df_profs["Ano"].dropna().unique().tolist()
            ano_sel = st.selectbox("📅 Selecione o Ano:", anos)

            df_filtro = df_profs[df_profs["Ano"] == ano_sel]

            colA, colB = st.columns(2)

            # 1. Barras — Carga Horária
            with colA:
                st.subheader(f"📊 Carga Horária Total por Professor — {ano_sel}")
                carga = df_filtro.groupby("Professor")["Carga Horária"].sum().reset_index()
                carga = carga.sort_values("Carga Horária", ascending=True)
                fig_carga = px.bar(carga, x="Carga Horária", y="Professor", orientation="h")
                fig_carga.update_traces(
                    text=carga["Carga Horária"],
                    texttemplate="%{x}",
                    textposition="outside"
                )
                st.plotly_chart(style_fig(fig_carga, height=500), use_container_width=True)

            # 2. Barras — Nº de Aulas
            with colB:
                st.subheader(f"📘 Número de Aulas por Professor — {ano_sel}")
                aulas = df_filtro.copy()
                aulas["Qtd Aulas"] = (aulas["Carga Horária"] / 4).round().astype(int)
                aulas = aulas.groupby("Professor")["Qtd Aulas"].sum().reset_index()
                aulas = aulas.sort_values("Qtd Aulas", ascending=True)
                fig_aulas = px.bar(aulas, x="Qtd Aulas", y="Professor", orientation="h")
                fig_aulas.update_traces(
                    text=aulas["Qtd Aulas"],
                    texttemplate="%{x}",
                    textposition="outside"
                )
                st.plotly_chart(style_fig(fig_aulas, height=500), use_container_width=True)

           # 3. Treemap
            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader(f"🌳 Distribuição da Carga Horária (Treemap) — {ano_sel}")

            carga_tot = df_filtro.groupby("Professor")["Carga Horária"].sum().reset_index()

            fig_tree = px.treemap(
                carga_tot,
                path=["Professor"],
                values="Carga Horária",
                color="Carga Horária",  # cores baseadas na carga
                color_continuous_scale="Viridis"
            )

            fig_tree.update_traces(
                textinfo="label+percent entry+value",
                textfont_size=16
            )

            fig_tree.update_layout(
                margin=dict(t=20, l=10, r=10, b=10),
                coloraxis_colorbar=dict(
                    title=dict(
                        text="Carga Horária",
                        font=dict(size=14)
                    ),
                    tickfont=dict(size=12)
                )
            )

            st.plotly_chart(style_fig(fig_tree, height=500), use_container_width=True)

            # 4. Distribuição por Dia da Semana
            if "DiaSemana" in df_profs.columns:
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("📅 Distribuição da Carga Horária por Dia da Semana")

                # Filtro de professores
                profs = df_profs["Professor"].dropna().unique().tolist()
                profs_sel = st.multiselect("👩‍🏫 Selecione os Professores:", profs, default=profs)

                df_semana = df_profs[df_profs["Professor"].isin(profs_sel)]

                # Agrupa por dia da semana e professor
                dist = df_semana.groupby(["DiaSemana", "Professor"])["Carga Horária"].sum().reset_index()

                # Ordena os dias
                ordem_dias = ["Segunda-Feira","Terça-Feira","Quarta-Feira","Quinta-Feira","Sexta-Feira"]
                dist["DiaSemana"] = pd.Categorical(dist["DiaSemana"], categories=ordem_dias, ordered=True)
                dist = dist.sort_values(["DiaSemana","Professor"])

                # Gráfico
                fig_dias = px.bar(
                    dist,
                    x="DiaSemana",
                    y="Carga Horária",
                    color="Professor",
                    barmode="group",
                    text="Carga Horária"
                )

                fig_dias.update_traces(
                    texttemplate="%{y}",
                    textposition="outside",
                    textfont_size=18  # 🔥 valores bem maiores
                )

                st.plotly_chart(style_fig(fig_dias, height=500), use_container_width=True)

            # -------------------------
            # 📋 Tabela Detalhada com Expander
            # -------------------------
            with st.expander("📋 Mostrar/Ocultar Dados completos"):
                st.dataframe(df_filtro, use_container_width=True)


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
