#!/usr/bin/env python3
"""
Admin API Endpoints - API Key Management and System Settings
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import sqlite3
from datetime import datetime

# Import API key manager
try:
    from api_key_manager_json import APIKeyManagerJSON
    API_KEY_MANAGER_AVAILABLE = True
except ImportError:
    API_KEY_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Admin API Blueprint
admin_api = Blueprint('admin_api', __name__)

def admin_required(f):
    """Decorator for functions requiring admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'message': 'Login required.'}), 401
        
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Admin privileges required.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@admin_api.route('/api/admin/api-keys', methods=['GET'])
@login_required
@admin_required
def get_api_keys():
    """Query all API key list"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_keys = manager.get_all_api_keys()
        
        # Display only part of API key for security
        for api_key in api_keys:
            if api_key['api_key']:
                api_key['api_key'] = api_key['api_key'][:20] + '...'
        
        return jsonify({
            'success': True,
            'api_keys': api_keys
        })
        
    except Exception as e:
        logger.error(f"Failed to query API key list: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to query API key list: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['GET'])
@login_required
@admin_required
def get_api_key(site_name):
    """Query API key for specific site"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_key = manager.get_api_key(site_name)
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': f'API key not found: {site_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'api_key': api_key
        })
        
    except Exception as e:
        logger.error(f"Failed to query API key ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to query API key: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys', methods=['POST'])
@login_required
@admin_required
def add_api_key():
    """Add new API key"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['siteName', 'apiUsername', 'apiKey', 'serverIp']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        manager = APIKeyManagerJSON()
        
        success = manager.add_api_key(
            site_name=data['siteName'],
            api_username=data['apiUsername'],
            api_key=data['apiKey'],
            server_ip=data['serverIp'],
            server_port=int(data.get('serverPort', 8080)),
            notes=data.get('notes', '')
        )
        
        if success:
            logger.info(f"API key added: {data['siteName']} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API key successfully added: {data["siteName"]}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add API key.'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to add API key: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to add API key: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['PUT'])
@login_required
@admin_required
def update_api_key(site_name):
    """Update API key"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        data = request.get_json()
        manager = APIKeyManagerJSON()
        
        # Fields to update
        update_data = {}
        if 'apiUsername' in data:
            update_data['api_username'] = data['apiUsername']
        if 'apiKey' in data:
            update_data['api_key'] = data['apiKey']
        if 'serverIp' in data:
            update_data['server_ip'] = data['serverIp']
        if 'serverPort' in data:
            update_data['server_port'] = int(data['serverPort'])
        if 'notes' in data:
            update_data['notes'] = data['notes']
        
        success = manager.update_api_key(site_name, **update_data)
        
        if success:
            logger.info(f"API key updated: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API key successfully updated: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update API key.'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to update API key ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to update API key: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['DELETE'])
@login_required
@admin_required
def delete_api_key(site_name):
    """Delete API key"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        manager = APIKeyManagerJSON()
        success = manager.deactivate_api_key(site_name)
        
        if success:
            logger.info(f"API key deleted: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API key successfully deleted: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete API key.'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to delete API key ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to delete API key: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_api_key(site_name):
    """Enable/Disable API key"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        manager = APIKeyManagerJSON()
        success = manager.update_api_key(site_name, is_active=is_active)
        
        if success:
            action = 'enabled' if is_active else 'disabled'
            logger.info(f"API key {action}: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API key successfully {action}: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to {action} API key.'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to toggle API key ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to toggle API key: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>/test', methods=['POST'])
@login_required
@admin_required
def test_api_connection(site_name):
    """Test API connection"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_data = manager.get_api_key(site_name)
        
        if not api_data:
            return jsonify({
                'success': False,
                'message': f'API key not found: {site_name}'
            }), 404
        
        # Test API connection
        import requests
        from config import get_api_headers
        
        headers = get_api_headers(site_name)
        base_url = f"http://{api_data['server_ip']}:{api_data['server_port']}"
        test_url = f"{base_url}/api/client"
        
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return jsonify({
                'success': True,
                'message': f'Connection successful (status code: {response.status_code})'
            })
        except requests.RequestException as e:
            return jsonify({
                'success': False,
                'message': f'Connection failed: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"API connection test failed ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/test-all', methods=['POST'])
@login_required
@admin_required
def test_all_api_connections():
    """Test all API connections"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API key manager is not available.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_keys = manager.get_all_api_keys()
        
        results = []
        success_count = 0
        
        for api_key in api_keys:
            if not api_key['is_active']:
                continue
                
            try:
                import requests
                from config import get_api_headers
                
                headers = get_api_headers(api_key['site_name'])
                base_url = f"http://{api_key['server_ip']}:{api_key['server_port']}"
                test_url = f"{base_url}/api/client"
                
                response = requests.get(test_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                results.append({
                    'site_name': api_key['site_name'],
                    'status': 'success',
                    'message': f'Connection successful (status code: {response.status_code})'
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    'site_name': api_key['site_name'],
                    'status': 'error',
                    'message': f'Connection failed: {str(e)}'
                })
        
        return jsonify({
            'success': True,
            'message': f'Test completed: {success_count}/{len(results)} successful',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"All API connection test failed: {e}")
        return jsonify({
            'success': False,
            'message': f'All connection test failed: {str(e)}'
        }), 500

@admin_api.route('/api/admin/system-status', methods=['GET'])
@login_required
@admin_required
def get_system_status():
    """Query system status"""
    try:
        # Check database connection status - changed to JSON-only system
        db_status = {'connected': True, 'type': 'JSON'}
        try:
            # Consider always connected since it's a JSON file-based system
            data_dir = 'data'
            if os.path.exists(data_dir):
                db_status['connected'] = True
                db_status['type'] = 'JSON Files'
            else:
                db_status['connected'] = False
                db_status['error'] = 'Data directory not found'
        except Exception as e:
            db_status['error'] = str(e)
        
        # Check encryption key status
        encryption_status = {'available': False}
        try:
            if API_KEY_MANAGER_AVAILABLE:
                manager = APIKeyManagerJSON()
                # Check if encryption key file exists
                encryption_status['available'] = os.path.exists('api_key_encryption.key')
            else:
                encryption_status['error'] = 'API key manager is not available.'
        except Exception as e:
            encryption_status['error'] = str(e)
        
        return jsonify({
            'success': True,
            'db_status': db_status,
            'encryption_status': encryption_status,
            'api_key_manager_available': API_KEY_MANAGER_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"Failed to query system status: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to query system status: {str(e)}'
        }), 500

@admin_api.route('/api/admin/system-logs', methods=['GET'])
@login_required
@admin_required
def get_system_logs():
    """Query system logs"""
    try:
        log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'message': 'Log file not found.'
            }), 404
        
        # Read only last 100 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines)
        })
        
    except Exception as e:
        logger.error(f"Failed to query system logs: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to query system logs: {str(e)}'
        }), 500

