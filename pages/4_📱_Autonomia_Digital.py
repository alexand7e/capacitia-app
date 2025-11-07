"""Dashboard CapacitIA Autonomia Digital."""

import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.io as pio
import numpy as np
import sys
from datetime import datetime
import re
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.loaders import load_autonomia_digital_data
from src.utils.constants import DESCRIPTIONS, COLORS

# =========================
# CONFIG & THEME
# =========================
st.set_page_config(
    page_title="CapacitIA Autonomia Digital",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Plotly theme
pio.templates["capacit_dark"] = pio.templates["plotly_dark"]
pio.templates["capacit_dark"].layout.font.family = "Inter, Segoe UI, Roboto, Arial"
pio.templates["capacit_dark"].layout.colorway = [
    "#7DD3FC", "#34D399", "#FBBF24", "#F472B6", "#60A5FA", "#A78BFA", "#F87171"
]
pio.templates["capacit_dark"].layout.paper_bgcolor = "#0f1220"
pio.templates["capacit_dark"].layout.plot_bgcolor = "#11142a"
pio.templates["capacit_dark"].layout.hoverlabel = dict(
    bgcolor="#0f1220", font_size=12, font_family="Inter, Segoe UI, Roboto, Arial"
)
pio.templates.default = "capacit_dark"

# =========================
# CSS GLOBAL
# =========================
with open("styles/main.css", "r", encoding="utf-8") as f:
    css_content = f.read()
st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# =========================
# CARREGAR DADOS
# =========================
df_inscricoes, df_avaliacoes = load_autonomia_digital_data()

if df_inscricoes is None or df_avaliacoes is None:
    st.error("Erro ao carregar dados. Verifique se os arquivos Parquet foram gerados.")
    st.stop()

# =========================
# HEADER
# =========================
st.title("📱 CapacitIA Autonomia Digital")
st.markdown(f"""
<div style="color: {COLORS['muted']}; margin-bottom: 24px;">
{DESCRIPTIONS['autonomia_digital'].strip()}
</div>
<div style="color: {COLORS['muted']}; font-size: 0.9rem;">
Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
</div>
""", unsafe_allow_html=True)

# Botão para voltar à home
if st.button("🏠 Voltar à Home", key="btn_home_autonomia"):
    st.switch_page("app.py")

# =========================
# KPIs PRINCIPAIS
# =========================
st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_inscritos = len(df_inscricoes)
total_avaliacoes = len(df_avaliacoes)
taxa_avaliacao = (total_avaliacoes / total_inscritos * 100) if total_inscritos > 0 else 0

# Calcular taxa de aposentados
aposentados_col = [c for c in df_inscricoes.columns if 'aposentado' in c.lower()][0] if any('aposentado' in c.lower() for c in df_inscricoes.columns) else None
perc_aposentados = 0
if aposentados_col:
    aposentados = df_inscricoes[aposentados_col].astype(str).str.contains('Sim', case=False, na=False).sum()
    perc_aposentados = (aposentados / total_inscritos * 100) if total_inscritos > 0 else 0

# Calcular satisfação média
avaliacao_col = [c for c in df_avaliacoes.columns if 'avaliacao_evento' in c.lower()][0] if any('avaliacao_evento' in c.lower() for c in df_avaliacoes.columns) else None
satisfacao_media = 0
if avaliacao_col:
    try:
        avaliacoes_numericas = pd.to_numeric(df_avaliacoes[avaliacao_col], errors='coerce')
        satisfacao_media = avaliacoes_numericas.mean() if not avaliacoes_numericas.isna().all() else 0
    except:
        pass

col1.markdown(f'<div class="kpi"><h4>Total de Inscritos</h4><div class="val">{total_inscritos:,}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="kpi"><h4>Total de Avaliações</h4><div class="val">{total_avaliacoes:,}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="kpi"><h4>Taxa de Avaliação</h4><div class="val">{taxa_avaliacao:.1f}%</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="kpi"><h4>Aposentados</h4><div class="val">{perc_aposentados:.0f}%</div></div>', unsafe_allow_html=True)

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# FILTROS
# =========================
st.markdown('<h3>🔍 Filtros</h3>', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)

with col_f1:
    # Filtro por projeto de extensão
    projeto_col = [c for c in df_inscricoes.columns if 'projeto' in c.lower() and 'extensao' in c.lower()][0] if any('projeto' in c.lower() and 'extensao' in c.lower() for c in df_inscricoes.columns) else None
    if projeto_col:
        projetos_disponiveis = ["Todos"] + sorted(df_inscricoes[projeto_col].dropna().unique().tolist())
        projeto_selecionado = st.selectbox(
            "📚 Projeto de Extensão",
            projetos_disponiveis,
            index=0,
            key="filtro_projeto"
        )
    else:
        projeto_selecionado = "Todos"

with col_f2:
    # Filtro por período (baseado na data de inscrição)
    data_col = [c for c in df_inscricoes.columns if 'data' in c.lower() or 'carimbo' in c.lower()][0] if any('data' in c.lower() or 'carimbo' in c.lower() for c in df_inscricoes.columns) else None
    if data_col:
        # Extrair períodos únicos se possível
        periodo_selecionado = st.selectbox(
            "📅 Período",
            ["Todos"],
            index=0,
            key="filtro_periodo"
        )
    else:
        periodo_selecionado = "Todos"

# Aplicar filtros
df_inscricoes_filtrado = df_inscricoes.copy()
if projeto_selecionado != "Todos" and projeto_col:
    df_inscricoes_filtrado = df_inscricoes_filtrado[df_inscricoes_filtrado[projeto_col] == projeto_selecionado]

st.markdown('<div class="sep"></div>', unsafe_allow_html=True)

# =========================
# ABAS
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Visão Geral", "📝 Inscrições", "⭐ Avaliações", "🎓 Aprendizados"])

# --------- Visão Geral
with tab1:
    colA, colB = st.columns(2)
    
    with colA:
        st.markdown('<div class="panel"><h3>Participantes por Projeto de Extensão</h3>', unsafe_allow_html=True)
        if projeto_col:
            participantes_por_projeto = df_inscricoes_filtrado.groupby(projeto_col).size().reset_index(name='Total')
            participantes_por_projeto = participantes_por_projeto.sort_values('Total', ascending=True)
            
            if not participantes_por_projeto.empty:
                fig = px.bar(
                    participantes_por_projeto, 
                    x='Total', 
                    y=projeto_col, 
                    orientation='h',
                    title=None,
                    text='Total'
                )
                fig.update_traces(texttemplate='%{text}', textposition='outside', cliponaxis=False)
                fig.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title=None,
                    yaxis_title=None
                )
                st.plotly_chart(fig, use_container_width=True, key="autonomia_projeto_bar")
            else:
                st.info("Sem dados para plotar.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with colB:
        st.markdown('<div class="panel"><h3>Distribuição de Aposentados</h3>', unsafe_allow_html=True)
        if aposentados_col:
            aposentados_dist = df_inscricoes_filtrado[aposentados_col].value_counts()
            
            if not aposentados_dist.empty:
                fig_pie = px.pie(
                    values=aposentados_dist.values,
                    names=aposentados_dist.index,
                    hole=0.55,
                    title=None
                )
                fig_pie.update_traces(textinfo='percent+label', textposition='inside')
                fig_pie.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="v", y=0.5, yanchor="middle", x=1.02)
                )
                st.plotly_chart(fig_pie, use_container_width=True, key="autonomia_aposentados_pie")
            else:
                st.info("Sem dados para plotar.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Temas de maior dificuldade
    st.markdown('<div class="panel"><h3>Temas de Maior Dificuldade</h3>', unsafe_allow_html=True)
    dificuldade_col = [c for c in df_inscricoes.columns if 'dificuldade' in c.lower()][0] if any('dificuldade' in c.lower() for c in df_inscricoes.columns) else None
    if dificuldade_col:
        # Contar temas mencionados
        temas = df_inscricoes_filtrado[dificuldade_col].dropna().astype(str)
        
        if not temas.empty:
            # Preparar texto para nuvem de palavras
            # Remover valores vazios e "nan"
            temas_limpos = temas[~temas.str.lower().isin(['nan', 'none', '', 'na'])]
            
            if len(temas_limpos) > 0:
                # Criar dicionário de frequências (contar ocorrências de cada tema)
                temas_texto = ' '.join(temas_limpos.tolist())
                
                # Limpar e processar texto
                temas_texto = re.sub(r'[^\w\s]', ' ', temas_texto)  # Remove pontuação
                palavras = temas_texto.lower().split()
                
                # Criar dicionário de frequências
                freq_dict = {}
                for palavra in palavras:
                    if len(palavra) > 2:  # Ignorar palavras muito curtas
                        freq_dict[palavra] = freq_dict.get(palavra, 0) + 1
                
                # Se não houver frequências suficientes, usar contagem simples
                if not freq_dict:
                    temas_contagem = temas_limpos.value_counts()
                    freq_dict = {str(k): int(v) for k, v in temas_contagem.items() if len(str(k)) > 2}
                
                if freq_dict:
                    # Criar nuvem de palavras com tema escuro
                    fig_wordcloud, ax = plt.subplots(figsize=(12, 6), facecolor='#0f1220')
                    ax.set_facecolor('#0f1220')
                    
                    wordcloud = WordCloud(
                        width=1200,
                        height=600,
                        background_color='#0f1220',
                        colormap='viridis',  # Usar cores vibrantes
                        max_words=100,
                        relative_scaling=0.5,
                        min_font_size=10,
                        max_font_size=80,
                        prefer_horizontal=0.7
                    ).generate_from_frequencies(freq_dict)
                    
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    
                    # Ajustar cores do texto para tema escuro
                    plt.tight_layout(pad=0)
                    
                    # Converter para imagem e exibir no Streamlit
                    img_buffer = io.BytesIO()
                    fig_wordcloud.savefig(img_buffer, format='png', facecolor='#0f1220', bbox_inches='tight', pad_inches=0)
                    img_buffer.seek(0)
                    
                    st.image(img_buffer, use_container_width=True)
                    plt.close(fig_wordcloud)
                    
                    # Também mostrar gráfico de barras com top temas
                    st.markdown("### Top 10 Temas Mais Mencionados")
                    temas_contagem = temas_limpos.value_counts().head(10)
                    
                    if not temas_contagem.empty:
                        fig_temas = px.bar(
                            x=temas_contagem.values,
                            y=temas_contagem.index,
                            orientation='h',
                            title=None
                        )
                        fig_temas.update_layout(
                            height=400,
                            margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title="Menções",
                            yaxis_title="Temas",
                            plot_bgcolor='#11142a',
                            paper_bgcolor='#0f1220',
                            font_color='#e6e7ee'
                        )
                        fig_temas.update_traces(marker_color='#7DD3FC')
                        st.plotly_chart(fig_temas, use_container_width=True, key="autonomia_temas")
                else:
                    st.info("Sem dados suficientes para gerar nuvem de palavras.")
            else:
                st.info("Sem dados de temas de dificuldade.")
        else:
            st.info("Sem dados de temas de dificuldade.")
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Inscrições
with tab2:
    st.markdown('<div class="panel"><h3>Análise de Inscrições</h3>', unsafe_allow_html=True)
    
    # Estatísticas de inscrições
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Total de Inscritos", len(df_inscricoes_filtrado))
    with col_stat2:
        if aposentados_col:
            aposentados_count = df_inscricoes_filtrado[aposentados_col].astype(str).str.contains('Sim', case=False, na=False).sum()
            st.metric("Aposentados", aposentados_count)
    with col_stat3:
        lgpd_col = [c for c in df_inscricoes.columns if 'autorizo' in c.lower() or 'lgpd' in c.lower()][0] if any('autorizo' in c.lower() or 'lgpd' in c.lower() for c in df_inscricoes.columns) else None
        if lgpd_col:
            autorizacoes = df_inscricoes_filtrado[lgpd_col].astype(str).str.contains('Confirmo', case=False, na=False).sum()
            st.metric("Autorizações LGPD", autorizacoes)
    
    # Projetos de extensão
    if projeto_col:
        st.markdown("### Projetos de Extensão")
        projetos_contagem = df_inscricoes_filtrado[projeto_col].value_counts()
        st.dataframe(projetos_contagem.reset_index(), use_container_width=True)
    
    # Temas de dificuldade mais comuns
    if dificuldade_col:
        st.markdown("### Temas de Dificuldade Mais Comuns")
        temas_df = df_inscricoes_filtrado[dificuldade_col].value_counts().head(10).reset_index()
        temas_df.columns = ['Tema', 'Quantidade']
        st.dataframe(temas_df, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Avaliações
with tab3:
    st.markdown('<div class="panel"><h3>Análise de Avaliações</h3>', unsafe_allow_html=True)
    
    # Satisfação geral
    if avaliacao_col:
        avaliacoes_numericas = pd.to_numeric(df_avaliacoes[avaliacao_col], errors='coerce')
        if not avaliacoes_numericas.isna().all():
            col_aval1, col_aval2, col_aval3 = st.columns(3)
            with col_aval1:
                st.metric("Satisfação Média", f"{avaliacoes_numericas.mean():.1f}/5")
            with col_aval2:
                st.metric("Avaliações Positivas (4-5)", f"{(avaliacoes_numericas >= 4).sum()}")
            with col_aval3:
                st.metric("Total de Avaliações", len(df_avaliacoes))
            
            # Distribuição de avaliações
            fig_dist = px.histogram(
                avaliacoes_numericas.dropna(),
                nbins=5,
                title="Distribuição de Avaliações",
                labels={'value': 'Nota', 'count': 'Quantidade'}
            )
            fig_dist.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=50, b=10)
            )
            st.plotly_chart(fig_dist, use_container_width=True, key="autonomia_avaliacao_dist")
    
    # Avaliações por dimensão
    st.markdown("### Avaliações por Dimensão")
    dimensoes = {
        'Conteúdo': [c for c in df_avaliacoes.columns if 'conteudo' in c.lower()],
        'Local': [c for c in df_avaliacoes.columns if 'local' in c.lower()],
        'Atendimento': [c for c in df_avaliacoes.columns if 'atendimento' in c.lower() or 'acolhimento' in c.lower()],
    }
    
    col_dim1, col_dim2, col_dim3 = st.columns(3)
    for i, (dimensao, cols) in enumerate(dimensoes.items()):
        if cols:
            col_dimensao = cols[0]
            avaliacoes_dim = pd.to_numeric(df_avaliacoes[col_dimensao], errors='coerce')
            if not avaliacoes_dim.isna().all():
                media = avaliacoes_dim.mean()
                with [col_dim1, col_dim2, col_dim3][i]:
                    st.metric(dimensao, f"{media:.1f}/5")
    
    # Sugestões e feedback
    sugestoes_col = [c for c in df_avaliacoes.columns if 'sugestao' in c.lower() or 'elogio' in c.lower() or 'reclamacao' in c.lower()][0] if any('sugestao' in c.lower() or 'elogio' in c.lower() or 'reclamacao' in c.lower() for c in df_avaliacoes.columns) else None
    if sugestoes_col:
        st.markdown("### Sugestões, Elogios e Reclamações")
        sugestoes = df_avaliacoes[sugestoes_col].dropna()
        sugestoes_validas = sugestoes[sugestoes.astype(str).str.strip() != '']
        if len(sugestoes_validas) > 0:
            # Nuvem de palavras para sugestões
            sugestoes_texto = ' '.join(sugestoes_validas.astype(str).tolist())
            sugestoes_texto = re.sub(r'[^\w\s]', ' ', sugestoes_texto)
            palavras_sugestoes = sugestoes_texto.lower().split()
            
            # Criar dicionário de frequências
            freq_dict_sugestoes = {}
            for palavra in palavras_sugestoes:
                if len(palavra) > 3:  # Ignorar palavras muito curtas
                    freq_dict_sugestoes[palavra] = freq_dict_sugestoes.get(palavra, 0) + 1
            
            if freq_dict_sugestoes:
                # Criar nuvem de palavras
                fig_wordcloud_sug, ax_sug = plt.subplots(figsize=(12, 6), facecolor='#0f1220')
                ax_sug.set_facecolor('#0f1220')
                
                wordcloud_sug = WordCloud(
                    width=1200,
                    height=600,
                    background_color='#0f1220',
                    colormap='plasma',  # Cores diferentes para diferenciar
                    max_words=100,
                    relative_scaling=0.5,
                    min_font_size=10,
                    max_font_size=80,
                    prefer_horizontal=0.7
                ).generate_from_frequencies(freq_dict_sugestoes)
                
                ax_sug.imshow(wordcloud_sug, interpolation='bilinear')
                ax_sug.axis('off')
                plt.tight_layout(pad=0)
                
                # Converter para imagem
                img_buffer_sug = io.BytesIO()
                fig_wordcloud_sug.savefig(img_buffer_sug, format='png', facecolor='#0f1220', bbox_inches='tight', pad_inches=0)
                img_buffer_sug.seek(0)
                
                st.image(img_buffer_sug, use_container_width=True)
                plt.close(fig_wordcloud_sug)
            
            # Tabela com sugestões (opcional, pode ser colapsada)
            with st.expander("📋 Ver todas as sugestões em texto"):
                st.dataframe(sugestoes_validas.reset_index(drop=True), use_container_width=True, height=300)
        else:
            st.info("Nenhuma sugestão registrada.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --------- Aprendizados
with tab4:
    st.markdown('<div class="panel"><h3>O que os Participantes Aprenderam</h3>', unsafe_allow_html=True)
    
    # Mapear colunas de aprendizado
    aprendizados_map = {
        'Funções básicas do celular': [c for c in df_avaliacoes.columns if 'funcoes' in c.lower() and 'celular' in c.lower()],
        'Uso de e-mail': [c for c in df_avaliacoes.columns if 'email' in c.lower() and 'usar' in c.lower()],
        'Segurança digital': [c for c in df_avaliacoes.columns if 'seguranca' in c.lower() or 'confiaveis' in c.lower()],
        'IA no dia a dia': [c for c in df_avaliacoes.columns if 'inteligencia' in c.lower() or 'ia' in c.lower()],
        'Gov.pi Cidadão': [c for c in df_avaliacoes.columns if 'gov' in c.lower() and 'cidad' in c.lower()],
        'Piauí Saúde Digital': [c for c in df_avaliacoes.columns if 'saude' in c.lower() and 'digital' in c.lower()],
        'BO Fácil': [c for c in df_avaliacoes.columns if 'bo' in c.lower() and 'facil' in c.lower()],
    }
    
    aprendizados_data = []
    for aprendizado, cols in aprendizados_map.items():
        if cols:
            col_aprendizado = cols[0]
            sim_count = df_avaliacoes[col_aprendizado].astype(str).str.contains('Sim', case=False, na=False).sum()
            total = len(df_avaliacoes[df_avaliacoes[col_aprendizado].notna()])
            perc = (sim_count / total * 100) if total > 0 else 0
            aprendizados_data.append({
                'Aprendizado': aprendizado,
                'Aprenderam': sim_count,
                'Total': total,
                'Percentual': perc
            })
    
    if aprendizados_data:
        df_aprendizados = pd.DataFrame(aprendizados_data)
        df_aprendizados = df_aprendizados.sort_values('Percentual', ascending=True)
        
        fig_aprend = px.bar(
            df_aprendizados,
            x='Percentual',
            y='Aprendizado',
            orientation='h',
            title=None,
            text='Percentual'
        )
        fig_aprend.update_traces(texttemplate='%{text:.1f}%', textposition='outside', cliponaxis=False)
        fig_aprend.update_xaxes(ticksuffix="%", range=[0, 110])
        fig_aprend.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Percentual",
            yaxis_title=None
        )
        st.plotly_chart(fig_aprend, use_container_width=True, key="autonomia_aprendizados")
        
        # Matriz colorida (heatmap) para detalhamento
        st.markdown("### Detalhamento")
        # Criar matriz para heatmap
        matriz_data = df_aprendizados[['Aprendizado', 'Percentual']].set_index('Aprendizado')
        matriz_data = matriz_data.T  # Transpor para melhor visualização
        
        # Criar heatmap
        fig_heatmap = px.imshow(
            matriz_data,
            labels=dict(x="Aprendizado", y="", color="Percentual (%)"),
            color_continuous_scale='Viridis',
            aspect="auto",
            text_auto='.1f'
        )
        fig_heatmap.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='#11142a',
            paper_bgcolor='#0f1220',
            font_color='#e6e7ee',
            xaxis=dict(side='bottom')
        )
        fig_heatmap.update_traces(textfont_size=12, textfont_color='white')
        st.plotly_chart(fig_heatmap, use_container_width=True, key="autonomia_heatmap")
        
        # Tabela também disponível (colapsada)
        with st.expander("📊 Ver dados em tabela"):
            st.dataframe(df_aprendizados, use_container_width=True)
    else:
        st.info("Sem dados de aprendizados disponíveis.")
    
    # Aprendizados extras
    extras_col = [c for c in df_avaliacoes.columns if 'extras' in c.lower() or 'registrar' in c.lower()][0] if any('extras' in c.lower() or 'registrar' in c.lower() for c in df_avaliacoes.columns) else None
    if extras_col:
        st.markdown("### Aprendizados Extras Registrados")
        extras = df_avaliacoes[extras_col].dropna()
        extras_validos = extras[extras.astype(str).str.strip() != '']
        if len(extras_validos) > 0:
            # Processar aprendizados extras para treemap
            extras_texto = ' '.join(extras_validos.astype(str).tolist())
            extras_texto = re.sub(r'[^\w\s]', ' ', extras_texto)
            palavras_extras = extras_texto.lower().split()
            
            # Criar dicionário de frequências
            freq_dict_extras = {}
            for palavra in palavras_extras:
                if len(palavra) > 3:  # Ignorar palavras muito curtas
                    freq_dict_extras[palavra] = freq_dict_extras.get(palavra, 0) + 1
            
            # Criar DataFrame para treemap
            if freq_dict_extras:
                df_treemap = pd.DataFrame([
                    {'Aprendizado': k, 'Frequência': v} 
                    for k, v in sorted(freq_dict_extras.items(), key=lambda x: x[1], reverse=True)[:30]
                ])
                
                # Criar treemap
                fig_treemap = px.treemap(
                    df_treemap,
                    path=['Aprendizado'],
                    values='Frequência',
                    title=None,
                    color='Frequência',
                    color_continuous_scale='Blues'
                )
                fig_treemap.update_traces(
                    textinfo='label+value',
                    texttemplate='<b>%{label}</b><br>%{value}',
                    textposition='middle center',
                    hovertemplate='<b>%{label}</b><br>Frequência: %{value}<extra></extra>'
                )
                fig_treemap.update_layout(
                    height=500,
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor='#11142a',
                    paper_bgcolor='#0f1220',
                    font_color='#e6e7ee'
                )
                st.plotly_chart(fig_treemap, use_container_width=True, key="autonomia_extras_treemap")
            
            # Tabela também disponível (colapsada)
            with st.expander("📋 Ver todos os aprendizados extras em texto"):
                st.dataframe(extras_validos.reset_index(drop=True), use_container_width=True, height=300)
        else:
            st.info("Nenhum aprendizado extra registrado.")
    
    st.markdown('</div>', unsafe_allow_html=True)
