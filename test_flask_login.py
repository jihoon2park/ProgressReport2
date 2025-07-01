#!/usr/bin/env python3
"""
Flask-Login 통합 테스트 스크립트
"""

import requests
import json

def test_login():
    """로그인 테스트"""
    print("=== Flask-Login 통합 테스트 ===")
    
    # 테스트 서버 URL (실제 서버 주소로 변경)
    base_url = "http://localhost:5000"
    
    # 테스트 사용자 정보
    test_users = [
        {"username": "admin", "password": "password123", "site": "Parafield Gardens"},
        {"username": "doctor1", "password": "password123", "site": "Parafield Gardens"},
        {"username": "physio1", "password": "password123", "site": "Parafield Gardens"}
    ]
    
    for user in test_users:
        print(f"\n--- {user['username']} 로그인 테스트 ---")
        
        # 로그인 시도
        login_data = {
            'username': user['username'],
            'password': user['password'],
            'site': user['site']
        }
        
        try:
            # 세션 생성
            session = requests.Session()
            
            print("1. 로그인 테스트...")
            login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
            
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
                            print(f"❌ 연장 후 세션 상태 확인 실패: {status_response2.status_code}")
                            print(f"   응답 내용: {status_response2.text}")
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

def test_protected_routes():
    """보호된 라우트 테스트"""
    print("\n=== 보호된 라우트 테스트 ===")
    
    base_url = "http://localhost:5000"
    
    # 로그인하지 않은 상태에서 보호된 라우트 접근
    try:
        session = requests.Session()
        
        # 인덱스 페이지 접근 (로그인 필요)
        response = session.get(f"{base_url}/index")
        print(f"로그인 없이 /index 접근: {response.status_code}")
        
        # API 엔드포인트 접근
        response = session.get(f"{base_url}/api/user-info")
        print(f"로그인 없이 /api/user-info 접근: {response.status_code}")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {str(e)}")

if __name__ == "__main__":
    print("Flask-Login 통합 테스트를 시작합니다...")
    print("서버가 실행 중인지 확인하세요.")
    
    # 테스트 실행
    test_login()
    test_protected_routes()
    
    print("\n=== 테스트 완료 ===") 