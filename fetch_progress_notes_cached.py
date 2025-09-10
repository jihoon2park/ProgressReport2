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
        
        # 캐시 매니저 사용
        from progress_notes_cache_manager import cache_manager
        
        if force_refresh:
            # 강제 새로고침: 캐시 무시하고 API에서 직접 조회
            logger.info(f"강제 새로고침 모드 - API에서 직접 조회: {site}")
            result = cache_manager._get_notes_from_api_and_cache(site, page, per_page, days)
        else:
            # 하이브리드 캐싱 사용
            logger.info(f"하이브리드 캐싱 모드 - 사이트: {site}")
            result = cache_manager.get_cached_notes(site, page, per_page, days, use_hybrid=True)
        
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
        
        from progress_notes_cache_manager import cache_manager
        
        if site:
            # 특정 사이트 캐시만 초기화
            cache_manager._clear_site_cache(site)
            logger.info(f"Progress Notes 캐시 초기화 완료 - 사이트: {site}")
            return jsonify({
                'success': True,
                'message': f'Cache cleared for {site}'
            })
        else:
            # 전체 캐시 초기화
            cache_manager.cleanup_old_cache(days=0)
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
