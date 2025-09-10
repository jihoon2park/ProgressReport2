#!/usr/bin/env python3
"""
Progress Report System - Phase 2 마이그레이션
Week 1 - Day 3-4: 케어 영역, 이벤트 타입 마이그레이션
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

class Phase2Migration:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def run_phase2_migration(self):
        """Phase 2 마이그레이션 실행"""
        print("Phase 2 마이그레이션 시작")
        print("대상: 케어 영역, 이벤트 타입 데이터")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # 1. 케어 영역 마이그레이션
            self.migrate_care_areas(conn)
            
            # 2. 이벤트 타입 마이그레이션
            self.migrate_event_types(conn)
            
            # 3. 결과 요약
            self.print_migration_summary(conn)
            
            conn.close()
            print("Phase 2 마이그레이션 완료!")
            return True
            
        except Exception as e:
            print(f"Phase 2 마이그레이션 실패: {e}")
            return False
    
    def migrate_care_areas(self, conn):
        """케어 영역 데이터 마이그레이션"""
        print("케어 영역 데이터 마이그레이션 시작...")
        
        care_area_file = 'data/carearea.json'
        if not os.path.exists(care_area_file):
            print(f"케어 영역 파일 {care_area_file}을 찾을 수 없습니다.")
            return
        
        try:
            with open(care_area_file, 'r', encoding='utf-8') as f:
                care_areas = json.load(f)
            
            cursor = conn.cursor()
            migrated_count = 0
            
            for area in care_areas:
                try:
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
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"케어 영역 {area.get('Id')} 마이그레이션 실패: {e}")
            
            conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'carearea'
            ''', (datetime.now().isoformat(), migrated_count))
            
            conn.commit()
            print(f"케어 영역 {migrated_count}개 마이그레이션 완료")
            
        except Exception as e:
            print(f"케어 영역 마이그레이션 실패: {e}")
    
    def migrate_event_types(self, conn):
        """이벤트 타입 데이터 마이그레이션"""
        print("이벤트 타입 데이터 마이그레이션 시작...")
        
        event_type_file = 'data/eventtype.json'
        if not os.path.exists(event_type_file):
            print(f"이벤트 타입 파일 {event_type_file}을 찾을 수 없습니다.")
            return
        
        try:
            with open(event_type_file, 'r', encoding='utf-8') as f:
                event_types = json.load(f)
            
            cursor = conn.cursor()
            migrated_count = 0
            
            for event in event_types:
                try:
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
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"이벤트 타입 {event.get('Id')} 마이그레이션 실패: {e}")
            
            conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'eventtype'
            ''', (datetime.now().isoformat(), migrated_count))
            
            conn.commit()
            print(f"이벤트 타입 {migrated_count}개 마이그레이션 완료")
            
        except Exception as e:
            print(f"이벤트 타입 마이그레이션 실패: {e}")
    
    def print_migration_summary(self, conn):
        """마이그레이션 결과 요약"""
        print("\nPhase 2 마이그레이션 결과 요약")
        print("=" * 40)
        
        cursor = conn.cursor()
        
        # 각 테이블의 레코드 수 확인
        tables = ['care_areas', 'event_types']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table}: {count:,}개 레코드")
            except sqlite3.Error as e:
                print(f"{table} 테이블 조회 실패: {e}")
        
        # 동기화 상태 확인
        print("\n동기화 상태:")
        cursor.execute('''
            SELECT data_type, sync_status, records_synced, last_sync_time 
            FROM sync_status 
            WHERE data_type IN ('carearea', 'eventtype')
            ORDER BY data_type
        ''')
        
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]}개)")
        
        # 샘플 데이터 확인
        print("\n샘플 케어 영역 (상위 5개):")
        cursor.execute('SELECT id, description FROM care_areas WHERE is_archived = 0 ORDER BY id LIMIT 5')
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        print("\n샘플 이벤트 타입 (상위 5개):")
        cursor.execute('SELECT id, description FROM event_types WHERE is_archived = 0 ORDER BY id LIMIT 5')
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")


def main():
    print("=" * 50)
    print("Progress Report System - Phase 2 마이그레이션")
    print("Week 1 - Day 3-4: 케어 영역, 이벤트 타입")
    print("=" * 50)
    
    try:
        migration = Phase2Migration()
        success = migration.run_phase2_migration()
        
        if success:
            print("\nPhase 2 마이그레이션이 성공적으로 완료되었습니다!")
            print("다음 단계: 테스트 및 검증을 실행하세요.")
            print("명령어: python test_week1.py")
        else:
            print("\nPhase 2 마이그레이션에 실패했습니다.")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n파일을 찾을 수 없습니다: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
