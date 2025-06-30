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
            
            # 로그인
            response = session.post(f"{base_url}/login", data=login_data)
            print(f"로그인 응답 상태: {response.status_code}")
            
            if response.status_code == 302:  # 리다이렉트 (성공)
                print("✅ 로그인 성공")
                
                # 사용자 정보 조회
                user_info_response = session.get(f"{base_url}/api/user-info")
                if user_info_response.status_code == 200:
                    user_info = user_info_response.json()
                    print(f"사용자 정보: {json.dumps(user_info, indent=2, ensure_ascii=False)}")
                else:
                    print(f"❌ 사용자 정보 조회 실패: {user_info_response.status_code}")
                
                # 로그아웃
                logout_response = session.get(f"{base_url}/logout")
                print(f"로그아웃 응답: {logout_response.status_code}")
                
            else:
                print(f"❌ 로그인 실패: {response.text}")
                
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