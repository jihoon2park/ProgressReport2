# Parafield Gardens DB 직접 접속 설정 완료

## ✅ 확인된 정보

- **서버**: `efsvr02\sqlexpress`
- **데이터베이스**: `ManadPlus_Edenfield`
- **인증 방식**: Windows Authentication (현재 사용자: `EDENFIELD\it.support`)
- **연결 상태**: ✅ 성공

## 📋 주요 테이블 구조

### Event 테이블 (Incident)
- `Id` - Event ID
- `Date` - Event 발생 날짜
- `Description` - Event 설명
- `PersonId` - Client ID
- `LocationId` - 위치 ID
- `StatusEnumId` - 상태
- 기타 여러 컬럼...

### Client 테이블
- `Id` - Client ID
- `FirstName` - 이름
- `LastName` - 성
- 기타...

### EventType 테이블
- `Id` - EventType ID
- `Description` - EventType 설명

### Event_EventType (다대다 관계)
- `EventId` - Event ID
- `EventTypeId` - EventType ID

## 🔧 .env 파일 설정

`.env` 파일에 다음을 추가하세요:

```env
# Parafield Gardens DB 직접 접속 (Windows Authentication)
MANAD_DB_SERVER_PARAFIELD_GARDENS=efsvr02\sqlexpress
MANAD_DB_NAME_PARAFIELD_GARDENS=ManadPlus_Edenfield
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true

# DB 직접 접속 활성화
USE_DB_DIRECT_ACCESS=true
```

## 📝 다음 단계

1. ✅ DB 연결 확인 완료
2. ✅ 테이블 구조 확인 완료
3. ⏳ 실제 쿼리 작성 (Event 테이블에서 데이터 조회)
4. ⏳ `manad_db_connector.py` 쿼리 업데이트
5. ⏳ 테스트 및 검증

## 🧪 테스트 스크립트

```bash
# 데이터베이스 목록 확인
python test_parafield_list_databases.py

# 테이블 구조 확인
python test_parafield_db_schema.py

# 실제 데이터 조회 테스트 (준비 중)
python test_parafield_fetch_incidents.py
```

