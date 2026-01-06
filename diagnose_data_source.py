#!/usr/bin/env python3
"""
데이터 소스 진단 스크립트
인시던트 로드와 KPI가 서로 다른 데이터 소스를 사용하는지 확인
"""

import sqlite3
import os
from datetime import datetime, timedelta

def diagnose_data_source():
    """데이터 소스 진단"""
    
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. USE_DB_DIRECT_ACCESS 설정 확인
        cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
        result = cursor.fetchone()
        use_db_direct = result[0].lower() == 'true' if result and result[0] else False
        
        print("=" * 60)
        print("데이터 소스 진단")
        print("=" * 60)
        print(f"\n📊 USE_DB_DIRECT_ACCESS 설정: {use_db_direct}")
        
        if use_db_direct:
            print("   ⚠️  DB 직접 접속 모드 활성화")
            print("   → 인시던트 로드: MANAD DB에서 직접 조회 (실시간)")
            print("   → KPI 계산: CIMS SQLite DB에서 조회 (동기화된 데이터)")
            print("   → **데이터 소스가 다릅니다!**")
        else:
            print("   ✅ API 모드")
            print("   → 인시던트 로드: CIMS SQLite DB에서 조회")
            print("   → KPI 계산: CIMS SQLite DB에서 조회")
            print("   → 데이터 소스가 동일합니다")
        
        # 2. 최근 30일 인시던트 수 (CIMS DB)
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            AND incident_date != ''
            AND incident_date >= ?
        """, [month_ago])
        cims_month_count = cursor.fetchone()[0]
        print(f"\n📅 CIMS DB 최근 30일 인시던트: {cims_month_count}개")
        
        # 3. 상태별 분포 (최근 30일)
        cursor.execute("""
            SELECT status, COUNT(*) as cnt
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            AND incident_date != ''
            AND incident_date >= ?
            AND status IS NOT NULL AND status != ''
            GROUP BY status
            ORDER BY cnt DESC
        """, [month_ago])
        status_dist = cursor.fetchall()
        print(f"\n📈 최근 30일 상태별 분포:")
        for row in status_dist:
            print(f"   - {row[0]}: {row[1]}개")
        
        # 4. 마지막 동기화 시간
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync = cursor.fetchone()
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync[0])
            days_ago = (datetime.now() - sync_time).days
            print(f"\n🔄 마지막 동기화: {last_sync[0]} ({days_ago}일 전)")
            
            if days_ago > 1:
                print(f"   ⚠️  동기화가 {days_ago}일 전에 실행되었습니다!")
                print(f"   → CIMS DB 데이터가 최신이 아닐 수 있습니다")
        else:
            print(f"\n⚠️  동기화 기록이 없습니다")
        
        # 5. 문제 진단
        print(f"\n{'='*60}")
        print("문제 진단")
        print(f"{'='*60}")
        
        if use_db_direct:
            print("\n❌ 문제 발견:")
            print("   1. 인시던트 로드: MANAD DB에서 직접 조회 (실시간)")
            print("   2. KPI 계산: CIMS SQLite DB에서 조회 (동기화된 데이터)")
            print("   3. 두 데이터 소스가 다르므로 숫자가 일치하지 않을 수 있습니다")
            print("\n💡 해결 방법:")
            print("   - 인시던트 로드도 CIMS SQLite DB를 사용하도록 수정")
            print("   - 또는 KPI도 MANAD DB를 사용하도록 수정")
            print("   - 두 API가 동일한 데이터 소스를 사용해야 합니다")
        
        if last_sync and (datetime.now() - datetime.fromisoformat(last_sync[0])).days > 1:
            print("\n❌ 추가 문제:")
            print("   - CIMS DB 동기화가 오래 전에 실행되었습니다")
            print("   - Force Sync를 실행하여 최신 데이터로 업데이트하세요")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_data_source()

