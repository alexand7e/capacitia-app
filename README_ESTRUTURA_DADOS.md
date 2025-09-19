# Estrutura de Dados - Dashboard CapacitIA

## Visão Geral

Este documento descreve a estrutura dos dados processados do sistema CapacitIA e as limitações identificadas nos filtros cruzados da aplicação.

## Arquivos de Dados Processados

Os dados são armazenados em formato Parquet na pasta `.data/processed/` e são gerados a partir do arquivo CSV `dados_gerais_capacitia.csv` através do script `src/process_csv_to_parquet.py`.

### 1. dados.parquet
**Descrição**: Dados detalhados de todos os participantes e eventos
**Registros**: 872 participantes
**Colunas**:
- `evento`: Nome do evento/curso
- `formato`: Tipo do curso (Masterclass, Curso, Workshop)
- `orgao_externo`: Classificação se é órgão externo (Sim/Não)
- `eixo`: Eixo temático do curso
- `local_realizacao`: Local onde foi realizado
- `nome`: Nome do participante
- `cargo`: Cargo do participante
- `cargo_outros`: Outros cargos especificados
- `orgao`: Órgão/Secretaria do participante
- `orgao_outros`: Outros órgãos especificados
- `vinculo`: Tipo de vínculo empregatício
- `vinculo_outros`: Outros vínculos especificados
- `certificado`: Se recebeu certificado (Sim/Não)
- `cargo_gestao`: Se possui cargo de gestão (Sim/Não)
- `servidor_estado`: Se é servidor do estado (Sim/Não)

### 2. secretarias.parquet
**Descrição**: Dados agregados por órgão/secretaria
**Registros**: 45 órgãos
**Colunas**:
- `secretaria_orgao`: Nome do órgão/secretaria
- `n_inscritos`: Total de inscritos
- `n_certificados`: Total de certificados emitidos
- `n_evasao`: Total de evasões (inscritos - certificados)

### 3. cargos.parquet
**Descrição**: Dados agregados por cargo e órgão
**Registros**: 203 combinações cargo-órgão
**Colunas**:
- `cargo`: Nome do cargo
- `orgao`: Órgão do cargo
- `total_inscritos`: Total de inscritos neste cargo
- `n_gestores`: Número de gestores
- `n_servidores_estado`: Número de servidores do estado
- `perc_gestores`: Percentual de gestores
- `perc_servidores`: Percentual de servidores do estado

### 4. visao_aberta.parquet
**Descrição**: Dados agregados por evento
**Colunas**:
- `evento`: Nome do evento
- `formato`: Tipo do curso
- `eixo`: Eixo temático
- `local_realizacao`: Local de realização
- `n_inscritos`: Total de inscritos
- `n_certificados`: Total de certificados

### 5. ministrantes.parquet
**Descrição**: Dados dos ministrantes (simulados)
**Colunas**:
- `evento`: Nome do evento
- `ministrante`: Nome do ministrante
- `carga_horaria`: Carga horária
- `tipo_ministrante`: Tipo (Interno/Externo/Convidado)
- `area_expertise`: Área de expertise
- `total_participantes`: Total de participantes
- `eixo`: Eixo temático
- `local_realizacao`: Local de realização

## Limitações dos Filtros Cruzados

### Problema Identificado
A estrutura atual dos dados processados apresenta limitações para filtros cruzados eficientes:

1. **Separação de Dados**: Os dados estão divididos em múltiplas tabelas agregadas que perderam as relações originais
2. **Falta de Chaves Relacionais**: Não há chaves primárias/estrangeiras claras entre as tabelas
3. **Agregação Prematura**: Os dados já estão agregados, dificultando filtros dinâmicos

### Impactos nos Filtros

#### Filtro de Órgão/Secretaria
- **Funciona em**: `secretarias.parquet` (dados já agregados por órgão)
- **Limitação em**: `cargos.parquet` (precisa ser filtrado manualmente no código)
- **Não afeta**: `visao_aberta.parquet` (não tem relação direta com órgão)

#### Filtro de Órgão Externo
- **Funciona em**: `dados.parquet` (tem coluna `orgao_externo`)
- **Limitação em**: `cargos.parquet` (precisa classificação em tempo real)
- **Não afeta**: `secretarias.parquet` e `visao_aberta.parquet` (não têm classificação)

#### Filtro de Tipo de Curso
- **Funciona em**: `dados.parquet` e `visao_aberta.parquet` (têm coluna `formato`)
- **Não afeta**: `secretarias.parquet` e `cargos.parquet` (dados agregados sem tipo)

## Soluções Implementadas

### 1. Filtros Dinâmicos no Código
- Aplicação de filtros em tempo real nos DataFrames
- Recriação de dados agregados quando necessário
- Classificação dinâmica de órgãos externos

### 2. Estrutura de Dados Híbrida
- Manutenção dos dados originais (`dados.parquet`) para filtros complexos
- Uso de dados agregados para performance em visualizações simples
- Recálculo de KPIs baseado em dados filtrados

## Recomendações para Melhorias

### 1. Reestruturação dos Dados
- Manter uma tabela principal desnormalizada com todos os dados
- Criar views/agregações apenas para performance
- Implementar chaves relacionais claras

### 2. Otimização de Performance
- Usar índices em colunas frequentemente filtradas
- Implementar cache para consultas complexas
- Considerar uso de banco de dados relacional para dados maiores

### 3. Melhoria na Arquitetura
- Separar lógica de filtros em módulos específicos
- Implementar padrão Observer para sincronização de filtros
- Criar testes automatizados para validar filtros cruzados

## Manutenção

### Adição de Novos Filtros
1. Verificar se a coluna existe em `dados.parquet`
2. Implementar lógica de filtro no arquivo `app.py`
3. Atualizar recálculo de KPIs se necessário
4. Testar combinações com filtros existentes

### Modificação de Dados
1. Atualizar `process_csv_to_parquet.py` se necessário
2. Reprocessar dados com `python src/process_csv_to_parquet.py`
3. Verificar compatibilidade com filtros existentes
4. Atualizar documentação

---

**Última atualização**: Janeiro 2025
**Responsável**: Secretaria de Inteligência Artificial do Piauí