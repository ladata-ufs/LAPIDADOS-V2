# mantendo uma separação para que esse arquivo gerador de estatisticas e graficos sirva somente para analisar
# os dados previamente limpos pelo arquivo anterior. boa prática! (fonte: eu)

#############
# bibliotecas
#############

# para manipular as atuais tabelas em python
import pandas as pd
# matplotlib é a biblioteca padrão pra gráficos estáticos em python
import matplotlib.pyplot as plt
# os para garantir a saída
import os
 
 
####################
# configuração geral
####################
 
# armazenamos sommente os meses, em ordem crescente, definindo o eixo x do gráfico.
MESES = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


#################################
# função de carregamento de dados
#################################

def carregar_dados_limpos(caminho_csv="output/dados_limpos.csv"):
    # esse parse_dates serve para converter a data, que o pandas salva em csv (doc original) em datetime de novo
    df = pd.read_csv(caminho_csv, parse_dates=["data"])
    return df


####################################
# função de estatísticas descritivas 
####################################

def gerar_estatisticas_descritivas(df):
    # esse (dropna() é essencial aqui, se deixarmos os NaN dos dias ausentes, eles distorcem a contagem e a média achando que nao choveu)
    serie_valida = df["precipitacao_mm"].dropna()

    estatisticas = {
        # arredondamos os valores para facilitar o calculo
        "n_dias_validos": int(serie_valida.count()),
        "media_mm": round(serie_valida.mean(), 2),
        "mediana_mm": round(serie_valida.median(), 2),
        "desvio_padrao_mm": round(serie_valida.std(), 2),
        "minimo_mm": round(serie_valida.min(), 2),
        "maximo_mm": round(serie_valida.max(), 2),
        "percentil_25_mm": round(serie_valida.quantile(0.25), 2),
        "percentil_75_mm": round(serie_valida.quantile(0.75), 2),
        # dias em que choveu de fato, diferente de dias sem dado 
        "dias_com_chuva": int((serie_valida > 0).sum()),
        "dias_sem_chuva": int((serie_valida == 0).sum()),
    }
    return estatisticas


##########################################
# função de agregação climatologica mensal 
##########################################

def calcular_precipitacao_media_mensal(df):
    # agrupamos só por "mes" e não por "ano" e "mes" como no resumo_mensal.csv (que ainda nao tava no output)
    media_por_mes = df.groupby("mes")["precipitacao_mm"].mean().round(2)
    # reindexar garante que os 12 meses apareçam, mesmo que algum mês não tenha dado
    media_por_mes = media_por_mes.reindex(range(1, 13))
    return media_por_mes


################################
# função de visualização gráfica
################################

def plotar_grafico_precipitacao_media_mensal(media_por_mes, caminho_saida="output/grafico_precipitacao_media_mensal.png"):
    # especificacao o matplotlib: ele trabalha comm dois objetos de eixo (x e y) mas salva a figura
    fig, eixo = plt.subplots(figsize=(10, 6))

    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    # o formato o eixo.bar é o x e a altura, e a altura aqui é determinada pelos valores de cada mes existente (12)
    eixo.bar(meses, media_por_mes.values, color="#4A0E0E")

    ## importantissimo pra todo grafico!!!!!
    eixo.set_title("Precipitação Média Mensal - Estação A409 (Aracaju)")
    eixo.set_xlabel("Mês")
    eixo.set_ylabel("Precipitação média (mm/dia)")
    eixo.grid(axis="y", linestyle="--", alpha=0.4)

    for indice, valor in enumerate(media_por_mes.values):
        # adicionando detalhes nas barras graficas pra facilitar leitura
        eixo.text(indice, valor + 0.05, f"{valor:.1f}", ha="center", fontsize=9)

    fig.tight_layout()

    # cria a pasta pra saida se ainda nao houver
    pasta_saida = os.path.dirname(caminho_saida)
    if pasta_saida and not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    # salvando o grafico no disco 
    fig.savefig(caminho_saida, dpi=150)
    plt.close(fig)


##########
# pipeline
##########

def analisar_precipitacao(caminho_dados_limpos="output/dados_limpos.csv"):
    df = carregar_dados_limpos(caminho_dados_limpos)

    estatisticas = gerar_estatisticas_descritivas(df)
    media_por_mes = calcular_precipitacao_media_mensal(df)

    # espelhando a estrutura do primeiro arquivo
    print("=" * 60)
    print("ESTATÍSTICAS DESCRITIVAS - PRECIPITAÇÃO DIÁRIA")
    print("=" * 60)
    for chave, valor in estatisticas.items():
        print(f"{chave:.<30} {valor}")

    print("-" * 60)
    print("PRECIPITAÇÃO MÉDIA POR MÊS (climatologia, todos os anos)")
    for mes_numero, nome_mes in zip(range(1, 13), MESES):
        print(f"{nome_mes}: {media_por_mes.loc[mes_numero]:.2f} mm/dia")
    print("=" * 60)

    plotar_grafico_precipitacao_media_mensal(media_por_mes)

    return estatisticas, media_por_mes


if __name__ == "__main__":
    analisar_precipitacao()


