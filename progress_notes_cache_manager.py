#!/usr/bin/env python3
"""
Progress Notes Cache Manager
Supports hybrid caching and pagination
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class ProgressNotesCacheManager:
    """Progress Notes Cache Management Class"""
    
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.cache_duration_hours = 1  # Cache valid for 1 hour
        self.max_cache_days = 30  # Delete data older than 30 days
        
    def get_db_connection(self):
        """Database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_cached_notes(self, site: str, page: int = 1, per_page: int = 50, 
                        days: int = 7, use_hybrid: bool = True) -> Dict:
        """
        Query Progress Notes with hybrid caching
        
        Args:
            site: Site name
            page: Page number (starts from 1)
            per_page: Number of items per page
            days: Number of days to query
            use_hybrid: Whether to use hybrid caching
            
        Returns:
            {
                'notes': List[Dict],
                'total_count': int,
                'page': int,
                'per_page': int,
                'total_pages': int,
                'cache_status': str,
                'last_sync': str
            }
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. Check cache status
            cache_status = self._check_cache_status(site, days)
            
            if use_hybrid and cache_status['is_fresh']:
                # 2. Query data from cache
                logger.info(f"Querying Progress Notes from cache - Site: {site}, Page: {page}")
                return self._get_notes_from_cache(site, page, per_page, days, cache_status)
            else:
                # 3. Query latest data from API and update cache
                logger.info(f"Querying Progress Notes from API and updating cache - Site: {site}")
                return self._get_notes_from_api_and_cache(site, page, per_page, days)
                
        except Exception as e:
            logger.error(f"Failed to query Progress Notes: {e}")
            return {
                'notes': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'cache_status': 'error',
                'last_sync': None,
                'error': str(e)
            }
        finally:
            conn.close()
    
    def _check_cache_status(self, site: str, days: int) -> Dict:
        """Check cache status"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check actual cache data
            cursor.execute('''
                SELECT COUNT(*) as count, MAX(created_at) as last_created
                FROM progress_notes_cache 
                WHERE site_name = ? AND expires_at > ?
            ''', (site, datetime.now().isoformat()))
            
            cache_info = cursor.fetchone()
            cache_count = cache_info[0] if cache_info else 0
            last_created = cache_info[1] if cache_info and cache_info[1] else None
            
            # Also check sync status
            cursor.execute('''
                SELECT last_sync, sync_status, records_count
                FROM progress_notes_sync 
                WHERE site_name = ?
            ''', (site,))
            
            sync_info = cursor.fetchone()
            
            if cache_count == 0:
                return {
                    'is_fresh': False,
                    'last_sync': None,
                    'total_notes': 0,
                    'status': 'no_cache'
                }
            
            # Calculate cache age
            if last_created:
                last_created_dt = datetime.fromisoformat(last_created)
                cache_age_hours = (datetime.now() - last_created_dt).total_seconds() / 3600
            else:
                cache_age_hours = float('inf')
            
            return {
                'is_fresh': cache_age_hours < self.cache_duration_hours,
                'last_sync': sync_info[0] if sync_info else last_created,
                'total_notes': cache_count,
                'status': sync_info[1] if sync_info else 'cached',
                'cache_age_hours': cache_age_hours
            }
            
        except Exception as e:
            logger.error(f"Failed to check cache status: {e}")
            return {
                'is_fresh': False,
                'last_sync': None,
                'total_notes': 0,
                'status': 'error'
            }
        finally:
            conn.close()
    
    def _get_notes_from_cache(self, site: str, page: int, per_page: int, 
                             days: int, cache_status: Dict) -> Dict:
        """Query data from cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Calculate date range
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Query data from cache (all notes stored as a single JSON)
            cursor.execute('''
                SELECT data
                FROM progress_notes_cache 
                WHERE site_name = ? AND expires_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (site, datetime.now().isoformat()))
            
            cache_row = cursor.fetchone()
            if not cache_row:
                return {
                    'notes': [],
                    'total_count': 0,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'cache_status': 'no_cache',
                    'last_sync': None
                }
            
            # Parse JSON data
            try:
                all_notes = json.loads(cache_row[0])
                if not isinstance(all_notes, list):
                    all_notes = []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse cache data JSON: {e}")
                return {
                    'notes': [],
                    'total_count': 0,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'cache_status': 'error',
                    'last_sync': None
                }
            
            # Date filtering (apply days parameter)
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_notes = []
                for note in all_notes:
                    # Check note creation date (support various field names)
                    note_date = None
                    for date_field in ['createdAt', 'CreatedAt', 'created_at', 'date']:
                        if date_field in note and note[date_field]:
                            try:
                                if isinstance(note[date_field], str):
                                    note_date = datetime.fromisoformat(note[date_field].replace('Z', '+00:00'))
                                else:
                                    note_date = note[date_field]
                                break
                            except:
                                continue
                    
                    if note_date is None or note_date >= cutoff_date:
                        filtered_notes.append(note)
                all_notes = filtered_notes
            
            # Apply pagination
            total_count = len(all_notes)
            offset = (page - 1) * per_page
            notes = all_notes[offset:offset + per_page]
            
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'notes': notes,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'cache_status': 'cached',
                'last_sync': cache_status['last_sync'],
                'cache_age_hours': cache_status.get('cache_age_hours', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to query data from cache: {e}")
            raise
        finally:
            conn.close()
    
    def _get_notes_from_api_and_cache(self, site: str, page: int, per_page: int, days: int) -> Dict:
        """Query data from API and update cache"""
        try:
            # Query data from API (use existing logic)
            from api_progressnote_fetch import fetch_progress_notes_for_site
            
            success, api_notes = fetch_progress_notes_for_site(site, days=days, event_types=[])
            
            if not success or not api_notes:
                return {
                    'notes': [],
                    'total_count': 0,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'cache_status': 'api_error',
                    'last_sync': None
                }
            
            # Update cache
            self._update_cache(site, api_notes)
            
            # Apply pagination
            total_count = len(api_notes)
            offset = (page - 1) * per_page
            paginated_notes = api_notes[offset:offset + per_page]
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'notes': paginated_notes,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'cache_status': 'api_fresh',
                'last_sync': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to query data from API: {e}")
            raise
    
    def _update_cache(self, site: str, notes: List[Dict]):
        """Update cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Delete existing data
            cursor.execute('DELETE FROM progress_notes_cache WHERE site_name = ?', (site,))
            
            # Insert new data
            new_notes_count = 0
            cache_key = f"progress_notes_{site}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            expires_at = datetime.now() + timedelta(hours=self.cache_duration_hours)
            
            # Store all notes as a single JSON
            cursor.execute('''
                INSERT INTO progress_notes_cache 
                (site_name, cache_key, data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                site,
                cache_key,
                json.dumps(notes),
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))
            new_notes_count = len(notes)
            
            # Update sync status
            cursor.execute('''
                INSERT OR REPLACE INTO progress_notes_sync 
                (site_name, last_sync, records_count, sync_status)
                VALUES (?, ?, ?, 'success')
            ''', (
                site,
                datetime.now().isoformat(),
                len(notes)
            ))
            
            conn.commit()
            logger.info(f"Cache update completed - Site: {site}, Notes count: {new_notes_count}")
            
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")
            raise
        finally:
            conn.close()
    
    def cleanup_old_cache(self, days: int = None):
        """Clean up old cache data"""
        if days is None:
            days = self.max_cache_days
            
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                DELETE FROM progress_notes_cache 
                WHERE created_at < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Old cache data cleanup completed - Deleted items: {deleted_count}")
            
        except Exception as e:
            logger.error(f"Failed to clean up cache: {e}")
        finally:
            conn.close()

# Global instance
cache_manager = ProgressNotesCacheManager()
