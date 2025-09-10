# 고급 알람 시스템 설정 가이드

## 개요
이 문서는 Progress Report 시스템의 고급 알람 기능 설정 방법을 설명합니다.

## 구현된 기능

### 1. FCM (Firebase Cloud Messaging) 연동
- 실시간 푸시 알림 전송
- 단일/멀티캐스트/토픽 기반 알림
- 자동 토큰 관리

### 2. 알람 템플릿 시스템
- 사전 정의된 알람 메시지 템플릿
- 위험도별 자동 템플릿 선택
- 사용자 정의 템플릿 생성

### 3. 수신자 관리
- 특정 직원/팀별 알람 전송
- FCM 토큰 자동 관리
- 알림 선호도 설정

### 4. 알람 에스컬레이션
- 미응답 시 자동 에스컬레이션
- 다단계 에스컬레이션 계획
- 실시간 에스컬레이션 상태 모니터링

## 설치 및 설정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 설정을 추가하세요:

```env
# FCM 설정
FCM_API_KEY=your-fcm-api-key-here
FIREBASE_CREDENTIALS_PATH=path/to/firebase-service-account-key.json

# 알람 설정
ALARM_ESCALATION_CHECK_INTERVAL=60
ALARM_CLEANUP_DAYS=7
```

### 3. Firebase 프로젝트 설정

#### 3.1 Firebase 콘솔에서 프로젝트 생성
1. [Firebase Console](https://console.firebase.google.com/)에 접속
2. 새 프로젝트 생성
3. Cloud Messaging 활성화

#### 3.2 서비스 계정 키 생성
1. 프로젝트 설정 > 서비스 계정
2. Firebase Admin SDK > 새 비공개 키 생성
3. 다운로드된 JSON 파일을 안전한 위치에 저장

#### 3.3 FCM API 키 확인
1. 프로젝트 설정 > 클라우드 메시징
2. 서버 키 복사

### 4. 데이터 디렉토리 생성
```bash
mkdir -p data
```

## 사용 방법

### 1. 기본 알람 전송
```javascript
// IncidentViewer.html에서
sendAlarmToMobile(incidentId, eventType, clientName, riskRating);
```

### 2. 고급 알람 관리
- "⚙️ Show Advanced Alarm Management" 버튼 클릭
- 템플릿 생성 및 관리
- 수신자 추가 및 관리
- 에스컬레이션 상태 모니터링

### 3. API 엔드포인트

#### 알람 전송
```
POST /api/send-alarm
{
    "incident_id": "123",
    "event_type": "Fire",
    "client_name": "Client A",
    "site": "Site 1",
    "risk_rating": "High",
    "template_id": "optional",
    "custom_message": "optional",
    "custom_recipients": ["user1", "user2"],
    "priority": "high"
}
```

#### 템플릿 관리
```
GET /api/alarm-templates          # 템플릿 목록
POST /api/alarm-templates         # 새 템플릿 생성
```

#### 수신자 관리
```
GET /api/alarm-recipients        # 수신자 목록
POST /api/alarm-recipients       # 새 수신자 추가
PUT /api/alarm-recipients/{id}/fcm-token  # FCM 토큰 업데이트
```

#### 에스컬레이션 관리
```
GET /api/alarms/escalations      # 대기 중인 에스컬레이션
GET /api/alarms/{id}/escalations # 특정 알람의 에스컬레이션
POST /api/alarms/{id}/acknowledge # 알람 확인
```

## 파일 구조

```
ProgressReport/
├── fcm_service.py           # FCM 연동 서비스
├── alarm_service.py         # 알람 템플릿, 수신자, 에스컬레이션 서비스
├── alarm_manager.py         # 통합 알람 관리 서비스
├── app.py                   # Flask 앱 (업데이트됨)
├── templates/
│   └── IncidentViewer.html # UI (업데이트됨)
└── data/                    # 데이터 저장소
    ├── alarm_templates.json
    ├── alarm_recipients.json
    ├── alarm_escalations.json
    └── alarm_logs.json
```

## 모니터링 및 로깅

### 1. 로그 파일
- `logs/app.log`: 일반 애플리케이션 로그
- `data/alarm_logs.json`: 알람 전송 로그
- `data/alarm_acknowledgments.json`: 알람 확인 로그

### 2. 에스컬레이션 모니터링
- 1분마다 자동 체크
- 대기 중인 에스컬레이션 개수 표시
- 실시간 상태 업데이트

## 문제 해결

### 1. FCM 연결 실패
- FCM_API_KEY 환경변수 확인
- Firebase 서비스 계정 키 파일 경로 확인
- 네트워크 연결 상태 확인

### 2. 알람 전송 실패
- 수신자의 FCM 토큰 확인
- 알람 템플릿 설정 확인
- 로그 파일에서 오류 메시지 확인

### 3. 에스컬레이션 작동 안함
- 템플릿의 에스컬레이션 설정 확인
- 수신자 권한 설정 확인
- 타이머 서비스 상태 확인

## 보안 고려사항

1. **FCM API 키 보호**: 환경변수로 관리, 소스코드에 하드코딩 금지
2. **서비스 계정 키**: 안전한 위치에 저장, 접근 권한 제한
3. **사용자 인증**: 모든 API 엔드포인트에 로그인 필요
4. **데이터 검증**: 입력 데이터 검증 및 sanitization

## 성능 최적화

1. **FCM 토큰 캐싱**: 자주 사용되는 토큰 메모리 캐싱
2. **배치 처리**: 여러 알람을 한 번에 처리
3. **비동기 처리**: 알람 전송을 백그라운드에서 처리
4. **로그 로테이션**: 오래된 로그 파일 자동 정리

## 향후 개선 사항

1. **SMS 연동**: FCM 외에 SMS 알림 지원
2. **이메일 연동**: 이메일 알림 지원
3. **웹훅**: 외부 시스템과의 연동
4. **통계 대시보드**: 알람 전송 통계 및 분석
5. **모바일 앱**: 전용 모바일 앱 개발

## 지원 및 문의

문제가 발생하거나 추가 기능이 필요한 경우:
1. 로그 파일 확인
2. 환경변수 설정 검증
3. Firebase 프로젝트 설정 확인
4. 개발팀에 문의


