"""
Unknown Fall Type 분석용 데이터 추출 스크립트

Unknown으로 분류된 Fall incidents의 상세 정보를 CSV 파일로 저장합니다.
"""

import sqlite3
import csv
from datetime import datetime, timedelta
import os

def export_unknown_falls():
    """Unknown으로 분류된 Fall incidents를 CSV로 저장"""
    
    try:
        # DB 연결
        db_path = 'progress_report.db'
        if not os.path.exists(db_path):
            print(f"❌ Database not found: {db_path}")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Fall policy detector 임포트
        from services.fall_policy_detector import fall_detector
        
        # 최근 30일 Fall incidents 조회
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT 
                id,
                incident_id,
                incident_type,
                incident_date,
                site,
                resident_name,
                description,
                severity
            FROM cims_incidents
            WHERE incident_type LIKE '%Fall%'
            AND incident_date >= ?
            ORDER BY incident_date DESC
        """, (thirty_days_ago,))
        
        incidents = cursor.fetchall()
        
        # Unknown falls 수집
        unknown_falls = []
        
        for incident in incidents:
            incident_id = incident[0]
            incident_manad_id = incident[1]
            incident_type = incident[2]
            incident_date = incident[3]
            site = incident[4]
            resident_name = incident[5]
            description = incident[6]
            severity = incident[7]
            
            # Fall 유형 감지
            fall_type = fall_detector.detect_fall_type_from_incident(incident_id, cursor)
            
            # Unknown인 경우만 수집
            if fall_type == 'unknown':
                # Progress notes 조회
                cursor.execute("""
                    SELECT content, created_at
                    FROM cims_progress_notes
                    WHERE incident_id = ?
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (incident_id,))
                
                notes = cursor.fetchall()
                progress_notes = []
                for note in notes:
                    note_text = note[0] or ''
                    note_date = note[1] or ''
                    if note_text.strip():
                        progress_notes.append(f"[{note_date}] {note_text[:200]}")
                
                progress_notes_str = "\n---\n".join(progress_notes) if progress_notes else "No progress notes"
                
                unknown_falls.append({
                    'incident_id': incident_manad_id,
                    'incident_type': incident_type,
                    'incident_date': incident_date,
                    'site': site,
                    'resident_name': resident_name,
                    'severity': severity,
                    'description': description or 'No description',
                    'progress_notes': progress_notes_str,
                    'db_id': incident_id
                })
        
        conn.close()
        
        # CSV 파일로 저장
        if unknown_falls:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'unknown_falls_{timestamp}.csv'
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = [
                    'incident_id', 
                    'incident_type', 
                    'incident_date', 
                    'site',
                    'resident_name',
                    'severity',
                    'description', 
                    'progress_notes',
                    'db_id'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(unknown_falls)
            
            print(f"✅ Unknown Falls 저장 완료!")
            print(f"📄 파일명: {filename}")
            print(f"📊 총 {len(unknown_falls)}개의 Unknown Falls")
            print(f"\n📋 Summary:")
            
            # 사이트별 집계
            site_counts = {}
            for fall in unknown_falls:
                site = fall['site']
                site_counts[site] = site_counts.get(site, 0) + 1
            
            for site, count in sorted(site_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {site}: {count}건")
            
            # 상세 텍스트 파일도 생성 (더 읽기 쉽게)
            text_filename = f'unknown_falls_{timestamp}.txt'
            with open(text_filename, 'w', encoding='utf-8') as txtfile:
                txtfile.write("=" * 80 + "\n")
                txtfile.write("Unknown Fall Incidents - Detailed Report\n")
                txtfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                txtfile.write(f"Total: {len(unknown_falls)} incidents\n")
                txtfile.write("=" * 80 + "\n\n")
                
                for idx, fall in enumerate(unknown_falls, 1):
                    txtfile.write(f"\n{'=' * 80}\n")
                    txtfile.write(f"[{idx}/{len(unknown_falls)}] Incident ID: {fall['incident_id']}\n")
                    txtfile.write(f"{'=' * 80}\n")
                    txtfile.write(f"Type:         {fall['incident_type']}\n")
                    txtfile.write(f"Date:         {fall['incident_date']}\n")
                    txtfile.write(f"Site:         {fall['site']}\n")
                    txtfile.write(f"Resident:     {fall['resident_name']}\n")
                    txtfile.write(f"Severity:     {fall['severity']}\n")
                    txtfile.write(f"DB ID:        {fall['db_id']}\n")
                    txtfile.write(f"\nDescription:\n")
                    txtfile.write(f"{'-' * 80}\n")
                    txtfile.write(f"{fall['description']}\n")
                    txtfile.write(f"\nProgress Notes:\n")
                    txtfile.write(f"{'-' * 80}\n")
                    txtfile.write(f"{fall['progress_notes']}\n")
                    txtfile.write("\n")
            
            print(f"📄 상세 파일: {text_filename}")
            print(f"\n💡 Tip: 텍스트 파일을 열어서 패턴을 찾아보세요!")
            
        else:
            print("✅ Unknown Falls가 없습니다!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔍 Unknown Fall Incidents 추출 중...\n")
    export_unknown_falls()

