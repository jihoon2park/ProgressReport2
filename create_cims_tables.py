#!/usr/bin/env python3
"""
CIMS 테이블 생성 스크립트
cims_incidents 및 관련 테이블들을 생성합니다.
"""

import sqlite3
import os
import sys

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def create_cims_tables():
    """CIMS 테이블들을 생성합니다."""
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 기존 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"기존 CIMS 테이블: {existing_tables if existing_tables else '없음'}")
        
        # cims_database_schema.sql 파일 읽기
        schema_file = 'cims_database_schema.sql'
        if not os.path.exists(schema_file):
            print(f"❌ 스키마 파일을 찾을 수 없습니다: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # 주석 제거 및 정리
        lines = []
        for line in schema_sql.split('\n'):
            line = line.strip()
            # 주석 제거
            if line.startswith('--'):
                continue
            if line:
                lines.append(line)
        
        # 전체 SQL을 하나의 문자열로 합치기
        clean_sql = ' '.join(lines)
        
        # SQL 문들을 세미콜론으로 분리
        statements = []
        current = []
        in_string = False
        string_char = None
        
        for char in clean_sql:
            if char in ("'", '"') and (not current or current[-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            current.append(char)
            
            if not in_string and char == ';':
                statement = ''.join(current).strip()
                if statement and statement != ';':
                    statements.append(statement)
                current = []
        
        # 남은 문장 처리
        if current:
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
        
        # 각 SQL 문 실행
        created_tables = []
        for statement in statements:
            try:
                statement_upper = statement.upper().strip()
                
                # CREATE TABLE 문 처리
                if statement_upper.startswith('CREATE TABLE'):
                    # 테이블 이름 추출
                    table_name = None
                    parts = statement.split()
                    for i, part in enumerate(parts):
                        if part.upper() == 'TABLE' and i + 1 < len(parts):
                            table_name = parts[i + 1].strip('(').strip()
                            break
                    
                    if table_name:
                        # 테이블이 이미 존재하는지 확인
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if cursor.fetchone():
                            print(f"⏭️  테이블이 이미 존재합니다: {table_name}")
                            continue
                    
                    cursor.execute(statement)
                    if table_name:
                        created_tables.append(table_name)
                        print(f"✅ 테이블 생성 완료: {table_name}")
                
                # CREATE INDEX 문 처리
                elif statement_upper.startswith('CREATE INDEX'):
                    try:
                        cursor.execute(statement)
                        print(f"✅ 인덱스 생성 완료")
                    except sqlite3.OperationalError as e:
                        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                            print(f"⏭️  인덱스가 이미 존재합니다")
                        else:
                            print(f"⚠️  인덱스 생성 오류: {str(e)[:100]}")
                
                # INSERT 문 처리
                elif statement_upper.startswith('INSERT'):
                    try:
                        cursor.execute(statement)
                        print(f"✅ 초기 데이터 삽입 완료")
                    except sqlite3.IntegrityError as e:
                        if 'UNIQUE constraint' in str(e):
                            print(f"⏭️  데이터가 이미 존재합니다")
                        else:
                            print(f"⚠️  데이터 삽입 오류: {str(e)[:100]}")
                
                # 기타 SQL 문
                else:
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        print(f"⚠️  SQL 실행 오류 (무시): {str(e)[:100]}")
                        
            except sqlite3.Error as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print(f"⏭️  이미 존재합니다: {str(e)[:50]}")
                else:
                    print(f"⚠️  SQL 실행 중 오류: {str(e)[:100]}")
        
        conn.commit()
        
        # 생성된 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        all_cims_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n" + "=" * 60)
        print(f"✅ CIMS 테이블 생성 완료!")
        print(f"생성된 테이블: {len(created_tables)}개")
        for table in created_tables:
            print(f"  - {table}")
        print(f"\n전체 CIMS 테이블: {len(all_cims_tables)}개")
        for table in all_cims_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count}개 레코드")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 CIMS 테이블 생성 시작...")
    success = create_cims_tables()
    if success:
        print("\n✅ 완료!")
        sys.exit(0)
    else:
        print("\n❌ 실패!")
        sys.exit(1)

