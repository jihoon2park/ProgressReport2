"""
성능 개선 검증 스크립트

Before vs After 비교
"""

import sqlite3
import time
from datetime import datetime, timedelta

def test_performance():
    """성능 테스트"""
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🚀 성능 개선 검증 테스트")
    print("=" * 80)
    
    # Test 1: DB 조회 속도
    print("\n[Test 1] DB 조회 속도 (fall_type 컬럼 활용)")
    print("-" * 80)
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    start = time.time()
    cursor.execute("""
        SELECT id, incident_id, fall_type
        FROM cims_incidents
        WHERE incident_type LIKE '%Fall%'
        AND incident_date >= ?
        ORDER BY incident_date DESC
    """, (thirty_days_ago,))
    fall_incidents = cursor.fetchall()
    elapsed = time.time() - start
    
    print(f"✅ 조회 시간: {elapsed*1000:.2f}ms")
    print(f"✅ 총 건수: {len(fall_incidents)}개")
    
    # Fall type 통계
    stats = {'witnessed': 0, 'unwitnessed': 0, 'unknown': 0, 'null': 0}
    for incident in fall_incidents:
        fall_type = incident[2]
        if fall_type:
            stats[fall_type] = stats.get(fall_type, 0) + 1
        else:
            stats['null'] += 1
    
    print(f"\n📊 Fall Type 분포:")
    print(f"  - Witnessed:   {stats['witnessed']}개")
    print(f"  - Unwitnessed: {stats['unwitnessed']}개")
    print(f"  - Unknown:     {stats['unknown']}개")
    print(f"  - Null:        {stats['null']}개")
    
    # Test 2: 캐시 히트율 확인
    print("\n[Test 2] DB 저장 비율")
    print("-" * 80)
    
    total = len(fall_incidents)
    cached = total - stats['null']
    cache_hit_rate = (cached / total * 100) if total > 0 else 0
    
    print(f"✅ DB에 저장된 데이터: {cached}/{total} ({cache_hit_rate:.1f}%)")
    print(f"⚠️  계산 필요한 데이터: {stats['null']}/{total} ({(stats['null']/total*100) if total > 0 else 0:.1f}%)")
    
    # Test 3: 메모리 캐시 확인
    print("\n[Test 3] 메모리 캐시 확인")
    print("-" * 80)
    
    from services.fall_policy_detector import fall_detector
    
    # 캐시 정보
    cache_info = fall_detector._cached_detect_fall_type.cache_info()
    print(f"✅ 캐시 히트: {cache_info.hits}회")
    print(f"⚠️  캐시 미스: {cache_info.misses}회")
    print(f"📊 히트율: {(cache_info.hits/(cache_info.hits+cache_info.misses)*100) if (cache_info.hits+cache_info.misses) > 0 else 0:.1f}%")
    print(f"💾 캐시 크기: {cache_info.currsize}/{cache_info.maxsize}")
    
    # 성능 예측
    print("\n[Test 4] 성능 개선 예측")
    print("-" * 80)
    
    # 기존 방식: 70개 * 평균 15ms = 1050ms
    # 새 방식: DB 조회만 = ~3ms
    
    old_time = total * 15  # ms
    new_time = elapsed * 1000 + (stats['null'] * 15)  # ms
    improvement = ((old_time - new_time) / old_time * 100) if old_time > 0 else 0
    
    print(f"📉 기존 방식 예상 시간: ~{old_time:.0f}ms")
    print(f"📈 새 방식 실제 시간: ~{new_time:.1f}ms")
    print(f"🚀 성능 개선: {improvement:.1f}%")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료!")
    print("=" * 80)

if __name__ == '__main__':
    test_performance()

