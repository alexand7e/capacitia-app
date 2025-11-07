#!/usr/bin/env python3
"""Script para verificar os resultados do processamento CSV para Parquet."""

import pandas as pd
from pathlib import Path

def main():
    base_path = Path.cwd()
    processed_path = base_path / ".data" / "processed"
    raw_path = base_path / ".data" / "raw"
    
    print("=" * 80)
    print("VERIFICAÇÃO DOS RESULTADOS DO PROCESSAMENTO")
    print("=" * 80)
    
    # 1. Verificar união de colunas no arquivo dados.parquet
    print("\n1. VERIFICANDO UNIÃO DE COLUNAS (dados.parquet)")
    print("-" * 80)
    df_dados = pd.read_parquet(processed_path / "dados.parquet")
    print(f"[OK] Total de registros: {len(df_dados)}")
    print(f"[OK] Colunas presentes: {list(df_dados.columns)}")
    
    # Verificar se colunas OUTROS foram removidas
    colunas_outros = ['orgao_outros', 'vinculo_outros', 'cargo_outros']
    colunas_removidas = [col for col in colunas_outros if col not in df_dados.columns]
    print(f"[OK] Colunas OUTROS removidas: {colunas_removidas}")
    
    # Verificar estatísticas
    print(f"\n[OK] Orgaos unicos: {df_dados['orgao'].nunique()}")
    print(f"[OK] Vinculos unicos: {df_dados['vinculo'].nunique()}")
    print(f"[OK] Cargos unicos: {df_dados['cargo'].nunique()}")
    
    # Verificar se há valores unidos (comparar com CSV original)
    print("\n2. VERIFICANDO UNIÃO DE VALORES (comparando com CSV original)")
    print("-" * 80)
    df_original = pd.read_csv(raw_path / "dados_gerais_capacitia.csv", sep=';', skiprows=1, nrows=1000)
    df_original.columns = [
        'EVENTO', 'FORMATO', 'ORGÃO EXTERNO', 'EIXO', 'LOCAL DE REALIZAÇÃO',
        'NOME', 'CARGO', 'CARGO OUTROS', 'ÓRGÃO', 'ÓRGÃO OUTROS',
        'VÍNCULO', 'VÍNCULO OUTROS', 'CERTIFICADO', 'CARGO DE GESTÃO', 'SERVIDOR DO ESTADO'
    ]
    
    # Verificar se há casos onde OUTROS tinha valor
    casos_orgao_outros = df_original[
        (df_original['ÓRGÃO OUTROS'].notna()) & 
        (df_original['ÓRGÃO OUTROS'] != '') & 
        (df_original['ÓRGÃO OUTROS'] != 'NA')
    ]
    casos_vinculo_outros = df_original[
        (df_original['VÍNCULO OUTROS'].notna()) & 
        (df_original['VÍNCULO OUTROS'] != '') & 
        (df_original['VÍNCULO OUTROS'] != 'NA')
    ]
    casos_cargo_outros = df_original[
        (df_original['CARGO OUTROS'].notna()) & 
        (df_original['CARGO OUTROS'] != '') & 
        (df_original['CARGO OUTROS'] != 'NA')
    ]
    
    print(f"[OK] Casos com ORGAO OUTROS preenchido: {len(casos_orgao_outros)}")
    print(f"[OK] Casos com VINCULO OUTROS preenchido: {len(casos_vinculo_outros)}")
    print(f"[OK] Casos com CARGO OUTROS preenchido: {len(casos_cargo_outros)}")
    
    # 3. Verificar remoção de dados sensíveis - Autonomia Digital Avaliações
    print("\n3. VERIFICANDO REMOÇÃO DE DADOS SENSÍVEIS - Autonomia Digital (Avaliações)")
    print("-" * 80)
    df_avaliacoes = pd.read_parquet(processed_path / "autonomiadigital_avaliacoes.parquet")
    print(f"[OK] Total de registros: {len(df_avaliacoes)}")
    print(f"[OK] Colunas presentes: {len(df_avaliacoes.columns)}")
    
    colunas_sensiveis_avaliacoes = ['nome', 'cpf', 'email', 'genero', 'idade', 'digite seu nome']
    colunas_presentes_sensiveis = [col for col in colunas_sensiveis_avaliacoes 
                                   if any(col in str(col_df).lower() for col_df in df_avaliacoes.columns)]
    if colunas_presentes_sensiveis:
        print(f"[ATENCAO] Colunas sensiveis ainda presentes: {colunas_presentes_sensiveis}")
    else:
        print("[OK] Dados sensiveis removidos com sucesso!")
    
    print(f"\n[OK] Primeiras colunas: {list(df_avaliacoes.columns[:5])}")
    
    # 4. Verificar remoção de dados sensíveis - Autonomia Digital Inscrições
    print("\n4. VERIFICANDO REMOÇÃO DE DADOS SENSÍVEIS - Autonomia Digital (Inscrições)")
    print("-" * 80)
    df_inscricoes = pd.read_parquet(processed_path / "autonomiadigital_inscricoes.parquet")
    print(f"[OK] Total de registros: {len(df_inscricoes)}")
    print(f"[OK] Colunas presentes: {len(df_inscricoes.columns)}")
    
    colunas_sensiveis_inscricoes = ['nome', 'cpf', 'email', 'telefone', 'cidade', 'bairro', 'genero', 'idade']
    colunas_presentes_sensiveis = [col for col in colunas_sensiveis_inscricoes 
                                   if any(col in str(col_df).lower() for col_df in df_inscricoes.columns)]
    if colunas_presentes_sensiveis:
        print(f"[ATENCAO] Colunas sensiveis ainda presentes: {colunas_presentes_sensiveis}")
    else:
        print("[OK] Dados sensiveis removidos com sucesso!")
    
    print(f"\n[OK] Primeiras colunas: {list(df_inscricoes.columns[:5])}")
    
    # 5. Verificar remoção de dados sensíveis - Saúde
    print("\n5. VERIFICANDO REMOÇÃO DE DADOS SENSÍVEIS - Saúde")
    print("-" * 80)
    df_saude = pd.read_parquet(processed_path / "saude.parquet")
    print(f"[OK] Total de registros: {len(df_saude)}")
    print(f"[OK] Colunas presentes: {list(df_saude.columns)}")
    
    colunas_sensiveis_saude = ['nome', 'e-mail', 'email']
    colunas_presentes_sensiveis = [col for col in colunas_sensiveis_saude 
                                   if any(col in str(col_df).lower() for col_df in df_saude.columns)]
    if colunas_presentes_sensiveis:
        print(f"[ATENCAO] Colunas sensiveis ainda presentes: {colunas_presentes_sensiveis}")
    else:
        print("[OK] Dados sensiveis removidos com sucesso!")
    
    # 6. Verificar arquivos gerados
    print("\n6. VERIFICANDO ARQUIVOS PARQUET GERADOS")
    print("-" * 80)
    arquivos_esperados = [
        "dados.parquet",
        "visao_aberta.parquet",
        "secretarias.parquet",
        "cargos.parquet",
        "ministrantes.parquet",
        "autonomiadigital_avaliacoes.parquet",
        "autonomiadigital_inscricoes.parquet",
        "saude.parquet"
    ]
    
    for arquivo in arquivos_esperados:
        arquivo_path = processed_path / arquivo
        if arquivo_path.exists():
            tamanho = arquivo_path.stat().st_size / 1024  # KB
            print(f"[OK] {arquivo}: {tamanho:.2f} KB")
        else:
            print(f"[ERRO] {arquivo}: NAO ENCONTRADO")
    
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO CONCLUÍDA!")
    print("=" * 80)

if __name__ == "__main__":
    main()

