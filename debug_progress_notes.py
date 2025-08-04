#!/usr/bin/env python3
"""
Progress Notes 디버그 스크립트 - Barrie McAskill 문제 진단
"""

from datetime import datetime
from api_progressnote_fetch import ProgressNoteFetchClient, find_resident_of_day_event_types, fetch_event_types_for_site
import json

def debug_progress_notes():
    print("=== Progress Notes 디버그 - Barrie McAskill 문제 진단 ===")
    
    site = "Parafield Gardens"
    year, month = 2025, 7
    
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
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    print(f"\n2. 날짜 범위: {start_date} ~ {end_date}")
    
    # 3. 각 EventType별로 노트 가져오기
    client = ProgressNoteFetchClient(site)
    
    all_notes = []
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
            all_notes.extend(notes)
            
            # Barrie McAskill 관련 노트 찾기 (ClientServiceId: 1538)
            barrie_notes = []
            for note in notes:
                client_service_id = note.get('ClientServiceId')
                if client_service_id == 1538:  # Barrie McAskill의 MainClientServiceId
                    barrie_notes.append(note)
            
            if barrie_notes:
                print(f"✅ Barrie McAskill {event_type_name} 노트 {len(barrie_notes)}개 발견")
                for i, note in enumerate(barrie_notes):
                    print(f"  노트 {i+1}: ID={note.get('Id')}, EventDate={note.get('EventDate')}")
                    print(f"    - ClientServiceId: {note.get('ClientServiceId')}")
                    print(f"    - NotesDetailTitle: {note.get('NotesDetailTitle', 'N/A')}")
                    print(f"    - NotesPlainText: {note.get('NotesPlainText', 'N/A')[:100]}...")
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
    
    # 4. 클라이언트 데이터 확인
    print(f"\n4. 클라이언트 데이터 확인...")
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
            
            # Barrie McAskill의 노트가 있는지 확인
            barrie_client_service_id = barrie_client.get('MainClientServiceId')
            barrie_notes_found = []
            
            for note in all_notes:
                if note.get('ClientServiceId') == barrie_client_service_id:
                    barrie_notes_found.append(note)
            
            if barrie_notes_found:
                print(f"✅ Barrie McAskill 노트 {len(barrie_notes_found)}개 발견")
                for i, note in enumerate(barrie_notes_found):
                    print(f"  노트 {i+1}: ID={note.get('Id')}, EventDate={note.get('EventDate')}")
            else:
                print(f"❌ Barrie McAskill 노트 없음 - 매칭 실패 또는 노트 누락")
                
        else:
            print("❌ Barrie McAskill 클라이언트 정보 없음")
            
    except Exception as e:
        print(f"❌ Client_list.json 읽기 실패: {str(e)}")
    
    # 5. 전체 노트 분석
    print(f"\n5. 전체 노트 분석...")
    print(f"총 노트 수: {len(all_notes)}")
    
    # ClientServiceId별 노트 수
    client_service_counts = {}
    for note in all_notes:
        client_service_id = note.get('ClientServiceId')
        if client_service_id:
            client_service_counts[client_service_id] = client_service_counts.get(client_service_id, 0) + 1
    
    print(f"노트가 있는 클라이언트 수: {len(client_service_counts)}")
    print(f"ClientServiceId별 노트 수 (상위 10개):")
    sorted_counts = sorted(client_service_counts.items(), key=lambda x: x[1], reverse=True)
    for client_id, count in sorted_counts[:10]:
        print(f"  - ClientServiceId {client_id}: {count}개 노트")

if __name__ == "__main__":
    debug_progress_notes() 