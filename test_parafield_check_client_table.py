#!/usr/bin/env python3
"""Client 테이블 컬럼 확인"""

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

print("Client 테이블의 모든 컬럼:")
print("=" * 60)

cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Client'
    ORDER BY ORDINAL_POSITION
""")

columns = cursor.fetchall()
for i, col in enumerate(columns, 1):
    nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
    print(f"{i:2}. {col[0]:30} {col[1]:20} {nullable}")

# 샘플 데이터도 확인
print("\n\nClient 테이블 샘플 데이터 (3개):")
print("=" * 60)

cursor.execute("SELECT TOP 3 * FROM Client WHERE IsDeleted = 0")
rows = cursor.fetchall()
if rows:
    # 컬럼명 가져오기
    columns = [column[0] for column in cursor.description]
    print(f"컬럼: {', '.join(columns[:10])}...")
    for row in rows:
        print(f"  ID: {row[0]}, 데이터: {str(row)[:200]}...")

conn.close()

