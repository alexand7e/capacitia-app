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
st.markdown("""
<style>
:root{ --bg:#0f1220; --panel:#11142a; --muted:#7780a1; --text:#e6e7ee; --accent:#7DD3FC; --accent2:#34D399; }
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text) !important; }
/* esconder sidebar */
[data-testid="stSidebar"], [data-testid="stSidebarNav"], section[data-testid="stSidebar"]{ display:none !important; }
header [data-testid="stToolbar"]{ visibility:hidden; }
[data-testid="stAppViewContainer"] .main .block-container{ padding-top: 72px !important; }
.hero { margin-top: 8px; }
.sep{ border-top:1px solid #1e2443; margin:16px 0 12px 0; }
.hero {
  background: radial-gradient(1200px 400px at 10% -20%, rgba(125,211,252,.15), transparent),
              radial-gradient(1000px 400px at 90% -30%, rgba(52,211,153,.12), transparent),
              linear-gradient(180deg, #0f1220 0%, #0f1220 100%);
  border:1px solid #1e2443; border-radius:18px; padding:20px; margin-bottom:12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.25);
}
.kpi{ background: var(--panel); border:1px solid #1e2443; border-radius:16px; padding:16px; }
.kpi h4{ font-size:.85rem; font-weight:600; color:var(--muted); margin:0 0 6px 0; }
.kpi .val{ font-size:1.6rem; font-weight:800; letter-spacing:.2px; }
.panel{ background: var(--panel); border:1px solid #1e2443; border-radius:18px; padding:14px; }
.panel h3{ margin:0 0 6px 0; font-size:1.0rem; }
.js-plotly-plot, .plot-container{ border-radius:12px; }
@media (max-width: 1200px){ [data-testid="stAppViewContainer"] .main .block-container{ padding-top: 84px !important; } }
</style>
""", unsafe_allow_html=True)

# =========================
# DATA LOAD
# =========================
# tenta achar automaticamente o arquivo (novo ou antigo)
_CANDIDATES = [
    Path("dados") / "RelatorioCapacitia_AtualizadoAgosto.xlsx",
    Path("dados") / "relatorio_capacitia.xlsx",
    Path("RelatorioCapacitia_AtualizadoAgosto.xlsx"),
    Path("relatorio_capacitia.xlsx"),
]
DEFAULT_XLSX = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])

@st.cache_data(show_spinner=False)
def load_sheets(path: Path):
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

if not DEFAULT_XLSX.exists():
    st.error(f"Arquivo Excel não encontrado. Verifique estes caminhos:\n{[str(p) for p in _CANDIDATES]}")
    st.stop()

df_dados, df_visao, df_secretarias_raw, df_cargos_raw, df_min = load_sheets(DEFAULT_XLSX)

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
    if only_with_inscritos and "Nº INSCRITOS" in df.columns:
        insc = pd.to_numeric(df["Nº INSCRITOS"], errors="coerce").fillna(0)
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
    nome_org_col = [c for c in df.columns if "SECRETARIA" in str(c).upper() or "ÓRGÃO" in str(c).upper()][0]
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
    num_insc = pd.to_numeric(df_f["Nº INSCRITOS"], errors="coerce")
    num_evas = pd.to_numeric(df_f["Nº EVASÃO"], errors="coerce")
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
    vals = pd.to_numeric(df_sec_view["Nº INSCRITOS"], errors="coerce").fillna(0)
    return int((vals > 0).sum())

tot_insc, tot_cert = get_totais_visao(df_visao)
taxa_cert = (tot_cert / tot_insc * 100) if tot_insc else 0.0
sec_atendidas = count_secretarias_unicas(df_secretarias)


