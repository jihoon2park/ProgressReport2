#!/usr/bin/env python3
"""
DB Schema Migration Script
운영 서버와 개발 서버의 DB 스키마를 동기화하는 스크립트
"""

import sqlite3
import os
import sys
from datetime import datetime

def get_db_connection(db_path):
    """데이터베이스 연결"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ DB 연결 실패: {e}")
        return None

def get_table_schema(conn, table_name):
    """테이블 스키마 정보 가져오기"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return [dict(row) for row in columns]
    except Exception as e:
        print(f"❌ 테이블 스키마 조회 실패 ({table_name}): {e}")
        return []

def get_table_list(conn):
    """테이블 목록 가져오기"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        return [row[0] for row in tables]
    except Exception as e:
        print(f"❌ 테이블 목록 조회 실패: {e}")
        return []

def compare_schemas(dev_conn, prod_conn):
    """개발 서버와 운영 서버 스키마 비교"""
    print("🔍 스키마 비교 중...")
    
    dev_tables = get_table_list(dev_conn)
    prod_tables = get_table_list(prod_conn)
    
    print(f"📊 개발 서버 테이블 수: {len(dev_tables)}")
    print(f"📊 운영 서버 테이블 수: {len(prod_tables)}")
    
    differences = []
    
    # 공통 테이블 비교
    common_tables = set(dev_tables) & set(prod_tables)
    for table in common_tables:
        dev_schema = get_table_schema(dev_conn, table)
        prod_schema = get_table_schema(prod_conn, table)
        
        dev_columns = {col['name']: col for col in dev_schema}
        prod_columns = {col['name']: col for col in prod_schema}
        
        # 컬럼 차이점 찾기
        for col_name, dev_col in dev_columns.items():
            if col_name not in prod_columns:
                differences.append({
                    'type': 'missing_column',
                    'table': table,
                    'column': col_name,
                    'dev_info': dev_col
                })
            else:
                prod_col = prod_columns[col_name]
                if dev_col['type'] != prod_col['type']:
                    differences.append({
                        'type': 'type_mismatch',
                        'table': table,
                        'column': col_name,
                        'dev_type': dev_col['type'],
                        'prod_type': prod_col['type']
                    })
    
    # 개발 서버에만 있는 테이블
    missing_tables = set(dev_tables) - set(prod_tables)
    for table in missing_tables:
        differences.append({
            'type': 'missing_table',
            'table': table
        })
    
    return differences

def generate_migration_sql(differences):
    """마이그레이션 SQL 생성"""
    migration_sql = []
    migration_sql.append("-- DB Schema Migration Script")
    migration_sql.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    migration_sql.append("")
    
    for diff in differences:
        if diff['type'] == 'missing_column':
            table = diff['table']
            column = diff['column']
            col_info = diff['dev_info']
            
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_info['type']}"
            if col_info['notnull']:
                sql += " NOT NULL"
            if col_info['dflt_value'] is not None:
                sql += f" DEFAULT {col_info['dflt_value']}"
            
            migration_sql.append(f"-- Add missing column: {table}.{column}")
            migration_sql.append(sql + ";")
            migration_sql.append("")
        
        elif diff['type'] == 'missing_table':
            table = diff['table']
            migration_sql.append(f"-- Create missing table: {table}")
            migration_sql.append(f"-- Note: Table creation SQL needs to be provided manually")
            migration_sql.append("")
    
    return migration_sql

def apply_migration(conn, migration_sql):
    """마이그레이션 적용"""
    print("🚀 마이그레이션 적용 중...")
    
    try:
        cursor = conn.cursor()
        
        for sql in migration_sql:
            if sql.strip() and not sql.startswith('--'):
                print(f"실행: {sql}")
                cursor.execute(sql)
        
        conn.commit()
        print("✅ 마이그레이션 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False

def backup_database(db_path):
    """데이터베이스 백업"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 백업 완료: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return None

def main():
    print("🔧 DB Schema Migration Tool")
    print("=" * 50)
    
    # DB 경로 설정
    dev_db = "progress_report.db"
    prod_db = input("운영 서버 DB 경로를 입력하세요 (기본값: progress_report.db): ").strip()
    if not prod_db:
        prod_db = "progress_report.db"
    
    # 개발 서버 DB 연결
    print(f"📁 개발 서버 DB: {dev_db}")
    dev_conn = get_db_connection(dev_db)
    if not dev_conn:
        return
    
    # 운영 서버 DB 연결
    print(f"📁 운영 서버 DB: {prod_db}")
    prod_conn = get_db_connection(prod_db)
    if not prod_conn:
        dev_conn.close()
        return
    
    try:
        # 스키마 비교
        differences = compare_schemas(dev_conn, prod_conn)
        
        if not differences:
            print("✅ 두 서버의 스키마가 동일합니다!")
            return
        
        print(f"\n📋 발견된 차이점: {len(differences)}개")
        for i, diff in enumerate(differences, 1):
            if diff['type'] == 'missing_column':
                print(f"{i}. 누락된 컬럼: {diff['table']}.{diff['column']}")
            elif diff['type'] == 'missing_table':
                print(f"{i}. 누락된 테이블: {diff['table']}")
            elif diff['type'] == 'type_mismatch':
                print(f"{i}. 타입 불일치: {diff['table']}.{diff['column']} ({diff['dev_type']} vs {diff['prod_type']})")
        
        # 마이그레이션 SQL 생성
        migration_sql = generate_migration_sql(differences)
        
        # SQL 파일 저장
        sql_file = "migration_schema.sql"
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(migration_sql))
        print(f"\n📄 마이그레이션 SQL 저장: {sql_file}")
        
        # 사용자 확인
        print("\n⚠️  주의사항:")
        print("1. 운영 서버에 적용하기 전에 반드시 백업을 생성하세요")
        print("2. 테스트 환경에서 먼저 검증하세요")
        print("3. 데이터 손실 가능성이 있으니 신중하게 진행하세요")
        
        apply_now = input("\n지금 마이그레이션을 적용하시겠습니까? (y/N): ").strip().lower()
        
        if apply_now == 'y':
            # 백업 생성
            backup_path = backup_database(prod_db)
            if not backup_path:
                print("❌ 백업 실패로 마이그레이션을 중단합니다.")
                return
            
            # 마이그레이션 적용
            if apply_migration(prod_conn, migration_sql):
                print("🎉 마이그레이션 성공!")
            else:
                print("❌ 마이그레이션 실패!")
        else:
            print("📄 마이그레이션 SQL 파일을 확인하고 수동으로 적용하세요.")
    
    finally:
        dev_conn.close()
        prod_conn.close()

if __name__ == "__main__":
    main()