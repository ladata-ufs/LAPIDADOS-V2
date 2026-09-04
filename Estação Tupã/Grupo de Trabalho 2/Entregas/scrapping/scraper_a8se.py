import logging
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from base_scraper import ArticleData, BaseScraper

logger = logging.getLogger(__name__)


class A8SEScraper(BaseScraper):
    """
    Classe responsável pelo Web Scraping do portal A8SE.
    Herda da classe BaseScraper a gestão do Selenium WebDriver, extração de localização e salvamento de CSVs.
    """

    BASE_SITE_URL = "https://a8se.com"

    def __init__(
        self,
        search_url: str = "https://a8se.com/pesquisa/1788530302/alagamento",
        headless: bool = True,
    ):
        super().__init__(nome_portal="A8SE", headless=headless)
        self.start_url = search_url

    def get_page_soup(self, url: str) -> BeautifulSoup | None:
        """Navega até a URL especificada utilizando Selenium e retorna o objeto BeautifulSoup."""
        if not self.driver:
            self._init_driver()

        logger.info(f"[{self.nome_portal}] Acessando URL: {url}")
        self.driver.get(url)

        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "main-list"))
            )
        except TimeoutException as e:
            logger.warning(
                f"[{self.nome_portal}] Aviso ao aguardar carregamento dos artigos: {e}"
            )

        return BeautifulSoup(self.driver.page_source, "html.parser")

    def parse_article(self, article_tag: BeautifulSoup) -> ArticleData | None:
        """Realiza o parse de um container div.box-news individual."""
        try:
            a_tag = article_tag.find("a", class_="img-flex") or article_tag.find("a")

            raw_href = a_tag.get("href", "") if a_tag else ""
            link = urljoin(self.BASE_SITE_URL, raw_href) if raw_href else ""

            details_div = article_tag.find("div", class_="--details")
            if not details_div and a_tag:
                details_div = a_tag.find("div", class_="--details")

            date_str = ""
            title = ""
            texto = ""

            if details_div:
                hat_tag = details_div.find("div", class_=lambda c: c and "--hat" in c)
                if hat_tag:
                    date_str = hat_tag.get_text(strip=True)

                title_tag = details_div.find(
                    "div", class_=lambda c: c and "--title" in c
                )
                if title_tag:
                    title = title_tag.get_text(strip=True)

                excerpt_tag = details_div.find("p")
                texto = excerpt_tag.get_text(strip=True) if excerpt_tag else title

            if not title:
                return None

            localizacao = self.location_extractor.extract(title, texto)

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
        """Verifica a paginação e retorna a URL da próxima página se existir."""
        paginate_div = soup.find("div", class_="list-paginate")
        if not paginate_div:
            return None

        next_button = paginate_div.find("a", class_="next") or paginate_div.find(
            "a", attrs={"aria-label": "Next"}
        )
        if next_button and next_button.get("href") and next_button.get("href") != "#":
            raw_href = next_button["href"]
            return urljoin(self.BASE_SITE_URL, raw_href)

        return None

    def run(self) -> list[ArticleData]:
        """Executa a raspagem percorrendo todas as páginas de resultado."""
        all_articles: list[ArticleData] = []
        current_url: str | None = self.start_url
        page_count = 1

        try:
            while current_url:
                logger.info(f"[{self.nome_portal}] Processando Página {page_count}...")
                soup = self.get_page_soup(current_url)
                if not soup:
                    break

                main_list = soup.find("div", class_="main-list")
                if not main_list:
                    logger.info(
                        f"[{self.nome_portal}] Container 'main-list' não encontrado. Encerrando."
                    )
                    break

                box_news_list = main_list.find_all(
                    "div", class_=lambda c: c and "box-news" in c
                )
                logger.info(
                    f"[{self.nome_portal}] Encontrados {len(box_news_list)} artigos na página {page_count}."
                )

                if not box_news_list:
                    logger.info(
                        f"[{self.nome_portal}] Nenhum artigo encontrado. Encerrando."
                    )
                    break

                for box in box_news_list:
                    article_data = self.parse_article(box)
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
    scraper = A8SEScraper(headless=True)
    articles = scraper.run()

    scraper.export_csvs(
        articles,
        required_filename="requirde_a8se_data.csv",
        expanded_filename="explanded__a8se_data.csv",
    )
