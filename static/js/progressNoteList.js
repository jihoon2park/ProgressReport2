// Progress Note list page JS (dynamic site support)
console.log('[progressNoteList.js] ========== SCRIPT LOADED ==========');
console.log('[progressNoteList.js] Script file loaded at:', new Date().toISOString());

// Use global progressNoteDB instance (without variable declaration)

// Current site setting (received from server or URL parameter or default value)
let currentSite = window.currentSite || new URLSearchParams(window.location.search).get('site') || 'Ramsay';
console.log('[progressNoteList.js] Current site determined:', currentSite);
console.log('[progressNoteList.js] window.currentSite:', window.currentSite);
console.log('[progressNoteList.js] URL params:', new URLSearchParams(window.location.search).get('site'));

// Immediate check for progressNoteDB
if (typeof window.progressNoteDB !== 'undefined') {
    console.log('[progressNoteList.js] progressNoteDB is already available');
} else {
    console.warn('[progressNoteList.js] progressNoteDB is not yet available (will check again on DOMContentLoaded)');
}

// Global client mapping object
let clientMap = {};

// Global client list for filter dropdown
let clientList = [];

// Selected client filter (PersonId)
let selectedClientId = null;

// Selected event type filter (server filter; value '' or '__fall__' or exact Description)
let selectedEventType = '';

/**
 * Single source of truth for Reporting Period options (nursing system: no hardcoded values in HTML).
 * First entry = default period (cached API used only for first visit / All Clients + this period).
 * To change default to 2 weeks: put { value: 14, label: '2 weeks' } first, or set DEFAULT_PERIOD_DAYS = 14.
 */
const PERIOD_OPTIONS = [
    { value: 7, label: '1 week' },
    { value: 14, label: '2 weeks' },
    { value: 21, label: '3 weeks' },
    { value: 28, label: '4 weeks' }
];

/** Default period in days (must match first PERIOD_OPTIONS entry when that is the cached/default period). */
const DEFAULT_PERIOD_DAYS = PERIOD_OPTIONS[0].value;

/** Allowed period values for validation. */
const PERIOD_VALUES = Object.freeze(PERIOD_OPTIONS.map(function (o) { return o.value; }));

/** Period in days from Reporting Period dropdown. Max notes returned = within this range only. */
function getPeriodDays() {
    const el = document.getElementById('reportingPeriodFilter');
    if (!el) return DEFAULT_PERIOD_DAYS;
    const v = parseInt(el.value, 10);
    return (PERIOD_VALUES.indexOf(v) >= 0) ? v : DEFAULT_PERIOD_DAYS;
}

/** True when client, period, or event type differs from default — use server pagination, not cached API. */
function isFilterMode() {
    return selectedClientId != null || getPeriodDays() !== DEFAULT_PERIOD_DAYS || selectedEventType !== '';
}

/** Value for grouped Fall event types (any description containing 'fall'). */
const EVENT_TYPE_FALL = '__fall__';

/** Cached event types per site. Load once per site, bind to select. */
let cachedEventTypesBySite = {};

/**
 * Load event types for current site once and cache. Populate #eventTypeFilter from cache.
 * Call on init and when site changes.
 */
async function populateEventTypeFilter() {
    const el = document.getElementById('eventTypeFilter');
    if (!el) return;
    const currentValue = el.value;
    try {
        if (!cachedEventTypesBySite[currentSite]) {
            const response = await fetch('/api/event-types', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ site: currentSite })
            });
            const result = await response.json();
            let raw = (result.success && result.data) ? result.data : [];
            cachedEventTypesBySite[currentSite] = Array.isArray(raw) ? raw : (raw && raw.data) ? raw.data : [];
        }
        const allTypes = cachedEventTypesBySite[currentSite];
        const fallLabels = new Set();
        const otherLabels = new Set();
        allTypes.forEach(function (et) {
            const desc = (et.Description || '').trim();
            if (!desc) return;
            if (desc.toLowerCase().indexOf('fall') >= 0) {
                fallLabels.add(desc);
            } else {
                otherLabels.add(desc);
            }
        });
        el.innerHTML = '';
        const optAll = document.createElement('option');
        optAll.value = '';
        optAll.textContent = 'All Event Types';
        el.appendChild(optAll);
        if (fallLabels.size > 0) {
            const optFall = document.createElement('option');
            optFall.value = EVENT_TYPE_FALL;
            optFall.textContent = 'Fall';
            el.appendChild(optFall);
        }
        Array.from(otherLabels).sort().forEach(function (label) {
            const opt = document.createElement('option');
            opt.value = label;
            opt.textContent = label;
            el.appendChild(opt);
        });
        if (currentValue && (currentValue === EVENT_TYPE_FALL || Array.from(otherLabels).indexOf(currentValue) >= 0)) {
            el.value = currentValue;
        } else {
            el.value = '';
            selectedEventType = '';
        }
    } catch (e) {
        console.error('[populateEventTypeFilter]', e);
    }
}

