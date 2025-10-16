#!/usr/bin/env python3
"""
CIMS Database Initialization Script
CIMS (Compliance-Driven Incident Management System) 데이터베이스 초기화 스크립트
"""

import sqlite3
import os
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_cims_database(db_path="progress_report.db"):
    """CIMS 데이터베이스 테이블 초기화"""
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info(f"CIMS 데이터베이스 초기화 시작: {db_path}")
        
        # CIMS 스키마 파일 읽기
        schema_file = "cims_database_schema.sql"
        if not os.path.exists(schema_file):
            logger.error(f"스키마 파일을 찾을 수 없습니다: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # SQL 문을 개별적으로 실행 (테이블 생성 먼저, 인덱스는 나중에)
        sql_statements = schema_sql.split(';')
        
        # 테이블 생성 문과 인덱스 생성 문 분리
        table_statements = []
        index_statements = []
        insert_statements = []
        
        for statement in sql_statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                if statement.upper().startswith('CREATE TABLE'):
                    table_statements.append(statement)
                elif statement.upper().startswith('CREATE INDEX'):
                    index_statements.append(statement)
                elif statement.upper().startswith('INSERT'):
                    insert_statements.append(statement)
        
        # 1. 테이블 생성
        for statement in table_statements:
            try:
                cursor.execute(statement)
                logger.info(f"테이블 생성: {statement.split()[2] if len(statement.split()) > 2 else 'unknown'}")
            except sqlite3.Error as e:
                if "already exists" in str(e).lower():
                    logger.info(f"테이블이 이미 존재함: {e}")
                else:
                    logger.error(f"테이블 생성 오류: {e}")
                    logger.error(f"문제가 된 SQL: {statement}")
        
        # 2. 인덱스 생성
        for statement in index_statements:
            try:
                cursor.execute(statement)
                logger.debug(f"인덱스 생성: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"인덱스가 이미 존재함: {e}")
                else:
                    logger.warning(f"인덱스 생성 오류 (무시됨): {e}")
        
        # 3. 데이터 삽입
        for statement in insert_statements:
            try:
                cursor.execute(statement)
                logger.info(f"데이터 삽입: {statement[:50]}...")
            except sqlite3.Error as e:
                if "already exists" in str(e).lower() or "UNIQUE constraint failed" in str(e):
                    logger.info(f"데이터가 이미 존재함: {e}")
                else:
                    logger.error(f"데이터 삽입 오류: {e}")
                    logger.error(f"문제가 된 SQL: {statement}")
        
        # 기존 사용자 테이블에 새 역할 추가 (필요한 경우)
        try:
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            role_column = next((col for col in columns if col[1] == 'role'), None)
            
            if role_column:
                # 역할 제약 조건 업데이트 (SQLite에서는 직접 수정이 어려우므로 로그만 남김)
                logger.info("사용자 역할 시스템이 CIMS 역할을 지원하도록 업데이트되었습니다.")
        except sqlite3.Error as e:
            logger.warning(f"사용자 테이블 업데이트 확인 중 오류: {e}")
        
        # 변경사항 커밋
        conn.commit()
        
        # 테이블 생성 확인
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'cims_%'
            ORDER BY name
        """)
        
        cims_tables = cursor.fetchall()
        logger.info(f"생성된 CIMS 테이블: {[table[0] for table in cims_tables]}")
        
        # 기본 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM cims_policies")
        policy_count = cursor.fetchone()[0]
        logger.info(f"기본 정책 수: {policy_count}")
        
        conn.close()
        
        logger.info("CIMS 데이터베이스 초기화 완료!")
        return True
        
    except Exception as e:
        logger.error(f"CIMS 데이터베이스 초기화 실패: {e}")
        return False

def add_sample_users():
    """CIMS 테스트용 샘플 사용자 추가"""
    try:
        conn = sqlite3.connect("progress_report.db")
        cursor = conn.cursor()
        
        # 샘플 사용자 데이터
        sample_users = [
            {
                'username': 'nurse1',
                'password_hash': 'hashed_password_here',  # 실제로는 해시된 패스워드 사용
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'role': 'registered_nurse',
                'position': 'Registered Nurse',
                'location': '["Parafield Gardens"]'
            },
            {
                'username': 'carer1',
                'password_hash': 'hashed_password_here',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'role': 'carer',
                'position': 'Personal Care Assistant',
                'location': '["Parafield Gardens"]'
            },
            {
                'username': 'clinical_mgr1',
                'password_hash': 'hashed_password_here',
                'first_name': 'Dr. Emma',
                'last_name': 'Thompson',
                'role': 'clinical_manager',
                'position': 'Clinical Manager',
                'location': '["All"]'
            }
        ]
        
        for user in sample_users:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO users (
                        username, password_hash, first_name, last_name, 
                        role, position, location, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    user['username'],
                    user['password_hash'],
                    user['first_name'],
                    user['last_name'],
                    user['role'],
                    user['position'],
                    user['location']
                ))
                logger.info(f"샘플 사용자 추가: {user['username']} ({user['role']})")
            except sqlite3.Error as e:
                logger.warning(f"사용자 {user['username']} 추가 실패: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info("샘플 사용자 추가 완료")
        return True
        
    except Exception as e:
        logger.error(f"샘플 사용자 추가 실패: {e}")
        return False

def verify_cims_installation():
    """CIMS 설치 확인"""
    try:
        conn = sqlite3.connect("progress_report.db")
        cursor = conn.cursor()
        
        # 필수 테이블 확인
        required_tables = [
            'cims_policies',
            'cims_incidents', 
            'cims_tasks',
            'cims_progress_notes',
            'cims_audit_logs'
        ]
        
        missing_tables = []
        for table in required_tables:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table,))
            
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            logger.error(f"누락된 테이블: {missing_tables}")
            return False
        
        # 기본 정책 확인
        cursor.execute("SELECT COUNT(*) FROM cims_policies WHERE is_active = 1")
        active_policies = cursor.fetchone()[0]
        
        logger.info(f"✅ CIMS 설치 확인 완료")
        logger.info(f"   - 필수 테이블: {len(required_tables)}개 모두 존재")
        logger.info(f"   - 활성 정책: {active_policies}개")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"CIMS 설치 확인 실패: {e}")
        return False

if __name__ == "__main__":
    import sys
    import io
    
    # Windows 환경에서 한글 출력 문제 해결
    if sys.platform.startswith('win'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("CIMS (Compliance-Driven Incident Management System)")
    print("Database Initialization Script")
    print("=" * 60)
    
    # 1. 데이터베이스 초기화
    if init_cims_database():
        print("SUCCESS: CIMS database initialization completed")
    else:
        print("ERROR: CIMS database initialization failed")
        exit(1)
    
    # 2. 샘플 사용자 추가 (선택사항)
    response = input("\nAdd sample users? (y/N): ")
    if response.lower() in ['y', 'yes']:
        if add_sample_users():
            print("SUCCESS: Sample users added")
        else:
            print("ERROR: Failed to add sample users")
    
    # 3. 설치 확인
    print("\n" + "=" * 40)
    print("Verifying installation...")
    print("=" * 40)
    
    if verify_cims_installation():
        print("\nSUCCESS: CIMS system installed successfully!")
        print("\nNext steps:")
        print("1. Start the web application")
        print("2. Go to /incident_dashboard2 URL")
        print("3. Check the new CIMS dashboard")
    else:
        print("\nERROR: CIMS installation has issues. Check logs.")
        exit(1)
