#!/usr/bin/env python3
"""
CIMS database status check script
Check cims_incidents table status on production server.
"""

import sqlite3
import os
from datetime import datetime, timedelta

def check_cims_data():
    """Check CIMS database status"""
    
    # Database path
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
        if not cursor.fetchone():
            print("❌ cims_incidents table does not exist.")
            return
        
        print("✅ cims_incidents table exists")
        
        # 2. Total incident count
        cursor.execute("SELECT COUNT(*) as total FROM cims_incidents")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total incidents: {total}")
        
        if total == 0:
            print("⚠️  Table is empty. Synchronization is required.")
            print("   Solution: Call /api/cims/force-sync API or restart the server.")
            return
        
        # 3. Statistics by date
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN incident_date IS NOT NULL AND incident_date != '' THEN 1 END) as with_date,
                COUNT(CASE WHEN status IS NOT NULL AND status != '' THEN 1 END) as with_status
            FROM cims_incidents
        """)
        stats = cursor.fetchone()
        print(f"   - Incidents with date: {stats[1]}")
        print(f"   - Incidents with status: {stats[2]}")
        
        # 4. Status distribution
        cursor.execute("""
            SELECT status, COUNT(*) as cnt
            FROM cims_incidents
            WHERE status IS NOT NULL AND status != ''
            GROUP BY status
            ORDER BY cnt DESC
        """)
        status_dist = cursor.fetchall()
        print(f"\n📈 Status distribution:")
        for row in status_dist:
            print(f"   - {row[0]}: {row[1]}")
        
        # 5. Incidents in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            AND incident_date != ''
            AND incident_date >= ?
        """, [week_ago])
        week_count = cursor.fetchone()[0]
        print(f"\n📅 Incidents in last 7 days: {week_count}")
        
        # 6. Date samples
        cursor.execute("""
            SELECT incident_date, status, incident_type
            FROM cims_incidents
            WHERE incident_date IS NOT NULL 
            ORDER BY incident_date DESC
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print(f"\n📋 Recent incident samples (5):")
        for row in samples:
            print(f"   - {row[0]} | {row[1]} | {row[2]}")
        
        # 7. Check synchronization status
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync = cursor.fetchone()
        if last_sync:
            print(f"\n🔄 Last sync time: {last_sync[0]}")
        else:
            print(f"\n⚠️  No sync record found.")
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    check_cims_data()

