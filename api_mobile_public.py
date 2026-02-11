"""
Public API endpoints for Edenfield mobile app (no login required).
"""
import os
import sqlite3
import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required

logger = logging.getLogger(__name__)

mobile_public_bp = Blueprint('mobile_public', __name__)


@mobile_public_bp.route('/api/audit-progress-notes', methods=['GET', 'POST'])
@login_required
def audit_progress_notes():
    """Return all progress notes for last 7 days. Login required."""
    try:
        from app import get_safe_site_servers, get_australian_time  # deferred to avoid circular import

        site = None
        if request.method == 'POST':
            data = request.get_json() or {}
            site = data.get('site')
        else:
            site = request.args.get('site')
        site = site or 'Parafield Gardens'
        days = 7
        per_page = 5000

        safe_site_servers = get_safe_site_servers()
        if site not in safe_site_servers:
            return jsonify({'success': False, 'message': f'Unknown site: {site}'}), 400

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
        except Exception:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'

        from api_progressnote_fetch import fetch_progress_notes_for_site

        if use_db_direct:
            success, notes, total_count = fetch_progress_notes_for_site(
                site, days,
                limit=per_page, offset=0, return_total=True
            )
        else:
            success, notes, _ = fetch_progress_notes_for_site(site, days, limit=per_page)
            total_count = len(notes) if notes else 0

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to fetch progress notes',
                'data': [],
                'count': 0,
                'cache_info': {'status': 'error', 'cache_age_hours': 0, 'last_sync': None},
            }), 500

        notes_out = list(notes) if notes else []
        return jsonify({
            'success': True,
            'site': site,
            'data': notes_out,
            'count': total_count if total_count is not None else len(notes_out),
            'cache_info': {
                'status': 'fresh_db_data' if use_db_direct else 'fresh_api_data',
                'cache_age_hours': 0,
                'last_sync': get_australian_time().isoformat(),
            },
        })
    except Exception as e:
        logger.error(f"Error in audit_progress_notes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# /api/wounds is defined in app.py (api_wounds) - no auth required
