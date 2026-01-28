#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task display issue diagnosis script
- Check if tasks are actually created
- Check task due_date
- Check if there are tasks for today's date
"""
import sqlite3
import json
from datetime import datetime, timedelta
import sys
import io

# Configure UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Database path configuration
DB_PATH = 'progress_report.db'

def get_db_connection():
    """Connect to database"""
    return sqlite3.connect(DB_PATH)

def diagnose_task_display(site='Parafield Gardens'):
    """Diagnose task display issue"""
    print("=" * 60)
    print(f"[DIAGNOSE] Task Display Issue - {site}")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    today_str = today.strftime('%Y-%m-%d')
    yesterday = (today - timedelta(days=1))
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"\n[1] Date Info:")
    print(f"   Today: {today_str}")
    print(f"   Yesterday: {yesterday_str}")
    
    # 1. Check recent Fall Incidents for Parafield Gardens
    print(f"\n[2] Recent Fall Incidents ({site}):")
    cursor.execute("""
        SELECT 
            id, incident_id, incident_type, incident_date, 
            status, fall_type
        FROM cims_incidents
        WHERE site = ?
        AND incident_type LIKE '%Fall%'
        AND status IN ('Open', 'Overdue')
        ORDER BY incident_date DESC
        LIMIT 10
    """, (site,))
    
    incidents = cursor.fetchall()
    print(f"   Total Open/Overdue Fall Incidents: {len(incidents)}")
    
    for inc in incidents[:5]:
        inc_date = inc[3]
        inc_date_obj = datetime.fromisoformat(inc_date).date() if inc_date else None
        date_marker = ""
        if inc_date_obj:
            if inc_date_obj == today:
                date_marker = " [TODAY]"
            elif inc_date_obj == yesterday:
                date_marker = " [YESTERDAY]"
        print(f"      - {inc[1]}: {inc_date} ({inc[4]}){date_marker}")
    
    # 2. Check tasks
    print(f"\n[3] Tasks for {site}:")
    cursor.execute("""
        SELECT 
            t.id, t.task_id, t.task_name, t.due_date, t.status,
            i.incident_id, i.incident_date
        FROM cims_tasks t
        JOIN cims_incidents i ON t.incident_id = i.id
        WHERE i.site = ?
        ORDER BY t.due_date DESC
        LIMIT 20
    """, (site,))
    
    tasks = cursor.fetchall()
    print(f"   Total Tasks: {len(tasks)}")
    
    if tasks:
        # Classify by date
        today_tasks = []
        yesterday_tasks = []
        other_tasks = []
        
        for task in tasks:
            due_date_str = task[3]
            if not due_date_str:
                other_tasks.append(task)
                continue
                
            try:
                due_date_obj = datetime.fromisoformat(due_date_str).date()
                if due_date_obj == today:
                    today_tasks.append(task)
                elif due_date_obj == yesterday:
                    yesterday_tasks.append(task)
                else:
                    other_tasks.append(task)
            except:
                other_tasks.append(task)
        
        print(f"\n   Tasks by Date:")
        print(f"      Today ({today_str}): {len(today_tasks)} tasks")
        for task in today_tasks[:5]:
            print(f"         - {task[1]}: {task[3]} ({task[4]}) - Incident: {task[5]}")
        
        print(f"\n      Yesterday ({yesterday_str}): {len(yesterday_tasks)} tasks")
        for task in yesterday_tasks[:5]:
            print(f"         - {task[1]}: {task[3]} ({task[4]}) - Incident: {task[5]}")
        
        print(f"\n      Other dates: {len(other_tasks)} tasks")
        for task in other_tasks[:5]:
            print(f"         - {task[1]}: {task[3]} ({task[4]}) - Incident: {task[5]}")
    else:
        print("   [ERROR] No tasks found!")
    
    # 3. Check incidents with tasks for today's date
    print(f"\n[4] Incidents with Tasks Today ({today_str}):")
    cursor.execute("""
        SELECT DISTINCT
            i.id, i.incident_id, i.incident_date, i.status,
            COUNT(t.id) as task_count
        FROM cims_incidents i
        JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.site = ?
        AND i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND DATE(t.due_date) = DATE(?)
        GROUP BY i.id
        ORDER BY i.incident_date DESC
    """, (site, today_str))
    
    incidents_with_tasks_today = cursor.fetchall()
    
    if incidents_with_tasks_today:
        print(f"   Found {len(incidents_with_tasks_today)} incidents with tasks today:")
        for inc in incidents_with_tasks_today:
            print(f"      - {inc[1]}: {inc[4]} tasks (incident_date: {inc[2]})")
    else:
        print("   [WARNING] No incidents with tasks due today!")
    
    # 4. Simulate schedule-batch API conditions (from 5 days ago)
    print(f"\n[5] Schedule-Batch API Simulation (5 days before {today_str}):")
    five_days_before = (today - timedelta(days=5)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT 
            i.id, i.incident_id, i.incident_type, i.incident_date,
            i.status, i.fall_type,
            t.id as task_db_id, t.task_id, t.task_name, t.due_date, 
            t.status as task_status
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.site = ? 
        AND DATE(i.incident_date) >= DATE(?)
        AND i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        ORDER BY i.incident_date DESC, t.due_date ASC
    """, (site, five_days_before))
    
    rows = cursor.fetchall()
    
    # Group by incidents
    incidents_map = {}
    for row in rows:
        incident_id = row[0]
        if incident_id not in incidents_map:
            incidents_map[incident_id] = {
                'incident_id': row[1],
                'incident_date': row[2],
                'status': row[4],
                'tasks': []
            }
        
        if row[6] is not None:  # task_db_id
            incidents_map[incident_id]['tasks'].append({
                'task_id': row[7],
                'due_date': row[9],
                'status': row[10]
            })
    
    print(f"   API would return {len(incidents_map)} incidents")
    
    # Check incidents with tasks for today's date
    incidents_with_tasks_today_api = []
    for inc_id, inc_data in incidents_map.items():
        for task in inc_data['tasks']:
            if task['due_date']:
                try:
                    task_date = datetime.fromisoformat(task['due_date']).date()
                    if task_date == today:
                        incidents_with_tasks_today_api.append({
                            'incident_id': inc_data['incident_id'],
                            'incident_date': inc_data['incident_date'],
                            'task': task
                        })
                        break
                except:
                    pass
    
    if incidents_with_tasks_today_api:
        print(f"\n   Incidents with tasks due today (from API simulation):")
        for item in incidents_with_tasks_today_api[:5]:
            print(f"      - {item['incident_id']}: task {item['task']['task_id']} due {item['task']['due_date']}")
    else:
        print(f"\n   [WARNING] No incidents with tasks due today in API simulation!")
    
    # 6. Check task creation logic - check if recent Fall Incidents have tasks
    print(f"\n[6] Recent Fall Incidents Task Status:")
    cursor.execute("""
        SELECT 
            i.id, i.incident_id, i.incident_date, i.status,
            COUNT(t.id) as task_count
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.site = ?
        AND i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND DATE(i.incident_date) >= DATE(?)
        GROUP BY i.id
        ORDER BY i.incident_date DESC
    """, (site, five_days_before))
    
    recent_incidents = cursor.fetchall()
    
    incidents_without_tasks = [inc for inc in recent_incidents if inc[4] == 0]
    incidents_with_tasks = [inc for inc in recent_incidents if inc[4] > 0]
    
    print(f"   Total incidents (last 5 days): {len(recent_incidents)}")
    print(f"   With tasks: {len(incidents_with_tasks)}")
    print(f"   Without tasks: {len(incidents_without_tasks)}")
    
    if incidents_without_tasks:
        print(f"\n   [WARNING] Incidents without tasks:")
        for inc in incidents_without_tasks[:5]:
            print(f"      - {inc[1]} (incident_date: {inc[2]})")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("[COMPLETE] Diagnosis finished")
    print("=" * 60)

if __name__ == '__main__':
    import sys
    site = sys.argv[1] if len(sys.argv) > 1 else 'Parafield Gardens'
    try:
        diagnose_task_display(site)
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

