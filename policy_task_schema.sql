-- =========================================
-- Policy Manager & Task Scheduling Schema
-- =========================================

-- 1. Scheduled tasks table
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    incident_id VARCHAR(100) NOT NULL,
    policy_id INTEGER NOT NULL,
    client_name VARCHAR(200),
    client_id INTEGER,
    task_type VARCHAR(100) NOT NULL, -- 'vital_chart', 'medication', 'assessment'
    task_description TEXT,
    scheduled_time TIMESTAMP NOT NULL,
    due_time TIMESTAMP, -- Due time
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'cancelled', 'overdue'
    priority VARCHAR(20) DEFAULT 'normal', -- 'high', 'medium', 'normal', 'low'
    assigned_user VARCHAR(100),
    assigned_role VARCHAR(50), -- 'RN', 'doctor', 'physiotherapist'
    site VARCHAR(100),
    deep_link VARCHAR(500), -- nursingapp://task/SCH-567
    notification_sent BOOLEAN DEFAULT 0,
    notification_count INTEGER DEFAULT 0,
    last_notification_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    completed_by VARCHAR(100),
    completion_notes TEXT,
    FOREIGN KEY (policy_id) REFERENCES escalation_policies(id),
    FOREIGN KEY (client_id) REFERENCES clients_cache(id)
);

-- 2. Extend incidents table (modify existing incidents_cache table)
ALTER TABLE incidents_cache ADD COLUMN workflow_status VARCHAR(50) DEFAULT 'open'; -- 'open', 'in_progress', 'closed'
ALTER TABLE incidents_cache ADD COLUMN total_tasks INTEGER DEFAULT 0;
ALTER TABLE incidents_cache ADD COLUMN completed_tasks INTEGER DEFAULT 0;
ALTER TABLE incidents_cache ADD COLUMN policy_id INTEGER;
ALTER TABLE incidents_cache ADD COLUMN created_by VARCHAR(100);
ALTER TABLE incidents_cache ADD COLUMN closed_at TIMESTAMP;
ALTER TABLE incidents_cache ADD COLUMN closed_by VARCHAR(100);

-- 3. Task execution logs table
CREATE TABLE IF NOT EXISTS task_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL, -- 'created', 'notified', 'started', 'completed', 'cancelled'
    performed_by VARCHAR(100),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details TEXT, -- Additional information in JSON format
    fcm_message_id VARCHAR(100), -- FCM message ID (when sending notification)
    FOREIGN KEY (task_id) REFERENCES scheduled_tasks(task_id)
);

-- 4. Policy execution results table
CREATE TABLE IF NOT EXISTS policy_execution_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    policy_id INTEGER NOT NULL,
    incident_id VARCHAR(100) NOT NULL,
    execution_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_end TIMESTAMP,
    total_tasks_created INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_cancelled INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2), -- Completion rate (%)
    average_completion_time INTEGER, -- Average completion time (minutes)
    notes TEXT,
    FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
);

-- 5. Create indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON scheduled_tasks(status, scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_incident ON scheduled_tasks(incident_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user ON scheduled_tasks(assigned_user, status);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_site ON scheduled_tasks(site, status);
CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_execution_logs(task_id, performed_at);
CREATE INDEX IF NOT EXISTS idx_incidents_workflow ON incidents_cache(workflow_status, site);
