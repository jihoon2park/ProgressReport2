// Progress Note list page JS (dynamic site support)

// Use global progressNoteDB instance (without variable declaration)

// Current site setting (received from server or URL parameter or default value)
const currentSite = window.currentSite || new URLSearchParams(window.location.search).get('site') || 'Ramsay';

// 전역 클라이언트 매핑 객체
let clientMap = {};



// Client mapping test function
function testClientMapping() {
    console.log('=== Client Mapping Test ===');
    console.log('clientMap key count:', Object.keys(clientMap).length);
    
    // Check example keys
    const sampleKeys = Object.keys(clientMap).slice(0, 5);
    console.log('Sample keys:', sampleKeys);
    
    // Check type of each key
    sampleKeys.forEach(key => {
        console.log(`Key: "${key}" (type: ${typeof key})`);
        console.log(`Mapped data:`, clientMap[key]);
    });
    
    // Match test with actual Progress Note's ClientServiceId
    if (window._testNoteClientServiceId) {
        const testId = window._testNoteClientServiceId;
        const stringId = String(testId);
        console.log(`Test ID: ${testId} (type: ${typeof testId})`);
        console.log(`String conversion: "${stringId}" (type: ${typeof stringId})`);
        console.log(`Mapping result:`, clientMap[stringId]);
    }
}

// Load client information
async function loadClientMap() {
    try {
        console.log('Loading client file...');
        const response = await fetch(`/data/${currentSite.toLowerCase().replace(' ', '_')}_client.json`);
        console.log('Client file response status:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`Failed to load client information: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Client data loaded successfully. Data type:', typeof data);
        console.log('Data structure:', Array.isArray(data) ? 'Array' : 'Object');
        console.log('Data keys:', Object.keys(data));
        
        // MainClientServiceId → clientInfo mapping (unified with string keys)
        clientMap = {};
        
        if (Array.isArray(data)) {
            console.log('Processing as array. Length:', data.length);
            data.forEach((client, index) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
                if (index < 3) {
                    console.log(`Client ${index}:`, client.MainClientServiceId, typeof client.MainClientServiceId);
                }
            });
        } else if (data.Clients && Array.isArray(data.Clients)) {
            console.log('Processing as Clients array. Length:', data.Clients.length);
            data.Clients.forEach((client, index) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
                if (index < 3) {
                    console.log(`Client ${index}:`, client.MainClientServiceId, typeof client.MainClientServiceId);
                }
            });
        } else if (data.client_info && Array.isArray(data.client_info)) {
            console.log('Processing as client_info array. Length:', data.client_info.length);
            data.client_info.forEach((client, index) => {
                if (client.MainClientServiceId) {
                    // Convert to string to use as key
                    clientMap[String(client.MainClientServiceId)] = client;
                }
                if (index < 3) {
                    console.log(`Client ${index}:`, client.MainClientServiceId, typeof client.MainClientServiceId);
                }
            });
        } else {
            console.log('Unknown data structure:', data);
            console.log('Available keys:', Object.keys(data));
        }
        
        // Check mapping results
        console.log('Client mapping completed. Total key count:', Object.keys(clientMap).length);
        if (Object.keys(clientMap).length > 0) {
            const sampleKeys = Object.keys(clientMap).slice(0, 5);
            console.log('Sample keys:', sampleKeys);
            sampleKeys.forEach(key => {
                const client = clientMap[key];
                console.log(`Key ${key}: ${client.FirstName} ${client.LastName} (${client.WingName})`);
            });
        } else {
            console.error('Client mapping is empty!');
        }
        
        // For diagnosis: save mapping key list
        let debugText = 'Client mapping key list (max 50):\n' + Object.keys(clientMap).slice(0, 50).join(', ') + '\n';
        debugText += `\nTotal client count: ${Object.keys(clientMap).length}\n`;
        debugText += `\nExample client data (first):\n`;
        const firstKey = Object.keys(clientMap)[0];
        if (firstKey) {
            debugText += `Key: ${firstKey} (type: ${typeof firstKey})\n`;
            debugText += `Data: ${JSON.stringify(clientMap[firstKey], null, 2)}\n`;
        }
        window._debugClientMap = clientMap; // Save globally
        window._debugText = debugText;
        console.log('Client mapping completed. Key count:', Object.keys(clientMap).length);
        console.log('Example key:', firstKey, 'type:', typeof firstKey);
        console.log('clientMap keys (first 20):', Object.keys(clientMap).slice(0, 20));
        
        // Check if specific key exists (2114)
        const testKey = '2114';
        console.log(`Test key ${testKey} exists:`, testKey in clientMap);
        if (testKey in clientMap) {
            console.log(`Test key ${testKey} data:`, clientMap[testKey]);
        }
    } catch (e) {
        console.error('Error loading client information:', e);
        console.error('Error details:', e.message);
    }
}

