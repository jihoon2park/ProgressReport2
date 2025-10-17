# Severity NULL 문제 해결 가이드

## 📊 문제 요약

### 로그 에러 (상용 서버):
```
Error processing incident 400: NOT NULL constraint failed: cims_incidents.severity
Error processing incident 390: NOT NULL constraint failed: cims_incidents.severity
Error processing incident 378: NOT NULL constraint failed: cims_incidents.severity
... (총 15개 incidents 실패)
```

### 결과 비교:

| 항목 | 개발 서버 | 상용 서버 | 차이 |
|------|----------|----------|------|
| West Park updated | 78개 | 75개 | **-3개** |
| Yankalilla updated | 102개 | 91개 | **-11개** |
| Total sync | 102개 | 91개 | **-11개** |
| Open incidents | 116개 | 94개 | **-22개** |
| Dashboard (7일) | 30개 | 29개 | -1개 |

## 🔍 근본 원인

### 1. DB 스키마 차이

**개발 서버 (정상):**
```sql
CREATE TABLE cims_incidents (
    ...
    severity VARCHAR(20),  -- NULL 허용
    ...
);
```

**상용 서버 (문제):**
```sql
CREATE TABLE cims_incidents (
    ...
    severity VARCHAR(20) NOT NULL,  -- NOT NULL 제약!
    ...
);
```

### 2. MANAD Plus API 데이터 이슈

일부 incident 데이터에 `SeverityRating`과 `RiskRatingName` 둘 다 없는 경우 발생:

```python
# app.py line 5781, 5819 (수정 전)
incident.get('SeverityRating') or incident.get('RiskRatingName')
# → 둘 다 None이면 None 반환 → NOT NULL 제약 위반!
```

**실패한 Incidents:**
- West Park: 400, 390, 378, 388
- Yankalilla: 207, 222, 206, 230, 224, 215, 219, 223, 234, 227, 229

→ **총 15개의 incidents가 DB에 저장되지 못함**

→ **Open incidents 수가 116 → 94로 감소**

→ **대시보드 KPI도 영향 받음**

## ✅ 해결 방법

### Step 1: 코드 수정 (이미 완료)

`app.py` 두 곳을 수정했습니다:

#### Line 5819 (INSERT - 새 incident):
```python
# BEFORE
incident.get('SeverityRating') or incident.get('RiskRatingName'),

# AFTER
incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',
```

#### Line 5781 (UPDATE - 기존 incident):
```python
# BEFORE
incident.get('SeverityRating') or incident.get('RiskRatingName'),

# AFTER  
incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',
```

### Step 2: 상용 서버에 코드 배포

```bash
# 1. 현재 변경사항 커밋
git add app.py
git commit -m "Fix: Add default 'Unknown' value for severity to prevent NULL constraint errors"

# 2. 상용 서버로 push
git push origin main  # 또는 배포 브랜치

# 3. 상용 서버에서 pull
# (상용 서버에서)
cd /path/to/production
git pull origin main
```

### Step 3: 상용 서버 재시작

```bash
# 상용 서버에서
# Windows:
.\START_SYSTEMS.bat

# Linux:
./start_server.sh
```

### Step 4: Force Sync 재실행

1. 상용 서버 Dashboard 접속
2. Force Sync 버튼 클릭
3. 이번에는 모든 incidents가 성공적으로 저장됨

**예상 결과:**
```
Synchronization Complete!
X new incidents synced
Y existing incidents updated (에러 없이 모두 성공!)
0 tasks auto-generated for Z Fall incidents
W incident statuses updated
```

## 🔧 추가 해결 방법 (선택사항)

만약 이미 저장된 데이터에 NULL severity가 있다면:

### Option 1: 진단 및 수정 스크립트 실행

```bash
# 상용 서버에서
python3 fix_severity_issue.py
```

이 스크립트는:
1. DB 스키마 확인
2. severity가 NULL인 레코드 확인
3. 백업 생성
4. NULL 값을 'Unknown'으로 업데이트

### Option 2: 수동 SQL 실행

```sql
-- 백업
CREATE TABLE cims_incidents_backup_manual AS 
SELECT * FROM cims_incidents;

-- NULL severity 확인
SELECT COUNT(*) FROM cims_incidents WHERE severity IS NULL;

-- NULL → 'Unknown'으로 업데이트
UPDATE cims_incidents 
SET severity = 'Unknown' 
WHERE severity IS NULL;

-- 확인
SELECT COUNT(*) FROM cims_incidents WHERE severity IS NULL;
-- 결과: 0이어야 함
```

## 📊 검증

### 1. 로그 확인

다음 에러가 더 이상 나타나지 않아야 합니다:
```
Error processing incident XXX: NOT NULL constraint failed: cims_incidents.severity
```

