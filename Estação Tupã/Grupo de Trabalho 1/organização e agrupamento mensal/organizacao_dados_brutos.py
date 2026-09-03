#############
# bibliotecas
#############


# numpy é usado aqui só pra ter o np.nan, que é o jeito padrão das bibliotecas de representar um null em colunas numericas
import numpy as np
# pras futuras tabelas em python
import pandas as pd
# json para salvar os metadados da estacao em arquivo
import json
# os é usado pra criar a pasta de saída caso ela ainda não exista
import os
 
 
######################
# configurações gerais
######################
 
# número de linhas de metadado, ou seja, caracteristicas, no topo do arquivo bruto do BDMEP: (9 linhas de "Chave: Valor" + 1 linha em branco = 10 linhas antes do cabeçalho da tabela de dados)
N_LINHAS_METADADOS = 9
# marcador de valor ausente, usado pelo BDMEP nos arquivos exportados, ressaltados visando o tratamento dos dados.
MARCADOR_NULO = "null"
# dicionario com as estações do ano no hemisfério sul de acordo com o mês, simplificando a análise
ESTACOES_DO_ANO = {
    12: "Verão", 1: "Verão", 2: "Verão",
    3: "Outono", 4: "Outono", 5: "Outono",
    6: "Inverno", 7: "Inverno", 8: "Inverno",
    9: "Primavera", 10: "Primavera", 11: "Primavera",
}

 
####################################################
# função de leitura e separação de metadados x dados
####################################################
 
# lê as primeiras linhas do arquivo bruto do BDMEP e devolve como um dicionario (formato "key: value")
def ler_metadados(caminho_arquivo):
# abrimos o arquivo em modo leitura, especificando utf-8 por causa dos acentos
    arquivo = open(caminho_arquivo, encoding="utf-8")
 
    # lista vazia onde vamos guardar cada uma das linhas de metadados
    linhas_cabecalho = []
    for i in range(N_LINHAS_METADADOS):
        # readline() lê uma linha por vez do arquivo, na ordem em que aparecem
        linhas_cabecalho.append(arquivo.readline())
    # fechamos o arquivo depois de pegar as linhas que precisávamos
    arquivo.close()
 
    # criamos um dicionário vazio onde vamos guardar os pares chave/valor
    metadados = {}
 
    # cada linha vem no formato "Nome: ARACAJU", o método .split(":", 1) separa a linha em duas partes usando o ":" como corte,
    # o "1" no final garante que só o PRIMEIRO ":" da linha é usado (boas praticas antibug)
    for linha in linhas_cabecalho:
        partes = linha.strip().split(":", 1)
        chave = partes[0].strip()
        valor = partes[1].strip()
        metadados[chave] = valor
 
    return metadados
 
 
# lê a tabela de dados do arquivo bruto do BDMEP, pulando o bloco de metadados
def ler_dados_brutos(caminho_arquivo):
    ## skip rows: pula as N linhas de metadados + 1 linha em branco
    ## header=0: a primeira linha é o cabeçalho real da tabela
    df_bruto = pd.read_csv(
        caminho_arquivo,
        sep=";",
        skiprows=N_LINHAS_METADADOS + 1,
        header=0,
        encoding="utf-8",
    )
 
    # o arquivo do BDMEP termina cada linha com um ";" sobrando, o que faz o pandas criar uma terceira coluna vazia sem nome (aparece como "Unnamed: 2")
    # aqui a gente descarta essa coluna extra, mantendo só as duas que interessam
    df_bruto = df_bruto.iloc[:, 0:2]
 
    # renomeamos as colunas pra nomes mais simples de trabalhar (o nome original da segunda coluna é bem grande: "PRECIPITACAO TOTAL, DIARIO (AUT)(mm)")
    df_bruto.columns = ["data", "precipitacao_mm"]
 
    return df_bruto
 
 
##########################################################################
# função de parsing/estruturação, tipagem e tratamento de valores ausentes
##########################################################################
 
