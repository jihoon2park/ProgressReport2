#!/usr/bin/env python3
"""
Mrs Phoebe Smith - 올바른 조합 테스트 (Ada Sims 성공 사례 기반)
ClientId = 클라이언트 레코드 ID, ClientServiceId = MainClientServiceId
"""

import json
import requests
from datetime import datetime

# Mrs Phoebe Smith: Ada Sims 성공 사례를 기반으로 한 올바른 조합
test_data = {
    "ClientId": 26,  # Mrs Phoebe Smith의 Id (클라이언트 레코드 ID)
    "ClientServiceId": 27,  # Mrs Phoebe Smith의 MainClientServiceId
    "EventDate": "2024-12-23T09:00:00.000Z",
    "ProgressNoteEventType": {
        "Id": 3  # Doctor 이벤트 타입
    },
    "NotesPlainText": "Mrs Phoebe Smith - 올바른 조합 테스트 (ClientId=Id, ClientServiceId=MainClientServiceId)",
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
    
    print("Mrs Phoebe Smith - 올바른 조합으로 Progress Note API 테스트 중...")
    print(f"URL: {url}")
    print(f"ClientId: {test_data['ClientId']} (Mrs Phoebe Smith Id - 클라이언트 레코드 ID)")
    print(f"ClientServiceId: {test_data['ClientServiceId']} (Mrs Phoebe Smith MainClientServiceId)")
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
            print("\n✅ SUCCESS: Mrs Phoebe Smith - 올바른 조합으로 API 호출 성공!")
            return True
        else:
            print(f"\n❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        return False

if __name__ == "__main__":
    test_api() 