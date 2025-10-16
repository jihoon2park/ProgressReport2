# CIMS Database Schema Documentation

**Clinical Incident Management System (CIMS)**  
**Version:** 1.0  
**Last Updated:** 2025-10-16

---

## 📊 Database Overview

- **Database Type:** SQLite3
- **Database File:** `progress_report.db`
- **Total Tables:** 17 (excluding backups and internal tables)
- **Total Records:** 1,300+

---

## 🗂️ Table Categories

### 1. Core CIMS Tables
- `cims_incidents` - Incident records
- `cims_tasks` - Task/Visit schedules
- `cims_policies` - Clinical policies
- `cims_progress_notes` - Progress notes
- `cims_notifications` - User notifications
- `cims_task_assignments` - Task assignments
- `cims_audit_logs` - Audit trail
- `cims_dashboard_kpi_cache` - KPI cache

### 2. External Data Cache
- `clients_cache` - Resident data from MANAD Plus
- `sites` - Site configuration
- `sync_status` - Synchronization status

### 3. User Management
- `users` - User accounts
- `access_logs` - User access logs
- `fcm_tokens` - Firebase Cloud Messaging tokens
- `progress_note_logs` - Progress note activity logs

### 4. Reference Data
- `care_areas` - Care area definitions
- `event_types` - Incident event types
- `system_settings` - System configuration

---

## 📋 Detailed Schema

### 1. `cims_incidents` (182 rows) 🚨

**Purpose:** Central incident registry synced from MANAD Plus

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `incident_id` | VARCHAR(100) | YES | - | **Unique incident ID** (e.g., INC-408) |
| `manad_incident_id` | VARCHAR(100) | NO | - | Original MANAD Plus incident ID |
| `resident_id` | INTEGER | YES | - | Resident identifier |
| `resident_name` | VARCHAR(200) | YES | - | Resident full name |
| `incident_type` | VARCHAR(100) | YES | - | Fall, Wound/Skin, Medication, Behaviour, etc. |
| `severity` | VARCHAR(50) | NO | - | Severity rating (e.g., "3 - Mild") |
| `status` | VARCHAR(50) | NO | - | Open, Overdue, Closed |
| `incident_date` | TIMESTAMP | YES | - | Incident occurrence date/time |
| `location` | VARCHAR(200) | NO | - | Room, wing, department |
| `description` | TEXT | NO | - | Detailed incident description |
| `initial_actions_taken` | TEXT | NO | - | Actions taken immediately |
| `witnesses` | TEXT | NO | - | Witness information |
| `reported_by` | INTEGER | NO | - | User ID who reported (0 = system) |
| `reported_by_name` | VARCHAR(200) | NO | - | Reporter's name |
| `site` | VARCHAR(100) | YES | - | Site name (Parafield Gardens, etc.) |
| `policy_applied` | INTEGER | NO | - | Policy ID applied to this incident |
| `created_at` | TIMESTAMP | NO | - | Record creation time |
| `updated_at` | TIMESTAMP | NO | - | Last update time |

**Indexes:**
- UNIQUE: `incident_id`
- INDEX: `manad_incident_id`
- INDEX: `site`, `status`, `incident_date`

---

### 2. `cims_tasks` (828 rows) ✅

**Purpose:** Nurse visit schedules and task assignments (auto-generated from policies)

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `task_id` | VARCHAR(100) | YES | - | **Unique task ID** (e.g., TASK-INC253-P1-V1) |
| `incident_id` | INTEGER | YES | - | **Foreign Key → cims_incidents.id** |
| `policy_id` | INTEGER | YES | - | **Foreign Key → cims_policies.id** |
| `task_name` | VARCHAR(300) | YES | - | Task description |
| `description` | TEXT | NO | - | Detailed instructions |
| `assigned_role` | VARCHAR(100) | YES | - | Registered Nurse, All Staff, Clinical Manager |
| `assigned_user_id` | INTEGER | NO | - | Specific user assignment |
| `due_date` | TIMESTAMP | YES | - | **Scheduled visit time** |
| `priority` | VARCHAR(20) | NO | 'normal' | urgent, high, normal, low |
| `status` | VARCHAR(50) | NO | 'pending' | pending, in_progress, completed, overdue |
| `completed_by_user_id` | INTEGER | NO | - | User who completed the task |
| `completed_at` | TIMESTAMP | NO | - | Completion timestamp |
| `documentation_required` | BOOLEAN | NO | 1 | Requires progress note |
| `note_type` | VARCHAR(100) | NO | - | Dynamic Form - Post Fall Assessment |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update time |

