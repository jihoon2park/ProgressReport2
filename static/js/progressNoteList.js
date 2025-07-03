// Progress Note list page JS (dynamic site support)

// Use global progressNoteDB instance (without variable declaration)

// Current site setting (received from server or URL parameter or default value)
const currentSite = window.currentSite || new URLSearchParams(window.location.search).get('site') || 'Ramsay';

// 전역 클라이언트 매핑 객체
let clientMap = {};

// Top progress bar control
function showTopProgressBar() {
    const bar = document.getElementById('top-progress-bar');
    if (!bar) return;
    
    // Record start time for minimum loading duration
    bar._loadingStartTime = Date.now();
    
    // Reset and show progress bar
    bar.style.width = '0%';
    bar.style.display = 'block';
    
    // Animate progress bar with repeating animation
    let progress = 0;
    const animateProgress = () => {
        progress += 2;
        if (progress > 90) {
            progress = 0;
        }
        bar.style.width = progress + '%';
    };
    
    // Start animation
    bar._progressInterval = setInterval(animateProgress, 100);
    
    // Disable refresh button and show loading state
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.textContent = 'Loading...';
        refreshBtn.style.opacity = '0.6';
        refreshBtn.style.cursor = 'not-allowed';
    }
    
    // Show loading message in table area
    const tableContainer = document.getElementById('notesTable');
    if (tableContainer) {
        const loadingMsg = document.createElement('div');
        loadingMsg.id = 'loadingMessage';
        loadingMsg.style.cssText = `
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 14px;
            background: #f9f9f9;
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #e0e0e0;
        `;
        loadingMsg.innerHTML = `
            <div style="margin-bottom: 10px;">
                <div style="width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto;"></div>
            </div>
            Loading data from Manad plus server...
        `;
        tableContainer.parentNode.insertBefore(loadingMsg, tableContainer);
    }
}

