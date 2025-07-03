// DOM Elements object to store references
const DOM = {};

// Session timeout related variables
let sessionTimeoutId = null;
let sessionWarningId = null;
let sessionCheckInterval = null;
const SESSION_TIMEOUT_MINUTES = 5;
const SESSION_WARNING_MINUTES = 1;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're in popup mode (iframe)
    if (window.parent !== window) {
        // Hide header buttons in popup mode
        const headerButtons = document.getElementById('headerButtons');
        if (headerButtons) {
            headerButtons.style.display = 'none';
        }
    }
    
    // Initialize DOM references
    initializeDOMElements();
    
    // Initialize UI components
    initializeUI();
    
    // Session refresh (user information update)
    refreshUserSession();
    
    // Start session timeout monitoring
    startSessionTimeoutMonitoring();
    
    // User activity detection (session extension)
    setupActivityDetection();
    
    // 프로그레스 노트 데이터베이스 초기화 및 데이터 가져오기
    initializeProgressNoteData();
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
    // DOM.flagOnNoticeboard = document.getElementById('flagOnNoticeboard'); // 주석 처리됨
    // DOM.archived = document.getElementById('archived'); // 주석 처리됨
    
    // Buttons
    DOM.currentTimeBtn = document.getElementById('currentTimeBtn');
    DOM.addEventTypeBtn = document.getElementById('addEventTypeBtn');
    // DOM.previousVersionsBtn = document.getElementById('previousVersionsBtn'); // Commented out
    
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
    
    // Toolbar
    // DOM.toolbar = document.querySelector('.toolbar'); // Commented out
}

// Initialize all UI components
function initializeUI() {
    initializeDatePicker();
    initializeTabs();
    initializeToolbar();
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

        fetch('/data/Client_list.json')
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

    const preferredName = client.PreferredName ? 
        '(' + client.PreferredName + ')' : '';
    
    const detailsHTML = 
        '<div class="client-details">' +
            '<h3>' + client.ClientName + ' ' + preferredName + '</h3>' +
            '<p>Gender: ' + (client.Gender || client.gender || 'Not specified') + '</p>' +
            '<p>ID: ' + client.PersonId + '</p>' +
            '<p>Birth Date: ' + new Date(client.BirthDate).toLocaleDateString() + '</p>' +
            '<p>Wing: ' + (client.WingName || 'N/A') + '</p>' +
            '<p>Room: ' + (client.RoomName || 'N/A') + '</p>' +
        '</div>';

    DOM.clientDetailsDiv.innerHTML = detailsHTML;
}

// Load the client list from JSON
function loadClientList() {
    if (!DOM.client) return;
    
    fetch('/data/Client_list.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            DOM.client.innerHTML = '<option value="">(none)</option>';
            
            if (Array.isArray(data)) {
                data.sort((a, b) => {
                    const nameA = a.ClientName || '';
                    const nameB = b.ClientName || '';
                    return nameA.localeCompare(nameB);
                });
                
                data.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.PersonId;
                    option.textContent = client.ClientName + ' (ID: ' + client.PersonId + ')';
                    DOM.client.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading clients:', error);
            DOM.client.innerHTML = '<option value="">(none)</option>';
            const option = document.createElement('option');
            option.textContent = 'Error loading client list';
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
function initializeToolbar() {
    // Toolbar is commented out, so it may not exist
    if (!DOM.toolbar) {
        console.log('Toolbar not found (likely commented out) - skipping toolbar initialization');
        return;
    }
    
    if (!DOM.notes) {
        console.error('Notes textarea not found');
        return;
    }

    DOM.toolbar.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const command = button.title.toLowerCase();
            if (command === 'unordered list') {
                document.execCommand('insertUnorderedList', false, null);
            } else if (command === 'ordered list') {
                document.execCommand('insertOrderedList', false, null);
            } else if (command === 'decrease indent') {
                document.execCommand('outdent', false, null);
            } else if (command === 'increase indent') {
                document.execCommand('indent', false, null);
            } else {
                document.execCommand(command, false, null);
            }
            DOM.notes.focus();
        });
    });
}

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
    
    // ResizeObserver로 textarea 크기 변화 감지
    if (window.ResizeObserver) {
        const resizeObserver = new ResizeObserver(entries => {
            adjustFloatingButtonsPosition();
        });
        resizeObserver.observe(DOM.notes);
    }
    
    // Notes 내용 변화 감지
    DOM.notes.addEventListener('input', adjustFloatingButtonsPosition);
    DOM.notes.addEventListener('scroll', adjustFloatingButtonsPosition);
    
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
    
    console.log(`Notes height: ${notesHeight}px, Scroll height: ${notesScrollHeight}px, Has scrollbar: ${hasScrollbar}`);
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
    console.log('세션 타임아웃 모니터링 시작');
    
    // 30초마다 세션 상태 확인
    sessionCheckInterval = setInterval(checkSessionStatus, 30000);
    
    // 초기 세션 상태 확인
    checkSessionStatus();
}

