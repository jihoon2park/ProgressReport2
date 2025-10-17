#!/usr/bin/env python3
"""
상용 서버 Sync 문제 확인 스크립트
- 왜 65개 Fall incident에 task가 생성되지 않았는지 확인
"""
import sqlite3
from datetime import datetime
import json

def get_db_connection():
    """DB 연결"""
    conn = sqlite3.connect('progress_report.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_production_issue():
    """상용 서버 문제 확인"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 상용 서버 Sync 문제 진단")
    print("=" * 80)
    print()
    
    # 1. Check if cims_policies table exists
    print("1️⃣  DB 스키마 확인")
    print("-" * 80)
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cims_policies'
    """)
    
    if cursor.fetchone():
        print("   ✅ cims_policies 테이블 존재")
        
        # Check policy count
        cursor.execute("SELECT COUNT(*) as count FROM cims_policies")
        policy_count = cursor.fetchone()['count']
        print(f"   📊 Total policies: {policy_count}개")
        
        cursor.execute("SELECT COUNT(*) as count FROM cims_policies WHERE is_active = 1")
        active_count = cursor.fetchone()['count']
        print(f"   📊 Active policies: {active_count}개")
        
        if active_count == 0:
            print("   ❌ 활성화된 Policy가 없습니다!")
            print("      → 이것이 task 생성 실패 원인입니다.")
        else:
            # Check Fall policy
            cursor.execute("""
                SELECT id, name, rules_json 
                FROM cims_policies 
                WHERE is_active = 1
            """)
            
            policies = cursor.fetchall()
            has_fall_policy = False
            
            for policy in policies:
                print(f"\n   Policy: {policy['name']}")
                try:
                    rules = json.loads(policy['rules_json'])
                    association = rules.get('incident_association', {})
                    incident_type = association.get('incident_type')
                    
                    print(f"     - Incident Type: {incident_type}")
                    
                    if incident_type == 'Fall':
                        has_fall_policy = True
                        print(f"     - ✅ Fall Policy입니다!")
                        
                        schedule = rules.get('nurse_visit_schedule', [])
                        print(f"     - Visit Schedule: {len(schedule)} phases")
                        
                        if len(schedule) == 0:
                            print(f"     - ❌ Visit schedule이 비어있습니다!")
                            print(f"        → Task를 생성할 수 없습니다.")
                        else:
                            for idx, phase in enumerate(schedule, 1):
                                print(f"       Phase {idx}: {phase.get('phase_name', 'N/A')}")
                    
                except Exception as e:
                    print(f"     - ⚠️  Rules JSON 파싱 오류: {str(e)}")
            
            if not has_fall_policy:
                print("\n   ❌ Fall Policy가 없습니다!")
                print("      → Fall incident에 대한 task를 생성할 수 없습니다.")
    else:
        print("   ❌ cims_policies 테이블이 없습니다!")
        print("      → Policy 마이그레이션이 필요합니다.")
    
    print()
    
    # 2. Check Fall incidents without tasks
    print("2️⃣  Task가 없는 Fall Incidents 확인")
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
        LIMIT 10
    """)
    
    incidents = cursor.fetchall()
    print(f"   Found: {len(incidents)}개 (최대 10개만 표시)")
    print()
    
    if incidents:
        for idx, inc in enumerate(incidents, 1):
            print(f"   {idx}. {inc['incident_id']}")
            print(f"      Date: {inc['incident_date']}")
            print(f"      Type: {inc['incident_type']}")
            print(f"      Status: {inc['status']}")
            print()
    
    # 3. Check if tasks table exists
    print("3️⃣  Task 테이블 확인")
    print("-" * 80)
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cims_tasks'
    """)
    
    if cursor.fetchone():
        print("   ✅ cims_tasks 테이블 존재")
        
        cursor.execute("SELECT COUNT(*) as count FROM cims_tasks")
        task_count = cursor.fetchone()['count']
        print(f"   📊 Total tasks: {task_count}개")
        
        if task_count == 0:
            print("   ⚠️  Task가 하나도 없습니다!")
    else:
        print("   ❌ cims_tasks 테이블이 없습니다!")
    
    print()
    
    # 4. Summary and recommendations
    print("4️⃣  진단 요약 및 해결 방법")
    print("-" * 80)
    
    # Check all issues
    issues = []
    solutions = []
    
    # Issue 1: No policies table
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cims_policies'
    """)
    if not cursor.fetchone():
        issues.append("❌ cims_policies 테이블 없음")
        solutions.append("1. Policy 마이그레이션 실행: python3 create_policy_tables.py")
        solutions.append("2. Fall Policy 생성: 개발 서버에서 policy 데이터를 export하여 import")
    else:
        # Check active policies
        cursor.execute("SELECT COUNT(*) as count FROM cims_policies WHERE is_active = 1")
        if cursor.fetchone()['count'] == 0:
            issues.append("❌ Active Policy 없음")
            solutions.append("1. Policy를 활성화하거나 새로 생성해야 합니다")
            solutions.append("2. 개발 서버의 cims_policies 테이블을 복사할 수 있습니다")
        else:
            # Check Fall policy
            cursor.execute("""
                SELECT id, rules_json 
                FROM cims_policies 
                WHERE is_active = 1
            """)
            
            has_fall_policy = False
            for policy in cursor.fetchall():
                try:
                    rules = json.loads(policy['rules_json'])
                    if rules.get('incident_association', {}).get('incident_type') == 'Fall':
                        has_fall_policy = True
                        schedule = rules.get('nurse_visit_schedule', [])
                        if len(schedule) == 0:
                            issues.append("❌ Fall Policy의 visit schedule이 비어있음")
                            solutions.append("1. Fall Policy의 rules_json을 수정해야 합니다")
                        else:
                            issues.append("✅ Fall Policy 정상")
                        break
                except:
                    pass
            
            if not has_fall_policy:
                issues.append("❌ Fall Policy 없음")
                solutions.append("1. Fall incident에 대한 Policy를 생성해야 합니다")
    
    print("   문제점:")
    for issue in issues:
        print(f"     {issue}")
    
    if solutions:
        print("\n   해결 방법:")
        for solution in solutions:
            print(f"     {solution}")
    
    print()
    print("=" * 80)
    print("✅ 진단 완료")
    print("=" * 80)
    print()
    print("💡 다음 단계:")
    print("   1. 이 스크립트를 상용 서버에서 실행하세요")
    print("   2. 문제가 발견되면 위의 해결 방법을 따르세요")
    print("   3. Policy 데이터를 복사해야 할 경우:")
    print("      - 개발: sqlite3 progress_report.db '.dump cims_policies' > policies.sql")
    print("      - 상용: sqlite3 progress_report.db < policies.sql")
    print()
    
    conn.close()

if __name__ == '__main__':
    try:
        check_production_issue()
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

