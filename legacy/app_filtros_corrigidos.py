# CORREÇÃO DOS FILTROS GLOBAIS - CAPACITIA DASHBOARD
# Este arquivo contém a versão corrigida da seção de filtros globais

import streamlit as st
import pandas as pd

def aCplicar_filtros_globais(df_dados, df_secretarias, df_cargos, df_visao):
    """
    Função centralizada para aplicar filtros globais de forma consistente
    
    Args:
        df_dados: DataFrame principal com dados individuais
        df_secretarias: DataFrame agregado por secretaria/órgão
        df_cargos: DataFrame agregado por cargo
        df_visao: DataFrame de visão aberta
    
    Returns:
        tuple: DataFrames filtrados (df_dados_filtrado, df_secretarias_filtrado, df_cargos_filtrado, df_visao_filtrado)
    """
    
    # ==========================================
    # SEÇÃO: FILTROS GLOBAIS CORRIGIDOS
    # ==========================================
    
    st.markdown("---")
    st.markdown("### 🔍 **FILTROS GLOBAIS**")
    
    # Criar colunas para organizar os filtros
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    # FILTRO 1: Tipo de Curso/Evento
    with col_filtro1:
        # Obter valores únicos de eventos do df_dados (fonte única de verdade)
        eventos_disponiveis = ["Todos"] + sorted(df_dados['evento'].dropna().unique().tolist())
        evento_selecionado = st.selectbox(
            "📚 **Tipo de Curso/Evento**",
            eventos_disponiveis,
            key="filtro_evento_global"
        )
    
    # FILTRO 2: Órgão/Secretaria  
    with col_filtro2:
        # Obter valores únicos de órgãos do df_dados
        orgaos_disponiveis = ["Todos"] + sorted(df_dados['orgao'].dropna().unique().tolist())
        orgao_selecionado = st.selectbox(
            "🏛️ **Órgão/Secretaria**",
            orgaos_disponiveis,
            key="filtro_orgao_global"
        )
    
    # FILTRO 3: Órgão Externo
    with col_filtro3:
        # Obter valores únicos de órgão externo do df_dados
        orgao_externo_opcoes = ["Todos", "Sim", "Não"]
        orgao_externo_selecionado = st.selectbox(
            "🌐 **Órgão Externo**",
            orgao_externo_opcoes,
            key="filtro_orgao_externo_global"
        )
    
    # ==========================================
    # APLICAÇÃO DOS FILTROS
    # ==========================================
    
    # Começar com cópia dos dados originais
    df_dados_filtrado = df_dados.copy()
    
    # Aplicar filtro de evento
    if evento_selecionado != "Todos":
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado['evento'] == evento_selecionado]
    
    # Aplicar filtro de órgão
    if orgao_selecionado != "Todos":
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado['orgao'] == orgao_selecionado]
    
    # Aplicar filtro de órgão externo
    if orgao_externo_selecionado != "Todos":
        df_dados_filtrado = df_dados_filtrado[df_dados_filtrado['orgao_externo'] == orgao_externo_selecionado]
    
    # ==========================================
    # RECALCULAR AGREGAÇÕES COM DADOS FILTRADOS
    # ==========================================
    
    # Recalcular df_secretarias com dados filtrados
    if len(df_dados_filtrado) > 0:
        # Agrupar por órgão e recalcular métricas
        df_secretarias_filtrado = df_dados_filtrado.groupby('orgao').agg({
            'nome': 'count',  # Total de inscritos
            'certificado': lambda x: (x == 'Sim').sum(),  # Certificados
        }).reset_index()
        
        df_secretarias_filtrado.columns = ['orgao', 'n_inscritos', 'n_certificados']
        df_secretarias_filtrado['n_evasao'] = df_secretarias_filtrado['n_inscritos'] - df_secretarias_filtrado['n_certificados']
        df_secretarias_filtrado['taxa_certificacao'] = (df_secretarias_filtrado['n_certificados'] / df_secretarias_filtrado['n_inscritos'] * 100).round(1)
        
        # Renomear coluna para compatibilidade com código existente
        df_secretarias_filtrado = df_secretarias_filtrado.rename(columns={'orgao': 'SECRETARIA/ÓRGÃO'})
        
    else:
        # Se não há dados após filtros, criar DataFrame vazio com estrutura correta
        df_secretarias_filtrado = pd.DataFrame(columns=['SECRETARIA/ÓRGÃO', 'n_inscritos', 'n_certificados', 'n_evasao', 'taxa_certificacao'])
    
    # Recalcular df_cargos com dados filtrados
    if len(df_dados_filtrado) > 0:
        df_cargos_filtrado = df_dados_filtrado.groupby(['cargo', 'orgao']).agg({
            'nome': 'count',  # Total por cargo
            'certificado': lambda x: (x == 'Sim').sum(),  # Certificados por cargo
        }).reset_index()
        
        df_cargos_filtrado.columns = ['cargo', 'orgao', 'total_inscritos', 'certificados']
        df_cargos_filtrado['taxa_certificacao'] = (df_cargos_filtrado['certificados'] / df_cargos_filtrado['total_inscritos'] * 100).round(1)
        
        # Adicionar coluna de gestores (simplificada)
        cargos_gestao = ['Diretor', 'Secretário (a)', 'Chefe de Gabinete', 'Coordenador']
        df_cargos_filtrado['n_gestores'] = df_cargos_filtrado['cargo'].apply(
            lambda x: df_cargos_filtrado[df_cargos_filtrado['cargo'] == x]['total_inscritos'].sum() 
            if x in cargos_gestao else 0
        )
        
    else:
        # DataFrame vazio com estrutura correta
        df_cargos_filtrado = pd.DataFrame(columns=['cargo', 'orgao', 'total_inscritos', 'certificados', 'taxa_certificacao', 'n_gestores'])
    
    # Filtrar df_visao (se aplicável)
    df_visao_filtrado = df_visao.copy()
    if evento_selecionado != "Todos":
        df_visao_filtrado = df_visao_filtrado[df_visao_filtrado['evento'] == evento_selecionado]
    
    # ==========================================
    # EXIBIR INFORMAÇÕES DOS FILTROS APLICADOS
    # ==========================================
    
    # Mostrar resumo dos filtros aplicados
    filtros_ativos = []
    if evento_selecionado != "Todos":
        filtros_ativos.append(f"Evento: {evento_selecionado}")
    if orgao_selecionado != "Todos":
        filtros_ativos.append(f"Órgão: {orgao_selecionado}")
    if orgao_externo_selecionado != "Todos":
        filtros_ativos.append(f"Órgão Externo: {orgao_externo_selecionado}")
    
    if filtros_ativos:
        st.info(f"🔍 **Filtros ativos**: {' | '.join(filtros_ativos)} | **Registros encontrados**: {len(df_dados_filtrado)}")
    else:
        st.info(f"📊 **Visualizando todos os dados** | **Total de registros**: {len(df_dados_filtrado)}")
    
    # Botão para limpar filtros
    if st.button("🔄 Limpar Todos os Filtros", key="limpar_filtros_globais"):
        st.rerun()
    
    return df_dados_filtrado, df_secretarias_filtrado, df_cargos_filtrado, df_visao_filtrado