**Foreign Keys:**
- `incident_id` → `cims_incidents(id)`
- `policy_id` → `cims_policies(id)`
- `assigned_user_id` → `users(id)`
- `completed_by_user_id` → `users(id)`

**Indexes:**
- UNIQUE: `task_id`
- INDEX: `incident_id`, `due_date`, `status`

**Task Generation Logic:**
- **Fall incidents** → 12 tasks auto-generated (based on Fall policy)
  - Phase 1: Every 30 min for 2 hours → 4 visits
  - Phase 2: Every 1 hour for 2 hours → 2 visits
  - Phase 3: Every 4 hours for 24 hours → 6 visits

---

### 3. `cims_policies` (1 row) 📜

**Purpose:** Clinical policies and workflow rules

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `policy_id` | VARCHAR(50) | YES | - | **Unique policy ID** |
| `name` | VARCHAR(200) | YES | - | Policy name (e.g., Fall Management Policy V3) |
| `description` | TEXT | NO | - | Policy description |
| `version` | VARCHAR(20) | YES | - | Version number |
| `effective_date` | TIMESTAMP | YES | - | When policy becomes active |
| `expiry_date` | TIMESTAMP | NO | - | Expiration date (NULL = no expiry) |
| `rules_json` | TEXT | YES | - | **Policy rules in JSON format** |
| `is_active` | BOOLEAN | NO | 1 | Active flag |
| `created_by` | INTEGER | NO | - | User ID who created |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update time |

**Foreign Keys:**
- `created_by` → `users(id)`

**rules_json Structure:**
```json
{
  "incident_association": {
    "incident_type": "Fall"
  },
  "nurse_visit_schedule": [
    {
      "interval": 30,
      "interval_unit": "minutes",
      "duration": 2,
      "duration_unit": "hours"
    },
    {
      "interval": 1,
      "interval_unit": "hours",
      "duration": 2,
      "duration_unit": "hours"
    },
    {
      "interval": 4,
      "interval_unit": "hours",
      "duration": 24,
      "duration_unit": "hours"
    }
  ],
  "common_assessment_tasks": "Monitor for any change in level of consciousness...",
  "common_conditions": "...",
  "common_instructions": "..."
}
```

---

### 4. `cims_progress_notes` (0 rows) 📝

**Purpose:** Progress notes linked to tasks/incidents

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `note_id` | VARCHAR(100) | YES | - | **Unique note ID** |
| `incident_id` | INTEGER | YES | - | **Foreign Key → cims_incidents.id** |
| `task_id` | INTEGER | NO | - | **Foreign Key → cims_tasks.id** (NULL if general note) |
| `author_id` | INTEGER | YES | - | **Foreign Key → users.id** |
| `content` | TEXT | YES | - | Note content |
| `note_type` | VARCHAR(100) | NO | - | Type of note |
| `vitals_data` | TEXT | NO | - | Vital signs (JSON) |
| `assessment_data` | TEXT | NO | - | Assessment data (JSON) |
| `attachments` | TEXT | NO | - | File attachments (JSON) |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Note creation time |
| `updated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update time |

**Foreign Keys:**
- `incident_id` → `cims_incidents(id)`
- `task_id` → `cims_tasks(id)`
- `author_id` → `users(id)`

---

### 5. `cims_notifications` (0 rows) 🔔

**Purpose:** User notifications for urgent tasks

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `notification_id` | VARCHAR(100) | YES | - | **Unique notification ID** |
| `user_id` | INTEGER | YES | - | **Foreign Key → users.id** |
| `task_id` | INTEGER | NO | - | Related task (if applicable) |
| `incident_id` | INTEGER | NO | - | Related incident (if applicable) |
| `type` | VARCHAR(50) | YES | - | urgent_task, overdue_task, etc. |
| `title` | VARCHAR(200) | YES | - | Notification title |
| `message` | TEXT | YES | - | Notification message |
| `priority` | VARCHAR(20) | NO | 'normal' | urgent, high, normal, low |
| `is_read` | BOOLEAN | NO | 0 | Read status |
| `sent_at` | TIMESTAMP | NO | - | Send timestamp |
| `read_at` | TIMESTAMP | NO | - | Read timestamp |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation time |

**Foreign Keys:**
- `user_id` → `users(id)`
- `task_id` → `cims_tasks(id)`
- `incident_id` → `cims_incidents(id)`

---

### 6. `cims_task_assignments` (0 rows) 👥

**Purpose:** Specific task assignments to users

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `task_id` | INTEGER | YES | - | **Foreign Key → cims_tasks.id** |
| `assigned_to_user_id` | INTEGER | YES | - | **Foreign Key → users.id** |
| `assigned_by_user_id` | INTEGER | YES | - | **Foreign Key → users.id** |
| `assigned_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Assignment timestamp |
| `status` | VARCHAR(50) | NO | 'active' | active, completed, cancelled |
| `notes` | TEXT | NO | - | Assignment notes |

