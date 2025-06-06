#!/usr/bin/env python3
"""
클라이언트 정보를 새로 가져와서 Client_list.json 업데이트
"""

from app import fetch_client_information
import json

try:
    print("Parafield Gardens 클라이언트 정보 업데이트 중...")
    
    success, client_info = fetch_client_information('Parafield Gardens')
    
    if success:
        print("✅ 클라이언트 정보 업데이트 완료!")
        
        # 업데이트된 파일 확인
        with open('data/Client_list.json', 'r', encoding='utf-8') as f:
            updated_clients = json.load(f)
        
        print(f"📊 총 {len(updated_clients)}명의 클라이언트 정보")
        
        # 처음 3명의 정보 확인
        print("\n처음 3명의 클라이언트 정보:")
        for i, client in enumerate(updated_clients[:3]):
            print(f"\n{i+1}. {client['ClientName']}")
            print(f"   PersonId (MainClientServiceId): {client['PersonId']}")
            print(f"   MainClientServiceId: {client.get('MainClientServiceId', 'N/A')}")
            print(f"   OriginalPersonId: {client.get('OriginalPersonId', 'N/A')}")
            print(f"   Room: {client.get('RoomName', 'N/A')}")
        
        # 27번 ID 확인 (테스트에서 본 MainClientServiceId)
        client_27 = next((c for c in updated_clients if c['PersonId'] == 27), None)
        if client_27:
            print(f"\n🎯 MainClientServiceId 27번 클라이언트 발견:")
            print(f"   이름: {client_27['ClientName']}")
            print(f"   PersonId: {client_27['PersonId']}")
            print(f"   방: {client_27['RoomName']}")
        else:
            print("\n❌ MainClientServiceId 27번 클라이언트를 찾을 수 없습니다.")
            
    else:
        print("❌ 클라이언트 정보 업데이트 실패")
        
except Exception as e:
    print(f"❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc() 