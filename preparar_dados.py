"""
Script de preparação: CSV ou XLSX → CSV padronizado para o pipeline

Uso com CSV (dados já existentes):
    uv run preparar_dados.py --input dados_gerais_capacitia.csv --ano 2026
    uv run preparar_dados.py --input .data/raw/dados_gerais_capacitia.csv --ano 2025

Uso com XLSX (múltiplos anos em abas separadas):
    uv run preparar_dados.py --input capacitia-dados.xlsx --ano todos
    uv run preparar_dados.py --input capacitia-dados.xlsx --ano 2026

Saída:
    .data/raw/dados_gerais_capacitia.csv  (sobrescreve com coluna ANO adicionada)
"""

import pandas as pd
import argparse
from pathlib import Path
import sys
import re

# ============================================================
# CONFIGURAÇÕES
# ============================================================

HEADER_ROW = 6  # linha do cabeçalho real no XLSX (0-indexed)

COLUNAS_MAP = {
    "EVENTO":              "EVENTO",
    "FORMATO":             "FORMATO",
    "EIXO":                "EIXO",
    "LOCAL DE REALIZAÇÃO": "LOCAL DE REALIZAÇÃO",
    "NOME":                "NOME",
    "CARGO":               "CARGO",
    "CARGO OUTROS":        "CARGO OUTROS",
    "ÓRGÃO":               "ÓRGÃO",
    "ÓRGÃO OUTROS":        "ÓRGÃO OUTROS",
    "VÍNCULO":             "VÍNCULO",
    "VÍNCULO OUTROS":      "VÍNCULO OUTROS",
    "CERTIFICADO":         "CERTIFICADO",
    "CARGO DE GESTÃO":     "CARGO DE GESTÃO",
    "SERVIDOR DO ESTADO":  "SERVIDOR DO ESTADO",
}

ORGAOS_EXTERNOS = {
    "MPPI", "MP-PI", "MPE-PI", "PRF",
    "CÂMARA MUNICIPAL DE TERESINA", "CAMARA MUNICIPAL DE TERESINA",
    "DETRAN", "DETRAN-PI", "DETRAN/PI",
    "TRE", "TRF", "TRT",
    "POLÍCIA FEDERAL", "POLICIA FEDERAL",
    "IBAMA", "INCRA",
    "PREFEITURA", "PREFEITURA DE TERESINA",
}

# ============================================================
# UTILITÁRIOS
# ============================================================

def _resolve_path(input_arg: str) -> Path:
    """Tenta localizar o arquivo em múltiplos caminhos."""
    candidates = [
        Path(input_arg),
        Path(".data") / "raw" / Path(input_arg).name,
        Path(__file__).parent / input_arg,
        Path(__file__).parent / ".data" / "raw" / Path(input_arg).name,
    ]
    for p in candidates:
        if p.exists():
            return p
    return Path(input_arg)  # retorna original para exibir erro correto


def _detect_sep(filepath: Path) -> str:
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
    return ";" if first_line.count(";") > first_line.count(",") else ","


def _infer_year(event_name: str) -> str:
    m = re.search(r"(202\d)", str(event_name))
    return m.group(1) if m else ""


def _inferir_orgao_externo(orgao_series: pd.Series) -> pd.Series:
    return orgao_series.str.strip().str.upper().isin(ORGAOS_EXTERNOS).map({True: "Sim", False: "Não"})


# ============================================================
# LEITORES
# ============================================================

