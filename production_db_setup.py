#!/usr/bin/env python3
"""
Production 서버용 SQLite 데이터베이스 설정 스크립트
- 데이터베이스 존재 여부 확인
- 필요시 초기화 실행
- 권한 및 보안 설정
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionDBSetup:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = Path(db_path)
        self.schema_file = Path('database_schema.sql')
    
    def check_database_exists(self):
        """데이터베이스 파일 존재 확인"""
        return self.db_path.exists() and self.db_path.stat().st_size > 0
    
    def check_database_structure(self):
        """데이터베이스 구조 검증"""
        if not self.check_database_exists():
            return False
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 필수 테이블 존재 확인
            required_tables = [
                'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
                'clients_cache', 'care_areas', 'event_types'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            conn.close()
            
            if missing_tables:
                logger.warning(f"누락된 테이블: {missing_tables}")
                return False
            
            logger.info("✅ 데이터베이스 구조 검증 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 구조 검증 실패: {e}")
            return False
    
    def initialize_database(self):
        """데이터베이스 초기화"""
        logger.info("🗄️ 데이터베이스 초기화 시작")
        
        try:
            # 스키마 파일 확인
            if not self.schema_file.exists():
                logger.error(f"스키마 파일 {self.schema_file}를 찾을 수 없습니다.")
                return False
            
            # 스키마 실행
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # SQL 문 실행
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        if "already exists" not in str(e):
                            logger.error(f"SQL 실행 실패: {e}")
                            raise
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 데이터베이스 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            return False
    
    def setup_production_database(self):
        """Production 데이터베이스 설정"""
        logger.info("🚀 Production 데이터베이스 설정 시작")
        
        # 1. 데이터베이스 존재 여부 확인
        if self.check_database_exists():
            logger.info("기존 데이터베이스 발견")
            
            # 2. 구조 검증
            if self.check_database_structure():
                logger.info("✅ 기존 데이터베이스 검증 완료")
                return True
            else:
                logger.warning("⚠️ 데이터베이스 구조 문제 발견 - 재초기화 필요")
        else:
            logger.info("데이터베이스가 존재하지 않음 - 새로 생성")
        
        # 3. 데이터베이스 초기화
        if not self.initialize_database():
            logger.error("❌ 데이터베이스 초기화 실패")
            return False
        
        # 4. 권한 설정 (Unix 계열 시스템에서만)
        if os.name != 'nt':  # Windows가 아닌 경우
            try:
                os.chmod(str(self.db_path), 0o664)  # rw-rw-r--
                logger.info("✅ 데이터베이스 파일 권한 설정 완료")
            except Exception as e:
                logger.warning(f"권한 설정 실패: {e}")
        
        logger.info("🎉 Production 데이터베이스 설정 완료!")
        return True
    
    def get_database_info(self):
        """데이터베이스 정보 조회"""
        if not self.check_database_exists():
            return None
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 테이블 수
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            # 파일 크기
            file_size = self.db_path.stat().st_size / (1024 * 1024)  # MB
            
            # SQLite 버전
            cursor.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'path': str(self.db_path),
                'size_mb': round(file_size, 2),
                'table_count': table_count,
                'sqlite_version': sqlite_version
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 정보 조회 실패: {e}")
            return None


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🏭 Production SQLite 데이터베이스 설정")
    print("=" * 60)
    
    setup = ProductionDBSetup()
    
    # 데이터베이스 설정 실행
    success = setup.setup_production_database()
    
    if success:
        # 데이터베이스 정보 출력
        db_info = setup.get_database_info()
        if db_info:
            print("\n📊 데이터베이스 정보:")
            print(f"  파일 경로: {db_info['path']}")
            print(f"  파일 크기: {db_info['size_mb']} MB")
            print(f"  테이블 수: {db_info['table_count']}개")
            print(f"  SQLite 버전: {db_info['sqlite_version']}")
        
        print("\n✅ Production 데이터베이스 설정 완료!")
        print("이제 웹 애플리케이션을 시작할 수 있습니다.")
        
    else:
        print("\n❌ Production 데이터베이스 설정 실패!")
        print("로그를 확인하고 문제를 해결하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
