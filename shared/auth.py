"""
Shared authentication system for both Core and Admin systems
"""
import json
import os
import hashlib
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, id, username, display_name, role, position=None, sites=None):
        self.id = id
        self.username = username
        self.display_name = display_name
        self.role = role
        self.position = position or "Unknown"
        self.sites = sites or []
    
    def get_id(self):
        return str(self.id)
    
    def has_admin_access(self):
        """Check if user has admin access"""
        return self.role in ['admin', 'site_admin']
    
    def can_access_admin_system(self):
        """Check if user can access admin management system"""
        return self.role in ['admin', 'site_admin']

class AuthManager:
    """Shared authentication manager"""
    
    def __init__(self, users_file_path=None):
        if users_file_path is None:
            # Default path relative to project root
            project_root = os.path.dirname(os.path.dirname(__file__))
            users_file_path = os.path.join(project_root, 'data', 'users', 'users.json')
        
        self.users_file_path = users_file_path
        self._users_cache = None
        self._last_modified = None
    
    def _load_users(self):
        """Load users from JSON file with caching"""
        try:
            if not os.path.exists(self.users_file_path):
                return {}
            
            # Check if file was modified
            current_modified = os.path.getmtime(self.users_file_path)
            if self._users_cache is None or current_modified != self._last_modified:
                with open(self.users_file_path, 'r', encoding='utf-8') as f:
                    self._users_cache = json.load(f)
                self._last_modified = current_modified
            
            return self._users_cache
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        users = self._load_users()
        for user_data in users.get('users', []):
            if str(user_data.get('id')) == str(user_id):
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    display_name=user_data['display_name'],
                    role=user_data['role'],
                    position=user_data.get('position'),
                    sites=user_data.get('sites', [])
                )
        return None
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        users = self._load_users()
        
        for user_data in users.get('users', []):
            if user_data['username'].lower() == username.lower():
                # Simple password check (in production, use proper hashing)
                if user_data.get('password') == password:
                    return User(
                        id=user_data['id'],
                        username=user_data['username'],
                        display_name=user_data['display_name'],
                        role=user_data['role'],
                        position=user_data.get('position'),
                        sites=user_data.get('sites', [])
                    )
        return None
    
    def get_all_users(self):
        """Get all users"""
        users = self._load_users()
        user_list = []
        
        for user_data in users.get('users', []):
            user_list.append(User(
                id=user_data['id'],
                username=user_data['username'],
                display_name=user_data['display_name'],
                role=user_data['role'],
                position=user_data.get('position'),
                sites=user_data.get('sites', [])
            ))
        
        return user_list

# Global auth manager instance
auth_manager = AuthManager()
