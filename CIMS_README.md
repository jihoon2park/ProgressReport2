# CIMS - Compliance-Driven Incident Management System

## 🏥 Overview

CIMS (Compliance-Driven Incident Management System)는 요양원에서 발생하는 모든 인시던트(낙상, 피부 손상, 투약 오류 등)에 대해 회사의 복잡하고 자주 업데이트되는 정책을 자동으로 적용하여, 간호사와 케어러가 필요한 모든 진행 노트와 후속 조치를 빠뜨리지 않고 규정된 시간 내에 완료하도록 보장하는 시스템입니다.

**MANAD Plus 통합**: CIMS는 MANAD Plus 시스템과 완전히 통합되어, Progress Note 작성은 MANAD Plus에서 처리하고, CIMS는 스케줄링과 컴플라이언스 추적에 집중합니다.

## 🎯 주요 목표

- **자동 정책 적용**: 인시던트 발생 시 관련 정책을 자동으로 적용하여 필요한 태스크 생성
- **규정 준수 보장**: 모든 태스크가 정해진 시간 내에 완료되도록 모니터링
- **책임 추적**: 모든 활동에 대한 완전한 감사 로그 유지
- **실시간 알림**: 마감 임박 및 지연된 태스크에 대한 자동 알림
- **외부 시스템 통합**: MANAD Plus와의 완전한 연동을 통한 효율적인 워크플로우

## 🚀 새로운 기능

### 1. MANAD Plus 통합 시스템
- **폴링 기반 연동**: MANAD Plus API에서 새로운 인시던트 자동 감지
- **이중 확인 시스템**: MANAD Plus에서 Progress Note 작성 → CIMS에서 완료 확인
- **딥링크 지원**: 모바일에서 MANAD Plus 앱으로 직접 연결
- **오프라인 모드**: 네트워크 없이도 태스크 완료 확인 가능

### 2. 사용자 역할 시스템
- **Admin**: 사용자 관리, 정책 업로드/편집, 최종 인시던트 승인, 통합 서비스 관리
- **Registered Nurse (RN)**: MANAD Plus에서 인시던트 보고, 태스크 완료 확인
- **Carer**: 제한된 인시던트 보고, 간단한 태스크 완료 확인
- **Clinical Manager**: 전문 태스크 할당, 검토 및 승인, 컴플라이언스 모니터링

### 3. 정책 엔진
- JSON 기반 정책 규칙 저장
- 인시던트 유형과 심각도에 따른 자동 태스크 생성
- 버전 관리 및 유효 기간 설정
- MANAD Plus 인시던트 데이터 기반 자동 트리거

### 4. 태스크 관리 시스템
- **모바일 최적화 대시보드**: 터치 친화적 인터페이스
- **확인 기반 완료**: MANAD Plus 작업 완료 후 CIMS에서 확인
- **실시간 카운트다운 타이머**: 긴급도별 시각적 표시
- **오프라인 동기화**: 연결 복구 시 자동 데이터 전송

### 5. 관리자 대시보드
- **실시간 KPI**: 규정 준수율, 미준수 태스크, 미처리 사고
- **긴급 알림 시스템**: 기한 초과 태스크 실시간 모니터링
- **위험 분석**: 사고 유형별 차트, 담당자별 컴플라이언스 현황
- **통합 서비스 제어**: MANAD Plus 연동 상태 관리

### 6. 감사 로그 시스템
- **이중 추적**: MANAD Plus 작업 + CIMS 확인 기록
- **컴플라이언스 타임스탬프**: 로컬 디바이스 시간 기록
- **불변 로그**: 법적 증거로 사용 가능한 완전한 감사 추적

## 📋 데이터베이스 구조

### 핵심 테이블
- **cims_policies**: 정책 규칙 및 버전 관리
- **cims_incidents**: 인시던트 정보 및 분류 (MANAD Plus 연동 ID 포함)
- **cims_tasks**: 태스크 할당 및 진행 상황 (완료 방식 추적)
- **cims_audit_logs**: 감사 로그 및 책임 추적 (MANAD Plus 통합 로그)
- **cims_notifications**: 알림 및 알림 관리
- **system_settings**: MANAD Plus 연동 설정 및 상태

### MANAD Plus 통합 필드
- **manad_incident_id**: MANAD Plus의 원본 인시던트 ID
- **completion_method**: 태스크 완료 방식 (direct/manad_plus_confirmation)
- **manad_last_checked_at**: 마지막 폴링 시간

## 🛠️ 설치 및 설정

### 1. 시스템 요구사항
- Python 3.7+
- SQLite 3
- Flask 3.1.1+
- 기존 Progress Report System

### 2. 설치 단계

#### 자동 설치 (권장)
```bash
# 1. CIMS 시작 스크립트 실행
start_cims.bat

# 또는 수동으로:
python init_cims_database.py
```

