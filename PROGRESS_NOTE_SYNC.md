# Progress Note 자동 동기화 시스템

## 개요

MANAD Plus에서 "Post Fall" Progress Note를 자동으로 가져와서 방문 스케줄 Task와 매칭하여 자동 완료 처리하는 시스템입니다.

## 주요 기능

### 1. 자동 동기화 (Automatic Synchronization)

**동기화 트리거**:
- Incident 동기화 시 자동으로 Progress Note도 동기화
- 5분마다 자동으로 실행 (Incident sync 주기와 동일)
- 수동 트리거도 가능 (`POST /api/cims/sync-progress-notes`)

**동기화 대상**:
- 최근 7일 이내 발생한 Open/Overdue 상태의 Fall Incident
- 각 Incident에 대해 발생일부터 7일간의 Progress Note 조회
- "Post Fall" 타입의 Progress Note만 필터링

### 2. Task 매칭 로직 (Task Matching Logic)

**매칭 기준**:
```python
# Progress Note 작성 시간과 Task due_date가 ±30분 이내면 매칭
time_diff = abs((note_time - task_due).total_seconds())
if time_diff <= 1800:  # 30분 = 1800초
    # 매칭 성공 → Task 완료 처리
```

**매칭 프로세스**:
1. MANAD Plus에서 "Post Fall" Progress Note 조회
2. Progress Note의 `CreatedDate` 추출
3. 해당 Incident의 미완료 Task 조회
4. Task의 `due_date`와 Progress Note 시간 비교
5. ±30분 이내면 Task를 'completed'로 변경
6. CIMS DB에 Progress Note 레코드 생성 (Sync 마커)

### 3. 자동 Incident 관리 (Automatic Incident Management)

**Task 완료 시**:
- 자동으로 `check_and_update_incident_status()` 호출
- 모든 Task 완료 → Incident 'Closed'
- 마지막 Task 마감 시간 초과 + 미완료 → Incident 'Overdue'

## 데이터 흐름

```
1. Incident 동기화 (5분마다)
   ↓
2. Progress Note 동기화 트리거
   ↓
3. MANAD Plus에서 Post Fall Progress Note 조회
   ├─ Fall Incident만 필터링
   ├─ 최근 7일 이내 Open/Overdue Incident
   └─ 각 Incident당 7일간의 Progress Note
   ↓
4. Task 매칭 (±30분 이내)
   ├─ Progress Note CreatedDate
   └─ Task due_date
   ↓
5. Task 자동 완료 처리
   ├─ status = 'completed'
   ├─ completed_at = note_time
   └─ CIMS Progress Note 레코드 생성
   ↓
6. Incident 상태 자동 업데이트
   ├─ 모든 Task 완료 → 'Closed'
   └─ 마지막 Task 초과 + 미완료 → 'Overdue'
```

## API Endpoints

### 1. POST /api/cims/sync-progress-notes
**목적**: Progress Note 동기화 수동 트리거

**권한**: Admin, Clinical Manager

**동작**:
1. Open/Overdue Fall Incident 조회
2. MANAD Plus에서 Progress Note 조회
3. Task 매칭 및 자동 완료 처리
4. Incident 상태 업데이트

**응답**:
```json
{
  "success": true,
  "message": "Progress Note synchronization completed"
}
```

### 2. GET /api/cims/tasks/batch-status
**목적**: 여러 Incident의 Task 상태를 한 번에 조회

**파라미터**:
- `incident_ids`: Comma-separated incident IDs (e.g., "123,124,125")

**응답**:
```json
{
  "tasks": {
    "123": [
      {
        "id": 1,
        "task_id": "TASK-ABC123",
        "task_name": "30min post-fall check",
        "due_date": "2025-10-14T08:00:00",
        "status": "completed",
        "completed_at": "2025-10-14T08:05:00"
      }
    ],
    "124": [...]
  }
}
```

## Backend Implementation

### app.py - sync_progress_notes_with_tasks()

