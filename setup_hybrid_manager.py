#!/usr/bin/env python3
"""
Progress Report System - 하이브리드 데이터 매니저 설정
Week 2 - Day 3-4: 기존 앱과 통합 준비
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

class HybridDataManagerSetup:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def setup_hybrid_manager(self):
        """하이브리드 데이터 매니저 설정"""
        print("=" * 60)
        print("Progress Report System - 하이브리드 데이터 매니저 설정")
        print("Week 2 - Day 3-4: 기존 앱과 통합")
        print("=" * 60)
        
        try:
            # 1. 데이터베이스 연결 테스트
            self.test_database_connection()
            
            # 2. 하이브리드 매니저 클래스 생성
            self.create_hybrid_manager_class()
            
            # 3. 기존 앱 통합을 위한 어댑터 생성
            self.create_app_adapter()
            
            # 4. 성능 테스트
            self.run_comprehensive_tests()
            
            # 5. 사용 예시 생성
            self.create_usage_examples()
            
            print("\n✅ 하이브리드 데이터 매니저 설정 완료!")
            return True
            
        except Exception as e:
            print(f"\n❌ 설정 실패: {e}")
            return False
    
    def test_database_connection(self):
        """데이터베이스 연결 및 상태 확인"""
        print("\n1. 데이터베이스 연결 테스트")
        print("-" * 40)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 테이블 존재 확인
            tables = ['users', 'clients_cache', 'care_areas', 'event_types', 'fcm_tokens']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table}: {count:,}개 레코드")
            
            # 인덱스 성능 확인
            start_time = time.time()
            cursor.execute("SELECT * FROM clients_cache WHERE site = 'Parafield Gardens' LIMIT 10")
            results = cursor.fetchall()
            query_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 인덱스 성능: {query_time:.2f}ms (10개 레코드)")
            
        finally:
            conn.close()
    
    def create_hybrid_manager_class(self):
        """실제 앱에서 사용할 하이브리드 매니저 클래스 생성"""
        print("\n2. 하이브리드 매니저 클래스 생성")
        print("-" * 40)
        
        manager_code = '''#!/usr/bin/env python3
"""
Progress Report System - 실제 운영용 하이브리드 데이터 매니저
SQLite 캐시와 JSON 백업을 조합한 고성능 데이터 관리
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class ProductionHybridManager:
    """운영환경용 하이브리드 데이터 매니저"""
    
    def __init__(self, db_path: str = 'progress_report.db', data_dir: str = 'data'):
        self.db_path = db_path
        self.data_dir = data_dir
        self.cache_expiry_hours = 6  # 캐시 만료 시간
        
        # 데이터베이스 존재 확인
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    @contextmanager
    def get_db_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    # ===========================================
    # 사용자 관리
    # ===========================================
    
    def authenticate_user(self, username: str, password_hash: str) -> Optional[Dict]:
        """사용자 인증 (SQLite 기반)"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            user = cursor.fetchone()
            if user:
                # location JSON 파싱
                user_dict = dict(user)
                if user_dict.get('location'):
                    try:
                        user_dict['location'] = json.loads(user_dict['location'])
                    except json.JSONDecodeError:
                        user_dict['location'] = []
                return user_dict
        return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """사용자 정보 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user = cursor.fetchone()
            if user:
                user_dict = dict(user)
                if user_dict.get('location'):
                    try:
                        user_dict['location'] = json.loads(user_dict['location'])
                    except json.JSONDecodeError:
                        user_dict['location'] = []
                return user_dict
        return None
    
    def get_all_users(self) -> List[Dict]:
        """모든 활성 사용자 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE is_active = 1 ORDER BY username')
            
            users = []
            for row in cursor.fetchall():
                user_dict = dict(row)
                if user_dict.get('location'):
                    try:
                        user_dict['location'] = json.loads(user_dict['location'])
                    except json.JSONDecodeError:
                        user_dict['location'] = []
                users.append(user_dict)
            
            return users
    
    # ===========================================
    # 클라이언트 데이터 관리
    # ===========================================
    
    def get_clients(self, site: str, search_term: str = None, room_filter: str = None) -> List[Dict]:
        """클라이언트 데이터 조회 (고성능 SQLite 기반)"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM clients_cache WHERE site = ? AND is_active = 1"
            params = [site]
            
            if search_term:
                query += " AND (client_name LIKE ? OR preferred_name LIKE ?)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern])
            
            if room_filter:
                query += " AND room_number LIKE ?"
                params.append(f"%{room_filter}%")
            
            query += " ORDER BY client_name"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_client_by_id(self, person_id: int, site: str = None) -> Optional[Dict]:
        """ID로 특정 클라이언트 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            if site:
                cursor.execute('''
                    SELECT * FROM clients_cache 
                    WHERE person_id = ? AND site = ? AND is_active = 1
                ''', (person_id, site))
            else:
                cursor.execute('''
                    SELECT * FROM clients_cache 
                    WHERE person_id = ? AND is_active = 1
                    ORDER BY site
                ''', (person_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def search_clients_global(self, search_term: str) -> List[Dict]:
        """전체 사이트에서 클라이언트 검색"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            search_pattern = f"%{search_term}%"
            cursor.execute('''
                SELECT * FROM clients_cache 
                WHERE (client_name LIKE ? OR preferred_name LIKE ? OR room_number LIKE ?)
                AND is_active = 1
                ORDER BY site, client_name
            ''', (search_pattern, search_pattern, search_pattern))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_clients_paginated(self, site: str, page: int = 1, per_page: int = 50) -> Dict:
        """페이지네이션된 클라이언트 목록"""
        offset = (page - 1) * per_page
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 전체 개수 조회
            cursor.execute('''
                SELECT COUNT(*) FROM clients_cache 
                WHERE site = ? AND is_active = 1
            ''', (site,))
            total = cursor.fetchone()[0]
            
            # 페이지 데이터 조회
            cursor.execute('''
                SELECT * FROM clients_cache 
                WHERE site = ? AND is_active = 1
                ORDER BY client_name
                LIMIT ? OFFSET ?
            ''', (site, per_page, offset))
            
            clients = [dict(row) for row in cursor.fetchall()]
            
            return {
                'clients': clients,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
    
    # ===========================================
    # 참조 데이터 관리
    # ===========================================
    
    def get_care_areas(self, include_archived: bool = False) -> List[Dict]:
        """케어 영역 조회 (SQLite 캐시 우선)"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            if include_archived:
                cursor.execute('SELECT * FROM care_areas ORDER BY description')
            else:
                cursor.execute('SELECT * FROM care_areas WHERE is_archived = 0 ORDER BY description')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_event_types(self, include_archived: bool = False) -> List[Dict]:
        """이벤트 타입 조회 (SQLite 캐시 우선)"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            if include_archived:
                cursor.execute('SELECT * FROM event_types ORDER BY description')
            else:
                cursor.execute('SELECT * FROM event_types WHERE is_archived = 0 ORDER BY description')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_care_area_by_id(self, care_area_id: int) -> Optional[Dict]:
        """특정 케어 영역 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM care_areas WHERE id = ?', (care_area_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_event_type_by_id(self, event_type_id: int) -> Optional[Dict]:
        """특정 이벤트 타입 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM event_types WHERE id = ?', (event_type_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    # ===========================================
    # FCM 토큰 관리
    # ===========================================
    
    def get_fcm_tokens(self, user_id: str = None, active_only: bool = True) -> List[Dict]:
        """FCM 토큰 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM fcm_tokens"
            params = []
            
            conditions = []
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if active_only:
                conditions.append("is_active = 1")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_fcm_token(self, user_id: str, token: str, device_info: str = None) -> bool:
        """FCM 토큰 추가"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO fcm_tokens 
                    (user_id, token, device_info, created_at, last_used, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, token, device_info, datetime.now().isoformat(), 
                      datetime.now().isoformat(), True))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"FCM 토큰 추가 실패: {e}")
            return False
    
    # ===========================================
    # 로그 관리
    # ===========================================
    
    def log_access(self, user_info: Dict, page: str = None, ip_address: str = None):
        """사용자 접근 로그 기록"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO access_logs 
                    (timestamp, username, display_name, role, position, page_accessed, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    user_info.get('username'),
                    user_info.get('display_name'),
                    user_info.get('role'),
                    user_info.get('position'),
                    page,
                    ip_address
                ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"접근 로그 기록 실패: {e}")
    
    def log_progress_note(self, user_info: Dict, client_info: Dict, note_content: str, 
                         care_area_id: int = None, event_type_id: int = None, site: str = None):
        """Progress Note 작성 로그 기록"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO progress_note_logs 
                    (timestamp, username, display_name, role, position, 
                     client_id, client_name, care_area_id, event_type_id, 
                     note_content, site)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    user_info.get('username'),
                    user_info.get('display_name'),
                    user_info.get('role'),
                    user_info.get('position'),
                    client_info.get('person_id'),
                    client_info.get('client_name'),
                    care_area_id,
                    event_type_id,
                    note_content,
                    site
                ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Progress Note 로그 기록 실패: {e}")
    
    # ===========================================
    # 통계 및 분석
    # ===========================================
    
    def get_statistics(self) -> Dict:
        """시스템 통계 조회"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 사용자 통계
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            stats['active_users'] = cursor.fetchone()[0]
            
            # 클라이언트 통계
            cursor.execute('SELECT site, COUNT(*) FROM clients_cache WHERE is_active = 1 GROUP BY site')
            stats['clients_by_site'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute('SELECT COUNT(*) FROM clients_cache WHERE is_active = 1')
            stats['total_clients'] = cursor.fetchone()[0]
            
            # 케어 영역 통계
            cursor.execute('SELECT COUNT(*) FROM care_areas WHERE is_archived = 0')
            stats['active_care_areas'] = cursor.fetchone()[0]
            
            # 이벤트 타입 통계
            cursor.execute('SELECT COUNT(*) FROM event_types WHERE is_archived = 0')
            stats['active_event_types'] = cursor.fetchone()[0]
            
            # FCM 토큰 통계
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
            stats['active_fcm_tokens'] = cursor.fetchone()[0]
            
            # 최근 로그 통계
            cursor.execute('''
                SELECT COUNT(*) FROM access_logs 
                WHERE timestamp > datetime('now', '-7 days')
            ''')
            stats['recent_access_logs'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM progress_note_logs 
                WHERE timestamp > datetime('now', '-7 days')
            ''')
            stats['recent_progress_notes'] = cursor.fetchone()[0]
            
            return stats
    
    # ===========================================
    # 유틸리티 메서드
    # ===========================================
    
    def is_cache_healthy(self) -> bool:
        """캐시 상태 확인"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 기본 쿼리 테스트
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM clients_cache')
                client_count = cursor.fetchone()[0]
                
                # 최소한의 데이터가 있는지 확인
                return user_count > 0 and client_count > 0
                
        except Exception as e:
            logger.error(f"캐시 상태 확인 실패: {e}")
            return False
    
    def get_cache_info(self) -> Dict:
        """캐시 정보 조회"""
        info = {}
        
        try:
            # 데이터베이스 파일 크기
            if os.path.exists(self.db_path):
                info['db_size_mb'] = round(os.path.getsize(self.db_path) / 1024 / 1024, 2)
            
            # 통계 정보
            info.update(self.get_statistics())
            
            # 동기화 상태
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT data_type, site, sync_status, last_sync_time, records_synced
                    FROM sync_status
                    ORDER BY data_type, site
                ''')
                
                info['sync_status'] = []
                for row in cursor.fetchall():
                    info['sync_status'].append({
                        'data_type': row[0],
                        'site': row[1],
                        'status': row[2],
                        'last_sync': row[3],
                        'records': row[4]
                    })
            
        except Exception as e:
            logger.error(f"캐시 정보 조회 실패: {e}")
        
        return info
'''
        
        with open('production_hybrid_manager.py', 'w', encoding='utf-8') as f:
            f.write(manager_code)
        
        print("  ✓ production_hybrid_manager.py 생성 완료")
    
    def create_app_adapter(self):
        """기존 앱과의 통합을 위한 어댑터 생성"""
        print("\n3. 앱 통합 어댑터 생성")
        print("-" * 40)
        
        adapter_code = '''#!/usr/bin/env python3
"""
Progress Report System - 앱 통합 어댑터
기존 Flask 앱과 하이브리드 매니저를 연결
"""

from production_hybrid_manager import ProductionHybridManager
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class AppIntegrationAdapter:
    """기존 Flask 앱과 하이브리드 매니저를 연결하는 어댑터"""
    
    def __init__(self):
        self.hybrid_manager = ProductionHybridManager()
    
    # ===========================================
    # 기존 config_users.py 대체 함수들
    # ===========================================
    
    def authenticate_user(self, username: str, password: str) -> dict:
        """사용자 인증 (config_users.py 대체)"""
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return self.hybrid_manager.authenticate_user(username, password_hash)
    
    def get_user(self, username: str) -> dict:
        """사용자 정보 조회 (config_users.py 대체)"""
        return self.hybrid_manager.get_user(username)
    
    # ===========================================
    # JSON 파일 대체 함수들
    # ===========================================
    
    def get_clients_for_site(self, site: str, search_term: str = None) -> list:
        """사이트별 클라이언트 조회 (JSON 파일 대체)"""
        return self.hybrid_manager.get_clients(site, search_term=search_term)
    
    def get_care_areas_list(self) -> list:
        """케어 영역 목록 (carearea.json 대체)"""
        return self.hybrid_manager.get_care_areas()
    
    def get_event_types_list(self) -> list:
        """이벤트 타입 목록 (eventtype.json 대체)"""
        return self.hybrid_manager.get_event_types()
    
    # ===========================================
    # Flask 라우트에서 사용할 헬퍼 함수들
    # ===========================================
    
    def get_clients_for_progress_note(self, site: str) -> list:
        """Progress Note 작성용 클라이언트 목록"""
        clients = self.hybrid_manager.get_clients(site)
        
        # Progress Note 작성에 필요한 형태로 변환
        return [
            {
                'PersonId': client['person_id'],
                'ClientName': client['client_name'],
                'PreferredName': client['preferred_name'],
                'RoomNumber': client['room_number'],
                'RoomName': client['room_name']
            }
            for client in clients
        ]
    
    def get_dropdown_data(self) -> dict:
        """드롭다운용 데이터 (케어 영역, 이벤트 타입)"""
        return {
            'care_areas': [
                {
                    'Id': area['id'],
                    'Description': area['description']
                }
                for area in self.hybrid_manager.get_care_areas()
            ],
            'event_types': [
                {
                    'Id': event['id'],
                    'Description': event['description']
                }
                for event in self.hybrid_manager.get_event_types()
            ]
        }
    
    def search_clients_across_sites(self, search_term: str) -> list:
        """전체 사이트에서 클라이언트 검색"""
        return self.hybrid_manager.search_clients_global(search_term)
    
    # ===========================================
    # 로깅 및 분석
    # ===========================================
    
    def log_user_access(self, user_info: dict, page: str, request):
        """사용자 접근 로그"""
        ip_address = request.remote_addr if request else None
        self.hybrid_manager.log_access(user_info, page, ip_address)
    
    def log_progress_note_creation(self, user_info: dict, client_info: dict, 
                                 note_content: str, care_area_id: int, 
                                 event_type_id: int, site: str):
        """Progress Note 작성 로그"""
        self.hybrid_manager.log_progress_note(
            user_info, client_info, note_content, 
            care_area_id, event_type_id, site
        )
    
    # ===========================================
    # 관리자 기능
    # ===========================================
    
    def get_system_statistics(self) -> dict:
        """시스템 통계 (관리자 대시보드용)"""
        return self.hybrid_manager.get_statistics()
    
    def get_cache_health_status(self) -> dict:
        """캐시 상태 정보"""
        return {
            'healthy': self.hybrid_manager.is_cache_healthy(),
            'info': self.hybrid_manager.get_cache_info()
        }
    
    # ===========================================
    # FCM 관련
    # ===========================================
    
    def get_fcm_tokens_for_user(self, user_id: str) -> list:
        """사용자의 FCM 토큰 목록"""
        return self.hybrid_manager.get_fcm_tokens(user_id)
    
    def register_fcm_token(self, user_id: str, token: str, device_info: str = None) -> bool:
        """FCM 토큰 등록"""
        return self.hybrid_manager.add_fcm_token(user_id, token, device_info)


# 전역 어댑터 인스턴스
app_adapter = None

def get_app_adapter():
    """앱 어댑터 싱글톤 인스턴스 반환"""
    global app_adapter
    if app_adapter is None:
        app_adapter = AppIntegrationAdapter()
    return app_adapter

def init_hybrid_manager(app):
    """Flask 앱 초기화 시 호출"""
    try:
        adapter = get_app_adapter()
        if adapter.hybrid_manager.is_cache_healthy():
            app.logger.info("하이브리드 데이터 매니저 초기화 성공")
            return True
        else:
            app.logger.error("하이브리드 데이터 매니저 캐시 상태 불량")
            return False
    except Exception as e:
        app.logger.error(f"하이브리드 데이터 매니저 초기화 실패: {e}")
        return False
'''
        
        with open('app_integration_adapter.py', 'w', encoding='utf-8') as f:
            f.write(adapter_code)
        
        print("  ✓ app_integration_adapter.py 생성 완료")
    
    def run_comprehensive_tests(self):
        """종합 성능 및 기능 테스트"""
        print("\n4. 종합 테스트 실행")
        print("-" * 40)
        
        try:
            from production_hybrid_manager import ProductionHybridManager
            manager = ProductionHybridManager()
            
            # 성능 테스트
            import time
            
            # 1. 사용자 인증 테스트
            start_time = time.time()
            admin_user = manager.get_user('admin')
            auth_time = (time.time() - start_time) * 1000
            
            if admin_user:
                print(f"  ✓ 사용자 인증: {auth_time:.2f}ms")
            else:
                print("  ✗ 사용자 인증 실패")
            
            # 2. 클라이언트 조회 테스트
            start_time = time.time()
            pg_clients = manager.get_clients('Parafield Gardens')
            client_query_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 클라이언트 조회: {len(pg_clients)}명, {client_query_time:.2f}ms")
            
            # 3. 검색 테스트
            start_time = time.time()
            search_results = manager.search_clients_global('Smith')
            search_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 전체 검색: {len(search_results)}명, {search_time:.2f}ms")
            
            # 4. 페이지네이션 테스트
            start_time = time.time()
            paginated = manager.get_clients_paginated('Parafield Gardens', page=1, per_page=10)
            pagination_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 페이지네이션: {len(paginated['clients'])}명/{paginated['total']}명, {pagination_time:.2f}ms")
            
            # 5. 참조 데이터 테스트
            start_time = time.time()
            care_areas = manager.get_care_areas()
            event_types = manager.get_event_types()
            ref_data_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 참조 데이터: 케어영역 {len(care_areas)}개, 이벤트 {len(event_types)}개, {ref_data_time:.2f}ms")
            
            # 6. 통계 테스트
            start_time = time.time()
            stats = manager.get_statistics()
            stats_time = (time.time() - start_time) * 1000
            
            print(f"  ✓ 통계 조회: {stats_time:.2f}ms")
            print(f"    - 활성 사용자: {stats['active_users']}명")
            print(f"    - 전체 클라이언트: {stats['total_clients']}명")
            print(f"    - 활성 FCM 토큰: {stats['active_fcm_tokens']}개")
            
        except Exception as e:
            print(f"  ✗ 테스트 실패: {e}")
    
    def create_usage_examples(self):
        """사용 예시 생성"""
        print("\n5. 사용 예시 생성")
        print("-" * 40)
        
        example_code = '''#!/usr/bin/env python3
"""
Progress Report System - 하이브리드 매니저 사용 예시
기존 Flask 앱에서 사용하는 방법
"""

from app_integration_adapter import get_app_adapter
from flask import Flask, request, jsonify, render_template
from flask_login import login_required, current_user

app = Flask(__name__)

# 앱 어댑터 초기화
adapter = get_app_adapter()

# ===========================================
# 기존 라우트 개선 예시
# ===========================================

@app.route('/api/clients/<site>')
@login_required
def get_clients_api(site):
    """클라이언트 API - JSON 파일 대신 SQLite 사용"""
    search_term = request.args.get('search', '')
    room_filter = request.args.get('room', '')
    
    # 기존: JSON 파일 로드 (느림)
    # with open(f'data/{site}_client.json', 'r') as f:
    #     clients = json.load(f)
    
    # 개선: SQLite 캐시 사용 (빠름)
    clients = adapter.get_clients_for_site(site, search_term)
    
    # 접근 로그 기록
    user_info = {
        'username': current_user.username,
        'display_name': current_user.display_name,
        'role': current_user.role,
        'position': current_user.position
    }
    adapter.log_user_access(user_info, f'/api/clients/{site}', request)
    
    return jsonify({
        'success': True,
        'clients': clients,
        'count': len(clients)
    })

@app.route('/progress-notes')
@login_required
def progress_notes():
    """Progress Notes 페이지 - 드롭다운 데이터 최적화"""
    site = request.args.get('site', 'Parafield Gardens')
    
    # 기존: 여러 JSON 파일 로드 (느림)
    # clients = load_json(f'{site}_client.json')
    # care_areas = load_json('carearea.json')
    # event_types = load_json('eventtype.json')
    
    # 개선: 통합 조회 (빠름)
    clients = adapter.get_clients_for_progress_note(site)
    dropdown_data = adapter.get_dropdown_data()
    
    return render_template('ProgressNote.html',
                         clients=clients,
                         care_areas=dropdown_data['care_areas'],
                         event_types=dropdown_data['event_types'],
                         site=site)

@app.route('/api/search-clients')
@login_required
def search_clients_api():
    """전체 사이트 클라이언트 검색"""
    search_term = request.args.get('q', '')
    
    if len(search_term) < 2:
        return jsonify({'success': False, 'message': '검색어는 2글자 이상 입력하세요.'})
    
    # SQLite 기반 고속 검색
    results = adapter.search_clients_across_sites(search_term)
    
    return jsonify({
        'success': True,
        'results': results,
        'count': len(results)
    })

@app.route('/api/clients-paginated/<site>')
@login_required
def get_clients_paginated_api(site):
    """페이지네이션된 클라이언트 목록"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    # SQLite 기반 페이지네이션
    result = adapter.hybrid_manager.get_clients_paginated(site, page, per_page)
    
    return jsonify({
        'success': True,
        **result
    })

@app.route('/admin/statistics')
@login_required
def admin_statistics():
    """관리자 통계 대시보드"""
    if current_user.role not in ['admin', 'site_admin']:
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
    
    # 시스템 통계
    stats = adapter.get_system_statistics()
    cache_status = adapter.get_cache_health_status()
    
    return jsonify({
        'success': True,
        'statistics': stats,
        'cache_status': cache_status
    })

# ===========================================
# 로그인 개선 예시
# ===========================================

@app.route('/login', methods=['POST'])
def login():
    """로그인 - config_users.py 대신 SQLite 사용"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    # 기존: config_users.py 사용 (정적)
    # user = authenticate_user(username, password)
    
    # 개선: SQLite 사용 (동적, 확장 가능)
    user = adapter.authenticate_user(username, password)
    
    if user:
        # Flask-Login 처리
        # login_user(User(user))
        
        # 로그인 로그 기록
        adapter.log_user_access(user, '/login', request)
        
        return jsonify({'success': True, 'redirect': '/dashboard'})
    else:
        return jsonify({'success': False, 'message': '로그인 실패'}), 401

# ===========================================
# FCM 관련 개선 예시
# ===========================================

@app.route('/api/fcm/register', methods=['POST'])
@login_required
def register_fcm_token():
    """FCM 토큰 등록 - SQLite 기반"""
    data = request.get_json()
    token = data.get('token')
    device_info = data.get('device_info')
    
    if not token:
        return jsonify({'success': False, 'message': '토큰이 필요합니다.'}), 400
    
    # SQLite에 토큰 저장
    success = adapter.register_fcm_token(current_user.username, token, device_info)
    
    return jsonify({
        'success': success,
        'message': '토큰 등록 완료' if success else '토큰 등록 실패'
    })

# ===========================================
# 성능 비교 예시
# ===========================================

def performance_comparison():
    """성능 비교 예시"""
    import time
    import json
    
    # 기존 방식 (JSON 파일)
    start_time = time.time()
    with open('data/parafield_gardens_client.json', 'r') as f:
        json_clients = json.load(f)
    json_time = (time.time() - start_time) * 1000
    
    # 개선 방식 (SQLite)
    start_time = time.time()
    sqlite_clients = adapter.get_clients_for_site('Parafield Gardens')
    sqlite_time = (time.time() - start_time) * 1000
    
    print(f"JSON 파일 로드: {json_time:.2f}ms")
    print(f"SQLite 조회: {sqlite_time:.2f}ms")
    print(f"성능 개선: {json_time/sqlite_time:.1f}배 빠름")

if __name__ == '__main__':
    # 성능 비교 실행
    performance_comparison()
    
    # Flask 앱 실행
    app.run(debug=True)
'''
        
        with open('usage_examples.py', 'w', encoding='utf-8') as f:
            f.write(example_code)
        
        print("  ✓ usage_examples.py 생성 완료")


def main():
    try:
        setup = HybridDataManagerSetup()
        success = setup.setup_hybrid_manager()
        
        if success:
            print("\n🎉 하이브리드 데이터 매니저 설정 완료!")
            print("\n📁 생성된 파일들:")
            print("  - production_hybrid_manager.py (핵심 매니저)")
            print("  - app_integration_adapter.py (Flask 통합 어댑터)")
            print("  - usage_examples.py (사용 예시)")
            
            print("\n다음 단계:")
            print("1. 기존 Flask 앱에 어댑터 통합")
            print("2. 성능 테스트 실행")
            print("명령어: python test_week2.py")
        else:
            print("\n❌ 설정에 실패했습니다.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
