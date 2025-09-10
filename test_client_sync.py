#!/usr/bin/env python3
"""
클라이언트 동기화 테스트
새로운 거주자 추가 시나리오 테스트
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

def test_client_sync_scenario():
    """새로운 거주자 추가 시나리오 테스트"""
    print("=" * 60)
    print("새로운 거주자 추가 시나리오 테스트")
    print("=" * 60)
    
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print("❌ 데이터베이스 파일을 찾을 수 없습니다.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 현재 상태 확인
        print("\n1. 현재 클라이언트 상태 확인")
        print("-" * 40)
        
        cursor.execute('''
            SELECT site, COUNT(*) as count, MAX(last_synced) as last_sync
            FROM clients_cache 
            WHERE is_active = 1
            GROUP BY site
        ''')
        
        for row in cursor.fetchall():
            site, count, last_sync = row
            if last_sync:
                sync_time = datetime.fromisoformat(last_sync)
                age = datetime.now() - sync_time
                age_minutes = int(age.total_seconds() / 60)
                print(f"  {site}: {count}명 (마지막 동기화: {age_minutes}분 전)")
            else:
                print(f"  {site}: {count}명 (동기화 기록 없음)")
        
        # 2. 캐시 만료 시뮬레이션
        print("\n2. 캐시 만료 시뮬레이션")
        print("-" * 40)
        
        # Parafield Gardens 캐시를 31분 전으로 설정 (만료 시뮬레이션)
        expired_time = datetime.now() - timedelta(minutes=31)
        cursor.execute('''
            UPDATE sync_status 
            SET last_sync_time = ?
            WHERE data_type = 'clients' AND site = 'Parafield Gardens'
        ''', (expired_time.isoformat(),))
        
        conn.commit()
        print("  ✓ Parafield Gardens 캐시를 31분 전으로 설정 (만료 상태)")
        
        # 3. 새 거주자 추가 시뮬레이션
        print("\n3. 새 거주자 추가 시뮬레이션")
        print("-" * 40)
        
        # 가상의 새 거주자 데이터
        new_resident = {
            'person_id': 9999,
            'client_name': '김철수 (테스트)',
            'preferred_name': '철수',
            'room_number': '999',
            'room_name': '999: Test',
            'site': 'Parafield Gardens'
        }
        
        # SQLite에 새 거주자 추가
        cursor.execute('''
            INSERT INTO clients_cache 
            (person_id, client_name, preferred_name, room_number, room_name, 
             site, last_synced, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_resident['person_id'],
            new_resident['client_name'],
            new_resident['preferred_name'],
            new_resident['room_number'],
            new_resident['room_name'],
            new_resident['site'],
            datetime.now().isoformat(),
            True
        ))
        
        conn.commit()
        print(f"  ✓ 새 거주자 추가: {new_resident['client_name']}")
        
        # 4. 업데이트된 상태 확인
        print("\n4. 업데이트된 상태 확인")
        print("-" * 40)
        
        cursor.execute('''
            SELECT COUNT(*) FROM clients_cache 
            WHERE site = 'Parafield Gardens' AND is_active = 1
        ''')
        pg_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT client_name, room_number 
            FROM clients_cache 
            WHERE site = 'Parafield Gardens' AND person_id = 9999 AND is_active = 1
        ''')
        test_client = cursor.fetchone()
        
        if test_client:
            print(f"  ✓ Parafield Gardens: {pg_count}명 (새 거주자 포함)")
            print(f"  ✓ 테스트 거주자 확인: {test_client[0]} (방: {test_client[1]})")
        else:
            print("  ❌ 테스트 거주자를 찾을 수 없습니다.")
        
        # 5. 실제 시나리오 시뮬레이션
        print("\n5. 실제 사용 시나리오 시뮬레이션")
        print("-" * 40)
        
        # Progress Note 작성을 위한 클라이언트 목록 조회
        cursor.execute('''
            SELECT client_name, preferred_name, room_number
            FROM clients_cache 
            WHERE site = 'Parafield Gardens' AND is_active = 1
            AND client_name LIKE '%김철수%'
            ORDER BY client_name
        ''')
        
        search_results = cursor.fetchall()
        
        if search_results:
            print("  ✓ Progress Note 작성 시 새 거주자 검색 가능:")
            for client in search_results:
                name = client[1] or client[0]  # preferred_name 또는 client_name
                print(f"    - {name} (방: {client[2]})")
        else:
            print("  ❌ 새 거주자를 검색할 수 없습니다.")
        
        # 6. 동기화 상태 확인
        print("\n6. 동기화 상태 확인")
        print("-" * 40)
        
        cursor.execute('''
            SELECT data_type, site, sync_status, last_sync_time, records_synced
            FROM sync_status 
            WHERE data_type = 'clients'
            ORDER BY site
        ''')
        
        for row in cursor.fetchall():
            data_type, site, status, last_sync, records = row
            if last_sync:
                sync_time = datetime.fromisoformat(last_sync)
                age = datetime.now() - sync_time
                age_minutes = int(age.total_seconds() / 60)
                expired = "만료됨" if age_minutes > 30 else "유효함"
                print(f"  {site}: {status} ({records}개, {age_minutes}분 전, {expired})")
            else:
                print(f"  {site}: {status} ({records}개, 동기화 기록 없음)")
        
        # 7. 정리 (테스트 데이터 제거)
        print("\n7. 테스트 데이터 정리")
        print("-" * 40)
        
        cursor.execute('DELETE FROM clients_cache WHERE person_id = 9999')
        conn.commit()
        print("  ✓ 테스트 거주자 데이터 제거 완료")
        
        # 동기화 시간 복구
        cursor.execute('''
            UPDATE sync_status 
            SET last_sync_time = ?
            WHERE data_type = 'clients' AND site = 'Parafield Gardens'
        ''', (datetime.now().isoformat(),))
        
        conn.commit()
        print("  ✓ 동기화 시간 복구 완료")
        
    finally:
        conn.close()

def demonstrate_update_workflow():
    """업데이트 워크플로우 설명"""
    print("\n" + "=" * 60)
    print("새로운 거주자 추가 시 업데이트 워크플로우")
    print("=" * 60)
    
    print("""
