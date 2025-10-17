#!/usr/bin/env python3
"""
개발 vs 상용 서버 Dashboard KPI 차이 분석
최근 7일간의 incident를 비교하여 어떤 차이가 있는지 확인
"""
import sqlite3
from datetime import datetime, timedelta
import json

def get_db_connection():
    """DB 연결"""
    conn = sqlite3.connect('progress_report.db')
    conn.row_factory = sqlite3.Row
    return conn

def analyze_dashboard_kpis():
    """대시보드 KPI 분석 (최근 7일)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 Dashboard KPI 분석 (최근 7일)")
    print("=" * 80)
    print()
    
    # 현재 시간 기준 7일 전
    now = datetime.now()
    start_date = now - timedelta(days=7)
    
    print(f"📅 분석 기간:")
    print(f"   시작: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   종료: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   (최근 7일간)")
    print()
    
    # 1. 최근 7일간 전체 Incident 조회
    print("1️⃣  최근 7일간 Incident 목록")
    print("-" * 80)
    
    cursor.execute("""
        SELECT i.id, i.incident_id, i.incident_type, i.incident_date, 
               i.status, i.site, i.resident_name
        FROM cims_incidents i
        WHERE i.incident_date >= ?
        ORDER BY i.incident_date DESC
    """, (start_date.isoformat(),))
    
    incidents = cursor.fetchall()
    total_incidents = len(incidents)
    
    print(f"   Total Incidents: {total_incidents}개")
    print()
    
    # 2. Status별 분류
    print("2️⃣  Status별 분류")
    print("-" * 80)
    
    status_count = {}
    for inc in incidents:
        status = inc['status']
        status_count[status] = status_count.get(status, 0) + 1
    
    for status, count in sorted(status_count.items()):
        print(f"   {status}: {count}개")
    print()
    
    # 3. Site별 분류
    print("3️⃣  Site별 분류")
    print("-" * 80)
    
    site_count = {}
    for inc in incidents:
        site = inc['site'] or 'Unknown'
        site_count[site] = site_count.get(site, 0) + 1
    
    for site, count in sorted(site_count.items()):
        print(f"   {site}: {count}개")
    print()
    
    # 4. Incident Type별 분류
    print("4️⃣  Incident Type별 분류")
    print("-" * 80)
    
    type_count = {}
    for inc in incidents:
        inc_type = inc['incident_type'] or 'Unknown'
        type_count[inc_type] = type_count.get(inc_type, 0) + 1
    
    for inc_type, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
        print(f"   {inc_type}: {count}개")
    print()
    
    # 5. Task가 없는 Incident (Open Incidents)
    print("5️⃣  Task 없는 Incident (Open Incidents)")
    print("-" * 80)
    
    open_incidents = []
    for inc in incidents:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM cims_tasks
            WHERE incident_id = ?
        """, (inc['id'],))
        
        task_count = cursor.fetchone()['count']
        if task_count == 0:
            open_incidents.append(inc)
    
    print(f"   Open Incidents: {len(open_incidents)}개")
    
    if open_incidents:
        print(f"\n   목록:")
        for idx, inc in enumerate(open_incidents[:10], 1):
            print(f"     {idx}. {inc['incident_id']} | {inc['incident_date']} | {inc['incident_type']}")
            print(f"        Site: {inc['site']} | Resident: {inc['resident_name']}")
    print()
    
    # 6. Overdue Tasks가 있는 Incident
    print("6️⃣  Overdue Tasks")
    print("-" * 80)
    
    overdue_incidents = set()
    cursor.execute("""
        SELECT DISTINCT t.incident_id, i.incident_id as inc_id
        FROM cims_tasks t
        JOIN cims_incidents i ON i.id = t.incident_id
        WHERE t.status != 'completed'
        AND t.due_date < ?
        AND i.incident_date >= ?
    """, (now.isoformat(), start_date.isoformat()))
    
    overdue_tasks = cursor.fetchall()
    for task in overdue_tasks:
        overdue_incidents.add(task['incident_id'])
    
    print(f"   Overdue Tasks가 있는 Incidents: {len(overdue_incidents)}개")
    
    if overdue_incidents:
        print(f"\n   목록:")
        for idx, inc_id in enumerate(list(overdue_incidents)[:10], 1):
            cursor.execute("""
                SELECT incident_id, incident_type, incident_date, site
                FROM cims_incidents
                WHERE id = ?
            """, (inc_id,))
            inc = cursor.fetchone()
            if inc:
                print(f"     {idx}. {inc['incident_id']} | {inc['incident_date']} | {inc['incident_type']}")
    print()
    
    # 7. 7일 경계선 근처 Incident (±1시간)
    print("7️⃣  7일 경계선 근처 Incidents (중요!)")
    print("-" * 80)
    print(f"   경계선: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    boundary_start = start_date - timedelta(hours=1)
    boundary_end = start_date + timedelta(hours=1)
    
    cursor.execute("""
        SELECT i.incident_id, i.incident_type, i.incident_date, i.status, i.site
        FROM cims_incidents i
        WHERE i.incident_date BETWEEN ? AND ?
        ORDER BY i.incident_date DESC
    """, (boundary_start.isoformat(), boundary_end.isoformat()))
    
    boundary_incidents = cursor.fetchall()
    
    if boundary_incidents:
        print(f"   경계선 ±1시간 내 Incidents: {len(boundary_incidents)}개")
        print(f"   ⚠️  이 incidents가 서버 시간 차이로 포함/제외될 수 있습니다!")
        print()
        
        for idx, inc in enumerate(boundary_incidents, 1):
            inc_date = datetime.fromisoformat(inc['incident_date'])
            time_diff = (inc_date - start_date).total_seconds() / 60  # 분 단위
            included = "✅ 포함" if inc_date >= start_date else "❌ 제외"
            
            print(f"     {idx}. {inc['incident_id']}")
            print(f"        Date: {inc['incident_date']} ({included})")
            print(f"        경계선으로부터: {time_diff:+.1f}분")
            print(f"        Type: {inc['incident_type']} | Site: {inc['site']}")
            print()
    else:
        print("   경계선 근처에 incident가 없습니다.")
    print()
    
    # 8. KPI 요약 (Dashboard와 동일한 계산)
    print("8️⃣  Dashboard KPI 요약")
    print("-" * 80)
    
    print(f"   Total Incidents: {total_incidents}개")
    print(f"   Open Incidents (tasks 없음): {len(open_incidents)}개")
    print(f"   Overdue Tasks가 있는 Incidents: {len(overdue_incidents)}개")
    
    # Compliance Rate 계산
    completed_count = 0
    total_tasks = 0
    
    for inc in incidents:
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
            FROM cims_tasks
            WHERE incident_id = ?
        """, (inc['id'],))
        
        result = cursor.fetchone()
        total_tasks += result['total'] or 0
        completed_count += result['completed'] or 0
    
    compliance_rate = (completed_count * 100 / total_tasks) if total_tasks > 0 else 0
    print(f"   Total Tasks: {total_tasks}개")
    print(f"   Completed Tasks: {completed_count}개")
    print(f"   Compliance Rate: {compliance_rate:.1f}%")
    print()
    
    # 9. 서버 비교 가이드
    print("9️⃣  서버 비교 가이드")
    print("-" * 80)
    print("   개발 서버 결과: Total: 30, Open: 30, Overdue: 12")
    print("   상용 서버 결과: Total: 29, Open: 29, Overdue: 11")
    print()
    print("   📋 차이점 분석:")
    
    if total_incidents == 30:
        print("   ✅ 이 서버는 개발 서버입니다 (30개)")
    elif total_incidents == 29:
        print("   ✅ 이 서버는 상용 서버입니다 (29개)")
    else:
        print(f"   ℹ️  이 서버는 {total_incidents}개의 incident를 가지고 있습니다")
    
    print()
    print("   🔍 차이 발생 가능한 원인:")
    print("   1. 서버 시간 차이 (timezone, NTP sync)")
    print("   2. 7일 경계선 근처의 incident")
    print("   3. 동기화 타이밍 차이")
    print("   4. 한쪽 서버에만 있는 incident")
    print()
    
    # 10. 권장 사항
    print("🔟  권장 조치")
    print("-" * 80)
    print("   1. 두 서버의 시스템 시간 확인:")
    print("      date")
    print()
    print("   2. 경계선 근처 incidents 확인 (위 7번 참조)")
    print()
    print("   3. 두 서버에서 이 스크립트를 동시에 실행하여 비교")
    print()
    print("   4. 차이가 1개면 정상 (시간차로 인한 경계선 문제)")
    print("      차이가 2개 이상이면 동기화 문제 가능성")
    print()
    
    print("=" * 80)
    print("✅ 분석 완료")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    try:
        analyze_dashboard_kpis()
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

