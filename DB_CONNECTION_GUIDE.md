# Database Connection Configuration Guide
# 데이터베이스 접속 설정 가이드

This document explains where database connection settings and login credentials are stored and how to configure them.
이 문서는 데이터베이스 접속 설정과 로그인 정보가 어디에 저장되어 있는지, 그리고 어떻게 설정하는지 설명합니다.

---

## 📁 Configuration Files Overview
## 📁 설정 파일 개요

The system uses multiple configuration files for database access. Here's where everything is located:
시스템은 데이터베이스 접속을 위해 여러 설정 파일을 사용합니다. 각 파일의 위치는 다음과 같습니다:

### 1. Environment Variables (`.env` file)
### 1. 환경 변수 (`.env` 파일)

**Location**: Project root directory (`.env`)
**위치**: 프로젝트 루트 디렉토리 (`.env`)

**Purpose**: Primary configuration for database direct access mode
**목적**: 데이터베이스 직접 접속 모드의 주요 설정

**Priority**: Used as fallback when `site_config.json` is not available
**우선순위**: `site_config.json`이 없을 때 폴백으로 사용

**Example Configuration**:
**설정 예시**:

```env
# ============================================
# DB Direct Access Mode Toggle
# DB 직접 접속 모드 전환
# ============================================
# true: Use direct DB access (fast, real-time)
# true: DB 직접 접속 사용 (빠름, 실시간)
# false: Use API mode (legacy method)
# false: API 모드 사용 (기존 방식)
USE_DB_DIRECT_ACCESS=true

# ============================================
# Parafield Gardens Database Configuration
# Parafield Gardens 데이터베이스 설정
# ============================================
MANAD_DB_SERVER_PARAFIELD_GARDENS=efsvr02\sqlexpress
MANAD_DB_NAME_PARAFIELD_GARDENS=ManadPlus_Edenfield
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true

# For SQL Server Authentication (if not using Windows Auth):
# SQL Server 인증 사용 시 (Windows 인증 미사용):
# MANAD_DB_USER_PARAFIELD_GARDENS=your_username
# MANAD_DB_PASSWORD_PARAFIELD_GARDENS=your_password
# MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=false

# ============================================
# Other Sites Database Configuration
# 다른 사이트 데이터베이스 설정
# ============================================
# Nerrilda
MANAD_DB_SERVER_NERRILDA=server_name\instance
MANAD_DB_NAME_NERRILDA=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_NERRILDA=true

# Ramsay
MANAD_DB_SERVER_RAMSAY=server_name\instance
MANAD_DB_NAME_RAMSAY=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_RAMSAY=true

# West Park
MANAD_DB_SERVER_WEST_PARK=server_name\instance
MANAD_DB_NAME_WEST_PARK=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_WEST_PARK=true

# Yankalilla
MANAD_DB_SERVER_YANKALILLA=server_name\instance
MANAD_DB_NAME_YANKALILLA=ManadPlus_XXX
MANAD_DB_USE_WINDOWS_AUTH_YANKALILLA=true

# ============================================
# Common Database Settings (Fallback)
# 공통 데이터베이스 설정 (폴백)
# ============================================
# Used when site-specific settings are not available
# 사이트별 설정이 없을 때 사용
MANAD_DB_NAME=ManadPlus_Edenfield
MANAD_DB_USER=your_username
MANAD_DB_PASSWORD=your_password

# ============================================
# ODBC Driver Configuration (Optional)
# ODBC 드라이버 설정 (선택사항)
# ============================================
# Windows (usually auto-detected):
# MANAD_DB_DRIVER={ODBC Driver 17 for SQL Server}
# Linux:
# MANAD_DB_DRIVER=ODBC Driver 17 for SQL Server

# ============================================
# Flask Application Settings
# Flask 애플리케이션 설정
# ============================================
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
HOST=0.0.0.0
PORT=5000
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**File Status**: 
- **Status**: Not tracked in git (in `.gitignore`)
- **상태**: Git에서 추적하지 않음 (`.gitignore`에 포함)
- **Security**: Contains sensitive credentials - DO NOT commit to version control
- **보안**: 민감한 자격 증명 포함 - 버전 관리에 커밋하지 마세요

---

### 2. Site Configuration JSON (`site_config.json`)
### 2. 사이트 설정 JSON (`site_config.json`)

**Location**: `data/api_keys/site_config.json`
**위치**: `data/api_keys/site_config.json`

**Purpose**: Recommended method for site-specific database and API configurations
**목적**: 사이트별 데이터베이스 및 API 설정을 위한 권장 방법

**Priority**: Highest priority - checked first before environment variables
**우선순위**: 최우선 - 환경 변수보다 먼저 확인됨

**Example Configuration**:
**설정 예시**:

```json
[
  {
    "site_name": "Parafield Gardens",
    "api": {
      "server_ip": "192.168.1.11",
      "server_port": 8080,
      "base_url": "http://192.168.1.11:8080",
      "api_username": "ManadAPI",
      "api_key": "your-api-key-here"
    },
    "database": {
      "server": "efsvr02\\sqlexpress",
      "database": "ManadPlus_Edenfield",
      "use_windows_auth": true,
      "username": null,
      "password": null
    }
  },
  {
    "site_name": "Nerrilda",
    "api": {
      "server_ip": "192.168.21.12",
      "server_port": 8080,
      "base_url": "http://192.168.21.12:8080",
      "api_username": "ManadAPI",
      "api_key": "your-api-key-here"
    },
    "database": {
      "server": "192.168.21.12\\sqlexpress",
      "database": "ManadPlus_Nerrilda",
      "use_windows_auth": true,
      "username": null,
      "password": null
    }
  },
  {
    "site_name": "Ramsay",
    "api": {
      "server_ip": "192.168.31.12",
      "server_port": 8080,
      "base_url": "http://192.168.31.12:8080",
      "api_username": "ManadAPI",
      "api_key": "your-api-key-here"
    },
    "database": {
      "server": "192.168.31.12\\sqlexpress",
      "database": "ManadPlus_Ramsay",
      "use_windows_auth": false,
      "username": "db_user",
      "password": "db_password"
    }
  }
]
```

**File Status**:
- **Status**: May be tracked in git (check `.gitignore`)
- **상태**: Git에서 추적될 수 있음 (`.gitignore` 확인)
- **Security**: Contains API keys and database credentials - should be secured
- **보안**: API 키와 데이터베이스 자격 증명 포함 - 보안 처리 필요

**Configuration Loading**:
- **Code Location**: `manad_db_connector.py` (lines 28-85)
- **코드 위치**: `manad_db_connector.py` (28-85줄)
- **Function**: `get_site_db_config(site_name)` retrieves database config for a specific site
- **함수**: `get_site_db_config(site_name)` 특정 사이트의 DB 설정을 가져옴

---

### 3. User Login Credentials (`config_users.py`)
### 3. 사용자 로그인 정보 (`config_users.py`)

**Location**: `config_users.py` (project root)
**위치**: `config_users.py` (프로젝트 루트)

**Purpose**: Stores all user authentication credentials and roles
**목적**: 모든 사용자 인증 자격 증명과 역할 저장

**Documentation**: See `LOGIN_CREDENTIALS.md` for detailed user list
**문서**: 상세한 사용자 목록은 `LOGIN_CREDENTIALS.md` 참조

**Example Structure**:
**구조 예시**:

```python
USERS = {
    'admin': {
        'password': 'password123',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'admin',
        'location': ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
    },
    'PGROD': {
        'password': 'pgpassword',
        'first_name': 'Parafield',
        'last_name': 'ROD',
        'role': 'admin',
        'location': ['Parafield Gardens', 'Ramsay', 'Nerrilda']
    },
    # ... more users
}
```

**File Status**:
- **Status**: Tracked in git (contains non-sensitive test credentials)
- **상태**: Git에서 추적됨 (민감하지 않은 테스트 자격 증명 포함)
- **Security**: For production, consider moving to database or environment variables
- **보안**: 프로덕션 환경에서는 데이터베이스나 환경 변수로 이동 고려

**Quick Reference** (from `LOGIN_CREDENTIALS.md`):
**빠른 참조** (`LOGIN_CREDENTIALS.md`에서):

| Purpose | Username | Password |
|---------|----------|----------|
| Main Admin | `admin` | `password123` |
| ROD Admin | `ROD` | `rod1234!` |
| Parafield Gardens | `PGROD` | `pgpassword` |
| West Park | `WPROD` | `wppassword` |
| Yankalilla | `YKROD` | `ykpassword` |

---

### 4. Flask Configuration (`config_env.py`)
### 4. Flask 설정 (`config_env.py`)

**Location**: `config_env.py` (project root)
**위치**: `config_env.py` (프로젝트 루트)

**Purpose**: Flask application settings loaded from environment variables
**목적**: 환경 변수에서 로드되는 Flask 애플리케이션 설정

**Key Functions**:
**주요 함수**:

- `get_flask_config()` - Returns Flask configuration dictionary
- `get_flask_config()` - Flask 설정 딕셔너리 반환
- `get_environment()` - Returns current environment (development/production)
- `get_environment()` - 현재 환경 반환 (development/production)
- `get_config_value(key, default)` - Gets config value with environment-specific override
- `get_config_value(key, default)` - 환경별 오버라이드가 있는 설정값 가져오기

**Configuration Keys**:
**설정 키**:

```python
{
    'SECRET_KEY': '...',           # Flask session secret
    'DEBUG': False,                # Debug mode
    'HOST': '0.0.0.0',            # Server host
    'PORT': 5000,                  # Server port
    'ENVIRONMENT': 'production',   # Environment name
    'LOG_LEVEL': 'INFO',          # Logging level
    'API_TIMEOUT': 30,            # API request timeout
    'DATABASE_URL': None          # Database URL (future use)
}
```

---

### 5. SQLite Database (`progress_report.db`)
### 5. SQLite 데이터베이스 (`progress_report.db`)

**Location**: Project root directory
**위치**: 프로젝트 루트 디렉토리

**Purpose**: Local SQLite database for CIMS data, user sessions, and cache
**목적**: CIMS 데이터, 사용자 세션, 캐시를 위한 로컬 SQLite 데이터베이스

**Configuration**:
**설정**:

- **Path**: Set in `shared/config.py` or `config_env.py`
- **경로**: `shared/config.py` 또는 `config_env.py`에서 설정
- **Default**: `progress_report.db` (project root)
- **기본값**: `progress_report.db` (프로젝트 루트)

**No credentials required** - file-based database
**자격 증명 불필요** - 파일 기반 데이터베이스

---

## 🔄 Configuration Priority Order
## 🔄 설정 우선순위 순서

When the system needs database connection information, it checks in this order:
시스템이 데이터베이스 연결 정보가 필요할 때 다음 순서로 확인합니다:

1. **`site_config.json`** (Highest Priority / 최우선)
   - Location: `data/api_keys/site_config.json`
   - 위치: `data/api_keys/site_config.json`
   - Used by: `manad_db_connector.py`
   - 사용처: `manad_db_connector.py`

2. **Environment Variables** (Fallback / 폴백)
   - Location: `.env` file (project root)
   - 위치: `.env` 파일 (프로젝트 루트)
   - Format: `MANAD_DB_SERVER_{SITE_NAME}`, `MANAD_DB_NAME_{SITE_NAME}`, etc.
   - 형식: `MANAD_DB_SERVER_{SITE_NAME}`, `MANAD_DB_NAME_{SITE_NAME}` 등

3. **Default/Hardcoded Values** (Last Resort / 최후의 수단)
   - Location: `config.py`
   - 위치: `config.py`
   - Used only if above methods fail
   - 위 방법들이 실패할 때만 사용

---

## 🔍 How to Check Current Configuration
## 🔍 현재 설정 확인 방법

### 1. Check Environment Variables
### 1. 환경 변수 확인

```bash
# Windows PowerShell
Get-Content .env

