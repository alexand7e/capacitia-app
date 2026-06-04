# pagina_ia.py (versão com abas e filtros no topo)
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import plotly.express as px

# --- CSS para manter o padrão visual ---
def aplicar_estilo_css():
    st.markdown("""
    <style>
        .main { background-color: #1e1e2f; }
        p, h1, h2, h3, h4, h5, h6, .st-emotion-cache-16idsys p, .st-emotion-cache-1gulkj5 { color: #FFFFFF; }
        .st-emotion-cache-1y4p8pa { /* Cor de fundo do expander */
            background-color: #2a2a40;
        }
        .kpi-card {
            background-color: #2a2a40; padding: 25px; border-radius: 10px; border: 1px solid #3a3a5a;
            text-align: center; color: white; height: 160px; display: flex; flex-direction: column; justify-content: center;
        }
        .kpi-card h3 { color: #FFD166; font-size: 42px; margin-bottom: 8px; }
        .kpi-card p { color: #ccc; font-size: 18px; margin-top: 0; }
        .st-emotion-cache-16txtl3 { padding-top: 2rem; } /* Ajuste de espaçamento dos filtros */
    </style>
    """, unsafe_allow_html=True)

# --- Carregamento dos dados ---
@st.cache_data
def carregar_dados_corretos():
    """Carrega e prepara os dados das duas tabelas."""
    try:
        df_projetos = pd.read_csv("./dados/CapacitIA - Trabalhos _ Assistentes - ASSISTENTES.csv")
        df_participantes = pd.read_csv("./dados/Utilização de Assistentes de IA (respostas) - Respostas ao formulário 1.csv")
        df_projetos.columns = df_projetos.columns.str.strip()
        df_participantes.columns = df_participantes.columns.str.strip()
        return df_projetos, df_participantes
    except FileNotFoundError as e:
        st.error(f"Erro de arquivo: {e}. Verifique se os nomes dos arquivos CSV estão corretos.")
        return None, None
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        return None, None

