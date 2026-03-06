"""Dashboard CapacitIA — Evolução Temporal (Linha do Tempo Anual)."""

import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_servidores_data
from src.utils.constants import COLORS

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="Evolução Temporal - CapacitIA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

pio.templates["capacit_dark"] = pio.templates["plotly_dark"]
pio.templates["capacit_dark"].layout.font.family = "Inter, Segoe UI, Roboto, Arial"
pio.templates["capacit_dark"].layout.colorway = [
    "#7DD3FC", "#34D399", "#FBBF24", "#F472B6", "#60A5FA", "#A78BFA", "#F87171"
]
pio.templates["capacit_dark"].layout.paper_bgcolor = "#0f1220"
pio.templates["capacit_dark"].layout.plot_bgcolor  = "#11142a"
pio.templates["capacit_dark"].layout.hoverlabel = dict(
    bgcolor="#0f1220", font_size=12, font_family="Inter, Segoe UI, Roboto, Arial"
)
pio.templates.default = "capacit_dark"

with open("styles/main.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# =========================
# HELPERS
# =========================
def style_fig(fig, height=420):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis_title=None,
        yaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def fmt_br(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def delta_badge(valor: float, suffix: str = "%") -> str:
    """Retorna HTML colorido para variação positiva/negativa."""
    if pd.isna(valor):
        return '<span style="color:#7780a1">— primeiro ano</span>'
    cor = "#34D399" if valor >= 0 else "#F87171"
    sinal = "▲" if valor >= 0 else "▼"
    return f'<span style="color:{cor};font-weight:700">{sinal} {abs(valor):.1f}{suffix}</span>'


# =========================
# CARREGAR DADOS
# =========================
processed_path = Path(".data") / "processed"


@st.cache_data(show_spinner=False)
def load_evolucao():
    """Carrega arquivos de evolução anual; fallback: recalcula a partir de dados.parquet."""
    files = {
        "geral":   "evolucao_anual_geral.parquet",
        "formato": "evolucao_anual_formato.parquet",
        "orgao":   "evolucao_anual_orgao.parquet",
        "cargo":   "evolucao_anual_cargo.parquet",
        "eixo":    "evolucao_anual_eixo.parquet",
    }

    result = {}
    missing = []
    for key, fname in files.items():
        fpath = processed_path / fname
        if fpath.exists():
            result[key] = pd.read_parquet(fpath)
        else:
            missing.append(key)

    if missing:
        # Fallback: recalcular a partir de dados.parquet
        dados_path = processed_path / "dados.parquet"
        if not dados_path.exists():
            return None

        df = pd.read_parquet(dados_path)

        # Se não houver coluna ano, tentar inferir
        if "ano" not in df.columns:
            st.warning(
                "⚠️ Coluna **ano** não encontrada nos dados. "
                "Execute novamente `preparar_dados.py` e `process_csv_to_parquet.py` "
                "para habilitar a linha do tempo completa. "
                "Exibindo dados do ano corrente como fallback."
            )
            df["ano"] = "2025"

        df["ano"] = df["ano"].astype(str).str.strip()

        # geral
        geral = df.groupby("ano").agg(
            total_inscritos=("nome", "count"),
            total_certificados=("certificado", lambda x: (x == "Sim").sum()),
            total_eventos=("evento", "nunique"),
            total_orgaos=("orgao", "nunique"),
            total_gestores=("cargo_gestao", lambda x: (x == "Sim").sum()) if "cargo_gestao" in df.columns else ("nome", "count"),
        ).reset_index()
        geral["taxa_certificacao"] = (
            geral["total_certificados"] / geral["total_inscritos"] * 100
        ).round(2)
        geral["taxa_evasao"] = (
            (geral["total_inscritos"] - geral["total_certificados"])
            / geral["total_inscritos"] * 100
        ).round(2)
        for col in ["total_inscritos", "total_certificados", "total_eventos", "total_orgaos"]:
            geral[f"{col}_crescimento_pct"] = geral[col].pct_change() * 100
        result["geral"] = geral

        # formato
        if "formato" not in result:
            ev_fmt = df.groupby(["ano", "formato"]).agg(
                n_inscritos=("nome", "count"),
                n_certificados=("certificado", lambda x: (x == "Sim").sum()),
                n_eventos=("evento", "nunique"),
            ).reset_index()
            ev_fmt["taxa_certificacao"] = (ev_fmt["n_certificados"] / ev_fmt["n_inscritos"] * 100).round(2)
            result["formato"] = ev_fmt

        # orgao
        if "orgao" not in result:
            filtro = df["orgao"].astype(str).str.strip()
            df_org = df[~filtro.str.lower().isin(["outro", "outros", ""])].copy()
            ev_org = df_org.groupby(["ano", "orgao"]).agg(
                n_inscritos=("nome", "count"),
                n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            ).reset_index()
            ev_org["taxa_certificacao"] = (ev_org["n_certificados"] / ev_org["n_inscritos"] * 100).round(2)
            result["orgao"] = ev_org

        # cargo
        if "cargo" not in result:
            filtro_c = df["cargo"].astype(str).str.strip().str.lower()
            df_c = df[~filtro_c.isin(["", "outro", "outros"])].copy()
            ev_c = df_c.groupby(["ano", "cargo"]).agg(
                n_inscritos=("nome", "count"),
                n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            ).reset_index()
            result["cargo"] = ev_c

        # eixo
        if "eixo" not in result:
            ev_eixo = df.groupby(["ano", "eixo"]).agg(
                n_inscritos=("nome", "count"),
                n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            ).reset_index()
            result["eixo"] = ev_eixo

    return result


with st.spinner("Carregando dados de evolução..."):
    evolucao = load_evolucao()

if evolucao is None:
    st.error(
        "❌ Dados não encontrados. Execute o pipeline de processamento:\n"
        "```\npython src/process_csv_to_parquet.py\n```"
    )
    st.stop()

geral    = evolucao["geral"].sort_values("ano")
formato  = evolucao["formato"]
orgao_ev = evolucao["orgao"]
cargo_ev = evolucao["cargo"]
eixo_ev  = evolucao["eixo"]

anos_disponiveis = sorted(geral["ano"].unique().tolist())
tem_comparacao   = len(anos_disponiveis) >= 2


# =========================
# HEADER
# =========================
st.title("📈 Evolução Temporal — CapacitIA")
st.markdown(
    f'<p style="color:{COLORS["muted"]}; margin-bottom:4px;">'
    f"Acompanhe o crescimento e as mudanças do programa ao longo dos anos. "
    f"Anos disponíveis: <b style='color:{COLORS['primary']}'>{' · '.join(anos_disponiveis)}</b>"
    f"</p>"
    f'<p style="color:{COLORS["muted"]}; font-size:0.85rem;">Atualizado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>',
    unsafe_allow_html=True,
)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🏠 Voltar à Home", use_container_width=True):
        st.switch_page("app.py")
with col_btn2:
    if st.button("👥 Ver Servidores", use_container_width=True):
        st.switch_page("pages/2_👥_Servidores.py")

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# KPIs DE CRESCIMENTO (comparação último vs penúltimo ano)
# =========================
st.markdown("## 🚀 Visão de Crescimento")

if tem_comparacao:
    ano_atual  = anos_disponiveis[-1]
    ano_ant    = anos_disponiveis[-2]
    row_atual  = geral[geral["ano"] == ano_atual].iloc[0]
    row_ant    = geral[geral["ano"] == ano_ant].iloc[0]

    def crescimento(atual, ant):
        if ant == 0:
            return np.nan
        return (atual - ant) / ant * 100

    kpis = [
        ("Inscritos",          row_atual.total_inscritos,    row_ant.total_inscritos,    "👥"),
        ("Certificados",       row_atual.total_certificados, row_ant.total_certificados, "✅"),
        ("Eventos",            row_atual.total_eventos,       row_ant.total_eventos,      "📅"),
        ("Órgãos Atendidos",   row_atual.total_orgaos,        row_ant.total_orgaos,       "🏢"),
        ("Taxa Certificação",  row_atual.taxa_certificacao,   row_ant.taxa_certificacao,  "🎯"),
    ]

    cols = st.columns(len(kpis))
    for col, (label, val_atual, val_ant, icon) in zip(cols, kpis):
        delta_pct = crescimento(val_atual, val_ant)
        is_taxa   = label == "Taxa Certificação"
        fmt       = f"{val_atual:.1f}%" if is_taxa else fmt_br(val_atual)
        badge     = delta_badge(delta_pct)
        col.markdown(
            f'<div class="kpi">'
            f'<h4>{icon} {label}</h4>'
            f'<div class="val">{fmt}</div>'
            f'<div style="font-size:0.8rem;margin-top:4px">{badge} vs {ano_ant}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    row = geral.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi"><h4>👥 Inscritos</h4><div class="val">{fmt_br(row.total_inscritos)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi"><h4>✅ Certificados</h4><div class="val">{fmt_br(row.total_certificados)}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi"><h4>📅 Eventos</h4><div class="val">{int(row.total_eventos)}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi"><h4>🎯 Taxa Cert.</h4><div class="val">{row.taxa_certificacao:.1f}%</div></div>', unsafe_allow_html=True)
    st.info("ℹ️ Apenas um ano disponível. Adicione dados de outros anos para habilitar comparações.")

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# ABAS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visão Geral",
    "📚 Por Formato",
    "🏢 Por Órgão",
    "👤 Por Cargo",
    "🧭 Por Eixo",
])


