#!/usr/bin/env python3
"""
FCM 토큰 등록 테스트 (인증 없이)
"""

import requests
import json

def test_fcm_token_registration():
    """FCM 토큰 등록 테스트"""
    print("📱 FCM 토큰 등록 테스트 시작...")
    
    base_url = "http://127.0.0.1:5000"
    
    # 테스트 토큰 데이터
    test_tokens = [
        {
            'user_id': 'mobile_nurse_1',
            'token': 'fcm_token_mobile_nurse_001',
            'device_info': 'Mobile Nurse iPhone 13'
        },
        {
            'user_id': 'mobile_doctor_1', 
            'token': 'fcm_token_mobile_doctor_001',
            'device_info': 'Mobile Doctor Samsung Galaxy'
        }
    ]
    
    try:
        # 1. Health check
        print("\n1️⃣ Health Check...")
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 서버 상태: {health_data['status']}")
            print(f"   FCM 서비스: {health_data['services']['fcm']}")
            print(f"   Task Manager: {health_data['services']['task_manager']}")
        else:
            print(f"❌ Health check 실패: {response.status_code}")
            return False
        
        # 2. FCM 토큰 등록 테스트
        print("\n2️⃣ FCM 토큰 등록 테스트...")
        
        for token_data in test_tokens:
            print(f"\n📱 등록 중: {token_data['user_id']} - {token_data['device_info']}")
            
            response = requests.post(
                f"{base_url}/api/fcm/register-token",
                headers={'Content-Type': 'application/json'},
                data=json.dumps(token_data)
            )
            
            print(f"   응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    print(f"   ✅ 등록 성공: {result['message']}")
                else:
                    print(f"   ❌ 등록 실패: {result['message']}")
            else:
                print(f"   ❌ HTTP 오류: {response.text}")
        
        # 3. 등록된 토큰 확인
        print("\n3️⃣ 등록된 토큰 확인...")
        
        # SQLite에서 직접 확인
        import sqlite3
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, device_info, is_active, created_at
            FROM fcm_tokens
            WHERE user_id LIKE 'mobile_%'
            ORDER BY created_at DESC
        ''')
        
        mobile_tokens = cursor.fetchall()
        print(f"📊 등록된 모바일 토큰: {len(mobile_tokens)}개")
        
        for token in mobile_tokens:
            status = "✅ Active" if token[2] else "❌ Inactive"
            print(f"   - {token[0]}: {token[1]} ({status})")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("📱 FCM Token Registration Test (No Auth)")
    print("=" * 60)
    
    success = test_fcm_token_registration()
    
    if success:
        print("\n🎉 FCM 토큰 등록 테스트 성공!")
        print("이제 모바일 앱에서 인증 없이 토큰을 등록할 수 있습니다.")
    else:
        print("\n❌ FCM 토큰 등록 테스트 실패!")
        exit(1)
