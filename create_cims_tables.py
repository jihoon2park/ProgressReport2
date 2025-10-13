#!/usr/bin/env python3
"""
Simple CIMS table creation script
"""

import sqlite3
import os

def create_cims_tables():
    """Create basic CIMS tables"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        print("Creating CIMS tables...")
        
        # 1. Policies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cims_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                version VARCHAR(20) NOT NULL,
                effective_date TIMESTAMP NOT NULL,
                rules_json TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("OK cims_policies table created")
        
        # 2. Incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cims_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id VARCHAR(100) UNIQUE NOT NULL,
                resident_id INTEGER NOT NULL,
                resident_name VARCHAR(200) NOT NULL,
                incident_type VARCHAR(100) NOT NULL,
                severity VARCHAR(50) NOT NULL,
                status VARCHAR(50) DEFAULT 'Open',
                incident_date TIMESTAMP NOT NULL,
                location VARCHAR(200),
                description TEXT,
                reported_by INTEGER NOT NULL,
                site VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("OK cims_incidents table created")
        
        # 3. Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cims_tasks (
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("OK cims_tasks table created")
        
        # 4. Progress Notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cims_progress_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id VARCHAR(100) UNIQUE NOT NULL,
                incident_id INTEGER NOT NULL,
                task_id INTEGER,
                author_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                note_type VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("OK cims_progress_notes table created")
        
        # 5. Audit Logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cims_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_id VARCHAR(100) UNIQUE NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                action VARCHAR(100) NOT NULL,
                target_entity_type VARCHAR(50) NOT NULL,
                target_entity_id INTEGER NOT NULL,
                details TEXT
            )
        ''')
        print("OK cims_audit_logs table created")
        
        # Insert sample policy
        cursor.execute('''
            INSERT OR IGNORE INTO cims_policies (
                policy_id, name, description, version, effective_date, rules_json
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            'FALL-001',
            'Fall Management Policy V3',
            'Basic fall management protocol',
            '3.0',
            '2025-01-01 00:00:00',
            '{"policy_name": "Fall Management Policy V3", "rule_sets": [{"name": "Basic Fall Protocol", "trigger_condition": {"incident_field": "type", "operator": "EQUALS", "value": "Fall"}, "tasks_to_generate": [{"task_name": "Initial Assessment", "assigned_role": "Registered Nurse", "due_offset": 30, "due_unit": "minutes", "documentation_required": true}]}]}'
        ))
        print("OK Sample policy inserted")
        
        conn.commit()
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims_%'")
        tables = cursor.fetchall()
        print(f"\nCreated CIMS tables: {[t[0] for t in tables]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating CIMS tables: {e}")
        return False

if __name__ == "__main__":
    print("CIMS Table Creation Script")
    print("=" * 40)
    
    if create_cims_tables():
        print("\nSUCCESS: CIMS tables created successfully!")
    else:
        print("\nERROR: Failed to create CIMS tables")
