#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task가 보이지 않는 문제 진단 스크립트
"""
import sqlite3
import json
from datetime import datetime, timedelta
import sys
import os
import io

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# DB 경로 설정
DB_PATH = 'progress_report.db'

def get_db_connection():
    """DB 연결"""
    return sqlite3.connect(DB_PATH)

def diagnose_task_issue():
    """Task 문제 진단"""
    print("=" * 60)
    print("[DIAGNOSE] Task Problem Diagnosis")
    print("=" * 60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Policy 확인
    print("\n[1] Fall Policy Check:")
    cursor.execute("""
        SELECT id, policy_id, name, is_active, rules_json
        FROM cims_policies
        WHERE policy_id LIKE 'FALL-%'
    """)
    policies = cursor.fetchall()
    
    if not policies:
        print("   [ERROR] No Fall Policy found!")
        print("   [SOLUTION] Run Force Synchronization from Settings page")
    else:
        active_policies = [p for p in policies if p[3] == 1]
        print(f"   [OK] Total {len(policies)} policies found (Active: {len(active_policies)})")
        for policy in policies:
            status = "[ACTIVE]" if policy[3] == 1 else "[INACTIVE]"
            print(f"      - {policy[1]} ({policy[2]}): {status}")
    
    # 2. Fall Incidents 확인
    print("\n[2] Fall Incidents Check:")
    cursor.execute("""
        SELECT 
            id, incident_id, incident_type, incident_date, 
            status, site, fall_type
        FROM cims_incidents
        WHERE incident_type LIKE '%Fall%'
        ORDER BY incident_date DESC
        LIMIT 20
    """)
    incidents = cursor.fetchall()
    
    if not incidents:
        print("   [ERROR] No Fall Incident found!")
    else:
        print(f"   [OK] Total {len(incidents)} Fall Incidents found")
        
        # Status별 분류
        status_count = {}
        for inc in incidents:
            status = inc[4] or 'NULL'
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"   Status 분포:")
        for status, count in status_count.items():
            marker = "[OK]" if status in ['Open', 'Overdue'] else "[WARN]"
            print(f"      {marker} {status}: {count}개")
        
        # Open/Overdue만 표시
        open_incidents = [inc for inc in incidents if inc[4] in ['Open', 'Overdue']]
        print(f"\n   [OK] Open/Overdue status: {len(open_incidents)} incidents")
        for inc in open_incidents[:5]:
            print(f"      - {inc[1]} ({inc[5]}): {inc[4]} - fall_type={inc[6]}")
    
    # 3. Tasks 확인
    print("\n[3] Tasks Check:")
    cursor.execute("""
        SELECT COUNT(*) FROM cims_tasks
    """)
    total_tasks = cursor.fetchone()[0]
    print(f"   총 Tasks: {total_tasks}개")
    
    if total_tasks == 0:
        print("   [ERROR] No tasks found!")
    else:
        # Task 상태별 분류
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM cims_tasks 
            GROUP BY status
        """)
        task_status = cursor.fetchall()
        print(f"   Status 분포:")
        for status, count in task_status:
            print(f"      - {status}: {count}개")
        
        # Incident별 Task 수
        cursor.execute("""
            SELECT 
                i.incident_id, i.status, i.site,
                COUNT(t.id) as task_count
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            GROUP BY i.id
            ORDER BY task_count ASC, i.incident_date DESC
            LIMIT 10
        """)
        incident_tasks = cursor.fetchall()
        
        print(f"\n   Incident별 Task 수 (최소 Task부터):")
        for inc_id, inc_status, site, task_count in incident_tasks:
            marker = "[NO TASKS]" if task_count == 0 else "[HAS TASKS]"
            print(f"      {marker} {inc_id} ({site}): {task_count}개 tasks")
    
    # 4. Task가 없는 Fall Incident 확인
    print("\n[4] Fall Incidents Without Tasks:")
    cursor.execute("""
        SELECT 
            i.id, i.incident_id, i.incident_type, i.incident_date,
            i.status, i.site, i.fall_type
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND t.id IS NULL
        ORDER BY i.incident_date DESC
        LIMIT 10
    """)
    incidents_without_tasks = cursor.fetchall()
    
    if not incidents_without_tasks:
        print("   [OK] All Open/Overdue Fall Incidents have tasks!")
    else:
        print(f"   [ERROR] {len(incidents_without_tasks)} incidents without tasks:")
        for inc in incidents_without_tasks:
            print(f"      - {inc[1]} ({inc[5]}): status={inc[4]}, fall_type={inc[6]}")
        print(f"\n   [SOLUTION]:")
        print(f"      1. Mobile Dashboard를 새로고침 (자동 생성 시도)")
        print(f"      2. Settings에서 Force Synchronization 실행")
    
    # 5. 최근 5일 내 Incident 확인 (schedule-batch API 조건)
    print("\n[5] Recent 5 Days Fall Incidents (schedule-batch API conditions):")
    five_days_ago = (datetime.now() - timedelta(days=5)).isoformat()
    
    cursor.execute("""
        SELECT 
            i.id, i.incident_id, i.incident_type, i.incident_date,
            i.status, i.site, i.fall_type,
            COUNT(t.id) as task_count
        FROM cims_incidents i
        LEFT JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND DATE(i.incident_date) >= DATE(?)
        GROUP BY i.id
        ORDER BY i.incident_date DESC
    """, (five_days_ago,))
    
    recent_incidents = cursor.fetchall()
    
    if not recent_incidents:
        print("   [ERROR] No matching incidents in last 5 days!")
        print("   [CONDITIONS]:")
        print("      - incident_type LIKE '%Fall%'")
        print("      - status IN ('Open', 'Overdue')")
        print("      - incident_date >= 5일 전")
    else:
        print(f"   [OK] {len(recent_incidents)} incidents found:")
        for inc in recent_incidents[:10]:
            task_marker = "[NO TASKS]" if inc[7] == 0 else "[HAS TASKS]"
            print(f"      {task_marker} {inc[1]} ({inc[5]}): {inc[7]}개 tasks, status={inc[4]}")
    
    # 6. 사이트별 요약
    print("\n[6] Site Summary:")
    sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
    
    for site in sites:
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT i.id) as incident_count,
                COUNT(t.id) as task_count
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.site = ?
            AND i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            AND DATE(i.incident_date) >= DATE(?)
        """, (site, five_days_ago))
        
        result = cursor.fetchone()
        incident_count = result[0] or 0
        task_count = result[1] or 0
        
        if incident_count > 0:
            marker = "[OK]" if task_count > 0 else "[NO TASKS]"
            print(f"   {marker} {site}: {incident_count}개 incidents, {task_count}개 tasks")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("[COMPLETE] Diagnosis finished")
    print("=" * 60)

if __name__ == '__main__':
    try:
        diagnose_task_issue()
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

