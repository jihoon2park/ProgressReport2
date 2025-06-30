# Flask-Login 마이그레이션 가이드

## 개요
기존의 커스텀 세션 기반 인증 시스템을 Flask-Login으로 마이그레이션했습니다.

## 주요 변경사항

### 1. 새로운 파일
- `models.py`: Flask-Login을 위한 User 클래스 정의
- `test_flask_login.py`: 통합 테스트 스크립트

### 2. 수정된 파일
- `app.py`: Flask-Login 통합
- `requirements.txt`: Flask-Login 의존성 (이미 포함됨)

## 새로운 기능

### 1. 향상된 보안
- CSRF 보호
- 세션 관리 강화
- Remember Me 기능
- 자동 로그아웃

### 2. 표준화된 인증
- Flask 생태계 표준 사용
- 더 깔끔한 코드 구조
- 유지보수성 향상

### 3. 사용자 객체
```python
# 사용자 정보 접근
current_user.username
current_user.display_name
current_user.role
current_user.is_admin()
current_user.is_doctor()
current_user.is_physiotherapist()
```

## 사용법

### 1. 서버 실행
```bash
python app.py
```

### 2. 로그인
- 기존과 동일한 로그인 폼 사용
- Remember Me 기능 자동 활성화

### 3. 보호된 라우트
```python
@login_required
def protected_route():
    # 현재 사용자 정보
    user = current_user
    return f"Hello, {user.display_name}!"
```

### 4. 로그아웃
```python
logout_user()
```

## 테스트

### 1. 테스트 스크립트 실행
```bash
python test_flask_login.py
```

### 2. 수동 테스트
1. 브라우저에서 `http://localhost:5000` 접속
2. 로그인 시도
3. 보호된 페이지 접근 확인
4. 로그아웃 테스트

## 기존 코드와의 호환성

### 1. 세션 데이터
- 기존 세션 데이터는 `session['site']` 등으로 유지
- 사용자 정보는 `current_user` 객체로 접근

### 2. 템플릿
- 기존 템플릿은 수정 없이 작동
- `current_user` 객체 사용 가능

### 3. API 엔드포인트
- 기존 API는 `@login_required` 데코레이터 사용
- 응답 형식 동일

## 문제 해결

### 1. 로그인 실패
- 사용자명/비밀번호 확인
- 서버 로그 확인

### 2. 세션 문제
- 브라우저 쿠키 삭제
- 서버 재시작

### 3. 권한 문제
- 사용자 역할 확인
- `current_user.is_admin()` 등 사용

## 향후 개선사항

### 1. 역할 기반 접근 제어
```python
def require_role(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_role(role):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@require_role('admin')
def admin_only():
    return "Admin only"
```

### 2. 로그인 이벤트 처리
```python
@login_manager.user_loaded_from_request
def user_loaded_from_request(request):
    # 요청에서 사용자 로드 시 처리
    pass
```

### 3. 세션 설정 커스터마이징
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
```

## 마이그레이션 체크리스트

- [x] User 클래스 생성
- [x] LoginManager 설정
- [x] 로그인/로그아웃 함수 수정
- [x] 보호된 라우트 데코레이터 변경
- [x] 템플릿 호환성 확인
- [x] API 엔드포인트 수정
- [x] 테스트 스크립트 생성
- [x] 문서화

## 결론
Flask-Login 마이그레이션을 통해 더 안전하고 표준화된 인증 시스템을 구축했습니다. 기존 기능은 모두 유지되면서 보안성과 유지보수성이 크게 향상되었습니다. 