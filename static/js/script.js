// 중복 스크립트 로드 방지
if (window.scriptLoaded) {
    console.log('Script already loaded, exiting...');
    throw new Error('Script already loaded');
}
window.scriptLoaded = true;

// DOM Elements object to store references
const DOM = {};

// Session timeout related variables
let sessionTimeoutId = null;
let sessionWarningId = null;
let sessionCheckInterval = null;
const SESSION_TIMEOUT_MINUTES = 10;
const SESSION_WARNING_MINUTES = 2;

// 중복 실행 방지를 위한 플래그 (전역 변수로 설정)
if (typeof window.sessionMonitoringStarted === 'undefined') {
    window.sessionMonitoringStarted = false;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // 중복 실행 방지 (이미 초기화되었으면 리턴)
    if (window.sessionInitialized) {
        return;
    }
    window.sessionInitialized = true;
    
    // Check if we're in popup mode (iframe)
    if (window.parent !== window) {
        
        // Hide header buttons in popup mode
        const headerButtons = document.getElementById('headerButtons');
        if (headerButtons) {
            headerButtons.style.display = 'none';
        }
    }
    
    // Check if we're on the progress note form page (index.html)
    const isProgressNotePage = document.getElementById('createDate') && document.getElementById('createTime');
    
    if (isProgressNotePage) {
        // Initialize DOM references
        initializeDOMElements();
        
        // Initialize UI components
        initializeUI();
    } else {
        console.log('Not on progress note form page, skipping form-specific initialization');
    }
    
    // Session refresh (user information update) - always run
    refreshUserSession();
    
    // Start session timeout monitoring (중복 실행 방지)
    if (!window.sessionMonitoringStarted) {
        console.log('Starting session monitoring...');
        startSessionTimeoutMonitoring();
        window.sessionMonitoringStarted = true;
    } else {
        console.log('Session monitoring already started, skipping...');
    }
    
    // User activity detection (session extension) - always run
    setupActivityDetection();
    

});

// Store references to all DOM elements we'll need
function initializeDOMElements() {
    // Form fields
    DOM.createDate = document.getElementById('createDate');
    DOM.createTime = document.getElementById('createTime');
    DOM.eventDate = document.getElementById('eventDate');
    DOM.eventTime = document.getElementById('eventTime');
    DOM.lateEntry = document.getElementById('lateEntry');
    DOM.eventType = document.getElementById('eventType');
    DOM.careArea = document.getElementById('careArea');
    DOM.riskRating = document.getElementById('riskRating');
    DOM.notes = document.getElementById('notes');
    
    // Buttons
    DOM.currentTimeBtn = document.getElementById('currentTimeBtn');
    DOM.addEventTypeBtn = document.getElementById('addEventTypeBtn');
    
    // Floating action buttons (near notes)
    DOM.floatingSaveNewBtn = document.getElementById('floatingSaveNewBtn');
    DOM.floatingSaveCloseBtn = document.getElementById('floatingSaveCloseBtn');
    DOM.floatingCloseBtn = document.getElementById('floatingCloseBtn');
    
    // Client related
    DOM.client = document.getElementById('client');
    DOM.service = document.getElementById('service');
    DOM.clientDetailsDiv = document.querySelector('.client-details-nav');
    DOM.clientDetailItems = document.querySelectorAll('.nav-list li');
    
    // Tab related
    DOM.tabButtons = document.querySelectorAll('.tab-button');
    DOM.tabContents = document.querySelectorAll('.tab-content');
}

// Initialize all UI components
function initializeUI() {
    initializeDatePicker();
    initializeTabs();
    initializeButtons();
    initializeClientHandling();
    loadCareAreas();
    loadEventTypes();
    loadReferenceData();
    initializeNotesResizeObserver();
}

// Initialize date and time pickers
function initializeDatePicker() {
    if (!DOM.createDate || !DOM.createTime) {
        console.error('Date/time input elements not found');
        return;
    }

    // Date picker for Create date
    if (typeof flatpickr === 'function') {
        flatpickr(DOM.createDate, {
            dateFormat: "d M Y",
            defaultDate: "today",
            allowInput: true
        });
        
        // Date picker for Event date
        if (DOM.eventDate) {
            flatpickr(DOM.eventDate, {
                dateFormat: "d M Y",
                defaultDate: "today",
                allowInput: true
            });
        }
        
        // Time picker for Create time
        flatpickr(DOM.createTime, {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            defaultDate: new Date(),
            time_24hr: true,
            allowInput: true
        });
        
        // Time picker for Event time
        if (DOM.eventTime) {
            flatpickr(DOM.eventTime, {
                enableTime: true,
                noCalendar: true,
                dateFormat: "H:i",
                defaultDate: new Date(),
                time_24hr: true,
                allowInput: true
            });
        }
    } else {
        console.error('Flatpickr library not loaded');
    }
    
    // Set current time button
    if (DOM.currentTimeBtn) {
        DOM.currentTimeBtn.addEventListener('click', setCurrentDateTime);
    }
}

