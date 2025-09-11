#!/usr/bin/env python3
"""
API 키 테스트 스크립트
"""

from api_key_manager_json import get_api_key_manager

def test_api_keys():
    """API 키 테스트"""
    print("🔑 API 키 테스트 시작...")
    
    try:
        manager = get_api_key_manager()
        api_keys = manager.get_all_api_keys()
        
        print(f"📊 총 API 키 개수: {len(api_keys)}")
        print("\n📋 API 키 목록:")
        
        for key in api_keys:
            site_name = key.get('site_name', 'Unknown')
            api_key = key.get('api_key', 'No Key')
            server_url = key.get('server_url', 'No URL')
            
            print(f"  🏢 {site_name}")
            print(f"     API Key: {api_key[:20]}...")
            print(f"     Server: {server_url}")
            print()
        
        # 각 사이트별 API 헤더 테스트
        print("🧪 API 헤더 테스트:")
        for key in api_keys:
            site_name = key.get('site_name')
            if site_name:
                headers = manager.get_api_headers(site_name)
                server_info = manager.get_server_info(site_name)
                
                print(f"  📡 {site_name}:")
                print(f"     Headers: {headers}")
                print(f"     Server Info: {server_info}")
                print()
        
        print("✅ API 키 테스트 완료!")
        
    except Exception as e:
        print(f"❌ API 키 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_keys()
