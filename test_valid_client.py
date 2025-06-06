#!/usr/bin/env python3
"""
유효한 ClientId로 Progress Note API 테스트
"""

from api_progressnote import send_specific_progress_note
import json

# 유효한 테스트 데이터 (MainClientServiceId 27 사용)
test_data = {
    "ClientId": 27,  # MainClientServiceId
    "EventDate": "2025-01-27T12:00:00",
    "ProgressNoteEventType": {
        "Id": 3
    },
    "NotesPlainText": "Valid ClientId 테스트 - Mrs Phoebe Smith (MainClientServiceId: 27)",
    "CreatedByUser": {
        "FirstName": "Paul",
        "LastName": "Vaska",
        "UserName": "PaulVaska",
        "Position": "GP"
    },
    "CreatedDate": "2025-01-27T12:00:00"
}

try:
    print("유효한 ClientId (27)로 Progress Note API 테스트 중...")
    print(f"클라이언트: Mrs Phoebe Smith")
    print(f"ClientId: {test_data['ClientId']}")
    
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