# Análise de Dados Meteorológicos de Aracaju (INMET)

## Descrição

Este projeto tem como objetivo consolidar, tratar e analisar dados meteorológicos da cidade de Aracaju disponibilizados pelo Instituto Nacional de Meteorologia (INMET).

O fluxo foi desenvolvido para transformar arquivos anuais em uma base única, padronizar os dados e prepará-los para análises exploratórias e visualizações no Looker Studio.

---

# Estrutura do Projeto

```
.
├── dados_brutos/
│   ├── inmet_aracaju_2016.csv
│   ├── inmet_aracaju_2017.csv
│   ├── inmet_aracaju_2018.csv
│   ├── inmet_aracaju_2019.csv
│   ├── inmet_aracaju_2020.csv
│   ├── inmet_aracaju_2021.csv
│   └── inmet_aracaju_2024.csv
│
├── dados_tratados/
│   ├── inmet_aracaju.csv
│   └── inmet_aracaju_tratado.csv
│
├── merged_inmet_data.py
├── process_merged_data.py
└── Instructions.md
```

---

# Organização dos Dados

## `dados_brutos/`

Contém os arquivos originais obtidos junto ao INMET.

Cada arquivo representa um ano de observações meteorológicas da estação localizada em Aracaju.

Atualmente o projeto possui registros referentes aos anos:

* 2016
* 2017
* 2018
* 2019
* 2020
* 2021

Além desses dados históricos, também existe uma base contendo os dados meteorológicos de **2024**, permitindo futuras análises comparativas e atualizações da série temporal.

Esses arquivos permanecem inalterados durante todo o processamento.

---

## `dados_tratados/`

Armazena os arquivos produzidos durante o pipeline de tratamento.

### `inmet_aracaju.csv`

Arquivo resultante da união de todos os arquivos anuais presentes em `dados_brutos`.

Nenhuma transformação é realizada nessa etapa além da concatenação dos registros.

### `inmet_aracaju_tratado.csv`

Base final utilizada para análises.

Nessa etapa são realizadas diversas transformações para padronização dos dados.

---

# Scripts

## `merged_inmet_data.py`

Responsável por consolidar todos os arquivos anuais em um único conjunto de dados.

As principais etapas executadas são:

* leitura de todos os arquivos anuais;
* concatenação dos DataFrames;
* preservação da ordem cronológica dos registros;
* geração do arquivo consolidado `inmet_aracaju.csv`.

---

## `process_merged_data.py`

Responsável pelo tratamento da base consolidada.

Entre as transformações realizadas estão:

* criação de um campo de data e hora (timestamp) a partir das colunas de data e hora;
* padronização do formato temporal;
* conversão das colunas meteorológicas para tipos numéricos (`float`);
* substituição das vírgulas decimais por ponto;
* tratamento de valores ausentes;
* ordenação cronológica dos registros;
* exportação da base tratada para utilização em ferramentas analíticas.

---

# Fluxo do Projeto

```
Dados Brutos (2016–2021 + 2024)
                │
                ▼
      merged_inmet_data.py
                │
                ▼
      inmet_aracaju.csv
                │
                ▼
     process_merged_data.py
                │
                ▼
 inmet_aracaju_tratado.csv
                │
                ▼
        Looker Studio
```

---

# Visualização dos Dados

Após o tratamento dos dados, a base foi importada para o **Looker Studio**, onde foi realizada uma análise exploratória utilizando gráficos temporais, indicadores e agregações mensais.

O objetivo dessa etapa foi compreender o comportamento climático da cidade ao longo dos anos observados.

---

# Principais Resultados

A análise evidenciou um padrão sazonal bastante consistente no regime de chuvas da cidade de Aracaju.

Os maiores volumes de precipitação concentram-se entre os meses de **março e julho**, independentemente do ano analisado. Durante esse período, a precipitação mensal pode atingir valores próximos de **400 mm**, caracterizando a estação mais chuvosa da região.

A partir do mês de **agosto**, observa-se uma redução significativa das chuvas. Nos meses correspondentes ao verão, os volumes mensais geralmente permanecem abaixo de **100 mm**, indicando um período consideravelmente mais seco.

Apesar da expressiva variação na precipitação ao longo do ano, as análises mostraram que **temperatura** e **umidade relativa do ar** apresentam pouca oscilação sazonal. Esses parâmetros permanecem próximos de suas médias anuais, mesmo durante os períodos de maior incidência de chuvas.

Esse comportamento pode ser explicado pela localização geográfica de Aracaju. Por ser uma cidade litorânea, a influência do Oceano Atlântico atua como um regulador térmico, reduzindo as amplitudes de temperatura e contribuindo para a manutenção de elevados índices de umidade ao longo de todo o ano.

---

# Tecnologias Utilizadas

* Python
* Pandas
* Looker Studio: https://datastudio.google.com/reporting/a0c04c4e-6baa-4567-9754-f85a210fcf10

---

# Fonte dos Dados

Instituto Nacional de Meteorologia (INMET)

Os dados utilizados correspondem às observações meteorológicas registradas pela estação meteorológica localizada na cidade de Aracaju, disponibilizadas pelo INMET.