# converte tipos de dados e trata valores ausentes: "data" -> datetime64 e "precipitacao_mm" -> float, com o marcador textual "null" do BDMEP convertido para NaN 
def limpar_e_tipar(df_bruto):
    # .copy() evita alterar o dataframe original 
    df = df_bruto.copy()
    # pd.to_datetime transforma o texto "2016-09-03" num objeto de data real, no formato ano-mes-dia
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d")
    # a coluna de precipitação vem como texto, então primeiro tiramos espaços extras
    df["precipitacao_mm"] = df["precipitacao_mm"].astype(str).str.strip()
    # tratamento de valor ausente: trocamos o null pelo np.nan e representamos a ausencia de dados conforme o pandas entende
    df["precipitacao_mm"] = df["precipitacao_mm"].replace(MARCADOR_NULO, np.nan)
    # convertemos a coluna inteira de texto pra número decimal (float)
    df["precipitacao_mm"] = pd.to_numeric(df["precipitacao_mm"])
 
    return df
 
 
######################################################
# funça~o de validação de integridade da série temporal
######################################################
 
# garante que a série tenha exatamente uma linha por dia entre a primeira e a última data
def validar_serie_temporal(df):
   # pega a primeira e a última data que existem no dataframe
    data_inicio = df["data"].min()
    data_fim = df["data"].max()
 
    # cria uma lista com TODOS os dias entre data_inicio e data_fim, sem pular nenhum
    calendario_completo = pd.date_range(data_inicio, data_fim, freq="D")
    # coloca a coluna "data" como índice do dataframe (é um requisito do reindex)
    df = df.set_index("data")
    # reindexar faz o dataframe "se encaixar" no calendário completo:
    # se faltar uma data, ela é criada com precipitacao_mm = NaN automaticamente
    df = df.reindex(calendario_completo)
 
    # devolve a coluna "data" pro lugar normal (em vez de ficar como índice)
    df = df.rename_axis("data").reset_index()
 
    return df
 
 
###################################
# função de engenharia de atributos
###################################
 
# adiciona colunas derivadas da data, úteis para agregações e análises exploratórias: ano, mês, dia do ano e estação do ano, sendo possivel puxar gráficos e demonstrações virtuais daqui.
def adicionar_atributos_temporais(df):
  
    df = df.copy()
    # .dt é o "acessador" do pandas pra pegar partes de uma coluna de data
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.month
    # .map() olha o número do mês e devolve o nome da estação do ano, usando o dicionário ESTACOES_DO_ANO definido anteriormente
    df["estacao_do_ano"] = df["mes"].map(ESTACOES_DO_ANO)
 
    # cria uma coluna true/false: true quando o dia não tem medição válida
    df["dado_ausente"] = df["precipitacao_mm"].isna()
 
    return df
 
 
#########################################################################
# função de estatísticas descritivas/qualidade dos dados (anual e mensal)
#########################################################################
 
# resume os dados por ano: quantos dias tinham medição, quantos faltaram, qual o percentual de falha, e o total de chuva acumulada no ano
def gerar_resumo_anual(df):
    # groupby agrupa todas as linhas por ano
    # .agg() calcula, pra cada grupo, as estatísticas que a gente pedir
    resumo = df.groupby("ano").agg(
        dias_no_periodo=("data", "count"),
        dias_com_dado=("dado_ausente", lambda coluna: (coluna == False).sum()),
        dias_ausentes=("dado_ausente", "sum"),
        precipitacao_total_mm=("precipitacao_mm", "sum"),
    )
 
    # depois do groupby, o "ano" vira o índice da tabela e reset_index devolve ele como uma coluna normal, o que deixa o resultado mais fácil de exportar
    resumo = resumo.reset_index()
 
    # calcula o percentual de dias sem dado em relação ao total de dias do ano
    resumo["pct_falha"] = (resumo["dias_ausentes"] / resumo["dias_no_periodo"] * 100).round(1)
 
    return resumo
 
# resume os dados por mês E ano
def gerar_resumo_mensal(df):
    # dessa vez agrupamos por DUAS colunas ao mesmo tempo: ano e mes
    # isso separa, por exemplo, janeiro/2019 de janeiro/2020, em vez de misturar todos os "janeiros"
    resumo = df.groupby(["ano", "mes"]).agg(
        dias_no_mes=("data", "count"),
        dias_com_dado=("dado_ausente", lambda coluna: (coluna == False).sum()),
        dias_ausentes=("dado_ausente", "sum"),
        precipitacao_total_mm=("precipitacao_mm", "sum"),
        precipitacao_media_mm=("precipitacao_mm", "mean"),
    )
 
    # depois do groupby com duas colunas, "ano" e "mes" viram os dois níveis do índice
    # reset_index() devolve os dois como colunas normais de novo
    resumo = resumo.reset_index()
 
    resumo["pct_falha"] = (resumo["dias_ausentes"] / resumo["dias_no_mes"] * 100).round(1)
    resumo["precipitacao_media_mm"] = resumo["precipitacao_media_mm"].round(2)
 
    # cria uma coluna "ano_mes" tipo "2019-01", que facilita muito na hora de fazer um grafico de linha
    resumo["ano_mes"] = resumo["ano"].astype(str) + "-" + resumo["mes"].astype(str).str.zfill(2)
     # .astype(str) transforma o número em texto, e .zfill(2) garante que o mês sempre tenha 2 dígitos

    return resumo
 
 
