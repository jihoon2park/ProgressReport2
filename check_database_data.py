#!/usr/bin/env python3
"""
Check database data status
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_data():
    """Check current database data"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("DATABASE DATA STATUS")
        print("=" * 60)
        
        # Check incidents
        cursor.execute("SELECT COUNT(*) FROM cims_incidents")
        incident_count = cursor.fetchone()[0]
        print(f"\n📋 CIMS Incidents: {incident_count} rows")
        
        if incident_count > 0:
            cursor.execute("""
                SELECT incident_type, COUNT(*) 
                FROM cims_incidents 
                GROUP BY incident_type
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """)
            print("   Top incident types:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]}")
            
            cursor.execute("""
                SELECT site, COUNT(*) 
                FROM cims_incidents 
                GROUP BY site
            """)
            print("   By site:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]}")
        
        # Check tasks
        cursor.execute("SELECT COUNT(*) FROM cims_tasks")
        task_count = cursor.fetchone()[0]
        print(f"\n✅ CIMS Tasks: {task_count} rows")
        
        if task_count > 0:
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM cims_tasks 
                GROUP BY status
            """)
            print("   By status:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]}")
        
        # Check policies
        cursor.execute("SELECT COUNT(*) FROM cims_policies WHERE is_active = 1")
        policy_count = cursor.fetchone()[0]
        print(f"\n📜 Active Policies: {policy_count}")
        
        if policy_count > 0:
            cursor.execute("SELECT name, version FROM cims_policies WHERE is_active = 1")
            for row in cursor.fetchall():
                print(f"     - {row[0]} (v{row[1]})")
        
        # Check clients cache
        cursor.execute("SELECT COUNT(*) FROM clients_cache")
        client_count = cursor.fetchone()[0]
        print(f"\n👤 Cached Clients: {client_count} rows")
        
        if client_count > 0:
            cursor.execute("""
                SELECT site, COUNT(*) 
                FROM clients_cache 
                GROUP BY site
            """)
            print("   By site:")
            for row in cursor.fetchall():
                print(f"     - {row[0]}: {row[1]}")
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        user_count = cursor.fetchone()[0]
        print(f"\n👨‍⚕️ Active Users: {user_count}")
        
        # Check last sync
        cursor.execute("SELECT key, value FROM system_settings WHERE key LIKE 'last_%sync%'")
        syncs = cursor.fetchall()
        if syncs:
            print("\n🔄 Last Sync Times:")
            for row in syncs:
                print(f"     - {row[0]}: {row[1]}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        
        # Summary
        if incident_count == 0:
            print("⚠️  WARNING: No incidents in database!")
            print("   → Need to run Force Sync to import data")
            return False
        else:
            print(f"✅ Database has data: {incident_count} incidents, {task_count} tasks")
            return True
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_data()

