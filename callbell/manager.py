"""
Multi-Site Callbell Manager
Manages multiple callbell monitoring systems and provides unified API access.
"""
import os
import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from flask_login import current_user

from .base_monitor import (
    CallbellMonitor, get_color_settings, save_color_settings,
    init_settings_table, CARD_STYLES
)
from .ramsay_monitor import RamsayCallbellMonitor
from .parafield_monitor import ParafieldCallbellMonitor

logger = logging.getLogger(__name__)


class CallbellManager:
    """Manages multiple callbell monitoring systems."""
    
    def __init__(self, db_path: str, site_config_path: str):
        """
        Initialize the callbell manager.
        
        Args:
            db_path: Path to the SQLite database file
            site_config_path: Path to site_config.json
        """
        self.db_path = db_path
        self.site_config_path = site_config_path
        self.monitors: Dict[str, CallbellMonitor] = {}
        self.site_configs = []
        
        self._load_site_configs()
        # Ensure settings table exists
        init_settings_table(self.db_path)
    
    def _load_site_configs(self):
        """Load site configurations from JSON file."""
        try:
            with open(self.site_config_path, 'r', encoding='utf-8') as f:
                self.site_configs = json.load(f)
            logger.info(f"✅ Loaded {len(self.site_configs)} site configurations")
        except Exception as e:
            logger.error(f"Failed to load site configs: {e}")
            self.site_configs = []
    
    def _get_site_config(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific site."""
        for site in self.site_configs:
            if site.get('id') == site_id:
                return site
        return None
    
    def register_monitor(self, site_id: str, monitor_type: str = 'auto') -> bool:
        """
        Register and start a callbell monitor for a site.
        
        Args:
            site_id: Site identifier (e.g., 'ramsay', 'parafield_gardens')
            monitor_type: Type of monitor ('ramsay', 'parafield', or 'auto' to detect)
        
        Returns:
            True if monitor was registered successfully, False otherwise
        """
        if site_id in self.monitors:
            logger.warning(f"Monitor for {site_id} already registered")
            return False
        
        site_config = self._get_site_config(site_id)
        if not site_config:
            logger.error(f"No configuration found for site: {site_id}")
            return False
        
        if not site_config.get('is_active', True):
            logger.info(f"Site {site_id} is not active, skipping")
            return False
        
        # Check if site has callbell configuration
        if 'callbell' not in site_config:
            logger.info(f"Site {site_id} has no callbell configuration, skipping")
            return False
        
        site_name = site_config.get('site_name', site_id)
        callbell_config = site_config['callbell']
        
        # Auto-detect monitor type if needed
        if monitor_type == 'auto':
            if 'base_url' in callbell_config:
                monitor_type = 'ramsay'
            elif 'host' in callbell_config:
                monitor_type = 'parafield'
            else:
                logger.error(f"Cannot auto-detect monitor type for {site_id}")
                return False
        
        # Create the appropriate monitor
        try:
            if monitor_type == 'ramsay':
                monitor = RamsayCallbellMonitor(site_id, site_name, self.db_path, callbell_config)
            elif monitor_type == 'parafield':
                monitor = ParafieldCallbellMonitor(site_id, site_name, self.db_path, callbell_config)
            else:
                logger.error(f"Unknown monitor type: {monitor_type}")
                return False
            
            # Start the monitor
            monitor.start()
            self.monitors[site_id] = monitor
            logger.info(f"✅ Registered and started monitor for {site_name} ({site_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register monitor for {site_id}: {e}")
            return False
    
    def get_monitor(self, site_id: str) -> Optional[CallbellMonitor]:
        """Get a specific monitor by site ID."""
        return self.monitors.get(site_id)
    
    def get_all_active_calls(self) -> List[Dict[str, Any]]:
        """Get active calls from all registered monitors."""
        all_calls = []
        for site_id, monitor in self.monitors.items():
            calls = monitor.get_active_calls()
            all_calls.extend(calls)
        return all_calls
    
    def get_site_active_calls(self, site_id: str) -> List[Dict[str, Any]]:
        """Get active calls for a specific site."""
        monitor = self.get_monitor(site_id)
        if monitor:
            return monitor.get_active_calls()
        return []
    
    def clear_site_calls(self, site_id: str) -> bool:
        """Clear all active calls for a specific site."""
        monitor = self.get_monitor(site_id)
        if monitor:
            monitor.clear_all_calls()
            return True
        return False
    
    def reset_all_calls(self):
        """Reset all active calls across all known tables (used on server startup)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all active_calls tables
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'active_calls%'"
                ).fetchall()
                for (table_name,) in tables:
                    conn.execute(f'DELETE FROM {table_name}')
                    logger.info(f"🗑️ Auto-reset: cleared {table_name}")
            logger.info("✅ All active call tables cleared on startup")
        except Exception as e:
            logger.error(f"Failed to reset all calls: {e}")
    
    def get_debug_info(self, site_id: Optional[str] = None) -> Dict[str, Any]:
        """Get debug information for one or all monitors."""
        if site_id:
            monitor = self.get_monitor(site_id)
            if monitor:
                return monitor.get_debug_info()
            return {}
        else:
            return {
                site_id: monitor.get_debug_info()
                for site_id, monitor in self.monitors.items()
            }
    
    def stop_all(self):
        """Stop all registered monitors."""
        for site_id, monitor in self.monitors.items():
            try:
                monitor.stop()
                logger.info(f"Stopped monitor for {site_id}")
            except Exception as e:
                logger.error(f"Error stopping monitor for {site_id}: {e}")
        self.monitors.clear()


