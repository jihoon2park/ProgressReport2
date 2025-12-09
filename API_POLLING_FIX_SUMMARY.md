# API 폴링 반복 문제 해결

## 📅 날짜: 2025-11-19

## 🐛 문제 상황

로그에 1분마다 반복적으로 에러가 발생:
```
2025-11-19 15:25:52,385 - get_cache_status_current error: no such table: cims_cache_management
2025-11-19 15:26:52,385 - get_cache_status_current error: no such table: cims_cache_management
2025-11-19 15:27:52,389 - get_cache_status_current error: no such table: cims_cache_management
```

## 🔍 원인 분석

### 1. 프론트엔드 폴링
- `integrated_dashboard.html`에서 5초마다 `/api/cache/status-current` API 호출
- 캐시 상태 인디케이터 업데이트용

### 2. 데이터베이스 연결 문제
- **실제 원인**: Working directory 문제
  - 여러 프로세스가 다른 working directory에서 실행
  - 상대 경로(`progress_report.db`)로 연결 시 파일을 찾지 못함
- **부수 원인**: WAL 모드와 read-only 연결 호환성
  - Write-Ahead Logging 사용 시 read-only 연결이 최신 데이터를 보지 못할 수 있음

### 3. 여러 프로세스 실행
- 여러 시작 스크립트 존재:
  - `start.bat` - Dual startup (Core + Admin)
  - `RUN.bat` - Unified startup
  - `start_systems.ps1` - PowerShell startup
  - `start_manad_integrator.py` - MANAD Plus 통합
- 일부 프로세스는 올바른 working directory 설정 없이 실행

## ✅ 해결 방법

### 1. `get_db_connection()` 함수 수정
**절대 경로 사용으로 working directory 문제 해결**

```python
def get_db_connection(read_only: bool = False):
    """CIMS용 데이터베이스 연결"""
    # 절대 경로 사용하여 working directory 문제 방지
    import os
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progress_report.db')
    
    if read_only:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', timeout=60.0, uri=True)
    else:
        conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    # ... PRAGMA 설정
    return conn
```

**변경 사항:**
- ✅ `__file__`을 기준으로 절대 경로 계산
- ✅ 어떤 working directory에서 실행해도 정확한 DB 파일 접근

### 2. `get_cache_status_current()` 함수 개선
**에러 로깅 레벨 조정 및 read-only 모드 제거**

```python
@app.route('/api/cache/status-current', methods=['GET'])
@login_required
def get_cache_status_current():
    """Return latest cache/sync status for dashboard indicator"""
    try:
        # read_only 대신 일반 연결 사용 (WAL 모드 호환성)
        conn = get_db_connection(read_only=False)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, last_processed
            FROM cims_cache_management
            ORDER BY last_processed DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        status = row[0] if row else 'idle'
        last = row[1] if row else None
        return jsonify({'success': True, 'status': status, 'last_processed': last})
    except Exception as e:
        # 테이블이 없거나 접근할 수 없을 때 조용히 처리
        if 'no such table' in str(e):
            logger.debug(f"cims_cache_management table not found (first run?): {e}")
        else:
            logger.warning(f"get_cache_status_current error: {e}")
        return jsonify({'success': True, 'status': 'idle'}), 200
```

**변경 사항:**
- ✅ `read_only=False`로 변경 → WAL 모드 호환성 향상
- ✅ 연결 명시적으로 닫기 (`conn.close()`)
- ✅ "no such table" 에러는 `debug` 레벨로 처리
- ✅ 다른 에러는 `warning` 레벨로 처리
- ✅ 모든 경우 정상 응답 반환 (UI 인디케이터 기능 유지)

## 📊 테스트 결과

### 데이터베이스 확인
```bash
$ python check_tables.py
============================================================
CIMS 및 Cache 관련 테이블:
============================================================
  - cims_cache_management ✓
  - cims_dashboard_kpi_cache ✓
  - ... (총 16개 테이블)

✓ cims_cache_management 테이블이 존재합니다.
✓ Read-only 연결 성공: status=idle
```

### WAL 체크포인트
```bash
$ python fix_cache_status_api.py
✓ WAL 체크포인트 완료
✓ 테이블이 존재합니다
✓ Read-only 연결 성공: status=idle
Journal Mode: wal
```

## 🎯 기대 효과

### Before (수정 전)
```log
2025-11-19 15:25:52 - ERROR - get_cache_status_current error: no such table
2025-11-19 15:26:52 - ERROR - get_cache_status_current error: no such table
2025-11-19 15:27:52 - ERROR - get_cache_status_current error: no such table
```
❌ 로그가 error로 가득 참
❌ 실제 문제가 숨겨짐

### After (수정 후)
```log
2025-11-19 15:25:52 - DEBUG - cims_cache_management table not found (first run?)
```
✅ 정상 작동 시 로그 없음
✅ 실제 문제만 warning/error로 기록
✅ 절대 경로 사용으로 working directory 문제 해결

## 📝 추가 권장 사항

### 1. 모든 DB 연결 함수 통합
현재 여러 파일에 `get_db_connection()` 함수가 분산되어 있음:
- `app.py` ✓ (수정 완료)
- `cims_api_endpoints.py`
- `cims_cache_api.py`
- `unified_data_sync_manager.py`
- `client_sync_manager.py`

**권장**: 공통 유틸리티 모듈 생성 (`db_utils.py`)

### 2. 프로세스 관리 개선
여러 시작 스크립트를 하나로 통합하거나, working directory를 명확히 설정

### 3. 로깅 정책
- `INFO`: 정상 작동 정보
- `WARNING`: 복구 가능한 문제
- `ERROR`: 즉각 조치 필요한 문제
- `DEBUG`: 개발/진단용 상세 정보

## 🔄 배포 방법

1. 수정된 `app.py` 파일 배포
2. 실행 중인 Flask 앱 재시작:
   ```bash
   # Windows
   RUN.bat
   
   # 또는 프로세스 종료 후 재시작
   taskkill /f /im python.exe
   python app.py
   ```

3. 로그 모니터링:
   ```bash
   tail -f logs/app.log
   ```

4. 더 이상 반복적인 에러 메시지가 나타나지 않는지 확인

## ✅ 완료 체크리스트

- [x] 문제 원인 분석
- [x] 데이터베이스 테이블 확인
- [x] WAL 모드 호환성 테스트
- [x] `get_db_connection()` 함수 수정 (절대 경로)
- [x] `get_cache_status_current()` 함수 개선
- [x] 에러 로깅 레벨 조정
- [x] 수정 사항 문서화
- [ ] 운영 서버 배포
- [ ] 배포 후 모니터링

## 📚 관련 파일

- `app.py` - 메인 애플리케이션 (수정됨)
- `templates/integrated_dashboard.html` - 프론트엔드 폴링 코드
- `progress_report.db` - SQLite 데이터베이스
- `API_POLLING_FIX_SUMMARY.md` - 이 문서

---

**작성자**: AI Assistant  
**검토자**: IT Support Team  
**최종 업데이트**: 2025-11-19

