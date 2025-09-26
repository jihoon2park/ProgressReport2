#!/usr/bin/env python3
"""
JSON 전용 시스템 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from json_data_manager import JSONDataManager
import json

def test_json_system():
    """JSON 시스템 테스트"""
    print("=== JSON 전용 시스템 테스트 ===")
    
    try:
        # JSON 데이터 매니저 초기화
        manager = JSONDataManager()
        print("✅ JSON 데이터 매니저 초기화 성공")
        
        # 시스템 상태 확인
        is_healthy = manager.is_healthy()
        print(f"📊 시스템 상태: {'건강' if is_healthy else '문제 있음'}")
        
        # 통계 정보 조회
        stats = manager.get_statistics()
        print(f"📈 시스템 통계:")
        print(f"   - 총 클라이언트: {stats.get('total_clients', 0)}명")
        print(f"   - 활성 케어 영역: {stats.get('active_care_areas', 0)}개")
        print(f"   - 활성 이벤트 타입: {stats.get('active_event_types', 0)}개")
        print(f"   - 활성 FCM 토큰: {stats.get('active_fcm_tokens', 0)}개")
        
        # 사이트별 클라이언트 조회 테스트
        from config import SITE_SERVERS
        for site in SITE_SERVERS.keys():
            clients = manager.get_clients(site)
            print(f"   - {site}: {len(clients)}명")
        
        # 케어 영역 조회 테스트
        care_areas = manager.get_care_areas()
        print(f"📋 케어 영역: {len(care_areas)}개")
        
        # 이벤트 타입 조회 테스트
        event_types = manager.get_event_types()
        print(f"📋 이벤트 타입: {len(event_types)}개")
        
        print("\n✅ JSON 시스템 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ JSON 시스템 테스트 실패: {e}")
        return False

def test_json_files():
    """JSON 파일 구조 확인"""
    print("\n=== JSON 파일 구조 확인 ===")
    
    data_dir = 'data'
    if not os.path.exists(data_dir):
        print("❌ data 디렉토리가 없습니다.")
        return False
    
    # 필수 파일들 확인
    required_files = ['carearea.json', 'eventtype.json']
    optional_files = ['fcm/tokens.json', 'logs/access_logs.json', 'logs/progress_note_logs.json']
    
    print("📁 필수 파일들:")
    for filename in required_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"   ✅ {filename}: {len(data) if isinstance(data, list) else 'N/A'}개 항목")
            except Exception as e:
                print(f"   ❌ {filename}: 읽기 실패 - {e}")
        else:
            print(f"   ❌ {filename}: 파일 없음")
    
    print("\n📁 선택적 파일들:")
    for filename in optional_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"   ✅ {filename}: {len(data) if isinstance(data, list) else 'N/A'}개 항목")
            except Exception as e:
                print(f"   ❌ {filename}: 읽기 실패 - {e}")
        else:
            print(f"   ⚠️ {filename}: 파일 없음 (정상)")
    
    return True

def main():
    """메인 함수"""
    print("JSON 전용 시스템 테스트")
    print("=" * 50)
    
    # 1. JSON 파일 구조 확인
    test_json_files()
    
    # 2. JSON 시스템 테스트
    test_json_system()
    
    print("\n" + "=" * 50)
    print("테스트 완료!")

if __name__ == "__main__":
    main()
