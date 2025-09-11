#!/usr/bin/env python3
"""
업데이트된 API 키 확인
"""

from api_key_manager_json import get_api_key_manager

def check_updated_keys():
    """업데이트된 API 키 확인"""
    print("🔑 업데이트된 API 키 확인...")
    
    manager = get_api_key_manager()
    api_keys = manager.get_all_api_keys()
    
    print(f"📊 총 API 키 개수: {len(api_keys)}")
    print("\n📋 업데이트된 API 키 목록:")
    
    for key in api_keys:
        site_name = key.get('site_name', 'Unknown')
        api_key = key.get('api_key', 'No Key')
        updated_at = key.get('updated_at', 'Unknown')
        
        print(f"  🏢 {site_name}")
        print(f"     API Key: {api_key[:20]}...")
        print(f"     Updated: {updated_at}")
        print()
    
    print("✅ API 키 확인 완료!")

if __name__ == "__main__":
    check_updated_keys()
