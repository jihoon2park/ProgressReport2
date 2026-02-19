"""
Mobile App API Blueprint
Provides endpoints for the Edenfield staff mobile app:
  - /api/app/config       GET    Pre-login config (sites, login fields)
  - /api/app/login        POST   Authenticate staff, register session
  - /api/app/heartbeat    POST   Keep staff session alive, return calls
  - /api/app/finish-shift POST   End staff session
  - /api/app/admin/config GET/POST  Admin: read/write app config
  - /api/app/admin/staff-online GET  Admin: list online staff
"""
import os
import json
import time
import sqlite3
import logging
from flask import Blueprint, request, jsonify
from config_users import authenticate_user, get_username_by_lowercase

logger = logging.getLogger(__name__)

app_api_bp = Blueprint('app_api', __name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CALLBELL_DB = os.path.join(_BASE_DIR, 'edenfield_calls.db')
_SITE_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'site_config.json')
_GLOBAL_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'app_global_config.json')

# ── Default app config ──────────────────────────────────────
_DEFAULT_APP_CONFIG = {
    'require_staff_name': True,
    'poll_interval_ms': 1000,
    'show_timer': False,
}

# ── DB helpers ──────────────────────────────────────────────

def _ensure_tables():
    """Create app_config and staff_sessions tables if missing."""
    with sqlite3.connect(_CALLBELL_DB) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS staff_sessions (
                session_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                staff_name TEXT,
                site TEXT NOT NULL,
                device_info TEXT,
                started_at REAL NOT NULL,
                last_heartbeat REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')
        # Seed defaults if empty
        existing = conn.execute('SELECT COUNT(*) FROM app_config').fetchone()[0]
        if existing == 0:
            for k, v in _DEFAULT_APP_CONFIG.items():
                conn.execute('INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)',
                             (k, json.dumps(v)))
        conn.commit()


def _get_app_config() -> dict:
    """Read all app_config rows into a dict."""
    _ensure_tables()
    config = _DEFAULT_APP_CONFIG.copy()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            rows = conn.execute('SELECT key, value FROM app_config').fetchall()
            for k, v in rows:
                try:
                    config[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    config[k] = v
    except Exception as e:
        logger.error(f"Failed to read app_config: {e}")
    return config


def _get_callbell_sites() -> list:
    """Return list of sites that are actively being monitored (not just configured)."""
    try:
        from callbell.manager import get_manager
        manager = get_manager()
        result = []
        for site_id, monitor in manager.monitors.items():
            result.append({'id': site_id, 'name': monitor.site_name})
        return result
    except Exception as e:
        logger.error(f"Failed to get monitored sites: {e}")
        return []


# Map site_id to staff username (auto-set behind the scenes)
_SITE_STAFF_MAP = {
    'parafield_gardens': 'staff.parafield',
    'ramsay': 'staff.ramsay',
}

def _build_login_fields(config: dict) -> list:
    """Build dynamic login field definitions from config."""
    fields = [
        {'key': 'site', 'label': 'Site', 'type': 'select', 'required': True},
        {'key': 'password', 'label': 'Password', 'type': 'password', 'required': True},
    ]
    if config.get('require_staff_name', True):
        fields.append({'key': 'staff_name', 'label': 'Staff Name', 'type': 'text', 'required': True})
    return fields


# ── Public endpoints (no auth required) ─────────────────────

@app_api_bp.route('/api/app/config', methods=['GET'])
def api_app_config():
    """Pre-login config: available sites, login fields, poll interval."""
    config = _get_app_config()
    sites = _get_callbell_sites()
    fields = _build_login_fields(config)
    return jsonify({
        'success': True,
        'sites': sites,
        'login_fields': fields,
        'poll_interval_ms': config.get('poll_interval_ms', 3000),
    })


@app_api_bp.route('/api/app/login', methods=['POST'])
def api_app_login():
    """Authenticate staff user, create session, return user info + config."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    password = (data.get('password') or '').strip()
    site = (data.get('site') or '').strip()
    staff_name = (data.get('staff_name') or '').strip()
    device_info = (data.get('device_info') or '').strip()

    if not password:
        return jsonify({'success': False, 'message': 'Password required'}), 400
    if not site:
        return jsonify({'success': False, 'message': 'Site selection required'}), 400

    # Auto-resolve username from site selection
    site_id = _site_name_to_id(site)
    username = data.get('username', '').strip() or _SITE_STAFF_MAP.get(site_id, '')
    if not username:
        return jsonify({'success': False, 'message': 'No staff account configured for this site'}), 400

    success, user_info = authenticate_user(username, password)
    if not success:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401

    role = user_info.get('role', '')
    # Only staff, site_admin, and admin can use the app
    if role not in ('staff', 'site_admin', 'admin'):
        return jsonify({'success': False, 'message': 'This account does not have app access'}), 403

    config = _get_app_config()

    # Check if staff_name is required
    if config.get('require_staff_name', True) and not staff_name:
        return jsonify({'success': False, 'message': 'Staff name is required'}), 400

    # Create session
    import uuid
    session_id = str(uuid.uuid4())
    now = time.time()
    _ensure_tables()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            # Deactivate any existing sessions for this username + staff_name on same site
            # (allows multiple people to share the same account with different staff names)
            conn.execute(
                'UPDATE staff_sessions SET is_active = 0 WHERE username = ? AND site = ? AND staff_name = ? AND is_active = 1',
                (username, site, staff_name)
            )
            conn.execute('''
                INSERT INTO staff_sessions (session_id, username, staff_name, site, device_info, started_at, last_heartbeat, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (session_id, username, staff_name, site, device_info, now, now))
    except Exception as e:
        logger.error(f"Failed to create staff session: {e}")

    actual_username = get_username_by_lowercase(username) or username
    display_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()

    return jsonify({
        'success': True,
        'session_id': session_id,
        'user': {
            'username': actual_username,
            'display_name': display_name,
            'role': role,
            'site': site,
            'staff_name': staff_name,
        },
        'config': {
            'poll_interval_ms': config.get('poll_interval_ms', 3000),
            'show_timer': config.get('show_timer', False),
        },
    })


# ── Authenticated endpoints (session_id required) ───────────

def _validate_session(data: dict):
    """Validate session_id from request data. Returns session row or None."""
    session_id = data.get('session_id', '')
    if not session_id:
        return None
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            row = conn.execute(
                'SELECT session_id, username, staff_name, site FROM staff_sessions WHERE session_id = ? AND is_active = 1',
                (session_id,)
            ).fetchone()
            return row
    except Exception:
        return None


@app_api_bp.route('/api/app/heartbeat', methods=['POST'])
def api_app_heartbeat():
    """Keep session alive and return active calls for the staff's site."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid or expired session', 'logged_out': True}), 401

    session_id, username, staff_name, site = session_row
    now = time.time()

    # Update heartbeat
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('UPDATE staff_sessions SET last_heartbeat = ? WHERE session_id = ?', (now, session_id))
    except Exception as e:
        logger.error(f"Failed to update heartbeat: {e}")

    # Get calls for this staff's site - use callbell manager
    calls = []
    try:
        from callbell.manager import get_manager
        manager = get_manager()
        # Map site display name to site_id
        site_id = _site_name_to_id(site)
        if site_id:
            calls = manager.get_site_active_calls(site_id)
    except Exception as e:
        logger.error(f"Failed to get calls for heartbeat: {e}")

    config = _get_app_config()

    return jsonify({
        'success': True,
        'calls': calls,
        'config': {
            'poll_interval_ms': config.get('poll_interval_ms', 3000),
            'show_timer': config.get('show_timer', False),
        },
    })


