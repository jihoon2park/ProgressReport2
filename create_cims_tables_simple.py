#!/usr/bin/env python3
"""
CIMS 테이블 생성 스크립트 (간단 버전)
필요한 테이블만 직접 생성합니다.
"""

import sqlite3
import os
import sys

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def create_cims_tables():
    """CIMS 테이블들을 생성합니다."""
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 기존 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"기존 CIMS 테이블: {existing_tables if existing_tables else '없음'}")
        
        created_tables = []
        
        # 1. cims_policies 테이블
        if 'cims_policies' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    version VARCHAR(20) NOT NULL,
                    effective_date TIMESTAMP NOT NULL,
                    expiry_date TIMESTAMP,
                    rules_json TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """)
            created_tables.append('cims_policies')
            print("✅ cims_policies 테이블 생성 완료")
        else:
            print("⏭️  cims_policies 테이블이 이미 존재합니다")
        
        # 2. cims_incidents 테이블
        if 'cims_incidents' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id VARCHAR(100) UNIQUE NOT NULL,
                    manad_incident_id VARCHAR(100),
                    resident_id INTEGER NOT NULL,
                    resident_name VARCHAR(200) NOT NULL,
                    incident_type VARCHAR(100) NOT NULL,
                    severity VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'Open',
                    incident_date TIMESTAMP NOT NULL,
                    location VARCHAR(200),
                    description TEXT,
                    initial_actions_taken TEXT,
                    witnesses TEXT,
                    reported_by INTEGER,
                    reported_by_name VARCHAR(200),
                    site VARCHAR(100) NOT NULL,
                    policy_applied INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reported_by) REFERENCES users(id),
                    FOREIGN KEY (policy_applied) REFERENCES cims_policies(id)
                )
            """)
            created_tables.append('cims_incidents')
            print("✅ cims_incidents 테이블 생성 완료")
        else:
            print("⏭️  cims_incidents 테이블이 이미 존재합니다")
        
        # 3. cims_tasks 테이블
        if 'cims_tasks' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id VARCHAR(100) UNIQUE NOT NULL,
                    incident_id INTEGER NOT NULL,
                    policy_id INTEGER NOT NULL,
                    task_name VARCHAR(300) NOT NULL,
                    description TEXT,
                    assigned_role VARCHAR(100) NOT NULL,
                    assigned_user_id INTEGER,
                    due_date TIMESTAMP NOT NULL,
                    priority VARCHAR(20) DEFAULT 'normal',
                    status VARCHAR(50) DEFAULT 'pending',
                    completed_by_user_id INTEGER,
                    completed_at TIMESTAMP,
                    documentation_required BOOLEAN DEFAULT 1,
                    note_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
                    FOREIGN KEY (policy_id) REFERENCES cims_policies(id),
                    FOREIGN KEY (assigned_user_id) REFERENCES users(id),
                    FOREIGN KEY (completed_by_user_id) REFERENCES users(id)
                )
            """)
            created_tables.append('cims_tasks')
            print("✅ cims_tasks 테이블 생성 완료")
        else:
            print("⏭️  cims_tasks 테이블이 이미 존재합니다")
        
        # 4. cims_progress_notes 테이블
        if 'cims_progress_notes' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_progress_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    note_id VARCHAR(100) UNIQUE NOT NULL,
                    incident_id INTEGER NOT NULL,
                    task_id INTEGER,
                    author_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    note_type VARCHAR(100),
                    vitals_data TEXT,
                    assessment_data TEXT,
                    attachments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
                    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
                    FOREIGN KEY (author_id) REFERENCES users(id)
                )
            """)
            created_tables.append('cims_progress_notes')
            print("✅ cims_progress_notes 테이블 생성 완료")
        else:
            print("⏭️  cims_progress_notes 테이블이 이미 존재합니다")
        
        # 5. cims_audit_logs 테이블
        if 'cims_audit_logs' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id VARCHAR(100) UNIQUE NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    target_entity_type VARCHAR(50) NOT NULL,
                    target_entity_id INTEGER NOT NULL,
                    details TEXT,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            created_tables.append('cims_audit_logs')
            print("✅ cims_audit_logs 테이블 생성 완료")
        else:
            print("⏭️  cims_audit_logs 테이블이 이미 존재합니다")
        
        # 6. cims_task_assignments 테이블
        if 'cims_task_assignments' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_task_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    assigned_to_user_id INTEGER NOT NULL,
                    assigned_by_user_id INTEGER NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    notes TEXT,
                    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
                    FOREIGN KEY (assigned_to_user_id) REFERENCES users(id),
                    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id)
                )
            """)
            created_tables.append('cims_task_assignments')
            print("✅ cims_task_assignments 테이블 생성 완료")
        else:
            print("⏭️  cims_task_assignments 테이블이 이미 존재합니다")
        
        # 7. cims_notifications 테이블
        if 'cims_notifications' not in existing_tables:
            cursor.execute("""
                CREATE TABLE cims_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_id VARCHAR(100) UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER,
                    incident_id INTEGER,
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    priority VARCHAR(20) DEFAULT 'normal',
                    is_read BOOLEAN DEFAULT 0,
                    sent_at TIMESTAMP,
                    read_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
                    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id)
                )
            """)
            created_tables.append('cims_notifications')
            print("✅ cims_notifications 테이블 생성 완료")
        else:
            print("⏭️  cims_notifications 테이블이 이미 존재합니다")
        
        # 인덱스 생성
        indexes = [
            ("idx_cims_incidents_type", "cims_incidents", "incident_type"),
            ("idx_cims_incidents_severity", "cims_incidents", "severity"),
            ("idx_cims_incidents_status", "cims_incidents", "status"),
            ("idx_cims_incidents_date", "cims_incidents", "incident_date"),
            ("idx_cims_incidents_site", "cims_incidents", "site"),
            ("idx_cims_incidents_resident", "cims_incidents", "resident_id"),
            ("idx_cims_incidents_manad_id", "cims_incidents", "manad_incident_id"),
            ("idx_cims_tasks_incident", "cims_tasks", "incident_id"),
            ("idx_cims_tasks_status", "cims_tasks", "status"),
            ("idx_cims_tasks_due_date", "cims_tasks", "due_date"),
        ]
        
        for idx_name, table_name, column_name in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({column_name})")
                print(f"✅ 인덱스 생성 완료: {idx_name}")
            except sqlite3.OperationalError as e:
                if 'already exists' not in str(e).lower():
                    print(f"⚠️  인덱스 생성 오류 ({idx_name}): {str(e)[:100]}")
        
        conn.commit()
        
        # 생성된 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        all_cims_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n" + "=" * 60)
        print(f"✅ CIMS 테이블 생성 완료!")
        print(f"생성된 테이블: {len(created_tables)}개")
        for table in created_tables:
            print(f"  - {table}")
        print(f"\n전체 CIMS 테이블: {len(all_cims_tables)}개")
        for table in all_cims_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count}개 레코드")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 CIMS 테이블 생성 시작...")
    success = create_cims_tables()
    if success:
        print("\n✅ 완료!")
        sys.exit(0)
    else:
        print("\n❌ 실패!")
        sys.exit(1)