// 세션 상태 확인
function checkSessionStatus() {
    fetch('/api/session-status')
        .then(response => {
            if (response.status === 401) {
                // 세션 만료: 즉시 로그아웃 처리
                handleSessionTimeout();
                return Promise.reject('Session expired');
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
                
                console.log(`session remaining time: ${remainingMinutes}min ${remainingSeconds % 60}sec`);
                
                // 1분 남았을 때 경고
                if (remainingSeconds <= 60 && remainingSeconds > 0) {
                    showSessionWarning(remainingSeconds);
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
                <p>Your session will expire in <strong>${minutes}min ${seconds}sec</strong>.</p>
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
    `;
    
    document.head.appendChild(style);
    document.body.appendChild(warningModal);
    
    // 버튼 이벤트 리스너
    document.getElementById('extend-session-btn').addEventListener('click', extendSession);
    document.getElementById('logout-now-btn').addEventListener('click', logoutNow);
    
    // 경고 ID 저장
    sessionWarningId = warningModal;
    
    // 10초 후 자동으로 경고 제거 (사용자가 아무것도 하지 않으면)
    setTimeout(() => {
        if (sessionWarningId) {
            removeSessionWarning();
        }
    }, 10000);
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

// 지금 로그아웃
function logoutNow() {
    removeSessionWarning();
    window.location.href = '/logout';
}

// 세션 경고 제거
function removeSessionWarning() {
    if (sessionWarningId) {
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
    
    document.getElementById('go-login-btn').addEventListener('click', () => {
        // 로그아웃 처리 후 로그인 페이지로 이동
        fetch('/logout')
            .then(() => {
                window.location.href = '/';
            })
            .catch(() => {
                window.location.href = '/';
            });
    });
    
    // 3초 후 자동으로 로그아웃 처리 후 로그인 페이지로 이동
    setTimeout(() => {
        fetch('/logout')
            .then(() => {
                window.location.href = '/';
            })
            .catch(() => {
                window.location.href = '/';
            });
    }, 3000);
}

// 사용자 활동 감지 (세션 연장)
function setupActivityDetection() {
    console.log('사용자 활동 감지 설정');
    
    // 사용자 활동 이벤트들
    const activityEvents = [
        'mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'
    ];
    
    let activityTimeout = null;
    
    activityEvents.forEach(event => {
        document.addEventListener(event, () => {
            // 마지막 활동 시간 기록
            sessionStorage.setItem('lastActivity', Date.now().toString());
            
            // 기존 타임아웃 클리어
            if (activityTimeout) {
                clearTimeout(activityTimeout);
            }
            
            // 2분 후에 세션 연장 시도
            activityTimeout = setTimeout(() => {
                extendSessionSilently();
            }, 120000); // 2분
        });
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
            console.log('조용한 세션 연장 성공');
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

// 프로그레스 노트 데이터베이스 초기화 및 데이터 가져오기
async function initializeProgressNoteData() {
    try {
        console.log('프로그레스 노트 데이터베이스 초기화 시작...');
        
        // IndexedDB 초기화
        await progressNoteDB.init();
        console.log('IndexedDB 초기화 완료');
        
        // 현재 사이트 정보 가져오기
        const site = document.querySelector('.site-name').textContent;
        console.log(`현재 사이트: ${site}`);
        
        // 데이터베이스 정보 조회
        const dbInfo = await progressNoteDB.getDatabaseInfo();
        console.log('데이터베이스 정보:', dbInfo);
        
        // 마지막 업데이트 시간 확인
        const lastUpdate = await progressNoteDB.getLastUpdateTime(site);
        console.log(`${site} 마지막 업데이트:`, lastUpdate);
        
        // 데이터 가져오기 (2주치)
        await fetchAndSaveProgressNotes(site, 14);
        
        console.log('프로그레스 노트 데이터베이스 초기화 완료');
        
    } catch (error) {
        console.error('프로그레스 노트 데이터베이스 초기화 실패:', error);
    }
}

// 프로그레스 노트 가져오기 및 저장
async function fetchAndSaveProgressNotes(site, days = 14) {
    try {
        console.log(`${site}에서 ${days}일치 프로그레스 노트 가져오기 시작...`);
        
        // 서버에서 프로그레스 노트 가져오기
        const response = await fetch('/api/fetch-progress-notes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                site: site,
                days: days
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`${site}: ${result.count}개의 프로그레스 노트 가져오기 성공`);
            
            // IndexedDB에 저장
            if (result.data && result.data.length > 0) {
                const saveResult = await progressNoteDB.saveProgressNotes(site, result.data);
                console.log(`${site} 저장 결과:`, saveResult);
                
                // 마지막 업데이트 시간 저장
                await progressNoteDB.saveLastUpdateTime(site, result.fetched_at);
                
                // Only show notification on progress note list page, not in popup
                if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
                    showNotification(`${site}: ${result.count} progress notes have been loaded.`, 'success');
                }
            } else {
                console.log(`${site}: 가져올 프로그레스 노트가 없습니다.`);
                // Only show notification on progress note list page, not in popup
                if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
                    showNotification(`${site}: No progress notes to load.`, 'info');
                }
            }
        } else {
            throw new Error(result.message || '프로그레스 노트 가져오기 실패');
        }
        
    } catch (error) {
        console.error(`${site} 프로그레스 노트 가져오기 실패:`, error);
        // Only show notification on progress note list page, not in popup
        if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
            showNotification(`${site} Failed to load progress notes: ${error.message}`, 'error');
        }
    }
}

// 증분 업데이트로 프로그레스 노트 가져오기
async function fetchIncrementalProgressNotes(site) {
    try {
        console.log(`${site} 증분 업데이트 시작...`);
        
        // 마지막 업데이트 시간 가져오기
        const lastUpdate = await progressNoteDB.getLastUpdateTime(site);
        
        if (!lastUpdate) {
            console.log(`${site}: 마지막 업데이트 시간이 없어 전체 데이터를 가져옵니다.`);
            return await fetchAndSaveProgressNotes(site, 14);
        }
        
        console.log(`${site} 마지막 업데이트: ${lastUpdate}`);
        
        // 증분 업데이트 요청
        const response = await fetch('/api/fetch-progress-notes-incremental', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                site: site,
                since_date: lastUpdate
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            console.log(`${site}: ${result.count}개의 새로운 프로그레스 노트 가져오기 성공`);
            
            // IndexedDB에 저장
            if (result.data && result.data.length > 0) {
                const saveResult = await progressNoteDB.saveProgressNotes(site, result.data);
                console.log(`${site} 저장 결과:`, saveResult);
                
                // 마지막 업데이트 시간 저장
                await progressNoteDB.saveLastUpdateTime(site, result.fetched_at);
                
                // Only show notification on progress note list page, not in popup
                if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
                    showNotification(`${site}: ${result.count} new progress notes have been loaded.`, 'success');
                }
            } else {
                console.log(`${site}: 새로운 프로그레스 노트가 없습니다.`);
                // Only show notification on progress note list page, not in popup
                if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
                    showNotification(`${site}: No new progress notes available.`, 'info');
                }
            }
        } else {
            throw new Error(result.message || '증분 업데이트 실패');
        }
        
    } catch (error) {
        console.error(`${site} 증분 업데이트 실패:`, error);
        // Only show notification on progress note list page, not in popup
        if (document.title.includes('Progress Notes') && (!window.parent || window.parent === window)) {
            showNotification(`${site} Incremental update failed: ${error.message}`, 'error');
        }
    }
}

// 프로그레스 노트 조회
async function getProgressNotes(site, options = {}) {
    try {
        const result = await progressNoteDB.getProgressNotes(site, options);
        console.log(`${site} 프로그레스 노트 조회 결과:`, result);
        return result;
    } catch (error) {
        console.error(`${site} 프로그레스 노트 조회 실패:`, error);
        throw error;
    }
}

// 프로그레스 노트 데이터베이스 정보 조회
async function getProgressNoteDBInfo() {
    try {
        const info = await progressNoteDB.getDatabaseInfo();
        console.log('프로그레스 노트 데이터베이스 정보:', info);
        return info;
    } catch (error) {
        console.error('데이터베이스 정보 조회 실패:', error);
        throw error;
    }
}

// 프로그레스 노트 새로고침 (수동)
async function refreshProgressNotes() {
    const site = document.querySelector('.site-name').textContent;
    console.log(`${site} 프로그레스 노트 수동 새로고침 시작...`);
    
    try {
        await fetchAndSaveProgressNotes(site, 14);
        showNotification(`${site} Progress notes refresh completed`, 'success');
    } catch (error) {
        console.error('프로그레스 노트 새로고침 실패:', error);
        showNotification('Progress notes refresh failed', 'error');
    }
}

// 프로그레스 노트 증분 업데이트 (수동)
async function updateProgressNotes() {
    const site = document.querySelector('.site-name').textContent;
    console.log(`${site} 프로그레스 노트 증분 업데이트 시작...`);
    
    try {
        await fetchIncrementalProgressNotes(site);
        showNotification(`${site} Progress notes incremental update completed`, 'success');
    } catch (error) {
        console.error('프로그레스 노트 증분 업데이트 실패:', error);
        showNotification('Progress notes incremental update failed', 'error');
    }
}