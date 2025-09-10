import json
import os
import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, site: str):
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APIClient initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(site))

    def get_client_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/client"
            logger.info(f"Requesting client information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            client_data = response.json()
            
            return client_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e



def get_api_client(site):
    """API 클라이언트 인스턴스를 반환하는 함수"""
    return APIClient(site)

def fetch_client_information(site):
    """클라이언트 정보를 가져오고 처리하는 함수"""
    logger.info(f"클라이언트 정보 요청 시작 - 사이트: {site}")
    try:
        api_client = APIClient(site)
        client_info = api_client.get_client_information()
        logger.info(f"클라이언트 정보 가져오기 성공 - 사이트: {site}")
        return True, client_info
    except requests.RequestException as e:
        logger.error(f"클라이언트 정보 가져오기 실패 - 사이트: {site}, 에러: {str(e)}")
        return False, None