#### 수동 설치
```bash
# 1. 데이터베이스 스키마 적용
python init_cims_database.py

# 2. 애플리케이션 시작
python app.py
```

### 3. Access Methods
- **CIMS Integrated Dashboard**: http://127.0.0.1:5000/integrated_dashboard (Role-based auto-switching)
- **Legacy CIMS Dashboard**: http://127.0.0.1:5000/incident_dashboard2 (Redirects to integrated dashboard)
- **Legacy Admin Dashboard**: http://127.0.0.1:5000/admin_dashboard (Redirects to integrated dashboard)
- **Mobile Task Dashboard**: http://127.0.0.1:5000/mobile_dashboard
- **Policy Management Interface**: http://127.0.0.1:5000/policy_admin
- **Legacy System**: http://127.0.0.1:5000/

## 🎮 사용 방법

### 1. MANAD Plus 통합 워크플로우
1. **인시던트 발생**: MANAD Plus에서 인시던트 보고
2. **자동 감지**: CIMS Integrator가 폴링으로 새 인시던트 감지
3. **태스크 생성**: Policy Engine이 자동으로 관련 태스크 생성
4. **알림 전송**: 담당자에게 태스크 할당 알림

### 2. 태스크 완료 프로세스 (MANAD Plus 통합)
1. **모바일 대시보드**: 할당된 태스크 확인
2. **"START NOTE" 클릭**: 태스크 완료 확인 페이지로 이동
3. **MANAD Plus 이동**: "GO TO MANAD PLUS" 버튼으로 외부 시스템 접속
4. **Progress Note 작성**: MANAD Plus에서 실제 문서 작성
5. **완료 확인**: CIMS로 돌아와서 완료 확인 체크
6. **컴플라이언스 기록**: 타임스탬프와 함께 감사 로그 생성

### 3. 관리자 기능
1. **관리자 대시보드**: 실시간 KPI 및 컴플라이언스 모니터링
2. **정책 관리**: 시각적 정책 편집기로 규칙 생성/수정
3. **통합 서비스 제어**: MANAD Plus 연동 상태 관리
4. **사용자 관리**: 역할별 권한 설정 및 관리

### 4. 모바일 최적화 기능
1. **터치 인터페이스**: 모바일 친화적 태스크 관리
2. **오프라인 모드**: 네트워크 없이도 태스크 완료 확인 가능
3. **딥링크 지원**: MANAD Plus 앱으로 직접 연결
4. **실시간 동기화**: 연결 복구 시 자동 데이터 전송

## 📊 정책 예시

### Fall Management Policy
```json
{
  "policy_name": "Fall Management Policy V3",
  "policy_id": "FALL-001",
  "rule_sets": [
    {
      "name": "High Severity Fall Protocol",
      "trigger_condition": {
        "incident_field": "type",
        "operator": "EQUALS",
        "value": "Fall",
        "AND": [
          {
            "incident_field": "severity",
            "operator": "IN",
            "value": ["High", "Injury Suspected"]
          }
        ]
      },
      "tasks_to_generate": [
        {
          "task_name": "Respond to Fall & Check Vitals (Step 6)",
          "assigned_role": "All Staff",
          "due_offset": 5,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Initial Response Check"
        },
        {
          "task_name": "Post Fall Assessment & Injury Check (Step 7)",
          "assigned_role": "Registered Nurse",
          "due_offset": 30,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Dynamic Form - Post Fall Assessment"
        }
      ]
    }
  ]
}
```

## 🔧 API 엔드포인트

### 태스크 관리 (MANAD Plus 통합)
- `GET /api/v1/tasks/me` - 사용자 태스크 조회
- `GET /api/v1/tasks/{task_id}` - 특정 태스크 상세 정보
- `POST /api/v1/tasks/{task_id}/confirm-completion` - MANAD Plus 완료 확인
- `GET /api/v1/tasks/overdue` - 기한 초과 태스크 조회

### 인시던트 관리
- `POST /api/v1/incidents` - 새 인시던트 생성 (직접 보고)
- `GET /api/v1/analytics/compliance-summary` - 컴플라이언스 요약
- `GET /api/v1/analytics/incidents-by-type` - 사고 유형별 분석

### MANAD Plus 통합
- `GET /api/v1/integrator/status` - 통합 서비스 상태 조회
- `POST /api/v1/integrator/start` - 통합 서비스 시작
- `POST /api/v1/integrator/stop` - 통합 서비스 중지

### 정책 관리
- `GET /api/cims/policies` - 정책 목록 조회
- `POST /api/cims/policies` - 새 정책 생성
- `PUT /api/cims/policies/{id}` - 정책 업데이트

## 🎨 사용자 인터페이스

### 관리자 대시보드
- **실시간 KPI**: 규정 준수율, 미준수 태스크, 미처리 사고
- **긴급 알림**: 기한 초과 태스크 실시간 모니터링
- **위험 분석**: 사고 유형별 차트, 담당자별 컴플라이언스 현황
- **통합 서비스 제어**: MANAD Plus 연동 상태 관리

