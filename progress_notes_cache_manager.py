#!/usr/bin/env python3
"""
Progress Notes 캐시 매니저
하이브리드 캐싱과 페이지네이션을 지원
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

class ProgressNotesCacheManager:
    """Progress Notes 캐시 관리 클래스"""
    
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.cache_duration_hours = 1  # 1시간 캐시 유효
        self.max_cache_days = 30  # 30일 이상된 데이터 삭제
        
    def get_db_connection(self):
        """데이터베이스 연결"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_cached_notes(self, site: str, page: int = 1, per_page: int = 50, 
                        days: int = 7, use_hybrid: bool = True) -> Dict:
        """
        하이브리드 캐싱으로 Progress Notes 조회
        
        Args:
            site: 사이트명
            page: 페이지 번호 (1부터 시작)
            per_page: 페이지당 항목 수
            days: 조회할 일수
            use_hybrid: 하이브리드 캐싱 사용 여부
            
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
            
            # 1. 캐시 상태 확인
            cache_status = self._check_cache_status(site, days)
            
            if use_hybrid and cache_status['is_fresh']:
                # 2. 캐시에서 데이터 조회
                logger.info(f"캐시에서 Progress Notes 조회 - 사이트: {site}, 페이지: {page}")
                return self._get_notes_from_cache(site, page, per_page, days, cache_status)
            else:
                # 3. API에서 최신 데이터 조회 후 캐시 업데이트
                logger.info(f"API에서 Progress Notes 조회 후 캐시 업데이트 - 사이트: {site}")
                return self._get_notes_from_api_and_cache(site, page, per_page, days)
                
        except Exception as e:
            logger.error(f"Progress Notes 조회 실패: {e}")
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
        """캐시 상태 확인"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 마지막 동기화 시간 확인
            cursor.execute('''
                SELECT last_sync_time, sync_status, total_notes
                FROM progress_notes_sync 
                WHERE site = ?
            ''', (site,))
            
            sync_info = cursor.fetchone()
            
            if not sync_info:
                return {
                    'is_fresh': False,
                    'last_sync': None,
                    'total_notes': 0,
                    'status': 'no_cache'
                }
            
            last_sync = datetime.fromisoformat(sync_info['last_sync_time']) if sync_info['last_sync_time'] else None
            cache_age_hours = (datetime.now() - last_sync).total_seconds() / 3600 if last_sync else float('inf')
            
            return {
                'is_fresh': cache_age_hours < self.cache_duration_hours,
                'last_sync': sync_info['last_sync_time'],
                'total_notes': sync_info['total_notes'],
                'status': sync_info['sync_status'],
                'cache_age_hours': cache_age_hours
            }
            
        except Exception as e:
            logger.error(f"캐시 상태 확인 실패: {e}")
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
        """캐시에서 데이터 조회"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 날짜 범위 계산
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 전체 개수 조회 (api_created_at이 NULL인 경우도 포함)
            cursor.execute('''
                SELECT COUNT(*) as total
                FROM progress_notes_cache 
                WHERE site = ? AND is_active = 1 
                AND (api_created_at >= ? OR api_created_at IS NULL)
            ''', (site, cutoff_date.isoformat()))
            
            total_count = cursor.fetchone()['total']
            
            # 페이지네이션으로 데이터 조회 (api_created_at이 NULL인 경우도 포함)
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT note_data, api_created_at, api_updated_at
                FROM progress_notes_cache 
                WHERE site = ? AND is_active = 1 
                AND (api_created_at >= ? OR api_created_at IS NULL)
                ORDER BY COALESCE(api_created_at, created_at) DESC
                LIMIT ? OFFSET ?
            ''', (site, cutoff_date.isoformat(), per_page, offset))
            
            notes = []
            for row in cursor.fetchall():
                note_data = json.loads(row['note_data'])
                notes.append(note_data)
            
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
            logger.error(f"캐시에서 데이터 조회 실패: {e}")
            raise
        finally:
            conn.close()
    
    def _get_notes_from_api_and_cache(self, site: str, page: int, per_page: int, days: int) -> Dict:
        """API에서 데이터 조회 후 캐시 업데이트"""
        try:
            # API에서 데이터 조회 (기존 로직 사용)
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
            
            # 캐시 업데이트
            self._update_cache(site, api_notes)
            
            # 페이지네이션 적용
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
            logger.error(f"API에서 데이터 조회 실패: {e}")
            raise
    
    def _update_cache(self, site: str, notes: List[Dict]):
        """캐시 업데이트"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 기존 데이터 비활성화
            cursor.execute('''
                UPDATE progress_notes_cache 
                SET is_active = 0, updated_at = ?
                WHERE site = ?
            ''', (datetime.now().isoformat(), site))
            
            # 새 데이터 삽입
            new_notes_count = 0
            for note in notes:
                try:
                    note_id = note.get('id') or note.get('Id')
                    if not note_id:
                        continue
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO progress_notes_cache 
                        (site, note_id, note_data, api_created_at, api_updated_at, is_active)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (
                        site,
                        note_id,
                        json.dumps(note),
                        note.get('createdAt') or note.get('CreatedAt'),
                        note.get('updatedAt') or note.get('UpdatedAt'),
                    ))
                    new_notes_count += 1
                    
                except Exception as e:
                    logger.warning(f"노트 캐시 저장 실패 (ID: {note_id}): {e}")
                    continue
            
            # 동기화 상태 업데이트
            cursor.execute('''
                INSERT OR REPLACE INTO progress_notes_sync 
                (site, last_sync_time, total_notes, new_notes_count, sync_status, updated_at)
                VALUES (?, ?, ?, ?, 'success', ?)
            ''', (
                site,
                datetime.now().isoformat(),
                len(notes),
                new_notes_count,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            logger.info(f"캐시 업데이트 완료 - 사이트: {site}, 노트 수: {new_notes_count}")
            
        except Exception as e:
            logger.error(f"캐시 업데이트 실패: {e}")
            raise
        finally:
            conn.close()
    
    def cleanup_old_cache(self, days: int = None):
        """오래된 캐시 데이터 정리"""
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
            
            logger.info(f"오래된 캐시 데이터 정리 완료 - 삭제된 항목: {deleted_count}")
            
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")
        finally:
            conn.close()

# 전역 인스턴스
cache_manager = ProgressNotesCacheManager()
