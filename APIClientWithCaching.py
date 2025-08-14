import json
import os
import requests
from typing import Dict, Any
import logging

# 테스트용 설정
SITE_SERVERS = {
    "test_site": "http://192.168.1.11:8080"
}

API_HEADERS = {
    'x-api-username': 'ManadAPI',
    'x-api-key': '6RU+gahOFDvf/aF2dC7hAV+flYNe+dMb8Ts2xMsR0QM=',
    'Content-Type': 'application/json'
    # 필요한 경우 인증 헤더 등 추가
}

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, site: str):
        self.site = site
        self.base_url = SITE_SERVERS.get(site)
        self.session = requests.Session()
        self.session.headers.update(API_HEADERS)
        self.client_data_path = 'templates/client_data'
        
        if not os.path.exists(self.client_data_path):
            os.makedirs(self.client_data_path)

    def get_client_information(self) -> Dict[str, Any]:
        """
        클라이언트 정보를 가져오는 함수
        캐시 사용 안함 - API 실패시 에러 발생
        """
        try:
            endpoint = f"{self.base_url}/api/client"
            response = self.session.get(endpoint)
            response.raise_for_status()
            client_data = response.json()
            
            # 성공적으로 가져왔다면 캐시에 저장 (읽기 전용 백업용)
            self._cache_client_data(client_data)
            return client_data
            
        except requests.RequestException as e:
            # API 호출 실패시 에러 발생 (캐시 사용 안함)
            logger.error(f"API 호출 실패: {str(e)}")
            raise e  # 캐시된 데이터 사용 안함, 에러 발생

    def _cache_client_data(self, data: Dict[str, Any]) -> None:
        """클라이언트 데이터를 파일에 캐시"""
        cache_path = self._get_client_cache_path()
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_cached_client_data(self) -> Dict[str, Any]:
        """캐시된 클라이언트 데이터 로드"""
        cache_path = self._get_client_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _get_client_cache_path(self) -> str:
        """클라이언트 데이터 캐시 파일 경로 반환"""
        return os.path.join(self.client_data_path, f'{self.site}_client.json')

def test_api_client():
    # 테스트용 API 클라이언트 생성
    client = APIClient("test_site")
    
    try:
        # API 호출 테스트
        client_info = client.get_client_information()
        print("API 호출 성공:", client_info)
        
    except requests.RequestException as e:
        print("API 호출 실패:", str(e))
        print("캐시 사용 안함 - 에러 발생")
        
    except Exception as e:
        print("예상치 못한 오류:", str(e))

if __name__ == "__main__":
    test_api_client()