# Global manager instance
_manager: Optional[CallbellManager] = None


def get_manager() -> CallbellManager:
    """Get the global callbell manager instance."""
    global _manager
    if _manager is None:
        raise RuntimeError("CallbellManager not initialized. Call init_manager() first.")
    return _manager


def init_manager(db_path: str, site_config_path: str) -> CallbellManager:
    """Initialize the global callbell manager."""
    global _manager
    _manager = CallbellManager(db_path, site_config_path)
    return _manager


# ── Flask Blueprint ──
callbell_bp = Blueprint('callbell', __name__)


@callbell_bp.route('/callbell')
def callbell_page():
    """Unified callbell monitor page. All data comes from /api/callbell/poll."""
    return render_template('callbell.html')


# Legacy routes for backward compatibility
@callbell_bp.route('/ramsay-callbell')
def ramsay_callbell_page():
    """Ramsay callbell monitor page."""
    return redirect(url_for('callbell.callbell_page'))

@callbell_bp.route('/parafield-callbell')
def parafield_callbell_page():
    """Parafield Gardens callbell monitor page."""
    return redirect(url_for('callbell.callbell_page'))


@callbell_bp.route('/api/callbell/auth')
def api_callbell_auth():
    """Check if current user has admin access for callbell controls."""
    if current_user.is_authenticated:
        role = getattr(current_user, 'role', '')
        is_admin = role in ('admin', 'site_admin')
        return jsonify({
            'authenticated': True,
            'is_admin': is_admin,
            'role': role,
            'display_name': getattr(current_user, 'display_name', ''),
        })
    return jsonify({'authenticated': False, 'is_admin': False, 'role': '', 'display_name': ''})


@callbell_bp.route('/api/callbell/<site_id>/active')
def api_site_active_calls(site_id: str):
    """Get active calls for a specific site with computed colors."""
    manager = get_manager()
    calls = manager.get_site_active_calls(site_id)
    settings = get_color_settings(manager.db_path)
    debug = manager.get_debug_info(site_id)
    
    return jsonify({
        'site_id': site_id,
        'calls': calls,
        'settings': settings,
        'card_styles': CARD_STYLES,
        'debug': debug,
    })


@callbell_bp.route('/api/callbell/<site_id>/reset', methods=['POST'])
def api_site_reset_calls(site_id: str):
    """Clear all active calls for a specific site. Requires admin/site_admin."""
    if not current_user.is_authenticated or getattr(current_user, 'role', '') not in ('admin', 'site_admin'):
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
    
    manager = get_manager()
    success = manager.clear_site_calls(site_id)
    
    if success:
        logger.info(f"Cleared active calls for {site_id}")
        return jsonify({'status': 'ok', 'site_id': site_id})
    else:
        return jsonify({'status': 'error', 'message': f'Site {site_id} not found'}), 404


