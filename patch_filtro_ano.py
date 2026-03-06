"""
patch_filtro_ano.py
-------------------
Adiciona filtro de ANO em todas as páginas de módulo do CapacitIA.
Execute uma única vez na raiz do projeto:

    python patch_filtro_ano.py

O script modifica in-place:
    pages/2_👥_Servidores.py
    pages/3_🏥_Saúde.py
    pages/4_📱_Autonomia_Digital.py
    pages/1_📊_Visão_Unificada.py
"""

import re
from pathlib import Path

# ── helpers ────────────────────────────────────────────────────────────────

def patch(path: Path, replacements: list[tuple[str, str]]) -> bool:
    """Aplica lista de (old, new) substituições em um arquivo."""
    content = path.read_text(encoding="utf-8")
    original = content
    for old, new in replacements:
        if old not in content:
            print(f"  ⚠️  Trecho não encontrado em {path.name}: {old[:60]!r}...")
            continue
        content = content.replace(old, new, 1)
    if content != original:
        path.write_text(content, encoding="utf-8")
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════
# 1. SERVIDORES
# ══════════════════════════════════════════════════════════════════════════

def patch_servidores():
    path = Path("pages/2_👥_Servidores.py")
    if not path.exists():
        print(f"❌ {path} não encontrado.")
        return

    changes = [

        # ── A. Extrair anos disponíveis logo após carregar os dados ──────
        (
            "if df_dados is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()",

            "if df_dados is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()\n\n"
            "# Anos disponíveis nos dados\n"
            "_anos_srv = sorted(df_dados['ano'].dropna().unique().tolist()) if 'ano' in df_dados.columns else []\n"
            "_tem_anos_srv = len(_anos_srv) > 1",
        ),

        # ── B. Trocar 3 colunas por 4 no bloco de filtros globais ────────
        (
            "col_f1, col_f2, col_f3 = st.columns(3)\n\n"
            "with col_f1:\n"
            "    # Filtro por tipo de curso",

            "col_f0, col_f1, col_f2, col_f3 = st.columns(4)\n\n"
            "with col_f0:\n"
            "    _ano_opts = [\"Todos os Anos\"] + _anos_srv\n"
            "    ano_selecionado = st.selectbox(\n"
            "        \"📅 Ano\",\n"
            "        _ano_opts,\n"
            "        index=0,\n"
            "        key=\"filtro_ano\",\n"
            "        help=\"Filtra todos os gráficos e métricas pelo ano selecionado.\",\n"
            "    )\n\n"
            "with col_f1:\n"
            "    # Filtro por tipo de curso",
        ),

        # ── C. Aplicar filtro de ano ANTES dos demais ────────────────────
        (
            "# Começar com cópia dos dados originais\n"
            "df_dados_filtrado = df_dados.copy() if df_dados is not None else pd.DataFrame()",

            "# Começar com cópia dos dados originais\n"
            "df_dados_filtrado = df_dados.copy() if df_dados is not None else pd.DataFrame()\n\n"
            "# 0. Filtro por ANO (aplicado primeiro, antes de qualquer outro)\n"
            "if ano_selecionado != \"Todos os Anos\" and 'ano' in df_dados_filtrado.columns:\n"
            "    df_dados_filtrado = df_dados_filtrado[\n"
            "        df_dados_filtrado['ano'].astype(str) == str(ano_selecionado)\n"
            "    ]\n"
            "if ano_selecionado != \"Todos os Anos\" and 'ano' in df_visao.columns:\n"
            "    df_visao_filtrado = df_visao[\n"
            "        df_visao['ano'].astype(str) == str(ano_selecionado)\n"
            "    ].copy()\n"
            "else:\n"
            "    df_visao_filtrado = df_visao.copy()",
        ),

        # ── D. Adicionar ano nos filtros ativos exibidos ao usuário ─────
        (
            "filtros_ativos = []\n"
            "if tipo_selecionado != \"Todos\":",

            "filtros_ativos = []\n"
            "if ano_selecionado != \"Todos os Anos\":\n"
            "    filtros_ativos.append(f\"Ano: {ano_selecionado}\")\n"
            "if tipo_selecionado != \"Todos\":",
        ),
    ]

    ok = patch(path, changes)
    print(f"  {'✅' if ok else '⚠️  sem mudanças'} {path.name}")


