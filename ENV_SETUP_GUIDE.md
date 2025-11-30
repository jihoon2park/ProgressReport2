# .env 파일 설정 가이드

## 현재 구조

시스템은 **환경 변수로 DB 직접 접속과 API 접속을 전환**할 수 있습니다:

- `USE_DB_DIRECT_ACCESS=true` → DB 직접 접속 모드 (빠름, 실시간)
- `USE_DB_DIRECT_ACCESS=false` → API 모드 (기존 방식)

DB 직접 접속 실패 시 **자동으로 API로 fallback**됩니다.

## .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
# ============================================
# DB 직접 접속 설정
# ============================================
# true: DB 직접 접속 사용 (빠름, 실시간)
# false: API 사용 (기존 방식)
USE_DB_DIRECT_ACCESS=true

# ============================================
# Parafield Gardens DB 설정
# ============================================
MANAD_DB_SERVER_PARAFIELD_GARDENS=efsvr02\sqlexpress
MANAD_DB_NAME_PARAFIELD_GARDENS=ManadPlus_Edenfield
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true

# ============================================
# 기타 Flask 설정 (필요시)
# ============================================
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
HOST=0.0.0.0
PORT=5000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 전환 방법

### DB 직접 접속 모드로 전환
```env
USE_DB_DIRECT_ACCESS=true
```

### API 모드로 전환
```env
USE_DB_DIRECT_ACCESS=false
```

**변경 후 서버 재시작 필요**

## 동작 방식

1. **DB 직접 접속 모드 (`USE_DB_DIRECT_ACCESS=true`)**:
   - DB에서 직접 데이터 조회
   - 실패 시 자동으로 API로 fallback
   - 로그: `🔌 DB 직접 접속 모드: {site}`

2. **API 모드 (`USE_DB_DIRECT_ACCESS=false`)**:
   - 기존 API 방식 사용
   - 로그: `🌐 API 모드: {site}`

## 다른 사이트 추가

다른 사이트도 DB 직접 접속을 사용하려면:

```env
# Nerrilda
MANAD_DB_SERVER_NERRILDA=server_name\instance
MANAD_DB_NAME_NERRILDA=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_NERRILDA=true

# Ramsay
MANAD_DB_SERVER_RAMSAY=server_name\instance
MANAD_DB_NAME_RAMSAY=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_RAMSAY=true
```

## 확인 방법

서버 로그에서 다음 메시지를 확인하세요:

- `🔌 DB 직접 접속 모드: Parafield Gardens` → DB 직접 접속 사용 중
- `🌐 API 모드: Parafield Gardens` → API 사용 중
- `⚠️ DB 직접 접속 실패, API로 fallback` → DB 실패, API로 자동 전환

