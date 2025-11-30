#!/usr/bin/env python3
"""
Parafield Gardens DB 연결 테스트 스크립트
Windows Authentication을 사용하여 MSSQL 서버에 연결 테스트
"""

import os
import sys
from dotenv import load_dotenv
import logging

# .env 파일 로딩
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection():
    """DB 연결 테스트"""
    print("=" * 60)
    print("Parafield Gardens DB 연결 테스트")
    print("=" * 60)
    
    # 환경 변수 설정
    site = "Parafield Gardens"
    
    # Parafield Gardens DB 정보 (하드코딩 또는 환경 변수에서 로드)
    # 환경 변수가 설정되어 있지 않으면 하드코딩된 값 사용
    # 서버 이름 형식: efsvr02\sqlexpress 또는 efsvr02,1433\sqlexpress
    os.environ.setdefault('MANAD_DB_SERVER_PARAFIELD_GARDENS', 'efsvr02\\sqlexpress')
    
    # 데이터베이스 이름 확인 필요 - 여러 가능성 시도
    db_name = os.environ.get('MANAD_DB_NAME_PARAFIELD_GARDENS', 'MANAD_Plus')
    os.environ.setdefault('MANAD_DB_NAME_PARAFIELD_GARDENS', db_name)
    os.environ.setdefault('MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS', 'true')
    
    print(f"\n📋 연결 정보:")
    print(f"   서버: {os.environ.get('MANAD_DB_SERVER_PARAFIELD_GARDENS')}")
    print(f"   데이터베이스: {os.environ.get('MANAD_DB_NAME_PARAFIELD_GARDENS')}")
    print(f"   인증: Windows Authentication")
    print(f"   사용자: EDENFIELD\\it.support (현재 Windows 사용자)")
    print(f"\n💡 연결 실패 시 확인 사항:")
    print(f"   1. 서버 이름이 정확한지 확인 (efsvr02\\sqlexpress)")
    print(f"   2. 네트워크에서 서버에 접근 가능한지 확인")
    print(f"   3. 데이터베이스 이름이 정확한지 확인 (현재: {db_name})")
    print(f"   4. SQL Server Browser 서비스가 실행 중인지 확인")
    
    try:
        from manad_db_connector import MANADDBConnector
        
        print(f"\n🔌 DB Connector 초기화 중...")
        connector = MANADDBConnector(site)
        
        if not connector.connection_string:
            print("❌ 연결 문자열 생성 실패!")
            return False
        
        print("✅ 연결 문자열 생성 성공")
        print(f"\n📝 연결 문자열 (일부):")
        conn_str_display = connector.connection_string.replace('Trusted_Connection=yes;', 'Trusted_Connection=yes; [마스킹됨]')
        print(f"   {conn_str_display[:100]}...")
        
        # 연결 테스트
        print(f"\n🔍 DB 연결 테스트 중...")
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            
            # 간단한 쿼리로 연결 확인
            cursor.execute("SELECT @@VERSION as SQLVersion, DB_NAME() as CurrentDB, SYSTEM_USER as CurrentUser")
            row = cursor.fetchone()
            
            print("✅ 연결 성공!")
            print(f"\n📊 서버 정보:")
            
            if hasattr(row, '__getitem__'):
                # pyodbc 결과
                print(f"   SQL Server 버전: {row[0][:50]}...")
                print(f"   현재 데이터베이스: {row[1]}")
                print(f"   현재 사용자: {row[2]}")
            else:
                # pymssql 결과 (딕셔너리)
                print(f"   SQL Server 버전: {row.get('SQLVersion', 'N/A')[:50]}...")
                print(f"   현재 데이터베이스: {row.get('CurrentDB', 'N/A')}")
                print(f"   현재 사용자: {row.get('CurrentUser', 'N/A')}")
        
        # 테이블 목록 조회 테스트
        print(f"\n🔍 테이블 목록 조회 중...")
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            
            # 사용 가능한 테이블 조회
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_SCHEMA, TABLE_NAME
            """)
            
            tables = cursor.fetchall()
            print(f"✅ {len(tables)}개 테이블 발견")
            
            if tables:
                print(f"\n📋 주요 테이블 (최대 20개):")
                count = 0
                for table in tables[:20]:
                    schema = table[0] if hasattr(table, '__getitem__') else table.get('TABLE_SCHEMA', '')
                    name = table[1] if hasattr(table, '__getitem__') else table.get('TABLE_NAME', '')
                    print(f"   - {schema}.{name}")
                    count += 1
                    if count >= 20:
                        break
        
        # Incident 테이블 확인
        print(f"\n🔍 Incident 관련 테이블 확인 중...")
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            
            # Incident로 시작하는 테이블 찾기
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND (TABLE_NAME LIKE '%Incident%' OR TABLE_NAME LIKE '%Event%' OR TABLE_NAME LIKE '%Client%')
                ORDER BY TABLE_NAME
            """)
            
            incident_tables = cursor.fetchall()
            
            if incident_tables:
                print(f"✅ {len(incident_tables)}개 관련 테이블 발견:")
                for table in incident_tables:
                    schema = table[0] if hasattr(table, '__getitem__') else table.get('TABLE_SCHEMA', '')
                    name = table[1] if hasattr(table, '__getitem__') else table.get('TABLE_NAME', '')
                    print(f"   - {schema}.{name}")
            else:
                print("⚠️ Incident 관련 테이블을 찾을 수 없습니다.")
                print("   실제 테이블명을 확인해야 합니다.")
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"\n❌ 모듈 import 오류: {e}")
        print("\n💡 해결 방법:")
        print("   pip install pyodbc")
        return False
        
    except Exception as e:
        print(f"\n❌ 연결 오류: {e}")
        print(f"\n오류 타입: {type(e).__name__}")
        import traceback
        print(f"\n상세 오류:")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

