#!/usr/bin/env python3
"""
프로그레스 노트 조회 API 클라이언트
사이트별로 프로그레스 노트를 가져와서 IndexedDB에 저장하는 기능
"""

import requests
import logging
import os
import json
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
            logger.error(f"Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}")
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
        logger.info(f"Session headers: {dict(self.session.headers)}")
    
    def fetch_progress_notes(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 500, # Default limit
                           progress_note_event_type_id: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        특정 조건에 맞는 프로그레스 노트를 가져옵니다.
        
        Args:
            start_date: 시작 날짜 (기본값: 14일 전)
            end_date: 종료 날짜 (기본값: 현재 시간)
            limit: 가져올 최대 개수 (기본값: 500)
            progress_note_event_type_id: 특정 이벤트 타입 ID로 필터링
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        try:
            # 기본값 설정
            if start_date is None:
                start_date = datetime.now() - timedelta(days=14)
            if end_date is None:
                end_date = datetime.now()
            
            # API 파라미터 설정
            params = {}
            
            # 날짜 형식 변환 (POSTMAN과 동일한 형식 사용)
            start_date_str = start_date.strftime('%Y-%m-%dT00:00:00Z')
            end_date_str = end_date.strftime('%Y-%m-%dT23:59:59Z')
            
            # 이벤트 타입 필터링
            if progress_note_event_type_id is not None:
                params['progressNoteEventTypeId'] = progress_note_event_type_id
            
            # 날짜 필터 적용 - POSTMAN과 동일한 형식 사용 (gt: >, lt: <)
            params['date'] = [f'gt:{start_date_str}', f'lt:{end_date_str}']
            
            # Limit 파라미터 설정
            if limit is not None:
                params['limit'] = limit
            
            # API 요청
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=120  # 타임아웃을 2분으로 증가
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} progress notes from {self.site}")
                
                # 응답 데이터 샘플 로깅 (파일로만 저장)
                if data and len(data) > 0:
                    debug_info = {
                        'timestamp': datetime.now().isoformat(),
                        'site': self.site,
                        'api_url': self.api_url,
                        'params': params,
                        'date_range': f"{start_date_str} to {end_date_str}",
                        'event_type_filter': progress_note_event_type_id,
                        'limit': params.get('limit'),
                        'response_status': response.status_code,
                        'records_fetched': len(data),
                        'sample_records': []
                    }
                    
                    for i, record in enumerate(data[:3]):
                        event_type = record.get('ProgressNoteEventType', {})
                        debug_info['sample_records'].append({
                            'index': i+1,
                            'id': record.get('Id'),
                            'event_date': record.get('EventDate'),
                            'event_type': event_type.get('Description', 'N/A')
                        })
                    
                    # Save debug info to file
                    try:
                        logs_dir = os.path.join(os.getcwd(), 'logs')
                        os.makedirs(logs_dir, exist_ok=True)
                        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                        filename = f'api_debug_{timestamp}.json'
                        filepath = os.path.join(logs_dir, filename)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(debug_info, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"Failed to save debug log: {str(e)}")
                else:
                    logger.info("No data returned from API")
                
                return True, data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                # API 실패시 상세한 에러 정보 제공
                error_details = {
                    'status_code': response.status_code,
                    'response_text': response.text,
                    'api_url': self.api_url,
                    'params': params,
                    'site': self.site,
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"API 실패 상세 정보: {error_details}")
                return False, None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after 120 seconds for {self.site}")
            return False, None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
    
    def fetch_recent_progress_notes(self, days: int = 14, limit: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        최근 N일간의 프로그레스 노트를 가져옵니다.
        
        Args:
            days: 가져올 일수 (기본값: 14일)
            limit: 최대 개수 (None이면 기본값 500 사용)
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        effective_limit = limit if limit is not None else 500
        return self.fetch_progress_notes(start_date, end_date, limit=effective_limit)
    
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
            
        return success, data

    def fetch_rod_progress_notes(self, year: int, month: int, event_types: List[str] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        ROD 대시보드용 프로그레스 노트를 가져옵니다.
        
        Args:
            year: 년도
            month: 월
            event_types: 필터링할 이벤트 타입 리스트 (None이면 자동으로 "Resident of the day" 이벤트 타입 찾기)
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        try:
            logger.info(f"Fetching ROD progress notes for {year}-{month}, event_types: {event_types}")
            
            # 년도/월에 해당하는 날짜 범위 계산
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # 이벤트 타입이 제공되지 않았으면 "Resident of the day" 이벤트 타입 자동 찾기
            if not event_types or len(event_types) == 0:
                logger.info("No event types provided, searching for 'Resident of the day' event types")
                event_types = self.find_resident_of_day_event_types()
                if not event_types:
                    logger.error("No Resident of the day event types found")
                    return False, None
                logger.info(f"Found Resident of the day event types: {event_types}")
            
            # 이벤트 타입 ID 찾기
            event_type_ids = []
            for event_type_name in event_types:
                event_type_id = self._find_event_type_id(event_type_name)
                if event_type_id:
                    event_type_ids.append(event_type_id)
                    logger.info(f"Found event type ID {event_type_id} for '{event_type_name}'")
                else:
                    logger.warning(f"Event type '{event_type_name}' not found")
            
            if not event_type_ids:
                logger.error("No valid event type IDs found")
                return False, None
            
            # 각 이벤트 타입별로 프로그레스 노트 가져오기
            all_notes = []
            for event_type_id in event_type_ids:
                logger.info(f"Fetching notes for event type ID: {event_type_id}")
                success, notes = self.fetch_progress_notes(
                    start_date=start_date,
                    end_date=end_date,
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes:
                    logger.info(f"Found {len(notes)} notes for event type ID {event_type_id}")
                    all_notes.extend(notes)
                else:
                    logger.warning(f"No notes found for event type ID {event_type_id}")
            
            logger.info(f"Total ROD notes found: {len(all_notes)}")
            return True, all_notes
            
        except Exception as e:
            logger.error(f"Error fetching ROD progress notes: {str(e)}")
            return False, None
    
    def fetch_progress_notes_by_event_types(self, days: int, event_types: List[str]) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        특정 이벤트 타입들로 필터링된 프로그레스 노트를 가져옵니다.
        
        Args:
            days: 가져올 일수
            event_types: 필터링할 이벤트 타입 리스트
            
        Returns:
            (성공 여부, 데이터 리스트 또는 None)
        """
        try:
            logger.info(f"Fetching progress notes by event types: {event_types} for {days} days")
            
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # 이벤트 타입 ID 찾기
            event_type_ids = []
            for event_type_name in event_types:
                event_type_id = self._find_event_type_id(event_type_name)
                if event_type_id:
                    event_type_ids.append(event_type_id)
                    logger.info(f"Found event type ID {event_type_id} for '{event_type_name}'")
                else:
                    logger.warning(f"Event type '{event_type_name}' not found")
            
            if not event_type_ids:
                logger.error("No valid event type IDs found")
                return False, None
            
            # 각 이벤트 타입별로 프로그레스 노트 가져오기 (성능 최적화: limit 제거)
            all_notes = []
            for event_type_id in event_type_ids:
                logger.info(f"Fetching notes for event type ID: {event_type_id}")
                success, notes = self.fetch_progress_notes(
                    start_date=start_date,
                    end_date=end_date,
                    limit=None,  # 성능 최적화: limit 제거
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes:
                    logger.info(f"Found {len(notes)} notes for event type ID {event_type_id}")
                    all_notes.extend(notes)
                else:
                    logger.warning(f"No notes found for event type ID {event_type_id}")
            
            logger.info(f"Total notes found for event types: {len(all_notes)}")
            return True, all_notes
            
        except Exception as e:
            logger.error(f"Error fetching progress notes by event types: {str(e)}")
            return False, None
    
    def find_resident_of_day_event_types(self) -> List[str]:
        """
        "Resident of the day" 관련 이벤트 타입들을 찾습니다.
        
        Returns:
            "Resident of the day" 관련 이벤트 타입 이름 리스트
        """
        try:
            logger.info(f"Finding Resident of the day event types for site: {self.site}")
            
            # 사이트별 JSON 파일에서 이벤트 타입 로드
            from api_eventtype import get_site_event_types
            event_types = get_site_event_types(self.site)
            
            if not event_types:
                logger.error(f"Failed to load event types from JSON for site {self.site}")
                return []
            
            logger.info(f"Searching through {len(event_types)} event types for 'Resident of the day'")
            resident_of_day_types = []
            
            for event_type in event_types:
                description = event_type.get('Description', '')
                event_id = event_type.get('Id')
                
                if 'resident of the day' in description.lower():
                    logger.info(f"Found Resident of the day event type: '{description}' (ID: {event_id})")
                    resident_of_day_types.append(description)
            
            logger.info(f"Found {len(resident_of_day_types)} Resident of the day event types: {resident_of_day_types}")
            return resident_of_day_types
            
        except Exception as e:
            logger.error(f"Error finding Resident of the day event types: {str(e)}")
            return []
    
    def _find_event_type_id(self, event_type_name: str) -> Optional[int]:
        """
        이벤트 타입 이름으로 ID를 찾습니다.
        
        Args:
            event_type_name: 이벤트 타입 이름
            
        Returns:
            이벤트 타입 ID 또는 None
        """
        try:
            logger.info(f"Finding event type ID for '{event_type_name}' in site: {self.site}")
            
            # 사이트별 JSON 파일에서 이벤트 타입 로드
            from api_eventtype import get_site_event_types
            event_types = get_site_event_types(self.site)
            
            if not event_types:
                logger.error(f"Failed to load event types from JSON for site {self.site}")
                return None
            
            logger.info(f"Found {len(event_types)} event types for site {self.site}")
            # 이벤트 타입 이름으로 ID 찾기
            for event_type in event_types:
                description = event_type.get('Description', '')
                event_id = event_type.get('Id')
                if event_type_name.lower() in description.lower():
                    logger.info(f"Found matching event type: '{description}' (ID: {event_id})")
                    return event_id
            
            logger.warning(f"Event type '{event_type_name}' not found in {len(event_types)} available types")
            return None
            
        except Exception as e:
            logger.error(f"Error finding event type ID for '{event_type_name}': {str(e)}")
            return None

def fetch_progress_notes_for_site(site: str, days: int = 14, event_types: List[str] = None, year: int = None, month: int = None, client_service_id: int = None, limit: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    특정 사이트의 프로그레스 노트를 가져오는 편의 함수 (DB 직접 접속 또는 API)
    
    Args:
        site: 사이트명
        days: 가져올 일수
        event_types: 필터링할 이벤트 타입 리스트
        year: 년도 (ROD 대시보드용)
        month: 월 (ROD 대시보드용)
        client_service_id: 특정 클라이언트 서비스 ID로 필터링
        limit: 최대 조회 개수 (None이면 DB 500/API 기본값 사용). filter endpoint에서 전체를 한 번에 받을 때 큰 값 전달.
        
    Returns:
        (성공 여부, 데이터 리스트 또는 None)
    """
    import sqlite3
    import os
    
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
    
    # DB 직접 접속 모드
    if use_db_direct:
        try:
            from manad_db_connector import MANADDBConnector
            from datetime import datetime, timedelta
            
            logger.info(f"🔌 DB 직접 접속 모드: Progress Notes 조회 - {site}")
            connector = MANADDBConnector(site)
            
            # ROD 대시보드용 특별 처리
            if year is not None and month is not None:
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
            
            # Event Type 필터링 (ID 변환 필요시)
            event_type_id = None
            if event_types and len(event_types) > 0:
                # Event Type 이름으로 ID 찾기 (간단한 버전, 실제로는 더 복잡할 수 있음)
                logger.warning(f"Event Type 필터링은 DB 직접 접속 모드에서 아직 완전히 지원되지 않습니다: {event_types}")
            
            effective_limit = limit if limit is not None else 500
            logger.info(f"🔍 [FILTER] connector.fetch_progress_notes 호출 - client_service_id={client_service_id}, limit={effective_limit}")
            logger.info(f"🔍 [FILTER] Parameters: start_date={start_date}, end_date={end_date}, limit={effective_limit}, event_type_id={event_type_id}, client_service_id={client_service_id}")
            progress_success, progress_notes = connector.fetch_progress_notes(
                start_date, end_date, limit=effective_limit, progress_note_event_type_id=event_type_id, client_service_id=client_service_id
            )
            logger.info(f"🔍 [FILTER] connector.fetch_progress_notes 결과 - success={progress_success}, notes_count={len(progress_notes) if progress_notes else 0}")
            
            if not progress_success or not progress_notes:
                error_msg = f"❌ DB 직접 접속 실패: {site} - Progress Notes 조회 결과가 비어있습니다. DB 연결 설정을 확인하세요."
                logger.error(error_msg)
                raise Exception(error_msg)
            
            return True, progress_notes
            
        except Exception as db_error:
            error_msg = f"❌ DB 직접 접속 실패: {site} - {str(db_error)}. DB 연결 설정 및 드라이버 설치를 확인하세요."
            logger.error(error_msg)
            raise Exception(error_msg)
    
    # API 모드
    try:
        logger.info(f"🌐 API 모드: Progress Notes 조회 - {site}")
        client = ProgressNoteFetchClient(site)
        logger.info(f"Fetching progress notes for site {site} with {days} days range, event_types: {event_types}")
        
        # ROD 대시보드용 특별 처리 (year와 month가 제공되고 event_types가 null이거나 빈 배열인 경우)
        logger.info(f"Checking ROD mode conditions: year={year}, month={month}, event_types={event_types}, event_types type={type(event_types)}")
        logger.info(f"Condition check: year is not None = {year is not None}, month is not None = {month is not None}")
        logger.info(f"Condition check: not event_types = {not event_types}, len(event_types) == 0 = {len(event_types) == 0 if event_types else 'N/A'}")
        
        # ROD 모드 조건: year와 month가 있고, event_types가 None이거나 빈 배열이거나 빈 문자열 리스트인 경우
        is_rod_mode = (year is not None and 
                      month is not None and 
                      (event_types is None or 
                       len(event_types) == 0 or 
                       (isinstance(event_types, list) and all(not et for et in event_types))))
        
        logger.info(f"ROD mode determination: {is_rod_mode}")
        
        if is_rod_mode:
            logger.info(f"ROD dashboard mode - fetching for year: {year}, month: {month}, event_types: {event_types}")
            return client.fetch_rod_progress_notes(year, month, event_types)
        else:
            # 일반적인 프로그레스 노트 요청
            # Note: API 모드에서는 client_service_id 필터링을 지원하지 않음
            # 클라이언트 필터링은 클라이언트 측에서 수행됨
            if event_types:
                # 이벤트 타입별로 필터링하여 가져오기
                logger.info(f"General request with event type filtering: {event_types}")
                return client.fetch_progress_notes_by_event_types(days, event_types)
            else:
                # 일반 프로그레스 노트 요청: 모든 노트 가져오기
                logger.info("No event types specified, fetching all progress notes")
                if client_service_id:
                    logger.warning(f"Client service ID filter ({client_service_id}) is not supported in API mode. Filtering will be done client-side.")
                return client.fetch_recent_progress_notes(days, limit=limit)
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

def fetch_event_types_for_site(site: str) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    특정 사이트의 이벤트 타입 목록을 가져옵니다. (사이트별 JSON 파일 사용)
    
    Args:
        site (str): 사이트 이름
    
    Returns:
        (성공 여부, 이벤트 타입 리스트 또는 None)
    """
    try:
        from api_eventtype import get_site_event_types
        event_types = get_site_event_types(site)
        
        if event_types:
            logger.info(f"Successfully loaded {len(event_types)} event types for site {site}")
            return True, event_types
        else:
            logger.warning(f"No event types found for site {site}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error fetching event types for site {site}: {str(e)}")
        return False, None

# 사이트별 Resident of the day 이벤트 타입 ID (하드코딩)
SITE_EVENT_TYPE_IDS = {
    'Parafield Gardens': {'rn_en': 30, 'pca': 121},
    'Nerrilda': {'rn_en': 30, 'pca': 85},
    'Ramsay': {'rn_en': 82, 'pca': 30},
    'West Park': {'rn_en': 30, 'pca': 100},
    'Yankalilla': {'rn_en': 30, 'pca': 63}
}

def find_resident_of_day_event_types(event_types: List[Dict[str, Any]] = None, site: str = None) -> tuple[Optional[int], Optional[int]]:
    """
    사이트별 Resident of the day 이벤트 타입 ID를 반환합니다.
    
    Args:
        event_types: 이벤트 타입 목록 (사용하지 않음, 호환성을 위해 유지)
        site: 사이트명 (사용하지 않음, 호환성을 위해 유지)
    
    Returns:
        (RN/EN 이벤트 타입 ID, PCA 이벤트 타입 ID)
    """
    # 현재 사이트의 이벤트 타입 ID 반환 (하드코딩된 값 사용)
    # 사이트는 ProgressNoteFetchClient의 self.site에서 가져옴
    return None, None  # 이 함수는 더 이상 사용되지 않음

def get_site_event_type_ids(site: str) -> tuple[Optional[int], Optional[int]]:
    """
    특정 사이트의 Resident of the day 이벤트 타입 ID를 반환합니다.
    
    Args:
        site: 사이트명
    
    Returns:
        (RN/EN 이벤트 타입 ID, PCA 이벤트 타입 ID)
    """
    site_ids = SITE_EVENT_TYPE_IDS.get(site)
    if site_ids:
        rn_en_id = site_ids.get('rn_en')
        pca_id = site_ids.get('pca')
        logger.info(f"Using hardcoded event type IDs for {site}: RN/EN={rn_en_id}, PCA={pca_id}")
        return rn_en_id, pca_id
    else:
        logger.error(f"No event type IDs found for site: {site}")
        return None, None

# 기존 API에서 이벤트 타입을 가져오는 로직 (주석 처리)
"""
def find_resident_of_day_event_types_from_api(event_types: List[Dict[str, Any]]) -> tuple[Optional[int], Optional[int]]:
    # 이벤트 타입 목록에서 Resident of the day 관련 이벤트 타입 ID를 찾습니다.
    rn_en_id = None
    pca_id = None
    
    for event_type in event_types:
        description = event_type.get('Description', '').lower()
        event_id = event_type.get('Id')
        
        if 'resident of the day' in description:
            # lifestyle은 제외
            if 'lifestyle' in description:
                logger.info(f"Skipping lifestyle event type: ID {event_id} - {event_type.get('Description')}")
                continue
            elif 'pca' in description:
                pca_id = event_id
                logger.info(f"Found PCA Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
            elif any(keyword in description for keyword in ['rn', 'en', 'nurse']):
                rn_en_id = event_id
                logger.info(f"Found RN/EN Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
    
    return rn_en_id, pca_id
"""

def fetch_residence_of_day_notes_with_client_data(site, year, month):
    """
    특정 년월의 "Resident of the day" 노트를 클라이언트 데이터와 함께 가져옵니다.
    
    Args:
        site (str): 사이트 이름
        year (int): 년도
        month (int): 월
    
    Returns:
        dict: Residence별 상태 정보
    """
    try:
        logger.info(f"Fetching Resident of the day notes for {site} - {year}/{month}")
        
        # Create debug info for file logging
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'site': site,
            'year': year,
            'month': month,
            'steps': []
        }
        
        # 1. 클라이언트 정보 가져오기
        from api_client import fetch_client_information
        client_success, client_data = fetch_client_information(site)
        if not client_success or not client_data:
            logger.error(f"Failed to fetch client data for {site}")
            return {}
        
        debug_info['steps'].append({
            'step': 'client_data_fetch',
            'success': client_success,
            'client_count': len(client_data) if client_data else 0,
            'sample_clients': []
        })
        
        # Add sample client data to debug info
        if client_data:
            for i, client in enumerate(client_data[:3]):
                first_name = client.get('FirstName', '')
                surname = client.get('Surname', '')
                last_name = client.get('LastName', '')
                main_id = client.get('MainClientServiceId', '')
                debug_info['steps'][-1]['sample_clients'].append({
                    'index': i+1,
                    'name': f"{first_name} {surname or last_name}",
                    'main_client_service_id': main_id
                })
        
        # 2. 날짜 범위 설정
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        debug_info['steps'].append({
            'step': 'date_range_setup',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        # 3. 사이트별 Resident of the day 관련 EventType ID들 가져오기 (하드코딩)
        rn_en_id, pca_id = get_site_event_type_ids(site)
        
        # 기존 API에서 이벤트 타입을 가져오는 로직 (주석 처리)
        # event_success, event_types = fetch_event_types_for_site(site)
        # if not event_success or not event_types:
        #     logger.error(f"Failed to fetch event types for {site}")
        #     return {}
        # rn_en_id, pca_id = find_resident_of_day_event_types(event_types)
        
        debug_info['steps'].append({
            'step': 'event_type_fetch',
            'success': True,  # 하드코딩된 값 사용
            'event_types_count': 0,  # API에서 가져오지 않음
            'rn_en_id': rn_en_id,
            'pca_id': pca_id
        })
        
        if not rn_en_id and not pca_id:
            logger.warning(f"No Resident of the day event types found for {site}")
            return {}
        
        # 4. 모든 Resident of the day 노트를 한 번에 가져오기 (최적화)
        all_resident_notes = []
        event_type_mapping = {}  # 노트를 RN/EN과 PCA로 분류하기 위한 매핑
        rn_en_notes = []  # RN/EN 노트만 따로 저장
        pca_notes = []    # PCA 노트만 따로 저장
        
        # 먼저 저장된 파일에서 데이터를 찾아보기
        logs_dir = os.path.join(os.getcwd(), 'data')
        timestamp_pattern = f"{year}_{month:02d}"
        
        # 5월 데이터 파일 찾기 (정확한 패턴 매칭)
        rn_en_files = [f for f in os.listdir(logs_dir) if f.startswith(f'progress_notes_rn_en_{site}_{timestamp_pattern}_')]
        pca_files = [f for f in os.listdir(logs_dir) if f.startswith(f'progress_notes_pca_{site}_{timestamp_pattern}_')]
        
        logger.info(f"Looking for files with pattern: {timestamp_pattern}")
        logger.info(f"Site: {site}")
        logger.info(f"All files in data directory: {[f for f in os.listdir(logs_dir) if 'Parafield' in f and '2025_05' in f]}")
        logger.info(f"Found RN/EN files: {rn_en_files}")
        logger.info(f"Found PCA files: {pca_files}")
        
        if rn_en_files and pca_files:
            # 가장 최근 파일 선택
            rn_en_files.sort(reverse=True)
            pca_files.sort(reverse=True)
            
            try:
                # RN/EN 노트 로드
                rn_en_filepath = os.path.join(logs_dir, rn_en_files[0])
                with open(rn_en_filepath, 'r', encoding='utf-8') as f:
                    rn_en_notes = json.load(f)
                logger.info(f"Loaded {len(rn_en_notes)} RN/EN notes from file: {rn_en_files[0]}")
                
                # PCA 노트 로드
                pca_filepath = os.path.join(logs_dir, pca_files[0])
                with open(pca_filepath, 'r', encoding='utf-8') as f:
                    pca_notes = json.load(f)
                logger.info(f"Loaded {len(pca_notes)} PCA notes from file: {pca_files[0]}")
                
                # 모든 노트 합치기
                all_resident_notes = rn_en_notes + pca_notes
                
                # 노트를 타입별로 분류
                for note in rn_en_notes:
                    event_type_mapping[note.get('Id')] = "RN/EN"
                for note in pca_notes:
                    event_type_mapping[note.get('Id')] = "PCA"
                
                logger.info(f"Successfully loaded {len(all_resident_notes)} notes from saved files")
                
            except Exception as e:
                logger.error(f"Failed to load notes from files: {str(e)}")
                # 파일 로드 실패 시 API에서 가져오기
                all_resident_notes = []
                rn_en_notes = []
                pca_notes = []
        else:
            logger.info(f"No saved files found for {site} {year}/{month}, fetching from API")
        
        # 저장된 파일이 없거나 로드 실패한 경우 API에서 가져오기
        if not all_resident_notes:
            # RN/EN, PCA 이벤트 타입 ID를 포함하여 한 번에 가져오기
            event_type_ids = []
            if rn_en_id:
                event_type_ids.append(rn_en_id)
            if pca_id:
                event_type_ids.append(pca_id)
            
            if event_type_ids:
                # 모든 이벤트 타입을 한 번에 가져오기
                client = ProgressNoteFetchClient(site)
            
            # 날짜 범위를 조금 더 넓게 설정 (전후 1일 포함)
            extended_start_date = start_date - timedelta(days=1)
            extended_end_date = end_date + timedelta(days=1)
            
            debug_info['steps'].append({
                'step': 'fetch_notes_optimized',
                'event_type_ids': event_type_ids,
                'date_range': f"{extended_start_date.isoformat()} to {extended_end_date.isoformat()}",
                'notes_fetched': 0
            })
            
            # 각 이벤트 타입별로 개별 호출 (API가 OR 조건을 지원하지 않는 경우)
            for event_type_id in event_type_ids:
                success, notes = client.fetch_progress_notes(
                    start_date=extended_start_date,
                    end_date=extended_end_date,
                    limit=None,  # 제한 없음
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes is not None:
                    all_resident_notes.extend(notes)
                    
                    # 노트를 타입별로 분류
                    if event_type_id == rn_en_id:
                        event_type_name = "RN/EN"
                    elif event_type_id == pca_id:
                        event_type_name = "PCA"
                    else:
                        event_type_name = "Unknown"
                    
                    for note in notes:
                        event_type_mapping[note.get('Id')] = event_type_name
                    
                    # Event Type별로 노트 분리 저장
                    if event_type_name == "RN/EN":
                        rn_en_notes = notes
                    elif event_type_name == "PCA":
                        pca_notes = notes
                    
                    debug_info['steps'][-1]['notes_fetched'] += len(notes)
                    logger.info(f"Fetched {len(notes)} notes for event type ID {event_type_id} ({event_type_name})")
                else:
                    logger.warning(f"No notes found for EventType ID {event_type_id}")
        else:
            logger.warning("No Resident of the day event types found")
        
        # Progress Note를 JSON 파일로 저장 (Event Type별로 분리)
        try:
            logs_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # RN/EN 노트 저장
            if rn_en_notes:
                rn_en_filename = f'progress_notes_rn_en_{site}_{year}_{month:02d}_{timestamp}.json'
                rn_en_filepath = os.path.join(logs_dir, rn_en_filename)
                with open(rn_en_filepath, 'w', encoding='utf-8') as f:
                    json.dump(rn_en_notes, f, indent=2, ensure_ascii=False)
                logger.info(f"RN/EN notes saved to: {rn_en_filename}")
            
            # PCA 노트 저장
            if pca_notes:
                pca_filename = f'progress_notes_pca_{site}_{year}_{month:02d}_{timestamp}.json'
                pca_filepath = os.path.join(logs_dir, pca_filename)
                with open(pca_filepath, 'w', encoding='utf-8') as f:
                    json.dump(pca_notes, f, indent=2, ensure_ascii=False)
                logger.info(f"PCA notes saved to: {pca_filename}")
                
        except Exception as e:
            logger.error(f"Failed to save progress notes to JSON files: {str(e)}")
        
        debug_info['steps'].append({
            'step': 'total_notes_summary',
            'total_notes': len(all_resident_notes),
            'sample_notes': []
        })
        
        # Add sample notes to debug info
        if all_resident_notes:
            for i, note in enumerate(all_resident_notes[:3]):
                debug_info['steps'][-1]['sample_notes'].append({
                    'index': i+1,
                    'id': note.get('Id'),
                    'client_service_id': note.get('ClientServiceId'),
                    'event_type': note.get('ProgressNoteEventType', {}).get('Description', 'N/A'),
                    'event_date': note.get('EventDate', 'N/A')
                })
        
        # 5. Residence별로 노트 매칭 및 상태 생성
        residence_status = {}
        unmatched_notes = []  # 매칭 실패한 노트 추적
        
        # 클라이언트 데이터 구조 확인 및 처리
        if isinstance(client_data, dict):
            client_list = list(client_data.values()) if client_data else []
        elif isinstance(client_data, list):
            client_list = client_data
        else:
            logger.error(f"Unexpected client data type: {type(client_data)}")
            client_list = []
        
        logger.info(f"Processing {len(client_list)} clients")
        
        # 먼저 모든 residence의 ClientRecordId를 수집
        residence_client_mapping = {}
        for residence in client_list:
            if isinstance(residence, dict):
                first_name = residence.get('FirstName', '')
                surname = residence.get('Surname', '')
                last_name = residence.get('LastName', '')
                preferred_name = residence.get('PreferredName', '')
                wing_name = residence.get('WingName', '')
                
                # Residence 이름 생성 - FirstName과 Surname/LastName 조합
                if first_name and surname:
                    residence_name = f"{first_name} {surname}"
                elif first_name and last_name:
                    residence_name = f"{first_name} {last_name}"
                elif first_name:
                    residence_name = first_name
                else:
                    continue
                
                # Residence의 ClientRecordId 찾기 (실시간 API 데이터에서는 다른 필드명 사용)
                residence_client_record_id = residence.get('ClientRecordId') or residence.get('Id') or residence.get('ClientId')
                
                # Residence 이름과 ClientRecordId 매핑 저장
                residence_client_mapping[residence_name] = residence_client_record_id
                
                # 모든 resident를 화면에 표시 (노트가 없어도 표시)
                residence_notes = []
                
                if residence_client_record_id:
                    # 해당 Residence의 노트 찾기 (매칭된 노트만)
                    for note in all_resident_notes:
                        note_client_id = note.get('ClientId')
                        
                        # 매칭 로직: ClientRecordId로만 매칭
                        if note_client_id == residence_client_record_id:
                            residence_notes.append(note)
                
                # 노트가 없어도 residence_status에 추가 (모든 residence 표시)
                

                
                # Residence별 상태 생성 (노트가 없어도 생성)
                rn_en_has_note = False
                pca_has_note = False
                rn_en_count = 0
                pca_count = 0
                
                for note in residence_notes:
                    note_id = note.get('Id')
                    event_type_name = event_type_mapping.get(note_id)
                    
                    if event_type_name == "RN/EN":
                        rn_en_has_note = True
                        rn_en_count += 1
                    elif event_type_name == "PCA":
                        pca_has_note = True
                        pca_count += 1
                
                residence_status[residence_name] = {
                    'residence_name': residence_name,
                    'preferred_name': preferred_name,
                    'wing_name': wing_name,
                    'rn_en_has_note': rn_en_has_note,
                    'pca_has_note': pca_has_note,
                    'rn_en_count': rn_en_count,
                    'pca_count': pca_count,
                    'total_count': rn_en_count + pca_count
                }
        
        # 매칭되지 않은 노트 계산 (효율적인 방법)
        matched_note_ids = set()
        
        logger.info(f"Total notes to process: {len(all_resident_notes)}")
        logger.info(f"Total residences available: {len(residence_client_mapping)}")
        
        # 각 노트가 어떤 residence와 매칭되는지 확인
        for note in all_resident_notes:
            note_client_id = note.get('ClientId')
            note_matched = False
            
            # 모든 residence의 ClientRecordId와 비교
            for residence_name, residence_client_record_id in residence_client_mapping.items():
                if residence_client_record_id and note_client_id == residence_client_record_id:
                    matched_note_ids.add(note.get('Id'))
                    note_matched = True
                    break
            
            # 매칭되지 않은 노트 추가
            if not note_matched:
                unmatched_note_info = {
                    'note_id': note.get('Id'),
                    'client_id': note_client_id,
                    'event_type': note.get('ProgressNoteEventType', {}).get('Description', 'Unknown'),
                    'event_date': note.get('EventDate', 'Unknown'),
                    'residence_name': 'Unknown',
                    'residence_client_record_id': 'Unknown'
                }
                unmatched_notes.append(unmatched_note_info)
        
        logger.info(f"Matched notes: {len(matched_note_ids)}")
        logger.info(f"Unmatched notes: {len(unmatched_notes)}")
        
        # Save debug info to file
        try:
            logs_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'rod_processing_{site}_{year}_{month:02d}_{timestamp}.json'
            filepath = os.path.join(logs_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save ROD processing debug log: {str(e)}")
        
        # 매칭 실패한 노트 중복 제거
        unique_unmatched_notes = []
        seen_notes = set()
        for note in unmatched_notes:
            note_key = f"{note['note_id']}_{note['client_id']}"
            if note_key not in seen_notes:
                unique_unmatched_notes.append(note)
                seen_notes.add(note_key)
        
        # 매칭되지 않은 노트를 JSON 파일로 저장
        if unique_unmatched_notes:
            try:
                logs_dir = os.path.join(os.getcwd(), 'data')
                os.makedirs(logs_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                unmatched_filename = f'unmatched_notes_{site}_{year}_{month:02d}_{timestamp}.json'
                unmatched_filepath = os.path.join(logs_dir, unmatched_filename)
                
                unmatched_data = {
                    'site': site,
                    'year': year,
                    'month': month,
                    'timestamp': datetime.now().isoformat(),
                    'total_notes': len(all_resident_notes),
                    'matched_notes': len(matched_note_ids),
                    'unmatched_notes_count': len(unique_unmatched_notes),
                    'unmatched_notes': unique_unmatched_notes,
                    'summary': {
                        'total_residences': len(residence_client_mapping),
                        'available_client_ids': list(residence_client_mapping.values()),
                        'unmatched_client_ids': list(set([note['client_id'] for note in unique_unmatched_notes]))
                    }
                }
                
                with open(unmatched_filepath, 'w', encoding='utf-8') as f:
                    json.dump(unmatched_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved {len(unique_unmatched_notes)} unmatched notes to: {unmatched_filename}")
                
            except Exception as e:
                logger.error(f"Failed to save unmatched notes to file: {str(e)}")
        else:
            logger.info("No unmatched notes found")
        
        logger.info(f"ROD processing completed for {site}: {len(residence_status)} residences, {len(unique_unmatched_notes)} unmatched notes")
        if len(residence_status) == 0:
            logger.warning("No residences found in residence_status!")
        
        # residence_status에 unmatched_notes 정보 추가
        result = {
            'residence_status': residence_status,
            'unmatched_notes': unique_unmatched_notes
        }
        return result
        
    except Exception as e:
        logger.error(f"Error in fetch_residence_of_day_notes_with_client_data: {str(e)}")
        return {}

def save_data_to_file(site: str, year: int, month: int, all_notes: list, residence_status: dict, debug_info: dict = None):
    """
    받은 데이터를 JSON 파일로 저장합니다.
    
    Args:
        site (str): 사이트 이름
        year (int): 년도
        month (int): 월
        all_notes (list): 모든 Progress Note 데이터
        residence_status (dict): Residence별 상태 정보
        debug_info (dict): 디버깅 정보 (선택사항)
    """
    try:
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{site}_{year:04d}{month:02d}_{timestamp}.json"
        filepath = os.path.join('data', filename)
        
        # data 디렉토리가 없으면 생성
        os.makedirs('data', exist_ok=True)
        
        # JSON 데이터 구성
        data_to_save = {
            'site': site,
            'year': year,
            'month': month,
            'timestamp': timestamp,
            'raw_progress_notes': all_notes,
            'processed_residence_status': residence_status
        }
        
        # 디버깅 정보가 있으면 추가
        if debug_info:
            data_to_save['debug_info'] = debug_info
        
        # JSON 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to file: {filepath}")
        
    except Exception as e:
        logger.error(f"Error saving data to file: {str(e)}")

def fetch_residence_of_day_notes(site: str, start_date: datetime, end_date: datetime) -> tuple[bool, Optional[Dict[str, List[Dict[str, Any]]]]]:
    """
    특정 사이트에서 "Resident of the day" 제목의 노트를 Residence별로 그룹화하여 가져옵니다.
    
    Args:
        site: 사이트명
        start_date: 시작 날짜
        end_date: 종료 날짜
        
    Returns:
        (성공 여부, Residence별 노트 딕셔너리 또는 None)
    """
    try:
        client = ProgressNoteFetchClient(site)
        success, all_notes = client.fetch_progress_notes(start_date, end_date, limit=1000)
        
        if not success or not all_notes:
            logger.warning(f"No progress notes found for site {site}")
            return True, {}
        
        # "Resident of the day" 제목을 가진 노트 필터링 및 Residence별 그룹화
        resident_notes = {}
        for note in all_notes:
            # NotesDetailTitle이 "Resident of the day"인지 확인
            if note.get('NotesDetailTitle') and 'resident of the day' in note['NotesDetailTitle'].lower():
                # Residence 이름 추출 (NotesDetailTitle에서 "Resident of the day - [Residence Name]" 형식)
                title = note.get('NotesDetailTitle', '')
                residence_name = extract_residence_name_from_title(title)
                
                if residence_name:
                    if residence_name not in resident_notes:
                        resident_notes[residence_name] = []
                    resident_notes[residence_name].append(note)
        
        logger.info(f"Found Resident of the day notes for {len(resident_notes)} residences in site {site}")
        return True, resident_notes
        
    except Exception as e:
        logger.error(f"Error fetching Resident of the day notes for site {site}: {str(e)}")
        return False, None

def extract_residence_name_from_title(title: str) -> Optional[str]:
    """
    NotesDetailTitle에서 Residence 이름을 추출합니다.
    
    Args:
        title: NotesDetailTitle 문자열
        
    Returns:
        Residence 이름 또는 None
    """
    try:
        # "Resident of the day - [Residence Name]" 형식에서 Residence 이름 추출
        if 'resident of the day' in title.lower():
            # 대시(-) 이후의 텍스트를 Residence 이름으로 간주
            parts = title.split('-')
            if len(parts) > 1:
                residence_name = parts[1].strip()
                return residence_name if residence_name else None
        
        # 다른 형식도 시도
        if 'resident of the day' in title.lower():
            # "Resident of the day [Residence Name]" 형식
            import re
            match = re.search(r'resident of the day\s*[-:]\s*(.+)', title, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    except Exception as e:
        logger.error(f"Error extracting residence name from title '{title}': {str(e)}")
        return None

def fetch_residence_of_day_notes_for_all_sites(start_date: datetime, end_date: datetime) -> Dict[str, tuple[bool, Optional[List[Dict[str, Any]]]]]:
    """
    모든 사이트에서 "Resident of the day" 노트를 가져옵니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        
    Returns:
        사이트별 (성공 여부, Resident of the day 노트 리스트) 딕셔너리
    """
    results = {}
    
    for site in SITE_SERVERS.keys():
        try:
            success, data = fetch_residence_of_day_notes(site, start_date, end_date)
            results[site] = (success, data)
            logger.info(f"Site {site}: {'Success' if success else 'Failed'} - {len(data) if data else 0} Resident of the day notes")
        except Exception as e:
            logger.error(f"Error fetching Resident of the day data for site {site}: {str(e)}")
            results[site] = (False, None)
    
    return results

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 테스트 실행
    test_progress_note_fetch() 