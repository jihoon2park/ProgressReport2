#!/usr/bin/env python3
"""
DB to JSON Migration Script
SQLite DB의 모든 데이터를 JSON 파일로 마이그레이션
"""

import sqlite3
import json
import os
from datetime import datetime
from json_data_manager import JSONDataManager

def migrate_database_to_json(db_path: str = 'progress_report.db'):
    """DB 데이터를 JSON 파일로 마이그레이션"""
    print("🔄 DB to JSON 마이그레이션 시작...")
    
    # JSON 데이터 매니저 초기화
    json_manager = JSONDataManager()
    
    try:
        # DB 연결
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ===========================================
        # 1. 사용자 데이터 마이그레이션
        # ===========================================
        print("👥 사용자 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM users")
            users = []
            for row in cursor.fetchall():
                user_data = {
                    'id': row['id'],
                    'username': row['username'],
                    'password_hash': row['password_hash'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'role': row['role'],
                    'position': row['position'],
                    'location': row['location'],
                    'is_active': bool(row['is_active']),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                users.append(user_data)
            
            json_manager._save_json(
                json_manager._get_file_path("users", "users.json"), 
                users
            )
            print(f"✅ 사용자 {len(users)}명 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 사용자 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 2. FCM 토큰 데이터 마이그레이션
        # ===========================================
        print("📱 FCM 토큰 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM fcm_tokens")
            tokens = []
            for row in cursor.fetchall():
                token_data = {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'token': row['token'],
                    'device_info': row['device_info'],
                    'created_at': row['created_at'],
                    'last_used': row['last_used'],
                    'is_active': bool(row['is_active'])
                }
                tokens.append(token_data)
            
            json_manager._save_json(
                json_manager._get_file_path("fcm", "tokens.json"), 
                tokens
            )
            print(f"✅ FCM 토큰 {len(tokens)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ FCM 토큰 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 3. 접근 로그 데이터 마이그레이션
        # ===========================================
        print("📊 접근 로그 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 1000")
            access_logs = []
            for row in cursor.fetchall():
                log_data = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'display_name': row['display_name'],
                    'role': row['role'],
                    'position': row['position'],
                    'ip_address': row['ip_address'],
                    'user_agent': row['user_agent'],
                    'page_accessed': row['page_accessed'],
                    'session_duration': row['session_duration']
                }
                access_logs.append(log_data)
            
            json_manager._save_json(
                json_manager._get_file_path("logs", "access_logs.json"), 
                access_logs
            )
            print(f"✅ 접근 로그 {len(access_logs)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 접근 로그 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 4. Progress Note 로그 데이터 마이그레이션
        # ===========================================
        print("📝 Progress Note 로그 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM progress_note_logs ORDER BY timestamp DESC LIMIT 1000")
            progress_logs = []
            for row in cursor.fetchall():
                log_data = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'client_id': row['client_id'],
                    'client_name': row['client_name'],
                    'site': row['site'],
                    'action': row['action'],
                    'note_id': row['note_id'],
                    'details': row['details']
                }
                progress_logs.append(log_data)
            
            json_manager._save_json(
                json_manager._get_file_path("logs", "progress_note_logs.json"), 
                progress_logs
            )
            print(f"✅ Progress Note 로그 {len(progress_logs)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ Progress Note 로그 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 5. 클라이언트 캐시 데이터 마이그레이션
        # ===========================================
        print("👤 클라이언트 캐시 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT DISTINCT site FROM clients_cache")
            sites = [row[0] for row in cursor.fetchall()]
            
            for site in sites:
                cursor.execute("SELECT * FROM clients_cache WHERE site = ?", (site,))
                clients = []
                for row in cursor.fetchall():
                    client_data = {
                        'id': row['id'],
                        'person_id': row['person_id'],
                        'first_name': row['first_name'],
                        'last_name': row['last_name'],
                        'date_of_birth': row['date_of_birth'],
                        'site': row['site'],
                        'cached_at': row['cached_at'],
                        'is_active': bool(row['is_active'])
                    }
                    clients.append(client_data)
                
                filename = f"clients_{site.replace(' ', '_').lower()}.json"
                json_manager._save_json(
                    json_manager._get_file_path("cache", filename), 
                    clients
                )
                print(f"  ✅ {site}: {len(clients)}명 클라이언트 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 클라이언트 캐시 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 6. 케어 영역 데이터 마이그레이션
        # ===========================================
        print("🏥 케어 영역 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM care_areas")
            care_areas = []
            for row in cursor.fetchall():
                care_area_data = {
                    'id': row['id'],
                    'care_area_id': row['care_area_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'is_archived': bool(row['is_archived']),
                    'cached_at': row['cached_at']
                }
                care_areas.append(care_area_data)
            
            json_manager._save_json(
                json_manager._get_file_path("cache", "care_areas.json"), 
                care_areas
            )
            print(f"✅ 케어 영역 {len(care_areas)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 케어 영역 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 7. 이벤트 타입 데이터 마이그레이션
        # ===========================================
        print("📋 이벤트 타입 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM event_types")
            event_types = []
            for row in cursor.fetchall():
                event_type_data = {
                    'id': row['id'],
                    'event_type_id': row['event_type_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'is_archived': bool(row['is_archived']),
                    'cached_at': row['cached_at']
                }
                event_types.append(event_type_data)
            
            json_manager._save_json(
                json_manager._get_file_path("cache", "event_types.json"), 
                event_types
            )
            print(f"✅ 이벤트 타입 {len(event_types)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 이벤트 타입 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 8. 인시던트 캐시 데이터 마이그레이션
        # ===========================================
        print("🚨 인시던트 캐시 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT DISTINCT site FROM incidents_cache")
            sites = [row[0] for row in cursor.fetchall()]
            
            for site in sites:
                cursor.execute("SELECT * FROM incidents_cache WHERE site = ?", (site,))
                incidents = []
                for row in cursor.fetchall():
                    incident_data = {
                        'id': row['id'],
                        'incident_id': row['incident_id'],
                        'client_id': row['client_id'],
                        'client_name': row['client_name'],
                        'incident_date': row['incident_date'],
                        'incident_type': row['incident_type'],
                        'description': row['description'],
                        'site': row['site'],
                        'cached_at': row['cached_at']
                    }
                    incidents.append(incident_data)
                
                filename = f"incidents_{site.replace(' ', '_').lower()}.json"
                json_manager._save_json(
                    json_manager._get_file_path("cache", filename), 
                    incidents
                )
                print(f"  ✅ {site}: {len(incidents)}개 인시던트 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 인시던트 캐시 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 9. 사이트 데이터 마이그레이션
        # ===========================================
        print("🏢 사이트 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM sites")
            sites = []
            for row in cursor.fetchall():
                site_data = {
                    'id': row['id'],
                    'site_name': row['site_name'],
                    'server_ip': row['server_ip'],
                    'description': row['description'],
                    'is_active': bool(row['is_active']),
                    'created_at': row['created_at']
                }
                sites.append(site_data)
            
            json_manager._save_json(
                json_manager._get_file_path("system", "sites.json"), 
                sites
            )
            print(f"✅ 사이트 {len(sites)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 사이트 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 10. 동기화 상태 데이터 마이그레이션
        # ===========================================
        print("🔄 동기화 상태 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM sync_status")
            sync_status = []
            for row in cursor.fetchall():
                sync_data = {
                    'id': row['id'],
                    'data_type': row['data_type'],
                    'site': row['site'],
                    'sync_status': row['sync_status'],
                    'last_sync_time': row['last_sync_time'],
                    'records_synced': row['records_synced'],
                    'error_message': row['error_message']
                }
                sync_status.append(sync_data)
            
            json_manager._save_json(
                json_manager._get_file_path("system", "sync_status.json"), 
                sync_status
            )
            print(f"✅ 동기화 상태 {len(sync_status)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ 동기화 상태 데이터 마이그레이션 실패: {e}")
        
        # ===========================================
        # 11. API 키 데이터 마이그레이션
        # ===========================================
        print("🔑 API 키 데이터 마이그레이션 중...")
        try:
            cursor.execute("SELECT * FROM api_keys")
            api_keys = []
            for row in cursor.fetchall():
                api_key_data = {
                    'id': row['id'],
                    'site_name': row['site_name'],
                    'api_key': row['api_key'],
                    'server_url': row['server_url'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                api_keys.append(api_key_data)
            
            json_manager._save_json(
                json_manager._get_file_path("api_keys", "api_keys.json"), 
                api_keys
            )
            print(f"✅ API 키 {len(api_keys)}개 마이그레이션 완료")
        except Exception as e:
            print(f"❌ API 키 데이터 마이그레이션 실패: {e}")
        
        print("\n🎉 DB to JSON 마이그레이션 완료!")
        
        # 마이그레이션 결과 요약
        data_info = json_manager.get_data_info()
        print("\n📊 마이그레이션 결과:")
        for key, value in data_info.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
    finally:
        conn.close()

def main():
    print("🔄 DB to JSON 마이그레이션 도구")
    print("=" * 50)
    
    db_path = input("DB 파일 경로를 입력하세요 (기본값: progress_report.db): ").strip()
    if not db_path:
        db_path = "progress_report.db"
    
    if not os.path.exists(db_path):
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return
    
    print(f"📁 대상 DB: {db_path}")
    
    # 백업 생성
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 백업 생성: {backup_path}")
    except Exception as e:
        print(f"❌ 백업 생성 실패: {e}")
        return
    
    # 마이그레이션 실행
    migrate_database_to_json(db_path)
    
    print(f"\n📄 JSON 파일들이 'data' 디렉토리에 저장되었습니다.")
    print("⚠️  마이그레이션 완료 후 DB 파일을 삭제할 수 있습니다.")

if __name__ == "__main__":
    main()
