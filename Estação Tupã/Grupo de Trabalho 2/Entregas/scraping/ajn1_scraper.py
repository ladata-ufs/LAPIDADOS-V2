import logging
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_scraper import ArticleData, BaseScraper

logger = logging.getLogger(__name__)


class AJN1Scraper(BaseScraper):
    """
    Classe responsável por gerenciar a navegação e raspagem do portal AJN1.
    Herda as rotinas comuns de Selenium, extração de localização e salvamento de CSV de BaseScraper.
    """

    def __init__(self, headless: bool = True, timeout: int = 15):
        super().__init__(nome_portal="AJN1", headless=headless, timeout=timeout)

    def get_page_soup(self, url: str) -> BeautifulSoup:
        """Navega até a URL especificada utilizando Selenium e retorna BeautifulSoup."""
        if not self.driver:
            self._init_driver()

        logger.info(f"[{self.nome_portal}] Acessando URL: {url}")
        self.safe_get(url)

        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "archive-card"))
            )
        except TimeoutException as e:
            logger.warning(
                f"[{self.nome_portal}] Aviso ao aguardar carregamento dos artigos: {e}"
            )

        return BeautifulSoup(self.driver.page_source, "html.parser")

    def parse_article(self, article_tag: BeautifulSoup) -> ArticleData | None:
        """Realiza o parse de uma tag <article class="archive-card"> individual."""
        try:
            title_tag = article_tag.select_one(".archive-card-title a")
            title = title_tag.get_text(strip=True) if title_tag else ""
            link = title_tag.get("href", "") if title_tag else ""

            date_tag = article_tag.select_one(".meta-date")
            date_str = date_tag.get_text(strip=True) if date_tag else ""

            excerpt_tag = article_tag.select_one(".archive-card-excerpt")
            texto = excerpt_tag.get_text(strip=True) if excerpt_tag else ""

            localizacao = (
                self.location_extractor.extract_aracaju_location(title, texto) or ""
            )

            return ArticleData(
                data=date_str,
                localizacao=localizacao,
                texto=texto,
                titulo=title,
                link=link,
            )
        except (AttributeError, KeyError, ValueError) as err:
            logger.error(f"[{self.nome_portal}] Erro ao parsear artigo: {err}")
            return None

    def get_next_page_url(self, soup: BeautifulSoup) -> str | None:
        """Retorna a URL da próxima página na paginação ou None."""
        next_button = soup.select_one(".pagination ul.page-numbers li a.next")
        if next_button and next_button.get("href"):
            return next_button["href"]
        return None

    def scrape_search_results(self, start_url: str) -> list[ArticleData]:
        """Percorre todas as páginas de resultados a partir de uma URL inicial."""
        all_articles: list[ArticleData] = []
        current_url: str | None = start_url
        page_count = 1

        try:
            while current_url:
                logger.info(f"[{self.nome_portal}] Processando Página {page_count}...")
                soup = self.get_page_soup(current_url)

                articles_tags = soup.select("article.archive-card")
                logger.info(
                    f"[{self.nome_portal}] Encontrados {len(articles_tags)} artigos na página {page_count}."
                )

                if not articles_tags:
                    logger.info(
                        f"[{self.nome_portal}] Nenhum artigo encontrado. Encerrando raspagem."
                    )
                    break

                for tag in articles_tags:
                    article_data = self.parse_article(tag)
                    if article_data:
                        all_articles.append(article_data)

                current_url = self.get_next_page_url(soup)
                if current_url:
                    page_count += 1
                    time.sleep(1.5)
                else:
                    logger.info(f"[{self.nome_portal}] Fim da paginação atingido.")

        finally:
            self.close()

        logger.info(
            f"[{self.nome_portal}] Total de {len(all_articles)} artigos raspados em {page_count} página(s)."
        )
        return all_articles


if __name__ == "__main__":
    START_URL = "https://ajn1.com.br/page/1/?s=ALAGAMENTO"

    logger.info("Iniciando raspagem do AJN1...")
    scraper = AJN1Scraper(headless=True)

    articles = scraper.scrape_search_results(START_URL)

    scraper.export_csvs(
        articles,
        required_filename="requirde_ajn1_data.csv",
        expanded_filename="explanded__ajn1_data.csv",
    )

    logger.info("Processo AJN1 concluído!")
