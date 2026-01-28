from typing import Dict, Any
import requests
import logging
import json
import os

from flask import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APICareArea:
    def __init__(self, site: str):
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APICareArea initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(site))

    def get_care_area_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/referencetable/carearea"
            logger.info(f"Requesting care area information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            care_area_data = response.json()
            
            # Save data to file
            self._save_care_area_data(care_area_data)
            
            return care_area_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e

    def _save_care_area_data(self, care_area_data: Dict[str, Any]):
        """Save Care Area data to JSON file"""
        try:
            # Create data directory if it doesn't exist
            if not os.path.exists('data'):
                os.makedirs('data')
                logger.info("data directory created")

            # Save as JSON file
            with open('data/carearea.json', 'w', encoding='utf-8') as f:
                json.dump(care_area_data, f, ensure_ascii=False, indent=4)
            
            logger.info("Care Area data saved successfully: data/carearea.json")
            
        except Exception as e:
            logger.error(f"Error saving Care Area data: {str(e)}")
            raise