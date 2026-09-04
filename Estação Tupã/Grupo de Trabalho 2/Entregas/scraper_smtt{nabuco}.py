import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import logging
from dataclasses import dataclass, asdict
from typing import Optional

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
INTERVALO_REQUISICOES = 1.0

# Dicionários de Localidades (Aracaju)
BAIRROS_ARACAJU = {
    "13 de Julho": "Zona Sul", "17 de Março": "Zona Sul", "Aeroporto": "Zona Sul",
    "América": "Zona Oeste", "Atalaia": "Zona Sul", "Bugio": "Zona Norte",
    "Capucho": "Zona Oeste", "Centro": "Zona Centro", "Cidade Nova": "Zona Norte",
    "Cirurgia": "Zona Centro", "Coroa do Meio": "Zona Sul", "Dom Luciano": "Zona Norte",
    "Farolândia": "Zona Sul", "Getúlio Vargas": "Zona Centro", "Grageru": "Zona Sul",
    "Inácio Barbosa": "Zona Sul", "Industrial": "Zona Norte", "Jabotiana": "Zona Oeste",
    "Japãozinho": "Zona Norte", "Jardim Centenário": "Zona Norte", "Lamarão": "Zona Norte",
    "Luzia": "Zona Sul", "Macaxeira": "Zona Norte", "Olaria": "Zona Norte",
    "Palestina": "Zona Norte", "Pereira Lobo": "Zona Sul", "Ponto Novo": "Zona Sul",
    "Porto Dantas": "Zona Norte", "Salgado Filho": "Zona Sul", "Santa Maria": "Zona Sul",
    "Santo Antônio": "Zona Norte", "Santos Dumont": "Zona Norte", "São Conrado": "Zona Sul",
    "São José": "Zona Centro", "Siqueira Campos": "Zona Oeste", "Suíssa": "Zona Sul",
    "Zona de Expansão": "Zona de Expansão"
}

CONJUNTOS_LOCALIDADES = {
    "Augusto Franco": "Zona Sul", "Orlando Dantas": "Zona Sul", "Sol Nascente": "Zona Sul",
    "Santa Lúcia": "Zona Sul", "Castelo Branco": "Zona Oeste", "Médici": "Zona Sul",
    "Marcos Freire": "Zona Norte", "Fernando Collor": "Zona Norte", "Piabeta": "Zona Norte",
    "Beira Mar": "Zona Sul"
}

LOGRADOUROS_CONHECIDOS = [
    "Avenida Hermes Fontes", "Av. Hermes Fontes", "Avenida Francisco Porto",
    "Avenida Beira Mar", "Avenida Euclides Figueiredo", "Avenida Visconde de Maracaju",
    "Rua Bahia", "Avenida Acrísio Cruz", "Largo da Aparecida"
]

@dataclass
class RegistroAlagamento:
    data: str
    bairro: str
    zona: str
    logradouro: str
    titulo: str
    descricao: str
    fonte_url: str
    fonte: str

def eh_evento_alagamento(titulo: str, texto_completo: str) -> bool:
    texto = f"{titulo} {texto_completo}".lower()
    
    # 1. Filtro Negativo: Ignora projetos, manutenções, histórico e previsões
    ignorados = [
        "obra de", "obra da", "projetos de trânsito", "revitaliza", "macrodrenagem", 
        "previsão", "prevenir", "investimento", "histórico de alagamento", 
        "duplicação da ponte", "compra de", "ônibus", "carro roubado", 
        "sinistros", "chamadas", "resolver o problema de alagamento"
    ]
    if any(ign in texto for ign in ignorados):
        return False
        
    # 2. Filtro Positivo Estrito: Confirma que o evento de fato ocorreu
    confirmados = [
        "chuva que", "forte chuva", "chuvas fortes", "fortes chuvas", 
        "ponto de alagamento", "pontos de alagamento", "alagamento registrado", 
        "vias alagadas", "inundou", "transtornos causados", "placas perdidas", 
        "enchente", "efeitos da chuva", "monitoramento das chuvas", 
        "afetadas pelas chuvas", "impactos da chuva", "sob forte chuva", 
        "chuvas na última", "após fortes chuvas", "minimizar efeitos", 
        "atenção redobrada", "cuidados ao dirigir", "período de chuvas"
    ]
    return any(conf in texto for conf in confirmados)