// Set current date and time in the form
function setCurrentDateTime() {
    const now = new Date();
    
    if (DOM.createDate && DOM.createDate._flatpickr) {
        DOM.createDate._flatpickr.setDate(now);
    }
    
    if (DOM.eventDate && DOM.eventDate._flatpickr) {
        DOM.eventDate._flatpickr.setDate(now);
    }
    
    if (DOM.createTime && DOM.createTime._flatpickr) {
        DOM.createTime._flatpickr.setDate(now);
    } else if (DOM.createTime) {
        DOM.createTime.value = now.toTimeString().slice(0, 5);
    }
    
    if (DOM.eventTime && DOM.eventTime._flatpickr) {
        DOM.eventTime._flatpickr.setDate(now);
    } else if (DOM.eventTime) {
        DOM.eventTime.value = now.toTimeString().slice(0, 5);
    }
}

// Initialize tabs
function initializeTabs() {
    if (!DOM.tabButtons || !DOM.tabContents) {
        console.error('Tab elements not found');
        return;
    }
    
    DOM.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            DOM.tabButtons.forEach(btn => btn.classList.remove('active'));
            DOM.tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            const tabId = button.getAttribute('data-tab');
            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                targetTab.classList.add('active');
            }
        });
    });
}

// Initialize client dropdown and related functionality
function initializeClientHandling() {
    if (!DOM.client) {
        console.error('Client select element not found');
        return;
    }

    // Load client list
    loadClientList();
    
    // Add change event listener
    DOM.client.addEventListener('change', function() {
        const selectedClientId = this.value;
        
        if (!selectedClientId) {
            displayClientDetails(null);
            return;
        }

        // Get site from URL parameter or from template variable
        const urlParams = new URLSearchParams(window.location.search);
        let site = urlParams.get('site');
        
        // If site is not in URL, try to get from template variable or default
        if (!site) {
            const siteElement = document.querySelector('.site-name');
            if (siteElement) {
                site = siteElement.textContent.trim();
            }
        }
        
        if (!site) {
            site = 'Parafield Gardens';
        }

        // Use site-specific API endpoint
        fetch(`/api/clients/${encodeURIComponent(site)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(clients => {
                const selectedClient = clients.find(client => 
                    client.PersonId.toString() === selectedClientId.toString()
                );
                displayClientDetails(selectedClient);
            })
            .catch(error => {
                console.error('Error fetching client details:', error);
                if (DOM.clientDetailsDiv) {
                    DOM.clientDetailsDiv.innerHTML = '<p>Error loading client details</p>';
                }
            });
    });
    
    // Initialize client detail items if they exist
    if (DOM.clientDetailItems) {
        DOM.clientDetailItems.forEach(item => {
            item.addEventListener('click', () => {
                DOM.clientDetailItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                console.log('Mapped to: ' + item.textContent);
                // Add logic to display content for each section
            });
        });
    }
}

// Display client details in the UI
function displayClientDetails(client) {
    if (!DOM.clientDetailsDiv) {
        console.warn('Client details container not found');
        return;
    }

    if (!client) {
        DOM.clientDetailsDiv.innerHTML = '<p>No client selected</p>';
        return;
    }

    // 표시 형식: "성, 이름" (LastName, FirstName) 순서로 명시적으로 구성
    const firstName = (client.FirstName || '').trim();
    const lastName = (client.LastName || '').trim();
    let clientName = '';
    if (lastName && firstName) {
        clientName = `${lastName}, ${firstName}`;
    } else if (lastName) {
        clientName = lastName;
    } else if (firstName) {
        clientName = firstName;
    } else {
        clientName = client.ClientName || 'Unknown';
    }
    
    const preferredName = client.PreferredName ? 
        '(' + client.PreferredName + ')' : '';
    
    const detailsHTML = 
        '<div class="client-details">' +
            '<h3>' + clientName + ' ' + preferredName + '</h3>' +
            '<p>Gender: ' + (client.Gender || client.gender || 'Not specified') + '</p>' +
            '<p>ID: ' + client.PersonId + '</p>' +
            '<p>Birth Date: ' + (client.BirthDate ? new Date(client.BirthDate).toLocaleDateString() : 'N/A') + '</p>' +
            '<p>Wing: ' + (client.WingName || 'N/A') + '</p>' +
            '<p>Room: ' + (client.RoomName || 'N/A') + '</p>' +
        '</div>';

    DOM.clientDetailsDiv.innerHTML = detailsHTML;
}

// Load the client list from JSON
function loadClientList() {
    if (!DOM.client) return;
    
    // Get site from URL parameter or from template variable
    const urlParams = new URLSearchParams(window.location.search);
    let site = urlParams.get('site');
    
    // If site is not in URL, try to get from template variable or default
    if (!site) {
        // Check if site is available from template (set by server)
        const siteElement = document.querySelector('.site-name');
        if (siteElement) {
            site = siteElement.textContent.trim();
        }
    }
    
    // Default site if still not found
    if (!site) {
        site = 'Parafield Gardens';
    }
    
    console.log('Loading client list for site:', site);
    
    // Use site-specific API endpoint
    fetch(`/api/clients/${encodeURIComponent(site)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            DOM.client.innerHTML = '<option value="">(none)</option>';
            
            if (Array.isArray(data) && data.length > 0) {
                // 성(LastName) 기준으로 정렬 (성, 이름 순서)
                data.sort((a, b) => {
                    const lastNameA = (a.LastName || '').trim();
                    const lastNameB = (b.LastName || '').trim();
                    
                    // LastName으로 먼저 비교
                    const lastNameCompare = lastNameA.localeCompare(lastNameB);
                    if (lastNameCompare !== 0) {
                        return lastNameCompare;
                    }
                    
                    // LastName이 같으면 FirstName으로 비교
                    const firstNameA = (a.FirstName || '').trim();
                    const firstNameB = (b.FirstName || '').trim();
                    return firstNameA.localeCompare(firstNameB);
                });
                
                data.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.PersonId;
                    // 표시 형식: "성, 이름 (ID: ...)" - LastName, FirstName 순서로 명시적으로 구성
                    const firstName = (client.FirstName || '').trim();
                    const lastName = (client.LastName || '').trim();
                    let displayName = '';
                    if (lastName && firstName) {
                        displayName = `${lastName}, ${firstName}`;
                    } else if (lastName) {
                        displayName = lastName;
                    } else if (firstName) {
                        displayName = firstName;
                    } else {
                        displayName = client.ClientName || 'Unknown';
                    }
                    option.textContent = displayName + ' (ID: ' + client.PersonId + ')';
                    DOM.client.appendChild(option);
                });
                
                console.log(`✅ Loaded ${data.length} clients for site: ${site}`);
            } else {
                console.warn(`No clients found for site: ${site}`);
                const option = document.createElement('option');
                option.textContent = 'No clients available';
                option.disabled = true;
                DOM.client.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error loading clients:', error);
            DOM.client.innerHTML = '<option value="">(none)</option>';
            const option = document.createElement('option');
            option.textContent = 'Error loading client list: ' + error.message;
            option.disabled = true;
            DOM.client.appendChild(option);
        });
}

// Load care areas from JSON
function loadCareAreas() {
    if (!DOM.careArea) return;
    
    fetch('/data/carearea.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            DOM.careArea.innerHTML = '<option value="">(none)</option>';

            if (Array.isArray(data)) {
                const sortedAreas = data.sort((a, b) => {
                    const descA = a.Description || '';
                    const descB = b.Description || '';
                    return descA.localeCompare(descB);
                });

                sortedAreas.forEach(area => {
                    if (area.Description) {
                        const option = document.createElement('option');
                        option.value = area.Id;
                        option.textContent = area.Description;
                        DOM.careArea.appendChild(option);
                    }
                });

                console.log('Loaded ' + sortedAreas.length + ' Care Areas');
            }
        })
        .catch(error => {
            console.error('Error loading Care Areas:', error);
            DOM.careArea.innerHTML = '<option value="">(none)</option>';
            const option = document.createElement('option');
            option.textContent = 'Error loading care areas';
            option.disabled = true;
            DOM.careArea.appendChild(option);
        });
}

