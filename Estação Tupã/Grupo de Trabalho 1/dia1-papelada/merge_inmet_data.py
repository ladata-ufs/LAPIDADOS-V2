import pandas as pd
import glob
import os

# Localiza todos os arquivos no padrão
arquivos = sorted(glob.glob("inmet_aracaju_*.csv"))

# Lê e armazena os DataFrames
dfs = [pd.read_csv(arquivo,sep=';', low_memory=False) for arquivo in arquivos]

# Une todos os DataFrames
df_final = pd.concat(dfs, ignore_index=True)

# Salva o arquivo consolidado
df_final.to_csv("inmet_aracaju.csv", index=False, sep=';')

print(f"{len(arquivos)} arquivos unidos com sucesso.")
print(f"Total de registros: {len(df_final)}")
print("Arquivo salvo como: inmet_aracaju.csv")