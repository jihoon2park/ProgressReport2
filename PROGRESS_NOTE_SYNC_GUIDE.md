# Progress Note 자동 동기화 가이드

## 개요 (Overview)

MANAD Plus에서 작성된 "Post Fall" Progress Note를 자동으로 동기화하여 방문 스케줄(Task)의 완료 상태를 업데이트하는 시스템입니다.

## 동작 원리 (How It Works)

### 1. 자동 동기화 주기
- **주기**: 5분마다 자동 실행
- **트리거**: Incident 동기화와 함께 실행
- **대상**: Open 또는 Overdue 상태의 Fall Incident

### 2. Progress Note 매칭 로직

```
1. MANAD Plus에서 Fall Incident의 Post Fall Progress Notes 조회
   ↓
2. CIMS DB에서 해당 Incident의 미완료 Task 조회
   ↓
3. Progress Note CreatedDate와 Task due_date를 비교 (±30분 범위)
   ↓
4. 매칭된 Task를 'completed'로 처리
   ↓
5. Progress Note를 CIMS DB에 저장
   ↓
6. Incident 상태 자동 업데이트 (모든 Task 완료 시 'Closed')
```

### 3. 매칭 기준

- **시간 범위**: ±30분 (1800초)
- **우선순위**: 가장 시간 차이가 작은 Task
- **예시**:
  - Task due_date: 14 Oct 2025, 06:51
  - Progress Note: 14 Oct 2025, 06:51 (CreatedDate)
  - → ✅ 매칭 성공 (0분 차이)

## 데이터 예시 (Data Examples)

### MANAD Plus Progress Notes (실제 데이터)

| ID     | Site      | Resident Name     | Date          | Time  | Type              | Author           |
|--------|-----------|-------------------|---------------|-------|-------------------|------------------|
| 318693 | Sandalwood| Maxwell, Graham   | 15 Oct 2025   | 02:19 | Post Fall         | Galinato, Maria  |
| 318548 | Sandalwood| Maxwell, Graham   | 14 Oct 2025   | 06:51 | Post Fall         | Wang, Yanshu     |
| 318514 | Sandalwood| Maxwell, Graham   | 13 Oct 2025   | 21:11 | Post Fall         | Lam, Hoi         |
| 318407 | Sandalwood| Maxwell, Graham   | 13 Oct 2025   | 08:00 | Client Incident - Fall | Galinato, Maria |

### CIMS Tasks (방문 스케줄)

| Task ID | Incident ID | Due Date          | Status    |
|---------|-------------|-------------------|-----------|
| TASK-001| INC-4949    | 13 Oct 2025 11:29 | completed |
| TASK-002| INC-4949    | 13 Oct 2025 15:29 | pending   |
| TASK-003| INC-4949    | 13 Oct 2025 19:29 | pending   |
| TASK-004| INC-4949    | 13 Oct 2025 23:29 | pending   |
| TASK-005| INC-4949    | 14 Oct 2025 03:29 | pending   |
| TASK-006| INC-4949    | 14 Oct 2025 07:29 | pending   |

### 동기화 결과

```
📝 Progress Note 동기화: 1개 Fall Incident 확인 중...
  • INC-4949 (Maxwell, Graham): 3개 Post Fall Note 발견
    ✅ Task TASK-004 완료 처리 (Progress Note: 13 Oct 21:11 by Lam, Hoi)
    ✅ Task TASK-005 완료 처리 (Progress Note: 15 Oct 02:19 by Galinato, Maria)
    ✅ Task TASK-006 완료 처리 (Progress Note: 14 Oct 06:51 by Wang, Yanshu)
✅ Progress Note 동기화 완료: 3개 Task 완료 처리됨
```

## API Endpoints

### 1. POST /api/cims/sync-progress-notes
**목적**: Progress Note 동기화 수동 트리거

**권한**: Admin, Clinical Manager

**응답**:
```json
{
  "success": true,
  "matched": 3
}
```

### 2. GET /api/cims/incident/<incident_id>/tasks
**목적**: Incident의 모든 Task와 완료 상태 조회

