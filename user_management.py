"""
user_management.py
User management module with admin privilege check and password validation
Includes functions for creating and deleting users
"""

import hashlib
import logging
from typing import Dict, Tuple, Optional
from flask_login import current_user

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password requirements
    
    Requirements:
    - At least 8 characters
    
    Args:
        password: Password to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    return True, None


def validate_user_data(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate user data before creation
    
    Args:
        data: User data dictionary containing:
            - username (required)
            - password (required)
            - first_name (required)
            - last_name (required)
            - role (required)
            - position (required)
            - location (required, list)
            - landing_page (optional)
            
    Returns:
        (is_valid, error_message)
    """
    # Required fields
    required_fields = ['username', 'password', 'first_name', 'last_name', 'role', 'position', 'location']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate username
    username = data.get('username', '').strip()
    if not username:
        return False, "Username cannot be empty"
    
    # Validate password
    password = data.get('password', '')
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return False, error_msg
    
    # Validate first_name
    first_name = data.get('first_name', '').strip()
    if not first_name:
        return False, "First name cannot be empty"
    
    # Validate last_name
    last_name = data.get('last_name', '').strip()
    if not last_name:
        return False, "Last name cannot be empty"
    
    # Validate role
    role = data.get('role', '').strip()
    # Only one admin exists in the system - admins cannot create other admin users
    valid_roles = ['site_admin', 'doctor', 'physiotherapist', 'nurse', 'registered_nurse', 'carer', 'clinical_manager']
    if role not in valid_roles:
        return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
    
    # Explicitly prevent admin role creation
    if role.lower() == 'admin':
        return False, "Cannot create admin users. Only one admin account exists in the system."
    
    # Validate position
    position = data.get('position', '').strip()
    if not position:
        return False, "Position cannot be empty"
    
    # Validate location
    location = data.get('location')
    if not location:
        return False, "Location is required"
    
    if isinstance(location, list):
        if len(location) == 0:
            return False, "At least one location must be selected"
    elif isinstance(location, str):
        if not location.strip():
            return False, "Location cannot be empty"
    else:
        return False, "Location must be a string or list"
    
    return True, None


def check_admin_privilege() -> Tuple[bool, Optional[str]]:
    """
    Check if current user has admin privilege
    
    Returns:
        (has_privilege, error_message)
    """
    if not current_user or not current_user.is_authenticated:
        return False, "User not authenticated"
    
    user_role = getattr(current_user, 'role', '').lower()
    if user_role != 'admin':
        logger.warning(f"Unauthorized user management attempt by {current_user.username} (role: {user_role})")
        return False, "Access denied. Only administrators can manage users."
    
    return True, None


def create_new_user(user_data: Dict, users_db: Dict) -> Tuple[bool, str]:
    """
    Create a new user in the system
    
    This function:
    1. Checks admin privilege
    2. Validates user data
    3. Validates password
    4. Checks if user already exists
    5. Creates the user
    
    Args:
        user_data: Dictionary containing user information:
            - username (required)
            - password (required)
            - first_name (required)
            - last_name (required)
            - role (required)
            - position (required)
            - location (required, list)
            - landing_page (optional)
        users_db: Reference to the USERS_DB dictionary from config_users
        
    Returns:
        (success, message)
    """
    try:
        # 1. Check admin privilege
        has_privilege, error_msg = check_admin_privilege()
        if not has_privilege:
            return False, error_msg
        
        # 2. Validate user data
        is_valid, error_msg = validate_user_data(user_data)
        if not is_valid:
            return False, error_msg
        
        # 3. Check if user already exists (case-insensitive)
        username = user_data['username'].strip()
        username_lower = username.lower()
        
        for existing_username in users_db.keys():
            if existing_username.lower() == username_lower:
                return False, f"User '{username}' already exists"
        
        # 4. Prepare user data
        new_user = {
            "password_hash": hash_password(user_data['password']),
            "first_name": user_data['first_name'].strip(),
            "last_name": user_data['last_name'].strip(),
            "role": user_data['role'].strip(),
            "position": user_data['position'].strip(),
            "location": user_data['location'] if isinstance(user_data['location'], list) else [user_data['location']]
        }
        
        # Add landing_page if provided
        if user_data.get('landing_page'):
            new_user["landing_page"] = user_data['landing_page'].strip()
        
        # 5. Add user to database
        users_db[username] = new_user
        
        logger.info(f"User created successfully: {username} by {current_user.username}")
        return True, f"User '{username}' created successfully"
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return False, f"Failed to create user: {str(e)}"


def delete_user(username: str, users_db: Dict) -> Tuple[bool, str]:
    """
    Delete a user from the system
    
    This function:
    1. Checks admin privilege
    2. Validates that user exists
    3. Prevents self-deletion
    4. Deletes the user
    
    Args:
        username: Username of the user to delete
        users_db: Reference to the USERS_DB dictionary from config_users
        
    Returns:
        (success, message)
    """
    try:
        # 1. Check admin privilege
        has_privilege, error_msg = check_admin_privilege()
        if not has_privilege:
            return False, error_msg
        
        # 2. Check if user exists (case-insensitive)
        username_lower = username.lower()
        actual_username = None
        
        for existing_username in users_db.keys():
            if existing_username.lower() == username_lower:
                actual_username = existing_username
                break
        
        if not actual_username:
            return False, f"User '{username}' not found"
        
        # 3. Prevent self-deletion
        if actual_username.lower() == current_user.username.lower():
            return False, "Cannot delete your own account"
        
        # 4. Delete the user
        del users_db[actual_username]
        
        logger.info(f"User deleted successfully: {actual_username} by {current_user.username}")
        return True, f"User '{actual_username}' deleted successfully"
        
    except KeyError:
        return False, f"User '{username}' not found"
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return False, f"Failed to delete user: {str(e)}"
