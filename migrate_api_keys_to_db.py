#!/usr/bin/env python3
"""
API 키를 config.py에서 데이터베이스로 마이그레이션하는 스크립트
"""

import sys
import os
from api_key_manager import APIKeyManager

def migrate_api_keys():
    """기존 API 키를 DB로 마이그레이션"""
    
    # 기존 하드코딩된 API 키들
    legacy_api_keys = {
        'Parafield Gardens': {
            'api_username': 'ManadAPI',
            'api_key': 'qPh+xiaSIvRCqQ5nB6gNBQl12IMLFED4C5s/xfjQ88k=',
            'server_ip': '192.168.1.11',
            'server_port': 8080,
            'notes': 'Migrated from config.py'
        },
        'Nerrilda': {
            'api_username': 'ManadAPI',
            'api_key': 'UYlsB9uLJt8pqc+82WKzLYcIH+hxWsF3IJCemHkc77w=',
            'server_ip': '192.168.21.12',
            'server_port': 8080,
            'notes': 'Migrated from config.py'
        },
        'Ramsay': {
            'api_username': 'ManadAPI',
            'api_key': 'DtQEnNJohGnYnzQory++De2NijWqINO+enhDdBNHYTM=',
            'server_ip': '192.168.31.12',
            'server_port': 8080,
            'notes': 'Migrated from config.py'
        },
        'West Park': {
            'api_username': 'ManadAPI',
            'api_key': 'oWhTkk0QwiXk/TWrqDDQNHpC30/htIVqwIZf8Fc+kaw=',
            'server_ip': '192.168.41.12',
            'server_port': 8080,
            'notes': 'Migrated from config.py'
        },
        'Yankalilla': {
            'api_username': 'ManadAPI',
            'api_key': 'RhU1zjQMJs2/BK/USVmVywy5SdimDTm28BRguF70c+I=',
            'server_ip': '192.168.51.12',
            'server_port': 8080,
            'notes': 'Migrated from config.py'
        }
    }
    
    print("🔄 API 키 마이그레이션 시작...")
    
    try:
        # API 키 매니저 초기화
        manager = APIKeyManager()
        
        success_count = 0
        total_count = len(legacy_api_keys)
        
        for site_name, api_data in legacy_api_keys.items():
            print(f"  📝 {site_name} API 키 마이그레이션 중...")
            
            success = manager.add_api_key(
                site_name=site_name,
                api_username=api_data['api_username'],
                api_key=api_data['api_key'],
                server_ip=api_data['server_ip'],
                server_port=api_data['server_port'],
                notes=api_data['notes']
            )
            
            if success:
                success_count += 1
                print(f"    ✅ {site_name} 성공")
            else:
                print(f"    ❌ {site_name} 실패")
        
        print(f"\n📊 마이그레이션 완료: {success_count}/{total_count} 성공")
        
        if success_count == total_count:
            print("🎉 모든 API 키가 성공적으로 마이그레이션되었습니다!")
            print("\n📋 다음 단계:")
            print("1. 서비스 재시작")
            print("2. API 키가 정상 작동하는지 확인")
            print("3. config.py에서 하드코딩된 키 제거 (선택사항)")
            return True
        else:
            print("⚠️ 일부 API 키 마이그레이션이 실패했습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False

def verify_migration():
    """마이그레이션 검증"""
    print("\n🔍 마이그레이션 검증 중...")
    
    try:
        manager = APIKeyManager()
        api_keys = manager.get_all_api_keys()
        
        print(f"  📊 DB에 저장된 API 키 수: {len(api_keys)}")
        
        for api_data in api_keys:
            print(f"  ✅ {api_data['site_name']}: {api_data['server_ip']}:{api_data['server_port']}")
        
        return len(api_keys) > 0
        
    except Exception as e:
        print(f"❌ 검증 실패: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 API 키 DB 마이그레이션 도구")
    print("=" * 60)
    
    # 마이그레이션 실행
    if migrate_api_keys():
        # 검증
        if verify_migration():
            print("\n🎉 마이그레이션이 성공적으로 완료되었습니다!")
            sys.exit(0)
        else:
            print("\n⚠️ 마이그레이션은 완료되었지만 검증에 실패했습니다.")
            sys.exit(1)
    else:
        print("\n❌ 마이그레이션이 실패했습니다.")
        sys.exit(1)