// Load event types from JSON
function loadEventTypes() {
    if (!DOM.eventType) return;
    
            // Fetch user information and Event Type data simultaneously
    Promise.all([
        fetch('/api/user-info').then(response => response.json()),
        fetch('/data/eventtype.json').then(response => response.json())
    ])
    .then(([userInfo, eventTypeData]) => {
        DOM.eventType.innerHTML = '<option value="">(none)</option>';

        if (Array.isArray(eventTypeData)) {
            // Filter only items where IsArchived is false and sort by Description
            const activeEventTypes = eventTypeData
                .filter(item => !item.IsArchived)
                .sort((a, b) => {
                    const descA = a.Description || '';
                    const descB = b.Description || '';
                    return descA.localeCompare(descB);
                });

            // Add all Event Types to dropdown
            activeEventTypes.forEach(eventType => {
                if (eventType.Description) {
                    const option = document.createElement('option');
                    option.value = eventType.Id;
                    option.textContent = eventType.Description;
                    DOM.eventType.appendChild(option);
                }
            });

            // Set default value based on user role
            const userRole = userInfo.role;
            let defaultEventType = null;
            
            if (userRole === 'doctor') {
                // Set "Doctor" Event Type as default for Doctor role
                defaultEventType = activeEventTypes.find(et => et.Description === 'Doctor');
            } else if (userRole === 'physiotherapist') {
                // Set "Physio Therapist" Event Type as default for Physiotherapist role
                defaultEventType = activeEventTypes.find(et => et.Description === 'Physio Therapist');
            }
            
            if (defaultEventType) {
                DOM.eventType.value = defaultEventType.Id;
                
                // Apply light background color for visual indication (indicates default value)
                DOM.eventType.style.backgroundColor = '#e8f4fd';
                DOM.eventType.style.color = '#333';
                
                console.log(`Event Type default value set based on role (${userRole}): ${defaultEventType.Description} (ID: ${defaultEventType.Id})`);
            } else {
                // Normal style for Admin or other roles
                DOM.eventType.style.backgroundColor = '';
                DOM.eventType.style.color = '';
            }

            console.log('Loaded ' + activeEventTypes.length + ' Event Types');
        }
    })
    .catch(error => {
        console.error('Error loading Event Types or User Info:', error);
        DOM.eventType.innerHTML = '<option value="">(none)</option>';
        const option = document.createElement('option');
        option.textContent = 'Error loading event types';
        option.disabled = true;
        DOM.eventType.appendChild(option);
    });
}

// Initialize text editor toolbar


