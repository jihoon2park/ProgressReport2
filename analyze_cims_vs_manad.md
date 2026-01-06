# CIMS DB vs MANAD DB 직접 쿼리 분석

## 현재 CIMS DB에 저장되는 데이터

### 1. **cims_incidents** 테이블
- **MANAD에서 가져온 데이터:**
  - `manad_incident_id`: MANAD 원본 ID
  - `incident_type`, `severity`, `incident_date`, `description`
  - `resident_id`, `resident_name`, `site`
  - `risk_rating` (MANAD의 RiskRatingName)
  - `is_review_closed` (MANAD의 IsReviewClosed)
  - `is_ambulance_called` (MANAD의 IsAmbulanceCalled)
  - `is_admitted_to_hospital` (MANAD의 IsAdmittedToHospital)
  - `is_major_inj

ury` (MANAD의 IsMajorInjury)
  - `reviewed_date` (MANAD의 ReviewedDate)
  - `status_enum_id` (MANAD의 StatusEnumId: 0=Open, 1=In Progress, 2=Closed)

- **CIMS에서 추가/수정하는 데이터:**
  - `status`: CIMS에서 관리 (Open, Closed, In Progress, Overdue)
    - MANAD의 StatusEnumId를 기반으로 하지만 CIMS에서 "Overdue" 추가 가능
  - `fall_type`: CIMS에서 계산 (witnessed, unwitnessed, unknown)
    - MANAD의 IsWitnessed를 기반으로 하지만 CIMS에서 추가 계산/분류

### 2. **cims_tasks** 테이블 (MANAD에 없음)
- 정책 기반 자동 생성된 태스크
- Fall 인시던트에 대해 자동으로 12개 태스크 생성
- Task 완료 상태, 할당 정보 등

### 3. **cims_policies** 테이블 (MANAD에 없음)
- 정책 규칙 및 버전 관리

### 4. **cims_audit_logs** 테이블 (MANAD에 없음)
- 감사 로그

## MANAD DB에서 직접 쿼리 가능한 데이터

`manad_db_connector.py`의 `fetch_incidents()` 함수에서:
- `StatusEnumId`: 0=Open, 1=In Progress, 2=Closed
- `IsReviewClosed`: Boolean
- `IsAmbulanceCalled`: Boolean
- `IsAdmittedToHospital`: Boolean
- `IsMajorInjury`: Boolean
- `ReviewedDate`: Timestamp
- `IsWitnessed`: Boolean (fall_type 계산에 사용 가능)
- `RiskRatingName`: String
- `SeverityRating`: String

## 대시보드 KPI가 CIMS DB를 사용하는 이유

### 현재 사용 중인 CIMS 전용 필드:
1. **`status`**: CIMS에서 관리 (Open, Closed, In Progress, Overdue)
   - MANAD의 StatusEnumId를 변환하지만 "Overdue"는 CIMS에서 추가
2. **`fall_type`**: CIMS에서 계산 (witnessed, unwitnessed, unknown)
   - MANAD의 IsWitnessed를 기반으로 하지만 추가 계산 필요
3. **`is_review_closed`**: MANAD에서 가져오지만 CIMS DB에 저장됨

## MANAD DB 직접 쿼리로 전환 가능 여부

### ✅ 가능한 부분:
1. **기본 인시던트 데이터**: MANAD DB에서 직접 쿼리 가능
2. **Status**: MANAD의 StatusEnumId를 직접 사용 (0=Open, 2=Closed, 1=In Progress)
3. **IsReviewClosed, IsAmbulanceCalled 등**: MANAD DB에 직접 존재
4. **IsWitnessed**: MANAD DB에 직접 존재 (fall_type 계산 가능)

### ❌ 불가능한 부분:
1. **cims_tasks**: MANAD에 없음 (정책 기반 자동 생성)
2. **cims_policies**: MANAD에 없음
3. **Overdue 상태**: CIMS에서 계산하는 상태 (MANAD에는 없음)
4. **fall_type**: CIMS에서 계산하는 필드 (MANAD의 IsWitnessed를 기반으로 하지만 추가 로직 필요)

## 결론

### 대시보드 KPI만 MANAD DB 직접 쿼리로 전환 가능:
- **장점:**
  - 실시간 데이터 (동기화 지연 없음)
  - 개발/운영 서버 간 데이터 불일치 문제 해결
  - CIMS DB 동기화 불필요

- **단점:**
  - "Overdue" 상태는 MANAD에 없으므로 별도 계산 필요
  - fall_type은 MANAD의 IsWitnessed를 기반으로 계산 가능
  - 매번 MANAD DB 쿼리 (성능 고려 필요)

### CIMS DB가 여전히 필요한 이유:
1. **cims_tasks**: 정책 기반 자동 생성된 태스크 관리
2. **cims_policies**: 정책 엔진
3. **cims_audit_logs**: 감사 로그
4. **Task 완료 상태**: CIMS에서 관리

## 권장 사항

**대시보드 KPI는 MANAD DB에서 직접 쿼리로 전환:**
- 실시간 데이터 보장
- 동기화 문제 해결
- 개발/운영 서버 간 데이터 일치

**CIMS DB는 Task 관리용으로만 유지:**
- cims_tasks, cims_policies, cims_audit_logs는 계속 사용

