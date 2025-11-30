#!/usr/bin/env python3
"""
Incident 219 (INC-5007) Keith Rainbow의 tasks 확인
"""

import sqlite3
import json

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

# 1. Incident 정보 확인
cursor.execute("""
    SELECT id, incident_id, resident_name, incident_type, fall_type, incident_date
    FROM cims_incidents
    WHERE id = 219
""")

incident = cursor.fetchone()
print("=" * 80)
print("=== Incident 219 정보 ===")
print("=" * 80)
print(f"DB ID: {incident[0]}")
print(f"Incident ID: {incident[1]}")
print(f"Resident: {incident[2]}")
print(f"Type: {incident[3]}")
print(f"Fall Type: {incident[4]}")
print(f"Incident Date: {incident[5]}")

# 2. 이 Incident의 모든 tasks 조회
cursor.execute("""
    SELECT t.id, t.task_id, t.task_name, t.due_date, t.status, 
           t.policy_id, p.policy_id as policy_code, p.name as policy_name
    FROM cims_tasks t
    LEFT JOIN cims_policies p ON t.policy_id = p.id
    WHERE t.incident_id = 219
    ORDER BY t.due_date
""")

tasks = cursor.fetchall()

print(f"\n=" * 80)
print(f"=== Tasks (Total: {len(tasks)}) ===")
print("=" * 80)

if tasks:
    for task in tasks:
        print(f"\nTask ID: {task[1]}")
        print(f"  Name: {task[2]}")
        print(f"  Due Date: {task[3]}")
        print(f"  Status: {task[4]}")
        print(f"  Policy DB ID: {task[5]}")
        print(f"  Policy Code: {task[6]}")
        print(f"  Policy Name: {task[7]}")
else:
    print("No tasks found!")

# 3. Policy 정보 확인
print(f"\n=" * 80)
print("=== All Fall Policies ===")
print("=" * 80)

cursor.execute("""
    SELECT id, policy_id, name, is_active, rules_json
    FROM cims_policies
    WHERE policy_id LIKE 'FALL-%'
""")

policies = cursor.fetchall()

for policy in policies:
    print(f"\nPolicy DB ID: {policy[0]}")
    print(f"Policy Code: {policy[1]}")
    print(f"Name: {policy[2]}")
    print(f"Active: {policy[3]}")
    
    rules = json.loads(policy[4])
    schedule = rules.get('nurse_visit_schedule', [])
    print(f"Phases: {len(schedule)}")
    
    total_visits = 0
    for phase in schedule:
        interval = int(phase.get('interval', 30))
        duration = int(phase.get('duration', 2))
        interval_unit = phase.get('interval_unit', 'minutes')
        duration_unit = phase.get('duration_unit', 'hours')
        
        interval_minutes = interval * 60 if interval_unit == 'hours' else interval
        duration_minutes = duration * 60 if duration_unit == 'hours' else duration * 24 * 60 if duration_unit == 'days' else duration
        
        num_visits = max(1, duration_minutes // interval_minutes)
        total_visits += num_visits
    
    print(f"Total Visits: {total_visits}")

conn.close()

