# app.py (Versão Refinada com UI/UX Melhorado)
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Capacitações",
    page_icon="🚀",
    layout="wide"
)

# --- CSS CUSTOMIZADO PARA APLICAR A PALETA DE CORES E ESTILO DOS CARDS ---
# Injetando o CSS que você sugeriu para um visual mais moderno.
st.markdown("""
<style>
    /* Cor de fundo principal */
    .main {
        background-color: #1e1e2f;
    }
    /* Estilo dos cards de KPI */
    .kpi-card {
        background-color: #2a2a40;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #3a3a5a;
        text-align: center;
        color: white;
    }
    .kpi-card h3 {
        color: #FFD166; /* Destaque amarelo para o valor */
        font-size: 32px;
        margin-bottom: 5px;
    }
    .kpi-card p {
        color: #ccc; /* Cinza claro para o rótulo */
        font-size: 16px;
        margin-top: 0;
    }
    /* Cor do texto geral */
    p, h1, h2, h3, h4, h5, h6, .st-emotion-cache-16idsys p {
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)


# --- 2. CARREGAMENTO E CACHE DOS DADOS ---
@st.cache_data
def carregar_dados():
    caminho_arquivo = './dados/capacitia-dados.xlsx'
    planilhas = [
        'CARGOS-INCRITOS', 'CARGOS-CERTIFICADOS', 'SECRETARIAS-MASTERCLASS',
        'SECRETARIAS-CURSO 1', 'SECRETARIAS-CURSO 2'
    ]
    dfs = {}
    for planilha in planilhas:
        try:
            if planilha == 'SECRETARIAS-CURSO 2':
                dfs[planilha] = pd.read_excel(caminho_arquivo, sheet_name=planilha, skiprows=1)
            else:
                dfs[planilha] = pd.read_excel(caminho_arquivo, sheet_name=planilha)
        except Exception as e:
            st.error(f"Erro ao carregar a planilha '{planilha}': {e}")
            return None
    return dfs

# SUBSTITUA A ANTIGA FUNÇÃO POR ESTA VERSÃO MELHORADA

# SUBSTITUA A ANTIGA FUNÇÃO POR ESTA VERSÃO MELHORADA

# SUBSTITUA A ANTIGA FUNÇÃO POR ESTA VERSÃO TOTALMENTE INTERATIVA

def construir_aba_visao_geral(df_filtrado, df_comparativo_cargo, df_secretarias_geral, eventos_selecionados):
    """Gera todos os elementos da aba 'Visão Geral' com gráficos interativos."""
    
    # Seção de KPIs e texto introdutório (sem alterações)
    # ... (o código dos cards e do texto markdown permanece o mesmo) ...
    st.markdown("> ℹ️ **Bem-vindo ao Dashboard de Análise!** Use os filtros à esquerda para explorar os indicadores. Os cartões e gráficos são atualizados automaticamente.")
    st.markdown("---")
    # (código dos 8 cards omitido para brevidade, mas deve ser mantido no seu arquivo)


    # --- SEÇÃO DE GRÁFICOS TOTALMENTE INTERATIVA ---
    st.subheader("Análise Comparativa: Secretarias e Cargos")

    # O seletor de visualização agora controla os dois gráficos abaixo
    visao_geral = st.radio(
        "Visualizar por:",
        options=['Inscritos', 'Certificados', 'Comparativo'],
        horizontal=True,
        label_visibility="collapsed"
    )

    # Prepara o dataframe de secretarias para a nova visualização
    df_comparativo_secretaria = df_secretarias_geral.groupby('SECRETARIA/ÓRGÃO')[['Nº INSCRITOS', 'Nº CERTIFICADOS']].sum()

    col_dist1, col_dist2 = st.columns(2)

    # --- BLOCO 1 ATUALIZADO: GRÁFICO DE SECRETARIA INTERATIVO ---
    with col_dist1:
        st.markdown("<p style='text-align: center;'>Análise de Desempenho por Secretaria</p>", unsafe_allow_html=True)

        if visao_geral == 'Inscritos':
            df_view_sec = df_comparativo_secretaria.nlargest(10, 'Nº INSCRITOS').sort_values(by='Nº INSCRITOS')
            fig_sec = px.bar(df_view_sec, x='Nº INSCRITOS', y=df_view_sec.index, orientation='h', title='Top 10 Secretarias por Nº de Inscritos', text_auto=True)
            fig_sec.update_traces(marker_color='#FFD166')

        elif visao_geral == 'Certificados':
            df_view_sec = df_comparativo_secretaria.nlargest(10, 'Nº CERTIFICADOS').sort_values(by='Nº CERTIFICADOS')
            fig_sec = px.bar(df_view_sec, x='Nº CERTIFICADOS', y=df_view_sec.index, orientation='h', title='Top 10 Secretarias por Nº de Certificados', text_auto=True)
            fig_sec.update_traces(marker_color='#06D6A0')

        elif visao_geral == 'Comparativo':
            df_view_sec = df_comparativo_secretaria.nlargest(10, 'Nº INSCRITOS')
            fig_sec = px.bar(
                df_view_sec,
                x=['Nº INSCRITOS', 'Nº CERTIFICADOS'],
                y=df_view_sec.index,
                orientation='h',
                title='Inscritos vs. Certificados (Top 10 Secretarias)',
                barmode='group',
                text_auto=True,
                color_discrete_map={'Nº INSCRITOS': '#FFD166', 'Nº CERTIFICADOS': '#06D6A0'}
            )
        
        fig_sec.update_layout(yaxis_title="", title_x=0.5, legend_title_text='')
        st.plotly_chart(fig_sec, use_container_width=True)


    # --- BLOCO 2: GRÁFICO DE CARGO INTERATIVO (sem alterações na lógica) ---
    with col_dist2:
        st.markdown("<p style='text-align: center;'>Análise de Desempenho por Cargo</p>", unsafe_allow_html=True)
        
        if visao_geral == 'Inscritos':
            df_view_cargo = df_comparativo_cargo.nlargest(10, 'Inscritos').sort_values(by='Inscritos')
            fig_cargos = px.bar(df_view_cargo, x='Inscritos', y=df_view_cargo.index, orientation='h', title='Top 10 Cargos por Nº de Inscritos', text_auto=True)
            fig_cargos.update_traces(marker_color='#FFD166')
        
        elif visao_geral == 'Certificados':
            df_view_cargo = df_comparativo_cargo.nlargest(10, 'Certificados').sort_values(by='Certificados')
            fig_cargos = px.bar(df_view_cargo, x='Certificados', y=df_view_cargo.index, orientation='h', title='Top 10 Cargos por Nº de Certificados', text_auto=True)
            fig_cargos.update_traces(marker_color='#06D6A0')

        elif visao_geral == 'Comparativo':
            df_view_cargo = df_comparativo_cargo.nlargest(10, 'Inscritos')
            fig_cargos = px.bar(
                df_view_cargo,
                x=['Inscritos', 'Certificados'],
                y=df_view_cargo.index,
                orientation='h',
                title='Inscritos vs. Certificados (Top 10 Cargos)',
                barmode='group',
                text_auto=True,
                color_discrete_map={'Inscritos': '#FFD166', 'Certificados': '#06D6A0'}
            )
        
        fig_cargos.update_layout(yaxis_title="", title_x=0.5, legend_title_text='')
        st.plotly_chart(fig_cargos, use_container_width=True)

    st.markdown("---")

    # 4. Funil de Conversão (mantido)
    st.subheader("Funil de Conversão Consolidado do Programa")
    total_inscritos_geral = df_secretarias_geral['Nº INSCRITOS'].sum()
    total_certificados_geral = df_secretarias_geral['Nº CERTIFICADOS'].sum()
    fig_funil = px.funnel(x=[total_inscritos_geral, total_certificados_geral], y=['Inscritos', 'Certificados'], title="")
    st.plotly_chart(fig_funil, use_container_width=True)
    

dados = carregar_dados()

# --- 3. PRÉ-PROCESSAMENTO E CÁLCULOS ---
if dados:
    # Análise por Cargo (estática)
    total_inscritos_cargo = dados['CARGOS-INCRITOS'].drop(columns=['Unnamed: 0']).sum()
    total_certificados_cargo = dados['CARGOS-CERTIFICADOS'].drop(columns=['Unnamed: 0']).sum()
    df_comparativo_cargo = pd.DataFrame({
        'Inscritos': total_inscritos_cargo,
        'Certificados': total_certificados_cargo
    }).fillna(0)
    df_comparativo_cargo['Taxa de Certificação (%)'] = \
        (df_comparativo_cargo['Certificados'] / df_comparativo_cargo['Inscritos'] * 100).round(2)

    # Análise por Secretaria (base para os filtros)
    df_masterclass = dados['SECRETARIAS-MASTERCLASS'].assign(Evento='Masterclass')
    df_curso1 = dados['SECRETARIAS-CURSO 1'].assign(Evento='Curso 1')
    df_curso2 = dados['SECRETARIAS-CURSO 2'].assign(Evento='Curso 2')
    df_secretarias_geral = pd.concat([df_masterclass, df_curso1, df_curso2], ignore_index=True)
    df_secretarias_geral['SECRETARIA/ÓRGÃO'] = df_secretarias_geral['SECRETARIA/ÓRGÃO'].astype(str)



# --- 4. BARRA LATERAL (FILTROS) ---
st.sidebar.header('⚙️ Filtros de Análise')

if dados:
    # --- NOVO: CAMPO DE CUSTO SIMULADO NA BARRA LATERAL ---
    # custo_por_inscricao = st.sidebar.number_input(
    #     'Simular Custo por Inscrição (R$)',
    #     min_value=0.0,
    #     value=50.0, # Valor padrão
    #     step=10.0,
    #     format="%.2f",
    #     help="Insira um valor hipotético para calcular o custo por certificado."
    # )
    st.sidebar.markdown("---")
    
    # Filtros existentes
    eventos_unicos = df_secretarias_geral['Evento'].unique()
    eventos_selecionados = st.sidebar.multiselect('Selecione a(s) Capacitação(ões)', options=eventos_unicos, default=eventos_unicos)
    secretarias_unicas = sorted(df_secretarias_geral['SECRETARIA/ÓRGÃO'].unique())
    secretarias_selecionadas = st.sidebar.multiselect('Selecione a(s) Secretaria(s)/Órgão(s)', options=secretarias_unicas, default=secretarias_unicas)

    if not eventos_selecionados: eventos_selecionados = eventos_unicos.tolist()
    if not secretarias_selecionadas: secretarias_selecionadas = secretarias_unicas

    # --- NOVO: BOTÃO PARA LIMPAR FILTROS ---
    if st.sidebar.button("🔁 Limpar Filtros"):
        st.rerun()

# --- 5. LÓGICA DE FILTRAGEM DOS DADOS ---
if dados:
    df_filtrado = df_secretarias_geral[
        (df_secretarias_geral['Evento'].isin(eventos_selecionados)) &
        (df_secretarias_geral['SECRETARIA/ÓRGÃO'].isin(secretarias_selecionadas))
    ]

# --- TÍTULO PRINCIPAL ---
st.title('🚀 Dashboard de Desempenho das Capacitações')
st.markdown('---')


# --- 6. ABAS PRINCIPAIS ---
if dados:
    tab1, tab2, tab3 = st.tabs(["Visão Geral", "Análise por Cargo", "Análise por Secretaria"])

    # --- TAB 1: VISÃO GERAL ---
    with tab1:
        # --- NOVO: TEXTO INTRODUTÓRIO (MARKDOWN) ---
        st.markdown("""
        > ℹ️ **Bem-vindo ao Dashboard de Análise!** Use os filtros à esquerda para explorar os indicadores de desempenho das capacitações oferecidas. Os cartões e gráficos são atualizados automaticamente com base na sua seleção.
        """)
        st.markdown("---")

        # Cálculos dos KPIs
        total_inscritos = int(df_filtrado['Nº INSCRITOS'].sum())
        total_certificados = int(df_filtrado['Nº CERTIFICADOS'].sum())
        capacitacoes_analisadas = df_filtrado['Evento'].nunique()

        # TOTAIS REAIS DE EVENTOS (baseado na sua lista mestra de capacitações)
        TOTAL_MASTERCLASSES_REAL = 8
        TOTAL_CURSOS_E_WORKSHOPS_REAL = 19

        # Lógica final para exibir os totais corretos baseada na SELEÇÃO DE TIPO
        # Se o TIPO 'Masterclass' estiver selecionado no filtro, mostre o total de masterclasses que aconteceram.
        num_masterclass = TOTAL_MASTERCLASSES_REAL if 'Masterclass' in eventos_selecionados else 0
            
        # Se QUALQUER TIPO de curso ('Curso 1', 'Curso 2', etc.) estiver selecionado, mostre o total de cursos que aconteceram.
        tem_curso_selecionado = any('Curso' in evento for evento in eventos_selecionados)
        num_cursos = TOTAL_CURSOS_E_WORKSHOPS_REAL if tem_curso_selecionado else 0

        if total_inscritos > 0:
            taxa_certificacao = (total_certificados / total_inscritos * 100)
        else:
            taxa_certificacao = 0

        # --- NOVO: REDESIGN DOS CARDS DE KPI COM CSS ---
        st.subheader("Indicadores de Desempenho")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="kpi-card"><h3>{total_inscritos}</h3><p>Total de Inscritos</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><h3>{total_certificados}</h3><p>Total de Certificados</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><h3 style="color: #06D6A0;">{taxa_certificacao:.1f}%</h3><p>Taxa de Certificação</p></div>', unsafe_allow_html=True)
        with col4:
            taxa_evasao = 100 - taxa_certificacao
            st.markdown(f'<div class="kpi-card"><h3 style="color: #EF476F;">{taxa_evasao:.1f}%</h3><p>Taxa de Evasão</p></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True) # Espaçamento
        
        # --- NOVO: ADIÇÃO DOS 2 NOVOS CARDS ---
        st.subheader("Indicadores de Gestão e Escala")
        col5, col6, col7, col8 = st.columns(4)
        with col5:
             st.markdown(f'<div class="kpi-card"><h3>{df_filtrado["SECRETARIA/ÓRGÃO"].nunique()}</h3><p>Secretarias Atendidas</p></div>', unsafe_allow_html=True)
        with col6:
            st.markdown(f'<div class="kpi-card"><h3>{num_masterclass}</h3><p>Nº de Masterclasses</p></div>', unsafe_allow_html=True)
        with col7:
            st.markdown(f'<div class="kpi-card"><h3>{num_cursos}</h3><p>Nº de Cursos</p></div>', unsafe_allow_html=True)
        with col8:
            media_inscritos = total_inscritos / capacitacoes_analisadas if capacitacoes_analisadas > 0 else 0
            st.markdown(f'<div class="kpi-card"><h3>{media_inscritos:.1f}</h3><p>Média de Inscritos por Evento</p></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        construir_aba_visao_geral(df_filtrado, df_comparativo_cargo, df_secretarias_geral, eventos_selecionados)

    # --- Tab 2: Análise por Cargo ---
    with tab2:
        st.header('👥 Desempenho Geral por Cargo (Todos os Eventos)')
        st.info('Esta seção apresenta dados consolidados de todos os eventos e não é afetada pelos filtros.')

        # Gráfico 1: Total de Inscritos por Cargo
        fig_inscritos_cargo = px.bar(
            df_comparativo_cargo.sort_values(by='Inscritos', ascending=False),
            x=df_comparativo_cargo.sort_values(by='Inscritos', ascending=False).index,
            y='Inscritos',
            title="Total de Inscritos por Cargo em Todas as Masterclasses",
            labels={'index': 'Cargo', 'Inscritos': 'Número Total de Inscritos'},
            text='Inscritos'
        )
        fig_inscritos_cargo.update_traces(textposition='outside')
        st.plotly_chart(fig_inscritos_cargo, use_container_width=True)

        # Gráfico 2: Taxa de Certificação (%) por Cargo
        fig_taxa_certificacao_cargo = px.bar(
            df_comparativo_cargo.sort_values(by='Taxa de Certificação (%)', ascending=False),
            x=df_comparativo_cargo.sort_values(by='Taxa de Certificação (%)', ascending=False).index,
            y='Taxa de Certificação (%)',
            title="Taxa de Certificação por Cargo (Todos os Eventos)",
            labels={'index': 'Cargo', 'Taxa de Certificação (%)': 'Taxa de Certificação (%)'},
            text='Taxa de Certificação (%)'
        )
        fig_taxa_certificacao_cargo.update_traces(textposition='outside')
        st.plotly_chart(fig_taxa_certificacao_cargo, use_container_width=True)


    # --- Tab 3: Análise por Secretaria ---
    with tab3:
        st.header('🏢 Desempenho Detalhado por Secretaria/Órgão')

        # Gráfico 3: Ranking de Inscrições por Secretaria (Filtrado)
        df_inscritos_secretaria = df_filtrado.groupby('SECRETARIA/ÓRGÃO')['Nº INSCRITOS'].sum().sort_values(ascending=False).reset_index()
        fig_inscritos_secretaria = px.bar(
            df_inscritos_secretaria,
            x='SECRETARIA/ÓRGÃO',
            y='Nº INSCRITOS',
            title='Total de Inscritos por Secretaria/Órgão (Filtrado)',
            labels={'SECRETARIA/ÓRGÃO': 'Secretaria / Órgão', 'Nº INSCRITOS': 'Número de Inscritos'},
            text='Nº INSCRITOS'
        )
        fig_inscritos_secretaria.update_traces(textposition='outside')
        st.plotly_chart(fig_inscritos_secretaria, use_container_width=True)

        # Gráfico 4: Ranking de Desempenho (Taxa de Certificação) por Secretaria (Filtrado)
        df_desempenho_secretaria = df_filtrado.groupby('SECRETARIA/ÓRGÃO')[['Nº INSCRITOS', 'Nº CERTIFICADOS']].sum().reset_index()
        df_desempenho_secretaria['Taxa de Certificação (%)'] = \
            (df_desempenho_secretaria['Nº CERTIFICADOS'] / df_desempenho_secretaria['Nº INSCRITOS'] * 100).round(2).fillna(0)
        df_desempenho_secretaria_ordenado = df_desempenho_secretaria.sort_values(by='Taxa de Certificação (%)', ascending=False)

        fig_taxa_secretaria = px.bar(
            df_desempenho_secretaria_ordenado,
            x='SECRETARIA/ÓRGÃO',
            y='Taxa de Certificação (%)',
            title='Taxa de Certificação por Secretaria/Órgão (Filtrado)',
            labels={'SECRETARIA/ÓRGÃO': 'Secretaria / Órgão', 'Taxa de Certificação (%)': 'Taxa de Certificação (%)'},
            text='Taxa de Certificação (%)'
        )
        fig_taxa_secretaria.update_traces(textposition='outside')
        st.plotly_chart(fig_taxa_secretaria, use_container_width=True)

        # Gráfico 5: Comparativo Agrupado (Inscritos, Certificados, Evasão) por Secretaria (Filtrado)
        fig_balanco_secretaria = px.bar(
            df_filtrado.sort_values(by='Nº INSCRITOS', ascending=False),
            x='SECRETARIA/ÓRGÃO',
            y=['Nº INSCRITOS', 'Nº CERTIFICADOS', 'Nº EVASÃO'],
            title='Balanço por Secretaria/Órgão (Filtrado)',
            labels={'SECRETARIA/ÓRGÃO': 'Secretaria / Órgão', 'value': 'Quantidade', 'variable': 'Métrica'},
            barmode='group'
        )
        st.plotly_chart(fig_balanco_secretaria, use_container_width=True)