// Progress Note list page JS (dynamic site support)

// Use global progressNoteDB instance (without variable declaration)

// Current site setting (received from server or URL parameter or default value)
const currentSite = window.currentSite || new URLSearchParams(window.location.search).get('site') || 'Ramsay';

// Global client mapping object
let clientMap = {};

// Performance monitoring variables
let performanceMetrics = {
    startTime: null,
    intervals: new Set(),
    observers: new Set(),
    eventListeners: new Set()
};

// Performance monitoring function
function logPerformance(message, data = {}) {
    // Limit logging for performance improvement
    const isImportant = message.includes('error') || 
                       message.includes('failed') || 
                       message.includes('completed') ||
                       message.includes('initialization');
    
    if (!isImportant) {
        return; // Do not output unimportant logs
    }
    
    const timestamp = Date.now();
    const memory = performance.memory ? {
        used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
        total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
        limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
    } : null;
    
    console.log(`[PERF ${timestamp}] ${message}`, {
        ...data,
        memory,
        intervals: performanceMetrics.intervals.size,
        observers: performanceMetrics.observers.size,
        eventListeners: performanceMetrics.eventListeners.size
    });
}

// Cleanup function to prevent memory leaks
function cleanup() {
    logPerformance('Starting cleanup');
    
    // Clear all intervals
    performanceMetrics.intervals.forEach(intervalId => {
        clearInterval(intervalId);
    });
    performanceMetrics.intervals.clear();
    
    // Disconnect all observers
    performanceMetrics.observers.forEach(observer => {
        observer.disconnect();
    });
    performanceMetrics.observers.clear();
    
    // Remove event listeners (if we had stored references)
    performanceMetrics.eventListeners.clear();
    
    // Clear global variables
    if (window.allNotes) {
        window.allNotes.length = 0;
    }
    
    logPerformance('Cleanup completed');
}

// Refresh button control
function disableRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = 'Loading...';
        refreshBtn.style.opacity = '0.6';
        refreshBtn.style.cursor = 'not-allowed';
        
        // Automatically reactivate after 10 seconds
        setTimeout(() => {
            enableRefreshButton();
        }, 10000);
    }
}

function enableRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = 'Refresh';
        refreshBtn.style.opacity = '1';
        refreshBtn.style.cursor = 'pointer';
    }
}

