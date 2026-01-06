#!/usr/bin/env python3
"""
프로덕션과 개발 환경 비교 스크립트
두 환경의 데이터베이스 상태를 비교합니다.
"""

import sqlite3
import os
from datetime import datetime

def compare_environments():
    """프로덕션과 개발 환경 비교"""
    
    print("=" * 60)
    print("프로덕션 vs 개발 환경 비교")
    print("=" * 60)
    
    # 프로덕션 경로 (IIS)
    prod_path = r'C:\inetpub\wwwroot\ProgressNoteWeb\ProgressReport2\progress_report.db'
    
    # 개발 경로 (현재 디렉토리)
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
            print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
            results[env_name] = None
            continue
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. 전체 인시던트 수
            cursor.execute("SELECT COUNT(*) as total FROM cims_incidents")
            total = cursor.fetchone()[0]
            print(f"📊 전체 인시던트 수: {total}")
            
            # 2. 상태별 분포
            cursor.execute("""
                SELECT status, COUNT(*) as cnt
                FROM cims_incidents
                WHERE status IS NOT NULL AND status != ''
                GROUP BY status
                ORDER BY cnt DESC
            """)
            status_dist = cursor.fetchall()
            print(f"📈 상태별 분포:")
            status_dict = {}
            for row in status_dist:
                print(f"   - {row[0]}: {row[1]}개")
                status_dict[row[0]] = row[1]
            
            # 3. 최근 7일 인시던트 수
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM cims_incidents
                WHERE incident_date IS NOT NULL 
                AND incident_date != ''
                AND incident_date >= ?
            """, [week_ago])
            week_count = cursor.fetchone()[0]
            print(f"📅 최근 7일 인시던트: {week_count}개")
            
            # 4. 마지막 동기화 시간
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'last_incident_sync_time'
            """)
            last_sync = cursor.fetchone()
            if last_sync:
                sync_time = datetime.fromisoformat(last_sync[0])
                days_ago = (datetime.now() - sync_time).days
                print(f"🔄 마지막 동기화: {last_sync[0]} ({days_ago}일 전)")
            else:
                print(f"⚠️  동기화 기록이 없습니다.")
            
            # 5. 최신 인시던트 날짜
            cursor.execute("""
                SELECT MAX(incident_date) as latest_date
                FROM cims_incidents
                WHERE incident_date IS NOT NULL AND incident_date != ''
            """)
            latest = cursor.fetchone()[0]
            if latest:
                print(f"📅 최신 인시던트 날짜: {latest}")
            
            results[env_name] = {
                'total': total,
                'status_dist': status_dict,
                'week_count': week_count,
                'last_sync': last_sync[0] if last_sync else None,
                'latest_date': latest
            }
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            results[env_name] = None
        finally:
            conn.close()
    
    # 비교 결과
    print(f"\n{'='*60}")
    print("비교 결과")
    print(f"{'='*60}")
    
    if results.get('Production') and results.get('Development'):
        prod = results['Production']
        dev = results['Development']
        
        print(f"\n전체 인시던트 수:")
        print(f"  Production: {prod['total']}개")
        print(f"  Development: {dev['total']}개")
        print(f"  차이: {abs(prod['total'] - dev['total'])}개")
        
        print(f"\n최근 7일 인시던트:")
        print(f"  Production: {prod['week_count']}개")
        print(f"  Development: {dev['week_count']}개")
        print(f"  차이: {abs(prod['week_count'] - dev['week_count'])}개")
        
        if prod['last_sync'] and dev['last_sync']:
            prod_sync = datetime.fromisoformat(prod['last_sync'])
            dev_sync = datetime.fromisoformat(dev['last_sync'])
            print(f"\n마지막 동기화 시간:")
            print(f"  Production: {prod['last_sync']}")
            print(f"  Development: {dev['last_sync']}")
            print(f"  차이: {abs((prod_sync - dev_sync).days)}일")
        
        print(f"\n⚠️  두 환경이 서로 다른 데이터를 사용하고 있습니다!")
        print(f"   해결 방법:")
        print(f"   1. 프로덕션에서 Force Sync 실행")
        print(f"   2. 두 환경이 동일한 MANAD DB 소스를 사용하는지 확인")
        print(f"   3. 동기화 스케줄이 제대로 작동하는지 확인")

if __name__ == '__main__':
    from datetime import timedelta
    compare_environments()

