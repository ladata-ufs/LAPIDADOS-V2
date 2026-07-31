import pandas as pd

# ==========================
# Leitura
# ==========================
df = pd.read_csv(
    "inmet_aracaju.csv",
    sep=";",
    low_memory=False
)

# ==========================
# Trata Hora
# ==========================
# Ex.: 0 -> 0000
#      100 -> 0100
#      900 -> 0900
#      2300 -> 2300

df["Hora (UTC)"] = (
    df["Hora (UTC)"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.zfill(4)
)

# ==========================
# Cria Timestamp
# ==========================

df["timestamp"] = pd.to_datetime(
    df["Data"] + " " + df["Hora (UTC)"],
    format="%d/%m/%Y %H%M"
)

# ==========================
# Converte números
# ==========================

colunas_numericas = df.columns.drop(
    ["Data", "Hora (UTC)", "timestamp"]
)

for col in colunas_numericas:
    df[col] = (
        df[col]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .replace("", pd.NA)
    )

    df[col] = pd.to_numeric(df[col], errors="coerce")

# ==========================
# Reorganiza colunas
# ==========================

colunas = ["timestamp"] + [
    c for c in df.columns
    if c not in ["timestamp", "Data", "Hora (UTC)"]
]

df = df[colunas]

# ==========================
# Ordena
# ==========================

df = df.sort_values("timestamp")

# ==========================
# Salva
# ==========================
df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
df.to_csv(
    "inmet_aracaju_tratado.csv",
    sep=",",
    decimal=".",
    encoding="utf-8",
    index=False,
    date_format="%Y-%m-%d %H:%M:%S"
)

print(df.info())
print(df.head())