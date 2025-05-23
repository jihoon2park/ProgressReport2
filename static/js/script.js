document.addEventListener('DOMContentLoaded', function() {
    // Current Time 버튼 이벤트 리스너 추가
    document.getElementById('currentTimeBtn').addEventListener('click', function() {
        const now = new Date();
        
        // 날짜 포맷팅 (예: "10 May 2023" 형식)
        const options = { day: 'numeric', month: 'short', year: 'numeric' };
        const formattedDate = now.toLocaleDateString('en-GB', options);
        
        // 시간 포맷팅 (HH:MM 형식)
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const formattedTime = `${hours}:${minutes}`;
        
        // input 필드에 현재 날짜와 시간 설정
        document.getElementById('createDate').value = formattedDate;
        document.getElementById('createTime').value = formattedTime;
    });
});

document.addEventListener('DOMContentLoaded', () => {
    // --- Global Variables ---
    let reference_table = {}; // To store fetched reference data

    // --- DOM Elements ---
    const clientSelect = document.getElementById('client');
    const serviceSelect = document.getElementById('service');
    const clientDetailItems = document.querySelectorAll('.nav-list li');

    const createDateInput = document.getElementById('createDate');
    const createTimeInput = document.getElementById('createTime');
    const lateEntryCheckbox = document.getElementById('lateEntry');
    const eventTypeSelect = document.getElementById('eventType');
    const careAreaSelect = document.getElementById('careArea');
    const riskRatingSelect = document.getElementById('riskRating');
    const notesTextarea = document.getElementById('notes');
    const flagOnNoticeboardCheckbox = document.getElementById('flagOnNoticeboard');
    const archivedCheckbox = document.getElementById('archived');

    const saveNewBtn = document.getElementById('saveNewBtn');
    const saveCloseBtn = document.getElementById('saveCloseBtn');
    const closeBtn = document.getElementById('closeBtn');
    const addEventTypeBtn = document.getElementById('addEventTypeBtn');
    const previousVersionsBtn = document.getElementById('previousVersionsBtn');

    const tabs = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    // --- API Simulation ---
    const MOCK_API_URL = 'http://server/api/referencetable/'; // Your API endpoint

    async function fetchReferenceData() {
        console.log(`Workspaceing reference data from ${MOCK_API_URL}...`);
        // Simulate API call
        return new Promise(resolve => {
            setTimeout(() => {
                const mockData = {
                    eventTypes: [
                        { id: 'et1', name: 'Initial Assessment' },
                        { id: 'et2', name: 'Follow-up Visit' },
                        { id: 'et3', name: 'Phone Call' },
                        { id: 'et4', name: 'Medication Change' }
                    ],
                    careAreas: [
                        { id: 'ca1', name: 'Clinical Care' },
                        { id: 'ca2', name: 'Personal Support' },
                        { id: 'ca3', name: 'Social Activities' },
                        { id: 'ca4', name: 'Allied Health' }
                    ],
                    riskRatings: [
                        { id: 'rr1', name: 'Low' },
                        { id: 'rr2', name: 'Medium' },
                        { id: 'rr3', name: 'High' },
                        { id: 'rr4', name: 'Critical' }
                    ]
                };
                console.log("Mock data received:", mockData);
                resolve(mockData);
            }, 1000);
        });
    }

    // --- Populate Dropdowns ---
    function populateDropdown(selectElement, items, defaultOptionText = "(none)") {
        selectElement.innerHTML = `<option value="">${defaultOptionText}</option>`; // Clear existing and add default
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item.name;
            selectElement.appendChild(option);
        });
    }

    async function initializeDropdowns() {
        try {
            reference_table = await fetchReferenceData();
            if (reference_table.eventTypes) {
                populateDropdown(eventTypeSelect, reference_table.eventTypes);
            }
            if (reference_table.careAreas) {
                populateDropdown(careAreaSelect, reference_table.careAreas);
            }
            if (reference_table.riskRatings) {
                populateDropdown(riskRatingSelect, reference_table.riskRatings);
            }
        } catch (error) {
            console.error("Failed to initialize dropdowns:", error);
            // Potentially display an error message to the user
        }
    }

    // --- Event Handlers ---
    function handleClientSelection() {
        const selectedClientId = clientSelect.value;
        if (selectedClientId) {
            console.log(`Client selected: ${selectedClientId} - ${clientSelect.options[clientSelect.selectedIndex].text}`);
            // Here you would typically fetch and display client-specific information
            // For now, let's just log it and maybe update a dummy area
            document.querySelector('.no-photo').textContent = `Details for ${clientSelect.options[clientSelect.selectedIndex].text}`;
        } else {
            document.querySelector('.no-photo').textContent = 'No Photo Available';
        }
    }

    clientDetailItems.forEach(item => {
        item.addEventListener('click', () => {
            clientDetailItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            console.log(`Mapsd to: ${item.textContent}`);
            // Add logic to display content for each section
        });
    });

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const targetTabContentId = tab.dataset.tab;
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === targetTabContentId) {
                    content.classList.add('active');
                }
            });
        });
    });

    function getCurrentDateTime() {
        const now = new Date();
        const day = String(now.getDate()).padStart(2, '0');
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = monthNames[now.getMonth()];
        const year = now.getFullYear();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');

        return {
            date: `${day} ${month} ${year}`, // Format as in image
            time: `${hours}:${minutes}`
        };
    }

    function setInitialDateTime() {
        const { date, time } = getCurrentDateTime();
        
        // 달력 선택기 초기화
        flatpickr(createDateInput, {
            defaultDate: "today",
            dateFormat: "d M Y",
            allowInput: true,
            monthSelectorType: "static"
        });
        
        // 시간 선택기 초기화
        flatpickr(createTimeInput, {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            defaultDate: new Date(),
            time_24hr: true,
            allowInput: true
        });
    }


    function gatherFormData() {
        const formData = {
            clientId: clientSelect.value,
            service: serviceSelect.value,
            createDate: createDateInput.value,
            createTime: createTimeInput.value,
            lateEntry: lateEntryCheckbox.checked,
            eventType: eventTypeSelect.value,
            careArea: careAreaSelect.value,
            riskRating: riskRatingSelect.value,
            notes: notesTextarea.value,
            flagOnNoticeboard: flagOnNoticeboardCheckbox.checked,
            archived: archivedCheckbox.checked
        };
        return formData;
    }

    async function sendDataToBackend(data) {
        // Simulate sending data to a backend API
        console.log("Sending data to backend:", JSON.stringify(data, null, 2));
        // Replace with actual fetch POST request:
        /*
        try {
            const response = await fetch('YOUR_BACKEND_API_ENDPOINT_FOR_SAVING', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            console.log('Save successful:', result);
            alert('Progress note saved successfully!');
            return true;
        } catch (error) {
            console.error('Error saving progress note:', error);
            alert('Failed to save progress note.');
            return false;
        }
        */
        return new Promise(resolve => { // Simulating async operation
            setTimeout(() => {
                alert('Data (simulated) sent to backend. Check console for JSON.');
                resolve(true);
            }, 500);
        });
    }

    function clearForm() {
        // Reset fields to their initial state or empty
        // clientSelect.value = ""; // Don't clear client usually for "Save & New"
        // serviceSelect.value = "";
        // For a true "Save & New", you might want to keep client/service
        // and reset other note-specific fields.
        const { date, time } = getCurrentDateTime();
        // createDateInput.value = date; // Or keep existing if that's the workflow
        createTimeInput.value = time;
        lateEntryCheckbox.checked = false;
        eventTypeSelect.value = "";
        careAreaSelect.value = "";
        riskRatingSelect.value = "";
        notesTextarea.value = "";
        flagOnNoticeboardCheckbox.checked = false;
        archivedCheckbox.checked = false; // Or based on workflow
        console.log("Form cleared for new entry (partially).");
    }

    async function handleSave(andClose = false) {
        const formData = gatherFormData();
        if (!formData.clientId) {
            alert("Please select a client.");
            return;
        }
        if (!formData.eventType) {
            alert("Please select an event type.");
            return;
        }
        // Add more validation as needed

        const success = await sendDataToBackend(formData);
        if (success) {
            if (andClose) {
                // Simulate closing the window/view
                alert("Closing progress notes window (simulated).");
                // If this were a real app, you might hide the modal or redirect.
                // For this example, we can just clear the form.
                // clearForm(); // Or a more thorough reset if closing means starting fresh next time
            } else { // Save & New
                clearForm();
                eventTypeSelect.focus(); // Focus on a key field for the new note
            }
        }
    }

    // --- Event Listeners ---
    clientSelect.addEventListener('change', handleClientSelection);

    saveNewBtn.addEventListener('click', () => handleSave(false));
    saveCloseBtn.addEventListener('click', () => handleSave(true));

    /**
     * Handles user logout process with confirmation
     * @param {string} redirectUrl URL to redirect after successful logout
     * @returns {Promise<void>}
     */
    const handleLogout = async (redirectUrl = '/') => {
        const LOGOUT_ENDPOINT = '/logout';
        const CONFIRMATION_MESSAGE = 'Do you want to log out?';

        if (confirm(CONFIRMATION_MESSAGE)) {
            try {
                await fetch(LOGOUT_ENDPOINT);
                window.location.href = redirectUrl;
            } catch (error) {
                console.error('Logout failed:', error);
                alert('Failed to log out. Please try again.');
            }
        }
    };

    closeBtn.addEventListener('click', () => handleLogout());

    addEventTypeBtn.addEventListener('click', () => {
        alert("Add new Event Type functionality to be implemented (e.g., open a modal).");
    });

    previousVersionsBtn.addEventListener('click', () => {
        alert("Previous Versions functionality to be implemented (e.g., fetch and display history).");
    });


    // --- Initialization ---
    setInitialDateTime();
    initializeDropdowns();
    handleClientSelection(); // Initial check in case a client is pre-selected (not in this HTML)
});