### 모바일 태스크 대시보드
- **터치 최적화**: 모바일 친화적 인터페이스
- **긴급도 우선**: 기한 초과 → 긴급 → 일반 순서 정렬
- **실시간 카운트다운**: 남은 시간 시각적 표시
- **오프라인 지원**: 네트워크 없이도 작업 가능

### 태스크 완료 확인 페이지
- **MANAD Plus 연동**: 외부 시스템으로 직접 연결
- **이중 확인 시스템**: 외부 작업 완료 후 CIMS 확인
- **컴플라이언스 타임스탬프**: 로컬 디바이스 시간 기록
- **오프라인 동기화**: 연결 복구 시 자동 전송

### 정책 관리 인터페이스
- **시각적 편집기**: IF-THEN 로직 기반 규칙 생성
- **JSON 미리보기**: 실시간 정책 규칙 확인
- **버전 관리**: 정책 버전 및 유효 기간 설정
- **검색 및 필터링**: 상태, 유형별 정책 관리

## 🔒 보안 및 규정 준수

### 인증 및 권한
- 개인 계정 필수 (익명 접근 불가)
- 역할 기반 접근 제어 (RBAC)
- 자동 로그아웃 정책

### 감사 추적
- 모든 중요 활동 기록
- 불변 감사 로그
- 법적 증거로 활용 가능

## 🚨 알려진 제한사항

1. **MANAD Plus API**: 실제 MANAD Plus API 연동을 위해서는 API 엔드포인트 설정 필요
2. **푸시 알림**: FCM 푸시 알림은 별도 설정 필요
3. **딥링크**: MANAD Plus 앱이 설치되어 있어야 완전한 딥링크 기능 사용 가능

## 🔄 기존 시스템과의 통합

CIMS는 기존 Progress Report System과 MANAD Plus와 완전히 통합되어 있습니다:

### 기존 시스템 통합
- 기존 사용자 인증 시스템 활용
- 기존 데이터베이스에 새 테이블 추가
- 기존 네비게이션에 CIMS 링크 추가
- 기존 기능에 영향 없음

### MANAD Plus 통합
- **폴링 기반 연동**: MANAD Plus API에서 인시던트 자동 감지
- **이중 확인 시스템**: 외부 시스템 작업 + CIMS 확인
- **딥링크 지원**: 모바일에서 MANAD Plus 앱으로 직접 연결
- **오프라인 동기화**: 네트워크 복구 시 자동 데이터 전송

## 📞 지원 및 문의

시스템 관련 문의사항이나 기술 지원이 필요한 경우:
1. 시스템 로그 확인
2. 감사 로그에서 오류 추적
3. 개발팀에 문의

## 🔮 향후 개발 계획

1. **MANAD Plus 완전 통합**
   - 실제 MANAD Plus API 연동
   - 실시간 웹소켓 통신
   - 양방향 데이터 동기화

2. **고급 모바일 기능**
   - 네이티브 모바일 앱
   - 카메라 통합 (증거 사진)
   - QR/바코드 스캔
   - 생체 인증 로그인

3. **고급 알림 시스템**
   - FCM 푸시 알림
   - 이메일 알림
   - SMS 알림
   - 음성 알림

4. **AI 기반 분석**
   - 예측 분석 (위험 예측)
   - 패턴 인식
   - 자동 정책 제안
   - 성과 최적화 제안

5. **고급 정책 관리**
   - 정책 시뮬레이션
   - A/B 테스트
   - 자동 정책 최적화
   - 규정 변경 자동 감지

---

## 🎯 MANAD Plus 통합 워크플로우 다이어그램

```
MANAD Plus (Progress Notes)     CIMS (Compliance Tracking)
┌─────────────────────┐        ┌─────────────────────┐
│ 1. 인시던트 보고    │        │                     │
│ 2. Progress Note 작성│        │                     │
└─────────────────────┘        └─────────────────────┘
           │                              │
           │ API 폴링 (60초마다)          │
           │ ────────────────────────────→ │
           │                              │
           │                              │ 3. Policy Engine 트리거
           │                              │ 4. 태스크 자동 생성
           │                              │ 5. 담당자에게 알림
           │                              │
           │                              │
           │ 6. 딥링크로 MANAD Plus 접속  │
           │ ←──────────────────────────── │
           │                              │
           │ 7. Progress Note 작성        │
           │                              │
           │ 8. CIMS로 돌아와서 확인      │
           │ ────────────────────────────→ │
           │                              │ 9. 완료 확인 및 감사 로그
```

---

**CIMS v2.0** - Compliance-Driven Incident Management System with MANAD Plus Integration
*Built for aged care facilities to ensure regulatory compliance and accountability through seamless external system integration*