**Foreign Keys:**
- `task_id` → `cims_tasks(id)`
- `assigned_to_user_id` → `users(id)`
- `assigned_by_user_id` → `users(id)`

---

### 7. `cims_audit_logs` (0 rows) 📜

**Purpose:** Complete audit trail for compliance

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `log_id` | VARCHAR(100) | YES | - | **Unique log ID** |
| `timestamp` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Log timestamp |
| `user_id` | INTEGER | YES | - | **Foreign Key → users.id** |
| `action` | VARCHAR(100) | YES | - | created, updated, deleted, viewed |
| `target_entity_type` | VARCHAR(50) | YES | - | incident, task, policy, user |
| `target_entity_id` | INTEGER | YES | - | Target record ID |
| `details` | TEXT | NO | - | Action details (JSON) |
| `ip_address` | VARCHAR(45) | NO | - | Client IP address |
| `user_agent` | TEXT | NO | - | Browser/device info |

**Foreign Keys:**
- `user_id` → `users(id)`

---

### 8. `clients_cache` (270 rows) 👤

**Purpose:** Cached resident data from MANAD Plus API

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `person_id` | INTEGER | YES | - | MANAD Plus person ID |
| `client_name` | VARCHAR(200) | YES | - | Full name |
| `preferred_name` | VARCHAR(100) | NO | - | Preferred name |
| `title` | VARCHAR(10) | NO | - | Mr, Mrs, Ms, etc. |
| `first_name` | VARCHAR(100) | NO | - | First name |
| `middle_name` | VARCHAR(100) | NO | - | Middle name |
| `surname` | VARCHAR(100) | NO | - | Surname |
| `gender` | VARCHAR(10) | NO | - | Gender |
| `birth_date` | DATE | NO | - | Date of birth |
| `admission_date` | DATE | NO | - | Admission date |
| `room_name` | VARCHAR(50) | NO | - | Room name/number |
| `room_number` | VARCHAR(10) | NO | - | Room number |
| `wing_name` | VARCHAR(100) | NO | - | Wing/section name |
| `location_id` | INTEGER | NO | - | Location ID |
| `location_name` | VARCHAR(200) | NO | - | Location name |
| `main_client_service_id` | INTEGER | NO | - | Service ID |
| `original_person_id` | INTEGER | NO | - | Original person ID |
| `client_record_id` | INTEGER | NO | - | Client record ID |
| `site` | VARCHAR(100) | YES | - | Site name |
| `last_synced` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last sync time |
| `is_active` | BOOLEAN | NO | 1 | Active flag |

---

### 9. `users` (20 rows) 👨‍⚕️