@callbell_bp.route('/api/callbell/poll')
def api_callbell_poll():
    """Single combined endpoint: returns all permitted sites' calls, auth, and settings.
    Frontend calls this ONE endpoint every 1 second."""
    manager = get_manager()

    # Determine which callbell sites exist
    callbell_site_ids = set()
    callbell_sites_meta = []
    for cfg in manager.site_configs:
        if 'callbell' in cfg and cfg.get('is_active', True):
            callbell_site_ids.add(cfg['id'])
            callbell_sites_meta.append({'id': cfg['id'], 'name': cfg['site_name']})

    # Filter by user permissions
    is_admin = False
    role = ''
    display_name = ''
    if current_user.is_authenticated:
        role = getattr(current_user, 'role', '')
        is_admin = role in ('admin', 'site_admin')
        display_name = getattr(current_user, 'display_name', '')
        locations = getattr(current_user, 'location', [])

        if role != 'admin' and 'All' not in locations:
            allowed_names = set(locations) if isinstance(locations, list) else {locations}
            callbell_sites_meta = [s for s in callbell_sites_meta if s['name'] in allowed_names]
            callbell_site_ids = {s['id'] for s in callbell_sites_meta}

    # Gather calls per permitted site
    sites_data = {}
    total = 0
    for site_id in callbell_site_ids:
        monitor = manager.get_monitor(site_id)
        calls = monitor.get_active_calls() if monitor else []
        sites_data[site_id] = calls
        total += len(calls)

    settings = get_color_settings(manager.db_path)

    return jsonify({
        'sites': callbell_sites_meta,
        'calls_by_site': sites_data,
        'total_calls': total,
        'settings': settings,
        'card_styles': CARD_STYLES,
        'is_admin': is_admin,
        'role': role,
        'display_name': display_name,
    })


@callbell_bp.route('/api/callbell/settings', methods=['GET'])
def api_get_settings():
    """Get current color threshold settings."""
    manager = get_manager()
    settings = get_color_settings(manager.db_path)
    return jsonify({
        'settings': settings,
        'card_styles': CARD_STYLES,
    })


@callbell_bp.route('/api/callbell/settings', methods=['POST'])
def api_save_settings():
    """Save color threshold settings. Requires admin/site_admin."""
    if not current_user.is_authenticated or getattr(current_user, 'role', '') not in ('admin', 'site_admin'):
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
    
    manager = get_manager()
    data = request.get_json()
    
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400
    
    green = int(data.get('green_minutes', 3))
    yellow = int(data.get('yellow_minutes', 5))
    red = int(data.get('red_minutes', 7))
    
    # Validate: green < yellow < red
    if not (0 < green < yellow < red):
        return jsonify({
            'status': 'error',
            'message': 'Thresholds must be: Green < Yellow < Red (all > 0)'
        }), 400
    
    save_color_settings(manager.db_path, green, yellow, red)
    logger.info(f"Color settings updated: green={green}m, yellow={yellow}m, red={red}m")
    
    return jsonify({
        'status': 'ok',
        'settings': {'green_minutes': green, 'yellow_minutes': yellow, 'red_minutes': red}
    })


# Legacy Ramsay routes for backward compatibility with existing apps
@callbell_bp.route('/api/callbell/active')
def api_callbell_active():
    """Legacy route - returns Ramsay active calls."""
    return api_site_active_calls('ramsay')

@callbell_bp.route('/api/callbell/all/active')
def api_all_active_calls():
    """Legacy route - redirects to combined poll endpoint."""
    return api_callbell_poll()

@callbell_bp.route('/api/callbell/reset', methods=['POST'])
def api_callbell_reset():
    """Legacy route - resets Ramsay active calls."""
    return api_site_reset_calls('ramsay')