def calcular_kpis_filtrados(df_dados_filtrado):
    """
    Calcula KPIs com base nos dados filtrados
    
    Args:
        df_dados_filtrado: DataFrame com dados após aplicação dos filtros
    
    Returns:
        dict: Dicionário com os KPIs calculados
    """
    
    if len(df_dados_filtrado) == 0:
        return {
            'total_inscritos': 0,
            'total_certificados': 0,
            'taxa_certificacao': 0,
            'total_orgaos': 0,
            'total_eventos': 0,
            'orgaos_externos': 0
        }
    
    kpis = {
        'total_inscritos': len(df_dados_filtrado),
        'total_certificados': len(df_dados_filtrado[df_dados_filtrado['certificado'] == 'Sim']),
        'total_orgaos': df_dados_filtrado['orgao'].nunique(),
        'total_eventos': df_dados_filtrado['evento'].nunique(),
        'orgaos_externos': len(df_dados_filtrado[df_dados_filtrado['orgao_externo'] == 'Sim'])
    }
    
    # Calcular taxa de certificação
    if kpis['total_inscritos'] > 0:
        kpis['taxa_certificacao'] = round((kpis['total_certificados'] / kpis['total_inscritos']) * 100, 1)
    else:
        kpis['taxa_certificacao'] = 0
    
    return kpis


# ==========================================
# EXEMPLO DE USO NO APP.PY PRINCIPAL
# ==========================================

"""
# No app.py principal, substituir a seção de filtros globais por:

# Aplicar filtros globais
df_dados_filtrado, df_secretarias_filtrado, df_cargos_filtrado, df_visao_filtrado = aplicar_filtros_globais(
    df_dados, df_secretarias, df_cargos, df_visao
)

# Calcular KPIs com dados filtrados
kpis_filtrados = calcular_kpis_filtrados(df_dados_filtrado)

# Usar os DataFrames filtrados no restante do dashboard
# Exemplo:
st.metric("Total de Inscritos", kpis_filtrados['total_inscritos'])
st.metric("Certificados", kpis_filtrados['total_certificados'])
st.metric("Taxa de Certificação", f"{kpis_filtrados['taxa_certificacao']}%")

# Usar df_secretarias_filtrado, df_cargos_filtrado, etc. nos gráficos e tabelas
"""