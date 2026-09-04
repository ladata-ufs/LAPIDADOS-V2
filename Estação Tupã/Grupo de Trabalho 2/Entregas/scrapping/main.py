import logging

from ajn1_scraper import AJN1Scraper
from scraper_sosergipe import SoSergipeScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

visual_line = "=========================================="


def run_all_scrapers(search_term: str = "ALAGAMENTO", headless: bool = True) -> None:
    """
    Executa sequencialmente todos os scrapers configurados (AJN1 e Só Sergipe)
    e exporta os arquivos CSV resultantes diretamente para a pasta 'dados_brutos'.
    """
    logger.info(visual_line)
    logger.info("INICIANDO EXECUÇÃO GERAL DOS SCRAPERS")
    logger.info(visual_line)

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

    logger.info(f"\n{visual_line}")
    logger.info("TODOS OS SCRAPERS FORAM EXECUTADOS COM SUCESSO!")
    logger.info("Os arquivos foram gerados na pasta 'dados_brutos'.")
    logger.info(visual_line)


if __name__ == "__main__":
    run_all_scrapers(search_term="ALAGAMENTO", headless=True)
