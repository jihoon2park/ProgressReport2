#!/usr/bin/env python3
"""
CIMS 데이터베이스 상태 확인 스크립트
프로덕션 서버에서 cims_incidents 테이블 상태를 확인합니다.
"""

import sqlite3
import os
from datetime import datetime, timedelta

def check_cims_data():
    """CIMS 데이터베이스 상태 확인"""
    
    # 데이터베이스 경로
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. 테이블 존재 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
        if not cursor.fetchone():
            print("❌ cims_incidents 테이블이 존재하지 않습니다.")
            return
        
        print("✅ cims_incidents 테이블 존재 확인")
        
        # 2. 전체 인시던트 수
        cursor.execute("SELECT COUNT(*) as total FROM cims_incidents")
        total = cursor.fetchone()[0]
        print(f"\n📊 전체 인시던트 수: {total}")
        
        if total == 0:
            print("⚠️  테이블이 비어있습니다. 동기화가 필요합니다.")
            print("   해결 방법: /api/cims/force-sync API를 호출하거나 서버를 재시작하세요.")
            return
        
        # 3. 날짜별 통계
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN incident_date IS NOT NULL AND incident_date != '' THEN 1 END) as with_date,
                COUNT(CASE WHEN status IS NOT NULL AND status != '' THEN 1 END) as with_status
            FROM cims_incidents
        """)
        stats = cursor.fetchone()
        print(f"   - 날짜가 있는 인시던트: {stats[1]}")
        print(f"   - 상태가 있는 인시던트: {stats[2]}")
        
        # 4. 상태별 분포
        cursor.execute("""
            SELECT status, COUNT(*) as cnt
            FROM cims_incidents
            WHERE status IS NOT NULL AND status != ''
            GROUP BY status
            ORDER BY cnt DESC
        """)
        status_dist = cursor.fetchall()
        print(f"\n📈 상태별 분포:")
        for row in status_dist:
            print(f"   - {row[0]}: {row[1]}개")
        
        # 5. 최근 7일 인시던트 수
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            AND incident_date != ''
            AND incident_date >= ?
        """, [week_ago])
        week_count = cursor.fetchone()[0]
        print(f"\n📅 최근 7일 인시던트: {week_count}개")
        
        # 6. 날짜 샘플
        cursor.execute("""
            SELECT incident_date, status, incident_type
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            ORDER BY incident_date DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print(f"\n📋 최근 인시던트 샘플 (5개):")
        for row in samples:
            print(f"   - {row[0]} | {row[1]} | {row[2]}")
        
        # 7. 동기화 상태 확인
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync = cursor.fetchone()
        if last_sync:
            print(f"\n🔄 마지막 동기화 시간: {last_sync[0]}")
        else:
            print(f"\n⚠️  동기화 기록이 없습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_cims_data()

