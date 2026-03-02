from pathlib import Path
import pandas as pd


COLUNAS_INSCRICOES = {
    "Carimbo de data/hora": "data_inscricao",
    "Gênero": "genero",
    "Idade": "idade",
    "Cidade": "cidade",
    "Bairro": "bairro",
    "Você é aposentado(a)?": "aposentado",
    "Você participa de qual projeto de extensão? ": "projeto_extensao",
    "Dentre esses temas, qual(is) você tem mais dificuldade": "temas_dificuldade",
}

def process_autonomiadigital_inscricoes(raw_path: Path, processed_path: Path) -> pd.DataFrame:
    """
    Processa dados_inscricoes_capacitia_autonomiadigital.csv
    → autonomiadigital_inscricoes.parquet

    Remove dados sensíveis (nome, CPF, telefone, e-mail).
    Mantém informações demográficas e de participação.
    """
    csv_file = raw_path / "dados_inscricoes_capacitia_autonomiadigital.csv"
    print(f"[inscricoes] Lendo {csv_file}...")

    df = pd.read_csv(csv_file, sep=";", dtype=object, encoding="utf-8")

    # Limpar espaços nas colunas e valores de texto
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Remover dados sensíveis antes de qualquer outra operação
    colunas_sensiveis = [
        "Digite seu nome sem abreviar",
        "CPF",
        "Telefone/Celular/WhatsApp",
        "E-mail (se houver)",
        "Autorizo o tratamento dos meus dados pessoais pela SIA nos termos da Lei nº 13.709/2018 (LGPD).",
        # Coluna de texto livre que pode conter dados pessoais
        "Caso você não seja de nenhum projeto citado acima. \n1. Diga de qual grupo você faz parte, se houver. \n2. Como soube do treinamento. \n3. Se inscrever para os dia 28 e 30 de outubro",
    ]
    df = df.drop(columns=[c for c in colunas_sensiveis if c in df.columns])

    # Renomear colunas usando o mapeamento (apenas as que existem)
    mapeamento = {k.strip(): v for k, v in COLUNAS_INSCRICOES.items()}
    df = df.rename(columns=mapeamento)

    # Padronizar coluna de data (formato do Google Forms: MM/DD/YYYY HH:MM:SS)
    if "data_inscricao" in df.columns:
        df["data_inscricao"] = pd.to_datetime(df["data_inscricao"], format="%m/%d/%Y %H:%M:%S", errors="coerce")

    # Padronizar idade para numérico
    if "idade" in df.columns:
        df["idade"] = pd.to_numeric(df["idade"], errors="coerce")

    # Padronizar coluna aposentado: Sim/Não → True/False
    if "aposentado" in df.columns:
        df["aposentado"] = df["aposentado"].str.lower().map({"sim": True, "não": False, "nao": False})

    # Salvar
    processed_path.mkdir(parents=True, exist_ok=True)
    output = processed_path / "autonomiadigital_inscricoes.parquet"
    df.to_parquet(output, index=False)
    print(f"[inscricoes] ✓ {len(df)} registros → {output}")
    return df

