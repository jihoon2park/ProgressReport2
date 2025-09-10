#!/usr/bin/env python3
"""
누락된 테이블들 생성 스크립트
"""

import sqlite3
import json
from datetime import datetime

def create_missing_tables():
    """누락된 테이블들 생성"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        print("🗄️ 누락된 테이블 생성 중...")
        
        # 1. escalation_policies 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escalation_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name VARCHAR(200) NOT NULL,
                description TEXT,
                event_type VARCHAR(100),
                priority VARCHAR(20) DEFAULT 'normal',
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ escalation_policies 테이블 생성")
        
        # 2. escalation_steps 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escalation_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                step_number INTEGER NOT NULL,
                delay_minutes INTEGER DEFAULT 0,
                repeat_count INTEGER DEFAULT 1,
                recipients TEXT, -- JSON 배열
                message_template TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
            )
        ''')
        print("✅ escalation_steps 테이블 생성")
        
        # 3. alarm_templates 테이블 (이미 schema에 있지만 확인)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarm_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                title_template VARCHAR(500),
                body_template TEXT,
                priority VARCHAR(20) DEFAULT 'normal',
                category VARCHAR(100),
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ alarm_templates 테이블 생성")
        
        # 4. alarm_recipients 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarm_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(20),
                role VARCHAR(100),
                team VARCHAR(100),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ alarm_recipients 테이블 생성")
        
        # 5. 기본 데이터 삽입
        print("\n📋 기본 데이터 삽입 중...")
        
        # 기본 에스컬레이션 정책
        cursor.execute('SELECT COUNT(*) FROM escalation_policies')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO escalation_policies 
                (policy_name, description, event_type, priority, created_by)
                VALUES 
                ('Emergency Standard Escalation', '15min 4x → 30min 2x → 1hr 2x → 6hr 2x', 'emergency', 'high', 1),
                ('Normal Situation Escalation', 'Standard escalation for normal situations', 'normal', 'medium', 1),
                ('Medication Alert Escalation', 'Medication reminder escalation policy', 'medication', 'normal', 1)
            ''')
            print("✅ 기본 에스컬레이션 정책 생성")
            
            # 첫 번째 정책의 단계들
            policy_id = 1
            steps = [
                (1, 0, 1, '["RN", "doctor"]', '🚨 Emergency situation - immediate attention required'),
                (2, 15, 4, '["admin", "site_admin", "doctor"]', '🚨 Emergency unhandled - 15min interval alarm'),
                (3, 30, 2, '["admin", "site_admin", "doctor", "manager"]', '🚨 Emergency ongoing - 30min interval alarm'),
                (4, 60, 2, '["admin", "manager", "director"]', '🚨 Emergency prolonged - 1hr interval alarm'),
                (5, 360, 2, '["admin", "manager", "director"]', '🚨 Emergency critical - 6hr interval alarm')
            ]
            
            for step_num, delay, repeat, recipients, message in steps:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (policy_id, step_num, delay, repeat, recipients, message))
            
            print("✅ 기본 에스컬레이션 단계 생성")
        
        # 기본 알람 템플릿
        cursor.execute('SELECT COUNT(*) FROM alarm_templates')
        if cursor.fetchone()[0] == 0:
            templates = [
                ('EMERGENCY_ALERT', 'Emergency Alert', 'Critical situation alert', 
                 '🚨 Emergency Alert: {client_name}', 
                 'Emergency situation detected for {client_name} at {site}. Immediate attention required.', 
                 'high', 'emergency'),
                ('MEDICATION_REMINDER', 'Medication Reminder', 'Medication time reminder',
                 '💊 Medication Time: {client_name}',
                 'Medication administration required for {client_name}. Please check medication schedule.',
                 'normal', 'medication'),
                ('ROUTINE_CHECK', 'Routine Check', 'Standard routine check alert',
                 '📋 Routine Check: {client_name}',
                 'Routine care check required for {client_name}.',
                 'normal', 'routine')
            ]
            
            for template_id, name, desc, title, body, priority, category in templates:
                cursor.execute('''
                    INSERT INTO alarm_templates 
                    (template_id, name, description, title_template, body_template, priority, category, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (template_id, name, desc, title, body, priority, category))
            
            print("✅ 기본 알람 템플릿 생성")
        
        # 기본 알람 수신자
        cursor.execute('SELECT COUNT(*) FROM alarm_recipients')
        if cursor.fetchone()[0] == 0:
            recipients = [
                (1, 'System Admin', 'admin@company.com', '+61-400-000-001', 'admin', 'IT'),
                (2, 'Site Manager', 'manager@company.com', '+61-400-000-002', 'site_admin', 'Management'),
                (3, 'Head Nurse', 'nurse@company.com', '+61-400-000-003', 'doctor', 'Medical')
            ]
            
            for user_id, name, email, phone, role, team in recipients:
                cursor.execute('''
                    INSERT INTO alarm_recipients 
                    (user_id, name, email, phone, role, team)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, name, email, phone, role, team))
            
            print("✅ 기본 알람 수신자 생성")
        
        conn.commit()
        print("\n🎉 모든 누락된 테이블 생성 완료!")
        
        # 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📊 총 {len(all_tables)}개 테이블 존재:")
        for table in all_tables:
            if not table.startswith('sqlite_'):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count}개 레코드")
        
        return True
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_missing_tables()
    if success:
        print("\n✅ 성공! 이제 앱을 다시 시작할 수 있습니다.")
    else:
        print("\n❌ 실패!")
        exit(1)