```python
def sync_progress_notes_with_tasks():
    """
    MANAD Plus에서 Progress Note를 가져와서 Task와 매칭하여 자동 완료 처리
    """
    # 1. Open/Overdue Fall Incident 조회 (최근 7일)
    incidents = get_fall_incidents()
    
    for incident in incidents:
        # 2. MANAD Plus에서 Progress Note 조회
        client = ProgressNoteFetchClient(incident.site)
        notes = client.fetch_progress_notes(
            start_date=incident.incident_date,
            end_date=incident.incident_date + 7days
        )
        
        # 3. "Post Fall" 필터링
        post_fall_notes = filter_post_fall_notes(notes, incident.resident_id)
        
        # 4. 미완료 Task 조회
        tasks = get_pending_tasks(incident.id)
        
        # 5. 매칭 및 완료 처리 (±30분)
        for note in post_fall_notes:
            for task in tasks:
                if match_time(note.created_date, task.due_date, window=30min):
                    complete_task(task.id, note.created_date)
                    create_cims_progress_note(incident.id, task.id, note)
        
        # 6. Incident 상태 업데이트
        check_and_update_incident_status(incident.id)
```

### 자동 동기화 통합

```python
def get_cims_incidents():
    """Open 상태 인시던트 목록 조회 (자동 동기화 포함)"""
    
    # Incident 동기화
    if should_sync:
        sync_incidents_from_manad_to_cims()
        
        # Progress Note 자동 동기화 추가
        sync_progress_notes_with_tasks()  # ← 새로 추가
    
    # Incident 목록 반환
    return incidents
```

## Frontend Implementation

### Mobile Dashboard (templates/mobile_task_dashboard.html)

**Batch Task Status Loading**:
```javascript
// Fetch task data for all fall incidents in one batch
const incidentIds = fallIncidents.map(inc => inc.id).join(',');
const response = await fetch(`/api/cims/tasks/batch-status?incident_ids=${incidentIds}`);
const data = await response.json();
const incidentTasksMap = data.tasks || {};
```

**Task Status Matching**:
```javascript
// Find matching task by due_date (±5 minutes)
const matchingTask = incidentTasks.find(task => {
    const taskDue = new Date(task.due_date);
    const timeDiff = Math.abs(taskDue - visitTime);
    return timeDiff < 5 * 60 * 1000;  // 5 minutes
});

// Display status badge
const taskStatus = matchingTask ? matchingTask.status : 'pending';
```

**Status Badge Display**:
- ✅ **OK** (녹색): `status === 'completed'`
- ⏰ **Pending** (노란색): `status === 'pending'` && not overdue
- ❌ **NOK** (빨간색): overdue (visit time passed && not completed)

## 실제 사용 예시

### 시나리오: Graham Maxwell Fall Incident

**Incident 정보**:
- Incident ID: INC-4949
- 발생 시간: 13 Oct 2025, 07:29 AM
- 환자: Graham Maxwell (ClientId: 318693)
- 사이트: Sandalwood (Parafield Gardens)

**생성된 방문 스케줄 (12개 Task)**:
```
Phase 1: Every 30 min for 2 hours (4 visits)
  07:59, 08:29, 08:59, 09:29

Phase 2: Every 1 hour for 2 hours (2 visits)
  10:29, 11:29

Phase 3: Every 4 hours for 24 hours (6 visits)
  15:29, 19:29, 23:29, 03:29, 07:29, 11:29
```

**MANAD Plus Progress Notes**:
```
318693 | 15 Oct 02:19 | Post Fall | Maria Galinato
318548 | 14 Oct 06:51 | Post Fall | Yanshu Wang
318514 | 13 Oct 21:11 | Post Fall | Hoi Lam
318407 | 13 Oct 08:00 | Client Incident - Fall | Maria Galinato
```

**매칭 결과**:
```
✅ 13 Oct 08:00 Post Fall → Task 07:59 (±30분 매칭)
✅ 13 Oct 21:11 Post Fall → Task 19:29 (±30분 매칭)
✅ 14 Oct 06:51 Post Fall → Task 07:29 (±30분 매칭)
✅ 15 Oct 02:19 Post Fall → Task 03:29 (±30분 매칭)

📊 4/12 Tasks 완료 (33% Compliance)
⚠️ Incident 상태: Overdue (마지막 Task 11:29 초과)
```

## 로그 예시

