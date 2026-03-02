from pathlib import Path
import pandas as pd


COLUNAS_AVALIACOES = {
    "Carimbo de data/hora": "data_avaliacao",
    "Gênero": "genero",
    "Idade": "idade",
    "Você aprendeu sobre as funções básicas do celular? (conectar a internet, configurar notificação, toque, fonte, instalar e desinstalar app)": "aprendeu_celular_basico",
    "Você aprendeu a usar o seu e-mail? (identificar seu e-mail, recuperar senha)": "aprendeu_email",
    "Você aprendeu a identificar sites confiáveis e se proteger de golpes virtuais, fake news?": "aprendeu_seguranca",
    "Você aprendeu  como a inteligência artificial pode te ajudar no dia a dia?": "aprendeu_ia",
    "Você aprendeu a usar o Gov.pi cidadão?": "aprendeu_govpi",
    "Você aprendeu a usar o Piauí Saúde Digital?": "aprendeu_saude_digital",
    "Você aprendeu a usar o BO fácil?": "aprendeu_bo_facil",
    "Quer registrar algo que você aprendeu a mais e não está destacado acima?": "aprendizado_extra",
    "Como você avalia esse evento?": "nota_evento",
    "O que você achou do conteúdo?": "nota_conteudo",
    "O que você achou do local do evento?": "nota_local",
    "Como você avalia o atendimento e o acolhimento do evento?": "nota_atendimento",
    "Deixe uma sugestão, elogio ou reclamação.": "sugestao",
}




def process_autonomiadigital_avaliacoes(raw_path: Path, processed_path: Path) -> pd.DataFrame:
    """
    Processa dados_avaliacoes_capacitia_autonomiadigital.csv
    → autonomiadigital_avaliacoes.parquet

    Remove dados sensíveis (nome, CPF, e-mail).
    Mantém avaliações, notas e dados demográficos.
    """
    csv_file = raw_path / "dados_avaliacoes_capacitia_autonomiadigital.csv"
    print(f"[avaliacoes] Lendo {csv_file}...")

    df = pd.read_csv(csv_file, sep=";", dtype=object, encoding="utf-8")

    # Limpar espaços
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Remover dados sensíveis
    colunas_sensiveis = [
        "Digite seu nome sem abreviar",
        "CPF",
        "Se tiver, informe seu e-mail",
    ]
    df = df.drop(columns=[c for c in colunas_sensiveis if c in df.columns])

    # Renomear colunas
    mapeamento = {k.strip(): v for k, v in COLUNAS_AVALIACOES.items()}
    df = df.rename(columns=mapeamento)

    # Padronizar data (formato do Google Forms: MM/DD/YYYY HH:MM:SS)
    if "data_avaliacao" in df.columns:
        df["data_avaliacao"] = pd.to_datetime(df["data_avaliacao"], format="%m/%d/%Y %H:%M:%S", errors="coerce")

    # Padronizar idade
    if "idade" in df.columns:
        df["idade"] = pd.to_numeric(df["idade"], errors="coerce")

    # Padronizar notas para numérico (1-5)
    colunas_nota = ["nota_evento", "nota_conteudo", "nota_local", "nota_atendimento"]
    for col in colunas_nota:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Padronizar colunas de aprendizado (Sim/Não → True/False)
    colunas_aprendizado = [
        "aprendeu_celular_basico", "aprendeu_email", "aprendeu_seguranca",
        "aprendeu_ia", "aprendeu_govpi", "aprendeu_saude_digital", "aprendeu_bo_facil",
    ]
    for col in colunas_aprendizado:
        if col in df.columns:
            df[col] = df[col].str.lower().map({"sim": True, "não": False, "nao": False})

    # Salvar
    processed_path.mkdir(parents=True, exist_ok=True)
    output = processed_path / "autonomiadigital_avaliacoes.parquet"
    df.to_parquet(output, index=False)
    print(f"[avaliacoes] ✓ {len(df)} registros → {output}")
    return df

