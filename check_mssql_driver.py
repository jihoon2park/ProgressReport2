#!/usr/bin/env python3
"""MSSQL 드라이버 확인 및 설치 스크립트"""

import sys
import subprocess

def check_pyodbc():
    """pyodbc 설치 여부 확인"""
    try:
        import pyodbc
        print("✅ pyodbc 설치됨")
        drivers = pyodbc.drivers()
        print(f"   사용 가능한 ODBC 드라이버: {len(drivers)}개")
        sql_drivers = [d for d in drivers if 'SQL Server' in d]
        if sql_drivers:
            print(f"   ✅ SQL Server 드라이버 발견: {', '.join(sql_drivers)}")
        else:
            print("   ⚠️ SQL Server 드라이버 없음")
            print("   ODBC Driver 17 for SQL Server 설치 필요:")
            print("   https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
        return True
    except ImportError:
        print("❌ pyodbc 설치 안됨")
        return False

def check_pymssql():
    """pymssql 설치 여부 확인"""
    try:
        import pymssql
        print("✅ pymssql 설치됨")
        return True
    except ImportError:
        print("❌ pymssql 설치 안됨")
        return False

def install_driver(driver_name='pyodbc'):
    """드라이버 설치 시도"""
    print(f"\n🔧 {driver_name} 설치 시도...")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', driver_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✅ {driver_name} 설치 완료")
            return True
        else:
            print(f"❌ {driver_name} 설치 실패:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {driver_name} 설치 중 오류: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("MSSQL 드라이버 확인 및 설치")
    print("=" * 60)
    print()
    
    pyodbc_ok = check_pyodbc()
    pymssql_ok = check_pymssql()
    
    if not pyodbc_ok and not pymssql_ok:
        print("\n⚠️ MSSQL 드라이버가 설치되지 않았습니다.")
        print("\n자동 설치를 시도하시겠습니까? (Y/N): ", end='')
        choice = input().strip().upper()
        
        if choice == 'Y':
            if install_driver('pyodbc'):
                check_pyodbc()
            else:
                print("\npyodbc 설치 실패. pymssql 설치를 시도합니다...")
                if install_driver('pymssql'):
                    check_pymssql()
        else:
            print("\n수동 설치 명령어:")
            print("  pip install pyodbc")
            print("  또는")
            print("  pip install pymssql")
    elif pyodbc_ok:
        print("\n✅ pyodbc 사용 가능 - DB 직접 접속 모드 사용 가능")
    elif pymssql_ok:
        print("\n✅ pymssql 사용 가능 - DB 직접 접속 모드 사용 가능")

