# Sync 결과 차이 분석 및 해결 가이드

## 📊 문제 상황

개발 서버와 상용 서버에서 같은 소스 코드로 Force Sync를 실행했지만 결과가 다릅니다.

### 개발 서버 결과:
```
Synchronization Complete!
6 new incidents synced
100 existing incidents updated
0 tasks auto-generated for 0 Fall incidents
73 incident statuses updated
```

### 상용 서버 결과:
```
Synchronization Complete!
2 new incidents synced
150 existing incidents updated
0 tasks auto-generated for 65 Fall incidents  ← 문제!
0 incident statuses updated                   ← 문제!
```

## 🔍 원인 분석

소스 코드가 같아도 **데이터베이스 상태**가 다르면 결과가 달라집니다.

### Force Sync 동작 방식 (app.py, line 5873-5970)

```python
def force_sync_all():
    # 1. Full incident sync (30 days)
    sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
    
    # 2. Check for Fall incidents without tasks and generate them
    cursor.execute("""
        SELECT i.id, i.incident_id, i.incident_date, i.incident_type
        FROM cims_incidents i
        WHERE i.incident_type LIKE '%Fall%'
        AND i.status IN ('Open', 'Overdue')
        AND NOT EXISTS (
            SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id
        )
    """)
    # → 개발: 0개 찾음, 상용: 65개 찾음
    
    for inc in incidents_without_tasks:
        num_tasks = auto_generate_fall_tasks(inc[0], inc[2], cursor)
        # → 개발: 실행 안 됨, 상용: 65번 실행했지만 task 0개 생성!
    
    # 3. Progress note sync
    pn_sync_result = sync_progress_notes_from_manad_to_cims()
    
    # 4. Update incident statuses
    cursor.execute("""
        SELECT DISTINCT i.id
        FROM cims_incidents i
        JOIN cims_tasks t ON i.id = t.incident_id
        WHERE i.status IN ('Open', 'Overdue')
    """)
    # → 개발: 73개 찾음, 상용: 0개 찾음 (tasks가 없으니까!)
```

### 핵심 문제

**상용 서버에서 `auto_generate_fall_tasks()` 함수가 65번 호출되었지만 task를 하나도 생성하지 못했습니다!**

## 🔴 가능한 원인

### 1. Active Fall Policy가 없음 (가장 가능성 높음)

`auto_generate_fall_tasks()` 함수는 활성화된 Fall Policy를 찾아서 task를 생성합니다:

```python
def auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor):
    # Get Fall policy
    cursor.execute("""
        SELECT id, rules_json
        FROM cims_policies
        WHERE is_active = 1
    """)
    
    policies = cursor.fetchall()
    fall_policy = None
    
    for policy_row in policies:
        rules = json.loads(policy_row[1])
        association = rules.get('incident_association', {})
        if association.get('incident_type') == 'Fall':
            fall_policy = policy_row
            break
    
    if not fall_policy:
        logger.warning(f"No active Fall policy found for task generation")
        return 0  # ← Task 0개 생성!
```

**상용 서버에 Fall Policy가 없거나 비활성화되어 있을 가능성이 높습니다.**

### 2. cims_policies 테이블이 없음

Policy 마이그레이션이 안 되어 있을 수 있습니다.

### 3. Fall Policy의 visit_schedule이 비어있음

Policy는 있지만 rules_json이 잘못 설정되어 있을 수 있습니다.

## 🛠️ 진단 및 해결 방법

### Step 1: 개발 서버 상태 확인 (이미 완료)

```bash
cd /home/itsupport/DEV_code/ProgressReport2
python3 diagnose_sync_difference.py
```

**결과:**
- ✅ Fall Policy 존재: "Fall Management Policy V3" (3 phases)
- ✅ 73개 Fall incident 모두 task 있음
- ✅ 73개 incident가 status update 대상

### Step 2: 상용 서버 상태 확인

이 스크립트들을 상용 서버로 복사하고 실행:

```bash
# 1. 진단 스크립트 실행
python3 diagnose_sync_difference.py

# 2. 상세 문제 확인
python3 check_production_sync_issue.py
```

### Step 3: 문제에 따른 해결 방법

#### 시나리오 A: cims_policies 테이블이 없는 경우

```bash
# Policy 테이블 생성
python3 create_policy_tables.py

# 개발 서버에서 policy 데이터 export
sqlite3 progress_report.db ".dump cims_policies" > policies.sql

# 상용 서버로 파일 복사 후 import
sqlite3 progress_report.db < policies.sql
```

