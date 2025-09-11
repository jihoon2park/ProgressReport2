#!/usr/bin/env python3
"""
API 키 관리자 - 데이터베이스에서 API 키를 안전하게 관리
"""

import sqlite3
import os
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class APIKeyManager:
    """API 키 관리자 - DB에 평문으로 저장 및 관리"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        # 테이블 생성
        self._create_table()
    
    def _create_table(self):
        """API 키 테이블 생성"""
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
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_site ON api_keys(site_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)')
        
        conn.commit()
        conn.close()
    
    # 암호화 제거 - 평문으로 저장
    
    def add_api_key(self, site_name: str, api_username: str, api_key: str, 
                   server_ip: str, server_port: int = 8080, notes: str = "") -> bool:
        """새 API 키 추가"""
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
            
            logger.info(f"API 키 추가/업데이트 완료: {site_name}")
            return True
            
        except Exception as e:
            logger.error(f"API 키 추가 실패 ({site_name}): {e}")
            return False
    
    def get_api_key(self, site_name: str) -> Optional[Dict]:
        """사이트별 API 키 조회 (복호화된 키 포함)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 먼저 api_key 컬럼이 있는지 확인
            cursor.execute("PRAGMA table_info(api_keys)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'api_key' in columns:
                # 새로운 스키마 (평문 API 키)
                cursor.execute('''
                    SELECT site_name, api_username, api_key, server_ip, server_port, is_active, notes
                    FROM api_keys 
                    WHERE site_name = ? AND is_active = 1
                ''', (site_name,))
            else:
                # 기존 스키마 (암호화된 API 키) - 폴백 사용
                logger.warning(f"api_key 컬럼이 없음, 폴백 사용: {site_name}")
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
            logger.error(f"API 키 조회 실패 ({site_name}): {e}")
            return None
    
    def get_all_api_keys(self) -> List[Dict]:
        """모든 활성 API 키 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 먼저 api_key 컬럼이 있는지 확인
            cursor.execute("PRAGMA table_info(api_keys)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'api_key' in columns:
                # 새로운 스키마 (평문 API 키)
                cursor.execute('''
                    SELECT site_name, api_username, api_key, server_ip, server_port, is_active, notes
                    FROM api_keys 
                    WHERE is_active = 1
                    ORDER BY site_name
                ''')
            else:
                # 기존 스키마 (암호화된 API 키) - 빈 결과 반환
                logger.warning("api_key 컬럼이 없음, 빈 결과 반환")
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
            logger.error(f"모든 API 키 조회 실패: {e}")
            return []
    
    def update_api_key(self, site_name: str, api_key: str = None, 
                      server_ip: str = None, server_port: int = None, 
                      is_active: bool = None, notes: str = None) -> bool:
        """API 키 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 기존 데이터 조회
            cursor.execute('SELECT * FROM api_keys WHERE site_name = ?', (site_name,))
            existing = cursor.fetchone()
            
            if not existing:
                logger.error(f"API 키를 찾을 수 없습니다: {site_name}")
                return False
            
            # 업데이트할 필드들
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
                logger.info(f"API 키 업데이트 완료: {site_name}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"API 키 업데이트 실패 ({site_name}): {e}")
            return False
    
    def deactivate_api_key(self, site_name: str) -> bool:
        """API 키 비활성화"""
        return self.update_api_key(site_name, is_active=False)
    
    def get_api_headers(self, site_name: str) -> Optional[Dict[str, str]]:
        """사이트별 API 헤더 반환 (기존 get_api_headers 함수 대체)"""
        api_data = self.get_api_key(site_name)
        
        if not api_data:
            logger.error(f"API 키를 찾을 수 없습니다: {site_name}")
            return None
        
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-username': api_data['api_username'],
            'x-api-key': api_data['api_key']
        }
    
    def get_server_info(self, site_name: str) -> Optional[Dict[str, str]]:
        """사이트별 서버 정보 반환"""
        api_data = self.get_api_key(site_name)
        
        if not api_data:
            return None
        
        return {
            'server_ip': api_data['server_ip'],
            'server_port': str(api_data['server_port']),
            'base_url': f"http://{api_data['server_ip']}:{api_data['server_port']}"
        }


# 전역 인스턴스
_api_key_manager = None

def get_api_key_manager():
    """API 키 매니저 싱글톤 인스턴스"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager

def get_api_headers(site_name: str) -> Optional[Dict[str, str]]:
    """기존 함수와 호환성을 위한 래퍼"""
    manager = get_api_key_manager()
    return manager.get_api_headers(site_name)

def get_server_info(site_name: str) -> Optional[Dict[str, str]]:
    """서버 정보 조회"""
    manager = get_api_key_manager()
    return manager.get_server_info(site_name)

def get_site_servers() -> Dict[str, str]:
    """모든 사이트 서버 정보 조회"""
    manager = get_api_key_manager()
    servers = {}
    
    for api_data in manager.get_all_api_keys():
        servers[api_data['site_name']] = f"{api_data['server_ip']}:{api_data['server_port']}"
    
    return servers
