#!/usr/bin/env python3
"""Check if incident 4938 exists"""
import sqlite3

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT incident_id, resident_name, incident_type, incident_date, status, manad_incident_id, description
    FROM cims_incidents 
    WHERE manad_incident_id = '4938'
""")

result = cursor.fetchone()
if result:
    print("✅ Found incident 4938:")
    print(f"  Incident ID: {result[0]}")
    print(f"  Resident: {result[1]}")
    print(f"  Type: {result[2]}")
    print(f"  Date: {result[3]}")
    print(f"  Status: {result[4]}")
    print(f"  MANAD ID: {result[5]}")
    print(f"  Description: {result[6][:80]}...")
else:
    print("❌ Incident 4938 NOT FOUND")
    
# Check all Open incidents from Oct 6
cursor.execute("""
    SELECT incident_id, resident_name, incident_type, incident_date, manad_incident_id
    FROM cims_incidents 
    WHERE status = 'Open' AND incident_date LIKE '2025-10-06%'
    ORDER BY incident_date DESC
""")

oct6_incidents = cursor.fetchall()
print(f"\n📅 All Open incidents from Oct 6, 2025: {len(oct6_incidents)} incidents")
for inc in oct6_incidents:
    print(f"  - {inc[0]}: {inc[1]} ({inc[2]}) - MANAD ID: {inc[4]}")

conn.close()

