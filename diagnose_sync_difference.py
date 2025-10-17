#!/usr/bin/env python3
"""
개발 vs 상용 서버 Sync 결과 차이 진단 스크립트
"""
import sqlite3
from datetime import datetime, timedelta
import json

def get_db_connection():
    """DB 연결"""
    conn = sqlite3.connect('progress_report.db')
    conn.row_factory = sqlite3.Row
    return conn

def diagnose_sync_differences():
    """Sync 차이점 진단"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 SYNC 차이점 진단 보고서")
    print("=" * 80)
    print(f"진단 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Total incidents 통계
    print("1️⃣  전체 Incident 통계")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Open' THEN 1 END) as open,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue,
            COUNT(CASE WHEN status = 'Closed' THEN 1 END) as closed
        FROM cims_incidents
    """)
    
    stats = cursor.fetchone()
    print(f"   Total Incidents: {stats['total']}")
    print(f"   - Open: {stats['open']}")
    print(f"   - Overdue: {stats['overdue']}")
    print(f"   - Closed: {stats['closed']}")
    print()
    
    # 2. Fall incidents 분석 (sync 차이의 핵심)
    print("2️⃣  Fall Incident 분석 (tasks 없는 것)")
    print("-" * 80)
    
    cursor.execute("""
        SELECT i.id, i.incident_id, i.incident_date, i.incident_type, i.status
        FROM cims_incidents i
        WHERE i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND NOT EXISTS (
            SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id
        )
        ORDER BY i.incident_date DESC
    """)
    
    fall_without_tasks = cursor.fetchall()
    print(f"   Tasks 없는 Fall Incidents: {len(fall_without_tasks)}개")
    
    if fall_without_tasks:
        print(f"\n   최근 5개:")
        for idx, inc in enumerate(fall_without_tasks[:5], 1):
            print(f"     {idx}. {inc['incident_id']} | {inc['incident_date']} | {inc['status']}")
            print(f"        Type: {inc['incident_type']}")
    print()
    
    # 3. Incidents with tasks (status update 대상)
    print("3️⃣  Task가 있는 Incident 분석 (status update 대상)")
    print("-" * 80)
    
    cursor.execute("""
        SELECT DISTINCT i.id, i.incident_id, i.status, 
               COUNT(t.id) as task_count
        FROM cims_incidents i
        JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.status IN ('Open', 'Overdue')
        GROUP BY i.id, i.incident_id, i.status
        ORDER BY i.id
    """)
    
    incidents_with_tasks = cursor.fetchall()
    print(f"   Task가 있는 Open/Overdue Incidents: {len(incidents_with_tasks)}개")
    
    if incidents_with_tasks:
        print(f"\n   최근 5개:")
        for idx, inc in enumerate(incidents_with_tasks[:5], 1):
            print(f"     {idx}. {inc['incident_id']} | Status: {inc['status']} | Tasks: {inc['task_count']}개")
    print()
    
    # 4. All Fall incidents (tasks 있는 것 포함)
    print("4️⃣  전체 Fall Incident 통계")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_fall,
            COUNT(CASE WHEN status = 'Open' THEN 1 END) as open,
            COUNT(CASE WHEN status = 'Overdue' THEN 1 END) as overdue,
            COUNT(CASE WHEN status = 'Closed' THEN 1 END) as closed
        FROM cims_incidents
        WHERE incident_type LIKE '%Fall%'
    """)
    
    fall_stats = cursor.fetchone()
    print(f"   Total Fall Incidents: {fall_stats['total_fall']}")
    print(f"   - Open: {fall_stats['open']}")
    print(f"   - Overdue: {fall_stats['overdue']}")
    print(f"   - Closed: {fall_stats['closed']}")
    
    # Fall incidents with tasks
    cursor.execute("""
        SELECT COUNT(DISTINCT i.id) as count
        FROM cims_incidents i
        JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.incident_type LIKE '%Fall%'
    """)
    
    fall_with_tasks = cursor.fetchone()['count']
    print(f"   - Tasks 있음: {fall_with_tasks}")
    print(f"   - Tasks 없음: {len(fall_without_tasks)}")
    print()
    
    # 5. Policy 확인
    print("5️⃣  Active Policy 확인")
    print("-" * 80)
    
    cursor.execute("""
        SELECT id, name, is_active
        FROM cims_policies
        WHERE is_active = 1
    """)
    
    policies = cursor.fetchall()
    print(f"   Active Policies: {len(policies)}개")
    
    for policy in policies:
        print(f"     - {policy['name']} (ID: {policy['id']})")
        
        # Check if it's Fall policy
        cursor.execute("""
            SELECT rules_json FROM cims_policies WHERE id = ?
        """, (policy['id'],))
        
        rules_row = cursor.fetchone()
        if rules_row:
            try:
                rules = json.loads(rules_row['rules_json'])
                association = rules.get('incident_association', {})
                if association.get('incident_type') == 'Fall':
                    print(f"       → Fall Policy ✓")
                    schedule = rules.get('nurse_visit_schedule', [])
                    print(f"       → Visit Schedule: {len(schedule)} phases")
            except:
                pass
    print()
    
    # 6. Recent sync times
    print("6️⃣  최근 동기화 시간")
    print("-" * 80)
    
    cursor.execute("""
        SELECT key, value
        FROM system_settings
        WHERE key LIKE 'last_sync_%'
        ORDER BY key
    """)
    
    sync_times = cursor.fetchall()
    for st in sync_times:
        site_name = st['key'].replace('last_sync_', '').replace('_', ' ').title()
        try:
            sync_time = datetime.fromisoformat(st['value'])
            time_diff = datetime.now() - sync_time
            print(f"   {site_name}: {sync_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_diff.seconds // 60}분 전)")
        except:
            print(f"   {site_name}: {st['value']}")
    print()
    
    # 7. 가능한 원인 분석
    print("7️⃣  차이 발생 가능한 원인")
    print("-" * 80)
    
    reasons = []
    
    # Reason 1: No Fall policy
    if len(policies) == 0:
        reasons.append("❌ Active Policy가 없음 → Fall task 자동 생성 불가")
    else:
        has_fall_policy = False
        for policy in policies:
            cursor.execute("SELECT rules_json FROM cims_policies WHERE id = ?", (policy['id'],))
            rules_row = cursor.fetchone()
            if rules_row:
                try:
                    rules = json.loads(rules_row['rules_json'])
                    if rules.get('incident_association', {}).get('incident_type') == 'Fall':
                        has_fall_policy = True
                        break
                except:
                    pass
        
        if not has_fall_policy:
            reasons.append("❌ Fall Policy가 없음 → Fall task 자동 생성 불가")
        else:
            reasons.append("✅ Fall Policy 존재")
    
    # Reason 2: Database state differences
    if len(fall_without_tasks) > 0:
        reasons.append(f"⚠️  {len(fall_without_tasks)}개의 Fall incident에 task가 없음")
    else:
        reasons.append("✅ 모든 Fall incident에 task가 있음")
    
    if len(incidents_with_tasks) == 0:
        reasons.append("⚠️  Task가 있는 incident가 0개 → status update 불가")
    else:
        reasons.append(f"✅ {len(incidents_with_tasks)}개 incident가 status update 대상")
    
    # Reason 3: Recent incidents
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM cims_incidents
        WHERE incident_date >= datetime('now', '-7 days')
    """)
    
    recent = cursor.fetchone()['count']
    reasons.append(f"ℹ️  최근 7일 incident: {recent}개")
    
    for reason in reasons:
        print(f"   {reason}")
    
    print()
    print("=" * 80)
    print("✅ 진단 완료")
    print("=" * 80)
    print()
    print("💡 권장사항:")
    print("   1. 두 서버에서 이 스크립트를 실행하여 결과를 비교하세요")
    print("   2. Policy 설정이 동일한지 확인하세요 (cims_policies 테이블)")
    print("   3. DB 백업 시점이 다를 수 있습니다")
    print("   4. API 접근 설정이 다를 수 있습니다 (config.py)")
    print()
    
    conn.close()

if __name__ == '__main__':
    try:
        diagnose_sync_differences()
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

