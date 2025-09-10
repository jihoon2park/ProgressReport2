#!/usr/bin/env python3
"""
프로덕션 환경 자동 설정 스크립트
DB 초기화, API 키 마이그레이션, FCM 설정 등을 자동으로 수행
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_exists():
    """데이터베이스 파일 존재 여부 확인"""
    return os.path.exists('progress_report.db')

def initialize_database():
    """데이터베이스 초기화"""
    try:
        from init_database import DatabaseInitializer
        initializer = DatabaseInitializer()
        success = initializer.initialize_database()
        
        if success:
            logger.info("✅ 데이터베이스 초기화 완료")
            return True
        else:
            logger.error("❌ 데이터베이스 초기화 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 중 오류: {str(e)}")
        return False

def migrate_api_keys():
    """API 키 마이그레이션 (하드코딩된 키를 DB로 이동)"""
    try:
        from migrate_hardcoded_keys_to_db import migrate_hardcoded_keys
        if migrate_hardcoded_keys():
            logger.info("✅ API 키 마이그레이션 완료")
            return True
        else:
            logger.error("❌ API 키 마이그레이션 실패")
            return False
    except Exception as e:
        logger.error(f"❌ API 키 마이그레이션 중 오류: {str(e)}")
        return False

def setup_directories():
    """필요한 디렉토리 생성"""
    directories = ['logs', 'data', 'instance']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"📁 디렉토리 생성: {directory}")

def verify_database_tables():
    """데이터베이스 테이블 검증"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 필수 테이블 확인
        required_tables = [
            'users', 'api_keys', 'fcm_tokens', 'progress_notes_cache',
            'progress_notes_sync', 'escalation_policies', 'escalation_steps'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.warning(f"⚠️ 누락된 테이블: {missing_tables}")
            return False
        else:
            logger.info("✅ 모든 필수 테이블이 존재합니다")
            return True
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 검증 중 오류: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """메인 실행 함수"""
    logger.info("🚀 프로덕션 환경 설정 시작")
    
    # 1. 디렉토리 설정
    setup_directories()
    
    # 2. 데이터베이스 초기화
    if not check_database_exists():
        logger.info("📊 데이터베이스가 없습니다. 초기화를 시작합니다...")
        if not initialize_database():
            logger.error("❌ 데이터베이스 초기화 실패. 프로덕션 설정을 중단합니다.")
            sys.exit(1)
    else:
        logger.info("📊 기존 데이터베이스가 발견되었습니다.")
    
    # 3. API 키 마이그레이션
    migrate_api_keys()
    
    # 4. 데이터베이스 검증
    if not verify_database_tables():
        logger.error("❌ 데이터베이스 검증 실패")
        sys.exit(1)
    
    logger.info("✅ 프로덕션 환경 설정 완료!")
    logger.info("🎉 애플리케이션을 시작할 수 있습니다.")

if __name__ == "__main__":
    main()
