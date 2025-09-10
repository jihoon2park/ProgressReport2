#!/usr/bin/env python3
"""
원본 FCM 토큰 데이터 확인 및 정리
"""

import sqlite3
from datetime import datetime

def check_and_cleanup_fcm_tokens():
    """FCM 토큰 데이터 확인 및 테스트 데이터 정리"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        print("🔍 현재 FCM 토큰 상태 확인...")
        
        # 모든 토큰 조회
        cursor.execute('''
            SELECT user_id, token, device_info, created_at, last_used, is_active
            FROM fcm_tokens
            ORDER BY created_at
        ''')
        
        all_tokens = cursor.fetchall()
        print(f"총 FCM 토큰 개수: {len(all_tokens)}")
        
        # 원본 토큰과 테스트 토큰 구분
        original_tokens = []
        test_tokens = []
        
        for token in all_tokens:
            user_id, token_value, device_info, created_at, last_used, is_active = token
            
            if token_value.startswith('test_token_'):
                test_tokens.append(token)
            else:
                original_tokens.append(token)
        
        print(f"\n📱 원본 FCM 토큰: {len(original_tokens)}개")
        for token in original_tokens:
            print(f"  - {token[0]}: {token[2]} (토큰: {token[1][:20]}...)")
        
        print(f"\n🧪 테스트 FCM 토큰: {len(test_tokens)}개")
        for token in test_tokens:
            print(f"  - {token[0]}: {token[2]}")
        
        # 테스트 토큰 삭제 여부 확인
        if test_tokens:
            print(f"\n🗑️ {len(test_tokens)}개 테스트 토큰 삭제 중...")
            cursor.execute("DELETE FROM fcm_tokens WHERE token LIKE 'test_token_%'")
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"✅ {deleted_count}개 테스트 토큰 삭제 완료")
        
        # 최종 상태 확인
        cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
        active_count = cursor.fetchone()[0]
        
        print(f"\n📊 최종 FCM 토큰 상태:")
        print(f"  - 활성 토큰: {active_count}개")
        
        # 원본 토큰들 다시 조회
        cursor.execute('''
            SELECT user_id, device_info, created_at, is_active
            FROM fcm_tokens
            ORDER BY created_at
        ''')
        
        final_tokens = cursor.fetchall()
        print(f"\n📱 최종 FCM 디바이스 목록:")
        for token in final_tokens:
            status = "Active" if token[3] else "Inactive"
            print(f"  - User: {token[0]}")
            print(f"    Device: {token[1]}")
            print(f"    Registered: {token[2]}")
            print(f"    Status: {status}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ FCM 토큰 확인 실패: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Original FCM Token Check")
    print("=" * 50)
    
    success = check_and_cleanup_fcm_tokens()
    
    if success:
        print("✅ FCM 토큰 확인 완료!")
        print("이제 Policy Management에서 디바이스 목록을 확인할 수 있습니다.")
    else:
        print("❌ FCM 토큰 확인 실패!")
        exit(1)
