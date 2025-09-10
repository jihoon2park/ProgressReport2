#!/usr/bin/env python3
"""
FCM 토큰 제거 기능 테스트
"""

import requests
import json

def test_fcm_token_removal():
    """FCM 토큰 제거 테스트"""
    print("🗑️ FCM 토큰 제거 테스트 시작...")
    
    base_url = "http://127.0.0.1:5000"
    
    # 테스트할 토큰 (방금 등록한 토큰 중 하나)
    test_token = "fcm_token_mobile_nurse_001"
    
    try:
        # 1. 제거 전 상태 확인
        print("\n1️⃣ 제거 전 토큰 상태 확인...")
        
        import sqlite3
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, is_active FROM fcm_tokens WHERE token = ?', (test_token,))
        before = cursor.fetchone()
        
        if before:
            print(f"   토큰 발견: {before[0]}, 활성: {bool(before[1])}")
        else:
            print("   토큰을 찾을 수 없음")
            return False
        
        conn.close()
        
        # 2. 토큰 제거 API 호출
        print(f"\n2️⃣ 토큰 제거 API 호출...")
        print(f"   제거할 토큰: {test_token}")
        
        response = requests.post(
            f"{base_url}/api/fcm/unregister-token",
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'token': test_token})
        )
        
        print(f"   응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"   ✅ 제거 성공: {result['message']}")
            else:
                print(f"   ❌ 제거 실패: {result['message']}")
                return False
        else:
            print(f"   ❌ HTTP 오류: {response.text}")
            return False
        
        # 3. 제거 후 상태 확인
        print("\n3️⃣ 제거 후 토큰 상태 확인...")
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, is_active FROM fcm_tokens WHERE token = ?', (test_token,))
        after = cursor.fetchone()
        
        if after:
            print(f"   토큰 상태: {after[0]}, 활성: {bool(after[1])}")
            if not after[1]:
                print("   ✅ 토큰이 성공적으로 비활성화되었습니다!")
            else:
                print("   ❌ 토큰이 여전히 활성 상태입니다.")
                return False
        else:
            print("   토큰이 완전히 삭제되었습니다.")
        
        conn.close()
        
        # 4. 전체 활성 토큰 수 확인
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
        active_count = cursor.fetchone()[0]
        print(f"\n📊 현재 활성 토큰: {active_count}개")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🗑️ FCM Token Remove Test")
    print("=" * 50)
    
    success = test_fcm_token_removal()
    
    if success:
        print("\n🎉 FCM 토큰 제거 테스트 성공!")
        print("이제 FCM Admin Dashboard의 Remove 버튼이 정상 작동합니다.")
    else:
        print("\n❌ FCM 토큰 제거 테스트 실패!")
        exit(1)