// Initialize buttons
function initializeButtons() {
    // Floating Save & Close button (near notes)
    if (DOM.floatingSaveCloseBtn) {
        DOM.floatingSaveCloseBtn.addEventListener('click', function() {
            handleSave(true);
        });
    }

    // Floating Save & New button (near notes)
    if (DOM.floatingSaveNewBtn) {
        DOM.floatingSaveNewBtn.addEventListener('click', function() {
            handleSave(false);
        });
    }
    
    // Floating Close button (near notes)
    if (DOM.floatingCloseBtn) {
        DOM.floatingCloseBtn.addEventListener('click', function() {
            // Check if we're in an iframe (popup mode)
            if (window.parent !== window) {
                // Send message to parent window to close popup
                window.parent.postMessage({
                    type: 'PROGRESS_NOTE_SAVED',
                    action: 'close_only'
                }, '*');
            } else {
                // Show confirmation dialog before closing
                if (confirm('Do you want to logout?')) {
                    // Handle logout instead of closing window
                    window.location.href = '/logout';
                }
            }
        });
    }
    
    // Add Event Type button
    if (DOM.addEventTypeBtn) {
        DOM.addEventTypeBtn.addEventListener('click', function() {
            alert("Add new Event Type functionality to be implemented (e.g., open a modal).");
        });
    }
}

// Handle saving data
function handleSave(andClose = false) {
    const formData = gatherFormData();
    
    // Basic validation
    if (!formData.clientId) {
        alert("Please select a client.");
        return;
    }
    
    if (!formData.eventType) {
        alert("Please select an event type.");
        return;
    }
    
    // Save data to server
    saveProgressNoteToServer(formData)
        .then(success => {
            if (success) {
                if (andClose) {
                    // Check if we're in an iframe (popup mode)
                    if (window.parent !== window) {
                        // Send message to parent window to close popup and refresh
                        window.parent.postMessage({
                            type: 'PROGRESS_NOTE_SAVED',
                            action: 'close_and_refresh'
                        }, '*');
                    } else {
                        if (confirm('Data saved successfully. Close the window?')) {
                            window.location.href = '/logout';
                        }
                    }
                } else {
                    resetForm();
                    // Check if we're in an iframe (popup mode)
                    if (window.parent !== window) {
                        // Send message to parent window to refresh
                        window.parent.postMessage({
                            type: 'PROGRESS_NOTE_SAVED',
                            action: 'refresh_only'
                        }, '*');
                    } else {
                        alert('Data saved successfully. Form has been reset for new entry.');
                    }
                }
            }
        });
}

// Send progress note data to server
function saveProgressNoteToServer(formData) {
    console.log('Saving progress note data:', formData);
    
    return fetch('/save_progress_note', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Progress note saved successfully:', data.data);
            
            // Handle API transmission result
            if (data.api_response) {
                // API transmission successful
                console.log('API transmission successful:', data.api_response);
                alert('✅ Progress Note saved and sent to API successfully!');
            } else if (data.warning || data.api_error) {
                // File saved successfully but API transmission failed
                console.warn('API transmission failed:', data.api_error || data.warning);
                                  const warningMsg = data.warning || 'API transmission failed.';
                alert('⚠️ Progress Note saved but API transmission failed.\n\n' + warningMsg + '\n\nThe file was saved successfully, so you can try again later.');
            } else {
                // General save success (no API transmission info)
                alert('✅ Progress Note saved successfully!');
            }
            
            return true;
        } else {
            console.error('Failed to save progress note:', data.message);
                            alert('❌ Progress Note save failed: ' + data.message);
            return false;
        }
    })
    .catch(error => {
        console.error('Error saving progress note:', error);
                    alert('❌ Error occurred while saving Progress Note: ' + error.message);
        return false;
    });
}

// Gather all form data
function gatherFormData() {
            // Check date/time values first
    const createDateValue = DOM.createDate ? DOM.createDate.value : '';
    const createTimeValue = DOM.createTime ? DOM.createTime.value : '';
    const eventDateValue = DOM.eventDate ? DOM.eventDate.value : '';
    const eventTimeValue = DOM.eventTime ? DOM.eventTime.value : '';
    
    console.log('Raw date/time values:', {
        createDate: createDateValue,
        createTime: createTimeValue,
        eventDate: eventDateValue,
        eventTime: eventTimeValue
    });
    
            // Get actual Date object from Flatpickr instance
    let createDateFormatted = '';
    let eventDateFormatted = '';
    
    if (DOM.createDate && DOM.createDate._flatpickr) {
        const selectedDate = DOM.createDate._flatpickr.selectedDates[0];
        if (selectedDate) {
            createDateFormatted = formatDateTime(selectedDate, createTimeValue);
        }
    } else if (createDateValue) {
        createDateFormatted = formatDateTime(createDateValue, createTimeValue);
    }
    
    if (DOM.eventDate && DOM.eventDate._flatpickr) {
        const selectedDate = DOM.eventDate._flatpickr.selectedDates[0];
        if (selectedDate) {
            eventDateFormatted = formatDateTime(selectedDate, eventTimeValue);
        }
    } else if (eventDateValue) {
        eventDateFormatted = formatDateTime(eventDateValue, eventTimeValue);
    }
    
    const formData = {
        clientId: DOM.client ? DOM.client.value : '',
        eventType: DOM.eventType ? DOM.eventType.value : '', // Get value even if disabled
        careArea: DOM.careArea ? DOM.careArea.value : '',
        riskRating: DOM.riskRating ? DOM.riskRating.value : '',
        createDate: createDateFormatted,
        eventDate: eventDateFormatted,
        notes: DOM.notes ? DOM.notes.value : '',
        lateEntry: DOM.lateEntry ? DOM.lateEntry.checked : false
        // flagOnNoticeboard: DOM.flagOnNoticeboard ? DOM.flagOnNoticeboard.checked : false, // Commented out
        // archived: DOM.archived ? DOM.archived.checked : false // Commented out
    };
    
    console.log('Gathered form data:', formData);
    return formData;
}