**Purpose:** User accounts and authentication

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `username` | VARCHAR(50) | YES | - | **Unique username** |
| `password_hash` | VARCHAR(255) | YES | - | Hashed password |
| `first_name` | VARCHAR(100) | YES | - | First name |
| `last_name` | VARCHAR(100) | YES | - | Last name |
| `role` | VARCHAR(20) | YES | - | admin, clinical_manager, nurse, carer, doctor |
| `position` | VARCHAR(100) | NO | - | Job title |
| `location` | TEXT | NO | - | Work location(s) (JSON array) |
| `is_active` | BOOLEAN | NO | 1 | Active account flag |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Account creation time |
| `updated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update time |

**User Roles:**
- `admin` - Full system access
- `clinical_manager` - Clinical oversight, policy management
- `nurse` - Task completion, progress notes
- `carer` - Task viewing, basic reporting
- `doctor` - Clinical review, incident viewing

---

### 10. `sites` (4 rows) 🏥

**Purpose:** Site/facility configuration

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `site_name` | VARCHAR(100) | YES | - | **Site name** (Parafield Gardens, Nerrilda, Ramsay, West Park, Yankalilla) |
| `server_ip` | VARCHAR(50) | NO | - | MANAD Plus server IP |
| `description` | TEXT | NO | - | Site description |
| `is_active` | BOOLEAN | NO | 1 | Active flag |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation time |

**Active Sites:**
1. Parafield Gardens
2. Nerrilda
3. Ramsay
4. West Park
5. Yankalilla

---

### 11. `sync_status` (8 rows) 🔄

**Purpose:** Track synchronization status per site

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `data_type` | VARCHAR(50) | YES | - | incidents, progress_notes, clients |
| `site` | VARCHAR(100) | NO | - | Site name (NULL = all sites) |
| `last_sync_time` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last successful sync |
| `sync_status` | VARCHAR(20) | NO | 'pending' | pending, in_progress, completed, failed |
| `error_message` | TEXT | NO | - | Error details if failed |
| `records_synced` | INTEGER | NO | 0 | Number of records synced |

---

### 12. `system_settings` (6 rows) ⚙️

**Purpose:** System-wide configuration key-value store

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `key` | TEXT | - | - | **Primary Key** (setting key) |
| `value` | TEXT | YES | - | Setting value |
| `updated_at` | TEXT | YES | - | Last update timestamp |

**Common Settings:**
- `last_incident_sync_time` - Last incident synchronization
- `last_sync_parafield_gardens` - Last sync per site
- `last_sync_nerrilda`
- `last_sync_ramsay`
- `last_sync_west_park`
- `last_sync_yankalilla`

---

### 13. `fcm_tokens` (0 rows) 📱

**Purpose:** Firebase Cloud Messaging tokens for mobile notifications

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `user_id` | VARCHAR(100) | YES | - | User identifier |
| `token` | TEXT | YES | - | FCM registration token |
| `device_info` | VARCHAR(200) | NO | - | Device information |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Token registration time |
| `last_used` | TIMESTAMP | NO | - | Last notification sent |
| `is_active` | BOOLEAN | NO | 1 | Active token flag |

---

### 14. `cims_dashboard_kpi_cache` (0 rows) 📊

**Purpose:** Cache for dashboard KPIs (performance optimization)

| Column Name | Type | NOT NULL | Default | Description |
|------------|------|----------|---------|-------------|
| `id` | INTEGER | - | - | **Primary Key** |
| `cache_key` | TEXT | YES | - | Cache identifier (period + incident_type) |
| `compliance_rate` | REAL | NO | - | Overall compliance percentage |
| `overdue_tasks_count` | INTEGER | NO | - | Number of overdue tasks |
| `open_incidents_count` | INTEGER | NO | - | Number of open incidents |
| `total_tasks_count` | INTEGER | NO | - | Total tasks in period |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Cache creation time |
| `expires_at` | TIMESTAMP | YES | - | Cache expiration time |

---

### 15-17. Reference Tables

#### `care_areas` (0 rows)
- Care area definitions from MANAD Plus

#### `event_types` (0 rows)
- Event type definitions from MANAD Plus

#### `access_logs` (0 rows)
- User access activity logs

#### `progress_note_logs` (0 rows)
- Progress note activity tracking

---

## 🔧 Production Migration Scripts

### Script 1: Create All Tables

```sql
-- Run this on production server to create all required tables

-- 1. CIMS Incidents
CREATE TABLE IF NOT EXISTS cims_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(100) UNIQUE NOT NULL,
    manad_incident_id VARCHAR(100),
    resident_id INTEGER NOT NULL,
    resident_name VARCHAR(200) NOT NULL,
    incident_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50),
    status VARCHAR(50),
    incident_date TIMESTAMP NOT NULL,
    location VARCHAR(200),
    description TEXT,
    initial_actions_taken TEXT,
    witnesses TEXT,
    reported_by INTEGER,
    reported_by_name VARCHAR(200),
    site VARCHAR(100) NOT NULL,
    policy_applied INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidents_manad_id ON cims_incidents(manad_incident_id);
