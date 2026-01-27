# Database Migration Guide
# 데이터베이스 마이그레이션 가이드

Follow this guide when running the app for the first time in a local environment or when database migration is needed.
로컬 환경에서 앱을 처음 실행하거나 데이터베이스 마이그레이션이 필요한 경우 이 가이드를 따르세요.

## 🚀 Quick Start
## 🚀 빠른 시작

### Windows Users
### Windows 사용자

1. **Run batch file** (Simplest method)
1. **배치 파일 실행** (가장 간단한 방법)
   ```cmd
   run_migration.bat
   ```

2. Or **Run Python script directly**
2. 또는 **Python 스크립트 직접 실행**
   ```cmd
   python run_migration.py
   ```

### Linux/Mac Users
### Linux/Mac 사용자

```bash
python3 run_migration.py
```

## 📋 What the Migration Script Does
## 📋 마이그레이션 스크립트가 수행하는 작업

This script automatically performs the following operations:
이 스크립트는 다음 작업을 자동으로 수행합니다:

1. **Base Database Schema Creation**
1. **기본 데이터베이스 스키마 생성**
   - Creates core tables: `users`, `fcm_tokens`, `access_logs`, etc.
   - `users`, `fcm_tokens`, `access_logs` 등 핵심 테이블 생성
   - Creates cache tables: `clients_cache`, `care_areas`, `event_types`, etc.
   - `clients_cache`, `care_areas`, `event_types` 등 캐시 테이블 생성
   - Creates configuration tables: `sites`, `sync_status`, etc.
   - `sites`, `sync_status` 등 설정 테이블 생성

2. **CIMS Database Schema Creation**
2. **CIMS 데이터베이스 스키마 생성**
   - `cims_policies` - Policy management table
   - `cims_policies` - 정책 관리 테이블
   - `cims_incidents` - Incident management table
   - `cims_incidents` - 인시던트 관리 테이블
   - `cims_tasks` - Task management table
   - `cims_tasks` - 태스크 관리 테이블
   - `cims_progress_notes` - Progress notes table
   - `cims_progress_notes` - 진행 노트 테이블
   - `cims_audit_logs` - Audit log table
   - `cims_audit_logs` - 감사 로그 테이블
   - `cims_notifications` - Notifications table
   - `cims_notifications` - 알림 테이블
   - `cims_task_assignments` - Task assignments table
   - `cims_task_assignments` - 태스크 할당 테이블

3. **CIMS Incidents Table Column Additions**
3. **CIMS 인시던트 테이블 컬럼 추가**
   - `risk_rating` - Risk rating
   - `risk_rating` - 위험 등급
   - `is_review_closed` - Review completion status
   - `is_review_closed` - 검토 완료 여부
   - `is_ambulance_called` - Ambulance call status
   - `is_ambulance_called` - 구급차 호출 여부
   - `is_admitted_to_hospital` - Hospital admission status
   - `is_admitted_to_hospital` - 병원 입원 여부
   - `is_major_injury` - Major injury status
   - `is_major_injury` - 중상 여부
   - `reviewed_date` - Review date/time
   - `reviewed_date` - 검토 일시
   - `status_enum_id` - Status enumeration ID
   - `status_enum_id` - 상태 열거형 ID

4. **Database Verification**
4. **데이터베이스 검증**
   - Verifies all tables are created correctly
   - 모든 테이블이 올바르게 생성되었는지 확인
   - Checks record count for each table
   - 테이블별 레코드 수 확인

## ⚠️ Important Notes
## ⚠️ 주의사항

- **Existing Data Preservation**: This script preserves existing tables and data. Tables that already exist will be skipped.
- **기존 데이터 보존**: 이 스크립트는 기존 테이블과 데이터를 보존합니다. 이미 존재하는 테이블은 건너뜁니다.
- **Backup Recommended**: If you have important data, backup before migration:
- **백업 권장**: 중요한 데이터가 있는 경우 마이그레이션 전에 백업하세요:
  ```cmd
  copy progress_report.db progress_report.db.backup
  ```

## 🔍 Troubleshooting
## 🔍 문제 해결

### When Migration Fails
### 마이그레이션이 실패하는 경우

1. **Check Log File**
1. **로그 파일 확인**
   ```
   migration.log
   ```
   Detailed error information is recorded in this file.
   이 파일에 상세한 오류 정보가 기록됩니다.

2. **Common Issues**
2. **일반적인 문제들**

   **Issue**: `database_schema.sql file not found`
   **문제**: `database_schema.sql 파일을 찾을 수 없습니다`
   - **Solution**: Run the script from the project root directory.
   - **해결**: 프로젝트 루트 디렉토리에서 스크립트를 실행하세요.

   **Issue**: `Permission denied` or `Access denied`
   **문제**: `Permission denied` 또는 `Access denied`
   - **Solution**: The database file may be in use by another process. Close the app and try again.
   - **해결**: 데이터베이스 파일이 다른 프로세스에서 사용 중일 수 있습니다. 앱을 종료한 후 다시 시도하세요.

   **Issue**: `Python is not installed`
   **문제**: `Python이 설치되어 있지 않습니다`
   - **Solution**: Install Python 3.11 or higher.
   - **해결**: Python 3.11 이상을 설치하세요.

3. **Manual Migration**
3. **수동 마이그레이션**

   If the migration script fails, you can run these commands manually in order:
   마이그레이션 스크립트가 실패하는 경우, 다음 순서로 수동 실행할 수 있습니다:

   ```cmd
   # 1. Create base schema
   # 1. 기본 스키마 생성
   python init_database.py

   # 2. Create CIMS tables
   # 2. CIMS 테이블 생성
   python create_cims_tables.py

   # 3. Add CIMS incidents columns
   # 3. CIMS 인시던트 컬럼 추가
   python migrate_cims_schema.py
   ```

## ✅ After Migration Completion
## ✅ 마이그레이션 완료 후

Once migration is completed successfully:
마이그레이션이 성공적으로 완료되면:

1. **Run Application**
1. **앱 실행**
   ```cmd
   python app.py
   ```

2. **Or Run Flask Development Server**
2. **또는 Flask 개발 서버 실행**
   ```cmd
   flask run
   ```

3. **Access in Browser**
3. **브라우저에서 접속**
   ```
   http://localhost:5000
   ```

## 📞 Need Additional Help?
## 📞 추가 도움이 필요한 경우

- Check log file (`migration.log`)
- 로그 파일 (`migration.log`) 확인
- Refer to project README.md
- 프로젝트 README.md 참조
- Contact development team
- 개발팀에 문의

---

**Last Updated**: 2026-01-27
**마지막 업데이트**: 2026-01-27
