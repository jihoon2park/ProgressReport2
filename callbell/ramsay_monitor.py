"""
Ramsay Callbell Monitor - Polling-based implementation
Polls the Ramsay callbell hardware via HTTP and decodes proprietary format.
"""
import re
import time
import logging
import threading
import requests
from typing import Dict, Any, Optional
from .base_monitor import CallbellMonitor

logger = logging.getLogger(__name__)


class RamsayCallbellMonitor(CallbellMonitor):
    """Ramsay-specific callbell monitor using HTTP polling."""
    
    def __init__(self, site_id: str, site_name: str, db_path: str, config: Dict[str, Any]):
        """
        Initialize Ramsay callbell monitor.
        
        Args:
            site_id: Site identifier (e.g., 'ramsay')
            site_name: Display name (e.g., 'Ramsay')
            db_path: Path to SQLite database
            config: Ramsay callbell configuration with keys:
                - base_url: Base URL of the callbell system
                - username: Login username
                - password: Login password
                - hdnSuper: Hidden super field
                - hdnDealer: Hidden dealer field
        """
        super().__init__(site_id, site_name, db_path)
        
        self.config = config
        self.base_url = config['base_url']
        self.login_url = f"{self.base_url}/Login.asp"
        self.data_url = f"{self.base_url}/server/GetPortData.asp"
        
        self.session = None
        self.monitor_thread = None
        self.running = False
        
        # Update debug info
        self.debug_info.update({
            'base_url': self.base_url,
            'poll_count': 0,
            'last_status': None,
            'last_response_len': None,
            'last_raw_preview': None,
            'last_decoded_count': None,
            'last_saved': None,
        })
    
    def _decode_message(self, raw_data: str) -> list:
        """
        Decode Ramsay's proprietary message format.
        Format: comma-separated ASCII codes (e.g., "072,101,108,108,111" = "Hello")
        """
        matches = re.findall(r'(\d{3}(?:,\d{3})*)', raw_data)
        return [''.join([chr(int(c)) for c in m.split(',')]) for m in matches]
    
    def _monitor_loop(self):
        """Background polling loop - exact copy of working callbell_monitor.py logic."""
        self.debug_info['monitor_started'] = True
        logger.info(f"[{self.site_name}] Monitor loop started")
        
        hw_session = requests.Session()
        hw_session.headers.update({
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.3; WOW64; Trident/7.0)',
            'Connection': 'Keep-Alive',
        })
        pdata_val = '1257726'
        poll_count = 0
        
        while self.running:
            try:
                poll_count += 1
                self.debug_info['poll_count'] = poll_count
                response = hw_session.get(self.data_url,
                                          params={'id': '10', 'pdata': pdata_val}, timeout=10)
                self.debug_info['last_status'] = response.status_code
                self.debug_info['last_response_len'] = len(response.text)
                logger.debug(f'[{self.site_name}] Poll #{poll_count} status={response.status_code} len={len(response.text)}')

                raw_text = response.text.strip()

                # Only re-login if the response is an actual HTML login page, not just data containing "Login.asp"
                if response.status_code != 200 or (raw_text.startswith('<') and 'Login.asp' in raw_text):
                    logger.info(f'[{self.site_name}] Re-login required (status={response.status_code}, starts_with_html={raw_text[:20]})')
                    hw_session.post(self.login_url, data={
                        'hdnSuper': self.config['hdnSuper'],
                        'hdnDealer': self.config['hdnDealer'],
                        'User': self.config['username'],
                        'Password': self.config['password'],
                        'hdnKill': '1',
                    }, timeout=10)
                    continue

                # Skip empty/null responses
                if not raw_text or raw_text == 'null':
                    time.sleep(1)
                    continue

                self.debug_info['last_raw_preview'] = repr(raw_text[:200])

                new_id = re.search(r'^(\d+):', raw_text)
                if new_id:
                    pdata_val = new_id.group(1)

                messages = self._decode_message(raw_text)
                self.debug_info['last_decoded_count'] = len(messages)
                for msg in messages:
                    self._process_message(msg)

                # Log DB state periodically
                if poll_count % 10 == 0:
                    active = self.get_active_calls()
                    logger.debug(f"[{self.site_name}] Active calls: {len(active)}")

                time.sleep(1)
            except Exception as e:
                logger.error(f"[{self.site_name}] Poll error: {e}")
                self.debug_info['last_error'] = str(e)
                time.sleep(2)
    
    def _process_message(self, msg: str):
        """Process a decoded message and update the database."""
        # Extract room number from message (format: [ROOM_ID])
        room_match = re.search(r'\[(.*?)\]', msg)
        if not room_match:
            return
        
        room_id = room_match.group(1)
        
        # Check if call was cancelled
        if 'Cancelled' in msg:
            self.archive_call(room_id)
            return
        
        # Determine call type and priority
        call_type = 'Normal'
        priority = 3
        
        if 'EMERGENCY' in msg:
            call_type = 'Emergency'
            priority = 1
        elif 'Staff Assist' in msg:
            call_type = 'Staff Assist'
            priority = 2
        elif 'CALL' in msg:
            call_type = 'Call'
            priority = 3
        else:
            return  # Unknown type, skip
        
        # Check if call already exists
        active = self.get_active_calls()
        found = next((c for c in active if c['room'] == room_id), None)
        
        if not found:
            # New call - save it
            start_time = time.time()
            self.save_call(room_id, call_type, priority, start_time)
            self.debug_info['last_saved'] = f'{room_id} ({call_type})'
    
    def start(self):
        """Start the Ramsay callbell monitor."""
        if self.running:
            logger.warning(f"[{self.site_name}] Monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.monitor_started = True
        logger.info(f"✅ [{self.site_name}] Callbell monitor started (polling mode)")
    
    def stop(self):
        """Stop the Ramsay callbell monitor."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.session:
            self.session.close()
        logger.info(f"🛑 [{self.site_name}] Callbell monitor stopped")
