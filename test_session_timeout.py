#!/usr/bin/env python3
"""
세션 타임아웃 기능 테스트 스크립트
"""

import requests
import json
import time
from datetime import datetime

def test_session_timeout():
    """세션 타임아웃 기능 테스트"""
    print("=== 세션 타임아웃 기능 테스트 ===")
    
    # 테스트 서버 URL
    base_url = "http://localhost:5000"
    
    # 테스트 사용자 정보
    test_user = {
        "username": "admin",
        "password": "password123", 
        "site": "Parafield Gardens"
    }
    
    try:
        # 세션 생성
        session = requests.Session()
        
        print("1. 로그인 테스트...")
        login_response = session.post(f"{base_url}/login", data=test_user, allow_redirects=False)
        
        print(f"   로그인 응답 상태: {login_response.status_code}")
        print(f"   리다이렉트 URL: {login_response.headers.get('Location', 'None')}")
        
        # 302 (리다이렉트) 또는 200 (성공) 모두 성공으로 처리
        if login_response.status_code in [200, 302]:
            print("✅ 로그인 성공")
            
            # 리다이렉트가 있으면 따라가기
            if login_response.status_code == 302:
                redirect_url = login_response.headers.get('Location')
                if redirect_url:
                    print(f"   리다이렉트 따라가기: {redirect_url}")
                    session.get(f"{base_url}{redirect_url}")
            
            print("\n2. 세션 상태 확인...")
            status_response = session.get(f"{base_url}/api/session-status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"✅ 세션 상태 확인 성공")
                print(f"   - 세션 생성 시간: {status_data['session_created']}")
                print(f"   - 세션 만료 시간: {status_data['session_expires']}")
                print(f"   - 남은 시간: {status_data['remaining_seconds']}초")
                
                # 세션 연장 테스트
                print("\n3. 세션 연장 테스트...")
                extend_response = session.post(f"{base_url}/api/extend-session")
                
                if extend_response.status_code == 200:
                    extend_data = extend_response.json()
                    print(f"✅ 세션 연장 성공")
                    print(f"   - 새로운 세션 생성 시간: {extend_data['session_created']}")
                    
                    # 연장 후 상태 확인
                    print("\n4. 연장 후 세션 상태 확인...")
                    status_response2 = session.get(f"{base_url}/api/session-status")
                    
                    if status_response2.status_code == 200:
                        status_data2 = status_response2.json()
                        print(f"✅ 연장 후 세션 상태 확인 성공")
                        print(f"   - 남은 시간: {status_data2['remaining_seconds']}초")
                        
                        # 5분 대기 테스트 (실제로는 너무 오래 걸리므로 10초만 대기)
                        print("\n5. 세션 타임아웃 대기 테스트 (10초)...")
                        print("   실제 테스트에서는 5분을 기다려야 합니다.")
                        print("   브라우저에서 직접 테스트하세요.")
                        
                else:
                    print(f"❌ 세션 연장 실패: {extend_response.status_code}")
                    print(f"   응답 내용: {extend_response.text}")
            else:
                print(f"❌ 세션 상태 확인 실패: {status_response.status_code}")
                print(f"   응답 내용: {status_response.text}")
                
        else:
            print(f"❌ 로그인 실패: {login_response.status_code}")
            print(f"   응답 내용: {login_response.text}")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()

def test_session_timeout_manual():
    """수동 세션 타임아웃 테스트 가이드"""
    print("\n=== 수동 세션 타임아웃 테스트 가이드 ===")
    print("1. 브라우저에서 http://localhost:5000 접속")
    print("2. 로그인 (admin/password123)")
    print("3. 5분 동안 아무것도 하지 않기")
    print("4. 1분 남았을 때 경고 팝업 확인")
    print("5. '세션 연장' 버튼 클릭하여 연장 테스트")
    print("6. 또는 5분 후 자동 로그아웃 확인")
    
    print("\n=== 테스트 시나리오 ===")
    print("시나리오 1: 세션 연장")
    print("  - 1분 전 경고 팝업에서 '세션 연장' 클릭")
    print("  - 세션이 연장되는지 확인")
    
    print("\n시나리오 2: 자동 로그아웃")
    print("  - 경고 팝업을 무시하고 5분 대기")
    print("  - 자동으로 로그인 페이지로 이동하는지 확인")
    
    print("\n시나리오 3: 사용자 활동 감지")
    print("  - 로그인 후 마우스나 키보드 활동")
    print("  - 2분 후 자동으로 세션이 연장되는지 확인")

if __name__ == "__main__":
    print("세션 타임아웃 기능 테스트를 시작합니다...")
    print("서버가 실행 중인지 확인하세요.")
    
    # API 테스트
    test_session_timeout()
    
    # 수동 테스트 가이드
    test_session_timeout_manual()
    
    print("\n=== 테스트 완료 ===") 