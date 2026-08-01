import pandas as pd
import os
import glob
from datetime import datetime
from fpdf import FPDF
import json
import re

class RelatorioINMET:
    def __init__(self, diretorio_arquivos):
        self.diretorio = diretorio_arquivos
        self.arquivos = []
        self.dados_estacoes = []
        
    def listar_arquivos(self):
        padrao = os.path.join(self.diretorio, "*.CSV")
        self.arquivos = glob.glob(padrao)
        print(f"Encontrados {len(self.arquivos)} arquivos CSV")
        return self.arquivos
    
    def extrair_metadados(self, caminho_arquivo):
        try:
            with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                linhas = [next(f) for _ in range(10)]
            
            metadados = {}
            for linha in linhas[:8]:
                if ';' in linha:
                    partes = linha.strip().split(';')
                    if len(partes) >= 2:
                        chave = partes[0].strip()
                        valor = partes[1].strip()
                        metadados[chave] = valor
            
            cabecalho = None
            for linha in linhas[8:10]:
                if 'Data;Hora UTC' in linha:
                    cabecalho = linha.strip().split(';')
                    break
            
            df = pd.read_csv(
                caminho_arquivo,
                sep=';',
                decimal=',',
                encoding='latin-1',
                skiprows=8,
                nrows=5
            )
            
            with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                total_linhas = sum(1 for _ in f)
            
            nome_arquivo = os.path.basename(caminho_arquivo)
            
            uf = metadados.get('UF', '')
            estacao = metadados.get('ESTACAO', '')
            
            if not estacao:
                partes_nome = nome_arquivo.split('_')
                if len(partes_nome) >= 5:
                    uf = partes_nome[2] if len(partes_nome) > 2 else ''
                    estacao = partes_nome[4] if len(partes_nome) > 4 else ''
            
            resultado = {
                'arquivo': nome_arquivo,
                'uf': uf,
                'estacao': estacao,
                'codigo_wmo': metadados.get('CODIGO (WMO)', ''),
                'latitude': metadados.get('LATITUDE', ''),
                'longitude': metadados.get('LONGITUDE', ''),
                'altitude': metadados.get('ALTITUDE', ''),
                'data_fundacao': metadados.get('DATA DE FUNDACAO', ''),
                'cabecalho': cabecalho,
                'amostra_dados': df.head(3).to_dict('records') if not df.empty else [],
                'total_linhas': total_linhas,
                'colunas_principais': self._identificar_colunas_principais(cabecalho),
                'dados_faltantes': self._verificar_dados_faltantes(caminho_arquivo)
            }
            
            return resultado
            
        except Exception as e:
            print(f"Erro ao processar {caminho_arquivo}: {e}")
            return None
    
    def _identificar_colunas_principais(self, cabecalho):
        if not cabecalho:
            return {}
        
        colunas = {}
        padroes = {
            'precipitacao': r'PRECIPITA',
            'temperatura': r'TEMPERATURA DO AR',
            'umidade': r'UMIDADE RELATIVA',
            'pressao': r'PRESSAO ATMOSFERICA',
            'vento': r'VENTO, VELOCIDADE'
        }
        
        for i, col in enumerate(cabecalho):
            col_limpo = col.strip().upper()
            for chave, padrao in padroes.items():
                if re.search(padrao, col_limpo, re.IGNORECASE):
                    if chave not in colunas:
                        colunas[chave] = []
                    colunas[chave].append(i)
        
        return colunas
    
    def _verificar_dados_faltantes(self, caminho_arquivo):
        try:
            with open(caminho_arquivo, 'r', encoding='latin-1') as f:
                linhas = f.readlines()
            
            linhas_dados = linhas[9:]
            total_linhas = len(linhas_dados)
            
            linhas_vazias = 0
            for linha in linhas_dados:
                if ';;;;;;;;' in linha or linha.count(';') > 30:
                    linhas_vazias += 1
            
            return {
                'total_linhas_dados': total_linhas,
                'linhas_com_dados_faltantes': linhas_vazias,
                'percentual_faltante': (linhas_vazias / total_linhas * 100) if total_linhas > 0 else 0
            }
        except:
            return {'total_linhas_dados': 0, 'linhas_com_dados_faltantes': 0, 'percentual_faltante': 0}
    
    def processar_todos_arquivos(self):
        arquivos = self.listar_arquivos()
        
        for arquivo in arquivos:
            print(f"Processando: {os.path.basename(arquivo)}")
            metadados = self.extrair_metadados(arquivo)
            if metadados:
                self.dados_estacoes.append(metadados)
        
        print(f"Processados {len(self.dados_estacoes)} arquivos com sucesso")
        return self.dados_estacoes
    
    def gerar_pdf(self, nome_arquivo_saida="relatorio_semana1.pdf"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        
        pdf.cell(0, 10, "RELATORIO SEMANA 1 - PROJETO TUPA", ln=True, align='C')
        pdf.cell(0, 10, "Analise de Dados INMET", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Data de geracao: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "RESUMO GERAL", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, f"Total de arquivos processados: {len(self.dados_estacoes)}", ln=True)
        
        estacoes_lista = [f"{d['estacao']} ({d['uf']}) - WMO: {d['codigo_wmo']}" for d in self.dados_estacoes]
        pdf.cell(0, 10, f"Estacoes encontradas: {', '.join(estacoes_lista)}", ln=True)
        pdf.ln(10)
        
        for i, estacao in enumerate(self.dados_estacoes, 1):
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, f"ESTACAO {i}: {estacao['estacao']}", ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. METADADOS DA ESTACAO", ln=True)
            pdf.set_font("Arial", "", 10)
            
            metadados_dict = {
                'UF': estacao['uf'],
                'Codigo WMO': estacao['codigo_wmo'],
                'Latitude': estacao['latitude'],
                'Longitude': estacao['longitude'],
                'Altitude': estacao['altitude'],
                'Data de Fundacao': estacao['data_fundacao'],
                'Arquivo': estacao['arquivo']
            }
            
            for chave, valor in metadados_dict.items():
                pdf.cell(0, 7, f"   {chave}: {valor}", ln=True)
            
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "2. VARIAVEIS DISPONIVEIS", ln=True)
            pdf.set_font("Arial", "", 10)
            
            if estacao['cabecalho']:
                for col in estacao['cabecalho']:
                    pdf.cell(0, 6, f"   {col.strip()}", ln=True)
            
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "3. COLUNAS PRINCIPAIS IDENTIFICADAS", ln=True)
            pdf.set_font("Arial", "", 10)
            
            for tipo, indices in estacao['colunas_principais'].items():
                if indices:
                    pdf.cell(0, 6, f"   {tipo.capitalize()}: colunas {indices}", ln=True)
            
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "4. AMOSTRA DE DADOS (primeiras 3 linhas)", ln=True)
            pdf.set_font("Arial", "", 9)
            
            if estacao['amostra_dados']:
                for amostra in estacao['amostra_dados']:
                    itens = list(amostra.items())[:6]
                    texto = "   " + " | ".join([f"{k[:15]}: {v}" for k, v in itens])
                    pdf.multi_cell(0, 5, texto)
            
            pdf.ln(5)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "5. ANALISE DE DADOS FALTANTES", ln=True)
            pdf.set_font("Arial", "", 10)
            
            faltantes = estacao['dados_faltantes']
            pdf.cell(0, 7, f"   Total de linhas de dados: {faltantes['total_linhas_dados']}", ln=True)
            pdf.cell(0, 7, f"   Linhas com dados faltantes: {faltantes['linhas_com_dados_faltantes']}", ln=True)
            pdf.cell(0, 7, f"   Percentual de dados faltantes: {faltantes['percentual_faltante']:.2f}%", ln=True)
            
            pdf.ln(5)
        
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, f"Relatorio gerado automaticamente pelo script de analise da Semana 1 - {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
        
        pdf.output(nome_arquivo_saida)
        print(f"PDF gerado com sucesso: {nome_arquivo_saida}")
        
        return nome_arquivo_saida
    
    def gerar_sumario_json(self, nome_arquivo_saida="sumario_estacoes.json"):
        with open(nome_arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(self.dados_estacoes, f, ensure_ascii=False, indent=2)
        print(f"JSON gerado com sucesso: {nome_arquivo_saida}")
        return nome_arquivo_saida


if __name__ == "__main__":
    # CORREÇÃO: Use apenas o caminho do diretório, não uma tupla de arquivos
    diretorio = "/home/krpto/Documentos/UFS/LADATA/Estação Tupa/Semana 1/daods/"
    
    print("Iniciando processamento dos dados INMET...")
    print("=" * 60)
    
    relatorio = RelatorioINMET(diretorio)
    dados = relatorio.processar_todos_arquivos()
    
    if dados:
        pdf_gerado = relatorio.gerar_pdf("relatorio_semana1.pdf")
        json_gerado = relatorio.gerar_sumario_json("sumario_estacoes.json")
        
        print("\n" + "=" * 60)
        print("RESUMO FINAL")
        print("=" * 60)
        print(f"Total de estacoes processadas: {len(dados)}")
        for d in dados:
            print(f"   {d['estacao']} ({d['uf']}) - WMO: {d['codigo_wmo']}")
            print(f"     Dados faltantes: {d['dados_faltantes']['percentual_faltante']:.1f}%")
        
        print(f"\nArquivos gerados:")
        print(f"   {pdf_gerado}")
        print(f"   {json_gerado}")
    else:
        print("Nenhum dado foi processado. Verifique o diretorio dos arquivos.")