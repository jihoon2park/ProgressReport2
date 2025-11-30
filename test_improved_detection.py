"""
개선된 Fall Detection 로직 전체 테스트
"""

import sqlite3
from datetime import datetime, timedelta
from services.fall_policy_detector import fall_detector

def test_all_falls():
    """전체 Fall incidents 분류 테스트"""
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    # 최근 30일 Fall incidents 조회
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute("""
        SELECT id, incident_id, incident_type, site, description
        FROM cims_incidents
        WHERE incident_type LIKE '%Fall%'
        AND incident_date >= ?
        ORDER BY incident_date DESC
    """, (thirty_days_ago,))
    
    incidents = cursor.fetchall()
    
    # 통계
    stats = {
        'total': len(incidents),
        'witnessed': 0,
        'unwitnessed': 0,
        'unknown': 0,
        'by_site': {}
    }
    
    print("=" * 80)
    print("🔍 개선된 Fall Detection 로직 테스트")
    print("=" * 80)
    print(f"\n📊 총 {len(incidents)}개 Fall incidents 분석 중...\n")
    
    for incident in incidents:
        incident_id = incident[0]
        incident_manad_id = incident[1]
        site = incident[3]
        
        # Fall 유형 감지
        fall_type = fall_detector.detect_fall_type_from_incident(incident_id, cursor)
        
        # 통계 업데이트
        stats[fall_type] += 1
        
        if site not in stats['by_site']:
            stats['by_site'][site] = {
                'witnessed': 0,
                'unwitnessed': 0,
                'unknown': 0
            }
        stats['by_site'][site][fall_type] += 1
    
    conn.close()
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("📈 전체 결과:")
    print("=" * 80)
    print(f"\n{'분류':<20} {'건수':<10} {'비율':<10}")
    print("-" * 80)
    print(f"{'Total Falls':<20} {stats['total']:<10} {100.0:>6.1f}%")
    print(f"{'Witnessed':<20} {stats['witnessed']:<10} {stats['witnessed']/stats['total']*100:>6.1f}%")
    print(f"{'Unwitnessed':<20} {stats['unwitnessed']:<10} {stats['unwitnessed']/stats['total']*100:>6.1f}%")
    print(f"{'Unknown':<20} {stats['unknown']:<10} {stats['unknown']/stats['total']*100:>6.1f}%")
    
    print("\n" + "=" * 80)
    print("📍 사이트별 분포:")
    print("=" * 80)
    print(f"\n{'Site':<20} {'Witnessed':<12} {'Unwitnessed':<14} {'Unknown':<10}")
    print("-" * 80)
    
    for site, site_stats in sorted(stats['by_site'].items()):
        print(f"{site:<20} {site_stats['witnessed']:<12} {site_stats['unwitnessed']:<14} {site_stats['unknown']:<10}")
    
    # 개선도 계산
    print("\n" + "=" * 80)
    print("🎯 성능 지표:")
    print("=" * 80)
    accuracy = (stats['witnessed'] + stats['unwitnessed']) / stats['total'] * 100
    print(f"  ✅ 분류 정확도: {accuracy:.1f}% ({stats['witnessed'] + stats['unwitnessed']}/{stats['total']}개 성공)")
    print(f"  ❓ Unknown 비율: {stats['unknown']/stats['total']*100:.1f}% ({stats['unknown']}/{stats['total']}개)")
    print(f"\n  💡 개선 목표: Unknown을 10% 미만으로 줄이기")
    
    if stats['unknown'] > 0:
        print(f"\n  📝 참고: 남은 {stats['unknown']}개 Unknown cases를 수동 검토하여 추가 패턴 발견 가능")

if __name__ == '__main__':
    test_all_falls()

