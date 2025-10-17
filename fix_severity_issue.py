#!/usr/bin/env python3
"""
Severity NOT NULL 제약 문제 해결 스크립트
"""
import sqlite3
from datetime import datetime

def get_db_connection():
    """DB 연결"""
    conn = sqlite3.connect('progress_report.db')
    conn.row_factory = sqlite3.Row
    return conn

def check_schema():
    """현재 스키마 확인"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 cims_incidents 테이블 스키마 확인")
    print("=" * 80)
    print()
    
    cursor.execute("PRAGMA table_info(cims_incidents)")
    columns = cursor.fetchall()
    
    print("컬럼 정보:")
    print(f"{'Name':<30} {'Type':<20} {'NotNull':<10} {'Default':<15}")
    print("-" * 80)
    
    severity_info = None
    for col in columns:
        is_null = "NOT NULL" if col['notnull'] else "NULL OK"
        default = col['dflt_value'] or "None"
        print(f"{col['name']:<30} {col['type']:<20} {is_null:<10} {default:<15}")
        
        if col['name'] == 'severity':
            severity_info = col
    
    print()
    
    if severity_info:
        if severity_info['notnull']:
            print("❌ severity 컬럼이 NOT NULL 제약을 가지고 있습니다!")
            print("   이것이 문제의 원인입니다.")
        else:
            print("✅ severity 컬럼이 NULL을 허용합니다.")
    else:
        print("⚠️  severity 컬럼을 찾을 수 없습니다!")
    
    print()
    conn.close()
    return severity_info

def check_null_severity():
    """severity가 NULL인 incidents 확인"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔍 severity가 NULL인 Incidents 확인")
    print("=" * 80)
    print()
    
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM cims_incidents
        WHERE severity IS NULL
    """)
    
    null_count = cursor.fetchone()['count']
    print(f"severity가 NULL인 incidents: {null_count}개")
    
    if null_count > 0:
        cursor.execute("""
            SELECT incident_id, site, incident_type, incident_date
            FROM cims_incidents
            WHERE severity IS NULL
            ORDER BY incident_date DESC
            LIMIT 10
        """)
        
        incidents = cursor.fetchall()
        print(f"\n최근 10개:")
        for idx, inc in enumerate(incidents, 1):
            print(f"  {idx}. {inc['incident_id']} | {inc['site']} | {inc['incident_type']}")
    
    print()
    conn.close()
    return null_count

def backup_table():
    """테이블 백업"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"cims_incidents_backup_{timestamp}"
    
    print(f"📦 테이블 백업 중: {backup_name}")
    
    cursor.execute(f"""
        CREATE TABLE {backup_name} AS 
        SELECT * FROM cims_incidents
    """)
    
    conn.commit()
    
    cursor.execute(f"SELECT COUNT(*) as count FROM {backup_name}")
    count = cursor.fetchone()['count']
    
    print(f"✅ {count}개의 레코드 백업 완료")
    print()
    
    conn.close()
    return backup_name

def fix_null_severity():
    """severity가 NULL인 레코드에 기본값 설정"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔧 severity NULL 값 수정")
    print("=" * 80)
    print()
    
    cursor.execute("""
        UPDATE cims_incidents
        SET severity = 'Unknown'
        WHERE severity IS NULL
    """)
    
    updated = cursor.rowcount
    conn.commit()
    
    print(f"✅ {updated}개의 레코드 수정 완료 (severity = 'Unknown')")
    print()
    
    conn.close()
    return updated

def main():
    """메인 함수"""
    print("=" * 80)
    print("🛠️  Severity NOT NULL 문제 해결 도구")
    print("=" * 80)
    print()
    print("이 스크립트는:")
    print("  1. 현재 DB 스키마 확인")
    print("  2. severity가 NULL인 레코드 확인")
    print("  3. NULL 값을 'Unknown'으로 업데이트")
    print()
    
    response = input("계속하시겠습니까? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ 취소됨")
        return
    
    print()
    
    # 1. 스키마 확인
    severity_info = check_schema()
    
    # 2. NULL severity 확인
    null_count = check_null_severity()
    
    # 3. NULL 값 수정
    if null_count > 0:
        print("=" * 80)
        print("⚠️  경고")
        print("=" * 80)
        print(f"{null_count}개의 incident에 severity가 NULL입니다.")
        print("이 레코드들을 'Unknown'으로 업데이트하시겠습니까?")
        print()
        
        response = input("업데이트하시겠습니까? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ 업데이트 취소됨")
            return
        
        print()
        
        # 백업
        backup_name = backup_table()
        
        # 수정
        updated = fix_null_severity()
        
        # 확인
        null_count_after = check_null_severity()
        
        if null_count_after == 0:
            print("=" * 80)
            print("✅ 모든 NULL severity 값이 수정되었습니다!")
            print("=" * 80)
            print()
            print(f"백업 테이블: {backup_name}")
            print("문제가 발생하면 백업에서 복원할 수 있습니다:")
            print(f"  DROP TABLE cims_incidents;")
            print(f"  ALTER TABLE {backup_name} RENAME TO cims_incidents;")
            print()
    else:
        print("✅ severity가 NULL인 레코드가 없습니다.")
        print()
    
    # 권장사항
    print("=" * 80)
    print("📋 권장사항")
    print("=" * 80)
    print()
    print("1. app.py의 severity 처리 코드를 수정하여 NULL 방지:")
    print("   line 5819:")
    print("   OLD: incident.get('SeverityRating') or incident.get('RiskRatingName'),")
    print("   NEW: incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',")
    print()
    print("2. 또는 DB 스키마에서 NOT NULL 제약 제거 (SQLite 제한으로 복잡함)")
    print()
    print("3. 수정 후 Force Sync를 다시 실행하세요")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

