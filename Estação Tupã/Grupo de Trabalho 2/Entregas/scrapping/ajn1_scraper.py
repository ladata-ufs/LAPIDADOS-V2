import os
import re
import time
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de Logging para monitorar a execução
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


@dataclass
class ArticleData:
    """Estrutura de dados para armazenar os campos extraídos de um artigo."""

    data: str
    localizacao: str
    texto: str
    titulo: str
    link: str

    def to_required_dict(self) -> Dict[str, str]:
        """Retorna apenas os campos exigidos no arquivo 'requirde_ajn1_data.csv'."""
        return {"data": self.data, "localizacao": self.localizacao, "texto": self.texto}

    def to_expanded_dict(self) -> Dict[str, str]:
        """Retorna os campos completos para o arquivo 'explanded__ajn1_data.csv'."""
        return {
            "data": self.data,
            "localizacao": self.localizacao,
            "texto": self.texto,
            "titulo": self.titulo,
            "link": self.link,
        }


class LocationExtractor:
    """
    Classe responsável por extrair informações de localização geográfica
    a partir de títulos e trechos de notícias.
    """

    # Lista de municípios de Sergipe e regiões comuns cobridas pelo portal AJN1
    SERGIPE_MUNICIPALITIES = [
        "Aracaju",
        "Nossa Senhora do Socorro",
        "Lagarto",
        "Itabaiana",
        "Estância",
        "São Cristóvão",
        "Maruim",
        "Laranjeiras",
        "Barra dos Coqueiros",
        "Propriá",
        "Tobias Barreto",
        "Simão Dias",
        "Itaporanga d'Ajuda",
        "Capela",
        "Canindé de São Francisco",
        "Neópolis",
        "Japaratuba",
        "Campo do Brito",
        "Boquim",
        "Carmópolis",
        "Pirambu",
        "Nossa Senhora das Dores",
        "Poço Redondo",
        "Porto da Folha",
        "Umbaúba",
        "Sergipe",
        "Grande Aracaju",
        "Zona Sul",
        "Zona Norte",
        "Centro",
        "Jabotiana",
        "Jardins",
        "Coroa do Meio",
        "Atalaia",
    ]

    def __init__(self):
        # Compila expressão regular para buscas eficientes
        escaped_cities = [re.escape(city) for city in self.SERGIPE_MUNICIPALITIES]
        self.city_pattern = re.compile(
            rf"\b({'|'.join(escaped_cities)})\b", re.IGNORECASE
        )

        # Padrão genérico de preposição + local (ex: "em Aracaju", "no bairro Jabotiana")
        self.preposition_pattern = re.compile(
            r"\b(?:em|no|na|nos|nas|para|de)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:de|da|do|dos|das|e)\s+[A-ZÀ-Ú][a-zà-ú]+|\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            re.UNICODE,
        )

    def extract(self, title: str, text: str) -> str:
        """
        Extrai a localização combinando busca por municípios conhecidos de Sergipe
        e heurísticas gramaticais de preposição.

        Args:
            title (str): Título da notícia.
            text (str): Exerto/resumo ou conteúdo da notícia.

        Returns:
            str: Nome da localização identificada ou 'Não informada'.
        """
        full_content = f"{title}. {text}"

        # 1. Busca direta por municípios e bairros de Sergipe conhecidos
        matches = self.city_pattern.findall(full_content)
        if matches:
            # Elimina duplicatas preservando a caixa original
            unique_locations = list(dict.fromkeys([m.title() for m in matches]))
            return ", ".join(unique_locations)

        # 2. Heurística baseada em preposição caso não encontre na lista predefinida
        prep_matches = self.preposition_pattern.findall(title)
        if prep_matches:
            return prep_matches[0].strip()

        return "Não informada"