CREATE INDEX IF NOT EXISTS idx_incidents_site_status ON cims_incidents(site, status, incident_date);

-- 2. CIMS Tasks
CREATE TABLE IF NOT EXISTS cims_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    incident_id INTEGER NOT NULL,
    policy_id INTEGER NOT NULL,
    task_name VARCHAR(300) NOT NULL,
    description TEXT,
    assigned_role VARCHAR(100) NOT NULL,
    assigned_user_id INTEGER,
    due_date TIMESTAMP NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    completed_by_user_id INTEGER,
    completed_at TIMESTAMP,
    documentation_required BOOLEAN DEFAULT 1,
    note_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
    FOREIGN KEY (policy_id) REFERENCES cims_policies(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id),
    FOREIGN KEY (completed_by_user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_incident ON cims_tasks(incident_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON cims_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON cims_tasks(status);

-- 3. CIMS Policies
CREATE TABLE IF NOT EXISTS cims_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    expiry_date TIMESTAMP,
    rules_json TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 4. CIMS Progress Notes
CREATE TABLE IF NOT EXISTS cims_progress_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id VARCHAR(100) UNIQUE NOT NULL,
    incident_id INTEGER NOT NULL,
    task_id INTEGER,
    author_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    note_type VARCHAR(100),
    vitals_data TEXT,
    assessment_data TEXT,
    attachments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

-- 5. CIMS Notifications
CREATE TABLE IF NOT EXISTS cims_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    task_id INTEGER,
    incident_id INTEGER,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    is_read BOOLEAN DEFAULT 0,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id)
);

-- 6. CIMS Task Assignments
CREATE TABLE IF NOT EXISTS cims_task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    assigned_to_user_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    notes TEXT,
    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id)
);

-- 7. CIMS Audit Logs
CREATE TABLE IF NOT EXISTS cims_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id INTEGER NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 8. Clients Cache
CREATE TABLE IF NOT EXISTS clients_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    client_name VARCHAR(200) NOT NULL,
    preferred_name VARCHAR(100),
    title VARCHAR(10),
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    surname VARCHAR(100),
    gender VARCHAR(10),
    birth_date DATE,
    admission_date DATE,
    room_name VARCHAR(50),
    room_number VARCHAR(10),
    wing_name VARCHAR(100),
    location_id INTEGER,
    location_name VARCHAR(200),
    main_client_service_id INTEGER,
    original_person_id INTEGER,
    client_record_id INTEGER,
    site VARCHAR(100) NOT NULL,
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_clients_site ON clients_cache(site);
CREATE INDEX IF NOT EXISTS idx_clients_client_record_id ON clients_cache(client_record_id);

-- 9. Users
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    position VARCHAR(100),
    location TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Sites
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name VARCHAR(100) UNIQUE NOT NULL,
    server_ip VARCHAR(50),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Sync Status
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type VARCHAR(50) NOT NULL,
    site VARCHAR(100),
    last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    records_synced INTEGER DEFAULT 0
);

-- 12. System Settings
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 13. FCM Tokens
CREATE TABLE IF NOT EXISTS fcm_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    token TEXT NOT NULL,
    device_info VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- 14. Dashboard KPI Cache
CREATE TABLE IF NOT EXISTS cims_dashboard_kpi_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    compliance_rate REAL,
    overdue_tasks_count INTEGER,
    open_incidents_count INTEGER,
    total_tasks_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- 15. Care Areas
CREATE TABLE IF NOT EXISTS care_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description VARCHAR(500) NOT NULL,
    is_archived BOOLEAN DEFAULT 0,
    is_external BOOLEAN DEFAULT 0,
    last_updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 16. Event Types
CREATE TABLE IF NOT EXISTS event_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description VARCHAR(500) NOT NULL,
    color_argb INTEGER,
    is_archived BOOLEAN DEFAULT 0,
    is_external BOOLEAN DEFAULT 0,
    last_updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 17. Access Logs
CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username VARCHAR(50),
    display_name VARCHAR(200),
    role VARCHAR(20),
    position VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    page_accessed VARCHAR(200),
    session_duration INTEGER
);

