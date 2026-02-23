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
import re
import json
import time
import sqlite3
import logging
from flask import Blueprint, request, jsonify
from config_users import authenticate_user, get_username_by_lowercase

logger = logging.getLogger(__name__)

# Lazy import firebase push to avoid circular imports
def _get_firebase_push():
    try:
        import firebase_push
        return firebase_push
    except Exception as e:
        logger.error(f"Failed to import firebase_push: {e}")
        return None

app_api_bp = Blueprint('app_api', __name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CALLBELL_DB = os.path.join(_BASE_DIR, 'edenfield_calls.db')
_SITE_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'site_config.json')
_GLOBAL_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'app_global_config.json')
_STAFF_NAMES_PATH = os.path.join(_BASE_DIR, 'data', 'staff_names.json')

# ── Default app config ──────────────────────────────────────
_DEFAULT_APP_CONFIG = {
    'require_staff_name': True,
    'poll_interval_ms': 1000,
    'show_timer': False,
}

# ── DB helpers ──────────────────────────────────────────────

def _ensure_tables():
    """Create app_config and staff_sessions tables if missing."""
    try:
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
                    is_active INTEGER NOT NULL DEFAULT 1,
                    areas TEXT DEFAULT '[]'
                )
            ''')
            # Migrate: add areas column if missing
            cols = {r[1] for r in conn.execute("PRAGMA table_info(staff_sessions)").fetchall()}
            if 'areas' not in cols:
                conn.execute("ALTER TABLE staff_sessions ADD COLUMN areas TEXT DEFAULT '[]'")
            # Seed defaults if empty
            existing = conn.execute('SELECT COUNT(*) FROM app_config').fetchone()[0]
            if existing == 0:
                for k, v in _DEFAULT_APP_CONFIG.items():
                    conn.execute('INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)',
                                 (k, json.dumps(v)))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure tables: {e}")


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


@app_api_bp.route('/api/app/staff-names', methods=['GET'])
def api_app_staff_names():
    """Return staff name suggestions and areas for a given site."""
    site = request.args.get('site', '').strip()
    try:
        with open(_STAFF_NAMES_PATH, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        site_data = all_data.get(site, {})
        # Support both old format (list) and new format (dict with staff/areas)
        if isinstance(site_data, list):
            names = site_data
            areas = []
        else:
            names = site_data.get('staff', [])
            areas = site_data.get('areas', [])
        return jsonify({'success': True, 'names': names, 'areas': areas})
    except Exception as e:
        logger.error(f"Failed to read staff names: {e}")
        return jsonify({'success': True, 'names': [], 'areas': []})


@app_api_bp.route('/api/app/checkin', methods=['POST'])
def api_app_checkin():
    """Staff check-in: create session with just site + staff_name. No password needed."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    site = (data.get('site') or '').strip()
    staff_name = (data.get('staff_name') or '').strip()
    device_info = (data.get('device_info') or '').strip()
    areas = data.get('areas', [])  # list of selected area names

    if not site:
        return jsonify({'success': False, 'message': 'Site selection required'}), 400
    if not staff_name:
        return jsonify({'success': False, 'message': 'Staff name is required'}), 400

    # Validate areas is a list
    if not isinstance(areas, list):
        areas = []
    areas_json = json.dumps(areas)

    # Auto-resolve username from site
    site_id = _site_name_to_id(site)
    username = _SITE_STAFF_MAP.get(site_id, 'staff')

    config = _get_app_config()

    # Create session
    import uuid
    session_id = str(uuid.uuid4())
    now = time.time()
    _ensure_tables()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            # Deactivate any existing sessions for this staff_name on same site
            conn.execute(
                'UPDATE staff_sessions SET is_active = 0 WHERE site = ? AND staff_name = ? AND is_active = 1',
                (site, staff_name)
            )
            conn.execute('''
                INSERT INTO staff_sessions (session_id, username, staff_name, site, device_info, started_at, last_heartbeat, is_active, areas)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ''', (session_id, username, staff_name, site, device_info, now, now, areas_json))
    except Exception as e:
        logger.error(f"Failed to create staff session: {e}")
        return jsonify({'success': False, 'message': 'Failed to create session'}), 500

    return jsonify({
        'success': True,
        'session_id': session_id,
        'user': {
            'username': username,
            'display_name': staff_name,
            'role': 'staff',
            'site': site,
            'staff_name': staff_name,
            'areas': areas,
        },
        'config': {
            'poll_interval_ms': config.get('poll_interval_ms', 3000),
            'show_timer': config.get('show_timer', False),
        },
    })


@app_api_bp.route('/api/app/login', methods=['POST'])
def api_app_login():
    """Legacy login endpoint - redirects to checkin."""
    return api_app_checkin()


# ── Authenticated endpoints (session_id required) ───────────

def _validate_session(data: dict):
    """Validate session_id from request data. Returns session row or None.
    Row: (session_id, username, staff_name, site, areas_json)"""
    session_id = data.get('session_id', '')
    if not session_id:
        return None
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            row = conn.execute(
                'SELECT session_id, username, staff_name, site, areas FROM staff_sessions WHERE session_id = ? AND is_active = 1',
                (session_id,)
            ).fetchone()
            return row
    except Exception:
        return None


@app_api_bp.route('/api/app/heartbeat', methods=['POST'])
def api_app_heartbeat():
    """Keep session alive and return active calls for the staff's site, filtered by area."""
    try:
        data = request.get_json() or {}
        session_row = _validate_session(data)
        if not session_row:
            return jsonify({'success': False, 'message': 'Invalid or expired session', 'logged_out': True}), 401

        session_id, username, staff_name, site, areas_json = session_row
        now = time.time()

        # Parse user's selected areas
        try:
            user_areas = json.loads(areas_json) if areas_json else []
        except (json.JSONDecodeError, TypeError):
            user_areas = []

        # Update heartbeat — sessions stay active until staff finishes shift
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
            site_id = _site_name_to_id(site)
            if site_id:
                monitor = manager.get_monitor(site_id)
                calls = monitor.get_active_calls(consumer='app') if monitor else []
        except Exception as e:
            logger.error(f"Failed to get calls for heartbeat: {e}")

        # Filter calls by user's selected areas (if any areas selected)
        if user_areas and calls:
            calls = _filter_calls_by_area(calls, user_areas, site)

        config = _get_app_config()

        # Get notification tone from callbell settings
        tone = 'bell1'
        try:
            from callbell.base_monitor import get_notification_tone
            tone = get_notification_tone(_CALLBELL_DB)
        except Exception:
            pass

        return jsonify({
            'success': True,
            'calls': calls,
            'config': {
                'poll_interval_ms': config.get('poll_interval_ms', 3000),
                'show_timer': config.get('show_timer', False),
                'notification_tone': tone,
            },
        })
    except Exception as e:
        logger.error(f"Unhandled error in heartbeat: {e}")
        return jsonify({'success': False, 'message': 'Server error', 'calls': []}), 500


@app_api_bp.route('/api/app/register-push-token', methods=['POST'])
def api_app_register_push_token():
    """Register a device FCM token for push notifications."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401

    token = (data.get('token') or '').strip()
    if not token:
        return jsonify({'success': False, 'message': 'Token required'}), 400

    session_id, username, staff_name, site, _areas = session_row
    fp = _get_firebase_push()
    if fp:
        fp.register_device_token(session_id, token, site, staff_name or '')
    return jsonify({'success': True})


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

    # Remove device tokens for this session
    fp = _get_firebase_push()
    if fp:
        fp.unregister_device_tokens(session_id)

    return jsonify({'success': True, 'message': 'Shift ended'})


@app_api_bp.route('/api/app/cancel-call', methods=['POST'])
def api_app_cancel_call():
    """Staff manually cancels/dismisses a call that was a mistake or already handled."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid or expired session'}), 401

    session_id, username, staff_name, site, _areas = session_row
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
                        SELECT username, staff_name, site, device_info, started_at, last_heartbeat, areas
                        FROM staff_sessions
                        WHERE is_active = 1 AND site = ?
                        ORDER BY staff_name
                    ''', (site_filter,)).fetchall()
                else:
                    rows = []
            elif see_all:
                rows = conn.execute('''
                    SELECT username, staff_name, site, device_info, started_at, last_heartbeat, areas
                    FROM staff_sessions
                    WHERE is_active = 1
                    ORDER BY site, staff_name
                ''').fetchall()
            else:
                if not allowed_locations:
                    rows = []
                else:
                    placeholders = ','.join('?' * len(allowed_locations))
                    rows = conn.execute(f'''
                        SELECT username, staff_name, site, device_info, started_at, last_heartbeat, areas
                        FROM staff_sessions
                        WHERE is_active = 1 AND site IN ({placeholders})
                        ORDER BY site, staff_name
                    ''', allowed_locations).fetchall()

        staff = []
        for r in rows:
            try:
                areas = json.loads(r[6]) if r[6] else []
            except (json.JSONDecodeError, TypeError):
                areas = []
            staff.append({
                'username': r[0],
                'staff_name': r[1],
                'site': r[2],
                'device_info': r[3],
                'started_at': r[4],
                'last_heartbeat': r[5],
                'areas': areas,
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


# ── Update areas endpoint ─────────────────────────────────────

@app_api_bp.route('/api/app/update-areas', methods=['POST'])
def api_app_update_areas():
    """Update the areas/wings a staff member is working on."""
    data = request.get_json() or {}
    session_row = _validate_session(data)
    if not session_row:
        return jsonify({'success': False, 'message': 'Invalid or expired session'}), 401

    areas = data.get('areas', [])
    if not isinstance(areas, list):
        areas = []
    areas_json = json.dumps(areas)

    session_id = session_row[0]
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('UPDATE staff_sessions SET areas = ? WHERE session_id = ?', (areas_json, session_id))
        return jsonify({'success': True, 'areas': areas})
    except Exception as e:
        logger.error(f"Failed to update areas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Area parsing and call filtering ──────────────────────────

# Parafield: message format like "JACA RM 1.8 OUT OF BED"
# Area prefix mapping (first 4 chars of the wing name)
_PARAFIELD_AREA_PREFIXES = {
    'ACAC': 'Acacia',
    'JACA': 'Jacaranda',
    'KURR': 'Kurrajong',
    'SAND': 'Sandalwood',
    'WATT': 'Wattle',
    'WILL': 'Willow',
}

# Ramsay: room number to area mapping
_RAMSAY_ROOM_AREAS = [
    (range(1, 15), 'Rotary'),      # Room 1-14
    (range(15, 29), 'Lions'),      # Room 15-28
    (range(29, 39), 'Masonic'),    # Room 29-38
    (range(39, 49), 'Jaycee'),     # Room 39-48
    (range(54, 58), 'McGhee'),     # Room 54-57 (checked before Apex)
    (range(49, 63), 'Apex'),       # Room 49-62 (except 54-57 handled above)
]

_RAMSAY_ROOM_RE = re.compile(r'(?:RM|rm|Rm)\s*(\d+)', re.IGNORECASE)


def _detect_area_parafield(message_text: str) -> str:
    """Detect area from Parafield callbell message text.
    Message format: 'JACA RM 1.8 OUT OF BED' or 'KURR RM 4.2 CALL'
    Returns area name or empty string if not detected."""
    try:
        upper = message_text.strip().upper()
        for prefix, area_name in _PARAFIELD_AREA_PREFIXES.items():
            if upper.startswith(prefix):
                return area_name
    except Exception:
        pass
    return ''


def _detect_area_ramsay(message_text: str) -> str:
    """Detect area from Ramsay callbell message text.
    Message format: 'RM 56 BED - CALL' or 'RM 1.1' or 'RM 1A'
    Returns area name or empty string if not detected."""
    try:
        match = _RAMSAY_ROOM_RE.search(message_text)
        if not match:
            return ''
        room_num = int(match.group(1))
        for room_range, area_name in _RAMSAY_ROOM_AREAS:
            if room_num in room_range:
                return area_name
    except Exception:
        pass
    return ''


def _filter_calls_by_area(calls: list, user_areas: list, site: str) -> list:
    """Filter calls to only include those matching the user's selected areas.
    If a call's area cannot be detected, include it for all users (fallback)."""
    if not user_areas:
        return calls

    # Normalize user areas to lowercase for comparison
    user_areas_lower = {a.lower() for a in user_areas}

    filtered = []
    for call in calls:
        # Get the message text to parse area from
        msg = call.get('messageText', '') or call.get('room', '')

        try:
            if site.lower().startswith('parafield'):
                detected_area = _detect_area_parafield(msg)
            elif site.lower().startswith('ramsay'):
                detected_area = _detect_area_ramsay(msg)
            else:
                detected_area = ''
        except Exception:
            detected_area = ''

        # If area can't be detected, show to all users (fallback)
        if not detected_area:
            filtered.append(call)
        elif detected_area.lower() in user_areas_lower:
            filtered.append(call)

    return filtered


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
