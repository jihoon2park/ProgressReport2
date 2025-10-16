-- =========================================
-- CIMS (Compliance-Driven Incident Management System) - Database Schema
-- 새로운 인시던트 관리 시스템을 위한 데이터베이스 스키마
-- =========================================

-- ===========================================
-- CIMS 핵심 테이블들
-- ===========================================

-- 1. 정책 관리 테이블 (Policy Management)
CREATE TABLE cims_policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    effective_date TIMESTAMP NOT NULL,
    expiry_date TIMESTAMP,
    rules_json TEXT NOT NULL, -- JSON 형태의 정책 규칙
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 2. 인시던트 테이블 (Incident Management)
CREATE TABLE cims_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id VARCHAR(100) UNIQUE NOT NULL,
    manad_incident_id VARCHAR(100), -- MANAD Plus 시스템의 원본 incident ID
    resident_id INTEGER NOT NULL,
    resident_name VARCHAR(200) NOT NULL,
    incident_type VARCHAR(100) NOT NULL, -- 'Fall', 'Skin Breakdown', 'Medication Error'
    severity VARCHAR(50) NOT NULL, -- 'High', 'Medium', 'Low', 'Injury Suspected', 'No Injury'
    status VARCHAR(50) DEFAULT 'Open', -- 'Open', 'In Progress', 'Closed'
    incident_date TIMESTAMP NOT NULL,
    location VARCHAR(200),
    description TEXT,
    initial_actions_taken TEXT,
    witnesses TEXT,
    reported_by INTEGER,
    reported_by_name VARCHAR(200), -- 리포터 이름 (MANAD 통합용)
    site VARCHAR(100) NOT NULL,
    policy_applied INTEGER, -- 적용된 정책 ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reported_by) REFERENCES users(id),
    FOREIGN KEY (policy_applied) REFERENCES cims_policies(id)
);

-- 3. 태스크 관리 테이블 (Task Management)
CREATE TABLE cims_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    incident_id INTEGER NOT NULL,
    policy_id INTEGER NOT NULL,
    task_name VARCHAR(300) NOT NULL,
    description TEXT,
    assigned_role VARCHAR(100) NOT NULL, -- 'Registered Nurse', 'All Staff', 'Clinical Manager'
    assigned_user_id INTEGER, -- 특정 사용자에게 할당된 경우
    due_date TIMESTAMP NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal', -- 'urgent', 'high', 'normal', 'low'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'overdue'
    completed_by_user_id INTEGER,
    completed_at TIMESTAMP,
    documentation_required BOOLEAN DEFAULT 1,
    note_type VARCHAR(100), -- 'Initial Response Check', 'Dynamic Form - Post Fall Assessment'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
    FOREIGN KEY (policy_id) REFERENCES cims_policies(id),
    FOREIGN KEY (assigned_user_id) REFERENCES users(id),
    FOREIGN KEY (completed_by_user_id) REFERENCES users(id)
);

-- 4. 진행 노트 테이블 (Progress Notes)
CREATE TABLE cims_progress_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id VARCHAR(100) UNIQUE NOT NULL,
    incident_id INTEGER NOT NULL,
    task_id INTEGER,
    author_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    note_type VARCHAR(100),
    vitals_data TEXT, -- JSON 형태의 바이탈 데이터
    assessment_data TEXT, -- JSON 형태의 평가 데이터
    attachments TEXT, -- JSON 형태의 첨부파일 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES cims_incidents(id),
    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

-- 5. 감사 로그 테이블 (Audit Log)
CREATE TABLE cims_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_id VARCHAR(100) UNIQUE NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL, -- 'incident_created', 'task_completed', 'policy_updated'
    target_entity_type VARCHAR(50) NOT NULL, -- 'incident', 'task', 'policy', 'note'
    target_entity_id INTEGER NOT NULL,
    details TEXT, -- JSON 형태의 상세 정보 (변경 전/후 값 등)
    ip_address VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 6. 태스크 할당 테이블 (Task Assignments)
CREATE TABLE cims_task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    assigned_to_user_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'transferred', 'completed'
    notes TEXT,
    FOREIGN KEY (task_id) REFERENCES cims_tasks(id),
    FOREIGN KEY (assigned_to_user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id)
);

-- 7. 알림 테이블 (Notifications)
CREATE TABLE cims_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    task_id INTEGER,
    incident_id INTEGER,
    type VARCHAR(50) NOT NULL, -- 'task_due', 'task_overdue', 'incident_created'
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

-- ===========================================
-- 인덱스 생성 (성능 최적화)
-- ===========================================

-- 정책 관련 인덱스
CREATE INDEX idx_cims_policies_active ON cims_policies(is_active);
CREATE INDEX idx_cims_policies_effective ON cims_policies(effective_date);
CREATE INDEX idx_cims_policies_policy_id ON cims_policies(policy_id);

-- 인시던트 관련 인덱스
CREATE INDEX idx_cims_incidents_type ON cims_incidents(incident_type);
CREATE INDEX idx_cims_incidents_severity ON cims_incidents(severity);
CREATE INDEX idx_cims_incidents_status ON cims_incidents(status);
CREATE INDEX idx_cims_incidents_date ON cims_incidents(incident_date);
CREATE INDEX idx_cims_incidents_site ON cims_incidents(site);
CREATE INDEX idx_cims_incidents_resident ON cims_incidents(resident_id);
CREATE INDEX idx_cims_incidents_manad_id ON cims_incidents(manad_incident_id);

