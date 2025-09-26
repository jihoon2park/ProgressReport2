#!/usr/bin/env python3
"""
app.py JSON 전용 시스템 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_app_imports():
    """app.py import 테스트"""
    print("=== app.py Import 테스트 ===")
    
    try:
        # JSON 데이터 매니저 import 테스트
        from json_data_manager import JSONDataManager
        print("✅ JSONDataManager import 성공")
        
        # JSON 매니저 초기화
        manager = JSONDataManager()
        print("✅ JSONDataManager 초기화 성공")
        
        # 시스템 상태 확인
        is_healthy = manager.is_healthy()
        print(f"📊 시스템 상태: {'건강' if is_healthy else '문제 있음'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import 테스트 실패: {e}")
        return False

def test_app_basic_functions():
    """app.py 기본 함수 테스트"""
    print("\n=== app.py 기본 함수 테스트 ===")
    
    try:
        # app.py의 기본 함수들 테스트
        from json_data_manager import JSONDataManager
        
        manager = JSONDataManager()
        
        # 케어 영역 조회
        care_areas = manager.get_care_areas()
        print(f"📋 케어 영역: {len(care_areas)}개")
        
        # 이벤트 타입 조회
        event_types = manager.get_event_types()
        print(f"📋 이벤트 타입: {len(event_types)}개")
        
        # FCM 토큰 조회
        fcm_tokens = manager.get_fcm_tokens()
        print(f"📱 FCM 토큰: {len(fcm_tokens)}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 기본 함수 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("app.py JSON 전용 시스템 테스트")
    print("=" * 50)
    
    # 1. Import 테스트
    test_app_imports()
    
    # 2. 기본 함수 테스트
    test_app_basic_functions()
    
    print("\n" + "=" * 50)
    print("테스트 완료!")

if __name__ == "__main__":
    main()
