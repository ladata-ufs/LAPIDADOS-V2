import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pandas as pd
from selenium import webdriver
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
    Classe responsável por identificar e extrair nomes de municípios de Sergipe
    ou bairros citados no texto ou título da notícia.
    """

    LOCATIONS_SERGIPE: ClassVar[tuple[str, ...]] = (
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
        "Itabaianinha",
        "Nossa Senhora da Glória",
        "Cedro de São João",
        "Sergipe",
        "Grande Aracaju",
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
        "Zona Sul",
        "Zona Norte",
    )

    def __init__(self):
        escaped_cities = [re.escape(city) for city in self.LOCATIONS_SERGIPE]
        self.city_pattern = re.compile(
            rf"\b({'|'.join(escaped_cities)})\b", re.IGNORECASE
        )
        self.preposition_pattern = re.compile(
            r"\b(?:em|no|na|nos|nas|para|de)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:de|da|do|dos|das|e)\s+[A-ZÀ-Ú][a-zà-ú]+|\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            re.UNICODE,
        )
        self.bairro_pattern = re.compile(
            r"\bbairro\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)",
            re.IGNORECASE,
        )

    def extract(self, title: str, text: str) -> str:
        """
        Extrai localizações combinando busca por municípios/bairros de Sergipe,
        padrões de bairro e heurísticas gramaticais de preposição.
        """
        combined_content = f"{title}. {text}"
        found_locations = set()

        # 1. Menções diretas a "bairro X"
        bairro_matches = self.bairro_pattern.findall(combined_content)
        for b in bairro_matches:
            found_locations.add(f"Bairro {b.strip().title()}")

        # 2. Busca por municípios e bairros da lista predefinida
        city_matches = self.city_pattern.findall(combined_content)
        for m in city_matches:
            found_locations.add(m.title())

        if found_locations:
            return ", ".join(sorted(found_locations))

        # 3. Heurística baseada em preposição no título
        prep_matches = self.preposition_pattern.findall(title)
        if prep_matches:
            return prep_matches[0].strip()

        return "Não informada"


class BaseScraper:
    """
    Classe base para gerenciamento de Selenium WebDriver, resolução da pasta de dados brutos
    e exportação padronizada de arquivos CSV.
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
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        logger.info(f"[{self.nome_portal}] WebDriver do Chrome inicializado.")

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
        Gera e salva os dois arquivos CSV exigidos na pasta de dados brutos:
        1. Versão reduzida/requirida (data, localizacao, texto)
        2. Versão expandida (data, localizacao, texto, titulo, link)
        """
        if not articles:
            logger.warning(
                f"[{self.nome_portal}] Nenhum dado fornecido para exportação."
            )
            return

        df_required = pd.DataFrame([a.to_required_dict() for a in articles])
        df_expanded = pd.DataFrame([a.to_expanded_dict() for a in articles])

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