-- 태스크 관련 인덱스
CREATE INDEX idx_cims_tasks_incident ON cims_tasks(incident_id);
CREATE INDEX idx_cims_tasks_assigned_user ON cims_tasks(assigned_user_id);
CREATE INDEX idx_cims_tasks_assigned_role ON cims_tasks(assigned_role);
CREATE INDEX idx_cims_tasks_status ON cims_tasks(status);
CREATE INDEX idx_cims_tasks_due_date ON cims_tasks(due_date);
CREATE INDEX idx_cims_tasks_priority ON cims_tasks(priority);

-- 진행 노트 관련 인덱스
CREATE INDEX idx_cims_notes_incident ON cims_progress_notes(incident_id);
CREATE INDEX idx_cims_notes_task ON cims_progress_notes(task_id);
CREATE INDEX idx_cims_notes_author ON cims_progress_notes(author_id);
CREATE INDEX idx_cims_notes_created ON cims_progress_notes(created_at);

-- 감사 로그 관련 인덱스
CREATE INDEX idx_cims_audit_user ON cims_audit_logs(user_id);
CREATE INDEX idx_cims_audit_timestamp ON cims_audit_logs(timestamp);
CREATE INDEX idx_cims_audit_action ON cims_audit_logs(action);
CREATE INDEX idx_cims_audit_target ON cims_audit_logs(target_entity_type, target_entity_id);

-- 알림 관련 인덱스
CREATE INDEX idx_cims_notifications_user ON cims_notifications(user_id);
CREATE INDEX idx_cims_notifications_read ON cims_notifications(is_read);
CREATE INDEX idx_cims_notifications_created ON cims_notifications(created_at);

-- ===========================================
-- 기본 정책 데이터 삽입
-- ===========================================

-- Fall Management Policy 예시
INSERT INTO cims_policies (policy_id, name, description, version, effective_date, rules_json, created_by) VALUES 
('FALL-001', 'Fall Management Policy V3', 'Comprehensive fall management protocol for aged care facilities', '3.0', CURRENT_TIMESTAMP, 
'{
  "policy_name": "Fall Management Policy V3",
  "policy_id": "FALL-001",
  "rule_sets": [
    {
      "name": "High Severity Fall Protocol",
      "trigger_condition": {
        "incident_field": "type",
        "operator": "EQUALS",
        "value": "Fall",
        "AND": [
          {
            "incident_field": "severity",
            "operator": "IN",
            "value": ["High", "Injury Suspected"]
          }
        ]
      },
      "tasks_to_generate": [
        {
          "task_name": "Respond to Fall & Check Vitals (Step 6)",
          "assigned_role": "All Staff",
          "due_offset": 5,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Initial Response Check"
        },
        {
          "task_name": "Post Fall Assessment & Injury Check (Step 7)",
          "assigned_role": "Registered Nurse",
          "due_offset": 30,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Dynamic Form - Post Fall Assessment"
        },
        {
          "task_name": "4-Hour Neurological Monitoring Note",
          "assigned_role": "Registered Nurse",
          "due_offset": 4,
          "due_unit": "hours",
          "documentation_required": true,
          "note_type": "Dynamic Form - Neuro Obs"
        },
        {
          "task_name": "Incident Closure Request & Physician Notification",
          "assigned_role": "Registered Nurse",
          "due_offset": 72,
          "due_unit": "hours",
          "documentation_required": true,
          "note_type": "Final Closure Report"
        },
        {
          "task_name": "Clinical Manager Review & Approval",
          "assigned_role": "Clinical Manager",
          "due_offset": 74,
          "due_unit": "hours",
          "documentation_required": true,
          "note_type": "Manager Review Note"
        }
      ]
    },
    {
      "name": "Low Severity Fall Protocol",
      "trigger_condition": {
        "incident_field": "type",
        "operator": "EQUALS",
        "value": "Fall",
        "AND": [
          {
            "incident_field": "severity",
            "operator": "EQUALS",
            "value": "Low/No Injury"
          }
        ]
      },
      "tasks_to_generate": [
        {
          "task_name": "RN Review and Follow-up Assessment",
          "assigned_role": "Registered Nurse",
          "due_offset": 60,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Progress Note - Low Severity Fall"
        },
        {
          "task_name": "Environmental Safety Check",
          "assigned_role": "Carer / All Staff",
          "due_offset": 10,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Checklist - Environmental Safety"
        }
      ]
    }
  ]
}', 1);

-- Skin Breakdown Policy 예시
INSERT INTO cims_policies (policy_id, name, description, version, effective_date, rules_json, created_by) VALUES 
('SKIN-001', 'Skin Breakdown Management Policy V2', 'Skin integrity and wound management protocol', '2.0', CURRENT_TIMESTAMP,
'{
  "policy_name": "Skin Breakdown Management Policy V2",
  "policy_id": "SKIN-001",
  "rule_sets": [
    {
      "name": "Pressure Injury Protocol",
      "trigger_condition": {
        "incident_field": "type",
        "operator": "EQUALS",
        "value": "Skin Breakdown"
      },
      "tasks_to_generate": [
        {
          "task_name": "Initial Wound Assessment",
          "assigned_role": "Registered Nurse",
          "due_offset": 15,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Dynamic Form - Wound Assessment"
        },
        {
          "task_name": "Wound Photography and Documentation",
          "assigned_role": "Registered Nurse",
          "due_offset": 30,
          "due_unit": "minutes",
          "documentation_required": true,
          "note_type": "Photo Documentation"
        },
        {
          "task_name": "Care Plan Review and Update",
          "assigned_role": "Clinical Manager",
          "due_offset": 24,
          "due_unit": "hours",
          "documentation_required": true,
          "note_type": "Care Plan Update"
        }
      ]
    }
  ]
}', 1);