-- 18. Progress Note Logs
CREATE TABLE IF NOT EXISTS progress_note_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    username VARCHAR(50),
    display_name VARCHAR(200),
    role VARCHAR(20),
    position VARCHAR(100),
    client_id INTEGER,
    client_name VARCHAR(200),
    care_area_id INTEGER,
    event_type_id INTEGER,
    note_content TEXT,
    site VARCHAR(100)
);
```

---

## 🔄 Data Synchronization Flow

### Automatic Sync (Every 5 minutes)

```
MANAD Plus API → CIMS Database
     ↓                 ↓
1. Incidents      cims_incidents
2. Clients        clients_cache
3. Progress Notes cims_progress_notes (via task matching)
     ↓
4. Auto-generate tasks for Fall incidents
     ↓
5. Update incident status (Open/Overdue/Closed)
```

### Force Sync (Manual)

```
System Settings → Force Synchronization Button
     ↓
1. Full incident sync (30 days)
2. Generate missing tasks
3. Sync progress notes
4. Update all statuses
     ↓
Dashboard refresh
```

---

## ⚠️ Common Production Issues

### Issue 1: Missing Columns

**Symptoms:** `no such column: column_name`

**Solution:** Check if production DB has all required columns

**Verification Script:**
```python
# Check if specific column exists
cursor.execute("PRAGMA table_info(cims_incidents)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

required_columns = ['id', 'incident_id', 'manad_incident_id', 'resident_id', 
                    'resident_name', 'incident_type', 'severity', 'status', 
                    'incident_date', 'location', 'description', 'site']

missing = [col for col in required_columns if col not in column_names]
if missing:
    print(f"Missing columns: {missing}")
```

### Issue 2: Missing Tables

**Solution:** Run the complete schema creation script above

### Issue 3: Tasks Not Auto-Generated

**Symptoms:** Fall incidents have 0 tasks

**Solution:**
1. Check if Fall policy exists and is active
2. Verify `auto_generate_fall_tasks()` is called in sync
3. Use Force Sync to regenerate missing tasks

---

## 📝 Maintenance Scripts

### Check Database Health

```bash
cd /home/itsupport/DEV_code/ProgressReport2
.venv/bin/python << 'EOF'
import sqlite3
conn = sqlite3.connect('progress_report.db')
cursor = conn.cursor()

# Check critical tables
tables = ['cims_incidents', 'cims_tasks', 'cims_policies', 'users']

for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"{table}: {count} rows")

# Check Fall incidents without tasks
cursor.execute("""
    SELECT COUNT(*) FROM cims_incidents i
    WHERE i.incident_type LIKE '%Fall%'
    AND NOT EXISTS (SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id)
""")
missing_tasks = cursor.fetchone()[0]
print(f"\nFall incidents without tasks: {missing_tasks}")

conn.close()
EOF
```

### Generate Missing Tasks

```bash
# Use Force Sync button in System Settings
# OR manually trigger:
curl -X POST http://127.0.0.1:5000/api/cims/force-sync \
  -H "Content-Type: application/json" \
  --cookie "session=YOUR_SESSION_COOKIE"
```

---

## 📊 Database Statistics

- **Total Incidents:** 182
- **Total Tasks:** 828
- **Active Policies:** 1 (Fall Management Policy V3)
- **Cached Residents:** 270
- **Active Users:** 20
- **Active Sites:** 5

---

## 🚀 Key Features

### 1. **Auto Task Generation**
- New Fall incidents → 12 nurse visit tasks
- Policy-based scheduling
- No manual intervention required

### 2. **Progress Note Sync**
- MANAD Plus "Post Fall" notes → CIMS tasks
- Auto-match by timestamp (±30 minutes)
- Auto-update task completion status

### 3. **Incident Status Management**
- All tasks completed → Status = "Closed"
- Last task overdue → Status = "Overdue"
- No visits yet → Status = "Open"

### 4. **Background Synchronization**
- Every 5 minutes (incremental)
- Force Sync available (30 days full sync)
- Non-blocking (background thread)

---

## 📖 Related Documentation

- `DATA_SYNC_OPTIMIZATION.md` - Data synchronization strategies
- `PROGRESS_NOTE_SYNC.md` - Progress note synchronization details
- `cims_database_schema.sql` - Raw SQL schema file

---

**Document Version:** 1.0  
**Generated:** 2025-10-16  
**Maintained By:** IT Support Team

