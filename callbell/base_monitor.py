"""
Base Callbell Monitor - Abstract base class for all callbell systems
Provides common interface and database operations for multi-site support.
"""
import os
import time
import sqlite3
import logging
import threading
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _open_db(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and busy_timeout.
    Eliminates 'database is locked' errors under concurrency."""
    conn = sqlite3.connect(db_path, timeout=15)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=10000')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn

# ── Card color definitions ──
# Light-theme professional palette for mobile app
CARD_STYLES = {
    'gray':   {'bg': '#F0F4F8', 'border': '#90A4AE', 'text': '#455A64'},
    'green':  {'bg': '#E8F5E9', 'border': '#43A047', 'text': '#1B5E20'},
    'yellow': {'bg': '#FFF8E1', 'border': '#F9A825', 'text': '#E65100'},
    'red':    {'bg': '#FFEBEE', 'border': '#E53935', 'text': '#B71C1C'},
}

# Default color thresholds (minutes)
DEFAULT_SETTINGS = {
    'green_minutes': 3,
    'yellow_minutes': 5,
    'red_minutes': 7,
    'notification_tone': 'bell1',
    'call_max_minutes': 60,
}


# ── In-memory settings cache (event-driven invalidation) ──
_settings_cache: Dict[str, Any] = {}
_settings_cache_lock = threading.Lock()


def _invalidate_settings_cache():
    """Clear the settings cache so next read reloads from DB."""
    with _settings_cache_lock:
        _settings_cache.clear()


def init_settings_table(db_path: str):
    """Create settings table and insert defaults if not present."""
    try:
        with _open_db(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS callbell_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    'INSERT OR IGNORE INTO callbell_settings (key, value) VALUES (?, ?)',
                    (key, str(value))
                )
        logger.info("Settings table initialized")
    except Exception as e:
        logger.error(f"Failed to initialize settings table: {e}")


def get_color_settings(db_path: str) -> Dict[str, Any]:
    """Read color threshold settings — returns from cache if available."""
    with _settings_cache_lock:
        if _settings_cache:
            return _settings_cache.copy()
    settings = DEFAULT_SETTINGS.copy()
    try:
        with _open_db(db_path) as conn:
            rows = conn.execute('SELECT key, value FROM callbell_settings').fetchall()
            for key, value in rows:
                if key in settings:
                    if key == 'notification_tone':
                        settings[key] = value
                    else:
                        try:
                            settings[key] = int(value)
                        except (ValueError, TypeError):
                            pass
    except Exception as e:
        logger.error(f"Failed to read color settings: {e}")
    with _settings_cache_lock:
        _settings_cache.update(settings)
    return settings


def get_notification_tone(db_path: str) -> str:
    """Read notification tone — uses cached settings."""
    settings = get_color_settings(db_path)
    return settings.get('notification_tone', 'bell1')


def save_notification_tone(db_path: str, tone: str):
    """Save notification tone setting to DB and invalidate cache."""
    valid = ('default', 'bell1', 'bell2', 'bell3')
    if tone not in valid:
        raise ValueError(f'Invalid tone: {tone}. Must be one of {valid}')
    try:
        with _open_db(db_path) as conn:
            conn.execute('INSERT OR REPLACE INTO callbell_settings (key, value) VALUES (?, ?)',
                         ('notification_tone', tone))
        _invalidate_settings_cache()
        logger.info(f"Notification tone saved: {tone}")
    except Exception as e:
        logger.error(f"Failed to save notification tone: {e}")


def save_color_settings(db_path: str, green_minutes: int, yellow_minutes: int, red_minutes: int):
    """Save color threshold settings to DB and invalidate cache."""
    try:
        with _open_db(db_path) as conn:
            conn.execute('INSERT OR REPLACE INTO callbell_settings (key, value) VALUES (?, ?)',
                         ('green_minutes', str(green_minutes)))
            conn.execute('INSERT OR REPLACE INTO callbell_settings (key, value) VALUES (?, ?)',
                         ('yellow_minutes', str(yellow_minutes)))
            conn.execute('INSERT OR REPLACE INTO callbell_settings (key, value) VALUES (?, ?)',
                         ('red_minutes', str(red_minutes)))
        _invalidate_settings_cache()
        logger.info(f"Color settings saved: green={green_minutes}m, yellow={yellow_minutes}m, red={red_minutes}m")
    except Exception as e:
        logger.error(f"Failed to save color settings: {e}")


def compute_card_color(elapsed_seconds: float, priority: int, settings: Dict[str, int]) -> str:
    """
    Compute the card color level based on elapsed time and call priority.
    
    Priority mapping:
        1 = Emergency  → always red
        2 = Staff Assist → starts from yellow (skips gray/green)
        3 = Normal Call  → follows threshold rules
    
    Returns: 'gray', 'green', 'yellow', or 'red'
    """
    # Emergency: always red, no matter how long
    if priority == 1:
        return 'red'
    
    elapsed_min = elapsed_seconds / 60.0
    green_min = settings.get('green_minutes', 3)
    yellow_min = settings.get('yellow_minutes', 5)
    red_min = settings.get('red_minutes', 7)
    
    # Compute base level from elapsed time
    if elapsed_min >= red_min:
        level = 'red'
    elif elapsed_min >= yellow_min:
        level = 'yellow'
    elif elapsed_min >= green_min:
        level = 'green'
    else:
        level = 'gray'
    
    # Staff Assist: minimum color is yellow
    if priority == 2 and level in ('gray', 'green'):
        level = 'yellow'
    
    return level


class CallbellMonitor(ABC):
    """Abstract base class for callbell monitoring systems."""
    
    def __init__(self, site_id: str, site_name: str, db_path: str):
        """
        Initialize the callbell monitor.
        
        Args:
            site_id: Unique identifier for the site (e.g., 'ramsay', 'parafield_gardens')
            site_name: Display name for the site (e.g., 'Ramsay', 'Parafield Gardens')
            db_path: Path to the SQLite database file
        """
        self.site_id = site_id
        self.site_name = site_name
        self.db_path = db_path
        self.monitor_started = False
        self._buzz_levels_app = {}      # legacy — no longer used for client buzz
        self._push_levels = {}           # FCM push: buzz_key -> last pushed card_level
        self._push_lock = threading.Lock()
        self.debug_info = {
            'site_id': site_id,
            'site_name': site_name,
            'monitor_started': False,
            'monitor_type': self.__class__.__name__,
            'db_path': db_path,
            'last_error': None,
        }
        
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables."""
        # For Ramsay, use original table names for backward compatibility
        if self.site_id == 'ramsay':
            active_table = 'active_calls'
            history_table = 'call_history'
        else:
            # For other sites, use prefixed table names
            active_table = f'active_calls_{self.site_id}'
            history_table = f'call_history_{self.site_id}'
        
        self._active_table = active_table
        self._history_table = history_table
        
        schema = f"""
        CREATE TABLE IF NOT EXISTS {active_table} (
            room TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            priority INTEGER NOT NULL,
            start_time REAL NOT NULL,
            event_id TEXT,
            color TEXT,
            message_text TEXT,
            message_subtext TEXT,
            site_id TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS {history_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            type TEXT NOT NULL,
            priority INTEGER NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            event_id TEXT,
            duration_seconds REAL,
            site_id TEXT NOT NULL
        );
        """
        
        try:
            with _open_db(self.db_path) as conn:
                conn.executescript(schema)
                
                # Migrate existing tables: add ALL expected columns if missing
                # (CREATE TABLE IF NOT EXISTS won't alter existing tables)
                active_migrations = {
                    'event_id': 'TEXT', 'site_id': 'TEXT',
                    'color': 'TEXT', 'message_text': 'TEXT', 'message_subtext': 'TEXT',
                    'priority': 'INTEGER DEFAULT 3',
                }
                history_migrations = {
                    'event_id': 'TEXT', 'site_id': 'TEXT',
                    'priority': 'INTEGER DEFAULT 3',
                    'end_time': 'REAL', 'duration_seconds': 'REAL',
                }
                for tbl, migrations in [(active_table, active_migrations), (history_table, history_migrations)]:
                    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
                    for col, col_type in migrations.items():
                        if col not in cols:
                            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
                            logger.info(f"Migrated: added {col} to {tbl}")
                conn.commit()
            
            # Also ensure settings table exists
            init_settings_table(self.db_path)
            logger.info(f"✅ Database initialized for {self.site_name}")
        except Exception as e:
            logger.error(f"Failed to initialize database for {self.site_name}: {e}")
            self.debug_info['last_error'] = str(e)
    
    def save_call(self, room: str, call_type: str, priority: int, start_time: float,
                  event_id: Optional[str] = None, color: Optional[str] = None,
                  message_text: Optional[str] = None, message_subtext: Optional[str] = None):
        """Save a new active call to the database."""
        is_new = False
        try:
            with _open_db(self.db_path) as conn:
                cursor = conn.execute(f'''
                    INSERT OR IGNORE INTO {self._active_table}
                    (room, type, priority, start_time, event_id, color, message_text, message_subtext, site_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (room, call_type, priority, start_time, event_id, color, 
                      message_text or room, message_subtext or call_type, self.site_id))
                is_new = cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to save call for {self.site_name}: {e}")
            self.debug_info['last_error'] = str(e)
        
        if is_new:
            logger.info(f"[{self.site_name}] Call saved: {room} ({call_type}) priority={priority}")
            # Send FCM push in background thread (non-blocking)
            try:
                from firebase_push import send_push_for_new_call
                threading.Thread(
                    target=send_push_for_new_call,
                    kwargs=dict(
                        site_name=self.site_name, room=room, call_type=call_type,
                        priority=priority, message_text=message_text or room,
                        card_level='red' if priority <= 1 else 'yellow' if priority <= 2 else 'green',
                    ),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Failed to send push for new call: {e}")
    
    def archive_call(self, room: str, event_id: Optional[str] = None):
        """Archive and remove a call from active calls."""
        try:
            with _open_db(self.db_path) as conn:
                query = f'SELECT room, type, priority, start_time, event_id FROM {self._active_table} WHERE room = ?'
                params = [room]
                
                if event_id:
                    query += ' OR (event_id = ?)'
                    params.append(event_id)
                
                row = conn.execute(query, params).fetchone()
                
                if row:
                    end_time = time.time()
                    duration = end_time - row[3]
                    
                    conn.execute(f'''
                        INSERT INTO {self._history_table}
                        (room, type, priority, start_time, end_time, event_id, duration_seconds, site_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (row[0], row[1], row[2], row[3], end_time, row[4], duration, self.site_id))
                    
                    delete_query = f'DELETE FROM {self._active_table} WHERE room = ?'
                    delete_params = [room]
                    if event_id:
                        delete_query += ' OR (event_id = ?)'
                        delete_params.append(event_id)
                    
                    conn.execute(delete_query, delete_params)
                    logger.info(f"[{self.site_name}] Call archived: {room} (duration: {duration:.0f}s)")
        except Exception as e:
            logger.error(f"Failed to archive call for {self.site_name}: {e}")
            self.debug_info['last_error'] = str(e)
    
    def get_active_calls(self, consumer: str = 'web') -> List[Dict[str, Any]]:
        """Get all active calls with computed card colors. Pure read — no writes."""
        try:
            now = time.time()
            settings = get_color_settings(self.db_path)
            call_max_seconds = settings.get('call_max_minutes', 60) * 60
            
            with _open_db(self.db_path) as conn:
                rows = conn.execute(f'''
                    SELECT room, type, priority, start_time, color, message_text, message_subtext, event_id
                    FROM {self._active_table}
                ''').fetchall()
            
            calls = []
            current_event_ids = set()
            for r in rows:
                elapsed = now - r[3]
                # Skip stale calls in output (archive timer handles cleanup)
                if elapsed > call_max_seconds:
                    continue
                priority = r[2]
                event_id = r[7]
                card_level = compute_card_color(elapsed, priority, settings)
                style = CARD_STYLES[card_level]
                
                buzz_key = event_id if event_id is not None else r[0]
                current_event_ids.add(buzz_key)
                buzz = (consumer == 'app')
                
                calls.append({
                    'room': r[0],
                    'type': r[1],
                    'priority': priority,
                    'start': r[3],
                    'color': r[4] or '#ffffff',
                    'messageText': r[5] or r[0],
                    'messageSubText': r[6] or r[1],
                    'event_id': event_id,
                    'site_id': self.site_id,
                    'site_name': self.site_name,
                    'elapsed_seconds': int(elapsed),
                    'card_level': card_level,
                    'card_bg': style['bg'],
                    'card_border': style['border'],
                    'card_text': style['text'],
                    'buzz': buzz,
                })
            
            level_order = {'red': 0, 'yellow': 1, 'green': 2, 'gray': 3}
            calls.sort(key=lambda c: (level_order.get(c['card_level'], 3), -c['elapsed_seconds']))
            
            # Check for color escalations and send FCM push in background
            if consumer == 'app':
                self._check_push_escalations(calls, current_event_ids)
            
            return calls
        except Exception as e:
            logger.error(f"Failed to get active calls for {self.site_name}: {e}")
            self.debug_info['last_error'] = str(e)
            return []
    
    def _check_push_escalations(self, calls: List[Dict[str, Any]], current_keys: set):
        """Check if any call's color level changed and send FCM push if so."""
        with self._push_lock:
            escalated = []
            for call in calls:
                buzz_key = call.get('event_id') or call['room']
                current_level = call['card_level']
                prev_level = self._push_levels.get(buzz_key)
                
                if prev_level is not None and prev_level != current_level:
                    escalated.append(call)
                
                self._push_levels[buzz_key] = current_level
            
            stale = [k for k in self._push_levels if k not in current_keys]
            for k in stale:
                del self._push_levels[k]
        
        if escalated:
            try:
                from firebase_push import send_push_for_new_call
                level_order = {'red': 0, 'yellow': 1, 'green': 2, 'gray': 3}
                escalated.sort(key=lambda c: level_order.get(c['card_level'], 3))
                top = escalated[0]
                # Run FCM push in background thread
                threading.Thread(
                    target=send_push_for_new_call,
                    kwargs=dict(
                        site_name=self.site_name,
                        room=top['room'],
                        call_type=top.get('type', ''),
                        priority=top.get('priority', 3),
                        message_text=top.get('messageText', top['room']),
                        card_level=top['card_level'],
                    ),
                    daemon=True,
                ).start()
            except Exception as e:
                logger.error(f"Failed to send escalation push: {e}")
    
    def archive_stale_calls(self):
        """Archive calls that exceeded call_max_minutes. Called by periodic timer."""
        try:
            now = time.time()
            settings = get_color_settings(self.db_path)
            call_max_seconds = settings.get('call_max_minutes', 60) * 60
            
            with _open_db(self.db_path) as conn:
                rows = conn.execute(f'''
                    SELECT room FROM {self._active_table}
                    WHERE (? - start_time) > ?
                ''', (now, call_max_seconds)).fetchall()
            
            for (room,) in rows:
                try:
                    self.archive_call(room)
                    logger.info(f"[{self.site_name}] Auto-archived stale call: {room}")
                except Exception as e:
                    logger.error(f"Failed to auto-archive {room}: {e}")
        except Exception as e:
            logger.error(f"Failed to run archive timer for {self.site_name}: {e}")
    
    def clear_all_calls(self):
        """Clear all active calls for this site."""
        try:
            with _open_db(self.db_path) as conn:
                conn.execute(f'DELETE FROM {self._active_table}')
            logger.info(f"[{self.site_name}] All active calls cleared")
        except Exception as e:
            logger.error(f"Failed to clear calls for {self.site_name}: {e}")
            self.debug_info['last_error'] = str(e)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information for this monitor."""
        return self.debug_info.copy()
    
    @abstractmethod
    def start(self):
        """Start the callbell monitoring system (to be implemented by subclasses)."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop the callbell monitoring system (to be implemented by subclasses)."""
        pass