function hideTopProgressBar() {
    const bar = document.getElementById('top-progress-bar');
    if (!bar) return;
    
    // Calculate elapsed time
    const elapsedTime = Date.now() - (bar._loadingStartTime || 0);
    const minLoadingTime = 10000; // 10 seconds minimum
    const remainingTime = Math.max(0, minLoadingTime - elapsedTime);
    
    // If minimum time hasn't passed, wait
    if (remainingTime > 0) {
        setTimeout(() => {
            hideTopProgressBar();
        }, remainingTime);
        return;
    }
    
    // Stop the animation
    if (bar._progressInterval) {
        clearInterval(bar._progressInterval);
        bar._progressInterval = null;
    }
    
    // Complete the progress bar
    bar.style.width = '100%';
    setTimeout(() => {
        bar.style.display = 'none';
        bar.style.width = '0%';
    }, 350);
    
    // Re-enable refresh button and restore original state
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.textContent = 'Refresh';
        refreshBtn.style.opacity = '1';
        refreshBtn.style.cursor = 'pointer';
    }
    
    // Remove loading message
    const loadingMsg = document.getElementById('loadingMessage');
    if (loadingMsg) {
        loadingMsg.remove();
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
        recordId: note.Id || note.ClientServiceId || '',
        serviceWing: serviceWing,
        client: clientName,
        date: note.EventDate ? note.EventDate.split('T')[0] : '',
        time: note.EventDate ? (note.EventDate.split('T')[1] || '').slice(0,5) : '',
        lateEntry: note.IsLateEntry ? '✔' : '',
        eventType: note.ProgressNoteEventType?.Description || '',
        careAreas: (note.CareAreas || []).map(ca => ca.Description).join(', '),
        createdBy: note.CreatedByName || note.CreatedBy || (note.CreatedByUser?.UserName || '')
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
        <b>Created by:</b> ${note.CreatedByName || note.CreatedBy || (note.CreatedByUser?.UserName || '')}<br>
        <b>Late entry:</b> ${note.IsLateEntry ? 'Yes' : 'No'}<br>
        <hr>
        <b>Notes:</b><br>
        <div style="background:#f7f7f7; padding:10px; border-radius:4px; font-size:0.97em; max-height:400px; overflow-y:auto;">
            ${safeHtmlNotes || (note.NotesPlainText || note.Notes || '')}
        </div>
    `;
}

// Table rendering
async function renderNotesTable() {
    await window.progressNoteDB.init();
    const { notes } = await window.progressNoteDB.getProgressNotes(currentSite, { limit: 10000, sortBy: 'EventDate', sortOrder: 'desc' });
    
    console.log(`Rendering table with ${notes.length} notes for site: ${currentSite}`);
    
    // 최신 데이터 로깅
    if (notes.length > 0) {
        console.log('Latest 5 notes in table:');
        notes.slice(0, 5).forEach((note, index) => {
            console.log(`${index + 1}. ID: ${note.Id}, EventDate: ${note.EventDate}, CreatedDate: ${note.CreatedDate || 'N/A'}`);
        });
    }
    
    // 전역 변수에 모든 노트 데이터 저장 (필터링용)
    window.allNotes = notes.map(note => mapNoteToRow(note));
    
    const tbody = document.querySelector('#notesTable tbody');
    tbody.innerHTML = '';
    
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
        tbody.appendChild(tr);
    });
    
    // 필터 적용 (기존 필터가 있는 경우)
    if (window.currentFilters && (window.currentFilters.client || window.currentFilters.eventType)) {
        window.applyFilters();
    }
    
    // Auto-select first visible row
    if (notes.length > 0) {
        selectNote(0, notes);
    }
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

// Execute on page load
window.addEventListener('DOMContentLoaded', async () => {
    console.log('Page loaded - starting initialization');
    console.log('Current site:', currentSite);
    
    // 사이트 제목 업데이트
    const siteTitle = document.getElementById('siteTitle');
    if (siteTitle) {
        siteTitle.textContent = `Progress Notes - ${currentSite}`;
    }
    
    // Detect site change and initialize
    await initializeForSite(currentSite);
    
    // Detect URL change (browser back/forward)
    window.addEventListener('popstate', handleSiteChange);
    
    // Detect URL change (programmatic)
    let currentUrl = window.location.href;
    const observer = new MutationObserver(() => {
        if (window.location.href !== currentUrl) {
            currentUrl = window.location.href;
            handleSiteChange();
        }
    });
    observer.observe(document, { subtree: true, childList: true });
});

// Site-specific initialization function
async function initializeForSite(site) {
    console.log(`Initializing for site: ${site}`);
    
    try {
        showTopProgressBar(); // 로딩 상태 시작
        
        // 1. Load client mapping first (differs by site)
        await loadClientMap();
        
        // 2. Initialize IndexedDB
        await window.progressNoteDB.init();
        
        // 3. Always fetch 2 weeks of data
        console.log('Fetching 2 weeks of data for site:', site);
        await fetchAndSaveProgressNotes();
        
        // 4. Table rendering
        await renderNotesTable();
        
        console.log('Site initialization completed for:', site);
        hideTopProgressBar(); // 로딩 상태 종료
    } catch (error) {
        hideTopProgressBar(); // 에러 시에도 로딩 상태 종료
        console.error('Error during site initialization for:', site, error);
    }
}

// Fetch Progress Notes from server and save (full refresh)
async function fetchAndSaveProgressNotes() {
    try {
        console.log('Starting to fetch Progress Notes from server...');
        
        const response = await fetch('/api/fetch-progress-notes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                site: currentSite,
                days: 14
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`Successfully fetched ${result.count} Progress Notes from server`);
            
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
        
        hideTopProgressBar();
    } catch (error) {
        hideTopProgressBar();
        console.error('Failed to fetch Progress Notes:', error);
    }
}

// 수동 새로고침 함수
async function refreshData() {
    try {
        showTopProgressBar(); // 로딩 상태 시작
        console.log('Manual refresh requested for site:', currentSite);
        
        // Always fetch 2 weeks of data
        await fetchAndSaveProgressNotes();
        
        // 테이블 다시 렌더링
        await renderNotesTable();
        hideTopProgressBar(); // 테이블 렌더링 끝난 후 프로그레스 바 닫기
    } catch (error) {
        hideTopProgressBar();
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
        console.log('Site changed from', currentSite, 'to', newSite);
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

// 증분 업데이트 함수는 제거됨 (항상 전체 데이터를 가져옴)
async function fetchIncrementalProgressNotes(lastUpdateTime) {
    console.log('Incremental update is disabled. Fetching full data instead.');
    await fetchAndSaveProgressNotes();
} 