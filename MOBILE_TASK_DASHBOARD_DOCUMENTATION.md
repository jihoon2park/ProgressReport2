# Mobile Task Dashboard - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Site Structure](#site-structure)
3. [Technology Stack](#technology-stack)
4. [Features & Functionality](#features--functionality)
5. [Authentication & User Management](#authentication--user-management)
6. [Database Schema](#database-schema)
7. [API Endpoints](#api-endpoints)
8. [Deployment & Configuration](#deployment--configuration)
9. [Handover Information](#handover-information)

---

## Overview

The **Mobile Task Dashboard** (`mobile_task_dashboard.html`) is a mobile-optimized web application designed for healthcare staff to view and manage nurse visit schedules for Fall incidents in aged care facilities. It provides real-time task scheduling, status tracking, and incident management capabilities optimized for tablet and mobile devices.

### Key Characteristics
- **Mobile-First Design**: Responsive layout optimized for tablets and smartphones
- **Real-Time Updates**: Auto-refreshes every 5 minutes with manual refresh capability
- **Local Caching**: Browser localStorage for offline viewing (5-minute TTL)
- **Task Status Tracking**: Visual indicators for pending, completed, and overdue tasks
- **Site-Specific Filtering**: View schedules for specific aged care facilities

---

## Site Structure

### File Organization

```
ProgressReport/
├── templates/
│   └── mobile_task_dashboard.html    # Main dashboard page (2,062 lines)
├── app.py                            # Flask backend routes
├── cims_api_endpoints.py             # CIMS API endpoints
├── cims_cache_api.py                 # Caching API endpoints
├── cims_policy_engine.py             # Policy engine for task generation
├── manad_db_connector.py             # MANAD database connector
├── models.py                         # Database models
├── config_users.py                   # User authentication configuration
├── requirements.txt                  # Python dependencies
└── cims_database_schema.sql          # Database schema
```

### Route Structure

**Backend Route**: `/mobile_dashboard`
- **Method**: GET
- **Authentication**: Required (`@login_required`)
- **Permission**: Users with `can_complete_tasks()` or `is_admin()`
- **Template**: `mobile_task_dashboard.html`

**API Endpoints Used**:
- `/api/cims/schedule-batch/<site>/<date>` - Batch schedule retrieval
- `/api/cims/policies` - Policy information
- `/integrated_dashboard` - Return to main dashboard

### Page Layout Structure

```html
<div class="page-container">
  ├── <div class="mobile-header">        # Fixed header with title and current time
  ├── <div class="filter-bar">            # Site and date filters
  ├── <div class="timetable-container">  # Main schedule table
  │   ├── <div class="timetable-header">
  │   └── <div class="schedule-table-wrapper">
  │       └── <table class="schedule-table">
  └── <div id="incidentModal">           # Incident details modal
</div>
```

---

## Technology Stack

### Backend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11+ | Core programming language |
| **Flask** | 3.1.1 | Web application framework |
| **Flask-Login** | 0.6.3 | User session management |
| **Flask-SQLAlchemy** | 3.1.1 | Database ORM (optional) |
| **SQLite** | Latest | Local database for CIMS data |
| **pyodbc/pymssql** | Latest | SQL Server connectivity |
| **requests** | 2.32.3 | HTTP client for API calls |
| **python-dotenv** | 1.1.0 | Environment configuration |
| **gunicorn** | 21.2.0 | WSGI HTTP server (Linux) |
| **schedule** | 1.2.0 | Background task scheduling |
| **firebase-admin** | 6.4.0 | Push notification service |

### Frontend Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **HTML5** | Latest | Markup language |
| **CSS3** | Latest | Styling with custom properties |
| **JavaScript (ES6+)** | Latest | Client-side logic |
| **Bootstrap** | 5.1.3 | CSS framework (CDN) |
| **Font Awesome** | 6.0.0 | Icon library (CDN) |
| **LocalStorage API** | Native | Client-side caching |
| **Fetch API** | Native | HTTP requests |

### External Services

- **MANAD Plus Database**: Direct SQL Server access for real-time incident data
- **Firebase Cloud Messaging (FCM)**: Push notifications (optional)
- **CDN Services**: Bootstrap and Font Awesome via jsDelivr

### Database Systems

1. **SQLite** (`progress_report.db`)
   - CIMS incidents, tasks, policies
   - User sessions and settings
   - FCM tokens (synced with SQLite)

2. **SQL Server** (MANAD Plus)
   - Direct read-only access via `manad_db_connector.py`
   - Real-time incident and resident data
   - Primary data source for schedule generation

---

## Features & Functionality

### 1. Site and Date Filtering

**Site Selection**:
- Available sites: Parafield Gardens, Nerrilda, Ramsay, West Park, Yankalilla
- Dropdown selector with site icons
- Selected site saved in localStorage

**Date Selection**:
- Range: 4 days ago to 2 days later
- Default: Today
- Format: "Today (Mon, 15 Jan)" / "Tomorrow (Tue, 16 Jan)" / etc.
- Australian date format (en-AU)

### 2. Schedule Display

**Table Columns**:
1. **Time** - Visit time (HH:MM format, 24-hour)
2. **Patient** - Resident name
3. **Room** - Location/room number
4. **Type** - Incident type (Fall) with badge (Witnessed/Unwitnessed/Unknown)
5. **Occurred** - Original incident date and time
6. **INC #** - Incident ID (clickable for details)
7. **Tasks** - Assessment tasks (truncated to 80 chars)
8. **Phase** - Visit phase badge (P1, P2, P3, etc.)
9. **Status** - Task status badge:
   - **OK** (green) - Completed
   - **Waiting** (yellow) - Pending
   - **NOK** (red) - Overdue

**Color Coding**:
- Each incident assigned one of 6 color schemes
- Overdue tasks highlighted with red background
- Current task (next 1 hour) with blinking animation and red border
- "▶ NEXT" indicator for upcoming tasks

### 3. Current Time Display

- Large digital clock in header
- Updates every second
- Format: HH:MM:SS (24-hour)
- Shows last update time below clock

### 4. Task Status Logic

**Status Determination**:
- **OK**: Task status is "completed"
- **NOK**: Current time > visit time AND task not completed
- **Waiting**: Current time < visit time

**Current Task Detection**:
- Visit time is within next 60 minutes
- Task is not completed
- Selected date is today
- Visual: Blinking animation, red border, "▶ NEXT" badge

### 5. Caching System

**LocalStorage Caching**:
- Cache key format: `visit_schedule_{site}_{date}`
- TTL: 5 minutes (300,000 ms)
- Cache structure:
  ```json
  {
    "schedule": {...},
    "timestamp": 1234567890,
    "site": "Parafield Gardens",
    "date": "2026-01-15"
  }
  ```

**Cache Management**:
- Automatic cache validation before API calls
- Manual cache clear button
- Old cache cleanup when localStorage quota exceeded
- Cache miss triggers API call

### 6. Auto-Refresh

- **Interval**: 5 minutes (300,000 ms)
- **Indicator**: Bottom-right corner notification
- **Behavior**: Only refreshes if site and date selected
- **Manual Refresh**: "Clear Cache" button forces fresh data

### 7. Incident Details Modal

**Trigger**: Click on Incident ID column
**Content**:
- Incident ID
- Patient name
- Occurred date/time
- Location
- Incident type with Fall type badge
- Description
- Assessment tasks

**Features**:
- Auto-closes after 5 seconds
- Manual close button
- Click outside to close
- Smooth animations

### 8. Auto-Scroll to Next Task

- Automatically scrolls to next pending task after schedule loads
- Only active when viewing today's date
- Smooth scroll animation with visual highlight
- Button in bottom-right for manual scroll

### 9. Responsive Design

**Breakpoints**:
- **Mobile** (< 768px): Compact layout, smaller fonts
- **Tablet** (768px - 1024px): Medium layout
- **Desktop** (> 1024px): Full layout

**Optimizations**:
- Touch-friendly buttons (min 44px)
- Scrollable table with sticky header
- Fixed header and filters
- Smooth animations with CSS transforms

### 10. Policy-Based Visit Generation

**Fall Type-Based Policy Selection**:
- **Witnessed Falls**: Uses `FALL-002-WITNESSED` policy
- **Unwitnessed/Unknown Falls**: Uses `FALL-001-UNWITNESSED` policy

**Visit Schedule Generation**:
- Based on policy `nurse_visit_schedule` rules
- Each phase defines interval and duration
- Tasks with `due_date` take priority over policy schedule
- If no tasks exist, generates expected visits from policy

**Example Policy Structure**:
```json
{
  "nurse_visit_schedule": [
    {
      "interval": 30,
      "interval_unit": "minutes",
      "duration": 2,
      "duration_unit": "hours"
    }
  ],
  "common_assessment_tasks": "Check vital signs, assess for injuries..."
}
```

---

## Authentication & User Management

### User Authentication System

**Authentication Method**: Flask-Login with session-based authentication
**Password Hashing**: SHA-256
**Session Management**: Non-persistent (expires on browser close)

### User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| **admin** | System administrator | Full access |
| **site_admin** | Site administrator | Site-specific access |
| **doctor** | General practitioner | View and review |
| **clinical_manager** | Clinical manager | View and manage |
| **nurse** | Registered nurse | View and complete tasks |
| **carer** | Care staff | View and complete tasks |

### User Accounts

**Configuration File**: `config_users.py`

**Admin Accounts**:
- `admin` / `password123` - Full system access
- `ROD` / `rod1234!` - Admin access
- `operation` / `password123` - Operations manager

**Site Admin Accounts**:
- `PGROD` / `pgpassword` - Parafield Gardens admin
- `WPROD` / `wppassword` - West Park admin
- `RSROD` / `rspassword` - Ramsay admin
- `NROD` / `nrpassword` - Nerrilda admin
- `YKROD` / `ykpassword` - Yankalilla admin

**Doctor Accounts**:
- `ChanduraVadeen` / `Chandura123!` - All sites
- `PaulVaska` / `Paul123!` - All sites
- `walgampola` / `1Prasanta` - Parafield Gardens
- `LawJohn` / `John123!` - Yankalilla
- `LauKin` / `Kin456@` - Yankalilla
- `WorleyPaul` / `Paul789#` - Yankalilla
- `HorKC` / `KC234$` - Yankalilla
- `SallehAudrey` / `Audrey567%` - Yankalilla
- `LiNini` / `Nini890@` - Yankalilla
- `KiranantawatSoravee` / `Soravee345&` - Yankalilla
- `BansalShiveta` / `Shiveta678*` - Yankalilla
- `BehanStephen` / `Stephen901?` - Yankalilla
- `philipd` / `philip1234!` - West Park

**Login Endpoint**: `/login`
- **Method**: POST
- **Parameters**: `username`, `password`, `site`
- **Response**: Redirects to user's landing page or dashboard

**Session Details**:
- Session stored in Flask session (server-side)
- Session ID stored in cookie
- Session timeout based on role (default: browser close)
- Site selection stored in session

### Access Control

**Mobile Dashboard Access**:
```python
if not current_user.can_complete_tasks() and not current_user.is_admin():
    flash('Access denied', 'error')
    return redirect(url_for('rod_dashboard'))
```

**API Endpoint Protection**:
```python
@app.route('/api/cims/schedule-batch/<site>/<date>')
@login_required
def get_schedule_batch(site, date):
    if not (current_user.is_admin() or 
            current_user.role in ['clinical_manager', 'nurse', 'carer']):
        return jsonify({'error': 'Access denied'}), 403
```

---

## Database Schema

### CIMS Tables

#### 1. `cims_policies`
Policy definitions for incident management.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| policy_id | VARCHAR(50) | Unique policy ID (e.g., "FALL-001-UNWITNESSED") |
| name | VARCHAR(200) | Policy name |
| description | TEXT | Policy description |
| version | VARCHAR(20) | Policy version |
| effective_date | TIMESTAMP | When policy becomes active |
| expiry_date | TIMESTAMP | When policy expires |
| rules_json | TEXT | JSON policy rules |
| is_active | BOOLEAN | Active status |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

#### 2. `cims_incidents`
Fall incidents from MANAD Plus system.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| incident_id | VARCHAR(100) | Unique incident ID |
| manad_incident_id | VARCHAR(100) | MANAD Plus incident ID |
| resident_id | INTEGER | Resident ID |
| resident_name | VARCHAR(200) | Resident name |
| incident_type | VARCHAR(100) | Incident type (e.g., "Fall") |
| fall_type | VARCHAR(50) | Fall type: "witnessed", "unwitnessed", "unknown" |
| severity | VARCHAR(50) | Severity rating |
| status | VARCHAR(50) | Status: "Open", "Overdue", "Closed" |
| incident_date | TIMESTAMP | When incident occurred |
| location | VARCHAR(200) | Location/room |
| description | TEXT | Incident description |
| site | VARCHAR(100) | Site name |
| policy_applied | INTEGER | Applied policy ID |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

#### 3. `cims_tasks`
Tasks generated from policies for each incident.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| task_id | VARCHAR(100) | Unique task ID (e.g., "TASK-INC423-P3-V10") |
| incident_id | INTEGER | Foreign key to cims_incidents |
| policy_id | INTEGER | Foreign key to cims_policies |
| task_name | VARCHAR(300) | Task name |
| description | TEXT | Task description |
| assigned_role | VARCHAR(100) | Assigned role |
| assigned_user_id | INTEGER | Specific user assignment (optional) |
| due_date | TIMESTAMP | When task is due |
| priority | VARCHAR(20) | Priority level |
| status | VARCHAR(50) | Status: "pending", "completed", "overdue" |
| completed_by_user_id | INTEGER | User who completed task |
| completed_at | TIMESTAMP | Completion timestamp |
| documentation_required | BOOLEAN | Whether documentation is required |
| note_type | VARCHAR(100) | Type of note required |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

**Task ID Format**: `TASK-{INCIDENT_ID}-P{PHASE}-V{VISIT_NUMBER}`
- Example: `TASK-INC423-P3-V10` = Task for Incident 423, Phase 3, Visit 10

#### 4. Additional Tables
- `cims_progress_notes` - Progress notes for tasks
- `cims_audit_logs` - Audit trail
- `cims_notifications` - Notification queue
- `users` - User accounts (optional, if using DB-based auth)

### Database Connection

**SQLite Connection**:
```python
def get_db_connection(read_only: bool = False):
    db_path = 'progress_report.db'
    conn = sqlite3.connect(db_path)
    if read_only:
        conn.execute('PRAGMA journal_mode=WAL')
    return conn
```

**SQL Server Connection** (MANAD Plus):
- Uses `manad_db_connector.py`
- Direct read-only access
- Connection pooling
- Site-specific connection strings

---

## API Endpoints

### 1. Schedule Batch API

**Endpoint**: `/api/cims/schedule-batch/<site>/<date>`

**Method**: GET

**Authentication**: Required (`@login_required`)

**Parameters**:
- `site` (path): Site name (e.g., "Parafield Gardens")
- `date` (path): Date in YYYY-MM-DD format

**Response**:
```json
{
  "success": true,
  "incidents": [
    {
      "id": 123,
      "incident_id": "INC-423",
      "incident_type": "Fall",
      "fall_type": "witnessed",
      "resident_name": "John Doe",
      "location": "Room 101",
      "incident_date": "2026-01-15T08:00:00",
      "description": "Fall in bathroom",
      "site": "Parafield Gardens",
      "tasks": [
        {
          "task_id": "TASK-INC423-P1-V1",
          "due_date": "2026-01-15T08:30:00",
          "status": "pending",
          "task_name": "Initial Response Check"
        }
      ]
    }
  ],
  "policies": {
    "FALL-001-UNWITNESSED": {
      "policy_id": "FALL-001-UNWITNESSED",
      "rules": {
        "nurse_visit_schedule": [...],
        "common_assessment_tasks": "..."
      }
    }
  },
  "policy": {...},  // Backwards compatibility
  "site": "Parafield Gardens",
  "date": "2026-01-15",
  "auto_generated": false,
  "timestamp": "2026-01-15T12:00:00"
}
```

**Error Response**:
```json
{
  "error": "Access denied",
  "success": false
}
```

**Status Codes**:
- `200`: Success
- `403`: Access denied
- `500`: Internal server error

### 2. Policies API

**Endpoint**: `/api/cims/policies`

**Method**: GET

**Authentication**: Required

**Response**: Array of policy objects

### 3. Incident Tasks API

**Endpoint**: `/api/cims/incident/<incident_id>/tasks`

**Method**: GET

**Authentication**: Required

**Response**: Array of task objects for specific incident

---

## Deployment & Configuration

### Environment Setup

**Required Environment Variables** (`.env` file):

```env
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///progress_report.db

# MANAD Database Connections (if using direct DB access)
MANAD_DB_SERVER_PARAFIELD_GARDENS=server_name\instance
MANAD_DB_NAME_PARAFIELD_GARDENS=MANAD_Plus
MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS=true

# Site Configuration (in site_config.json)
{
  "Parafield Gardens": {
    "server": "efsvr02\\sqlexpress",
    "database": "MANAD_Plus",
    "use_windows_auth": true
  },
  "Nerrilda": {
    "server": "192.168.21.12",
    "database": "MANAD_Plus",
    "use_windows_auth": false,
    "username": "db_user",
    "password": "db_password"
  }
}
```

### Installation Steps

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install SQL Server Drivers** (Windows):
   ```bash
   # ODBC Driver 17 for SQL Server required
   # Download from Microsoft website
   pip install pyodbc
   ```

3. **Initialize Database**:
   ```bash
   python init_database.py
   # or
   sqlite3 progress_report.db < cims_database_schema.sql
   ```

4. **Configure Users**:
   - Edit `config_users.py` to add/modify users
   - Or use admin interface to manage users

5. **Start Application**:
   ```bash
   # Development
   python app.py
   
   # Production (Windows IIS)
   # Deploy using web.config and IIS configuration
   
   # Production (Linux)
   gunicorn -c gunicorn.conf.py app:app
   ```

### Configuration Files

**Site Configuration**: `data/api_keys/site_config.json`
```json
{
  "Parafield Gardens": {
    "server": "efsvr02\\sqlexpress",
    "database": "MANAD_Plus",
    "use_windows_auth": true
  }
}
```

**User Configuration**: `config_users.py`
- Python dictionary with user credentials
- SHA-256 password hashing
- Role-based access control

### Production Deployment

**Windows IIS Deployment**:
1. Install IIS with URL Rewrite module
2. Install Python and wfastcgi
3. Configure application pool (Python 3.11)
4. Deploy using `web.config`
5. Set environment variables in IIS

**Linux Deployment**:
1. Install Gunicorn and Nginx
2. Configure Nginx as reverse proxy
3. Use systemd service for Gunicorn
4. Set up SSL certificates (Let's Encrypt)

---

## Handover Information

### Important Files to Know

1. **Frontend**: `templates/mobile_task_dashboard.html`
   - 2,062 lines of HTML/CSS/JavaScript
   - Single-page application
   - Client-side caching logic

2. **Backend Routes**: `app.py` (lines 8488-8535)
   - `/mobile_dashboard` route handler
   - Permission checking
   - Initial state validation

3. **API Endpoint**: `app.py` (lines 8168-8371)
   - `/api/cims/schedule-batch/<site>/<date>`
   - Batch data retrieval
   - Policy selection logic

4. **Database Schema**: `cims_database_schema.sql`
   - Table definitions
   - Indexes
   - Sample policy data

5. **User Management**: `config_users.py`
   - User credentials
   - Role definitions
   - Authentication functions

### Common Issues & Solutions

**Issue**: Schedule not loading
- **Check**: Site and date selected
- **Check**: User has correct permissions
- **Check**: Database connection (SQLite and SQL Server)
- **Check**: Policies exist and are active

**Issue**: Tasks not appearing
- **Check**: Tasks exist in `cims_tasks` table
- **Check**: Policy is correctly applied to incident
- **Check**: Task `due_date` matches selected date
- **Solution**: Run Force Synchronization in Settings

**Issue**: Cache not clearing
- **Solution**: Use "Clear Cache" button
- **Check**: Browser localStorage quota
- **Solution**: Manually clear browser localStorage

**Issue**: Auto-refresh not working
- **Check**: Site and date are selected
- **Check**: Browser tab is active
- **Solution**: Manual refresh using "Clear Cache" button

### Maintenance Tasks

**Regular Maintenance**:
1. **Database Cleanup**:
   - Archive old incidents (older than 1 year)
   - Clean up completed tasks
   - Optimize SQLite database

2. **Cache Management**:
   - Monitor localStorage usage
   - Adjust cache TTL if needed
   - Clear old caches periodically

3. **Policy Updates**:
   - Review policy effectiveness
   - Update visit schedules as needed
   - Test policy changes in dev environment

4. **User Management**:
   - Review user access logs
   - Update passwords periodically
   - Remove inactive users

**Scheduled Tasks**:
- Background sync with MANAD Plus (if using API mode)
- Task status updates (overdue detection)
- Notification sending (if FCM enabled)

### Testing Checklist

**Functional Testing**:
- [ ] Login with different user roles
- [ ] Select different sites
- [ ] Select different dates (past, today, future)
- [ ] View schedule table
- [ ] Click incident ID to view details
- [ ] Test cache functionality (clear cache button)
- [ ] Test auto-refresh (wait 5 minutes)
- [ ] Test auto-scroll to next task
- [ ] Test on mobile/tablet devices
- [ ] Test on different browsers

**Performance Testing**:
- [ ] Load time with many incidents
- [ ] Cache hit/miss behavior
- [ ] Memory usage with long sessions
- [ ] Network requests (should be minimal with caching)

**Security Testing**:
- [ ] Access control (unauthorized users)
- [ ] Session timeout
- [ ] XSS prevention (input sanitization)
- [ ] SQL injection prevention (parameterized queries)

### Backup & Recovery

**Database Backup**:
```bash
# SQLite backup
sqlite3 progress_report.db ".backup backup.db"

# SQL Server backup (MANAD Plus)
# Use SQL Server Management Studio or backup scripts
```

**Configuration Backup**:
- `config_users.py` - User credentials
- `data/api_keys/site_config.json` - Site configurations
- `.env` - Environment variables
- Database schema files

**Recovery Steps**:
1. Restore database from backup
2. Verify configuration files
3. Test login and permissions
4. Verify database connections
5. Test schedule loading

### Contact Information

**System Information**:
- **Project Name**: ProgressReport
- **Location**: `C:\Users\it.support\PycharmProjects\ProgressReport`
- **Primary Language**: Python 3.11+
- **Framework**: Flask 3.1.1
- **Database**: SQLite + SQL Server (MANAD Plus)

**Key Dependencies**:
- See `requirements.txt` for complete list
- Critical: Flask, Flask-Login, pyodbc/pymssql

### Future Enhancements

**Potential Improvements**:
1. Task completion directly from dashboard
2. Real-time notifications via WebSockets
3. Offline mode with IndexedDB
4. Export schedule to PDF/Excel
5. Multi-language support
6. Advanced filtering (by nurse, status, etc.)
7. Calendar view option
8. Task reassignment functionality

---

## Summary

The Mobile Task Dashboard is a comprehensive solution for managing nurse visit schedules for Fall incidents in aged care facilities. It provides:

- **Real-time schedule viewing** with automatic updates
- **Efficient caching** for offline access
- **Mobile-optimized interface** for tablets and smartphones
- **Role-based access control** with multiple user types
- **Policy-driven task generation** based on Fall type
- **Visual status indicators** for task completion

The system integrates seamlessly with the MANAD Plus database and provides a user-friendly interface for healthcare staff to manage their daily visit schedules efficiently.

---

**Document Version**: 1.0  
**Last Updated**: January 2026  
**Author**: System Documentation  
**Status**: Complete
