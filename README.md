# Capacitia App — Reprodutibilidade e Tratamento de Dados

Este repositório contém um dashboard em Streamlit, scripts de processamento de dados e notebooks analíticos para avaliação e modelagem de certificação de servidores. Este guia explica como reproduzir o ambiente, processar os dados (CSV → Parquet), verificar resultados, executar o app e rodar as análises avançadas.

## Requisitos
- Python `3.10+` (recomendado)
- Windows (suportado) — comandos abaixo usam PowerShell
- Pacotes listados em `requirements.txt`

## Instalação
- Criar e ativar ambiente virtual:
  - `python -m venv .venv`
  - `.\.venv\Scripts\Activate.ps1`
- Instalar dependências:
  - `pip install -r requirements.txt`

## Estrutura de Pastas
- `.data/raw/` — arquivos CSV de entrada
- `.data/processed/` — arquivos Parquet gerados
- `src/` — scripts de processamento e utilitários
- `pages/` e `app.py` — app Streamlit
- `.analytics/` — notebooks e execução automatizada
- `reports/images/` — imagens geradas (gráficos e SHAP)

## Tratamento de Dados (CSV → Parquet)
- Coloque os arquivos de entrada na pasta `.data/raw/`:
  - `dados_gerais_capacitia.csv` (principal)
  - `dados_inscricoes_capacitia_autonomiadigital.csv`
  - `dados_avaliacoes_capacitia_autonomiadigital.csv`
  - `dados_capacitia_saude.csv`
- Executar o pipeline de processamento:
  - `python src\process_csv_to_parquet.py`
- O script:
  - Une colunas com sufixo `OUTROS` nas principais (ex.: `ÓRGÃO` + `ÓRGÃO OUTROS`)
  - Padroniza nomes e tipos
  - Gera os seguintes arquivos em `.data/processed/`:
    - `dados.parquet`, `visao_aberta.parquet`, `secretarias.parquet`, `cargos.parquet`, `ministrantes.parquet`
    - `autonomiadigital_avaliacoes.parquet`, `autonomiadigital_inscricoes.parquet`, `saude.parquet`

### Verificação Pós‑Processamento
- Validar rapidamente os resultados:
  - `python src\verify_results.py`
- O verificador confirma:
  - Remoção/união correta de colunas `OUTROS`
  - Presença dos arquivos Parquet esperados
  - Remoção de dados sensíveis nas bases de Autonomia Digital e Saúde

## Executar o Dashboard
- Garantir dados processados em `.data/processed/`
- Rodar o app:
  - `streamlit run app.py`
- Principais colunas utilizadas nas páginas:
  - `evento`, `orgao`, `certificado`, `formato`, `eixo`, `cargo`, `vinculo`, `cargo_gestao`, `servidor_estado`, `orgao_externo`

## Análises Avançadas e Modelagem
- Notebooks relevantes em `.analytics/`:
  - `servidores_analise_avancada.ipynb` — modelagem com XGBoost, otimização e SHAP
  - `servidores_modelagem_export.ipynb` e variantes — fluxos de exportação
- Execução automática (sem Jupyter CLI):
  - `python -m nbconvert --to notebook --execute .analytics\servidores_analise_avancada.ipynb --output .analytics\servidores_analise_avancada-executed.ipynb`
  - ou `python .analytics\run_notebook.py` (usa `nbclient`)
- Resultados esperados:
  - Imagens salvas em `reports/images/` (ex.: `xgboost_confusion_matrix.png`, `shap_summary_plot.png`)

## Dependências Principais
- App: `streamlit`, `pandas`, `numpy`, `plotly`, `openpyxl`, `pyarrow`, `wordcloud`, `matplotlib`, `seaborn`
- Modelagem: `scikit-learn`, `xgboost==2.0.3`, `shap==0.49.1`
- Notebooks: `nbconvert`, `nbformat`, `nbclient`

## Dicas e Solução de Problemas
- `joblib` pode emitir `KeyError` em `resource_tracker` durante grid search; são avisos e não impedem a execução.
- Compatibilidade `SHAP` + `XGBoost`:
  - Versões foram fixadas (`xgboost==2.0.3`, `shap==0.49.1`) para evitar erros de parse do `base_score`.
- Imagens de relatório:
  - `reports/images/` está ignorado no git. Gere novamente executando os notebooks.
- Ambiente virtual:
  - Se a ativação falhar no PowerShell, ajuste a política: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Fluxo de Reprodutibilidade — Resumo
1. `python -m venv .venv && .\.venv\Scripts\Activate.ps1`
2. `pip install -r requirements.txt`
3. Copiar CSVs para `.data/raw/`
4. `python src\process_csv_to_parquet.py`
5. `python src\verify_results.py`
6. `streamlit run app.py`
7. (Opcional) Executar `.analytics\servidores_analise_avancada.ipynb` para gerar imagens de interpretação

## Créditos
- Secretaria de Inteligência Artificial do Piauí — CapacitIA
