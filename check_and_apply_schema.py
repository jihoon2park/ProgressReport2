#!/usr/bin/env python3
"""
데이터베이스 확인 및 작업 관리 스키마 적용
"""

import sqlite3
import os

def check_tables():
    """현재 테이블 목록 확인"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"현재 테이블 목록: {tables}")
    
    # incidents_cache 테이블 확인
    has_incidents = 'incidents_cache' in tables
    print(f"incidents_cache 테이블 존재: {has_incidents}")
    
    conn.close()
    return has_incidents

def create_incidents_cache_table():
    """incidents_cache 테이블 생성"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id VARCHAR(100) NOT NULL,
                client_id INTEGER,
                client_name VARCHAR(200),
                incident_type VARCHAR(100),
                incident_date TIMESTAMP,
                description TEXT,
                severity VARCHAR(20),
                status VARCHAR(50),
                site VARCHAR(100),
                reported_by VARCHAR(100),
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(incident_id, site)
            )
        ''')
        
        conn.commit()
        print("✅ incidents_cache 테이블 생성 완료")
        return True
        
    except Exception as e:
        print(f"❌ incidents_cache 테이블 생성 실패: {e}")
        return False
    finally:
        conn.close()

def apply_task_management_schema():
    """작업 관리 스키마 적용"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 1. scheduled_tasks 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id VARCHAR(100) UNIQUE NOT NULL,
                incident_id VARCHAR(100) NOT NULL,
                policy_id INTEGER NOT NULL,
                client_name VARCHAR(200),
                client_id INTEGER,
                task_type VARCHAR(100) NOT NULL,
                task_description TEXT,
                scheduled_time TIMESTAMP NOT NULL,
                due_time TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'normal',
                assigned_user VARCHAR(100),
                assigned_role VARCHAR(50),
                site VARCHAR(100),
                deep_link VARCHAR(500),
                notification_sent BOOLEAN DEFAULT 0,
                notification_count INTEGER DEFAULT 0,
                last_notification_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                completed_by VARCHAR(100),
                completion_notes TEXT
            )
        ''')
        print("✅ scheduled_tasks 테이블 생성 완료")
        
        # 2. incidents_cache 테이블에 컬럼 추가
        columns_to_add = [
            ('workflow_status', 'VARCHAR(50) DEFAULT "open"'),
            ('total_tasks', 'INTEGER DEFAULT 0'),
            ('completed_tasks', 'INTEGER DEFAULT 0'),
            ('policy_id', 'INTEGER'),
            ('created_by', 'VARCHAR(100)'),
            ('closed_at', 'TIMESTAMP'),
            ('closed_by', 'VARCHAR(100)')
        ]
        
        for column_name, column_def in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE incidents_cache ADD COLUMN {column_name} {column_def}')
                print(f"✅ incidents_cache에 {column_name} 컬럼 추가")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e):
                    print(f"⚠️ {column_name} 컬럼 이미 존재 (건너뜀)")
                else:
                    print(f"❌ {column_name} 컬럼 추가 실패: {e}")
        
        # 3. task_execution_logs 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id VARCHAR(100) NOT NULL,
                action VARCHAR(50) NOT NULL,
                performed_by VARCHAR(100),
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                fcm_message_id VARCHAR(100)
            )
        ''')
        print("✅ task_execution_logs 테이블 생성 완료")
        
        # 4. policy_execution_results 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS policy_execution_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id INTEGER NOT NULL,
                incident_id VARCHAR(100) NOT NULL,
                execution_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_end TIMESTAMP,
                total_tasks_created INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                tasks_cancelled INTEGER DEFAULT 0,
                success_rate DECIMAL(5,2),
                average_completion_time INTEGER,
                notes TEXT
            )
        ''')
        print("✅ policy_execution_results 테이블 생성 완료")
        
        # 5. 인덱스 생성
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(status, scheduled_time)',
            'CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_incident ON scheduled_tasks(incident_id)',
            'CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user ON scheduled_tasks(assigned_user, status)',
            'CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_site ON scheduled_tasks(site, status)',
            'CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_execution_logs(task_id, performed_at)',
            'CREATE INDEX IF NOT EXISTS idx_incidents_workflow ON incidents_cache(workflow_status, site)'
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("✅ 인덱스 생성 완료")
        
        conn.commit()
        print("\n🎉 Task Management 스키마 적용 완료!")
        
        return True
        
    except Exception as e:
        print(f"❌ 작업 관리 스키마 적용 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("🚀 Database Check and Task Schema Application")
    print("=" * 60)
    
    # 1. 현재 테이블 확인
    has_incidents = check_tables()
    
    # 2. incidents_cache 테이블이 없으면 생성
    if not has_incidents:
        print("\n📋 incidents_cache 테이블 생성 중...")
        if not create_incidents_cache_table():
            print("💥 incidents_cache 테이블 생성 실패!")
            return
    
    # 3. 작업 관리 스키마 적용
    print("\n📋 작업 관리 스키마 적용 중...")
    success = apply_task_management_schema()
    
    if success:
        print("\n🎉 모든 스키마 적용 완료!")
        print("다음 단계: Task Manager 테스트 실행")
    else:
        print("\n💥 스키마 적용 실패!")

if __name__ == "__main__":
    main()
