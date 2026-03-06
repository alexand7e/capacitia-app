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


class CapacitiaCSVProcessor:

    def __init__(self, base_path: Path = None):
        script_dir = Path(__file__).resolve().parent
        self.base_path = base_path or script_dir.parent
        self.raw_path = self.base_path / ".data" / "raw"
        self.processed_path = self.base_path / ".data" / "processed"
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def load_csv_data(self) -> pd.DataFrame:
        csv_file = self.raw_path / "dados_gerais_capacitia.csv"

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV não encontrado: {csv_file}")

        logger.info(f"Lendo CSV: {csv_file}")

        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()

        sep = ";" if first_line.count(";") > first_line.count(",") else ","
        logger.info(f"Separador detectado: '{sep}'")

        df = pd.read_csv(csv_file, sep=sep, dtype=str, encoding="utf-8", engine="python")
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

        # --- Inferir ANO se não vier do CSV ---
        # O preparar_dados.py já injeta a coluna 'ano'.
        # Se vier de outra fonte sem essa coluna, tentamos inferir pelo nome do evento.
        if "ano" not in df.columns:
            logger.warning("Coluna 'ano' não encontrada — inferindo a partir do nome do evento.")
            df["ano"] = df.get("evento", pd.Series([""] * len(df))).apply(
                lambda ev: self._infer_year_from_event(str(ev))
            )

        # Garantir que ano seja string limpa
        df["ano"] = df["ano"].astype(str).str.strip()

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

    @staticmethod
    def _infer_year_from_event(event_name: str) -> str:
        """Tenta inferir o ano a partir do nome do evento (fallback)."""
        import re
        match = re.search(r"(202\d)", event_name)
        return match.group(1) if match else "2025"

    # ------------------------------------------------------------------
    # CRIAÇÃO DOS DataFrames
    # ------------------------------------------------------------------

    def create_df_dados(self, df):
        logger.info("Gerando df_dados...")
        df_dados = pd.DataFrame()
        df_dados["ano"] = df.get("ano", "2025")          # ← NOVO: coluna de ano
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

        visao = df.groupby(["ano", "evento"]).agg(   # ← NOVO: agrupa por ano + evento
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum())
        ).reset_index()

        base = df.drop_duplicates(subset=["evento"]).set_index("evento")
        visao["formato"] = visao["evento"].map(base["formato"])
        visao["eixo"] = visao["evento"].map(base["eixo"])
        visao["local_realizacao"] = visao["evento"].map(base["local_de_realizacao"])

        visao = visao[["ano", "evento", "formato", "eixo", "local_realizacao",
                        "n_inscritos", "n_certificados"]]
        return visao

    def create_df_secretarias(self, df):
        logger.info("Gerando secretaria.parquet...")

        filtro = df["orgao"].astype(str).str.strip()
        df_filtrado = df[~filtro.str.lower().isin(["outro", "outros", ""])].copy()

        secret = df_filtrado.groupby(["ano", "orgao"]).agg(   # ← NOVO: por ano + órgão
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            n_turmas=("evento", "nunique"),
        ).reset_index()

        secret["n_evasao"] = secret["n_inscritos"] - secret["n_certificados"]
        secret = secret.rename(columns={"orgao": "secretaria_orgao"})
        return secret

    def create_df_orgaos_parceiros(self, df):
        logger.info("Gerando orgaos_parceiros.parquet...")

        if "orgao_externo" not in df.columns:
            logger.warning("Coluna 'orgao_externo' não encontrada. Criando DataFrame vazio.")
            return pd.DataFrame(columns=["ano", "orgao_parceiro", "n_inscritos",
                                         "n_certificados", "n_turmas", "taxa_certificacao",
                                         "formatos", "eixos"])

        df_parceiros = df[df["orgao_externo"].astype(str).str.strip().str.upper() == "SIM"].copy()

        if len(df_parceiros) == 0:
            valores_unicos = df["orgao_externo"].astype(str).str.strip().str.upper().unique()
            logger.warning(f"Nenhum órgão parceiro encontrado. Valores únicos em 'orgao_externo': {valores_unicos}")
            return pd.DataFrame(columns=["ano", "orgao_parceiro", "n_inscritos",
                                         "n_certificados", "n_turmas", "taxa_certificacao",
                                         "formatos", "eixos"])

        parceiros = df_parceiros.groupby(["ano", "orgao"]).agg(   # ← NOVO: por ano + órgão
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x.astype(str).str.strip().str.upper() == "SIM").sum()),
            n_turmas=("evento", "nunique"),
            formatos=("formato", lambda x: ", ".join(x.unique().astype(str))),
            eixos=("eixo", lambda x: ", ".join(x.unique().astype(str))),
        ).reset_index()

        parceiros["taxa_certificacao"] = (
            (parceiros["n_certificados"] / parceiros["n_inscritos"] * 100).round(2)
        )
        parceiros = parceiros.rename(columns={"orgao": "orgao_parceiro"})
        parceiros = parceiros.sort_values(["ano", "n_inscritos"], ascending=[True, False])
        return parceiros

    def create_df_cargos(self, df):
        logger.info("Gerando cargos...")
        filtro_cargo = df["cargo"].astype(str).str.strip().str.lower()
        df_cargos_base = df[~filtro_cargo.isin(["", "outro", "outros"])].copy()

        cargos = df_cargos_base.groupby(["ano", "cargo", "orgao"]).agg(   # ← NOVO: por ano
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
        return cargos

    def create_df_min(self, df):
        logger.info("Gerando ministrantes (simulados)...")
        eventos = df["evento"].unique()
        registros = []
        for ev in eventos:
            ev_df = df[df["evento"] == ev]
            registros.append({
                "ano": ev_df["ano"].iloc[0] if "ano" in ev_df.columns else "2025",
                "evento": ev,
                "ministrante": f"Ministrante {ev[:20]}",
                "carga_horaria": int(np.random.choice([4, 8, 16, 20, 40])),
                "tipo_ministrante": np.random.choice(["Interno", "Externo", "Convidado"]),
                "area_expertise": np.random.choice(["IA", "Gestao", "Tecnologia"]),
                "total_participantes": ev_df.shape[0],
                "eixo": ev_df["eixo"].iloc[0],
                "local_realizacao": ev_df["local_de_realizacao"].iloc[0],
            })
        return pd.DataFrame(registros)

    def create_df_evolucao_anual(self, df):
        """
        NOVO: Cria DataFrame de evolução anual para a feature de linha do tempo.
        Agrega métricas-chave por ano para comparação histórica.
        """
        logger.info("Gerando evolucao_anual.parquet...")

        anos_disponiveis = sorted(df["ano"].unique())

        evolucao = df.groupby("ano").agg(
            total_inscritos=("nome", "count"),
            total_certificados=("certificado", lambda x: (x == "Sim").sum()),
            total_eventos=("evento", "nunique"),
            total_orgaos=("orgao", "nunique"),
            total_gestores=("cargo_de_gestao", lambda x: (x == "Sim").sum()),
        ).reset_index()

        evolucao["taxa_certificacao"] = (
            evolucao["total_certificados"] / evolucao["total_inscritos"] * 100
        ).round(2)

        evolucao["taxa_evasao"] = (
            (evolucao["total_inscritos"] - evolucao["total_certificados"])
            / evolucao["total_inscritos"] * 100
        ).round(2)

        # Calcular crescimento percentual em relação ao ano anterior
        for col in ["total_inscritos", "total_certificados", "total_eventos", "total_orgaos"]:
            evolucao[f"{col}_crescimento_pct"] = evolucao[col].pct_change() * 100

        # --- Evolução por formato/tipo ---
        evolucao_formato = df.groupby(["ano", "formato"]).agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
            n_eventos=("evento", "nunique"),
        ).reset_index()
        evolucao_formato["taxa_certificacao"] = (
            evolucao_formato["n_certificados"] / evolucao_formato["n_inscritos"] * 100
        ).round(2)

        # --- Evolução por órgão (top órgãos em ambos os anos) ---
        filtro = df["orgao"].astype(str).str.strip()
        df_org = df[~filtro.str.lower().isin(["outro", "outros", ""])].copy()
        evolucao_orgao = df_org.groupby(["ano", "orgao"]).agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
        ).reset_index()
        evolucao_orgao["taxa_certificacao"] = (
            evolucao_orgao["n_certificados"] / evolucao_orgao["n_inscritos"] * 100
        ).round(2)

        # --- Evolução por cargo (top cargos) ---
        filtro_cargo = df["cargo"].astype(str).str.strip().str.lower()
        df_cargo = df[~filtro_cargo.isin(["", "outro", "outros"])].copy()
        evolucao_cargo = df_cargo.groupby(["ano", "cargo"]).agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
        ).reset_index()

        # --- Evolução por eixo ---
        evolucao_eixo = df.groupby(["ano", "eixo"]).agg(
            n_inscritos=("nome", "count"),
            n_certificados=("certificado", lambda x: (x == "Sim").sum()),
        ).reset_index()

        return {
            "geral": evolucao,
            "formato": evolucao_formato,
            "orgao": evolucao_orgao,
            "cargo": evolucao_cargo,
            "eixo": evolucao_eixo,
        }

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

        df_orgaos_parceiros = self.create_df_orgaos_parceiros(df)
        self.save_to_parquet(df_orgaos_parceiros, "orgaos_parceiros")

        # NOVO: gerar arquivos de evolução anual
        evolucao = self.create_df_evolucao_anual(df)
        self.save_to_parquet(evolucao["geral"],   "evolucao_anual_geral")
        self.save_to_parquet(evolucao["formato"],  "evolucao_anual_formato")
        self.save_to_parquet(evolucao["orgao"],    "evolucao_anual_orgao")
        self.save_to_parquet(evolucao["cargo"],    "evolucao_anual_cargo")
        self.save_to_parquet(evolucao["eixo"],     "evolucao_anual_eixo")

        logger.info("Processamento concluído com sucesso!")


def main():
    processor = CapacitiaCSVProcessor()
    processor.process_all()

if __name__ == "__main__":
    main()
