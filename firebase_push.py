"""
Firebase Cloud Messaging (FCM) push notification service.
Sends push notifications to staff mobile devices when new calls come in.
"""
import os
import logging
import sqlite3
import threading

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CALLBELL_DB = os.path.join(_BASE_DIR, 'edenfield_calls.db')
_FIREBASE_KEY_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'firebase-adminsdk.json')

_firebase_app = None
_init_lock = threading.Lock()


def _init_firebase():
    """Initialize Firebase Admin SDK (once)."""
    global _firebase_app
    if _firebase_app is not None:
        return True
    with _init_lock:
        if _firebase_app is not None:
            return True
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not os.path.exists(_FIREBASE_KEY_PATH):
                logger.error(f"Firebase key not found: {_FIREBASE_KEY_PATH}")
                return False
            cred = credentials.Certificate(_FIREBASE_KEY_PATH)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase Admin SDK initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return False


def _ensure_device_tokens_table():
    """Create device_tokens table if it doesn't exist."""
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS device_tokens (
                    token TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    site TEXT NOT NULL,
                    staff_name TEXT,
                    registered_at REAL NOT NULL
                )
            ''')
    except Exception as e:
        logger.error(f"Failed to create device_tokens table: {e}")


def register_device_token(session_id: str, token: str, site: str, staff_name: str = ''):
    """Register a device FCM token for push notifications."""
    import time
    _ensure_device_tokens_table()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO device_tokens (token, session_id, site, staff_name, registered_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (token, session_id, site, staff_name, time.time()))
        logger.info(f"📱 Push token registered for {staff_name} at {site}")
    except Exception as e:
        logger.error(f"Failed to register device token: {e}")


def unregister_device_tokens(session_id: str):
    """Remove device tokens for a session (on finish-shift)."""
    _ensure_device_tokens_table()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            conn.execute('DELETE FROM device_tokens WHERE session_id = ?', (session_id,))
    except Exception as e:
        logger.error(f"Failed to unregister device tokens: {e}")


def _get_tokens_for_site(site_name: str) -> list:
    """Get all active device tokens for a site."""
    _ensure_device_tokens_table()
    try:
        with sqlite3.connect(_CALLBELL_DB) as conn:
            rows = conn.execute('''
                SELECT dt.token FROM device_tokens dt
                INNER JOIN staff_sessions ss ON dt.session_id = ss.session_id
                WHERE ss.site = ? AND ss.is_active = 1
            ''', (site_name,)).fetchall()
            return [r[0] for r in rows]
    except Exception as e:
        logger.error(f"Failed to get tokens for site {site_name}: {e}")
        return []


def send_push_for_new_call(site_name: str, room: str, call_type: str, priority: int,
                           message_text: str = '', card_level: str = 'green'):
    """Send FCM push notification to all devices at a site for a new call."""
    if not _init_firebase():
        return

    tokens = _get_tokens_for_site(site_name)
    if not tokens:
        return

    try:
        from firebase_admin import messaging

        # Build urgency label
        if card_level == 'red':
            urgency = '🔴 URGENT'
        elif card_level == 'yellow':
            urgency = '🟡 Warning'
        else:
            urgency = '🟢 New'

        title = f'{urgency} — {message_text or room}'
        body = f'Call from {room} requires attention'

        # Send to each token individually (handles invalid tokens gracefully)
        messages = []
        for token in tokens:
            msg = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='callbell-alerts',
                        priority='max',
                        sound='default',
                        vibrate_timings_millis=[0, 800, 150, 800, 150, 800, 150, 800],
                        default_vibrate_timings=False,
                        visibility='public',
                        tag='callbell-call',
                    ),
                ),
                token=token,
            )
            messages.append(msg)

        if messages:
            response = messaging.send_each(messages)
            success = response.success_count
            failure = response.failure_count
            logger.info(f"📤 Push sent for {room} at {site_name}: {success} ok, {failure} failed")

            # Clean up invalid tokens
            for i, send_response in enumerate(response.responses):
                if send_response.exception is not None:
                    error_code = getattr(send_response.exception, 'code', '')
                    if 'NOT_FOUND' in str(error_code) or 'UNREGISTERED' in str(error_code):
                        try:
                            with sqlite3.connect(_CALLBELL_DB) as conn:
                                conn.execute('DELETE FROM device_tokens WHERE token = ?', (tokens[i],))
                            logger.info(f"🗑️ Removed invalid FCM token")
                        except Exception:
                            pass
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
