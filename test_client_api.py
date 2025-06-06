#!/usr/bin/env python3
"""
클라이언트 API 응답 구조 확인 스크립트
"""

from api_client import APIClient
import json

try:
    print("Parafield Gardens API 클라이언트 정보 조회 중...")
    client = APIClient('Parafield Gardens')
    response = client.get_client_information()
    
    if response and len(response) > 0:
        print(f"\n총 {len(response)}명의 클라이언트 정보 수신")
        print("\n첫 번째 클라이언트 데이터:")
        print("=" * 50)
        print(json.dumps(response[0], indent=2, ensure_ascii=False))
        
        print("\n사용 가능한 필드들:")
        print("=" * 30)
        for key, value in response[0].items():
            print(f"- {key}: {value} ({type(value).__name__})")
        
        # MainClientServiceId가 있는지 특별히 확인
        if 'MainClientServiceId' in response[0]:
            print(f"\n✅ MainClientServiceId 발견: {response[0]['MainClientServiceId']}")
        else:
            print("\n❌ MainClientServiceId 필드 없음")
            
        # PersonId와 비교
        if 'PersonId' in response[0]:
            print(f"📋 PersonId: {response[0]['PersonId']}")
            
    else:
        print("❌ 클라이언트 정보가 없습니다.")
        
except Exception as e:
    print(f"❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc() 