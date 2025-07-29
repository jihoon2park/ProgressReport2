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
                           limit: int = 1000,
                           progress_note_event_type_id: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        프로그레스 노트를 가져옵니다.
        EventType 필터를 우선적으로 적용하여 데이터 양을 줄이고 성능을 개선합니다.
        
        Args:
            start_date: 시작 날짜 (기본값: 2주 전)
            end_date: 종료 날짜 (기본값: 현재 시간)
            limit: 가져올 최대 개수
            progress_note_event_type_id: 특정 EventType ID로 필터링 (성능 개선을 위해 우선 적용)
            
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
            
            # API 파라미터 구성 (EventType 필터를 우선적으로 적용)
            params = {}
            
            # EventType 필터를 먼저 적용 (데이터 양을 크게 줄임)
            if progress_note_event_type_id is not None:
                params['progressNoteEventTypeId'] = progress_note_event_type_id
                logger.info(f"Applying EventType filter: ID {progress_note_event_type_id}")
            
            # 날짜 필터 적용
            params['date'] = [f'gt:{start_date_str}', f'lt:{end_date_str}']
            
            # Limit 파라미터 (None이면 제외)
            if limit is not None:
                params['limit'] = limit
            
            logger.info(f"Fetching progress notes from {self.site}")
            logger.info(f"Date range: {start_date_str} to {end_date_str}")
            logger.info(f"EventType filter: {progress_note_event_type_id}")
            logger.info(f"Limit: {limit}")
            logger.info(f"Optimized params: {params}")
            
            # API 요청 (EventType 필터가 적용된 상태로)
            logger.info(f"Making optimized API request to: {self.api_url}")
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=30  # EventType 필터로 데이터 양이 줄어들어 타임아웃 단축
            )
            
            logger.info(f"API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} progress notes from {self.site}")
                
                # 성능 개선 로그
                if progress_note_event_type_id is not None:
                    logger.info(f"Performance improvement: Fetched only {len(data)} notes with EventType filter instead of all notes")
                
                # 응답 데이터 샘플 로깅 (간소화)
                if data and len(data) > 0:
                    logger.info("Response data sample:")
                    for i, record in enumerate(data[:2]):  # 샘플 수 줄임
                        event_type = record.get('ProgressNoteEventType', {})
                        logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, EventType: {event_type.get('Description', 'N/A')}")
                else:
                    logger.info("No data returned from API")
                
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

