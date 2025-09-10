#!/usr/bin/env python3
"""
Progress Report System - Phase 3 마이그레이션
Week 2 - Day 1-2: 클라이언트 데이터 캐시화
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

class Phase3Migration:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def run_phase3_migration(self):
        """Phase 3 마이그레이션 실행"""
        print("=" * 60)
        print("Progress Report System - Phase 3 마이그레이션")
        print("Week 2 - Day 1-2: 클라이언트 데이터 캐시화")
        print("=" * 60)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # 1. 각 사이트별 클라이언트 데이터 마이그레이션
            self.migrate_all_client_data(conn)
            
            # 2. 클라이언트 리스트 백업 데이터 처리
            self.migrate_client_list_backup(conn)
            
            # 3. 결과 요약 및 검증
            self.print_migration_summary(conn)
            
            conn.close()
            print("\nPhase 3 마이그레이션 완료!")
            return True
            
        except Exception as e:
            print(f"\nPhase 3 마이그레이션 실패: {e}")
            return False
    
    def migrate_all_client_data(self, conn):
        """모든 사이트의 클라이언트 데이터 마이그레이션"""
        print("\n클라이언트 데이터 마이그레이션 시작...")
        
        # 사이트별 파일 매핑
        site_files = [
            ('parafield_gardens_client.json', 'Parafield Gardens'),
            ('nerrilda_client.json', 'Nerrilda'),
            ('ramsay_client.json', 'Ramsay'),
            ('yankalilla_client.json', 'Yankalilla')
        ]
        
        total_migrated = 0
        
        for filename, site_name in site_files:
            count = self.migrate_site_clients(conn, filename, site_name)
            total_migrated += count
        
        print(f"전체 클라이언트 {total_migrated}명 마이그레이션 완료")
    
    def migrate_site_clients(self, conn, filename: str, site_name: str):
        """개별 사이트의 클라이언트 데이터 마이그레이션"""
        filepath = f'data/{filename}'
        
        if not os.path.exists(filepath):
            print(f"  ! {site_name}: 파일 {filename} 없음 (건너뜀)")
            return 0
        
        print(f"  {site_name} 클라이언트 데이터 처리 중...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                client_data = json.load(f)
            
            cursor = conn.cursor()
            migrated_count = 0
            
            # JSON 구조 파악
            if isinstance(client_data, dict) and 'client_info' in client_data:
                clients = client_data['client_info']
            elif isinstance(client_data, list):
                clients = client_data
            else:
                print(f"    ! 알 수 없는 JSON 구조: {type(client_data)}")
                return 0
            
            # 기존 사이트 데이터 정리
            cursor.execute('DELETE FROM clients_cache WHERE site = ?', (site_name,))
            
            # 새 데이터 삽입
            for client in clients:
                try:
                    # 필수 필드 확인
                    person_id = (client.get('PersonId') or 
                               client.get('MainClientServiceId') or 
                               client.get('ClientRecordId'))
                    
                    if not person_id:
                        continue
                    
                    client_name = (client.get('ClientName') or 
                                 f"{client.get('FirstName', '')} {client.get('Surname', '')}".strip() or
                                 client.get('PreferredName', 'Unknown'))
                    
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
                        site_name,
                        datetime.now().isoformat(),
                        True
                    ))
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"    ! 클라이언트 데이터 처리 실패: {e}")
            
            conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'clients' AND site = ?
            ''', (datetime.now().isoformat(), migrated_count, site_name))
            
            conn.commit()
            print(f"    ✓ {site_name}: {migrated_count}명 마이그레이션 완료")
            return migrated_count
            
        except Exception as e:
            print(f"    ✗ {site_name} 마이그레이션 실패: {e}")
            
            # 실패 상태 기록
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'failed', error_message = ?
                WHERE data_type = 'clients' AND site = ?
            ''', (datetime.now().isoformat(), str(e), site_name))
            conn.commit()
            
            return 0
    
    def migrate_client_list_backup(self, conn):
        """클라이언트 리스트 백업 데이터 마이그레이션"""
        print("\n클라이언트 리스트 백업 데이터 처리 중...")
        
        filepath = 'data/Client_list.json'
        if not os.path.exists(filepath):
            print("  ! Client_list.json 파일 없음 (건너뜀)")
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                clients = json.load(f)
            
            cursor = conn.cursor()
            backup_count = 0
            
            for client in clients:
                try:
                    person_id = client.get('PersonId')
                    if not person_id:
                        continue
                    
                    # 이미 존재하는 클라이언트인지 확인
                    cursor.execute('''
                        SELECT COUNT(*) FROM clients_cache 
                        WHERE person_id = ? AND site != 'Backup'
                    ''', (person_id,))
                    
                    if cursor.fetchone()[0] > 0:
                        continue  # 이미 다른 사이트에 존재함
                    
                    # 백업 데이터로 추가
                    cursor.execute('''
                        INSERT OR IGNORE INTO clients_cache 
                        (person_id, client_name, preferred_name, gender, birth_date,
                         room_name, wing_name, main_client_service_id, 
                         original_person_id, client_record_id, site, last_synced, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        person_id,
                        client.get('ClientName'),
                        client.get('PreferredName'),
                        client.get('Gender'),
                        client.get('BirthDate'),
                        client.get('RoomName'),
                        client.get('WingName'),
                        client.get('MainClientServiceId'),
                        client.get('OriginalPersonId'),
                        client.get('ClientRecordId'),
                        'Backup',
                        datetime.now().isoformat(),
                        True
                    ))
                    backup_count += 1
                    
                except Exception as e:
                    print(f"    ! 백업 데이터 처리 실패: {e}")
            
            conn.commit()
            print(f"  ✓ 백업 데이터 {backup_count}명 추가 완료")
            
        except Exception as e:
            print(f"  ✗ 백업 데이터 처리 실패: {e}")
    
    def print_migration_summary(self, conn):
        """마이그레이션 결과 요약"""
        print("\n" + "=" * 50)
        print("Phase 3 마이그레이션 결과 요약")
        print("=" * 50)
        
        cursor = conn.cursor()
        
        # 사이트별 클라이언트 수 확인
        cursor.execute('''
            SELECT site, COUNT(*) as count, MAX(last_synced) as last_sync
            FROM clients_cache 
            WHERE is_active = 1
            GROUP BY site
            ORDER BY site
        ''')
        
        total_clients = 0
        print("\n사이트별 클라이언트 수:")
        for row in cursor.fetchall():
            site, count, last_sync = row[0], row[1], row[2]
            print(f"  {site}: {count:,}명 (마지막 동기화: {last_sync[:19] if last_sync else 'N/A'})")
            total_clients += count
        
        print(f"\n전체 클라이언트: {total_clients:,}명")
        
        # 동기화 상태 확인
        print("\n동기화 상태:")
        cursor.execute('''
            SELECT data_type, site, sync_status, records_synced, error_message
            FROM sync_status 
            WHERE data_type = 'clients'
            ORDER BY site
        ''')
        
        for row in cursor.fetchall():
            data_type, site, status, records, error = row
            if status == 'success':
                print(f"  ✓ {site}: {status} ({records}개)")
            else:
                print(f"  ✗ {site}: {status}")
                if error:
                    print(f"    오류: {error}")
        
        # 성능 테스트
        print("\n성능 테스트:")
        self.run_performance_test(cursor)
        
        # 데이터 샘플 확인
        print("\n데이터 샘플 (각 사이트별 3명):")
        cursor.execute('''
            SELECT site, client_name, preferred_name, room_number
            FROM clients_cache 
            WHERE is_active = 1
            ORDER BY site, client_name
        ''')
        
        current_site = None
        count_per_site = 0
        
        for row in cursor.fetchall():
            site, name, preferred, room = row
            
            if current_site != site:
                current_site = site
                count_per_site = 0
                print(f"\n  {site}:")
            
            if count_per_site < 3:
                display_name = preferred or name
                room_info = f" (방: {room})" if room else ""
                print(f"    - {display_name}{room_info}")
                count_per_site += 1
    
    def run_performance_test(self, cursor):
        """간단한 성능 테스트"""
        import time
        
        # 사이트별 조회 테스트
        start_time = time.time()
        cursor.execute("SELECT * FROM clients_cache WHERE site = 'Parafield Gardens' AND is_active = 1")
        results = cursor.fetchall()
        query_time = (time.time() - start_time) * 1000
        
        print(f"  사이트별 조회: {len(results)}명, {query_time:.2f}ms")
        
        # 이름 검색 테스트
        start_time = time.time()
        cursor.execute("SELECT * FROM clients_cache WHERE client_name LIKE '%Smith%' AND is_active = 1")
        results = cursor.fetchall()
        search_time = (time.time() - start_time) * 1000
        
        print(f"  이름 검색: {len(results)}명, {search_time:.2f}ms")
        
        # 방 번호 검색 테스트
        start_time = time.time()
        cursor.execute("SELECT * FROM clients_cache WHERE room_number LIKE '1%' AND is_active = 1")
        results = cursor.fetchall()
        room_search_time = (time.time() - start_time) * 1000
        
        print(f"  방 번호 검색: {len(results)}명, {room_search_time:.2f}ms")


def main():
    try:
        migration = Phase3Migration()
        success = migration.run_phase3_migration()
        
        if success:
            print("\n✅ Phase 3 마이그레이션이 성공적으로 완료되었습니다!")
            print("다음 단계: 하이브리드 데이터 매니저 구현")
            print("명령어: python setup_hybrid_manager.py")
        else:
            print("\n❌ Phase 3 마이그레이션에 실패했습니다.")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
