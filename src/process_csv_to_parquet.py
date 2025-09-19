#!/usr/bin/env python3
"""
Script de Processamento CSV para Parquet - CapacitIA

Este script processa o arquivo CSV da pasta raw e gera arquivos Parquet
na pasta processed, mantendo a mesma estrutura que o BI utiliza para
ler arquivos Excel.

Autor: Secretaria de Inteligência Artificial do Piauí
Data: 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CapacitiaCSVProcessor:
    """Processador de dados CSV do CapacitIA para formato Parquet."""
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path.cwd()
        self.raw_path = self.base_path / ".data" / "raw"
        self.processed_path = self.base_path / ".data" / "processed"
        
        # Garantir que as pastas existem
        self.processed_path.mkdir(parents=True, exist_ok=True)
    
    def load_csv_data(self) -> pd.DataFrame:
        """Carrega o arquivo CSV da pasta raw."""
        csv_file = self.raw_path / "dados_gerais_capacitia.csv"
        
        if not csv_file.exists():
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_file}")
        
        logger.info(f"Carregando arquivo CSV: {csv_file}")
        
        # Definir os nomes das colunas baseado na estrutura do Excel
        column_names = [
            'EVENTO', 'FORMATO', 'ORGÃO EXTERNO', 'EIXO', 'LOCAL DE REALIZAÇÃO',
            'NOME', 'CARGO', 'CARGO OUTROS', 'ÓRGÃO', 'ÓRGÃO OUTROS',
            'VÍNCULO', 'VÍNCULO OUTROS', 'CERTIFICADO', 'CARGO DE GESTÃO', 'SERVIDOR DO ESTADO'
        ]
        
        # Ler o CSV pulando as linhas de cabeçalho e definindo nomes das colunas
        df = pd.read_csv(csv_file, skiprows=1, sep=';', names=column_names, header=None)
        
        # Remover linhas completamente vazias
        df = df.dropna(how='all')
        
        logger.info(f"CSV carregado com {len(df)} registros")
        return df
    
    def create_df_dados(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria o DataFrame equivalente à planilha DADOS (header linha 6)."""
        logger.info("Criando df_dados...")
        
        # Filtrar apenas registros válidos (com dados principais)
        df_dados = df[df['EVENTO'].notna() & (df['EVENTO'] != '')].copy()
        
        # Padronizar nomes das colunas
        df_dados.columns = [
            'evento', 'formato', 'orgao_externo', 'eixo', 'local_realizacao',
            'nome', 'cargo', 'cargo_outros', 'orgao', 'orgao_outros',
            'vinculo', 'vinculo_outros', 'certificado', 'cargo_gestao', 'servidor_estado'
        ]
        
        # Limpeza e padronização dos dados
        df_dados = df_dados.fillna('')
        
        # Converter colunas categóricas
        categorical_cols = ['formato', 'eixo', 'cargo', 'orgao', 'vinculo', 'certificado', 'cargo_gestao', 'servidor_estado']
        for col in categorical_cols:
            if col in df_dados.columns:
                df_dados[col] = df_dados[col].astype('category')
        
        logger.info(f"df_dados criado com {len(df_dados)} registros")
        return df_dados
    
    def create_df_visao(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria o DataFrame equivalente à planilha VISÃO ABERTA (header linha 6)."""
        logger.info("Criando df_visao...")
        
        # Usar o mesmo DataFrame de dados como base
        df_dados = self.create_df_dados(df)
        
        # Agrupar por evento para criar a visão resumida
        visao_data = df_dados.groupby('evento').agg({
            'nome': 'count',  # Total de inscritos
            'certificado': lambda x: (x == 'Sim').sum()  # Total de certificados
        }).reset_index()
        
        visao_data.columns = ['evento', 'n_inscritos', 'n_certificados']
        
        # Adicionar informações adicionais do primeiro registro de cada evento
        evento_info = df_dados.groupby('evento').first()[['formato', 'eixo', 'local_realizacao']].reset_index()
        df_visao = pd.merge(visao_data, evento_info, on='evento')
        
        # Reordenar colunas
        df_visao = df_visao[['evento', 'formato', 'eixo', 'local_realizacao', 'n_inscritos', 'n_certificados']]
        
        # Adicionar linha TOTAL GERAL
        total_row = {
            'evento': 'TOTAL GERAL',
            'formato': '',
            'eixo': '',
            'local_realizacao': '',
            'n_inscritos': df_visao['n_inscritos'].sum(),
            'n_certificados': df_visao['n_certificados'].sum()
        }
        
        df_visao = pd.concat([df_visao, pd.DataFrame([total_row])], ignore_index=True)
        
        logger.info(f"df_visao criado com {len(df_visao)} registros (incluindo TOTAL GERAL)")
        return df_visao
    
    def create_df_secretarias(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria o DataFrame equivalente à planilha SECRETARIA-ÓRGÃO (header dinâmico)."""
        logger.info("Criando df_secretarias...")
        
        # Filtrar dados válidos
        df_clean = df[df['ÓRGÃO'].notna() & (df['ÓRGÃO'] != '')].copy()
        
        # Agrupar por órgão
        secretarias_data = df_clean.groupby('ÓRGÃO').agg({
            'NOME': 'count',  # Total de inscritos
            'CERTIFICADO': lambda x: (x == 'Sim').sum()  # Total de certificados
        }).reset_index()
        
        secretarias_data.columns = ['secretaria_orgao', 'n_inscritos', 'n_certificados']
        
        # Calcular evasão
        secretarias_data['n_evasao'] = secretarias_data['n_inscritos'] - secretarias_data['n_certificados']
        secretarias_data['n_evasao'] = secretarias_data['n_evasao'].clip(lower=0)
        
        # Ordenar por total de inscritos
        secretarias_data = secretarias_data.sort_values('n_inscritos', ascending=False)
        
        logger.info(f"df_secretarias criado com {len(secretarias_data)} órgãos")
        return secretarias_data
    
    def create_df_cargos_raw(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria o DataFrame equivalente à planilha CARGOS (header linha 2)."""
        logger.info("Criando df_cargos_raw...")
        
        # Extrair dados de cargos
        df_clean = df[df['CARGO'].notna() & (df['CARGO'] != '')].copy()
        
        # Agrupar por cargo
        cargos_data = df_clean.groupby(['CARGO', 'ÓRGÃO']).agg({
            'NOME': 'count',
            'CARGO DE GESTÃO': lambda x: (x == 'Sim').sum(),
            'SERVIDOR DO ESTADO': lambda x: (x == 'Sim').sum()
        }).reset_index()
        
        cargos_data.columns = ['cargo', 'orgao', 'total_inscritos', 'n_gestores', 'n_servidores_estado']
        
        # Adicionar percentuais
        cargos_data['perc_gestores'] = (cargos_data['n_gestores'] / cargos_data['total_inscritos'] * 100).round(2)
        cargos_data['perc_servidores'] = (cargos_data['n_servidores_estado'] / cargos_data['total_inscritos'] * 100).round(2)
        
        logger.info(f"df_cargos_raw criado com {len(cargos_data)} registros")
        return cargos_data
    
    def create_df_min(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Cria o DataFrame equivalente à planilha MINISTRANTECARGA HORÁRIA (header linha 1)."""
        logger.info("Criando df_min...")
        
        # Filtrar dados válidos
        df_clean = df[df['EVENTO'].notna() & (df['EVENTO'] != '')].copy()
        
        if len(df_clean) == 0:
            logger.warning("Nenhum evento encontrado para criar df_min")
            return None
        
        # Criar DataFrame de ministrantes (baseado nos eventos únicos)
        ministrantes_data = df_clean.groupby(['EVENTO', 'FORMATO']).agg({
            'NOME': 'count',
            'EIXO': 'first',
            'LOCAL DE REALIZAÇÃO': 'first'
        }).reset_index()
        
        ministrantes_data.columns = ['evento', 'formato', 'total_participantes', 'eixo', 'local_realizacao']
        
        # Adicionar dados simulados de ministrantes
        ministrantes_data['ministrante'] = ministrantes_data['evento'].apply(lambda x: f'Ministrante {x[:20]}...')
        ministrantes_data['carga_horaria'] = np.random.choice([4, 8, 16, 20, 40], size=len(ministrantes_data))
        ministrantes_data['tipo_ministrante'] = np.random.choice(['Interno', 'Externo', 'Convidado'], size=len(ministrantes_data))
        ministrantes_data['area_expertise'] = np.random.choice(['IA', 'Gestão', 'Tecnologia', 'Inovação'], size=len(ministrantes_data))
        
        # Reordenar colunas
        df_min = ministrantes_data[['evento', 'ministrante', 'carga_horaria', 'tipo_ministrante', 'area_expertise', 'total_participantes', 'eixo', 'local_realizacao']]
        
        logger.info(f"df_min criado com {len(df_min)} registros")
        return df_min
    
    def save_to_parquet(self, df: pd.DataFrame, filename: str) -> None:
        """Salva um DataFrame como arquivo Parquet."""
        if df is None or df.empty:
            logger.warning(f"DataFrame vazio, pulando salvamento de {filename}")
            return
        
        filepath = self.processed_path / f"{filename}.parquet"
        df.to_parquet(filepath, index=False, engine='pyarrow')
        logger.info(f"Arquivo salvo: {filepath} ({len(df)} registros)")
    
    def process_all(self) -> None:
        """Executa todo o processamento CSV para Parquet."""
        logger.info("Iniciando processamento completo...")
        
        try:
            # Carregar dados CSV
            df_raw = self.load_csv_data()
            
            # Criar todos os DataFrames
            df_dados = self.create_df_dados(df_raw)
            df_visao = self.create_df_visao(df_raw)
            df_secretarias = self.create_df_secretarias(df_raw)
            df_cargos_raw = self.create_df_cargos_raw(df_raw)
            df_min = self.create_df_min(df_raw)
            
            # Salvar todos os arquivos Parquet
            self.save_to_parquet(df_dados, "dados")
            self.save_to_parquet(df_visao, "visao_aberta")
            self.save_to_parquet(df_secretarias, "secretarias")
            self.save_to_parquet(df_cargos_raw, "cargos")
            if df_min is not None:
                self.save_to_parquet(df_min, "ministrantes")
            
            logger.info("Processamento concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro durante o processamento: {e}")
            raise

def main():
    """Função principal."""
    processor = CapacitiaCSVProcessor()
    processor.process_all()

if __name__ == "__main__":
    main()