from typing import Dict, Any
import requests
import logging
import json
import os

from flask import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIEventType:
    def __init__(self, site: str):
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APIEventType initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(site))

    def get_event_type_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/referencetable/progressnoteeventtype"
            logger.info(f"Requesting event type information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            event_type_data = response.json()
            
            # 데이터를 파일로 저장
            self._save_event_type_data(event_type_data)
            
            return event_type_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e

    def _save_event_type_data(self, event_type_data: Dict[str, Any]):
        """Event Type 데이터를 JSON 파일로 저장 (사이트별 + 통합)"""
        try:
            # data 디렉토리가 없으면 생성
            if not os.path.exists('data'):
                os.makedirs('data')
                logger.info("data 디렉토리 생성됨")

            # 1. 사이트별 JSON 파일로 저장
            site_filename = f'data/eventtype_{self.site}.json'
            with open(site_filename, 'w', encoding='utf-8') as f:
                json.dump(event_type_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Event Type 데이터가 사이트별로 저장됨: {site_filename}")
            
            # 2. 통합 JSON 파일로도 저장 (기존 호환성 유지)
            with open('data/eventtype.json', 'w', encoding='utf-8') as f:
                json.dump(event_type_data, f, ensure_ascii=False, indent=4)
            logger.info("Event Type 데이터가 통합 파일로 저장됨: data/eventtype.json")
            
        except Exception as e:
            logger.error(f"Event Type 데이터 저장 중 오류 발생: {str(e)}")
            raise

def fetch_all_sites_event_types():
    """모든 사이트의 Event Type을 가져와서 사이트별로 저장"""
    from config import SITE_SERVERS
    
    results = {}
    for site in SITE_SERVERS.keys():
        try:
            logger.info(f"Fetching event types for site: {site}")
            api_event_type = APIEventType(site)
            event_types = api_event_type.get_event_type_information()
            results[site] = event_types
            logger.info(f"Successfully fetched {len(event_types)} event types for {site}")
        except Exception as e:
            logger.error(f"Failed to fetch event types for {site}: {str(e)}")
            results[site] = []
    
    return results

def get_site_event_types(site: str):
    """특정 사이트의 Event Type을 JSON 파일에서 로드"""
    try:
        site_filename = f'data/eventtype_{site}.json'
        
        # 사이트별 파일이 있으면 로드
        if os.path.exists(site_filename):
            with open(site_filename, 'r', encoding='utf-8') as f:
                event_types = json.load(f)
            logger.info(f"Loaded {len(event_types)} event types for site {site} from {site_filename}")
            return event_types
        
        # 사이트별 파일이 없으면 통합 파일에서 로드
        elif os.path.exists('data/eventtype.json'):
            with open('data/eventtype.json', 'r', encoding='utf-8') as f:
                event_types = json.load(f)
            logger.info(f"Loaded {len(event_types)} event types for site {site} from data/eventtype.json (fallback)")
            return event_types
        
        else:
            logger.warning(f"No event type files found for site {site}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading event types for site {site}: {str(e)}")
        return [] 