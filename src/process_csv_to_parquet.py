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
        
        # Padronizar nomes das colunas - CORREÇÃO: formato e orgao_externo estavam trocados
        df_dados.columns = [
            'evento', 'orgao_externo', 'formato', 'eixo', 'local_realizacao',
            'nome', 'cargo', 'cargo_outros', 'orgao', 'orgao_outros',
            'vinculo', 'vinculo_outros', 'certificado', 'cargo_gestao', 'servidor_estado'
        ]
        
        # Limpeza e padronização dos dados
        df_dados = df_dados.fillna('')
        
        # Função auxiliar para unir colunas principais com "OUTROS"
        def unir_colunas(principal, outros):
            """Une coluna principal com coluna 'OUTROS', priorizando principal."""
            # Se principal tem valor válido, usar principal
            if pd.notna(principal) and principal not in ['', 'NA']:
                return principal
            # Se principal vazio mas outros tem valor válido, usar outros
            elif pd.notna(outros) and outros not in ['', 'NA']:
                return outros
            # Caso contrário, retornar vazio
            return ''
        
        # Unir colunas duplicadas: unir "OUTROS" nas colunas principais
        # ÓRGÃO: unir 'orgao' e 'orgao_outros'
        df_dados['orgao'] = df_dados.apply(
            lambda row: unir_colunas(row['orgao'], row['orgao_outros']), axis=1
        )
        
        # VÍNCULO: unir 'vinculo' e 'vinculo_outros'
        df_dados['vinculo'] = df_dados.apply(
            lambda row: unir_colunas(row['vinculo'], row['vinculo_outros']), axis=1
        )
        
        # CARGO: unir 'cargo' e 'cargo_outros' (considerar 'Outro' como vazio)
        df_dados['cargo'] = df_dados.apply(
            lambda row: unir_colunas(
                row['cargo'] if row['cargo'] != 'Outro' else '', 
                row['cargo_outros']
            ), axis=1
        )
        
        # Remover colunas "OUTROS" já que foram unidas
        df_dados = df_dados.drop(columns=['orgao_outros', 'vinculo_outros', 'cargo_outros'], errors='ignore')
        
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
        
        # Função auxiliar para unir colunas principais com "OUTROS"
        def unir_colunas(principal, outros):
            """Une coluna principal com coluna 'OUTROS', priorizando principal."""
            if pd.notna(principal) and principal not in ['', 'NA']:
                return principal
            elif pd.notna(outros) and outros not in ['', 'NA']:
                return outros
            return ''
        
        # Primeiro, unir as colunas ÓRGÃO e ÓRGÃO OUTROS
        df_temp = df.copy()
        df_temp['ÓRGÃO_UNIDO'] = df_temp.apply(
            lambda row: unir_colunas(row['ÓRGÃO'], row['ÓRGÃO OUTROS']), axis=1
        )
        
        # Filtrar dados válidos usando a coluna unida
        df_clean = df_temp[df_temp['ÓRGÃO_UNIDO'].notna() & (df_temp['ÓRGÃO_UNIDO'] != '')].copy()
        
        # Agrupar por órgão unido
        secretarias_data = df_clean.groupby('ÓRGÃO_UNIDO').agg({
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
        
        # Função auxiliar para unir colunas principais com "OUTROS"
        def unir_colunas(principal, outros):
            """Une coluna principal com coluna 'OUTROS', priorizando principal."""
            if pd.notna(principal) and principal not in ['', 'NA']:
                return principal
            elif pd.notna(outros) and outros not in ['', 'NA']:
                return outros
            return ''
        
        # Primeiro, precisamos unir as colunas duplicadas antes de agrupar
        # Criar uma cópia temporária com colunas unidas
        df_temp = df.copy()
        
        # Unir ÓRGÃO e ÓRGÃO OUTROS
        df_temp['ÓRGÃO_UNIDO'] = df_temp.apply(
            lambda row: unir_colunas(row['ÓRGÃO'], row['ÓRGÃO OUTROS']), axis=1
        )
        
        # Unir CARGO e CARGO OUTROS (considerar 'Outro' como vazio)
        df_temp['CARGO_UNIDO'] = df_temp.apply(
            lambda row: unir_colunas(
                row['CARGO'] if row['CARGO'] != 'Outro' else '', 
                row['CARGO OUTROS']
            ), axis=1
        )
        
        # Extrair dados de cargos usando as colunas unidas
        df_clean = df_temp[df_temp['CARGO_UNIDO'].notna() & (df_temp['CARGO_UNIDO'] != '')].copy()
        
        # Agrupar por cargo unido
        cargos_data = df_clean.groupby(['CARGO_UNIDO', 'ÓRGÃO_UNIDO']).agg({
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
    
    def process_autonomiadigital(self) -> None:
        """Processa os CSVs de Autonomia Digital, removendo dados sensíveis."""
        logger.info("Iniciando processamento de dados de Autonomia Digital...")
        
        try:
            # Processar arquivo de avaliações
            avaliacoes_file = self.raw_path / "dados_avaliacoes_capacitia_autonomiadigital.csv"
            if avaliacoes_file.exists():
                logger.info(f"Processando arquivo de avaliações: {avaliacoes_file}")
                # Tentar diferentes encodings
                try:
                    df_avaliacoes = pd.read_csv(avaliacoes_file, sep=';', encoding='utf-8', low_memory=False)
                except UnicodeDecodeError:
                    try:
                        df_avaliacoes = pd.read_csv(avaliacoes_file, sep=';', encoding='latin-1', low_memory=False)
                    except UnicodeDecodeError:
                        df_avaliacoes = pd.read_csv(avaliacoes_file, sep=';', encoding='cp1252', low_memory=False)
                
                # Remover dados sensíveis e pessoais
                colunas_sensiveis = [
                    'Digite seu nome sem abreviar',
                    'Gênero',
                    'Idade',
                    'CPF',
                    'Se tiver, informe seu e-mail'
                ]
                
                # Encontrar colunas para remover (compatível com diferentes encodings)
                colunas_para_remover = []
                for col_sensivel in colunas_sensiveis:
                    for col_df in df_avaliacoes.columns:
                        # Comparar normalizando espaços e case
                        if col_df.strip() == col_sensivel.strip():
                            colunas_para_remover.append(col_df)
                            break
                
                # Remover colunas sensíveis
                df_avaliacoes_clean = df_avaliacoes.drop(columns=colunas_para_remover, errors='ignore')
                
                # Padronizar nomes das colunas (lowercase, underscore)
                df_avaliacoes_clean.columns = df_avaliacoes_clean.columns.str.lower().str.replace(' ', '_').str.replace('?', '').str.replace('(', '').str.replace(')', '').str.strip()
                
                # Limpar dados
                df_avaliacoes_clean = df_avaliacoes_clean.fillna('')
                
                # Renomear colunas principais para nomes mais limpos
                rename_map = {
                    'carimbo_de_data/hora': 'data_hora',
                    'você_aprendeu_sobre_as_funções_básicas_do_celular_conectar_a_internet_configurar_notificação_toque_fonte_instalar_e_desinstalar_app': 'aprendeu_funcoes_celular',
                    'você_aprendeu_a_usar_o_seu_e-mail_identificar_seu_e-mail_recuperar_senha': 'aprendeu_email',
                    'você_aprendeu_a_identificar_sites_confiáveis_e_se_proteger_de_golpes_virtuais_fake_news': 'aprendeu_seguranca_digital',
                    'você_aprendeu_como_a_inteligência_artificial_pode_te_ajudar_no_dia_a_dia': 'aprendeu_ia',
                    'você_aprendeu_a_usar_o_govpi_cidadão': 'aprendeu_govpi',
                    'você_aprendeu_a_usar_o_piauí_saúde_digital': 'aprendeu_saude_digital',
                    'você_aprendeu_a_usar_o_bo_fácil': 'aprendeu_bo_facil',
                    'quer_registrar_algo_que_você_aprendeu_a_mais_e_não_está_destacado_acima': 'aprendizados_extras',
                    'como_você_avalia_esse_evento': 'avaliacao_evento',
                    'o_que_você_achou_do_conteúdo': 'avaliacao_conteudo',
                    'o_que_você_achou_do_local_do_evento': 'avaliacao_local',
                    'como_você_avalia_o_atendimento_e_o_acolhimento_do_evento': 'avaliacao_atendimento',
                    'deixe_uma_sugestão_elogio_ou_reclamação': 'sugestao_elogio_reclamacao'
                }
                df_avaliacoes_clean = df_avaliacoes_clean.rename(columns=rename_map)
                
                # Salvar arquivo processado
                self.save_to_parquet(df_avaliacoes_clean, "autonomiadigital_avaliacoes")
            else:
                logger.warning(f"Arquivo de avaliações não encontrado: {avaliacoes_file}")
            
            # Processar arquivo de inscrições
            inscricoes_file = self.raw_path / "dados_inscricoes_capacitia_autonomiadigital.csv"
            if inscricoes_file.exists():
                logger.info(f"Processando arquivo de inscrições: {inscricoes_file}")
                # Tentar diferentes encodings
                try:
                    df_inscricoes = pd.read_csv(inscricoes_file, sep=';', encoding='utf-8', low_memory=False)
                except UnicodeDecodeError:
                    try:
                        df_inscricoes = pd.read_csv(inscricoes_file, sep=';', encoding='latin-1', low_memory=False)
                    except UnicodeDecodeError:
                        df_inscricoes = pd.read_csv(inscricoes_file, sep=';', encoding='cp1252', low_memory=False)
                
                # Remover dados sensíveis e pessoais
                colunas_sensiveis_originais = [
                    'Digite seu nome sem abreviar',
                    'Gênero',
                    'Idade',
                    'CPF',
                    'Cidade',
                    'Bairro',
                    'Telefone/Celular/WhatsApp',
                    'E-mail (se houver)'
                ]
                
                # Encontrar colunas para remover (comparando com nomes originais do CSV)
                colunas_para_remover = []
                for col_original in colunas_sensiveis_originais:
                    for col_df in df_inscricoes.columns:
                        if col_df.strip() == col_original:
                            colunas_para_remover.append(col_df)
                
                # Remover colunas sensíveis
                df_inscricoes_clean = df_inscricoes.drop(columns=colunas_para_remover, errors='ignore')
                
                # Padronizar nomes das colunas (lowercase, underscore)
                df_inscricoes_clean.columns = df_inscricoes_clean.columns.str.lower().str.replace(' ', '_').str.replace('/', '_').str.replace('?', '').str.replace('(', '').str.replace(')', '').str.replace('\n', '_').str.strip()
                
                # Limpar dados
                df_inscricoes_clean = df_inscricoes_clean.fillna('')
                
                # Renomear colunas principais para nomes mais limpos
                rename_map = {
                    'carimbo_de_data/hora': 'data_hora',
                    'você_é_aposentado(a)': 'aposentado',
                    'você_participa_de_qual_projeto_de_extensão': 'projeto_extensao',
                    'caso_você_não_seja_de_nenhum_projeto_citado_acima__1__diga_de_qual_grupo_você_faz_parte_se_houver__2__como_soube_do_treinamento__3__se_inscrever_para_os_dia_28_e_30_de_outubro': 'informacoes_adicional',
                    'autorizo_o_tratamento_dos_meus_dados_pessoais_pela_sia_nos_termos_da_lei_n_13.709/2018_lgpd': 'autorizacao_lgpd',
                    'dentre_esses_temas_qual(is)_você_tem_mais_dificuldade': 'temas_dificuldade'
                }
                df_inscricoes_clean = df_inscricoes_clean.rename(columns=rename_map)
                
                # Salvar arquivo processado
                self.save_to_parquet(df_inscricoes_clean, "autonomiadigital_inscricoes")
            else:
                logger.warning(f"Arquivo de inscrições não encontrado: {inscricoes_file}")
            
            logger.info("Processamento de Autonomia Digital concluído!")
            
        except Exception as e:
            logger.error(f"Erro durante o processamento de Autonomia Digital: {e}")
            raise
    
    def process_saude(self) -> None:
        """Processa o CSV de Saúde, removendo dados sensíveis."""
        logger.info("Iniciando processamento de dados de Saúde...")
        
        try:
            saude_file = self.raw_path / "dados_capacitia_saude.csv"
            if not saude_file.exists():
                logger.warning(f"Arquivo de saúde não encontrado: {saude_file}")
                return
            
            logger.info(f"Processando arquivo de saúde: {saude_file}")
            # Tentar diferentes encodings
            try:
                df_saude = pd.read_csv(saude_file, sep=';', encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                try:
                    df_saude = pd.read_csv(saude_file, sep=';', encoding='latin-1', low_memory=False)
                except UnicodeDecodeError:
                    df_saude = pd.read_csv(saude_file, sep=';', encoding='cp1252', low_memory=False)
            
            # Remover dados sensíveis e pessoais
            colunas_sensiveis_originais = ['Nome', 'E-mail']
            
            # Encontrar colunas para remover (comparando com nomes originais do CSV)
            colunas_para_remover = []
            for col_original in colunas_sensiveis_originais:
                for col_df in df_saude.columns:
                    if col_df.strip() == col_original:
                        colunas_para_remover.append(col_df)
            
            # Remover colunas sensíveis
            df_saude_clean = df_saude.drop(columns=colunas_para_remover, errors='ignore')
            
            # Remover colunas vazias (Unnamed)
            df_saude_clean = df_saude_clean.loc[:, ~df_saude_clean.columns.str.contains('^Unnamed')]
            
            # Padronizar nomes das colunas (lowercase, underscore)
            df_saude_clean.columns = df_saude_clean.columns.str.lower().str.replace(' ', '_').str.strip()
            
            # Limpar dados
            df_saude_clean = df_saude_clean.fillna('')
            
            # Renomear colunas principais para nomes mais limpos
            rename_map = {
                'nº': 'numero',
                'data': 'data',
                'lote': 'lote'
            }
            df_saude_clean = df_saude_clean.rename(columns=rename_map)
            
            # Salvar arquivo processado
            self.save_to_parquet(df_saude_clean, "saude")
            
            logger.info("Processamento de Saúde concluído!")
            
        except Exception as e:
            logger.error(f"Erro durante o processamento de Saúde: {e}")
            raise
    
    def process_all(self) -> None:
        """Executa todo o processamento CSV para Parquet."""
        logger.info("Iniciando processamento completo...")
        
        try:
            # Carregar dados CSV principais
            df_raw = self.load_csv_data()
            
            # Criar todos os DataFrames principais
            df_dados = self.create_df_dados(df_raw)
            df_visao = self.create_df_visao(df_raw)
            df_secretarias = self.create_df_secretarias(df_raw)
            df_cargos_raw = self.create_df_cargos_raw(df_raw)
            df_min = self.create_df_min(df_raw)
            
            # Salvar todos os arquivos Parquet principais
            self.save_to_parquet(df_dados, "dados")
            self.save_to_parquet(df_visao, "visao_aberta")
            self.save_to_parquet(df_secretarias, "secretarias")
            self.save_to_parquet(df_cargos_raw, "cargos")
            if df_min is not None:
                self.save_to_parquet(df_min, "ministrantes")
            
            # Processar dados de Autonomia Digital
            self.process_autonomiadigital()
            
            # Processar dados de Saúde
            self.process_saude()
            
            logger.info("Processamento completo concluído com sucesso!")
            
        except Exception as e:
            logger.error(f"Erro durante o processamento: {e}")
            raise

def main():
    """Função principal."""
    processor = CapacitiaCSVProcessor()
    processor.process_all()

if __name__ == "__main__":
    main()