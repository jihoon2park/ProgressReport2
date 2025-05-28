from typing import Dict, Any
import requests
import logging

from flask import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIEventType:
    def __init__(self, site: str):
        from config import SITE_SERVERS, API_HEADERS
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APIEventType initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(API_HEADERS)

    def get_event_type_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/referencetable/progressnoteeventtype"
            logger.info(f"Requesting event type information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            event_type_data = response.json()
            
            # 상세 데이터 로깅
            logger.info("Event Type Data received:")
            logger.info(json.dumps(event_type_data, indent=2, ensure_ascii=False))
            
            # 데이터를 파일로 저장
            self._save_event_type_data(event_type_data)
            
            return event_type_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e

    def _save_event_type_data(self, event_type_data: Dict[str, Any]):
        """Event Type 데이터를 JSON 파일로 저장"""
        import json
        import os
        
        try:
            # data 디렉토리가 없으면 생성
            if not os.path.exists('data'):
                os.makedirs('data')
                logger.info("data 디렉토리 생성됨")

            # JSON 파일로 저장
            with open('data/eventtype.json', 'w', encoding='utf-8') as f:
                json.dump(event_type_data, f, ensure_ascii=False, indent=4)
            
            logger.info("Event Type 데이터가 성공적으로 저장됨: data/eventtype.json")
            
        except Exception as e:
            logger.error(f"Event Type 데이터 저장 중 오류 발생: {str(e)}")
            raise 