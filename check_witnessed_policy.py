#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

cursor.execute('SELECT policy_id, rules_json FROM cims_policies WHERE policy_id = "FALL-002-WITNESSED"')
row = cursor.fetchone()

if row:
    print('=' * 60)
    print('FALL-002-WITNESSED Policy')
    print('=' * 60)
    rules = json.loads(row[1])
    schedule = rules.get('nurse_visit_schedule', [])
    
    print(f'\nPhases: {len(schedule)}')
    for idx, phase in enumerate(schedule, 1):
        interval = phase.get('interval', 30)
        interval_unit = phase.get('interval_unit', 'minutes')
        duration = phase.get('duration', 30)
        duration_unit = phase.get('duration_unit', 'minutes')
        
        interval_minutes = interval * 60 if interval_unit == 'hours' else interval
        duration_minutes = duration * 60 if duration_unit == 'hours' else duration * 24 * 60 if duration_unit == 'days' else duration
        
        num_visits = max(1, duration_minutes // interval_minutes)
        
        print(f'\nPhase {idx}:')
        print(f'  Interval: {interval} {interval_unit} ({interval_minutes} minutes)')
        print(f'  Duration: {duration} {duration_unit} ({duration_minutes} minutes)')
        print(f'  Expected visits: {num_visits}')
        print(f'  Full config: {json.dumps(phase, indent=4)}')
else:
    print('❌ FALL-002-WITNESSED policy not found!')

conn.close()

