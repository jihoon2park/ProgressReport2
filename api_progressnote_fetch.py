#!/usr/bin/env python3
"""
프로그레스 노트 조회 API 클라이언트
사이트별로 프로그레스 노트를 가져와서 IndexedDB에 저장하는 기능
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from config import SITE_SERVERS, API_HEADERS, get_api_headers

# 로깅 설정
logger = logging.getLogger(__name__)

class ProgressNoteFetchClient:
    """프로그레스 노트 조회 API 클라이언트"""
    
    def __init__(self, site: str):
        """
        Args:
            site: 사이트명 (예: 'Parafield Gardens', 'Nerrilda')
        """
        self.site = site
        self.server_ip = SITE_SERVERS.get(site)
        
        if not self.server_ip:
            raise ValueError(f"Unknown site: {site}")
        
        # server_ip에 이미 포트가 포함되어 있으므로 그대로 사용
        self.base_url = f"http://{self.server_ip}"
        self.api_url = f"{self.base_url}/api/progressnote/details"
        
        # 세션 생성
        self.session = requests.Session()
        # 사이트별 API 헤더 설정
        site_headers = get_api_headers(site)
        self.session.headers.update(site_headers)
        
        logger.info(f"ProgressNoteFetchClient initialized for site: {site} ({self.server_ip})")
        logger.info(f"API URL: {self.api_url}")
    
    def fetch_progress_notes(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 100) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        프로그레스 노트를 가져옵니다.
        
        Args:
            start_date: 시작 날짜 (기본값: 2주 전)
            end_date: 종료 날짜 (기본값: 현재 시간)
            limit: 가져올 최대 개수
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        try:
            # 기본값 설정: 2주 전부터 현재까지
            if start_date is None:
                start_date = datetime.now() - timedelta(weeks=2)
            if end_date is None:
                end_date = datetime.now()
            
            # 날짜 형식 변환 (ISO 8601)
            start_date_str = start_date.isoformat() + 'Z'
            end_date_str = end_date.isoformat() + 'Z'
            
            # API 파라미터 구성
            params = {
                'date': [f'gt:{start_date_str}', f'lt:{end_date_str}'],
                'limit': limit
            }
            
            logger.info(f"Fetching progress notes from {self.site}")
            logger.info(f"Date range: {start_date_str} to {end_date_str}")
            logger.info(f"Limit: {limit}")
            
            # API 요청
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=30
            )
            
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} progress notes from {self.site}")
                return True, data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return False, None
                
        except requests.RequestException as e:
            logger.error(f"Network error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
    
    def fetch_recent_progress_notes(self, days: int = 14) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        최근 N일간의 프로그레스 노트를 가져옵니다.
        
        Args:
            days: 가져올 일수 (기본값: 14일)
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.fetch_progress_notes(start_date, end_date)
    
    def fetch_progress_notes_since(self, since_date: datetime) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        특정 날짜 이후의 프로그레스 노트를 가져옵니다 (증분 업데이트용).
        
        Args:
            since_date: 시작 날짜
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        end_date = datetime.now()
        return self.fetch_progress_notes(since_date, end_date)

def fetch_progress_notes_for_site(site: str, days: int = 14) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    특정 사이트의 프로그레스 노트를 가져오는 편의 함수
    
    Args:
        site: 사이트명
        days: 가져올 일수
        
    Returns:
        (성공 여부, 데이터 리스트 또는 None)
    """
    try:
        client = ProgressNoteFetchClient(site)
        return client.fetch_recent_progress_notes(days)
    except Exception as e:
        logger.error(f"Error creating client for site {site}: {str(e)}")
        return False, None

def fetch_progress_notes_for_all_sites(days: int = 14) -> Dict[str, tuple[bool, Optional[List[Dict[str, Any]]]]]:
    """
    모든 사이트의 프로그레스 노트를 가져오는 함수
    
    Args:
        days: 가져올 일수
        
    Returns:
        사이트별 결과 딕셔너리
    """
    results = {}
    
    for site in SITE_SERVERS.keys():
        logger.info(f"Fetching progress notes for site: {site}")
        success, data = fetch_progress_notes_for_site(site, days)
        results[site] = (success, data)
        
        if success:
            logger.info(f"Successfully fetched {len(data) if data else 0} progress notes from {site}")
        else:
            logger.error(f"Failed to fetch progress notes from {site}")
    
    return results

# 테스트 함수
def test_progress_note_fetch():
    """프로그레스 노트 조회 기능 테스트"""
    print("=== 프로그레스 노트 조회 테스트 ===")
    
    # 사용 가능한 사이트 출력
    print(f"Available sites: {list(SITE_SERVERS.keys())}")
    
    # 각 사이트별로 테스트
    for site in SITE_SERVERS.keys():
        print(f"\n--- {site} 테스트 ---")
        
        try:
            client = ProgressNoteFetchClient(site)
            success, data = client.fetch_recent_progress_notes(days=7)  # 7일치만 테스트
            
            if success:
                print(f"✅ 성공: {len(data) if data else 0}개의 프로그레스 노트 조회")
                if data and len(data) > 0:
                    # 첫 번째 항목 샘플 출력
                    sample = data[0]
                    print(f"   샘플 데이터:")
                    print(f"   - ID: {sample.get('Id')}")
                    print(f"   - ClientId: {sample.get('ClientId')}")
                    print(f"   - EventDate: {sample.get('EventDate')}")
                    print(f"   - Notes: {sample.get('NotesPlainText', '')[:50]}...")
            else:
                print(f"❌ 실패: 프로그레스 노트 조회 실패")
                
        except Exception as e:
            print(f"❌ 오류: {str(e)}")

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    test_progress_note_fetch() 