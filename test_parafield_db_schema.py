#!/usr/bin/env python3
"""
Parafield Gardens DB - 테이블 구조 확인
ManadPlus_Edenfield 데이터베이스의 테이블과 컬럼 확인
"""

import pyodbc
import sys

def check_schema():
    """테이블 구조 확인"""
    print("=" * 60)
    print("Parafield Gardens DB - 테이블 구조 확인")
    print("=" * 60)
    
    # 서버 정보
    server = 'efsvr02\\sqlexpress'
    database = 'ManadPlus_Edenfield'
    
    print(f"\n📋 연결 정보:")
    print(f"   서버: {server}")
    print(f"   데이터베이스: {database}")
    print(f"   인증: Windows Authentication")
    
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )
        
        print(f"\n🔌 연결 시도 중...")
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        print(f"✅ 연결 성공!")
        
        # Incident 관련 테이블 찾기
        print(f"\n🔍 Incident 관련 테이블 검색 중...")
        cursor.execute("""
            SELECT 
                TABLE_SCHEMA,
                TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND (
                TABLE_NAME LIKE '%Incident%' 
                OR TABLE_NAME LIKE '%Event%' 
                OR TABLE_NAME LIKE '%Client%'
                OR TABLE_NAME LIKE '%Adverse%'
            )
            ORDER BY TABLE_NAME
        """)
        
        incident_tables = cursor.fetchall()
        
        if incident_tables:
            print(f"\n✅ {len(incident_tables)}개 관련 테이블 발견:\n")
            
            for schema, table_name in incident_tables:
                print(f"   📋 {schema}.{table_name}")
                
                # 각 테이블의 컬럼 조회
                cursor.execute(f"""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        CHARACTER_MAXIMUM_LENGTH,
                        IS_NULLABLE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """, (schema, table_name))
                
                columns = cursor.fetchall()
                print(f"      컬럼 ({len(columns)}개):")
                for col in columns:
                    col_name = col[0]
                    col_type = col[1]
                    col_length = f"({col[2]})" if col[2] else ""
                    nullable = "NULL" if col[3] == 'YES' else "NOT NULL"
                    print(f"         - {col_name}: {col_type}{col_length} {nullable}")
                print()
        else:
            print(f"   ⚠️ Incident 관련 테이블을 찾을 수 없습니다.")
        
        # 모든 테이블 목록 (참고용)
        print(f"\n📋 전체 테이블 목록 (최대 30개):")
        cursor.execute("""
            SELECT 
                TABLE_SCHEMA,
                TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        all_tables = cursor.fetchall()
        for schema, table_name in all_tables[:30]:
            print(f"   - {schema}.{table_name}")
        
        if len(all_tables) > 30:
            print(f"   ... (총 {len(all_tables)}개 테이블, 30개만 표시)")
        
        conn.close()
        
        print(f"\n" + "=" * 60)
        print(f"✅ 완료!")
        print(f"=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = check_schema()
        sys.exit(0 if success else 1)
    except ImportError:
        print("❌ pyodbc가 설치되지 않았습니다.")
        print("💡 설치: pip install pyodbc")
        sys.exit(1)

