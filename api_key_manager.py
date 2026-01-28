#!/usr/bin/env python3
"""
API Key Manager - Safely manage API keys in database
"""

import sqlite3
import os
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class APIKeyManager:
    """API Key Manager - Store and manage in plain text in DB"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        # Create table
        self._create_table()
    
    def _create_table(self):
        """Create API key table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL UNIQUE,
                api_username TEXT NOT NULL,
                api_key TEXT NOT NULL,
                server_ip TEXT NOT NULL,
                server_port INTEGER DEFAULT 8080,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'system',
                notes TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_site ON api_keys(site_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)')
        
        conn.commit()
        conn.close()
    
    # Encryption removed - store in plain text
    
    def add_api_key(self, site_name: str, api_username: str, api_key: str, 
                   server_ip: str, server_port: int = 8080, notes: str = "") -> bool:
        """Add new API key"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO api_keys 
                (site_name, api_username, api_key, server_ip, server_port, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (site_name, api_username, api_key, server_ip, server_port, notes))
            
            conn.commit()
            conn.close()
            
            logger.info(f"API key added/updated: {site_name}")
            return True
            
        except Exception as e:
            logger.error(f"API key addition failed ({site_name}): {e}")
            return False
    
    def get_api_key(self, site_name: str) -> Optional[Dict]:
        """Get API key for site (includes decrypted key)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First check if api_key column exists
            cursor.execute("PRAGMA table_info(api_keys)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'api_key' in columns:
                # New schema (plain text API key)
                cursor.execute('''
                    SELECT site_name, api_username, api_key, server_ip, server_port, is_active, notes
                    FROM api_keys 
                    WHERE site_name = ? AND is_active = 1
                ''', (site_name,))
            else:
                # Old schema (encrypted API key) - use fallback
                logger.warning(f"api_key column not found, using fallback: {site_name}")
                return None
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'site_name': result[0],
                    'api_username': result[1],
                    'api_key': result[2],
                    'server_ip': result[3],
                    'server_port': result[4],
                    'is_active': bool(result[5]),
                    'notes': result[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"API key lookup failed ({site_name}): {e}")
            return None
    
    def get_all_api_keys(self) -> List[Dict]:
        """Get all active API keys"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # First check if api_key column exists
            cursor.execute("PRAGMA table_info(api_keys)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'api_key' in columns:
                # New schema (plain text API key)
                cursor.execute('''
                    SELECT site_name, api_username, api_key, server_ip, server_port, is_active, notes
                    FROM api_keys 
                    WHERE is_active = 1
                    ORDER BY site_name
                ''')
            else:
                # Old schema (encrypted API key) - return empty result
                logger.warning("api_key column not found, returning empty result")
                conn.close()
                return []
            
            results = cursor.fetchall()
            conn.close()
            
            api_keys = []
            for result in results:
                api_keys.append({
                    'site_name': result[0],
                    'api_username': result[1],
                    'api_key': result[2],
                    'server_ip': result[3],
                    'server_port': result[4],
                    'is_active': bool(result[5]),
                    'notes': result[6]
                })
            
            return api_keys
            
        except Exception as e:
            logger.error(f"Failed to get all API keys: {e}")
            return []
    
    def update_api_key(self, site_name: str, api_key: str = None, 
                      server_ip: str = None, server_port: int = None, 
                      is_active: bool = None, notes: str = None) -> bool:
        """Update API key"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing data
            cursor.execute('SELECT * FROM api_keys WHERE site_name = ?', (site_name,))
            existing = cursor.fetchone()
            
            if not existing:
                logger.error(f"API key not found: {site_name}")
                return False
            
            # Fields to update
            update_fields = []
            update_values = []
            
            if api_key is not None:
                encrypted_key = self._encrypt_key(api_key)
                update_fields.append('api_key_encrypted = ?')
                update_values.append(encrypted_key)
            
            if server_ip is not None:
                update_fields.append('server_ip = ?')
                update_values.append(server_ip)
            
            if server_port is not None:
                update_fields.append('server_port = ?')
                update_values.append(server_port)
            
            if is_active is not None:
                update_fields.append('is_active = ?')
                update_values.append(is_active)
            
            if notes is not None:
                update_fields.append('notes = ?')
                update_values.append(notes)
            
            if update_fields:
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                update_values.append(site_name)
                
                query = f"UPDATE api_keys SET {', '.join(update_fields)} WHERE site_name = ?"
                cursor.execute(query, update_values)
                
                conn.commit()
                logger.info(f"API key updated: {site_name}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"API key update failed ({site_name}): {e}")
            return False
    
    def deactivate_api_key(self, site_name: str) -> bool:
        """Deactivate API key"""
        return self.update_api_key(site_name, is_active=False)
    
    def get_api_headers(self, site_name: str) -> Optional[Dict[str, str]]:
        """Return API headers for site (replaces existing get_api_headers function)"""
        api_data = self.get_api_key(site_name)
        
        if not api_data:
            logger.error(f"API key not found: {site_name}")
            return None
        
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-username': api_data['api_username'],
            'x-api-key': api_data['api_key']
        }
    
    def get_server_info(self, site_name: str) -> Optional[Dict[str, str]]:
        """Return server information for site"""
        api_data = self.get_api_key(site_name)
        
        if not api_data:
            return None
        
        return {
            'server_ip': api_data['server_ip'],
            'server_port': str(api_data['server_port']),
            'base_url': f"http://{api_data['server_ip']}:{api_data['server_port']}"
        }


# Global instance
_api_key_manager = None

def get_api_key_manager():
    """API key manager singleton instance"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager

def get_api_headers(site_name: str) -> Optional[Dict[str, str]]:
    """Wrapper for backward compatibility with existing function"""
    manager = get_api_key_manager()
    return manager.get_api_headers(site_name)

def get_server_info(site_name: str) -> Optional[Dict[str, str]]:
    """Get server information"""
    manager = get_api_key_manager()
    return manager.get_server_info(site_name)

def get_site_servers() -> Dict[str, str]:
    """Get server information for all sites"""
    manager = get_api_key_manager()
    servers = {}
    
    for api_data in manager.get_all_api_keys():
        servers[api_data['site_name']] = f"{api_data['server_ip']}:{api_data['server_port']}"
    
    return servers
