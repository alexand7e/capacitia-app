# Análise dos Problemas nos Filtros Globais - Dashboard CapacitIA

## Resumo Executivo

Após análise detalhada da estrutura dos dados e código dos filtros globais, foram identificados **múltiplos problemas críticos** que impedem o funcionamento correto da filtragem cruzada no dashboard.

## 1. Estrutura dos Dados

### Arquivo Raw (CSV)
- **Arquivo**: `dados_gerais_capacitia.csv` (1.134 linhas)
- **Estrutura**: Dados individuais por participante/evento
- **Colunas principais**: EVENTO, FORMATO, ÓRGÃO EXTERNO, EIXO, NOME, CARGO, ÓRGÃO, VÍNCULO, CERTIFICADO, etc.
- **Problema**: Coluna "ÓRGÃO EXTERNO" com valores "Sim"/"Não" mas inconsistente com a lógica de filtragem

### Arquivos Processados (Parquet)

#### df_dados.parquet
- **Linhas**: 874 registros individuais
- **Colunas**: 15 colunas incluindo `orgao_externo`, `orgao`, `cargo`, etc.
- **Status**: ✅ Estrutura correta para filtragem

#### df_secretarias.parquet  
- **Linhas**: 47 órgãos/secretarias
- **Colunas**: `secretaria_orgao`, `n_inscritos`, `n_certificados`, `n_evasao`
- **Status**: ✅ Dados agregados corretos

#### df_cargos.parquet
- **Linhas**: 207 registros (cargo + órgão)
- **Colunas**: `cargo`, `orgao`, `total_inscritos`, `n_gestores`, etc.
- **Status**: ✅ Estrutura correta

## 2. Problemas Identificados nos Filtros

### 🚨 Problema 1: Incompatibilidade de Nomes de Colunas

**Localização**: Linhas 505-507 em `app.py`

```python
# ERRO: Busca por "secretaria_orgao" mas df_secretarias usa "SECRETARIA/ÓRGÃO"
df_secretarias_filtrado = df_secretarias[df_secretarias["secretaria_orgao"] == orgao_selecionado].copy()
```

**Causa**: O código assume que `df_secretarias` tem coluna `secretaria_orgao`, mas após a função `clean_secretarias()`, a coluna se chama `"SECRETARIA/ÓRGÃO"`.

### 🚨 Problema 2: Referência a Variável Inexistente

**Localização**: Linhas 507, 544, etc.

```python
# ERRO: df_f não está definido no contexto dos filtros
df_f_filtrado = df_f[df_f["orgao"] == orgao_selecionado].copy()
```

**Causa**: A variável `df_f` é definida na linha 268, mas é usada incorretamente no contexto de filtragem. Deveria usar `df_dados`.

### 🚨 Problema 3: Lógica de Filtragem Circular

**Localização**: Linhas 510-540

**Problema**: O código tenta recriar `df_cargos_ev` dinamicamente durante a filtragem, mas:
1. Usa dados simulados em vez de dados reais
2. Cria dependências circulares entre filtros
3. Não mantém consistência entre diferentes DataFrames

### 🚨 Problema 4: Mapeamento Incorreto de Órgão Externo

**Localização**: Linhas 543-590

**Problema**: 
- Filtra `df_f_filtrado` por `orgao_externo`, mas `df_f` não tem essa coluna
- Deveria filtrar `df_dados` que tem a coluna `orgao_externo`

### 🚨 Problema 5: Estrutura de Dados Inadequada para Filtros Cruzados

**Problema Fundamental**: Os dados estão pré-agregados em diferentes níveis:
- `df_secretarias`: Agregado por órgão
- `df_cargos`: Agregado por cargo+órgão  
- `df_visao`: Agregado por evento

**Impacto**: Impossível aplicar filtros cruzados consistentes porque não há uma fonte única de verdade.

## 3. Erro Específico Observado

```
KeyError: "['Assessor', 'Chefe de Gabinete', 'Consultor', 'Diretor', 'Secretário (a)'] not in index"
```

**Causa**: O código tenta acessar colunas do DataFrame usando nomes de cargos como se fossem nomes de colunas, quando na verdade são valores da coluna `cargo`.

## 4. Impacto dos Problemas

### Filtros Não Funcionam
- ❌ Filtro por Órgão/Secretaria: Falha por incompatibilidade de nomes
- ❌ Filtro por Órgão Externo: Falha por referência incorreta
- ❌ Filtro por Tipo de Curso: Funciona parcialmente mas não se integra

### Dados Inconsistentes
- KPIs calculados com dados não filtrados
- Gráficos mostram dados completos mesmo com filtros ativos
- Tabelas não refletem seleções dos filtros

### Experiência do Usuário
- Interface sugere funcionalidade que não existe
- Filtros aparentam funcionar mas não afetam os dados
- Resultados confusos e não confiáveis

## 5. Recomendações de Correção

### Correção Imediata (Crítica)
1. **Corrigir nomes de colunas** nas referências de filtragem
2. **Usar df_dados como fonte única** para todos os filtros
3. **Remover lógica de recriação dinâmica** de DataFrames

### Correção Estrutural (Recomendada)
1. **Implementar filtros baseados em df_dados**
2. **Recalcular agregações** após aplicação de filtros
3. **Criar função centralizada de filtragem**

### Melhoria Arquitetural (Ideal)
1. **Refatorar para arquitetura baseada em dados granulares**
2. **Implementar cache inteligente** para agregações filtradas
3. **Separar lógica de dados da lógica de apresentação**

## 6. Próximos Passos

1. ✅ **Análise Completa** - Concluída
2. 🔄 **Implementar Correções Críticas** - Em andamento
3. ⏳ **Testar Filtros Corrigidos**
4. ⏳ **Validar Consistência dos Dados**
5. ⏳ **Documentar Soluções Implementadas**

---

**Data da Análise**: Janeiro 2025  
**Responsável**: Análise Técnica SIA-PI  
**Status**: Problemas identificados, correções em desenvolvimento