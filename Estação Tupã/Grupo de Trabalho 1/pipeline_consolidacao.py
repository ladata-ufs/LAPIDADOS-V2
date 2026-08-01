import pandas as pd
import os
import glob
from datetime import datetime

class ConsolidadorINMET:
    def __init__(self, diretorio_arquivos):
        self.diretorio = diretorio_arquivos
        self.arquivos = []
        self.dados_consolidados = pd.DataFrame()
        self.metadados_arquivos = []

    def listar_arquivos(self):
        padrao = os.path.join(self.diretorio, "*.CSV")
        self.arquivos = glob.glob(padrao)
        print(f"Encontrados {len(self.arquivos)} arquivos CSV para consolidar.")
        return self.arquivos

    def extrair_metadados(self, caminho_arquivo):
        metadados = {}
        try:
            with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                for i in range(8):
                    linha = f.readline()
                    if ';' in linha:
                        partes = linha.strip().split(';')
                        if len(partes) >= 2:
                            chave = partes[0].strip()
                            valor = partes[1].strip()
                            metadados[chave] = valor
        except Exception as e:
            print(f"Erro ao ler metadados de {os.path.basename(caminho_arquivo)}: {e}")
        return metadados

    def consolidar_dados(self):
        arquivos = self.listar_arquivos()
        if not arquivos:
            print("Nenhum arquivo encontrado.")
            return None

        for arquivo in arquivos:
            print(f"Consolidando: {os.path.basename(arquivo)}")
            metadados = self.extrair_metadados(arquivo)
            self.metadados_arquivos.append(metadados)

            try:
                df_temp = pd.read_csv(
                    arquivo,
                    sep=';',
                    decimal=',',
                    encoding='latin-1',
                    skiprows=8,
                    low_memory=False
                )
                self.dados_consolidados = pd.concat([self.dados_consolidados, df_temp], ignore_index=True)
            except Exception as e:
                print(f"Erro ao ler o arquivo {os.path.basename(arquivo)}: {e}")

        print(f"Consolidação concluída. Total de linhas: {len(self.dados_consolidados)}")
        return self.dados_consolidados

    def salvar_dados_consolidados(self, nome_arquivo_saida="dados_inmet_consolidados.csv"):
        if self.dados_consolidados.empty:
            print("Não há dados para salvar.")
            return
        self.dados_consolidados.to_csv(nome_arquivo_saida, sep=';', decimal=',', index=False, encoding='latin-1')
        print(f"Dados consolidados salvos em: {nome_arquivo_saida}")

    def salvar_metadados(self, nome_arquivo_saida="metadados_arquivos.json"):
        import json
        with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(self.metadados_arquivos, f, ensure_ascii=False, indent=2)
        print(f"Metadados dos arquivos salvos em: {nome_arquivo_saida}")


if __name__ == "__main__":
    diretorio = "/home/krpto/Documentos/UFS/LADATA/Estação Tupa/Semana 1/daods/"

    print("Iniciando consolidação dos dados INMET para a Semana 1...")
    print("=" * 60)

    consolidador = ConsolidadorINMET(diretorio)
    dados_consolidados = consolidador.consolidar_dados()

    if dados_consolidados is not None and not dados_consolidados.empty:
        consolidador.salvar_dados_consolidados("dados_inmet_consolidados.csv")
        consolidador.salvar_metadados("metadados_arquivos.json")

        print("\n" + "=" * 60)
        print("RESUMO DA CONSOLIDAÇÃO")
        print("=" * 60)
        print(f"Total de arquivos processados: {len(consolidador.arquivos)}")
        print(f"Total de linhas no arquivo consolidado: {len(dados_consolidados)}")
        print(f"Colunas no arquivo consolidado: {list(dados_consolidados.columns)}")
        print("\nArquivos gerados para a Semana 1:")
        print("   dados_inmet_consolidados.csv")
        print("   metadados_arquivos.json")
    else:
        print("Nenhum dado foi consolidado. Verifique o diretório dos arquivos.")
