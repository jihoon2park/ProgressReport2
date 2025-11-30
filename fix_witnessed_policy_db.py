#!/usr/bin/env python3
"""
FALL-002-WITNESSED Policy의 duration_unit 수정
"""

import sqlite3
import json

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

# FALL-002-WITNESSED policy 조회
cursor.execute('SELECT id, policy_id, rules_json FROM cims_policies WHERE policy_id = "FALL-002-WITNESSED"')
row = cursor.fetchone()

if row:
    print('=' * 60)
    print('FALL-002-WITNESSED Policy 수정')
    print('=' * 60)
    
    rules = json.loads(row[2])
    schedule = rules.get('nurse_visit_schedule', [])
    
    print(f'\n수정 전:')
    for idx, phase in enumerate(schedule, 1):
        print(f'  Phase {idx}: duration_unit="{phase.get("duration_unit", "")}"')
    
    # duration_unit 수정
    modified = False
    for phase in schedule:
        if not phase.get('duration_unit') or phase.get('duration_unit') == '':
            phase['duration_unit'] = 'minutes'
            modified = True
            print(f'\n✅ Phase 수정: duration_unit="minutes"로 변경')
    
    if modified:
        # DB 업데이트
        cursor.execute("""
            UPDATE cims_policies 
            SET rules_json = ?
            WHERE policy_id = 'FALL-002-WITNESSED'
        """, (json.dumps(rules),))
        
        conn.commit()
        
        print(f'\n수정 후:')
        for idx, phase in enumerate(schedule, 1):
            print(f'  Phase {idx}: duration_unit="{phase.get("duration_unit")}"')
        
        print('\n✅ Policy 업데이트 완료!')
    else:
        print('\n✅ Policy가 이미 올바르게 설정되어 있습니다.')
else:
    print('❌ FALL-002-WITNESSED policy를 찾을 수 없습니다!')

conn.close()



