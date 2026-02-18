"""
Ramsay Callbell Monitor - UDP Syslog listener implementation.
Listens for Kiwi syslog packets on UDP and parses call events.

Packet format (from Kiwi at 192.168.31.124):
  <150>2026-02-18 12:08:33 Edenfield Ramsay: Message "[RM 56 BED] CALL #5 " has been dispatched to Jaycee Display (5)
  <150>2026-02-18 12:09:25 Edenfield Ramsay: Message "[RM 12 BED] EMERGENCY #5 " has been dispatched to Jaycee Display (5)
  <150>2026-02-18 12:09:16 Edenfield Ramsay: Message "[RM 12 BED] CALL #7 Staff Assist" has been dispatched to ...
  <150>2026-02-18 12:09:34 Edenfield Ramsay: Message "Cancelled: [RM 12 BED] CALL #5 " has been dispatched to ...

We only care about "has been dispatched" messages.
Ignore: "completed successfully", "purged due to reaching queue size limit".
"""
import re
import os
import time
import socket
import logging
import threading
from typing import Dict, Any, Optional
from .base_monitor import CallbellMonitor

logger = logging.getLogger(__name__)

# Extract the quoted content from a "dispatched" syslog message
_DISPATCH_RE = re.compile(r'Message "(.+?)"\s+has been dispatched')

# Parse call info from the extracted content
# Handles: [RM 56 BED] CALL #5    / [RM 12 BED] EMERGENCY #5
#           [RM 12 BED] CALL #7 Staff Assist
#           Cancelled: [RM 12 BED] CALL #5
_CALL_RE = re.compile(
    r'(?P<cancelled>Cancelled:\s*)?'
    r'\[(?P<room>[^\]]+)\]\s*'
    r'(?P<type>EMERGENCY|CALL)\s*#\d+\s*(?P<subtype>Staff Assist)?'
)


