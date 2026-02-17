"""
Parafield Gardens Callbell Monitor - WebSocket-based implementation
Connects to Aptus annunciator system via WebSocket for real-time call events.
"""
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from .base_monitor import CallbellMonitor

logger = logging.getLogger(__name__)

# ── Type code suffix translations for display ──
# Longest suffixes first to avoid partial matches (e.g., "ENS C" before "C")
_TYPE_SUFFIXES = [
    (' ENS C', ' ENS CALL'),
    (' ENS A', ' ENS ASSIST'),
    (' ENS', ' ENSUITE'),
    (' OB', ' OUT OF BED'),
    (' BA', ' BATHROOM ASSIST'),
    (' WB', ' WANDER'),
    (' C', ' CALL'),
    (' A', ' ASSIST'),
    (' E', ' EMERGENCY'),
    (' B', ' BED'),
]


def _translate_room_display(raw: str) -> str:
    """Translate type code suffix in room name for display.
    e.g. 'KURR RM 4.2 C' -> 'KURR RM 4.2 CALL'
    """
    upper = raw.strip().upper()
    for suffix, replacement in _TYPE_SUFFIXES:
        if upper.endswith(suffix):
            return upper[:-len(suffix)] + replacement
    return upper


# Import WebSocket dependencies
try:
    import socketio
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("python-socketio not installed. Parafield monitor will not work.")
    logger.warning("Install with: pip install python-socketio[client]")