// Field mapping (API data → table column)
function mapNoteToRow(note) {
    // Save first note's ClientServiceId for testing
    if (!window._testNoteClientServiceId) {
        window._testNoteClientServiceId = note.ClientServiceId;
        console.log('First note ClientServiceId saved:', note.ClientServiceId, 'type:', typeof note.ClientServiceId);
    }
    
    // Convert to string for mapping (resolve type mismatch)
    const clientServiceIdStr = String(note.ClientServiceId);
    let clientInfo = clientMap[clientServiceIdStr];
    
    // Debug: mapping attempt log
    if (!window._mappingAttempts) window._mappingAttempts = [];
    window._mappingAttempts.push({
        noteId: note.Id,
        clientServiceId: note.ClientServiceId,
        clientServiceIdStr: clientServiceIdStr,
        found: !!clientInfo,
        clientName: clientInfo ? `${clientInfo.FirstName} ${clientInfo.LastName}` : 'NOT FOUND'
    });
    
    // For diagnosis: accumulate each note's ClientServiceId and clientInfo as text
    if (!window._debugRowText) window._debugRowText = '';
    window._debugRowText += `note.ClientServiceId: ${note.ClientServiceId} (${typeof note.ClientServiceId}), clientInfo: ${clientInfo ? '[FOUND]' : '[NOT FOUND]'}\n`;
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
        console.log('Client mapping successful:', clientInfo.MainClientServiceId, 'WingName:', clientInfo.WingName, 'ClientName:', [clientInfo.Title, clientInfo.FirstName, clientInfo.LastName].filter(Boolean).join(' '));
    } else {
        serviceWing = note.WingName || note.LocationName || (note.Client && note.Client.WingName) || (note.ClientInfo && note.ClientInfo.WingName) || '';
        console.log('Client mapping failed:', note.ClientServiceId, 'type:', typeof note.ClientServiceId, 'using fallback:', serviceWing);
        console.log('clientMap keys (first 10):', Object.keys(clientMap).slice(0, 10));
        console.log('Looking for key:', String(note.ClientServiceId), 'exists:', String(note.ClientServiceId) in clientMap);
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
    console.log('renderNotesTable function started');
    await window.progressNoteDB.init();
    const { notes } = await window.progressNoteDB.getProgressNotes(currentSite, { limit: 1000, sortBy: 'EventDate', sortOrder: 'desc' });
    console.log('Loaded Progress Note count:', notes.length, notes);
    
    const tbody = document.querySelector('#notesTable tbody');
    console.log('tbody element:', tbody);
    
    tbody.innerHTML = '';
    console.log('tbody content cleared');
    
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
    
    console.log(`Total ${notes.length} rows added`);
    
            // Auto-select first row
    if (notes.length > 0) {
        console.log('First row selected');
        selectNote(0, notes);
    }
    
            // Output mapping result summary
    if (window._mappingAttempts) {
        const total = window._mappingAttempts.length;
        const found = window._mappingAttempts.filter(a => a.found).length;
        const notFound = total - found;
        
        console.log('=== Client Mapping Result Summary ===');
        console.log(`Total Progress Notes: ${total}`);
        console.log(`Mapping successful: ${found} (${((found/total)*100).toFixed(1)}%)`);
        console.log(`Mapping failed: ${notFound} (${((notFound/total)*100).toFixed(1)}%)`);
        
        if (notFound > 0) {
            console.log('Failed ClientServiceId mappings:');
            const failedIds = window._mappingAttempts
                .filter(a => !a.found)
                .map(a => a.clientServiceId)
                .slice(0, 10); // First 10 only
            console.log(failedIds);
            
            console.log('Keys in clientMap (first 20):');
            console.log(Object.keys(clientMap).slice(0, 20));
        }
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

    // Show loading popup
function showLoadingPopup(message) {
    // Remove existing popup if any
    const existingPopup = document.getElementById('loadingPopup');
    if (existingPopup) {
        existingPopup.remove();
    }
    
    const popup = document.createElement('div');
    popup.id = 'loadingPopup';
    popup.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    const content = document.createElement('div');
    content.style.cssText = `
        background: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        max-width: 400px;
    `;
    
    content.innerHTML = `
        <div style="margin-bottom: 20px;">
            <div style="width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto;"></div>
        </div>
        <h3 style="margin: 0 0 10px 0; color: #333;">Loading Data...</h3>
        <p style="margin: 0; color: #666; font-size: 14px;">${message}</p>
        <p style="margin: 10px 0 0 0; color: #999; font-size: 12px;">Please wait...</p>
    `;
    
    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
    
    popup.appendChild(content);
    document.body.appendChild(popup);
}

    // Hide loading popup
function hideLoadingPopup() {
    const popup = document.getElementById('loadingPopup');
    if (popup) {
        popup.remove();
    }
}

    // Complete IndexedDB deletion and recreation
async function resetIndexedDB() {
    console.log('Starting IndexedDB complete deletion...');
    
    return new Promise((resolve, reject) => {
        const request = indexedDB.deleteDatabase('ProgressNoteDB');
        
        request.onsuccess = () => {
            console.log('IndexedDB deletion completed');
            resolve();
        };
        
        request.onerror = () => {
            console.error('IndexedDB deletion failed:', request.error);
            reject(request.error);
        };
    });
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
        // 1. Load client mapping first (differs by site)
        console.log('Loading client mapping for site:', site);
        await loadClientMap();
        console.log('Client mapping loaded for site:', site);
        
        // 2. Initialize IndexedDB
        console.log('Initializing IndexedDB...');
        await window.progressNoteDB.init();
        console.log('IndexedDB initialization completed');
        
        // 3. Check existing data and incremental update
        const { notes } = await window.progressNoteDB.getProgressNotes(site, { limit: 1 });
        console.log('Current data count in IndexedDB for site:', site, notes.length);
        
        if (notes.length === 0) {
            console.log('No data in IndexedDB for site:', site, '. Fetching initial data from server...');
            
            // Get initial data
            try {
                await fetchAndSaveProgressNotes();
            } catch (error) {
                console.error('Failed to fetch initial data from server, using test data:', error);
                
                // Generate test data (use different client IDs for each site)
                const testData = [
                    {
                        Id: 1,
                        ClientServiceId: site === 'Ramsay' ? 1750 : 2114,
                        EventDate: '2025-07-02T10:00:00',
                        NotesPlainText: 'Test note 1',
                        IsLateEntry: false,
                        ProgressNoteEventType: { Description: 'Daily Note' },
                        CareAreas: [{ Description: 'Personal Care' }],
                        CreatedByName: 'Test User'
                    },
                    {
                        Id: 2,
                        ClientServiceId: site === 'Ramsay' ? 1751 : 2115,
                        EventDate: '2025-07-02T11:00:00',
                        NotesPlainText: 'Test note 2',
                        IsLateEntry: true,
                        ProgressNoteEventType: { Description: 'Incident Report' },
                        CareAreas: [{ Description: 'Medication' }],
                        CreatedByName: 'Test User 2'
                    }
                ];
                
                // Save test data to IndexedDB
                await window.progressNoteDB.saveProgressNotes(site, testData);
                console.log('Test data saved for site:', site);
            }
        } else {
            console.log('Data exists in IndexedDB for site:', site, '. Checking for incremental updates...');
            
            // Check last update time
            const lastUpdateTime = await window.progressNoteDB.getLastUpdateTime(site);
            
            if (lastUpdateTime) {
                console.log('Last update time for site:', site, lastUpdateTime);
                
                // Try incremental update
                try {
                    await fetchIncrementalProgressNotes(lastUpdateTime);
                } catch (error) {
                    console.error('Failed to fetch incremental updates for site:', site, error);
                    // Full refresh if incremental update fails
                    console.log('Falling back to full refresh for site:', site);
                    await fetchAndSaveProgressNotes();
                }
            } else {
                console.log('No last update time found for site:', site, '. Performing full refresh...');
                await fetchAndSaveProgressNotes();
            }
        }
        
        // 4. Table rendering
        console.log('Starting table rendering for site:', site);
        await renderNotesTable();
        console.log('Table rendering completed for site:', site);
        
        // 5. Execute client mapping test
        testClientMapping();
        
        console.log('Site initialization completed for:', site);
    } catch (error) {
        console.error('Error during site initialization for:', site, error);
    }
}

// Fetch Progress Notes from server and save (full refresh)
async function fetchAndSaveProgressNotes() {
    try {
        console.log('Starting to fetch Progress Notes from server...');
        showLoadingPopup(`Fetching Progress Note data from ${currentSite}...`);
        
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
            
            // Check actual data structure
            if (result.data && result.data.length > 0) {
                console.log('First data item keys:', Object.keys(result.data[0]));
                console.log('First data item:', result.data[0]);
            }
            
            showLoadingPopup(`Saving ${result.count} items to IndexedDB...`);
            
            // Save to IndexedDB
            if (result.data && result.data.length > 0) {
                const saveResult = await window.progressNoteDB.saveProgressNotes(currentSite, result.data);
                console.log('IndexedDB save result:', saveResult);
                
                // Save last update time
                await window.progressNoteDB.saveLastUpdateTime(currentSite, result.fetched_at);
                
                console.log('Progress Note data saved successfully');
                showLoadingPopup('Data saving completed!');
                
                // 1초 후 팝업 닫기
                setTimeout(() => {
                    hideLoadingPopup();
                }, 1000);
            }
        } else {
            throw new Error(result.message || 'Failed to fetch Progress Notes');
        }
        
    } catch (error) {
        console.error('Failed to fetch Progress Notes:', error);
        showLoadingPopup('An error occurred while fetching data.');
        
        // 2초 후 팝업 닫기
        setTimeout(() => {
            hideLoadingPopup();
        }, 2000);
    }
}

