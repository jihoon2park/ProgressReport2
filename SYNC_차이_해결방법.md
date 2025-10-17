# 🔍 Sync 결과 차이 해결 가이드

## 📊 문제 요약

**개발 서버:**
- ✅ 0 tasks auto-generated for 0 Fall incidents (모든 Fall incident에 이미 task 있음)
- ✅ 73 incident statuses updated (정상)

**상용 서버:**
- ❌ 0 tasks auto-generated for **65 Fall incidents** (task 생성 실패!)
- ❌ 0 incident statuses updated (task가 없어서 업데이트 불가)

## 🎯 핵심 원인

**상용 서버에 Fall Policy가 없거나 비활성화되어 있습니다.**

코드는 100% 같지만, **데이터베이스 상태**가 다릅니다:
- 개발: Fall Policy 있음 ✅
- 상용: Fall Policy 없음 ❌

## 🛠️ 해결 방법 (3단계)

### Step 1: 상용 서버에서 문제 확인

다음 파일들을 상용 서버로 복사:
```bash
- diagnose_sync_difference.py
- check_production_sync_issue.py
- export_fall_policy.py
```

상용 서버에서 실행:
```bash
cd /path/to/production
python3 diagnose_sync_difference.py
python3 check_production_sync_issue.py
```

### Step 2: Fall Policy Import

#### Option A: JSON 파일로 Import (권장, 가장 안전)

1. **개발 서버에서 이미 export 완료:**
   ```bash
   # 이미 생성된 파일:
   fall_policy_production.json
   ```

2. **파일을 상용 서버로 복사**

3. **상용 서버에서 import:**
   ```bash
   cd /path/to/production
   python3 export_fall_policy.py import fall_policy_production.json
   ```

#### Option B: SQLite 직접 복사 (빠르지만 주의 필요)

```bash
# 개발 서버
cd /home/itsupport/DEV_code/ProgressReport2
sqlite3 progress_report.db ".dump cims_policies" > policies.sql

# 상용 서버로 파일 복사 후
cd /path/to/production
sqlite3 progress_report.db < policies.sql
```

### Step 3: Force Sync 재실행

Dashboard에서 Force Sync 버튼 클릭 또는:
```bash
# API 직접 호출
curl -X POST http://localhost:5000/api/cims/force-sync \
  -H "Content-Type: application/json" \
  --cookie "session=YOUR_SESSION_COOKIE"
```

**예상 결과:**
```
Synchronization Complete!
X new incidents synced
Y existing incidents updated
780 tasks auto-generated for 65 Fall incidents  ← 이제 정상!
65 incident statuses updated                     ← 이제 정상!
```

## 📋 Quick Reference

### 생성된 파일들

| 파일명 | 용도 | 사용 방법 |
|--------|------|-----------|
| `diagnose_sync_difference.py` | DB 상태 진단 | `python3 diagnose_sync_difference.py` |
| `check_production_sync_issue.py` | 상세 문제 분석 | `python3 check_production_sync_issue.py` |
| `export_fall_policy.py` | Policy export/import | `python3 export_fall_policy.py [export\|import\|list]` |
| `fall_policy_production.json` | Export된 Fall Policy | 상용 서버로 복사하여 import |
| `SYNC_DIFFERENCE_GUIDE.md` | 상세 가이드 (영문) | 참고 문서 |

### 명령어 모음

```bash
# 개발 서버
python3 diagnose_sync_difference.py              # 현재 상태 확인
python3 export_fall_policy.py list               # Policy 목록
python3 export_fall_policy.py export policy.json # Policy export

# 상용 서버
python3 diagnose_sync_difference.py              # 문제 확인
python3 check_production_sync_issue.py           # 상세 분석
python3 export_fall_policy.py import policy.json # Policy import
python3 export_fall_policy.py list               # Import 확인
```

## ⚠️ 주의사항

### 1. 백업 필수!
```bash
# 상용 서버 작업 전
cp progress_report.db progress_report.db.backup_$(date +%Y%m%d_%H%M%S)
```

### 2. 검증 체크리스트

Import 후 다음을 확인:

- [ ] `python3 export_fall_policy.py list` → Active Policy 확인
- [ ] Fall Policy가 "🟢 Active" 상태인지 확인
- [ ] Visit Schedule: 3 phases 확인
- [ ] Force Sync 재실행
- [ ] Task 생성 개수가 0보다 큰지 확인
- [ ] Status update 개수가 0보다 큰지 확인
- [ ] Dashboard에서 Fall incidents에 tasks가 보이는지 확인

### 3. 문제가 계속되면

Logs 확인:
```bash
cd logs
tail -f app.log | grep -i "fall\|policy\|task"
```

DB 직접 확인:
```bash
sqlite3 progress_report.db
> SELECT * FROM cims_policies WHERE is_active = 1;
> SELECT COUNT(*) FROM cims_tasks;
```

## 📞 추가 지원

문제가 해결되지 않으면:

1. `logs/app.log` 파일 확인
2. 에러 메시지 검색: `grep -i "error\|fail" logs/app.log`
3. Policy 상태 재확인: `python3 export_fall_policy.py list`
4. DB 스키마 확인: `sqlite3 progress_report.db ".schema cims_policies"`

## 🎓 배운 점

### 왜 이런 일이 발생했나?

1. **소스 코드는 같지만 DB 상태가 다름**
   - 개발: Policy 마이그레이션 완료
   - 상용: Policy 마이그레이션 미완료 또는 DB 복원 시 누락

2. **Sync는 DB 의존적**
   - Fall Policy가 없으면 task 생성 불가
   - Task가 없으면 status update 불가

3. **환경 동기화의 중요성**
   - 소스 코드만 같아서는 부족
   - DB 스키마와 기본 데이터(Policy 등)도 동기화 필요

### 예방 방법

1. **배포 체크리스트 작성**
   ```
   [ ] 소스 코드 업데이트
   [ ] 마이그레이션 스크립트 실행
   [ ] Policy 데이터 확인
   [ ] Force Sync 테스트
   [ ] 로그 확인
   ```

2. **자동화 스크립트**
   - 배포 시 자동으로 schema 버전 확인
   - 필수 데이터(Policy 등) 존재 여부 검증

3. **모니터링**
   - Force Sync 결과를 로그에 기록
   - Task 생성 실패 시 alert 발생

---

**작성일**: 2025-10-17  
**개발 서버 상태**: ✅ Fall Policy 정상  
**Export 파일**: `fall_policy_production.json` (준비 완료)

