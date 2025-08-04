#!/usr/bin/env python3
"""
API 데이터 확인 스크립트
"""

from api_client import fetch_client_information
import json

def check_api_data():
    print("=== API 데이터 확인 ===")
    
    site = "Parafield Gardens"
    
    # API에서 클라이언트 데이터 가져오기
    print(f"1. {site} API에서 클라이언트 데이터 가져오기...")
    success, client_data = fetch_client_information(site)
    
    if success and client_data:
        print(f"✅ API에서 {len(client_data)}개의 클라이언트 데이터 가져옴")
        
        # Barrie McAskill 찾기
        barrie_found = False
        for client in client_data:
            if isinstance(client, dict):
                first_name = client.get('FirstName', '')
                surname = client.get('Surname', '')
                last_name = client.get('LastName', '')
                
                # Barrie McAskill 확인
                if 'Barrie' in first_name and 'McAskill' in surname:
                    barrie_found = True
                    print(f"✅ API에서 Barrie McAskill 발견!")
                    print(f"  - FirstName: {first_name}")
                    print(f"  - Surname: {surname}")
                    print(f"  - LastName: {last_name}")
                    print(f"  - MainClientServiceId: {client.get('MainClientServiceId')}")
                    print(f"  - WingName: {client.get('WingName')}")
                    break
        
        if not barrie_found:
            print("❌ API에서 Barrie McAskill을 찾을 수 없습니다")
            
            # 모든 클라이언트 이름 출력 (디버깅용)
            print("\nAPI에서 가져온 모든 클라이언트:")
            for i, client in enumerate(client_data[:20]):  # 처음 20개만 출력
                if isinstance(client, dict):
                    first_name = client.get('FirstName', '')
                    surname = client.get('Surname', '')
                    last_name = client.get('LastName', '')
                    name = f"{first_name} {surname}".strip() or f"{first_name} {last_name}".strip() or first_name
                    print(f"  {i+1}. {name}")
            
            if len(client_data) > 20:
                print(f"  ... (총 {len(client_data)}개 중 처음 20개만 표시)")
        
        # Client_list.json과 비교
        print(f"\n2. Client_list.json과 비교...")
        try:
            with open('data/Client_list.json', 'r', encoding='utf-8') as f:
                client_list = json.load(f)
            
            print(f"Client_list.json에서 {len(client_list)}개의 클라이언트")
            
            # Client_list.json에서 Barrie McAskill 찾기
            barrie_in_list = None
            for client in client_list:
                if client.get('PersonId') == 1538:
                    barrie_in_list = client
                    break
            
            if barrie_in_list:
                print(f"✅ Client_list.json에서 Barrie McAskill 발견")
                print(f"  - ClientName: {barrie_in_list.get('ClientName')}")
                print(f"  - MainClientServiceId: {barrie_in_list.get('MainClientServiceId')}")
            else:
                print("❌ Client_list.json에서 Barrie McAskill을 찾을 수 없습니다")
            
            # API와 Client_list.json의 차이점 확인
            api_ids = set()
            for client in client_data:
                if isinstance(client, dict):
                    client_id = client.get('MainClientServiceId')
                    if client_id:
                        api_ids.add(client_id)
            
            list_ids = set()
            for client in client_list:
                client_id = client.get('MainClientServiceId')
                if client_id:
                    list_ids.add(client_id)
            
            print(f"\n3. 데이터 비교:")
            print(f"  API 클라이언트 수: {len(api_ids)}")
            print(f"  Client_list.json 클라이언트 수: {len(list_ids)}")
            print(f"  API에만 있는 클라이언트: {len(api_ids - list_ids)}")
            print(f"  Client_list.json에만 있는 클라이언트: {len(list_ids - api_ids)}")
            
            if 1538 in (list_ids - api_ids):
                print("❌ Barrie McAskill (ID: 1538)이 API에는 없지만 Client_list.json에는 있습니다!")
            
        except Exception as e:
            print(f"❌ Client_list.json 읽기 실패: {str(e)}")
            
    else:
        print("❌ API에서 클라이언트 데이터 가져오기 실패")

if __name__ == "__main__":
    check_api_data() 