#!/usr/bin/env python3
"""
FCM 테스트 데이터 생성 스크립트
Policy Management에서 디바이스 목록을 볼 수 있도록 테스트 데이터 생성
"""

import sqlite3
import json
from datetime import datetime

def create_test_fcm_data():
    """테스트용 FCM 토큰 데이터 생성"""
    print("🔥 FCM 테스트 데이터 생성 중...")
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 기존 FCM 토큰 확인
        cursor.execute("SELECT COUNT(*) FROM fcm_tokens")
        token_count = cursor.fetchone()[0]
        print(f"현재 FCM 토큰 개수: {token_count}")
        
        if token_count == 0:
            print("📱 테스트용 FCM 토큰 생성...")
            
            # 테스트 토큰 데이터
            test_tokens = [
                ('admin', 'test_token_admin_001', 'Admin iPhone 12'),
                ('PaulVaska', 'test_token_paul_002', 'Paul Samsung Galaxy S21'),
                ('walgampola', 'test_token_walga_003', 'Walga iPad Pro'),
                ('ROD', 'test_token_rod_004', 'ROD Android Tablet'),
                ('test_nurse_1', 'test_token_nurse1_005', 'Nurse 1 iPhone 13'),
                ('test_nurse_2', 'test_token_nurse2_006', 'Nurse 2 Samsung Galaxy'),
                ('test_doctor', 'test_token_doctor_007', 'Doctor iPhone 14'),
                ('test_manager', 'test_token_manager_008', 'Manager iPad')
            ]
            
            for user_id, token, device_info in test_tokens:
                cursor.execute('''
                    INSERT OR IGNORE INTO fcm_tokens 
                    (user_id, token, device_info, created_at, last_used, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (user_id, token, device_info, datetime.now(), datetime.now()))
            
            print(f"✅ {len(test_tokens)}개 테스트 토큰 생성")
        
        # credential/fcm_tokens.json 파일도 생성 (export-tokens API용)
        print("\n📄 credential/fcm_tokens.json 파일 생성...")
        
        # 현재 DB의 모든 토큰 조회
        cursor.execute('''
            SELECT user_id, token, device_info, created_at, last_used, is_active
            FROM fcm_tokens
            ORDER BY created_at DESC
        ''')
        
        all_tokens = cursor.fetchall()
        
        # JSON 형태로 변환
        tokens_data = []
        for token_row in all_tokens:
            tokens_data.append({
                'user_id': token_row[0],
                'token': token_row[1],
                'device_info': token_row[2],
                'created_at': token_row[3],
                'last_used': token_row[4],
                'is_active': bool(token_row[5])
            })
        
        # credential 디렉토리 확인
        import os
        os.makedirs('credential', exist_ok=True)
        
        # fcm_tokens.json 파일 생성
        with open('credential/fcm_tokens.json', 'w', encoding='utf-8') as f:
            json.dump(tokens_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ credential/fcm_tokens.json 파일 생성 완료 ({len(tokens_data)}개 토큰)")
        
        conn.commit()
        
        # 확인
        cursor.execute("SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1")
        active_count = cursor.fetchone()[0]
        
        print(f"\n📊 FCM 토큰 상태:")
        print(f"  - 총 토큰: {len(all_tokens)}개")
        print(f"  - 활성 토큰: {active_count}개")
        print(f"  - JSON 파일: credential/fcm_tokens.json")
        
        return True
        
    except Exception as e:
        print(f"❌ FCM 데이터 생성 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def test_fcm_api():
    """FCM API 테스트"""
    print("\n🧪 FCM API 테스트...")
    
    try:
        import requests
        
        # Health check
        response = requests.get('http://127.0.0.1:5000/api/health')
        if response.status_code == 200:
            print("✅ Health API 작동 확인")
        else:
            print(f"⚠️ Health API 응답: {response.status_code}")
        
        # FCM export-tokens API 테스트 (로그인 필요하므로 세션 사용)
        print("📱 FCM export-tokens API는 로그인이 필요합니다.")
        print("브라우저에서 http://127.0.0.1:5000/policy-management 접속하여 확인하세요.")
        
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 FCM Test Data Creation")
    print("=" * 60)
    
    success = create_test_fcm_data()
    
    if success:
        test_fcm_api()
        print("\n🎉 FCM 테스트 데이터 생성 완료!")
        print("브라우저에서 Policy Management 페이지를 새로고침하세요.")
    else:
        print("\n❌ FCM 데이터 생성 실패!")
        exit(1)
