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
            # 기본값 설정: 7일 전부터 현재까지
            if start_date is None:
                start_date = datetime.now() - timedelta(days=7)
            if end_date is None:
                end_date = datetime.now()
            
            # 날짜 형식 변환 (UTC 형식 - API 서버가 기대하는 형식)
            start_date_str = start_date.isoformat() + 'Z'
            end_date_str = end_date.isoformat() + 'Z'
            
            # API 파라미터 구성 (EventDate 기준으로 변경)
            params = {
                'date': [f'gt:{start_date_str}', f'lt:{end_date_str}'],
                'limit': limit
            }
            
            # CreatedDate 기준으로도 시도 (UTC 형식) - 백업용
            created_params = {
                'createddate': [f'gt:{start_date_str}', f'lt:{end_date_str}'],
                'limit': limit
            }
            
            logger.info(f"Trying EventDate params: {params}")
            logger.info(f"Also trying CreatedDate params: {created_params}")
            
            logger.info(f"Fetching progress notes from {self.site}")
            logger.info(f"Date range: {start_date_str} to {end_date_str}")
            logger.info(f"Start date (datetime): {start_date}")
            logger.info(f"End date (datetime): {end_date}")
            logger.info(f"Limit: {limit}")
            logger.info(f"API URL: {self.api_url}")
            logger.info(f"Request params: {params}")
            
            # API 요청 (EventDate 기준)
            logger.info(f"Making API request to: {self.api_url}")
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=60  # 타임아웃 증가
            )
            
            logger.info(f"API response status (EventDate): {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} progress notes from {self.site} (EventDate)")
                
                # 응답 데이터 샘플 로깅
                if data and len(data) > 0:
                    logger.info("Response data sample (EventDate):")
                    for i, record in enumerate(data[:3]):
                        logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, CreatedDate: {record.get('CreatedDate', 'N/A')}")
                else:
                    logger.info("No data returned from API (EventDate)")
                    logger.info(f"Response content: {response.text}")
                    logger.info(f"Response headers: {dict(response.headers)}")
                
                # CreatedDate 기준으로도 시도 (EventDate에 데이터가 없을 경우 백업으로 시도)
                if not data or len(data) == 0:
                    logger.info("Trying CreatedDate-based query as backup...")
                    created_response = self.session.get(
                        self.api_url,
                        params=created_params,
                        timeout=60
                    )
                    
                    logger.info(f"API response status (CreatedDate): {created_response.status_code}")
                    
                    if created_response.status_code == 200:
                        created_data = created_response.json()
                        logger.info(f"Successfully fetched {len(created_data)} progress notes from {self.site} (CreatedDate)")
                        
                        if created_data and len(created_data) > 0:
                            logger.info("Response data sample (CreatedDate):")
                            for i, record in enumerate(created_data[:3]):
                                logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, CreatedDate: {record.get('CreatedDate', 'N/A')}")
                        else:
                            logger.info("No data returned from API (CreatedDate)")
                            logger.info(f"CreatedDate response content: {created_response.text}")
                        
                        return True, created_data
                
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
        logger.info(f"Incremental update - since_date: {since_date}, end_date: {end_date}")
        logger.info(f"Time difference: {end_date - since_date}")
        
        success, data = self.fetch_progress_notes(since_date, end_date)
        
        if success and data:
            logger.info(f"Incremental update found {len(data)} records")
            # 최신 기록 몇 개 로깅
            if len(data) > 0:
                logger.info("Latest records in incremental update:")
                for i, record in enumerate(data[:5]):
                    logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, CreatedDate: {record.get('CreatedDate', 'N/A')}")
        else:
            logger.info("No new records found in incremental update")
            # 디버깅을 위해 전체 데이터 조회 시도
            logger.info("Attempting to fetch all recent data for debugging...")
            debug_success, debug_data = self.fetch_recent_progress_notes(days=1)
            if debug_success and debug_data:
                logger.info(f"Debug: Found {len(debug_data)} records in last 24 hours")
                if len(debug_data) > 0:
                    logger.info("Debug: Recent records:")
                    for i, record in enumerate(debug_data[:3]):
                        logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, CreatedDate: {record.get('CreatedDate', 'N/A')}")
                    
                    # 특정 ID 검색
                    target_id = 302872
                    found_record = next((r for r in debug_data if r.get('Id') == target_id), None)
                    if found_record:
                        logger.info(f"Found target record ID {target_id}:")
                        logger.info(f"  EventDate: {found_record.get('EventDate')}")
                        logger.info(f"  CreatedDate: {found_record.get('CreatedDate', 'N/A')}")
                        logger.info(f"  Since date: {since_date}")
                        logger.info(f"  Is EventDate > since_date: {found_record.get('EventDate') > since_date.isoformat()}")
                    else:
                        logger.info(f"Target record ID {target_id} not found in recent data")
            
        return success, data

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
        logger.info(f"Fetching progress notes for site {site} with {days} days range")
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