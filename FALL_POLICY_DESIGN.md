# Fall Incident Policy 설계 (2안 구조)

## 📊 Policy 개요

### Policy 1: Unwitnessed Fall (목격되지 않은 낙상)
**Policy ID**: `FALL-001-UNWITNESSED`  
**심각도**: High  
**모니터링 기간**: 3일 (72시간)

#### 방문 스케줄:
- **Phase 1 (초기 4시간)**: 30분마다 방문 (8회)
- **Phase 2 (다음 20시간)**: 2시간마다 방문 (10회)
- **Phase 3 (다음 3일)**: 4시간마다 방문 (18회)
- **총 방문 횟수**: 36회

#### 적용 조건:
```json
{
  "incident_association": {
    "incident_type": "Fall",
    "progress_note_contains": "Unwitnessed fall"
  }
}
```

#### 임상적 근거:
- 낙상 목격자가 없어 정확한 상황 파악 불가
- 두부 손상, 의식 변화 가능성 높음
- 지속적인 신경학적 관찰 필수
- 지연된 증상 발현 모니터링

---

### Policy 2: Witnessed Fall (목격된 낙상)
**Policy ID**: `FALL-002-WITNESSED`  
**심각도**: Medium  
**모니터링 기간**: 단일 평가

#### 방문 스케줄:
- **즉시 평가**: 30분 이내 RN 평가 (1회)
- **추가 방문**: 필요 시 의사 판단에 따름

#### 적용 조건:
```json
{
  "incident_association": {
    "incident_type": "Fall",
    "progress_note_contains": "Witnessed fall"
  }
}
```

#### 임상적 근거:
- 낙상 상황이 명확히 목격됨
- 즉각적인 부상 평가 가능
- 초기 평가로 추가 모니터링 필요성 판단
- 리소스 효율적 대응

---

## 🔄 Policy 적용 로직

### 우선순위
1. **먼저 Progress Note 확인**
   - "Unwitnessed fall" 포함 → FALL-001-UNWITNESSED
   - "Witnessed fall" 포함 → FALL-002-WITNESSED
   
2. **Progress Note 없는 경우**
   - 기본값: FALL-001-UNWITNESSED (안전 우선)
   
3. **명시되지 않은 경우**
   - 임시로 FALL-001-UNWITNESSED 적용
   - 추후 Progress Note 생성 시 재평가

### 자동 Policy 전환
- Witnessed Fall로 시작했으나
- 후속 관찰에서 합병증 발견 시
- 자동으로 Unwitnessed Fall Policy로 escalate

---

## 💾 데이터베이스 스키마

### Policy JSON 구조

#### FALL-001-UNWITNESSED
```json
{
  "policy_name": "Unwitnessed Fall Management Policy",
  "policy_id": "FALL-001-UNWITNESSED",
  "severity": "high",
  "incident_association": {
    "incident_type": "Fall",
    "progress_note_keywords": ["Unwitnessed fall", "unwitnessed fall"],
    "matching_logic": "OR"
  },
  "nurse_visit_schedule": [
    {
      "phase": 1,
      "description": "Critical monitoring period",
      "interval": 30,
      "interval_unit": "minutes",
      "duration": 4,
      "duration_unit": "hours"
    },
    {
      "phase": 2,
      "description": "Extended monitoring",
      "interval": 2,
      "interval_unit": "hours",
      "duration": 20,
      "duration_unit": "hours"
    },
    {
      "phase": 3,
      "description": "Observation period",
      "interval": 4,
      "interval_unit": "hours",
      "duration": 3,
      "duration_unit": "days"
    }
  ],
  "common_assessment_tasks": "Complete neurological observations: GCS, pupil response, limb movement, vital signs, pain assessment",
  "escalation_criteria": [
    "GCS decrease",
    "New confusion",
    "Severe headache",
    "Vomiting",
    "Pupil changes"
  ]
}
```

#### FALL-002-WITNESSED
```json
{
  "policy_name": "Witnessed Fall Management Policy",
  "policy_id": "FALL-002-WITNESSED",
  "severity": "medium",
  "incident_association": {
    "incident_type": "Fall",
    "progress_note_keywords": ["Witnessed fall", "witnessed fall"],
    "matching_logic": "OR"
  },
  "nurse_visit_schedule": [
    {
      "phase": 1,
      "description": "Initial assessment",
      "interval": 30,
      "interval_unit": "minutes",
      "duration": 30,
      "duration_unit": "minutes"
    }
  ],
  "common_assessment_tasks": "Initial post-fall assessment: injury check, vital signs, mobility assessment, pain level",
  "escalation_criteria": [
    "Any signs of head injury",
    "Altered consciousness",
    "Severe pain",
    "Unable to weight bear",
    "Patient/family concern"
  ],
  "escalation_policy": "FALL-001-UNWITNESSED"
}
```

---

## 🔍 Progress Note 파싱 로직

### 검색 패턴
```python
def detect_fall_type(progress_notes: List[str]) -> str:
    """
    Progress Notes에서 Fall 유형 감지
    
    Returns:
        'unwitnessed' | 'witnessed' | 'unknown'
    """
    unwitnessed_patterns = [
        "unwitnessed fall",
        "not witnessed",
        "found on floor",
        "discovered on ground"
    ]
    
    witnessed_patterns = [
        "witnessed fall",
        "observed falling",
        "staff witnessed",
        "seen falling"
    ]
    
    for note in progress_notes:
        note_lower = note.lower()
        
        # Unwitnessed 먼저 체크 (더 높은 우선순위)
        for pattern in unwitnessed_patterns:
            if pattern in note_lower:
                return 'unwitnessed'
        
        # Witnessed 체크
        for pattern in witnessed_patterns:
            if pattern in note_lower:
                return 'witnessed'
    
    # 불명확한 경우 안전을 위해 unwitnessed로 처리
    return 'unknown'  # → 기본값 unwitnessed 적용
```

---

## 📊 예상 효과

### 리소스 절감
- Witnessed Fall: 36회 → **1회** (97% 감소)
- 전체 Fall 중 약 40%가 Witnessed로 추정
- 간호사 방문 시간: **연간 약 1,000시간 절감**

### 임상적 개선
- 고위험 케이스에 집중
- 적절한 모니터링 강도
- 의료진 피로도 감소

### 시스템 효율성
- 명확한 Policy 분리
- 자동 Policy 선택
- 필요시 Escalation

---

## 🚀 구현 단계

### Phase 1: Policy 생성
1. DB에 FALL-002-WITNESSED Policy 추가
2. FALL-001을 FALL-001-UNWITNESSED로 업데이트

### Phase 2: 자동 감지 로직
1. Progress Note 파싱 함수 구현
2. Task 생성 시 자동 Policy 선택

### Phase 3: Dashboard 개선
1. Fall 유형 표시 (Witnessed/Unwitnessed)
2. Policy별 통계
3. Escalation 이력 추적

---

## ❓ FAQ

### Q1: Progress Note가 아직 없는 경우?
**A**: 기본값으로 Unwitnessed 적용 (안전 우선). Progress Note 생성 시 재평가.

### Q2: 두 유형이 혼재된 경우?
**A**: 첫 번째 Post Fall Assessment Note의 기록 우선. 불명확하면 Unwitnessed.

### Q3: Witnessed였으나 증상 악화 시?
**A**: Escalation Policy 적용. 자동으로 Unwitnessed Policy로 전환.

### Q4: 기존 데이터는?
**A**: 기본값 Unwitnessed로 처리. Progress Note 있으면 재분류.

---

**작성일**: 2025-11-24  
**버전**: 1.0