# =========================
# PREP CARGOS
# =========================
EVENTO_COL = df_cargos_raw.columns[0]  # geralmente "Unnamed: 0"
mask_evento = df_cargos_raw[EVENTO_COL].astype(str).str.contains(r"Masterclass|Workshop|Curso", case=False, na=False)
df_cargos_ev = df_cargos_raw.loc[mask_evento].copy()
df_cargos_ev["Tipo"] = (
    df_cargos_ev[EVENTO_COL]
    .str.extract(r"(Masterclass|Workshop|Curso)", expand=False)
    .str.title()
    .replace({"Curso": "Curso de IA"})
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

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi"><h4>Total de Inscritos</h4><div class="val">{fmt_int_br(tot_insc)}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi"><h4>Total de Certificados</h4><div class="val">{fmt_int_br(tot_cert)}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi"><h4>Taxa de Certificação</h4><div class="val">{taxa_cert:.2f}%</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi"><h4>Secretarias atendidas</h4><div class="val">{sec_atendidas}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# TABS (com remoção de NaN/±inf nos plots)
# =========================

def nz(df: pd.DataFrame, required_cols):
    """Remove linhas com NaN/±inf nas colunas exigidas."""
    clean = df.replace([np.inf, -np.inf], pd.NA)
    return clean.dropna(subset=required_cols)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "👥 Cargos", "🏢 Secretarias", "📚 Eventos"])

# --------- Visão Geral
with tab1:
    colA, colB = st.columns(2)

    with colA:
        st.markdown('<div class="panel"><h3>Desempenho por Secretaria</h3>', unsafe_allow_html=True)

