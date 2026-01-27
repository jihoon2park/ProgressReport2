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
        print(f"❌ Database file not found: {db_path}")
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
        print("Data source diagnosis")
        print("=" * 60)
        print(f"\n📊 USE_DB_DIRECT_ACCESS setting: {use_db_direct}")
        
        if use_db_direct:
            print("   ⚠️  Direct DB access mode enabled")
            print("   → Incident load: query MANAD DB directly (real-time)")
            print("   → KPI calculation: query CIMS SQLite DB (synced data)")
            print("   → **Data sources differ!**")
        else:
            print("   ✅ API mode")
            print("   → Incident load: query CIMS SQLite DB")
            print("   → KPI calculation: query CIMS SQLite DB")
            print("   → Data sources are the same")
        
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
        print(f"\n📅 CIMS DB incidents (last 30 days): {cims_month_count}")
        
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
        print("\n📈 Status distribution (last 30 days):")
        for row in status_dist:
            print(f"   - {row[0]}: {row[1]}")
        
        # 4. 마지막 동기화 시간
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync = cursor.fetchone()
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync[0])
            days_ago = (datetime.now() - sync_time).days
            print(f"\n🔄 Last sync: {last_sync[0]} ({days_ago} days ago)")
            
            if days_ago > 1:
                print(f"   ⚠️  Sync ran {days_ago} days ago!")
                print("   → CIMS DB data may not be up to date")
        else:
            print("\n⚠️  No sync record found")
        
        # 5. 문제 진단
        print(f"\n{'='*60}")
        print("Issue diagnosis")
        print(f"{'='*60}")
        
        if use_db_direct:
            print("\n❌ Issue found:")
            print("   1. Incident load: query MANAD DB directly (real-time)")
            print("   2. KPI calculation: query CIMS SQLite DB (synced data)")
            print("   3. Because data sources differ, numbers may not match")
            print("\n💡 Fix options:")
            print("   - Update incident loading to use the CIMS SQLite DB as well")
            print("   - Or update KPI calculations to use the MANAD DB as well")
            print("   - Both APIs should use the same data source")
        
        if last_sync and (datetime.now() - datetime.fromisoformat(last_sync[0])).days > 1:
            print("\n❌ Additional issue:")
            print("   - CIMS DB sync ran a long time ago")
            print("   - Run Force Sync to update to the latest data")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    diagnose_data_source()

