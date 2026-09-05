import glob
import pandas as pd 

csvS_lidos = glob.glob("dia_2/raw_data/aracaju_*.csv")

lista_df = []
print(csvS_lidos[0])
df_temp = pd.read_csv(csvS_lidos[1], sep=';')
print(type(df_temp.columns))

for csv in csvS_lidos:
    df = pd.read_csv(csv, sep=';')

    # Preenche os valores numéricos faltantes com a média da coluna
    df = df.fillna(df.mean(numeric_only=True))

    # Ajusta a formatação das datas
    df["Data"] = pd.to_datetime(df['Data'], errors='coerce')

    lista_df.append(df)

dados_concatenados = pd.concat(lista_df, ignore_index=False)
dados_concatenados.to_csv("dados_concatenados.csv", decimal='.', sep=';')
