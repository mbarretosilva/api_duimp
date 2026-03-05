"""
Main module for the Siscomex DUIMP Tax Extractor.

This script handles the authentication with the Siscomex API using mTLS and JWT,
performs the extraction of DUIMP data, items, and their respective taxes,
and exports the consolidated data to an Excel file.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any, Optional, Dict, List

import pandas as pd
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SiscomexAuth:
    """
    Handles authentication and session management for the Siscomex API.

    This class configures a requests.Session with mTLS certificates and
    performs the JWT authentication required for subsequent API calls.
    """

    def __init__(self, base_url: str, cert_path: str, key_path: str) -> None:
        """
        Initializes the SiscomexAuth with connection details.

        Args:
            base_url: The base URL for the API Gateway (e.g., https://api.siscomex.gov.br).
            cert_path: Full path to the public certificate file (.pem).
            key_path: Full path to the private key file (.pem).
        """
        self.base_url = base_url.rstrip("/")
        self.cert_path = cert_path
        self.key_path = key_path
        self.session = requests.Session()
        
        # Configure mTLS for all requests in this session
        if os.path.exists(cert_path) and os.path.exists(key_path):
            self.session.cert = (cert_path, key_path)
            logger.info("mTLS certificates configured successfully.")
        else:
            logger.warning(
                "Certificate files not found at %s or %s. mTLS may fail.",
                cert_path, key_path
            )

    def authenticate(self) -> bool:
        """
        Authenticates with the Siscomex Portal to obtain a JWT token.

        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        auth_url = f"{self.base_url}/portal/api/autenticar"
        headers = {"Role-Type": "IMPEXP"}

        try:
            logger.info("Attempting authentication with Siscomex...")
            response = self.session.post(auth_url, headers=headers, timeout=30)
            response.raise_for_status()

            token = response.headers.get("Set-Token")
            if not token and "application/json" in response.headers.get("Content-Type", ""):
                token = response.json().get("token")

            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                logger.info("Authentication successful. JWT token acquired.")
                return True
            
            logger.error("Authentication successful but no token was found in the response.")
            return False

        except requests.RequestException as e:
            logger.error("Failed to authenticate with Siscomex: %s", e)
            return False

class DuimpExtractor:
    """
    Extracts data from the DUIMP API.

    Handles version discovery, item extraction with pagination, tax retrieval,
    and implements a retry mechanism for API resilience.
    """

    def __init__(self, session: requests.Session, base_url: str) -> None:
        """
        Initializes the extractor.

        Args:
            session: An authenticated requests.Session.
            base_url: The base URL for the Siscomex API.
        """
        self.session = session
        self.base_url = base_url.rstrip("/")

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Helper to make HTTP requests with simple retries for 429 and 503.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL for the request.
            **kwargs: Additional arguments for requests.request.

        Returns:
            requests.Response: The HTTP response.

        Raises:
            requests.RequestException: If the call fails after retries.
        """
        max_retries = 3
        backoff_factor = 2

        for i in range(max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                if response.status_code in [429, 503]:
                    wait_time = backoff_factor ** (i + 1)
                    logger.warning("Received %d. Retrying in %d seconds...", response.status_code, wait_time)
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code in [429, 503]:
                         wait_time = backoff_factor ** (i + 1)
                         logger.warning("Received %d. Retrying in %d seconds...", e.response.status_code, wait_time)
                         time.sleep(wait_time)
                         continue

                if i == max_retries - 1:
                    raise e
                logger.warning("Request failed (%s). Retrying...", e)
                time.sleep(backoff_factor ** i)

        raise requests.RequestException("Max retries exceeded")

    def get_current_version(self, duimp_number: str) -> int:
        """
        Retrieves the current version of a DUIMP.

        Args:
            duimp_number: The DUIMP identification number.

        Returns:
            int: The current version number.

        Raises:
            ValueError: If the version cannot be found in the response.
        """
        url = f"{self.base_url}/duimp-api/api/ext/duimp/{duimp_number}"
        logger.info("Fetching current version for DUIMP %s...", duimp_number)
        
        try:
            response = self._make_request("GET", url)
            data = response.json()
            version = data.get("versao")
            
            if version is None:
                raise ValueError(f"Could not find version in API response for DUIMP {duimp_number}")
            
            logger.info("Current version for DUIMP %s is %d.", duimp_number, version)
            return int(version)

        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error("Error retrieving DUIMP version: %s", e)
            raise

    def get_all_items(self, duimp_number: str, version: int) -> List[Dict[str, Any]]:
        """
        Retrieves all items for a specific DUIMP version using pagination.

        Args:
            duimp_number: The DUIMP identification number.
            version: The version of the DUIMP to query.

        Returns:
            List[Dict[str, Any]]: A list of all item objects.
        """
        url = f"{self.base_url}/duimp-api/api/ext/duimp/{duimp_number}/{version}/itens"
        all_items = []
        page = 1
        limit = 50

        logger.info("Starting item extraction for DUIMP %s (Version %d)...", duimp_number, version)

        while True:
            params = {"page": page, "limit": limit}
            try:
                response = self._make_request("GET", url, params=params)
                data = response.json()
                
                items_in_page = data.get("list") or data.get("itens") or []
                
                if not items_in_page:
                    break
                
                all_items.extend(items_in_page)
                logger.info("Collected %d items (Total so far: %d).", len(items_in_page), len(all_items))

                total_pages = data.get("totalPages", 1)
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(0.5)

            except requests.RequestException as e:
                logger.error("Error during item pagination at page %d: %s", page, e)
                break

        return all_items

    def get_item_taxes(self, duimp_number: str, version: int, item_number: int) -> Dict[str, Any]:
        """
        Retrieves tax calculations for a specific item in a DUIMP.

        Args:
            duimp_number: The DUIMP identification number.
            version: The version of the DUIMP.
            item_number: The specific item number within the DUIMP.

        Returns:
            Dict[str, Any]: The JSON response containing calculated values.
        """
        url = f"{self.base_url}/duimp-api/api/ext/duimp/{duimp_number}/{version}/itens/{item_number}/valores-calculados"
        try:
            response = self._make_request("GET", url)
            return response.json()
        except requests.RequestException as e:
            logger.error("Failed to retrieve taxes for item %d: %s", item_number, e)
            return {}

    def flatten_taxes(self, duimp_number: str, version: int, item_number: int, tax_json: dict) -> List[Dict[str, Any]]:
        """
        Transforms the nested tax JSON into a flattened list of dictionaries.

        Args:
            duimp_number: The DUIMP identification number.
            version: The DUIMP version.
            item_number: The item number.
            tax_json: The nested JSON data from the API.

        Returns:
            List[Dict[str, Any]]: A list of flattened tax records.
        """
        # Attempt to find NCM from the JSON (usually present in the response if available)
        ncm = tax_json.get("ncm", "")
        flattened_records = []
        
        # Access the list of taxes (key depends on API version, often 'tributos' or 'listaTributos')
        tributos = tax_json.get("tributos") or tax_json.get("listaTributos") or []
        
        for tributo in tributos:
            tipo = tributo.get("tipo") or tributo.get("descricao")
            
            # Common fields from Siscomex API
            record = {
                "numero_duimp": duimp_number,
                "versao_duimp": version,
                "numero_item": item_number,
                "ncm_item": ncm,
                "tipo_tributo": tipo,
                "base_calculo": float(tributo.get("baseCalculo", 0.0)),
                "aliquota": float(tributo.get("aliquota", 0.0)),
                "valor_calculado": float(tributo.get("valorCalculado", 0.0)),
                "valor_a_recolher": float(tributo.get("valorARecolher", 0.0))
            }
            flattened_records.append(record)
            
        return flattened_records

def export_to_excel(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Exports the provided data to an Excel file using pandas.

    Args:
        data: List of flattened tax dictionaries.
        filename: The output filename (e.g., summary.xlsx).
    """
    if not data:
        logger.warning("No data provided for export.")
        return

    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False, engine='openpyxl')
        logger.info("Successfully exported data to %s.", filename)
    except Exception as e:
        logger.error("Failed to export Excel file: %s", e)

