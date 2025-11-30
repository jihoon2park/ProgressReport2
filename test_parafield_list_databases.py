#!/usr/bin/env python3
"""
Parafield Gardens DB - 데이터베이스 목록 조회
master 데이터베이스로 먼저 연결해서 실제 데이터베이스 목록 확인
"""

import pyodbc
import sys

def list_databases():
    """master로 연결해서 데이터베이스 목록 조회"""
    print("=" * 60)
    print("Parafield Gardens - 데이터베이스 목록 조회")
    print("=" * 60)
    
    # 서버 정보
    server = 'efsvr02\\sqlexpress'
    
    print(f"\n📋 연결 정보:")
    print(f"   서버: {server}")
    print(f"   데이터베이스: master (시스템 DB)")
    print(f"   인증: Windows Authentication")
    
    try:
        # master 데이터베이스로 연결 (데이터베이스 이름 필요 없음)
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE=master;"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )
        
        print(f"\n🔌 연결 시도 중...")
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        
        print(f"✅ 연결 성공!")
        
        # 서버 정보 조회
        cursor.execute("SELECT @@VERSION as SQLVersion, @@SERVERNAME as ServerName")
        row = cursor.fetchone()
        print(f"\n📊 서버 정보:")
        print(f"   서버 이름: {row[1]}")
        print(f"   SQL Server 버전: {row[0][:80]}...")
        
        # 현재 사용자 정보
        cursor.execute("SELECT SYSTEM_USER as CurrentUser, DB_NAME() as CurrentDB")
        row = cursor.fetchone()
        print(f"   현재 사용자: {row[0]}")
        print(f"   현재 데이터베이스: {row[1]}")
        
        # 모든 데이터베이스 목록 조회
        print(f"\n📋 사용 가능한 데이터베이스 목록:")
        cursor.execute("""
            SELECT 
                name,
                database_id,
                create_date,
                state_desc
            FROM sys.databases 
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
            ORDER BY name
        """)
        
        databases = cursor.fetchall()
        
        if databases:
            print(f"\n   총 {len(databases)}개 데이터베이스 발견:\n")
            for db in databases:
                print(f"   ✅ {db[0]}")
                print(f"      ID: {db[1]}, 상태: {db[3]}, 생성일: {db[2]}")
        else:
            print(f"   ❌ 사용자 데이터베이스를 찾을 수 없습니다.")
        
        # MANAD 관련 데이터베이스 찾기
        print(f"\n🔍 MANAD 관련 데이터베이스:")
        cursor.execute("""
            SELECT name
            FROM sys.databases 
            WHERE name LIKE '%MANAD%' OR name LIKE '%manad%' OR name LIKE '%Manad%'
            ORDER BY name
        """)
        
        manad_dbs = cursor.fetchall()
        if manad_dbs:
            for db in manad_dbs:
                print(f"   ✅ {db[0]}")
        else:
            print(f"   ⚠️ MANAD 관련 데이터베이스를 찾을 수 없습니다.")
        
        conn.close()
        
        print(f"\n" + "=" * 60)
        print(f"✅ 완료!")
        print(f"=" * 60)
        
        return True
        
    except pyodbc.Error as e:
        error_code = e.args[0]
        error_msg = str(e)
        
        print(f"\n❌ 연결 오류:")
        print(f"   오류 코드: {error_code}")
        print(f"   오류 메시지: {error_msg[:300]}")
        
        if '08001' in error_code or 'network-related' in error_msg.lower():
            print(f"\n💡 네트워크 연결 문제:")
            print(f"   1. 서버 이름 확인: {server}")
            print(f"   2. 네트워크 접근 가능 여부 확인: ping efsvr02")
            print(f"   3. SQL Server Browser 서비스 실행 확인")
            print(f"   4. 방화벽 설정 확인")
        elif 'Login failed' in error_msg:
            print(f"\n💡 인증 문제:")
            print(f"   1. Windows 인증 권한 확인")
            print(f"   2. 현재 사용자: EDENFIELD\\it.support")
        
        return False
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = list_databases()
        sys.exit(0 if success else 1)
    except ImportError:
        print("❌ pyodbc가 설치되지 않았습니다.")
        print("💡 설치: pip install pyodbc")
        sys.exit(1)

