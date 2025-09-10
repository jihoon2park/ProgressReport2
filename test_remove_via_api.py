#!/usr/bin/env python3
"""
실제 존재하는 토큰으로 제거 테스트
"""

import sqlite3
import requests
import json

def test_remove_existing_token():
    """실제 존재하는 토큰으로 제거 테스트"""
    print("🗑️ 실제 토큰 제거 테스트...")
    
    # 1. 현재 토큰 목록 확인
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, token, device_info FROM fcm_tokens WHERE is_active = 1 LIMIT 1')
    token_info = cursor.fetchone()
    
    if not token_info:
        print("❌ 활성 토큰이 없습니다.")
        return False
    
    user_id, token, device_info = token_info
    print(f"📱 테스트 대상 토큰:")
    print(f"   사용자: {user_id}")
    print(f"   디바이스: {device_info}")
    print(f"   토큰: {token[:20]}...")
    
    conn.close()
    
    # 2. API를 통해 제거
    try:
        print(f"\n🔥 토큰 제거 API 호출...")
        
        response = requests.post(
            "http://127.0.0.1:5000/api/fcm/unregister-token",
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'token': token})
        )
        
        print(f"응답 코드: {response.status_code}")
        result = response.json()
        print(f"응답 내용: {result}")
        
        if response.status_code == 200 and result['success']:
            print("✅ 토큰 제거 성공!")
            
            # 3. 제거 후 확인
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT is_active FROM fcm_tokens WHERE token = ?', (token,))
            after = cursor.fetchone()
            
            if after and not after[0]:
                print("✅ 토큰이 비활성화되었습니다!")
            else:
                print("❌ 토큰이 여전히 활성 상태입니다.")
            
            conn.close()
            return True
            
        else:
            print(f"❌ 토큰 제거 실패: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_remove_existing_token()
