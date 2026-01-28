#!/usr/bin/env python3
"""
Cache-based Progress Notes API Endpoints
Supports hybrid caching and pagination
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
progress_notes_cached_bp = Blueprint('progress_notes_cached', __name__)

def _get_notes_from_api_and_cache(site: str, page: int, per_page: int, days: int):
    """Query Progress Notes (Direct DB access or API) - Cache not needed in direct DB access mode"""
    try:
        import sqlite3
        import os
        
        # Check direct DB access mode
        use_db_direct = False
        try:
            conn = sqlite3.connect('progress_report.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                use_db_direct = result[0].lower() == 'true'
            else:
                use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        except:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
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
        
        # Save to cache only in API mode (direct DB access mode doesn't need cache - always real-time query)
        if not use_db_direct:
            from progress_notes_json_cache import json_cache
            json_cache.update_cache(site, notes)
        
        # Apply pagination
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
            'cache_status': 'fresh_db_data' if use_db_direct else 'updated',
            'last_sync': datetime.now().isoformat(),
            'cache_age_hours': 0
        }
        
    except Exception as e:
        logger.error(f"Progress Notes fetch failed: {e}")
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
    """Fetch progress notes from site (cache-based)"""
    try:
        data = request.get_json()
        site = data.get('site')
        days = data.get('days', 7)  # Default: 7 days
        page = data.get('page', 1)  # Page number
        per_page = data.get('per_page', 50)  # Items per page
        force_refresh = data.get('force_refresh', False)  # Force refresh
        event_types = data.get('event_types', [])  # Event type filter
        year = data.get('year')  # Year
        month = data.get('month')  # Month
        
        if not site:
            logger.error("Site parameter is missing in request")
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"Progress notes fetch request - site: {site}, days: {days}, page: {page}, per_page: {per_page}")
        logger.info(f"Request data: {data}")
        
        # Check site server configuration
        from config import SITE_SERVERS
        if site not in SITE_SERVERS:
            logger.error(f"Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}")
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}'
            }), 400
        
        # Check direct DB access mode
        import sqlite3
        import os
        
        use_db_direct = False
        try:
            conn = sqlite3.connect('progress_report.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                use_db_direct = result[0].lower() == 'true'
            else:
                use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        except:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
        # Direct DB access mode: Always real-time query without cache
        if use_db_direct:
            logger.info(f"🔌 Direct DB access mode: Progress Notes fetched in real time (no cache) - {site}")
            result = _get_notes_from_api_and_cache(site, page, per_page, days)
        else:
            # API mode: Use JSON cache (reduce API call costs)
            from progress_notes_json_cache import json_cache
            
            if force_refresh:
                # Force refresh: Ignore cache and query directly from API
                logger.info(f"Force refresh mode - fetching directly from API: {site}")
                result = _get_notes_from_api_and_cache(site, page, per_page, days)
            else:
                # Use JSON cache
                logger.info(f"JSON cache mode - site: {site}")
                result = json_cache.get_cached_notes(site, page, per_page)
                
                # Query from API if cache is missing or expired
                if not result['success'] or not json_cache.is_cache_valid(site):
                    logger.info(f"Cache missing/expired - fetching from API: {site}")
                    result = _get_notes_from_api_and_cache(site, page, per_page, days)
                else:
                    # Convert cache data to API format
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
        
        # Compose response data
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
        
        logger.info(
            f"Progress notes fetch succeeded - {site}: {result['total_count']} items (page {page}/{result['total_pages']})"
        )
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
    """Clear Progress Notes cache (Admin only)"""
    try:
        # Check admin privileges
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site')
        
        from progress_notes_json_cache import json_cache
        
        if site:
            # Clear cache for specific site only
            json_cache.clear_cache(site)
            logger.info(f"Progress Notes cache cleared - site: {site}")
            return jsonify({
                'success': True,
                'message': f'Cache cleared for {site}'
            })
        else:
            # Clear all caches
            json_cache.clear_cache()
            logger.info("All Progress Notes caches cleared")
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
