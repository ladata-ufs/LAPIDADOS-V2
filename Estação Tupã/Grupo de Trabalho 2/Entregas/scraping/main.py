import logging

from ajn1_scraper import AJN1Scraper
from scraper_a8se import A8SEScraper
from scraper_sosergipe import SoSergipeScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_all_scrapers(search_term: str = "ALAGAMENTO", headless: bool = True) -> None:
    """
    Executa sequencialmente todos os scrapers configurados (AJN1, Só Sergipe e A8SE)
    e exporta os arquivos CSV resultantes diretamente para a pasta 'dados_brutos'.
    """
    logger.info("==========================================")
    logger.info("INICIANDO EXECUÇÃO GERAL DOS SCRAPERS")
    logger.info("==========================================")

    # 1. Scraper AJN1
    logger.info("\n>>> Executando Raspador AJN1...")
    ajn1_start_url = f"https://ajn1.com.br/page/1/?s={search_term}"
    ajn1 = AJN1Scraper(headless=headless)
    ajn1_articles = ajn1.scrape_search_results(ajn1_start_url)
    ajn1.export_csvs(
        ajn1_articles,
        required_filename="requirde_ajn1_data.csv",
        expanded_filename="explanded__ajn1_data.csv",
    )

    # 2. Scraper Só Sergipe
    logger.info("\n>>> Executando Raspador Só Sergipe...")
    sosergipe = SoSergipeScraper(search_term=search_term, headless=headless)
    sosergipe_articles = sosergipe.run()
    sosergipe.export_csvs(
        sosergipe_articles,
        required_filename="requirde_sosergipe_data.csv",
        expanded_filename="explanded__sosergipe_data.csv",
    )

    # 3. Scraper A8SE
    logger.info("\n>>> Executando Raspador A8SE...")
    a8se_search_url = f"https://a8se.com/pesquisa/1788530302/{search_term.lower()}"
    a8se = A8SEScraper(search_url=a8se_search_url, headless=headless)
    a8se_articles = a8se.run()
    a8se.export_csvs(
        a8se_articles,
        required_filename="requirde_a8se_data.csv",
        expanded_filename="explanded__a8se_data.csv",
    )

    logger.info("\n==========================================")
    logger.info("TODOS OS SCRAPERS FORAM EXECUTADOS COM SUCESSO!")
    logger.info("Os arquivos foram gerados na pasta 'dados_brutos'.")
    logger.info("==========================================")


if __name__ == "__main__":
    run_all_scrapers(search_term="ALAGAMENTO", headless=True)
