import re
import time
import logging
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import pandas as pd

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de Logging para acompanhamento no console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


@dataclass
class ArticleData:
    """
    Estrutura de dados que representa as informações coletadas de um artigo.

    Attributes:
        data (str): Data da publicação extraída da tag .tie-date.
        localizacao (str): Localização extraída do texto/título.
        texto (str): Conteúdo resumido/texto extraído do artigo.
        titulo (str): Título da matéria.
        link (str): URL direta para a matéria original.
    """

    data: str
    localizacao: str
    texto: str
    titulo: str
    link: str

    def to_required_dict(self) -> Dict[str, str]:
        """Retorna o dicionário no formato simplificado (requirde_ajn1_data)."""
        return {"data": self.data, "localizacao": self.localizacao, "texto": self.texto}

    def to_expanded_dict(self) -> Dict[str, str]:
        """Retorna o dicionário no formato expandido (explanded__ajn1_data)."""
        return {
            "data": self.data,
            "localizacao": self.localizacao,
            "texto": self.texto,
            "titulo": self.titulo,
            "link": self.link,
        }


class LocationExtractor:
    """
    Classe responsável por identificar e extrair nomes de municípios de Sergipe
    ou bairros citados no texto ou título da notícia.
    """

    # Lista abrangente de municípios de Sergipe e bairros comuns de Aracaju
    LOCATIONS_SERGIPE = [
        "Aracaju",
        "Nossa Senhora do Socorro",
        "Lagarto",
        "Itabaiana",
        "Estância",
        "São Cristóvão",
        "Tobias Barreto",
        "Simão Dias",
        "Itabaianinha",
        "Poço Redondo",
        "Nossa Senhora da Glória",
        "Propriá",
        "Capela",
        "Laranjeiras",
        "Boquim",
        "Barra dos Coqueiros",
        "Maruim",
        "Japaratuba",
        "Carmópolis",
        "Neópolis",
        "Pirambu",
        "Canindé de São Francisco",
        "Umbaúba",
        "Cedro de São João",
        # Bairros conhecidos de Aracaju
        "Lamarão",
        "Jabotiana",
        "Jardins",
        "Bugio",
        "Santo Antônio",
        "Centro",
        "13 de Julho",
        "Atalaia",
        "Coroa do Meio",
        "Farolândia",
        "Santa Maria",
        "Santos Dumont",
        "Industrial",
        "Siqueira Campos",
        "Suíssa",
        "Salgado Filho",
        "Soledade",
        "Aeroporto",
        "Ponto Novo",
        "Luzia",
        "Grageru",
        "Inácio Barbosa",
    ]

    @classmethod
    def extract_location(cls, title: str, text: str) -> str:
        """
        Extrai localizações com base em regex de padrões comuns (ex: 'bairro X', 'em Y')
        ou por correspondência com lista de municípios/bairros de Sergipe.

        Args:
            title (str): Título da matéria.
            text (str): Texto/resumo da matéria.

        Returns:
            str: Localização(ões) encontrada(s) separadas por vírgula ou 'Sergipe (Não especificado)'.
        """
        combined_content = f"{title} {text}"
        found_locations = set()

        # 1. Procura por menções a "bairro [Nome]"
        bairro_match = re.findall(
            r"\bbairro\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            combined_content,
            flags=re.IGNORECASE,
        )
        for b in bairro_match:
            found_locations.add(f"Bairro {b.strip().title()}")

        # 2. Procura por correspondência direta com lista conhecida
        for loc in cls.LOCATIONS_SERGIPE:
            pattern = r"\b" + re.escape(loc) + r"\b"
            if re.search(pattern, combined_content, re.IGNORECASE):
                found_locations.add(loc)

        if found_locations:
            return ", ".join(sorted(found_locations))

        return "Sergipe (Não especificado)"