def get_db_connection():
    """Database connection"""
    conn = sqlite3.connect('progress_report.db', timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except:
        pass
    return conn

@admin_api.route('/api/admin/data-source-mode', methods=['GET'])
@login_required
@admin_required
def get_data_source_mode():
    """Query data source mode (DB or API)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query from system_settings
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'USE_DB_DIRECT_ACCESS'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        # Use value from DB if exists, otherwise check environment variable, default to 'api' if neither exists
        if result and result[0]:
            mode = result[0].lower()
        else:
            mode = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower()
        
        # Convert 'true'/'false' strings to 'db'/'api'
        if mode == 'true' or mode == 'db':
            mode = 'db'
        else:
            mode = 'api'
        
        return jsonify({
            'success': True,
            'mode': mode
        })
        
    except Exception as e:
        logger.error(f"Failed to query data source mode: {e}")
        # Return default value on error
        mode = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower()
        return jsonify({
            'success': True,
            'mode': 'db' if mode == 'true' or mode == 'db' else 'api'
        })

@admin_api.route('/api/admin/data-source-mode', methods=['POST'])
@login_required
@admin_required
def set_data_source_mode():
    """Set data source mode (DB or API)"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'api')  # 'db' or 'api'
        
        if mode not in ['db', 'api']:
            return jsonify({
                'success': False,
                'error': 'Invalid mode. Must be "db" or "api"'
            }), 400
        
        # Convert 'db'/'api' to 'true'/'false' for storage
        value = 'true' if mode == 'db' else 'false'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save to system_settings
        cursor.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES ('USE_DB_DIRECT_ACCESS', ?, ?)
        """, (value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Also update environment variable (applies only to current process)
        os.environ['USE_DB_DIRECT_ACCESS'] = value
        
        logger.info(f"Data source mode changed: {mode} (by {current_user.username})")
        
        return jsonify({
            'success': True,
            'mode': mode,
            'message': f'Data source mode changed to "{mode}" mode. Server restart is recommended to apply changes.'
        })
        
    except Exception as e:
        logger.error(f"Failed to set data source mode: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to set data source mode: {str(e)}'
        }), 500

@admin_api.route('/api/admin/restart-server', methods=['POST'])
@login_required
@admin_required
def restart_server():
    """Restart server (execute batch file)"""
    import subprocess
    import os
    import sys
    from pathlib import Path
    
    try:
        logger.info(f"Server restart requested: {current_user.username}")
        
        # Find project root directory
        project_root = Path(__file__).parent.absolute()
        restart_script = project_root / 'restart_server_simple.bat'
        
        if not restart_script.exists():
            return jsonify({
                'success': False,
                'error': 'Restart script not found.'
            }), 404
        
        # Execute batch file in background
        # Use CREATE_NEW_CONSOLE flag on Windows
        if sys.platform == 'win32':
            subprocess.Popen(
                [str(restart_script)],
                cwd=str(project_root),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=True
            )
        else:
            # For Linux/Mac
            subprocess.Popen(
                ['bash', str(restart_script)],
                cwd=str(project_root)
            )
        
        logger.info("Server restart script executed")
        
        return jsonify({
            'success': True,
            'message': 'Server restart has started. It will automatically reconnect shortly.'
        })
        
    except Exception as e:
        logger.error(f"Server restart failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Server restart failed: {str(e)}'
        }), 500
