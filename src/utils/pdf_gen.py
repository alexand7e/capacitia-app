"""Gerador de relatórios PDF para CapacitIA Servidores."""

from datetime import datetime
import os
import io
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def criar_grafico_plotly_para_pdf(fig, width=500, height=300):
    """Converte um gráfico Plotly em imagem para inclusão no PDF."""
    # Configurar fundo transparente e fonte preta
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(color='black', size=12),
        title_font=dict(color='black', size=16),
        coloraxis_colorbar=dict(
            tickfont=dict(color='black'),
            title_font=dict(color='black')
        )
    )
    # Atualizar cores de texto nos traces
    fig.update_traces(
        textfont=dict(color='black')
    )
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    return Image(io.BytesIO(img_bytes), width=width*0.7, height=height*0.7)


def header_footer_capacitia(canvas, doc):
    """Cabeçalho e rodapé para o relatório CapacitIA com imagem de fundo."""
    canvas.saveState()
    page_width, page_height = A4
    
    # Tentar carregar e desenhar a imagem de fundo
    try:
        from pathlib import Path
        from reportlab.lib.utils import ImageReader
        
        # Caminho para a imagem de fundo
        img_path = Path("styles") / "fundo.png"
        
        if img_path.exists():
            img = ImageReader(str(img_path))
            # Desenhar a imagem cobrindo toda a página
            canvas.drawImage(
                img,
                0,
                0,
                width=page_width,
                height=page_height,
                preserveAspectRatio=False,
                mask='auto'
            )
    except Exception as e:
        # Se houver erro ao carregar a imagem, usar cabeçalho/rodapé simples
        print(f"Aviso: Não foi possível carregar imagem de fundo: {e}")
        
        # Cabeçalho alternativo (sem imagem)
        canvas.setFillColor(colors.HexColor("#1E3A8A"))
        canvas.rect(0, page_height - 0.8*inch, page_width, 0.8*inch, fill=True, stroke=False)
        
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(0.75*inch, page_height - 0.5*inch, "CapacitIA Servidores - Relatório Analítico")
    
    # Rodapé (sempre desenhado)
    canvas.setFillColor(colors.HexColor("#1E3A8A"))
    canvas.rect(0, 0, page_width, 0.5*inch, fill=True, stroke=False)
    
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(0.75*inch, 0.25*inch, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    canvas.drawRightString(page_width - 0.75*inch, 0.25*inch, f"Página {doc.page}")
    
    canvas.restoreState()


def gerar_relatorio_capacitia(df_dados, df_visao, df_secretarias, df_cargos, df_orgaos_parceiros=None, nome_arquivo="relatorio_capacitia.pdf"):
    """
    Gera relatório PDF completo do CapacitIA Servidores.
    
    Args:
        df_dados: DataFrame com dados individuais de participantes
        df_visao: DataFrame com visão consolidada de eventos
        df_secretarias: DataFrame com dados por secretaria
        df_cargos: DataFrame com dados por cargo
        nome_arquivo: Nome do arquivo PDF a ser gerado
    
    Returns:
        Caminho completo do arquivo gerado ou None em caso de erro
    """
    try:
        # Criar diretório de relatórios se não existir
        reports_dir = Path(".data") / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        caminho_completo = reports_dir / nome_arquivo
        
        # Configurar documento
        doc = SimpleDocTemplate(
            str(caminho_completo),
            pagesize=A4,
            topMargin=1.2*inch,
            bottomMargin=0.8*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=colors.HexColor("#1E3A8A"),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=12,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        section_style = ParagraphStyle(
            'CustomSection',
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=20,
            spaceAfter=12,
            borderPadding=(0, 0, 5, 0),
            borderColor=colors.HexColor("#1E3A8A"),
            borderWidth=2,
            borderRadius=None
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.HexColor("#334155"),
            spaceAfter=8,
            alignment=TA_LEFT
        )
        
        kpi_style = ParagraphStyle(
            'KPIStyle',
            parent=styles['Normal'],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=colors.HexColor("#1E3A8A"),
            alignment=TA_CENTER
        )
        
        # Elementos do documento
        elementos = []
        
        # ===== CAPA =====
        elementos.append(Spacer(1, 1.5*inch))
        elementos.append(Paragraph("Relatório Analítico", title_style))
        elementos.append(Paragraph("CapacitIA Servidores", title_style))
        elementos.append(Spacer(1, 0.3*inch))
        elementos.append(Paragraph(
            f"Período de análise: Dados consolidados até {datetime.now().strftime('%d/%m/%Y')}",
            subtitle_style
        ))
        elementos.append(Spacer(1, 0.2*inch))
        elementos.append(Paragraph(
            "Este relatório apresenta uma análise completa do programa CapacitIA Servidores, "
            "incluindo métricas de participação, certificação e análises por tipo de evento, "
            "secretaria e cargo.",
            body_style
        ))
        elementos.append(PageBreak())
        
        # ===== SUMÁRIO EXECUTIVO =====
        elementos.append(Paragraph("1. Sumário Executivo", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        # Calcular KPIs principais
        total_participantes = len(df_dados)
        total_certificados = (df_dados['certificado'] == 'Sim').sum() if 'certificado' in df_dados.columns else 0
        taxa_certificacao = (total_certificados / total_participantes * 100) if total_participantes > 0 else 0
        total_eventos = len(df_visao) if df_visao is not None else 0
        total_secretarias = df_dados['orgao'].nunique() if 'orgao' in df_dados.columns else 0
        
        # Tabela de KPIs
        kpi_data = [
            ['Métrica', 'Valor'],
            ['Total de Participantes', f'{total_participantes:,}'.replace(',', '.')],
            ['Total de Certificados', f'{total_certificados:,}'.replace(',', '.')],
            ['Taxa de Certificação', f'{taxa_certificacao:.1f}%'],
            ['Total de Eventos', str(total_eventos)],
            ['Secretarias Atendidas', str(total_secretarias)],
        ]
        
        kpi_table = Table(kpi_data, colWidths=[3.5*inch, 2*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        
        elementos.append(kpi_table)
        elementos.append(Spacer(1, 0.3*inch))
        
        # Destaques
        elementos.append(Paragraph("<b>Principais Destaques:</b>", body_style))
        elementos.append(Spacer(1, 0.1*inch))
        
        # Análise por formato
        if 'formato' in df_dados.columns:
            formato_counts = df_dados['formato'].value_counts()
            formato_mais_popular = formato_counts.index[0] if len(formato_counts) > 0 else "N/A"
            elementos.append(Paragraph(
                f"• <b>Tipo de evento mais popular:</b> {formato_mais_popular} ({formato_counts.iloc[0]} participantes)",
                body_style
            ))
        
        # Top secretaria
        if 'orgao' in df_dados.columns:
            top_secretaria = df_dados['orgao'].value_counts().index[0]
            top_secretaria_count = df_dados['orgao'].value_counts().iloc[0]
            elementos.append(Paragraph(
                f"• <b>Secretaria com maior participação:</b> {top_secretaria} ({top_secretaria_count} participantes)",
                body_style
            ))
        
        elementos.append(PageBreak())
        
        # ===== ANÁLISE POR TIPO DE EVENTO =====
        elementos.append(Paragraph("2. Análise por Tipo de Evento", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        if 'formato' in df_dados.columns and df_visao is not None:
            # Métricas por tipo
            metricas_tipo = df_visao.groupby('formato').agg({
                'evento': 'count',
                'n_inscritos': ['sum', 'mean'],
                'n_certificados': ['sum', 'mean']
            }).round(1)
            
            metricas_tipo.columns = ['Num_Eventos', 'Total_Inscritos', 'Media_Inscritos', 
                                      'Total_Certificados', 'Media_Certificados']
            metricas_tipo['Taxa_Cert'] = (metricas_tipo['Total_Certificados'] / 
                                          metricas_tipo['Total_Inscritos'] * 100).round(1)
            metricas_tipo = metricas_tipo.reset_index()
            
            # Tabela de métricas por tipo
            tipo_data = [['Tipo', 'Nº Eventos', 'Total Part.', 'Média Part.', 'Taxa Cert.']]
            for _, row in metricas_tipo.iterrows():
                tipo_data.append([
                    row['formato'],
                    str(int(row['Num_Eventos'])),
                    f"{int(row['Total_Inscritos']):,}".replace(',', '.'),
                    f"{row['Media_Inscritos']:.1f}",
                    f"{row['Taxa_Cert']:.1f}%"
                ])
            
            tipo_table = Table(tipo_data, colWidths=[1.5*inch, 1*inch, 1.2*inch, 1.2*inch, 1.2*inch])
            tipo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            
            elementos.append(tipo_table)
            elementos.append(Spacer(1, 0.3*inch))
            
            # Gráfico de distribuição por tipo
            fig_tipo = px.bar(
                metricas_tipo,
                x='formato',
                y='Total_Inscritos',
                title='Distribuição de Participantes por Tipo de Evento',
                labels={'formato': 'Tipo de Evento', 'Total_Inscritos': 'Total de Participantes'},
                color='formato',
                color_discrete_map={
                    'Curso': '#4CAF50',
                    'Masterclass': '#2196F3',
                    'Workshop': '#FF9800'
                }
            )
            fig_tipo.update_layout(showlegend=False, height=300)
            
            elementos.append(criar_grafico_plotly_para_pdf(fig_tipo))
        
        elementos.append(PageBreak())
        
        # ===== ANÁLISE POR SECRETARIA =====
        elementos.append(Paragraph("3. Análise por Secretaria/Órgão", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        if 'orgao' in df_dados.columns:
            # Preparar dados para treemap
            secretarias_data = df_dados.groupby('orgao').agg({
                'orgao': 'count',
                'certificado': lambda x: (x == 'Sim').sum()
            }).rename(columns={'orgao': 'Participantes', 'certificado': 'Certificados'})
            secretarias_data['Taxa_Cert'] = (secretarias_data['Certificados'] / 
                                             secretarias_data['Participantes'] * 100).round(1)
            secretarias_data = secretarias_data.sort_values('Participantes', ascending=False).head(20)
            secretarias_data = secretarias_data.reset_index()
            
            # Criar treemap de secretarias
            fig_secretarias = px.treemap(
                secretarias_data,
                path=['orgao'],
                values='Participantes',
                color='Taxa_Cert',
                color_continuous_scale='RdYlGn',
                title='Distribuição de Participantes por Secretaria/Órgão (Top 20)',
                hover_data={'Participantes': True, 'Certificados': True, 'Taxa_Cert': ':.1f'},
                labels={'orgao': 'Secretaria', 'Participantes': 'Participantes', 'Taxa_Cert': 'Taxa Cert. (%)'}
            )
            fig_secretarias.update_traces(
                texttemplate="<b>%{label}</b><br>%{value} part.<br>%{color:.1f}% cert.",
                textposition="middle center",
                textfont_size=10
            )
            fig_secretarias.update_layout(height=600)
            
            elementos.append(Paragraph(
                "Treemap mostrando as 20 secretarias com maior participação. "
                "O tamanho representa o número de participantes e a cor indica a taxa de certificação.",
                body_style
            ))
            elementos.append(Spacer(1, 0.1*inch))
            elementos.append(criar_grafico_plotly_para_pdf(fig_secretarias, width=700, height=600))
        
        elementos.append(PageBreak())
        
        # ===== ANÁLISE POR CARGO =====
        elementos.append(Paragraph("4. Análise por Cargo", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        if 'cargo' in df_dados.columns:
            # Preparar dados para treemap
            cargos_data = df_dados['cargo'].value_counts().head(20).reset_index()
            cargos_data.columns = ['Cargo', 'Participantes']
            
            # Criar treemap de cargos
            fig_cargos = px.treemap(
                cargos_data,
                path=['Cargo'],
                values='Participantes',
                title='Distribuição de Participantes por Cargo (Top 20)',
                color='Participantes',
                color_continuous_scale='Blues',
                hover_data={'Participantes': True}
            )
            fig_cargos.update_traces(
                texttemplate="<b>%{label}</b><br>%{value} participantes",
                textposition="middle center",
                textfont_size=10
            )
            fig_cargos.update_layout(height=600)
            
            elementos.append(Paragraph(
                "Treemap mostrando os 20 cargos com maior participação. "
                "O tamanho e a cor representam o número de participantes.",
                body_style
            ))
            elementos.append(Spacer(1, 0.1*inch))
            elementos.append(criar_grafico_plotly_para_pdf(fig_cargos, width=700, height=600))
            
            # Tabela detalhada de cargos
            elementos.append(Spacer(1, 0.3*inch))
            elementos.append(Paragraph("<b>Top 10 Cargos por Participação:</b>", body_style))
            elementos.append(Spacer(1, 0.1*inch))
            
            if df_cargos is not None and len(df_cargos) > 0:
                # Preparar dados de cargos com mais detalhes
                if 'cargo' in df_cargos.columns and 'total_inscritos' in df_cargos.columns:
                    top_cargos = df_cargos.nlargest(10, 'total_inscritos')[['cargo', 'total_inscritos', 'n_gestores', 'perc_gestores']]
                    cargo_table_data = [['Cargo', 'Inscritos', 'Gestores', '% Gestores']]
                    for _, row in top_cargos.iterrows():
                        cargo_table_data.append([
                            str(row['cargo'])[:30],
                            str(int(row['total_inscritos'])),
                            str(int(row['n_gestores'])) if pd.notna(row['n_gestores']) else '0',
                            f"{row['perc_gestores']:.1f}%" if pd.notna(row['perc_gestores']) else "0%"
                        ])
                    
                    cargo_table = Table(cargo_table_data, colWidths=[3*inch, 1*inch, 1*inch, 1*inch])
                    cargo_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ]))
                    elementos.append(cargo_table)
        
        elementos.append(PageBreak())
        
        # ===== ANÁLISE DE ÓRGÃOS PARCEIROS =====
        elementos.append(Paragraph("5. Análise de Órgãos Parceiros", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        if df_orgaos_parceiros is not None and len(df_orgaos_parceiros) > 0:
            elementos.append(Paragraph(
                "Esta seção apresenta uma análise detalhada dos órgãos parceiros (externos) "
                "que participaram do programa CapacitIA Servidores.",
                body_style
            ))
            elementos.append(Spacer(1, 0.2*inch))
            
            # KPIs de órgãos parceiros
            total_parceiros = len(df_orgaos_parceiros)
            total_inscritos_parceiros = df_orgaos_parceiros['n_inscritos'].sum()
            total_certificados_parceiros = df_orgaos_parceiros['n_certificados'].sum()
            taxa_cert_parceiros = (total_certificados_parceiros / total_inscritos_parceiros * 100) if total_inscritos_parceiros > 0 else 0
            
            parceiros_kpi_data = [
                ['Métrica', 'Valor'],
                ['Total de Órgãos Parceiros', str(total_parceiros)],
                ['Total de Inscritos', f'{total_inscritos_parceiros:,}'.replace(',', '.')],
                ['Total de Certificados', f'{total_certificados_parceiros:,}'.replace(',', '.')],
                ['Taxa de Certificação', f'{taxa_cert_parceiros:.1f}%'],
            ]
            
            parceiros_kpi_table = Table(parceiros_kpi_data, colWidths=[3.5*inch, 2*inch])
            parceiros_kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elementos.append(parceiros_kpi_table)
            elementos.append(Spacer(1, 0.3*inch))
            
            # Gráfico de barras dos top órgãos parceiros
            top_parceiros = df_orgaos_parceiros.head(15).sort_values('n_inscritos', ascending=True)
            fig_parceiros = px.bar(
                top_parceiros,
                x='n_inscritos',
                y='orgao_parceiro',
                orientation='h',
                title='Top 15 Órgãos Parceiros por Número de Inscritos',
                labels={'n_inscritos': 'Inscritos', 'orgao_parceiro': 'Órgão Parceiro'}
            )
            fig_parceiros.update_layout(height=500, showlegend=False)
            elementos.append(criar_grafico_plotly_para_pdf(fig_parceiros, width=700, height=500))
            elementos.append(Spacer(1, 0.3*inch))
            
            # Tabela detalhada de órgãos parceiros
            elementos.append(Paragraph("<b>Detalhamento por Órgão Parceiro:</b>", body_style))
            elementos.append(Spacer(1, 0.1*inch))
            
            parceiros_table_data = [['Órgão Parceiro', 'Inscritos', 'Certificados', 'Taxa Cert.', 'Turmas']]
            for _, row in df_orgaos_parceiros.head(20).iterrows():
                parceiros_table_data.append([
                    str(row['orgao_parceiro'])[:25],
                    str(int(row['n_inscritos'])),
                    str(int(row['n_certificados'])),
                    f"{row['taxa_certificacao']:.1f}%",
                    str(int(row['n_turmas'])) if pd.notna(row['n_turmas']) else '0'
                ])
            
            parceiros_table = Table(parceiros_table_data, colWidths=[2.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            parceiros_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (4, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elementos.append(parceiros_table)
        else:
            elementos.append(Paragraph(
                "Nenhum dado de órgãos parceiros disponível para análise.",
                body_style
            ))
        
        elementos.append(PageBreak())
        
        # ===== ANÁLISES ESTATÍSTICAS AVANÇADAS =====
        elementos.append(Paragraph("6. Análises Estatísticas Avançadas", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        # Análise de distribuição por formato
        if 'formato' in df_dados.columns:
            elementos.append(Paragraph("<b>6.1. Distribuição Detalhada por Formato</b>", body_style))
            elementos.append(Spacer(1, 0.1*inch))
            
            formato_stats = df_dados.groupby('formato').agg({
                'nome': 'count',
                'certificado': lambda x: (x == 'Sim').sum()
            }).rename(columns={'nome': 'Total', 'certificado': 'Certificados'})
            formato_stats['Taxa_Cert'] = (formato_stats['Certificados'] / formato_stats['Total'] * 100).round(1)
            formato_stats = formato_stats.reset_index()
            
            formato_table_data = [['Formato', 'Total', 'Certificados', 'Taxa Cert. (%)']]
            for _, row in formato_stats.iterrows():
                formato_table_data.append([
                    str(row['formato']),
                    f"{int(row['Total']):,}".replace(',', '.'),
                    f"{int(row['Certificados']):,}".replace(',', '.'),
                    f"{row['Taxa_Cert']:.1f}%"
                ])
            
            formato_table = Table(formato_table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            formato_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (3, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elementos.append(formato_table)
            elementos.append(Spacer(1, 0.3*inch))
        
        # Análise de vínculo
        if 'vinculo' in df_dados.columns:
            elementos.append(Paragraph("<b>6.2. Análise por Vínculo</b>", body_style))
            elementos.append(Spacer(1, 0.1*inch))
            
            vinculo_stats = df_dados['vinculo'].value_counts().head(10).reset_index()
            vinculo_stats.columns = ['Vínculo', 'Total']
            
            vinculo_table_data = [['Vínculo', 'Total de Participantes']]
            for _, row in vinculo_stats.iterrows():
                vinculo_table_data.append([
                    str(row['Vínculo'])[:30],
                    f"{int(row['Total']):,}".replace(',', '.')
                ])
            
            vinculo_table = Table(vinculo_table_data, colWidths=[3.5*inch, 2*inch])
            vinculo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elementos.append(vinculo_table)
            elementos.append(Spacer(1, 0.3*inch))
        
        # Análise de local de realização
        if 'local_realizacao' in df_dados.columns:
            elementos.append(Paragraph("<b>6.3. Análise por Local de Realização</b>", body_style))
            elementos.append(Spacer(1, 0.1*inch))
            
            local_stats = df_dados.groupby('local_realizacao').agg({
                'nome': 'count',
                'certificado': lambda x: (x == 'Sim').sum()
            }).rename(columns={'nome': 'Total', 'certificado': 'Certificados'})
            local_stats = local_stats.sort_values('Total', ascending=False).head(10).reset_index()
            
            local_table_data = [['Local de Realização', 'Total', 'Certificados']]
            for _, row in local_stats.iterrows():
                local_table_data.append([
                    str(row['local_realizacao'])[:35],
                    f"{int(row['Total']):,}".replace(',', '.'),
                    f"{int(row['Certificados']):,}".replace(',', '.')
                ])
            
            local_table = Table(local_table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
            local_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ]))
            elementos.append(local_table)
        
        elementos.append(PageBreak())
        
        # ===== CONCLUSÕES E RECOMENDAÇÕES =====
        elementos.append(Paragraph("7. Conclusões e Recomendações", section_style))
        elementos.append(Spacer(1, 0.2*inch))
        
        elementos.append(Paragraph("<b>Principais Conclusões:</b>", body_style))
        elementos.append(Spacer(1, 0.1*inch))
        
        # Gerar conclusões baseadas nos dados
        conclusoes = []
        
        if total_participantes > 0:
            conclusoes.append(
                f"O programa CapacitIA Servidores alcançou {total_participantes:,} participantes, "
                f"demonstrando ampla adesão e interesse pela capacitação em Inteligência Artificial."
            )
        
        if taxa_certificacao > 0:
            conclusoes.append(
                f"A taxa de certificação de {taxa_certificacao:.1f}% indica um bom nível de "
                f"engajamento e conclusão dos cursos pelos participantes."
            )
        
        if total_secretarias > 0:
            conclusoes.append(
                f"O programa atendeu {total_secretarias} secretarias/órgãos diferentes, "
                f"demonstrando ampla cobertura institucional."
            )
        
        if df_orgaos_parceiros is not None and len(df_orgaos_parceiros) > 0:
            conclusoes.append(
                f"O programa contou com a participação de {len(df_orgaos_parceiros)} órgãos parceiros, "
                f"ampliando o alcance e impacto da capacitação."
            )
        
        for i, conclusao in enumerate(conclusoes, 1):
            elementos.append(Paragraph(f"{i}. {conclusao}", body_style))
            elementos.append(Spacer(1, 0.1*inch))
        
        elementos.append(Spacer(1, 0.2*inch))
        elementos.append(Paragraph("<b>Recomendações:</b>", body_style))
        elementos.append(Spacer(1, 0.1*inch))
        
        recomendacoes = [
            "Continuar investindo em diversificação de formatos (Cursos, Masterclasses, Workshops) para atender diferentes necessidades.",
            "Ampliar parcerias com órgãos externos para aumentar o alcance do programa.",
            "Monitorar a taxa de certificação por secretaria para identificar oportunidades de melhoria.",
            "Desenvolver estratégias específicas para aumentar a participação de cargos com menor representatividade.",
        ]
        
        for i, recomendacao in enumerate(recomendacoes, 1):
            elementos.append(Paragraph(f"{i}. {recomendacao}", body_style))
            elementos.append(Spacer(1, 0.1*inch))
        
        # ===== RODAPÉ FINAL =====
        elementos.append(PageBreak())
        elementos.append(Spacer(1, 2*inch))
        elementos.append(Paragraph("Fim do Relatório", subtitle_style))
        elementos.append(Paragraph(
            "Este relatório foi gerado automaticamente pelo sistema CapacitIA.",
            body_style
        ))
        
        # Construir PDF
        doc.build(
            elementos,
            onFirstPage=header_footer_capacitia,
            onLaterPages=header_footer_capacitia
        )
        
        print(f"✅ Relatório PDF gerado com sucesso: {caminho_completo}")
        return str(caminho_completo)
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