class SoSergipeScraper:
    """
    Classe principal responsável pelo Web Scraping do site Só Sergipe utilizando
    Selenium para navegação e BeautifulSoup para parse das páginas.
    """

    def __init__(self, search_term: str = "ALAGAMENTO", headless: bool = True):
        """
        Inicializa o Scraper.

        Args:
            search_term (str): Termo de busca no site.
            headless (bool): Se True, executa o navegador Chrome em segundo plano.
        """
        self.search_term = search_term
        self.base_url = f"https://www.sosergipe.com.br/?s={search_term}"
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.articles_data: List[ArticleData] = []

    def _init_driver(self) -> None:
        """Inicializa o WebDriver do Chrome com opções configuradas."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info("WebDriver do Chrome inicializado com sucesso.")

    def _close_driver(self) -> None:
        """Encerra com segurança o WebDriver."""
        if self.driver:
            self.driver.quit()
            logging.info("WebDriver encerrado.")

    def _extract_articles_from_soup(self, soup: BeautifulSoup) -> List[ArticleData]:
        """
        Extrai os dados das tags <article class="item-list"> dentro do container
        div.post-listing.archive-box.

        Args:
            soup (BeautifulSoup): Objeto BeautifulSoup com o HTML da página.

        Returns:
            List[ArticleData]: Lista de objetos ArticleData da página atual.
        """
        page_articles: List[ArticleData] = []
        archive_box = soup.find("div", class_=re.compile(r"post-listing.*archive-box"))

        if not archive_box:
            logging.warning(
                "Container 'post-listing archive-box' não encontrado na página."
            )
            return page_articles

        articles = archive_box.find_all("article", class_="item-list")
        logging.info(f"Encontrados {len(articles)} artigos nesta página.")

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

                # 4. Localização
                location = LocationExtractor.extract_location(title, text)

                article_item = ArticleData(
                    data=date, localizacao=location, texto=text, titulo=title, link=link
                )
                page_articles.append(article_item)

            except Exception as e:
                logging.error(f"Erro ao processar elemento article: {e}")

        return page_articles

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """
        Identifica o número total de páginas através do container div.pagination.

        Args:
            soup (BeautifulSoup): HTML da primeira página parsed.

        Returns:
            int: Número total de páginas encontradas (padrão: 1).
        """
        pagination = soup.find("div", class_="pagination")
        if not pagination:
            return 1

        pages_span = pagination.find("span", class_="pages")
        if pages_span:
            # Exemplo de texto: "Page 1 of 6"
            match = re.search(r"Page\s+\d+\s+of\s+(\d+)", pages_span.get_text())
            if match:
                return int(match.group(1))

        # Fallback: procura o maior número nos links de página ou na tag last
        last_link = pagination.find("a", class_="last")
        if last_link and "title" in last_link.attrs:
            # Tenta pegar da URL ou title
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

    def run(self) -> None:
        """Executa todo o fluxo de raspagem através da paginação."""
        self._init_driver()
        try:
            logging.info(f"Acessando a página inicial: {self.base_url}")
            self.driver.get(self.base_url)

            # Aguarda carregamento do container principal
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "post-listing"))
            )

            first_page_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            total_pages = self._get_total_pages(first_page_soup)
            logging.info(f"Total de páginas identificadas: {total_pages}")

            # Processa a primeira página
            logging.info("--- Processando Página 1 ---")
            first_page_articles = self._extract_articles_from_soup(first_page_soup)
            self.articles_data.extend(first_page_articles)

            # Processa as páginas subsequentes (2 até N)
            for page in range(2, total_pages + 1):
                page_url = (
                    f"https://www.sosergipe.com.br/page/{page}/?s={self.search_term}"
                )
                logging.info(
                    f"--- Processando Página {page}/{total_pages}: {page_url} ---"
                )

                self.driver.get(page_url)
                time.sleep(2)  # Pausa respeitosa entre requisições

                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "post-listing"))
                    )
                except Exception:
                    logging.warning(f"Timeout ao aguardar container na página {page}.")

                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                articles = self._extract_articles_from_soup(soup)
                self.articles_data.extend(articles)

        finally:
            self._close_driver()

    def export_csvs(
        self,
        required_filename: str = "requirde_sosergipe_data.csv",
        expanded_filename: str = "explanded__sosergipe_data.csv",
    ) -> None:
        """
        Gera os dois arquivos CSV exigidos a partir dos dados coletados.

        Args:
            required_filename (str): Nome do arquivo CSV resumido.
            expanded_filename (str): Nome do arquivo CSV completo.
        """
        if not self.articles_data:
            logging.warning("Nenhum dado coletado para exportar.")
            return

        # 1. Primeiro CSV (data, localizacao, texto)
        required_list = [art.to_required_dict() for art in self.articles_data]
        df_required = pd.DataFrame(required_list)
        df_required.to_csv(required_filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"Arquivo CSV gerado com sucesso: '{required_filename}' ({len(df_required)} registros)."
        )

        # 2. Segundo CSV (data, localizacao, texto, titulo, link)
        expanded_list = [art.to_expanded_dict() for art in self.articles_data]
        df_expanded = pd.DataFrame(expanded_list)
        df_expanded.to_csv(expanded_filename, index=False, encoding="utf-8-sig")
        logging.info(
            f"Arquivo CSV gerado com sucesso: '{expanded_filename}' ({len(df_expanded)} registros)."
        )


if __name__ == "__main__":
    # Instancia e executa o Scraper
    scraper = SoSergipeScraper(search_term="ALAGAMENTO", headless=True)
    scraper.run()

    # Exporta para os CSVs especificados
    scraper.export_csvs(
        required_filename="requirde_sosergipe_data.csv",
        expanded_filename="explanded__sosergipe_data.csv",
    )
