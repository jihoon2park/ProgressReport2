#!/usr/bin/env python3
"""
캐시 기반 Progress Notes API 엔드포인트
하이브리드 캐싱과 페이지네이션 지원
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Blueprint 생성
progress_notes_cached_bp = Blueprint('progress_notes_cached', __name__)

def _get_notes_from_api_and_cache(site: str, page: int, per_page: int, days: int):
    """API에서 Progress Notes 조회 후 JSON 캐시에 저장"""
    try:
        from progress_notes_json_cache import json_cache
        from api_progressnote_fetch import fetch_progress_notes_for_site
        success, notes = fetch_progress_notes_for_site(site, days)
        
        if not success or not notes:
            return {
                'success': False,
                'notes': [],
                'page': page,
                'per_page': per_page,
                'total_count': 0,
                'total_pages': 0,
                'cache_status': 'no_data',
                'last_sync': None,
                'cache_age_hours': 0
            }
        
        # JSON 캐시에 저장
        json_cache.update_cache(site, notes)
        
        # 페이지네이션 적용
        total_count = len(notes)
        total_pages = (total_count + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_notes = notes[start_idx:end_idx]
        
        return {
            'success': True,
            'notes': paginated_notes,
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'cache_status': 'updated',
            'last_sync': datetime.now().isoformat(),
            'cache_age_hours': 0
        }
        
    except Exception as e:
        logger.error(f"API에서 데이터 조회 실패: {e}")
        return {
            'success': False,
            'notes': [],
            'page': page,
            'per_page': per_page,
            'total_count': 0,
            'total_pages': 0,
            'cache_status': 'error',
            'last_sync': None,
            'cache_age_hours': 0
        }

@progress_notes_cached_bp.route('/api/fetch-progress-notes-cached', methods=['POST'])
@login_required
def fetch_progress_notes_cached():
    """프로그레스 노트를 사이트에서 가져오기 (캐시 기반)"""
    try:
        data = request.get_json()
        site = data.get('site')
        days = data.get('days', 7)  # 기본값: 7일
        page = data.get('page', 1)  # 페이지 번호
        per_page = data.get('per_page', 50)  # 페이지당 항목 수
        force_refresh = data.get('force_refresh', False)  # 강제 새로고침
        event_types = data.get('event_types', [])  # 이벤트 타입 필터
        year = data.get('year')  # 년도
        month = data.get('month')  # 월
        
        if not site:
            logger.error("Site parameter is missing in request")
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"프로그레스 노트 가져오기 요청 - 사이트: {site}, 일수: {days}, 페이지: {page}, 페이지당: {per_page}")
        logger.info(f"Request data: {data}")
        
        # 사이트 서버 설정 확인
        from config import SITE_SERVERS
        if site not in SITE_SERVERS:
            logger.error(f"Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}")
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}'
            }), 400
        
        # JSON 캐시 매니저 사용
        from progress_notes_json_cache import json_cache
        
        if force_refresh:
            # 강제 새로고침: 캐시 무시하고 API에서 직접 조회
            logger.info(f"강제 새로고침 모드 - API에서 직접 조회: {site}")
            result = _get_notes_from_api_and_cache(site, page, per_page, days)
        else:
                # JSON 캐시 사용
                logger.info(f"JSON 캐시 모드 - 사이트: {site}")
                result = json_cache.get_cached_notes(site, page, per_page)
                
                # 캐시가 없거나 만료된 경우 API에서 조회
                if not result['success'] or not json_cache.is_cache_valid(site):
                    logger.info(f"캐시 없음/만료 - API에서 조회: {site}")
                    result = _get_notes_from_api_and_cache(site, page, per_page, days)
                else:
                    # 캐시 데이터를 API 형식으로 변환
                    result = {
                        'success': True,
                        'notes': result.get('data', []),
                        'page': result.get('pagination', {}).get('current_page', page),
                        'per_page': result.get('pagination', {}).get('per_page', per_page),
                        'total_count': result.get('pagination', {}).get('total_count', 0),
                        'total_pages': result.get('pagination', {}).get('total_pages', 0),
                        'cache_status': 'cached',
                        'last_sync': result.get('last_sync'),
                        'cache_age_hours': result.get('cache_age_hours', 0)
                    }
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'data': result['notes'],
            'pagination': {
                'page': result['page'],
                'per_page': result['per_page'],
                'total_count': result['total_count'],
                'total_pages': result['total_pages']
            },
            'cache_info': {
                'status': result['cache_status'],
                'last_sync': result['last_sync'],
                'cache_age_hours': result.get('cache_age_hours', 0)
            },
            'site': site,
            'count': result['total_count'],
            'fetched_at': datetime.now().isoformat()
        }
        
        logger.info(f"프로그레스 노트 가져오기 성공 - {site}: {result['total_count']}개 (페이지 {page}/{result['total_pages']})")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in fetch_progress_notes_cached: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@progress_notes_cached_bp.route('/api/clear-progress-notes-cache', methods=['POST'])
@login_required
def clear_progress_notes_cache():
    """Progress Notes 캐시 초기화 (Admin 전용)"""
    try:
        # 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site')
        
        from progress_notes_json_cache import json_cache
        
        if site:
            # 특정 사이트 캐시만 초기화
            json_cache.clear_cache(site)
            logger.info(f"Progress Notes 캐시 초기화 완료 - 사이트: {site}")
            return jsonify({
                'success': True,
                'message': f'Cache cleared for {site}'
            })
        else:
            # 전체 캐시 초기화
            json_cache.clear_cache()
            logger.info("전체 Progress Notes 캐시 초기화 완료")
            return jsonify({
                'success': True,
                'message': 'All cache cleared'
            })
            
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error clearing cache: {str(e)}'
        }), 500
