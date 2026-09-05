import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class ArticleData:
    """Estrutura de dados unificada para armazenar os campos extraídos de um artigo."""

    data: str
    localizacao: str
    texto: str
    titulo: str
    link: str

    def to_required_dict(self) -> dict[str, str]:
        """Retorna apenas os campos reduzidos/exigidos (data, localizacao, texto)."""
        return {"data": self.data, "localizacao": self.localizacao, "texto": self.texto}

    def to_expanded_dict(self) -> dict[str, str]:
        """Retorna os campos completos (data, localizacao, texto, titulo, link)."""
        return {
            "data": self.data,
            "localizacao": self.localizacao,
            "texto": self.texto,
            "titulo": self.titulo,
            "link": self.link,
        }


class LocationExtractor:
    """
    Classe responsável por identificar localizações referentes a Aracaju e seus bairros.
    Se a notícia não mencionar Aracaju nem nenhum de seus bairros, ela é descartada.
    """

    ARACAJU_LOCATIONS: ClassVar[tuple[str, ...]] = (
        "Aracaju",
        "Grande Aracaju",
        "Zona Sul",
        "Zona Norte",
        # Bairros de Aracaju
        "13 de Julho",
        "Aeroporto",
        "América",
        "Atalaia",
        "Bugio",
        "Capucho",
        "Centro",
        "Cidade Nova",
        "Cirurgia",
        "Coroa do Meio",
        "17 de Março",
        "Dezessete de Março",
        "Dom Luciano",
        "Farolândia",
        "Getúlio Vargas",
        "Grageru",
        "Inácio Barbosa",
        "Industrial",
        "Jabotiana",
        "Japãozinho",
        "Jardins",
        "José Conrado de Araújo",
        "Lamarão",
        "Luzia",
        "Marés",
        "Mosqueiro",
        "Novo Paraíso",
        "Olaria",
        "Osvaldo Aranha",
        "Palmeira",
        "Pereira Lobo",
        "Ponto Novo",
        "Porto D'Danta",
        "Salgado Filho",
        "Santa Maria",
        "Santo Antônio",
        "Santos Dumont",
        "São Conrado",
        "São José",
        "Siqueira Campos",
        "Soledade",
        "Suíssa",
        "Veneza",
    )

    def __init__(self):
        escaped_aracaju = [re.escape(loc) for loc in self.ARACAJU_LOCATIONS]
        self.aracaju_pattern = re.compile(
            rf"\b({'|'.join(escaped_aracaju)})\b", re.IGNORECASE
        )
        self.bairro_pattern = re.compile(
            r"\bbairro\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            re.IGNORECASE,
        )

    def extract_aracaju_location(self, title: str, text: str) -> str | None:
        """
        Extrai as localizações de Aracaju e seus bairros presentes no título ou texto.
        Retorna uma string com os locais de Aracaju encontrados ou None se Aracaju/bairros não forem mencionados.
        """
        combined_content = f"{title}. {text}"
        found_locations = set()

        # 1. Busca menções diretas a "bairro X" se X for um dos bairros de Aracaju conhecidos
        bairro_matches = self.bairro_pattern.findall(combined_content)
        for b in bairro_matches:
            b_name = b.strip().title()
            if any(
                re.search(rf"\b{re.escape(loc)}\b", b_name, re.IGNORECASE)
                for loc in self.ARACAJU_LOCATIONS
                if loc not in ("Aracaju", "Grande Aracaju", "Zona Sul", "Zona Norte")
            ):
                found_locations.add(f"Bairro {b_name}")

        # 2. Busca por Aracaju e seus bairros da lista predefinida
        city_matches = self.aracaju_pattern.findall(combined_content)
        for m in city_matches:
            found_locations.add(m.title())

        if found_locations:
            return ", ".join(sorted(found_locations))

        return None


class BaseScraper:
    """
    Classe base para gerenciamento de Selenium WebDriver, resolução da pasta de dados brutos,
    filtragem direta por Aracaju/bairros e exportação de CSVs.
    """

    def __init__(self, nome_portal: str, headless: bool = True, timeout: int = 15):
        self.nome_portal = nome_portal
        self.headless = headless
        self.timeout = timeout
        self.driver: webdriver.Chrome | None = None
        self.location_extractor = LocationExtractor()

        # Resolução do diretório 'dados_brutos'
        base_dir = Path(__file__).resolve().parent
        if (base_dir.parent / "dados_brutos").exists():
            self.raw_data_dir = base_dir.parent / "dados_brutos"
        else:
            self.raw_data_dir = base_dir / "dados_brutos"

        self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def _init_driver(self) -> None:
        """Inicializa e configura o Chrome WebDriver."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.page_load_strategy = "eager"
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        logger.info(f"[{self.nome_portal}] WebDriver do Chrome inicializado.")

    def safe_get(self, url: str) -> None:
        """
        Navega para a URL tratada contra timeouts de carregamento de scripts externos.
        Paralisa o carregamento de mídia/anúncios caso exceda o tempo e prossegue com o DOM.
        """
        if not self.driver:
            self._init_driver()

        try:
            self.driver.get(url)
        except TimeoutException:
            logger.warning(
                f"[{self.nome_portal}] Timeout no carregamento da página (30s) para {url}. Forçando interrupção do carregamento."
            )
            try:
                self.driver.execute_script("window.stop();")
            except WebDriverException as e:
                logger.debug(f"Aviso ao executar window.stop(): {e}")

    def close(self) -> None:
        """Encerra a sessão do WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info(f"[{self.nome_portal}] Sessão do Selenium encerrada.")

    def export_csvs(
        self,
        articles: list[ArticleData],
        required_filename: str,
        expanded_filename: str,
    ) -> None:
        """
        Gera e salva os dois arquivos CSV exigidos na pasta de dados brutos.
        Exporta APENAS matérias que mencionem explicitamente Aracaju ou algum de seus bairros.
        Descarta totalmente qualquer matéria que não mencione Aracaju ou seus bairros.
        """
        if not articles:
            logger.warning(
                f"[{self.nome_portal}] Nenhum dado fornecido para exportação."
            )
            return

        aracaju_articles: list[ArticleData] = []
        for a in articles:
            loc = self.location_extractor.extract_aracaju_location(a.titulo, a.texto)
            if loc:  # Se houver menção a Aracaju ou a algum de seus bairros
                a.localizacao = loc
                aracaju_articles.append(a)

        descartados_count = len(articles) - len(aracaju_articles)

        if descartados_count > 0:
            logger.info(
                f"[{self.nome_portal}] Filtragem: {len(aracaju_articles)} matérias de Aracaju/bairros mantidas, {descartados_count} sem menção a Aracaju descartadas."
            )

        if not aracaju_articles:
            logger.warning(
                f"[{self.nome_portal}] Nenhuma matéria com menção a Aracaju/bairros para exportar."
            )
            return

        df_required = pd.DataFrame([a.to_required_dict() for a in aracaju_articles])
        df_expanded = pd.DataFrame([a.to_expanded_dict() for a in aracaju_articles])

        req_path = self.raw_data_dir / required_filename
        exp_path = self.raw_data_dir / expanded_filename

        df_required.to_csv(req_path, index=False, encoding="utf-8-sig")
        logger.info(
            f"[{self.nome_portal}] CSV reduzido salvo em: '{req_path}' ({len(df_required)} linhas)."
        )

        df_expanded.to_csv(exp_path, index=False, encoding="utf-8-sig")
        logger.info(
            f"[{self.nome_portal}] CSV expandido salvo em: '{exp_path}' ({len(df_expanded)} linhas)."
        )
