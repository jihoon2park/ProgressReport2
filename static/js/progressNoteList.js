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
        
        // MainClientServiceId â†’ clientInfo mapping (unified with string keys)
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

// Field mapping (API data â†’ table column)
function mapNoteToRow(note) {
    // Convert to string for mapping (resolve type mismatch)
    const clientServiceIdStr = String(note.ClientServiceId);
    let clientInfo = clientMap[clientServiceIdStr];
    
    // Extract client name - í‘œì‹œ í˜•ì‹: "ì„±, ì´ë¦„" (LastName, FirstName)
    let clientName = '';
    
    // Helper function to format name as "LastName, FirstName"
    function formatClientNameAsLastNameFirst(obj) {
        const lastName = (obj.LastName || '').trim();
        const firstName = (obj.FirstName || '').trim();
        const title = (obj.Title || '').trim();
        
        if (lastName && firstName) {
            // "LastName, FirstName" í˜•ì‹
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
        // ClientNameì´ ì´ë¯¸ ìžˆëŠ” ê²½ìš°, "FirstName LastName" í˜•ì‹ì¼ ìˆ˜ ìžˆìœ¼ë¯€ë¡œ íŒŒì‹± ì‹œë„
        const nameParts = note.ClientName.trim().split(/\s+/);
        if (nameParts.length >= 2) {
            // ë§ˆì§€ë§‰ ë¶€ë¶„ì´ ì„±(LastName), ë‚˜ë¨¸ì§€ê°€ ì´ë¦„(FirstName)ìœ¼ë¡œ ê°€ì •
            const lastName = nameParts[nameParts.length - 1];
            const firstName = nameParts.slice(0, -1).join(' ');
            clientName = `${lastName}, ${firstName}`;
        } else {
            clientName = note.ClientName;
        }
    } else if (note.Client && note.Client.Name) {
        // Client.Nameì´ ìžˆëŠ” ê²½ìš°ë„ íŒŒì‹± ì‹œë„
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
    // HTML ë…¸íŠ¸ ë‚´ìš©ì„ ì•ˆì „í•˜ê²Œ ì²˜ë¦¬
    let safeHtmlNotes = '';
    if (note.HtmlNotes) {
        // style íƒœê·¸ì™€ body íƒœê·¸ë¥¼ ì œê±°í•˜ì—¬ íŽ˜ì´ì§€ CSSì— ì˜í–¥ì„ ì£¼ì§€ ì•Šë„ë¡ í•¨
        safeHtmlNotes = note.HtmlNotes
            .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '') // style íƒœê·¸ ì œê±°
            .replace(/<body[^>]*>/gi, '<div class="note-content">') // body íƒœê·¸ë¥¼ divë¡œ ë³€ê²½
            .replace(/<\/body>/gi, '</div>') // body ë‹«ëŠ” íƒœê·¸ë¥¼ divë¡œ ë³€ê²½
            .replace(/<html[^>]*>/gi, '') // html íƒœê·¸ ì œê±°
            .replace(/<\/html>/gi, '') // html ë‹«ëŠ” íƒœê·¸ ì œê±°
            .replace(/<head[^>]*>[\s\S]*?<\/head>/gi, ''); // head íƒœê·¸ì™€ ë‚´ìš© ì œê±°
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

/** Reset detail panel — close slide panel and clear row selection. Call on every table render. */
function resetDetailPanel() {
    closeDetailPanel();
    document.querySelectorAll('#notesTable tbody tr').forEach(function (tr) { tr.classList.remove('selected'); });
}

// â”€â”€ Render notes array into the table (pure render, no fetching) â”€â”€
function renderNotes(notes, pagination) {
    resetDetailPanel();
    var tbody = document.querySelector('#notesTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    window.currentPageNotes = notes; // keep reference for selectNote
    window.allNotes = notes.map(function(n){ return mapNoteToRow(n); });

    if (!notes || notes.length === 0) {
        var tr = document.createElement('tr');
        var td = document.createElement('td');
        td.colSpan = 6; td.style.textAlign = 'center'; td.style.padding = '20px';
        td.textContent = selectedClientId ? 'No progress notes found for selected client' : 'No progress notes found';
        tr.appendChild(td); tbody.appendChild(tr);
    } else {
        var fragment = document.createDocumentFragment();
        notes.forEach(function(note, idx) {
            var rowData = mapNoteToRow(note);
            var tr = document.createElement('tr');
            tr.dataset.idx = idx;
            Object.values(rowData).forEach(function(val) {
                var td = document.createElement('td');
                td.textContent = val || '';
                tr.appendChild(td);
            });
            tr.addEventListener('click', function() { selectNote(idx, notes); });
            fragment.appendChild(tr);
        });
        tbody.appendChild(fragment);
    }

    if (pagination) {
        updatePaginationUI(pagination);
    }
}

// Track which client is shown in the detail panel (for Client Details button)
var detailPanelClientId = null;

// Show details when row is selected — opens slide-from-right panel
function selectNote(idx, notes) {
    // Row highlight
    document.querySelectorAll('#notesTable tbody tr').forEach((tr, i) => {
        tr.classList.toggle('selected', i === idx);
    });
    var note = notes[idx];
    if (!note) return;

    // Populate detail panel meta
    var clientName = '';
    var clientInfo = clientMap[note.ClientId] || clientMap[note.ClientServiceId];
    if (clientInfo) {
        var first = (clientInfo.FirstName || '').trim();
        var last = (clientInfo.LastName || clientInfo.Surname || '').trim();
        clientName = last && first ? last + ', ' + first : (last || first || 'Unknown');
    } else {
        clientName = note.ClientId || '';
    }

    var metaEl = document.getElementById('detailMeta');
    if (metaEl) {
        metaEl.innerHTML = ''
            + '<div class="detail-meta-item"><span class="detail-meta-label">Client</span><span class="detail-meta-value">' + escHtml(clientName) + '</span></div>'
            + '<div class="detail-meta-item"><span class="detail-meta-label">Date / Time</span><span class="detail-meta-value">' + escHtml(note.EventDate ? note.EventDate.replace('T', ' ').slice(0, 16) : '') + '</span></div>'
            + '<div class="detail-meta-item"><span class="detail-meta-label">Event Type</span><span class="detail-meta-value">' + escHtml(note.ProgressNoteEventType?.Description || '') + '</span></div>'
            + '<div class="detail-meta-item"><span class="detail-meta-label">Care Area(s)</span><span class="detail-meta-value">' + escHtml((note.CareAreas || []).map(function(ca){return ca.Description;}).join(', ')) + '</span></div>';
    }

    // Populate notes content
    var notesEl = document.getElementById('detailNotes');
    if (notesEl) {
        var safeHtml = '';
        if (note.HtmlNotes) {
            safeHtml = note.HtmlNotes
                .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
                .replace(/<body[^>]*>/gi, '<div>')
                .replace(/<\/body>/gi, '</div>')
                .replace(/<html[^>]*>/gi, '').replace(/<\/html>/gi, '')
                .replace(/<head[^>]*>[\s\S]*?<\/head>/gi, '');
        }
        notesEl.innerHTML = safeHtml || (note.NotesPlainText || note.Notes || '<span style="color:#aaa">No notes</span>');
    }

    var titleEl = document.getElementById('detailPanelTitle');
    if (titleEl) titleEl.textContent = clientName ? clientName + ' — Note Details' : 'Note Details';

    // Store client ID and show/hide Client Details button in panel
    detailPanelClientId = note.ClientId || note.ClientServiceId || null;
    var panelClientBtn = document.getElementById('detailPanelClientBtn');
    if (panelClientBtn) {
        panelClientBtn.style.display = detailPanelClientId ? 'inline-block' : 'none';
    }

    openDetailPanel();
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

// Unified: fetch one page of progress notes from /api/fetch-progress-notes with current filters and render.
async function loadProgressNotes(page) {
    if (page == null) page = currentPage || 1;
    var req = {
        site: currentSite,
        days: getPeriodDays(),
        page: page,
        per_page: perPage
    };
    // Add client filter
    if (selectedClientId) {
        var selectedClient = clientList.find(function(c) {
            return String(c.PersonId) === String(selectedClientId);
        });
        if (selectedClient && selectedClient.MainClientServiceId != null) {
            req.client_service_id = selectedClient.MainClientServiceId;
        }
    }
    // Add event type filter
    if (selectedEventType) {
        req.event_types = selectedEventType === EVENT_TYPE_FALL ? ['Fall'] : [selectedEventType];
    }
    // Show loading
    var tbody = document.querySelector('#notesTable tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">Loading...</td></tr>';

    try {
        var response = await fetch('/api/fetch-progress-notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(req)
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        var result = await response.json();
        if (!result.success) throw new Error(result.message || 'Fetch failed');
        var data = (result.data && Array.isArray(result.data)) ? result.data : [];
        var pag = result.pagination || { page: page, per_page: perPage, total_count: data.length, total_pages: 1 };
        window.serverPagination = { page: pag.page, per_page: pag.per_page, total_count: pag.total_count, total_pages: pag.total_pages };
        currentPage = pag.page;
        renderNotes(data, window.serverPagination);
    } catch (e) {
        console.error('[loadProgressNotes] Error:', e);
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:red;">Error: ' + (e.message || String(e)) + '</td></tr>';
    }
}

// Keep old name as alias so any stale references still work
var loadFilterModePage = loadProgressNotes;

// Event type filter change handler
function handleEventTypeFilterChange() {
    var el = document.getElementById('eventTypeFilter');
    selectedEventType = el ? el.value || '' : '';
    currentPage = 1;
    loadProgressNotes(1);
}

// Client filter change handler
async function handleClientFilterChange() {
    // Reset event type when client/period changes
    selectedEventType = '';
    var eventTypeEl = document.getElementById('eventTypeFilter');
    if (eventTypeEl) eventTypeEl.value = '';

    var filterSelect = document.getElementById('clientFilter');
    if (!filterSelect) return;

    selectedClientId = filterSelect.value ? parseInt(filterSelect.value) : null;

    if (selectedClientId) {
        showClientProfile(selectedClientId);
    } else {
        hideClientProfile();
    }

    currentPage = 1;
    await loadProgressNotes(1);
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
        
        // ì‚¬ì´íŠ¸ ì œëª© ì—…ë°ì´íŠ¸ (ì˜µì…”ë„ - ìš”ì†Œê°€ ì—†ì–´ë„ ë¬´ì‹œ)
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
        
        // 2. Fetch and render page 1 via unified loadProgressNotes
        console.log('[initializeForSite] Step 2: Fetching page 1 of progress notes');
        currentPage = 1;
        await loadProgressNotes(1);
        console.log('[initializeForSite] Step 2 completed: Page 1 loaded and rendered');
        
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


// ì—ëŸ¬ ë©”ì‹œì§€ í‘œì‹œ í•¨ìˆ˜
function showErrorMessage(message) {
    // ê¸°ì¡´ ì—ëŸ¬ ë©”ì‹œì§€ ì œê±°
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // ìƒˆ ì—ëŸ¬ ë©”ì‹œì§€ ìƒì„±
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
        <strong>ì˜¤ë¥˜ ë°œìƒ</strong><br>
        ${message}<br>
        <small>ìžë™ìœ¼ë¡œ ì‚¬ë¼ì§‘ë‹ˆë‹¤</small>
    `;
    
    document.body.appendChild(errorDiv);
    
    // 10ì´ˆ í›„ ìžë™ ì œê±°
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 10000);
}

// ìˆ˜ë™ ìƒˆë¡œê³ ì¹¨ í•¨ìˆ˜ — respects current filters (client, period, event type)
async function refreshData() {
    try {
        disableRefreshButton();
        await loadProgressNotes(1);
    } catch (error) {
        console.error('Refresh failed:', error);
    } finally {
        enableRefreshButton();
    }
}

// ì „ì—­ í•¨ìˆ˜ë¡œ ë…¸ì¶œ (í…ŒìŠ¤íŠ¸ìš©)
window.testIncrementalUpdate = () => {
    console.log('Incremental update is disabled. Use refreshData() instead.');
};

// ì‚¬ì´íŠ¸ ë³€ê²½ ì‹œ í˜¸ì¶œí•  í•¨ìˆ˜ (URL íŒŒë¼ë¯¸í„° ë³€ê²½ ì‹œ)
function handleSiteChange() {
    const urlParams = new URLSearchParams(window.location.search);
    const newSite = urlParams.get('site') || 'Ramsay';
    
    if (newSite !== currentSite) {
        logPerformance('Site changed from', { from: currentSite, to: newSite });
        currentSite = newSite;
        selectedClientId = null;
        selectedEventType = '';
        hideClientProfile();
        const clientFilterEl = document.getElementById('clientFilter');
        if (clientFilterEl) clientFilterEl.value = '';
        const eventTypeEl = document.getElementById('eventTypeFilter');
        if (eventTypeEl) eventTypeEl.value = '';
        
        // Update site title
        const siteTitle = document.getElementById('siteTitle');
        if (siteTitle) {
            siteTitle.textContent = `Progress Notes - ${currentSite}`;
        }
        
        // ìƒˆë¡œìš´ ì‚¬ì´íŠ¸ë¡œ ì´ˆê¸°í™”
        initializeForSite(currentSite);
    }
}


// Performance debugging tools (available in console)
window.debugPerformance = {
    // í˜„ìž¬ ì„±ëŠ¥ ìƒíƒœ ì¶œë ¥
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
    
    // ê°•ì œ ì •ë¦¬
    cleanup: () => {
        cleanup();
        console.log('Forced cleanup completed');
    },
    
    // ë©”ëª¨ë¦¬ ì‚¬ìš©ëŸ‰ ëª¨ë‹ˆí„°ë§ ì‹œìž‘
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
                
                // ë©”ëª¨ë¦¬ ì‚¬ìš©ëŸ‰ì´ 80%ë¥¼ ë„˜ìœ¼ë©´ ê²½ê³ 
                if (used / limit > 0.8) {
                    console.warn('âš ï¸ High memory usage detected!');
                }
            }
        }, 5000); // 5ì´ˆë§ˆë‹¤ ì²´í¬
        
        console.log('Memory monitoring started');
    },
    
    // ë©”ëª¨ë¦¬ ëª¨ë‹ˆí„°ë§ ì¤‘ì§€
    stopMemoryMonitoring: () => {
        if (window.debugPerformance.memoryInterval) {
            clearInterval(window.debugPerformance.memoryInterval);
            window.debugPerformance.memoryInterval = null;
            console.log('Memory monitoring stopped');
        }
    },
    
    // ê°€ë¹„ì§€ ì»¬ë ‰ì…˜ ê°•ì œ ì‹¤í–‰ (ê°€ëŠ¥í•œ ê²½ìš°)
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
    // DevToolsê°€ ì—´ë ¤ìžˆì„ ë•Œë§Œ ì‹¤í–‰
    window.addEventListener('devtoolschange', (e) => {
        if (e.detail.open) {
            console.log('DevTools opened - enabling detailed performance monitoring');
            logPerformance('DevTools opened');
        }
    });
}

// Performance monitoring for Chrome DevTools
window.performanceMonitor = {
    // ì„±ëŠ¥ ë§ˆì»¤ ì¶”ê°€
    mark: (name) => {
        if (performance.mark) {
            performance.mark(name);
        }
        logPerformance(`Mark: ${name}`);
    },
    
    // ì„±ëŠ¥ ì¸¡ì •
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
    
    // ì„±ëŠ¥ ì¸¡ì • ì‹œìž‘
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

// íŽ˜ì´ì§€ë„¤ì´ì…˜ ê´€ë ¨ ì „ì—­ ë³€ìˆ˜
let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let perPage = 50;
let currentPaginationData = null;

// íŽ˜ì´ì§€ë„¤ì´ì…˜ ê¸°ëŠ¥
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
        console.error('íŽ˜ì´ì§€ë„¤ì´ì…˜ UI ìš”ì†Œë¥¼ ì°¾ì„ ìˆ˜ ì—†ìŠµë‹ˆë‹¤.');
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
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    loadProgressNotes(page);
}

function changePerPage() {
    var select = document.getElementById('perPageSelect');
    perPage = parseInt(select.value);
    currentPage = 1;
    loadProgressNotes(1);
}


// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// â”€â”€ CLIENT PROFILE (resident detail, wounds, tabs) â”€â”€
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

var residentCache = {};
var woundsCache = [];
var activeProfileTab = 'overview';

function escHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDateShort(iso) {
    if (!iso) return '\u2014';
    try {
        var d = new Date(iso);
        return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch (e) { return String(iso); }
}

function openDetailPanel() {
    var overlay = document.getElementById('detailOverlay');
    var panel = document.getElementById('detailPanel');
    if (overlay) overlay.classList.add('open');
    if (panel) panel.classList.add('open');
}

function closeDetailPanel() {
    var overlay = document.getElementById('detailOverlay');
    var panel = document.getElementById('detailPanel');
    if (overlay) overlay.classList.remove('open');
    if (panel) panel.classList.remove('open');
}

// Show "Client Details" button when a client is selected
function showClientProfile(clientId) {
    var btn = document.getElementById('btnClientDetails');
    if (btn) btn.classList.add('visible');
    // Pre-fetch resident data so modal opens fast
    var client = clientList.find(function (c) { return String(c.PersonId) === String(clientId); });
    if (client) {
        var cid = client.Id || client.PersonId;
        fetchResidentDetail(cid);
    }
}

// Open client details modal from the detail panel (for All Clients mode)
function openClientDetailsFromPanel() {
    if (!detailPanelClientId) return;
    // Find client in clientList by PersonId or MainClientServiceId
    var client = clientList.find(function(c) {
        return String(c.PersonId) === String(detailPanelClientId) ||
               String(c.MainClientServiceId) === String(detailPanelClientId);
    });
    if (!client) {
        // Try clientMap
        client = clientMap[detailPanelClientId];
    }
    if (!client) { alert('Client details not available'); return; }

    // Temporarily set selectedClientId so openClientDetailsModal works
    var prevSelected = selectedClientId;
    selectedClientId = client.PersonId;
    openClientDetailsModal();
    selectedClientId = prevSelected;
}

// Hide "Client Details" button
function hideClientProfile() {
    var btn = document.getElementById('btnClientDetails');
    if (btn) btn.classList.remove('visible');
    residentCache = {};
    woundsCache = [];
}

// Open client details modal
function openClientDetailsModal() {
    if (!selectedClientId) return;
    var client = clientList.find(function (c) { return String(c.PersonId) === String(selectedClientId); });
    if (!client) return;

    var last = (client.LastName || '').trim();
    var first = (client.FirstName || '').trim();
    var name = last && first ? last + ', ' + first : (last || first || 'Unknown');
    var initials = ((first || '?')[0] + (last || '?')[0]).toUpperCase();

    var avatarEl = document.getElementById('clientAvatar');
    var nameEl = document.getElementById('clientModalName');
    var subtitleEl = document.getElementById('clientModalSubtitle');
    if (avatarEl) avatarEl.textContent = initials;
    if (nameEl) nameEl.textContent = name;
    if (subtitleEl) subtitleEl.textContent = (client.WingName || '') + (client.WingName && client.LocationName ? ' · ' : '') + (client.LocationName || '');

    activeProfileTab = 'overview';
    updateProfileTabUI();

    // If data already fetched, render immediately; otherwise show loading
    if (residentCache && residentCache.person) {
        renderProfileTab('overview');
    } else {
        var content = document.getElementById('profileContent');
        if (content) content.innerHTML = '<div class="client-profile-loading">Loading resident data...</div>';
        var cid = client.Id || client.PersonId;
        fetchResidentDetail(cid);
    }

    var overlay = document.getElementById('clientModalOverlay');
    if (overlay) overlay.classList.add('open');
}

// Close client details modal
function closeClientDetailsModal() {
    var overlay = document.getElementById('clientModalOverlay');
    if (overlay) overlay.classList.remove('open');
}

function infoItem(label, value) {
    return '<div class="info-item"><span class="info-label">' + escHtml(label) + '</span><span class="info-value">' + escHtml(value || '—') + '</span></div>';
}

async function fetchResidentDetail(clientId) {
    try {
        var resp = await fetch('/api/residents/' + clientId + '?site=' + encodeURIComponent(currentSite));
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var json = await resp.json();
        if (!json.success) throw new Error(json.message || 'Failed');
        residentCache = json.data || {};

        // Also fetch wounds
        try {
            var wResp = await fetch('/api/wounds?site=' + encodeURIComponent(currentSite));
            if (wResp.ok) {
                var wJson = await wResp.json();
                if (wJson.success) {
                    woundsCache = (wJson.data || []).filter(function (w) {
                        return w.ClientId === clientId;
                    });
                }
            }
        } catch (e) {
            console.warn('[ClientProfile] Wounds fetch failed:', e.message);
            woundsCache = [];
        }

        renderProfileTab(activeProfileTab);
    } catch (e) {
        console.error('[ClientProfile] Resident detail error:', e.message);
        var content = document.getElementById('profileContent');
        if (content) content.innerHTML = '<div class="empty-tab">Could not load resident data: ' + escHtml(e.message) + '</div>';
    }
}

function switchProfileTab(tabId) {
    activeProfileTab = tabId;
    updateProfileTabUI();
    renderProfileTab(tabId);
}

function updateProfileTabUI() {
    document.querySelectorAll('.profile-tab').forEach(function (btn) {
        btn.classList.toggle('active', btn.dataset.tab === activeProfileTab);
    });
}

function renderProfileTab(tabId) {
    var content = document.getElementById('profileContent');
    if (!content) return;

    if (!residentCache || !residentCache.person) {
        content.innerHTML = '<div class="client-profile-loading">Loading...</div>';
        return;
    }

    var person = residentCache.person || {};
    var cs = residentCache.client_service || {};
    var contacts = residentCache.emergency_contacts || [];
    var tables = residentCache.tables || {};

    switch (tabId) {
        case 'overview':
            content.innerHTML = renderOverviewTab(person, cs, contacts);
            break;
        case 'clinical':
            content.innerHTML = renderClinicalTab(tables);
            break;
        case 'wounds':
            content.innerHTML = renderWoundsTab(tables);
            break;
        case 'monitoring':
            content.innerHTML = renderMonitoringTab(tables);
            break;
        default:
            content.innerHTML = '<div class="empty-tab">Unknown tab</div>';
    }
}

function renderOverviewTab(person, cs, contacts) {
    var html = '<div class="section-card"><div class="section-card-header">Personal & Location</div><div class="section-card-body"><div class="info-grid">';
    var pref = (person.PreferredName || '').trim();
    var fullName = ((person.FirstName || '') + ' ' + (person.LastName || '')).trim();
    html += infoItem('Name', pref || fullName || '—');
    html += infoItem('Birth Date', formatDateShort(person.BirthDate));
    html += infoItem('Height', person.Height ? person.Height + ' cm' : '—');
    html += infoItem('Wing', cs.WingName || '—');
    html += infoItem('Location', cs.LocationName || '—');
    html += infoItem('Admission', formatDateShort(cs.StartDate));
    html += '</div></div></div>';

    html += '<div class="section-card"><div class="section-card-header">Emergency Contacts</div><div class="section-card-body">';
    if (contacts.length === 0) {
        html += '<div class="empty-tab">No emergency contacts</div>';
    } else {
        contacts.forEach(function (c) {
            html += '<div class="contact-block">';
            html += '<div class="contact-name">' + escHtml(c.ContactName || 'Contact') + '</div>';
            if (c.Relationship) html += '<div class="contact-detail">Relationship: ' + escHtml(c.Relationship) + '</div>';
            if (c.MobilePhone) html += '<div class="contact-detail">Mobile: ' + escHtml(c.MobilePhone) + '</div>';
            if (c.BusinessHoursPhone) html += '<div class="contact-detail">Business: ' + escHtml(c.BusinessHoursPhone) + '</div>';
            if (c.AfterHoursPhone) html += '<div class="contact-detail">After Hours: ' + escHtml(c.AfterHoursPhone) + '</div>';
            if (c.Email) html += '<div class="contact-detail">Email: ' + escHtml(c.Email) + '</div>';
            html += '</div>';
        });
    }
    html += '</div></div>';
    return html;
}

function renderClinicalTab(tables) {
    var html = '';
    var adverseEvents = tables.AdverseEvent || [];
    var diagnosis = tables.ClientDiagnosis || [];

    if (adverseEvents.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Adverse Events</div><div class="section-card-body">';
        adverseEvents.forEach(function (ev) {
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(ev.Date)) + '</span><span class="data-row-text">' + escHtml(ev.Description || '—') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (diagnosis.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Diagnosis</div><div class="section-card-body">';
        diagnosis.forEach(function (d) {
            html += '<div class="data-row"><span class="data-row-text">' + escHtml(d.Description || d.Id || '—') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (!html) html = '<div class="empty-tab">No clinical data available</div>';
    return html;
}

function renderWoundsTab(tables) {
    var html = '';
    var wounds = tables.Wound || woundsCache || [];
    var followUps = tables.WoundFollowUp || [];

    if (wounds.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Active Wounds</div><div class="section-card-body">';
        wounds.forEach(function (w) {
            var desc = w.LocationNotes || w.Ma4WoundLocation || '—';
            var type = '';
            if (w.WoundType && w.WoundType.Description) type = w.WoundType.Description;
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(w.Date)) + '</span><span class="data-row-text">' + escHtml(desc) + (type ? ' <span style="color:#aaa">(' + escHtml(type) + ')</span>' : '') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (followUps.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Wound Follow-ups</div><div class="section-card-body">';
        followUps.forEach(function (w) {
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(w.Date)) + '</span><span class="data-row-text">' + escHtml(w.LocationNotes || '—') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (!html) html = '<div class="empty-tab">No wound data available</div>';
    return html;
}

function renderMonitoringTab(tables) {
    var html = '';
    var weight = tables.Weight || [];
    var pain = tables.Pain || [];
    var bowel = tables.BowelMonitoring || [];

    if (weight.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Weight</div><div class="section-card-body">';
        weight.forEach(function (w) {
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(w.Date)) + '</span><span class="data-row-text">' + escHtml(w.Value != null ? w.Value + ' kg' : '—') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (pain.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Pain</div><div class="section-card-body">';
        pain.forEach(function (p) {
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(p.Date)) + '</span><span class="data-row-text">' + escHtml(p.LocationNotes || '—') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (bowel.length > 0) {
        html += '<div class="section-card"><div class="section-card-header">Bowel Monitoring</div><div class="section-card-body">';
        bowel.forEach(function (b) {
            html += '<div class="data-row"><span class="data-row-date">' + escHtml(formatDateShort(b.Date)) + '</span><span class="data-row-text">Bowel open: ' + (b.IsBowelOpen ? 'Yes' : 'No') + '</span></div>';
        });
        html += '</div></div>';
    }

    if (!html) html = '<div class="empty-tab">No monitoring data available</div>';
    return html;
}
