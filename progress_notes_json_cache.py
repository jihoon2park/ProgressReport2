#!/usr/bin/env python3
"""
Progress Notes JSON Cache Manager
Manager that caches Progress Notes in JSON files instead of DB
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ProgressNotesJSONCache:
    """Progress Notes JSON file cache manager"""
    
    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = cache_dir
        self.cache_duration = 3600  # 1 hour (seconds)
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self, site: str) -> str:
        """Return cache file path for site"""
        safe_site = site.replace(" ", "_").lower()
        return os.path.join(self.cache_dir, f"progress_notes_{safe_site}.json")
    
    def _get_meta_file_path(self, site: str) -> str:
        """Return metadata file path for site"""
        safe_site = site.replace(" ", "_").lower()
        return os.path.join(self.cache_dir, f"progress_notes_{safe_site}_meta.json")
    
    def is_cache_valid(self, site: str) -> bool:
        """Check if cache is valid"""
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
            logger.error(f"Failed to validate cache ({site}): {e}")
            return False
    
    def get_cached_notes(self, site: str, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get cached Progress Notes"""
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
                    'message': 'Cache file not found'
                }
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            notes = cache_data.get('notes', [])
            total_count = len(notes)
            total_pages = (total_count + per_page - 1) // per_page
            
            # Apply pagination
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
                'message': f'Fetched {len(paginated_notes)} items from cache'
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch cache ({site}): {e}")
            return {
                'success': False,
                'data': [],
                'pagination': {
                    'current_page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'total_count': 0
                },
                'message': f'Cache fetch failed: {e}'
            }
    
    def update_cache(self, site: str, notes: List[Dict[str, Any]]) -> bool:
        """Update cache"""
        try:
            cache_file = self._get_cache_file_path(site)
            meta_file = self._get_meta_file_path(site)
            
            # Save cache data
            cache_data = {
                'site': site,
                'notes': notes,
                'cached_at': datetime.now().isoformat(),
                'total_count': len(notes)
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # Save metadata
            meta_data = {
                'site': site,
                'cached_at': datetime.now().isoformat(),
                'total_count': len(notes),
                'cache_duration': self.cache_duration
            }
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cache updated - {site}: {len(notes)} items")
            return True
            
        except Exception as e:
            logger.error(f"Cache update failed ({site}): {e}")
            return False
    
    def clear_cache(self, site: str = None) -> bool:
        """Clear cache"""
        try:
            if site:
                # Clear cache for specific site
                cache_file = self._get_cache_file_path(site)
                meta_file = self._get_meta_file_path(site)
                
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                
                logger.info(f"Cache cleared - {site}")
            else:
                # Clear all caches
                for filename in os.listdir(self.cache_dir):
                    if filename.startswith('progress_notes_') and filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                
                logger.info("All caches cleared")
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False
    
    def get_cache_info(self, site: str = None) -> Dict[str, Any]:
        """Get cache information"""
        try:
            if site:
                # Information for specific site
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
                # Information for all sites
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
            logger.error(f"Failed to fetch cache info: {e}")
            return {'error': str(e)}

# Global instance
json_cache = ProgressNotesJSONCache()
