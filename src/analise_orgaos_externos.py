import pandas as pd

# Carregar dados
df = pd.read_parquet('.data/processed/dados.parquet')
externos = df[df['orgao_externo'] == 'Sim']

# Filtrar apenas os órgãos de interesse
orgaos_interesse = ['PRF', 'MPPI', 'Câmara Municipal']
dados_interesse = externos[externos['orgao'].isin(orgaos_interesse)]

print('=== MÉTRICAS DOS ÓRGÃOS EXTERNOS ===\n')

for orgao in orgaos_interesse:
    dados_orgao = dados_interesse[dados_interesse['orgao'] == orgao]
    if len(dados_orgao) > 0:
        certificados = len(dados_orgao[dados_orgao['certificado'] == 'Sim'])
        taxa_cert = certificados / len(dados_orgao) * 100
        
        print(f'--- {orgao} ---')
        print(f'Total de inscritos: {len(dados_orgao)}')
        print(f'Certificados: {certificados}')
        print(f'Taxa de certificação: {taxa_cert:.2f}%')
        print(f'Eventos únicos: {dados_orgao["evento"].nunique()}')
        print(f'Formatos de capacitação: {dados_orgao["formato"].unique().tolist()}')
        print(f'Eixos de capacitação: {dados_orgao["eixo"].unique().tolist()}')
        print()

# Verificar se há menção a Defensoria Pública ou Procuradoria do Estado
print('=== VERIFICAÇÃO DE ÓRGÃOS PREVISTOS ===\n')

# Verificar em todas as colunas de texto
colunas_texto = ['orgao', 'orgao_outros', 'evento', 'local_realizacao']
orgaos_previstos = ['Defensoria', 'Procuradoria']

for orgao_previsto in orgaos_previstos:
    encontrado = False
    for coluna in colunas_texto:
        if df[coluna].astype(str).str.contains(orgao_previsto, case=False, na=False).any():
            registros = df[df[coluna].astype(str).str.contains(orgao_previsto, case=False, na=False)]
            print(f'Encontrado "{orgao_previsto}" na coluna "{coluna}":')
            print(f'Registros encontrados: {len(registros)}')
            print(f'Valores únicos: {registros[coluna].unique()[:5]}')  # Primeiros 5 valores
            encontrado = True
            print()
    
    if not encontrado:
        print(f'Nenhuma menção a "{orgao_previsto}" encontrada nos dados atuais.')
        print()

print('=== RESUMO GERAL DOS ÓRGÃOS EXTERNOS ===')
print(f'Total de órgãos externos atendidos: {externos["orgao"].nunique()}')
print(f'Total de participantes de órgãos externos: {len(externos)}')
print(f'Total de certificados emitidos para órgãos externos: {len(externos[externos["certificado"] == "Sim"])}')
print(f'Taxa geral de certificação órgãos externos: {len(externos[externos["certificado"] == "Sim"]) / len(externos) * 100:.2f}%')