@app_api_bp.route('/api/app/finish-shift', methods=['POST'])
def api_app_finish_shift():
    """End the staff session."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid or expired session'}), 401

    session_id = session_row[0]
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('UPDATE staff_sessions SET is_active = 0 WHERE session_id = ?', (session_id,))
    except Exception as e:
        logger.error(f"Failed to end session: {e}")

    return jsonify({'success': True, 'message': 'Shift ended'})


@app_api_bp.route('/api/app/cancel-call', methods=['POST'])
def api_app_cancel_call():
    """Staff manually cancels/dismisses a call that was a mistake or already handled."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid or expired session'}), 401

    session_id, username, staff_name, site = session_row
    event_id = data.get('event_id', '')
    room = data.get('room', '')

    if not event_id and not room:
        return jsonify({'success': False, 'message': 'event_id or room required'}), 400

    try:
        from callbell.manager import get_manager
        manager = get_manager()
        site_id = _site_name_to_id(site)
        if site_id:
            monitor = manager.get_monitor(site_id)
            if monitor:
                monitor.archive_call(room, event_id)
                logger.info(f"📞 [{site}] Call cancelled by {staff_name or username}: room={room} event={event_id}")
                return jsonify({'success': True, 'message': 'Call cancelled'})
        return jsonify({'success': False, 'message': 'Site monitor not found'}), 404
    except Exception as e:
        logger.error(f"Failed to cancel call: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Admin endpoints (require admin/site_admin via web session) ───

@app_api_bp.route('/api/app/admin/config', methods=['GET'])
def api_app_admin_config_get():
    """Get current app config (admin only)."""
    from flask_login import current_user
    if not current_user.is_authenticated or getattr(current_user, 'role', '') not in ('admin', 'site_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    config = _get_app_config()
    return jsonify({'success': True, 'config': config})


@app_api_bp.route('/api/app/admin/config', methods=['POST'])
def api_app_admin_config_post():
    """Update app config (admin only)."""
    from flask_login import current_user
    if not current_user.is_authenticated or getattr(current_user, 'role', '') not in ('admin', 'site_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data'}), 400

    _ensure_tables()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            for k, v in data.items():
                conn.execute('INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)',
                             (k, json.dumps(v)))
        logger.info(f"App config updated: {list(data.keys())}")
        return jsonify({'success': True, 'config': _get_app_config()})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app_api_bp.route('/api/app/admin/staff-online', methods=['GET'])
def api_app_admin_staff_online():
    """Get list of currently online staff (admin only)."""
    from flask_login import current_user
    if not current_user.is_authenticated or getattr(current_user, 'role', '') not in ('admin', 'site_admin'):
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    from config_users import get_user
    user_data = get_user(current_user.id) or {}
    allowed_locations = user_data.get('location', [])
    see_all = 'All' in allowed_locations
    role = getattr(current_user, 'role', '')

    # Optional ?site= filter from frontend (active tab site name)
    site_filter = request.args.get('site', '').strip()

    # Staff are online after login, offline after finish shift
    _ensure_tables()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            if site_filter:
                # Frontend is requesting a specific site tab
                # Admin can request any site; site_admin only their allowed sites
                if see_all or site_filter in allowed_locations:
                    rows = conn.execute('''
                        SELECT username, staff_name, site, device_info, started_at, last_heartbeat
                        FROM staff_sessions
                        WHERE is_active = 1 AND site = ?
                        ORDER BY staff_name
                    ''', (site_filter,)).fetchall()
                else:
                    rows = []
            elif see_all:
                rows = conn.execute('''
                    SELECT username, staff_name, site, device_info, started_at, last_heartbeat
                    FROM staff_sessions
                    WHERE is_active = 1
                    ORDER BY site, staff_name
                ''').fetchall()
            else:
                placeholders = ','.join('?' * len(allowed_locations))
                rows = conn.execute(f'''
                    SELECT username, staff_name, site, device_info, started_at, last_heartbeat
                    FROM staff_sessions
                    WHERE is_active = 1 AND site IN ({placeholders})
                    ORDER BY site, staff_name
                ''', allowed_locations).fetchall()

        staff = []
        for r in rows:
            staff.append({
                'username': r[0],
                'staff_name': r[1],
                'site': r[2],
                'device_info': r[3],
                'started_at': r[4],
                'last_heartbeat': r[5],
                'online_minutes': round((time.time() - r[4]) / 60, 1),
            })
        return jsonify({'success': True, 'staff': staff})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app_api_bp.route('/api/app/download-url', methods=['GET'])
def api_app_download_url():
    """Return app download URL from app_global_config.json for QR code generation."""
    try:
        with open(_GLOBAL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        url = cfg.get('app_download_url', '')
        if url:
            return jsonify({'success': True, 'url': url})
        return jsonify({'success': False, 'message': 'No app_download_url in app_global_config.json'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Helpers ──────────────────────────────────────────────────

def _site_name_to_id(site_name: str) -> str:
    """Map a site display name (e.g. 'Ramsay') to its config id (e.g. 'ramsay')."""
    try:
        with open(_SITE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            sites = json.load(f)
        for s in sites:
            if s.get('site_name', '').lower() == site_name.lower():
                return s['id']
            if s.get('id', '').lower() == site_name.lower():
                return s['id']
    except Exception:
        pass
    return ''
