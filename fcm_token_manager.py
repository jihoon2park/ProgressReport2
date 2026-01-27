import json
import os
from typing import List, Dict, Optional
from models import FCMToken
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FCMTokenManager:
    """FCM 토큰 관리 서비스"""
    
    def __init__(self, tokens_file: str = "credential/fcm_tokens.json"):
        """
        FCM 토큰 매니저 초기화
        
        Args:
            tokens_file: 토큰을 저장할 JSON 파일 경로
        """
        self.tokens_file = tokens_file
        self.tokens: Dict[str, List[FCMToken]] = {}  # user_id -> [FCMToken]
        self.load_tokens()
    
    def load_tokens(self):
        """저장된 토큰들을 로드합니다."""
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 데이터를 FCMToken 객체로 변환
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
        """토큰들을 JSON 파일에 저장합니다."""
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(self.tokens_file), exist_ok=True)
            
            # FCMToken 객체를 딕셔너리로 변환
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
        새로운 FCM 토큰을 등록합니다.
        
        Args:
            user_id: 사용자 ID
            token: FCM 등록 토큰
            device_info: 기기 정보
            
        Returns:
            등록 성공 여부
        """
        try:
            # 기존 토큰이 있는지 확인
            if user_id not in self.tokens:
                self.tokens[user_id] = []
            
            # 동일한 토큰이 이미 있는지 확인
            existing_token = None
            for existing in self.tokens[user_id]:
                if existing.token == token:
                    existing_token = existing
                    break
            
            if existing_token:
                # 기존 토큰 업데이트
                existing_token.last_used = datetime.now()
                existing_token.device_info = device_info or existing_token.device_info
                existing_token.is_active = True
                logger.info(f"Updated existing FCM token: {user_id}")
                
                # 즉시 파일에 저장
                self.save_tokens()
                return True
            else:
                # 새 토큰 추가
                new_token = FCMToken(user_id, token, device_info)
                self.tokens[user_id].append(new_token)
                logger.info(f"Registered new FCM token: {user_id}")
            
            # 파일에 저장
            self.save_tokens()
            return True
            
        except Exception as e:
            logger.error(f"Failed to register FCM token: {e}")
            return False
    
    def unregister_token(self, user_id: str, token: str) -> bool:
        """
        FCM 토큰을 제거합니다.
        
        Args:
            user_id: 사용자 ID
            token: FCM 등록 토큰
            
        Returns:
            제거 성공 여부
        """
        try:
            if user_id not in self.tokens:
                return False
            
            # 토큰 찾아서 제거
            for i, existing_token in enumerate(self.tokens[user_id]):
                if existing_token.token == token:
                    del self.tokens[user_id][i]
                    logger.info(f"Removed FCM token: {user_id}")
                    
                    # 사용자의 모든 토큰이 제거된 경우 사용자도 제거
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
        특정 사용자의 모든 활성 FCM 토큰을 반환합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            FCM 토큰 리스트
        """
        if user_id not in self.tokens:
            return []
        
        # 활성 토큰만 반환
        active_tokens = [token for token in self.tokens[user_id] if token.is_active]
        return active_tokens
    
    def get_user_token_strings(self, user_id: str) -> List[str]:
        """
        특정 사용자의 모든 활성 FCM 토큰 문자열을 반환합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            FCM 토큰 문자열 리스트
        """
        tokens = self.get_user_tokens(user_id)
        return [token.token for token in tokens]
    
    def get_all_tokens(self) -> List[str]:
        """
        모든 활성 FCM 토큰을 반환합니다.
        
        Returns:
            모든 FCM 토큰 문자열 리스트
        """
        all_tokens = []
        for user_id in self.tokens:
            all_tokens.extend(self.get_user_token_strings(user_id))
        return all_tokens
    
    def deactivate_user_tokens(self, user_id: str) -> bool:
        """
        특정 사용자의 모든 FCM 토큰을 비활성화합니다.
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            비활성화 성공 여부
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
        오랫동안 사용되지 않은 비활성 토큰을 정리합니다.
        
        Args:
            days_threshold: 정리할 토큰의 최소 비활성 일수
            
        Returns:
            정리된 토큰 수
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
                
                # 오래된 토큰 제거
                for token in tokens_to_remove:
                    user_tokens.remove(token)
                    cleanup_count += 1
                
                # 사용자의 모든 토큰이 제거된 경우 사용자도 제거
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
        FCM 토큰의 정보를 업데이트합니다 (사용자 ID, 기기 정보).
        
        Args:
            token: 업데이트할 FCM 토큰
            new_user_id: 새로운 사용자 ID
            new_device_info: 새로운 기기 정보
            
        Returns:
            업데이트 성공 여부
        """
        try:
            # 모든 사용자에서 해당 토큰을 찾기
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
            
            # 사용자 ID가 변경된 경우
            if old_user_id != new_user_id:
                # 기존 사용자에서 토큰 제거
                self.tokens[old_user_id].remove(token_obj)
                
                # 사용자의 모든 토큰이 제거된 경우 사용자도 제거
                if not self.tokens[old_user_id]:
                    del self.tokens[old_user_id]
                
                # 새 사용자에게 토큰 추가
                if new_user_id not in self.tokens:
                    self.tokens[new_user_id] = []
                
                # 토큰 객체의 사용자 ID 업데이트
                token_obj.user_id = new_user_id
                self.tokens[new_user_id].append(token_obj)
                
                logger.info(f"FCM token user ID changed: {old_user_id} -> {new_user_id}")
            
            # 기기 정보 업데이트
            if new_device_info is not None:
                token_obj.device_info = new_device_info
                logger.info(f"FCM token device info updated: {new_device_info}")
            
            # 마지막 사용 시간 업데이트
            token_obj.last_used = datetime.now()
            
            # 파일에 저장
            self.save_tokens()
            
            logger.info(f"FCM token info updated: {token[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update FCM token info: {e}")
            return False
    
    def update_token_value(self, old_token: str, new_token: str) -> bool:
        """
        FCM 토큰 값을 새로운 토큰으로 교체합니다.
        
        Args:
            old_token: 기존 토큰
            new_token: 새로운 토큰
            
        Returns:
            업데이트 성공 여부
        """
        try:
            # 기존 토큰을 찾습니다
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
            
            # 토큰 값 업데이트
            token_obj.token = new_token
            token_obj.last_used = datetime.now()
            
            # 파일에 저장
            self.save_tokens()
            
            logger.info(f"FCM token value replaced: {old_token[:20]}... -> {new_token[:20]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to replace FCM token value: {e}")
            return False
    
    def get_token_stats(self) -> Dict:
        """
        FCM 토큰 통계를 반환합니다.
        
        Returns:
            토큰 통계 딕셔너리
        """
        total_users = len(self.tokens)
        total_tokens = sum(len(tokens) for tokens in self.tokens.values())
        active_tokens = sum(len([t for t in tokens if t.is_active]) for tokens in self.tokens.values())
        
        # 사용자별 토큰 정보를 딕셔너리로 변환
        user_tokens = {}
        for user_id, tokens in self.tokens.items():
            user_tokens[user_id] = [token.to_dict() for token in tokens]
        
        # 오늘 등록된 토큰 수 계산
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

# 전역 FCM 토큰 매니저 인스턴스
fcm_token_manager = None

def get_fcm_token_manager() -> FCMTokenManager:
    """전역 FCM 토큰 매니저 인스턴스를 반환합니다."""
    global fcm_token_manager
    if fcm_token_manager is None:
        fcm_token_manager = FCMTokenManager()
    return fcm_token_manager

def initialize_fcm_token_manager(tokens_file: str = None) -> FCMTokenManager:
    """FCM 토큰 매니저를 초기화하고 반환합니다."""
    global fcm_token_manager
    fcm_token_manager = FCMTokenManager(tokens_file)
    return fcm_token_manager