# ─────────────────────────────────────────────
# TAB 1 — VISÃO GERAL
# ─────────────────────────────────────────────
with tab1:
    st.markdown("### 📊 Evolução dos Principais Indicadores")

    col_l, col_r = st.columns(2)

    # Gráfico principal: Inscritos e Certificados por Ano
    with col_l:
        st.markdown('<div class="panel"><h3>Inscritos vs Certificados por Ano</h3>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_bar(
            x=geral["ano"], y=geral["total_inscritos"],
            name="Inscritos", marker_color="#7DD3FC",
            text=geral["total_inscritos"].apply(fmt_br),
            textposition="outside",
        )
        fig_bar.add_bar(
            x=geral["ano"], y=geral["total_certificados"],
            name="Certificados", marker_color="#34D399",
            text=geral["total_certificados"].apply(fmt_br),
            textposition="outside",
        )
        fig_bar.update_layout(barmode="group", xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_bar, 400), use_container_width=True, key="tl_bar_geral")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="panel"><h3>Taxa de Certificação por Ano (%)</h3>', unsafe_allow_html=True)
        fig_taxa = go.Figure()
        fig_taxa.add_scatter(
            x=geral["ano"], y=geral["taxa_certificacao"],
            mode="lines+markers+text",
            line=dict(color="#FBBF24", width=3),
            marker=dict(size=12),
            text=geral["taxa_certificacao"].apply(lambda v: f"{v:.1f}%"),
            textposition="top center",
            name="Taxa Cert.",
        )
        fig_taxa.add_scatter(
            x=geral["ano"], y=geral["taxa_evasao"],
            mode="lines+markers+text",
            line=dict(color="#F87171", width=2, dash="dot"),
            marker=dict(size=10),
            text=geral["taxa_evasao"].apply(lambda v: f"{v:.1f}%"),
            textposition="bottom center",
            name="Taxa Evasão",
        )
        fig_taxa.update_layout(yaxis=dict(ticksuffix="%"), xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_taxa, 400), use_container_width=True, key="tl_linha_taxa")
        st.markdown('</div>', unsafe_allow_html=True)

    # Linha do tempo de eventos e órgãos
    col_ev, col_org = st.columns(2)
    with col_ev:
        st.markdown('<div class="panel"><h3>Total de Eventos por Ano</h3>', unsafe_allow_html=True)
        fig_ev = px.bar(
            geral, x="ano", y="total_eventos",
            text="total_eventos", color_discrete_sequence=["#A78BFA"],
        )
        fig_ev.update_traces(textposition="outside", cliponaxis=False)
        fig_ev.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_ev, 340), use_container_width=True, key="tl_ev")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_org:
        st.markdown('<div class="panel"><h3>Total de Órgãos Atendidos por Ano</h3>', unsafe_allow_html=True)
        fig_org = px.bar(
            geral, x="ano", y="total_orgaos",
            text="total_orgaos", color_discrete_sequence=["#F472B6"],
        )
        fig_org.update_traces(textposition="outside", cliponaxis=False)
        fig_org.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_org, 340), use_container_width=True, key="tl_org")
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabela de resumo anual
    if st.toggle("📋 Ver tabela de dados anuais", value=False, key="tg_tabela_geral"):
        display_cols = {
            "ano": "Ano",
            "total_inscritos": "Inscritos",
            "total_certificados": "Certificados",
            "taxa_certificacao": "Taxa Cert. (%)",
            "taxa_evasao": "Taxa Evasão (%)",
            "total_eventos": "Eventos",
            "total_orgaos": "Órgãos",
        }
        df_show = geral[[c for c in display_cols if c in geral.columns]].rename(columns=display_cols)
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    # Crescimento percentual (waterfall-style)
    if tem_comparacao:
        st.markdown('<div class="panel"><h3>📈 Crescimento Percentual Anual</h3>', unsafe_allow_html=True)
        metricas_cresc = []
        colunas_cresc = {
            "total_inscritos_crescimento_pct": "Inscritos",
            "total_certificados_crescimento_pct": "Certificados",
            "total_eventos_crescimento_pct": "Eventos",
            "total_orgaos_crescimento_pct": "Órgãos",
        }
        for col, label in colunas_cresc.items():
            if col in geral.columns:
                for _, row in geral.iterrows():
                    val = row.get(col, np.nan)
                    if not pd.isna(val):
                        metricas_cresc.append({"Ano": row["ano"], "Métrica": label, "Crescimento (%)": round(val, 1)})

        if metricas_cresc:
            df_cresc = pd.DataFrame(metricas_cresc)
            fig_cresc = px.bar(
                df_cresc, x="Métrica", y="Crescimento (%)", color="Ano",
                barmode="group", text="Crescimento (%)",
                color_discrete_sequence=["#7DD3FC", "#34D399", "#FBBF24", "#F472B6"],
            )
            fig_cresc.add_hline(y=0, line_dash="dot", line_color="#7780a1")
            fig_cresc.update_traces(texttemplate="%{y:+.1f}%", textposition="outside", cliponaxis=False)
            fig_cresc.update_yaxes(ticksuffix="%")
            st.plotly_chart(style_fig(fig_cresc, 420), use_container_width=True, key="tl_cresc")
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 2 — POR FORMATO
# ─────────────────────────────────────────────
with tab2:
    st.markdown("### 📚 Evolução por Tipo de Evento (Formato)")

    if formato.empty:
        st.info("Sem dados de formato disponíveis.")
    else:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="panel"><h3>Inscritos por Formato e Ano</h3>', unsafe_allow_html=True)
            fig_fmt = px.bar(
                formato.sort_values(["ano", "n_inscritos"], ascending=[True, False]),
                x="formato", y="n_inscritos", color="ano",
                barmode="group", text="n_inscritos",
                labels={"n_inscritos": "Inscritos", "formato": "Formato", "ano": "Ano"},
            )
            fig_fmt.update_traces(texttemplate="%{y}", textposition="outside", cliponaxis=False)
            st.plotly_chart(style_fig(fig_fmt, 400), use_container_width=True, key="tl_fmt_bar")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="panel"><h3>Taxa de Certificação por Formato</h3>', unsafe_allow_html=True)
            fig_fmt_taxa = px.line(
                formato.sort_values("ano"),
                x="ano", y="taxa_certificacao", color="formato",
                markers=True,
                labels={"taxa_certificacao": "Taxa Cert. (%)", "ano": "Ano"},
            )
            fig_fmt_taxa.update_yaxes(ticksuffix="%")
            fig_fmt_taxa.update_layout(xaxis=dict(type="category"))
            st.plotly_chart(style_fig(fig_fmt_taxa, 400), use_container_width=True, key="tl_fmt_taxa")
            st.markdown('</div>', unsafe_allow_html=True)

        # Heatmap: formato × ano (inscritos)
        st.markdown('<div class="panel"><h3>Heatmap — Inscritos por Formato × Ano</h3>', unsafe_allow_html=True)
        pivot = formato.pivot_table(index="formato", columns="ano", values="n_inscritos", aggfunc="sum").fillna(0)
        fig_heat = px.imshow(
            pivot,
            text_auto=True,
            color_continuous_scale="Blues",
            aspect="auto",
            labels={"color": "Inscritos"},
        )
        fig_heat.update_traces(textfont_size=13)
        fig_heat.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_heat, 300), use_container_width=True, key="tl_fmt_heat")
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 3 — POR ÓRGÃO
# ─────────────────────────────────────────────
with tab3:
    st.markdown("### 🏢 Evolução por Órgão/Secretaria")

    if orgao_ev.empty:
        st.info("Sem dados de órgãos disponíveis.")
    else:
        # Selecionar top N órgãos pelo total geral
        top_n_org = st.slider("Quantidade de órgãos a exibir", 5, 30, 15, key="sl_top_org")
        top_orgaos = (
            orgao_ev.groupby("orgao")["n_inscritos"].sum()
            .sort_values(ascending=False)
            .head(top_n_org)
            .index.tolist()
        )
        df_org_top = orgao_ev[orgao_ev["orgao"].isin(top_orgaos)]

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="panel"><h3>Inscritos por Órgão e Ano</h3>', unsafe_allow_html=True)
            fig_org = px.bar(
                df_org_top.sort_values("n_inscritos"),
                x="n_inscritos", y="orgao", color="ano",
                barmode="group", orientation="h",
                labels={"n_inscritos": "Inscritos", "orgao": "Órgão"},
            )
            fig_org.update_traces(texttemplate="%{x}", textposition="outside", cliponaxis=False)
            st.plotly_chart(style_fig(fig_org, 520), use_container_width=True, key="tl_org_bar")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="panel"><h3>Taxa de Certificação por Órgão e Ano</h3>', unsafe_allow_html=True)
            fig_org_taxa = px.bar(
                df_org_top.sort_values("taxa_certificacao"),
                x="taxa_certificacao", y="orgao", color="ano",
                barmode="group", orientation="h",
                labels={"taxa_certificacao": "Taxa Cert. (%)", "orgao": "Órgão"},
            )
            fig_org_taxa.update_traces(texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False)
            fig_org_taxa.update_xaxes(ticksuffix="%")
            st.plotly_chart(style_fig(fig_org_taxa, 520), use_container_width=True, key="tl_org_taxa")
            st.markdown('</div>', unsafe_allow_html=True)

        # Órgãos novos vs recorrentes (só se há 2+ anos)
        if tem_comparacao:
            st.markdown('<div class="panel"><h3>🆕 Órgãos Novos vs Recorrentes</h3>', unsafe_allow_html=True)
            orgaos_por_ano = {ano: set(orgao_ev[orgao_ev["ano"] == ano]["orgao"]) for ano in anos_disponiveis}
            resumo_rows = []
            for i, ano in enumerate(anos_disponiveis):
                orgaos_ano = orgaos_por_ano[ano]
                if i == 0:
                    novos, recorrentes = len(orgaos_ano), 0
                else:
                    orgaos_anteriores = set().union(*[orgaos_por_ano[a] for a in anos_disponiveis[:i]])
                    novos       = len(orgaos_ano - orgaos_anteriores)
                    recorrentes = len(orgaos_ano & orgaos_anteriores)
                resumo_rows.append({"Ano": ano, "Novos": novos, "Recorrentes": recorrentes, "Total": novos + recorrentes})

            df_resumo_org = pd.DataFrame(resumo_rows)
            fig_nov = px.bar(
                df_resumo_org.melt(id_vars="Ano", value_vars=["Novos", "Recorrentes"]),
                x="Ano", y="value", color="variable",
                barmode="stack", text="value",
                color_discrete_map={"Novos": "#34D399", "Recorrentes": "#7DD3FC"},
                labels={"value": "Órgãos", "variable": ""},
            )
            fig_nov.update_traces(texttemplate="%{y}", textposition="inside")
            fig_nov.update_layout(xaxis=dict(type="category"))
            st.plotly_chart(style_fig(fig_nov, 340), use_container_width=True, key="tl_org_novos")
            st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 4 — POR CARGO
