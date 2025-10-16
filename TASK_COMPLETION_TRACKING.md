# Task Completion Tracking System

## 개요 (Overview)

진행 노트(Progress Notes) 작성을 통한 방문 스케줄 완료 추적 시스템을 구현했습니다.
방문 스케줄이 모두 완료되면 자동으로 Incident가 Close되고, 마감 시간이 지났는데 미완료 시 Overdue로 표시됩니다.

## 주요 기능 (Key Features)

### 1. Task Completion Tracking (방문 완료 추적)

- **Progress Note 작성 = Task 완료**
  - 간호사가 방문 후 Progress Note를 작성하면 해당 Task가 자동으로 'completed' 상태로 변경됩니다.
  - `task_id`와 연결된 Progress Note가 생성되면 해당 방문이 완료된 것으로 처리됩니다.

### 2. Automatic Incident Closure (자동 사고 종결)

- **모든 Task 완료 → Incident Closed**
  - Incident에 연결된 모든 Task가 완료되면 Incident 상태가 자동으로 'Closed'로 변경됩니다.
  - `check_and_update_incident_status()` 함수가 Task 완료 후 자동으로 실행되어 상태를 확인합니다.

### 3. Overdue Task Management (지연 Task 관리)

- **마지막 방문 시간 초과 + 미완료 → Overdue**
  - 마지막 방문 스케줄 시간이 지났는데 완료되지 않은 Task가 있으면 Incident가 'Overdue' 상태로 변경됩니다.
  - Overdue Incident는 즉각적인 조치가 필요함을 나타냅니다.

### 4. Dashboard KPI Cards (대시보드 KPI 카드)

#### Overall Compliance Rate (전체 준수율)
- **계산 방식**: (정시 완료 Task 수 / 전체 완료 Task 수) × 100%
- **표시 기준**:
  - 90% 이상: "Excellent compliance" (녹색)
  - 70-89%: "Good compliance" (노란색)
  - 70% 미만: "Needs improvement" (빨간색)

#### Overdue Tasks (지연 Task)
- **계산 방식**: 마지막 방문 시간이 지났는데 미완료 Task가 있는 Incident 수
- **표시 기준**:
  - 0개: "All tasks on time" (녹색)
  - 1개 이상: "X incident(s) overdue" (빨간색)

#### Open Incidents (미방문 사고)
- **계산 방식**: 현재 시간까지 한 번도 방문하지 않은 (Task가 없는) Incident 수
- **의미**: 즉시 첫 방문이 필요한 사고

#### Total Incidents (전체 사고)
- **계산 방식**: 선택한 기간 내 발생한 전체 Incident 수
- **변경 사항**: "Total Tasks"에서 "Total Incidents"로 명칭 변경

## 데이터 흐름 (Data Flow)

```
1. Incident 발생
   ↓
2. Policy Engine이 자동으로 Task 생성 (방문 스케줄)
   ↓
3. 간호사가 방문 후 Progress Note 작성
   ↓
4. Task 상태가 'completed'로 변경
   ↓
5. check_and_update_incident_status() 실행
   ↓
6. 모든 Task 완료 → Incident 'Closed'
   또는
   마지막 Task 마감 시간 초과 + 미완료 → Incident 'Overdue'
```

## API Endpoints

### 1. GET /api/cims/dashboard-kpis
**목적**: Dashboard KPI 데이터 조회

**파라미터**:
- `period`: 기간 필터 (today, week, month)
- `incident_type`: 사고 유형 필터 (all, Fall, Wound/Skin, 등)

**응답**:
```json
{
  "total_incidents": 37,
  "closed_incidents": 5,
  "open_incidents": 12,
  "overdue_tasks": 3,
  "compliance_rate": 85.5,
  "period": "week",
  "incident_type": "all"
}
```

### 2. GET /api/cims/incident/<incident_id>/tasks
**목적**: 특정 Incident의 모든 Task와 완료 상태 조회

**응답**:
```json
{
  "tasks": [
    {
      "id": 123,
      "task_id": "TASK-ABC123",
      "task_name": "30min post-fall check",
      "due_date": "2025-10-14T08:00:00",
      "status": "completed",
      "completed_at": "2025-10-14T08:05:00",
      "completed_by": 5
    }
  ]
}
```

### 3. POST /api/cims/progress-notes
**목적**: Progress Note 생성 및 Task 완료 처리