# ══════════════════════════════════════════════════════════════════════════
# 2. SAÚDE
# ══════════════════════════════════════════════════════════════════════════

def patch_saude():
    path = Path("pages/3_🏥_Saúde.py")
    if not path.exists():
        print(f"❌ {path} não encontrado.")
        return

    changes = [

        # ── A. Extrair anos após carregar dados ──────────────────────────
        (
            "if df_saude is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()",

            "if df_saude is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()\n\n"
            "# Anos disponíveis\n"
            "_anos_saude = sorted(df_saude['ano'].dropna().unique().tolist()) if 'ano' in df_saude.columns else []",
        ),

        # ── B. Adicionar filtro de ano no bloco de filtros ───────────────
        (
            "st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)\n"
            "col_f1, col_f2 = st.columns(2)",

            "st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)\n"
            "col_f0, col_f1, col_f2 = st.columns(3)\n\n"
            "with col_f0:\n"
            "    _ano_opts_s = [\"Todos os Anos\"] + _anos_saude\n"
            "    ano_selecionado_saude = st.selectbox(\n"
            "        \"📅 Ano\",\n"
            "        _ano_opts_s,\n"
            "        index=0,\n"
            "        key=\"filtro_ano_saude\",\n"
            "    )",
        ),

        # ── C. Aplicar filtro de ano antes dos demais ────────────────────
        (
            "# Aplicar filtros\n"
            "df_saude_filtrado = df_saude.copy()",

            "# Aplicar filtros\n"
            "df_saude_filtrado = df_saude.copy()\n"
            "if ano_selecionado_saude != \"Todos os Anos\" and 'ano' in df_saude_filtrado.columns:\n"
            "    df_saude_filtrado = df_saude_filtrado[\n"
            "        df_saude_filtrado['ano'].astype(str) == str(ano_selecionado_saude)\n"
            "    ]",
        ),
    ]

    ok = patch(path, changes)
    print(f"  {'✅' if ok else '⚠️  sem mudanças'} {path.name}")


# ══════════════════════════════════════════════════════════════════════════
# 3. AUTONOMIA DIGITAL
# ══════════════════════════════════════════════════════════════════════════

