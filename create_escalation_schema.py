#!/usr/bin/env python3
"""
고급 에스컬레이션 스키마 생성
15분→30분→1시간→6시간 간격의 다단계 알람 시스템
"""

import sqlite3
import json
from datetime import datetime

def create_escalation_schema():
    """고급 에스컬레이션 스키마 생성"""
    print("고급 에스컬레이션 스키마 생성")
    
    db_path = 'progress_report.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 기존 에스컬레이션 테이블 삭제하고 재생성
        print("\n1. 에스컬레이션 정책 테이블 재설계")
        cursor.execute('DROP TABLE IF EXISTS escalation_policies')
        
        cursor.execute('''
            CREATE TABLE escalation_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name VARCHAR(100) NOT NULL,
                description TEXT,
                event_type VARCHAR(50) NOT NULL,
                priority VARCHAR(20) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✓ escalation_policies 테이블 생성")
        
        # 2. 에스컬레이션 단계 테이블
        cursor.execute('DROP TABLE IF EXISTS escalation_steps')
        
        cursor.execute('''
            CREATE TABLE escalation_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                delay_minutes INTEGER NOT NULL,
                repeat_count INTEGER NOT NULL,
                recipients TEXT NOT NULL,
                message_template VARCHAR(500),
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (policy_id) REFERENCES escalation_policies(id),
                UNIQUE(policy_id, step_number)
            )
        ''')
        print("  ✓ escalation_steps 테이블 생성")
        
        # 3. 알람 실행 로그 테이블
        cursor.execute('DROP TABLE IF EXISTS alarm_execution_logs')
        
        cursor.execute('''
            CREATE TABLE alarm_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alarm_id VARCHAR(100) NOT NULL,
                policy_id INTEGER,
                step_number INTEGER,
                repeat_number INTEGER,
                execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                recipients_sent TEXT,
                message_sent TEXT,
                status VARCHAR(20) DEFAULT 'sent',
                error_message TEXT,
                FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
            )
        ''')
        print("  ✓ alarm_execution_logs 테이블 생성")
        
        # 4. 활성 알람 상태 테이블
        cursor.execute('DROP TABLE IF EXISTS active_alarms')
        
        cursor.execute('''
            CREATE TABLE active_alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alarm_id VARCHAR(100) UNIQUE NOT NULL,
                policy_id INTEGER NOT NULL,
                incident_id VARCHAR(100),
                client_name VARCHAR(200),
                site VARCHAR(100),
                event_type VARCHAR(100),
                risk_rating VARCHAR(20),
                current_step INTEGER DEFAULT 1,
                current_repeat INTEGER DEFAULT 0,
                next_execution_time TIMESTAMP,
                total_sent INTEGER DEFAULT 0,
                is_acknowledged BOOLEAN DEFAULT 0,
                acknowledged_by VARCHAR(100),
                acknowledged_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
            )
        ''')
        print("  ✓ active_alarms 테이블 생성")
        
        # 5. 인덱스 생성
        indexes = [
            ('idx_escalation_steps_policy', 'escalation_steps', '(policy_id, step_number)'),
            ('idx_alarm_logs_alarm_id', 'alarm_execution_logs', '(alarm_id, execution_time)'),
            ('idx_active_alarms_next_exec', 'active_alarms', '(next_execution_time, is_acknowledged)'),
            ('idx_active_alarms_policy', 'active_alarms', '(policy_id, current_step)')
        ]
        
        for index_name, table_name, columns in indexes:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}')
        
        print("  ✓ 인덱스 생성 완료")
        
        conn.commit()
        print("\n✅ 고급 에스컬레이션 스키마 생성 완료!")
        
    except Exception as e:
        print(f"\n❌ 스키마 생성 실패: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_default_policies():
    """기본 에스컬레이션 정책 생성 (15분→30분→1시간→6시간)"""
    print("\n기본 에스컬레이션 정책 생성")
    print("-" * 50)
    
    db_path = 'progress_report.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 요구사항에 맞는 기본 정책들
        policies = [
            {
                'name': '긴급상황 표준 에스컬레이션',
                'description': '15분 4회 → 30분 2회 → 1시간 2회 → 6시간 2회',
                'event_type': 'emergency',
                'priority': 'high',
                'steps': [
                    {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['site_admin', 'doctor'], 'template': '🚨 긴급상황 발생 - 즉시 확인 필요'},
                    {'step': 2, 'delay': 15, 'repeat': 4, 'recipients': ['admin', 'site_admin', 'doctor'], 'template': '🚨 긴급상황 미처리 - 15분 간격 알림'},
                    {'step': 3, 'delay': 30, 'repeat': 2, 'recipients': ['admin', 'site_admin', 'doctor', 'manager'], 'template': '🚨 긴급상황 지속 - 30분 간격 알림'},
                    {'step': 4, 'delay': 60, 'repeat': 2, 'recipients': ['admin', 'manager', 'director'], 'template': '🚨 긴급상황 장기화 - 1시간 간격 알림'},
                    {'step': 5, 'delay': 360, 'repeat': 2, 'recipients': ['admin', 'manager', 'director'], 'template': '🚨 긴급상황 심각 - 6시간 간격 알림'}
                ]
            },
            {
                'name': '일반상황 표준 에스컬레이션',
                'description': '일반 상황에 대한 단계별 알림',
                'event_type': 'normal',
                'priority': 'medium',
                'steps': [
                    {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['site_admin'], 'template': '⚠️ 상황 발생 - 확인 요청'},
                    {'step': 2, 'delay': 30, 'repeat': 2, 'recipients': ['admin', 'site_admin'], 'template': '⚠️ 상황 미처리 - 30분 간격 알림'},
                    {'step': 3, 'delay': 120, 'repeat': 1, 'recipients': ['admin'], 'template': '⚠️ 상황 장기화 - 최종 확인 요청'}
                ]
            },
            {
                'name': '복약 알림 에스컬레이션',
                'description': '복약 시간 알림 및 미복용 시 에스컬레이션',
                'event_type': 'medication',
                'priority': 'normal',
                'steps': [
                    {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['doctor', 'site_admin'], 'template': '💊 복약 시간 알림'},
                    {'step': 2, 'delay': 15, 'repeat': 4, 'recipients': ['doctor', 'site_admin'], 'template': '💊 복약 미복용 - 15분 간격 알림'},
                    {'step': 3, 'delay': 30, 'repeat': 2, 'recipients': ['admin', 'doctor'], 'template': '💊 복약 미복용 지속 - 30분 간격 알림'},
                    {'step': 4, 'delay': 60, 'repeat': 2, 'recipients': ['admin', 'doctor'], 'template': '💊 복약 미복용 심각 - 1시간 간격 알림'}
                ]
            }
        ]
        
        # 정책 및 단계 삽입
        for policy_data in policies:
            # 정책 기본 정보 삽입
            cursor.execute('''
                INSERT INTO escalation_policies 
                (policy_name, description, event_type, priority, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                policy_data['name'],
                policy_data['description'],
                policy_data['event_type'],
                policy_data['priority'],
                1  # admin 사용자 ID
            ))
            
            policy_id = cursor.lastrowid
            
            # 에스컬레이션 단계 삽입
            for step_data in policy_data['steps']:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    policy_id,
                    step_data['step'],
                    step_data['delay'],
                    step_data['repeat'],
                    json.dumps(step_data['recipients']),
                    step_data['template']
                ))
            
            print(f"  ✓ {policy_data['name']}: {len(policy_data['steps'])}단계")
        
        conn.commit()
        print(f"\n✅ 기본 정책 {len(policies)}개 생성 완료")
        
        # 검증
        print("\n검증 결과:")
        cursor.execute('''
            SELECT ep.policy_name, ep.event_type, ep.priority, COUNT(es.id) as steps
            FROM escalation_policies ep
            LEFT JOIN escalation_steps es ON ep.id = es.policy_id
            WHERE ep.is_active = 1
            GROUP BY ep.id
            ORDER BY ep.priority DESC
        ''')
        
        for row in cursor.fetchall():
            policy_name, event_type, priority, steps = row
            print(f"  📋 {policy_name}: {steps}단계 ({event_type}, {priority})")
        
        # 상세 단계 확인 (긴급상황 정책)
        print("\n긴급상황 에스컬레이션 상세:")
        cursor.execute('''
            SELECT es.step_number, es.delay_minutes, es.repeat_count, es.recipients, es.message_template
            FROM escalation_policies ep
            JOIN escalation_steps es ON ep.id = es.policy_id
            WHERE ep.policy_name = '긴급상황 표준 에스컬레이션'
            ORDER BY es.step_number
        ''')
        
        for row in cursor.fetchall():
            step_num, delay, repeat, recipients, template = row
            recipients_list = json.loads(recipients)
            delay_text = f"{delay}분 후" if delay > 0 else "즉시"
            print(f"  단계 {step_num}: {delay_text} {repeat}회 반복 → {', '.join(recipients_list)}")
            print(f"           메시지: {template}")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ 정책 생성 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_escalation_schema()
    create_default_policies()
