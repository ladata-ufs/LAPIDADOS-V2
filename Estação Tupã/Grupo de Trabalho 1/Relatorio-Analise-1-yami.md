# Projeto TUPA - Analise e Consolidacao de Dados INMET

## Descricao

Este projeto tem como objetivo processar, analisar a qualidade e consolidar dados meteorologicos brutos disponibilizados pelo Instituto Nacional de Meteorologia (INMET), especificamente para a Semana 1 do Projeto TUPA.

O fluxo foi desenvolvido para varrer recortes anuais, extrair metadados, verificar a porcentagem de falhas nas medicoes e gerar uma base unificada para futuras analises exploratorias e modelagem de dados.

---

# Estrutura do Projeto

```
.
├── Dados brutos - INMET (2016-25)/
│   ├── INMET_NE_SE_A409_ARACAJU_01-01-2016_A_31-12-2016.CSV
│   ├── INMET_NE_SE_A409_ARACAJU_01-01-2017_A_31-12-2017.CSV
│   ├── ...
│   └── INMET_NE_SE_A409_ARACAJU_01-01-2025_A_31-12-2025.CSV
│
├── gerador_relatorios_inmet.py
├── pipeline_consolidacao.py
│
├── Dados Tratados - INMET (2016-25)/
│   ├── dados_inmet_consolidados.csv
│   ├── relatorio_semana1.pdf
│   ├── sumario_estacoes.json
│   └── metadados_arquivos.json
└── Relatorio-Analise-1-yami.md
```

---

# Organizacao dos Dados

## dados_brutos/

Contem os arquivos originais em formato CSV obtidos junto ao portal do INMET.

Cada arquivo representa as observacoes meteorologicas de um periodo especifico da estacao automatica de Aracaju (A409).
A serie historica analisada abrange os anos de 2016 a 2025.

Esses arquivos permanecem inalterados durante todo o processamento.

---

## dados_tratados/

Armazena os artefatos produzidos apos a execucao dos scripts de pipeline.

### dados_inmet_consolidados.csv

Arquivo resultante da uniao de todos os arquivos anuais presentes no diretorio de dados.
Os cabecalhos complexos de cada arquivo (as primeiras 8 linhas) sao ignorados nesta etapa para empilhar puramente os dados historicos continuos, resultando na base final que sera utilizada em analises.

### relatorio_semana1.pdf e sumario_estacoes.json

Documentos gerados contendo o diagnostico da qualidade dos dados. Apresentam um resumo de todas as variaveis disponiveis e o percentual de dados faltantes para cada ano consolidado.

### metadados_arquivos.json

Arquivo que reune os metadados extraidos do cabecalho original dos arquivos CSV (Latitude, Longitude, Altitude, WMO, etc.), facilitando consultas estruturadas independentes da base de medicoes temporais.

---

# Scripts

## gerador_relatorios_inmet.py

Responsavel por extrair metadados e gerar relatorios de qualidade da base.

As principais etapas executadas sao:
* leitura parcial dos arquivos (apenas cabecalho e primeiras linhas);
* identificacao automatica das colunas de interesse (precipitacao, temperatura, vento, umidade, pressao);
* calculo do percentual de dados faltantes ou linhas com falha nas medicoes;
* geracao de um documento PDF consolidado e um arquivo JSON de sumario.

---

## consolidador_dados_inmet.py

Responsavel por unificar toda a serie historica.

Entre as transformacoes realizadas estao:
* leitura iterativa dos dados brutos ignorando as linhas de metadados iniciais;
* concatenacao de todos os DataFrames;
* exportacao da base unificada (`dados_inmet_consolidados.csv`) que preserva a integridade dos dados numericos para consumo posterior.

---

# Fluxo do Projeto

```
Dados Brutos INMET (2016-2025)
               |
               +-----------------------------------+
               |                                   |
               v                                   v
  gerador_relatorios_inmet.py         pipeline_consolidacao.py
               |                                   |
               v                                   v
     relatorio_semana1.pdf            dados_inmet_consolidados.csv
     sumario_estacoes.json            metadados_arquivos.json
```

---

# Principais Resultados e Analise de Qualidade

A etapa de extracao de metadados demonstrou que os dados processados pertencem a estacao automatica ARACAJU (A409), localizada no estado de Sergipe.

Durante a varredura da qualidade, identificou-se padroes de variacao severa na integridade de captura ao longo da serie temporal:

* Os anos de 2016 a 2020 apresentam dados consistentes, indicando operacao continua e 0% de dados faltantes nas estruturas computadas.
* A partir de 2021, iniciou-se uma defasagem nas medicoes (aproximadamente 7.8% de falhas).
* O ano de 2022 apresentou instabilidades criticas, acumulando quase 70% de dados faltantes na amostra anual.
* Essa instabilidade se manteve nos registros subsequentes (2023 com cerca de 14% de perdas e 2024 com 9.4%).

Esses indicadores sao fundamentais para direcionar etapas de limpeza (data cleaning) e inputacao de valores nas variaveis atmosfericas (como temperatura, precipitacao e vento) antes da criacao de paineis (dashboards) ou da fase de modelagem preditiva.

---

# Tecnologias Utilizadas

* Python
* Pandas
* FPDF

---

# Fonte dos Dados

Instituto Nacional de Meteorologia (INMET)

Os dados utilizados correspondem as observacoes meteorologicas registradas pela estacao meteorologica A409 localizada na cidade de Aracaju, SE, disponibilizadas pelo INMET.
