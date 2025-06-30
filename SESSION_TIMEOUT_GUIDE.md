# 세션 타임아웃 기능 가이드

## 개요
로그인 후 5분 동안 아무 활동이 없으면 자동으로 로그아웃되며, 1분 전에 경고 팝업이 표시됩니다.

## 주요 기능

### 1. 세션 타임아웃 (5분)
- 로그인 후 5분 동안 활동이 없으면 자동 로그아웃
- Flask-Login의 세션 관리와 연동

### 2. 경고 팝업 (1분 전)
- 세션 만료 1분 전에 경고 모달 표시
- "세션 연장" 또는 "지금 로그아웃" 선택 가능
- 10초 후 자동으로 사라짐

### 3. 사용자 활동 감지
- 마우스, 키보드, 터치 활동 감지
- 2분 후 자동으로 세션 연장 (조용히)

### 4. 자동 로그아웃
- 세션 만료 시 자동으로 로그인 페이지로 이동
- 3초 후 자동 이동

## 구현 세부사항

### 1. 서버 측 (Flask)
```python
# 세션 타임아웃 설정
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=5)

# API 엔드포인트
/api/session-status    # 세션 상태 확인
/api/extend-session    # 세션 연장
```

### 2. 클라이언트 측 (JavaScript)
```javascript
// 세션 모니터링 (30초마다)
setInterval(checkSessionStatus, 30000);

// 사용자 활동 감지
['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
```

## 사용법

### 1. 일반 사용
- 로그인 후 정상적으로 사용
- 5분 동안 활동이 없으면 자동 로그아웃
- 1분 전에 경고 팝업 표시

### 2. 세션 연장
- 경고 팝업에서 "세션 연장" 클릭
- 또는 사용자 활동 시 자동 연장

### 3. 즉시 로그아웃
- 경고 팝업에서 "지금 로그아웃" 클릭
- 또는 5분 대기

## 테스트 방법

### 1. API 테스트
```bash
python test_session_timeout.py
```

### 2. 브라우저 테스트
1. `http://localhost:5000` 접속
2. 로그인 (admin/password123)
3. 5분 동안 아무것도 하지 않기
4. 1분 전 경고 팝업 확인
5. 세션 연장 또는 로그아웃 테스트

## 설정 변경

### 1. 타임아웃 시간 변경
```python
# app.py에서 수정
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)  # 10분으로 변경
```

### 2. 경고 시간 변경
```javascript
// static/js/script.js에서 수정
const SESSION_WARNING_MINUTES = 2;  // 2분 전에 경고
```

### 3. 모니터링 간격 변경
```javascript
// static/js/script.js에서 수정
sessionCheckInterval = setInterval(checkSessionStatus, 60000);  // 1분마다
```

## 문제 해결

### 1. 세션이 너무 빨리 만료됨
- 서버 시간과 클라이언트 시간 확인
- 네트워크 연결 상태 확인

### 2. 경고 팝업이 표시되지 않음
- 브라우저 콘솔에서 JavaScript 오류 확인
- 네트워크 탭에서 API 호출 확인

### 3. 세션 연장이 작동하지 않음
- 서버 로그 확인
- API 응답 상태 확인

## 보안 고려사항

### 1. 세션 보안
- HTTPS 사용 권장
- 세션 쿠키 보안 설정
- CSRF 보호

### 2. 자동 연장 제한
- 무한 연장 방지
- 최대 세션 시간 설정

### 3. 로그 기록
- 세션 만료 로그
- 사용자 활동 로그

## 향후 개선사항

### 1. 고급 기능
- 사용자별 타임아웃 설정
- 역할별 타임아웃 설정
- 세션 히스토리 관리

### 2. UI 개선
- 실시간 남은 시간 표시
- 세션 상태 인디케이터
- 커스텀 경고 메시지

### 3. 모바일 지원
- 터치 이벤트 최적화
- 모바일 친화적 UI
- 푸시 알림 지원 