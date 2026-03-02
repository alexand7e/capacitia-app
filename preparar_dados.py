"""
Script de preparação: XLSX → CSV
Converte o arquivo capacitia-dados.xlsx para o formato esperado pelo pipeline
(src/process_csv_to_parquet.py).

Uso:
    python preparar_dados.py --input capacitia-dados.xlsx --ano 2026
    python preparar_dados.py --input capacitia-dados.xlsx --ano 2025
    python preparar_dados.py --input capacitia-dados.xlsx --ano todos

Saída:
    .data/raw/dados_gerais_capacitia.csv
"""

import pandas as pd
import argparse
from pathlib import Path
import sys

# ============================================================
# CONFIGURAÇÕES
# ============================================================

# Linha onde está o cabeçalho real (0-indexed)
HEADER_ROW = 6

# Mapeamento: nome da coluna no Excel → nome esperado pelo pipeline
# Ambos os anos têm as mesmas colunas, mas o pipeline espera ORGAO EXTERNO
# que não existe no Excel — será inferido automaticamente
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

# Órgãos considerados externos (fora do governo estadual do Piauí)
# Ajuste esta lista conforme necessário
ORGAOS_EXTERNOS = {
    "MPPI", "MP-PI", "MPE-PI",
    "PRF",
    "CÂMARA MUNICIPAL DE TERESINA", "CAMARA MUNICIPAL DE TERESINA",
    "DETRAN", "DETRAN-PI", "DETRAN/PI",
    "TRE", "TRF", "TRT",
    "POLÍCIA FEDERAL", "POLICIA FEDERAL",
    "IBAMA", "INCRA",
    "PREFEITURA", "PREFEITURA DE TERESINA",
}

# ============================================================
# FUNÇÕES
# ============================================================

def ler_aba(caminho: Path, aba: str) -> pd.DataFrame:
    """Lê uma aba do XLSX pulando o cabeçalho institucional."""
    df = pd.read_excel(caminho, sheet_name=aba, header=HEADER_ROW, dtype=str)
    df = df.fillna("")
    # Remover linhas completamente vazias
    df = df[df.apply(lambda r: r.str.strip().ne("").any(), axis=1)]
    # Remover linhas de totais/rodapé
    df = df[~df.iloc[:, 0].str.upper().str.contains("TOTAL|SUBTOTAL", na=False)]
    # Limpar espaços em todos os campos de texto
    df = df.apply(lambda col: col.str.strip() if col.dtype == object else col)
    print(f"  [{aba}] {len(df)} registros lidos.")
    return df


def inferir_orgao_externo(df: pd.DataFrame) -> pd.Series:
    """
    Infere a coluna ÓRGÃO EXTERNO com base no campo ÓRGÃO.
    Retorna uma Series com 'Sim' ou 'Não'.
    """
    orgao = df["ÓRGÃO"].str.strip().str.upper()
    return orgao.isin(ORGAOS_EXTERNOS).map({True: "Sim", False: "Não"})


def padronizar(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que todas as colunas esperadas existem e estão na ordem certa."""
    # Renomear conforme mapeamento (lida com variações de espaço/acento)
    df = df.rename(columns=lambda c: c.strip())

    # Verificar colunas faltantes
    faltando = [c for c in COLUNAS_MAP.keys() if c not in df.columns]
    if faltando:
        print(f"  AVISO: Colunas não encontradas no Excel: {faltando}")
        for c in faltando:
            df[c] = ""

    # Normalizar campo FORMATO (remove espaços extras, padroniza capitalização)
    if "FORMATO" in df.columns:
        df["FORMATO"] = df["FORMATO"].str.strip()

    # Adicionar coluna ÓRGÃO EXTERNO (não existe no Excel, inferida)
    df.insert(2, "ÓRGÃO EXTERNO", inferir_orgao_externo(df))

    # Selecionar e reordenar colunas na ordem esperada pelo pipeline
    ordem_final = [
        "EVENTO", "FORMATO", "ÓRGÃO EXTERNO", "EIXO", "LOCAL DE REALIZAÇÃO",
        "NOME", "CARGO", "CARGO OUTROS", "ÓRGÃO", "ÓRGÃO OUTROS",
        "VÍNCULO", "VÍNCULO OUTROS", "CERTIFICADO", "CARGO DE GESTÃO", "SERVIDOR DO ESTADO"
    ]
    df = df[[c for c in ordem_final if c in df.columns]]

    return df


def salvar_csv(df: pd.DataFrame, destino: Path):
    """Salva o DataFrame como CSV no formato esperado pelo pipeline."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False, sep=";", encoding="utf-8")
    print(f"\n✅ CSV salvo em: {destino}")
    print(f"   Total de registros: {len(df)}")
    print(f"   Colunas: {list(df.columns)}")


def resumo(df: pd.DataFrame):
    """Imprime um resumo dos dados preparados."""
    print("\n📊 Resumo dos dados:")
    print(f"   Eventos únicos:   {df['EVENTO'].nunique()}")
    print(f"   Órgãos únicos:    {df['ÓRGÃO'].nunique()}")
    print(f"   Órgãos externos:  {(df['ÓRGÃO EXTERNO'] == 'Sim').sum()} registros")
    print(f"   Certificados Sim: {(df['CERTIFICADO'].str.strip() == 'Sim').sum()}")
    print(f"   Certificados Não: {(df['CERTIFICADO'].str.strip() == 'Não').sum()}")
    
    print("\n   Registros por FORMATO:")
    for fmt, cnt in df["FORMATO"].value_counts().items():
        print(f"     {fmt}: {cnt}")

    print("\n   Órgãos marcados como EXTERNOS:")
    externos = df[df["ÓRGÃO EXTERNO"] == "Sim"]["ÓRGÃO"].value_counts()
    if externos.empty:
        print("     (nenhum — revise a lista ORGAOS_EXTERNOS no script)")
    else:
        for org, cnt in externos.items():
            print(f"     {org}: {cnt}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Prepara XLSX do CapacitIA para CSV do pipeline.")
    parser.add_argument("--input",  required=True,  help="Caminho do arquivo XLSX")
    parser.add_argument("--ano",    default="todos", help="Ano a processar: 2025, 2026 ou todos")
    parser.add_argument("--output", default=".data/raw/dados_gerais_capacitia.csv",
                        help="Caminho de saída do CSV")
    args = parser.parse_args()

    caminho = Path(args.input)
    if not caminho.exists():
        print(f"❌ Arquivo não encontrado: {caminho}")
        sys.exit(1)

    print(f"📂 Lendo: {caminho}")

    # Determinar quais abas processar
    if args.ano == "todos":
        abas = ["2025 DADOS", "2026 DADOS"]
    elif args.ano == "2025":
        abas = ["2025 DADOS"]
    elif args.ano == "2026":
        abas = ["2026 DADOS"]
    else:
        print(f"❌ Ano inválido: {args.ano}. Use 2025, 2026 ou todos.")
        sys.exit(1)

    frames = []
    for aba in abas:
        print(f"\n📋 Processando aba: {aba}")
        df = ler_aba(caminho, aba)
        df = padronizar(df)
        frames.append(df)

    df_final = pd.concat(frames, ignore_index=True)

    resumo(df_final)
    salvar_csv(df_final, Path(args.output))

    print("\n✅ Pronto! Próximos passos:")
    print("   1. python src\\process_csv_to_parquet.py")
    print("   2. python src\\verify_results.py")
    print("   3. streamlit run app.py")


if __name__ == "__main__":
    main()
