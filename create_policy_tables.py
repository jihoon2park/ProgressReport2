#!/usr/bin/env python3
"""
Policy 관련 테이블 생성 및 데이터 마이그레이션
"""

import sqlite3
import json
import os
from datetime import datetime

def create_policy_tables():
    """Policy 관련 테이블 생성"""
    print("Policy 관련 테이블 생성 및 데이터 마이그레이션")
    
    db_path = 'progress_report.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 알람 템플릿 테이블 생성
        print("\n1. 알람 템플릿 테이블 생성")
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
        print("  ✓ alarm_templates 테이블 생성 완료")
        
        # 2. 알람 수신자 테이블 생성
        print("\n2. 알람 수신자 테이블 생성")
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
        print("  ✓ alarm_recipients 테이블 생성 완료")
        
        # 3. 에스컬레이션 정책 테이블 생성
        print("\n3. 에스컬레이션 정책 테이블 생성")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escalation_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_name VARCHAR(100) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                priority VARCHAR(20) NOT NULL,
                level_1_delay_minutes INTEGER DEFAULT 0,
                level_1_recipients TEXT,
                level_2_delay_minutes INTEGER DEFAULT 15,
                level_2_recipients TEXT,
                level_3_delay_minutes INTEGER DEFAULT 30,
                level_3_recipients TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("  ✓ escalation_policies 테이블 생성 완료")
        
        # 4. 실제 알람 템플릿 데이터 추가
        print("\n4. 실제 알람 템플릿 데이터 추가")
        
        real_templates = [
            ('emergency_high', '긴급 상황 알림 (High)', '높은 위험도의 긴급 상황 발생 시 사용', 
             '🚨 긴급상황 발생', '{client_name}님에게 {event_type} 상황이 발생했습니다. 즉시 확인이 필요합니다. (위치: {site})', 
             'high', 'emergency'),
            ('emergency_medium', '주의 상황 알림 (Medium)', '중간 위험도의 상황 발생 시 사용', 
             '⚠️ 주의상황 발생', '{client_name}님에게 {event_type} 상황이 발생했습니다. 확인 부탁드립니다. (위치: {site})', 
             'medium', 'warning'),
            ('daily_report', '일일 보고서', '일일 Progress Note 요약 보고서', 
             '📊 일일 보고서', '{site}의 {date} 일일 보고서가 준비되었습니다. Progress Note {count}건이 작성되었습니다.', 
             'normal', 'report'),
            ('medication_reminder', '복약 알림', '복약 시간 알림 템플릿', 
             '💊 복약 알림', '{client_name}님의 복약 시간입니다. {medication_name} 복용을 확인해주세요.', 
             'normal', 'medication'),
            ('shift_handover', '교대 인수인계', '교대 시 인수인계 알림 템플릿', 
             '👥 교대 인수인계', '{site}의 {shift_time} 교대 인수인계가 시작됩니다. 특이사항 {special_notes}건이 있습니다.', 
             'normal', 'handover')
        ]
        
        for template in real_templates:
            cursor.execute('''
                INSERT OR REPLACE INTO alarm_templates 
                (template_id, name, description, title_template, body_template, 
                 priority, category, is_active, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (*template, True, 1))
        
        print(f"  ✓ 실제 알람 템플릿 {len(real_templates)}개 추가")
        
        # 5. 실제 수신자 데이터 생성 (기존 사용자 기반)
        print("\n5. 실제 수신자 데이터 생성")
        
        cursor.execute('''
            SELECT id, username, first_name, last_name, role, position
            FROM users 
            WHERE is_active = 1
        ''')
        
        users = cursor.fetchall()
        
        team_mapping = {
            'admin': 'IT Support',
            'site_admin': 'Site Management', 
            'doctor': 'Medical Team',
            'physiotherapist': 'Therapy Team'
        }
        
        for user in users:
            email = f"{user[1]}@progressreport.com"
            phone = f"+61-{user[0]:03d}-{user[0]*111:03d}-{user[0]*222:04d}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO alarm_recipients 
                (user_id, name, email, phone, role, team, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user[0],  # id
                f"{user[2]} {user[3]}",  # first_name + last_name
                email,
                phone,
                user[5],  # position
                team_mapping.get(user[4], 'General'),  # role -> team
                True
            ))
        
        print(f"  ✓ 실제 수신자 {len(users)}명 생성")
        
        # 6. 에스컬레이션 정책 추가
        print("\n6. 에스컬레이션 정책 추가")
        
        policies = [
            ('긴급상황 에스컬레이션', 'emergency', 'high', 
             0, '["site_admin", "doctor"]', 
             5, '["admin", "site_admin", "doctor"]', 
             15, '["admin", "site_admin", "doctor"]'),
            ('일반상황 에스컬레이션', 'normal', 'medium',
             0, '["site_admin"]',
             30, '["admin", "site_admin"]',
             60, '["admin"]'),
            ('복약 알림 에스컬레이션', 'medication', 'normal',
             0, '["doctor", "site_admin"]',
             60, '["admin", "doctor"]',
             180, '["admin"]')
        ]
        
        for policy in policies:
            cursor.execute('''
                INSERT OR REPLACE INTO escalation_policies 
                (policy_name, event_type, priority, level_1_delay_minutes, level_1_recipients,
                 level_2_delay_minutes, level_2_recipients, level_3_delay_minutes, level_3_recipients)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', policy)
        
        print(f"  ✓ 에스컬레이션 정책 {len(policies)}개 추가")
        
        # 7. 최종 결과 확인
        print("\n7. 최종 결과 확인")
        print("-" * 50)
        
        # 모든 테이블 상태 확인
        tables = [
            ('users', '사용자'),
            ('clients_cache', '클라이언트'),
            ('care_areas', '케어 영역'),
            ('event_types', '이벤트 타입'),
            ('fcm_tokens', 'FCM 토큰'),
            ('alarm_templates', '알람 템플릿'),
            ('alarm_recipients', '수신자'),
            ('escalation_policies', '에스컬레이션 정책'),
            ('access_logs', '접근 로그'),
            ('progress_note_logs', 'Progress Note 로그')
        ]
        
        total_records = 0
        for table, description in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            total_records += count
            print(f"  📊 {description}: {count:,}개")
        
        print(f"\n📈 전체 레코드: {total_records:,}개")
        
        # 데이터베이스 크기
        db_size = os.path.getsize(db_path) / 1024 / 1024
        print(f"💾 데이터베이스 크기: {db_size:.2f} MB")
        
        conn.commit()
        print("\n🎉 완전한 SQLite 기반 시스템 구축 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    create_policy_tables()
