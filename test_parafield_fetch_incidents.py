#!/usr/bin/env python3
"""
Parafield Gardens DB - 실제 Incident 데이터 조회 테스트
Event 테이블에서 실제 데이터를 조회하여 쿼리 검증
"""

import pyodbc
import sys
from datetime import datetime, timedelta

def test_fetch_incidents():
    """실제 Incident 데이터 조회 테스트"""
    print("=" * 60)
    print("Parafield Gardens - 실제 Incident 데이터 조회 테스트")
    print("=" * 60)
    
    server = 'efsvr02\\sqlexpress'
    database = 'ManadPlus_Edenfield'
    
    print(f"\n📋 연결 정보:")
    print(f"   서버: {server}")
    print(f"   데이터베이스: {database}")
    
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )
        
        print(f"\n🔌 연결 중...")
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        print(f"✅ 연결 성공!")
        
        # 1. Event 테이블의 실제 컬럼명 확인
        print(f"\n🔍 Event 테이블 컬럼 확인...")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Event'
            ORDER BY ORDINAL_POSITION
        """)
        
        event_columns = cursor.fetchall()
        print(f"✅ Event 테이블 컬럼 ({len(event_columns)}개):")
        for col in event_columns[:20]:  # 처음 20개만 표시
            print(f"   - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        if len(event_columns) > 20:
            print(f"   ... (총 {len(event_columns)}개)")
        
        # 2. 최근 Event 몇 개 조회 (간단한 쿼리)
        print(f"\n🔍 최근 Event 5개 조회 (간단한 쿼리)...")
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 간단한 쿼리로 먼저 테스트
        simple_query = """
            SELECT TOP 5
                e.Id,
                e.Date,
                e.Description,
                e.PersonId,
                e.LocationId
            FROM Event e
            WHERE e.Date >= ? AND e.Date <= ?
            AND e.IsDeleted = 0
            ORDER BY e.Date DESC
        """
        
        cursor.execute(simple_query, (start_date, end_date))
        rows = cursor.fetchall()
        
        if rows:
            print(f"✅ {len(rows)}개 Event 발견:\n")
            for row in rows:
                print(f"   Event ID: {row[0]}")
                print(f"   Date: {row[1]}")
                print(f"   PersonId: {row[3]}")
                print(f"   Description: {(row[2] or '')[:100]}...")
                print()
        else:
            print(f"⚠️ 해당 기간에 Event가 없습니다. 더 넓은 기간으로 검색...")
            # 더 넓은 기간으로 시도
            wide_start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            cursor.execute(simple_query, (wide_start, end_date))
            rows = cursor.fetchall()
            if rows:
                print(f"✅ {len(rows)}개 Event 발견 (1년 범위):\n")
                for row in rows[:3]:  # 3개만 표시
                    print(f"   Event ID: {row[0]}, Date: {row[1]}, PersonId: {row[3]}")
        
        # 3. Event와 Client JOIN 테스트
        print(f"\n🔍 Event와 Client JOIN 테스트...")
        join_query = """
            SELECT TOP 3
                e.Id,
                e.Date,
                e.Description,
                e.PersonId,
                c.FirstName,
                c.LastName
            FROM Event e
            LEFT JOIN Client c ON e.PersonId = c.Id
            WHERE e.Date >= ?
            AND e.IsDeleted = 0
            ORDER BY e.Date DESC
        """
        
        cursor.execute(join_query, (start_date,))
        join_rows = cursor.fetchall()
        
        if join_rows:
            print(f"✅ JOIN 성공! {len(join_rows)}개 결과:\n")
            for row in join_rows:
                print(f"   Event ID: {row[0]}")
                print(f"   Date: {row[1]}")
                print(f"   Client: {row[4] or ''} {row[5] or ''} (ID: {row[3]})")
                print(f"   Description: {(row[2] or '')[:80]}...")
                print()
        
        # 4. EventType 관계 테이블 확인
        print(f"\n🔍 EventType 관계 테이블 확인...")
        cursor.execute("""
            SELECT TOP 3
                e.Id AS EventId,
                e.Date,
                (SELECT STRING_AGG(et.Description, ', ')
                 FROM Event_EventType eet
                 JOIN EventType et ON eet.EventTypeId = et.Id
                 WHERE eet.EventId = e.Id
                 AND et.IsArchived = 0) AS EventTypeNames
            FROM Event e
            WHERE e.Date >= ?
            AND e.IsDeleted = 0
            ORDER BY e.Date DESC
        """, (start_date,))
        
        type_rows = cursor.fetchall()
        
        if type_rows:
            print(f"✅ EventType 조회 성공:\n")
            for row in type_rows:
                print(f"   Event ID: {row[0]}, Date: {row[1]}")
                print(f"   Event Types: {row[2] or 'None'}")
                print()
        
        # 5. Location, Wing, Department 테이블 확인
        print(f"\n🔍 Location/Wing/Department 테이블 확인...")
        for table_name in ['Location', 'Wing', 'Department']:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
            """)
            exists = cursor.fetchone()[0] > 0
            if exists:
                print(f"   ✅ {table_name} 테이블 존재")
                # 컬럼 확인
                cursor.execute(f"""
                    SELECT TOP 3 COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
                """)
                cols = cursor.fetchall()
                col_names = [c[0] for c in cols]
                print(f"      주요 컬럼: {', '.join(col_names[:5])}")
            else:
                print(f"   ⚠️ {table_name} 테이블 없음")
        
        conn.close()
        
        print(f"\n" + "=" * 60)
        print(f"✅ 테스트 완료!")
        print(f"=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = test_fetch_incidents()
        sys.exit(0 if success else 1)
    except ImportError:
        print("❌ pyodbc가 설치되지 않았습니다.")
        print("💡 설치: pip install pyodbc")
        sys.exit(1)

