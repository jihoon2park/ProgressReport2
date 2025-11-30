#!/usr/bin/env python3
"""
Witnessed Fall Task 생성 문제 진단
"""

import sqlite3
import json

def main():
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()

    # 1. Check policies
    cursor.execute('SELECT policy_id, name, is_active, rules_json FROM cims_policies WHERE policy_id LIKE "FALL-%"')
    policies = cursor.fetchall()

    print('=' * 60)
    print('=== Fall Policies in DB ===')
    print('=' * 60)
    for policy_id, name, is_active, rules_json in policies:
        print(f'\n{policy_id}: {name} (Active: {is_active})')
        
        # Get visit schedule details
        rules = json.loads(rules_json)
        schedule = rules.get('nurse_visit_schedule', [])
        
        total_visits = 0
        print(f'  Phases: {len(schedule)}')
        for idx, phase in enumerate(schedule, 1):
            interval = int(phase.get('interval', 30))
            duration = int(phase.get('duration', 2))
            interval_unit = phase.get('interval_unit', 'minutes')
            duration_unit = phase.get('duration_unit', 'hours')
            
            interval_minutes = interval * 60 if interval_unit == 'hours' else interval
            duration_minutes = duration * 60 if duration_unit == 'hours' else duration * 24 * 60 if duration_unit == 'days' else duration
            
            num_visits = max(1, duration_minutes // interval_minutes)
            total_visits += num_visits
            
            print(f'    Phase {idx}: {num_visits} visits (Every {interval} {interval_unit} for {duration} {duration_unit})')
            
        print(f'  -> TOTAL VISITS: {total_visits}')

    print('\n' + '=' * 60)
    print('=== Fall Type Distribution (Open/Overdue) ===')
    print('=' * 60)
    
    # 2. Check fall_type distribution
    cursor.execute('''
        SELECT fall_type, COUNT(*) 
        FROM cims_incidents 
        WHERE incident_type LIKE "%Fall%" 
        AND status IN ("Open", "Overdue")
        GROUP BY fall_type
    ''')
    fall_types = cursor.fetchall()

    for fall_type, count in fall_types:
        display_type = fall_type if fall_type else "(NULL)"
        print(f'{display_type}: {count}')

    print('\n' + '=' * 60)
    print('=== Witnessed Falls Task Count (Sample 10) ===')
    print('=' * 60)
    
    # 3. Check tasks for witnessed falls
    cursor.execute('''
        SELECT i.incident_id, i.fall_type, COUNT(t.id) as task_count, 
               t.policy_id, p.policy_id as policy_code
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        LEFT JOIN cims_policies p ON t.policy_id = p.id
        WHERE i.incident_type LIKE "%Fall%"
        AND i.status IN ("Open", "Overdue")
        AND i.fall_type = "witnessed"
        GROUP BY i.incident_id, i.fall_type, t.policy_id, p.policy_id
        LIMIT 10
    ''')
    witnessed_tasks = cursor.fetchall()

    if witnessed_tasks:
        for incident_id, fall_type, task_count, policy_db_id, policy_code in witnessed_tasks:
            print(f'{incident_id}: {task_count} tasks (Policy: {policy_code or "N/A"})')
    else:
        print('No witnessed falls with tasks found.')

    print('\n' + '=' * 60)
    print('=== Unwitnessed Falls Task Count (Sample 5) ===')
    print('=' * 60)
    
    # 4. Check tasks for unwitnessed falls
    cursor.execute('''
        SELECT i.incident_id, i.fall_type, COUNT(t.id) as task_count, 
               p.policy_id as policy_code
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        LEFT JOIN cims_policies p ON t.policy_id = p.id
        WHERE i.incident_type LIKE "%Fall%"
        AND i.status IN ("Open", "Overdue")
        AND i.fall_type = "unwitnessed"
        GROUP BY i.incident_id, i.fall_type, p.policy_id
        LIMIT 5
    ''')
    unwitnessed_tasks = cursor.fetchall()

    if unwitnessed_tasks:
        for incident_id, fall_type, task_count, policy_code in unwitnessed_tasks:
            print(f'{incident_id}: {task_count} tasks (Policy: {policy_code or "N/A"})')
    else:
        print('No unwitnessed falls with tasks found.')

    conn.close()

if __name__ == '__main__':
    main()