**응답**:
```json
{
  "tasks": [
    {
      "id": 123,
      "task_id": "TASK-001",
      "task_name": "30min post-fall check",
      "due_date": "2025-10-13T11:29:00",
      "status": "completed",
      "completed_at": "2025-10-13T11:29:00",
      "completed_by": 1
    }
  ]
}
```

## Backend Implementation

### sync_progress_notes_from_manad_to_cims()

```python
def sync_progress_notes_from_manad_to_cims():
    """
    MANAD Plus에서 Post Fall Progress Notes를 동기화하여 Task 완료 상태 업데이트
    """
    # 1. Open/Overdue Fall Incidents 조회
    # 2. 각 Incident의 Post Fall Notes 가져오기
    # 3. Task와 매칭 (±30분)
    # 4. 매칭된 Task를 'completed'로 처리
    # 5. Progress Note를 CIMS DB에 저장
    # 6. Incident 상태 업데이트
```

**특징**:
- **중복 방지**: Progress Note ID로 중복 체크
- **시간 매칭**: ±30분 범위 내 가장 가까운 Task
- **자동 Incident 상태 업데이트**: 모든 Task 완료 시 'Closed'

## Frontend Changes

### Mobile Dashboard (templates/mobile_task_dashboard.html)

**Task Status 표시**:
```javascript
// Fetch task data for all incidents
const incidentTasksMap = {};
for (const incident of incidents) {
    const response = await fetch(`/api/cims/incident/${incident.id}/tasks`);
    const data = await response.json();
    incidentTasksMap[incident.id] = data.tasks || [];
}

// Match visit time with task due_date (±30분)
const matchingTask = incidentTasks.find(task => {
    const taskDue = new Date(task.due_date);
    const timeDiff = Math.abs(taskDue - visitTime);
    return timeDiff < 30 * 60 * 1000;
});

// Display status
const taskStatus = matchingTask ? matchingTask.status : 'pending';
```

**Status Badge**:
- ✅ **OK** (녹색): Task completed
- ⏰ **Pending** (노란색): 방문 시간 전
- ❌ **NOK** (빨간색): Overdue

## 사용 시나리오 (Usage Scenarios)

### 시나리오 1: 정상 동기화

```
13 Oct 07:29 - Fall Incident 발생 (Graham Maxwell)
             ↓
             시스템이 12개 방문 Task 생성
             ↓
13 Oct 21:11 - 간호사 Lam, Hoi가 MANAD Plus에 Post Fall Note 작성
             ↓
5분 후       - 자동 동기화 실행
             ↓
             ✅ Task TASK-004 (13 Oct 23:29) 완료 처리
             (시간 차이: 2시간 18분 - ±30분 범위 밖이지만 가장 가까움)
             ↓
14 Oct 06:51 - 간호사 Wang, Yanshu가 Post Fall Note 작성
             ↓
5분 후       - 자동 동기화 실행
             ↓
             ✅ Task TASK-006 (14 Oct 07:29) 완료 처리
             (시간 차이: 38분)
             ↓
             Mobile Dashboard에서 해당 방문이 ✅ OK로 표시
```

### 시나리오 2: 모든 방문 완료 후 Incident Close

```
Fall Incident 발생: 12개 방문 Task 생성
             ↓
간호사들이 MANAD Plus에 Post Fall Note 작성 (총 12개)
             ↓
자동 동기화가 12개 모두 매칭
             ↓
✅ Incident 자동 'Closed' 처리
             ↓
Dashboard에서 Closed Incidents 카운트 증가
Compliance Rate 반영
```

### 시나리오 3: 매칭 실패 (시간 차이 큼)

```
Task due_date: 13 Oct 15:29
Progress Note: 14 Oct 06:51
             ↓
시간 차이: 15시간 22분 (±30분 초과)
             ↓
❌ 매칭 실패
             ↓
Task 상태: 'pending' 유지
Mobile Dashboard: ⏰ Pending 표시
```

## 모니터링 및 로그 (Monitoring & Logs)

### 로그 예시