🏥 상황: 새로운 거주자 "이영희"가 Parafield Gardens에 입소

📋 현재 시스템에서의 처리 과정:

1️⃣ 외부 시스템 업데이트
   - 시설 관리 시스템에 "이영희" 정보 등록
   - PersonId: 1234, Room: 101A 할당

2️⃣ 우리 시스템의 상태
   ❌ SQLite 캐시: 아직 "이영희" 정보 없음
   ❌ 드롭다운 목록: "이영희" 나타나지 않음

3️⃣ 해결 방법들:

   🔄 Option A: 자동 새로고침 (30분 후)
   - 백그라운드 동기화가 API 호출
   - SQLite 캐시 자동 업데이트
   - 다음 Progress Note 작성 시 "이영희" 표시

   🔘 Option B: 수동 새로고침 (즉시)
   - 관리자가 "새로고침" 버튼 클릭
   - API에서 최신 데이터 가져오기
   - SQLite 캐시 즉시 업데이트

   ⚡ Option C: 스마트 캐시 (자동)
   - Progress Note 페이지 로드 시 캐시 나이 확인
   - 30분 이상 된 캐시는 자동 갱신
   - 사용자는 항상 최신 데이터 확인

4️⃣ 권장 구현 방안:
   ✅ 백그라운드 동기화 (30분 간격)
   ✅ 수동 새로고침 버튼 (긴급 시)
   ✅ 캐시 만료 자동 감지
   ✅ 변경사항 로그 기록

📊 예상 효과:
   - 새 거주자 반영 시간: 최대 30분 → 평균 15분
   - 긴급 시: 즉시 수동 새로고침 가능
   - 시스템 부하: 최소화 (스마트 캐싱)
   - 사용자 경험: 항상 최신 데이터 보장
""")

def show_implementation_guide():
    """구현 가이드 표시"""
    print("\n" + "=" * 60)
    print("구현 가이드")
    print("=" * 60)
    
    print("""
🛠️ 즉시 구현 가능한 기능들:

1. 수동 새로고침 API (이미 추가됨)
   POST /api/clients/refresh/<site>
   - 관리자/사이트 관리자만 사용 가능
   - 즉시 최신 데이터 가져와서 SQLite 업데이트

2. 동기화 상태 확인 API (이미 추가됨)
   GET /api/clients/sync-status
   - 각 사이트별 마지막 동기화 시간 확인
   - 캐시 만료 여부 확인

3. 전체 사이트 새로고침 API (이미 추가됨)
   POST /api/clients/refresh-all
   - 시스템 관리자만 사용 가능
   - 모든 사이트 데이터 일괄 업데이트

📱 UI에 추가할 기능들:

1. Progress Note 페이지에 "새로고침" 버튼
   - 클라이언트 드롭다운 옆에 배치
   - 클릭 시 해당 사이트 데이터 즉시 업데이트

2. 관리자 대시보드에 동기화 상태 표시
   - 각 사이트별 마지막 동기화 시간
   - 캐시 만료 상태 표시
   - 일괄 새로고침 버튼

3. 자동 새로고침 알림
   - 캐시가 30분 이상 된 경우 경고 메시지
   - "데이터가 오래되었습니다. 새로고침하시겠습니까?"

🚀 다음 단계 구현:

1. requirements.txt에 schedule 패키지 추가
   pip install schedule

2. Flask 앱 시작 시 백그라운드 동기화 시작
   from client_sync_manager import init_client_sync
   init_client_sync(app)

3. Progress Note 페이지 UI 개선
   - 새로고침 버튼 추가
   - 마지막 업데이트 시간 표시
""")

if __name__ == "__main__":
    test_client_sync_scenario()
    demonstrate_update_workflow()
    show_implementation_guide()
