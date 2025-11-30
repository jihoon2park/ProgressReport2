#!/usr/bin/env python3
"""
간단한 Parafield Gardens DB 연결 테스트
서버와 데이터베이스 연결만 확인
"""

import pyodbc
import sys

def test_simple_connection():
    """간단한 연결 테스트"""
    print("=" * 60)
    print("간단한 DB 연결 테스트")
    print("=" * 60)
    
    # 서버 정보
    server = 'efsvr02\\sqlexpress'
    
    print(f"\n📋 연결 정보:")
    print(f"   서버: {server}")
    print(f"   인증: Windows Authentication")
    
    # 여러 가능한 데이터베이스 이름 시도
    database_names = [
        'MANAD_Plus',
        'MANAD',
        'manad_plus',
        'manad',
        'MANADPlus',
        'manadplus'
    ]
    
    print(f"\n🔍 여러 데이터베이스 이름으로 시도...")
    
    for db_name in database_names:
        print(f"\n📝 시도 중: {db_name}")
        
        try:
            # 연결 문자열 생성
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={db_name};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
                f"Connection Timeout=10;"
            )
            
            print(f"   연결 문자열 생성 완료")
            print(f"   연결 시도 중...")
            
            # 연결 시도
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            
            # 간단한 쿼리 실행
            cursor.execute("SELECT DB_NAME() as CurrentDB, SYSTEM_USER as CurrentUser")
            row = cursor.fetchone()
            
            print(f"   ✅ 연결 성공!")
            print(f"   현재 데이터베이스: {row[0]}")
            print(f"   현재 사용자: {row[1]}")
            
            # 사용 가능한 데이터베이스 목록 조회
            print(f"\n📋 사용 가능한 데이터베이스 목록:")
            cursor.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name")
            databases = cursor.fetchall()
            for db in databases:
                print(f"   - {db[0]}")
            
            conn.close()
            print(f"\n✅ 성공! 데이터베이스 이름: {db_name}")
            return True
            
        except pyodbc.Error as e:
            error_code = e.args[0]
            error_msg = str(e)
            
            if '08001' in error_code or 'cannot open database' in error_msg.lower():
                print(f"   ❌ 데이터베이스 '{db_name}'을(를) 찾을 수 없습니다.")
            elif 'Login failed' in error_msg:
                print(f"   ❌ 로그인 실패 - 권한 확인 필요")
                break
            elif 'network-related' in error_msg.lower() or 'server/instance specified' in error_msg.lower():
                print(f"   ❌ 서버에 연결할 수 없습니다. 네트워크 또는 서버 이름 확인 필요")
                print(f"   💡 서버 이름 형식 확인: '{server}'")
                break
            else:
                print(f"   ❌ 오류: {error_msg[:200]}")
        
        except Exception as e:
            print(f"   ❌ 예상치 못한 오류: {e}")
    
    print(f"\n❌ 모든 시도 실패")
    print(f"\n💡 확인 사항:")
    print(f"   1. 서버 이름이 정확한지 확인: {server}")
    print(f"   2. 네트워크에서 서버에 접근 가능한지 확인 (ping efsvr02)")
    print(f"   3. SQL Server Browser 서비스가 실행 중인지 확인")
    print(f"   4. Windows 방화벽에서 SQL Server 포트(1433 또는 동적 포트) 허용 확인")
    print(f"   5. 실제 데이터베이스 이름 확인")
    
    return False


if __name__ == '__main__':
    try:
        success = test_simple_connection()
        sys.exit(0 if success else 1)
    except ImportError:
        print("❌ pyodbc가 설치되지 않았습니다.")
        print("💡 설치: pip install pyodbc")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

