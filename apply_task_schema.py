#!/usr/bin/env python3
"""
Task Management Schema 적용 스크립트
"""

import sqlite3
import os

def apply_task_schema():
    """작업 관리 스키마를 데이터베이스에 적용"""
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        print("🗄️ 데이터베이스 연결 완료")
        
        # 스키마 파일 읽기
        with open('policy_task_schema.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("📋 스키마 파일 읽기 완료")
        
        # SQL 문 분리 및 실행
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    print(f"  ✓ SQL 문 {i+1} 실행 완료")
                except sqlite3.Error as e:
                    if "already exists" in str(e) or "duplicate column" in str(e):
                        print(f"  ⚠️ SQL 문 {i+1} 이미 존재 (건너뜀)")
                    else:
                        print(f"  ❌ SQL 문 {i+1} 실행 실패: {e}")
                        print(f"     문제 SQL: {statement[:100]}...")
                        raise
        
        conn.commit()
        print("\n✅ Task Management 스키마 적용 완료!")
        
        # 생성된 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%task%' OR name LIKE '%scheduled%'")
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n📊 생성된 테이블: {[table[0] for table in tables]}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 스키마 적용 실패: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Task Management Schema Application")
    print("=" * 50)
    
    success = apply_task_schema()
    
    if success:
        print("\n🎉 스키마 적용 성공!")
        print("다음 단계: Task Manager 테스트")
    else:
        print("\n💥 스키마 적용 실패!")
        exit(1)
