#!/usr/bin/env python3
"""
모든 사이트 DB 연결 테스트 스크립트
각 사이트의 DB 직접 접속을 테스트합니다.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# .env 파일 로드
try:
    from dotenv import load_dotenv
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드 완료")
    else:
        print(f"⚠️ .env 파일을 찾을 수 없습니다.")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. 환경 변수를 수동으로 설정하세요.")
    print("💡 설치: pip install python-dotenv")
    # .env 파일 직접 읽기 (간단한 방법)
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"✅ .env 파일 직접 로드 완료")

from manad_db_connector import MANADDBConnector

def test_site_connection(site_name):
    """특정 사이트의 DB 연결 테스트"""
    print(f"\n{'=' * 60}")
    print(f"🔍 {site_name} DB 연결 테스트")
    print(f"{'=' * 60}")
    
    try:
        connector = MANADDBConnector(site_name)
        
        # 1. Client 조회 테스트
        print(f"\n1️⃣ Client 조회 테스트...")
        success, clients = connector.fetch_clients()
        if success and clients:
            print(f"   ✅ 성공: {len(clients)}명의 Client 조회 완료")
            if len(clients) > 0:
                print(f"   📋 샘플: {clients[0].get('FirstName', '')} {clients[0].get('LastName', '')}")
        else:
            print(f"   ❌ 실패: Client 조회 실패")
            return False
        
        # 2. Progress Notes 조회 테스트 (최근 7일)
        print(f"\n2️⃣ Progress Notes 조회 테스트 (최근 7일)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        success, progress_notes = connector.fetch_progress_notes(start_date, end_date, limit=10)
        if success and progress_notes:
            print(f"   ✅ 성공: {len(progress_notes)}개 Progress Notes 조회 완료")
        else:
            print(f"   ⚠️ 경고: Progress Notes 조회 실패 또는 데이터 없음")
        
        # 3. Care Area 조회 테스트
        print(f"\n3️⃣ Care Area 조회 테스트...")
        success, care_areas = connector.fetch_care_areas()
        if success and care_areas:
            print(f"   ✅ 성공: {len(care_areas)}개 Care Area 조회 완료")
        else:
            print(f"   ⚠️ 경고: Care Area 조회 실패")
        
        # 4. Event Type 조회 테스트
        print(f"\n4️⃣ Event Type 조회 테스트...")
        success, event_types = connector.fetch_event_types()
        if success and event_types:
            print(f"   ✅ 성공: {len(event_types)}개 Event Type 조회 완료")
        else:
            print(f"   ⚠️ 경고: Event Type 조회 실패")
        
        print(f"\n✅ {site_name} DB 연결 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ {site_name} DB 연결 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """모든 사이트 DB 연결 테스트"""
    sites = [
        'Parafield Gardens',
        'Nerrilda',
        'Ramsay',
        'West Park',
        'Yankalilla'
    ]
    
    print("=" * 60)
    print("모든 사이트 DB 연결 테스트")
    print("=" * 60)
    
    results = {}
    for site in sites:
        results[site] = test_site_connection(site)
    
    # 결과 요약
    print(f"\n{'=' * 60}")
    print("📊 테스트 결과 요약")
    print(f"{'=' * 60}")
    
    for site, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"   {site}: {status}")
    
    # 성공/실패 통계
    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)
    
    print(f"\n총 {total_count}개 사이트 중 {success_count}개 성공, {total_count - success_count}개 실패")
    
    if success_count == total_count:
        print("\n🎉 모든 사이트 DB 연결 성공!")
        return 0
    else:
        print("\n⚠️ 일부 사이트 DB 연결 실패. 설정을 확인하세요.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