**요청**:
```json
{
  "incident_id": 123,
  "task_id": 456,
  "content": "Patient stable, vital signs normal",
  "note_type": "Post Fall Assessment",
  "vitals_data": {},
  "assessment_data": {}
}
```

**동작**:
1. Progress Note 저장
2. 연결된 Task를 'completed' 상태로 변경
3. Incident 상태 자동 업데이트

## Frontend Changes

### Integrated Dashboard (templates/integrated_dashboard.html)

**KPI Cards HTML 업데이트**:
```html
<!-- Overall Compliance Rate -->
<div class="kpi-number" id="compliance-rate">--</div>
<div class="kpi-description" id="compliance-desc">No data</div>

<!-- Overdue Tasks -->
<div class="kpi-number text-danger" id="overdue-tasks">--</div>
<div class="kpi-description" id="overdue-desc">All tasks on time</div>

<!-- Open Incidents -->
<div class="kpi-number text-warning" id="open-incidents">--</div>
<div class="kpi-description" id="incidents-change">Not visited</div>

<!-- Total Incidents -->
<div class="kpi-number text-info" id="total-incidents">--</div>
<div class="kpi-description" id="total-incidents-desc">This Week</div>
```

**JavaScript Function**:
```javascript
async function updateKPICards() {
    const response = await fetch(`/api/cims/dashboard-kpis?period=${currentPeriod}&incident_type=${currentIncidentType}`);
    const kpiData = await response.json();
    
    // Update each KPI card with fetched data
    document.getElementById('compliance-rate').textContent = `${kpiData.compliance_rate}%`;
    document.getElementById('overdue-tasks').textContent = kpiData.overdue_tasks;
    document.getElementById('open-incidents').textContent = kpiData.open_incidents;
    document.getElementById('total-incidents').textContent = kpiData.total_incidents;
}
```

### Mobile Task Dashboard (templates/mobile_task_dashboard.html)

**Task Status 표시**:
```javascript
// Fetch task data for all incidents
const incidentTasksMap = {};
for (const incident of incidents) {
    const response = await fetch(`/api/cims/incident/${incident.id}/tasks`);
    const data = await response.json();
    incidentTasksMap[incident.id] = data.tasks || [];
}

// Match visit time with task due_date
const matchingTask = incidentTasks.find(task => {
    const taskDue = new Date(task.due_date);
    const timeDiff = Math.abs(taskDue - visitTime);
    return timeDiff < 5 * 60 * 1000; // Within 5 minutes
});

// Display status badge
const taskStatus = matchingTask ? matchingTask.status : 'pending';
```

**Status Badge 표시**:
- ✅ **OK** (녹색): Task completed
- ⏰ **Pending** (노란색): 아직 방문 시간 전
- ❌ **NOK** (빨간색): Overdue (방문 시간 지났는데 미완료)

## Backend Changes

### app.py

**1. 새로운 Helper Function**:
```python
def check_and_update_incident_status(incident_id):
    """
    인시던트의 모든 태스크 상태를 확인하고 인시던트 상태를 업데이트
    - 모든 태스크가 완료되면 'Closed'로 변경
    - 마지막 태스크 마감 시간이 지났는데 미완료 태스크가 있으면 'Overdue'로 변경
    """
```

**2. Progress Note 생성 시 Task 완료 처리**:
```python
# task_id가 있으면 해당 태스크를 완료 처리
if data.get('task_id'):
    cursor.execute("""
        UPDATE cims_tasks
        SET status = 'completed',
            completed_by_user_id = ?,
            completed_at = ?,
            updated_at = ?
        WHERE id = ?
    """, (current_user.id, completed_at, completed_at, data['task_id']))
    
    # 인시던트 상태 업데이트 체크
    check_and_update_incident_status(data['incident_id'])
```

## 사용 시나리오 (Usage Scenarios)

### 시나리오 1: 정상 완료
1. Fall Incident 발생 (13 Oct, 07:29 AM)
2. 시스템이 12개 방문 Task 자동 생성
3. 간호사가 각 방문 시간에 Progress Note 작성
4. 모든 12개 Task가 'completed' 상태로 변경
5. **Incident 자동으로 'Closed' 상태로 변경**
6. **Dashboard Compliance Rate에 반영**

