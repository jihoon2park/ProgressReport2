#!/usr/bin/env python3
"""CIMS 동기화 최적화 빠른 확인 스크립트"""

import sqlite3
from datetime import datetime

print("\n🔍 CIMS 동기화 최적화 상태 확인\n")

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

# 1. 기본 통계
cursor.execute("SELECT COUNT(*) FROM cims_incidents WHERE status = 'Open'")
open_incidents = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM clients_cache WHERE is_active = 1")
cached_clients = cursor.fetchone()[0]

print(f"📊 데이터:")
print(f"   • Open 인시던트: {open_incidents}개")
print(f"   • 클라이언트 캐시: {cached_clients}명")

# 2. 최적화 상태
cursor.execute("""
    SELECT value FROM system_settings 
    WHERE key = 'last_incident_sync_time'
""")
last_sync = cursor.fetchone()

if last_sync:
    sync_time = datetime.fromisoformat(last_sync[0])
    minutes_ago = int((datetime.now() - sync_time).total_seconds() / 60)
    
    print(f"\n⏰ 동기화:")
    print(f"   • 마지막 동기화: {minutes_ago}분 전")
    
    if minutes_ago < 5:
        print(f"   • 상태: ✅ 최신 (다음: {5-minutes_ago}분 후)")
    else:
        print(f"   • 상태: ⏰ 동기화 필요")
else:
    print(f"\n⏰ 동기화: ⚠️ 동기화 기록 없음")

# 3. 클라이언트 캐시 상태
cursor.execute("SELECT MAX(last_synced) FROM clients_cache")
last_client_cache = cursor.fetchone()[0]

if last_client_cache:
    cache_time = datetime.fromisoformat(last_client_cache)
    hours_ago = (datetime.now() - cache_time).total_seconds() / 3600
    
    print(f"\n💾 클라이언트 캐시:")
    print(f"   • 마지막 갱신: {hours_ago:.1f}시간 전")
    
    if hours_ago < 24:
        print(f"   • 상태: ✅ 유효 (다음: {24-hours_ago:.1f}시간 후)")
    else:
        print(f"   • 상태: ⏰ 갱신 필요")
else:
    print(f"\n💾 클라이언트 캐시: ⚠️ 캐시 없음")

# 4. 데이터 품질
cursor.execute("""
    SELECT 
        COUNT(CASE WHEN resident_name != '' AND resident_name IS NOT NULL THEN 1 END) * 100.0 / COUNT(*)
    FROM cims_incidents
""")
quality = cursor.fetchone()[0]

print(f"\n✅ 데이터 품질:")
print(f"   • 거주자 이름: {quality:.0f}%")

# 5. 사이트별 요약
cursor.execute("""
    SELECT site, COUNT(*) 
    FROM cims_incidents 
    WHERE status = 'Open'
    GROUP BY site
    ORDER BY COUNT(*) DESC
""")
sites = cursor.fetchall()

print(f"\n🏥 사이트별:")
for site, count in sites:
    print(f"   • {site}: {count}개")

conn.close()

# 결론
print(f"\n{'─'*50}")
if open_incidents > 0 and cached_clients > 0 and quality == 100:
    print("🎉 모든 최적화가 정상 작동 중입니다!")
else:
    print("⚠️  일부 설정을 확인하세요.")
print(f"{'─'*50}\n")

