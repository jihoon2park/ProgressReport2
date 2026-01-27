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
        print(f"❌ Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 기존 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing CIMS tables: {existing_tables if existing_tables else 'none'}")
        
        # cims_database_schema.sql 파일 읽기
        schema_file = 'cims_database_schema.sql'
        if not os.path.exists(schema_file):
            print(f"❌ Schema file not found: {schema_file}")
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
                            print(f"⏭️  Table already exists: {table_name}")
                            continue
                    
                    cursor.execute(statement)
                    if table_name:
                        created_tables.append(table_name)
                        print(f"✅ Table created: {table_name}")
                
                # CREATE INDEX 문 처리
                elif statement_upper.startswith('CREATE INDEX'):
                    try:
                        cursor.execute(statement)
                        print("✅ Index created")
                    except sqlite3.OperationalError as e:
                        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                            print("⏭️  Index already exists")
                        else:
                            print(f"⚠️  Index creation error: {str(e)[:100]}")
                
                # INSERT 문 처리
                elif statement_upper.startswith('INSERT'):
                    try:
                        cursor.execute(statement)
                        print("✅ Initial data inserted")
                    except sqlite3.IntegrityError as e:
                        if 'UNIQUE constraint' in str(e):
                            print("⏭️  Data already exists")
                        else:
                            print(f"⚠️  Data insert error: {str(e)[:100]}")
                
                # 기타 SQL 문
                else:
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        print(f"⚠️  SQL execution error (ignored): {str(e)[:100]}")
                        
            except sqlite3.Error as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print(f"⏭️  Already exists: {str(e)[:50]}")
                else:
                    print(f"⚠️  SQL execution error: {str(e)[:100]}")
        
        conn.commit()
        
        # 생성된 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        all_cims_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n" + "=" * 60)
        print("✅ CIMS table creation completed!")
        print(f"Tables created: {len(created_tables)}")
        for table in created_tables:
            print(f"  - {table}")
        print(f"\nTotal CIMS tables: {len(all_cims_tables)}")
        for table in all_cims_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} records")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting CIMS table creation...")
    success = create_cims_tables()
    if success:
        print("\n✅ Done!")
        sys.exit(0)
    else:
        print("\n❌ Failed!")
        sys.exit(1)