# 🔧 remove linhas com SECRETARIA/ÓRGÃO vazio/NaN
        base = drop_empty_labels(df_f, "SECRETARIA/ÓRGÃO")

        grp_sec = (
            base.groupby("SECRETARIA/ÓRGÃO")[["Nº INSCRITOS", "Nº CERTIFICADOS"]]
                .sum()
                .sort_values("Nº INSCRITOS", ascending=False)
        )
        grp_sec["Taxa de Permanência (%)"] = (
            grp_sec["Nº CERTIFICADOS"] / grp_sec["Nº INSCRITOS"]
        ).replace([pd.NA, float("inf")], 0).fillna(0) * 100


        modo = st.radio(
            "Visualizar",
            ["Inscritos", "Certificados", "Taxa de Permanência", "Comparativo"],
            horizontal=True, key="rg_sec",
        )

        if modo == "Inscritos":
            d = nz(grp_sec, ["Nº INSCRITOS"]).head(topn).sort_values("Nº INSCRITOS")
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame({"Nº INSCRITOS": []}), x="Nº INSCRITOS", y=[])
            else:
                fig = px.bar(d, x="Nº INSCRITOS", y=d.index, orientation="h", title="Top por Inscritos")
                x_max = max(1, d["Nº INSCRITOS"].max())
                fig.update_traces(text=d["Nº INSCRITOS"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Certificados":
            d = nz(grp_sec, ["Nº CERTIFICADOS"]).sort_values("Nº CERTIFICADOS", ascending=False) \
                                               .head(topn).sort_values("Nº CERTIFICADOS")
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame({"Nº CERTIFICADOS": []}), x="Nº CERTIFICADOS", y=[])
            else:
                fig = px.bar(d, x="Nº CERTIFICADOS", y=d.index, orientation="h", title="Top por Certificados")
                x_max = max(1, d["Nº CERTIFICADOS"].max())
                fig.update_traces(text=d["Nº CERTIFICADOS"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
                fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Taxa de Permanência":
            base = grp_sec[grp_sec["Nº INSCRITOS"] > 0]
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
            d = nz(grp_sec, ["Nº INSCRITOS", "Nº CERTIFICADOS"]).head(topn)
            if d.empty:
                st.info("Sem dados para plotar.")
                fig = px.bar(pd.DataFrame(columns=["Nº INSCRITOS","Nº CERTIFICADOS"]), x=["Nº INSCRITOS","Nº CERTIFICADOS"], y=[])
            else:
                fig = px.bar(d, x=["Nº INSCRITOS", "Nº CERTIFICADOS"], y=d.index, orientation="h", barmode="group")
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

    tipos_sel = sorted(df_cargos_ev["Tipo"].dropna().unique().tolist()) or ["Masterclass","Workshop","Curso de IA"]
    df_ev_view = df_cargos_ev[df_cargos_ev["Tipo"].isin(tipos_sel)].copy()

    tot_view = (df_ev_view[cargo_cols].sum().sort_values(ascending=False) if not df_ev_view.empty else pd.Series(dtype=float))
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
    if not df_ev_view.empty:
        df_tipo_view = df_ev_view.groupby("Tipo")[cargo_cols].sum().T.replace([np.inf, -np.inf], 0).fillna(0)
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
    if cargo_cols and not df_ev_view.empty:
        cargo_escolhido = st.selectbox("Escolha um cargo", cargo_cols, index=0, key="t2_cargo_series")
        serie = (df_ev_view[[EVENTO_COL, "Tipo", cargo_escolhido]]
                 .rename(columns={EVENTO_COL: "Evento", cargo_escolhido: "Inscritos"}))
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
    df_f_clean = drop_empty_labels(df_f, "SECRETARIA/ÓRGÃO")

    grp = (
        df_f_clean.groupby('SECRETARIA/ÓRGÃO')[['Nº INSCRITOS','Nº CERTIFICADOS']]
                .sum()
                .reset_index()
    )
    grp = grp.replace([np.inf, -np.inf], pd.NA)
    grp = nz(grp, ['Nº INSCRITOS','Nº CERTIFICADOS'])
    grp['Taxa de Certificação (%)'] = (
        grp['Nº CERTIFICADOS'] / grp['Nº INSCRITOS']
    ).replace([pd.NA, float('inf')], 0).fillna(0) * 100


    show_sec_table = st.toggle("Mostrar tabela de secretarias", value=False,
                               help="Ative para visualizar o consolidado; por padrão fica oculto.")
    if show_sec_table:
        df_panel(grp.round(2), "Consolidado por Secretaria/Órgão", key=f"tbl_sec_{len(grp)}")

    st.markdown('<div class="panel"><h3>Inscritos X Certificados</h3>', unsafe_allow_html=True)
    cA, cB = st.columns(2)

    with cA:
        top_comp = grp.sort_values('Nº INSCRITOS', ascending=False).head(topn)
        if top_comp.empty:
            st.info("Sem dados para o comparativo.")
        else:
            fig_comp = px.bar(top_comp, x=['Nº INSCRITOS','Nº CERTIFICADOS'], y='SECRETARIA/ÓRGÃO',
                              orientation='h', barmode='group', text_auto=True, title=None)
            fig_comp.update_traces(textposition="outside", cliponaxis=False, textfont_size=12)
            st.plotly_chart(style_fig(fig_comp), use_container_width=True, key=f"sec_comp_{topn}")

    with cB:
        top_taxa = grp[grp['Nº INSCRITOS'] > 0].sort_values('Taxa de Certificação (%)', ascending=False).head(topn)
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
    grp_tree = grp.sort_values('Nº INSCRITOS', ascending=False).head(max(topn*2, 20))
    grp_tree = nz(grp_tree, ['Nº INSCRITOS'])
    if grp_tree.empty:
        st.info("Sem dados para o treemap.")
    else:
        treemap = px.treemap(grp_tree, path=['SECRETARIA/ÓRGÃO'], values='Nº INSCRITOS',
                             color='Taxa de Certificação (%)', custom_data=['Taxa de Certificação (%)'],
                             title='Treemap — maiores contribuições')
        treemap.update_traces(texttemplate="<b>%{label}</b><br>%{customdata[0]:.0f}%", textposition="middle center")
        treemap.update_layout(uniformtext_minsize=12, uniformtext_mode='show')
        st.plotly_chart(style_fig(treemap, height=520), use_container_width=True, key="sec_tree")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Eventos
with tab4:
    if df_visao.empty:
        st.info("Aba 'VISÃO ABERTA' vazia ou inválida.")
    else:
        ev = df_visao.copy()
        # garantir numéricos e filtrar NaN/±inf
        ev["Nº INSCRITOS"] = pd.to_numeric(ev["Nº INSCRITOS"], errors="coerce")
        ev["Nº CERTIFICADOS"] = pd.to_numeric(ev["Nº CERTIFICADOS"], errors="coerce")
        ev = nz(ev, ["Nº INSCRITOS", "Nº CERTIFICADOS"])

        ev["Tipo"] = (
            ev["EVENTO"].astype(str)
            .str.extract(r"(Masterclass|Workshop|Curso)", expand=False)
            .str.title().replace({"Curso": "Curso de IA"})
        ).fillna("Outro")
        ev["Taxa de Certificação (%)"] = (
            ev["Nº CERTIFICADOS"] / ev["Nº INSCRITOS"]
        ).replace([pd.NA, float("inf")], 0).fillna(0) * 100
        ev["Evasão (Nº)"] = (ev["Nº INSCRITOS"] - ev["Nº CERTIFICADOS"]).clip(lower=0)

        def evento_curto(evento: str, tipo: str) -> str:
            s = str(evento)
            m = re.search(r"(\d+)\s*[ºª]?\s*(?=Masterclass|Workshop|Curso)", s, flags=re.I)
            num = m.group(1) if m else None
            base = "Curso" if "Curso" in tipo else ("Masterclass" if "Masterclass" in tipo else ("Workshop" if "Workshop" in tipo else tipo))
            return f"{num}° {base}" if num else base

        ev["EVENTO_CURTO"] = ev.apply(lambda r: evento_curto(r["EVENTO"], r["Tipo"]), axis=1)

        show_ev_table = st.toggle("Mostrar tabela de eventos", value=False,
                                  help="Ative para visualizar a planilha; por padrão fica oculta.")
        if show_ev_table:
            cols_evento = [c for c in ["Nº","EVENTO","Tipo","Nº INSCRITOS","Nº CERTIFICADOS","Evasão (Nº)","Taxa de Certificação (%)"] if c in ev.columns]
            df_panel(ev[cols_evento].reset_index(drop=True), "Eventos (filtrados)", key=f"tbl_evt_{len(ev)}")

        by_tipo = ev.groupby("Tipo")[["Nº INSCRITOS","Nº CERTIFICADOS"]].sum().replace([np.inf, -np.inf], 0).fillna(0)
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            if not by_tipo.empty:
                pie = px.pie(by_tipo.reset_index(), values="Nº INSCRITOS", names="Tipo", hole=0.55)
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
                                                  value_vars=["Nº INSCRITOS","Nº CERTIFICADOS"],
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
            ev_tmp = nz(ev_tmp, ["Nº INSCRITOS"])
            if ev_tmp.empty:
                st.info("Sem dados para o treemap.")
            else:
                ev_tmp["EVENTO_LABEL"] = ev_tmp.apply(lambda r: rotulo_curto(r["EVENTO"], r["Tipo"]), axis=1)
                col_tm, col_desc = st.columns([4, 1.7], gap="large")
                with col_tm:
                    tmap = px.treemap(
                        ev_tmp.sort_values("Nº INSCRITOS", ascending=False).head(max(topn*2, 20)),
                        path=["Tipo", "EVENTO_LABEL"], values="Nº INSCRITOS", title=None
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
                        <li><b>Tipo</b> (Curso de IA, Masterclass, Workshop): % do total para cada tipo.</li>
                        <li><b>Evento</b> (ex.: <i>11° Curso</i>): % daquele evento no total.</li>
                    </ul>
                    <p>Passe o mouse para ver <b>inscritos absolutos</b> e a mesma participação (%).</p>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
