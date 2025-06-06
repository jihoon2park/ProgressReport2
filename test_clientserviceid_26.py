#!/usr/bin/env python3
"""
ClientServiceId = 26 테스트 (클라이언트 레코드 ID)
"""

import json
import requests
from datetime import datetime

# ClientServiceId를 26으로 설정한 테스트 데이터
test_data = {
    "ClientId": 83,  # Mrs Phoebe Smith의 PersonId
    "ClientServiceId": 26,  # 클라이언트 레코드 Id
    "EventDate": "2024-12-23T09:00:00.000Z",
    "ProgressNoteEventType": {
        "Id": 3  # Doctor 이벤트 타입
    },
    "NotesPlainText": "ClientServiceId = 26 테스트 - Doctor 이벤트 - Mrs Phoebe Smith",
    "CreatedByUser": {
        "FirstName": "Test",
        "LastName": "User",
        "UserName": "testuser",
        "Position": "Test Position"
    },
    "CreatedDate": datetime.now().isoformat() + "Z"
}

def test_api():
    url = "http://192.168.1.11:8080/api/progressnote"  # Parafield Gardens
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-username': 'ManadAPI',
        'x-api-key': '6RU+gahOFDvf/aF2dC7hAV+flYNe+dMb8Ts2xMsR0QM='
    }
    
    print("ClientServiceId = 26으로 Progress Note API 테스트 중...")
    print(f"URL: {url}")
    print(f"ClientId: {test_data['ClientId']} (PersonId)")
    print(f"ClientServiceId: {test_data['ClientServiceId']} (클라이언트 레코드 Id)")
    print(f"ProgressNoteEventType: {test_data['ProgressNoteEventType']} (Doctor 이벤트)")
    print(f"테스트 데이터:")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))
    print("\n" + "="*50)
    
    try:
        response = requests.post(url, json=test_data, headers=headers, timeout=30)
        
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        if response.text:
            try:
                response_json = response.json()
                print(f"응답 JSON: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"응답 텍스트: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: ClientServiceId = 26으로 API 호출 성공!")
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 오류: {e}")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")

if __name__ == "__main__":
    test_api() 