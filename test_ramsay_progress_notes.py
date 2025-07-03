#!/usr/bin/env python3
"""
Ramsay 사이트 프로그레스 노트 가져오기 테스트
"""

import requests
import logging
from datetime import datetime, timedelta
from config import SITE_SERVERS, get_api_headers

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ramsay_progress_notes():
    """Ramsay 사이트 프로그레스 노트 가져오기 테스트"""
    print("=== Ramsay 사이트 프로그레스 노트 가져오기 테스트 ===")
    
    site = 'Ramsay'
    server_ip = SITE_SERVERS.get(site)
    
    if not server_ip:
        print(f"❌ {site} 사이트 설정을 찾을 수 없습니다.")
        return
    
    print(f"사이트: {site}")
    print(f"서버 IP: {server_ip}")
    
    # API URL 구성
    api_url = f"http://{server_ip}/api/progressnote/details"
    print(f"API URL: {api_url}")
    
    # 날짜 범위 설정 (5월 1일~10일)
    start_date = datetime(2025, 5, 1)
    end_date = datetime(2025, 5, 10)
    
    start_date_str = start_date.isoformat() + 'Z'
    end_date_str = end_date.isoformat() + 'Z'
    
    print(f"날짜 범위: {start_date_str} ~ {end_date_str}")
    
    # API 파라미터
    params = {
        'date': [f'gt:{start_date_str}', f'lt:{end_date_str}'],
        'limit': 100
    }
    
    # 세션 생성
    session = requests.Session()
    session.headers.update(get_api_headers(site))
    
    try:
        print("\nAPI 요청 시작...")
        response = session.get(api_url, params=params, timeout=30)
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공: {len(data)}개의 프로그레스 노트 조회")
            
            if data and len(data) > 0:
                # 첫 번째 항목 샘플 출력
                sample = data[0]
                print(f"\n샘플 데이터:")
                print(f"  - ID: {sample.get('Id')}")
                print(f"  - ClientId: {sample.get('ClientId')}")
                print(f"  - EventDate: {sample.get('EventDate')}")
                print(f"  - Notes: {sample.get('NotesPlainText', '')[:50]}...")
                print(f"  - CreatedBy: {sample.get('CreatedByUser', {}).get('UserName', 'N/A')}")
                
                # 전체 데이터 요약
                print(f"\n데이터 요약:")
                print(f"  - 총 개수: {len(data)}")
                
                # 클라이언트별 분포
                client_counts = {}
                for note in data:
                    client_id = note.get('ClientId')
                    client_counts[client_id] = client_counts.get(client_id, 0) + 1
                
                print(f"  - 고유 클라이언트 수: {len(client_counts)}")
                print(f"  - 클라이언트별 노트 수: {dict(list(client_counts.items())[:5])}...")
                
        else:
            print(f"❌ 실패: {response.status_code}")
            print(f"응답 내용: {response.text}")
            
    except requests.RequestException as e:
        print(f"❌ 네트워크 오류: {str(e)}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")

def test_ramsay_api_headers():
    """Ramsay 사이트 API 헤더 테스트"""
    print("\n=== Ramsay 사이트 API 헤더 테스트 ===")
    
    site = 'Ramsay'
    server_ip = SITE_SERVERS.get(site)
    
    # API URL 구성
    api_url = f"http://{server_ip}/api/progressnote/details"
    
    # 세션 생성
    session = requests.Session()
    session.headers.update(get_api_headers(site))
    
    print(f"사용된 헤더: {dict(session.headers)}")
    
    try:
        # 간단한 연결 테스트
        response = session.get(api_url, timeout=10)
        print(f"연결 테스트 응답: {response.status_code}")
        
    except Exception as e:
        print(f"연결 테스트 실패: {str(e)}")

if __name__ == "__main__":
    print("Ramsay 사이트 프로그레스 노트 가져오기 테스트를 시작합니다...")
    
    # API 헤더 테스트
    test_ramsay_api_headers()
    
    # 프로그레스 노트 가져오기 테스트
    test_ramsay_progress_notes()
    
    print("\n=== 테스트 완료 ===") 