######################
# função de exportação
######################
 
# salva os três resultados finais em disco: dados limpos, resumo anual e metadados (= output pra respeitar os nomes das pastas na main)
def exportar_resultados(df, resumo_anual, resumo_mensal, metadados, pasta_saida="output"):
    # cria a pasta de saída caso ela ainda não exista
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)
 
    # lista das colunas que queremos manter no arquivo final de dados diários
    colunas_finais = ["data", "ano", "mes", "estacao_do_ano", "precipitacao_mm", "dado_ausente"]
 
    # to_csv salva o dataframe como um arquivo .csv e index=false evita que o pandas salve o número da linha como uma coluna extra
    df[colunas_finais].to_csv(pasta_saida + "/dados_limpos.csv", index=False, encoding="utf-8")
 
    resumo_anual.to_csv(pasta_saida + "/resumo_anual.csv", index=False, encoding="utf-8")
    resumo_mensal.to_csv(pasta_saida + "/resumo_mensal.csv", index=False, encoding="utf-8")
 
    # salva o dicionário de metadados como um arquivo .json, (indent=2) pra ficar legível se alguém abrir o arquivo depois
    arquivo_json = open(pasta_saida + "/metadados.json", "w", encoding="utf-8")
    json.dump(metadados, arquivo_json, ensure_ascii=False, indent=2)
    arquivo_json.close()
 
    print("Arquivos exportados em (pasta):", pasta_saida)
 

 
####################
# pipeline principal
####################
 
# essa função chama, respectivamente, as etapas do processo: ler, limpar, validar, enriquecer, resumir, exportar
def organizar_dados_bdmep(caminho_arquivo_bruto):
    # separa a pasta onde está o arquivo pra usar depois na hora de salvar a saída
    pasta_do_arquivo = os.path.dirname(caminho_arquivo_bruto)
 
    # se o caminho informado não tiver nenhuma pasta na frente (ex.: só "dados.csv"), os.path.dirname devolve uma string vazia "" — e "" + "/output" viraria "/output",
    # que é a pasta "output" na base do sistema, e não do lado do script. por isso, se vier vazio, usamos "." (que significa "pasta atual")
    if pasta_do_arquivo == "":
        pasta_do_arquivo = "."
 
    metadados = ler_metadados(caminho_arquivo_bruto)
    df_bruto = ler_dados_brutos(caminho_arquivo_bruto)
 
    df = limpar_e_tipar(df_bruto)
    df = validar_serie_temporal(df)
    df = adicionar_atributos_temporais(df)
 
    resumo_anual = gerar_resumo_anual(df)
    resumo_mensal = gerar_resumo_mensal(df)
 
    # ------ relatório resumido no console -------
    print("=" * 60)
    print("Estacao:", metadados.get("Nome"), "(" + metadados.get("Codigo Estacao") + ")")
    print("Situacao atual:", metadados.get("Situacao"))
    print("Periodo:", df["data"].min().date(), "a", df["data"].max().date())
    print("Total de dias:", len(df))
    print("Dias com dado valido:", (df["dado_ausente"] == False).sum())
    print("Dias ausentes:", df["dado_ausente"].sum())
    print("-" * 60)
    print("Resumo por ano (dias ausentes e precipitação total):")
    print(resumo_anual.to_string(index=False))
    print("=" * 60)
 
    exportar_resultados(df, resumo_anual, resumo_mensal, metadados, pasta_do_arquivo + "/output")
 
    return df, resumo_anual, resumo_mensal, metadados
 
 
if __name__ == "__main__":
    # caminho do arquivo bruto baixado do BDMEP
    caminho = "dados_A409_D_2016-09-03_2026-09-03.csv"
 
    organizar_dados_bdmep(caminho)