# ─────────────────────────────────────────────
with tab4:
    st.markdown("### 👤 Evolução por Cargo")

    if cargo_ev.empty:
        st.info("Sem dados de cargo disponíveis.")
    else:
        top_n_cargo = st.slider("Quantidade de cargos a exibir", 5, 25, 12, key="sl_top_cargo")
        top_cargos = (
            cargo_ev.groupby("cargo")["n_inscritos"].sum()
            .sort_values(ascending=False)
            .head(top_n_cargo)
            .index.tolist()
        )
        df_c_top = cargo_ev[cargo_ev["cargo"].isin(top_cargos)]

        st.markdown('<div class="panel"><h3>Inscritos por Cargo e Ano</h3>', unsafe_allow_html=True)
        fig_cargo = px.bar(
            df_c_top.sort_values("n_inscritos"),
            x="n_inscritos", y="cargo", color="ano",
            barmode="group", orientation="h",
            labels={"n_inscritos": "Inscritos", "cargo": "Cargo"},
        )
        fig_cargo.update_traces(texttemplate="%{x}", textposition="outside", cliponaxis=False)
        st.plotly_chart(style_fig(fig_cargo, 540), use_container_width=True, key="tl_cargo_bar")
        st.markdown('</div>', unsafe_allow_html=True)

        # Heatmap de cargos × ano
        st.markdown('<div class="panel"><h3>Heatmap — Inscritos por Cargo × Ano</h3>', unsafe_allow_html=True)
        pivot_c = df_c_top.pivot_table(index="cargo", columns="ano", values="n_inscritos", aggfunc="sum").fillna(0)
        fig_heat_c = px.imshow(
            pivot_c, text_auto=True,
            color_continuous_scale="Teal", aspect="auto",
            labels={"color": "Inscritos"},
        )
        fig_heat_c.update_traces(textfont_size=12)
        fig_heat_c.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_heat_c, 420), use_container_width=True, key="tl_cargo_heat")
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 5 — POR EIXO
# ─────────────────────────────────────────────
with tab5:
    st.markdown("### 🧭 Evolução por Eixo Temático")

    if eixo_ev.empty:
        st.info("Sem dados de eixo disponíveis.")
    else:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="panel"><h3>Inscritos por Eixo e Ano</h3>', unsafe_allow_html=True)
            fig_eixo = px.bar(
                eixo_ev.sort_values(["ano", "n_inscritos"], ascending=[True, False]),
                x="eixo", y="n_inscritos", color="ano",
                barmode="group", text="n_inscritos",
                labels={"n_inscritos": "Inscritos", "eixo": "Eixo"},
            )
            fig_eixo.update_traces(texttemplate="%{y}", textposition="outside", cliponaxis=False)
            fig_eixo.update_layout(xaxis=dict(type="category"))
            st.plotly_chart(style_fig(fig_eixo, 420), use_container_width=True, key="tl_eixo_bar")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="panel"><h3>Participação por Eixo (Treemap)</h3>', unsafe_allow_html=True)
            fig_eixo_tree = px.treemap(
                eixo_ev,
                path=["eixo", "ano"],
                values="n_inscritos",
                color="n_inscritos",
                color_continuous_scale="Blues",
                labels={"n_inscritos": "Inscritos"},
            )
            fig_eixo_tree.update_traces(
                texttemplate="<b>%{label}</b><br>%{value}",
                textposition="middle center",
            )
            st.plotly_chart(style_fig(fig_eixo_tree, 420), use_container_width=True, key="tl_eixo_tree")
            st.markdown('</div>', unsafe_allow_html=True)

        # Heatmap: eixo × ano
        st.markdown('<div class="panel"><h3>Heatmap — Inscritos por Eixo × Ano</h3>', unsafe_allow_html=True)
        pivot_e = eixo_ev.pivot_table(index="eixo", columns="ano", values="n_inscritos", aggfunc="sum").fillna(0)
        fig_heat_e = px.imshow(
            pivot_e, text_auto=True,
            color_continuous_scale="Purples", aspect="auto",
            labels={"color": "Inscritos"},
        )
        fig_heat_e.update_traces(textfont_size=13)
        fig_heat_e.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(style_fig(fig_heat_e, 300), use_container_width=True, key="tl_eixo_heat")
        st.markdown('</div>', unsafe_allow_html=True)


# =========================
# RODAPÉ
# =========================
st.markdown("""
<div class="footer">
    <div class="logo">🏛️ Secretaria de Inteligência Artificial do Piauí</div>
    <div>Desenvolvido pela SIA-PI • <span class="year">2025</span></div>
    <div style="margin-top: 8px; font-size: 0.8rem;">CapacitIA — Linha do Tempo / Evolução Anual</div>
</div>
""", unsafe_allow_html=True)