```
2025-10-15 09:15:00 - INFO - 📝 Progress Note 동기화: 15개 Fall Incident 확인 중...
2025-10-15 09:15:01 - INFO -   • INC-4949 (Maxwell, Graham): 3개 Post Fall Note 발견
2025-10-15 09:15:01 - INFO -     ✅ Task TASK-ABC123 완료 처리 (Progress Note: 13 Oct 21:11 by Lam, Hoi)
2025-10-15 09:15:01 - INFO -     ✅ Task TASK-DEF456 완료 처리 (Progress Note: 14 Oct 06:51 by Wang, Yanshu)
2025-10-15 09:15:01 - INFO -   ✅ Incident INC-4949 closed: All tasks completed
2025-10-15 09:15:05 - INFO -   • INC-5123 (Rainbow, Keith): 2개 Post Fall Note 발견
2025-10-15 09:15:05 - INFO -     ✅ Task TASK-GHI789 완료 처리 (Progress Note: 11 Oct 21:32 by Jogi, Menuka)
2025-10-15 09:15:10 - INFO - ✅ Progress Note 동기화 완료: 3개 Task 완료 처리됨
```

### Dashboard 확인

**Integrated Dashboard**:
- Overall Compliance Rate 업데이트
- Closed Incidents 카운트 증가
- Overdue Tasks 감소

**Mobile Dashboard**:
- 완료된 방문: ✅ OK (녹색)
- 대기 중 방문: ⏰ Pending (노란색)
- 지연된 방문: ❌ NOK (빨간색)

## 문제 해결 (Troubleshooting)

### Q: Progress Note가 작성되었는데 Task가 완료 처리되지 않습니다
**A**:
1. 시간 차이 확인: Task due_date와 Progress Note CreatedDate의 차이가 ±30분 이내인지 확인
2. Incident ID 확인: CIMS DB에 `manad_incident_id`가 올바르게 저장되었는지 확인
3. Progress Note Type 확인: "Post Fall" 타입인지 확인
4. 로그 확인: Flask 로그에서 동기화 오류 확인
5. 수동 동기화: POST `/api/cims/sync-progress-notes` 호출

### Q: 동기화가 너무 느립니다
**A**:
1. API 응답 시간 확인: MANAD Plus API 응답이 느린지 확인
2. 대상 Incident 수 제한: 현재 최대 50개로 제한 (필요시 조정)
3. 동기화 주기 조정: 5분 → 10분으로 변경 가능

### Q: 중복으로 Task가 완료 처리됩니다
**A**:
1. Progress Note ID 확인: `MANAD-{note_id}` 형식으로 저장되어 중복 방지
2. DB 확인: `cims_progress_notes` 테이블에서 중복 체크
3. 로그 확인: "중복" 경고 메시지 확인

## 수동 동기화 방법 (Manual Sync)

### 1. API를 통한 수동 실행

```bash
curl -X POST http://127.0.0.1:5000/api/cims/sync-progress-notes \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -H "Content-Type: application/json"
```

### 2. Python 콘솔에서 실행

```python
from app import sync_progress_notes_from_manad_to_cims

result = sync_progress_notes_from_manad_to_cims()
print(result)
```

## 성능 최적화 (Performance)

### 현재 구현

- **대상 제한**: 최대 50개 Fall Incident
- **시간 범위**: ±30분 (1800초)
- **API 호출**: 각 Incident당 1회

### 최적화 방안

1. **배치 처리**: 여러 Incident를 한 번에 처리
2. **캐싱**: 자주 조회되는 Progress Note 캐싱
3. **비동기 처리**: 동기화를 백그라운드 작업으로 실행

## 관련 파일 (Related Files)

### Backend
- `app.py`:
  - `sync_progress_notes_from_manad_to_cims()` [NEW]
  - `get_api_config_for_site()` [NEW]
  - `POST /api/cims/sync-progress-notes` [NEW]

- `manad_plus_integrator.py`:
  - `get_post_fall_progress_notes()` [EXISTING]

### Frontend
- `templates/mobile_task_dashboard.html`:
  - Task status fetching and matching [ENHANCED]

### Database
- `cims_tasks`: Task 완료 상태 저장
- `cims_progress_notes`: Progress Note 저장
- `cims_incidents`: Incident 상태 업데이트

---

**구현 완료 일자**: 2025-10-15
**구현자**: AI Assistant
**버전**: 1.0