# --- Função principal da página ---
def construir_pagina_ia():
    aplicar_estilo_css()
    df_projetos, df_participantes = carregar_dados_corretos()

    if df_projetos is None or df_participantes is None:
        return

    st.title("🚀 Monitoramento de Resultados - CapacitIA")
    st.markdown("Acompanhamento dos projetos desenvolvidos e do engajamento dos participantes do programa.")

    # --- Nomes corretos das colunas para referência ---
    col_dev_assistente = "Desenvolveu algum assistente ou solução de IA dentro da sua Secretaria ou Órgão?"
    col_uso_assistente = "Atualmente, esse assistente está sendo utilizado por você ou sua equipe?"
    col_secretaria_projeto = "SECRETARIA / RESPONSÁVEL"
    col_secretaria_participante = "Órgão / Secretaria de Governo"
    col_desafios = "Que desafios ou limitações você identificou ao usar o assistente?"

    # --- FILTROS NO TOPO ---
    with st.expander("⚙️ Mostrar / Ocultar Filtros"):
        secretarias_participantes = sorted(df_participantes[col_secretaria_participante].dropna().unique())
        secretaria_selecionada = st.multiselect(
            "Filtrar por Secretaria do Participante",
            options=secretarias_participantes,
            default=secretarias_participantes
        )
        df_participantes_filtrado = df_participantes[df_participantes[col_secretaria_participante].isin(secretaria_selecionada)]

    st.markdown("---")

    # --- NAVEGAÇÃO POR ABAS ---
    tab_geral, tab_detalhes, tab_participantes, tab_dados = st.tabs([
        "📊 Visão Geral",
        "📂 Detalhes por Secretaria",
        "👥 Análise dos Participantes",
        "📋 Dados Completos"
    ])

    # --- ABA 1: VISÃO GERAL ---
    with tab_geral:
        st.subheader("Panorama Geral do Programa")

        # Cálculos dos KPIs
        total_projetos = len(df_projetos)
        total_participantes = len(df_participantes)
        desenvolvedores_ativos = df_participantes[col_dev_assistente].value_counts().get('Sim', 0)
        solucoes_em_uso = df_participantes[col_uso_assistente].value_counts().get('Sim', 0)
        secretarias_desenvolvedoras = df_projetos[col_secretaria_projeto].nunique()
        interesse_perc = df_participantes["Você tem interesse em aprimorar, ampliar ou corrigir o Assistente?"].value_counts(normalize=True).get('Sim', 0) * 100

        # Layout dos KPIs
        col1, col2, col3 = st.columns(3)
        col1.markdown(f'<div class="kpi-card"><h3>{total_projetos}</h3><p>Projetos Mapeados</p></div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="kpi-card"><h3>{total_participantes}</h3><p>Participantes</p></div>', unsafe_allow_html=True)
        col3.markdown(f'<div class="kpi-card"><h3>{secretarias_desenvolvedoras}</h3><p>Secretarias Envolvidas</p></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)
        col4.markdown(f'<div class="kpi-card"><h3 style="color: #06D6A0;">{desenvolvedores_ativos}</h3><p>Desenvolveram Soluções</p></div>', unsafe_allow_html=True)
        col5.markdown(f'<div class="kpi-card"><h3 style="color: #06D6A0;">{solucoes_em_uso}</h3><p>Soluções em Uso</p></div>', unsafe_allow_html=True)
        col6.markdown(f'<div class="kpi-card"><h3 style="color: #06D6A0;">{interesse_perc:.1f}%</h3><p>Interesse em Continuar</p></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Distribuição dos Projetos")
        projetos_por_sec = df_projetos[col_secretaria_projeto].value_counts()
        fig_proj_sec = px.bar(projetos_por_sec, x=projetos_por_sec.values, y=projetos_por_sec.index, orientation='h', text_auto=True, labels={'y': 'Secretaria', 'x': 'Nº de Projetos'})
        st.plotly_chart(fig_proj_sec, use_container_width=True)

    # --- ABA 2: DETALHES POR SECRETARIA ---
    with tab_detalhes:
        st.subheader("Explore os Projetos de uma Secretaria Específica")
        secretarias_com_projeto = sorted(df_projetos[col_secretaria_projeto].dropna().unique())
        secretaria_detalhe = st.selectbox("Selecione uma Secretaria para ver os detalhes", options=secretarias_com_projeto)

        if secretaria_detalhe:
            projetos_da_secretaria = df_projetos[df_projetos[col_secretaria_projeto] == secretaria_detalhe]
            st.markdown(f"#### Projetos da Secretaria: {secretaria_detalhe}")
            
            for index, row in projetos_da_secretaria.iterrows():
                with st.container(border=True):
                    st.markdown(f"##### {row['NOME']}")
                    st.write(row['DESCRIÇÃO'])
                    if pd.notna(row['LINK']):
                        st.link_button("Acessar Ferramenta", url=row['LINK'])

    # --- ABA 3: ANÁLISE DOS PARTICIPANTES ---
    with tab_participantes:
        st.subheader("Perfil e Percepções dos Participantes")
        st.info(f"Análise baseada nos filtros aplicados: **{', '.join(secretaria_selecionada)}**.")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### Desenvolveram um Assistente?")
            status_dev = df_participantes_filtrado[col_dev_assistente].value_counts()
            fig_status_dev = px.pie(status_dev, values=status_dev.values, names=status_dev.index, hole=0.4)
            st.plotly_chart(fig_status_dev, use_container_width=True)

        with col_g2:
            st.markdown("##### Assistentes em Uso Atualmente")
            status_uso = df_participantes_filtrado[col_uso_assistente].value_counts()
            fig_status_uso = px.pie(status_uso, values=status_uso.values, names=status_uso.index, hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
            st.plotly_chart(fig_status_uso, use_container_width=True)

        st.markdown("---")
        st.markdown("##### Desafios e Limitações Identificados")
        desafios = df_participantes_filtrado[col_desafios].dropna().value_counts().nlargest(10)
        fig_desafios = px.bar(desafios, x=desafios.values, y=desafios.index, orientation='h', text_auto=True, labels={'y': 'Desafio', 'x': 'Nº de Menções'})
        st.plotly_chart(fig_desafios, use_container_width=True)
    
    # --- ABA 4: DADOS COMPLETOS ---
    with tab_dados:
        st.subheader("Catálogo de Projetos de IA (Colunas Principais)")
        colunas_importantes_projetos = ['NOME', 'DESCRIÇÃO', 'SECRETARIA / RESPONSÁVEL', 'ORIGEM', 'LINK']
        st.dataframe(df_projetos[colunas_importantes_projetos], use_container_width=True)

        st.subheader("Acompanhamento dos Participantes (Colunas Principais)")
        colunas_importantes_participantes = [
            'Nome', col_secretaria_participante, col_dev_assistente, 
            col_uso_assistente, col_desafios, 'Você tem interesse em aprimorar, ampliar ou corrigir o Assistente?'
        ]
        st.dataframe(df_participantes_filtrado[colunas_importantes_participantes], use_container_width=True)