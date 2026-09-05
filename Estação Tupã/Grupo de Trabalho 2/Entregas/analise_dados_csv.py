import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

df = pd.read_csv(
    'dados_concatenados.csv',
    sep=';',
    decimal=',',
    encoding='utf-8',
)

df['Chuva (mm)'] = pd.to_numeric(df['Chuva (mm)'], errors='coerce').fillna(0)
df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)

acumulado_diario = (
    df.groupby(df['Data'].dt.date)['Chuva (mm)'].sum().reset_index()
)
acumulado_diario.columns = ['Data', 'Chuva_Total_Dia']
acumulado_diario['Data'] = pd.to_datetime(acumulado_diario['Data'])

# Agrupa por mês e ano
df['Ano_Mes'] = df['Data'].dt.to_period('M')
acumulado_mensal = df.groupby('Ano_Mes')['Chuva (mm)'].sum().reset_index()
acumulado_mensal.columns = ['Ano_Mes', 'Chuva_Total_Mes']

# Configuração visual geral
sns.set_theme(style='whitegrid')
plt.figure(figsize=(12, 5))
plt.plot(
    acumulado_diario['Data'],
    acumulado_diario['Chuva_Total_Dia'],
    color='#1f77b4',
    linewidth=1.2,
)
plt.fill_between(
    acumulado_diario['Data'],
    acumulado_diario['Chuva_Total_Dia'],
    color='#1f77b4',
    alpha=0.3,
)

plt.title('Precipitação Diária Acumulada - Picos de Chuva', fontsize=14, pad=15)
plt.xlabel('Data', fontsize=11)
plt.ylabel('Chuva (mm)', fontsize=11)
plt.tight_layout()
plt.savefig('Precipitação Diária Acumulada - Picos de Chuva')
plt.show()


acumulado_mensal['Ano_Mes_Str'] = acumulado_mensal['Ano_Mes'].astype(str)



plt.figure(figsize=(14, 5))
sns.barplot(
    data=acumulado_mensal,
    x='Ano_Mes_Str',
    y='Chuva_Total_Mes',
    palette='Blues_d',
)

plt.title(
    'Total Acumulado de Precipitação por Mês/Ano (Ordem Cronológica)',
    fontsize=14,
    pad=15,
)
plt.xlabel('Ano-Mês', fontsize=11)
plt.ylabel('Chuva Acumulada (mm)', fontsize=11)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('Chuva Acumulada (mm)')
plt.show()

acumulado_mensal['Mes_Num'] = acumulado_mensal['Ano_Mes'].dt.month

sazonalidade = (
    acumulado_mensal.groupby('Mes_Num')['Chuva_Total_Mes']
    .mean()
    .reset_index()
)

# Mapear números para nomes dos meses em português
nomes_meses = [
    'Jan',
    'Fev',
    'Mar',
    'Abr',
    'Mai',
    'Jun',
    'Jul',
    'Ago',
    'Set',
    'Out',
    'Nov',
    'Dez',
]
sazonalidade['Nome_Mes'] = sazonalidade['Mes_Num'].apply(
    lambda x: nomes_meses[x - 1]
)

plt.figure(figsize=(10, 5))
sns.barplot(
    data=sazonalidade, x='Nome_Mes', y='Chuva_Total_Mes', color='#4c72b0'
)

plt.title(
    'Sazonalidade Típica da Precipitação (Média Acumulada por Mês)',
    fontsize=14,
    pad=15,
)
plt.xlabel('Mês', fontsize=11)
plt.ylabel('Média da Chuva Acumulada (mm)', fontsize=11)
plt.tight_layout()
plt.savefig('Média da Chuva Acumulada (mm)')
plt.show()