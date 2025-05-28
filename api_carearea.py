from typing import Dict, Any
import requests
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APICareArea:
    def __init__(self, site: str):
        from config import SITE_SERVERS, API_HEADERS
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APICareArea initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(API_HEADERS)

    def get_care_area_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/referencetable/carearea"
            logger.info(f"Requesting care area information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            care_area_data = response.json()
            
            # 데이터를 파일로 저장
            self._save_care_area_data(care_area_data)
            
            return care_area_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e

    def _save_care_area_data(self, care_area_data: Dict[str, Any]):
        """Care Area 데이터를 JSON 파일로 저장"""
        import json
        import os
        
        try:
            # data 디렉토리가 없으면 생성
            if not os.path.exists('data'):
                os.makedirs('data')
                logger.info("data 디렉토리 생성됨")

            # JSON 파일로 저장
            with open('data/carearea.json', 'w', encoding='utf-8') as f:
                json.dump(care_area_data, f, ensure_ascii=False, indent=4)
            
            logger.info("Care Area 데이터가 성공적으로 저장됨: data/carearea.json")
            
        except Exception as e:
            logger.error(f"Care Area 데이터 저장 중 오류 발생: {str(e)}")
            raise