#!/usr/bin/env python3
"""
Unified Data Sync Manager - 통합 데이터 동기화 매니저
매일 새벽 3시에 모든 데이터를 동기화하는 시스템
"""

import sqlite3
import json
import os
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 필요한 함수들을 직접 import (순환 import 방지)
try:
    from api_client import get_api_client, fetch_client_information
    from config import SITE_SERVERS
except ImportError as e:
    print(f"Warning: 일부 모듈을 찾을 수 없습니다: {e}")
    SITE_SERVERS = {}

# 선택적 import (실패해도 계속 진행)
try:
    from api_carearea import APICareArea
except ImportError:
    APICareArea = None

try:
    from api_eventtype import APIEventType
except ImportError:
    APIEventType = None

try:
    from api_incident import fetch_incidents_with_client_data
except ImportError:
    fetch_incidents_with_client_data = None

logger = logging.getLogger(__name__)

class UnifiedDataSyncManager:
    """통합 데이터 동기화 매니저"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        self.sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        # 데이터베이스 존재 확인
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def get_db_connection(self):
        """데이터베이스 연결"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def update_sync_status(self, data_type: str, site: Optional[str] = None, 
                          status: str = 'success', records: int = 0, error: str = None):
        """동기화 상태 업데이트"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 타임아웃 설정
            cursor.execute('PRAGMA busy_timeout = 30000')  # 30초 타임아웃
            
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status 
                (data_type, site, last_sync_time, sync_status, records_synced, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data_type, site, datetime.now().isoformat(), status, records, error))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"동기화 상태 업데이트 실패: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def sync_clients_data(self) -> Dict[str, Any]:
        """클라이언트 데이터 동기화"""
        logger.info("🔄 클라이언트 데이터 동기화 시작")
        results = {'success': 0, 'failed': 0, 'total_changes': {'added': 0, 'updated': 0, 'removed': 0}}
        
        for site in self.sites:
            try:
                logger.info(f"  📍 {site} 클라이언트 동기화 중...")
                
                # API에서 최신 데이터 가져오기
                api_success, latest_clients = fetch_client_information(site)
                
                if not api_success:
                    logger.error(f"  ❌ {site} API에서 데이터를 가져올 수 없습니다")
                    self.update_sync_status('clients', site, 'failed', 0, 'API 호출 실패')
                    results['failed'] += 1
                    continue
                
                # SQLite 캐시 업데이트
                changes = self._update_clients_cache(site, latest_clients)
                results['total_changes']['added'] += changes['added']
                results['total_changes']['updated'] += changes['updated']
                results['total_changes']['removed'] += changes['removed']
                
                self.update_sync_status('clients', site, 'success', len(latest_clients))
                results['success'] += 1
                
                logger.info(f"  ✅ {site} 완료: 신규 {changes['added']}명, 업데이트 {changes['updated']}명, 제거 {changes['removed']}명")
                
            except Exception as e:
                logger.error(f"  ❌ {site} 클라이언트 동기화 실패: {e}")
                self.update_sync_status('clients', site, 'failed', 0, str(e))
                results['failed'] += 1
        
        logger.info(f"🔄 클라이언트 데이터 동기화 완료: {results['success']}/{len(self.sites)} 사이트 성공")
        return results
    
    def sync_care_areas_data(self) -> Dict[str, Any]:
        """케어 영역 데이터 동기화"""
        logger.info("🔄 케어 영역 데이터 동기화 시작")
        
        if APICareArea is None:
            logger.warning("⚠️ APICareArea 모듈을 찾을 수 없습니다. 케어 영역 동기화를 건너뜁니다.")
            return {'success': False, 'message': 'APICareArea 모듈 없음'}
        
        try:
            # API에서 케어 영역 데이터 가져오기 (첫 번째 사이트 사용)
            api_carearea = APICareArea(self.sites[0])  # Parafield Gardens 사용
            care_areas = api_carearea.get_care_area_information()
            
            if not care_areas:
                logger.error("❌ 케어 영역 API에서 데이터를 가져올 수 없습니다")
                self.update_sync_status('carearea', None, 'failed', 0, 'API 호출 실패')
                return {'success': False, 'message': 'API 호출 실패'}
            
            # SQLite 캐시 업데이트
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            for area in care_areas:
                cursor.execute('''
                    INSERT OR REPLACE INTO care_areas 
                    (id, description, is_archived, is_external, last_updated_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    area['Id'],
                    area['Description'],
                    area.get('IsArchived', False),
                    area.get('IsExternal', False),
                    area.get('LastUpdatedDate')
                ))
            
            conn.commit()
            conn.close()
            
            self.update_sync_status('carearea', None, 'success', len(care_areas))
            logger.info(f"✅ 케어 영역 동기화 완료: {len(care_areas)}개")
            
            return {'success': True, 'records': len(care_areas)}
            
        except Exception as e:
            logger.error(f"❌ 케어 영역 동기화 실패: {e}")
            self.update_sync_status('carearea', None, 'failed', 0, str(e))
            return {'success': False, 'message': str(e)}
    
    def sync_event_types_data(self) -> Dict[str, Any]:
        """이벤트 타입 데이터 동기화"""
        logger.info("🔄 이벤트 타입 데이터 동기화 시작")
        
        if APIEventType is None:
            logger.warning("⚠️ APIEventType 모듈을 찾을 수 없습니다. 이벤트 타입 동기화를 건너뜁니다.")
            return {'success': False, 'message': 'APIEventType 모듈 없음'}
        
        try:
            # API에서 이벤트 타입 데이터 가져오기 (첫 번째 사이트 사용)
            api_eventtype = APIEventType(self.sites[0])  # Parafield Gardens 사용
            event_types = api_eventtype.get_event_type_information()
            
            if not event_types:
                logger.error("❌ 이벤트 타입 API에서 데이터를 가져올 수 없습니다")
                self.update_sync_status('eventtype', None, 'failed', 0, 'API 호출 실패')
                return {'success': False, 'message': 'API 호출 실패'}
            
            # SQLite 캐시 업데이트
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            for event_type in event_types:
                cursor.execute('''
                    INSERT OR REPLACE INTO event_types 
                    (id, description, color_argb, is_archived, is_external, last_updated_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_type['Id'],
                    event_type['Description'],
                    event_type.get('ColorArgb'),
                    event_type.get('IsArchived', False),
                    event_type.get('IsExternal', False),
                    event_type.get('LastUpdatedDate')
                ))
            
            conn.commit()
            conn.close()
            
            self.update_sync_status('eventtype', None, 'success', len(event_types))
            logger.info(f"✅ 이벤트 타입 동기화 완료: {len(event_types)}개")
            
            return {'success': True, 'records': len(event_types)}
            
        except Exception as e:
            logger.error(f"❌ 이벤트 타입 동기화 실패: {e}")
            self.update_sync_status('eventtype', None, 'failed', 0, str(e))
            return {'success': False, 'message': str(e)}
    
    def sync_incidents_data(self) -> Dict[str, Any]:
        """인시던트 데이터 동기화"""
        logger.info("🔄 인시던트 데이터 동기화 시작")
        results = {'success': 0, 'failed': 0, 'total_incidents': 0}
        
        if fetch_incidents_with_client_data is None:
            logger.warning("⚠️ fetch_incidents_with_client_data 함수를 찾을 수 없습니다. 인시던트 동기화를 건너뜁니다.")
            return {'success': False, 'message': 'fetch_incidents_with_client_data 함수 없음'}
        
        # 최근 30일간의 인시던트 데이터 동기화
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for site in self.sites:
            try:
                logger.info(f"  📍 {site} 인시던트 동기화 중...")
                
                # API에서 인시던트 데이터 가져오기
                incident_data = fetch_incidents_with_client_data(
                    site, 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not incident_data or 'incidents' not in incident_data:
                    logger.error(f"  ❌ {site} 인시던트 데이터를 가져올 수 없습니다")
                    self.update_sync_status('incidents', site, 'failed', 0, 'API 호출 실패')
                    results['failed'] += 1
                    continue
                
                incidents = incident_data['incidents']
                
                # SQLite 캐시 업데이트
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                try:
                    # 타임아웃 설정
                    cursor.execute('PRAGMA busy_timeout = 30000')  # 30초 타임아웃
                    
                    for incident in incidents:
                        # incident_id가 없으면 건너뛰기
                        incident_id = incident.get('IncidentId') or incident.get('Id') or incident.get('incident_id')
                        if not incident_id:
                            logger.warning(f"  ⚠️ {site} 인시던트 ID가 없어서 건너뜀: {incident}")
                            continue
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO incidents_cache 
                            (incident_id, client_id, client_name, incident_type, incident_date, 
                             description, severity, status, site, reported_by, last_synced)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            str(incident_id),  # 문자열로 변환
                            incident.get('ClientId'),
                            incident.get('ClientName'),
                            incident.get('IncidentType'),
                            incident.get('IncidentDate'),
                            incident.get('Description'),
                            incident.get('Severity'),
                            incident.get('Status'),
                            site,
                            incident.get('ReportedBy'),
                            datetime.now().isoformat()
                        ))
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()
                
                self.update_sync_status('incidents', site, 'success', len(incidents))
                results['success'] += 1
                results['total_incidents'] += len(incidents)
                
                logger.info(f"  ✅ {site} 완료: {len(incidents)}개 인시던트")
                
            except Exception as e:
                logger.error(f"  ❌ {site} 인시던트 동기화 실패: {e}")
                self.update_sync_status('incidents', site, 'failed', 0, str(e))
                results['failed'] += 1
        
        logger.info(f"🔄 인시던트 데이터 동기화 완료: {results['success']}/{len(self.sites)} 사이트 성공, 총 {results['total_incidents']}개")
        return results
    
    def _update_clients_cache(self, site: str, latest_clients: List[Dict]) -> Dict[str, int]:
        """SQLite 클라이언트 캐시 업데이트"""
        changes = {'added': 0, 'updated': 0, 'removed': 0, 'total': len(latest_clients)}
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 기존 클라이언트 목록 가져오기
            cursor.execute('''
                SELECT person_id, client_name, room_number, last_synced 
                FROM clients_cache 
                WHERE site = ? AND is_active = 1
            ''', (site,))
            
            existing_clients = {row['person_id']: dict(row) for row in cursor.fetchall()}
            
            # 새 클라이언트 처리
            current_person_ids = set()
            
            for client in latest_clients:
                person_id = (client.get('PersonId') or 
                           client.get('MainClientServiceId') or 
                           client.get('ClientRecordId'))
                
                if not person_id:
                    continue
                
                current_person_ids.add(person_id)
                
                client_name = (client.get('ClientName') or 
                             f"{client.get('FirstName', '')} {client.get('Surname', '')}".strip() or
                             client.get('PreferredName', 'Unknown'))
                
                if person_id in existing_clients:
                    # 기존 클라이언트 업데이트
                    cursor.execute('''
                        UPDATE clients_cache 
                        SET client_name = ?, preferred_name = ?, title = ?, first_name = ?,
                            middle_name = ?, surname = ?, gender = ?, birth_date = ?,
                            admission_date = ?, room_name = ?, room_number = ?, wing_name = ?,
                            location_id = ?, location_name = ?, main_client_service_id = ?,
                            original_person_id = ?, client_record_id = ?, last_synced = ?
                        WHERE person_id = ? AND site = ?
                    ''', (
                        client_name,
                        client.get('PreferredName'),
                        client.get('Title'),
                        client.get('FirstName'),
                        client.get('MiddleName'),
                        client.get('Surname') or client.get('LastName'),
                        client.get('Gender') or client.get('GenderDesc'),
                        client.get('BirthDate'),
                        client.get('AdmissionDate'),
                        client.get('RoomName'),
                        client.get('RoomNumber'),
                        client.get('WingName'),
                        client.get('LocationId'),
                        client.get('LocationName'),
                        client.get('MainClientServiceId'),
                        client.get('OriginalPersonId'),
                        client.get('ClientRecordId'),
                        datetime.now().isoformat(),
                        person_id,
                        site
                    ))
                    changes['updated'] += 1
                else:
                    # 새 클라이언트 추가
                    cursor.execute('''
                        INSERT INTO clients_cache 
                        (person_id, client_name, preferred_name, title, first_name, 
                         middle_name, surname, gender, birth_date, admission_date,
                         room_name, room_number, wing_name, location_id, location_name,
                         main_client_service_id, original_person_id, client_record_id, 
                         site, last_synced, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        person_id,
                        client_name,
                        client.get('PreferredName'),
                        client.get('Title'),
                        client.get('FirstName'),
                        client.get('MiddleName'),
                        client.get('Surname') or client.get('LastName'),
                        client.get('Gender') or client.get('GenderDesc'),
                        client.get('BirthDate'),
                        client.get('AdmissionDate'),
                        client.get('RoomName'),
                        client.get('RoomNumber'),
                        client.get('WingName'),
                        client.get('LocationId'),
                        client.get('LocationName'),
                        client.get('MainClientServiceId'),
                        client.get('OriginalPersonId'),
                        client.get('ClientRecordId'),
                        site,
                        datetime.now().isoformat(),
                        True
                    ))
                    changes['added'] += 1
            
            # 제거된 클라이언트 처리 (비활성화)
            removed_person_ids = set(existing_clients.keys()) - current_person_ids
            for person_id in removed_person_ids:
                cursor.execute('''
                    UPDATE clients_cache 
                    SET is_active = 0, last_synced = ?
                    WHERE person_id = ? AND site = ?
                ''', (datetime.now().isoformat(), person_id, site))
                changes['removed'] += 1
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
        return changes
    
    def run_full_sync(self) -> Dict[str, Any]:
        """전체 데이터 동기화 실행"""
        logger.info("🌅 매일 새벽 3시 통합 데이터 동기화 시작")
        start_time = datetime.now()
        
        results = {
            'start_time': start_time.isoformat(),
            'clients': {},
            'care_areas': {},
            'event_types': {},
            'incidents': {},
            'summary': {
                'total_success': 0,
                'total_failed': 0,
                'total_records': 0
            }
        }
        
        try:
            # 1. 클라이언트 데이터 동기화
            results['clients'] = self.sync_clients_data()
            results['summary']['total_success'] += results['clients']['success']
            results['summary']['total_failed'] += results['clients']['failed']
            results['summary']['total_records'] += sum(results['clients']['total_changes'].values())
            
            # 2. 케어 영역 데이터 동기화
            results['care_areas'] = self.sync_care_areas_data()
            if results['care_areas']['success']:
                results['summary']['total_success'] += 1
                results['summary']['total_records'] += results['care_areas']['records']
            else:
                results['summary']['total_failed'] += 1
            
            # 3. 이벤트 타입 데이터 동기화
            results['event_types'] = self.sync_event_types_data()
            if results['event_types']['success']:
                results['summary']['total_success'] += 1
                results['summary']['total_records'] += results['event_types']['records']
            else:
                results['summary']['total_failed'] += 1
            
            # 4. 인시던트 데이터 동기화
            results['incidents'] = self.sync_incidents_data()
            results['summary']['total_success'] += results['incidents']['success']
            results['summary']['total_failed'] += results['incidents']['failed']
            results['summary']['total_records'] += results['incidents']['total_incidents']
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = duration
            
            logger.info(f"🌅 통합 데이터 동기화 완료: {duration:.1f}초")
            logger.info(f"📊 결과: 성공 {results['summary']['total_success']}개, 실패 {results['summary']['total_failed']}개, 총 {results['summary']['total_records']}개 레코드")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 통합 데이터 동기화 실패: {e}")
            results['error'] = str(e)
            return results
    
    def start_daily_sync(self):
        """매일 새벽 3시 동기화 스케줄러 시작"""
        def daily_sync_job():
            """매일 새벽 3시 동기화 작업"""
            logger.info("🌅 매일 새벽 3시 통합 데이터 동기화 시작")
            results = self.run_full_sync()
            
            # 결과 로깅
            if 'error' in results:
                logger.error(f"❌ 동기화 실패: {results['error']}")
            else:
                logger.info(f"✅ 동기화 완료: {results['summary']['total_records']}개 레코드 처리")
        
        # 스케줄 설정 - 매일 새벽 3시
        schedule.every().day.at("03:00").do(daily_sync_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 스케줄 확인
        
        # 백그라운드 스레드로 실행
        sync_thread = threading.Thread(target=run_scheduler, daemon=True)
        sync_thread.start()
        
        logger.info("🌅 매일 새벽 3시 통합 데이터 동기화 스케줄러 시작됨")


# Flask 앱에서 사용할 전역 인스턴스
unified_sync_manager = None

def get_unified_sync_manager():
    """통합 데이터 동기화 매니저 싱글톤 인스턴스"""
    global unified_sync_manager
    if unified_sync_manager is None:
        unified_sync_manager = UnifiedDataSyncManager()
    return unified_sync_manager

def init_unified_sync():
    """Flask 앱 초기화 시 호출"""
    try:
        manager = get_unified_sync_manager()
        manager.start_daily_sync()
        logger.info("✅ 통합 데이터 동기화 매니저 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 통합 데이터 동기화 매니저 초기화 실패: {e}")
        return False


# 명령줄에서 직접 실행 시 테스트
if __name__ == "__main__":
    print("🌅 통합 데이터 동기화 매니저 테스트")
    
    try:
        manager = UnifiedDataSyncManager()
        
        # 수동으로 전체 동기화 실행
        print("\n🔄 전체 데이터 동기화 실행 중...")
        results = manager.run_full_sync()
        
        print(f"\n📊 동기화 결과:")
        print(f"  - 클라이언트: {results['clients']['success']}/{len(manager.sites)} 사이트 성공")
        print(f"  - 케어 영역: {'성공' if results['care_areas']['success'] else '실패'}")
        print(f"  - 이벤트 타입: {'성공' if results['event_types']['success'] else '실패'}")
        print(f"  - 인시던트: {results['incidents']['success']}/{len(manager.sites)} 사이트 성공")
        print(f"  - 총 레코드: {results['summary']['total_records']}개")
        print(f"  - 소요 시간: {results.get('duration_seconds', 0):.1f}초")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

def init_unifiedd_sync():
    """통합 데이터 동기화 초기화 함수"""
    try:
        manager = UnifiedDataSyncManager()
        manager.start_background_sync()
        logger.info("✅ 통합 데이터 동기화 매니저 초기화 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 통합 데이터 동기화 매니저 초기화 실패: {e}")
        return False
