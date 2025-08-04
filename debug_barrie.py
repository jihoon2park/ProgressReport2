#!/usr/bin/env python3
"""
Barrie McAskill 디버그 스크립트
"""

import json
from datetime import datetime
from api_progressnote_fetch import ProgressNoteFetchClient, find_resident_of_day_event_types, fetch_event_types_for_site

def debug_barrie_mcaskill():
    print("=== Barrie McAskill 디버그 ===")
    
    site = "Parafield Gardens"
    
    # 1. EventType 확인
    print("1. EventType 확인...")
    event_success, event_types = fetch_event_types_for_site(site)
    if event_success and event_types:
        print(f"EventType 개수: {len(event_types)}")
        rn_en_id, pca_id = find_resident_of_day_event_types(event_types)
        print(f"RN/EN EventType ID: {rn_en_id}")
        print(f"PCA EventType ID: {pca_id}")
        
        # Resident of the day 관련 EventType 출력
        for event_type in event_types:
            desc = event_type.get('Description', '').lower()
            if 'resident of the day' in desc:
                print(f"  - ID: {event_type.get('Id')}, Description: {event_type.get('Description')}")
    else:
        print("❌ EventType 가져오기 실패")
        return
    
    # 2. 날짜 범위 설정
    year, month = 2025, 7
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    print(f"\n2. 날짜 범위: {start_date} ~ {end_date}")
    
    # 3. 각 EventType별로 노트 가져오기
    client = ProgressNoteFetchClient(site)
    
    for event_type_id, event_type_name in [(rn_en_id, "RN/EN"), (pca_id, "PCA")]:
        if event_type_id is None:
            print(f"\n❌ {event_type_name} EventType ID가 없습니다")
            continue
            
        print(f"\n3. {event_type_name} 노트 가져오기 (EventType ID: {event_type_id})...")
        
        success, notes = client.fetch_progress_notes(
            start_date=start_date,
            end_date=end_date,
            limit=None,
            progress_note_event_type_id=event_type_id
        )
        
        if success and notes:
            print(f"✅ {event_type_name} 노트 {len(notes)}개 발견")
            
            # Barrie McAskill 관련 노트 찾기
            barrie_notes = []
            for note in notes:
                client_service_id = note.get('ClientServiceId')
                if client_service_id == 1538:  # Barrie McAskill의 MainClientServiceId
                    barrie_notes.append(note)
            
            if barrie_notes:
                print(f"✅ Barrie McAskill {event_type_name} 노트 {len(barrie_notes)}개 발견")
                for i, note in enumerate(barrie_notes):
                    print(f"  노트 {i+1}: ID={note.get('Id')}, EventDate={note.get('EventDate')}")
            else:
                print(f"❌ Barrie McAskill {event_type_name} 노트 없음")
                
            # 모든 노트의 ClientServiceId 확인
            client_service_ids = set()
            for note in notes:
                client_service_id = note.get('ClientServiceId')
                if client_service_id:
                    client_service_ids.add(client_service_id)
            
            print(f"발견된 ClientServiceId들: {sorted(client_service_ids)}")
            
        else:
            print(f"❌ {event_type_name} 노트 가져오기 실패")
    
    # 4. Client_list.json에서 Barrie McAskill 정보 확인
    print(f"\n4. Client_list.json에서 Barrie McAskill 정보 확인...")
    try:
        with open('data/Client_list.json', 'r', encoding='utf-8') as f:
            clients = json.load(f)
        
        barrie_client = None
        for client in clients:
            if client.get('PersonId') == 1538:
                barrie_client = client
                break
        
        if barrie_client:
            print(f"✅ Barrie McAskill 클라이언트 정보 발견")
            print(f"  - ClientName: {barrie_client.get('ClientName')}")
            print(f"  - MainClientServiceId: {barrie_client.get('MainClientServiceId')}")
            print(f"  - WingName: {barrie_client.get('WingName')}")
        else:
            print("❌ Barrie McAskill 클라이언트 정보 없음")
            
    except Exception as e:
        print(f"❌ Client_list.json 읽기 실패: {str(e)}")

if __name__ == "__main__":
    debug_barrie_mcaskill() 