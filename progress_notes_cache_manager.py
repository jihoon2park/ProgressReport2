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
            
            # 실제 캐시 데이터 확인
            cursor.execute('''
                SELECT COUNT(*) as count, MAX(created_at) as last_created
                FROM progress_notes_cache 
                WHERE site_name = ? AND expires_at > ?
            ''', (site, datetime.now().isoformat()))
            
            cache_info = cursor.fetchone()
            cache_count = cache_info[0] if cache_info else 0
            last_created = cache_info[1] if cache_info and cache_info[1] else None
            
            # 동기화 상태도 확인
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
            
            # 캐시 나이 계산
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
            
            # 캐시에서 데이터 조회 (모든 노트가 하나의 JSON으로 저장됨)
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
            
            # JSON 데이터 파싱
            try:
                all_notes = json.loads(cache_row[0])
                if not isinstance(all_notes, list):
                    all_notes = []
            except json.JSONDecodeError as e:
                logger.error(f"캐시 데이터 JSON 파싱 실패: {e}")
                return {
                    'notes': [],
                    'total_count': 0,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': 0,
                    'cache_status': 'error',
                    'last_sync': None
                }
            
            # 날짜 필터링 (days 파라미터 적용)
            if days > 0:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_notes = []
                for note in all_notes:
                    # 노트의 생성일 확인 (다양한 필드명 지원)
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
            
            # 페이지네이션 적용
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
            
            # 기존 데이터 삭제
            cursor.execute('DELETE FROM progress_notes_cache WHERE site_name = ?', (site,))
            
            # 새 데이터 삽입
            new_notes_count = 0
            cache_key = f"progress_notes_{site}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            expires_at = datetime.now() + timedelta(hours=self.cache_duration_hours)
            
            # 모든 노트를 하나의 JSON으로 저장
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
            
            # 동기화 상태 업데이트
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
