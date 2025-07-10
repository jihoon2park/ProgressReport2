# Chrome 성능 디버깅 가이드

## 개요
Chrome에서 11개 스레드가 실행되면서 느려지는 문제를 진단하고 해결하는 방법을 설명합니다.

## 주요 성능 문제점

### 1. 세션 모니터링 중복 실행
- **문제**: `script.js`에서 세션 모니터링이 중복으로 시작될 수 있음
- **해결**: 중복 실행 방지 로직 추가, 간격을 10초에서 30초로 증가

### 2. 프로그레스 바 애니메이션
- **문제**: 100ms마다 실행되는 애니메이션이 정리되지 않을 경우 계속 실행
- **해결**: 로딩 애니메이션 바 완전 제거 (성능 최적화)

### 3. MutationObserver 메모리 누수
- **문제**: URL 변경 감지를 위한 MutationObserver가 정리되지 않음
- **해결**: 페이지 언로드 시 정리 로직 추가

### 4. 이벤트 리스너 누적
- **문제**: 테이블 행 클릭 이벤트가 누적됨
- **해결**: DocumentFragment 사용으로 DOM 조작 최적화

### 5. 대용량 데이터 처리
- **문제**: 10,000개 노트를 한 번에 로드하고 처리 (1주일 데이터로 제한)
- **해결**: 배치 처리 및 성능 측정 추가, 데이터 기간을 1주일로 제한

## 디버깅 도구 사용법

### 1. 브라우저 콘솔에서 성능 상태 확인

```javascript
// 현재 성능 상태 출력
debugPerformance.status()

// 강제 정리
debugPerformance.cleanup()

// 메모리 모니터링 시작
debugPerformance.startMemoryMonitoring()

// 메모리 모니터링 중지
debugPerformance.stopMemoryMonitoring()

// 가비지 컬렉션 강제 실행
debugPerformance.forceGC()
```

### 2. Chrome DevTools Performance Panel 사용

1. **Performance 탭 열기**
   - F12 → Performance 탭
   - 또는 Ctrl+Shift+E

2. **성능 기록 시작**
   - Record 버튼 클릭
   - 문제가 발생하는 동작 수행
   - Stop 버튼 클릭

3. **분석 포인트**
   - **Main 스레드**: JavaScript 실행 시간
   - **Memory**: 메모리 사용량 변화
   - **Network**: API 호출 및 응답 시간

### 3. Memory 탭에서 메모리 누수 확인

1. **Memory 탭 열기**
   - F12 → Memory 탭

2. **Heap Snapshot 생성**
   - Take snapshot 버튼 클릭
   - 동작 수행 후 다시 스냅샷 생성
   - 비교하여 메모리 누수 확인

### 4. Network 탭에서 API 호출 분석

1. **Network 탭 열기**
   - F12 → Network 탭

2. **API 호출 확인**
   - `/api/session-status` 호출 빈도
   - `/api/fetch-progress-notes` 응답 시간
   - 중복 호출 여부 확인

## 성능 최적화 방법

### 1. 세션 모니터링 최적화

```javascript
// 기존: 10초마다 체크
setInterval(checkSessionStatus, 10000);

// 개선: 60초마다 체크 (성능 최적화)
setInterval(checkSessionStatus, 60000);
```

### 2. 이벤트 리스너 최적화

```javascript
// 기존: 개별 DOM 조작
notes.forEach((note, idx) => {
    const tr = document.createElement('tr');
    // ... 설정
    tbody.appendChild(tr);
});

// 개선: DocumentFragment 사용 (1주일 데이터로 제한)
const fragment = document.createDocumentFragment();
notes.forEach((note, idx) => {
    const tr = document.createElement('tr');
    // ... 설정
    fragment.appendChild(tr);
});
tbody.appendChild(fragment);
```

### 3. 메모리 누수 방지

```javascript
// 페이지 언로드 시 정리
window.addEventListener('beforeunload', cleanup);
window.addEventListener('pagehide', cleanup);

function cleanup() {
    // 모든 인터벌 정리
    performanceMetrics.intervals.forEach(clearInterval);
    // 모든 옵저버 정리
    performanceMetrics.observers.forEach(observer => observer.disconnect());
}

// 추가 최적화
// - 세션 경고 팝업 비활성화
// - 과도한 로깅 제거
// - ResizeObserver 스로틀링 적용
// - 로딩 애니메이션 바 완전 제거
// - Refresh 버튼 10초 비활성화로 중복 요청 방지
```

## 문제 진단 체크리스트

### 1. 메모리 사용량 확인
- [ ] `debugPerformance.status()` 실행
- [ ] 메모리 사용량이 80% 이상인지 확인
- [ ] 메모리 사용량이 지속적으로 증가하는지 확인

### 2. 활성 인터벌 확인
- [ ] 활성 인터벌 개수 확인
- [ ] 불필요한 인터벌이 있는지 확인
- [ ] 인터벌이 정리되지 않고 있는지 확인

### 3. 이벤트 리스너 확인
- [ ] 이벤트 리스너 개수 확인
- [ ] 중복 리스너가 있는지 확인
- [ ] 리스너가 정리되지 않고 있는지 확인

### 4. API 호출 확인
- [ ] Network 탭에서 중복 API 호출 확인
- [ ] API 응답 시간 확인
- [ ] 불필요한 API 호출이 있는지 확인

## 성능 모니터링 스크립트

### 자동 성능 모니터링 시작

```javascript
// 콘솔에서 실행
debugPerformance.startMemoryMonitoring();

// 5초마다 성능 상태 출력
setInterval(() => {
    debugPerformance.status();
}, 5000);
```

### 성능 문제 자동 감지

```javascript
// 메모리 사용량이 높을 때 자동 정리
setInterval(() => {
    const memory = performance.memory;
    if (memory && memory.usedJSHeapSize / memory.jsHeapSizeLimit > 0.8) {
        console.warn('High memory usage detected, running cleanup...');
        debugPerformance.cleanup();
    }
}, 10000);
```

## Chrome 플래그 설정

성능 디버깅을 위해 Chrome을 다음 플래그로 실행:

```bash
# Windows
chrome.exe --enable-logging --v=1 --enable-gpu-rasterization --enable-zero-copy --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --disable-ipc-flooding-protection --expose-gc

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --enable-logging --v=1 --enable-gpu-rasterization --enable-zero-copy --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded-windows --disable-ipc-flooding-protection --expose-gc
```

## 추가 디버깅 팁

1. **Chrome Task Manager 사용**
   - Shift+Esc로 Task Manager 열기
   - JavaScript 메모리 사용량 확인
   - GPU 메모리 사용량 확인

2. **Performance Monitor 사용**
   - Chrome DevTools → More tools → Performance monitor
   - 실시간 CPU 및 메모리 사용량 모니터링

3. **Lighthouse 사용**
   - Chrome DevTools → Lighthouse 탭
   - 성능 점수 확인 및 개선 제안 받기

## 문제 해결 순서

1. **즉시 확인**: `debugPerformance.status()` 실행
2. **메모리 모니터링**: `debugPerformance.startMemoryMonitoring()` 실행
3. **강제 정리**: `debugPerformance.cleanup()` 실행
4. **성능 기록**: Chrome DevTools Performance 탭에서 기록
5. **메모리 스냅샷**: Memory 탭에서 힙 스냅샷 생성
6. **네트워크 분석**: Network 탭에서 API 호출 분석
7. **코드 최적화**: 발견된 문제점에 따라 코드 수정

이 가이드를 따라하면 Chrome에서 발생하는 성능 문제를 체계적으로 진단하고 해결할 수 있습니다. 