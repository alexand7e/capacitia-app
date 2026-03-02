from pathlib import Path
import sys

from process_csv_to_parquet import CapacitiaCSVProcessor
from processors.processor_autonomiadigital_inscricoes import process_autonomiadigital_inscricoes
from processors.processor_saude import process_saude
from processors.processors_autonomiadigital_avaliacoes import process_autonomiadigital_avaliacoes


RAW_PATH = Path(".data/raw")
PROCESSED_PATH = Path(".data/processed")


def process_all():
    print("=" * 60)
    print("Processando módulos do CapacitIA")
    print("=" * 60)

    erros = []

    processor = CapacitiaCSVProcessor()
    processor.process_all()

    try:
        df = process_autonomiadigital_inscricoes(RAW_PATH, PROCESSED_PATH)
        print(f"  Colunas: {list(df.columns)}\n")
    except FileNotFoundError as e:
        print(f"[inscricoes] ✗ Arquivo não encontrado: {e}\n")
        erros.append("inscricoes")
    except Exception as e:
        print(f"[inscricoes] ✗ Erro: {e}\n")
        erros.append("inscricoes")

    try:
        df = process_autonomiadigital_avaliacoes(RAW_PATH, PROCESSED_PATH)
        print(f"  Colunas: {list(df.columns)}\n")
    except FileNotFoundError as e:
        print(f"[avaliacoes] ✗ Arquivo não encontrado: {e}\n")
        erros.append("avaliacoes")
    except Exception as e:
        print(f"[avaliacoes] ✗ Erro: {e}\n")
        erros.append("avaliacoes")

    try:
        df = process_saude(RAW_PATH, PROCESSED_PATH)
        print(f"  Colunas: {list(df.columns)}\n")
    except FileNotFoundError as e:
        print(f"[saude] ✗ Arquivo não encontrado: {e}\n")
        erros.append("saude")
    except Exception as e:
        print(f"[saude] ✗ Erro: {e}\n")
        erros.append("saude")

    print("=" * 60)
    if erros:
        print(f"Concluído com erros em: {', '.join(erros)}")
        sys.exit(1)
    else:
        print("Todos os módulos processados com sucesso.")


def main():
    process_all()

if __name__ == "__main__":
    main()