// Format date and time into ISO string (local timezone, no milliseconds, no Z)
function formatDateTime(dateValue, timeValue) {
    if (!dateValue) return '';
    
    try {
        // Handle date format returned by Flatpickr
        let date;
        
        // Try parsing as Date object first
        if (dateValue instanceof Date) {
            date = dateValue;
        } else {
            // Convert to Date object if string
            date = new Date(dateValue);
        }
        
        // Check if valid date
        if (isNaN(date.getTime())) {
            console.error('Invalid date value:', dateValue);
            return '';
        }
        
        // Set time
        if (timeValue) {
            const timeParts = timeValue.split(':');
            if (timeParts.length >= 2) {
                date.setHours(parseInt(timeParts[0], 10));
                date.setMinutes(parseInt(timeParts[1], 10));
                date.setSeconds(0);
                date.setMilliseconds(0);
            }
        } else {
            date.setHours(0, 0, 0, 0);
        }
        
        // Return local time in YYYY-MM-DDTHH:mm:ss format
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
    } catch (e) {
        console.error('Error formatting date time:', e, 'dateValue:', dateValue, 'timeValue:', timeValue);
        return '';
    }
}

// Reset form for new entry
function resetForm() {
    // Reset all fields including client selection
    if (DOM.client) DOM.client.value = '';
    if (DOM.careArea) DOM.careArea.value = '';
    if (DOM.riskRating) DOM.riskRating.value = '';
    if (DOM.notes) DOM.notes.value = '';
    if (DOM.lateEntry) DOM.lateEntry.checked = false;
            // if (DOM.flagOnNoticeboard) DOM.flagOnNoticeboard.checked = false; // Commented out
        // if (DOM.archived) DOM.archived.checked = false; // Commented out
    
    // Clear client details display
    displayClientDetails(null);
    
            // Reset Event Type to role-based default value
    restoreEventTypeDefault();
    
    // Update time to current for both create and event dates
    setCurrentDateTime();
    
            // Adjust button position since Notes area was reset
    setTimeout(adjustFloatingButtonsPosition, 100);
}

// 역할별 Event Type 기본값 복원
function restoreEventTypeDefault() {
    if (!DOM.eventType) return;
    
    fetch('/api/user-info')
        .then(response => response.json())
        .then(userInfo => {
            const userRole = userInfo.role;
            
            if (userRole === 'doctor') {
                // Doctor 역할인 경우 "Doctor" Event Type 찾아서 선택
                const doctorOption = Array.from(DOM.eventType.options).find(option => 
                    option.textContent === 'Doctor'
                );
                if (doctorOption) {
                    DOM.eventType.value = doctorOption.value;
                    DOM.eventType.style.backgroundColor = '#e8f4fd';
                    DOM.eventType.style.color = '#333';
                    console.log('Reset 후 Doctor Event Type 복원');
                }
            } else if (userRole === 'physiotherapist') {
                // Physiotherapist 역할인 경우 "Physio Therapist" Event Type 찾아서 선택
                const physioOption = Array.from(DOM.eventType.options).find(option => 
                    option.textContent === 'Physio Therapist'
                );
                if (physioOption) {
                    DOM.eventType.value = physioOption.value;
                    DOM.eventType.style.backgroundColor = '#e8f4fd';
                    DOM.eventType.style.color = '#333';
                    console.log('Reset 후 Physio Therapist Event Type 복원');
                }
            } else {
                // Admin이나 기타 역할인 경우 기본값 없음
                DOM.eventType.value = '';
                DOM.eventType.style.backgroundColor = '';
                DOM.eventType.style.color = '';
                console.log('Reset 후 Admin Event Type 기본값 없음');
            }
        })
        .catch(error => {
            console.error('Error restoring event type default:', error);
            // 오류 발생 시 기본값 없음으로 설정
            DOM.eventType.value = '';
            DOM.eventType.style.backgroundColor = '';
            DOM.eventType.style.color = '';
        });
}

// Load reference data for dropdowns
function loadReferenceData() {
    // Mock API URL - replace with real one in production
    const MOCK_API_URL = 'http://server/api/referencetable/';
    
    // Simulate API call
    setTimeout(() => {
        const mockData = {
            // Event Types는 실제 API에서 가져오므로 제거
            riskRatings: [
                { id: 'rr1', name: 'Extreme' },
                { id: 'rr2', name: 'High' },
                { id: 'rr3', name: 'Moderate' },
                { id: 'rr4', name: 'Low' }
            ]
        };
        
        populateDropdowns(mockData);
    }, 1000);
}

// Populate dropdowns with reference data
function populateDropdowns(data) {
    // Event Types는 loadEventTypes() 함수에서 처리하므로 제거

    // Risk Ratings
    if (DOM.riskRating && data.riskRatings) {
        DOM.riskRating.innerHTML = '<option value="">(none)</option>';
        data.riskRatings.forEach(rating => {
            const option = document.createElement('option');
            option.value = rating.id;
            option.textContent = rating.name;
            DOM.riskRating.appendChild(option);
        });
    }
    
    // Note: Care Areas and Event Types are loaded separately from JSON files
}