def main() -> None:
    """
    Orchestrates the DUIMP extraction and tax consolidation process.
    """
    load_dotenv()

    # Configuration from .env
    base_url = os.getenv("SISCOMEX_BASE_URL", "https://api.siscomex.gov.br")
    cert_pub = os.getenv("CERT_PUB_PATH", "certs/cert.pem")
    cert_key = os.getenv("CERT_KEY_PATH", "certs/key.pem")
    duimp_numero = os.getenv("DUIMP_NUMERO")

    if not duimp_numero:
        logger.error("DUIMP_NUMERO not found in environment variables.")
        return

    # Phase 1: Authentication
    auth_manager = SiscomexAuth(base_url, cert_pub, cert_key)
    if not auth_manager.authenticate():
        logger.error("Authentication failed. Aborting.")
        return

    # Phase 2 & 3: Extraction and Tax Consolidation
    try:
        extractor = DuimpExtractor(auth_manager.session, base_url)
        
        # 1. Get current DUIMP version
        version = extractor.get_current_version(duimp_numero)
        
        # 2. Extract all items
        items = extractor.get_all_items(duimp_numero, version)
        
        consolidated_data = []
        logger.info("Processing taxes for %d items...", len(items))

        # 3. Loop through items to get tax details
        for item in items:
            item_number = item.get("numero")
            if item_number is None:
                continue

            logger.info("Fetching taxes for item %d...", item_number)
            tax_data = extractor.get_item_taxes(duimp_numero, version, item_number)
            
            # 4. Flatten and store
            item_records = extractor.flatten_taxes(duimp_numero, version, item_number, tax_data)
            consolidated_data.extend(item_records)

            # Respect rate limits
            time.sleep(0.2)

        # 5. Export to Excel
        output_file = f"duimp_{duimp_numero}_tributos.xlsx"
        export_to_excel(consolidated_data, output_file)
        
        logger.info("Process completed successfully.")

    except Exception as e:
        logger.exception("An error occurred during execution: %s", e)

if __name__ == "__main__":
    main()
