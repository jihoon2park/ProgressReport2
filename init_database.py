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
        logger.info("🚀 Progress Report System 데이터베이스 초기화 시작")
        
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
            
            logger.info("✅ 데이터베이스 초기화 완료!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
            return False
    
    def backup_existing_database(self):
        """기존 데이터베이스 백업"""
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.db_path, backup_path)
            logger.info(f"📦 기존 데이터베이스를 {backup_path}로 백업했습니다.")
    
    def verify_schema_file(self):
        """스키마 파일 존재 확인"""
        if not os.path.exists(self.schema_file):
            raise FileNotFoundError(f"스키마 파일 {self.schema_file}를 찾을 수 없습니다.")
        
        logger.info(f"📋 스키마 파일 {self.schema_file} 확인 완료")
    
    def create_database_schema(self):
        """데이터베이스 스키마 생성"""
        logger.info("🏗️ 데이터베이스 스키마 생성 중...")
        
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
                        logger.debug(f"SQL 문 {i+1} 실행 완료")
                    except sqlite3.Error as e:
                        if "already exists" not in str(e):
                            logger.error(f"SQL 문 {i+1} 실행 실패: {e}")
                            logger.error(f"문제가 된 SQL: {statement[:100]}...")
                            raise
            
            conn.commit()
            logger.info("✅ 스키마 생성 완료")
            
        finally:
            conn.close()
    
    def parse_sql_statements(self, sql_content):
        """SQL 문들을 파싱하여 개별 문장으로 분리"""
        # 더 간단한 방법으로 SQL 문 분리
        statements = []
        
        # 주석 제거
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        # 세미콜론으로 문장 분리
        full_content = ' '.join(lines)
        raw_statements = full_content.split(';')
        
        for statement in raw_statements:
            statement = statement.strip()
            if statement:
                statements.append(statement + ';')
        
        return statements
    
    def insert_initial_data(self):
        """초기 데이터 삽입"""
        logger.info("📝 초기 데이터 삽입 중...")
        
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
            logger.info("✅ 초기 데이터 삽입 완료")
            
        except Exception as e:
            logger.error(f"초기 데이터 삽입 실패: {e}")
            raise
        finally:
            conn.close()
    
    def verify_database(self):
        """데이터베이스 구조 검증"""
        logger.info("🔍 데이터베이스 구조 검증 중...")
        
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
            
            logger.info(f"📊 생성된 테이블: {len(tables)}개")
            for table in tables:
                logger.info(f"  ✓ {table}")
            
            # 누락된 테이블 확인
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"⚠️ 누락된 테이블: {missing_tables}")
            
            # 각 테이블의 레코드 수 확인
            logger.info("📈 테이블별 레코드 수:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  {table}: {count}개")
            
            logger.info("✅ 데이터베이스 검증 완료")
            
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
    print("🚀 Progress Report System - 데이터베이스 초기화")
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
            print("📊 데이터베이스 정보")
            print("=" * 60)
            print(f"SQLite 버전: {db_info['sqlite_version']}")
            print(f"데이터베이스 크기: {db_info['db_size_mb']} MB")
            print(f"테이블 수: {db_info['table_count']}개")
            print(f"파일 경로: {db_info['db_path']}")
        
        print("\n✅ 데이터베이스 초기화가 성공적으로 완료되었습니다!")
        print("다음 단계: Phase 1 마이그레이션을 실행하세요.")
        print("명령어: python migration_phase1.py")
        
    else:
        print("\n❌ 데이터베이스 초기화에 실패했습니다.")
        print("migration.log 파일을 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
