"""Funções auxiliares para processamento de dados."""

import pandas as pd
import numpy as np
import unicodedata
import re

def fmt_int_br(n: int) -> str:
    """Formata número inteiro no padrão brasileiro."""
    return str(f"{int(n):,}").replace(",", ".")

def _col_like(df: pd.DataFrame, *keywords):
    """Retorna o nome da 1ª coluna cujo título contém todos os keywords (case-insensitive)."""
    up = {c: str(c).upper().replace("\xa0", " ") for c in df.columns}
    for c, name in up.items():
        if all(k.upper() in name for k in keywords):
            return c
    return None

def _normalize_org(s: str) -> str:
    """Normaliza nome de órgão removendo acentos e espaços."""
    s = "" if pd.isna(s) else str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s).strip().upper()
    return s

def drop_empty_labels(df: pd.DataFrame, col: str):
    """Remove linhas com labels vazios ou inválidos."""
    s = df[col].astype(str)
    mask = s.str.strip().ne("") & ~s.str.lower().isin(["nan", "none", "nat"])
    return df.loc[mask].copy()

def nz(df: pd.DataFrame, required_cols):
    """Remove linhas com NaN/±inf nas colunas exigidas."""
    clean = df.replace([np.inf, -np.inf], pd.NA)
    return clean.dropna(subset=required_cols)

def _parse_ptbr_number(x):
    """Parse número no formato brasileiro (1.234,56)."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return np.nan
    s = str(x).strip()
    s = s.replace("\xa0", " ").replace(" ", "")
    s = re.sub(r"[^\d,.\-]", "", s)
    if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return np.nan

def _find_header_row(df: pd.DataFrame) -> int:
    """Encontra a linha de cabeçalho em DataFrame de secretarias."""
    for i in range(min(15, len(df))):
        row_txt = " ".join([str(v).upper() for v in df.iloc[i].tolist()])
        if "SECRETARIA/ÓRGÃO" in row_txt and "INSCRITOS" in row_txt:
            return i
    return 0

def clean_secretarias(df_secretarias_raw: pd.DataFrame) -> pd.DataFrame:
    """Limpa e padroniza DataFrame de secretarias."""
    df = df_secretarias_raw.copy()
    
    # Verifica se já está no formato padronizado (Parquet)
    if 'secretaria_orgao' in df.columns:
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

    mask_meta = df.astype(str).apply(
        lambda s: s.str.upper().str.contains("ATIVIDADE/EVENTO|TOTAL GERAL|^TOTAL$", na=False)
    ).any(axis=1)
    df = df[~mask_meta].dropna(how="all").copy()

    col_ins = _col_like(df, "INSCRIT") or "Nº INSCRITOS"
    col_cer = _col_like(df, "CERTIFIC") or "Nº CERTIFICADOS"
    col_eva = _col_like(df, "EVAS") or "Nº EVASÃO"
    for col in [col_ins, col_cer, col_eva]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    org_cols = [c for c in df.columns if "SECRETARIA" in str(c).upper() or "ÓRGÃO" in str(c).upper()]
    if not org_cols:
        nome_org_col = df.columns[0]
    else:
        nome_org_col = org_cols[0]
    df[nome_org_col] = df[nome_org_col].astype(str).str.strip()

    df = df.rename(columns={
        nome_org_col: "SECRETARIA/ÓRGÃO",
        col_ins: "Nº INSCRITOS",
        col_cer: "Nº CERTIFICADOS",
        col_eva: "Nº EVASÃO"
    })
    return df[["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS","Nº EVASÃO"] if "Nº EVASÃO" in df.columns else ["SECRETARIA/ÓRGÃO","Nº INSCRITOS","Nº CERTIFICADOS"]]