/** Populate #reportingPeriodFilter from PERIOD_OPTIONS. Call before any fetch that uses getPeriodDays(). */
function populatePeriodFilter() {
    const el = document.getElementById('reportingPeriodFilter');
    if (!el) return;
    el.innerHTML = '';
    PERIOD_OPTIONS.forEach(function (opt) {
        const option = document.createElement('option');
        option.value = String(opt.value);
        option.textContent = opt.label;
        if (opt.value === DEFAULT_PERIOD_DAYS) {
            option.selected = true;
        }
        el.appendChild(option);
    });
}

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
        console.log('[loadClientMap] Starting to load client map for site:', currentSite);
        const url = `/data/${currentSite.toLowerCase().replace(' ', '_')}_client.json`;
        console.log('[loadClientMap] Fetching from:', url);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[loadClientMap] HTTP error:', {
                status: response.status,
                statusText: response.statusText,
                url: url,
                errorText: errorText
            });
            throw new Error(`Failed to load client information: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('[loadClientMap] Received data:', {
            isArray: Array.isArray(data),
            hasClients: !!data.Clients,
            hasClientInfo: !!data.client_info,
            dataType: typeof data
        });
        
        // MainClientServiceId → clientInfo mapping (unified with string keys)
        clientMap = {};
        let mappedCount = 0;
        
        if (Array.isArray(data)) {
            console.log('[loadClientMap] Processing array data, length:', data.length);
            data.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                    mappedCount++;
                }
            });
        } else if (data.Clients && Array.isArray(data.Clients)) {
            console.log('[loadClientMap] Processing data.Clients array, length:', data.Clients.length);
            data.Clients.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                    mappedCount++;
                }
            });
        } else if (data.client_info && Array.isArray(data.client_info)) {
            console.log('[loadClientMap] Processing data.client_info array, length:', data.client_info.length);
            data.client_info.forEach((client) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                    mappedCount++;
                }
            });
        } else {
            console.warn('[loadClientMap] Unknown data structure:', Object.keys(data));
        }
        
        console.log('[loadClientMap] Client map created successfully:', {
            totalMapped: mappedCount,
            mapSize: Object.keys(clientMap).length
        });
        
    } catch (e) {
        console.error('[loadClientMap] Error loading client information:', {
            error: e,
            message: e.message,
            stack: e.stack,
            site: currentSite
        });
        clientMap = {}; // Reset to empty map on error
    }
}

// Load client list for filter dropdown
async function loadClientListForFilter() {
    try {
        console.log(`Loading client list for filter - site: ${currentSite}`);
        const url = `/api/clients/${encodeURIComponent(currentSite)}`;
        console.log(`Fetching from: ${url}`);
        
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Failed to load client list: ${response.status} ${response.statusText}`, errorText);
            throw new Error(`Failed to load client list: ${response.status} ${response.statusText}`);
        }
        
        const clients = await response.json();
        console.log(`Received ${clients ? clients.length : 0} clients from API`);
        
        if (!Array.isArray(clients)) {
            console.error('Client list is not an array:', clients);
            throw new Error('Client list is not an array');
        }
        
        if (clients.length === 0) {
            console.warn('No clients returned from API');
        }
        
        // Sort clients by LastName, FirstName
        clientList = clients.sort((a, b) => {
            const aLastName = (a.LastName || '').trim();
            const bLastName = (b.LastName || '').trim();
            const aFirstName = (a.FirstName || '').trim();
            const bFirstName = (b.FirstName || '').trim();
            
            if (aLastName !== bLastName) {
                return aLastName.localeCompare(bLastName);
            }
            return aFirstName.localeCompare(bFirstName);
        });
        
        console.log(`Sorted ${clientList.length} clients`);
        
        // Populate filter dropdown
        const filterSelect = document.getElementById('clientFilter');
        if (filterSelect) {
            console.log('Found clientFilter element, populating dropdown');
            // Clear existing options except "All Clients"
            filterSelect.innerHTML = '<option value="">All Clients</option>';
            
            // Add client options
            clientList.forEach((client, index) => {
                const lastName = (client.LastName || '').trim();
                const firstName = (client.FirstName || '').trim();
                const displayName = lastName && firstName 
                    ? `${lastName}, ${firstName}` 
                    : lastName || firstName || `Client ${client.PersonId}`;
                
                const option = document.createElement('option');
                option.value = client.PersonId;
                option.textContent = `${displayName} (ID: ${client.PersonId})`;
                filterSelect.appendChild(option);
                
                if (index < 3) {
                    console.log(`Added client option: ${displayName} (PersonId: ${client.PersonId}, MainClientServiceId: ${client.MainClientServiceId})`);
                }
            });
            
            console.log(`Populated filter dropdown with ${clientList.length} clients`);
        } else {
            console.error('clientFilter element not found in DOM');
        }
        
    } catch (e) {
        console.error('[loadClientListForFilter] Error loading client list for filter:', {
            error: e,
            message: e.message,
            stack: e.stack,
            site: currentSite,
            url: url
        });
        // Show error in filter dropdown
        const filterSelect = document.getElementById('clientFilter');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">Error loading clients</option>';
        }
        clientList = []; // Reset to empty array on error
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
    
    // Extract client name - 표시 형식: "성, 이름" (LastName, FirstName)
    let clientName = '';
    
    // Helper function to format name as "LastName, FirstName"
    function formatClientNameAsLastNameFirst(obj) {
        const lastName = (obj.LastName || '').trim();
        const firstName = (obj.FirstName || '').trim();
        const title = (obj.Title || '').trim();
        
        if (lastName && firstName) {
            // "LastName, FirstName" 형식
            return title ? `${lastName}, ${title} ${firstName}` : `${lastName}, ${firstName}`;
        } else if (lastName) {
            return lastName;
        } else if (firstName) {
            return firstName;
        }
        return '';
    }
    
    if (clientInfo) {
        clientName = formatClientNameAsLastNameFirst(clientInfo);
    } else if (note.Client) {
        clientName = formatClientNameAsLastNameFirst(note.Client);
    } else if (note.ClientName) {
        // ClientName이 이미 있는 경우, "FirstName LastName" 형식일 수 있으므로 파싱 시도
        const nameParts = note.ClientName.trim().split(/\s+/);
        if (nameParts.length >= 2) {
            // 마지막 부분이 성(LastName), 나머지가 이름(FirstName)으로 가정
            const lastName = nameParts[nameParts.length - 1];
            const firstName = nameParts.slice(0, -1).join(' ');
            clientName = `${lastName}, ${firstName}`;
        } else {
            clientName = note.ClientName;
        }
    } else if (note.Client && note.Client.Name) {
        // Client.Name이 있는 경우도 파싱 시도
        const nameParts = note.Client.Name.trim().split(/\s+/);
        if (nameParts.length >= 2) {
            const lastName = nameParts[nameParts.length - 1];
            const firstName = nameParts.slice(0, -1).join(' ');
            clientName = `${lastName}, ${firstName}`;
        } else {
            clientName = note.Client.Name;
        }
    } else if (note.ClientInfo && note.ClientInfo.Name) {
        const nameParts = note.ClientInfo.Name.trim().split(/\s+/);
        if (nameParts.length >= 2) {
            const lastName = nameParts[nameParts.length - 1];
            const firstName = nameParts.slice(0, -1).join(' ');
            clientName = `${lastName}, ${firstName}`;
        } else {
            clientName = note.ClientInfo.Name;
        }
    } else if (note.ClientInfo && note.ClientInfo.FirstName) {
        clientName = formatClientNameAsLastNameFirst(note.ClientInfo);
    }
    
    // Extract service wing (location) - use WingName (use LocationName if client mapping fails)
    let serviceWing = '';
    if (clientInfo) {
        serviceWing = clientInfo.WingName || clientInfo.LocationName || '';
    } else {
        serviceWing = note.WingName || note.LocationName || (note.Client && note.Client.WingName) || (note.ClientInfo && note.ClientInfo.WingName) || '';
    }
    
    var rawEventType = note.ProgressNoteEventType?.Description || '';
    var eventType = (typeof rawEventType === 'string')
        ? rawEventType.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
        : rawEventType;

    return {
        serviceWing: serviceWing,
        client: clientName,
        date: note.EventDate ? note.EventDate.split('T')[0] : '',
        time: note.EventDate ? (note.EventDate.split('T')[1] || '').slice(0,5) : '',
        eventType: eventType,
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

// Placeholder text for detail panel (never show note content on load — only on row click)
const DETAIL_PLACEHOLDER = 'Select a row to view detailed content here.';

/** Reset detail panel to placeholder and clear row selection. Call on every table render so detail never shows on load. */
function resetDetailPanel() {
    const el = document.getElementById('noteDetailContent');
    if (el) el.innerHTML = DETAIL_PLACEHOLDER;
    document.querySelectorAll('#notesTable tbody tr').forEach(function (tr) { tr.classList.remove('selected'); });
}

// Table rendering
async function renderNotesTable() {
    // Never show detail on load: reset panel first, before any async work
    resetDetailPanel();

    console.log('[renderNotesTable] ========== STARTING TABLE RENDERING ==========');
    console.log('[renderNotesTable] Starting table rendering');
    
    // Check if progressNoteDB is available
    if (typeof window.progressNoteDB === 'undefined') {
        console.error('[renderNotesTable] CRITICAL ERROR: progressNoteDB is not defined!');
        const tbody = document.querySelector('#notesTable tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">Error: progressNoteDB is not available</td></tr>';
        }
        return;
    }
    
    const measure = window.performanceMonitor ? window.performanceMonitor.startMeasure('renderNotesTable') : null;
    const startTime = Date.now();
    
    try {
        await window.progressNoteDB.init();
        
        // Filter mode + server pagination: use current page from last fetch (window.filterModeNotes). No bulk load into IndexedDB.
        // Default mode: use IndexedDB (filled by cached API or full fetch).
        let notes;
        if (isFilterMode() && Array.isArray(window.filterModeNotes)) {
            notes = window.filterModeNotes;
            console.log(`[renderNotesTable] Filter mode: using server page data, ${notes.length} notes`);
        } else {
            const limit = 10000;
            const { notes: idbNotes } = await window.progressNoteDB.getProgressNotes(currentSite, { limit: limit, sortBy: 'eventDate', sortOrder: 'desc' });
            notes = idbNotes || [];
            console.log(`[renderNotesTable] Default mode: ${notes.length} notes from IndexedDB`);
        }
        if (notes && notes.length > 0) {
            console.log(`[renderNotesTable] Sample notes from IndexedDB (first 3):`);
            notes.slice(0, 3).forEach((note, idx) => {
                console.log(`  ${idx + 1}. Id: ${note.Id}, ClientServiceId: ${note.ClientServiceId}, EventDate: ${note.EventDate}`);
            });
        } else {
            console.warn(`[renderNotesTable] No notes retrieved from IndexedDB for site: ${currentSite}`);
        }
        
        logPerformance(`Rendering table with ${notes.length} notes for site: ${currentSite}`, { 
            notesCount: notes.length,
            loadTime: Date.now() - startTime 
        });
        
        // 최신 데이터 로깅 (디버깅용)
        if (notes && notes.length > 0) {
            console.log('[renderNotesTable] Latest 5 notes from IndexedDB:');
            notes.slice(0, 5).forEach((note, index) => {
                console.log(`  ${index + 1}. ID: ${note.Id}, EventDate: ${note.EventDate}, CreatedDate: ${note.CreatedDate || 'N/A'}`);
            });
        } else {
            console.warn('[renderNotesTable] No notes found in IndexedDB');
        }
        
        // 최신 데이터 로깅 (성능 개선을 위해 간소화)
        if (notes && notes.length > 0) {
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
    
        // Filter notes by selected client if filter is active
        // Note: If client filter is active, data should already be filtered from server and saved to IndexedDB
        // Event type filter is server-side; no local filtering needed
        let filteredNotes = notes || [];
        
        console.log(`[renderNotesTable] Filtering notes - selectedClientId: ${selectedClientId}, selectedEventType: ${selectedEventType || 'all'}, notes count: ${notes ? notes.length : 0}`);
        
        // If client filter is active, data from IndexedDB should already be filtered from server
        // No need to filter again - just use all notes from IndexedDB
        // But we add a safety check to log if there's a mismatch
        if (selectedClientId && notes && notes.length > 0) {
            console.log(`[renderNotesTable] Client filter is active (${selectedClientId}), using all notes from IndexedDB (already filtered from server)`);
            
            // Optional: Verify that all notes match the selected client (for debugging)
            const selectedClient = clientList.find(c => c.PersonId === selectedClientId);
            if (selectedClient && selectedClient.MainClientServiceId) {
                const mismatchedNotes = notes.filter(note => {
                    return note && note.ClientServiceId && String(note.ClientServiceId) !== String(selectedClient.MainClientServiceId);
                });
                if (mismatchedNotes.length > 0) {
                    console.warn(`[renderNotesTable] Warning: Found ${mismatchedNotes.length} notes that don't match the selected client's MainClientServiceId`);
                    console.warn(`[renderNotesTable] Expected ClientServiceId: ${selectedClient.MainClientServiceId}`);
                }
            }
        } else if (selectedClientId && (!notes || notes.length === 0)) {
            console.warn(`[renderNotesTable] Client filter is active (${selectedClientId}) but no notes found in IndexedDB`);
        }
    
        // Filter mode = server pagination: one page in window.filterModeNotes, pagination in window.serverPagination.
        // Default mode = cached API: notes from IndexedDB, pagination from window.serverPagination or derived.
        let notesToShow;
        let paginationData;
        if (isFilterMode() && window.serverPagination) {
            notesToShow = filteredNotes;
            paginationData = window.serverPagination;
        } else if (isFilterMode()) {
            const totalCount = filteredNotes.length;
            notesToShow = filteredNotes.slice((currentPage - 1) * perPage, currentPage * perPage);
            paginationData = { page: currentPage, per_page: perPage, total_count: totalCount, total_pages: Math.ceil(totalCount / perPage) };
        } else {
            notesToShow = filteredNotes;
            paginationData = (window.serverPagination && !selectedClientId) ? window.serverPagination : { page: 1, per_page: perPage, total_count: filteredNotes.length, total_pages: Math.ceil(filteredNotes.length / perPage) };
        }
        
        // 전역 변수에 모든 노트 데이터 저장 (필터링용)
        window.allNotes = filteredNotes.map(note => mapNoteToRow(note));
        
        const tbody = document.querySelector('#notesTable tbody');
        if (!tbody) {
            console.error('[renderNotesTable] tbody element not found');
            return;
        }
        
        tbody.innerHTML = '';
        
        if (filteredNotes.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6;
            td.style.textAlign = 'center';
            td.style.padding = '20px';
            td.textContent = selectedClientId ? 'No progress notes found for selected client' : 'No progress notes found';
            tr.appendChild(td);
            tbody.appendChild(tr);
        } else {
            // Batch DOM operations for better performance (render only notesToShow)
            const fragment = document.createDocumentFragment();
            
            notesToShow.forEach((note, idx) => {
                try {
                    const rowData = mapNoteToRow(note);
                    const tr = document.createElement('tr');
                    tr.dataset.idx = idx;
                    Object.values(rowData).forEach(val => {
                        const td = document.createElement('td');
                        td.textContent = val || '';
                        tr.appendChild(td);
                    });
                    tr.addEventListener('click', () => selectNote(idx, notesToShow));
                    fragment.appendChild(tr);
                } catch (error) {
                    console.error('[renderNotesTable] Error mapping note to row:', error, note);
                }
            });
            
            tbody.appendChild(fragment);
        }
        
        // 페이지네이션 UI 강제 표시 (일반 목록 보기에서도)
        if (filteredNotes.length > 0 || (notes && notes.length > 0)) {
            console.log('강제로 페이지네이션 UI 표시 중...');
            if (isFilterMode()) {
                console.log('필터 모드: 클라이언트 페이지네이션', paginationData);
            } else if (window.serverPagination && !selectedClientId) {
                console.log('서버 페이지네이션 정보 사용:', window.serverPagination);
            }
            updatePaginationUI(paginationData);
        }
        
        // Detail panel already reset at start of renderNotesTable(); no row selected until user clicks

        logPerformance('Table rendering completed', { 
            totalTime: Date.now() - startTime,
            rowsRendered: filteredNotes.length 
        });
        
        measure.end();
    } catch (error) {
        console.error('[renderNotesTable] Error rendering table:', error);
        const tbody = document.querySelector('#notesTable tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">Error rendering table: ${error.message}</td></tr>`;
        }
        measure.end();
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

// Update progress notes table with new data
function updateProgressNotesTable(notes) {
    resetDetailPanel();
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

    console.log('Table updated successfully');
}

/**
 * Load one page of progress notes in filter mode (server pagination).
 * Uses /api/fetch-progress-notes with page, per_page; does not bulk-fetch into IndexedDB.
 * Sets window.filterModeNotes and window.serverPagination, then renders.
 */
async function loadFilterModePage(page) {
    const req = {
        site: currentSite,
        days: getPeriodDays(),
        page: page,
        per_page: perPage
    };
    const selectedClient = selectedClientId != null ? clientList.find(c => (c.PersonId === selectedClientId || String(c.PersonId) === String(selectedClientId))) : null;
    if (selectedClient && selectedClient.MainClientServiceId != null) {
        req.client_service_id = selectedClient.MainClientServiceId;
    }
    if (selectedEventType) {
        req.event_types = selectedEventType === EVENT_TYPE_FALL ? ['Fall'] : [selectedEventType];
    }
    try {
        const response = await fetch('/api/fetch-progress-notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req)
        });
        if (!response.ok) throw new Error('HTTP ' + response.status + ': ' + (await response.text()));
        const result = await response.json();
        if (!result.success) throw new Error(result.message || 'Fetch failed');
        const data = (result.data && Array.isArray(result.data)) ? result.data : [];
        const pag = result.pagination || { page: 1, per_page: perPage, total_count: data.length, total_pages: 1 };
        window.filterModeNotes = data;
        window.serverPagination = { page: pag.page, per_page: pag.per_page, total_count: pag.total_count, total_pages: pag.total_pages };
        currentPage = pag.page;
        updatePaginationUI(window.serverPagination);
        await renderNotesTable();
    } catch (e) {
        console.error('[loadFilterModePage]', e);
        window.filterModeNotes = [];
        window.serverPagination = { page: 1, per_page: perPage, total_count: 0, total_pages: 1 };
        const tbody = document.querySelector('#notesTable tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:red;">Error: ' + (e.message || String(e)) + '</td></tr>';
        updatePaginationUI(window.serverPagination);
    }
}

// Event type filter change handler (server filter; refetch)
function handleEventTypeFilterChange() {
    const el = document.getElementById('eventTypeFilter');
    selectedEventType = el ? el.value || '' : '';
    if (isFilterMode()) {
        loadFilterModePage(1);
    } else {
        loadProgressNotes();
    }
}

// Client filter change handler
async function handleClientFilterChange() {
    console.log('[FILTER] ========== CLIENT FILTER CHANGE ==========');
    console.log('[FILTER] Filter change event triggered at:', new Date().toISOString());
    
    // Reset Event type to "All" when Client or Period changes
    selectedEventType = '';
    const eventTypeEl = document.getElementById('eventTypeFilter');
    if (eventTypeEl) eventTypeEl.value = '';
    
    const filterSelect = document.getElementById('clientFilter');
    if (!filterSelect) {
        console.error('[FILTER] clientFilter element not found');
        return;
    }
    
    const previousClientId = selectedClientId;
    selectedClientId = filterSelect.value ? parseInt(filterSelect.value) : null;
    console.log('[FILTER] Previous client ID:', previousClientId);
    console.log('[FILTER] New selected client ID:', selectedClientId);
    console.log('[FILTER] Filter select value:', filterSelect.value);
    
    // Show loading indicator
    const tbody = document.querySelector('#notesTable tbody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">Loading...</td></tr>';
    }
    
    // If a client is selected, fetch data from server
    if (selectedClientId) {
        console.log('[FILTER] Client selected, looking up client in clientList');
        console.log('[FILTER] clientList length:', clientList.length);
        console.log('[FILTER] Searching for PersonId:', selectedClientId);
        
        // Try both numeric and string comparison (PersonId might be string or number)
        let selectedClient = clientList.find(c => c.PersonId === selectedClientId);
        if (!selectedClient) {
            // Try with string comparison
            selectedClient = clientList.find(c => String(c.PersonId) === String(selectedClientId));
        }
        if (!selectedClient) {
            // Try with numeric comparison
            selectedClient = clientList.find(c => parseInt(c.PersonId) === selectedClientId);
        }
        
        console.log('[FILTER] Selected client found:', selectedClient);
        console.log('[FILTER] Selected client type check:', {
            found: !!selectedClient,
            hasMainClientServiceId: selectedClient ? !!selectedClient.MainClientServiceId : false,
            MainClientServiceId: selectedClient ? selectedClient.MainClientServiceId : 'N/A',
            MainClientServiceIdType: selectedClient ? typeof selectedClient.MainClientServiceId : 'N/A'
        });
        
        if (selectedClient) {
            console.log('[FILTER] Client details:', {
                PersonId: selectedClient.PersonId,
                PersonIdType: typeof selectedClient.PersonId,
                FirstName: selectedClient.FirstName,
                LastName: selectedClient.LastName,
                MainClientServiceId: selectedClient.MainClientServiceId,
                MainClientServiceIdType: typeof selectedClient.MainClientServiceId,
                AllKeys: Object.keys(selectedClient)
            });
        } else {
            console.error('[FILTER] Client not found in clientList for PersonId:', selectedClientId);
            console.error('[FILTER] Searching in clientList:', {
                clientListLength: clientList.length,
                selectedClientId: selectedClientId,
                selectedClientIdType: typeof selectedClientId,
                firstFewClients: clientList.slice(0, 5).map(c => ({
                    PersonId: c.PersonId,
                    PersonIdType: typeof c.PersonId,
                    Name: `${c.LastName}, ${c.FirstName}`,
                    MainClientServiceId: c.MainClientServiceId
                }))
            });
        }
        
        // Check if MainClientServiceId exists and is not empty
        const hasValidMainClientServiceId = selectedClient && 
            selectedClient.MainClientServiceId !== null && 
            selectedClient.MainClientServiceId !== undefined && 
            selectedClient.MainClientServiceId !== '';
        
        if (hasValidMainClientServiceId) {
            // Filter mode: server pagination — fetch one page only (no bulk to IndexedDB)
            console.log('[FILTER] Client selected — loading page 1 via server pagination');
            await loadFilterModePage(1);
            return;
        } else {
            console.error('[FILTER] Client not found or missing MainClientServiceId');
            console.error('[FILTER] selectedClient:', selectedClient);
            if (selectedClient) {
                console.error('[FILTER] MainClientServiceId check failed:', {
                    MainClientServiceId: selectedClient.MainClientServiceId,
                    MainClientServiceIdType: typeof selectedClient.MainClientServiceId,
                    isNull: selectedClient.MainClientServiceId === null,
                    isUndefined: selectedClient.MainClientServiceId === undefined,
                    isEmptyString: selectedClient.MainClientServiceId === '',
                    isZero: selectedClient.MainClientServiceId === 0
                });
            }
            if (tbody) {
                const errorMsg = selectedClient 
                    ? `Client found but MainClientServiceId is missing or empty (ID: ${selectedClient.MainClientServiceId})`
                    : 'Client not found in client list';
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">Client information not found: ${errorMsg}</td></tr>`;
            }
            return;
        }
    } else {
        // "All Clients" selected. Cached API only when period === DEFAULT_PERIOD_DAYS; otherwise server-paginated fetch-progress-notes.
        const days = getPeriodDays();
        await window.progressNoteDB.deleteProgressNotes(currentSite);
        if (days === DEFAULT_PERIOD_DAYS) {
            console.log('[FILTER] All clients,', DEFAULT_PERIOD_DAYS, 'days (default) - using cached API');
            window.filterModeNotes = undefined;
            await fetchAndSaveProgressNotes();
        } else {
            console.log('[FILTER] All clients, period', days, 'days - server pagination (one page)');
            await loadFilterModePage(1);
            return;
        }
    }
    
    console.log('[FILTER] Rendering table with filtered data');
    if (isFilterMode()) currentPage = 1;
    await renderNotesTable();
    console.log('[FILTER] Table rendering completed');
}

// Fallback initialization function
let initializationStarted = false;
const startInitialization = async () => {
    if (initializationStarted) {
        console.log('[startInitialization] Initialization already started, skipping');
        return;
    }
    initializationStarted = true;
    
    try {
        console.log('[startInitialization] ========== STARTING INITIALIZATION ==========');
        console.log('[startInitialization] Document ready state:', document.readyState);
        console.log('[startInitialization] Current site:', currentSite);
        
        // Wait for progressNoteDB
        let retries = 0;
        while (typeof window.progressNoteDB === 'undefined' && retries < 20) {
            console.log(`[startInitialization] Waiting for progressNoteDB... (retry ${retries + 1}/20)`);
            await new Promise(resolve => setTimeout(resolve, 100));
            retries++;
        }
        
        if (typeof window.progressNoteDB === 'undefined') {
            console.error('[startInitialization] CRITICAL: progressNoteDB still not available after waiting!');
            console.error('[startInitialization] Available window properties:', Object.keys(window).filter(k => k.includes('progress') || k.includes('Progress')));
            throw new Error('progressNoteDB is not available');
        }
        
        console.log('[startInitialization] progressNoteDB is available, starting initializeForSite');
        await initializeForSite(currentSite);
        console.log('[startInitialization] Initialization completed');
    } catch (error) {
        console.error('[startInitialization] Error:', {
            error: error,
            message: error.message,
            stack: error.stack
        });
        initializationStarted = false; // Allow retry
    }
};

window.addEventListener('DOMContentLoaded', async () => {
    // Mark initialization as started to prevent fallback from running
    if (initializationStarted) {
        console.log('[DOMContentLoaded] Initialization already started, skipping');
        return;
    }
    initializationStarted = true;
    
    try {
        console.log('[DOMContentLoaded] ========== PAGE LOADED ==========');
        console.log('[DOMContentLoaded] Page loaded, starting initialization');
        console.log('[DOMContentLoaded] Current site:', currentSite);
        console.log('[DOMContentLoaded] Checking progressNoteDB availability...');
        
        // Check if progressNoteDB is available
        if (typeof window.progressNoteDB === 'undefined') {
            console.error('[DOMContentLoaded] CRITICAL: window.progressNoteDB is not defined!');
            console.error('[DOMContentLoaded] Available window properties:', Object.keys(window).filter(k => k.includes('progress') || k.includes('Progress')));
            throw new Error('progressNoteDB is not available. Make sure progressNoteDB.js is loaded before progressNoteList.js');
        } else {
            console.log('[DOMContentLoaded] progressNoteDB is available:', typeof window.progressNoteDB);
        }
        
        performanceMetrics.startTime = Date.now();
        logPerformance('Page loaded - starting initialization', { currentSite });
        
        // 사이트 제목 업데이트 (옵셔널 - 요소가 없어도 무시)
        const siteTitle = document.getElementById('siteTitle');
        if (siteTitle) {
            siteTitle.textContent = `Progress Notes - ${currentSite}`;
        }
        
        // Check if table element exists
        const notesTable = document.querySelector('#notesTable');
        if (notesTable) {
            console.log('[DOMContentLoaded] Notes table element found');
        } else {
            console.error('[DOMContentLoaded] CRITICAL: #notesTable element not found!');
        }
        
        // Check if client filter exists
        const clientFilter = document.getElementById('clientFilter');
        if (clientFilter) {
            console.log('[DOMContentLoaded] Client filter element found');
        } else {
            console.warn('[DOMContentLoaded] Client filter element not found (may not be loaded yet)');
        }
        
        // Detect site change and initialize
        console.log('[DOMContentLoaded] Starting site initialization');
        await initializeForSite(currentSite);
        console.log('[DOMContentLoaded] Site initialization completed');
        
        // Add event listener for client filter
        const clientFilterEl = document.getElementById('clientFilter');
        if (clientFilterEl) {
            console.log('[DOMContentLoaded] Adding event listener to clientFilter');
            clientFilterEl.addEventListener('change', handleClientFilterChange);
            console.log('[DOMContentLoaded] Event listener added successfully');
        } else {
            console.error('[DOMContentLoaded] clientFilter element not found when trying to add event listener');
        }
        // Period filter: refetch when changed (max notes = within selected period only)
        const periodFilterEl = document.getElementById('reportingPeriodFilter');
        if (periodFilterEl) {
            periodFilterEl.addEventListener('change', handleClientFilterChange);
        }
        // Event Type filter: server filter; refetch on change
        const eventTypeFilterEl = document.getElementById('eventTypeFilter');
        if (eventTypeFilterEl) {
            eventTypeFilterEl.addEventListener('change', handleEventTypeFilterChange);
        }
        
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
        
        console.log('[DOMContentLoaded] Initialization completed successfully');
        logPerformance('Initialization completed');
    } catch (error) {
        console.error('[DOMContentLoaded] Error during page initialization:', {
            error: error,
            message: error.message,
            stack: error.stack
        });
    }
});

// Fallback: If DOMContentLoaded already fired, start immediately
if (document.readyState !== 'loading') {
    console.log('[progressNoteList.js] DOM already loaded, starting initialization immediately');
    setTimeout(() => {
        console.log('[progressNoteList.js] Calling startInitialization from fallback');
        startInitialization();
    }, 100);
}

// Additional fallback: Start after 1 second if still not started
setTimeout(() => {
    if (!initializationStarted) {
        console.warn('[progressNoteList.js] Initialization not started after 1 second, forcing start');
        startInitialization();
    } else {
        console.log('[progressNoteList.js] Initialization already started, skipping fallback');
    }
}, 1000);


// Site-specific initialization function
async function initializeForSite(site) {
    console.log('[initializeForSite] Starting initialization for site:', site);
    logPerformance(`Initializing for site: ${site}`);
    
    try {
        // Refresh 버튼 비활성화
        console.log('[initializeForSite] Disabling refresh button');
        disableRefreshButton();
        
        // 1. Load client mapping first (differs by site)
        console.log('[initializeForSite] Step 1: Loading client map');
        await loadClientMap();
        console.log('[initializeForSite] Step 1 completed: Client map loaded');
        
        // 1.5. Load client list for filter dropdown
        console.log('[initializeForSite] Step 1.5: Loading client list for filter');
        await loadClientListForFilter();
        console.log('[initializeForSite] Step 1.5 completed: Client list loaded');
        
        // 1.6. Populate period filter from PERIOD_OPTIONS (single source of truth; no hardcoded values in HTML)
        populatePeriodFilter();
        console.log('[initializeForSite] Step 1.6 completed: Period filter populated, default=', DEFAULT_PERIOD_DAYS, 'days');
        
        // 1.7. Populate Event Type filter from /api/event-types (server filter)
        await populateEventTypeFilter();
        console.log('[initializeForSite] Step 1.7 completed: Event type filter populated');
        
        // 2. Initialize IndexedDB
        console.log('[initializeForSite] Step 2: Initializing IndexedDB');
        await window.progressNoteDB.init();
        console.log('[initializeForSite] Step 2 completed: IndexedDB initialized');
        
        // 3. Clear existing data and fetch default-period data (cached)
        console.log('[initializeForSite] Step 3: Clearing existing data and fetching progress notes');
        logPerformance('Clearing existing data and fetching default-period data for site:', { site, days: DEFAULT_PERIOD_DAYS });
        await window.progressNoteDB.deleteProgressNotes(site);
        console.log('[initializeForSite] Step 3.1: Existing data cleared');
        
        // 일반 프로그레스 노트 목록: 모든 노트 가져오기 (성능 최적화를 위해 기본 limit 사용)
        console.log('[initializeForSite] Step 3.2: Fetching all progress notes for general list view');
        console.log('[initializeForSite] About to call fetchAndSaveProgressNotes()');
        try {
            await fetchAndSaveProgressNotes();
            console.log('[initializeForSite] Step 3 completed: Progress notes fetched and saved');
        } catch (fetchError) {
            console.error('[initializeForSite] Error in fetchAndSaveProgressNotes:', {
                error: fetchError,
                message: fetchError.message,
                stack: fetchError.stack
            });
            throw fetchError; // Re-throw to be caught by outer try-catch
        }
        
        // 4. Table rendering
        console.log('[initializeForSite] Step 4: Rendering table');
        await renderNotesTable();
        console.log('[initializeForSite] Step 4 completed: Table rendered');
        
        console.log('[initializeForSite] Initialization completed successfully for site:', site);
        logPerformance('Site initialization completed for:', { site });
    } catch (error) {
        console.error('[initializeForSite] Error during site initialization:', {
            site: site,
            error: error,
            message: error.message,
            stack: error.stack,
            name: error.name
        });
        logPerformance('Site initialization failed:', { site, error: error.message });
        
        // Show error message to user
        const tbody = document.querySelector('#notesTable tbody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">Initialization Error: ${error.message}</td></tr>`;
        }
    } finally {
        enableRefreshButton();
    }
}

// Fetch Progress Notes from server and save (cached, DEFAULT_PERIOD_DAYS only). Use only for first visit or All Clients + default period. Other cases use /api/fetch-progress-notes (no cache).
async function fetchAndSaveProgressNotes(eventTypes = null) {
    try {
        console.log('[fetchAndSaveProgressNotes] Cached fetch -', DEFAULT_PERIOD_DAYS, 'days, no client filter');
        
        const requestBody = {
            site: currentSite,
            days: DEFAULT_PERIOD_DAYS
        };
        
        if (eventTypes && eventTypes.length > 0) {
            requestBody.event_types = eventTypes;
            console.log('[fetchAndSaveProgressNotes] Fetching progress notes with event type filtering:', eventTypes.join(', '));
        } else {
            console.log('[fetchAndSaveProgressNotes] Fetching all progress notes (no event type filtering)');
        }
        
        console.log('[fetchAndSaveProgressNotes] Request body:', JSON.stringify(requestBody, null, 2));
        
        const response = await fetch('/api/fetch-progress-notes-cached', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('[fetchAndSaveProgressNotes] Response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[fetchAndSaveProgressNotes] HTTP error response:', {
                status: response.status,
                statusText: response.statusText,
                errorText: errorText
            });
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('[fetchAndSaveProgressNotes] Response received:', {
            success: result.success,
            count: result.count,
            dataLength: result.data ? result.data.length : 0,
            hasPagination: !!result.pagination
        });
        
        if (result.success) {
            console.log(`[fetchAndSaveProgressNotes] Successfully fetched ${result.count} Progress Notes from server`);
            
            // 서버에서 받은 페이지네이션 정보를 전역 변수에 저장
            if (result.pagination) {
                window.serverPagination = result.pagination;
                console.log('[fetchAndSaveProgressNotes] 서버 페이지네이션 정보 저장:', result.pagination);
            }
            
            // Save to IndexedDB
            if (result.data && result.data.length > 0) {
                console.log('[fetchAndSaveProgressNotes] Saving to IndexedDB...');
                const saveResult = await window.progressNoteDB.saveProgressNotes(currentSite, result.data);
                console.log('[fetchAndSaveProgressNotes] IndexedDB save result:', saveResult);
                
                // Save last update time (use UTC time for API compatibility)
                const utcTime = new Date().toISOString();
                await window.progressNoteDB.saveLastUpdateTime(currentSite, utcTime);
                
                console.log('[fetchAndSaveProgressNotes] Progress Note data saved successfully');
            } else {
                console.warn('[fetchAndSaveProgressNotes] No progress notes found in response');
            }
        } else {
            console.error('[fetchAndSaveProgressNotes] API returned success=false:', result);
            throw new Error(result.message || 'Failed to fetch Progress Notes');
        }
    } catch (error) {
        console.error('[fetchAndSaveProgressNotes] Failed to fetch Progress Notes:', {
            error: error,
            message: error.message,
            stack: error.stack,
            site: currentSite
        });
        
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
            console.error('[fetchAndSaveProgressNotes] Failed to log error to server:', logError);
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

// 수동 새로고침 함수 — respects current filters (client, period, event type)
async function refreshData() {
    try {
        console.log('Manual refresh requested for site:', currentSite);
        disableRefreshButton();
        if (isFilterMode()) {
            await loadFilterModePage(1);
        } else {
            await window.progressNoteDB.deleteProgressNotes(currentSite);
            console.log('Fetching all progress notes for general list view');
            await fetchAndSaveProgressNotes();
            await renderNotesTable();
        }
    } catch (error) {
        console.error('Refresh failed for site:', currentSite, error);
    } finally {
        enableRefreshButton();
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
        selectedClientId = null;
        selectedEventType = '';
        const clientFilterEl = document.getElementById('clientFilter');
        if (clientFilterEl) clientFilterEl.value = '';
        const eventTypeEl = document.getElementById('eventTypeFilter');
        if (eventTypeEl) eventTypeEl.value = '';
        
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
    console.log('Incremental update is disabled. Fetching default-period (' + DEFAULT_PERIOD_DAYS + ' days) data instead.');
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
    const firstBtn = document.getElementById('firstPageBtn');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const lastBtn = document.getElementById('lastPageBtn');
    const pageNumbers = document.getElementById('pageNumbers');
    
    console.log('Pagination elements found:', {
        container: !!container,
        info: !!info,
        firstBtn: !!firstBtn,
        prevBtn: !!prevBtn,
        nextBtn: !!nextBtn,
        lastBtn: !!lastBtn,
        pageNumbers: !!pageNumbers
    });
    
    if (!container || !info || !prevBtn || !nextBtn || !pageNumbers) {
        console.error('페이지네이션 UI 요소를 찾을 수 없습니다.');
        return;
    }
    
    // Update page information
    const startItem = totalCount === 0 ? 0 : (currentPage - 1) * perPage + 1;
    const endItem = Math.min(currentPage * perPage, totalCount);
    info.textContent = `Showing ${startItem}-${endItem} of ${totalCount} items (Page ${currentPage}/${totalPages})`;
    
    // First/Last: show only when more than one page
    const showFirstLast = totalPages > 1;
    if (firstBtn) {
        firstBtn.style.display = showFirstLast ? '' : 'none';
        firstBtn.disabled = currentPage <= 1;
        firstBtn.onclick = () => goToPage(1);
    }
    if (lastBtn) {
        lastBtn.style.display = showFirstLast ? '' : 'none';
        lastBtn.disabled = currentPage >= totalPages;
        lastBtn.onclick = () => goToPage(totalPages);
    }
    
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
    
    if (page === currentPage && !isFilterMode()) {
        console.log(`Same page: ${page} - no action needed`);
        return;
    }
    
    console.log(`Changing to page: ${page}`);
    currentPage = page;
    if (isFilterMode()) {
        loadFilterModePage(page);
        return;
    }
    loadProgressNotes();
}

function changePerPage() {
    const select = document.getElementById('perPageSelect');
    perPage = parseInt(select.value);
    currentPage = 1;
    if (isFilterMode()) {
        loadFilterModePage(1);
        return;
    }
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
            days: DEFAULT_PERIOD_DAYS,
            page: currentPage,
            per_page: perPage,
            force_refresh: forceRefresh
        };
        
        console.log(`Loading progress notes (cached ${DEFAULT_PERIOD_DAYS}-day) - Page: ${currentPage}, Per Page: ${perPage}, Force Refresh: ${forceRefresh}`);
        
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
            updateProgressNotesTable(result.data);
            
            // 페이지네이션 UI 업데이트
            console.log('Pagination data:', result.pagination);
            if (result.pagination) {
                console.log('Updating pagination UI...', result.pagination);
                updatePaginationUI(result.pagination);
            } else {
                console.log('No pagination data received - creating default pagination');
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