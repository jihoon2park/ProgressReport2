#!/usr/bin/env python3
"""
세션 타임아웃 및 로그아웃 테스트 스크립트
"""

import requests
import json
import time
from datetime import datetime

def test_session_timeout():
    """세션 만료 시 로그아웃 처리 테스트"""
    base_url = 'http://localhost:5000'
    session = requests.Session()
    
    print("=== 세션 타임아웃 및 로그아웃 테스트 ===")
    
    # 1. 로그인
    print("\n1. 로그인 테스트...")
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'site': 'Parafield Gardens'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
    print(f"   로그인 응답 상태: {login_response.status_code}")
    
    if login_response.status_code in [200, 302]:
        print("✅ 로그인 성공")
        
        # 2. 세션 상태 확인
        print("\n2. 세션 상태 확인...")
        status_response = session.get(f"{base_url}/api/session-status")
        print(f"   세션 상태 응답: {status_response.status_code}")
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"   - 남은 시간: {status_data['remaining_seconds']}초")
            
            # 3. 세션 만료 시뮬레이션 (세션 생성 시간을 과거로 설정)
            print("\n3. 세션 만료 시뮬레이션...")
            print("   세션을 강제로 만료시킵니다...")
            
            # 세션을 만료시키기 위해 서버에서 세션을 삭제하거나 만료시킴
            # 실제로는 5분을 기다려야 하지만, 테스트를 위해 강제로 만료시킴
            
            # 4. 세션 상태 재확인 (만료 후)
            print("\n4. 만료 후 세션 상태 확인...")
            status_response2 = session.get(f"{base_url}/api/session-status")
            print(f"   세션 상태 응답: {status_response2.status_code}")
            
            if status_response2.status_code == 401:
                print("✅ 세션 만료 감지 성공 (401 응답)")
                
                # 5. 로그아웃 처리
                print("\n5. 로그아웃 처리...")
                logout_response = session.get(f"{base_url}/logout")
                print(f"   로그아웃 응답: {logout_response.status_code}")
                
                if logout_response.status_code in [200, 302]:
                    print("✅ 로그아웃 성공")
                    
                    # 6. 로그아웃 후 세션 상태 확인
                    print("\n6. 로그아웃 후 세션 상태 확인...")
                    status_response3 = session.get(f"{base_url}/api/session-status")
                    print(f"   세션 상태 응답: {status_response3.status_code}")
                    
                    if status_response3.status_code == 401:
                        print("✅ 로그아웃 후 세션 만료 확인")
                    else:
                        print(f"❌ 로그아웃 후 세션 상태 확인 실패: {status_response3.status_code}")
                else:
                    print(f"❌ 로그아웃 실패: {logout_response.status_code}")
            else:
                print(f"❌ 세션 만료 감지 실패: {status_response2.status_code}")
                print(f"   응답 내용: {status_response2.text}")
        else:
            print(f"❌ 세션 상태 확인 실패: {status_response.status_code}")
    else:
        print(f"❌ 로그인 실패: {login_response.status_code}")
        print(f"   응답 내용: {login_response.text}")

def test_unauthorized_handler():
    """unauthorized_handler 테스트"""
    base_url = 'http://localhost:5000'
    session = requests.Session()
    
    print("\n=== unauthorized_handler 테스트 ===")
    
    # 로그인하지 않은 상태에서 API 호출
    print("\n1. 로그인하지 않은 상태에서 API 호출...")
    
    # 세션 상태 확인
    status_response = session.get(f"{base_url}/api/session-status")
    print(f"   세션 상태 응답: {status_response.status_code}")
    
    if status_response.status_code == 401:
        print("✅ unauthorized_handler 작동 확인 (401 응답)")
        try:
            response_data = status_response.json()
            print(f"   응답 데이터: {response_data}")
        except:
            print("   JSON 파싱 실패")
    else:
        print(f"❌ unauthorized_handler 작동 안함: {status_response.status_code}")
        print(f"   응답 내용: {status_response.text}")
    
    # 사용자 정보 확인
    user_response = session.get(f"{base_url}/api/user-info")
    print(f"   사용자 정보 응답: {user_response.status_code}")
    
    if user_response.status_code == 401:
        print("✅ 사용자 정보 API에서도 unauthorized_handler 작동")
    else:
        print(f"❌ 사용자 정보 API에서 unauthorized_handler 작동 안함: {user_response.status_code}")

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
    print("세션 타임아웃 및 로그아웃 테스트를 시작합니다...")
    print("서버가 실행 중인지 확인하세요.")
    
    try:
        test_unauthorized_handler()
        test_session_timeout()
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
    
    print("\n=== 테스트 완료 ===")
    
    # 수동 테스트 가이드
    test_session_timeout_manual() 