#!/usr/bin/env python3
"""
Progress Report System - 데이터베이스 초기화
Week 1 - Day 1: 스키마 생성 및 초기 설정
"""

import sqlite3
import os
import sys
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.schema_file = 'database_schema.sql'
        
    def initialize_database(self):
        """데이터베이스 초기화 실행"""
        logger.info("🚀 Starting Progress Report System database initialization")
        
        try:
            # 1. 기존 데이터베이스 백업 (있다면)
            self.backup_existing_database()
            
            # 2. 스키마 파일 확인
            self.verify_schema_file()
            
            # 3. 데이터베이스 생성 및 스키마 적용
            self.create_database_schema()
            
            # 4. 초기 데이터 삽입
            self.insert_initial_data()
            
            # 5. 데이터베이스 검증
            self.verify_database()
            
            logger.info("✅ Database initialization completed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def backup_existing_database(self):
        """기존 데이터베이스 백업"""
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.db_path, backup_path)
            logger.info(f"📦 Backed up existing database to {backup_path}.")
    
    def verify_schema_file(self):
        """스키마 파일 존재 확인"""
        if not os.path.exists(self.schema_file):
            raise FileNotFoundError(f"Schema file not found: {self.schema_file}")
        
        logger.info(f"📋 Schema file verified: {self.schema_file}")
    
    def create_database_schema(self):
        """데이터베이스 스키마 생성"""
        logger.info("🏗️ Creating database schema...")
        
        # 스키마 파일 읽기
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # 데이터베이스 연결 및 스키마 실행
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # SQL 문들을 분리해서 실행
            statements = self.parse_sql_statements(schema_sql)
            
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        logger.debug(f"SQL statement {i+1} executed")
                    except sqlite3.Error as e:
                        if "already exists" not in str(e):
                            logger.error(f"SQL statement {i+1} failed: {e}")
                            logger.error(f"Failed SQL statement: {statement[:100]}...")
                            raise
            
            conn.commit()
            logger.info("✅ Schema creation completed")
            
        finally:
            conn.close()
    
    def parse_sql_statements(self, sql_content):
        """
        SQL 문들을 파싱하여 개별 문장으로 분리.

        NOTE: 기존 구현은 모든 줄을 하나로 합쳐 inline `--` 주석이 이후 전체를
        주석 처리해버려 "incomplete input" / 테이블 누락을 유발할 수 있음.
        """
        statements: list[str] = []
        buf: list[str] = []

        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False

        i = 0
        n = len(sql_content)
        while i < n:
            ch = sql_content[i]
            nxt = sql_content[i + 1] if i + 1 < n else ''

            if in_line_comment:
                if ch == '\n':
                    in_line_comment = False
                    buf.append(ch)
                i += 1
                continue

            if in_block_comment:
                if ch == '*' and nxt == '/':
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if not in_single_quote and not in_double_quote:
                if ch == '-' and nxt == '-':
                    in_line_comment = True
                    i += 2
                    continue
                if ch == '/' and nxt == '*':
                    in_block_comment = True
                    i += 2
                    continue

            if ch == "'" and not in_double_quote:
                if in_single_quote and nxt == "'":  # escaped single quote ('')
                    buf.append(ch)
                    buf.append(nxt)
                    i += 2
                    continue
                in_single_quote = not in_single_quote
                buf.append(ch)
                i += 1
                continue

            if ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                buf.append(ch)
                i += 1
                continue

            if ch == ';' and not in_single_quote and not in_double_quote:
                stmt = ''.join(buf).strip()
                if stmt:
                    statements.append(stmt + ';')
                buf = []
                i += 1
                continue

            buf.append(ch)
            i += 1

        tail = ''.join(buf).strip()
        if tail:
            statements.append(tail)

        return statements
    
    def insert_initial_data(self):
        """초기 데이터 삽입"""
        logger.info("📝 Inserting initial data...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 기본 사이트 정보 삽입
            sites_data = [
                ('Parafield Gardens', '192.168.1.11:8080', 'Edenfield Family Care - Parafield Gardens'),
                ('Nerrilda', None, 'Nerrilda Care Facility'),
                ('Ramsay', None, 'Ramsay Care Center'),
                ('Yankalilla', None, 'Yankalilla Care Home')
            ]
            
            for site_name, server_ip, description in sites_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO sites (site_name, server_ip, description)
                    VALUES (?, ?, ?)
                ''', (site_name, server_ip, description))
            
            # 기본 동기화 상태 레코드
            sync_data = [
                ('clients', 'Parafield Gardens'),
                ('clients', 'Nerrilda'),
                ('clients', 'Ramsay'),
                ('clients', 'Yankalilla'),
                ('carearea', None),
                ('eventtype', None),
                ('fcm_tokens', None),
                ('users', None)
            ]
            
            for data_type, site in sync_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO sync_status (data_type, site, sync_status, records_synced)
                    VALUES (?, ?, 'pending', 0)
                ''', (data_type, site))
            
            conn.commit()
            logger.info("✅ Initial data insertion completed")
            
        except Exception as e:
            logger.error(f"Initial data insertion failed: {e}")
            raise
        finally:
            conn.close()
    
    def verify_database(self):
        """데이터베이스 구조 검증"""
        logger.info("🔍 Verifying database structure...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 테이블 목록 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
                'clients_cache', 'care_areas', 'event_types', 'incidents_cache',
                'sites', 'sync_status', 'alarm_templates', 'alarm_recipients'
            ]
            
            logger.info(f"📊 Tables created: {len(tables)}")
            for table in tables:
                logger.info(f"  ✓ {table}")
            
            # 누락된 테이블 확인
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"⚠️ Missing tables: {missing_tables}")
            
            # 각 테이블의 레코드 수 확인
            logger.info("📈 Record count by table:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  {table}: {count}")
            
            logger.info("✅ Database verification completed")
            
        finally:
            conn.close()
    
    def get_database_info(self):
        """데이터베이스 정보 조회"""
        if not os.path.exists(self.db_path):
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 데이터베이스 버전
            cursor.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]
            
            # 데이터베이스 크기
            db_size = os.path.getsize(self.db_path)
            
            # 테이블 수
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            return {
                'sqlite_version': sqlite_version,
                'db_size_mb': round(db_size / 1024 / 1024, 2),
                'table_count': table_count,
                'db_path': self.db_path
            }
            
        finally:
            conn.close()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 Progress Report System - Database initialization")
    print("Week 1 - Day 1: Foundation Setup")
    print("=" * 60)
    
    initializer = DatabaseInitializer()
    
    # 초기화 실행
    success = initializer.initialize_database()
    
    if success:
        # 데이터베이스 정보 출력
        db_info = initializer.get_database_info()
        if db_info:
            print("\n" + "=" * 60)
            print("📊 Database info")
            print("=" * 60)
            print(f"SQLite version: {db_info['sqlite_version']}")
            print(f"Database size: {db_info['db_size_mb']} MB")
            print(f"Table count: {db_info['table_count']}")
            print(f"File path: {db_info['db_path']}")
        
        print("\n✅ Database initialization completed successfully!")
        print("Next step: run Phase 1 migration.")
        print("Command: python migration_phase1.py")
        
    else:
        print("\n❌ Database initialization failed.")
        print("Check the migration.log file.")
        sys.exit(1)


if __name__ == "__main__":
    main()
