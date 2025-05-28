// DOM Elements object to store references
const DOM = {};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize DOM references
    initializeDOMElements();
    
    // Initialize UI components
    initializeUI();
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
    // DOM.previousVersionsBtn = document.getElementById('previousVersionsBtn'); // 주석 처리됨
    
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
    // DOM.toolbar = document.querySelector('.toolbar'); // 주석 처리됨
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
    
    // 사용자 정보와 Event Type 데이터를 동시에 가져오기
    Promise.all([
        fetch('/api/user-info').then(response => response.json()),
        fetch('/data/eventtype.json').then(response => response.json())
    ])
    .then(([userInfo, eventTypeData]) => {
        DOM.eventType.innerHTML = '<option value="">(none)</option>';

        if (Array.isArray(eventTypeData)) {
            // IsArchived가 false인 항목만 필터링하고 Description으로 정렬
            const activeEventTypes = eventTypeData
                .filter(item => !item.IsArchived)
                .sort((a, b) => {
                    const descA = a.Description || '';
                    const descB = b.Description || '';
                    return descA.localeCompare(descB);
                });

            // 모든 Event Type을 드롭다운에 추가
            activeEventTypes.forEach(eventType => {
                if (eventType.Description) {
                    const option = document.createElement('option');
                    option.value = eventType.Id;
                    option.textContent = eventType.Description;
                    DOM.eventType.appendChild(option);
                }
            });

            // 사용자 역할에 따른 기본값 설정
            const userRole = userInfo.role;
            let defaultEventType = null;
            
            if (userRole === 'doctor') {
                // Doctor 역할인 경우 "Doctor" Event Type을 기본값으로 설정
                defaultEventType = activeEventTypes.find(et => et.Description === 'Doctor');
            } else if (userRole === 'physiotherapist') {
                // Physiotherapist 역할인 경우 "Physio Therapist" Event Type을 기본값으로 설정
                defaultEventType = activeEventTypes.find(et => et.Description === 'Physio Therapist');
            }
            
            if (defaultEventType) {
                DOM.eventType.value = defaultEventType.Id;
                
                // 시각적 표시를 위해 연한 배경색 적용 (기본값임을 나타냄)
                DOM.eventType.style.backgroundColor = '#e8f4fd';
                DOM.eventType.style.color = '#333';
                
                console.log(`역할(${userRole})에 따라 Event Type 기본값 설정: ${defaultEventType.Description} (ID: ${defaultEventType.Id})`);
            } else {
                // Admin이나 기타 역할인 경우 정상적인 스타일
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
    // Toolbar가 주석 처리되어 있으므로 존재하지 않을 수 있음
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
            // Show confirmation dialog before closing
            if (confirm('Do you want to logout?')) {
                // 창 닫기 대신 로그아웃 처리
                window.location.href = '/logout';
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
                    if (confirm('Data saved successfully. Close the window?')) {
                        window.location.href = '/logout';
                    }
                } else {
                    resetForm();
                    alert('Data saved successfully. Form has been reset for new entry.');
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
            return true;
        } else {
            console.error('Failed to save progress note:', data.message);
            alert('Failed to save progress note: ' + data.message);
            return false;
        }
    })
    .catch(error => {
        console.error('Error saving progress note:', error);
        alert('Error saving progress note: ' + error.message);
        return false;
    });
}

// Gather all form data
function gatherFormData() {
    // 날짜/시간 값들을 먼저 확인
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
    
    // Flatpickr 인스턴스에서 실제 Date 객체 가져오기
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
        eventType: DOM.eventType ? DOM.eventType.value : '', // disabled 상태여도 값 가져오기
        careArea: DOM.careArea ? DOM.careArea.value : '',
        riskRating: DOM.riskRating ? DOM.riskRating.value : '',
        createDate: createDateFormatted,
        eventDate: eventDateFormatted,
        notes: DOM.notes ? DOM.notes.value : '',
        lateEntry: DOM.lateEntry ? DOM.lateEntry.checked : false
        // flagOnNoticeboard: DOM.flagOnNoticeboard ? DOM.flagOnNoticeboard.checked : false, // 주석 처리됨
        // archived: DOM.archived ? DOM.archived.checked : false // 주석 처리됨
    };
    
    console.log('Gathered form data:', formData);
    return formData;
}

// Format date and time into ISO string
function formatDateTime(dateValue, timeValue) {
    if (!dateValue) return '';
    
    try {
        // Flatpickr에서 반환하는 날짜 형식을 처리
        let date;
        
        // 먼저 Date 객체로 파싱 시도
        if (dateValue instanceof Date) {
            date = dateValue;
        } else {
            // 문자열인 경우 Date 객체로 변환
            date = new Date(dateValue);
        }
        
        // 유효한 날짜인지 확인
        if (isNaN(date.getTime())) {
            console.error('Invalid date value:', dateValue);
            return '';
        }
        
        // 시간 설정
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
        
        return date.toISOString();
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
    // if (DOM.flagOnNoticeboard) DOM.flagOnNoticeboard.checked = false; // 주석 처리됨
    // if (DOM.archived) DOM.archived.checked = false; // 주석 처리됨
    
    // Clear client details display
    displayClientDetails(null);
    
    // Event Type은 역할별 기본값으로 다시 설정
    restoreEventTypeDefault();
    
    // Update time to current for both create and event dates
    setCurrentDateTime();
    
    // Notes 영역이 리셋되었으므로 버튼 위치 재조정
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