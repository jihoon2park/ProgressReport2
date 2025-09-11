#!/usr/bin/env python3
"""
JSON Data Manager
모든 데이터를 JSON 파일로 관리하는 통합 매니저
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

class JSONDataManager:
    """JSON 파일 기반 데이터 매니저"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._ensure_directories()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        directories = [
            self.data_dir,
            os.path.join(self.data_dir, "users"),
            os.path.join(self.data_dir, "fcm"),
            os.path.join(self.data_dir, "logs"),
            os.path.join(self.data_dir, "cache"),
            os.path.join(self.data_dir, "system"),
            os.path.join(self.data_dir, "api_keys")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _get_file_path(self, category: str, filename: str) -> str:
        """파일 경로 생성"""
        return os.path.join(self.data_dir, category, filename)
    
    def _load_json(self, file_path: str, default: Any = None) -> Any:
        """JSON 파일 로드"""
        try:
            if not os.path.exists(file_path):
                return default
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 로드 실패 ({file_path}): {e}")
            return default
    
    def _save_json(self, file_path: str, data: Any) -> bool:
        """JSON 파일 저장"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"JSON 저장 실패 ({file_path}): {e}")
            return False
    
    # ===========================================
    # 사용자 관리
    # ===========================================
    
    def get_users(self) -> List[Dict[str, Any]]:
        """사용자 목록 조회"""
        return self._load_json(self._get_file_path("users", "users.json"), [])
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """특정 사용자 조회"""
        users = self.get_users()
        for user in users:
            if user.get('username') == username:
                return user
        return None
    
    def save_user(self, user_data: Dict[str, Any]) -> bool:
        """사용자 저장/업데이트"""
        users = self.get_users()
        
        # 기존 사용자 찾기
        for i, user in enumerate(users):
            if user.get('username') == user_data.get('username'):
                users[i] = user_data
                break
        else:
            # 새 사용자 추가
            users.append(user_data)
        
        return self._save_json(self._get_file_path("users", "users.json"), users)
    
    def delete_user(self, username: str) -> bool:
        """사용자 삭제"""
        users = self.get_users()
        users = [user for user in users if user.get('username') != username]
        return self._save_json(self._get_file_path("users", "users.json"), users)
    
    # ===========================================
    # FCM 토큰 관리
    # ===========================================
    
    def get_fcm_tokens(self) -> List[Dict[str, Any]]:
        """FCM 토큰 목록 조회"""
        return self._load_json(self._get_file_path("fcm", "tokens.json"), [])
    
    def save_fcm_token(self, token_data: Dict[str, Any]) -> bool:
        """FCM 토큰 저장/업데이트"""
        tokens = self.get_fcm_tokens()
        
        # 기존 토큰 찾기
        for i, token in enumerate(tokens):
            if (token.get('user_id') == token_data.get('user_id') and 
                token.get('token') == token_data.get('token')):
                tokens[i] = token_data
                break
        else:
            # 새 토큰 추가
            tokens.append(token_data)
        
        return self._save_json(self._get_file_path("fcm", "tokens.json"), tokens)
    
    def delete_fcm_token(self, user_id: str, token: str) -> bool:
        """FCM 토큰 삭제"""
        tokens = self.get_fcm_tokens()
        tokens = [t for t in tokens if not (t.get('user_id') == user_id and t.get('token') == token)]
        return self._save_json(self._get_file_path("fcm", "tokens.json"), tokens)
    
    # ===========================================
    # 로그 관리
    # ===========================================
    
    def get_access_logs(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """접근 로그 조회"""
        return self._load_json(self._get_file_path("logs", "access_logs.json"), [])[-limit:]
    
    def save_access_log(self, log_data: Dict[str, Any]) -> bool:
        """접근 로그 저장"""
        logs = self.get_access_logs(limit=10000)  # 더 많은 로그 로드
        logs.append(log_data)
        
        # 최신 1000개만 유지
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        return self._save_json(self._get_file_path("logs", "access_logs.json"), logs)
    
    def get_progress_note_logs(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Progress Note 로그 조회"""
        return self._load_json(self._get_file_path("logs", "progress_note_logs.json"), [])[-limit:]
    
    def save_progress_note_log(self, log_data: Dict[str, Any]) -> bool:
        """Progress Note 로그 저장"""
        logs = self.get_progress_note_logs(limit=10000)
        logs.append(log_data)
        
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        return self._save_json(self._get_file_path("logs", "progress_note_logs.json"), logs)
    
    # ===========================================
    # 캐시 데이터 관리
    # ===========================================
    
    def get_clients_cache(self, site: str = None) -> List[Dict[str, Any]]:
        """클라이언트 캐시 조회"""
        if site:
            filename = f"clients_{site.replace(' ', '_').lower()}.json"
            return self._load_json(self._get_file_path("cache", filename), [])
        else:
            # 모든 사이트의 클라이언트 데이터
            all_clients = []
            for filename in os.listdir(os.path.join(self.data_dir, "cache")):
                if filename.startswith("clients_") and filename.endswith(".json"):
                    site_clients = self._load_json(self._get_file_path("cache", filename), [])
                    all_clients.extend(site_clients)
            return all_clients
    
    def save_clients_cache(self, site: str, clients: List[Dict[str, Any]]) -> bool:
        """클라이언트 캐시 저장"""
        filename = f"clients_{site.replace(' ', '_').lower()}.json"
        return self._save_json(self._get_file_path("cache", filename), clients)
    
    def get_care_areas(self) -> List[Dict[str, Any]]:
        """케어 영역 데이터 조회"""
        return self._load_json(self._get_file_path("cache", "care_areas.json"), [])
    
    def save_care_areas(self, care_areas: List[Dict[str, Any]]) -> bool:
        """케어 영역 데이터 저장"""
        return self._save_json(self._get_file_path("cache", "care_areas.json"), care_areas)
    
    def get_event_types(self) -> List[Dict[str, Any]]:
        """이벤트 타입 데이터 조회"""
        return self._load_json(self._get_file_path("cache", "event_types.json"), [])
    
    def save_event_types(self, event_types: List[Dict[str, Any]]) -> bool:
        """이벤트 타입 데이터 저장"""
        return self._save_json(self._get_file_path("cache", "event_types.json"), event_types)
    
    def get_incidents_cache(self, site: str = None) -> List[Dict[str, Any]]:
        """인시던트 캐시 조회"""
        if site:
            filename = f"incidents_{site.replace(' ', '_').lower()}.json"
            return self._load_json(self._get_file_path("cache", filename), [])
        else:
            all_incidents = []
            for filename in os.listdir(os.path.join(self.data_dir, "cache")):
                if filename.startswith("incidents_") and filename.endswith(".json"):
                    site_incidents = self._load_json(self._get_file_path("cache", filename), [])
                    all_incidents.extend(site_incidents)
            return all_incidents
    
    def save_incidents_cache(self, site: str, incidents: List[Dict[str, Any]]) -> bool:
        """인시던트 캐시 저장"""
        filename = f"incidents_{site.replace(' ', '_').lower()}.json"
        return self._save_json(self._get_file_path("cache", filename), incidents)
    
    # ===========================================
    # 시스템 데이터 관리
    # ===========================================
    
    def get_sites(self) -> List[Dict[str, Any]]:
        """사이트 목록 조회"""
        return self._load_json(self._get_file_path("system", "sites.json"), [])
    
    def save_sites(self, sites: List[Dict[str, Any]]) -> bool:
        """사이트 목록 저장"""
        return self._save_json(self._get_file_path("system", "sites.json"), sites)
    
    def get_sync_status(self) -> List[Dict[str, Any]]:
        """동기화 상태 조회"""
        return self._load_json(self._get_file_path("system", "sync_status.json"), [])
    
    def save_sync_status(self, sync_status: List[Dict[str, Any]]) -> bool:
        """동기화 상태 저장"""
        return self._save_json(self._get_file_path("system", "sync_status.json"), sync_status)
    
    # ===========================================
    # API 키 관리
    # ===========================================
    
    def get_api_keys(self) -> List[Dict[str, Any]]:
        """API 키 목록 조회"""
        return self._load_json(self._get_file_path("api_keys", "api_keys.json"), [])
    
    def save_api_key(self, api_key_data: Dict[str, Any]) -> bool:
        """API 키 저장/업데이트"""
        api_keys = self.get_api_keys()
        
        # 기존 API 키 찾기
        for i, key in enumerate(api_keys):
            if key.get('site_name') == api_key_data.get('site_name'):
                api_keys[i] = api_key_data
                break
        else:
            # 새 API 키 추가
            api_keys.append(api_key_data)
        
        return self._save_json(self._get_file_path("api_keys", "api_keys.json"), api_keys)
    
    def delete_api_key(self, site_name: str) -> bool:
        """API 키 삭제"""
        api_keys = self.get_api_keys()
        api_keys = [key for key in api_keys if key.get('site_name') != site_name]
        return self._save_json(self._get_file_path("api_keys", "api_keys.json"), api_keys)
    
    # ===========================================
    # 유틸리티 메서드
    # ===========================================
    
    def get_data_info(self) -> Dict[str, Any]:
        """데이터 현황 조회"""
        info = {
            'users': len(self.get_users()),
            'fcm_tokens': len(self.get_fcm_tokens()),
            'access_logs': len(self.get_access_logs()),
            'progress_note_logs': len(self.get_progress_note_logs()),
            'sites': len(self.get_sites()),
            'api_keys': len(self.get_api_keys())
        }
        
        # 캐시 데이터 개수
        cache_dir = os.path.join(self.data_dir, "cache")
        if os.path.exists(cache_dir):
            cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
            info['cache_files'] = len(cache_files)
        
        return info
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """오래된 로그 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        # 접근 로그 정리
        access_logs = self.get_access_logs(limit=10000)
        original_count = len(access_logs)
        access_logs = [log for log in access_logs 
                      if datetime.fromisoformat(log.get('timestamp', '1970-01-01')) > cutoff_date]
        if len(access_logs) < original_count:
            self._save_json(self._get_file_path("logs", "access_logs.json"), access_logs)
            cleaned_count += original_count - len(access_logs)
        
        # Progress Note 로그 정리
        progress_logs = self.get_progress_note_logs(limit=10000)
        original_count = len(progress_logs)
        progress_logs = [log for log in progress_logs 
                        if datetime.fromisoformat(log.get('timestamp', '1970-01-01')) > cutoff_date]
        if len(progress_logs) < original_count:
            self._save_json(self._get_file_path("logs", "progress_note_logs.json"), progress_logs)
            cleaned_count += original_count - len(progress_logs)
        
        return cleaned_count

# 전역 인스턴스
json_data_manager = JSONDataManager()