# Windows CMD
type .env

# Linux/Mac
cat .env
```

### 2. Check Site Config JSON
### 2. 사이트 설정 JSON 확인

```bash
# Windows PowerShell
Get-Content data\api_keys\site_config.json

# Linux/Mac
cat data/api_keys/site_config.json
```

### 3. Check Application Logs
### 3. 애플리케이션 로그 확인

When the application starts, it logs which configuration source is being used:
애플리케이션이 시작될 때 어떤 설정 소스를 사용하는지 로그에 기록됩니다:

```
📄 Loaded DB settings from site_config.json: Parafield Gardens
```

or

```
📄 Loaded DB settings from environment (fallback): Parafield Gardens
```

### 4. Check Code Location
### 4. 코드 위치 확인

**Database Connection Logic**:
**데이터베이스 연결 로직**:

- **File**: `manad_db_connector.py`
- **파일**: `manad_db_connector.py`
- **Class**: `MANADDBConnector`
- **클래스**: `MANADDBConnector`
- **Method**: `_get_connection_string(site)` (line 176)
- **메서드**: `_get_connection_string(site)` (176줄)

**Configuration Loading**:
**설정 로딩**:

- **File**: `manad_db_connector.py`
- **파일**: `manad_db_connector.py`
- **Functions**: 
  - `_load_site_config()` (line 34)
  - `get_site_db_config(site_name)` (line 54)
- **함수**:
  - `_load_site_config()` (34줄)
  - `get_site_db_config(site_name)` (54줄)

---

## 📝 Setting Up Database Connection
## 📝 데이터베이스 연결 설정하기

### Step 1: Choose Configuration Method
### 1단계: 설정 방법 선택

**Recommended**: Use `site_config.json` for centralized management
**권장**: 중앙 집중식 관리를 위해 `site_config.json` 사용

**Alternative**: Use `.env` file for environment-specific settings
**대안**: 환경별 설정을 위해 `.env` 파일 사용

### Step 2: Create/Edit Configuration File
### 2단계: 설정 파일 생성/편집

#### Option A: Using `site_config.json` (Recommended)
#### 옵션 A: `site_config.json` 사용 (권장)

1. Create directory if it doesn't exist:
1. 디렉토리가 없으면 생성:

```bash
mkdir -p data/api_keys
```

2. Create/edit `data/api_keys/site_config.json`:
2. `data/api_keys/site_config.json` 생성/편집:

```json
[
  {
    "site_name": "Parafield Gardens",
    "database": {
      "server": "efsvr02\\sqlexpress",
      "database": "ManadPlus_Edenfield",
      "use_windows_auth": true
    }
  }
]
```

#### Option B: Using `.env` file
#### 옵션 B: `.env` 파일 사용

1. Create `.env` file in project root:
1. 프로젝트 루트에 `.env` 파일 생성:

```env
USE_DB_DIRECT_ACCESS=true
MANAD_DB_SERVER_PARAFIELD_GARDENS=efsvr02\sqlexpress
MANAD_DB_NAME_PARAFIELD_GARDENS=ManadPlus_Edenfield
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true
```

### Step 3: Verify Configuration
### 3단계: 설정 확인

1. Start the application:
1. 애플리케이션 시작:

```bash
python app.py
```

2. Check logs for configuration loading messages:
2. 로그에서 설정 로딩 메시지 확인:

```
✅ Loaded site_config.json: 1 sites
📄 Loaded DB settings from site_config.json: Parafield Gardens
```

---

## 🔐 Security Best Practices
## 🔐 보안 모범 사례

### 1. Never Commit Credentials
### 1. 자격 증명을 커밋하지 마세요

- Add `.env` to `.gitignore` (already done)
- `.env`를 `.gitignore`에 추가 (이미 완료됨)
- Consider adding `site_config.json` to `.gitignore` if it contains production credentials
- 프로덕션 자격 증명이 포함된 경우 `site_config.json`도 `.gitignore`에 추가 고려

### 2. Use Windows Authentication When Possible
### 2. 가능하면 Windows 인증 사용

- More secure than SQL Server Authentication
- SQL Server 인증보다 더 안전함
- No passwords stored in configuration files
- 설정 파일에 비밀번호 저장 불필요

### 3. Restrict Database Permissions
### 3. 데이터베이스 권한 제한

- Use read-only database accounts for application access
- 애플리케이션 접근에는 읽기 전용 데이터베이스 계정 사용
- Grant minimum required permissions
- 최소한의 필요한 권한만 부여

### 4. Use Environment-Specific Configuration
### 4. 환경별 설정 사용

- Different credentials for development, staging, and production
- 개발, 스테이징, 프로덕션에 다른 자격 증명 사용
- Use environment variables for sensitive production settings
- 민감한 프로덕션 설정에는 환경 변수 사용

---

## 🐛 Troubleshooting
## 🐛 문제 해결

### Issue: "DB server/database is not configured"
### 문제: "DB server/database is not configured"

**Solution**:
**해결 방법**:

1. Check if `site_config.json` exists and has correct structure
1. `site_config.json`이 존재하고 올바른 구조인지 확인
2. Check if `.env` file has required variables
2. `.env` 파일에 필요한 변수가 있는지 확인
3. Verify site name matches exactly (case-sensitive)
3. 사이트 이름이 정확히 일치하는지 확인 (대소문자 구분)

### Issue: "Connection failed"
### 문제: "연결 실패"

**Solution**:
**해결 방법**:

1. Verify database server is accessible from your network
1. 데이터베이스 서버가 네트워크에서 접근 가능한지 확인
2. Check firewall settings
2. 방화벽 설정 확인
3. Verify Windows Authentication credentials (if using)
3. Windows 인증 자격 증명 확인 (사용 중인 경우)
4. Test connection using SQL Server Management Studio
4. SQL Server Management Studio로 연결 테스트

### Issue: "site_config.json file not found"
### 문제: "site_config.json 파일을 찾을 수 없음"

**Solution**:
**해결 방법**:

1. Create the file at `data/api_keys/site_config.json`
1. `data/api_keys/site_config.json`에 파일 생성
2. Or use `.env` file as fallback
2. 또는 `.env` 파일을 폴백으로 사용

---

## 📚 Related Documentation
## 📚 관련 문서

- **`ENV_SETUP_GUIDE.md`** - Environment variable setup guide
- **`ENV_SETUP_GUIDE.md`** - 환경 변수 설정 가이드
- **`DB_DIRECT_ACCESS_GUIDE.md`** - Direct database access guide
- **`DB_DIRECT_ACCESS_GUIDE.md`** - 직접 데이터베이스 접속 가이드
- **`LOGIN_CREDENTIALS.md`** - User login credentials reference
- **`LOGIN_CREDENTIALS.md`** - 사용자 로그인 자격 증명 참조
- **`MIGRATION_GUIDE.md`** - Database migration guide
- **`MIGRATION_GUIDE.md`** - 데이터베이스 마이그레이션 가이드

---

## 📞 Quick Reference
## 📞 빠른 참조

### Configuration File Locations
### 설정 파일 위치

| File | Location | Purpose |
|------|----------|---------|
| `.env` | Project root | Environment variables |
| `site_config.json` | `data/api_keys/` | Site-specific config (recommended) |
| `config_users.py` | Project root | User credentials |
| `config_env.py` | Project root | Flask configuration |
| `progress_report.db` | Project root | SQLite database |

### Configuration Priority
### 설정 우선순위

1. `site_config.json` → 2. `.env` → 3. Default values

### Common Environment Variables
### 일반적인 환경 변수

```env
USE_DB_DIRECT_ACCESS=true
MANAD_DB_SERVER_{SITE}=server\instance
MANAD_DB_NAME_{SITE}=database_name
MANAD_DB_USE_WINDOWS_AUTH_{SITE}=true
```

---

**Last Updated**: 2026-01-27
**마지막 업데이트**: 2026-01-27
