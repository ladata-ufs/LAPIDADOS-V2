import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# 1. Carregar os dados concatenados
df = pd.read_csv('dados_concatenados.csv', decimal='.')

# Tratamento básico de datas e valores nulos na chuva
df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
df['Chuva (mm)'] = pd.to_numeric(df['Chuva (mm)'], errors='coerce').fillna(0)

# -------------------------------------------------------------
# PREPARAÇÃO DAS BASES AGREGADAS
# -------------------------------------------------------------

# A. Acumulado Diário (Soma das 24 horas de cada dia)
df_diario = (
    df.groupby(df['Data'].dt.date)['Chuva (mm)'].sum().reset_index()
)
df_diario['Data'] = pd.to_datetime(df_diario['Data'])

# B. Acumulado Mensal Cronológico (Ano e Mês específicos, ex: 2023-05)
df['Ano_Mes'] = df['Data'].dt.to_period('M')
df_mensal_cronologico = (
    df.groupby('Ano_Mes')['Chuva (mm)'].sum().reset_index()
)
df_mensal_cronologico['Ano_Mes_Str'] = df_mensal_cronologico[
    'Ano_Mes'
].astype(str)

# C. Sazonalidade Típica (Média do acumulado mensal agrupado apenas pelo número do Mês 1 a 12)
# Primeiro calcula o acumulado de cada mês/ano, depois tira a média dos meses iguais
df_sazonal = (
    df_mensal_cronologico.assign(Mes=df_mensal_cronologico['Ano_Mes'].dt.month)
    .groupby('Mes')['Chuva (mm)']
    .mean()
    .reset_index()
)

nombres_meses = [
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
df_sazonal['Nome_Mes'] = df_sazonal['Mes'].apply(lambda x: nombres_meses[x - 1])

# -------------------------------------------------------------
# GERAÇÃO DOS GRÁFICOS
# -------------------------------------------------------------
sns.set_theme(style='whitegrid')

# 1. Gráfico de Linhas: Série Temporal Diária
plt.figure(figsize=(12, 5))
plt.plot(
    df_diario['Data'],
    df_diario['Chuva (mm)'],
    color='#1f77b4',
    linewidth=1.2,
    label='Chuva Diária',
)
plt.fill_between(
    df_diario['Data'], df_diario['Chuva (mm)'], color='#1f77b4', alpha=0.3
)
plt.title(
    'Série Temporal Diária da Precipitação (Picos de Chuva)',
    fontsize=14,
    fontweight='bold',
)
plt.xlabel('Data')
plt.ylabel('Chuva Acumulada no Dia (mm)')
plt.tight_layout()
plt.show()

# 2. Gráfico de Barras - Opção B: Total Acumulado por Mês/Ano (Ordem Cronológica)
plt.figure(figsize=(14, 5))
ax1 = sns.barplot(
    data=df_mensal_cronologico,
    x='Ano_Mes_Str',
    y='Chuva (mm)',
    color='#2b5c8f',
)
plt.title(
    'Opção B: Volume Total de Chuva por Mês/Ano (Histórico Cronológico)',
    fontsize=14,
    fontweight='bold',
)
plt.xlabel('Ano-Mês')
plt.ylabel('Chuva Acumulada no Mês (mm)')
plt.xticks(rotation=45)
for p in ax1.patches:
  if p.get_height() > 0:
    ax1.annotate(
        f'{p.get_height():.1f}',
        (p.get_x() + p.get_width() / 2.0, p.get_height()),
        ha='center',
        va='bottom',
        fontsize=8,
        xytext=(0, 3),
        textcoords='offset points',
    )
plt.tight_layout()
plt.show()

# 3. Gráfico de Barras - Opção A: Média do Acumulado Mensal (Sazonalidade Típica)
plt.figure(figsize=(10, 5))
ax2 = sns.barplot(
    data=df_sazonal, x='Nome_Mes', y='Chuva (mm)', palette='Blues_d'
)
plt.title(
    'Opção A: Sazonalidade Típica - Média do Acumulado Mensal',
    fontsize=14,
    fontweight='bold',
)
plt.xlabel('Mês do Ano')
plt.ylabel('Média de Chuva Acumulada (mm)')
for p in ax2.patches:
  if p.get_height() > 0:
    ax2.annotate(
        f'{p.get_height():.1f}',
        (p.get_x() + p.get_width() / 2.0, p.get_height()),
        ha='center',
        va='bottom',
        fontsize=9,
        xytext=(0, 3),
        textcoords='offset points',
    )
plt.tight_layout()
plt.show()