// Notes 영역 크기 변화 감지 및 버튼 위치 조정
function initializeNotesResizeObserver() {
    if (!DOM.notes) return;
    
    let resizeTimeout = null;
    let lastHeight = 0;
    
    // ResizeObserver로 textarea 크기 변화 감지 (스로틀링 적용)
    if (window.ResizeObserver) {
        const resizeObserver = new ResizeObserver(entries => {
            // 스로틀링으로 과도한 호출 방지
            if (resizeTimeout) {
                clearTimeout(resizeTimeout);
            }
            resizeTimeout = setTimeout(() => {
                const currentHeight = DOM.notes.offsetHeight;
                // 높이가 실제로 변경되었을 때만 조정
                if (Math.abs(currentHeight - lastHeight) > 10) {
                    adjustFloatingButtonsPosition();
                    lastHeight = currentHeight;
                }
            }, 100);
        });
        resizeObserver.observe(DOM.notes);
    }
    
    // Notes 내용 변화 감지 (스로틀링 적용)
    let inputTimeout = null;
    DOM.notes.addEventListener('input', () => {
        if (inputTimeout) {
            clearTimeout(inputTimeout);
        }
        inputTimeout = setTimeout(adjustFloatingButtonsPosition, 200);
    });
    
    // 스크롤 이벤트는 제거 (성능 개선)
    // DOM.notes.addEventListener('scroll', adjustFloatingButtonsPosition);
    
    // 초기 위치 설정
    setTimeout(adjustFloatingButtonsPosition, 100);
}

// Floating 버튼 위치 조정
function adjustFloatingButtonsPosition() {
    const floatingActions = document.querySelector('.floating-actions');
    if (!floatingActions || !DOM.notes) return;
    
    // Notes 영역의 실제 높이 계산
    const notesHeight = DOM.notes.offsetHeight;
    const notesScrollHeight = DOM.notes.scrollHeight;
    const hasScrollbar = notesScrollHeight > notesHeight;
    
    // Notes 내용이 많아서 스크롤이 생겼을 때는 버튼을 더 가깝게
    if (hasScrollbar || notesHeight > 200) {
        floatingActions.style.marginTop = '10px';
        floatingActions.style.position = 'sticky';
        floatingActions.style.bottom = '10px';
        floatingActions.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
        floatingActions.style.backdropFilter = 'blur(5px)';
        floatingActions.style.zIndex = '10';
    } else {
        floatingActions.style.marginTop = '15px';
        floatingActions.style.position = 'relative';
        floatingActions.style.bottom = 'auto';
        floatingActions.style.backgroundColor = 'transparent';
        floatingActions.style.backdropFilter = 'none';
        floatingActions.style.zIndex = 'auto';
    }
    
    // 성능 개선을 위해 로그 제거
    // console.log(`Notes height: ${notesHeight}px, Scroll height: ${notesScrollHeight}px, Has scrollbar: ${hasScrollbar}`);
}

// 세션 새로고침 함수
function refreshUserSession() {
    fetch('/api/refresh-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('세션 새로고침 성공:', data.user_info);
        } else {
            console.log('세션 새로고침 실패:', data.message);
        }
    })
    .catch(error => {
        console.log('세션 새로고침 오류:', error);
    });
}

// 세션 타임아웃 모니터링 시작
function startSessionTimeoutMonitoring() {
    // 이미 모니터링이 시작되었으면 중복 실행 방지
    if (sessionCheckInterval) {
        console.log('세션 모니터링이 이미 실행 중입니다.');
        return;
    }
    
    console.log('세션 타임아웃 모니터링 시작');
    
    // 기존 인터벌이 있다면 정리
    if (window.sessionCheckInterval) {
        clearInterval(window.sessionCheckInterval);
        window.sessionCheckInterval = null;
    }
    
    // 60초마다 세션 상태 확인 (성능 개선을 위해 간격 더 증가)
    sessionCheckInterval = setInterval(checkSessionStatus, 60000);
    window.sessionCheckInterval = sessionCheckInterval;
    
    // 초기 세션 상태 확인
    checkSessionStatus();
}

// 세션 상태 확인
function checkSessionStatus() {
    fetch('/api/session-status')
        .then(response => {
            if (response.status === 401) {
                // 세션 만료: 자동 세션 연장 시도 후 실패하면 로그아웃
                console.log('세션 만료 감지 - 자동 연장 시도');
                return extendSessionSilently().then(() => {
                    // 연장 성공 시 다시 상태 확인
                    return fetch('/api/session-status');
                }).catch(() => {
                    // 연장 실패 시 로그아웃
                    handleSessionTimeout();
                    return Promise.reject('Session expired');
                });
            }
            if (!response.ok) {
                throw new Error('Session status check failed');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const remainingSeconds = data.remaining_seconds;
                const remainingMinutes = Math.floor(remainingSeconds / 60);
                
                // 1분 이하로 남았을 때만 로그 출력 (성능 개선)
                if (remainingSeconds <= 60) {
                    console.log(`[${new Date().toISOString()}] session remaining time: ${remainingMinutes}min ${remainingSeconds % 60}sec`);
                    console.log(`⚠️ 세션 만료 임박: ${remainingSeconds}초 남음`);
                }
                
                // 1분 남았을 때 경고 (성능 개선을 위해 비활성화)
                // if (remainingSeconds <= 60 && remainingSeconds > 0) {
                //     showSessionWarning(remainingSeconds);
                // }
                
                // 이미 경고가 표시되고 있으면 남은 시간 업데이트
                if (sessionWarningId && remainingSeconds > 0) {
                    const countdownElement = document.getElementById('session-countdown');
                    if (countdownElement) {
                        const minutes = Math.floor(remainingSeconds / 60);
                        const seconds = remainingSeconds % 60;
                        countdownElement.textContent = `${minutes}min ${seconds}sec`;
                        
                        // 시간이 30초 이하로 남으면 빨간색으로 강조
                        if (remainingSeconds <= 30) {
                            countdownElement.style.color = '#ff0000';
                            countdownElement.style.animation = 'pulse 1s infinite';
                        } else {
                            countdownElement.style.color = '#e74c3c';
                            countdownElement.style.animation = 'none';
                        }
                    }
                }
                
                // 세션 만료 시 로그아웃
                if (remainingSeconds <= 0) {
                    handleSessionTimeout();
                }
            }
        })
        .catch(error => {
            if (error === 'Session expired') return;
            console.error('session status check error:', error);    
            // 네트워크 오류 시에도 세션 타임아웃 처리
            handleSessionTimeout();
        });
}

