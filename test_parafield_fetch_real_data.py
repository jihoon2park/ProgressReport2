#!/usr/bin/env python3
"""
Parafield Gardens - 실제 데이터 조회 (수정된 쿼리)
"""

import pyodbc
import sys
from datetime import datetime, timedelta

def test_fetch():
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
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    query = """
        SELECT TOP 5
            e.Id,
            e.PersonId AS ClientId,
            e.Date,
            e.DateReported AS ReportedDate,
            e.EventDetail AS Description,
            ISNULL(esr.Description, '') AS SeverityRating,
            ISNULL(err.Description, '') AS RiskRatingName,
            CASE 
                WHEN e.StatusEnumId = 0 THEN 'Open'
                WHEN e.StatusEnumId = 1 THEN 'Closed'
                ELSE 'Unknown'
            END AS Status,
            e.Actions AS ActionTaken,
            ISNULL(e.Ma4ReportedBy, ISNULL(pr_reported.FirstName + ' ' + pr_reported.LastName, '')) AS ReportedByName,
            ISNULL(p_client.FirstName, '') AS FirstName,
            ISNULL(p_client.LastName, '') AS LastName,
            ISNULL(et.Description, '') AS EventTypeName
        FROM Event e
        LEFT JOIN Person p_client ON e.PersonId = p_client.Id
        LEFT JOIN EventSeverityRating esr ON e.EventSeverityRatingId = esr.Id
        LEFT JOIN EventRiskRating err ON e.EventRiskRatingId = err.Id
        LEFT JOIN Person pr_reported ON e.ReportedById = pr_reported.Id
        LEFT JOIN EventType et ON e.EventTypeId = et.Id
        WHERE e.Date >= ? AND e.Date <= ?
        AND e.IsDeleted = 0
        ORDER BY e.Date DESC
    """
    
    print("=" * 60)
    print("실제 데이터 조회 테스트")
    print("=" * 60)
    
    cursor.execute(query, (start_date, end_date))
    rows = cursor.fetchall()
    
    print(f"\n✅ {len(rows)}개 Event 발견:\n")
    
    columns = [column[0] for column in cursor.description]
    print(f"컬럼: {', '.join(columns)}\n")
    
    for row in rows:
        print(f"Event ID: {row[0]}")
        print(f"  Date: {row[2]}")
        print(f"  Client: {row[10] or ''} {row[11] or ''} (PersonId: {row[1]})")
        print(f"  Event Type: {row[12]}")
        print(f"  Severity: {row[5]}")
        print(f"  Risk: {row[6]}")
        print(f"  Status: {row[7]}")
        print(f"  Reported By: {row[9]}")
        print(f"  Description: {(str(row[4]) if row[4] else '')[:100]}...")
        print()
    
    conn.close()

if __name__ == '__main__':
    test_fetch()