// 수동 새로고침 함수
async function refreshData() {
    try {
        console.log('Manual refresh requested for site:', currentSite);
        
        // 마지막 업데이트 시간 확인
        const lastUpdateTime = await window.progressNoteDB.getLastUpdateTime(currentSite);
        
        if (lastUpdateTime) {
            console.log('Attempting incremental refresh from:', lastUpdateTime);
            await fetchIncrementalProgressNotes(lastUpdateTime);
        } else {
            console.log('No last update time found, performing full refresh');
            await fetchAndSaveProgressNotes();
        }
        
        // 테이블 다시 렌더링
        await renderNotesTable();
        
    } catch (error) {
        console.error('Refresh failed for site:', currentSite, error);
        showLoadingPopup('Refresh failed. Please try again.');
        
        setTimeout(() => {
            hideLoadingPopup();
        }, 2000);
    }
}

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

// 증분 업데이트로 Progress Note 가져오기 및 저장
async function fetchIncrementalProgressNotes(lastUpdateTime) {
    try {
        console.log('Starting incremental update from:', lastUpdateTime);
        showLoadingPopup(`Checking for new Progress Notes since ${new Date(lastUpdateTime).toLocaleString()}...`);
        
        const response = await fetch('/api/fetch-progress-notes-incremental', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                site: currentSite,
                since_date: lastUpdateTime
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`Successfully fetched ${result.count} new Progress Notes from server`);
            
            if (result.data && result.data.length > 0) {
                showLoadingPopup(`Saving ${result.count} new items to IndexedDB...`);
                
                // IndexedDB에 저장
                const saveResult = await window.progressNoteDB.saveProgressNotes(currentSite, result.data);
                console.log('IndexedDB incremental save result:', saveResult);
                
                // Save last update time
                await window.progressNoteDB.saveLastUpdateTime(currentSite, result.fetched_at);
                
                console.log('Incremental update completed successfully');
                showLoadingPopup(`Updated with ${result.count} new Progress Notes!`);
                
                // 1초 후 팝업 닫기
                setTimeout(() => {
                    hideLoadingPopup();
                }, 1000);
            } else {
                console.log('No new data available');
                showLoadingPopup('No new Progress Notes found.');
                
                // 1초 후 팝업 닫기
                setTimeout(() => {
                    hideLoadingPopup();
                }, 1000);
            }
        } else {
            throw new Error(result.message || 'Failed to fetch incremental Progress Notes');
        }
        
    } catch (error) {
        console.error('Failed to fetch incremental Progress Notes:', error);
        throw error; // 상위 함수에서 처리하도록 에러를 다시 던짐
    }
} 