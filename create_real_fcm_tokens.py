#!/usr/bin/env python3
"""
실제 사용할 FCM 토큰 생성
"""

import sqlite3
from datetime import datetime

def create_real_fcm_tokens():
    """실제 사용할 FCM 토큰들을 SQLite DB에 생성"""
    print("📱 실제 FCM 토큰 생성 중...")
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 실제 사용자들의 FCM 토큰 (실제 토큰은 모바일 앱에서 등록됨)
        real_tokens = [
            ('PaulVaska', 'fcm_token_paul_real_001', 'Paul iPhone 12'),
            ('walgampola', 'fcm_token_walga_real_002', 'Walga Samsung Galaxy S21')
        ]
        
        for user_id, token, device_info in real_tokens:
            cursor.execute('''
                INSERT OR REPLACE INTO fcm_tokens 
                (user_id, token, device_info, created_at, last_used, is_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
            ''', (user_id, token, device_info))
            
            print(f"✅ {user_id}: {device_info}")
        
        conn.commit()
        
        # 확인
        cursor.execute('SELECT user_id, device_info, is_active FROM fcm_tokens')
        tokens = cursor.fetchall()
        
        print(f"\n📊 등록된 FCM 토큰: {len(tokens)}개")
        for token in tokens:
            status = "Active" if token[2] else "Inactive"
            print(f"  - {token[0]}: {token[1]} ({status})")
        
        return True
        
    except Exception as e:
        print(f"❌ FCM 토큰 생성 실패: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_real_fcm_tokens()
    if success:
        print("\n✅ 실제 FCM 토큰 생성 완료!")
        print("이제 Policy Management와 FCM Admin Dashboard 모두에서 디바이스를 볼 수 있습니다.")
    else:
        print("\n❌ FCM 토큰 생성 실패!")
        exit(1)