def ler_csv(caminho: Path, ano_fixo: str) -> pd.DataFrame:
    """Lê CSV existente e garante a coluna ANO."""
    sep = _detect_sep(caminho)
    print(f"  Separador detectado: '{sep}'")

    df = pd.read_csv(caminho, sep=sep, dtype=str, encoding="utf-8", engine="python")
    df = df.fillna("")
    df.columns = df.columns.str.strip()

    # Detectar e pular cabeçalho institucional (quando CSV vem direto do relatório)
    primeira_col = str(df.columns[0]).upper()
    if "GOVERNO" in primeira_col or "PIAUÍ" in primeira_col or "PIAUI" in primeira_col:
        print("  Detectado cabeçalho institucional — buscando linha de colunas reais...")
        for i, row in df.iterrows():
            vals = [str(v).strip().upper() for v in row.values]
            if "EVENTO" in vals and "FORMATO" in vals:
                df.columns = [str(v).strip() for v in df.iloc[i].values]
                df = df.iloc[i + 1:].reset_index(drop=True).fillna("")
                break

    # Limpar linhas vazias e de total
    df = df[df.apply(lambda r: r.astype(str).str.strip().ne("").any(), axis=1)]
    df = df[~df.iloc[:, 0].astype(str).str.upper().str.contains("TOTAL|SUBTOTAL", na=False)]
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)

    print(f"  {len(df)} registros após limpeza.")

    # --- Determinar ANO ---
    if ano_fixo and ano_fixo not in ("todos", "inferir"):
        df["ANO"] = ano_fixo
        print(f"  ANO fixado: {ano_fixo}")
    elif "ANO" in df.columns:
        print(f"  Coluna ANO já presente: {sorted(df['ANO'].dropna().unique().tolist())}")
    else:
        evento_col = next((c for c in df.columns if c.upper() == "EVENTO"), None)
        if evento_col:
            df["ANO"] = df[evento_col].apply(_infer_year)
            contagem = df["ANO"].value_counts().to_dict()
            sem_ano  = (df["ANO"] == "").sum()
            print(f"  Anos inferidos dos eventos: {contagem}")
            if sem_ano:
                print(f"  ⚠️  {sem_ano} registros sem ano detectado → usando '2025'")
                df.loc[df["ANO"] == "", "ANO"] = "2025"
        else:
            df["ANO"] = "2025"
            print("  ⚠️  Evento não encontrado — usando '2025' como padrão.")

    return df


def ler_aba_xlsx(caminho: Path, aba: str, ano_str: str) -> pd.DataFrame:
    """Lê uma aba do XLSX e adiciona coluna ANO."""
    df = pd.read_excel(caminho, sheet_name=aba, header=HEADER_ROW, dtype=str)
    df = df.fillna("")
    df = df[df.apply(lambda r: r.astype(str).str.strip().ne("").any(), axis=1)]
    df = df[~df.iloc[:, 0].astype(str).str.upper().str.contains("TOTAL|SUBTOTAL", na=False)]
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)
    df["ANO"] = ano_str
    print(f"  [{aba}] {len(df)} registros lidos → ANO={ano_str}")
    return df


# ============================================================
# PADRONIZAÇÃO
# ============================================================

