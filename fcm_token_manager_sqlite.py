"""
SQLite 기반 FCM 토큰 관리 서비스
JSON 파일 대신 SQLite DB를 사용하여 보안과 성능을 향상
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from models import FCMToken
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FCMTokenManagerSQLite:
    """SQLite 기반 FCM 토큰 관리 클래스"""
    
    def __init__(self, db_path: str = "progress_report.db"):
        """
        FCM 토큰 매니저 초기화 (SQLite 기반)
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        logger.info(f"Initializing FCM token manager (SQLite): {db_path}")
    
    def register_token(self, user_id: str, token: str, device_info: str = None) -> bool:
        """
        새로운 FCM 토큰을 등록합니다.
        
        Args:
            user_id: 사용자 ID
            token: FCM 토큰
            device_info: 디바이스 정보
            
        Returns:
            등록 성공 여부
        """
        try:
            logger.info(f"Starting FCM token registration: user_id={user_id}, device_info={device_info}, token={token[:20]}...")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            logger.info(f"SQLite DB connection opened: {self.db_path}")
            
            # 중복 토큰 확인
            cursor.execute('''
                SELECT id FROM fcm_tokens 
                WHERE user_id = ? AND token = ?
            ''', (user_id, token))
            
            existing = cursor.fetchone()
            logger.info(f"Duplicate token check: {existing is not None}")
            
            if existing:
                # 기존 토큰 업데이트 (활성화 및 마지막 사용 시간 갱신)
                cursor.execute('''
                    UPDATE fcm_tokens 
                    SET device_info = ?, last_used = CURRENT_TIMESTAMP, is_active = 1
                    WHERE user_id = ? AND token = ?
                ''', (device_info, user_id, token))
                updated_rows = cursor.rowcount
                logger.info(f"Updated existing FCM token: {user_id}, rows updated: {updated_rows}")
            else:
                # 새 토큰 등록
                cursor.execute('''
                    INSERT INTO fcm_tokens 
                    (user_id, token, device_info, created_at, last_used, is_active)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
                ''', (user_id, token, device_info))
                inserted_id = cursor.lastrowid
                logger.info(f"Registered new FCM token: {user_id}, inserted id: {inserted_id}")
            
            conn.commit()
            logger.info(f"FCM token registration completed: {user_id}")
            
            # 등록 후 확인
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
        FCM 토큰을 비활성화합니다.
        
        Args:
            user_id: 사용자 ID (선택사항)
            token: 제거할 FCM 토큰
            
        Returns:
            제거 성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if user_id and token:
                # 사용자 ID와 토큰 모두 제공된 경우
                logger.info(f"Attempting to hard-delete FCM token: user_id={user_id}, token={token[:20]}...")
                cursor.execute('''
                    DELETE FROM fcm_tokens 
                    WHERE user_id = ? AND token = ?
                ''', (user_id, token))
            elif token:
                # 토큰만 제공된 경우 (FCM Admin Dashboard에서 호출)
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
        특정 사용자의 모든 토큰을 조회합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            FCMToken 객체 리스트
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
        특정 사용자의 활성 토큰 문자열 리스트를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            토큰 문자열 리스트
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
        모든 활성 토큰 문자열 리스트를 반환합니다.
        
        Returns:
            모든 활성 토큰 문자열 리스트
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
        토큰 정보를 업데이트합니다.
        
        Args:
            token: 업데이트할 토큰
            user_id: 새 사용자 ID (선택사항)
            device_info: 새 디바이스 정보 (선택사항)
            
        Returns:
            업데이트 성공 여부
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 업데이트할 필드들 구성
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
        비활성 토큰을 정리합니다.
        
        Args:
            days_threshold: 정리 기준 일수
            
        Returns:
            정리된 토큰 개수
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
        FCM 토큰 통계를 반환합니다.
        
        Returns:
            토큰 통계 딕셔너리
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기본 통계
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM fcm_tokens WHERE is_active = 1')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens')
            total_tokens = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1')
            active_tokens = cursor.fetchone()[0]
            
            # 오늘 등록된 토큰
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute('''
                SELECT COUNT(*) FROM fcm_tokens 
                WHERE created_at >= ?
            ''', (today.isoformat(),))
            today_tokens = cursor.fetchone()[0]
            
            # 사용자별 토큰 정보
            cursor.execute('''
                SELECT user_id, token, device_info, created_at, last_used, is_active
                FROM fcm_tokens
                ORDER BY user_id, created_at DESC
            ''')
            
            all_token_rows = cursor.fetchall()
            
            # 사용자별로 그룹화
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
        토큰 값을 교체합니다.
        
        Args:
            old_token: 기존 토큰
            new_token: 새 토큰
            
        Returns:
            교체 성공 여부
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
        """등록된 사용자 수를 반환합니다."""
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
        """모든 등록된 사용자 ID 리스트를 반환합니다."""
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
        토큰을 검색합니다 (사용자 ID 또는 디바이스 정보 기준).
        
        Args:
            search_term: 검색어
            
        Returns:
            검색된 토큰 정보 리스트
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


# 전역 FCM 토큰 매니저 인스턴스 (SQLite 기반)
fcm_token_manager_sqlite = None

def get_fcm_token_manager_sqlite() -> FCMTokenManagerSQLite:
    """SQLite 기반 FCM 토큰 매니저 싱글톤 인스턴스 반환"""
    global fcm_token_manager_sqlite
    if fcm_token_manager_sqlite is None:
        fcm_token_manager_sqlite = FCMTokenManagerSQLite()
    return fcm_token_manager_sqlite