```
2025-10-15 09:13:18 - INFO - Triggering incident sync from MANAD API (증분 동기화)...
2025-10-15 09:13:18 - INFO - Incident sync completed: {'success': True, 'synced': 0, 'updated': 0}
2025-10-15 09:13:18 - INFO - Triggering Progress Note sync...
2025-10-15 09:13:18 - INFO - 📋 Progress Note 동기화: 25개 Fall Incident 확인
2025-10-15 09:13:19 - INFO -   📝 Graham Maxwell: 4개 Post Fall Progress Note 발견
2025-10-15 09:13:19 - INFO -     ✅ Task '30min post-fall check' 완료 처리 (Note: 13 Oct 08:00)
2025-10-15 09:13:19 - INFO -     ✅ Task '4h post-fall check' 완료 처리 (Note: 13 Oct 21:11)
2025-10-15 09:13:19 - INFO -     ✅ Task '4h post-fall check' 완료 처리 (Note: 14 Oct 06:51)
2025-10-15 09:13:19 - INFO -     ✅ Task '4h post-fall check' 완료 처리 (Note: 15 Oct 02:19)
2025-10-15 09:13:19 - INFO -   ⏰ Incident INC-4949 marked as overdue
2025-10-15 09:13:20 - INFO - 📊 Progress Note 동기화 완료: 24개 Task 매칭, 25개 Incident 처리
2025-10-15 09:13:20 - INFO - Progress Note sync completed
```

## 매칭 정확도 향상 팁

### 1. 시간 창 조정
현재 ±30분 (1800초) 설정:
```python
if time_diff <= 1800:  # 30분 = 1800초
```

필요시 조정 가능:
- ±15분: `time_diff <= 900`
- ±1시간: `time_diff <= 3600`

### 2. Progress Note 타입 확장
현재는 "Post Fall"만 인식:
```python
'Post Fall' in note.get('ProgressNoteEventType', {}).get('Name', '')
```

추가 타입 인식:
```python
note_type = note.get('ProgressNoteEventType', {}).get('Name', '')
if 'Post Fall' in note_type or 'Fall Follow Up' in note_type:
    # 매칭 처리
```

### 3. 중복 매칭 방지
한 Progress Note가 여러 Task에 매칭되지 않도록:
```python
for note in post_fall_notes:
    for task in tasks:
        if match_time(note, task):
            complete_task(task)
            break  # ← 첫 번째 매칭만 처리
```

## 문제 해결 (Troubleshooting)

### Q: Progress Note가 매칭되지 않습니다
**A**: 다음을 확인하세요:
1. Progress Note 타입이 "Post Fall"인지 확인
2. Progress Note `CreatedDate`와 Task `due_date` 시간 차이 확인 (±30분 이내여야 함)
3. Task 상태가 'pending'인지 확인 (이미 완료된 Task는 매칭 안 됨)
4. Incident `resident_id`와 Progress Note `ClientId`가 일치하는지 확인

### Q: Task가 중복으로 완료 처리됩니다
**A**: 
1. 매칭 로직에 `break` 문이 있는지 확인
2. 동기화가 너무 자주 실행되지 않는지 확인 (5분 주기 권장)
3. `completed_at` 필드로 이미 완료된 Task 필터링

### Q: 동기화가 너무 느립니다
**A**:
1. Batch API 사용 확인 (`/api/cims/tasks/batch-status`)
2. 조회 기간 축소 (7일 → 3일)
3. Limit 파라미터 조정 (`limit=100`)

## 성능 최적화

### 1. Batch Processing
- 개별 API 호출 대신 Batch API 사용
- 한 번에 여러 Incident의 Task 조회

### 2. 캐싱
- Progress Note 조회 결과 캐싱
- 최근 동기화 시간 체크하여 불필요한 조회 방지

### 3. 인덱싱
```sql
CREATE INDEX idx_tasks_incident_status ON cims_tasks(incident_id, status);
CREATE INDEX idx_tasks_due_date ON cims_tasks(due_date);
CREATE INDEX idx_incidents_type_status ON cims_incidents(incident_type, status, incident_date);
```

## 향후 개선 사항

1. **실시간 알림**
   - Task 자동 완료 시 담당 간호사에게 FCM 알림
   - Incident Close 시 관리자에게 알림

2. **AI 기반 매칭**
   - Progress Note 내용 분석으로 Task 매칭 정확도 향상
   - NLP로 "Post Fall" 외 다양한 표현 인식

3. **충돌 해결**
   - 여러 Progress Note가 하나의 Task와 매칭될 경우 우선순위 결정
   - 가장 근접한 시간의 Note 선택

4. **통계 및 리포트**
   - 매칭 성공률 추적
   - 자동 완료 vs 수동 완료 비율

---

**구현 완료 일자**: 2025-10-15
**구현자**: AI Assistant
**관련 파일**: 
- `app.py` (sync_progress_notes_with_tasks, trigger_progress_note_sync, get_batch_task_status)
- `templates/mobile_task_dashboard.html` (Batch API 통합)
- `api_progressnote_fetch.py` (Progress Note API Client)
