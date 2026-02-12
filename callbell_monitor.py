"""
Ramsay Callbell Monitor — polling strategy (no WebSockets).
Loads credentials from site_config.json.
Provides: start_callbell_monitor(), REST API at /api/callbell/active,
          and the /ramsay-callbell page route via a Blueprint.
"""
import os
import re
import json
import time
import sqlite3
import logging
import threading
import requests
from flask import Blueprint, render_template, jsonify

logger = logging.getLogger(__name__)

# ── Paths ──
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CALLBELL_DB = os.path.join(_BASE_DIR, 'edenfield_calls.db')
_SITE_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'site_config.json')

# ── Load callbell credentials from site_config.json (Ramsay section) ──
def _load_callbell_config():
    """Read the Ramsay callbell config from site_config.json."""
    try:
        with open(_SITE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            sites = json.load(f)
        for site in sites:
            if site.get('id') == 'ramsay' and 'callbell' in site:
                cb = site['callbell']
                base_url = cb['base_url']
                return {
                    'base_url': base_url,
                    'login_url': f"{base_url}/Login.asp",
                    'data_url': f"{base_url}/server/GetPortData.asp",
                    'login_payload': {
                        'hdnSuper': cb['hdnSuper'],
                        'hdnDealer': cb['hdnDealer'],
                        'User': cb['username'],
                        'Password': cb['password'],
                        'hdnKill': '1',
                    },
                    'headers': {
                        'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.3; WOW64; Trident/7.0)',
                        'Connection': 'Keep-Alive',
                    },
                }
        logger.error('Ramsay callbell section not found in site_config.json')
    except Exception as e:
        logger.error(f'Failed to load callbell config from site_config.json: {e}')
    return None

_config = _load_callbell_config()

# ── DB schema ──
_SCHEMA = """
CREATE TABLE IF NOT EXISTS active_calls (
    room TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    priority INTEGER NOT NULL,
    start_time REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS call_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT NOT NULL,
    type TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL
);
"""

def _init_db():
    conn = sqlite3.connect(_CALLBELL_DB)
    conn.executescript(_SCHEMA)
    conn.commit()
    conn.close()

_init_db()

# ── DB helpers ──
def _save(room, call_type, priority, start_time):
    with sqlite3.connect(_CALLBELL_DB) as conn:
        conn.execute('INSERT OR REPLACE INTO active_calls VALUES (?, ?, ?, ?)',
                     (room, call_type, priority, start_time))

def _archive(room):
    with sqlite3.connect(_CALLBELL_DB) as conn:
        row = conn.execute('SELECT room, type, start_time FROM active_calls WHERE room = ?',
                           (room,)).fetchone()
        if row:
            conn.execute('INSERT INTO call_history (room, type, start_time, end_time) VALUES (?, ?, ?, ?)',
                         (row[0], row[1], row[2], time.time()))
        conn.execute('DELETE FROM active_calls WHERE room = ?', (room,))

def get_active_calls():
    with sqlite3.connect(_CALLBELL_DB) as conn:
        rows = conn.execute('SELECT room, type, priority, start_time FROM active_calls').fetchall()
        return [{'room': r[0], 'type': r[1], 'priority': r[2], 'start': r[3]} for r in rows]

def _decode(raw_data):
    matches = re.findall(r'(\d{3}(?:,\d{3})*)', raw_data)
    return [''.join([chr(int(c)) for c in m.split(',')]) for m in matches]

# ── Background monitor thread ──
def _monitor_loop():
    """Background thread: poll callbell hardware and update DB."""
    if not _config:
        logger.error('Callbell config not found in site_config.json — monitor disabled')
        return

    hw_session = requests.Session()
    hw_session.headers.update(_config['headers'])
    pdata_val = '1257726'

    while True:
        try:
            response = hw_session.get(_config['data_url'],
                                      params={'id': '10', 'pdata': pdata_val}, timeout=10)
            if response.status_code != 200 or 'Login.asp' in response.text:
                hw_session.post(_config['login_url'], data=_config['login_payload'], timeout=10)
                continue

            raw_text = response.text
            new_id = re.search(r'^(\d+):', raw_text)
            if new_id:
                pdata_val = new_id.group(1)

            messages = _decode(raw_text)
            for msg in messages:
                room_match = re.search(r'\[(.*?)\]', msg)
                if not room_match:
                    continue
                room_id = room_match.group(1)

                if 'Cancelled' in msg:
                    _archive(room_id)
                else:
                    call_type, priority = 'Normal', 3
                    if 'EMERGENCY' in msg:
                        call_type, priority = 'Emergency', 1
                    elif 'Staff Assist' in msg:
                        call_type, priority = 'Staff Assist', 2
                    elif 'CALL' in msg:
                        call_type, priority = 'Call', 3
                    else:
                        continue

                    active = get_active_calls()
                    found = next((c for c in active if c['room'] == room_id), None)
                    start_time = found['start'] if found else time.time()
                    if not found:
                        _save(room_id, call_type, priority, start_time)

            time.sleep(1)
        except Exception as e:
            logger.warning(f'Callbell hardware link down: {e}')
            time.sleep(2)

def start_callbell_monitor():
    """Start the callbell hardware polling thread (daemon)."""
    t = threading.Thread(target=_monitor_loop, daemon=True)
    t.start()
    logger.info('✅ Ramsay Callbell monitor started (polling mode)')

# ── Blueprint (public routes, no login) ──
callbell_bp = Blueprint('callbell', __name__)

@callbell_bp.route('/ramsay-callbell')
def ramsay_callbell():
    """Public callbell monitor page — no login required."""
    return render_template('ramsay_callbell.html')

@callbell_bp.route('/api/callbell/active')
def api_callbell_active():
    """REST endpoint — returns current active calls as JSON."""
    return jsonify(get_active_calls())