class ParafieldCallbellMonitor(CallbellMonitor):
    """Parafield Gardens (Aptus) callbell monitor using WebSocket."""
    
    def __init__(self, site_id: str, site_name: str, db_path: str, config: Dict[str, Any]):
        """
        Initialize Parafield callbell monitor.
        
        Args:
            site_id: Site identifier (e.g., 'parafield_gardens')
            site_name: Display name (e.g., 'Parafield Gardens')
            db_path: Path to SQLite database
            config: Aptus configuration with keys:
                - host: Aptus server IP/hostname
                - port: Aptus server port
                - device_id: Aptus device ID
                - username: Login username
                - password: Login password
                - use_ssl: Whether to use HTTPS (default: False)
        """
        super().__init__(site_id, site_name, db_path)
        
        if not WEBSOCKET_AVAILABLE:
            raise ImportError("python-socketio is required for Parafield monitor")
        
        self.config = config
        self.host = config['host']
        self.port = config['port']
        self.device_id = config['device_id']
        self.use_ssl = config.get('use_ssl', False)
        
        protocol = 'https' if self.use_ssl else 'http'
        self.base_url = f"{protocol}://{self.host}:{self.port}"
        
        self.session = None
        self.sio = None
        self.monitor_thread = None
        self.running = False
        self.authenticated = False
        
        # Update debug info
        self.debug_info.update({
            'host': self.host,
            'port': self.port,
            'device_id': self.device_id,
            'websocket_connected': False,
            'last_event_time': None,
            'total_calls_received': 0,
            'total_calls_cancelled': 0,
        })
    
    
    def _setup_websocket_handlers(self):
        """Register Socket.IO event handlers."""
        did = self.device_id
        
        @self.sio.event
        def connect():
            logger.info(f"✅ [{self.site_name}] WebSocket connected (sid={self.sio.sid})")
            self.debug_info['websocket_connected'] = True
            self.debug_info['last_connect_time'] = time.time()
            # Send time sync
            ms = int(time.time() * 1000)
            self.sio.emit("system/time", {"ts": ms})
        
        @self.sio.event
        def disconnect():
            logger.warning(f"❌ [{self.site_name}] WebSocket disconnected")
            self.debug_info['websocket_connected'] = False
            self.debug_info['last_disconnect_time'] = time.time()
        
        @self.sio.event
        def connect_error(data):
            logger.error(f"❌ [{self.site_name}] WebSocket connection error: {data}")
            self.debug_info['last_error'] = f"Connection error: {data}"
        
        # Handle raiseCall events
        @self.sio.on(f"{did}/raiseCall")
        def on_raise_call(data):
            self.debug_info['last_event_time'] = datetime.now().isoformat()
            self.debug_info['total_calls_received'] += 1
            
            if isinstance(data, dict) and 'event' in data:
                event = data['event']
                self._handle_raise_call(event)
                
                # Send ACK
                event_id = event.get('eventInstanceId')
                if event_id:
                    self.sio.emit("ack", event_id)
        
        # Handle cancelCall events
        @self.sio.on(f"{did}/cancelCall")
        def on_cancel_call(data):
            self.debug_info['last_event_time'] = datetime.now().isoformat()
            self.debug_info['total_calls_cancelled'] += 1
            
            if isinstance(data, dict) and 'event' in data:
                event = data['event']
                self._handle_cancel_call(event)
        
        # Handle time sync
        @self.sio.on("time")
        def on_time(data):
            pass  # Just acknowledge time sync
    
    def _handle_raise_call(self, event: Dict[str, Any]):
        """Process a raiseCall event."""
        room = event.get('messageText', 'Unknown')
        call_type = event.get('messageSubText', 'CALL')
        parafield_priority = event.get('priority', 1)
        event_id = event.get('eventInstanceId', '')
        color = event.get('colour', '#ffffff')
        start_time = event.get('eventDatetime', time.time() * 1000) / 1000  # Convert ms to seconds
        
        # Map Parafield priority to Ramsay convention:
        # Parafield priority 1 (CALL, OUT OF BED, ENSUITE) = Ramsay priority 3 (normal/red)
        # Parafield priority 2 (ASSIST) = Ramsay priority 2 (staff assist/yellow)
        # Parafield priority 0 or other = Ramsay priority 1 (emergency/highest)
        if parafield_priority == 1:
            priority = 3  # Normal call (red color)
        elif parafield_priority == 2:
            priority = 2  # Staff assist (yellow color)
        else:
            priority = 1  # Emergency (highest priority)
        
        display_text = _translate_room_display(room)
        
        self.save_call(
            room=room,
            call_type=call_type,
            priority=priority,
            start_time=start_time,
            event_id=event_id,
            color=color,
            message_text=display_text,
            message_subtext=call_type
        )
    
    def _handle_cancel_call(self, event: Dict[str, Any]):
        """Process a cancelCall event."""
        room = event.get('messageText', 'Unknown')
        event_id = event.get('eventInstanceId', '')
        self.archive_call(room, event_id)
    
    def _time_sync_loop(self):
        """Periodic time synchronization (every 6 minutes)."""
        while self.running and self.sio and self.sio.connected:
            time.sleep(360)
            if self.sio and self.sio.connected:
                ms = int(time.time() * 1000)
                self.sio.emit("system/time", {"ts": ms})
    
    def _connect_websocket(self) -> bool:
        """Connect to Aptus WebSocket server (no authentication required)."""
        current_time_ms = int(time.time() * 1000)
        query_params = {
            "deviceId": self.device_id,
            "startTime": str(current_time_ms),
            "screenWidth": "1920",
            "screenHeight": "1080",
            "serialNumber": "",
            "imei": "",
            "x-session-id": "",
        }
        
        qs = "&".join(f"{k}={v}" for k, v in query_params.items())
        url_with_query = f"{self.base_url}?{qs}"
        
        try:
            self.sio.connect(
                url_with_query,
                socketio_path="/annunciator/socketio",
                transports=["websocket", "polling"],
                wait_timeout=10,
            )
            logger.info(f"✅ [{self.site_name}] Connected via polling transport")
            return True
        except Exception as e:
            logger.error(f"[{self.site_name}] Connection failed: {e}")
            self.debug_info['last_error'] = str(e)
            return False
    
    def _monitor_loop(self):
        """Background monitoring loop with automatic reconnection."""
        self.debug_info['monitor_started'] = True
        logger.info(f"[{self.site_name}] Monitor loop started (no authentication required)")
        
        while self.running:
            try:
                self.sio = socketio.Client(
                    reconnection=True,
                    reconnection_delay=5,
                    reconnection_attempts=0,
                    logger=False,
                    engineio_logger=False,
                )
                
                self._setup_websocket_handlers()
                
                if not self._connect_websocket():
                    logger.warning(f"[{self.site_name}] Connection failed, retrying in 30s...")
                    time.sleep(30)
                    continue
                
                # Start time sync thread
                time_sync_thread = threading.Thread(target=self._time_sync_loop, daemon=True)
                time_sync_thread.start()
                
                # Keep connection alive
                self.sio.wait()
                
            except Exception as e:
                logger.error(f"[{self.site_name}] Monitor loop error: {e}")
                self.debug_info['last_error'] = str(e)
            
            # If we get here, connection was lost — retry after delay
            if self.running:
                logger.info(f"[{self.site_name}] Reconnecting in 30s...")
                time.sleep(30)
    
    def start(self):
        """Start the Parafield callbell monitor."""
        if self.running:
            logger.warning(f"[{self.site_name}] Monitor already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.monitor_started = True
        logger.info(f"✅ [{self.site_name}] Callbell monitor started (WebSocket mode)")
    
    def stop(self):
        """Stop the Parafield callbell monitor."""
        self.running = False
        if self.sio and self.sio.connected:
            self.sio.disconnect()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info(f"🛑 [{self.site_name}] Callbell monitor stopped")
