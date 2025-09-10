#!/usr/bin/env python3
"""
FCM 토큰 데이터를 JSON 파일에서 SQLite DB로 마이그레이션
"""

import json
import sqlite3
import os
from datetime import datetime

def migrate_fcm_tokens_to_sqlite():
    """JSON 파일의 FCM 토큰을 SQLite DB로 마이그레이션"""
    print("🔄 FCM 토큰 마이그레이션 시작...")
    
    json_file_path = "credential/fcm_tokens.json"
    
    # 1. 기존 JSON 파일 확인
    if os.path.exists(json_file_path):
        print(f"📄 기존 JSON 파일 발견: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            print(f"JSON 파일 형태: {type(json_data)}")
            
            # JSON 데이터 구조 확인
            if isinstance(json_data, dict):
                # 딕셔너리 형태: {user_id: [tokens]}
                print("JSON 형태: 사용자별 토큰 딕셔너리")
                token_count = sum(len(tokens) for tokens in json_data.values())
                print(f"총 {len(json_data)}명 사용자, {token_count}개 토큰")
            elif isinstance(json_data, list):
                # 리스트 형태: [token_objects]
                print("JSON 형태: 토큰 객체 리스트")
                print(f"총 {len(json_data)}개 토큰")
            else:
                print(f"알 수 없는 JSON 형태: {type(json_data)}")
                return False
                
        except Exception as e:
            print(f"❌ JSON 파일 읽기 실패: {e}")
            return False
    else:
        print("📄 기존 JSON 파일이 없습니다. 빈 DB로 시작합니다.")
        json_data = {}
    
    # 2. SQLite DB 연결
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 기존 SQLite 데이터 확인
        cursor.execute('SELECT COUNT(*) FROM fcm_tokens')
        existing_count = cursor.fetchone()[0]
        print(f"📊 기존 SQLite DB 토큰: {existing_count}개")
        
        if existing_count > 0:
            print("⚠️ SQLite DB에 기존 토큰이 있습니다. 백업 후 진행...")
            
            # 기존 데이터 백업
            cursor.execute('SELECT * FROM fcm_tokens')
            backup_data = cursor.fetchall()
            
            backup_file = f"fcm_tokens_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump([{
                    'id': row[0], 'user_id': row[1], 'token': row[2],
                    'device_info': row[3], 'created_at': row[4],
                    'last_used': row[5], 'is_active': bool(row[6])
                } for row in backup_data], f, indent=2, default=str)
            
            print(f"✅ 기존 데이터 백업: {backup_file}")
        
        # 기존 데이터 삭제
        cursor.execute('DELETE FROM fcm_tokens')
        print("🗑️ 기존 SQLite 데이터 삭제")
        
        # 3. JSON 데이터를 SQLite로 마이그레이션
        migrated_count = 0
        
        if json_data:
            if isinstance(json_data, dict):
                # 딕셔너리 형태 처리
                for user_id, user_tokens in json_data.items():
                    if isinstance(user_tokens, list):
                        for token_info in user_tokens:
                            cursor.execute('''
                                INSERT OR REPLACE INTO fcm_tokens 
                                (user_id, token, device_info, created_at, last_used, is_active)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                user_id,
                                token_info.get('token', ''),
                                token_info.get('device_info', 'Unknown Device'),
                                token_info.get('created_at', datetime.now().isoformat()),
                                token_info.get('last_used', datetime.now().isoformat()),
                                token_info.get('is_active', True)
                            ))
                            migrated_count += 1
            
            elif isinstance(json_data, list):
                # 리스트 형태 처리
                for token_info in json_data:
                    cursor.execute('''
                        INSERT OR REPLACE INTO fcm_tokens 
                        (user_id, token, device_info, created_at, last_used, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        token_info.get('user_id', 'unknown'),
                        token_info.get('token', ''),
                        token_info.get('device_info', 'Unknown Device'),
                        token_info.get('created_at', datetime.now().isoformat()),
                        token_info.get('last_used', datetime.now().isoformat()),
                        token_info.get('is_active', True)
                    ))
                    migrated_count += 1
        
        conn.commit()
        
        # 4. 마이그레이션 결과 확인
        cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
        final_count = cursor.fetchone()[0]
        
        print(f"\n✅ 마이그레이션 완료!")
        print(f"  - 마이그레이션된 토큰: {migrated_count}개")
        print(f"  - SQLite DB 활성 토큰: {final_count}개")
        
        # 최종 토큰 목록 표시
        cursor.execute('''
            SELECT user_id, device_info, created_at, is_active
            FROM fcm_tokens
            ORDER BY created_at
        ''')
        
        final_tokens = cursor.fetchall()
        print(f"\n📱 최종 FCM 디바이스 목록:")
        for token in final_tokens:
            status = "✅ Active" if token[3] else "❌ Inactive"
            print(f"  - {token[0]}: {token[1]} ({status})")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 FCM Token Migration: JSON → SQLite DB")
    print("=" * 60)
    
    success = migrate_fcm_tokens_to_sqlite()
    
    if success:
        print("\n🎉 마이그레이션 성공!")
        print("이제 FCM 토큰 매니저를 SQLite 기반으로 수정해야 합니다.")
    else:
        print("\n❌ 마이그레이션 실패!")
        exit(1)
