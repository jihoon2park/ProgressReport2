"""
Multi-Site Callbell Monitor Integration
This module replaces the old callbell_monitor.py with a modular multi-site system.

To use in your Flask app:
    from callbell_monitor_multi import init_callbell_system, callbell_bp
    
    # Initialize the system
    init_callbell_system(app)
    
    # Register the blueprint
    app.register_blueprint(callbell_bp)

Available routes:
    - /callbell/<site_id> - Monitor page for specific site
    - /api/callbell/<site_id>/active - Get active calls for site
    - /api/callbell/<site_id>/reset - Reset calls for site
    - /api/callbell/all/active - Get all active calls from all sites
    
    Legacy routes (for backward compatibility):
    - /ramsay-callbell - Ramsay monitor page
    - /api/callbell/active - Ramsay active calls
    - /api/callbell/reset - Ramsay reset
"""
import os
import json
import subprocess
import logging
from flask import Flask

from callbell import init_manager, callbell_bp

logger = logging.getLogger(__name__)

# Paths
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CALLBELL_DB = os.path.join(_BASE_DIR, 'edenfield_calls.db')
_SITE_CONFIG_PATH = os.path.join(_BASE_DIR, 'data', 'api_keys', 'site_config.json')


def _kill_port_once(port: int):
    """Kill any process holding the UDP port. Runs ONCE on app startup."""
    my_pid = os.getpid()
    try:
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'UDP'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.splitlines():
            if f':{port}' in line and 'UDP' in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid != my_pid and pid != 0:
                    logger.info(f"Startup: killing stale PID {pid} on UDP port {port}")
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], timeout=5)
    except Exception as e:
        logger.warning(f"Startup port cleanup warning: {e}")


def _get_ramsay_port() -> int:
    """Read the Ramsay listen port from site config."""
    try:
        with open(_SITE_CONFIG_PATH) as f:
            config = json.load(f)
        for site in config.get('sites', []):
            if site.get('id') == 'ramsay':
                return site.get('callbell', {}).get('listen_port', 10514)
    except Exception:
        pass
    return 10514


def init_callbell_system(app: Flask = None, sites_to_monitor: list = None):
    """
    Initialize the multi-site callbell monitoring system.
    
    Args:
        app: Flask application instance (optional, for logging context)
        sites_to_monitor: List of site IDs to monitor. If None, defaults to ['parafield_gardens'].
                         To enable specific monitors, pass a list:
                         Example: ['parafield_gardens'] - Only Parafield
                         Example: ['ramsay', 'parafield_gardens'] - Both sites
                         Example: [] - No monitors (disabled)
    
    Returns:
        CallbellManager instance
    """
    if app:
        logger.info("Initializing multi-site callbell monitoring system...")
    
    # Initialize the manager
    manager = init_manager(_CALLBELL_DB, _SITE_CONFIG_PATH)
    
    # Only remove calls older than 4 hours (safe to call from any process)
    manager.cleanup_stale_calls(max_age_hours=4.0)
    
    # One-time: kill any stale process holding the Ramsay UDP port
    if sites_to_monitor and 'ramsay' in sites_to_monitor:
        _kill_port_once(_get_ramsay_port())
    
    # Default: Only Parafield Gardens enabled (Ramsay disabled by default)
    if sites_to_monitor is None:
        sites_to_monitor = ['parafield_gardens']
        logger.info("📋 Using default monitors: Parafield Gardens only (Ramsay disabled)")
    
    # Allow empty list to disable all monitors
    if not sites_to_monitor:
        logger.warning("⚠️ No callbell monitors enabled (empty sites_to_monitor list)")
        return manager
    
    # Register monitors for each site
    for site_id in sites_to_monitor:
        try:
            success = manager.register_monitor(site_id, monitor_type='auto')
            if success:
                logger.info(f"✅ Callbell monitor registered for: {site_id}")
            else:
                logger.warning(f"⚠️ Could not register monitor for: {site_id}")
        except Exception as e:
            logger.error(f"❌ Error registering monitor for {site_id}: {e}")
    
    logger.info(f"Callbell system initialized with {len(manager.monitors)} active monitors")
    return manager


def start_callbell_monitor():
    """
    Legacy function for backward compatibility.
    Initializes the multi-site system with default settings.
    """
    return init_callbell_system()


# Export the blueprint for Flask app registration
__all__ = ['init_callbell_system', 'start_callbell_monitor', 'callbell_bp']