// Load client information
async function loadClientMap() {
    try {
        const response = await fetch(`/data/${currentSite.toLowerCase().replace(' ', '_')}_client.json`);
        
        if (!response.ok) {
            throw new Error(`Failed to load client information: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // MainClientServiceId → clientInfo mapping (unified with string keys)
        clientMap = {};
        
        if (Array.isArray(data)) {
            data.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
            });
        } else if (data.Clients && Array.isArray(data.Clients)) {
            data.Clients.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
            });
        } else if (data.client_info && Array.isArray(data.client_info)) {
            data.client_info.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
            });
        }
        
    } catch (e) {
        console.error('Error loading client information:', e);
    }
}

// Load event types for filtering
async function loadEventTypes() {
    try {
        console.log('Loading event types...');
        
        const response = await fetch('/data/eventtype.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const eventTypeData = await response.json();
        console.log(`Loaded ${eventTypeData.length} event type records`);
        
        return eventTypeData;
    } catch (error) {
        console.error('Failed to load event types:', error);
        return [];
    }
}

// Get Resident of the day event type names for filtering
async function getResidentOfDayEventTypeNames() {
    try {
        const eventTypes = await loadEventTypes();
        const residentOfDayTypes = eventTypes
            .filter(et => et.Description && et.Description.toLowerCase().includes('resident of the day'))
            .map(et => et.Description);
        
        console.log(`Found ${residentOfDayTypes.length} Resident of the day event types:`, residentOfDayTypes);
        return residentOfDayTypes;
    } catch (error) {
        console.error('Failed to get Resident of the day event type names:', error);
        return [];
    }
}

// Field mapping (API data → table column)
function mapNoteToRow(note) {
    // Convert to string for mapping (resolve type mismatch)
    const clientServiceIdStr = String(note.ClientServiceId);
    let clientInfo = clientMap[clientServiceIdStr];
    
    // Extract client name
    let clientName = '';
    if (clientInfo) {
        clientName = [clientInfo.Title, clientInfo.FirstName, clientInfo.LastName].filter(Boolean).join(' ');
    } else if (note.Client) {
        clientName = [note.Client.Title, note.Client.FirstName, note.Client.LastName].filter(Boolean).join(' ');
    } else if (note.ClientName) {
        clientName = note.ClientName;
    } else if (note.Client && note.Client.Name) {
        clientName = note.Client.Name;
    } else if (note.ClientInfo && note.ClientInfo.Name) {
        clientName = note.ClientInfo.Name;
    } else if (note.ClientInfo && note.ClientInfo.FirstName) {
        clientName = [note.ClientInfo.Title, note.ClientInfo.FirstName, note.ClientInfo.LastName].filter(Boolean).join(' ');
    }
    
    // Extract service wing (location) - use WingName (use LocationName if client mapping fails)
    let serviceWing = '';
    if (clientInfo) {
        serviceWing = clientInfo.WingName || clientInfo.LocationName || '';
    } else {
        serviceWing = note.WingName || note.LocationName || (note.Client && note.Client.WingName) || (note.ClientInfo && note.ClientInfo.WingName) || '';
    }
    
    return {
        serviceWing: serviceWing,
        client: clientName,
        date: note.EventDate ? note.EventDate.split('T')[0] : '',
        time: note.EventDate ? (note.EventDate.split('T')[1] || '').slice(0,5) : '',
        eventType: note.ProgressNoteEventType?.Description || '',
        careAreas: (note.CareAreas || []).map(ca => ca.Description).join(', ')
    };
}

// Format note details
function formatNoteDetail(note) {
    // HTML 노트 내용을 안전하게 처리
    let safeHtmlNotes = '';
    if (note.HtmlNotes) {
        // style 태그와 body 태그를 제거하여 페이지 CSS에 영향을 주지 않도록 함
        safeHtmlNotes = note.HtmlNotes
            .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '') // style 태그 제거
            .replace(/<body[^>]*>/gi, '<div class="note-content">') // body 태그를 div로 변경
            .replace(/<\/body>/gi, '</div>') // body 닫는 태그를 div로 변경
            .replace(/<html[^>]*>/gi, '') // html 태그 제거
            .replace(/<\/html>/gi, '') // html 닫는 태그 제거
            .replace(/<head[^>]*>[\s\S]*?<\/head>/gi, ''); // head 태그와 내용 제거
    }
    
    return `
        <b>Event type:</b> ${note.ProgressNoteEventType?.Description || ''}<br>
        <b>Date:</b> ${note.EventDate ? note.EventDate.replace('T', ' ').slice(0, 16) : ''}<br>
        <b>Client:</b> ${note.ClientId || ''}<br>
        <b>Care area(s):</b> ${(note.CareAreas || []).map(ca => ca.Description).join(', ')}<br>
        <hr>
        <b>Notes:</b><br>
        <div style="background:#f7f7f7; padding:10px; border-radius:4px; font-size:0.97em; max-height:400px; overflow-y:auto;">
            ${safeHtmlNotes || (note.NotesPlainText || note.Notes || '')}
        </div>
    `;
}

// Table rendering
async function renderNotesTable() {
    const measure = window.performanceMonitor.startMeasure('renderNotesTable');
    const startTime = Date.now();
    
    await window.progressNoteDB.init();
    const { notes } = await window.progressNoteDB.getProgressNotes(currentSite, { limit: 10000, sortBy: 'eventDate', sortOrder: 'desc' });
    
    logPerformance(`Rendering table with ${notes.length} notes for site: ${currentSite}`, { 
        notesCount: notes.length,
        loadTime: Date.now() - startTime 
    });
    
    // 최신 데이터 로깅 (디버깅용)
    if (notes.length > 0) {
        console.log('Latest 5 notes from IndexedDB:');
        notes.slice(0, 5).forEach((note, index) => {
            console.log(`  ${index + 1}. ID: ${note.Id}, EventDate: ${note.EventDate}, CreatedDate: ${note.CreatedDate || 'N/A'}`);
        });
    }
    
    // 최신 데이터 로깅 (성능 개선을 위해 간소화)
    if (notes.length > 0) {
        // 성능 개선을 위해 상세 로깅 제거
        // logPerformance('Latest 5 notes in table:', {
        //     notes: notes.slice(0, 5).map((note, index) => ({
        //         index: index + 1,
        //         id: note.Id,
        //         eventDate: note.EventDate,
        //         createdDate: note.CreatedDate || 'N/A'
        //     }))
        // });
    }
    
    // 전역 변수에 모든 노트 데이터 저장 (필터링용)
    window.allNotes = notes.map(note => mapNoteToRow(note));
    
    const tbody = document.querySelector('#notesTable tbody');
    tbody.innerHTML = '';
    
    // Batch DOM operations for better performance
    const fragment = document.createDocumentFragment();
    
    notes.forEach((note, idx) => {
        const rowData = mapNoteToRow(note);
        const tr = document.createElement('tr');
        tr.dataset.idx = idx;
        Object.values(rowData).forEach(val => {
            const td = document.createElement('td');
            td.textContent = val;
            tr.appendChild(td);
        });
        tr.addEventListener('click', () => selectNote(idx, notes));
        fragment.appendChild(tr);
    });
    
    tbody.appendChild(fragment);
    
    // 페이지네이션 UI 강제 표시 (일반 목록 보기에서도)
    if (notes.length > 0) {
        console.log('강제로 페이지네이션 UI 표시 중...');
        
        // 서버에서 받은 페이지네이션 정보 사용 (우선순위)
        let paginationData;
        if (window.serverPagination) {
            console.log('서버 페이지네이션 정보 사용:', window.serverPagination);
            paginationData = window.serverPagination;
        } else {
            // 서버 페이지네이션 정보가 없으면 전체 노트 수 사용
            const totalCount = window.allNotes ? window.allNotes.length : notes.length;
            console.log('전체 노트 수 사용:', totalCount, '현재 표시된 노트 수:', notes.length);
            
            paginationData = {
                page: 1,
                per_page: 50,
                total_count: totalCount,
                total_pages: Math.ceil(totalCount / 50)
            };
        }
        
        console.log('최종 페이지네이션 데이터:', paginationData);
        updatePaginationUI(paginationData);
    }
    
    // Auto-select first visible row
    if (notes.length > 0) {
        selectNote(0, notes);
    }
    
    logPerformance('Table rendering completed', { 
        totalTime: Date.now() - startTime,
        rowsRendered: notes.length 
    });
    
    measure.end();
}

// Show details when row is selected
function selectNote(idx, notes) {
    // Row highlight
    document.querySelectorAll('#notesTable tbody tr').forEach((tr, i) => {
        tr.classList.toggle('selected', i === idx);
    });
    // Show detail content
    const note = notes[idx];
    document.getElementById('noteDetailContent').innerHTML = formatNoteDetail(note);
}

// Update progress notes table with new data
function updateProgressNotesTable(notes) {
    console.log('Updating table with', notes.length, 'notes');
    
    const tbody = document.querySelector('#notesTable tbody');
    tbody.innerHTML = '';
    
    // Batch DOM operations for better performance
    const fragment = document.createDocumentFragment();
    
    notes.forEach((note, idx) => {
        const rowData = mapNoteToRow(note);
        const tr = document.createElement('tr');
        tr.dataset.idx = idx;
        Object.values(rowData).forEach(val => {
            const td = document.createElement('td');
            td.textContent = val;
            tr.appendChild(td);
        });
        tr.addEventListener('click', () => selectNote(idx, notes));
        fragment.appendChild(tr);
    });
    
    tbody.appendChild(fragment);
    
    // Auto-select first visible row
    if (notes.length > 0) {
        selectNote(0, notes);
    }
    
    console.log('Table updated successfully');
}

// Execute on page load
window.addEventListener('DOMContentLoaded', async () => {
    performanceMetrics.startTime = Date.now();
    logPerformance('Page loaded - starting initialization', { currentSite });
    
    // 사이트 제목 업데이트
    const siteTitle = document.getElementById('siteTitle');
    if (siteTitle) {
        siteTitle.textContent = `Progress Notes - ${currentSite}`;
    }
    
    // Detect site change and initialize
    await initializeForSite(currentSite);
    
    // Detect URL change (browser back/forward)
    window.addEventListener('popstate', handleSiteChange);
    
    // Detect URL change (programmatic) - with proper cleanup
    let currentUrl = window.location.href;
    const observer = new MutationObserver(() => {
        if (window.location.href !== currentUrl) {
            currentUrl = window.location.href;
            handleSiteChange();
        }
    });
    observer.observe(document, { subtree: true, childList: true });
    performanceMetrics.observers.add(observer);
    
    // Add cleanup on page unload
    window.addEventListener('beforeunload', cleanup);
    window.addEventListener('pagehide', cleanup);
    
    logPerformance('Initialization completed');
});

// Site-specific initialization function
async function initializeForSite(site) {
    logPerformance(`Initializing for site: ${site}`);
    
    try {
        // Refresh 버튼 비활성화
        disableRefreshButton();
        
        // 1. Load client mapping first (differs by site)
        await loadClientMap();
        
        // 2. Initialize IndexedDB
        await window.progressNoteDB.init();
        
        // 3. Clear existing data and fetch 1 week of data
        logPerformance('Clearing existing data and fetching 1 week of data for site:', { site });
        await window.progressNoteDB.deleteProgressNotes(site);
        
        // 일반 프로그레스 노트 목록: 모든 노트 가져오기 (성능 최적화를 위해 기본 limit 사용)
        console.log('Fetching all progress notes for general list view');
        await fetchAndSaveProgressNotes();
        
        // 4. Table rendering
        await renderNotesTable();
        
        logPerformance('Site initialization completed for:', { site });
    } catch (error) {
        console.error('Error during site initialization for:', site, error);
        logPerformance('Site initialization failed:', { site, error: error.message });
    }
}

// Fetch Progress Notes from server and save (full refresh)
async function fetchAndSaveProgressNotes(eventTypes = null) {
    try {
        console.log('Starting to fetch Progress Notes from server...');
        
        // Prepare request body
        const requestBody = {
            site: currentSite,
            days: 7  // 1주일 데이터만 가져오기
        };
        
        // Add event types if specified
        if (eventTypes && eventTypes.length > 0) {
            requestBody.event_types = eventTypes;
            console.log(`Fetching progress notes with event type filtering: ${eventTypes.join(', ')}`);
        } else {
            console.log('Fetching all progress notes (no event type filtering)');
        }
        
        const response = await fetch('/api/fetch-progress-notes-cached', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`Successfully fetched ${result.count} Progress Notes from server`);
            
            // 서버에서 받은 페이지네이션 정보를 전역 변수에 저장
            if (result.pagination) {
                window.serverPagination = result.pagination;
                console.log('서버 페이지네이션 정보 저장:', result.pagination);
            }
            
            // Save to IndexedDB
            if (result.data && result.data.length > 0) {
                const saveResult = await window.progressNoteDB.saveProgressNotes(currentSite, result.data);
                console.log('IndexedDB save result:', saveResult);
                
                // Save last update time (use UTC time for API compatibility)
                const utcTime = new Date().toISOString();
                await window.progressNoteDB.saveLastUpdateTime(currentSite, utcTime);
                
                console.log('Progress Note data saved successfully');
            } else {
                console.log('No progress notes found.');
            }
        } else {
            throw new Error(result.message || 'Failed to fetch Progress Notes');
        }
    } catch (error) {
        console.error('Failed to fetch Progress Notes:', error);
        
        // 사용자에게 에러 메시지 표시
        const errorMessage = `데이터 가져오기 실패: ${error.message}`;
        showErrorMessage(errorMessage);
        
        // 에러 로그를 서버로 전송 (선택사항)
        try {
            await fetch('/api/log-rod-debug', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    error: 'Progress Notes fetch failed',
                    message: error.message,
                    site: currentSite,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (logError) {
            console.error('Failed to log error to server:', logError);
        }
    }
}

// 에러 메시지 표시 함수
function showErrorMessage(message) {
    // 기존 에러 메시지 제거
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // 새 에러 메시지 생성
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ff4444;
        color: white;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        z-index: 1000;
        max-width: 400px;
        word-wrap: break-word;
    `;
    errorDiv.innerHTML = `
        <strong>오류 발생</strong><br>
        ${message}<br>
        <small>자동으로 사라집니다</small>
    `;
    
    document.body.appendChild(errorDiv);
    
    // 10초 후 자동 제거
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 10000);
}

// 수동 새로고침 함수
async function refreshData() {
    try {
        console.log('Manual refresh requested for site:', currentSite);
        
        // Refresh 버튼 비활성화
        disableRefreshButton();
        
        // Clear existing data and fetch 1 week of data
        await window.progressNoteDB.deleteProgressNotes(currentSite);
        
        // 일반 프로그레스 노트 목록: 모든 노트 가져오기 (성능 최적화를 위해 기본 limit 사용)
        console.log('Fetching all progress notes for general list view');
        await fetchAndSaveProgressNotes();
        
        // 테이블 다시 렌더링
        await renderNotesTable();
    } catch (error) {
        console.error('Refresh failed for site:', currentSite, error);
    }
}

// 전역 함수로 노출 (테스트용)
window.testIncrementalUpdate = () => {
    console.log('Incremental update is disabled. Use refreshData() instead.');
};

// 사이트 변경 시 호출할 함수 (URL 파라미터 변경 시)
function handleSiteChange() {
    const urlParams = new URLSearchParams(window.location.search);
    const newSite = urlParams.get('site') || 'Ramsay';
    
    if (newSite !== currentSite) {
        logPerformance('Site changed from', { from: currentSite, to: newSite });
        currentSite = newSite;
        
        // Update site title
        const siteTitle = document.getElementById('siteTitle');
        if (siteTitle) {
            siteTitle.textContent = `Progress Notes - ${currentSite}`;
        }
        
        // 새로운 사이트로 초기화
        initializeForSite(currentSite);
    }
}

// 증분 업데이트 함수는 제거됨 (항상 1주일 데이터를 가져옴)
async function fetchIncrementalProgressNotes(lastUpdateTime) {
    console.log('Incremental update is disabled. Fetching 1 week of data instead.');
    await fetchAndSaveProgressNotes();
}

// Performance debugging tools (available in console)
window.debugPerformance = {
    // 현재 성능 상태 출력
    status: () => {
        const memory = performance.memory ? {
            used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
            total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
            limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
        } : null;
        
        console.log('=== Performance Status ===');
        console.log('Memory:', memory);
        console.log('Active intervals:', performanceMetrics.intervals.size);
        console.log('Active observers:', performanceMetrics.observers.size);
        console.log('Event listeners:', performanceMetrics.eventListeners.size);
        console.log('All notes count:', window.allNotes ? window.allNotes.length : 0);
        console.log('Client map size:', Object.keys(clientMap).length);
        
        // List active intervals
        if (performanceMetrics.intervals.size > 0) {
            console.log('Active interval IDs:', Array.from(performanceMetrics.intervals));
        }
        
        // List active observers
        if (performanceMetrics.observers.size > 0) {
            console.log('Active observers:', Array.from(performanceMetrics.observers));
        }
    },
    
    // 강제 정리
    cleanup: () => {
        cleanup();
        console.log('Forced cleanup completed');
    },
    
    // 메모리 사용량 모니터링 시작
    startMemoryMonitoring: () => {
        if (window.debugPerformance.memoryInterval) {
            clearInterval(window.debugPerformance.memoryInterval);
        }
        
        window.debugPerformance.memoryInterval = setInterval(() => {
            const memory = performance.memory;
            if (memory) {
                const used = Math.round(memory.usedJSHeapSize / 1024 / 1024);
                const total = Math.round(memory.totalJSHeapSize / 1024 / 1024);
                const limit = Math.round(memory.jsHeapSizeLimit / 1024 / 1024);
                
                console.log(`Memory: ${used}MB / ${total}MB (${limit}MB limit)`);
                
                // 메모리 사용량이 80%를 넘으면 경고
                if (used / limit > 0.8) {
                    console.warn('⚠️ High memory usage detected!');
                }
            }
        }, 5000); // 5초마다 체크
        
        console.log('Memory monitoring started');
    },
    
    // 메모리 모니터링 중지
    stopMemoryMonitoring: () => {
        if (window.debugPerformance.memoryInterval) {
            clearInterval(window.debugPerformance.memoryInterval);
            window.debugPerformance.memoryInterval = null;
            console.log('Memory monitoring stopped');
        }
    },
    
    // 가비지 컬렉션 강제 실행 (가능한 경우)
    forceGC: () => {
        if (window.gc) {
            window.gc();
            console.log('Garbage collection forced');
        } else {
            console.log('Garbage collection not available (use --expose-gc flag)');
        }
    }
};

// Chrome DevTools Performance Panel Integration
if (window.chrome && window.chrome.devtools) {
    // DevTools가 열려있을 때만 실행
    window.addEventListener('devtoolschange', (e) => {
        if (e.detail.open) {
            console.log('DevTools opened - enabling detailed performance monitoring');
            logPerformance('DevTools opened');
        }
    });
}

// Performance monitoring for Chrome DevTools
window.performanceMonitor = {
    // 성능 마커 추가
    mark: (name) => {
        if (performance.mark) {
            performance.mark(name);
        }
        logPerformance(`Mark: ${name}`);
    },
    
    // 성능 측정
    measure: (name, startMark, endMark) => {
        if (performance.measure) {
            try {
                const measure = performance.measure(name, startMark, endMark);
                logPerformance(`Measure: ${name}`, {
                    duration: Math.round(measure.duration),
                    startTime: Math.round(measure.startTime)
                });
                return measure;
            } catch (e) {
                console.warn(`Failed to measure ${name}:`, e);
            }
        }
    },
    
    // 성능 측정 시작
    startMeasure: (name) => {
        const startMark = `${name}-start`;
        performance.mark(startMark);
        return {
            end: () => {
                const endMark = `${name}-end`;
                performance.mark(endMark);
                window.performanceMonitor.measure(name, startMark, endMark);
            }
        };
    }
};

// 페이지네이션 관련 전역 변수
let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let perPage = 50;
let currentPaginationData = null;

// 페이지네이션 기능
function updatePaginationUI(paginationData) {
    console.log('updatePaginationUI called with:', paginationData);
    currentPaginationData = paginationData;
    currentPage = paginationData.page;
    totalPages = paginationData.total_pages;
    totalCount = paginationData.total_count;
    
    const container = document.getElementById('paginationContainer');
    const info = document.getElementById('paginationInfo');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const pageNumbers = document.getElementById('pageNumbers');
    
    console.log('Pagination elements found:', {
        container: !!container,
        info: !!info,
        prevBtn: !!prevBtn,
        nextBtn: !!nextBtn,
        pageNumbers: !!pageNumbers
    });
    
    if (!container || !info || !prevBtn || !nextBtn || !pageNumbers) {
        console.error('페이지네이션 UI 요소를 찾을 수 없습니다.');
        return;
    }
    
    // Update page information
    const startItem = (currentPage - 1) * perPage + 1;
    const endItem = Math.min(currentPage * perPage, totalCount);
    info.textContent = `Showing ${startItem}-${endItem} of ${totalCount} items (Page ${currentPage}/${totalPages})`;
    
    // Update Previous/Next button states
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
    
    // Generate page numbers (forced display version)
    console.log('Creating page numbers...', { currentPage, totalPages });
    pageNumbers.innerHTML = '';
    
    // Show maximum 10 page numbers
    const maxVisiblePages = Math.min(10, totalPages);
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Adjust start page
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    console.log('Page range:', { startPage, endPage, totalPages });
    
    // Create page number buttons
    for (let i = startPage; i <= endPage; i++) {
        console.log(`Creating page button for page ${i}`);
        const pageBtn = document.createElement('button');
        pageBtn.className = `page-number ${i === currentPage ? 'active' : ''}`;
        pageBtn.textContent = i;
        pageBtn.onclick = () => {
            console.log(`Page ${i} clicked`);
            goToPage(i);
        };
        pageNumbers.appendChild(pageBtn);
    }
    
    console.log('Page numbers created:', pageNumbers.children.length, 'buttons');
    
    // Force page numbers to be visible with styles
    pageNumbers.style.display = 'flex';
    pageNumbers.style.gap = '5px';
    pageNumbers.style.justifyContent = 'center';
    pageNumbers.style.alignItems = 'center';
    
    // Show container
    console.log('Showing pagination container');
    container.style.display = 'block';
    
    // Debug: Output pagination information
    console.log('Pagination UI updated:', {
        currentPage,
        totalPages,
        totalCount,
        perPage,
        startItem: (currentPage - 1) * perPage + 1,
        endItem: Math.min(currentPage * perPage, totalCount)
    });
}

function changePage(direction) {
    console.log(`changePage called: direction=${direction}, currentPage=${currentPage}, totalPages=${totalPages}`);
    const newPage = currentPage + direction;
    if (newPage >= 1 && newPage <= totalPages) {
        console.log(`Going to page: ${newPage}`);
        goToPage(newPage);
    } else {
        console.log(`Invalid page: ${newPage} (must be between 1 and ${totalPages})`);
    }
}

function goToPage(page) {
    console.log(`goToPage called: page=${page}, currentPage=${currentPage}, totalPages=${totalPages}`);
    if (page < 1 || page > totalPages) {
        console.log(`Invalid page: ${page} (must be between 1 and ${totalPages})`);
        return;
    }
    
    if (page === currentPage) {
        console.log(`Same page: ${page} - no action needed`);
        return;
    }
    
    console.log(`Changing to page: ${page}`);
    currentPage = page;
    loadProgressNotes();
}

function changePerPage() {
    const select = document.getElementById('perPageSelect');
    perPage = parseInt(select.value);
    currentPage = 1; // Reset to first page
    loadProgressNotes();
}


function updateCacheStatus(cacheInfo) {
    const statusDiv = document.getElementById('cacheStatus');
    const statusText = document.getElementById('cacheStatusText');
    
    if (!statusDiv || !statusText) {
        return;
    }
    
    let statusClass = 'cached';
    let statusMessage = 'Loaded from cache';
    
    if (cacheInfo.status === 'api-fresh') {
        statusClass = 'api-fresh';
        statusMessage = 'Freshly loaded from API';
    } else if (cacheInfo.status === 'error') {
        statusClass = 'error';
        statusMessage = 'Error occurred during loading';
    } else if (cacheInfo.status === 'cached') {
        const ageHours = cacheInfo.cache_age_hours || 0;
        if (ageHours < 1) {
            statusMessage = `Loaded from cache (${Math.round(ageHours * 60)} minutes ago)`;
        } else {
            statusMessage = `Loaded from cache (${Math.round(ageHours)} hours ago)`;
        }
    }
    
    statusText.textContent = statusMessage;
    statusDiv.className = `cache-status ${statusClass}`;
    statusDiv.style.display = 'block';
}

// 기존 loadProgressNotes 함수 수정
async function loadProgressNotes(forceRefresh = false) {
    try {
        performanceMonitor.startMeasure('loadProgressNotes');
        
        const requestBody = {
            site: currentSite,
            days: 7,
            page: currentPage,
            per_page: perPage,
            force_refresh: forceRefresh
        };
        
        console.log(`Loading progress notes - Page: ${currentPage}, Per Page: ${perPage}, Force Refresh: ${forceRefresh}`);
        
        const response = await fetch('/api/fetch-progress-notes-cached', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('API Response:', result);
        
        if (result.success) {
            // 데이터 표시
            updateProgressNotesTable(result.data);
            
            // 페이지네이션 UI 업데이트
            console.log('Pagination data:', result.pagination);
            if (result.pagination) {
                console.log('Updating pagination UI...', result.pagination);
                updatePaginationUI(result.pagination);
            } else {
                console.log('No pagination data received - creating default pagination');
                // API에서 페이지네이션 데이터가 없으면 기본값으로 생성
                const defaultPagination = {
                    page: currentPage,
                    per_page: perPage,
                    total_count: result.data ? result.data.length : 0,
                    total_pages: Math.ceil((result.data ? result.data.length : 0) / perPage)
                };
                console.log('Using default pagination:', defaultPagination);
                updatePaginationUI(defaultPagination);
            }
            
            // 캐시 상태 표시
            if (result.cache_info) {
                updateCacheStatus(result.cache_info);
            }
            
            console.log(`Progress notes loaded successfully - ${result.count} items (Page ${currentPage}/${result.pagination?.total_pages || 1})`);
        } else {
            throw new Error(result.message || 'Failed to load progress notes');
        }
        
    } catch (error) {
        console.error('Error loading progress notes:', error);
        showError(`Failed to load progress notes: ${error.message}`);
    } finally {
        performanceMonitor.endMeasure('loadProgressNotes');
    }
}

// 페이지 로드 시 디버깅 도구 안내
console.log('Performance debugging tools available:');
console.log('- debugPerformance.status() - 현재 성능 상태 확인');
console.log('- debugPerformance.cleanup() - 강제 정리');
console.log('- debugPerformance.startMemoryMonitoring() - 메모리 모니터링 시작');
console.log('- debugPerformance.stopMemoryMonitoring() - 메모리 모니터링 중지');
console.log('- debugPerformance.forceGC() - 가비지 컬렉션 강제 실행');
console.log('- performanceMonitor.mark("name") - 성능 마커 추가');
console.log('- performanceMonitor.startMeasure("name") - 성능 측정 시작'); 