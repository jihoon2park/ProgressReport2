import json
import os
from typing import List, Dict, Optional
from models import FCMToken
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FCMTokenManager:
    """FCM token management service"""
    
    def __init__(self, tokens_file: str = "credential/fcm_tokens.json"):
        """
        Initialize FCM token manager
        
        Args:
            tokens_file: JSON file path to save tokens
        """
        self.tokens_file = tokens_file
        self.tokens: Dict[str, List[FCMToken]] = {}  # user_id -> [FCMToken]
        self.load_tokens()
    
    def load_tokens(self):
        """Load saved tokens"""
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Convert data to FCMToken objects
                for user_id, tokens_data in data.items():
                    self.tokens[user_id] = []
                    for token_data in tokens_data:
                        try:
                            token_obj = FCMToken.from_dict(token_data)
                            self.tokens[user_id].append(token_obj)
                        except Exception as e:
                            logger.error(f"Error loading token (user: {user_id}): {e}")
                
                logger.info(f"FCM tokens loaded: {len(self.tokens)} users")
            else:
                logger.info("FCM token file does not exist. Creating a new one.")
                self.save_tokens()
                
        except Exception as e:
            logger.error(f"Failed to load FCM tokens: {e}")
            self.tokens = {}
    
    def save_tokens(self):
        """Save tokens to JSON file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
            
            # Convert FCMToken objects to dictionaries
            data = {}
            for user_id, tokens in self.tokens.items():
                data[user_id] = [token.to_dict() for token in tokens]
            
            with open(self.tokens_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"FCM tokens saved: {len(self.tokens)} users")
            
        except Exception as e:
            logger.error(f"Failed to save FCM tokens: {e}")
    
    def register_token(self, user_id: str, token: str, device_info: str = None) -> bool:
        """
        Register new FCM token
        
        Args:
            user_id: User ID
            token: FCM registration token
            device_info: Device information
            
        Returns:
            Registration success status
        """
        try:
            # Check if existing tokens exist
            if user_id not in self.tokens:
                self.tokens[user_id] = []
            
            # Check if same token already exists
            existing_token = None
            for existing in self.tokens[user_id]:
                if existing.token == token:
                    existing_token = existing
                    break
            
            if existing_token:
                # Update existing token
                existing_token.last_used = datetime.now()
                existing_token.device_info = device_info or existing_token.device_info
                existing_token.is_active = True
                logger.info(f"Updated existing FCM token: {user_id}")
                
                # Save to file immediately
                self.save_tokens()
                return True
            else:
                # Add new token
                new_token = FCMToken(user_id, token, device_info)
                self.tokens[user_id].append(new_token)
                logger.info(f"Registered new FCM token: {user_id}")
            
            # Save to file
            self.save_tokens()
            return True
            
        except Exception as e:
            logger.error(f"Failed to register FCM token: {e}")
            return False
    
    def unregister_token(self, user_id: str, token: str) -> bool:
        """
        Remove FCM token
        
        Args:
            user_id: User ID
            token: FCM registration token
            
        Returns:
            Removal success status
        """
        try:
            if user_id not in self.tokens:
                return False
            
            # Find and remove token
            for i, existing_token in enumerate(self.tokens[user_id]):
                if existing_token.token == token:
                    del self.tokens[user_id][i]
                    logger.info(f"Removed FCM token: {user_id}")
                    
                    # Remove user if all tokens are removed
                    if not self.tokens[user_id]:
                        del self.tokens[user_id]
                    
                    self.save_tokens()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove FCM token: {e}")
            return False
    
    def get_user_tokens(self, user_id: str) -> List[FCMToken]:
        """
        Return all active FCM tokens for specific user
        
        Args:
            user_id: User ID
            
        Returns:
            FCM token list
        """
        if user_id not in self.tokens:
            return []
        
        # Return only active tokens
        active_tokens = [token for token in self.tokens[user_id] if token.is_active]
        return active_tokens
    
    def get_user_token_strings(self, user_id: str) -> List[str]:
        """
        Return all active FCM token strings for specific user
        
        Args:
            user_id: User ID
            
        Returns:
            FCM token string list
        """
        tokens = self.get_user_tokens(user_id)
        return [token.token for token in tokens]
    
    def get_all_tokens(self) -> List[str]:
        """
        Return all active FCM tokens
        
        Returns:
            All FCM token string list
        """
        all_tokens = []
        for user_id in self.tokens:
            all_tokens.extend(self.get_user_token_strings(user_id))
        return all_tokens
    
    def deactivate_user_tokens(self, user_id: str) -> bool:
        """
        Deactivate all FCM tokens for specific user
        
        Args:
            user_id: User ID
            
        Returns:
            Deactivation success status
        """
        try:
            if user_id not in self.tokens:
                return False
            
            for token in self.tokens[user_id]:
                token.is_active = False
            
            self.save_tokens()
            logger.info(f"Deactivated user's FCM tokens: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate user's FCM tokens: {e}")
            return False
    
    def cleanup_inactive_tokens(self, days_threshold: int = 30) -> int:
        """
        Clean up inactive tokens that haven't been used for a long time
        
        Args:
            days_threshold: Minimum inactive days for tokens to be cleaned up
            
        Returns:
            Number of cleaned up tokens
        """
        try:
            cleanup_count = 0
            threshold_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            threshold_date = threshold_date.replace(day=threshold_date.day - days_threshold)
            
            for user_id in list(self.tokens.keys()):
                user_tokens = self.tokens[user_id]
                tokens_to_remove = []
                
                for token in user_tokens:
                    if not token.is_active and token.last_used < threshold_date:
                        tokens_to_remove.append(token)
                
                # Remove old tokens
                for token in tokens_to_remove:
                    user_tokens.remove(token)
                    cleanup_count += 1
                
                # Remove user if all tokens are removed
                if not user_tokens:
                    del self.tokens[user_id]
            
            if cleanup_count > 0:
                self.save_tokens()
                logger.info(f"Inactive FCM tokens cleaned up: {cleanup_count}")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to clean up FCM tokens: {e}")
            return 0
    
    def update_token_info(self, token: str, new_user_id: str, new_device_info: str = None) -> bool:
        """
        Update FCM token information (user ID, device information)
        
        Args:
            token: FCM token to update
            new_user_id: New user ID
            new_device_info: New device information
            
        Returns:
            Update success status
        """
        try:
            # Find the token from all users
            old_user_id = None
            token_obj = None
            
            for user_id, tokens in self.tokens.items():
                for t in tokens:
                    if t.token == token:
                        old_user_id = user_id
                        token_obj = t
                        break
                if token_obj:
                    break
            
            if not token_obj:
                logger.warning(f"FCM token to update not found: {token[:20]}...")
                return False
            
            # If user ID changed
            if old_user_id != new_user_id:
                # Remove token from old user
                self.tokens[old_user_id].remove(token_obj)
                
                # Remove user if all tokens are removed
                if not self.tokens[old_user_id]:
                    del self.tokens[old_user_id]
                
                # Add token to new user
                if new_user_id not in self.tokens:
                    self.tokens[new_user_id] = []
                
                # Update token object's user ID
                token_obj.user_id = new_user_id
                self.tokens[new_user_id].append(token_obj)
                
                logger.info(f"FCM token user ID changed: {old_user_id} -> {new_user_id}")
            
            # Update device information
            if new_device_info is not None:
                token_obj.device_info = new_device_info
                logger.info(f"FCM token device info updated: {new_device_info}")
            
            # Update last used time
            token_obj.last_used = datetime.now()
            
            # Save to file
            self.save_tokens()
            
            logger.info(f"FCM token info updated: {token[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update FCM token info: {e}")
            return False
    
    def update_token_value(self, old_token: str, new_token: str) -> bool:
        """
        Replace FCM token value with new token
        
        Args:
            old_token: Existing token
            new_token: New token
            
        Returns:
            Update success status
        """
        try:
            # Find existing token
            token_obj = None
            user_id = None
            
            for uid, tokens in self.tokens.items():
                for t in tokens:
                    if t.token == old_token:
                        token_obj = t
                        user_id = uid
                        break
                if token_obj:
                    break
            
            if not token_obj:
                logger.warning(f"FCM token to replace not found: {old_token[:20]}...")
                return False
            
            # Update token value
            token_obj.token = new_token
            token_obj.last_used = datetime.now()
            
            # Save to file
            self.save_tokens()
            
            logger.info(f"FCM token value replaced: {old_token[:20]}... -> {new_token[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to replace FCM token value: {e}")
            return False
    
    def get_token_stats(self) -> Dict:
        """
        Return FCM token statistics
        
        Returns:
            Token statistics dictionary
        """
        total_users = len(self.tokens)
        total_tokens = sum(len(tokens) for tokens in self.tokens.values())
        active_tokens = sum(len([t for t in tokens if t.is_active]) for tokens in self.tokens.values())
        
        # Convert user token information to dictionary
        user_tokens = {}
        for user_id, tokens in self.tokens.items():
            user_tokens[user_id] = [token.to_dict() for token in tokens]
        
        # Calculate number of tokens registered today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_tokens = 0
        for tokens in self.tokens.values():
            for token in tokens:
                if token.created_at and token.created_at >= today:
                    today_tokens += 1
        
        return {
            'total_users': total_users,
            'total_tokens': total_tokens,
            'active_tokens': active_tokens,
            'inactive_tokens': total_tokens - active_tokens,
            'today_tokens': today_tokens,
            'user_tokens': user_tokens
        }

# Global FCM token manager instance
fcm_token_manager = None

def get_fcm_token_manager() -> FCMTokenManager:
    """Return global FCM token manager instance"""
    global fcm_token_manager
    if fcm_token_manager is None:
        fcm_token_manager = FCMTokenManager()
    return fcm_token_manager

def initialize_fcm_token_manager(tokens_file: str = None) -> FCMTokenManager:
    """Initialize and return FCM token manager"""
    global fcm_token_manager
    fcm_token_manager = FCMTokenManager(tokens_file)
    return fcm_token_manager
