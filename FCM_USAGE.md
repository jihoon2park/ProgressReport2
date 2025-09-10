# Firebase Cloud Messaging (FCM) 사용 가이드

## 개요

이 프로젝트는 Firebase Cloud Messaging (FCM)을 통해 안드로이드 단말로 푸시 알림을 보낼 수 있는 기능을 제공합니다.

## 아키텍처

```
귀하의 서버 ↔ FCM 백엔드 ↔ 안드로이드 앱
```

- **귀하의 서버**: Flask 기반 웹 애플리케이션
- **FCM 백엔드**: Google의 Firebase Cloud Messaging 서비스
- **안드로이드 앱**: FCM을 통해 메시지를 수신하는 모바일 앱

## 설치 및 설정

### 1. Firebase 프로젝트 설정

1. [Firebase Console](https://console.firebase.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 설정 > 서비스 계정 탭에서 "새 비공개 키 생성" 클릭
4. 다운로드된 JSON 파일을 `static/json/` 폴더에 저장

### 2. Python 의존성 설치

```bash
pip install firebase-admin
```

## 주요 기능

### 1. FCM 토큰 관리

- **토큰 등록**: 사용자의 FCM 등록 토큰을 서버에 저장
- **토큰 제거**: 사용자의 FCM 토큰을 서버에서 제거
- **토큰 조회**: 현재 사용자의 등록된 토큰 정보 확인

### 2. 푸시 알림 전송

- **개별 사용자**: 특정 사용자에게만 알림 전송
- **전체 사용자**: 모든 등록된 사용자에게 알림 전송
- **토픽 기반**: 특정 토픽을 구독한 사용자들에게 알림 전송

### 3. 알림 유형

- **알림 메시지**: 사용자에게 표시되는 알림 (제목, 내용, 이미지)
- **데이터 메시지**: 앱 내부에서 처리할 수 있는 커스텀 데이터

## API 엔드포인트

### FCM 토큰 관리

#### 토큰 등록
```http
POST /api/fcm/register-token
Content-Type: application/json

{
    "token": "FCM_등록_토큰",
    "device_info": "기기_정보"
}
```

#### 토큰 제거
```http
POST /api/fcm/unregister-token
Content-Type: application/json

{
    "token": "FCM_등록_토큰"
}
```

#### 토큰 조회
```http
GET /api/fcm/tokens
```

### 푸시 알림 전송

#### 알림 전송
```http
POST /api/fcm/send-notification
Content-Type: application/json

{
    "title": "알림 제목",
    "body": "알림 내용",
    "user_ids": ["user1", "user2"],  // 선택사항: 특정 사용자
    "topic": "news",                  // 선택사항: 토픽
    "data": {                         // 선택사항: 추가 데이터
        "type": "alert",
        "id": "123"
    },
    "image_url": "https://example.com/image.jpg"  // 선택사항: 이미지
}
```

### 관리자 기능

#### FCM 통계 조회
```http
GET /api/fcm/stats
```

#### 비활성 토큰 정리
```http
POST /api/fcm/cleanup
Content-Type: application/json

{
    "days_threshold": 30
}
```

## 사용 예시

### 1. Python에서 FCM 서비스 사용

```python
from fcm_service import get_fcm_service
from fcm_token_manager import get_fcm_token_manager

# FCM 서비스 초기화
fcm_service = get_fcm_service()
token_manager = get_fcm_token_manager()

# 특정 사용자에게 알림 전송
user_tokens = token_manager.get_user_token_strings("user123")
if user_tokens:
    result = fcm_service.send_notification_to_tokens(
        user_tokens,
        "새 알림",
        "새로운 메시지가 도착했습니다!",
        {"type": "message", "id": "123"}
    )
    print(f"알림 전송 결과: {result}")
```

### 2. 토픽 기반 알림 전송

```python
# 특정 토픽으로 구독한 모든 사용자에게 알림
result = fcm_service.send_topic_message(
    "news",
    "뉴스 업데이트",
    "새로운 뉴스가 있습니다.",
    {"category": "breaking", "priority": "high"}
)
```

### 3. 데이터 메시지 전송

```python
# 백그라운드 처리용 데이터 메시지
result = fcm_service.send_data_message(
    "user_token",
    {"action": "sync", "timestamp": "2025-01-01T00:00:00Z"}
)
```

## 웹 인터페이스

### FCM 테스트 페이지

`/fcm-test` 경로에서 FCM 기능을 테스트할 수 있습니다:

- FCM 토큰 등록/제거
- 푸시 알림 전송 테스트
- FCM 통계 조회
- 토큰 정리

## 안드로이드 앱 구현

### 1. FCM 토큰 가져오기

```kotlin
import com.google.firebase.messaging.FirebaseMessaging

FirebaseMessaging.getInstance().getToken()
    .addOnCompleteListener { task ->
        if (task.isSuccessful) {
            val token = task.result
            // 이 토큰을 서버로 전송하여 저장
            sendTokenToServer(token)
        }
    }
```

### 2. 메시지 수신 처리

```kotlin
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {
    
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        
        // 알림 메시지 처리
        remoteMessage.notification?.let { notification ->
            val title = notification.title
            val body = notification.body
            // 알림 표시 로직
        }
        
        // 데이터 메시지 처리
        remoteMessage.data.isNotEmpty().let { data ->
            // 앱 내부 로직 처리
        }
    }
    
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        // 새로운 토큰을 서버로 전송
        sendTokenToServer(token)
    }
}
```

### 3. AndroidManifest.xml 설정

```xml
<service
    android:name=".MyFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

## 보안 고려사항

1. **서비스 계정 키**: Firebase 서비스 계정 JSON 파일은 절대 공개 저장소에 업로드하지 마세요
2. **토큰 검증**: 클라이언트에서 받은 FCM 토큰의 유효성을 검증하세요
3. **사용자 인증**: FCM API는 로그인된 사용자만 접근할 수 있습니다
4. **권한 관리**: 관리자 기능은 관리자 권한을 가진 사용자만 사용할 수 있습니다

## 모니터링 및 로깅

- 모든 FCM 작업은 로그 파일에 기록됩니다
- `logs/app.log`에서 FCM 관련 로그를 확인할 수 있습니다
- FCM 통계를 통해 토큰 상태를 모니터링할 수 있습니다

## 문제 해결

### 일반적인 문제

1. **토큰 등록 실패**
   - Firebase 서비스 계정 JSON 파일 경로 확인
   - 파일 권한 확인

2. **알림 전송 실패**
   - FCM 토큰 유효성 확인
   - Firebase 프로젝트 설정 확인

3. **안드로이드 앱에서 알림 수신 안됨**
   - FCM 토큰이 서버에 제대로 등록되었는지 확인
   - 앱의 FCM 설정 확인

### 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/app.log | grep FCM

# FCM 관련 로그만 필터링
grep "FCM" logs/app.log
```

## 추가 리소스

- [Firebase Cloud Messaging 공식 문서](https://firebase.google.com/docs/cloud-messaging)
- [Firebase Admin SDK Python 문서](https://firebase.google.com/docs/admin/setup)
- [Android FCM 가이드](https://firebase.google.com/docs/cloud-messaging/android/client)

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