class AJN1Scraper:
    """
    Classe responsável por gerenciar o Selenium WebDriver, navegar pelas páginas de busca
    do AJN1, fazer o parse do HTML com BeautifulSoup e extrair as informações.
    """

    def __init__(self, headless: bool = True, timeout: int = 15):
        """
        Inicializa a classe com as configurações do navegador e extrator de localização.

        Args:
            headless (bool): Se True, executa o Chrome em modo invisível (sem janela).
            timeout (int): Tempo máximo de espera para elementos carregarem no DOM.
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.location_extractor = LocationExtractor()

    def _init_driver(self) -> None:
        """Configura e inicializa a instância do Chrome WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def get_page_soup(self, url: str) -> BeautifulSoup:
        """
        Navega até a URL especificada utilizando o Selenium e retorna o objeto BeautifulSoup.

        Args:
            url (str): URL da página a ser raspada.

        Returns:
            BeautifulSoup: Objeto BeautifulSoup contendo o HTML processado.
        """
        if not self.driver:
            self._init_driver()

        logging.info(f"Acessando URL: {url}")
        self.driver.get(url)

        # Aguarda a presença da lista de artigos
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "archive-card"))
            )
        except Exception as e:
            logging.warning(f"Aviso ao aguardar carregamento dos artigos: {e}")

        # Retorna o HTML traduzido pelo BeautifulSoup
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def parse_article(self, article_tag: BeautifulSoup) -> Optional[ArticleData]:
        """
        Realiza o parse de uma tag <article class="archive-card"> individual.

        Args:
            article_tag (BeautifulSoup): Tag contendo os dados da notícia.

        Returns:
            Optional[ArticleData]: Objeto preenchido ou None em caso de falha.
        """
        try:
            # 1. Título e Link
            title_tag = article_tag.select_one(".archive-card-title a")
            title = title_tag.get_text(strip=True) if title_tag else ""
            link = title_tag.get("href", "") if title_tag else ""

            # 2. Data da notícia
            date_tag = article_tag.select_one(".meta-date")
            date_str = date_tag.get_text(strip=True) if date_tag else ""

            # 3. Texto (Excerpt)
            excerpt_tag = article_tag.select_one(".archive-card-excerpt")
            texto = excerpt_tag.get_text(strip=True) if excerpt_tag else ""

            # 4. Extração da localização
            localizacao = self.location_extractor.extract(title, texto)

            return ArticleData(
                data=date_str,
                localizacao=localizacao,
                texto=texto,
                titulo=title,
                link=link,
            )
        except Exception as err:
            logging.error(f"Erro ao parsear artigo: {err}")
            return None

    def get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Verifica no elemento de paginação se existe um link para a próxima página.

        Args:
            soup (BeautifulSoup): Objeto BeautifulSoup da página atual.

        Returns:
            Optional[str]: URL da próxima página ou None se for a última página.
        """
        next_button = soup.select_one(".pagination ul.page-numbers li a.next")
        if next_button and next_button.get("href"):
            return next_button["href"]
        return None

    def scrape_search_results(self, start_url: str) -> List[ArticleData]:
        """
        Percorre todas as páginas de resultados a partir de uma URL inicial.

        Args:
            start_url (str): URL inicial de busca.

        Returns:
            List[ArticleData]: Lista contendo todos os artigos raspados.
        """
        all_articles: List[ArticleData] = []
        current_url: Optional[str] = start_url
        page_count = 1

        try:
            while current_url:
                logging.info(f"--- Processando Página {page_count} ---")
                soup = self.get_page_soup(current_url)

                # Busca todos os artigos na div.archive-list ou soltos na página
                articles_tags = soup.select("article.archive-card")
                logging.info(
                    f"Encontrados {len(articles_tags)} artigos na página {page_count}."
                )

                if not articles_tags:
                    logging.info("Nenhum artigo encontrado. Encerrando raspagem.")
                    break

                for tag in articles_tags:
                    article_data = self.parse_article(tag)
                    if article_data:
                        all_articles.append(article_data)

                # Busca o link da próxima página
                current_url = self.get_next_page_url(soup)
                if current_url:
                    page_count += 1
                    time.sleep(1.5)  # Intervalo para conduta ética de scraping
                else:
                    logging.info("Fim da paginação atingido.")

        finally:
            self.close()

        logging.info(
            f"Total de {len(all_articles)} artigos raspados em {page_count} página(s)."
        )
        return all_articles

    def close(self) -> None:
        """Encerra com segurança a sessão do WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logging.info("Sessão do Selenium encerrada.")


class CSVExporter:
    """Classe responsável por exportar os dados raspados para arquivos CSV."""

    @staticmethod
    def export(
        articles: List[ArticleData],
        required_filename: str = "requirde_ajn1_data.csv",
        expanded_filename: str = "explanded__ajn1_data.csv",
    ) -> None:
        """
        Gera os dois arquivos CSV exigidos:
        1. 'requirde_ajn1_data.csv': com (data, localizacao, texto)
        2. 'explanded__ajn1_data.csv': com (data, localizacao, texto, titulo, link)

        Args:
            articles (List[ArticleData]): Lista de artigos extraídos.
            required_filename (str): Nome do arquivo CSV reduzido.
            expanded_filename (str): Nome do arquivo CSV expandido.
        """
        if not articles:
            logging.warning("Nenhum artigo fornecido para exportação.")
            return

        # Prepara DataFrames do pandas
        required_list = [a.to_required_dict() for a in articles]
        expanded_list = [a.to_expanded_dict() for a in articles]

        df_required = pd.DataFrame(required_list)
        df_expanded = pd.DataFrame(expanded_list)

        # Salva em UTF-8 com BOM (utf-8-sig) para compatibilidade perfeita com Excel
        df_required.to_csv(required_filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"Arquivo '{required_filename}' gerado com sucesso ({len(df_required)} linhas)."
        )

        df_expanded.to_csv(expanded_filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"Arquivo '{expanded_filename}' gerado com sucesso ({len(df_expanded)} linhas)."
        )


# ==========================================
# PONTO DE ENTRADA PRINCIPAL (MAIN)
# ==========================================
if __name__ == "__main__":
    START_URL = "https://ajn1.com.br/page/1/?s=ALAGAMENTO"

    logging.info("Iniciando processo de Web Scraping...")
    scraper = AJN1Scraper(headless=True)

    # 1. Executa a raspagem de todas as páginas
    articles = scraper.scrape_search_results(START_URL)

    # 2. Exporta os resultados para os CSVs solicitados
    CSVExporter.export(
        articles,
        required_filename="requirde_ajn1_data.csv",
        expanded_filename="explanded__ajn1_data.csv",
    )

    logging.info("Processo concluído!")
