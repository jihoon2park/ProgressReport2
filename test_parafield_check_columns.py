#!/usr/bin/env python3
"""
Event 테이블의 모든 컬럼명 확인
"""

import pyodbc
import sys

def check_event_columns():
    """Event 테이블의 모든 컬럼 확인"""
    server = 'efsvr02\\sqlexpress'
    database = 'ManadPlus_Edenfield'
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
        f"Connection Timeout=10;"
    )
    
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()
    
    print("Event 테이블의 모든 컬럼:")
    print("=" * 60)
    
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Event'
        ORDER BY ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    for i, col in enumerate(columns, 1):
        nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
        print(f"{i:2}. {col[0]:30} {col[1]:20} {nullable}")
    
    conn.close()

if __name__ == '__main__':
    check_event_columns()

