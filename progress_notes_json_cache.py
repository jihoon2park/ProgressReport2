#!/usr/bin/env python3
"""
Progress Notes JSON Cache Manager
DB 대신 JSON 파일로 Progress Notes를 캐시하는 매니저
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProgressNotesJSONCache:
    """Progress Notes JSON 파일 캐시 매니저"""
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = cache_dir
        self.cache_duration = 3600  # 1시간 (초)
        
        # 캐시 디렉토리 생성
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self, site: str) -> str:
        """사이트별 캐시 파일 경로 반환"""
        safe_site = site.replace(" ", "_").lower()
        return os.path.join(self.cache_dir, f"progress_notes_{safe_site}.json")
    
    def _get_meta_file_path(self, site: str) -> str:
        """사이트별 메타데이터 파일 경로 반환"""
        safe_site = site.replace(" ", "_").lower()
        return os.path.join(self.cache_dir, f"progress_notes_{safe_site}_meta.json")
    
    def is_cache_valid(self, site: str) -> bool:
        """캐시가 유효한지 확인"""
        try:
            meta_file = self._get_meta_file_path(site)
            if not os.path.exists(meta_file):
                return False
            
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            cache_time = datetime.fromisoformat(meta.get('cached_at', ''))
            expires_at = cache_time + timedelta(seconds=self.cache_duration)
            
            return datetime.now() < expires_at
            
        except Exception as e:
            logger.error(f"캐시 유효성 확인 실패 ({site}): {e}")
            return False
    
    def get_cached_notes(self, site: str, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """캐시된 Progress Notes 조회"""
        try:
            cache_file = self._get_cache_file_path(site)
            if not os.path.exists(cache_file):
                return {
                    'success': False,
                    'data': [],
                    'pagination': {
                        'current_page': page,
                        'per_page': per_page,
                        'total_pages': 0,
                        'total_count': 0
                    },
                    'message': '캐시 파일이 없습니다'
                }
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            notes = cache_data.get('notes', [])
            total_count = len(notes)
            total_pages = (total_count + per_page - 1) // per_page
            
            # 페이지네이션 적용
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_notes = notes[start_idx:end_idx]
            
            return {
                'success': True,
                'data': paginated_notes,
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_pages': total_pages,
                    'total_count': total_count
                },
                'cached_at': cache_data.get('cached_at'),
                'message': f'캐시에서 {len(paginated_notes)}개 조회'
            }
            
        except Exception as e:
            logger.error(f"캐시 조회 실패 ({site}): {e}")
            return {
                'success': False,
                'data': [],
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'total_count': 0
                },
                'message': f'캐시 조회 실패: {e}'
            }
    
    def update_cache(self, site: str, notes: List[Dict[str, Any]]) -> bool:
        """캐시 업데이트"""
        try:
            cache_file = self._get_cache_file_path(site)
            meta_file = self._get_meta_file_path(site)
            
            # 캐시 데이터 저장
            cache_data = {
                'site': site,
                'notes': notes,
                'cached_at': datetime.now().isoformat(),
                'total_count': len(notes)
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 메타데이터 저장
            meta_data = {
                'site': site,
                'cached_at': datetime.now().isoformat(),
                'total_count': len(notes),
                'cache_duration': self.cache_duration
            }
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"캐시 업데이트 완료 - {site}: {len(notes)}개")
            return True
            
        except Exception as e:
            logger.error(f"캐시 업데이트 실패 ({site}): {e}")
            return False
    
    def clear_cache(self, site: str = None) -> bool:
        """캐시 삭제"""
        try:
            if site:
                # 특정 사이트 캐시 삭제
                cache_file = self._get_cache_file_path(site)
                meta_file = self._get_meta_file_path(site)
                
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                
                logger.info(f"캐시 삭제 완료 - {site}")
            else:
                # 모든 캐시 삭제
                for filename in os.listdir(self.cache_dir):
                    if filename.startswith('progress_notes_') and filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                
                logger.info("모든 캐시 삭제 완료")
            
            return True
            
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False
    
    def get_cache_info(self, site: str = None) -> Dict[str, Any]:
        """캐시 정보 조회"""
        try:
            if site:
                # 특정 사이트 정보
                meta_file = self._get_meta_file_path(site)
                if not os.path.exists(meta_file):
                    return {'site': site, 'cached': False}
                
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                return {
                    'site': site,
                    'cached': True,
                    'cached_at': meta.get('cached_at'),
                    'total_count': meta.get('total_count', 0),
                    'is_valid': self.is_cache_valid(site)
                }
            else:
                # 모든 사이트 정보
                cache_info = []
                for filename in os.listdir(self.cache_dir):
                    if filename.startswith('progress_notes_') and filename.endswith('_meta.json'):
                        site_name = filename.replace('progress_notes_', '').replace('_meta.json', '').replace('_', ' ').title()
                        meta_file = os.path.join(self.cache_dir, filename)
                        
                        with open(meta_file, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        
                        cache_info.append({
                            'site': site_name,
                            'cached': True,
                            'cached_at': meta.get('cached_at'),
                            'total_count': meta.get('total_count', 0),
                            'is_valid': self.is_cache_valid(site_name)
                        })
                
                return cache_info
                
        except Exception as e:
            logger.error(f"캐시 정보 조회 실패: {e}")
            return {'error': str(e)}

# 전역 인스턴스
json_cache = ProgressNotesJSONCache()
