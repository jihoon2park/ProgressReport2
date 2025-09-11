#!/usr/bin/env python3
"""
JSON 기반 API 키 매니저
DB 대신 JSON 파일로 API 키를 관리
"""

import json
import os
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class APIKeyManagerJSON:
    """JSON 파일 기반 API 키 매니저"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.api_keys_file = os.path.join(data_dir, "api_keys", "api_keys.json")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        os.makedirs(os.path.join(self.data_dir, "api_keys"), exist_ok=True)
    
    def _load_api_keys(self) -> List[Dict[str, Any]]:
        """API 키 목록 로드"""
        try:
            if not os.path.exists(self.api_keys_file):
                return []
            
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"API 키 로드 실패: {e}")
            return []
    
    def _save_api_keys(self, api_keys: List[Dict[str, Any]]) -> bool:
        """API 키 목록 저장"""
        try:
            with open(self.api_keys_file, 'w', encoding='utf-8') as f:
                json.dump(api_keys, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"API 키 저장 실패: {e}")
            return False
    
    def get_all_api_keys(self) -> List[Dict[str, Any]]:
        """모든 API 키 조회"""
        return self._load_api_keys()
    
    def get_api_key(self, site_name: str) -> Optional[Dict[str, Any]]:
        """특정 사이트의 API 키 조회"""
        api_keys = self._load_api_keys()
        for api_key in api_keys:
            if api_key.get('site_name') == site_name:
                return api_key
        return None
    
    def add_api_key(self, site_name: str, api_key: str, server_url: str) -> bool:
        """API 키 추가"""
        api_keys = self._load_api_keys()
        
        # 기존 API 키가 있는지 확인
        for existing_key in api_keys:
            if existing_key.get('site_name') == site_name:
                logger.warning(f"API 키가 이미 존재합니다: {site_name}")
                return False
        
        # 새 API 키 추가
        new_id = max([k.get('id', 0) for k in api_keys], default=0) + 1
        new_api_key = {
            'id': new_id,
            'site_name': site_name,
            'api_key': api_key,
            'server_url': server_url,
            'server_ip': server_url.split('://')[1].split(':')[0],
            'server_port': server_url.split(':')[-1],
            'created_at': '2025-09-11T12:00:00',
            'updated_at': '2025-09-11T12:00:00'
        }
        
        api_keys.append(new_api_key)
        return self._save_api_keys(api_keys)
    
    def update_api_key(self, site_name: str, api_key: str, server_url: str) -> bool:
        """API 키 업데이트"""
        api_keys = self._load_api_keys()
        
        for i, existing_key in enumerate(api_keys):
            if existing_key.get('site_name') == site_name:
                api_keys[i].update({
                    'api_key': api_key,
                    'server_url': server_url,
                    'server_ip': server_url.split('://')[1].split(':')[0],
                    'server_port': server_url.split(':')[-1],
                    'updated_at': '2025-09-11T12:00:00'
                })
                return self._save_api_keys(api_keys)
        
        logger.warning(f"API 키를 찾을 수 없습니다: {site_name}")
        return False
    
    def delete_api_key(self, site_name: str) -> bool:
        """API 키 삭제"""
        api_keys = self._load_api_keys()
        original_count = len(api_keys)
        api_keys = [k for k in api_keys if k.get('site_name') != site_name]
        
        if len(api_keys) < original_count:
            return self._save_api_keys(api_keys)
        
        logger.warning(f"API 키를 찾을 수 없습니다: {site_name}")
        return False
    
    def get_api_headers(self, site_name: str) -> Dict[str, str]:
        """사이트에 맞는 API 헤더 반환"""
        api_key_data = self.get_api_key(site_name)
        
        if not api_key_data:
            logger.error(f"API 키를 찾을 수 없습니다: {site_name}")
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
        """서버 정보 반환"""
        api_key_data = self.get_api_key(site_name)
        
        if not api_key_data:
            logger.error(f"API 키를 찾을 수 없습니다: {site_name}")
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
        """사이트 서버 정보 반환"""
        api_keys = self._load_api_keys()
        servers = {}
        
        for api_key in api_keys:
            site_name = api_key.get('site_name')
            server_ip = api_key.get('server_ip')
            server_port = api_key.get('server_port')
            
            if site_name and server_ip and server_port:
                servers[site_name] = f"{server_ip}:{server_port}"
        
        return servers

# 전역 인스턴스
api_key_manager = APIKeyManagerJSON()

def get_api_key_manager():
    """API 키 매니저 인스턴스 반환"""
    return api_key_manager

def get_api_headers(site_name: str) -> Dict[str, str]:
    """사이트에 맞는 API 헤더 반환"""
    return api_key_manager.get_api_headers(site_name)

def get_server_info(site_name: str) -> Dict[str, str]:
    """서버 정보 반환"""
    return api_key_manager.get_server_info(site_name)

def get_site_servers() -> Dict[str, str]:
    """사이트 서버 정보 반환"""
    return api_key_manager.get_site_servers()
