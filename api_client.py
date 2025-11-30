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
    """클라이언트 정보를 가져오고 처리하는 함수 (DB 직접 접속 또는 API)"""
    import os
    import sqlite3
    
    # DB 직접 접속 모드 확인
    use_db_direct = False
    try:
        conn = sqlite3.connect('progress_report.db', timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            use_db_direct = result[0].lower() == 'true'
        else:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
    except:
        use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
    
    # DB 직접 접속 모드 (fallback 비활성화 - 에러 발생)
    if use_db_direct:
        try:
            from manad_db_connector import MANADDBConnector
            logger.info(f"🔌 DB 직접 접속 모드: Client 정보 조회 - {site} (fallback 비활성화)")
            connector = MANADDBConnector(site)
            success, client_info = connector.fetch_clients()
            
            if success and client_info:
                # JSON 파일로 저장 (기존 형식 유지)
                save_client_data_to_json(site, client_info)
                logger.info(f"✅ DB에서 클라이언트 정보 조회 성공 - {site}: {len(client_info)}명")
                return True, client_info
            else:
                error_msg = f"❌ DB 직접 접속 실패: {site} - 클라이언트 정보 조회 결과가 비어있습니다. DB 연결 설정을 확인하세요."
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as db_error:
            error_msg = f"❌ DB 직접 접속 실패: {site} - {str(db_error)}. DB 연결 설정 및 드라이버 설치를 확인하세요."
            logger.error(error_msg)
            raise Exception(error_msg)
    
    # API 모드 (기본 또는 fallback)
    logger.info(f"🌐 API 모드: Client 정보 조회 - {site}")
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

