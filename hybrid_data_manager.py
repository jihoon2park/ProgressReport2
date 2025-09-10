#!/usr/bin/env python3
"""
Progress Report System - 하이브리드 데이터 관리자
DB와 JSON을 효율적으로 조합하여 데이터 관리
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class HybridDataManager:
    """DB와 JSON을 조합한 하이브리드 데이터 관리자"""
    
    def __init__(self, db_path: str = 'progress_report.db', data_dir: str = 'data'):
        self.db_path = db_path
        self.data_dir = data_dir
        self.cache_expiry = {
            'clients': timedelta(hours=6),      # 클라이언트 정보: 6시간
            'carearea': timedelta(days=7),      # 케어 영역: 7일
            'eventtype': timedelta(days=7),     # 이벤트 타입: 7일
            'incidents': timedelta(hours=1),    # 인시던트: 1시간
        }
    
    @contextmanager
    def get_db_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ===========================================
    # 스마트 캐시 관리
    # ===========================================
    
    def is_cache_valid(self, data_type: str, site: Optional[str] = None) -> bool:
        """캐시 유효성 검사"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_sync_time FROM sync_status 
                WHERE data_type = ? AND (site = ? OR site IS NULL)
                ORDER BY last_sync_time DESC LIMIT 1
            ''', (data_type, site))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            last_sync = datetime.fromisoformat(result['last_sync_time'])
            expiry_time = self.cache_expiry.get(data_type, timedelta(hours=1))
            
            return datetime.now() - last_sync < expiry_time
    
    def update_sync_status(self, data_type: str, site: Optional[str] = None, 
                          status: str = 'success', records: int = 0, error: str = None):
        """동기화 상태 업데이트"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status 
                (data_type, site, last_sync_time, sync_status, records_synced, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data_type, site, datetime.now().isoformat(), status, records, error))
            
            conn.commit()
    
    # ===========================================
    # 클라이언트 데이터 관리 (Tier 2)
    # ===========================================
    
    async def get_clients(self, site: str, force_refresh: bool = False) -> List[Dict]:
        """클라이언트 데이터 조회 (DB 캐시 우선, API 동기화)"""
        
        # 1. 캐시 유효성 확인
        if not force_refresh and self.is_cache_valid('clients', site):
            logger.info(f"{site} 클라이언트 데이터: DB 캐시 사용")
            return self._get_clients_from_db(site)
        
        # 2. API에서 최신 데이터 시도
        try:
            logger.info(f"{site} 클라이언트 데이터: API에서 동기화 시도")
            clients = await self._fetch_clients_from_api(site)
            
            # 3. DB 캐시 업데이트
            self._update_clients_cache(site, clients)
            
            # 4. JSON 백업 저장
            self._save_clients_json_backup(site, clients)
            
            self.update_sync_status('clients', site, 'success', len(clients))
            return clients
            
        except Exception as e:
            logger.warning(f"{site} API 동기화 실패: {e}")
            
            # 5. API 실패시 DB 캐시 사용
            cached_clients = self._get_clients_from_db(site)
            if cached_clients:
                logger.info(f"{site} 클라이언트 데이터: DB 캐시 사용 (API 실패)")
                self.update_sync_status('clients', site, 'failed', 0, str(e))
                return cached_clients
            
            # 6. DB도 없으면 JSON 백업 사용
            return self._get_clients_from_json(site)
    
    def _get_clients_from_db(self, site: str) -> List[Dict]:
        """DB에서 클라이언트 데이터 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM clients_cache 
                WHERE site = ? AND is_active = 1
                ORDER BY client_name
            ''', (site,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _update_clients_cache(self, site: str, clients: List[Dict]):
        """DB 클라이언트 캐시 업데이트"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 기존 데이터 비활성화
            cursor.execute('UPDATE clients_cache SET is_active = 0 WHERE site = ?', (site,))
            
            # 새 데이터 삽입
            for client in clients:
                cursor.execute('''
                    INSERT OR REPLACE INTO clients_cache 
                    (person_id, client_name, preferred_name, room_number, site, 
                     last_synced, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client.get('PersonId'),
                    client.get('ClientName'),
                    client.get('PreferredName'),
                    client.get('RoomNumber'),
                    site,
                    datetime.now().isoformat(),
                    1
                ))
            
            conn.commit()
    
    async def _fetch_clients_from_api(self, site: str) -> List[Dict]:
        """API에서 클라이언트 데이터 가져오기 (시뮬레이션)"""
        # 실제로는 외부 API 호출
        await asyncio.sleep(0.1)  # API 호출 시뮬레이션
        
        # JSON 파일에서 시뮬레이션 데이터 로드
        return self._get_clients_from_json(site)
    
    def _get_clients_from_json(self, site: str) -> List[Dict]:
        """JSON 파일에서 클라이언트 데이터 조회 (백업)"""
        site_files = {
            'Parafield Gardens': 'parafield_gardens_client.json',
            'Nerrilda': 'nerrilda_client.json',
            'Ramsay': 'ramsay_client.json',
            'Yankalilla': 'yankalilla_client.json'
        }
        
        filename = site_files.get(site)
        if not filename:
            return []
        
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'client_info' in data:
                return data['client_info']
            elif isinstance(data, list):
                return data
            
        except Exception as e:
            logger.error(f"JSON 파일 읽기 실패 {filepath}: {e}")
        
        return []
    
    def _save_clients_json_backup(self, site: str, clients: List[Dict]):
        """클라이언트 데이터 JSON 백업 저장"""
        site_files = {
            'Parafield Gardens': 'parafield_gardens_client.json',
            'Nerrilda': 'nerrilda_client.json',
            'Ramsay': 'ramsay_client.json',
            'Yankalilla': 'yankalilla_client.json'
        }
        
        filename = site_files.get(site)
        if filename:
            filepath = os.path.join(self.data_dir, filename)
            backup_data = {
                'site': site,
                'last_updated': datetime.now().isoformat(),
                'client_info': clients
            }
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    # ===========================================
    # 참조 데이터 관리 (Tier 2)
    # ===========================================
    
    def get_care_areas(self, include_archived: bool = False) -> List[Dict]:
        """케어 영역 조회 (DB 우선)"""
        
        # 1. DB에서 조회 시도
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "" if include_archived else "WHERE is_archived = 0"
            cursor.execute(f'''
                SELECT * FROM care_areas {where_clause}
                ORDER BY description
            ''')
            
            db_results = [dict(row) for row in cursor.fetchall()]
            
            if db_results:
                return db_results
        
        # 2. DB에 없으면 JSON에서 로드하고 DB에 캐시
        return self._load_and_cache_care_areas(include_archived)
    
    def _load_and_cache_care_areas(self, include_archived: bool = False) -> List[Dict]:
        """JSON에서 케어 영역 로드하고 DB에 캐시"""
        filepath = os.path.join(self.data_dir, 'carearea.json')
        
        try:
            with open(filepath, 'r') as f:
                care_areas = json.load(f)
            
            # DB에 캐시
            with self.get_db_connection() as conn:
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
            
            self.update_sync_status('carearea', None, 'success', len(care_areas))
            
            # 필터링해서 반환
            if include_archived:
                return care_areas
            else:
                return [area for area in care_areas if not area.get('IsArchived', False)]
        
        except Exception as e:
            logger.error(f"케어 영역 로드 실패: {e}")
            return []
    
    def get_event_types(self, include_archived: bool = False) -> List[Dict]:
        """이벤트 타입 조회 (DB 우선)"""
        
        # 1. DB에서 조회 시도
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "" if include_archived else "WHERE is_archived = 0"
            cursor.execute(f'''
                SELECT * FROM event_types {where_clause}
                ORDER BY description
            ''')
            
            db_results = [dict(row) for row in cursor.fetchall()]
            
            if db_results:
                return db_results
        
        # 2. DB에 없으면 JSON에서 로드하고 DB에 캐시
        return self._load_and_cache_event_types(include_archived)
    
    def _load_and_cache_event_types(self, include_archived: bool = False) -> List[Dict]:
        """JSON에서 이벤트 타입 로드하고 DB에 캐시"""
        filepath = os.path.join(self.data_dir, 'eventtype.json')
        
        try:
            with open(filepath, 'r') as f:
                event_types = json.load(f)
            
            # DB에 캐시
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                for event in event_types:
                    cursor.execute('''
                        INSERT OR REPLACE INTO event_types 
                        (id, description, color_argb, is_archived, is_external, last_updated_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        event['Id'],
                        event['Description'],
                        event.get('ColorArgb'),
                        event.get('IsArchived', False),
                        event.get('IsExternal', False),
                        event.get('LastUpdatedDate')
                    ))
                
                conn.commit()
            
            self.update_sync_status('eventtype', None, 'success', len(event_types))
            
            # 필터링해서 반환
            if include_archived:
                return event_types
            else:
                return [event for event in event_types if not event.get('IsArchived', False)]
        
        except Exception as e:
            logger.error(f"이벤트 타입 로드 실패: {e}")
            return []
    
    # ===========================================
    # 하이브리드 데이터 관리 (Tier 3)
    # ===========================================
    
    def get_incidents(self, site: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None, use_cache: bool = True) -> List[Dict]:
        """인시던트 데이터 조회 (하이브리드 방식)"""
        
        if use_cache and self.is_cache_valid('incidents', site):
            # DB 캐시 사용
            return self._get_incidents_from_db(site, start_date, end_date)
        else:
            # JSON 파일 직접 조회
            return self._get_incidents_from_json(site, start_date, end_date)
    
    def _get_incidents_from_db(self, site: str, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> List[Dict]:
        """DB에서 인시던트 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM incidents_cache WHERE site = ?"
            params = [site]
            
            if start_date:
                query += " AND incident_date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND incident_date <= ?"
                params.append(end_date)
            
            query += " ORDER BY incident_date DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def _get_incidents_from_json(self, site: str, start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> List[Dict]:
        """JSON에서 인시던트 조회"""
        # incidents_Parafield Gardens_2025-08-25_2025-09-01_20250901_150146.json 형태
        incidents = []
        
        for filename in os.listdir(self.data_dir):
            if filename.startswith('incidents_') and site.replace(' ', ' ') in filename:
                filepath = os.path.join(self.data_dir, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        file_incidents = json.load(f)
                    
                    # 날짜 필터링
                    filtered_incidents = file_incidents
                    if start_date or end_date:
                        filtered_incidents = []
                        for incident in file_incidents:
                            incident_date = incident.get('date', '')
                            if start_date and incident_date < start_date:
                                continue
                            if end_date and incident_date > end_date:
                                continue
                            filtered_incidents.append(incident)
                    
                    incidents.extend(filtered_incidents)
                    
                except Exception as e:
                    logger.error(f"인시던트 파일 읽기 실패 {filepath}: {e}")
        
        return incidents
    
    # ===========================================
    # 유틸리티 메서드
    # ===========================================
    
    def get_sync_status_summary(self) -> Dict[str, Any]:
        """동기화 상태 요약"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT data_type, site, last_sync_time, sync_status, records_synced
                FROM sync_status
                ORDER BY data_type, site
            ''')
            
            results = {}
            for row in cursor.fetchall():
                data_type = row['data_type']
                if data_type not in results:
                    results[data_type] = []
                
                results[data_type].append({
                    'site': row['site'],
                    'last_sync': row['last_sync_time'],
                    'status': row['sync_status'],
                    'records': row['records_synced']
                })
            
            return results
    
    def force_refresh_all_cache(self):
        """모든 캐시 강제 새로고침"""
        logger.info("모든 캐시 강제 새로고침 시작...")
        
        # 사이트별 클라이언트 데이터
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        for site in sites:
            asyncio.run(self.get_clients(site, force_refresh=True))
        
        # 참조 데이터
        self._load_and_cache_care_areas()
        self._load_and_cache_event_types()
        
        logger.info("모든 캐시 새로고침 완료")


# ===========================================
# 사용 예시
# ===========================================

async def example_usage():
    """하이브리드 데이터 매니저 사용 예시"""
    manager = HybridDataManager()
    
    # 1. 클라이언트 데이터 조회 (자동 캐시/동기화)
    clients = await manager.get_clients('Parafield Gardens')
    print(f"클라이언트 {len(clients)}명 조회")
    
    # 2. 케어 영역 조회 (DB 우선, JSON 백업)
    care_areas = manager.get_care_areas()
    print(f"케어 영역 {len(care_areas)}개 조회")
    
    # 3. 이벤트 타입 조회
    event_types = manager.get_event_types()
    print(f"이벤트 타입 {len(event_types)}개 조회")
    
    # 4. 인시던트 조회 (하이브리드)
    incidents = manager.get_incidents('Parafield Gardens')
    print(f"인시던트 {len(incidents)}개 조회")
    
    # 5. 동기화 상태 확인
    sync_status = manager.get_sync_status_summary()
    print("동기화 상태:", sync_status)


if __name__ == "__main__":
    asyncio.run(example_usage())
