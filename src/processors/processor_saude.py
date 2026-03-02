from pathlib import Path
import pandas as pd

COLUNAS_SAUDE = {
    "Nº ": "numero",
    "Data": "data",
    "Lote": "lote",
}

def process_saude(raw_path: Path, processed_path: Path) -> pd.DataFrame:
    """
    Processa dados_capacitia_saude.csv
    → saude.parquet

    Remove dados sensíveis (nome, e-mail).
    Mantém número, data e lote de capacitação.
    """
    csv_file = raw_path / "dados_capacitia_saude.csv"
    print(f"[saude] Lendo {csv_file}...")

    df = pd.read_csv(csv_file, sep=";", dtype=object, encoding="utf-8")

    # Limpar espaços
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Remover colunas completamente vazias (Unnamed)
    df = df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Remover dados sensíveis
    colunas_sensiveis = ["Nome", "E-mail"]
    df = df.drop(columns=[c for c in colunas_sensiveis if c in df.columns])

    # Renomear colunas
    mapeamento = {k.strip(): v for k, v in COLUNAS_SAUDE.items()}
    df = df.rename(columns=mapeamento)

    # Padronizar número para inteiro
    if "numero" in df.columns:
        df["numero"] = pd.to_numeric(df["numero"], errors="coerce")

    # Padronizar lote: normalizar espaços
    if "lote" in df.columns:
        df["lote"] = df["lote"].str.strip()

    # Salvar
    processed_path.mkdir(parents=True, exist_ok=True)
    output = processed_path / "saude.parquet"
    df.to_parquet(output, index=False)
    print(f"[saude] ✓ {len(df)} registros → {output}")
    return df

