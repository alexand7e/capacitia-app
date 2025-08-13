import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(page_title="Dashboard CapacitIA", page_icon="🚀", layout="wide")

# Plotly theme
pio.templates["capacit_dark"] = pio.templates["plotly_dark"]
pio.templates["capacit_dark"].layout.font.family = "Inter, Segoe UI, Roboto, Arial"
pio.templates["capacit_dark"].layout.colorway = ["#7DD3FC","#34D399","#FBBF24","#F472B6","#60A5FA","#A78BFA","#F87171"]
pio.templates["capacit_dark"].layout.paper_bgcolor = "#0f1220"
pio.templates["capacit_dark"].layout.plot_bgcolor = "#11142a"
pio.templates["capacit_dark"].layout.hoverlabel = dict(bgcolor="#0f1220", font_size=12, font_family="Inter, Segoe UI, Roboto, Arial")
pio.templates.default = "capacit_dark"

# Global CSS (AJUSTE DO CABEÇALHO E TÍTULO)
st.markdown("""
<style>
:root{
  --bg:#0f1220; --panel:#11142a; --muted:#7780a1; --text:#e6e7ee; --accent:#7DD3FC; --accent2:#34D399;
  --safe-top: 18px;            /* espaço de segurança no topo */
}

/* Fundo e sidebar */
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text) !important; }
[data-testid="stSidebar"] { background: #0d1020; border-right:1px solid #1e2443; }

/* AUMENTA o padding superior do conteúdo (evita cortar o herói) */
[data-testid="stAppViewContainer"] .main .block-container { padding-top: var(--safe-top) !important; }

/* Header nativo transparente (sem sobrepor o conteúdo) */
header[data-testid="stHeader"] { background: transparent; }

/* Separador */
.sep { border-top:1px solid #1e2443; margin:16px 0 12px 0; }

/* Card do título (hero) */
.hero {
  background:
    radial-gradient(1200px 400px at 10% -20%, rgba(125,211,252,.15), transparent),
    radial-gradient(1000px 400px at 90% -30%, rgba(52,211,153,.12), transparent),
    linear-gradient(180deg, #0f1220 0%, #0f1220 100%);
  border:1px solid #1e2443;
  border-radius:18px;
  padding:22px 22px;           /* + padding = mais “respiro” pro título */
  margin:6px 0 12px 0;         /* pequeno afastamento do topo */
  box-shadow: 0 4px 24px rgba(0,0,0,.25);
  overflow: visible;           /* garante que nada seja “cortado” */
}

/* Estilo do título principal dentro do hero */
.hero .title {
  font-weight: 800;
  letter-spacing:.2px;
  margin: 0;
  line-height: 1.25;           /* evita corte */
  font-size: clamp(1.6rem, 1.1rem + 1.2vw, 2.2rem);  /* tamanho fluido */
  white-space: normal;         /* permite quebra */
  word-break: break-word;      /* segurança pra telas estreitas */
}

/* KPIs e painéis */
.kpi { background: var(--panel); border:1px solid #1e2443; border-radius:16px; padding:16px; }
.kpi h4 { font-size: .85rem; font-weight: 600; color: var(--muted); margin: 0 0 6px 0; }
.kpi .val { font-size: 1.6rem; font-weight: 800; letter-spacing:.2px; }

.panel { background: var(--panel); border:1px solid #1e2443; border-radius:18px; padding:14px; }
.panel h3 { margin: 0 0 6px 0; font-size:1.0rem; }

.js-plotly-plot, .plot-container { border-radius:12px; }

/* Ajustes responsivos */
@media (max-width: 900px){
  :root{ --safe-top: 22px; }   /* um pouco mais de espaço no topo no mobile */
  .kpi .val{ font-size: 1.4rem; }
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA LOAD
# =========================
DEFAULT_XLSX = Path("dados") / "relatorio_capacitia.xlsx"

@st.cache_data(show_spinner=False)
def load_sheets(path: Path):
    xls = pd.ExcelFile(path)
    df_dados        = pd.read_excel(xls, "DADOS", header=6)
    df_visao        = pd.read_excel(xls, "VISÃO ABERTA", header=6)  # Nº, EVENTO, Nº INSCRITOS, Nº CERTIFICADOS
    df_secretarias  = pd.read_excel(xls, "SECRETARIA-ÓRGÃO", header=2)  # SECRETARIA/ÓRGÃO, Nº INSCRITOS, Nº CERTIFICADOS, Nº EVASÃO
    df_cargos_raw   = pd.read_excel(xls, "CARGOS", header=2)  # eventos nas linhas; cargos nas colunas
    try:
        df_min      = pd.read_excel(xls, "MINISTRANTECARGA HORÁRIA", header=1)
    except Exception:
        df_min      = None

    # saneamento numérico nas planilhas que têm "Nº ... "
    for df in (df_visao, df_secretarias):
        for c in [c for c in df.columns if "Nº" in str(c)]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df_dados, df_visao, df_secretarias, df_cargos_raw, df_min

if not DEFAULT_XLSX.exists():
    st.error(f"Arquivo Excel não encontrado em: {DEFAULT_XLSX}")
    st.stop()

df_dados, df_visao, df_secretarias, df_cargos_raw, df_min = load_sheets(DEFAULT_XLSX)

# =========================
# HELPERS
# =========================
def style_fig(fig, height=420):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title=None, yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig

def df_panel(df: pd.DataFrame, title: str, key: str, max_rows: int = 22, min_h: int = 260, max_h: int = 640):
    """Renderiza um dataframe com altura proporcional ao número de linhas."""
    st.markdown(f'<div class="panel"><h3>{title}</h3>', unsafe_allow_html=True)
    h = min(max(min_h, 60 + 28 * min(len(df), max_rows)), max_h)  # ~28px por linha
    st.dataframe(df, use_container_width=True, height=h)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# SIDEBAR & KPIs
# =========================
with st.sidebar:
    st.header("⚙️ Filtros")
    secre_opts = sorted(df_secretarias["SECRETARIA/ÓRGÃO"].astype(str).dropna().unique().tolist())
    secre_sel = st.multiselect("Secretarias/Órgãos", options=secre_opts, default=secre_opts)
    topn = st.slider("Top N (gráficos)", 5, 30, 10, 1)
    if st.button("🔁 Resetar filtros"):
        st.experimental_rerun()

# filtro secretarias
df_f = df_secretarias[df_secretarias["SECRETARIA/ÓRGÃO"].astype(str).isin(secre_sel)].copy()
if "Nº EVASÃO" in df_f.columns:
    num_insc = pd.to_numeric(df_f["Nº INSCRITOS"], errors="coerce")
    num_evas = pd.to_numeric(df_f["Nº EVASÃO"], errors="coerce")
    df_f["Evasão (%)"] = (num_evas / num_insc.replace(0, pd.NA)) * 100

# KPIs
tot_insc = int(df_f["Nº INSCRITOS"].sum()) if "Nº INSCRITOS" in df_f else 0
tot_cert = int(df_f["Nº CERTIFICADOS"].sum()) if "Nº CERTIFICADOS" in df_f else 0
taxa_cert = (tot_cert / tot_insc * 100) if tot_insc else 0.0
sec_atendidas = df_f["SECRETARIA/ÓRGÃO"].nunique()

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
st.markdown(f"""
<div class="hero">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
    <div>
      <div class="title">🚀 Dashboard CapacitIA</div>
      <div style="color:#a6accd;">Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi"><h4>Total de Inscritos</h4><div class="val">{str(f"{tot_insc:,}").replace(",", ".")}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi"><h4>Total de Certificados</h4><div class="val">{str(f"{tot_cert:,}").replace(",", ".")}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi"><h4>Taxa de Certificação</h4><div class="val">{taxa_cert:.1f}%</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi"><h4>Secretarias atendidas</h4><div class="val">{sec_atendidas}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "👥 Cargos", "🏢 Secretarias", "📚 Eventos"])

