"""Funções de carregamento de dados para todos os módulos."""

import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
import streamlit as st
import sys

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

@st.cache_data(show_spinner=False)
def load_servidores_data() -> Tuple[Optional[pd.DataFrame], ...]:
    """Carrega dados do CapacitIA Servidores."""
    processed_path = Path(".data") / "processed"
    
    try:
        df_dados = pd.read_parquet(processed_path / "dados.parquet")
        df_visao = pd.read_parquet(processed_path / "visao_aberta.parquet")
        df_secretarias = pd.read_parquet(processed_path / "secretarias.parquet")
        df_cargos = pd.read_parquet(processed_path / "cargos.parquet")
        try:
            df_min = pd.read_parquet(processed_path / "ministrantes.parquet")
        except Exception:
            df_min = None
        return df_dados, df_visao, df_secretarias, df_cargos, df_min
    except Exception as e:
        st.error(f"Erro ao carregar dados de Servidores: {e}")
        return None, None, None, None, None

@st.cache_data(show_spinner=False)
def load_saude_data() -> Optional[pd.DataFrame]:
    """Carrega dados do CapacitIA Saúde."""
    processed_path = Path(".data") / "processed"
    
    try:
        df_saude = pd.read_parquet(processed_path / "saude.parquet")
        return df_saude
    except Exception as e:
        st.error(f"Erro ao carregar dados de Saúde: {e}")
        return None

@st.cache_data(show_spinner=False)
def load_autonomia_digital_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Carrega dados do CapacitIA Autonomia Digital."""
    processed_path = Path(".data") / "processed"
    
    try:
        df_inscricoes = pd.read_parquet(processed_path / "autonomiadigital_inscricoes.parquet")
        df_avaliacoes = pd.read_parquet(processed_path / "autonomiadigital_avaliacoes.parquet")
        return df_inscricoes, df_avaliacoes
    except Exception as e:
        st.error(f"Erro ao carregar dados de Autonomia Digital: {e}")
        return None, None

@st.cache_data(show_spinner=False)
def load_all_data() -> dict:
    """Carrega todos os dados de todos os módulos."""
    servidores_data = load_servidores_data()
    saude_data = load_saude_data()
    autonomia_data = load_autonomia_digital_data()
    
    return {
        'servidores': {
            'dados': servidores_data[0],
            'visao': servidores_data[1],
            'secretarias': servidores_data[2],
            'cargos': servidores_data[3],
            'ministrantes': servidores_data[4],
        },
        'saude': {
            'dados': saude_data,
        },
        'autonomia_digital': {
            'inscricoes': autonomia_data[0],
            'avaliacoes': autonomia_data[1],
        },
    }

