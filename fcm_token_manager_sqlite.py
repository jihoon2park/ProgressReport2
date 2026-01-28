"""
SQLite-based FCM Token Management Service
Uses SQLite DB instead of JSON files to improve security and performance
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from models import FCMToken
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FCMTokenManagerSQLite:
    """SQLite-based FCM Token Management Class"""
    
    def __init__(self, db_path: str = "progress_report.db"):
        """
        Initialize FCM Token Manager (SQLite-based)
        
        Args:
            db_path: SQLite database file path
        """
        self.db_path = db_path
        logger.info(f"Initializing FCM token manager (SQLite): {db_path}")
    
    def register_token(self, user_id: str, token: str, device_info: str = None) -> bool:
        """
        Register new FCM token.
        
        Args:
            user_id: User ID
            token: FCM token
            device_info: Device information
            
        Returns:
            Registration success status
        """
        try:
            logger.info(f"Starting FCM token registration: user_id={user_id}, device_info={device_info}, token={token[:20]}...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            logger.info(f"SQLite DB connection opened: {self.db_path}")
            
            # Check for duplicate token
            cursor.execute('''
                SELECT id FROM fcm_tokens 
                WHERE user_id = ? AND token = ?
            ''', (user_id, token))
            
            existing = cursor.fetchone()
            logger.info(f"Duplicate token check: {existing is not None}")
            
            if existing:
                # Update existing token (activate and update last used time)
                cursor.execute('''
                    UPDATE fcm_tokens 
                    SET device_info = ?, last_used = CURRENT_TIMESTAMP, is_active = 1
                    WHERE user_id = ? AND token = ?
                ''', (device_info, user_id, token))
                updated_rows = cursor.rowcount
                logger.info(f"Updated existing FCM token: {user_id}, rows updated: {updated_rows}")
            else:
                # Register new token
                cursor.execute('''
                    INSERT INTO fcm_tokens 
                    (user_id, token, device_info, created_at, last_used, is_active)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (user_id, token, device_info))
                inserted_id = cursor.lastrowid
                logger.info(f"Registered new FCM token: {user_id}, inserted id: {inserted_id}")
            
            conn.commit()
            logger.info(f"FCM token registration completed: {user_id}")
            
            # Verify after registration
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE user_id = ? AND is_active = 1', (user_id,))
            user_token_count = cursor.fetchone()[0]
            logger.info(f"Active token count for user {user_id}: {user_token_count}")
            
            return True
            
        except Exception as e:
            logger.error(f"FCM token registration failed - user_id: {user_id}, error: {e}")
            import traceback
            logger.error(f"FCM token registration stack trace: {traceback.format_exc()}")
            return False
        finally:
            if conn:
                conn.close()
                logger.info("SQLite DB connection closed")
    
    def unregister_token(self, user_id: str = None, token: str = None) -> bool:
        """
        Deactivate FCM token.
        
        Args:
            user_id: User ID (optional)
            token: FCM token to remove
            
        Returns:
            Removal success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id and token:
                # Both user_id and token provided
                logger.info(f"Attempting to hard-delete FCM token: user_id={user_id}, token={token[:20]}...")
                cursor.execute('''
                    DELETE FROM fcm_tokens 
                    WHERE user_id = ? AND token = ?
                ''', (user_id, token))
            elif token:
                # Only token provided (called from FCM Admin Dashboard)
                logger.info(f"Attempting to hard-delete FCM token (token only): token={token[:20]}...")
                cursor.execute('''
                    DELETE FROM fcm_tokens 
                    WHERE token = ?
                ''', (token,))
            else:
                logger.error("Failed to remove FCM token: user_id or token is required")
                return False
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"FCM token hard-delete succeeded: {cursor.rowcount} tokens")
                return True
            else:
                logger.warning(f"FCM token to delete not found: user_id={user_id}, token={token[:20] if token else 'None'}...")
                return False
            
        except Exception as e:
            logger.error(f"Failed to remove FCM token: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_user_tokens(self, user_id: str) -> List[FCMToken]:
        """
        Query all tokens for specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of FCMToken objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, token, device_info, created_at, last_used, is_active
                FROM fcm_tokens
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            token_rows = cursor.fetchall()
            
            tokens = []
            for row in token_rows:
                token = FCMToken(
                    user_id=row[0],
                    token=row[1],
                    device_info=row[2],
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    last_used=datetime.fromisoformat(row[4]) if row[4] else None,
                    is_active=bool(row[5])
                )
                tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to fetch user tokens: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_user_token_strings(self, user_id: str) -> List[str]:
        """
        Return list of active token strings for specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of token strings
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT token FROM fcm_tokens
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_used DESC
            ''', (user_id,))
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to fetch user token strings: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_all_tokens(self) -> List[str]:
        """
        Return list of all active token strings.
        
        Returns:
            List of all active token strings
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT token FROM fcm_tokens
                WHERE is_active = 1
                ORDER BY last_used DESC
            ''')
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to fetch all tokens: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def update_token_info(self, token: str, user_id: str = None, device_info: str = None) -> bool:
        """
        Update token information.
        
        Args:
            token: Token to update
            user_id: New user ID (optional)
            device_info: New device information (optional)
            
        Returns:
            Update success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Compose fields to update
            update_fields = []
            update_values = []
            
            if user_id is not None:
                update_fields.append("user_id = ?")
                update_values.append(user_id)
            
            if device_info is not None:
                update_fields.append("device_info = ?")
                update_values.append(device_info)
            
            if not update_fields:
                return False
            
            update_fields.append("last_used = CURRENT_TIMESTAMP")
            update_values.append(token)
            
            query = f'''
                UPDATE fcm_tokens 
                SET {", ".join(update_fields)}
                WHERE token = ?
            '''
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Updated FCM token info: {token[:20]}...")
                return True
            else:
                logger.warning(f"Token to update not found: {token[:20]}...")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update FCM token info: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def cleanup_inactive_tokens(self, days_threshold: int = 30) -> int:
        """
        Clean up inactive tokens.
        
        Args:
            days_threshold: Days threshold for cleanup
            
        Returns:
            Number of cleaned up tokens
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            cursor.execute('''
                DELETE FROM fcm_tokens 
                WHERE is_active = 0 
                  AND (last_used < ? OR last_used IS NULL)
            ''', (cutoff_date.isoformat(),))
            
            cleanup_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Inactive FCM tokens cleaned up: {cleanup_count}")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Failed to clean up FCM tokens: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_token_stats(self) -> Dict:
        """
        Return FCM token statistics.
        
        Returns:
            Token statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Basic statistics
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM fcm_tokens WHERE is_active = 1')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens')
            total_tokens = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
            active_tokens = cursor.fetchone()[0]
            
            # Tokens registered today
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute('''
                SELECT COUNT(*) FROM fcm_tokens 
                WHERE created_at >= ?
            ''', (today.isoformat(),))
            today_tokens = cursor.fetchone()[0]
            
            # Token information by user
            cursor.execute('''
                SELECT user_id, token, device_info, created_at, last_used, is_active
                FROM fcm_tokens
                ORDER BY user_id, created_at DESC
            ''')
            
            all_token_rows = cursor.fetchall()
            
            # Group by user
            user_tokens = {}
            for row in all_token_rows:
                user_id = row[0]
                if user_id not in user_tokens:
                    user_tokens[user_id] = []
                
                user_tokens[user_id].append({
                    'token': row[1],
                    'device_info': row[2],
                    'created_at': row[3],
                    'last_used': row[4],
                    'is_active': bool(row[5])
                })
            
            return {
                'total_users': total_users,
                'total_tokens': total_tokens,
                'active_tokens': active_tokens,
                'inactive_tokens': total_tokens - active_tokens,
                'today_tokens': today_tokens,
                'user_tokens': user_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch FCM stats: {e}")
            return {
                'total_users': 0,
                'total_tokens': 0,
                'active_tokens': 0,
                'inactive_tokens': 0,
                'today_tokens': 0,
                'user_tokens': {}
            }
        finally:
            if conn:
                conn.close()
    
    def update_token_value(self, old_token: str, new_token: str) -> bool:
        """
        Replace token value.
        
        Args:
            old_token: Existing token
            new_token: New token
            
        Returns:
            Replacement success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE fcm_tokens 
                SET token = ?, last_used = CURRENT_TIMESTAMP
                WHERE token = ?
            ''', (new_token, old_token))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"Replacing FCM token value: {old_token[:20]}... -> {new_token[:20]}...")
                return True
            else:
                logger.warning(f"Token to replace not found: {old_token[:20]}...")
                return False
            
        except Exception as e:
            logger.error(f"Failed to replace FCM token value: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_user_count(self) -> int:
        """Return number of registered users."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM fcm_tokens WHERE is_active = 1')
            return cursor.fetchone()[0]
            
        except Exception as e:
            logger.error(f"Failed to fetch user count: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_all_user_ids(self) -> List[str]:
        """Return list of all registered user IDs."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT user_id FROM fcm_tokens 
                WHERE is_active = 1
                ORDER BY user_id
            ''')
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to fetch user ID list: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def search_tokens(self, search_term: str) -> List[Dict]:
        """
        Search tokens (by user ID or device information).
        
        Args:
            search_term: Search term
            
        Returns:
            List of searched token information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, token, device_info, created_at, last_used, is_active
                FROM fcm_tokens
                WHERE (user_id LIKE ? OR device_info LIKE ?)
                  AND is_active = 1
                ORDER BY last_used DESC
            ''', (f'%{search_term}%', f'%{search_term}%'))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'user_id': row[0],
                    'token': row[1],
                    'device_info': row[2],
                    'created_at': row[3],
                    'last_used': row[4],
                    'is_active': bool(row[5])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"FCM token search failed: {e}")
            return []
        finally:
            if conn:
                conn.close()


# Global FCM token manager instance (SQLite-based)
fcm_token_manager_sqlite = None

def get_fcm_token_manager_sqlite() -> FCMTokenManagerSQLite:
    """Return SQLite-based FCM token manager singleton instance"""
    global fcm_token_manager_sqlite
    if fcm_token_manager_sqlite is None:
        fcm_token_manager_sqlite = FCMTokenManagerSQLite()
    return fcm_token_manager_sqlite
