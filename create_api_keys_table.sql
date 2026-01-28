-- Create API key management table
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name TEXT NOT NULL UNIQUE,
    api_username TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,  -- Encrypted API key
    server_ip TEXT NOT NULL,
    server_port INTEGER DEFAULT 8080,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',
    notes TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_site ON api_keys(site_name);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Insert initial data (with encrypted keys)
INSERT OR REPLACE INTO api_keys (site_name, api_username, api_key_encrypted, server_ip, server_port, notes) VALUES
('Parafield Gardens', 'ManadAPI', 'ENCRYPTED_KEY_1', '192.168.1.11', 8080, 'Parafield Gardens API Key'),
('Nerrilda', 'ManadAPI', 'ENCRYPTED_KEY_2', '192.168.21.12', 8080, 'Nerrilda API Key'),
('Ramsay', 'ManadAPI', 'ENCRYPTED_KEY_3', '192.168.31.12', 8080, 'Ramsay API Key'),
('West Park', 'ManadAPI', 'ENCRYPTED_KEY_4', '192.168.41.12', 8080, 'West Park API Key'),
('Yankalilla', 'ManadAPI', 'ENCRYPTED_KEY_5', '192.168.51.12', 8080, 'Yankalilla API Key');
