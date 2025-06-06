# 📡 Progress Note API 전송 기능 사용법

## 🎯 개요
Progress Note 데이터를 저장한 후 자동으로 `http://10.16.0.165:8080/api/progressnote` 엔드포인트로 POST 요청을 보내는 기능이 추가되었습니다.

## 📋 구현된 기능

### 1. **자동 API 전송**
- **순서**: Save 버튼 클릭 → JSON 파일 생성 → API 자동 전송
- **파일**: `api_progressnote.py`
- **엔드포인트**: `http://10.16.0.165:8080/api/progressnote`
- **메소드**: POST
- **데이터**: `prepare_send.json` 파일 내용

### 2. **전송 데이터 형식**
```json
{
    "ClientId": 2736,
    "EventDate": "2025-06-05T15:56:00",
    "ProgressNoteEventType": {
        "Id": 3
    },
    "NotesPlainText": "환자 노트 내용...",
    "CreatedByUser": {
        "FirstName": "Paul",
        "LastName": "Vaska", 
        "UserName": "PaulVaska",
        "Position": "GP"
    },
    "CreatedDate": "2025-06-05T15:56:00"
}
```

### 3. **응답 처리**
- ✅ **성공시**: "Progress Note가 성공적으로 저장되고 API로 전송되었습니다!"
- ⚠️ **부분 성공시**: "Progress Note가 저장되었지만 API 전송에 실패했습니다."
- ❌ **실패시**: "Progress Note 저장에 실패했습니다"

## 🔧 API 클라이언트 클래스

### **ProgressNoteAPIClient**
```python
from api_progressnote import ProgressNoteAPIClient

# 클라이언트 초기화
client = ProgressNoteAPIClient()

# API 연결 테스트
connection_ok = client.test_connection()

# Progress Note 전송
success, response = client.send_progress_note()
```

### **편의 함수들**
```python
from api_progressnote import send_progress_note_to_api, send_specific_progress_note

# prepare_send.json 파일 자동 전송
success, response = send_progress_note_to_api()

# 특정 데이터 전송
custom_data = {...}
success, response = send_specific_progress_note(custom_data)
```

## 🧪 테스트 방법

### 1. **직접 테스트**
```bash
# 터미널에서 직접 실행
python api_progressnote.py
```

### 2. **웹 인터페이스에서 테스트**
1. Progress Note 작성
2. Save 버튼 클릭
3. 결과 메시지 확인



## 📝 로그 기록

### **성공 로그 파일**
- **위치**: `data/progress_note_success.log`
- **형식**: JSON Lines (각 줄마다 하나의 JSON 객체)
```json
{
    "timestamp": "2025-01-27T10:49:05.119",
    "client_id": 2736,
    "event_type_id": 3,
    "created_by": "PaulVaska",
    "api_response": {"status": "success"}
}
```

### **에러 로그**
- 애플리케이션 로그에 기록
- 연결 실패, 타임아웃, 데이터 유효성 검사 실패 등

## ⚙️ 설정 변경

### **API URL 변경**
`api_progressnote.py` 파일에서:
```python
class ProgressNoteAPIClient:
    def __init__(self):
        self.api_url = "http://10.16.0.165:8080/api/progressnote"  # 여기서 변경
```

### **타임아웃 설정**
```python
response = self.session.post(
    self.api_url,
    json=data,
    timeout=30  # 초 단위 (기본값: 30초)
)
```

### **요청 헤더 수정**
```python
self.session.headers.update({
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'ProgressReport-Client/1.0',
    'Authorization': 'Bearer your-token'  # 필요시 추가
})
```

## 🔒 보안 고려사항

### **1. HTTPS 사용 권장**
```python
self.api_url = "https://10.16.0.165:8080/api/progressnote"  # HTTP → HTTPS
```

### **2. 인증 토큰 추가**
```python
# 헤더에 인증 토큰 추가
self.session.headers.update({
    'Authorization': 'Bearer your-api-token',
    'X-API-Key': 'your-api-key'
})
```

### **3. SSL 인증서 검증**
```python
# SSL 인증서 검증 비활성화 (개발용만)
self.session.verify = False

# 또는 사용자 정의 CA 인증서
self.session.verify = '/path/to/ca-cert.pem'
```

## 🐛 문제 해결

### **자주 발생하는 문제들**

#### 1. **연결 타임아웃**
```
ERROR: API 서버 연결 실패: Connection timeout
```
**해결책**: 
- API 서버 상태 확인
- 방화벽 설정 확인  
- URL 주소 확인

#### 2. **데이터 유효성 검사 실패**
```
ERROR: 필수 필드 누락: ClientId
```
**해결책**: 
- 클라이언트 선택 확인
- 필수 필드 입력 확인

#### 3. **모듈 import 오류**
```
ERROR: API 모듈 import 오류
```
**해결책**: 
- `api_progressnote.py` 파일 존재 확인
- Python 경로 확인

## 📊 사용 통계

### **성공 로그 분석**
```bash
# 성공한 전송 횟수 확인
wc -l data/progress_note_success.log

# 최근 전송 기록 확인  
tail -5 data/progress_note_success.log

# 특정 사용자의 전송 기록
grep "PaulVaska" data/progress_note_success.log
```

## 🔄 업데이트 이력

- **v1.0** (2025-01-27): 초기 API 전송 기능 구현
- API 연결 테스트 기능 추가
- 자동 백그라운드 전송 구현
- 에러 핸들링 및 로깅 추가 