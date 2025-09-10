#!/usr/bin/env python3
"""
현재 FCM 토큰 상태 확인
"""

import sqlite3

def check_current_fcm_tokens():
    """현재 FCM 토큰 상태 확인"""
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT user_id, device_info, is_active, created_at
            FROM fcm_tokens
            ORDER BY created_at
        ''')
        
        tokens = cursor.fetchall()
        
        print(f"📊 총 FCM 토큰: {len(tokens)}개")
        print("\n📱 등록된 디바이스:")
        
        for token in tokens:
            status = "✅ Active" if token[2] else "❌ Inactive"
            print(f"  - {token[0]}: {token[1]} ({status})")
            print(f"    등록 시간: {token[3]}")
        
        # 활성 토큰만 카운트
        cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
        active_count = cursor.fetchone()[0]
        
        print(f"\n📈 활성 토큰: {active_count}개")
        
        return tokens
        
    except Exception as e:
        print(f"❌ 토큰 확인 실패: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    check_current_fcm_tokens()
