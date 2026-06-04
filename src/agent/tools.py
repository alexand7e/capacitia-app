import pandas as pd
from langchain_core.tools import tool
from pathlib import Path

from .config import PROCESSED_DIR

PROCESSED_DIR.joinpath


def _load():
    return pd.read_parquet(PROCESSED_DIR / "dados.parquet")


@tool
def query_data(
    metric: str = "inscritos",
    group_by: str | None = None,
    filters: dict | None = None,
) -> str:
    """Retorna contagem de inscritos, certificados ou taxa, opcionalmente agrupado e filtrado.

    Args:
        metric: 'inscritos', 'certificados', ou 'taxa'
        group_by: coluna para agrupar (ex: 'orgao', 'formato', 'ano', 'evento', 'cargo')
        filters: dicionário de filtros exatos (ex: {"ano": "2025", "orgao": "SEFAZ"})
    """
    df = _load()
    if filters:
        for col, val in filters.items():
            if col in df.columns:
                df = df[df[col].astype(str) == str(val)]

    if metric == "taxa":
        if group_by and group_by in df.columns:
            grp = df.groupby(group_by)
            results = []
            for name, g in grp:
                cert = (g["certificado"] == "Sim").sum()
                taxa = round(cert / len(g) * 100, 1) if len(g) else 0
                results.append(f"{name}: {cert} certificados de {len(g)} inscritos ({taxa}%)")
            return "\n".join(results) if results else "Nenhum dado encontrado."
        cert = (df["certificado"] == "Sim").sum()
        taxa = round(cert / len(df) * 100, 1) if len(df) else 0
        return f"{cert} certificados de {len(df)} inscritos ({taxa}%)"

    if group_by and group_by in df.columns:
        if metric == "certificados":
            grp = df[df["certificado"] == "Sim"].groupby(group_by).size()
        else:
            grp = df.groupby(group_by).size()
        grp = grp.sort_values(ascending=False)
        return grp.to_string()

    if metric == "certificados":
        val = (df["certificado"] == "Sim").sum()
    else:
        val = len(df)
    return str(val)


@tool
def compare_years(metric: str = "inscritos", group: str | None = None) -> str:
    """Compara uma métrica entre 2025 e 2026, opcionalmente agrupada.

    Args:
        metric: 'inscritos', 'certificados', ou 'taxa'
        group: coluna para desagregar (ex: 'orgao', 'formato')
    """
    df = _load()
    lines = []
    if group and group in df.columns:
        for name in df[group].unique():
            d25 = df[(df["ano"] == "2025") & (df[group] == name)]
            d26 = df[(df["ano"] == "2026") & (df[group] == name)]
            if metric == "certificados":
                v25 = (d25["certificado"] == "Sim").sum()
                v26 = (d26["certificado"] == "Sim").sum()
            elif metric == "taxa":
                v25 = round((d25["certificado"] == "Sim").sum() / len(d25) * 100, 1) if len(d25) else 0
                v26 = round((d26["certificado"] == "Sim").sum() / len(d26) * 100, 1) if len(d26) else 0
            else:
                v25 = len(d25)
                v26 = len(d26)
            if v25 or v26:
                delta = f"{((v26 - v25) / v25 * 100):+.1f}%" if v25 else "—"
                lines.append(f"{name}: {v25} → {v26} ({delta})")
    else:
        d25 = df[df["ano"] == "2025"]
        d26 = df[df["ano"] == "2026"]
        if metric == "certificados":
            v25 = (d25["certificado"] == "Sim").sum()
            v26 = (d26["certificado"] == "Sim").sum()
        elif metric == "taxa":
            v25 = round((d25["certificado"] == "Sim").sum() / len(d25) * 100, 1) if len(d25) else 0
            v26 = round((d26["certificado"] == "Sim").sum() / len(d26) * 100, 1) if len(d26) else 0
        else:
            v25 = len(d25)
            v26 = len(d26)
        delta = f"{((v26 - v25) / v25 * 100):+.1f}%" if v25 else "—"
        lines.append(f"Geral: {v25} → {v26} ({delta})")

    return "\n".join(lines) if lines else "Dados insuficientes para comparação."


@tool
def get_summary() -> str:
    """Retorna um resumo geral do CapacitIA Servidores."""
    df = _load()
    total = len(df)
    certificados = (df["certificado"] == "Sim").sum()
    taxa = round(certificados / total * 100, 1) if total else 0
    eventos = df["evento"].nunique()
    orgaos = df["orgao"].nunique()
    cargos = df["cargo"].nunique()
    anos = sorted(df["ano"].dropna().unique())

    partes = [
        f"Total de participantes: {total}",
        f"Total de certificados: {certificados} (taxa {taxa}%)",
        f"Eventos realizados: {eventos}",
        f"Secretarias/órgãos envolvidos: {orgaos}",
        f"Cargos distintos: {cargos}",
        f"Anos: {', '.join(anos)}",
    ]

    if len(anos) >= 2:
        a25 = len(df[df["ano"] == anos[0]])
        a26 = len(df[df["ano"] == anos[1]])
        delta = ((a26 - a25) / a25 * 100) if a25 else 0
        partes.append(f"Crescimento de inscritos: {a25} → {a26} ({delta:+.1f}%)")

    return "\n".join(partes)


@tool
def search_docs(query: str) -> str:
    """Busca informação textual nos documentos do ChromaDB sobre eventos, órgãos, cargos.

    Args:
        query: pergunta textual sobre os dados
    """
    from .vector_store import get_vector_store
    store = get_vector_store()
    results = store.similarity_search(query, k=5)
    if not results:
        return "Nenhum resultado encontrado."
    return "\n\n".join(r.page_content for r in results)
