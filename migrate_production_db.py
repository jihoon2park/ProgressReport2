#!/usr/bin/env python3
"""
CIMS Database Migration Script for Production Server

이 스크립트는 프로덕션 서버의 DB를 최신 스키마로 업데이트합니다.
- 누락된 테이블 생성
- 누락된 컬럼 추가
- 인덱스 생성
- 데이터 무결성 체크

실행 방법:
    python migrate_production_db.py

주의:
    - 실행 전 DB 백업 권장
    - 트랜잭션으로 실행되어 실패 시 롤백
"""

import sqlite3
import os
from datetime import datetime
import json

DB_PATH = 'progress_report.db'

def backup_database():
    """데이터베이스 백업"""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return False

def get_table_columns(cursor, table_name):
    """테이블의 모든 컬럼 목록 조회"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {col[1]: col for col in cursor.fetchall()}
    except:
        return {}

def table_exists(cursor, table_name):
    """테이블 존재 여부 확인"""
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def create_missing_tables(cursor):
    """누락된 테이블 생성"""
    print("\n" + "="*80)
    print("Creating Missing Tables")
    print("="*80)
    
    tables_created = 0
    
    # Define all required tables
    table_definitions = {
        'cims_incidents': """
            CREATE TABLE cims_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id VARCHAR(100) UNIQUE NOT NULL,
                manad_incident_id VARCHAR(100),
                resident_id INTEGER NOT NULL,
                resident_name VARCHAR(200) NOT NULL,
                incident_type VARCHAR(100) NOT NULL,
                severity VARCHAR(50),
                status VARCHAR(50),
                incident_date TIMESTAMP NOT NULL,
                location VARCHAR(200),
                description TEXT,
                initial_actions_taken TEXT,
                witnesses TEXT,
                reported_by INTEGER,
                reported_by_name VARCHAR(200),
                site VARCHAR(100) NOT NULL,
                policy_applied INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """,
        'cims_tasks': """
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
        """,
        'cims_policies': """
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
        """,
        'cims_progress_notes': """
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
        """,
        'clients_cache': """
            CREATE TABLE clients_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                client_name VARCHAR(200) NOT NULL,
                preferred_name VARCHAR(100),
                title VARCHAR(10),
                first_name VARCHAR(100),
                middle_name VARCHAR(100),
                surname VARCHAR(100),
                gender VARCHAR(10),
                birth_date DATE,
                admission_date DATE,
                room_name VARCHAR(50),
                room_number VARCHAR(10),
                wing_name VARCHAR(100),
                location_id INTEGER,
                location_name VARCHAR(200),
                main_client_service_id INTEGER,
                original_person_id INTEGER,
                client_record_id INTEGER,
                site VARCHAR(100) NOT NULL,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """,
        'system_settings': """
            CREATE TABLE system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """,
        'sync_status': """
            CREATE TABLE sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type VARCHAR(50) NOT NULL,
                site VARCHAR(100),
                last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                records_synced INTEGER DEFAULT 0
            )
        """
    }
    
    for table_name, create_sql in table_definitions.items():
        if not table_exists(cursor, table_name):
            print(f"  Creating table: {table_name}...")
            cursor.execute(create_sql)
            tables_created += 1
            print(f"  ✅ Created: {table_name}")
        else:
            print(f"  ✓ Exists: {table_name}")
    
    print(f"\nTables created: {tables_created}")
    return tables_created

def add_missing_columns(cursor):
    """누락된 컬럼 추가"""
    print("\n" + "="*80)
    print("Adding Missing Columns")
    print("="*80)
    
    columns_added = 0
    
    # Define required columns per table
    required_columns = {
        'cims_incidents': [
            ('manad_incident_id', 'VARCHAR(100)'),
            ('severity', 'VARCHAR(50)'),
            ('status', 'VARCHAR(50)'),
            ('witnesses', 'TEXT'),
            ('reported_by_name', 'VARCHAR(200)'),
            ('policy_applied', 'INTEGER'),
            ('created_at', 'TIMESTAMP'),
            ('updated_at', 'TIMESTAMP'),
        ],
        'cims_tasks': [
            ('policy_id', 'INTEGER NOT NULL DEFAULT 1'),
            ('description', 'TEXT'),
            ('assigned_role', 'VARCHAR(100) NOT NULL DEFAULT "Registered Nurse"'),
            ('assigned_user_id', 'INTEGER'),
            ('completed_by_user_id', 'INTEGER'),
            ('completed_at', 'TIMESTAMP'),
            ('documentation_required', 'BOOLEAN DEFAULT 1'),
            ('note_type', 'VARCHAR(100)'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'cims_policies': [
            ('policy_id', 'VARCHAR(50) UNIQUE'),
            ('name', 'VARCHAR(200)'),
            ('description', 'TEXT'),
            ('version', 'VARCHAR(20)'),
            ('effective_date', 'TIMESTAMP'),
            ('expiry_date', 'TIMESTAMP'),
            ('created_by', 'INTEGER'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ],
        'clients_cache': [
            ('client_record_id', 'INTEGER'),
            ('site', 'VARCHAR(100)'),
            ('last_synced', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('is_active', 'BOOLEAN DEFAULT 1'),
        ],
        'users': [
            ('position', 'VARCHAR(100)'),
            ('location', 'TEXT'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ]
    }
    
    for table_name, columns in required_columns.items():
        if not table_exists(cursor, table_name):
            print(f"  ⚠️ Table {table_name} does not exist, skipping column check")
            continue
        
        existing_columns = get_table_columns(cursor, table_name)
        
        for col_name, col_type in columns:
            if col_name not in existing_columns:
                print(f"  Adding column: {table_name}.{col_name}...")
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    columns_added += 1
                    print(f"  ✅ Added: {table_name}.{col_name}")
                except Exception as e:
                    print(f"  ❌ Failed to add {table_name}.{col_name}: {str(e)}")
            else:
                print(f"  ✓ Exists: {table_name}.{col_name}")
    
    print(f"\nColumns added: {columns_added}")
    return columns_added

def create_indexes(cursor):
    """인덱스 생성"""
    print("\n" + "="*80)
    print("Creating Indexes")
    print("="*80)
    
    indexes_created = 0
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_incidents_manad_id ON cims_incidents(manad_incident_id)",
        "CREATE INDEX IF NOT EXISTS idx_incidents_site_status ON cims_incidents(site, status, incident_date)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_incident ON cims_tasks(incident_id)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON cims_tasks(due_date)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON cims_tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_clients_site ON clients_cache(site)",
        "CREATE INDEX IF NOT EXISTS idx_clients_client_record_id ON clients_cache(client_record_id)",
    ]
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            index_name = index_sql.split('idx_')[1].split(' ON')[0] if 'idx_' in index_sql else 'unknown'
            print(f"  ✅ Created index: idx_{index_name}")
            indexes_created += 1
        except Exception as e:
            if 'already exists' not in str(e):
                print(f"  ❌ Failed: {str(e)}")
    
    print(f"\nIndexes created: {indexes_created}")
    return indexes_created

def verify_data_integrity(cursor):
    """데이터 무결성 검증"""
    print("\n" + "="*80)
    print("Data Integrity Check")
    print("="*80)
    
    issues_found = 0
    
    # Check 1: Fall incidents without tasks
    cursor.execute("""
        SELECT COUNT(*) FROM cims_incidents i
        WHERE i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND NOT EXISTS (SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id)
    """)
    missing_tasks = cursor.fetchone()[0]
    
    if missing_tasks > 0:
        print(f"  ⚠️ {missing_tasks} Fall incidents without tasks")
        print(f"     → Run Force Sync to generate tasks")
        issues_found += 1
    else:
        print(f"  ✅ All Fall incidents have tasks")
    
    # Check 2: Active Fall policy
    cursor.execute("""
        SELECT COUNT(*) FROM cims_policies 
        WHERE is_active = 1
    """)
    active_policies = cursor.fetchone()[0]
    
    if active_policies == 0:
        print(f"  ⚠️ No active policies found")
        print(f"     → Create Fall Management Policy in Policy Admin")
        issues_found += 1
    else:
        print(f"  ✅ {active_policies} active policy(ies) found")
    
    # Check 3: Orphaned tasks (incident deleted but tasks remain)
    cursor.execute("""
        SELECT COUNT(*) FROM cims_tasks t
        WHERE NOT EXISTS (SELECT 1 FROM cims_incidents i WHERE i.id = t.incident_id)
    """)
    orphaned_tasks = cursor.fetchone()[0]
    
    if orphaned_tasks > 0:
        print(f"  ⚠️ {orphaned_tasks} orphaned tasks (incident deleted)")
        issues_found += 1
    else:
        print(f"  ✅ No orphaned tasks")
    
    # Check 4: System settings
    cursor.execute("SELECT COUNT(*) FROM system_settings")
    settings_count = cursor.fetchone()[0]
    
    if settings_count == 0:
        print(f"  ⚠️ No system settings found")
        print(f"     → System will initialize on first sync")
    else:
        print(f"  ✅ {settings_count} system settings configured")
    
    print(f"\nIssues found: {issues_found}")
    return issues_found

def main():
    """메인 마이그레이션 실행"""
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "CIMS Database Migration Script" + " "*28 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        print(f"   Please ensure you're in the correct directory.")
        return
    
    # 1. Backup
    print("Step 1: Backup")
    if not backup_database():
        response = input("\n⚠️ Backup failed. Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return
    
    # 2. Connect to database
    print("\nStep 2: Connect to Database")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"✅ Connected to: {DB_PATH}")
    
    try:
        # 3. Create missing tables
        print("\nStep 3: Create Missing Tables")
        tables_created = create_missing_tables(cursor)
        
        # 4. Add missing columns
        print("\nStep 4: Add Missing Columns")
        columns_added = add_missing_columns(cursor)
        
        # 5. Create indexes
        print("\nStep 5: Create Indexes")
        indexes_created = create_indexes(cursor)
        
        # 6. Verify data integrity
        print("\nStep 6: Verify Data Integrity")
        issues_found = verify_data_integrity(cursor)
        
        # 7. Commit changes
        conn.commit()
        print("\n" + "="*80)
        print("Migration Summary")
        print("="*80)
        print(f"  ✅ Tables created: {tables_created}")
        print(f"  ✅ Columns added: {columns_added}")
        print(f"  ✅ Indexes created: {indexes_created}")
        print(f"  {'⚠️' if issues_found > 0 else '✅'} Data issues: {issues_found}")
        print("\n✅ Migration completed successfully!")
        
        if issues_found > 0:
            print("\n⚠️ Post-migration actions required:")
            print("  1. Go to Integrated Dashboard → System Settings")
            print("  2. Click 'Force Synchronization'")
            print("  3. This will generate missing tasks and sync data")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        print("   All changes have been rolled back.")
        raise
    
    finally:
        conn.close()
        print("\nDatabase connection closed.")

if __name__ == '__main__':
    main()

