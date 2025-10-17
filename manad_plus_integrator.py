#!/usr/bin/env python3
"""
MANAD Plus Integrator Module
CIMS와 MANAD Plus 시스템 간의 연동을 담당하는 모듈
"""

import requests
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import threading
from cims_policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

class MANADPlusIntegrator:
    """MANAD Plus 시스템과의 연동을 처리하는 클래스"""
    
    def __init__(self, config: Dict = None):
        """
        MANAD Plus Integrator 초기화
        
        Args:
            config: MANAD Plus API 설정 정보
        """
        # 실제 MANAD Plus API 설정 (Parafield Gardens 서버 기준)
        if config is None:
            try:
                from config import get_server_info, get_api_headers
                server_info = get_server_info('Parafield Gardens')
                api_headers = get_api_headers('Parafield Gardens')
                
                self.config = {
                    'base_url': server_info['base_url'],
                    'server_ip': server_info['server_ip'],
                    'server_port': server_info['server_port'],
                    'api_username': api_headers.get('x-api-username', 'ManadAPI'),
                    'api_key': api_headers.get('x-api-key', ''),
                    'polling_interval': 300,  # 5분마다 폴링
                    'timeout': 30
                }
                logger.info(f"MANAD Plus Integrator initialized with {server_info['base_url']}")
            except Exception as e:
                logger.error(f"Failed to load server config: {e}")
                # 폴백 설정
                self.config = {
                    'base_url': 'http://192.168.1.11:8080',
                    'server_ip': '192.168.1.11',
                    'server_port': '8080',
                    'api_username': 'ManadAPI',
                    'api_key': '',
                    'polling_interval': 300,
                    'timeout': 30
                }
        else:
            self.config = config
        
        self.access_token = None
        self.token_expires_at = None
        self.policy_engine = PolicyEngine()
        self.is_running = False
        self.polling_thread = None
        
    def authenticate(self) -> bool:
        """
        MANAD Plus API 인증 확인
        실제 MANAD API는 x-api-key 헤더 방식을 사용하므로 별도 인증 불필요
        
        Returns:
            bool: 인증 성공 여부
        """
        try:
            # MANAD Plus API는 x-api-key 헤더 방식 사용
            # /api/system/canconnect로 연결 테스트
            test_url = f"{self.config['base_url']}/api/system/canconnect"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.config.get('timeout', 30)
            )
            
            if response.status_code == 200:
                logger.info("MANAD Plus API 연결 성공")
                self.access_token = 'api_key_based_auth'  # 토큰 대신 API 키 사용
                self.token_expires_at = datetime.now() + timedelta(days=365)  # API 키는 만료 없음
                return True
            else:
                logger.error(f"MANAD Plus API 연결 실패: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning("MANAD Plus API 서버에 연결할 수 없습니다.")
            return False
        except Exception as e:
            logger.error(f"MANAD Plus 인증 오류: {str(e)}")
            return False
    
    def is_token_valid(self) -> bool:
        """
        현재 토큰이 유효한지 확인
        
        Returns:
            bool: 토큰 유효성
        """
        if not self.access_token or not self.token_expires_at:
            return False
        
        # 만료 5분 전에 갱신
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_authenticated(self) -> bool:
        """
        인증 상태 확인 및 필요시 재인증
        
        Returns:
            bool: 인증 상태
        """
        if not self.is_token_valid():
            return self.authenticate()
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """
        API 요청용 헤더 생성
        
        Returns:
            Dict: HTTP 헤더
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_last_checked_time(self, full_sync=False) -> str:
        """
        마지막 폴링 시간 조회
        
        Args:
            full_sync: 전체 동기화 여부 (True시 7일 전부터 시작)
        
        Returns:
            str: ISO 8601 형식의 마지막 체크 시간
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'manad_last_checked_at'
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result and not full_sync:
                return result[0]
            else:
                # 전체 동기화시 7일 전부터, 일반 폴링시 24시간 전부터 시작
                if full_sync:
                    default_time = datetime.now() - timedelta(days=7)
                    logger.info("Performing full sync: fetching data from last 7 days")
                else:
                    default_time = datetime.now() - timedelta(hours=24)
                    logger.info("Regular polling: fetching data from last 24 hours")
                return default_time.isoformat() + 'Z'
                
        except Exception as e:
            logger.error(f"마지막 체크 시간 조회 오류: {str(e)}")
            # 오류 시 1시간 전부터 시작
            fallback_time = datetime.now() - timedelta(hours=1)
            return fallback_time.isoformat() + 'Z'
    
    def update_last_checked_time(self, timestamp: str) -> None:
        """
        마지막 폴링 시간 업데이트
        
        Args:
            timestamp: 업데이트할 시간 (ISO 8601)
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # system_settings 테이블이 없으면 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES ('manad_last_checked_at', ?, ?)
            """, (timestamp, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"마지막 체크 시간 업데이트 오류: {str(e)}")
    
    def extract_site_from_incident(self, incident_data: Dict) -> str:
        """
        MANAD Plus 인시던트 데이터에서 사이트 정보 추출
        
        Args:
            incident_data: MANAD Plus 인시던트 데이터
            
        Returns:
            str: 사이트 이름
        """
        # MANAD Plus 데이터에서 사이트 정보 추출
        # 실제 구현에서는 MANAD Plus API 응답 구조에 맞게 수정 필요
        
        # 거주자 정보에서 사이트 추출 시도
        resident_info = self.get_resident_info(incident_data['resident_id'])
        if resident_info and 'facility_name' in resident_info:
            return resident_info['facility_name']
        
        # 인시던트 데이터에서 직접 추출 시도
        if 'facility_name' in incident_data:
            return incident_data['facility_name']
        if 'site_name' in incident_data:
            return incident_data['site_name']
        if 'location' in incident_data:
            location = incident_data['location']
            if isinstance(location, dict) and 'facility' in location:
                return location['facility']
        
        # 기본값: 거주자 ID 기반으로 사이트 할당
        # 실제 구현에서는 거주자-사이트 매핑 테이블 사용
        site_mapping = {
            'Parafield Gardens': ['RES-001', 'RES-002', 'RES-003'],
            'Nerrilda': ['RES-004', 'RES-005', 'RES-006'],
            'Ramsay': ['RES-007', 'RES-008', 'RES-009'],
            'West Park': ['RES-010', 'RES-011', 'RES-012'],
            'Yankalilla': ['RES-013', 'RES-014', 'RES-015']
        }
        
        resident_id = incident_data['resident_id']
        for site, residents in site_mapping.items():
            if resident_id in residents:
                return site
        
        # 기본값
        return 'Parafield Gardens'
    
    def get_post_fall_progress_notes_optimized(self, client_id: int, fall_date: datetime, 
                                                max_days: int = 7) -> List[Dict]:
        """
        최적화된 Post Fall Progress Notes 조회 (CIMS DB 데이터 활용)
        
        ✅ 최적화:
        - Fall Incident Progress Note 조회 건너뛰기 (1회 API 호출 절약)
        - clientId 파라미터로 API 레벨 필터링 (네트워크 트래픽 감소)
        - progressNoteEventTypeId로 Post Fall만 조회 (불필요한 데이터 제거)
        - 날짜 범위를 필요한 만큼만 조회
        
        Args:
            client_id: MANAD ClientId (CIMS DB의 resident_manad_id)
            fall_date: Fall 발생 시간 (CIMS DB의 incident_date)
            max_days: 조회 기간 (기본 7일)
            
        Returns:
            Post Fall Progress Notes 목록
        """
        try:
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            # 날짜 범위 설정 (Fall 이후 ~ max_days)
            end_date = fall_date + timedelta(days=max_days)
            start_date_str = fall_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_date_str = end_date.strftime('%Y-%m-%dT23:59:59Z')
            
            notes_url = f"{self.config['base_url']}/api/progressnote/details"
            
            # 🚀 최적화된 파라미터
            params = {
                'clientId': client_id,  # ✅ 특정 환자만 조회
                'date': [f'gt:{start_date_str}', f'lt:{end_date_str}']  # ✅ 날짜 범위
            }
            
            # 🔍 Post Fall EventType ID 조회 (캐싱 고려)
            # Note: progressNoteEventTypeId는 MANAD Plus에서 "Post Fall"의 ID를 알아야 함
            # 일반적으로 EventType은 고정되어 있으므로 config나 상수로 관리 가능
            # 예: progressNoteEventTypeId = 12 (Post Fall)
            # params['progressNoteEventTypeId'] = 12  # TODO: 실제 ID 확인 필요
            
            logger.debug(f"Querying Post Fall notes: ClientId={client_id}, Date={start_date_str} to {end_date_str}")
            
            response = requests.get(notes_url, headers=headers, params=params, timeout=self.config['timeout'])
            
            if response.status_code != 200:
                # HTTP 204 = No Content (정상, Progress Note가 없음)
                if response.status_code == 204:
                    logger.debug(f"No Progress Notes found for ClientId={client_id} (HTTP 204 - No Content)")
                    return []
                else:
                    # 실제 에러인 경우만 WARNING 레벨로 로깅
                    logger.warning(f"Failed to get progress notes for ClientId={client_id}: HTTP {response.status_code}")
                    return []
            
            all_notes = response.json()
            
            # 📊 응답 크기 로그 (모니터링)
            logger.debug(f"API returned {len(all_notes)} notes for ClientId={client_id}")
            
            # 필터링 (API에서 clientId 필터가 적용되었으므로 간소화)
            post_fall_notes = []
            
            for note in all_notes:
                if note.get('IsDeleted', False):
                    continue
                
                event_type_obj = note.get('ProgressNoteEventType', {})
                event_type_desc = event_type_obj.get('Description', '') if isinstance(event_type_obj, dict) else ''
                notes_text = note.get('NotesPlainText', '').lower()
                
                # Post Fall 또는 Daily Progress (Fall 관련)
                if 'Post Fall' in event_type_desc or (event_type_desc == 'Daily Progress' and 'fall' in notes_text):
                    note_date = datetime.fromisoformat(note.get('CreatedDate').replace('Z', ''))
                    
                    # Fall Incident 이후의 노트만
                    if note_date > fall_date:
                        post_fall_notes.append(note)
            
            # 시간순 정렬
            post_fall_notes.sort(key=lambda x: x['CreatedDate'])
            
            logger.info(f"Found {len(post_fall_notes)} Post Fall notes for ClientId={client_id}")
            
            result = {
                'fall_trigger_date': fall_date,
                'client_id': client_id,
                'post_fall_notes': post_fall_notes
            }
            
            return result
                
        except requests.exceptions.ConnectionError:
            logger.warning("MANAD Plus API 서버에 연결할 수 없습니다. Post Fall notes를 조회할 수 없습니다.")
            return []
        except Exception as e:
            logger.error(f"Error getting post fall notes (optimized): {str(e)}")
            return []
    
    def get_post_fall_progress_notes(self, fall_incident_id: str) -> List[Dict]:
        """
        MANAD Plus API에서 Post Fall Progress Notes 조회 (LEGACY)
        
        ⚠️ DEPRECATED: 최적화를 위해 get_post_fall_progress_notes_optimized() 사용 권장
        
        Args:
            fall_incident_id: Fall Incident Progress Note ID
            
        Returns:
            Post Fall Progress Notes 목록 (시간순 정렬, IsDeleted=False만)
        """
        try:
            # 1. Fall Incident Progress Note 조회 (트리거)
            fall_url = f"{self.config['base_url']}/api/progressnote/{fall_incident_id}"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            fall_response = requests.get(fall_url, headers=headers, timeout=self.config['timeout'])
            
            if fall_response.status_code != 200:
                # HTTP 204 = No Content (정상, Progress Note가 없음)
                if fall_response.status_code == 204:
                    logger.debug(f"No Progress Note found for Fall Incident {fall_incident_id} (HTTP 204 - No Content)")
                    return []
                else:
                    # 실제 에러인 경우만 ERROR 레벨로 로깅
                    logger.error(f"Failed to get Fall Incident note {fall_incident_id}: HTTP {fall_response.status_code}")
                    return []
            
            fall_note = fall_response.json()
            fall_trigger_date = datetime.fromisoformat(fall_note.get('CreatedDate').replace('Z', ''))
            client_id = fall_note.get('ClientId')
            
            logger.info(f"Fall Incident trigger: ID={fall_incident_id}, Date={fall_trigger_date}, ClientId={client_id}")
            
            # 최적화된 메서드 사용
            return self.get_post_fall_progress_notes_optimized(client_id, fall_trigger_date)
                
        except requests.exceptions.ConnectionError:
            logger.warning("MANAD Plus API 서버에 연결할 수 없습니다. Post Fall notes를 조회할 수 없습니다.")
            return []
        except Exception as e:
            logger.error(f"Error getting post fall notes: {str(e)}")
            return []
    
    def check_progress_notes(self, incident_id: str, resident_id: str) -> bool:
        """
        MANAD Plus에서 특정 인시던트에 대한 progress note 존재 여부 확인
        
        Args:
            incident_id: MANAD Plus 인시던트 ID
            resident_id: 거주자 ID
            
        Returns:
            bool: Progress note 존재 여부
        """
        if not self.ensure_authenticated():
            return False
        
        try:
            # MANAD Plus API에서 progress notes 조회
            notes_url = f"{self.config['base_url']}/incidents/{incident_id}/progress-notes"
            
            response = requests.get(
                notes_url,
                headers=self.get_headers(),
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                notes = response.json()
                # 최근 24시간 내에 작성된 follow-up note가 있는지 확인
                recent_notes = [
                    note for note in notes 
                    if self.is_recent_followup_note(note)
                ]
                
                logger.info(f"Incident {incident_id}: Found {len(recent_notes)} recent follow-up notes")
                return len(recent_notes) > 0
            else:
                logger.warning(f"Failed to check progress notes for incident {incident_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking progress notes for incident {incident_id}: {str(e)}")
            return False
    
    def is_recent_followup_note(self, note: Dict) -> bool:
        """
        Progress note가 최근 follow-up note인지 확인
        
        Args:
            note: Progress note 데이터
            
        Returns:
            bool: 최근 follow-up note 여부
        """
        try:
            # 24시간 이내인지 확인
            note_time = datetime.fromisoformat(note['created_at'].replace('Z', '+00:00'))
            now = datetime.now(note_time.tzinfo)
            time_diff = (now - note_time).total_seconds()
            
            if time_diff > 24 * 3600:  # 24시간 초과
                return False
            
            # Follow-up 관련 키워드 확인
            followup_keywords = [
                'follow-up', 'follow up', 'followup',
                'assessment', 'monitoring', 'check',
                'vital signs', 'condition', 'status'
            ]
            
            content = note.get('content', '').lower()
            note_type = note.get('type', '').lower()
            
            # 내용이나 타입에 follow-up 키워드가 있는지 확인
            for keyword in followup_keywords:
                if keyword in content or keyword in note_type:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing progress note: {str(e)}")
            return False
    
    def monitor_deadlines_and_complete_tasks(self) -> None:
        """
        마감 시점에 progress note 확인 후 자동 완료 처리
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # 마감 시점이 지난 미완료 태스크 조회
            now = datetime.now()
            cursor.execute("""
                SELECT t.id, t.task_name, t.due_date, t.assigned_user_id,
                       i.manad_incident_id, i.resident_id, i.resident_name
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status IN ('Open', 'In Progress') 
                AND t.due_date <= ?
                AND i.manad_incident_id IS NOT NULL
            """, (now.isoformat(),))
            
            overdue_tasks = cursor.fetchall()
            logger.info(f"Found {len(overdue_tasks)} overdue tasks to check")
            
            for task in overdue_tasks:
                task_id, task_name, due_date, assigned_user_id, manad_incident_id, resident_id, resident_name = task
                
                # MANAD Plus에서 progress note 확인
                has_progress_note = self.check_progress_notes(manad_incident_id, resident_id)
                
                if has_progress_note:
                    # Progress note가 있으면 태스크 자동 완료
                    cursor.execute("""
                        UPDATE cims_tasks 
                        SET status = 'Completed', 
                            completed_at = ?,
                            completion_method = 'auto_manad_check'
                        WHERE id = ?
                    """, (now.isoformat(), task_id))
                    
                    # 감사 로그 생성
                    cursor.execute("""
                        INSERT INTO cims_audit_logs (
                            log_id, user_id, action, target_entity_type, target_entity_id, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"LOG-{now.strftime('%Y%m%d%H%M%S')}",
                        'MANAD_INTEGRATOR',
                        'task_auto_completed',
                        'task',
                        task_id,
                        json.dumps({
                            'manad_incident_id': manad_incident_id,
                            'resident_name': resident_name,
                            'reason': 'progress_note_found_in_manad',
                            'completed_at': now.isoformat()
                        })
                    ))
                    
                    logger.info(f"Task {task_id} auto-completed due to progress note found in MANAD Plus")
                else:
                    logger.info(f"Task {task_id} remains incomplete - no progress note found in MANAD Plus")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error monitoring deadlines: {str(e)}")
    
    def validate_pending_tasks(self) -> None:
        """
        Pending 상태 태스크의 주기적 검증 및 완료 처리
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # Pending 상태 태스크 조회
            cursor.execute("""
                SELECT t.id, t.task_name, t.pending_confirmation_at,
                       i.manad_incident_id, i.resident_id, i.resident_name
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status = 'Pending' 
                AND i.manad_incident_id IS NOT NULL
                AND t.pending_confirmation_at IS NOT NULL
            """)
            
            pending_tasks = cursor.fetchall()
            logger.info(f"Found {len(pending_tasks)} pending tasks to validate")
            
            for task in pending_tasks:
                task_id, task_name, pending_confirmation_at, manad_incident_id, resident_id, resident_name = task
                
                # MANAD Plus에서 progress note 확인
                has_progress_note = self.check_progress_notes(manad_incident_id, resident_id)
                
                if has_progress_note:
                    # Progress note가 확인되면 태스크 완료 처리
                    now = datetime.now()
                    cursor.execute("""
                        UPDATE cims_tasks 
                        SET status = 'Completed', 
                            completed_at = ?,
                            completion_method = 'auto_manad_validation'
                        WHERE id = ?
                    """, (now.isoformat(), task_id))
                    
                    # 감사 로그 생성
                    cursor.execute("""
                        INSERT INTO cims_audit_logs (
                            log_id, user_id, action, target_entity_type, target_entity_id, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"LOG-{now.strftime('%Y%m%d%H%M%S')}",
                        'MANAD_INTEGRATOR',
                        'task_validated_and_completed',
                        'task',
                        task_id,
                        json.dumps({
                            'manad_incident_id': manad_incident_id,
                            'resident_name': resident_name,
                            'reason': 'progress_note_validated_in_manad',
                            'completed_at': now.isoformat(),
                            'pending_confirmation_at': pending_confirmation_at
                        })
                    ))
                    
                    logger.info(f"Task {task_id} validated and completed due to progress note found in MANAD Plus")
                else:
                    # Progress note가 없으면 Pending 상태 유지
                    logger.info(f"Task {task_id} remains pending - no progress note found in MANAD Plus")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error validating pending tasks: {str(e)}")
    
    def poll_incidents(self, full_sync=False) -> List[Dict]:
        """
        MANAD Plus에서 새로운 사고 기록 폴링 (모의 데이터용)
        
        Args:
            full_sync: 전체 동기화 여부 (True시 7일 전부터 데이터 가져옴)
        
        Returns:
            List[Dict]: 새로운 사고 기록 목록
        """
        if not self.ensure_authenticated():
            logger.error("MANAD Plus 인증 실패로 폴링 중단")
            return []
        
        try:
            last_checked = self.get_last_checked_time(full_sync)
            incidents_url = f"{self.config['base_url']}/incidents/latest"
            
            params = {
                'last_checked_at': last_checked,
                'limit': 500 if full_sync else 100  # 전체 동기화시 더 많은 데이터 가져옴
            }
            
            try:
                response = requests.get(
                    incidents_url,
                    headers=self.get_headers(),
                    params=params,
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    incidents = response.json()
                    if full_sync:
                        logger.info(f"MANAD Plus 전체 동기화: {len(incidents)}개의 사고 기록 조회")
                    else:
                        logger.info(f"MANAD Plus에서 {len(incidents)}개의 사고 기록 조회")
                    
                    # 마지막 체크 시간 업데이트
                    if incidents:
                        latest_time = max(incident['last_updated_at'] for incident in incidents)
                        self.update_last_checked_time(latest_time)
                    else:
                        # 새로운 사고가 없어도 현재 시간으로 업데이트
                        self.update_last_checked_time(datetime.now().isoformat() + 'Z')
                    
                    return incidents
                else:
                    logger.error(f"MANAD Plus 사고 폴링 실패: {response.status_code} - {response.text}")
                    return []
                    
            except requests.exceptions.ConnectionError:
                # 실제 API가 없는 경우 - 새 데이터 없음
                logger.warning("MANAD Plus API 서버에 연결할 수 없습니다. 새로운 인시던트를 가져올 수 없습니다.")
                return []
                
        except Exception as e:
            logger.error(f"MANAD Plus 사고 폴링 오류: {str(e)}")
            return []
    
    def get_resident_info(self, resident_id: str) -> Optional[Dict]:
        """
        거주자 정보 조회
        
        Args:
            resident_id: 거주자 ID
            
        Returns:
            Dict: 거주자 정보 또는 None
        """
        if not self.ensure_authenticated():
            return None
        
        try:
            resident_url = f"{self.config['base_url']}/residents/{resident_id}"
            
            try:
                response = requests.get(
                    resident_url,
                    headers=self.get_headers(),
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"거주자 정보 조회 실패 ({resident_id}): {response.status_code}")
                    return None
                    
            except requests.exceptions.ConnectionError:
                # 실제 API가 없는 경우 - 기본 정보 반환
                logger.warning(f"MANAD Plus API 서버에 연결할 수 없습니다. 거주자 기본 정보를 사용합니다. ({resident_id})")
                return {
                    'resident_id': resident_id,
                    'full_name': f"Resident {resident_id}",
                    'facility_name': 'Unknown'
                }
                
        except Exception as e:
            logger.error(f"거주자 정보 조회 오류 ({resident_id}): {str(e)}")
            return None
    
    def process_incident(self, incident_data: Dict) -> bool:
        """
        MANAD Plus에서 받은 사고 데이터를 CIMS에서 처리
        
        Args:
            incident_data: MANAD Plus 사고 데이터
            
        Returns:
            bool: 처리 성공 여부
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # 거주자 정보 조회
                resident_info = self.get_resident_info(incident_data['resident_id'])
                resident_name = resident_info['full_name'] if resident_info else f"Resident {incident_data['resident_id']}"
                
                # 사이트 정보 추출 (MANAD Plus 데이터에서)
                site_name = self.extract_site_from_incident(incident_data)
                
                # CIMS 사고 데이터 생성 (WAL 모드 사용)
                conn = sqlite3.connect('progress_report.db')
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                cursor = conn.cursor()
                
                # 중복 체크 (MANAD incident ID 기준)
                cursor.execute("""
                    SELECT id FROM cims_incidents 
                    WHERE manad_incident_id = ?
                """, (incident_data['manad_incident_id'],))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"사고 {incident_data['manad_incident_id']} 이미 처리됨")
                    conn.close()
                    return True
                
                # 새 사고 생성
                incident_id = f"I-{incident_data['manad_incident_id']}"
                
                cursor.execute("""
                    INSERT INTO cims_incidents (
                        incident_id, manad_incident_id, resident_id, resident_name,
                        incident_type, severity, status, incident_date, 
                        description, reported_by, site, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident_id,
                    incident_data['manad_incident_id'],
                    incident_data['resident_id'],
                    resident_name,
                    incident_data['incident_type'],
                    incident_data['incident_severity_code'],
                    'Open',
                    incident_data['incident_time'],
                    f"Incident imported from MANAD Plus: {incident_data['incident_type']}",
                    'MANAD_PLUS_SYSTEM',
                    site_name,
                    datetime.now().isoformat()
                ))
                
                incident_db_id = cursor.lastrowid
                conn.commit()
                
                # 정책 엔진 트리거
                cims_incident_data = {
                    'id': incident_db_id,
                    'incident_id': incident_id,
                    'type': incident_data['incident_type'],
                    'severity': incident_data['incident_severity_code'],
                    'incident_date': incident_data['incident_time'],
                    'resident_id': incident_data['resident_id'],
                    'resident_name': resident_name,
                    'manad_incident_id': incident_data['manad_incident_id']
                }
                
                generated_tasks = self.policy_engine.apply_policies_to_incident(cims_incident_data)
                
                # 감사 로그 (고유한 로그 ID 생성)
                log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{incident_db_id}"
                cursor.execute("""
                    INSERT INTO cims_audit_logs (
                        log_id, user_id, action, target_entity_type, target_entity_id, details
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    log_id,
                    'MANAD_INTEGRATOR',
                    'incident_imported',
                    'incident',
                    incident_db_id,
                    json.dumps({
                        'manad_incident_id': incident_data['manad_incident_id'],
                        'incident_type': incident_data['incident_type'],
                        'severity': incident_data['incident_severity_code'],
                        'tasks_generated': len(generated_tasks)
                    })
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"사고 {incident_data['manad_incident_id']} 처리 완료, {len(generated_tasks)}개 태스크 생성")
                return True
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"데이터베이스 락 발생, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                    continue
                else:
                    logger.error(f"사고 처리 오류 ({incident_data.get('manad_incident_id', 'Unknown')}): {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"사고 처리 오류 ({incident_data.get('manad_incident_id', 'Unknown')}): {str(e)}")
                return False
        
        return False
    
    def polling_loop(self) -> None:
        """
        주기적 폴링 루프
        """
        logger.info("MANAD Plus 폴링 시작")
        
        while self.is_running:
            try:
                # 새로운 사고 폴링
                incidents = self.poll_incidents()
                
                # 각 사고 처리
                for incident in incidents:
                    self.process_incident(incident)
                
                # 마감 시점 모니터링 및 자동 완료 처리
                self.monitor_deadlines_and_complete_tasks()
                
                # Pending 상태 태스크 주기적 검증
                self.validate_pending_tasks()
                
                # 다음 폴링까지 대기
                time.sleep(self.config['polling_interval'])
                
            except Exception as e:
                logger.error(f"폴링 루프 오류: {str(e)}")
                time.sleep(30)  # 오류 시 30초 대기 후 재시도
    
    def start_polling(self) -> bool:
        """
        폴링 서비스 시작
        
        Returns:
            bool: 시작 성공 여부
        """
        if self.is_running:
            logger.warning("폴링이 이미 실행 중입니다")
            return False
        
        if not self.ensure_authenticated():
            logger.error("인증 실패로 폴링을 시작할 수 없습니다")
            return False
        
        self.is_running = True
        self.polling_thread = threading.Thread(target=self.polling_loop, daemon=False)
        self.polling_thread.start()
        
        logger.info("MANAD Plus 폴링 서비스 시작됨")
        return True
    
    def stop_polling(self) -> None:
        """
        폴링 서비스 중지
        """
        self.is_running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        logger.info("MANAD Plus 폴링 서비스 중지됨")
    
    def get_status(self) -> Dict:
        """
        통합 서비스 상태 조회
        
        Returns:
            Dict: 서비스 상태 정보
        """
        # API 연결 상태 확인 (Parafield Gardens 서버 기준)
        api_connected = False
        connection_error = None
        
        try:
            # MANAD API 연결 테스트 엔드포인트 사용
            test_url = f"{self.config['base_url']}/api/system/canconnect"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            test_response = requests.get(
                test_url,
                headers=headers,
                timeout=5
            )
            
            # 200-299 범위의 상태 코드면 연결됨
            if 200 <= test_response.status_code < 300:
                api_connected = True
                logger.info(f"MANAD Plus 서버 연결 성공: {test_url}")
            elif test_response.status_code == 401:
                api_connected = True  # 인증 오류지만 서버는 응답함
                connection_error = "인증 필요 (서버는 온라인)"
            elif test_response.status_code < 500:
                api_connected = True  # 클라이언트 오류지만 서버는 응답함
                connection_error = f"HTTP {test_response.status_code}"
            else:
                connection_error = f"서버 오류: HTTP {test_response.status_code}"
                
        except requests.exceptions.ConnectionError:
            connection_error = f"MANAD Plus 서버({self.config['server_ip']})에 연결할 수 없습니다"
        except requests.exceptions.Timeout:
            connection_error = "MANAD Plus 서버 응답 시간 초과"
        except Exception as e:
            connection_error = f"알 수 없는 오류: {str(e)}"
        
        return {
            'is_running': self.is_running,
            'is_authenticated': self.is_token_valid(),
            'api_connected': api_connected,
            'connection_error': connection_error,
            'last_checked': self.get_last_checked_time(),
            'config': {
                'base_url': self.config['base_url'],
                'server_ip': self.config.get('server_ip', 'Unknown'),
                'polling_interval': self.config['polling_interval']
            }
        }

# 전역 인스턴스
manad_integrator = MANADPlusIntegrator()

def get_manad_integrator() -> MANADPlusIntegrator:
    """
    MANAD Plus Integrator 인스턴스 반환
    
    Returns:
        MANADPlusIntegrator: 통합 서비스 인스턴스
    """
    return manad_integrator
