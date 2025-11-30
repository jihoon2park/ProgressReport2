# MSSQL 직접 접속 가이드

## 개요

MANAD MSSQL 데이터베이스에 직접 접속하면 API를 통한 동기화보다 훨씬 효율적입니다.

### 장점

1. **실시간 데이터 접근** - API 레이턴시 없이 직접 DB에서 읽기
2. **성능 향상** - 네트워크 오버헤드 감소, 배치 쿼리 가능, JOIN 쿼리 최적화
3. **백그라운드 동기화 불필요** - 필요할 때마다 직접 조회
4. **데이터 정확성** - API 변환 과정 없이 원본 데이터 직접 접근
5. **비용 절감** - API 호출 오버헤드 제거

## 설치 방법

### 1. MSSQL 드라이버 설치

#### Windows (권장: pyodbc)
```bash
pip install pyodbc
```

#### Linux/Mac (pymssql 또는 pyodbc)
```bash
# 옵션 1: pymssql (더 간단)
pip install pymssql

# 옵션 2: pyodbc (더 표준)
pip install pyodbc
# Linux 추가 설치 필요:
# sudo apt-get install unixodbc-dev
# sudo apt-get install freetds-dev freetds-bin
```

### 2. 환경 변수 설정

`.env` 파일에 DB 연결 정보 추가:

#### Windows Authentication 사용 (권장 - Parafield Gardens)

```env
# Parafield Gardens DB (Windows Authentication)
MANAD_DB_SERVER_PARAFIELD_GARDENS=efsvr02\sqlexpress
MANAD_DB_NAME_PARAFIELD_GARDENS=MANAD_Plus
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true
```

#### SQL Server Authentication 사용

```env
# Parafield Gardens DB (SQL Server Authentication)
MANAD_DB_SERVER_PARAFIELD_GARDENS=192.168.1.11
MANAD_DB_NAME_PARAFIELD_GARDENS=MANAD_Plus
MANAD_DB_USER_PARAFIELD_GARDENS=your_username
MANAD_DB_PASSWORD_PARAFIELD_GARDENS=your_password
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=false

# Nerrilda DB
MANAD_DB_SERVER_NERRILDA=192.168.21.12
MANAD_DB_NAME_NERRILDA=MANAD_Plus
MANAD_DB_USER_NERRILDA=your_username
MANAD_DB_PASSWORD_NERRILDA=your_password

# Ramsay DB
MANAD_DB_SERVER_RAMSAY=192.168.31.12
MANAD_DB_NAME_RAMSAY=MANAD_Plus
MANAD_DB_USER_RAMSAY=your_username
MANAD_DB_PASSWORD_RAMSAY=your_password

# West Park DB
MANAD_DB_SERVER_WEST_PARK=192.168.41.12
MANAD_DB_NAME_WEST_PARK=MANAD_Plus
MANAD_DB_USER_WEST_PARK=your_username
MANAD_DB_PASSWORD_WEST_PARK=your_password

# Yankalilla DB
MANAD_DB_SERVER_YANKALILLA=192.168.51.12
MANAD_DB_NAME_YANKALILLA=MANAD_Plus
MANAD_DB_USER_YANKALILLA=your_username
MANAD_DB_PASSWORD_YANKALILLA=your_password

# 공통 설정 (사이트별 설정이 없으면 이것 사용)
MANAD_DB_NAME=MANAD_Plus
MANAD_DB_USER=your_username
MANAD_DB_PASSWORD=your_password

# 드라이버 설정 (Windows는 보통 자동 감지)
# MANAD_DB_DRIVER={ODBC Driver 17 for SQL Server}  # Windows
# MANAD_DB_DRIVER=ODBC Driver 17 for SQL Server     # Linux
```

## 사용 방법

### 1. app.py 수정

`sync_incidents_from_manad_to_cims` 함수에서 DB 직접 접속 사용:

```python
def sync_incidents_from_manad_to_cims(full_sync=False):
    """MANAD DB에서 직접 데이터 동기화"""
    try:
        # DB 직접 접속 사용 (환경 변수로 전환 가능)
        use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
        if use_db_direct:
            from manad_db_connector import fetch_incidents_with_client_data_from_db
            
            # DB에서 직접 조회
            incidents_data = fetch_incidents_with_client_data_from_db(
                site_name, start_date, end_date, 
                fetch_clients=is_first_sync
            )
        else:
            # 기존 API 방식 (fallback)
            from api_incident import fetch_incidents_with_client_data
            incidents_data = fetch_incidents_with_client_data(
                site_name, start_date, end_date, 
                fetch_clients=is_first_sync
            )
        
        # 나머지 로직은 동일...
```

### 2. 환경 변수로 전환

`.env` 파일에 추가:
```env
USE_DB_DIRECT_ACCESS=true
```

## DB 스키마 확인 필요

`manad_db_connector.py`의 쿼리는 예시입니다. 실제 MANAD DB 구조에 맞게 수정 필요:

1. **테이블명 확인**:
   - `Incidents` → 실제 테이블명?
   - `Clients` → 실제 테이블명?

2. **컬럼명 확인**:
   - `Id`, `ClientId`, `Date` 등 실제 컬럼명과 일치하는지 확인

3. **관계 테이블 확인**:
   - Event Types와의 다대다 관계 테이블명 확인
   - `IncidentEventTypes` → 실제 테이블명?

## 테스트

```python
# test_db_connection.py
from manad_db_connector import MANADDBConnector

connector = MANADDBConnector('Parafield Gardens')

# Incident 조회 테스트
success, incidents = connector.fetch_incidents('2025-11-01', '2025-11-30')
if success:
    print(f"✅ {len(incidents)}개 Incident 조회 성공")
else:
    print("❌ 조회 실패")

# Client 조회 테스트
success, clients = connector.fetch_clients()
if success:
    print(f"✅ {len(clients)}명 Client 조회 성공")
```

## 보안 고려사항

1. **읽기 전용 권한**: DB 사용자 계정은 읽기 전용 권한만 부여
2. **VPN 연결**: 안전한 네트워크를 통한 접속 권장
3. **Connection Pooling**: 많은 요청 시 연결 풀 사용 고려
4. **타임아웃 설정**: 쿼리 타임아웃 설정 (현재 30초)

## 성능 비교

### API 방식 (현재)
- API 호출 시간: 2-5초
- 네트워크 레이턴시: 100-500ms
- 데이터 변환 오버헤드
- 백그라운드 동기화 필요

### DB 직접 접속 (제안)
- DB 쿼리 시간: 0.1-1초
- 네트워크 레이턴시: 10-50ms
- 직접 데이터 접근
- 백그라운드 동기화 불필요 (필요할 때만 조회)

**예상 성능 향상: 5-10배**

## 마이그레이션 계획

1. **1단계**: DB 연결 테스트 및 스키마 확인
2. **2단계**: `manad_db_connector.py` 쿼리 실제 DB 구조에 맞게 수정
3. **3단계**: 테스트 환경에서 검증
4. **4단계**: `USE_DB_DIRECT_ACCESS=true`로 전환
5. **5단계**: 백그라운드 동기화 제거 (선택적)

## 문제 해결

### 드라이버 설치 오류
```bash
# Windows
pip install pyodbc

# Linux
sudo apt-get update
sudo apt-get install unixodbc-dev
pip install pyodbc
```

### 연결 실패
- 방화벽 설정 확인
- DB 서버 IP/포트 확인
- 사용자 권한 확인 (읽기 권한)

### 쿼리 오류
- 실제 테이블/컬럼명 확인
- SQL Server Management Studio로 스키마 확인

