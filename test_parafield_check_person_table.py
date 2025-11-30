#!/usr/bin/env python3
"""Person 테이블 컬럼 확인"""

import pyodbc

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

print("Person 테이블의 컬럼 (이름 관련):")
print("=" * 60)

cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Person'
    AND (COLUMN_NAME LIKE '%Name%' OR COLUMN_NAME LIKE '%First%' OR COLUMN_NAME LIKE '%Last%' OR COLUMN_NAME LIKE '%Given%' OR COLUMN_NAME LIKE '%Surname%')
    ORDER BY ORDINAL_POSITION
""")

name_columns = cursor.fetchall()
print("이름 관련 컬럼:")
for col in name_columns:
    print(f"  - {col[0]}: {col[1]}")

# 전체 컬럼 확인
cursor.execute("""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Person'
    ORDER BY ORDINAL_POSITION
""")

all_columns = cursor.fetchall()
print(f"\n전체 컬럼 ({len(all_columns)}개):")
for i, col in enumerate(all_columns[:20], 1):
    print(f"  {i:2}. {col[0]}")
if len(all_columns) > 20:
    print(f"  ... (총 {len(all_columns)}개)")

# 샘플 데이터
print("\n\nPerson 테이블 샘플 (1개):")
cursor.execute("SELECT TOP 1 * FROM Person")
row = cursor.fetchone()
if row:
    columns = [column[0] for column in cursor.description]
    print(f"컬럼: {', '.join(columns[:15])}...")

conn.close()

