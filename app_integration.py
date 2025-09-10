#!/usr/bin/env python3
"""
Progress Report System - Flask 앱 통합
Week 3 - Day 1-2: 기존 앱과 SQLite 시스템 통합
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class FlaskAppIntegration:
    """Flask 앱과 SQLite 시스템 통합 클래스"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def get_db_connection(self):
        """데이터베이스 연결"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ===========================================
    # config_users.py 대체 함수들
    # ===========================================
    
    def authenticate_user_sqlite(self, username: str, password: str) -> Optional[Dict]:
        """SQLite 기반 사용자 인증 (config_users.py 대체)"""
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            ''', (username, password_hash))
            
            user = cursor.fetchone()
            if user:
                user_dict = dict(user)
                # location JSON 파싱
                if user_dict.get('location'):
                    try:
                        user_dict['location'] = json.loads(user_dict['location'])
                    except json.JSONDecodeError:
                        user_dict['location'] = []
                return user_dict
            return None
            
        finally:
            conn.close()
    
    def get_user_sqlite(self, username: str) -> Optional[Dict]:
        """SQLite 기반 사용자 정보 조회 (config_users.py 대체)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
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
            
        finally:
            conn.close()
    
    # ===========================================
    # JSON 파일 대체 함수들
    # ===========================================
    
    def get_clients_sqlite(self, site: str, search_term: str = None) -> List[Dict]:
        """SQLite 기반 클라이언트 조회 (JSON 파일 대체)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT * FROM clients_cache WHERE site = ? AND is_active = 1"
            params = [site]
            
            if search_term:
                query += " AND (client_name LIKE ? OR preferred_name LIKE ? OR room_number LIKE ?)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += " ORDER BY client_name"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def get_care_areas_sqlite(self, include_archived: bool = False) -> List[Dict]:
        """SQLite 기반 케어 영역 조회 (carearea.json 대체)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if include_archived:
                cursor.execute('SELECT * FROM care_areas ORDER BY description')
            else:
                cursor.execute('SELECT * FROM care_areas WHERE is_archived = 0 ORDER BY description')
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    def get_event_types_sqlite(self, include_archived: bool = False) -> List[Dict]:
        """SQLite 기반 이벤트 타입 조회 (eventtype.json 대체)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if include_archived:
                cursor.execute('SELECT * FROM event_types ORDER BY description')
            else:
                cursor.execute('SELECT * FROM event_types WHERE is_archived = 0 ORDER BY description')
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # ===========================================
    # 기존 앱 라우트와 호환되는 변환 함수들
    # ===========================================
    
    def convert_clients_for_frontend(self, clients: List[Dict]) -> List[Dict]:
        """SQLite 클라이언트 데이터를 프론트엔드 형식으로 변환"""
        converted = []
        
        for client in clients:
            # 기존 JSON 형식과 호환되도록 변환
            converted_client = {
                'id': client.get('person_id'),
                'PersonId': client.get('person_id'),
                'MainClientServiceId': client.get('main_client_service_id') or client.get('person_id'),
                'ClientName': client.get('client_name'),
                'PreferredName': client.get('preferred_name'),
                'RoomNumber': client.get('room_number'),
                'RoomName': client.get('room_name'),
                'Gender': client.get('gender'),
                'BirthDate': client.get('birth_date'),
                'AdmissionDate': client.get('admission_date'),
                'WingName': client.get('wing_name'),
                
                # 프론트엔드에서 사용하는 형식
                'name': client.get('preferred_name') or client.get('client_name'),
                'room': client.get('room_number')
            }
            converted.append(converted_client)
        
        return converted
    
    def convert_care_areas_for_frontend(self, care_areas: List[Dict]) -> List[Dict]:
        """SQLite 케어 영역을 프론트엔드 형식으로 변환"""
        return [
            {
                'Id': area['id'],
                'Description': area['description'],
                'IsArchived': area['is_archived'],
                'IsExternal': area['is_external']
            }
            for area in care_areas
        ]
    
    def convert_event_types_for_frontend(self, event_types: List[Dict]) -> List[Dict]:
        """SQLite 이벤트 타입을 프론트엔드 형식으로 변환"""
        return [
            {
                'Id': event['id'],
                'Description': event['description'],
                'ColorArgb': event['color_argb'],
                'IsArchived': event['is_archived'],
                'IsExternal': event['is_external']
            }
            for event in event_types
        ]
    
    # ===========================================
    # 통합 테스트 함수들
    # ===========================================
    
    def test_integration(self):
        """통합 테스트 실행"""
        print("=" * 60)
        print("Flask 앱 통합 테스트")
        print("=" * 60)
        
        test_results = []
        
        # 1. 사용자 인증 테스트
        print("\n1. 사용자 인증 테스트")
        print("-" * 40)
        
        admin_user = self.authenticate_user_sqlite('admin', 'password123')
        if admin_user:
            print(f"  ✓ admin 사용자 인증 성공: {admin_user['first_name']} {admin_user['last_name']}")
            test_results.append(True)
        else:
            print("  ❌ admin 사용자 인증 실패")
            test_results.append(False)
        
        # 2. 클라이언트 데이터 조회 테스트
        print("\n2. 클라이언트 데이터 조회 테스트")
        print("-" * 40)
        
        import time
        start_time = time.time()
        clients = self.get_clients_sqlite('Parafield Gardens')
        query_time = (time.time() - start_time) * 1000
        
        if clients:
            converted_clients = self.convert_clients_for_frontend(clients)
            print(f"  ✓ 클라이언트 조회 성공: {len(clients)}명 ({query_time:.2f}ms)")
            print(f"  ✓ 프론트엔드 변환 성공: {len(converted_clients)}명")
            
            # 샘플 데이터 확인
            if converted_clients:
                sample = converted_clients[0]
                print(f"  샘플: {sample['name']} (ID: {sample['id']}, 방: {sample['room']})")
            
            test_results.append(True)
        else:
            print("  ❌ 클라이언트 조회 실패")
            test_results.append(False)
        
        # 3. 케어 영역 조회 테스트
        print("\n3. 케어 영역 조회 테스트")
        print("-" * 40)
        
        start_time = time.time()
        care_areas = self.get_care_areas_sqlite()
        query_time = (time.time() - start_time) * 1000
        
        if care_areas:
            converted_care_areas = self.convert_care_areas_for_frontend(care_areas)
            print(f"  ✓ 케어 영역 조회 성공: {len(care_areas)}개 ({query_time:.2f}ms)")
            print(f"  ✓ 프론트엔드 변환 성공: {len(converted_care_areas)}개")
            test_results.append(True)
        else:
            print("  ❌ 케어 영역 조회 실패")
            test_results.append(False)
        
        # 4. 이벤트 타입 조회 테스트
        print("\n4. 이벤트 타입 조회 테스트")
        print("-" * 40)
        
        start_time = time.time()
        event_types = self.get_event_types_sqlite()
        query_time = (time.time() - start_time) * 1000
        
        if event_types:
            converted_event_types = self.convert_event_types_for_frontend(event_types)
            print(f"  ✓ 이벤트 타입 조회 성공: {len(event_types)}개 ({query_time:.2f}ms)")
            print(f"  ✓ 프론트엔드 변환 성공: {len(converted_event_types)}개")
            test_results.append(True)
        else:
            print("  ❌ 이벤트 타입 조회 실패")
            test_results.append(False)
        
        # 5. 검색 기능 테스트
        print("\n5. 검색 기능 테스트")
        print("-" * 40)
        
        start_time = time.time()
        search_results = self.get_clients_sqlite('Parafield Gardens', 'Smith')
        search_time = (time.time() - start_time) * 1000
        
        print(f"  ✓ 'Smith' 검색 결과: {len(search_results)}명 ({search_time:.2f}ms)")
        test_results.append(True)
        
        # 결과 요약
        success_count = sum(test_results)
        total_count = len(test_results)
        
        print(f"\n통합 테스트 결과: {success_count}/{total_count} 성공 ({success_count/total_count*100:.1f}%)")
        
        return success_count == total_count


def create_integration_patch():
    """기존 app.py에 적용할 통합 패치 생성"""
    print("=" * 60)
    print("Flask 앱 통합 패치 생성")
    print("=" * 60)
    
    patch_code = '''
# ==============================
# SQLite 통합 패치 - app.py에 추가할 코드
# ==============================

# 파일 상단에 추가
try:
    from app_integration import FlaskAppIntegration
    sqlite_integration = FlaskAppIntegration()
    USE_SQLITE = True
    print("✅ SQLite 통합 모드 활성화")
except ImportError:
    USE_SQLITE = False
    print("⚠️ SQLite 통합 모드 비활성화 - JSON 파일 사용")

# ==============================
# 기존 함수들을 SQLite 버전으로 대체
# ==============================

def get_clients_for_site_enhanced(site, search_term=None):
    """클라이언트 조회 (SQLite 우선, JSON 백업)"""
    if USE_SQLITE:
        try:
            # SQLite에서 조회
            clients = sqlite_integration.get_clients_sqlite(site, search_term)
            converted_clients = sqlite_integration.convert_clients_for_frontend(clients)
            logger.info(f"SQLite에서 {site} 클라이언트 {len(converted_clients)}명 조회")
            return converted_clients
        except Exception as e:
            logger.error(f"SQLite 클라이언트 조회 실패: {e}")
            # 실패 시 기존 JSON 방식으로 fallback
    
    # 기존 JSON 방식 (fallback)
    return get_clients_from_json_fallback(site, search_term)

def get_care_areas_enhanced():
    """케어 영역 조회 (SQLite 우선, JSON 백업)"""
    if USE_SQLITE:
        try:
            care_areas = sqlite_integration.get_care_areas_sqlite()
            converted_areas = sqlite_integration.convert_care_areas_for_frontend(care_areas)
            logger.info(f"SQLite에서 케어 영역 {len(converted_areas)}개 조회")
            return converted_areas
        except Exception as e:
            logger.error(f"SQLite 케어 영역 조회 실패: {e}")
    
    # 기존 JSON 방식 (fallback)
    return get_care_areas_from_json_fallback()

def get_event_types_enhanced():
    """이벤트 타입 조회 (SQLite 우선, JSON 백업)"""
    if USE_SQLITE:
        try:
            event_types = sqlite_integration.get_event_types_sqlite()
            converted_types = sqlite_integration.convert_event_types_for_frontend(event_types)
            logger.info(f"SQLite에서 이벤트 타입 {len(converted_types)}개 조회")
            return converted_types
        except Exception as e:
            logger.error(f"SQLite 이벤트 타입 조회 실패: {e}")
    
    # 기존 JSON 방식 (fallback)
    return get_event_types_from_json_fallback()

# ==============================
# 기존 라우트 수정 예시
# ==============================

# index 라우트 수정 예시
@app.route('/')
@login_required  
def home():
    """홈 페이지 (SQLite 통합 버전)"""
    try:
        site = session.get('site', 'Parafield Gardens')
        
        # SQLite에서 데이터 조회 (성능 향상)
        clients = get_clients_for_site_enhanced(site)
        care_areas = get_care_areas_enhanced()
        event_types = get_event_types_enhanced()
        
        # 동기화 상태 확인
        sync_status = get_client_sync_status_for_site(site)
        
        return render_template('index.html',
                             current_user=current_user,
                             clients=clients,
                             care_areas=care_areas,
                             event_types=event_types,
                             selected_site=site,
                             sync_status=sync_status)
        
    except Exception as e:
        logger.error(f"홈 페이지 로드 실패: {e}")
        # 기존 방식으로 fallback
        return render_template_with_json_fallback()

# ==============================
# 새로운 유틸리티 함수들
# ==============================

def get_client_sync_status_for_site(site):
    """특정 사이트의 동기화 상태 조회"""
    if not USE_SQLITE:
        return None
    
    try:
        conn = sqlite_integration.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT last_sync_time, sync_status, records_synced
            FROM sync_status 
            WHERE data_type = 'clients' AND site = ?
        ''', (site,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            last_sync = datetime.fromisoformat(result['last_sync_time']) if result['last_sync_time'] else None
            age_minutes = int((datetime.now() - last_sync).total_seconds() / 60) if last_sync else None
            
            return {
                'last_sync': result['last_sync_time'],
                'status': result['sync_status'],
                'records': result['records_synced'],
                'age_minutes': age_minutes,
                'is_expired': age_minutes > 30 if age_minutes else True
            }
    except Exception as e:
        logger.error(f"동기화 상태 조회 실패: {e}")
    
    return None

def log_progress_note_to_sqlite(user_info, client_info, note_content, care_area_id, event_type_id, site):
    """Progress Note 작성을 SQLite에 로그"""
    if not USE_SQLITE:
        return
    
    try:
        conn = sqlite_integration.get_db_connection()
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
            client_info.get('PersonId'),
            client_info.get('ClientName'),
            care_area_id,
            event_type_id,
            note_content,
            site
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Progress Note SQLite 로그 실패: {e}")
'''
    
    with open('integration_patch.py', 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    print("✅ integration_patch.py 생성 완료")
    print("이 코드를 app.py에 통합하여 SQLite 기능을 활성화할 수 있습니다.")


def create_performance_comparison():
    """성능 비교 스크립트 생성"""
    print("\n성능 비교 스크립트 생성")
    print("-" * 40)
    
    comparison_code = '''#!/usr/bin/env python3
"""
성능 비교: JSON vs SQLite
"""

import time
import json
import os
from app_integration import FlaskAppIntegration

def compare_performance():
    print("=" * 50)
    print("성능 비교: JSON vs SQLite")
    print("=" * 50)
    
    integration = FlaskAppIntegration()
    
    # 1. 클라이언트 조회 성능 비교
    print("\\n1. 클라이언트 조회 성능")
    print("-" * 30)
    
    # JSON 방식
    json_times = []
    json_file = 'data/parafield_gardens_client.json'
    
    if os.path.exists(json_file):
        for i in range(5):
            start_time = time.time()
            with open(json_file, 'r') as f:
                json_data = json.load(f)
            json_times.append((time.time() - start_time) * 1000)
        
        avg_json_time = sum(json_times) / len(json_times)
        print(f"JSON 파일 로드: {avg_json_time:.2f}ms (평균)")
    
    # SQLite 방식
    sqlite_times = []
    for i in range(5):
        start_time = time.time()
        clients = integration.get_clients_sqlite('Parafield Gardens')
        sqlite_times.append((time.time() - start_time) * 1000)
    
    avg_sqlite_time = sum(sqlite_times) / len(sqlite_times)
    print(f"SQLite 조회: {avg_sqlite_time:.2f}ms (평균)")
    
    if json_times:
        improvement = avg_json_time / avg_sqlite_time
        print(f"성능 개선: {improvement:.1f}배 빠름")
    
    # 2. 검색 성능 (SQLite만 가능)
    print("\\n2. 검색 성능 (새로운 기능)")
    print("-" * 30)
    
    search_times = []
    for search_term in ['Smith', 'A', 'John']:
        start_time = time.time()
        results = integration.get_clients_sqlite('Parafield Gardens', search_term)
        search_time = (time.time() - start_time) * 1000
        search_times.append(search_time)
        print(f"'{search_term}' 검색: {len(results)}명, {search_time:.2f}ms")
    
    avg_search_time = sum(search_times) / len(search_times)
    print(f"평균 검색 시간: {avg_search_time:.2f}ms")

if __name__ == "__main__":
    compare_performance()
'''
    
    with open('performance_comparison.py', 'w', encoding='utf-8') as f:
        f.write(comparison_code)
    
    print("✅ performance_comparison.py 생성 완료")


def main():
    """메인 실행 함수"""
    try:
        # 통합 클래스 초기화
        integration = FlaskAppIntegration()
        
        # 통합 테스트 실행
        success = integration.test_integration()
        
        if success:
            print("\n✅ Flask 앱 통합 테스트 성공!")
            
            # 통합 패치 생성
            create_integration_patch()
            
            # 성능 비교 스크립트 생성
            create_performance_comparison()
            
            print("\n📁 생성된 파일들:")
            print("  - app_integration.py (통합 클래스)")
            print("  - integration_patch.py (app.py 통합 코드)")
            print("  - performance_comparison.py (성능 비교)")
            
            print("\n다음 단계:")
            print("1. integration_patch.py의 코드를 app.py에 통합")
            print("2. 성능 비교 실행: python performance_comparison.py")
            print("3. 최종 테스트: python test_final_integration.py")
            
        else:
            print("\n❌ 통합 테스트 실패")
            print("문제를 해결한 후 다시 시도하세요.")
        
    except Exception as e:
        print(f"\n❌ 통합 실행 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