def extrair_bairros(texto: str) -> list[tuple[str, str]]:
    if not texto: return []
    texto_lower = texto.lower()
    encontrados = []

    for bairro, zona in BAIRROS_ARACAJU.items():
        if bairro.lower() in texto_lower:
            encontrados.append((bairro, zona))
    for local, zona in CONJUNTOS_LOCALIDADES.items():
        if local.lower() in texto_lower:
            encontrados.append((local, zona))

    resultado = []
    vistos = set()
    for bairro, zona in encontrados:
        chave = bairro.lower()
        if chave not in vistos:
            vistos.add(chave)
            resultado.append((bairro, zona))
    return resultado

def extrair_logradouros(texto: str) -> list[str]:
    if not texto: return []
    encontrados = []
    for logr in LOGRADOUROS_CONHECIDOS:
        if logr.lower() in texto.lower():
            encontrados.append(logr)
    padroes = [
        r'(?:rua|avenida|av\.|travessa|alameda|praça)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:de|do|da|dos|das)\s+)?[A-ZÀ-Ú]?[a-zà-ú]*(?:\s+[A-ZÀ-Ú]?[a-zà-ú]*)*)',
        r'(?:canal|rio)\s+(?:do\s+|da\s+|de\s+)?([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú]?[a-zà-ú]*)*)',
    ]
    for padrao in padroes:
        matches = re.findall(padrao, texto, re.IGNORECASE)
        for m in matches:
            logr = m.strip()
            if len(logr) > 3 and logr.lower() not in ["que", "para", "com", "por", "mais"]:
                if logr not in encontrados:
                    encontrados.append(logr)
    return encontrados[:5]

