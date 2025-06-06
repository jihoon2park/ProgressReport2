#!/usr/bin/env python3
"""
ClientServiceId 필드를 추가한 Progress Note API 테스트
"""

from api_progressnote import send_specific_progress_note
import json

# ClientServiceId 필드를 추가한 테스트 데이터
test_data = {
    "ClientId": 27,  # MainClientServiceId
    "ClientServiceId": 27,  # API에서 요구하는 ClientServiceId 필드
    "EventDate": "2025-01-27T12:00:00",
    "ProgressNoteEventType": {
        "Id": 3
    },
    "NotesPlainText": "ClientServiceId 필드 추가 테스트 - Mrs Phoebe Smith",
    "CreatedByUser": {
        "FirstName": "Paul",
        "LastName": "Vaska",
        "UserName": "PaulVaska",
        "Position": "GP"
    },
    "CreatedDate": "2025-01-27T12:00:00"
}

try:
    print("ClientServiceId 필드를 추가한 Progress Note API 테스트 중...")
    print(f"ClientId: {test_data['ClientId']}")
    print(f"ClientServiceId: {test_data['ClientServiceId']}")
    
    success, response = send_specific_progress_note(test_data, 'Parafield Gardens')
    
    if success:
        print("✅ Progress Note API 전송 성공!")
        print(f"응답: {json.dumps(response, indent=2, ensure_ascii=False)}")
    else:
        print("❌ Progress Note API 전송 실패")
        print(f"오류: {json.dumps(response, indent=2, ensure_ascii=False)}")
        
except Exception as e:
    print(f"❌ 테스트 중 오류: {e}")
    import traceback
    traceback.print_exc() 