### 2. Sync 결과 확인

Force Sync 후 로그:
```
✅ West Park: 0 new, 78 updated    (에러 없음!)
✅ Yankalilla: 0 new, 102 updated  (에러 없음!)
✅ Incident sync completed: 0 new, 102 updated
```

### 3. Open Incidents 수 확인

```python
# 진단 스크립트 실행
python3 compare_dashboard_kpis.py
```

**예상 결과:**
- Open incidents: 116개 (개발 서버와 동일)
- Dashboard (7일): 30-31개 (시간 경계선에 따라 ±1)

### 4. DB 직접 확인

```bash
sqlite3 progress_report.db

# NULL severity 확인
sqlite> SELECT COUNT(*) FROM cims_incidents WHERE severity IS NULL;
# 결과: 0

# severity 분포 확인
sqlite> SELECT severity, COUNT(*) FROM cims_incidents GROUP BY severity;
# 'Unknown' 포함한 분포 확인

sqlite> .quit
```

## 📋 체크리스트

상용 서버에서:

- [ ] `app.py` 업데이트 완료
- [ ] 서버 재시작 완료
- [ ] Force Sync 실행 완료
- [ ] 로그에서 "NOT NULL constraint" 에러 없음 확인
- [ ] Open incidents 수가 116개 근처로 증가 확인
- [ ] Dashboard KPI가 정상 표시 확인
- [ ] `fix_severity_issue.py` 실행 (필요시)
- [ ] NULL severity 레코드 0개 확인

## 💡 예방 조치

### 1. DB 스키마 표준화

개발/상용 서버의 DB 스키마를 동일하게 유지:

```sql
-- 표준 스키마 (severity NULL 허용)
CREATE TABLE cims_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(100) UNIQUE NOT NULL,
    manad_incident_id INTEGER UNIQUE,
    site VARCHAR(100),
    resident_id VARCHAR(50),
    resident_name VARCHAR(200),
    incident_type VARCHAR(200),
    incident_date TIMESTAMP,
    severity VARCHAR(20),  -- NOT NULL 제거!
    description TEXT,
    initial_actions_taken TEXT,
    location VARCHAR(200),
    witnesses TEXT,
    reported_by INTEGER,
    reported_by_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_by) REFERENCES users(id)
);
```

### 2. 데이터 검증

API에서 받은 데이터에 대한 방어적 코딩:

```python
# 좋은 예
severity = (
    incident.get('SeverityRating') or 
    incident.get('RiskRatingName') or 
    'Unknown'
)

# 또는
def get_severity(incident):
    """Get severity with fallback to Unknown"""
    severity = incident.get('SeverityRating') or incident.get('RiskRatingName')
    return severity if severity else 'Unknown'
```

### 3. 정기 모니터링

```bash
# 매일 또는 매주 실행
python3 fix_severity_issue.py  # check mode로 실행
```

### 4. 배포 체크리스트

새 코드 배포 시:
1. 개발 서버에서 테스트
2. DB 백업
3. 스키마 변경사항 확인
4. Force Sync 테스트
5. 로그 모니터링

## 🔗 관련 파일

| 파일 | 용도 |
|------|------|
| `app.py` | 수정된 메인 코드 (line 5781, 5819) |
| `fix_severity_issue.py` | 진단 및 수정 스크립트 |
| `compare_dashboard_kpis.py` | Dashboard 차이 분석 |
| `SEVERITY_NULL_ISSUE_FIX.md` | 이 가이드 |

## ❓ FAQ

### Q1: 왜 개발 서버는 문제 없었나요?

**A:** 개발 서버의 DB 스키마는 `severity`를 NULL 허용으로 설정되어 있습니다. 
상용 서버는 이전 마이그레이션 시 NOT NULL 제약이 추가된 것으로 보입니다.

### Q2: 코드만 수정하면 기존 데이터는?

**A:** 기존에 저장 실패한 incidents는 자동으로 복구되지 않습니다. 
Force Sync를 다시 실행하면 API에서 재동기화됩니다.

### Q3: 'Unknown' severity는 문제없나요?

**A:** 'Unknown'은 적절한 기본값입니다. 실제 severity가 없는 incidents를 
식별하고 추후 수동으로 업데이트할 수 있습니다.

### Q4: DB 스키마를 변경해야 하나요?

**A:** 필수는 아닙니다. 코드 수정만으로도 문제가 해결됩니다. 
하지만 개발/상용 환경의 스키마를 동일하게 유지하는 것이 좋습니다.

---

**작성일**: 2025-10-17  
**관련 이슈**: Severity NOT NULL constraint violation  
**해결 상태**: ✅ 코드 수정 완료, 배포 대기

