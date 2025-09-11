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
        
        # JSON 파일로 저장
        if client_info:
            save_client_data_to_json(site, client_info)
            logger.info(f"클라이언트 정보 가져오기 및 저장 성공 - 사이트: {site}")
        else:
            logger.warning(f"클라이언트 정보가 비어있음 - 사이트: {site}")
        
        return True, client_info
    except requests.RequestException as e:
        logger.error(f"클라이언트 정보 가져오기 실패 - 사이트: {site}, 에러: {str(e)}")
        return False, None

def save_client_data_to_json(site, client_data):
    """클라이언트 데이터를 JSON 파일로 저장"""
    try:
        # data 디렉토리 생성
        os.makedirs('data', exist_ok=True)
        
        # 파일명 생성 (사이트명을 소문자로 변환하고 공백을 언더스코어로 변경)
        filename = f"data/{site.replace(' ', '_').lower()}_client.json"
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(client_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"클라이언트 데이터 JSON 저장 완료 - {filename}")
        
    except Exception as e:
        logger.error(f"클라이언트 데이터 JSON 저장 실패 - 사이트: {site}, 에러: {str(e)}")