def obter_conteudo_artigo(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        
        for tag in soup.find_all(["header", "footer", "nav", "aside"]):
            tag.extract()
            
        for seletor in ["div.entry-content", "article", "div.post-content", "main"]:
            elem = soup.select_one(seletor)
            if elem and len(elem.get_text(strip=True)) > 100:
                return re.sub(r'\s+', ' ', elem.get_text(separator=" ", strip=True))
        body = soup.find("body")
        if body:
            return re.sub(r'\s+', ' ', body.get_text(separator=" ", strip=True))
    except Exception as e:
        logger.debug(f"Erro requests: {e}")
    return ""

def coletar_smtt(paginas_por_termo=20) -> list[dict]:
    base_url = "https://smtt.aracaju.se.gov.br"
    artigos = []
    urls_vistas = set()
    termos_busca = ["ALAGAMENTO", "CHUVA", "INUNDACAO"]

    for termo in termos_busca:
        logger.info(f"🔍 Buscando: {termo}")
        pagina = 1
        while pagina <= paginas_por_termo:
            url_busca = f"{base_url}/anos-anteriores/?search_text={termo}&filter_year=0&cat=0&paged={pagina}"
            try:
                resp = requests.get(url_busca, headers=HEADERS, timeout=60)
                resp.raise_for_status()
            except Exception as e:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.find_all("div", class_="lista-admin-card")
            rows = soup.find_all("tr")

            items_encontrados = []
            if cards:
                for card in cards:
                    titulo_elem = card.find(["h2", "h3", "h4", "a"])
                    link_elem = card.find("a", href=True)
                    data_span = card.find("div", class_="meta")
                    if titulo_elem and link_elem:
                        dt_text = data_span.get_text(strip=True) if data_span else "Data não disponível"
                        items_encontrados.append((titulo_elem.get_text(strip=True), link_elem.get("href", ""), dt_text))
            elif rows:
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        link_elem = cols[0].find("a", href=True)
                        if link_elem:
                            items_encontrados.append((link_elem.get_text(strip=True), link_elem.get("href", ""), cols[2].get_text(strip=True)))

            if not items_encontrados:
                break 

            for titulo, link, data in items_encontrados:
                if not link or link in urls_vistas:
                    continue
                urls_vistas.add(link)
                artigos.append({"titulo": titulo, "link": link, "data": data})
            
            pagina += 1
            time.sleep(INTERVALO_REQUISICOES)

    logger.info(f"📊 SMTT: {len(artigos)} alertas base coletados")
    return artigos

def processar_artigos(artigos: list[dict]) -> list[RegistroAlagamento]:
    registros = []
    for i, artigo in enumerate(artigos, 1):
        titulo = artigo["titulo"]
        link = artigo["link"]
        data = artigo["data"]

        logger.info(f"[{i}/{len(artigos)}] Lendo: {titulo[:65]}...")
        conteudo = obter_conteudo_artigo(link)
        texto_completo = f"{titulo} {conteudo}"

        if not eh_evento_alagamento(titulo, texto_completo):
            continue

        bairros = extrair_bairros(texto_completo)
        logradouros = extrair_logradouros(texto_completo)
        
        # Manter a descrição completa para a planilha expanded
        desc_final = re.sub(r'\s+', ' ', texto_completo) if conteudo else titulo
        logr_str = "; ".join(logradouros) if logradouros else "Não especificado"

        if bairros:
            for bairro, zona in bairros:
                registros.append(RegistroAlagamento(
                    data, bairro, zona, logr_str, titulo, desc_final, link, "SMTT Aracaju"
                ))
        else:
            registros.append(RegistroAlagamento(
                data, "Aracaju (bairro não especificado)", "Não identificada", logr_str, titulo, desc_final, link, "SMTT Aracaju"
            ))
        time.sleep(INTERVALO_REQUISICOES)
    return registros

def salvar_csv(registros: list[RegistroAlagamento], arquivo_base: str):
    if not registros:
        logger.warning("Nenhum registro validado.")
        return

    arq_required = f"{arquivo_base}_required.csv"
    arq_expanded = f"{arquivo_base}_expanded.csv"

    # Required recebe a descrição curta (conforme pedido original pelo Yami)
    with open(arq_required, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["data", "localizacao_bairro", "descricao"], quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for reg in registros:
            loc = reg.bairro + (f" ({reg.logradouro})" if reg.logradouro != "Não especificado" else "")
            desc_curta = reg.descricao[:500] + ("..." if len(reg.descricao) > 500 else "")
            writer.writerow({"data": reg.data, "localizacao_bairro": loc, "descricao": desc_curta})

    # Expanded recebe o texto completo (descrição do que aconteceu) sem cortes
    with open(arq_expanded, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["data", "localizacao_bairro", "titulo", "descricao", "link", "zona", "fonte"], quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for reg in registros:
            loc = reg.bairro + (f" ({reg.logradouro})" if reg.logradouro != "Não especificado" else "")
            writer.writerow({
                "data": reg.data, "localizacao_bairro": loc, "titulo": reg.titulo,
                "descricao": reg.descricao, "link": reg.fonte_url, "zona": reg.zona, "fonte": reg.fonte
            })

    logger.info(f"✅ {len(registros)} registros salvos com sucesso.")

def main():
    logger.info("Iniciando scraper dedicado da SMTT...")
    artigos = coletar_smtt(paginas_por_termo=20)
    registros = processar_artigos(artigos)
    
    # Ordenar por data cronológica reversa (tentativa simples de ordenar)
    registros.sort(key=lambda x: x.data, reverse=True)
    
    salvar_csv(registros, "dados_smtt")
    logger.info("Finalizado!")

if __name__ == "__main__":
    main()
