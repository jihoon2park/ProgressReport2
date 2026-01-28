#!/usr/bin/env python3
"""
Production and development environment comparison script
Compare database status between two environments.
"""

import sqlite3
import os
from datetime import datetime

def compare_environments():
    """Compare production and development environments"""
    
    print("=" * 60)
    print("Production vs Development Environment Comparison")
    print("=" * 60)
    
    # Production path (IIS)
    prod_path = r'C:\inetpub\wwwroot\ProgressNoteWeb\ProgressReport2\progress_report.db'
    
    # Development path (current directory)
    dev_path = 'progress_report.db'
    
    environments = {
        'Production': prod_path,
        'Development': dev_path
    }
    
    results = {}
    
    for env_name, db_path in environments.items():
        print(f"\n{'='*60}")
        print(f"{env_name} Environment")
        print(f"{'='*60}")
        
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            results[env_name] = None
            continue
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Total incident count
            cursor.execute("SELECT COUNT(*) as total FROM cims_incidents")
            total = cursor.fetchone()[0]
            print(f"📊 Total incidents: {total}")
            
            # 2. Status distribution
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM cims_incidents
                WHERE status IS NOT NULL AND status != ''
                GROUP BY status
                ORDER BY cnt DESC
            """)
            status_dist = cursor.fetchall()
            print(f"📈 Status distribution:")
            status_dict = {}
            for row in status_dist:
                print(f"   - {row[0]}: {row[1]}")
                status_dict[row[0]] = row[1]
            
            # 3. Incidents in last 7 days
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM cims_incidents
                WHERE incident_date IS NOT NULL 
                AND incident_date != ''
                AND incident_date >= ?
            """, [week_ago])
            week_count = cursor.fetchone()[0]
            print(f"📅 Incidents in last 7 days: {week_count}")
            
            # 4. Last sync time
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'last_incident_sync_time'
            """)
            last_sync = cursor.fetchone()
            if last_sync:
                sync_time = datetime.fromisoformat(last_sync[0])
                days_ago = (datetime.now() - sync_time).days
                print(f"🔄 Last sync: {last_sync[0]} ({days_ago} days ago)")
            else:
                print(f"⚠️  No sync record found.")
            
            # 5. Latest incident date
            cursor.execute("""
                SELECT MAX(incident_date) as latest_date
                FROM cims_incidents
                WHERE incident_date IS NOT NULL AND incident_date != ''
            """)
            latest = cursor.fetchone()[0]
            if latest:
                print(f"📅 Latest incident date: {latest}")
            
            results[env_name] = {
                'total': total,
                'status_dist': status_dict,
                'week_count': week_count,
                'last_sync': last_sync[0] if last_sync else None,
                'latest_date': latest
            }
            
        except Exception as e:
            print(f"❌ Error occurred: {e}")
            results[env_name] = None
        finally:
            conn.close()
    
    # Comparison results
    print(f"\n{'='*60}")
    print("Comparison Results")
    print(f"{'='*60}")
    
    if results.get('Production') and results.get('Development'):
        prod = results['Production']
        dev = results['Development']
        
        print(f"\nTotal incidents:")
        print(f"  Production: {prod['total']}")
        print(f"  Development: {dev['total']}")
        print(f"  Difference: {abs(prod['total'] - dev['total'])}")
        
        print(f"\nIncidents in last 7 days:")
        print(f"  Production: {prod['week_count']}")
        print(f"  Development: {dev['week_count']}")
        print(f"  Difference: {abs(prod['week_count'] - dev['week_count'])}")
        
        if prod['last_sync'] and dev['last_sync']:
            prod_sync = datetime.fromisoformat(prod['last_sync'])
            dev_sync = datetime.fromisoformat(dev['last_sync'])
            print(f"\nLast sync time:")
            print(f"  Production: {prod['last_sync']}")
            print(f"  Development: {dev['last_sync']}")
            print(f"  Difference: {abs((prod_sync - dev_sync).days)} days")
        
        print(f"\n⚠️  The two environments are using different data!")
        print(f"   Solutions:")
        print(f"   1. Run Force Sync on production")
        print(f"   2. Verify both environments use the same MANAD DB source")
        print(f"   3. Check if sync schedule is working properly")

if __name__ == '__main__':
    from datetime import timedelta
    compare_environments()

