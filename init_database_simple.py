

#!/usr/bin/env python3
"""
Progress Report System - 간단한 데이터베이스 초기화
Week 1 - Day 1: 스키마 생성 및 초기 설정
"""

import sqlite3
import os
import sys
from datetime import datetime

class SimpleDBInitializer:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
    def initialize_database(self):
        """데이터베이스 초기화"""
        print("데이터베이스 초기화 시작...")
        
        try:
            # 기존 DB 백업
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.db_path, backup_path)
                print(f"기존 DB를 {backup_path}로 백업")
            
            # 스키마 실행
            self.create_schema()
            
            # 초기 데이터
            self.insert_initial_data()
            
            # 검증
            self.verify_database()
            
            print("데이터베이스 초기화 완료!")
            return True
            
        except Exception as e:
            print(f"초기화 실패: {e}")
            return False
    
    def create_schema(self):
        """스키마 생성"""
        print("스키마 생성 중...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 사용자 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    position VARCHAR(100),
                    location TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # FCM 토큰 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fcm_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id VARCHAR(100) NOT NULL,
                    token TEXT NOT NULL,
                    device_info VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    UNIQUE(user_id, token)
                )
            ''')
            
            # 접근 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    username VARCHAR(50),
                    display_name VARCHAR(200),
                    role VARCHAR(20),
                    position VARCHAR(100),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    page_accessed VARCHAR(200),
                    session_duration INTEGER
                )
            ''')
            
            # Progress Note 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress_note_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    username VARCHAR(50),
                    display_name VARCHAR(200),
                    role VARCHAR(20),
                    position VARCHAR(100),
                    client_id INTEGER,
                    client_name VARCHAR(200),
                    care_area_id INTEGER,
                    event_type_id INTEGER,
                    note_content TEXT,
                    site VARCHAR(100)
                )
            ''')
            
            # 클라이언트 캐시 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    client_name VARCHAR(200) NOT NULL,
                    preferred_name VARCHAR(100),
                    title VARCHAR(10),
                    first_name VARCHAR(100),
                    middle_name VARCHAR(100),
                    surname VARCHAR(100),
                    gender VARCHAR(10),
                    birth_date DATE,
                    admission_date DATE,
                    room_name VARCHAR(50),
                    room_number VARCHAR(10),
                    wing_name VARCHAR(100),
                    location_id INTEGER,
                    location_name VARCHAR(200),
                    main_client_service_id INTEGER,
                    original_person_id INTEGER,
                    client_record_id INTEGER,
                    site VARCHAR(100) NOT NULL,
                    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    UNIQUE(person_id, site)
                )
            ''')
            
            # 케어 영역 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS care_areas (
                    id INTEGER PRIMARY KEY,
                    description VARCHAR(500) NOT NULL,
                    is_archived BOOLEAN DEFAULT 0,
                    is_external BOOLEAN DEFAULT 0,
                    last_updated_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 이벤트 타입 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_types (
                    id INTEGER PRIMARY KEY,
                    description VARCHAR(500) NOT NULL,
                    color_argb INTEGER,
                    is_archived BOOLEAN DEFAULT 0,
                    is_external BOOLEAN DEFAULT 0,
                    last_updated_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 사이트 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_name VARCHAR(100) UNIQUE NOT NULL,
                    server_ip VARCHAR(50),
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 동기화 상태 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type VARCHAR(50) NOT NULL,
                    site VARCHAR(100),
                    last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    records_synced INTEGER DEFAULT 0,
                    UNIQUE(data_type, site)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_site ON clients_cache(site)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_person_id ON clients_cache(person_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_logs_timestamp ON progress_note_logs(timestamp)')
            
            conn.commit()
            print("스키마 생성 완료")
            
        finally:
            conn.close()
    
    def insert_initial_data(self):
        """초기 데이터 삽입"""
        print("초기 데이터 삽입 중...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 사이트 정보
            sites = [
                ('Parafield Gardens', '192.168.1.11:8080', 'Edenfield Family Care - Parafield Gardens'),
                ('Nerrilda', None, 'Nerrilda Care Facility'),
                ('Ramsay', None, 'Ramsay Care Center'),
                ('Yankalilla', None, 'Yankalilla Care Home')
            ]
            
            for site_name, server_ip, description in sites:
                cursor.execute('''
                    INSERT OR IGNORE INTO sites (site_name, server_ip, description)
                    VALUES (?, ?, ?)
                ''', (site_name, server_ip, description))
            
            # 동기화 상태
            sync_types = [
                ('users', None),
                ('fcm_tokens', None),
                ('carearea', None),
                ('eventtype', None),
                ('clients', 'Parafield Gardens'),
                ('clients', 'Nerrilda'),
                ('clients', 'Ramsay'),
                ('clients', 'Yankalilla')
            ]
            
            for data_type, site in sync_types:
                cursor.execute('''
                    INSERT OR IGNORE INTO sync_status (data_type, site, sync_status, records_synced)
                    VALUES (?, ?, 'pending', 0)
                ''', (data_type, site))
            
            conn.commit()
            print("초기 데이터 삽입 완료")
            
        finally:
            conn.close()
    
    def verify_database(self):
        """데이터베이스 검증"""
        print("데이터베이스 검증 중...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 테이블 목록
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"생성된 테이블: {len(tables)}개")
            for table in tables:
                print(f"  - {table}")
            
            # 각 테이블 레코드 수
            print("\n테이블별 레코드 수:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count}개")
            
        finally:
            conn.close()


def main():
    print("=" * 50)
    print("Progress Report System - DB 초기화")
    print("Week 1 - Day 1: Foundation Setup")
    print("=" * 50)
    
    initializer = SimpleDBInitializer()
    success = initializer.initialize_database()
    
    if success:
        print("\n초기화 성공! 다음 단계를 실행하세요:")
        print("python migration_phase1.py")
    else:
        print("\n초기화 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()
