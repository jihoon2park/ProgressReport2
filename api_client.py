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
    """
    거주자(Client) 정보를 가져오는 통합 함수
    
    DB 직접 접속 모드에서는 매번 최신 데이터를 DB에서 직접 조회합니다.
    캐시를 사용하지 않으며, 항상 최신 데이터를 반환합니다.
    
    Args:
        site: 사이트 이름 (예: 'Parafield Gardens')
        
    Returns:
        (성공 여부, 클라이언트 리스트)
    """
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
    
    # DB 직접 접속 모드 (권장 - 매번 최신 데이터 조회)
    if use_db_direct:
        try:
            logger.info(f"🔍 DEBUG: use_db_direct=True, importing MANADDBConnector")
            from manad_db_connector import MANADDBConnector
            logger.info(f"🔍 DEBUG: MANADDBConnector imported successfully")
            logger.info(f"🔌 DB 직접 접속: 거주자 정보 조회 - {site} (최신 데이터)")
            logger.info(f"🔍 DEBUG: Creating MANADDBConnector instance for site: {site}")
            connector = MANADDBConnector(site)
            logger.info(f"🔍 DEBUG: MANADDBConnector instance created, about to call fetch_clients()")
            import time
            start_time = time.time()
            success, client_info = connector.fetch_clients()
            elapsed_time = time.time() - start_time
            logger.info(f"🔍 DEBUG: fetch_clients() returned after {elapsed_time:.2f} seconds - success: {success}")
            
            if success and client_info:
                logger.info(f"🔍 DEBUG: Client info received, count: {len(client_info) if isinstance(client_info, list) else 'N/A'}")
                # JSON 파일로 저장 (참고용, 읽기는 하지 않음)
                save_client_data_to_json(site, client_info)
                logger.info(f"✅ 거주자 정보 조회 성공 - {site}: {len(client_info)}명")
                logger.info(f"🔍 DEBUG: Returning from fetch_client_information with success=True")
                return True, client_info
            else:
                error_msg = f"❌ DB 직접 접속 실패: {site} - 거주자 정보 조회 결과가 비어있습니다."
                logger.error(f"🔍 DEBUG: fetch_clients returned success={success}, client_info is empty or None")
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as db_error:
            logger.error(f"🔍 DEBUG: Exception in fetch_client_information (DB direct mode): {type(db_error).__name__}: {str(db_error)}")
            import traceback
            logger.error(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
            error_msg = f"❌ DB 직접 접속 실패: {site} - {str(db_error)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    # API 모드 (fallback)
    logger.info(f"🌐 API 모드: 거주자 정보 조회 - {site}")
    try:
        api_client = APIClient(site)
        client_info = api_client.get_client_information()
        
        # JSON 파일로 저장 (참고용)
        if client_info:
            save_client_data_to_json(site, client_info)
            logger.info(f"✅ 거주자 정보 조회 성공 - {site}: {len(client_info) if isinstance(client_info, list) else 'N/A'}명")
        
        return True, client_info
    except requests.RequestException as e:
        logger.error(f"❌ 거주자 정보 조회 실패 - {site}: {str(e)}")
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

