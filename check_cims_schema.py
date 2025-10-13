#!/usr/bin/env python3
"""Check cims_incidents table schema"""
import sqlite3

conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(cims_incidents)')
columns = cursor.fetchall()
print("Columns in cims_incidents table:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")
conn.close()

