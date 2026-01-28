#!/usr/bin/env python3
"""
JSON-based API Key Manager
Manages API keys using JSON files instead of DB
"""

import json
import os
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class APIKeyManagerJSON:
    """JSON file-based API key manager (integrated with site_config.json)"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        # New integrated configuration file (recommended)
        self.site_config_file = os.path.join(data_dir, "api_keys", "site_config.json")
        # Legacy API key file (for fallback)
        self.api_keys_file = os.path.join(data_dir, "api_keys", "api_keys.json")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(os.path.join(self.data_dir, "api_keys"), exist_ok=True)
    
    def _load_api_keys(self) -> List[Dict[str, Any]]:
        """Load API key list (site_config.json first, fallback to api_keys.json)"""
        try:
            # Step 1: Try site_config.json (integrated configuration)
            if os.path.exists(self.site_config_file):
                with open(self.site_config_file, 'r', encoding='utf-8') as f:
                    site_configs = json.load(f)
                    # Convert site_config format to api_keys format
                    api_keys = []
                    for config in site_configs:
                        api_info = config.get('api', {})
                        api_key_entry = {
                            'id': config.get('id'),
                            'site_name': config.get('site_name'),
                            'api_username': api_info.get('api_username', 'ManadAPI'),
                            'api_key': api_info.get('api_key', ''),
                            'server_ip': api_info.get('server_ip', ''),
                            'server_port': api_info.get('server_port', '8080'),
                            'server_url': f"http://{api_info.get('server_ip', '')}:{api_info.get('server_port', '8080')}",
                            'is_active': config.get('is_active', True),
                            'notes': config.get('notes', ''),
                            'created_at': config.get('created_at', ''),
                            'updated_at': config.get('updated_at', '')
                        }
                        api_keys.append(api_key_entry)
                    return api_keys
            
            # Step 2: Fallback to api_keys.json
            if os.path.exists(self.api_keys_file):
                with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return []
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return []
    
    def _save_api_keys(self, api_keys: List[Dict[str, Any]]) -> bool:
        """Save API key list"""
        try:
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
            return False
    
    def get_all_api_keys(self) -> List[Dict[str, Any]]:
        """Get all API keys"""
        return self._load_api_keys()
    
    def get_api_key(self, site_name: str) -> Optional[Dict[str, Any]]:
        """Get API key for a specific site"""
        api_keys = self._load_api_keys()
        for api_key in api_keys:
            if api_key.get('site_name') == site_name:
                return api_key
        return None
    
    def add_api_key(self, site_name: str, api_username: str, api_key: str, server_ip: str, server_port: int = 8080, notes: str = '') -> bool:
        """Add API key"""
        api_keys = self._load_api_keys()
        
        # Check if API key already exists
        for existing_key in api_keys:
            if existing_key.get('site_name') == site_name:
                logger.warning(f"API key already exists: {site_name}")
                return False
        
        # Add new API key
        new_id = max([k.get('id', 0) for k in api_keys], default=0) + 1
        new_api_key = {
            'id': new_id,
            'site_name': site_name,
            'api_username': api_username,
            'api_key': api_key,
            'server_ip': server_ip,
            'server_port': server_port,
            'server_url': f"http://{server_ip}:{server_port}",
            'notes': notes,
            'is_active': True,
            'created_at': '2025-09-11T12:00:00',
            'updated_at': '2025-09-11T12:00:00'
        }
        
        api_keys.append(new_api_key)
        return self._save_api_keys(api_keys)
    
    def update_api_key(self, site_name: str, **kwargs) -> bool:
        """Update API key"""
        api_keys = self._load_api_keys()
        
        for i, existing_key in enumerate(api_keys):
            if existing_key.get('site_name') == site_name:
                # Update only specified fields
                update_data = {}
                if 'api_username' in kwargs:
                    update_data['api_username'] = kwargs['api_username']
                if 'api_key' in kwargs:
                    update_data['api_key'] = kwargs['api_key']
                if 'server_ip' in kwargs:
                    update_data['server_ip'] = kwargs['server_ip']
                if 'server_port' in kwargs:
                    update_data['server_port'] = kwargs['server_port']
                if 'notes' in kwargs:
                    update_data['notes'] = kwargs['notes']
                if 'is_active' in kwargs:
                    update_data['is_active'] = kwargs['is_active']
                
                # Update server_url
                if 'server_ip' in update_data or 'server_port' in update_data:
                    server_ip = update_data.get('server_ip', existing_key.get('server_ip'))
                    server_port = update_data.get('server_port', existing_key.get('server_port'))
                    update_data['server_url'] = f"http://{server_ip}:{server_port}"
                
                update_data['updated_at'] = '2025-09-11T12:00:00'
                
                api_keys[i].update(update_data)
                return self._save_api_keys(api_keys)
        
        logger.warning(f"API key not found: {site_name}")
        return False
    
    def delete_api_key(self, site_name: str) -> bool:
        """Delete API key"""
        api_keys = self._load_api_keys()
        original_count = len(api_keys)
        api_keys = [k for k in api_keys if k.get('site_name') != site_name]
        
        if len(api_keys) < original_count:
            return self._save_api_keys(api_keys)
        
        logger.warning(f"API key not found: {site_name}")
        return False
    
    def deactivate_api_key(self, site_name: str) -> bool:
        """Deactivate API key (deactivate instead of delete)"""
        return self.update_api_key(site_name, is_active=False)
    
    def get_api_headers(self, site_name: str) -> Dict[str, str]:
        """Return API headers for site"""
        api_key_data = self.get_api_key(site_name)
        
        if not api_key_data:
            logger.error(f"API key not found: {site_name}")
            return {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'x-api-username': 'ManadAPI',
                'x-api-key': 'default-key'
            }
        
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-username': 'ManadAPI',
            'x-api-key': api_key_data['api_key']
        }
    
    def get_server_info(self, site_name: str) -> Dict[str, str]:
        """Return server information"""
        api_key_data = self.get_api_key(site_name)
        
        if not api_key_data:
            logger.error(f"API key not found: {site_name}")
            return {
                'server_ip': '192.168.1.11',
                'server_port': '8080',
                'base_url': 'http://192.168.1.11:8080'
            }
        
        return {
            'server_ip': api_key_data['server_ip'],
            'server_port': api_key_data['server_port'],
            'base_url': api_key_data['server_url']
        }
    
    def get_site_servers(self) -> Dict[str, str]:
        """Return site server information"""
        api_keys = self._load_api_keys()
        servers = {}
        
        for api_key in api_keys:
            site_name = api_key.get('site_name')
            server_ip = api_key.get('server_ip')
            server_port = api_key.get('server_port')
            
            if site_name and server_ip and server_port:
                servers[site_name] = f"{server_ip}:{server_port}"
        
        return servers

# Global instance
api_key_manager = APIKeyManagerJSON()

def get_api_key_manager():
    """Return API key manager instance"""
    return api_key_manager

def get_api_headers(site_name: str) -> Dict[str, str]:
    """Return API headers for site"""
    return api_key_manager.get_api_headers(site_name)

def get_server_info(site_name: str) -> Dict[str, str]:
    """Return server information"""
    return api_key_manager.get_server_info(site_name)

def get_site_servers() -> Dict[str, str]:
    """Return site server information"""
    return api_key_manager.get_site_servers()
