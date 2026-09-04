import logging
import re
import time

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_scraper import ArticleData, BaseScraper

logger = logging.getLogger(__name__)


class SoSergipeScraper(BaseScraper):
    """
    Classe principal responsável pelo Web Scraping do site Só Sergipe.
    Herda da classe BaseScraper a gestão do Selenium WebDriver, extração de localização e salvamento de CSVs.
    """

    def __init__(self, search_term: str = "ALAGAMENTO", headless: bool = True):
        super().__init__(nome_portal="Só Sergipe", headless=headless)
        self.search_term = search_term
        self.base_url = f"https://www.sosergipe.com.br/?s={search_term}"
        self.articles_data: list[ArticleData] = []

    def _extract_articles_from_soup(self, soup: BeautifulSoup) -> list[ArticleData]:
        """
        Extrai os dados das tags <article class="item-list"> dentro do container principal.
        """
        page_articles: list[ArticleData] = []
        archive_box = soup.find("div", class_=re.compile(r"post-listing.*archive-box"))

        if not archive_box:
            logger.warning(
                f"[{self.nome_portal}] Container 'post-listing archive-box' não encontrado na página."
            )
            return page_articles

        articles = archive_box.find_all("article", class_="item-list")
        logger.info(
            f"[{self.nome_portal}] Encontrados {len(articles)} artigos nesta página."
        )

        for article in articles:
            try:
                # 1. Título e Link
                title_tag = article.find("h2", class_="post-box-title")
                a_tag = title_tag.find("a") if title_tag else None
                title = a_tag.get_text(strip=True) if a_tag else "Sem Título"
                link = a_tag["href"] if a_tag and "href" in a_tag.attrs else ""

                # 2. Data
                date_tag = article.find("span", class_="tie-date")
                date = (
                    date_tag.get_text(strip=True) if date_tag else "Data indisponível"
                )

                # 3. Texto / Resumo
                entry_div = article.find("div", class_="entry")
                text = ""
                if entry_div:
                    p_tag = entry_div.find("p")
                    if p_tag:
                        text = p_tag.get_text(strip=True)
                    else:
                        text = entry_div.get_text(strip=True)

                # Limpa sufixos de "Leia Mais »" se existirem
                text = re.sub(r"Leia Mais\s*»", "", text).strip()

                # 4. Localização (reutilizando a classe unificada de localização)
                location = self.location_extractor.extract(title, text)

                article_item = ArticleData(
                    data=date, localizacao=location, texto=text, titulo=title, link=link
                )
                page_articles.append(article_item)

            except (AttributeError, KeyError, ValueError) as e:
                logger.error(
                    f"[{self.nome_portal}] Erro ao processar elemento article: {e}"
                )

        return page_articles

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """Identifica o número total de páginas através do container div.pagination."""
        pagination = soup.find("div", class_="pagination")
        if not pagination:
            return 1

        pages_span = pagination.find("span", class_="pages")
        if pages_span:
            match = re.search(r"Page\s+\d+\s+of\s+(\d+)", pages_span.get_text())
            if match:
                return int(match.group(1))

        last_link = pagination.find("a", class_="last")
        if last_link and "title" in last_link.attrs:
            href = last_link.get("href", "")
            match = re.search(r"/page/(\d+)/", href)
            if match:
                return int(match.group(1))

        page_links = pagination.find_all("a", class_="page")
        page_numbers = [1]
        for a in page_links:
            text = a.get_text(strip=True)
            if text.isdigit():
                page_numbers.append(int(text))

        return max(page_numbers)

    def run(self) -> list[ArticleData]:
        """Executa todo o fluxo de raspagem através da paginação."""
        self._init_driver()
        self.articles_data = []

        try:
            logger.info(
                f"[{self.nome_portal}] Acessando a página inicial: {self.base_url}"
            )
            self.driver.get(self.base_url)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "post-listing"))
            )

            first_page_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            total_pages = self._get_total_pages(first_page_soup)
            logger.info(
                f"[{self.nome_portal}] Total de páginas identificadas: {total_pages}"
            )

            logger.info(f"[{self.nome_portal}] Processando Página 1...")
            first_page_articles = self._extract_articles_from_soup(first_page_soup)
            self.articles_data.extend(first_page_articles)

            for page in range(2, total_pages + 1):
                page_url = (
                    f"https://www.sosergipe.com.br/page/{page}/?s={self.search_term}"
                )
                logger.info(
                    f"[{self.nome_portal}] Processando Página {page}/{total_pages}: {page_url}"
                )

                self.driver.get(page_url)
                time.sleep(2)

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "post-listing"))
                    )
                except TimeoutException:
                    logger.warning(
                        f"[{self.nome_portal}] Timeout ao aguardar container na página {page}."
                    )

                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                articles = self._extract_articles_from_soup(soup)
                self.articles_data.extend(articles)

        finally:
            self.close()

        return self.articles_data


if __name__ == "__main__":
    scraper = SoSergipeScraper(search_term="ALAGAMENTO", headless=True)
    articles = scraper.run()

    scraper.export_csvs(
        articles,
        required_filename="requirde_sosergipe_data.csv",
        expanded_filename="explanded__sosergipe_data.csv",
    )