def patch_autonomia():
    path = Path("pages/4_📱_Autonomia_Digital.py")
    if not path.exists():
        print(f"❌ {path} não encontrado.")
        return

    changes = [

        # ── A. Extrair anos após carregar dados ──────────────────────────
        (
            "if df_inscricoes is None or df_avaliacoes is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()",

            "if df_inscricoes is None or df_avaliacoes is None:\n"
            "    st.error(\"Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.\")\n"
            "    st.stop()\n\n"
            "# Anos disponíveis\n"
            "_data_col_ano = next(\n"
            "    (c for c in df_inscricoes.columns if 'data' in c.lower() or 'carimbo' in c.lower()),\n"
            "    None,\n"
            ")\n"
            "_anos_ad: list = []\n"
            "if 'ano' in df_inscricoes.columns:\n"
            "    _anos_ad = sorted(df_inscricoes['ano'].dropna().unique().tolist())\n"
            "elif _data_col_ano:\n"
            "    try:\n"
            "        _anos_ad = sorted(\n"
            "            pd.to_datetime(df_inscricoes[_data_col_ano], errors='coerce')\n"
            "            .dt.year.dropna().astype(int).unique().tolist()\n"
            "        )\n"
            "    except Exception:\n"
            "        _anos_ad = []",
        ),

        # ── B. Adicionar filtro de ano no bloco de filtros ───────────────
        (
            "st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)\n"
            "col_f1, col_f2 = st.columns(2)",

            "st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)\n"
            "col_f0, col_f1, col_f2 = st.columns(3)\n\n"
            "with col_f0:\n"
            "    _ano_opts_ad = [\"Todos os Anos\"] + [str(a) for a in _anos_ad]\n"
            "    ano_selecionado_ad = st.selectbox(\n"
            "        \"📅 Ano\",\n"
            "        _ano_opts_ad,\n"
            "        index=0,\n"
            "        key=\"filtro_ano_ad\",\n"
            "    )",
        ),

        # ── C. Aplicar filtro de ano ──────────────────────────────────────
        (
            "# Aplicar filtros\n"
            "df_inscricoes_filtrado = df_inscricoes.copy()",

            "# Aplicar filtros\n"
            "df_inscricoes_filtrado = df_inscricoes.copy()\n"
            "if ano_selecionado_ad != \"Todos os Anos\":\n"
            "    if 'ano' in df_inscricoes_filtrado.columns:\n"
            "        df_inscricoes_filtrado = df_inscricoes_filtrado[\n"
            "            df_inscricoes_filtrado['ano'].astype(str) == str(ano_selecionado_ad)\n"
            "        ]\n"
            "    elif _data_col_ano:\n"
            "        try:\n"
            "            _anos_series = pd.to_datetime(\n"
            "                df_inscricoes_filtrado[_data_col_ano], errors='coerce'\n"
            "            ).dt.year.astype('Int64').astype(str)\n"
            "            df_inscricoes_filtrado = df_inscricoes_filtrado[\n"
            "                _anos_series == str(ano_selecionado_ad)\n"
            "            ]\n"
            "        except Exception:\n"
            "            pass",
        ),
    ]

    ok = patch(path, changes)
    print(f"  {'✅' if ok else '⚠️  sem mudanças'} {path.name}")


# ══════════════════════════════════════════════════════════════════════════
# 4. VISÃO UNIFICADA
# ══════════════════════════════════════════════════════════════════════════

def patch_visao_unificada():
    path = Path("pages/1_📊_Visão_Unificada.py")
    if not path.exists():
        print(f"❌ {path} não encontrado.")
        return

    # Bloco de filtro de ano a inserir logo após o header
    filtro_block = (
        "\n# ── Filtro de Ano ────────────────────────────────────────────\n"
        "_df_srv_vu = all_data['servidores']['dados']\n"
        "_anos_vu: list = []\n"
        "if _df_srv_vu is not None and 'ano' in _df_srv_vu.columns:\n"
        "    _anos_vu = sorted(_df_srv_vu['ano'].dropna().unique().tolist())\n\n"
        "if _anos_vu:\n"
        "    _ano_opts_vu = [\"Todos os Anos\"] + _anos_vu\n"
        "    ano_vu = st.selectbox(\n"
        "        \"📅 Filtrar por Ano\",\n"
        "        _ano_opts_vu,\n"
        "        index=0,\n"
        "        key=\"filtro_ano_vu\",\n"
        "        help=\"Filtra os KPIs consolidados pelo ano selecionado.\",\n"
        "    )\n"
        "    if ano_vu != \"Todos os Anos\" and _df_srv_vu is not None:\n"
        "        _df_srv_vu = _df_srv_vu[_df_srv_vu['ano'].astype(str) == str(ano_vu)]\n"
        "        all_data['servidores']['dados'] = _df_srv_vu\n"
        "else:\n"
        "    ano_vu = \"Todos os Anos\"\n"
    )

    changes = [
        (
            "# =========================\n"
            "# KPIs CONSOLIDADOS\n"
            "# =========================",

            filtro_block +
            "\n# =========================\n"
            "# KPIs CONSOLIDADOS\n"
            "# =========================",
        ),
    ]

    ok = patch(path, changes)
    print(f"  {'✅' if ok else '⚠️  sem mudanças'} {path.name}")


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("🔧 Aplicando filtro de ano nas páginas...\n")
    patch_servidores()
    patch_saude()
    patch_autonomia()
    patch_visao_unificada()
    print("\n✅ Pronto! Reinicie o Streamlit para ver as mudanças:")
    print("   streamlit run app.py")