// 세션 경고 표시
function showSessionWarning(remainingSeconds) {
    // 이미 경고가 표시되고 있으면 중복 표시하지 않음
    if (sessionWarningId) {
        return;
    }
    
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    
    // 경고 모달 생성
    const warningModal = document.createElement('div');
    warningModal.id = 'session-warning-modal';
    warningModal.innerHTML = `
        <div class="session-warning-overlay">
            <div class="session-warning-content">
                <h3>⚠️ Session Expiration Warning</h3>
                <p>Your session will expire in <strong id="session-countdown">${minutes}min ${seconds}sec</strong>.</p>
                <p>Click the "Extend Session" button to continue working.</p>
                <div class="session-warning-buttons">
                    <button id="extend-session-btn" class="btn-primary">Extend Session</button>
                    <button id="logout-now-btn" class="btn-secondary">Logout Now</button>
                </div>
            </div>
        </div>
    `;
    
    // 스타일 추가
    const style = document.createElement('style');
    style.textContent = `
        .session-warning-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        }
        .session-warning-content {
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .session-warning-content h3 {
            color: #e74c3c;
            margin-bottom: 15px;
        }
        .session-warning-content p {
            margin-bottom: 10px;
            line-height: 1.5;
        }
        .session-warning-buttons {
            margin-top: 20px;
        }
        .session-warning-buttons button {
            margin: 0 10px;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover {
            background: #2980b9;
        }
        .btn-secondary {
            background: #95a5a6;
            color: white;
        }
        .btn-secondary:hover {
            background: #7f8c8d;
        }
        #session-countdown {
            color: #e74c3c;
            font-size: 1.2em;
            font-weight: bold;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    `;
    
    document.head.appendChild(style);
    document.body.appendChild(warningModal);
    
    // 버튼 이벤트 리스너
    document.getElementById('extend-session-btn').addEventListener('click', extendSession);
    document.getElementById('logout-now-btn').addEventListener('click', logoutNow);
    
    // 경고 ID 저장
    sessionWarningId = warningModal;
    
    // 실시간 카운트다운 시작
    startCountdown(remainingSeconds);
}

// 실시간 카운트다운 함수
function startCountdown(initialSeconds) {
    let remainingSeconds = initialSeconds;
    
    const countdownInterval = setInterval(() => {
        remainingSeconds--;
        
        const countdownElement = document.getElementById('session-countdown');
        if (countdownElement) {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            countdownElement.textContent = `${minutes}min ${seconds}sec`;
            
            // 시간이 30초 이하로 남으면 빨간색으로 강조
            if (remainingSeconds <= 30) {
                countdownElement.style.color = '#ff0000';
                countdownElement.style.animation = 'pulse 1s infinite';
            }
        }
        
        // 시간이 0이 되면 세션 타임아웃 처리
        if (remainingSeconds <= 0) {
            clearInterval(countdownInterval);
            handleSessionTimeout();
        }
        
        // 경고가 제거되면 카운트다운도 중지
        if (!sessionWarningId) {
            clearInterval(countdownInterval);
        }
    }, 1000);
    
    // 경고 모달에 카운트다운 인터벌 ID 저장
    if (sessionWarningId) {
        sessionWarningId._countdownInterval = countdownInterval;
    }
}

// 세션 연장
function extendSession() {
    fetch('/api/extend-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Session extension failed');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('세션 연장 성공');
            removeSessionWarning();
            
            // 성공 메시지 표시
            showNotification('Session extended successfully.', 'success');
        }
    })
    .catch(error => {
        console.error('session extension error:', error);
        showNotification('Session extension failed.', 'error');
        handleSessionTimeout();
    });
}

