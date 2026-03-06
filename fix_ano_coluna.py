"""
fix_ano_coluna.py
-----------------
Corrige parquets já gerados que não têm a coluna 'ano',
inferindo o ano a partir do nome do evento (ex.: "2º Curso ... 2026").
Também regenera os arquivos de evolução anual.

Execute na raiz do projeto:
    python fix_ano_coluna.py

Não precisa rodar preparar_dados.py nem process_csv_to_parquet.py novamente.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

PROCESSED = Path(".data/processed")


# ══════════════════════════════════════════════════════════════════
# UTILITÁRIOS
# ══════════════════════════════════════════════════════════════════

# Mapa manual: prefixo do evento → ano
# Adicione entradas aqui se a inferência automática falhar
EVENTO_ANO_MAP: dict[str, str] = {
    # ex.: "1º Masterclass": "2025",
}

# Padrão para encontrar 4 dígitos de ano no nome do evento
_RE_ANO = re.compile(r"\b(202\d)\b")

# Palavras-chave que aparecem em eventos de cada ciclo
# (só usado como fallback se não houver 4 dígitos no nome)
_KEYWORDS_2025 = {"capacitia i", "1ª edição", "primeiro ciclo"}
_KEYWORDS_2026 = {"capacitia ii", "2ª edição", "segundo ciclo"}


def infer_year(event_name: str) -> str:
    """
    Tenta extrair o ano do nome do evento usando 3 estratégias:
    1. Mapa manual (EVENTO_ANO_MAP)
    2. Regex: encontra '202x' no texto
    3. Palavras-chave (fallback)
    Retorna '2025' se nenhuma estratégia funcionar.
    """
    s = str(event_name).strip()

    # 1. mapa manual
    for prefix, ano in EVENTO_ANO_MAP.items():
        if s.startswith(prefix):
            return ano

    # 2. regex
    m = _RE_ANO.search(s)
    if m:
        return m.group(1)

    # 3. palavras-chave
    sl = s.lower()
    if any(kw in sl for kw in _KEYWORDS_2026):
        return "2026"
    if any(kw in sl for kw in _KEYWORDS_2025):
        return "2025"

    return "2025"


# ══════════════════════════════════════════════════════════════════
# PASSO 1 — adicionar coluna 'ano' nos parquets principais
# ══════════════════════════════════════════════════════════════════

def fix_dados():
    path = PROCESSED / "dados.parquet"
    df = pd.read_parquet(path)

    if "ano" in df.columns and df["ano"].ne("").all():
        anos = sorted(df["ano"].dropna().unique())
        print(f"  dados.parquet já tem coluna 'ano': {anos}")
        return df

    print("  Inferindo 'ano' a partir do nome do evento...")
    df["ano"] = df["evento"].apply(infer_year)

    # Mover 'ano' para primeira coluna
    cols = ["ano"] + [c for c in df.columns if c != "ano"]
    df = df[cols]

    df.to_parquet(path, index=False)
    dist = df["ano"].value_counts().sort_index().to_dict()
    print(f"  ✅ dados.parquet atualizado — distribuição: {dist}")
    return df


def fix_visao_aberta():
    path = PROCESSED / "visao_aberta.parquet"
    df = pd.read_parquet(path)

    if "ano" in df.columns and df["ano"].ne("").all():
        print(f"  visao_aberta.parquet já tem 'ano'.")
        return df

    print("  Inferindo 'ano' em visao_aberta...")
    df["ano"] = df["evento"].apply(infer_year)
    cols = ["ano"] + [c for c in df.columns if c != "ano"]
    df = df[cols]
    df.to_parquet(path, index=False)
    print(f"  ✅ visao_aberta.parquet atualizado.")
    return df


def fix_secretarias(df_dados: pd.DataFrame):
    """Recria secretarias.parquet agrupado por ano + órgão."""
    path = PROCESSED / "secretarias.parquet"

    filtro = df_dados["orgao"].astype(str).str.strip()
    df_f = df_dados[~filtro.str.lower().isin(["outro", "outros", ""])].copy()

    secret = df_f.groupby(["ano", "orgao"]).agg(
        n_inscritos=("nome", "count"),
        n_certificados=("certificado", lambda x: (x == "Sim").sum()),
        n_turmas=("evento", "nunique"),
    ).reset_index()
    secret["n_evasao"] = secret["n_inscritos"] - secret["n_certificados"]
    secret = secret.rename(columns={"orgao": "secretaria_orgao"})
    secret.to_parquet(path, index=False)
    print(f"  ✅ secretarias.parquet recriado com 'ano'.")
    return secret


def fix_cargos(df_dados: pd.DataFrame):
    path = PROCESSED / "cargos.parquet"
    filtro = df_dados["cargo"].astype(str).str.strip().str.lower()
    df_c = df_dados[~filtro.isin(["", "outro", "outros"])].copy()

    cargo_gestao_col = "cargo_gestao" if "cargo_gestao" in df_c.columns else None
    servidor_col = "servidor_estado" if "servidor_estado" in df_c.columns else None

    agg = {"nome": "count", "evento": "nunique"}
    if cargo_gestao_col:
        agg[cargo_gestao_col] = lambda x: (x == "Sim").sum()
    if servidor_col:
        agg[servidor_col] = lambda x: (x == "Sim").sum()

    cargos = df_c.groupby(["ano", "cargo", "orgao"]).agg(**{
        "total_inscritos": pd.NamedAgg("nome", "count"),
        "n_turmas":        pd.NamedAgg("evento", "nunique"),
        **({"n_gestores": pd.NamedAgg(cargo_gestao_col, lambda x: (x == "Sim").sum())} if cargo_gestao_col else {}),
        **({"n_servidores_estado": pd.NamedAgg(servidor_col, lambda x: (x == "Sim").sum())} if servidor_col else {}),
    }).reset_index()
    cargos.to_parquet(path, index=False)
    print(f"  ✅ cargos.parquet recriado com 'ano'.")


def fix_orgaos_parceiros(df_dados: pd.DataFrame):
    path = PROCESSED / "orgaos_parceiros.parquet"
    if "orgao_externo" not in df_dados.columns:
        print("  ⚠️  orgao_externo não encontrado — pulando orgaos_parceiros.")
        return

    df_p = df_dados[df_dados["orgao_externo"].astype(str).str.strip().str.upper() == "SIM"].copy()
    if df_p.empty:
        print("  ⚠️  Nenhum órgão externo encontrado.")
        return

    parc = df_p.groupby(["ano", "orgao"]).agg(
        n_inscritos=("nome", "count"),
        n_certificados=("certificado", lambda x: (x.str.strip().str.upper() == "SIM").sum()),
        n_turmas=("evento", "nunique"),
        formatos=("formato", lambda x: ", ".join(x.unique().astype(str))),
        eixos=("eixo", lambda x: ", ".join(x.unique().astype(str))),
    ).reset_index()
    parc["taxa_certificacao"] = (parc["n_certificados"] / parc["n_inscritos"] * 100).round(2)
    parc = parc.rename(columns={"orgao": "orgao_parceiro"})
    parc.to_parquet(path, index=False)
    print(f"  ✅ orgaos_parceiros.parquet recriado com 'ano'.")


# ══════════════════════════════════════════════════════════════════
# PASSO 2 — gerar arquivos de evolução anual
# ══════════════════════════════════════════════════════════════════

def gerar_evolucao(df: pd.DataFrame):
    print("\n📈 Gerando arquivos de evolução anual...")

    # ── geral ──────────────────────────────────────────────────────
    geral = df.groupby("ano").agg(
        total_inscritos   = ("nome", "count"),
        total_certificados= ("certificado", lambda x: (x == "Sim").sum()),
        total_eventos     = ("evento", "nunique"),
        total_orgaos      = ("orgao", "nunique"),
    ).reset_index().sort_values("ano")

    geral["taxa_certificacao"] = (
        geral["total_certificados"] / geral["total_inscritos"] * 100
    ).round(2)
    geral["taxa_evasao"] = (
        (geral["total_inscritos"] - geral["total_certificados"])
        / geral["total_inscritos"] * 100
    ).round(2)
    for col in ["total_inscritos", "total_certificados", "total_eventos", "total_orgaos"]:
        geral[f"{col}_crescimento_pct"] = geral[col].pct_change() * 100

    _save(geral, "evolucao_anual_geral")

    # ── por formato ────────────────────────────────────────────────
    fmt = df.groupby(["ano", "formato"]).agg(
        n_inscritos   = ("nome", "count"),
        n_certificados= ("certificado", lambda x: (x == "Sim").sum()),
        n_eventos     = ("evento", "nunique"),
    ).reset_index()
    fmt["taxa_certificacao"] = (fmt["n_certificados"] / fmt["n_inscritos"] * 100).round(2)
    _save(fmt, "evolucao_anual_formato")

    # ── por órgão ──────────────────────────────────────────────────
    filtro = df["orgao"].astype(str).str.strip()
    df_org = df[~filtro.str.lower().isin(["outro", "outros", ""])].copy()
    org = df_org.groupby(["ano", "orgao"]).agg(
        n_inscritos   = ("nome", "count"),
        n_certificados= ("certificado", lambda x: (x == "Sim").sum()),
    ).reset_index()
    org["taxa_certificacao"] = (org["n_certificados"] / org["n_inscritos"] * 100).round(2)
    _save(org, "evolucao_anual_orgao")

    # ── por cargo ──────────────────────────────────────────────────
    filtro_c = df["cargo"].astype(str).str.strip().str.lower()
    df_c = df[~filtro_c.isin(["", "outro", "outros"])].copy()
    cargo = df_c.groupby(["ano", "cargo"]).agg(
        n_inscritos   = ("nome", "count"),
        n_certificados= ("certificado", lambda x: (x == "Sim").sum()),
    ).reset_index()
    _save(cargo, "evolucao_anual_cargo")

    # ── por eixo ───────────────────────────────────────────────────
    eixo = df.groupby(["ano", "eixo"]).agg(
        n_inscritos   = ("nome", "count"),
        n_certificados= ("certificado", lambda x: (x == "Sim").sum()),
    ).reset_index()
    _save(eixo, "evolucao_anual_eixo")

    # Resumo no terminal
    print("\n  Resumo por ano:")
    for _, row in geral.iterrows():
        cresc = row.get("total_inscritos_crescimento_pct", float("nan"))
        badge = f"▲ +{cresc:.1f}%" if cresc > 0 else (f"▼ {cresc:.1f}%" if not pd.isna(cresc) else "— 1º ano")
        print(
            f"    {row['ano']}: {int(row['total_inscritos']):>5} inscritos | "
            f"{int(row['total_certificados']):>4} certificados | "
            f"{row['taxa_certificacao']:.1f}% cert. | {badge}"
        )


def _save(df: pd.DataFrame, name: str):
    path = PROCESSED / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  ✅ {name}.parquet salvo ({len(df)} linhas)")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not PROCESSED.exists():
        print(f"❌ Pasta {PROCESSED} não encontrada.")
        print("   Execute primeiro: python src/process_csv_to_parquet.py")
        raise SystemExit(1)

    print("🔧 Corrigindo parquets existentes...\n")

    df_dados = fix_dados()
    fix_visao_aberta()
    fix_secretarias(df_dados)
    fix_cargos(df_dados)
    fix_orgaos_parceiros(df_dados)
    gerar_evolucao(df_dados)

    print("\n✅ Tudo pronto! Reinicie o Streamlit:")
    print("   streamlit run app.py")