# --------- Visão Geral
with tab1:
    colA, colB = st.columns(2)

    with colA:
        st.markdown('<div class="panel"><h3>Desempenho por Secretaria</h3>', unsafe_allow_html=True)
        grp_sec = df_f.groupby("SECRETARIA/ÓRGÃO")[["Nº INSCRITOS", "Nº CERTIFICADOS"]].sum().sort_values("Nº INSCRITOS", ascending=False)
        grp_sec["Taxa de Permanência (%)"] = (
            grp_sec["Nº CERTIFICADOS"] / grp_sec["Nº INSCRITOS"]
        ).replace([pd.NA, float("inf")], 0).fillna(0) * 100

        modo = st.radio(
            "Visualizar",
            ["Inscritos", "Certificados", "Taxa de Permanência", "Comparativo"],
            horizontal=True, key="rg_sec",
        )

        if modo == "Inscritos":
            d = grp_sec.head(topn).sort_values("Nº INSCRITOS")
            fig = px.bar(d, x="Nº INSCRITOS", y=d.index, orientation="h", title="Top por Inscritos")
            x_max = max(1, d["Nº INSCRITOS"].max())
            fig.update_traces(text=d["Nº INSCRITOS"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
            fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Certificados":
            d = grp_sec.sort_values("Nº CERTIFICADOS", ascending=False).head(topn).sort_values("Nº CERTIFICADOS")
            fig = px.bar(d, x="Nº CERTIFICADOS", y=d.index, orientation="h", title="Top por Certificados")
            x_max = max(1, d["Nº CERTIFICADOS"].max())
            fig.update_traces(text=d["Nº CERTIFICADOS"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
            fig.update_xaxes(range=[0, x_max * 1.15])

        elif modo == "Taxa de Permanência":
            d = grp_sec[grp_sec["Nº INSCRITOS"] > 0].sort_values("Taxa de Permanência (%)", ascending=False).head(topn).sort_values("Taxa de Permanência (%)")
            fig = px.bar(d, x="Taxa de Permanência (%)", y=d.index, orientation="h", title="Top por Permanência")
            vals = d["Taxa de Permanência (%)"]
            x_max = max(1, vals.max())
            fig.update_traces(text=vals, texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False)
            fig.update_xaxes(ticksuffix="%", range=[0, max(100, x_max) * 1.12])

        else:  # Comparativo
            d = grp_sec.head(topn)
            fig = px.bar(d, x=["Nº INSCRITOS", "Nº CERTIFICADOS"], y=d.index, orientation="h", barmode="group")
            fig.update_traces(texttemplate="%{x}", textposition="outside", cliponaxis=False)

        st.plotly_chart(style_fig(fig), use_container_width=True, key=f"vg_sec_lbl_{modo}_{topn}")
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="panel"><h3>Desempenho por Cargo (Inscritos)</h3>', unsafe_allow_html=True)
        if not df_cargos_rank.empty:
            d = df_cargos_rank.head(topn).sort_values("Inscritos")
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
        fig_funil = px.funnel(funil_df, x="Total", y="Etapa", title=None)
        st.plotly_chart(style_fig(fig_funil, height=360), use_container_width=True, key="vg_funnel")
    else:
        st.info("Sem dados para montar o funil.")
    st.markdown('</div>', unsafe_allow_html=True)


# --------- Cargos
with tab2:
    st.markdown('<div class="panel"><h4>Visão de Cargos</h4>', unsafe_allow_html=True)

    # ✅ Sem filtro visível: usa todos os tipos existentes no arquivo
    tipos_sel = sorted(df_cargos_ev["Tipo"].dropna().unique().tolist()) or ["Masterclass","Workshop","Curso de IA"]
    df_ev_view = df_cargos_ev[df_cargos_ev["Tipo"].isin(tipos_sel)].copy()

    # totais por cargo
    tot_view = (
        df_ev_view[cargo_cols].sum().sort_values(ascending=False)
        if not df_ev_view.empty else pd.Series(dtype=float)
    )
    df_rank_view = (
        pd.DataFrame({"Cargo": tot_view.index, "Inscritos": tot_view.values})
        .set_index("Cargo") if not tot_view.empty else pd.DataFrame()
    )

    # ranking + donut com proporção 65/35 e alturas iguais
    col1, col2 = st.columns([1.65, 1])

    # Ranking com números fora da barra
    with col1:
        if not df_rank_view.empty:
            top_df = df_rank_view.head(topn).sort_values("Inscritos")
            fig_rank = px.bar(
                top_df, x="Inscritos", y=top_df.index, orientation="h",
                title=f"Top {topn} Cargos por Inscritos"
            )
            # rótulos fora + folga no eixo X
            x_max = max(1, top_df["Inscritos"].max())
            fig_rank.update_traces(text=top_df["Inscritos"], texttemplate="%{x}", textposition="outside", cliponaxis=False)
            fig_rank.update_xaxes(range=[0, x_max * 1.15])
            st.plotly_chart(style_fig(fig_rank, height=460), use_container_width=True,
                            key=f"t2_cargos_rank_{topn}")
        else:
            st.info("Sem dados para o ranking.")

    # Donut com percentuais dentro das fatias
    with col2:
        if not df_rank_view.empty:
            top_part = df_rank_view.head(topn).reset_index()
            top_part["%"] = top_part["Inscritos"] / top_part["Inscritos"].sum() * 100
            fig_pie = px.pie(top_part, values="Inscritos", names="Cargo", hole=0.55)
            fig_pie.update_traces(textinfo="percent", textposition="inside", insidetextorientation="radial")
            fig_pie.update_layout(legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02))
            st.plotly_chart(style_fig(fig_pie, height=460), use_container_width=True,
                            key=f"t2_cargos_pie_{topn}")
        else:
            st.info("Sem dados para o donut.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Stacked por tipo com números dentro de cada segmento
    st.markdown('<div class="panel"><h3>Inscritos por Cargo e Tipo de Evento</h3>', unsafe_allow_html=True)
    if not df_ev_view.empty:
        df_tipo_view = df_ev_view.groupby("Tipo")[cargo_cols].sum().T
        cols_presentes = [c for c in tipos_sel if c in df_tipo_view.columns]
        if cols_presentes:
            top_idx = df_rank_view.head(topn).index
            stacked_df = df_tipo_view.loc[top_idx, cols_presentes].fillna(0)
            stacked_df = stacked_df.loc[stacked_df.sum(axis=1).sort_values().index]
            fig_stacked = px.bar(
                stacked_df, x=cols_presentes, y=stacked_df.index,
                orientation="h", barmode="stack"
            )
            fig_stacked.update_traces(texttemplate="%{x:.0f}", textposition="inside", insidetextanchor="middle")
            st.plotly_chart(style_fig(fig_stacked), use_container_width=True,
                            key=f"t2_cargos_stacked_{topn}")
        else:
            st.info("Tipos selecionados não possuem dados.")
    else:
        st.info("Sem dados para o stacked.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Série por evento para um cargo  ▸ barras mais grossas
    st.markdown('<div class="panel"><h3>Evolução por Evento</h3>', unsafe_allow_html=True)
    if cargo_cols and not df_ev_view.empty:
        cargo_escolhido = st.selectbox("Escolha um cargo", cargo_cols, index=0, key="t2_cargo_series")
        serie = (
            df_ev_view[[EVENTO_COL, "Tipo", cargo_escolhido]]
            .rename(columns={EVENTO_COL: "Evento", cargo_escolhido: "Inscritos"})
        )

        fig_series = px.bar(
            serie, x="Evento", y="Inscritos", color="Tipo",
            barmode="group", title=None
        )
        # 🔧 barras mais grossas
        fig_series.update_layout(bargap=0.02, bargroupgap=0.02)
        fig_series.update_traces(marker_line_width=0)

        # eixo X legível
        fig_series.update_xaxes(tickangle=-35)

        st.plotly_chart(style_fig(fig_series, height=520), use_container_width=True,
                        key=f"t2_cargos_series_{cargo_escolhido}")
    else:
        st.info("Nenhuma coluna de cargo encontrada.")
    st.markdown('</div>', unsafe_allow_html=True)


# --------- Secretarias
with tab3:
    # Consolidado
    grp = df_f.groupby('SECRETARIA/ÓRGÃO')[['Nº INSCRITOS','Nº CERTIFICADOS']].sum().reset_index()
    grp['Taxa de Certificação (%)'] = (
        grp['Nº CERTIFICADOS'] / grp['Nº INSCRITOS']
    ).replace([pd.NA, float('inf')], 0).fillna(0) * 100

    # -------- TABELA (OCULTA POR PADRÃO) --------
    show_sec_table = st.toggle(
        "Mostrar tabela de secretarias", value=False,
        help="Ative para visualizar o consolidado; por padrão fica oculto."
    )
    if show_sec_table:
        df_panel(grp.round(2), "Consolidado por Secretaria/Órgão", key=f"tbl_sec_{len(grp)}")
    # --------------------------------------------

    st.markdown('<div class="panel"><h3>Inscritos X Certificados</h3>', unsafe_allow_html=True)
    cA, cB = st.columns(2)

    # --- Barras com valores visíveis (lado de fora)
    with cA:
        top_comp = grp.sort_values('Nº INSCRITOS', ascending=False).head(topn)
        fig_comp = px.bar(
            top_comp,
            x=['Nº INSCRITOS','Nº CERTIFICADOS'],
            y='SECRETARIA/ÓRGÃO',
            orientation='h',
            barmode='group',
            text_auto=True,                        # exibe números automaticamente
            title=None
        )
        fig_comp.update_traces(textposition="outside", cliponaxis=False, textfont_size=12)
        st.plotly_chart(style_fig(fig_comp), use_container_width=True, key=f"sec_comp_{topn}")

    # --- Top por taxa, com % visível
    with cB:
        top_taxa = grp[grp['Nº INSCRITOS'] > 0] \
            .sort_values('Taxa de Certificação (%)', ascending=False) \
            .head(topn)
        fig_taxa = px.bar(
            top_taxa,
            x='Taxa de Certificação (%)',
            y='SECRETARIA/ÓRGÃO',
            orientation='h',
            title=f'Top {topn} por Taxa de Certificação',
            text='Taxa de Certificação (%)'       # usa a própria coluna como texto
        )
        fig_taxa.update_traces(
            texttemplate='%{text:.0f}%',          # formata como porcentagem inteira
            textposition='outside',
            cliponaxis=False,
            textfont_size=12
        )
        fig_taxa.update_xaxes(ticksuffix="%")
        st.plotly_chart(style_fig(fig_taxa), use_container_width=True, key=f"sec_taxa_top_{topn}")

    # --- Treemap com % de certificação no centro
    st.markdown('<div class="panel"><h3>Participação no total de Inscritos</h3>', unsafe_allow_html=True)
    grp_tree = grp.sort_values('Nº INSCRITOS', ascending=False).head(max(topn*2, 20))
    treemap = px.treemap(
        grp_tree,
        path=['SECRETARIA/ÓRGÃO'],
        values='Nº INSCRITOS',
        color='Taxa de Certificação (%)',
        custom_data=['Taxa de Certificação (%)'],        # passa a % para usar no texto
        title='Treemap — maiores contribuições'
    )
    # label + % grande no centro de cada quadrado
    treemap.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:.0f}%",
        textposition="middle center"
    )
    treemap.update_layout(uniformtext_minsize=12, uniformtext_mode='show')
    st.plotly_chart(style_fig(treemap, height=520), use_container_width=True, key="sec_tree")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Eventos
with tab4:
    if df_visao.empty:
        st.info("Aba 'VISÃO ABERTA' vazia ou inválida.")
    else:
        import re

        # Base
        ev = df_visao.copy()
        ev["Tipo"] = (
            ev["EVENTO"].astype(str)
            .str.extract(r"(Masterclass|Workshop|Curso)", expand=False)
            .str.title()
            .replace({"Curso": "Curso de IA"})
        ).fillna("Outro")
        ev["Taxa de Certificação (%)"] = (
            ev["Nº CERTIFICADOS"] / ev["Nº INSCRITOS"]
        ).replace([pd.NA, float("inf")], 0).fillna(0) * 100
        ev["Evasão (Nº)"] = (ev["Nº INSCRITOS"] - ev["Nº CERTIFICADOS"]).clip(lower=0)

        # 🔹 Nome curto do evento para o treemap: "11° Curso", "7° Masterclass", "3° Workshop"
        def evento_curto(evento: str, tipo: str) -> str:
            s = str(evento)
            # tenta pegar o número que antecede a palavra Masterclass/Workshop/Curso
            m = re.search(r"(\d+)\s*[ºª]?\s*(?=Masterclass|Workshop|Curso)", s, flags=re.I)
            num = m.group(1) if m else None
            base = "Curso" if "Curso" in tipo else ("Masterclass" if "Masterclass" in tipo else ("Workshop" if "Workshop" in tipo else tipo))
            return f"{num}° {base}" if num else base

        ev["EVENTO_CURTO"] = ev.apply(lambda r: evento_curto(r["EVENTO"], r["Tipo"]), axis=1)

        # ✅ Filtros ocultos (usa todos os tipos)
        tipos_sel = sorted(ev["Tipo"].dropna().unique().tolist())
        ev_view = ev[ev["Tipo"].isin(tipos_sel)].copy()

        # ---- TABELA (OCULTA POR PADRÃO) ----
        show_ev_table = st.toggle(
            "Mostrar tabela de eventos", value=False,
            help="Ative para visualizar a planilha; por padrão fica oculta."
        )
        if show_ev_table:
            cols_evento = [
                c for c in ["Nº","EVENTO","Tipo","Nº INSCRITOS",
                            "Nº CERTIFICADOS","Evasão (Nº)","Taxa de Certificação (%)"]
                if c in ev_view.columns
            ]
            df_panel(ev_view[cols_evento].reset_index(drop=True),
                     "Eventos (filtrados)", key=f"tbl_evt_{len(ev_view)}")
        # ------------------------------------

        # === LINHA 1: Donut + Boxplot lado a lado ===
        by_tipo = ev_view.groupby("Tipo")[["Nº INSCRITOS","Nº CERTIFICADOS"]].sum()
        col_left, col_right = st.columns([1.2, 1])  # donut | boxplot

        with col_left:
            if not by_tipo.empty:
                pie = px.pie(by_tipo.reset_index(),
                             values="Nº INSCRITOS", names="Tipo", hole=0.55)
                pie.update_layout(legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02))
                st.plotly_chart(style_fig(pie, height=460), use_container_width=True,
                                key=f"ev_pie_{len(tipos_sel)}")
            else:
                st.info("Sem dados para o donut.")

        with col_right:
            if not ev_view.empty:
                box = px.box(ev_view, x="Tipo", y="Taxa de Certificação (%)",
                             title="Taxa de Certificação — distribuição por tipo")
                box.update_yaxes(ticksuffix="%")
                st.plotly_chart(style_fig(box, height=460), use_container_width=True, key="ev_box")
            else:
                st.info("Sem dados para o boxplot.")

        # === FULL WIDTH: Barras por tipo (com números acima das colunas) ===
        if not by_tipo.empty:
            st.markdown('<div class="panel"><h3>Totais por tipo (Inscritos x Certificados)</h3>', unsafe_allow_html=True)
            by_tipo2 = by_tipo.reset_index().melt(
                id_vars="Tipo",
                value_vars=["Nº INSCRITOS","Nº CERTIFICADOS"],
                var_name="Métrica", value_name="Total"
            )
            bar_tipo = px.bar(by_tipo2, x="Tipo", y="Total", color="Métrica", barmode="group", title=None)
            # rótulos acima das colunas
            bar_tipo.update_traces(texttemplate="%{y}", textposition="outside", cliponaxis=False)
            maxy = max(1, by_tipo2["Total"].max())
            bar_tipo.update_yaxes(range=[0, maxy * 1.15])
            st.plotly_chart(style_fig(bar_tipo, height=420), use_container_width=True, key="ev_bar_tipo")
            st.markdown('</div>', unsafe_allow_html=True)

        # === TREEMAP — rótulos curtos + % no quadrado + EXPLICAÇÃO LATERAL ===
        if not ev_view.empty:
            st.markdown('<div class="panel"><h3>Treemap — participação por evento</h3>', unsafe_allow_html=True)

            import re

            def rotulo_curto(evento: str, tipo: str) -> str:
                s = str(evento)
                base = s.split(":", 1)[0].strip() or tipo
                # 11° Curso / 2° Masterclass / 1° Workshop...
                m = re.search(r"(\d+)\s*[ºª]?\s*(Masterclass|Workshop|Curso(?:\s+de\s+IA)?)", base, flags=re.I)
                if m:
                    num = m.group(1)
                    kind = m.group(2)
                    kind = re.sub(r"(?i)^curso(?:\s+de\s+ia)?$", "Curso de IA", kind).title()
                    return f"{num}° {kind}"
                return " ".join(base.split()[:4])

            ev_tmp = ev_view.copy()
            ev_tmp["EVENTO_LABEL"] = ev_tmp.apply(lambda r: rotulo_curto(r["EVENTO"], r["Tipo"]), axis=1)

            # layout lado a lado: treemap | explicação
            col_tm, col_desc = st.columns([4, 1.7], gap="large")

            with col_tm:
                tmap = px.treemap(
                    ev_tmp.sort_values("Nº INSCRITOS", ascending=False).head(max(topn*2, 20)),
                    path=["Tipo", "EVENTO_LABEL"],
                    values="Nº INSCRITOS",
                    title=None
                )
                # mostra label + % do total filtrado no centro do quadrado
                tmap.update_traces(
                    textinfo="label+text",
                    texttemplate="%{label}<br>%{percentRoot:.1%}",
                    textposition="middle center",
                    hovertemplate="<b>%{label}</b><br>Inscritos: %{value}<br>Participação: %{percentRoot:.1%}<extra></extra>",
                )
                st.plotly_chart(style_fig(tmap, height=520), use_container_width=True, key="ev_treemap_labels_pct")

            with col_desc:
                st.markdown(
                    """
                    <div class="panel">
                    <h3>O que é essa porcentagem?</h3>
                    <p>É a <b>participação no total de inscritos</b> considerando todos os filtros atuais.</p>
                    <ul>
                        <li><b>Blocos de nível "Tipo"</b> (Curso de IA, Masterclass, Workshop): % do total para cada tipo.</li>
                        <li><b>Blocos de nível "Evento"</b> (ex.: <i>11° Curso</i>): % daquele evento no total.</li>
                    </ul>
                    <p>Passe o mouse sobre um bloco para ver <b>inscritos absolutos</b> e a mesma participação (%).</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)