// DB 초기화 및 로그아웃 함수
async function clearDatabaseAndLogout() {
    try {
        // IndexedDB 초기화
        if (window.progressNoteDB) {
            console.log('Clearing IndexedDB before logout...');
            await window.progressNoteDB.clearAll();
            console.log('IndexedDB cleared successfully');
        }
        
        // 서버에 DB 초기화 요청
        await fetch('/api/clear-database', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        console.log('Server database cleared successfully');
    } catch (error) {
        console.error('Error clearing database:', error);
    }
    
    // 로그아웃 처리 후 로그인 페이지로 이동
    try {
        await fetch('/logout');
    } catch (error) {
        console.error('Error during logout:', error);
    }
    
    window.location.href = '/';
}

// 지금 로그아웃
async function logoutNow() {
    removeSessionWarning();
    await clearDatabaseAndLogout();
}

// 세션 경고 제거
function removeSessionWarning() {
    if (sessionWarningId) {
        // 카운트다운 인터벌 중지
        if (sessionWarningId._countdownInterval) {
            clearInterval(sessionWarningId._countdownInterval);
        }
        sessionWarningId.remove();
        sessionWarningId = null;
    }
}

// 세션 타임아웃 처리
function handleSessionTimeout() {
    console.log('세션 타임아웃 - 로그아웃 처리');
    
    // 모니터링 중지
    if (sessionCheckInterval) {
        clearInterval(sessionCheckInterval);
        sessionCheckInterval = null;
    }
    
    // 경고 제거
    removeSessionWarning();
    
    // 타임아웃 모달 표시
    const timeoutModal = document.createElement('div');
    timeoutModal.innerHTML = `
        <div class="session-warning-overlay">
            <div class="session-warning-content">
                <h3>⏰ Session Expired</h3>
                <p>Your session has expired.</p>
                <p>You will be automatically redirected to the login page.</p>
                <div class="session-warning-buttons">
                    <button id="go-login-btn" class="btn-primary">Go to Login Page</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(timeoutModal);
    
    document.getElementById('go-login-btn').addEventListener('click', async () => {
        // DB 초기화 후 로그아웃 처리
        await clearDatabaseAndLogout();
    });
    
    // 3초 후 자동으로 DB 초기화 후 로그아웃 처리
    setTimeout(async () => {
        await clearDatabaseAndLogout();
    }, 3000);
}

// 사용자 활동 감지 (세션 연장) - 성능 최적화
function setupActivityDetection() {
    // 성능 개선을 위해 로그 제거
    // console.log('사용자 활동 감지 설정');
    
    // 사용자 활동 이벤트들 (의미 있는 활동만 감지)
    const activityEvents = [
        'mousedown', 'keypress', 'click', 'touchstart'
    ];
    
    let activityTimeout = null;
    let lastActivityTime = 0;
    const THROTTLE_DELAY = 2000; // 2초로 증가 (성능 개선)
    
    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            const now = Date.now();
            
            // 스로틀링으로 과도한 이벤트 처리 방지
            if (now - lastActivityTime < THROTTLE_DELAY) {
                return;
            }
            lastActivityTime = now;
            
            // 마지막 활동 시간 기록
            sessionStorage.setItem('lastActivity', now.toString());
            
            // 기존 타임아웃 클리어
            if (activityTimeout) {
                clearTimeout(activityTimeout);
            }
            
            // 4분 후에 세션 연장 시도 (1분 이하로 남았을 때만)
            activityTimeout = setTimeout(() => {
                // 현재 세션 상태를 확인하여 1분 이하로 남았을 때만 자동 연장
                checkSessionStatusForAutoExtension();
            }, 240000); // 4분 (5분 세션에서 1분 남았을 때)
        });
    });
}

// 자동 세션 연장을 위한 세션 상태 확인
function checkSessionStatusForAutoExtension() {
    fetch('/api/session-status')
        .then(response => {
            if (response.status === 401) {
                // 세션 만료: 자동 세션 연장 시도
                console.log('자동 연장 중 세션 만료 감지 - 연장 시도');
                return extendSessionSilently().then(() => {
                    // 연장 성공 시 다시 상태 확인
                    return fetch('/api/session-status');
                }).catch(() => {
                    // 연장 실패 시 로그아웃
                    handleSessionTimeout();
                    return Promise.reject('Session expired');
                });
            }
            if (!response.ok) {
                throw new Error('Session status check failed');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const remainingSeconds = data.remaining_seconds;
                
                // 1분 이하로 남았을 때만 자동 연장
                if (remainingSeconds <= 60 && remainingSeconds > 0) {
                    // 성능 개선을 위해 로그 제거
                    // console.log(`자동 세션 연장 시도 (남은 시간: ${remainingSeconds}초)`);
                    extendSessionSilently();
                } else {
                    // 성능 개선을 위해 로그 제거
                    // console.log(`자동 세션 연장 건너뜀 (남은 시간: ${remainingSeconds}초)`);
                }
            }
        })
        .catch(error => {
            if (error === 'Session expired') return;
            console.error('자동 세션 연장 확인 오류:', error);
        });
}

// 조용한 세션 연장 (사용자에게 알리지 않음)
function extendSessionSilently() {
    fetch('/api/extend-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Silent session extension failed');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 성능 개선을 위해 로그 제거
            // console.log('조용한 세션 연장 성공 (1분 이하 남은 경우)');
        }
    })
    .catch(error => {
        console.error('조용한 세션 연장 오류:', error);
    });
}

// 알림 표시 함수
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 스타일 추가
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: bold;
            z-index: 10001;
            animation: slideIn 0.3s ease-out;
        }
        .notification-success {
            background: #27ae60;
        }
        .notification-error {
            background: #e74c3c;
        }
        .notification-info {
            background: #3498db;
        }
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    
    document.head.appendChild(style);
    document.body.appendChild(notification);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

