-- =========================================
-- Progress Report System - SQLite Schema
-- Comprehensive schema for full JSON data migration
-- =========================================

-- ===========================================
-- TIER 1: Core permanent data tables
-- ===========================================

-- 1. User management table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'site_admin', 'doctor', 'physiotherapist', 'nurse', 'registered_nurse', 'carer', 'clinical_manager')),
    position VARCHAR(100),
    location TEXT, -- Stored as JSON array ["Parafield Gardens", "Ramsay"]
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. FCM token management table (credential/fcm_tokens.json)
CREATE TABLE fcm_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    token TEXT NOT NULL,
    device_info VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(user_id, token)
);

-- 3. User access logs table (UsageLog/access_*.json)
CREATE TABLE access_logs (
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
    session_duration INTEGER, -- In seconds
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. Progress Note creation logs table (UsageLog/progress_notes_*.json)
CREATE TABLE progress_note_logs (
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
    site VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ===========================================
-- TIER 2: Cache tables (temporary data + performance)
-- ===========================================

-- 5. Client cache table (*_client.json, Client_list.json)
CREATE TABLE clients_cache (
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
    site VARCHAR(100) NOT NULL, -- 'Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla'
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    UNIQUE(person_id, site)
);

-- 6. Care area table (carearea.json)
CREATE TABLE care_areas (
    id INTEGER PRIMARY KEY,
    description VARCHAR(500) NOT NULL,
    is_archived BOOLEAN DEFAULT 0,
    is_external BOOLEAN DEFAULT 0,
    last_updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Event type table (eventtype.json)
CREATE TABLE event_types (
    id INTEGER PRIMARY KEY,
    description VARCHAR(500) NOT NULL,
    color_argb INTEGER,
    is_archived BOOLEAN DEFAULT 0,
    is_external BOOLEAN DEFAULT 0,
    last_updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- TIER 3: Hybrid data tables
-- ===========================================

-- 8. Incident cache table (incidents_*.json)
CREATE TABLE incidents_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(100) NOT NULL,
    client_id INTEGER,
    client_name VARCHAR(200),
    incident_type VARCHAR(100),
    incident_date TIMESTAMP,
    description TEXT,
    severity VARCHAR(20),
    status VARCHAR(50),
    site VARCHAR(100),
    reported_by VARCHAR(100),
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(incident_id, site)
);

-- ===========================================
-- Auxiliary tables
-- ===========================================

-- 9. Site information table
CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name VARCHAR(100) UNIQUE NOT NULL,
    server_ip VARCHAR(50),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Data synchronization status table
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type VARCHAR(50) NOT NULL, -- 'clients', 'incidents', 'carearea', 'eventtype'
    site VARCHAR(100),
    last_sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'success', -- 'success', 'failed', 'partial'
    error_message TEXT,
    records_synced INTEGER DEFAULT 0,
    UNIQUE(data_type, site)
);

-- 11. Alarm template table (Policy & Alarm Management)
CREATE TABLE alarm_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    title_template VARCHAR(500),
    body_template TEXT,
    priority VARCHAR(20) DEFAULT 'normal',
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 12. Alarm recipient table
CREATE TABLE alarm_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(100),
    team VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ===========================================
-- Create indexes (performance optimization)
-- ===========================================

-- User-related indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(is_active);

-- Client-related indexes
CREATE INDEX idx_clients_person_id ON clients_cache(person_id);
CREATE INDEX idx_clients_site ON clients_cache(site);
CREATE INDEX idx_clients_room ON clients_cache(room_number);
CREATE INDEX idx_clients_name ON clients_cache(client_name);
CREATE INDEX idx_clients_active ON clients_cache(is_active);
CREATE INDEX idx_clients_sync ON clients_cache(last_synced);

-- FCM token indexes
CREATE INDEX idx_fcm_tokens_user ON fcm_tokens(user_id);
CREATE INDEX idx_fcm_tokens_active ON fcm_tokens(is_active);

-- Log-related indexes
CREATE INDEX idx_access_logs_timestamp ON access_logs(timestamp);
CREATE INDEX idx_access_logs_user ON access_logs(user_id);
CREATE INDEX idx_access_logs_username ON access_logs(username);
CREATE INDEX idx_progress_logs_timestamp ON progress_note_logs(timestamp);
CREATE INDEX idx_progress_logs_user ON progress_note_logs(user_id);
CREATE INDEX idx_progress_logs_client ON progress_note_logs(client_id);

-- Reference data indexes
CREATE INDEX idx_care_areas_archived ON care_areas(is_archived);
CREATE INDEX idx_event_types_archived ON event_types(is_archived);

-- Incident-related indexes
CREATE INDEX idx_incidents_site ON incidents_cache(site);
CREATE INDEX idx_incidents_date ON incidents_cache(incident_date);
CREATE INDEX idx_incidents_client ON incidents_cache(client_id);

-- Sync status indexes
CREATE INDEX idx_sync_status_type ON sync_status(data_type);
CREATE INDEX idx_sync_status_site ON sync_status(site);
CREATE INDEX idx_sync_status_time ON sync_status(last_sync_time);

-- ===========================================
-- Initial data insertion
-- ===========================================

<<<<<<< Updated upstream
-- 기본 사이트 정보
INSERT OR IGNORE INTO sites (site_name, description) VALUES 
=======
-- Default site information
INSERT INTO sites (site_name, description) VALUES 
>>>>>>> Stashed changes
('Parafield Gardens', 'Edenfield Family Care - Parafield Gardens'),
('Nerrilda', 'Nerrilda Care Facility'),
('Ramsay', 'Ramsay Care Center'),
('Yankalilla', 'Yankalilla Care Home');

<<<<<<< Updated upstream
-- 기본 동기화 상태 레코드
INSERT OR IGNORE INTO sync_status (data_type, site) VALUES
=======
-- Default sync status records
INSERT INTO sync_status (data_type, site) VALUES
>>>>>>> Stashed changes
('clients', 'Parafield Gardens'),
('clients', 'Nerrilda'),
('clients', 'Ramsay'),
('clients', 'Yankalilla'),
('carearea', NULL),
('eventtype', NULL),
('incidents', 'Parafield Gardens');
