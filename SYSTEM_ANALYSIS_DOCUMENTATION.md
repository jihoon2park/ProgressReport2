# Progress Report System - Complete System Analysis

## Overview

This document provides a comprehensive analysis of all 5 major systems in the Progress Report application. Each system is described with its functionality, architecture, and source code structure.

---

## Table of Contents

1. [Progress Note System](#1-progress-note-system)
2. [ROD (Resident of Day) Dashboard System](#2-rod-resident-of-day-dashboard-system)
3. [CIMS (Accident/Task Generation) System](#3-cims-accidenttask-generation-system)
4. [Edenfield Dashboard System](#4-edenfield-dashboard-system)
5. [Mobile Task Dashboard System](#5-mobile-task-dashboard-system)

---

## 1. Progress Note System

### Purpose
A web-based system that allows doctors and staff who cannot easily access remote systems to view and input Progress Notes directly through a web browser. This eliminates the need for VPN access or remote desktop connections.

### Key Features

1. **View Progress Notes**
   - Real-time viewing of all Progress Notes from MANAD Plus
   - Filter by client, date range, event type, care area
   - Search functionality
   - Pagination (50/100 items per page)

2. **Input Progress Notes**
   - Web form for creating new Progress Notes
   - Auto-save functionality
   - Direct integration with MANAD Plus API
   - Support for late entry notes
   - Event type, care area, risk rating selection

3. **Client-Side Caching**
   - IndexedDB for offline viewing
   - LocalStorage for preferences
   - Automatic cache refresh

### Access
- **Route**: `/progress-notes`
- **Template**: `templates/ProgressNoteList.html`
- **Access Control**: All authenticated users
- **Site Selection**: Based on user's allowed sites

### Source Code Structure

#### Backend Route Handler
**Location**: `app.py` lines 1714-1759

```python
@app.route('/progress-notes')
@login_required
def progress_notes():
    """Progress Note viewing and input page"""
    try:
        allowed_sites = session.get('allowed_sites', [])
        site = request.args.get('site', session.get('site', 'Parafield Gardens'))
        
        # Force single site if user has only one site access
        if isinstance(allowed_sites, list) and len(allowed_sites) == 1:
            forced_site = allowed_sites[0]
            if site != forced_site:
                return redirect(url_for('progress_notes', site=forced_site))
            site = forced_site
        
        # Log access
        user_info = {
            "username": current_user.username,
            "display_name": current_user.display_name,
            "role": current_user.role,
            "position": current_user.position
        }
        usage_logger.log_access(user_info)
        
        return render_template('ProgressNoteList.html', site=site)
```

#### Save Progress Note API
**Location**: `app.py` lines 1761-1825

```python
@app.route('/save_progress_note', methods=['POST'])
@login_required
def save_progress_note():
    """Save Progress Note and send to MANAD Plus API"""
    try:
        form_data = request.get_json()
        
        # Convert to MANAD Plus JSON format
        progress_note = create_progress_note_json(form_data)
        
        # Save to prepare_send.json
        if not save_prepare_send_json(progress_note):
            return jsonify({'success': False, 'message': 'Failed to save file.'})
        
        # Send to API
        from api_progressnote import send_progress_note_to_api
        selected_site = session.get('site', 'Parafield Gardens')
        api_success, api_response = send_progress_note_to_api(selected_site)
        
        if api_success:
            # Log success
            usage_logger.log_progress_note(form_data, user_info, success=True)
            return jsonify({
                'success': True, 
                'message': 'Progress Note saved and sent to API successfully.'
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'API send failed: {api_response}'
            })
```

#### Fetch Progress Notes API
**Location**: `app.py` lines 2342-2507

The system provides multiple APIs for fetching Progress Notes:

1. **Standard Fetch API** (`/api/fetch-progress-notes`)
   - Fetches from MANAD Plus directly (DB Direct Access mode)
   - Returns all Progress Notes for selected site and date range
   - Supports filtering by event type, care area, client

2. **Incremental Fetch API** (`/api/fetch-progress-notes-incremental`)
   - Fetches only new/updated notes since last fetch
   - Uses timestamp comparison
   - More efficient for frequent refreshes

#### Frontend JavaScript
**Location**: `static/js/progressNoteList.js`

Key functions:
- `initializeForSite(site)` - Initialize page for selected site
- `fetchAndSaveProgressNotes(eventTypes)` - Fetch notes from API and cache in IndexedDB
- `displayProgressNotes(notes)` - Render notes in table
- `saveProgressNote()` - Submit new note to backend

#### Client-Side Database
**Location**: `static/js/progressNoteDB.js`

**IndexedDB Structure**:
```javascript
class ProgressNoteDB {
    constructor() {
        this.dbName = 'ProgressNotesDB';
        this.version = 1;
        this.storeName = 'progressNotes';
    }
    
    async saveProgressNotes(site, progressNotes) {
        // Save to IndexedDB for offline access
    }
    
    async getProgressNotes(site, options = {}) {
        // Retrieve from IndexedDB
        // Supports filtering, sorting, pagination
    }
}
```

### Data Flow

```
1. User selects site and date range
   ↓
2. Frontend requests Progress Notes from API
   ↓
3. Backend queries MANAD Plus DB directly (or API)
   ↓
4. Data returned to frontend
   ↓
5. Frontend caches in IndexedDB
   ↓
6. Display in table with filtering/search
```

### Key Files
- `app.py` (routes 1714-2507)
- `templates/ProgressNoteList.html`
- `static/js/progressNoteList.js`
- `static/js/progressNoteDB.js`
- `api_progressnote.py` (API client)
- `manad_db_connector.py` (DB direct access)

---

## 2. ROD (Resident of Day) Dashboard System

### Purpose
A dashboard system for ROD (Resident of Day) administrators to monitor and verify whether all required Progress Notes have been entered for each resident on their assigned day. This ensures compliance with daily documentation requirements.

### Key Features

1. **Residence Status Tracking**
   - Daily view of all residences
   - Shows completion status (RN/EN notes, PCA notes)
   - Color-coded status indicators
   - Completion rate calculation

2. **Monthly/Yearly Views**
   - Historical data tracking
   - Trend analysis
   - Statistics by residence

3. **Site-Specific Access**
   - Single-site ROD users (YKROD, WPROD, NROD) see only their site
   - Multi-site ROD users (PGROD, RSROD) see multiple sites
   - General ROD users see all sites

4. **Real-Time Updates**
   - Auto-refresh every few minutes
   - Manual refresh button
   - Live completion status

### Access
- **Route**: `/rod-dashboard`
- **Template**: `templates/RODDashboard.html`
- **Access Control**: ROD users only (ROD, YKROD, PGROD, WPROD, RSROD, NROD)
- **Auto-redirect**: Non-ROD users redirected to Progress Notes

### Source Code Structure

#### Backend Route Handler
**Location**: `app.py` lines 1388-1448

```python
@app.route('/rod-dashboard')
@login_required
def rod_dashboard():
    """ROD Dashboard - Resident of Day monitoring"""
    # Check if user is ROD user
    username_upper = current_user.username.upper()
    if username_upper not in ['ROD', 'YKROD', 'PGROD', 'WPROD', 'RSROD', 'NROD']:
        flash('Access denied. This dashboard is for ROD users only.', 'error')
        return redirect(url_for('progress_notes'))
    
    allowed_sites = session.get('allowed_sites', [])
    site = request.args.get('site', session.get('site', 'Parafield Gardens'))
    
    # Site-specific access control
    sites_info = []
    safe_site_servers = get_safe_site_servers()
    
    # Single-site ROD users
    if username_upper in ['YKROD', 'WPROD', 'NROD']:
        allowed_sites = session.get('allowed_sites', [])
        if allowed_sites:
            site_name = allowed_sites[0]
            sites_info.append({
                'name': site_name,
                'server': safe_site_servers.get(site_name, 'Unknown'),
                'is_selected': True
            })
    # Multi-site ROD users
    elif username_upper in ['PGROD', 'RSROD']:
        allowed_sites = session.get('allowed_sites', [])
        for site_name in allowed_sites:
            if site_name in safe_site_servers:
                sites_info.append({
                    'name': site_name,
                    'server': safe_site_servers[site_name],
                    'is_selected': site_name == site
                })
    # General ROD users see all sites
    else:
        for site_name in safe_site_servers.keys():
            sites_info.append({
                'name': site_name,
                'server': safe_site_servers[site_name],
                'is_selected': site_name == site
            })
    
    return render_template('RODDashboard.html', 
                         site=site, 
                         sites=sites_info,
                         current_user=current_user)
```

#### ROD Residence Status API
**Location**: `app.py` lines 1999-2050

```python
@app.route('/api/rod-residence-status')
@login_required
def get_rod_residence_status():
    """Get Residence of Day status for selected site and date"""
    try:
        site = request.args.get('site', 'Parafield Gardens')
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Query MANAD Plus for Progress Notes on this date
        from manad_db_connector import MANADDBConnector
        connector = MANADDBConnector(site)
        
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all residences
            cursor.execute("""
                SELECT DISTINCT c.CareArea 
                FROM Client c
                WHERE c.IsDeleted = 0
            """)
            residences = [row[0] for row in cursor.fetchall() if row[0]]
            
            rod_status = {}
            
            for residence in residences:
                # Count RN/EN notes
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ProgressNote pn
                    JOIN Client c ON pn.ClientId = c.Id
                    WHERE c.CareArea = ?
                    AND CAST(pn.Date AS DATE) = CAST(? AS DATE)
                    AND pn.IsDeleted = 0
                    AND (pn.NoteType LIKE '%RN%' OR pn.NoteType LIKE '%EN%')
                """, (residence, date_obj))
                rn_en_count = cursor.fetchone()[0]
                
                # Count PCA notes
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ProgressNote pn
                    JOIN Client c ON pn.ClientId = c.Id
                    WHERE c.CareArea = ?
                    AND CAST(pn.Date AS DATE) = CAST(? AS DATE)
                    AND pn.IsDeleted = 0
                    AND pn.NoteType LIKE '%PCA%'
                """, (residence, date_obj))
                pca_count = cursor.fetchone()[0]
                
                # Calculate completion status
                rod_status[residence] = {
                    'rn_en_notes': rn_en_count,
                    'pca_notes': pca_count,
                    'total_notes': rn_en_count + pca_count,
                    'status': 'complete' if (rn_en_count > 0 and pca_count > 0) else 'incomplete'
                }
            
            # Calculate summary statistics
            total_residences = len(residences)
            total_rn_en = sum(s['rn_en_notes'] for s in rod_status.values())
            total_pca = sum(s['pca_notes'] for s in rod_status.values())
            completed_residences = sum(1 for s in rod_status.values() if s['status'] == 'complete')
            
            return jsonify({
                'success': True,
                'rodStatus': rod_status,
                'summary': {
                    'totalResidences': total_residences,
                    'totalRnEnNotes': total_rn_en,
                    'totalPcaNotes': total_pca,
                    'totalNotesCount': total_rn_en + total_pca,
                    'completedResidences': completed_residences,
                    'overallCompletionRate': (completed_residences / total_residences * 100) if total_residences > 0 else 0
                },
                'date': date_str,
                'site': site
            })
    
    except Exception as e:
        logger.error(f"ROD Status API 오류: {e}")
        return jsonify({'error': str(e)}), 500
```

#### ROD Stats API
**Location**: `app.py` lines 2160-2220

Provides monthly/yearly statistics for ROD dashboard:
- Total residences tracked
- Completion rates over time
- Notes count trends
- Site-by-site comparison

### Data Flow

```
1. ROD user logs in and accesses dashboard
   ↓
2. Frontend requests residence status for selected site/date
   ↓
3. Backend queries MANAD Plus for Progress Notes
   ↓
4. Count RN/EN and PCA notes per residence
   ↓
5. Calculate completion status
   ↓
6. Return status data to frontend
   ↓
7. Display in dashboard with color-coded indicators
```

### Key Files
- `app.py` (routes 1388-1448, 1999-2220)
- `templates/RODDashboard.html`
- `static/js/rodDashboard.js` (if exists)

---

## 3. CIMS (Accident/Task Generation) System

### Purpose
When an accident (especially Fall incidents) occurs, this system automatically generates tasks based on predefined policies. It ensures that nurses follow proper protocols and complete all required assessments and documentation at the correct times.

### Key Features

1. **Automatic Task Generation**
   - Detects Fall incidents from MANAD Plus
   - Applies appropriate policy based on Fall type (Witnessed/Unwitnessed)
   - Generates tasks with specific due dates and intervals
   - Supports multiple phases of care

2. **Policy-Based Task Creation**
   - **Witnessed Falls**: Uses `FALL-002-WITNESSED` policy
   - **Unwitnessed Falls**: Uses `FALL-001-UNWITNESSED` policy
   - Each policy defines visit schedule (interval, duration, phases)
   - Common assessment tasks for each visit

3. **Task Management**
   - Task status tracking (pending, completed, overdue)
   - Automatic completion via Progress Note sync
   - Task reassignment
   - Overdue detection and notifications

4. **Mobile Task Dashboard Integration**
   - Real-time task display
   - Site and date filtering
   - Status indicators (OK, Waiting, NOK)
   - Visual alerts for current/overdue tasks

### Access
- **Main Dashboard**: `/mobile_dashboard` (for nurses)
- **Admin Dashboard**: `/integrated_dashboard` (for managers)
- **API Endpoints**: Various CIMS APIs

### Source Code Structure

#### Task Generation Engine
**Location**: `cims_policy_engine.py`

```python
class PolicyEngine:
    """Policy Engine - Automatically generates tasks based on policies"""
    
    def apply_policies_to_incident(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply policies to incident and generate tasks"""
        try:
            # Fall Incident detection
            if incident_data.get('type') == 'Fall':
                logger.info(f"Fall incident detected: {incident_data.get('incident_id')}")
                return self._apply_fall_policy_with_timeline(incident_data)
            
            # Find applicable policies
            applicable_policies = self._find_applicable_policies(incident_data)
            
            if not applicable_policies:
                logger.warning(f"No applicable policies found")
                return []
            
            # Generate tasks from policies
            generated_tasks = []
            for policy in applicable_policies:
                tasks = self._generate_tasks_from_policy(policy, incident_data)
                generated_tasks.extend(tasks)
            
            # Save tasks to database
            saved_tasks = self._save_tasks_to_database(generated_tasks)
            
            logger.info(f"Generated {len(saved_tasks)} tasks for incident {incident_data.get('incident_id')}")
            return saved_tasks
```

#### Automatic Task Generation
**Location**: `services/cims_service.py` lines 100-200

```python
@staticmethod
def auto_generate_fall_tasks(
    incident_db_id: int, 
    incident_date_iso: str, 
    cursor: sqlite3.Cursor
) -> int:
    """Generate Fall incident tasks based on policy"""
    try:
        # Detect Fall type and select appropriate policy
        from services.fall_policy_detector import fall_detector
        
        fall_policy = fall_detector.get_appropriate_policy_for_incident(
            incident_db_id, 
            cursor
        )
        
        if not fall_policy:
            logger.warning(f"No active Fall policy found")
            return 0
        
        policy_id = fall_policy['id']
        visit_schedule = fall_policy['rules'].get('nurse_visit_schedule', [])
        common_tasks = fall_policy['rules'].get('common_assessment_tasks', '')
        
        # Calculate visit times based on policy schedule
        incident_time = datetime.fromisoformat(incident_date_iso)
        phase_start_time = incident_time
        tasks_created = 0
        
        for phase_idx, phase in enumerate(visit_schedule):
            interval = int(phase.get('interval', 30))
            interval_unit = phase.get('interval_unit', 'minutes')
            duration = int(phase.get('duration', 2))
            duration_unit = phase.get('duration_unit', 'hours')
            
            # Convert to minutes
            interval_minutes = (
                interval * 60 if interval_unit == 'hours' else
                interval * 24 * 60 if interval_unit == 'days' else
                interval
            )
            duration_minutes = (
                duration * 60 if duration_unit == 'hours' else
                duration * 24 * 60 if duration_unit == 'days' else
                duration
            )
            
            # Generate tasks for this phase
            number_of_visits = math.ceil(duration_minutes / interval_minutes)
            
            for visit_num in range(number_of_visits):
                visit_time = phase_start_time + timedelta(minutes=visit_num * interval_minutes)
                
                # Create task
                task_id = f"TASK-{incident_id}-P{phase_idx + 1}-V{visit_num + 1}"
                
                cursor.execute("""
                    INSERT INTO cims_tasks (
                        task_id, incident_id, policy_id, task_name,
                        assigned_role, due_date, status, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id,
                    incident_db_id,
                    policy_id,
                    f"Phase {phase_idx + 1} - Visit {visit_num + 1}",
                    'Registered Nurse',
                    visit_time.isoformat(),
                    'pending',
                    'normal'
                ))
                
                tasks_created += 1
            
            # Next phase starts after current phase duration
            phase_start_time = phase_start_time + timedelta(minutes=duration_minutes)
        
        return tasks_created
```

#### Incident Synchronization
**Location**: `manad_plus_integrator.py` lines 744-827

```python
def process_incident(self, incident_data: Dict) -> bool:
    """Process incident from MANAD Plus and generate tasks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if incident already exists
        cursor.execute("""
            SELECT id FROM cims_incidents 
            WHERE manad_incident_id = ?
        """, (incident_data['manad_incident_id'],))
        
        existing = cursor.fetchone()
        
        if not existing:
            # Create new incident
            incident_id = f"I-{incident_data['manad_incident_id']}"
            
            cursor.execute("""
                INSERT INTO cims_incidents (
                    incident_id, manad_incident_id, resident_id, resident_name,
                    incident_type, severity, status, incident_date, 
                    description, reported_by, site, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_id,
                incident_data['manad_incident_id'],
                incident_data['resident_id'],
                resident_name,
                incident_data['incident_type'],
                incident_data['incident_severity_code'],
                'Open',
                incident_data['incident_time'],
                f"Incident imported from MANAD Plus",
                'MANAD_PLUS_SYSTEM',
                site_name,
                datetime.now().isoformat()
            ))
            
            incident_db_id = cursor.lastrowid
            conn.commit()
            
            # Trigger policy engine to generate tasks
            cims_incident_data = {
                'id': incident_db_id,
                'incident_id': incident_id,
                'type': incident_data['incident_type'],
                'severity': incident_data['incident_severity_code'],
                'incident_date': incident_data['incident_time'],
                'resident_id': incident_data['resident_id'],
                'resident_name': resident_name
            }
            
            generated_tasks = self.policy_engine.apply_policies_to_incident(cims_incident_data)
            
            logger.info(f"Incident {incident_id}: {len(generated_tasks)} tasks generated")
        
        return True
```

#### Schedule Batch API
**Location**: `app.py` lines 8168-8371

This API provides all schedule data in a single call for the Mobile Dashboard:

```python
@app.route('/api/cims/schedule-batch/<site>/<date>')
@login_required
def get_schedule_batch(site, date):
    """Batch API - Returns all schedule data in one call"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get Incidents + Tasks in one JOIN query
        cursor.execute("""
            SELECT 
                i.id, i.incident_id, i.incident_type, i.incident_date,
                i.resident_name, i.resident_id, i.description,
                i.severity, i.status, i.location, i.site, i.fall_type,
                t.id as task_db_id, t.task_id, t.task_name, t.due_date, 
                t.status as task_status, t.completed_at
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.site = ? 
            AND DATE(i.incident_date) >= DATE(?)
            AND i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            ORDER BY i.incident_date DESC, t.due_date ASC
        """, (site, five_days_before))
        
        # 2. Group incidents with their tasks
        incidents_map = {}
        for row in rows:
            incident_id = row[0]
            if incident_id not in incidents_map:
                incidents_map[incident_id] = {
                    'id': row[0],
                    'incident_id': row[1],
                    'incident_type': row[2],
                    # ... other fields
                    'tasks': []
                }
            
            # Add task if exists
            if row[12] is not None:  # task_db_id
                incidents_map[incident_id]['tasks'].append({
                    'id': row[12],
                    'task_id': row[13],
                    'task_name': row[14],
                    'due_date': row[15],
                    'status': row[16] or 'pending'
                })
        
        # 3. Get Fall policies
        cursor.execute("""
            SELECT id, policy_id, name, rules_json
            FROM cims_policies
            WHERE is_active = 1 AND policy_id LIKE 'FALL-%'
        """)
        
        fall_policies = {}
        for policy_row in cursor.fetchall():
            policy_code = policy_row[1]  # FALL-001-UNWITNESSED or FALL-002-WITNESSED
            rules = json.loads(policy_row[3])
            fall_policies[policy_code] = {
                'id': policy_row[0],
                'policy_id': policy_code,
                'name': policy_row[2],
                'rules': rules
            }
        
        # 4. Auto-generate tasks if missing
        if len(incidents_map) > 0 and total_tasks == 0 and fall_policy:
            for incident_data in incidents_map.values():
                num_tasks = auto_generate_fall_tasks(
                    incident_data['id'], 
                    incident_data['incident_date'], 
                    cursor
                )
        
        return jsonify({
            'success': True,
            'incidents': list(incidents_map.values()),
            'policies': fall_policies,
            'site': site,
            'date': date
        })
```

#### Progress Note Auto-Sync
**Location**: `app.py` lines 6199-6224

Automatically syncs Progress Notes from MANAD Plus and matches them to tasks:

```python
@app.route('/api/cims/sync-progress-notes', methods=['POST'])
@login_required
def sync_progress_notes():
    """Sync Progress Notes and auto-complete matching tasks"""
    try:
        # Get Fall incidents from last 7 days
        conn = get_db_connection()
        cursor = conn.cursor()
        
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute("""
            SELECT id, incident_id, incident_date, site
            FROM cims_incidents
            WHERE incident_type LIKE '%Fall%'
            AND status IN ('Open', 'Overdue')
            AND incident_date >= ?
        """, (seven_days_ago,))
        
        incidents = cursor.fetchall()
        
        matched_count = 0
        
        for incident in incidents:
            incident_id = incident[0]
            site = incident[3]
            
            # Query MANAD Plus for Post Fall Progress Notes
            from manad_db_connector import MANADDBConnector
            connector = MANADDBConnector(site)
            
            with connector.get_connection() as conn_manad:
                cursor_manad = conn_manad.cursor()
                
                cursor_manad.execute("""
                    SELECT pn.Id, pn.CreatedDate, pn.NoteType
                    FROM ProgressNote pn
                    JOIN Client c ON pn.ClientId = c.Id
                    WHERE pn.NoteType LIKE '%Post Fall%'
                    AND CAST(pn.CreatedDate AS DATE) >= CAST(? AS DATE)
                """, (incident[2],))
                
                notes = cursor_manad.fetchall()
                
                # Get pending tasks for this incident
                cursor.execute("""
                    SELECT id, task_id, due_date, status
                    FROM cims_tasks
                    WHERE incident_id = ? AND status = 'pending'
                    ORDER BY due_date ASC
                """, (incident_id,))
                
                tasks = cursor.fetchall()
                
                # Match notes to tasks (±30 minutes)
                for note in notes:
                    note_time = datetime.fromisoformat(note[1])
                    
                    for task in tasks:
                        task_due = datetime.fromisoformat(task[2])
                        time_diff = abs((note_time - task_due).total_seconds())
                        
                        if time_diff <= 1800:  # 30 minutes
                            # Match found - complete task
                            cursor.execute("""
                                UPDATE cims_tasks
                                SET status = 'completed',
                                    completed_at = ?,
                                    completed_by_user_id = NULL
                                WHERE id = ?
                            """, (note_time.isoformat(), task[0]))
                            
                            matched_count += 1
                            break
        
        conn.commit()
        return jsonify({
            'success': True,
            'matched_tasks': matched_count
        })
```

### Data Flow

```
1. Accident occurs in MANAD Plus
   ↓
2. Background sync detects new incident
   ↓
3. CIMS system creates incident record
   ↓
4. Policy engine analyzes incident type
   ↓
5. Appropriate policy selected (Witnessed/Unwitnessed)
   ↓
6. Tasks generated based on policy schedule
   ↓
7. Tasks saved to CIMS database
   ↓
8. Mobile Dashboard displays tasks
   ↓
9. Nurse completes visit and documents in MANAD Plus
   ↓
10. Progress Note sync matches note to task
   ↓
11. Task automatically marked as completed
```

### Key Files
- `cims_policy_engine.py` - Policy engine
- `services/cims_service.py` - Task generation service
- `services/fall_policy_detector.py` - Fall type detection
- `manad_plus_integrator.py` - Incident sync
- `app.py` (routes 8168-8371, 6199-6224)
- `cims_database_schema.sql` - Database schema

---

## 4. Edenfield Dashboard System

### Purpose
A comprehensive dashboard for Edenfield management to view overall statistics across all 5 sites (Parafield Gardens, Nerrilda, Ramsay, West Park, Yankalilla). Provides high-level KPIs and trends for decision-making.

### Key Features

1. **Company-Wide Statistics**
   - Total residents across all sites
   - Total incidents (Open, Closed, Ambulance, Hospital)
   - Fall incidents count
   - Skin/Wound incidents count
   - Progress Notes count
   - Activity Events count

2. **Site-by-Site Breakdown**
   - Individual site statistics
   - Comparison across sites
   - Site-specific trends

3. **Period Filtering**
   - **Today**: Current day statistics
   - **This Week**: Last 7 days
   - **This Month**: Last 30 days (default)

4. **Activity Type Analysis**
   - Top activity types by count
   - Activity distribution across sites
   - Trend analysis

5. **Visual Dashboards**
   - Charts and graphs
   - Color-coded indicators
   - Summary cards

### Access
- **Route**: `/edenfield-dashboard`
- **Template**: `templates/edenfield_dashboard.html`
- **Access Control**: All authenticated users (typically admin/management)
- **Data Source**: Direct MANAD Plus database queries

### Source Code Structure

#### Backend Route Handler
**Location**: `app.py` lines 1452-1466

```python
@app.route('/edenfield-dashboard')
@login_required
def edenfield_dashboard():
    """Edenfield Dashboard - Company-wide statistics"""
    try:
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        return render_template('edenfield_dashboard.html', 
                             sites=sites,
                             current_user=current_user)
    except Exception as e:
        logger.error(f"Edenfield Dashboard 오류: {e}")
        return render_template('error.html', error=str(e)), 500
```

#### Statistics API
**Location**: `app.py` lines 1469-1711

This comprehensive API queries all 5 sites and aggregates data:

```python
@app.route('/api/edenfield/stats')
@login_required
def get_edenfield_stats():
    """Edenfield Statistics API - Aggregates data from all 5 sites"""
    try:
        # Period parameter
        period = request.args.get('period', 'month')  # today, week, month
        
        if period == 'today':
            days = 0
            date_filter = "CAST(GETDATE() AS DATE)"
        elif period == 'week':
            days = 7
            date_filter = "DATEADD(day, -7, GETDATE())"
        else:  # month (default)
            days = 30
            date_filter = "DATEADD(day, -30, GETDATE())"
        
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        all_stats = []
        
        for site_name in sites:
            try:
                from manad_db_connector import MANADDBConnector
                connector = MANADDBConnector(site_name)
                
                with connector.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    site_stats = {'site': site_name}
                    
                    # 1. Total Residents (active only)
                    cursor.execute("""
                        SELECT COUNT(DISTINCT c.Id) 
                        FROM Client c
                        INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                        WHERE c.IsDeleted = 0 
                        AND cs.IsDeleted = 0
                        AND cs.EndDate IS NULL
                    """)
                    site_stats['total_persons'] = cursor.fetchone()[0]
                    
                    # 2. AdverseEvent (Incident) Statistics
                    if period == 'today':
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND Date >= {date_filter}
                        """)
                    row = cursor.fetchone()
                    site_stats['incidents'] = {
                        'total': row[0] or 0,
                        'open': row[1] or 0,
                        'closed': row[2] or 0,
                        'ambulance': row[3] or 0,
                        'hospital': row[4] or 0
                    }
                    
                    # 3. Fall Incidents Count
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND CAST(ae.Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND ae.Date >= {date_filter}
                        """)
                    site_stats['fall_count'] = cursor.fetchone()[0]
                    
                    # 4. Skin/Wound Incidents Count
                    # ... similar query for skin/wound incidents
                    
                    # 5. Progress Notes Count
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND Date >= {date_filter}
                        """)
                    site_stats['progress_notes_30days'] = cursor.fetchone()[0]
                    
                    # 6. Activity Events Count
                    # ... similar query for activity events
                    
                    # 7. Top Activity Types
                    if period == 'today':
                        cursor.execute("""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND CAST(ae.StartDate AS DATE) = CAST(GETDATE() AS DATE)
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND ae.StartDate >= {date_filter}
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    site_stats['activity_types'] = [
                        {'name': row[0], 'count': row[1]} 
                        for row in cursor.fetchall()
                    ]
                    
                    all_stats.append(site_stats)
                    
            except Exception as site_error:
                logger.warning(f"Site {site_name} 통계 조회 실패: {site_error}")
                all_stats.append({
                    'site': site_name,
                    'error': str(site_error),
                    # ... default values
                })
        
        # Calculate totals across all sites
        totals = {
            'total_persons': sum(s.get('total_persons', 0) for s in all_stats),
            'total_incidents': sum(s.get('incidents', {}).get('total', 0) for s in all_stats),
            'open_incidents': sum(s.get('incidents', {}).get('open', 0) for s in all_stats),
            'closed_incidents': sum(s.get('incidents', {}).get('closed', 0) for s in all_stats),
            'ambulance_calls': sum(s.get('incidents', {}).get('ambulance', 0) for s in all_stats),
            'hospital_admissions': sum(s.get('incidents', {}).get('hospital', 0) for s in all_stats),
            'fall_count': sum(s.get('fall_count', 0) for s in all_stats),
            'progress_notes_30days': sum(s.get('progress_notes_30days', 0) for s in all_stats),
            # ... more totals
        }
        
        # Activity type totals across all sites
        activity_totals = {}
        for site in all_stats:
            for at in site.get('activity_types', []):
                name = at['name']
                activity_totals[name] = activity_totals.get(name, 0) + at['count']
        
        totals['activity_types'] = sorted(
            [{'name': k, 'count': v} for k, v in activity_totals.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]  # Top 10
        
        return jsonify({
            'success': True,
            'period': period,
            'sites': all_stats,
            'totals': totals
        })
    
    except Exception as e:
        logger.error(f"Edenfield Stats 오류: {e}")
        return jsonify({'error': str(e)}), 500
```

### Data Flow

```
1. User accesses Edenfield Dashboard
   ↓
2. Frontend requests statistics for selected period
   ↓
3. Backend queries each of 5 sites in parallel
   ↓
4. For each site:
   - Query active residents
   - Query incidents (with filters)
   - Query Fall incidents
   - Query Skin/Wound incidents
   - Query Progress Notes
   - Query Activity Events
   - Query top Activity Types
   ↓
5. Aggregate data across all sites
   ↓
6. Calculate totals and percentages
   ↓
7. Return combined statistics
   ↓
8. Frontend displays in dashboard with charts
```

### Key Files
- `app.py` (routes 1452-1711)
- `templates/edenfield_dashboard.html`
- `manad_db_connector.py` (for site connections)

---

## 5. Mobile Task Dashboard System

### Purpose
A mobile-optimized dashboard for nurses to view and manage their visit schedules for Fall incidents. Provides real-time task status, visual indicators, and automatic updates.

**Note**: This system has been fully documented in `MOBILE_TASK_DASHBOARD_DOCUMENTATION.md`. Please refer to that document for complete details.

### Brief Summary
- **Route**: `/mobile_dashboard`
- **Template**: `templates/mobile_task_dashboard.html`
- **Access**: Nurses, carers, clinical managers
- **Key Features**:
  - Site and date filtering
  - Real-time schedule display
  - Task status indicators (OK, Waiting, NOK)
  - Current task highlighting
  - Auto-refresh every 5 minutes
  - LocalStorage caching
  - Incident details modal

---

## System Integration

### Data Flow Between Systems

```
MANAD Plus Database (SQL Server)
    ├── Progress Note System
    │   ├── Reads Progress Notes
    │   └── Writes new Progress Notes
    │
    ├── ROD Dashboard
    │   └── Reads Progress Notes for status verification
    │
    ├── CIMS System
    │   ├── Reads Fall Incidents
    │   ├── Writes Tasks to SQLite
    │   └── Syncs Progress Notes for task completion
    │
    └── Edenfield Dashboard
        └── Reads aggregated statistics from all sites

SQLite Database (Local)
    ├── CIMS System
    │   ├── Stores Incidents (synced from MANAD)
    │   ├── Stores Tasks (generated from policies)
    │   └── Stores Policies
    │
    └── Mobile Task Dashboard
        └── Reads Tasks and Incidents
```

### Authentication Flow

All systems use the same authentication mechanism:
- **User Management**: `config_users.py`
- **Session Management**: Flask-Login
- **Role-Based Access**: Different roles have different access levels

### Common Components

1. **Database Access**
   - `manad_db_connector.py` - Direct SQL Server access
   - `get_db_connection()` - SQLite connection

2. **User Management**
   - `config_users.py` - User credentials
   - `models.py` - User model

3. **Logging**
   - `usage_logger.py` - Access and activity logging
   - Application logs in `logs/` directory

---

## Summary

The Progress Report system consists of 5 major subsystems:

1. **Progress Note System** - Web-based note viewing and input for remote users
2. **ROD Dashboard** - Resident of Day compliance monitoring
3. **CIMS System** - Automatic task generation for accidents
4. **Edenfield Dashboard** - Company-wide statistics and KPIs
5. **Mobile Task Dashboard** - Nurse visit schedule management

Each system serves a specific purpose while sharing common infrastructure for authentication, database access, and logging. The systems integrate seamlessly to provide a comprehensive healthcare management platform.

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Status**: Complete System Analysis