def padronizar(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza colunas, adiciona ÓRGÃO EXTERNO e reordena."""
    df = df.rename(columns=lambda c: str(c).strip())

    faltando = [c for c in COLUNAS_MAP if c not in df.columns]
    if faltando:
        print(f"  ⚠️  Colunas ausentes (serão criadas vazias): {faltando}")
        for c in faltando:
            df[c] = ""

    if "FORMATO" in df.columns:
        df["FORMATO"] = df["FORMATO"].str.strip()

    # ÓRGÃO EXTERNO: inferir se não existir
    if "ÓRGÃO EXTERNO" not in df.columns:
        orgao_col = next(
            (c for c in df.columns if "ÓRGÃO" in c.upper() and "OUTRO" not in c.upper()),
            None,
        )
        df["ÓRGÃO EXTERNO"] = (
            _inferir_orgao_externo(df[orgao_col]) if orgao_col else "Não"
        )

    ordem = [
        "ANO", "EVENTO", "FORMATO", "ÓRGÃO EXTERNO", "EIXO", "LOCAL DE REALIZAÇÃO",
        "NOME", "CARGO", "CARGO OUTROS", "ÓRGÃO", "ÓRGÃO OUTROS",
        "VÍNCULO", "VÍNCULO OUTROS", "CERTIFICADO", "CARGO DE GESTÃO", "SERVIDOR DO ESTADO",
    ]
    return df[[c for c in ordem if c in df.columns]]


# ============================================================
# SAÍDA E RESUMO
# ============================================================

def salvar_csv(df: pd.DataFrame, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, sep=";", encoding="utf-8")
    print(f"\n✅ CSV salvo em : {destino}")
    print(f"   Registros    : {len(df)}")
    print(f"   Colunas      : {list(df.columns)}")


def resumo(df: pd.DataFrame):
    print("\n📊 Resumo:")
    anos = sorted(df["ANO"].unique()) if "ANO" in df.columns else ["?"]
    for ano in anos:
        sub  = df[df["ANO"] == ano] if "ANO" in df.columns else df
        cert = (sub.get("CERTIFICADO", pd.Series()).str.strip() == "Sim").sum()
        taxa = cert / len(sub) * 100 if len(sub) else 0
        print(f"   {ano}: {len(sub):>5} inscritos | {cert:>4} certificados | {taxa:.1f}%")

    ev_col  = next((c for c in df.columns if c.upper() == "EVENTO"), None)
    org_col = next((c for c in df.columns if c.upper() == "ÓRGÃO" and "OUTRO" not in c.upper()), None)
    if ev_col:
        print(f"   Eventos únicos : {df[ev_col].nunique()}")
    if org_col:
        externos = df[df.get("ÓRGÃO EXTERNO", pd.Series("Não", index=df.index)) == "Sim"][org_col].value_counts()
        print(f"   Órgãos externos: {len(externos)}")
        for org, cnt in externos.head(8).items():
            print(f"     • {org}: {cnt}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Prepara CSV ou XLSX do CapacitIA para o pipeline.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--input", required=True,
        help="Arquivo de entrada (.csv ou .xlsx). Pode ser apenas o nome do arquivo\n"
             "se ele estiver em .data/raw/",
    )
    parser.add_argument(
        "--ano", default="inferir",
        help=(
            "Ano dos dados:\n"
            "  2025    → marca todos como 2025\n"
            "  2026    → marca todos como 2026\n"
            "  todos   → lê abas '2025 DADOS' e '2026 DADOS' (somente XLSX)\n"
            "  inferir → extrai o ano do nome do evento (padrão)"
        ),
    )
    parser.add_argument(
        "--output", default=".data/raw/dados_gerais_capacitia.csv",
        help="Destino do CSV (padrão: .data/raw/dados_gerais_capacitia.csv)",
    )
    args = parser.parse_args()

    caminho = _resolve_path(args.input)
    if not caminho.exists():
        print(f"❌ Arquivo não encontrado: '{args.input}'")
        print("   Caminhos tentados:")
        for p in [
            Path(args.input),
            Path(".data") / "raw" / Path(args.input).name,
        ]:
            print(f"     {p.resolve()}  {'✓' if p.exists() else '✗'}")
        sys.exit(1)

    sufixo = caminho.suffix.lower()
    print(f"📂 Arquivo: {caminho.resolve()}  (tipo: {sufixo})")

    frames = []

    if sufixo == ".csv":
        ano_param = "inferir" if args.ano == "todos" else args.ano
        if args.ano == "todos":
            print("⚠️  --ano todos é para XLSX. Inferindo ano automaticamente do CSV...")
        df = ler_csv(caminho, ano_param)
        frames.append(padronizar(df))

    elif sufixo in (".xlsx", ".xls"):
        abas_anos = (
            [("2025 DADOS", "2025"), ("2026 DADOS", "2026")]
            if args.ano in ("todos", "inferir")
            else [(f"{args.ano} DADOS", args.ano)]
        )
        for aba, ano_str in abas_anos:
            try:
                print(f"\n📋 Processando aba: '{aba}'")
                df_aba = ler_aba_xlsx(caminho, aba, ano_str)
                frames.append(padronizar(df_aba))
            except Exception as e:
                print(f"  ⚠️  Aba '{aba}' ignorada: {e}")
        if not frames:
            print("❌ Nenhuma aba processada com sucesso.")
            sys.exit(1)
    else:
        print(f"❌ Formato não suportado: '{sufixo}'. Use .csv ou .xlsx")
        sys.exit(1)

    df_final = pd.concat(frames, ignore_index=True)
    resumo(df_final)
    salvar_csv(df_final, Path(args.output))

    print("\n✅ Próximos passos:")
    print("   python src/process_csv_to_parquet.py")
    print("   streamlit run app.py")


if __name__ == "__main__":
    main()
