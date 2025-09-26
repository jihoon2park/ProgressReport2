#!/usr/bin/env python3
"""
사이트별 Event Type 로딩 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_eventtype import get_site_event_types
import json

def test_site_eventtype_loading():
    """사이트별 Event Type 로딩 테스트"""
    print("=== 사이트별 Event Type 로딩 테스트 ===")
    
    from config import SITE_SERVERS
    
    for site in SITE_SERVERS.keys():
        print(f"\n사이트: {site}")
        print("-" * 40)
        
        try:
            event_types = get_site_event_types(site)
            
            if event_types:
                print(f"✅ {len(event_types)}개 Event Type 로드 성공")
                
                # Resident of the day 이벤트 타입 찾기
                rod_types = [et for et in event_types if 'resident of the day' in et.get('Description', '').lower()]
                print(f"📋 Resident of the day 이벤트 타입: {len(rod_types)}개")
                for rod_type in rod_types:
                    print(f"   - {rod_type.get('Description')} (ID: {rod_type.get('Id')})")
                
                # 첫 번째 이벤트 타입 정보
                if event_types:
                    first_event = event_types[0]
                    print(f"📋 첫 번째 Event Type: {first_event.get('Description')} (ID: {first_event.get('Id')})")
            else:
                print("❌ Event Type 로드 실패 또는 데이터 없음")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

def test_json_file_structure():
    """JSON 파일 구조 확인"""
    print("\n=== JSON 파일 구조 확인 ===")
    
    from config import SITE_SERVERS
    
    for site in SITE_SERVERS.keys():
        safe_site_name = site.replace(' ', '_').replace('/', '_')
        filename = f'data/eventtype_{safe_site_name}.json'
        
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"\n📄 {filename}:")
                print(f"   - 타입: {type(data).__name__}")
                if isinstance(data, list):
                    print(f"   - 개수: {len(data)}개")
                    if data:
                        print(f"   - 첫 번째 항목 키: {list(data[0].keys())}")
                else:
                    print(f"   - 키: {list(data.keys())}")
                    
            except Exception as e:
                print(f"❌ {filename} 읽기 실패: {e}")
        else:
            print(f"❌ {filename} 파일 없음")

def main():
    """메인 함수"""
    print("사이트별 Event Type 로딩 시스템 테스트")
    print("=" * 60)
    
    # 1. JSON 파일 구조 확인
    test_json_file_structure()
    
    # 2. 사이트별 Event Type 로딩 테스트
    test_site_eventtype_loading()
    
    print("\n" + "=" * 60)
    print("테스트 완료!")

if __name__ == "__main__":
    main()