class RamsayCallbellMonitor(CallbellMonitor):
    """Ramsay-specific callbell monitor using UDP syslog listener."""

    def __init__(self, site_id: str, site_name: str, db_path: str, config: Dict[str, Any]):
        """
        Initialize Ramsay callbell monitor.

        Args:
            site_id: Site identifier (e.g., 'ramsay')
            site_name: Display name (e.g., 'Ramsay')
            db_path: Path to SQLite database
            config: Ramsay callbell configuration with keys:
                - listen_port: UDP port to listen on (default 514)
                - source_ip:   IP of Kiwi syslog forwarder to accept packets from
        """
        super().__init__(site_id, site_name, db_path)

        self.config = config
        logger.info(f"[{site_name}] Ramsay config received: {config}")
        self.listen_ip = config.get('listen_ip', '0.0.0.0')
        self.listen_port = config.get('listen_port', 10514)
        self.source_ip = config.get('source_ip')  # e.g. '192.168.31.124'
        logger.info(f"[{site_name}] Will listen on {self.listen_ip}:{self.listen_port}, source_ip={self.source_ip}")

        self.sock = None
        self.monitor_thread = None
        self.running = False

        # Dedup: each call dispatches to multiple groups; only process once.
        # Key = "room_key|raise" or "room_key|cancel", Value = timestamp
        self._recent_dispatches: Dict[str, float] = {}
        self._dedup_ttl = 5  # seconds

        # Debug info
        self.debug_info.update({
            'listen_port': self.listen_port,
            'source_ip': self.source_ip,
            'packets_received': 0,
            'calls_processed': 0,
            'cancels_processed': 0,
            'last_packet': None,
            'last_saved': None,
        })

    # ── Syslog message parsing ──────────────────────────────────

    def _parse_syslog(self, raw: str) -> Optional[Dict[str, Any]]:
        """
        Parse a syslog message. Returns call info dict or None.

        Only "has been dispatched" messages are processed.
        Returns:
            {room_key, room, call_type, priority, cancelled, display_text}
        """
        dispatch_match = _DISPATCH_RE.search(raw)
        if not dispatch_match:
            return None

        msg_content = dispatch_match.group(1).strip()

        call_match = _CALL_RE.search(msg_content)
        if not call_match:
            return None

        cancelled = bool(call_match.group('cancelled'))
        room = call_match.group('room').strip()       # e.g. "RM 56 BED"
        msg_type = call_match.group('type')            # "CALL" or "EMERGENCY"
        subtype = call_match.group('subtype')          # "Staff Assist" or None

        if msg_type == 'EMERGENCY':
            call_type = 'Emergency'
            priority = 1
            display_type = 'EMERGENCY'
        elif subtype and 'Staff Assist' in subtype:
            call_type = 'Staff Assist'
            priority = 2
            display_type = 'STAFF ASSIST'
        else:
            call_type = 'Call'
            priority = 3
            display_type = 'CALL'

        # Room key unique per room + type (a room can have CALL + EMERGENCY at same time)
        room_key = f"{room}|{call_type}"
        display_text = f"{room} - {display_type}"

        return {
            'room_key': room_key,
            'room': room,
            'call_type': call_type,
            'priority': priority,
            'cancelled': cancelled,
            'display_text': display_text,
        }

    # ── Deduplication ───────────────────────────────────────────

    def _dedup_check(self, key: str) -> bool:
        """Return True if this key was already seen recently (should skip)."""
        now = time.time()
        # Cleanup expired entries
        expired = [k for k, t in self._recent_dispatches.items() if now - t > self._dedup_ttl]
        for k in expired:
            del self._recent_dispatches[k]
        # Check
        if key in self._recent_dispatches:
            return True
        self._recent_dispatches[key] = now
        return False

    # ── Main listener loop ──────────────────────────────────────

    def _acquire_lock(self) -> bool:
        """Try to acquire a file lock so only one process runs the monitor."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
        lock_path = os.path.join(data_dir, f'.ramsay_monitor_{self.listen_port}.lock')
        try:
            import msvcrt
            self._lock_file = open(lock_path, 'w')
            msvcrt.locking(self._lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            self._lock_file.write(str(os.getpid()))
            self._lock_file.flush()
            return True
        except Exception:
            if hasattr(self, '_lock_file') and self._lock_file:
                self._lock_file.close()
                self._lock_file = None
            return False

    def _try_bind(self) -> bool:
        """Try to bind the UDP socket. Returns True if successful."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.sock.bind((self.listen_ip, self.listen_port))
            self.sock.settimeout(2.0)
            return True
        except OSError as e:
            if self.sock:
                self.sock.close()
                self.sock = None
            self.debug_info['last_error'] = str(e)
            return False

    def _monitor_loop(self):
        """Background UDP listener loop with file lock."""
        self.debug_info['monitor_started'] = True
        self.debug_info['status'] = 'starting'
        logger.info(f"[{self.site_name}] UDP syslog listener starting on {self.listen_ip}:{self.listen_port}")

        # Only one process should run the monitor - use file lock
        if not self._acquire_lock():
            self.debug_info['status'] = 'standby - another process is monitoring'
            logger.info(f"[{self.site_name}] Another process holds the monitor lock. Standing by.")
            # Wait in standby - if the other process dies, try to take over
            while self.running:
                time.sleep(10)
                if self._acquire_lock():
                    logger.info(f"[{self.site_name}] Lock acquired - taking over monitoring")
                    break
            if not self.running:
                return

        # We have the lock - bind the port
        self.debug_info['status'] = 'binding_port'
        if not self._try_bind():
            # Port stuck from a crashed process - wait for OS to release it
            logger.info(f"[{self.site_name}] Port {self.listen_port} not ready, waiting for OS to release...")
            for attempt in range(12):  # Wait up to 60 seconds
                if not self.running:
                    return
                time.sleep(5)
                if self._try_bind():
                    break
            else:
                self.debug_info['status'] = 'failed - could not bind port'
                logger.error(f"[{self.site_name}] Could not bind port {self.listen_port} after 60s")
                return

        self.debug_info['status'] = 'listening - waiting for packets'
        logger.info(f"✅ [{self.site_name}] Listening on UDP {self.listen_ip}:{self.listen_port}")

        while self.running:
            try:
                try:
                    data, addr = self.sock.recvfrom(4096)
                except socket.timeout:
                    continue

                # Filter by source IP if configured
                if self.source_ip and addr[0] != self.source_ip:
                    continue

                message = data.decode('utf-8', errors='ignore')
                self.debug_info['packets_received'] += 1
                self.debug_info['last_packet'] = message[:200]
                self.debug_info['status'] = 'connected - receiving packets'
                parsed = self._parse_syslog(message)
                if not parsed:
                    continue

                # Dedup: skip if we already processed this dispatch recently
                action = 'cancel' if parsed['cancelled'] else 'raise'
                dedup_key = f"{parsed['room_key']}|{action}"
                if self._dedup_check(dedup_key):
                    continue

                if parsed['cancelled']:
                    self.archive_call(parsed['room_key'])
                    self.debug_info['cancels_processed'] += 1
                    logger.info(f"📴 [{self.site_name}] Call cancelled: {parsed['display_text']}")
                else:
                    self.save_call(
                        room=parsed['room_key'],
                        call_type=parsed['call_type'],
                        priority=parsed['priority'],
                        start_time=time.time(),
                        message_text=parsed['display_text'],
                        message_subtext=parsed['call_type'],
                    )
                    self.debug_info['calls_processed'] += 1
                    self.debug_info['last_saved'] = parsed['display_text']
                    logger.info(
                        f"📞 [{self.site_name}] New call: {parsed['display_text']} "
                        f"(priority={parsed['priority']})"
                    )

            except Exception as e:
                logger.error(f"[{self.site_name}] Listener error: {e}")
                self.debug_info['last_error'] = str(e)
                time.sleep(1)

        # Cleanup
        if self.sock:
            self.sock.close()
            logger.info(f"[{self.site_name}] UDP socket closed")

    # ── Start / Stop ────────────────────────────────────────────

    def start(self):
        """Start the Ramsay callbell monitor."""
        if self.running:
            logger.warning(f"[{self.site_name}] Monitor already running")
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.monitor_started = True
        logger.info(f"✅ [{self.site_name}] Callbell monitor started (UDP syslog listener)")

    def stop(self):
        """Stop the Ramsay callbell monitor."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        logger.info(f"🛑 [{self.site_name}] Callbell monitor stopped")