#### 시나리오 B: Active Policy가 없는 경우

Option 1: 개발 서버의 policy를 복사 (권장)
```bash
# 개발 서버
sqlite3 progress_report.db "SELECT * FROM cims_policies;" > policy_data.csv

# 상용 서버
# policy_data.csv를 보고 수동으로 INSERT 또는
# 개발 서버 DB의 cims_policies 테이블을 통째로 복사
```

Option 2: Policy 직접 활성화
```sql
UPDATE cims_policies 
SET is_active = 1 
WHERE name LIKE '%Fall%';
```

#### 시나리오 C: Fall Policy가 없는 경우

새로운 Fall Policy를 생성해야 합니다. 개발 서버의 policy 데이터를 export하여 사용하세요.

## 📋 Quick Fix (빠른 해결)

가장 빠른 방법은 개발 서버의 policy 데이터를 상용 서버에 복사하는 것입니다:

### 개발 서버에서:
```bash
cd /home/itsupport/DEV_code/ProgressReport2
sqlite3 progress_report.db ".mode insert cims_policies" ".output policy_export.sql" "SELECT * FROM cims_policies WHERE name = 'Fall Management Policy V3';" ".quit"
```

또는 더 간단하게:
```bash
sqlite3 progress_report.db "SELECT id, policy_id, name, description, version, effective_date, expiry_date, rules_json, is_active FROM cims_policies WHERE is_active = 1;" > active_policies.txt
```

### 상용 서버에서:

1. `active_policies.txt` 파일을 확인하여 policy가 있는지 확인
2. Policy가 없으면 개발 서버에서 복사
3. 다시 Force Sync 실행

## 🔧 수동 Policy 확인 방법

### SQLite 직접 접근:

```bash
sqlite3 progress_report.db

# Policy 확인
SELECT id, name, is_active FROM cims_policies;

# Fall Policy 상세 확인
SELECT rules_json FROM cims_policies WHERE name LIKE '%Fall%';

# Task 없는 Fall incidents 확인
SELECT COUNT(*) 
FROM cims_incidents 
WHERE incident_type LIKE '%Fall%'
  AND status IN ('Open', 'Overdue')
  AND NOT EXISTS (
    SELECT 1 FROM cims_tasks WHERE incident_id = cims_incidents.id
  );
```

## 📊 예상되는 결과

Policy 문제를 해결하고 다시 Force Sync를 실행하면:

```
Synchronization Complete!
X new incidents synced
Y existing incidents updated
Z tasks auto-generated for 65 Fall incidents  ← Z가 0보다 커야 정상!
W incident statuses updated                    ← W가 0보다 커야 정상!
```

## 🚨 주의사항

1. **상용 서버 작업 전 백업 필수!**
   ```bash
   cp progress_report.db progress_report.db.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Policy import 후 확인**
   - Policy가 제대로 import되었는지 확인
   - is_active = 1인지 확인
   - rules_json이 비어있지 않은지 확인

3. **로그 확인**
   - Force Sync 실행 중 에러가 없는지 logs 디렉토리 확인
   - `"No active Fall policy found"` 메시지가 있는지 확인

## 📝 체크리스트

상용 서버에서 다음을 확인하세요:

- [ ] `python3 diagnose_sync_difference.py` 실행
- [ ] `python3 check_production_sync_issue.py` 실행
- [ ] `cims_policies` 테이블 존재 확인
- [ ] Active Fall Policy 존재 확인
- [ ] Fall Policy의 visit_schedule 확인
- [ ] 문제 해결 후 Force Sync 재실행
- [ ] Task가 65개 이상 생성되는지 확인
- [ ] Status update가 0보다 큰지 확인

## 💡 추가 정보

### DB 상태가 다른 이유

1. **백업/복원 시점 차이**: 상용 서버 DB가 policy 마이그레이션 전 백업일 수 있음
2. **수동 데이터 수정**: 누군가 policy를 삭제하거나 비활성화했을 수 있음
3. **마이그레이션 미실행**: Policy 관련 마이그레이션 스크립트가 상용 서버에서 실행되지 않았을 수 있음

### 예방 방법

1. **자동 DB 백업 스크립트** 사용
2. **마이그레이션 로그** 기록
3. **개발/상용 환경 동기화 체크리스트** 작성
4. **Policy 설정 버전 관리** (JSON 파일로 export)

---

**작성자**: AI Assistant  
**작성일**: 2025-10-17  
**관련 파일**: 
- `app.py` (line 5496-5970)
- `diagnose_sync_difference.py`
- `check_production_sync_issue.py`