def fetch_event_types_for_site(site: str) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    특정 사이트의 이벤트 타입 목록을 가져옵니다.
    
    Args:
        site (str): 사이트 이름
    
    Returns:
        (성공 여부, 이벤트 타입 리스트 또는 None)
    """
    try:
        from app import fetch_event_type_information
        success, event_types = fetch_event_type_information(site)
        return success, event_types
    except Exception as e:
        logger.error(f"Error fetching event types for site {site}: {str(e)}")
        return False, None

def find_resident_of_day_event_types(event_types: List[Dict[str, Any]]) -> tuple[Optional[int], Optional[int]]:
    """
    이벤트 타입 목록에서 Resident of the day 관련 이벤트 타입 ID를 찾습니다.
    
    Args:
        event_types: 이벤트 타입 목록
    
    Returns:
        (RN/EN 이벤트 타입 ID, PCA 이벤트 타입 ID)
    """
    rn_en_id = None
    pca_id = None
    
    for event_type in event_types:
        description = event_type.get('Description', '').lower()
        event_id = event_type.get('Id')
        
        if 'resident of the day' in description:
            if 'pca' in description:
                pca_id = event_id
                logger.info(f"Found PCA Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
            elif any(keyword in description for keyword in ['rn', 'en', 'nurse']):
                rn_en_id = event_id
                logger.info(f"Found RN/EN Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
    
    return rn_en_id, pca_id

def fetch_residence_of_day_notes_with_client_data(site, year, month):
    """
    특정 년월의 "Resident of the day" 노트를 클라이언트 데이터와 함께 가져옵니다.
    EventType 필터를 적용하여 데이터 양을 줄이고 성능을 개선합니다.
    
    Args:
        site (str): 사이트 이름
        year (int): 년도
        month (int): 월
    
    Returns:
        dict: Residence별 상태 정보
    """
    try:
        logger.info(f"Fetching Resident of the day notes for {site} - {year}/{month}")
        
        # 1. 클라이언트 정보 가져오기
        from api_client import fetch_client_information
        client_success, client_data = fetch_client_information(site)
        if not client_success or not client_data:
            logger.error(f"Failed to fetch client data for {site}")
            return {}
        
        # 2. 날짜 범위 설정
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # 3. 사이트별 Resident of the day 관련 EventType ID들 동적 찾기
        event_success, event_types = fetch_event_types_for_site(site)
        if not event_success or not event_types:
            logger.error(f"Failed to fetch event types for {site}")
            return {}
        
        rn_en_id, pca_id = find_resident_of_day_event_types(event_types)
        
        if not rn_en_id and not pca_id:
            logger.warning(f"No Resident of the day event types found for {site}")
            return {}
        
        # 4. 각 EventType별로 노트 가져오기 (필터링 적용)
        all_resident_notes = []
        event_type_mapping = {}  # 노트를 RN/EN과 PCA로 분류하기 위한 매핑
        
        for event_type_id, event_type_name in [(rn_en_id, "RN/EN"), (pca_id, "PCA")]:
            if event_type_id is None:
                logger.warning(f"No {event_type_name} event type found for {site}")
                continue
                
            logger.info(f"Fetching notes for EventType ID {event_type_id} ({event_type_name})")
            
            # 특정 EventType과 날짜 범위로 필터링하여 노트 가져오기
            client = ProgressNoteFetchClient(site)
            success, notes = client.fetch_progress_notes(
                start_date=start_date,
                end_date=end_date,
                limit=None,  # ROD 대시보드는 제한 없음
                progress_note_event_type_id=event_type_id  # EventType 필터 적용
            )
            
            if success and notes:
                logger.info(f"Found {len(notes)} notes for EventType ID {event_type_id} ({event_type_name})")
                all_resident_notes.extend(notes)
                
                # 노트를 타입별로 분류
                for note in notes:
                    event_type_mapping[note.get('Id')] = event_type_name
            else:
                logger.warning(f"No notes found for EventType ID {event_type_id} ({event_type_name})")
        
        logger.info(f"Total Resident of the day notes found: {len(all_resident_notes)}")
        
        # 5. Residence별로 노트 매칭 및 상태 생성
        residence_status = {}
        
        for residence in client_data:
            if isinstance(residence, dict):
                first_name = residence.get('FirstName', '')
                surname = residence.get('Surname', '')
                last_name = residence.get('LastName', '')
                preferred_name = residence.get('PreferredName', '')
                wing_name = residence.get('WingName', '')
                
                # Residence 이름 생성
                if first_name and surname:
                    residence_name = f"{first_name} {surname}"
                elif first_name and last_name:
                    residence_name = f"{first_name} {last_name}"
                elif first_name:
                    residence_name = first_name
                else:
                    continue
                
                # Residence의 ClientServiceId 찾기
                residence_client_service_id = residence.get('MainClientServiceId')
                
                if residence_name and residence_client_service_id:
                    # 해당 Residence의 노트 찾기
                    residence_notes = []
                    
                    for note in all_resident_notes:
                        note_client_service_id = note.get('ClientServiceId')
                        if note_client_service_id and note_client_service_id == residence_client_service_id:
                            residence_notes.append(note)
                    
                    logger.info(f"Found {len(residence_notes)} notes for residence: {residence_name}")
                    
                    # RN/EN과 PCA 노트 분리 (동적으로 찾은 이벤트 타입 ID 사용)
                    rn_en_notes = []
                    pca_notes = []
                    
                    for note in residence_notes:
                        note_id = note.get('Id')
                        event_type_name = event_type_mapping.get(note_id)
                        
                        if event_type_name == "RN/EN":
                            rn_en_notes.append(note)
                        elif event_type_name == "PCA":
                            pca_notes.append(note)
                    
                    # 상태 정보 생성
                    residence_status[residence_name] = {
                        'residence_name': residence_name,
                        'preferred_name': preferred_name or '',
                        'wing_name': wing_name or '',
                        'rn_en_notes': rn_en_notes,
                        'pca_notes': pca_notes,
                        'rn_en_has_note': len(rn_en_notes) > 0,
                        'pca_has_note': len(pca_notes) > 0,
                        'rn_en_count': len(rn_en_notes),
                        'pca_count': len(pca_notes),
                        'total_count': len(rn_en_notes) + len(pca_notes),
                        'rn_en_authors': [],
                        'pca_authors': []
                    }
                    
                    # RN/EN authors 추가
                    for note in rn_en_notes:
                        created_by = note.get('CreatedByUser', {})
                        if created_by:
                            first_name = created_by.get('FirstName', '')
                            last_name = created_by.get('LastName', '')
                            author_name = f"{first_name} {last_name}".strip()
                            if author_name:
                                residence_status[residence_name]['rn_en_authors'].append(author_name)
                            else:
                                residence_status[residence_name]['rn_en_authors'].append('Unknown')
                        else:
                            residence_status[residence_name]['rn_en_authors'].append('Unknown')
                    
                    # PCA authors 추가
                    for note in pca_notes:
                        created_by = note.get('CreatedByUser', {})
                        if created_by:
                            first_name = created_by.get('FirstName', '')
                            last_name = created_by.get('LastName', '')
                            author_name = f"{first_name} {last_name}".strip()
                            if author_name:
                                residence_status[residence_name]['pca_authors'].append(author_name)
                            else:
                                residence_status[residence_name]['pca_authors'].append('Unknown')
                        else:
                            residence_status[residence_name]['pca_authors'].append('Unknown')
        
        # 6. 데이터 저장 (검증용)
        save_data_to_file(site, year, month, all_resident_notes, residence_status)
        
        logger.info(f"Resident of the day status processing completed for {site} - {year}/{month}")
        logger.info(f"Performance improvement: Fetched only {len(all_resident_notes)} notes instead of all notes")
        return residence_status
        
    except Exception as e:
        logger.error(f"Error in fetch_residence_of_day_notes_with_client_data: {str(e)}")
        return {}

def save_data_to_file(site: str, year: int, month: int, all_notes: list, residence_status: dict):
    """
    받은 데이터를 JSON 파일로 저장합니다.
    
    Args:
        site (str): 사이트 이름
        year (int): 년도
        month (int): 월
        all_notes (list): 모든 Progress Note 데이터
        residence_status (dict): Residence별 상태 정보
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