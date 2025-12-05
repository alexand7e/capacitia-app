#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# OBS: Funções de criação do parquet autonomiadigital_avaliacoes, autonomiadigital_inscricoes e saude precisam ser implementadas.
class CapacitiaCSVProcessor:

    def __init__(self, base_path: Path = None):
        script_dir = Path(__file__).resolve().parent

        # SOBE UMA PASTA (src → raiz do projeto)
        self.base_path = base_path or script_dir.parent

        self.raw_path = self.base_path / ".data" / "raw"
        self.processed_path = self.base_path / ".data" / "processed"

        self.processed_path.mkdir(parents=True, exist_ok=True)

    def load_csv_data(self) -> pd.DataFrame:
        csv_file = self.raw_path / "dados_gerais_capacitia.csv"

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV não encontrado: {csv_file}")

        logger.info(f"Lendo CSV: {csv_file}")

        # Detectar separador automaticamente
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()

        if first_line.count(";") > first_line.count(","):
            sep = ";"
        else:
            sep = ","

        logger.info(f"Separador detectado: '{sep}'")

        df = pd.read_csv(
            csv_file,
            sep=sep,
            dtype=str,
            encoding="utf-8",
            engine="python"
        )

        # Remover espaços e normalizar nomes de colunas
        df = df.fillna("")
        df.columns = (
            df.columns
            .str.lower()
            .str.strip()
            .str.replace(" ", "_")
            .str.replace("ç", "c")
            .str.replace("ã", "a")
            .str.replace("õ", "o")
            .str.replace("á", "a")
            .str.replace("é", "e")
            .str.replace("í", "i")
            .str.replace("ó", "o")
            .str.replace("ú", "u")
        )

        logger.info(f"CSV carregado com {len(df)} linhas e {len(df.columns)} colunas.")
        logger.info(f"Colunas detectadas: {list(df.columns)}")

        def _is_outros(s: str) -> bool:
            v = str(s).strip().lower()
            return v in {"outro", "outros"} or v == ""

        def _unify_pair(primary: pd.Series, outros: pd.Series) -> pd.Series:
            p = primary.astype(str).str.strip()
            o = outros.astype(str).str.strip()
            return np.where(p.str.lower().isin(["outro", "outros", ""]), o, p)

        if "orgao" in df.columns:
            outros_col = df["orgao_outros"] if "orgao_outros" in df.columns else pd.Series([""] * len(df))
            df["orgao"] = _unify_pair(df["orgao"], outros_col)
            df["orgao"] = df["orgao"].astype(str).str.strip()

        if "cargo" in df.columns:
            outros_col = df["cargo_outros"] if "cargo_outros" in df.columns else pd.Series([""] * len(df))
            df["cargo"] = _unify_pair(df["cargo"], outros_col)
            df["cargo"] = df["cargo"].astype(str).str.strip()

        if "vinculo" in df.columns:
            outros_col = df["vinculo_outros"] if "vinculo_outros" in df.columns else pd.Series([""] * len(df))
            df["vinculo"] = _unify_pair(df["vinculo"], outros_col)
            df["vinculo"] = df["vinculo"].astype(str).str.strip()

        # Padronização via config
        try:
            import src.config as cfg
        except Exception:
            import config as cfg

        if "orgao" in df.columns:
            df["orgao"] = df["orgao"].map(cfg.canonical_orgao)
        if "cargo" in df.columns:
            df["cargo"] = df["cargo"].map(cfg.canonical_cargo)
        if "vinculo" in df.columns:
            df["vinculo"] = df["vinculo"].map(cfg.canonical_vinculo)

        return df

    def create_df_dados(self, df):
        logger.info("Gerando df_dados...")

        df_dados = pd.DataFrame()

        df_dados["evento"] = df["evento"]
        df_dados["orgao_externo"] = df.get("orgao_externo", "")
        df_dados["formato"] = df["formato"]
        df_dados["eixo"] = df["eixo"]
        df_dados["local_realizacao"] = df["local_de_realizacao"]
        df_dados["nome"] = df["nome"]
        df_dados["cargo"] = df["cargo"]
        df_dados["orgao"] = df["orgao"]
        df_dados["vinculo"] = df["vinculo"]
        df_dados["certificado"] = df["certificado"]
        df_dados["cargo_gestao"] = df["cargo_de_gestao"]
        df_dados["servidor_estado"] = df["servidor_do_estado"]

        return df_dados

    def create_df_visao(self, df):
        logger.info("Gerando visao_aberta...")

        visao = df.groupby("evento").agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum())
        ).reset_index()

        # recuperar informações fixas do primeiro registro de cada evento
        base = df.drop_duplicates(subset=["evento"]).set_index("evento")

        visao["formato"] = visao["evento"].map(base["formato"])
        visao["eixo"] = visao["evento"].map(base["eixo"])
        visao["local_realizacao"] = visao["evento"].map(base["local_de_realizacao"])

        visao = visao[
            ["evento", "formato", "eixo", "local_realizacao",
             "n_inscritos", "n_certificados"]
        ]

        return visao

    def create_df_secretarias(self, df):
        logger.info("Gerando secretaria.parquet...")

        filtro = df["orgao"].astype(str).str.strip()
        df_filtrado = df[~filtro.str.lower().isin(["outro", "outros", ""])].copy()

        secret = df_filtrado.groupby("orgao").agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            n_turmas=("evento", "nunique"),
        ).reset_index()

        # Calcular evasão
        secret["n_evasao"] = secret["n_inscritos"] - secret["n_certificados"]

        # Renomear coluna final
        secret = secret.rename(columns={"orgao": "secretaria_orgao"})

        return secret

    def create_df_cargos(self, df):
        logger.info("Gerando cargos...")
        filtro_cargo = df["cargo"].astype(str).str.strip().str.lower()
        df_cargos_base = df[~filtro_cargo.isin(["", "outro", "outros"])].copy()

        cargos = df_cargos_base.groupby(["cargo", "orgao"]).agg(
            total_inscritos=("nome", "count"),
            n_gestores=("cargo_de_gestao", lambda x: (x == "Sim").sum()),
            n_servidores_estado=("servidor_do_estado", lambda x: (x == "Sim").sum()),
            n_turmas=("evento", "nunique"),
        ).reset_index()

        cargos["perc_gestores"] = (
            cargos["n_gestores"] / cargos["total_inscritos"] * 100
        ).round(2)

        cargos["perc_servidores"] = (
            cargos["n_servidores_estado"] / cargos["total_inscritos"] * 100
        ).round(2)

        cargos.columns = [
            "cargo", "orgao", "total_inscritos",
            "n_gestores", "n_servidores_estado",
            "n_turmas",
            "perc_gestores", "perc_servidores"
        ]

        return cargos

    def create_df_min(self, df):
        logger.info("Gerando ministrantes (simulados)...")

        eventos = df["evento"].unique()
        registros = []

        for ev in eventos:
            registros.append({
                "evento": ev,
                "ministrante": f"Ministrante {ev[:20]}",
                "carga_horaria": int(np.random.choice([4, 8, 16, 20, 40])),
                "tipo_ministrante": np.random.choice(["Interno", "Externo", "Convidado"]),
                "area_expertise": np.random.choice(["IA", "Gestao", "Tecnologia"]),
                "total_participantes": df[df["evento"] == ev].shape[0],
                "eixo": df[df["evento"] == ev]["eixo"].iloc[0],
                "local_realizacao": df[df["evento"] == ev]["local_de_realizacao"].iloc[0],
            })

        return pd.DataFrame(registros)

    def save_to_parquet(self, df, name):
        filepath = self.processed_path / f"{name}.parquet"
        df.to_parquet(filepath, index=False)
        logger.info(f"Arquivo salvo: {filepath}")

    def process_all(self):
        df = self.load_csv_data()

        df_dados = self.create_df_dados(df)
        self.save_to_parquet(df_dados, "dados")

        df_visao = self.create_df_visao(df)
        self.save_to_parquet(df_visao, "visao_aberta")

        df_cargos = self.create_df_cargos(df)
        self.save_to_parquet(df_cargos, "cargos")

        df_min = self.create_df_min(df)
        self.save_to_parquet(df_min, "ministrantes")

        df_secretarias = self.create_df_secretarias(df)
        self.save_to_parquet(df_secretarias, "secretarias")

        logger.info("Processamento concluído com sucesso!")


def main():
    processor = CapacitiaCSVProcessor()
    processor.process_all()

if __name__ == "__main__":
    main()