### 시나리오 2: Overdue 발생
1. Fall Incident 발생 (13 Oct, 07:29 AM)
2. 시스템이 12개 방문 Task 자동 생성
3. 간호사가 5개 방문만 완료
4. 마지막 방문 시간 (14 Oct, 11:29 AM) 경과
5. **Incident 자동으로 'Overdue' 상태로 변경**
6. **Dashboard에 Overdue Task로 표시**
7. **Clinical Manager에게 알림 필요**

### 시나리오 3: 미방문 Incident
1. Fall Incident 발생 (14 Oct, 23:00)
2. 시스템이 12개 방문 Task 자동 생성
3. 아직 아무도 방문하지 않음 (Task 0개 완료)
4. **Dashboard Open Incidents 카운트 증가**
5. **Mobile Dashboard에 첫 방문 시간 표시**

## 테스트 방법 (Testing Guide)

### 1. Dashboard KPI 테스트
```
URL: http://127.0.0.1:5000/integrated_dashboard

1. Admin으로 로그인
2. Period 선택 (Today / This Week / This Month)
3. Incident Type 선택 (All / Fall / Wound/Skin, 등)
4. KPI Cards 확인:
   - Overall Compliance Rate: 퍼센티지 표시
   - Overdue Tasks: 숫자 표시
   - Open Incidents: 미방문 사고 수
   - Total Incidents: 전체 사고 수
```

### 2. Mobile Dashboard 테스트
```
URL: http://127.0.0.1:5000/mobile_dashboard

1. Nurse로 로그인
2. 사이트 선택 (e.g., Parafield Gardens)
3. 날짜 선택 (Today)
4. 방문 스케줄 확인:
   - 각 방문의 Status 확인 (OK / Pending / NOK)
   - Overdue 방문은 빨간색 배경
   - 완료된 방문은 녹색 OK 배지
```

### 3. Progress Note 작성 테스트
```
1. Mobile Dashboard에서 방문 클릭
2. Progress Note 작성
3. 저장 후 Status가 'OK'로 변경되는지 확인
4. 모든 방문 완료 후 Dashboard에서 Incident가 Closed되는지 확인
```

## 주의 사항 (Important Notes)

1. **Task와 Progress Note 연결**
   - Progress Note를 작성할 때 반드시 `task_id`를 포함해야 Task 완료 처리됩니다.
   
2. **Incident Status 변경**
   - Incident 상태는 자동으로 관리되므로 수동으로 변경하지 마세요.
   
3. **Compliance Rate 계산**
   - 정시 완료와 지연 완료를 구분하여 계산합니다.
   - Due date 이후에 완료된 Task는 "Late"로 분류됩니다.

4. **Overdue 기준**
   - Incident의 **마지막** Task 마감 시간을 기준으로 합니다.
   - 중간 Task가 지연되어도 마지막 Task가 완료되면 Overdue가 아닙니다.

## 향후 개선 사항 (Future Enhancements)

1. **실시간 알림**
   - Overdue Task 발생 시 FCM 푸시 알림
   - Clinical Manager에게 즉시 알림

2. **상세 리포트**
   - 월별/주별 Compliance Rate 추이 그래프
   - 사이트별 Compliance 비교

3. **자동 재할당**
   - Overdue Task를 다른 간호사에게 자동 재할당

4. **Progress Note 템플릿**
   - 사고 유형별 맞춤형 템플릿
   - 필수 입력 항목 체크리스트

## 문제 해결 (Troubleshooting)

### Q: KPI Cards에 "--"만 표시됩니다
**A**: 
1. 브라우저 콘솔에서 API 호출 오류 확인
2. `/api/cims/dashboard-kpis` 엔드포인트가 정상 응답하는지 확인
3. 선택한 기간에 Incident가 있는지 확인

### Q: Progress Note 작성 후에도 Status가 변경되지 않습니다
**A**:
1. Progress Note에 `task_id`가 포함되었는지 확인
2. Task의 `due_date`와 방문 시간이 5분 이내로 일치하는지 확인
3. 데이터베이스에서 Task 상태 직접 확인

### Q: Incident가 자동으로 Closed되지 않습니다
**A**:
1. 모든 Task가 'completed' 상태인지 확인
2. `check_and_update_incident_status()` 함수가 호출되었는지 로그 확인
3. 데이터베이스 연결 오류가 없는지 확인

---

**구현 완료 일자**: 2025-10-15
**구현자**: AI Assistant
**관련 파일**: 
- `app.py`
- `templates/integrated_dashboard.html`
- `templates/mobile_task_dashboard.html`
