from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    session, 
    jsonify, 
    send_from_directory,
    make_response
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import requests
from functools import wraps
import logging
import logging.handlers
import json
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
import time
import threading
import schedule
from dotenv import load_dotenv
import uuid
from dataclasses import asdict

# Load environment variables from .env file
load_dotenv()

# Helper function for Australian Eastern Standard Time (AEST, UTC+10)
def get_australian_time():
    """Return Australian Eastern Standard Time"""
    aest = timezone(timedelta(hours=10))
    return datetime.now(aest)

# Import internal modules
from api_client import APIClient
from api_carearea import APICareArea
from api_eventtype import APIEventType
from config import SITE_SERVERS, API_HEADERS, get_available_sites
from config_users import authenticate_user, get_user
from config_env import get_flask_config, print_current_config, get_cache_policy
from models import load_user, User
from usage_logger import usage_logger
from admin_api import admin_api
from alarm_manager import get_alarm_manager
from alarm_service import get_alarm_services
from fcm_service import get_fcm_service
from fcm_token_manager import get_fcm_token_manager

# SITE_SERVERS safety check and fallback handling
def get_safe_site_servers():
    """Return safe site server information (with fallback)"""
    try:
        # Get SITE_SERVERS from config
        if SITE_SERVERS and len(SITE_SERVERS) > 0:
            logger.info(f"SITE_SERVERS loaded successfully: {list(SITE_SERVERS.keys())}")
            return SITE_SERVERS
        else:
            logger.warning("SITE_SERVERS is empty, using fallback")
            return get_fallback_site_servers()
    except Exception as e:
        logger.error(f"Failed to load SITE_SERVERS: {e}, using fallback")
        return get_fallback_site_servers()

# IIS environment detection and configuration
def is_iis_environment():
    """Check if running in IIS environment"""
    return 'IIS' in os.environ.get('SERVER_SOFTWARE', '') or 'IIS' in os.environ.get('HTTP_HOST', '')

def get_application_path():
    """Return application path (considering IIS environment)"""
    if is_iis_environment():
        # Use current working directory in IIS environment
        return os.getcwd()
    else:
        # Use script directory in development environment
        return os.path.dirname(os.path.abspath(__file__))

# Cache safe site server information as global variable
_cached_site_servers = None

def get_cached_site_servers():
    """Return cached safe site server information"""
    global _cached_site_servers
    if _cached_site_servers is None:
        _cached_site_servers = get_safe_site_servers()
    return _cached_site_servers

def get_fallback_site_servers():
    """Fallback site server information"""
    return {
        'Parafield Gardens': '192.168.1.11:8080',
        'Nerrilda': '192.168.21.12:8080',
        'Ramsay': '192.168.31.12:8080',
        'West Park': '192.168.41.12:8080',
        'Yankalilla': '192.168.51.12:8080'
    }

# Load environment-specific configuration
flask_config = get_flask_config()

# Configure logging
log_level = getattr(logging, flask_config['LOG_LEVEL'].upper())


# Create log directory
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure file handler and console handler
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # Console output (development environment only)
        logging.StreamHandler(),
        # File output (max 50MB, 10 file rotation) - for production server
        logging.handlers.RotatingFileHandler(
            f'{log_dir}/app.log',
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

# Additional logging configuration for production server
def setup_production_logging():
    """Configure logging for production server"""
    try:
        # Error-only log file
        error_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/error.log',
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Access log file
        access_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/access.log',
            maxBytes=30*1024*1024,  # 30MB
            backupCount=5,
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        
        # Add handlers to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(error_handler)
        root_logger.addHandler(access_handler)
        
        logger.info("Production logging configured")
        
    except Exception as e:
        logger.error(f"Error while configuring logging: {str(e)}")

# Apply production logging configuration
setup_production_logging()

# Print current configuration
print_current_config()

# Initialize Flask app
app = Flask(__name__, static_url_path='/static')

# Apply environment-specific configuration
app.secret_key = flask_config['SECRET_KEY']
app.config['DEBUG'] = flask_config['DEBUG']

# Session timeout configuration (applied equally to all users)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=10)

def set_session_permanent(user_role):
    """Apply same session configuration to all users"""
    try:
        # Apply equally to all users
        session.permanent = True
        logger.info(f"User session configured: {user_role}")
    except Exception as e:
        logger.error(f"Error while configuring session: {e}")
        # Set to default value on error
        session.permanent = False

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def user_loader(user_id):
    """Flask-Login user_loader callback"""
    return load_user(user_id)

@login_manager.unauthorized_handler
def unauthorized_callback():
    logger.warning(f"Unauthenticated access attempt: {request.method} {request.path}")
    logger.warning(f"Request IP: {request.remote_addr}")
    logger.warning(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    if request.path.startswith('/api/'):
        logger.error(f"API authentication failed: {request.path}")
        return jsonify({'success': False, 'message': 'Authentication required', 'is_expired': True}), 401
    
    logger.info(f"Web page authentication failed, redirecting to home: {request.path}")
    return redirect(url_for('home'))

# Configuration validation log
if flask_config['ENVIRONMENT'] == 'production' and flask_config['DEBUG']:
    logger.warning("⚠️  DEBUG mode is enabled in production!")

if flask_config['SECRET_KEY'] == 'fallback-secret-key':
    logger.warning("⚠️  Using fallback SECRET_KEY. This is insecure!")

# Check and create data directory
if not os.path.exists('data'):
    os.makedirs('data')
    logger.info("`data` directory created")

# Note: Policy Scheduler and Unified Data Sync Manager are for JSON-based systems
# Not used in CIMS (DB-based) system.
# - Policy Scheduler → Replaced by CIMS Policy Engine
# - Unified Data Sync → Replaced by CIMS incremental sync + client caching

# ==============================
# Database Schema Migration (Auto-execution)
# Automatically resolve database schema differences between Production and Development environments
# ==============================
try:
    from migrate_cims_schema import run_migration
    db_path = flask_config.get('DATABASE_PATH', 'progress_report.db')
    migration_ok = run_migration(db_path)
    if migration_ok:
        logger.info("✅ Database schema migration completed")
    else:
        logger.warning("⚠️ Database schema migration did not complete successfully (app will continue)")
except Exception as e:
    logger.warning(f"⚠️ Database schema migration failed: {e}")
    # App continues to run even if migration fails

# ==============================
# Authentication-related functions (using Flask-Login)
# ==============================

def _is_authenticated():
    """Check user authentication status (using Flask-Login)"""
    return current_user.is_authenticated

def require_authentication(wrapped_function):
    """Decorator for routes requiring authentication (using Flask-Login)"""
    @wraps(wrapped_function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('home'))
        return wrapped_function(*args, **kwargs)
    return decorated_function

# ==============================
# Data Processing Functions
# ==============================

def process_client_information(client_info):
    """Process client information and extract only necessary data"""
    if not client_info:
        logger.warning("No client info to process.")
        return []
        
    processed_clients = []
    try:
        for client in client_info:
            processed_client = {
                'PersonId': client.get('MainClientServiceId'),  # Use MainClientServiceId as PersonId
                'ClientName': f"{client.get('Title', '')} {client.get('FirstName', '')} {client.get('LastName', '')}".strip(),
                'PreferredName': client.get('PreferredName', ''),
                'Gender': client.get('Gender', ''),
                'BirthDate': client.get('BirthDate'),
                'WingName': client.get('WingName'),
                'RoomName': client.get('RoomName'),
                'MainClientServiceId': client.get('MainClientServiceId'),  # Use as ClientServiceId
                'OriginalPersonId': client.get('PersonId'),  # Also preserve original PersonId
                'ClientRecordId': client.get('Id')  # Client record ID (use as ClientId)
            }
            processed_clients.append(processed_client)

        # Save processed data to file
        save_json_file('data/Client_list.json', processed_clients)
        
        return processed_clients
    except Exception as e:
        logger.error(f"Error processing client info: {str(e)}")
        return []

# fetch_client_information function is managed in api_client.py
# This function has been removed. Use api_client.fetch_client_information instead.

def fetch_care_area_information(site):
    """Fetch and process Care Area information (disabled - using DB)"""
    logger.info(f"Skipping Care Area fetch - retrieved from DB (site: {site})")
    return True, None  # No API call needed as data is queried from DB

def fetch_event_type_information(site):
    """Fetch and process Event Type information (enabled for ROD dashboard)"""
    try:
        from api_eventtype import APIEventType
        logger.info(f"Starting Event Type fetch - site: {site}")
        
        api_eventtype = APIEventType(site)
        event_type_data = api_eventtype.get_event_type_information()
        
        if event_type_data:
            # Event Type data is returned directly as a list
            if isinstance(event_type_data, list):
                logger.info(f"Event Type fetch succeeded - site: {site}, {len(event_type_data)} items")
                return True, event_type_data
            elif isinstance(event_type_data, dict) and 'data' in event_type_data:
                logger.info(f"Event Type fetch succeeded - site: {site}, {len(event_type_data['data'])} items")
                return True, event_type_data['data']
            else:
                logger.warning(f"Unexpected Event Type data structure - site: {site}, type: {type(event_type_data)}")
                return False, None
        else:
            logger.warning(f"Event Type fetch failed - site: {site}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error fetching Event Type - site: {site}, error: {e}")
        return False, None

def save_json_file(filepath, data):
    """Save JSON data to file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"File saved successfully: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file: {str(e)}")
        return False

def save_client_data(username, site, client_info):
    """Save client data to JSON file (disabled - using DB)"""
    logger.info(f"Skipping client data save - stored in DB (site: {site})")
    return None  # No need to create JSON file as data is stored in DB

def create_progress_note_json(form_data):
    """Convert user input data to Progress Note JSON format (only include fields with values)"""
    try:
        logger.info(f"Starting Progress Note JSON generation - input data: {form_data}")
        
        # Required fields
        progress_note = {}
        
        # Handle ClientId and ClientServiceId (required)
        if form_data.get('clientId'):
            try:
                selected_client_id = int(form_data.get('clientId'))
                
                # Find selected client information from Client_list.json
                import json
                try:
                    with open('data/Client_list.json', 'r', encoding='utf-8') as f:
                        clients = json.load(f)
                    
                    selected_client = None
                    for client in clients:
                        if client.get('PersonId') == selected_client_id:
                            selected_client = client
                            break
                    
                    if selected_client:
                        # Successful combination: ClientId = client record ID, ClientServiceId = MainClientServiceId
                        progress_note["ClientId"] = selected_client.get('ClientRecordId', selected_client_id)  # Client record ID
                        progress_note["ClientServiceId"] = selected_client.get('MainClientServiceId', selected_client_id)  # MainClientServiceId
                        
                        logger.info(f"ClientId set: {progress_note['ClientId']} (client record ID)")
                        logger.info(f"ClientServiceId set: {progress_note['ClientServiceId']} (MainClientServiceId)")
                    else:
                        logger.error(f"Selected client not found: {selected_client_id}")
                        return None
                        
                except Exception as e:
                    logger.error(f"Failed to read Client_list.json: {e}")
                    # Set default - use MainClientServiceId as client record ID is unknown
                    progress_note["ClientId"] = selected_client_id  # Use MainClientServiceId as ClientId (fallback)
                    progress_note["ClientServiceId"] = selected_client_id  # MainClientServiceId
                    logger.warning(
                        "Using fallback - unable to find exact client record ID, using MainClientServiceId"
                    )
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert ClientId: {form_data.get('clientId')}, error: {e}")
                return None
        else:
            logger.error("ClientId is missing - required field")
            return None
            
        # EventDate (required)
        if form_data.get('eventDate'):
            progress_note["EventDate"] = form_data.get('eventDate')
            logger.info(f"EventDate set: {progress_note['EventDate']}")
        else:
            # Use current time if EventDate is missing
            progress_note["EventDate"] = get_australian_time().isoformat()
            logger.info(f"EventDate default set: {progress_note['EventDate']}")
            
        # ProgressNoteEventType (required)
        if form_data.get('eventType'):
            try:
                event_type_id = int(form_data.get('eventType'))
                progress_note["ProgressNoteEventType"] = {
                    "Id": event_type_id
                }
                logger.info(f"ProgressNoteEventType set: {event_type_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert EventType: {form_data.get('eventType')}, error: {e}")
                return None
        else:
            logger.error("EventType is missing - required field")
            return None
            
        # NotesPlainText (required)
        notes_text = form_data.get('notes', '').strip()
        if notes_text:
            progress_note["NotesPlainText"] = notes_text
            logger.info(f"NotesPlainText set: {len(notes_text)}")
        else:
            # Set to empty string even for empty notes
            progress_note["NotesPlainText"] = ""
            logger.info("NotesPlainText set to empty string")
            
        # Optional fields (add only if value exists)
        
        # CreatedByUser (ExternalUserDto format)
        username = current_user.username
        first_name = current_user.first_name
        last_name = current_user.last_name
        position = current_user.position
        
        # Refetch from user DB if info is missing in session - need to review this later...... Jay 2025-06-05
        if username and (not first_name or not last_name or not position):
            logger.warning(f"Missing user info in session - refetching from user DB: {username}")
            user_data = get_user(username)
            if user_data:
                first_name = user_data.get('first_name', first_name)
                last_name = user_data.get('last_name', last_name)
                position = user_data.get('position', position)
                logger.info(f"Recovered user info from DB: {first_name} {last_name} - {position}")
        
        if username:
            progress_note["CreatedByUser"] = {
                "FirstName": first_name,
                "LastName": last_name,
                "UserName": username,
                "Position": position
            }
            logger.info(f"CreatedByUser set: {first_name} {last_name} ({username}) - {position}")
            
            # For debugging - check each field state
            logger.debug(f"CreatedByUser field state: FirstName='{first_name}', LastName='{last_name}', UserName='{username}', Position='{position}'")
            
        # CreatedDate (optional)
        if form_data.get('createDate'):
            progress_note["CreatedDate"] = form_data.get('createDate')
            logger.info(f"CreatedDate set: {progress_note['CreatedDate']}")
            
        # CareAreas (only if selected)
        if form_data.get('careArea'):
            try:
                care_area_id = int(form_data.get('careArea'))
                progress_note["CareAreas"] = [{
                    "Id": care_area_id
                }]
                logger.info(f"CareAreas set: {care_area_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to convert CareArea: {form_data.get('careArea')}, error: {e}")
                
        # ProgressNoteRiskRating (only if selected)
        if form_data.get('riskRating'):
            risk_rating_value = form_data.get('riskRating')
            
            # Map string ID to number
            risk_rating_mapping = {
                'rr1': 1,  # Extreme
                'rr2': 2,  # High
                'rr3': 3,  # Moderate
                'rr4': 4   # Low
            }
            
            risk_rating_id = None
            if risk_rating_value in risk_rating_mapping:
                risk_rating_id = risk_rating_mapping[risk_rating_value]
            elif risk_rating_value.isdigit():
                risk_rating_id = int(risk_rating_value)
                
            if risk_rating_id:
                progress_note["ProgressNoteRiskRating"] = {
                    "Id": risk_rating_id
                }
                logger.info(f"ProgressNoteRiskRating set: {risk_rating_id}")
                
        # Boolean fields (add only if true)
        if form_data.get('lateEntry'):
            progress_note["IsLateEntry"] = True
            logger.info("IsLateEntry set: True")
            
        if form_data.get('flagOnNoticeboard'):
            progress_note["IsNoticeFlag"] = True
            logger.info("IsNoticeFlag set: True")
            
        if form_data.get('archived'):
            progress_note["IsArchived"] = True
            logger.info("IsArchived set: True")
            
        # Add ClientServiceId only if needed by API
        # progress_note["ClientServiceId"] = 26  # Temporarily removed
        
        logger.info(f"Progress Note JSON generated: {progress_note}")
        return progress_note
        
    except Exception as e:
        logger.error(f"Exception during Progress Note JSON generation: {str(e)}", exc_info=True)
        return None

def save_prepare_send_json(progress_note_data):
    """Save data to prepare_send.json file (create new file each time, backup existing file)"""
    try:
        filepath = 'data/prepare_send.json'
        
        # Create backup if existing file exists
        if os.path.exists(filepath):
            # Circular backup system (max 1000 files)
            MAX_BACKUP_COUNT = 1000
            
            # Check existing backup files
            existing_backups = []
            for i in range(1, MAX_BACKUP_COUNT + 1):
                backup_filepath = f'data/prepare_send_backup{i}.json'
                if os.path.exists(backup_filepath):
                    existing_backups.append(i)
            
            # Determine next backup number
            if len(existing_backups) < MAX_BACKUP_COUNT:
                # Use next number if max count not reached yet
                backup_number = len(existing_backups) + 1
                logger.info(f"Creating new backup file: backup{backup_number}.json")
            else:
                # Find oldest file and overwrite if max count reached
                oldest_backup = 1
                oldest_time = None
                
                for i in range(1, MAX_BACKUP_COUNT + 1):
                    backup_filepath = f'data/prepare_send_backup{i}.json'
                    if os.path.exists(backup_filepath):
                        file_time = os.path.getmtime(backup_filepath)
                        if oldest_time is None or file_time < oldest_time:
                            oldest_time = file_time
                            oldest_backup = i
                
                backup_number = oldest_backup
                logger.info(f"Max backup count reached - overwriting oldest backup: backup{backup_number}.json")
            
            backup_filepath = f'data/prepare_send_backup{backup_number}.json'
            
            # Move existing file to backup (overwrite)
            try:
                import shutil
                shutil.move(filepath, backup_filepath)
                logger.info(f"Moved existing file to backup: {filepath} -> {backup_filepath}")
                logger.info(
                    f"Current backup count: {min(len(existing_backups) + 1, MAX_BACKUP_COUNT)}/{MAX_BACKUP_COUNT}"
                )
            except Exception as e:
                logger.error(f"Failed to create backup: {str(e)}")
                # Continue saving new file even if backup fails
        
        # Save as new file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_note_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Progress Note data saved to new file: {filepath}")
        logger.info(f"Saved data: {progress_note_data}")
        return True
    except Exception as e:
        logger.error(f"Error saving prepare_send.json: {str(e)}")
        return False

# ==============================
# API Server Status Check Functions
# ==============================

def check_api_server_health(server_ip):
    """Check API server status"""
    try:
        url = f"http://{server_ip}/api/system/canconnect"
        response = requests.get(url, timeout=5)
        return response.status_code == 200 and response.text.strip() == 'true'
    except Exception as e:
        logger.error(f"API server health check failed - {server_ip}: {str(e)}")
        return False

@app.route('/api/server-status')
def get_server_status():
    """Return API server status for all sites"""
    try:
        # Use safe site server information
        safe_site_servers = get_safe_site_servers()
        status = {}
        
        for site, server_ip in safe_site_servers.items():
            try:
                status[site] = check_api_server_health(server_ip)
                logger.debug(f"Server health check completed - {site}: {status[site]}")
            except Exception as e:
                logger.error(f"Server health check failed - {site}: {e}")
                status[site] = False
        
        logger.info(f"Server status API response: {status}")
        return jsonify(status)
    except Exception as e:
        logger.error(f"Server status API error: {e}")
        # Return empty status on error
        return jsonify({})

@app.route('/api/debug/site-servers')
def debug_site_servers_api():
    """Site server information debugging API (for IIS issue diagnosis)"""
    try:
        debug_info = {
            'timestamp': get_australian_time().isoformat(),
            'environment': 'IIS' if is_iis_environment() else 'Development',
            'config_loaded': False,
            'site_servers': {},
            'fallback_used': False,
            'errors': [],
            'iis_info': {
                'server_software': os.environ.get('SERVER_SOFTWARE', 'Not set'),
                'http_host': os.environ.get('HTTP_HOST', 'Not set'),
                'application_path': get_application_path(),
                'current_directory': os.getcwd(),
                'python_path': sys.executable
            }
        }

        
        logger.info(f"debug_info: {debug_info}")
        # Check config module status
        try:
            import config
            debug_info['config_loaded'] = True
            debug_info['use_db_api_keys'] = getattr(config, 'USE_DB_API_KEYS', 'Not defined')
            debug_info['site_servers'] = getattr(config, 'SITE_SERVERS', {})
        except Exception as e:
            debug_info['errors'].append(f"Failed to load config: {str(e)}")
        
        # Check safe site server information
        try:
            safe_servers = get_safe_site_servers()
            debug_info['safe_site_servers'] = safe_servers
            debug_info['fallback_used'] = safe_servers == get_fallback_site_servers()
        except Exception as e:
            debug_info['errors'].append(f"Failed to load safe site servers: {str(e)}")
            debug_info['safe_site_servers'] = get_fallback_site_servers()
            debug_info['fallback_used'] = True
        
        # Check API key manager status
        try:
            from api_key_manager import get_api_key_manager
            manager = get_api_key_manager()
            api_keys = manager.get_all_api_keys()
            debug_info['api_keys_count'] = len(api_keys)
            debug_info['api_keys'] = [{'site': key['site_name'], 'server': f"{key['server_ip']}:{key['server_port']}"} for key in api_keys]
        except Exception as e:
            debug_info['errors'].append(f"Failed to check API key manager: {str(e)}")
            debug_info['api_keys_count'] = 0
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({
            'error': f"Debugging API error: {str(e)}",
            'timestamp': get_australian_time().isoformat()
        }), 500

@app.route('/api/logs')
def get_logs():
    """API to query log file list and content"""
    try:
        log_files = []
        
        # 1. General log files (logs directory) - exclude meaningless log files
        log_dir = "logs"
        excluded_files = ['test.log', 'app.log', 'usage_system.log']
        
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith('.log') and filename not in excluded_files:
                    filepath = os.path.join(log_dir, filename)
                    stat = os.stat(filepath)
                    log_files.append({
                        'name': filename,
                        'type': 'system',
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'path': filepath
                    })
        
        # 2. Usage log files (UsageLog directory)
        usage_log_dir = "UsageLog"
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        stat = os.stat(filepath)
                        # Display as relative path (unify Windows path separators to slashes)
                        rel_path = os.path.relpath(filepath, usage_log_dir).replace('\\', '/')
                        log_files.append({
                            'name': f"UsageLog/{rel_path}",
                            'type': 'usage',
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'path': filepath
                        })
        
        return jsonify({
            'log_files': sorted(log_files, key=lambda x: x['modified'], reverse=True),
            'timestamp': get_australian_time().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f"Failed to query logs: {str(e)}"}), 500

@app.route('/api/logs/<path:filename>')
def get_log_content(filename):
    """Query specific log file content"""
    try:
        # Security: prevent path manipulation in filename
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'error': 'Invalid filename'}), 400
        
        # Check if UsageLog file
        if filename.startswith('UsageLog/'):
            # Convert Windows path separators to actual path
            filepath = filename.replace('/', os.sep)
        else:
            filepath = os.path.join("logs", filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Check if JSON file
        if filename.endswith('.json'):
            # Parse and display JSON file nicely
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Format JSON nicely
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            content_lines = formatted_json.split('\n')
            
            # Read last N lines
            lines = request.args.get('lines', 100, type=int)
            lines = min(lines, 1000)  # Limit to max 1000 lines
            
            if len(content_lines) > lines:
                content_lines = content_lines[-lines:]
            
            return jsonify({
                'filename': filename,
                'type': 'json',
                'lines': len(content_lines),
                'total_lines': len(formatted_json.split('\n')),
                'content': content_lines,
                'timestamp': get_australian_time().isoformat()
            })
        else:
            # General log file case
            lines = request.args.get('lines', 100, type=int)
            lines = min(lines, 1000)  # Limit to max 1000 lines
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                content_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return jsonify({
                'filename': filename,
                'type': 'text',
                'lines': len(content_lines),
                'total_lines': len(all_lines),
                'content': [line.rstrip() for line in content_lines],
                'timestamp': get_australian_time().isoformat()
            })
    except Exception as e:
        return jsonify({'error': f"Failed to query log content: {str(e)}"}), 500

@app.route('/logs')
def logs_page():
    """Log viewer page"""
    return render_template('LogViewer.html')

@app.route('/api/health')
def health_check():
    """Server status check API (for mobile app)"""
    try:
        # Test database connection
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        # Check FCM service status
        fcm_service = get_fcm_service()
        fcm_status = fcm_service is not None
        
        # Task Manager status check - disabled due to change to JSON-only system
        # task_manager = get_task_manager()
        task_manager_status = False  # Disabled
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': get_australian_time().isoformat(),
            'services': {
                'database': True,
                'fcm': fcm_status,
                'task_manager': task_manager_status,
                'user_count': user_count
            },
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'timestamp': get_australian_time().isoformat(),
            'error': str(e)
        }), 500

# ==============================
# Route Definitions
# ==============================

@app.route('/')
def home():
    """Home page"""
    if current_user.is_authenticated:
        logger.info(f"Home page access - User: {current_user.username}, Authenticated: {current_user.is_authenticated}")
        
        # Check allowed_sites and site information from session
        allowed_sites = session.get('allowed_sites', [])
        site = session.get('site', 'Parafield Gardens')
        
        logger.info(f"Home page session info - allowed_sites: {allowed_sites} (type: {type(allowed_sites)}), site: {site}")
        logger.info(f"Home page full session content: {dict(session)}")
        
        # Set default if allowed_sites is empty
        if not allowed_sites:
            safe_site_servers = get_safe_site_servers()
            allowed_sites = list(safe_site_servers.keys())
            session['allowed_sites'] = allowed_sites
            logger.warning(f"Home page: allowed_sites is empty, setting default site list: {allowed_sites}")
        
        # ROD users redirect to dedicated dashboard (case-insensitive)
        username_upper = current_user.username.upper()
        logger.info(f"Username check: {current_user.username} -> {username_upper}")
        if username_upper == 'ROD':
            logger.info(f"ROD user detected - redirecting to rod_dashboard")
            return redirect(url_for('rod_dashboard'))
        elif username_upper == 'YKROD':
            logger.info(f"YKROD user detected - redirecting to Yankalilla ROD dashboard")
            return redirect(url_for('rod_dashboard', site='Yankalilla'))
        elif username_upper == 'PGROD':
            logger.info(f"PGROD user detected - multi-site access, default redirect to Parafield Gardens")
            session['site'] = 'Parafield Gardens'
            session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
            return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
        elif username_upper == 'WPROD':
            logger.info(f"WPROD user detected - redirecting to West Park ROD dashboard")
            return redirect(url_for('rod_dashboard', site='West Park'))
        elif username_upper == 'RSROD':
            logger.info(f"RSROD user detected - multi-site access, default redirect to Ramsay")
            session['site'] = 'Ramsay'
            session['allowed_sites'] = ['Ramsay', 'Nerrilda']
            return redirect(url_for('rod_dashboard', site='Ramsay'))
        elif username_upper == 'NROD':
            logger.info(f"NROD user detected - redirecting to Nerrilda ROD dashboard")
            return redirect(url_for('rod_dashboard', site='Nerrilda'))
        
        # PG_admin users redirect to callbell
        if current_user.role == 'site_admin':
            logger.info(f"PG_admin user detected - redirecting to callbell")
            return redirect(url_for('callbell.callbell_page'))
        
        # Regular users redirect to progress_notes, checking session info
        logger.info(f"Regular user - redirecting to progress_notes (site={site}, allowed_sites={allowed_sites})")
        return redirect(url_for('progress_notes', site=site))
    
    # Fallback login page
    safe_site_servers = get_safe_site_servers()
    return render_template('LoginPage.html', sites=safe_site_servers.keys())

@app.route('/login', methods=['GET'])
def login_page():
    """Login page"""
    try:
        # Get safe site server information
        safe_site_servers = get_safe_site_servers()
        sites = list(safe_site_servers.keys())
        logger.info(f"Login page rendering - Site list: {sites}")
        return render_template('LoginPage.html', sites=sites)
    except Exception as e:
        logger.error(f"Login page rendering failed: {e}")
        # Final fallback
        fallback_sites = list(get_fallback_site_servers().keys())
        return render_template('LoginPage.html', sites=fallback_sites)

@app.route('/login', methods=['POST'])
def login():
    """Login processing"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        site = request.form.get('site')
        
        logger.info(f"Login attempt - User: {username}, Site: {site}")
        
        # Log access
        user_info = {
            "username": username,
            "display_name": username,
            "role": "unknown",
            "position": "unknown"
        }
        usage_logger.log_access(user_info)

        # Validate input values
        if not all([username, password, site]):
            flash('{Please fill in all fields}', 'error')
            return redirect(url_for('home'))

        # Verify authentication
        auth_success, user_info = authenticate_user(username, password)
        
        if auth_success:
            logger.info("Authentication successful")
            
            try:
                # Apply location policy
                user_location = user_info.get('location', [])
                user_role = user_info.get('role', 'USER').upper()
                logger.info(f"User location info: {user_location}, type: {type(user_location)}, role: {user_role}")
                
                # ADMIN users always have access to all sites
                if user_role == 'ADMIN':
                    safe_site_servers = get_safe_site_servers()
                    allowed_sites = list(safe_site_servers.keys())
                    logger.info(f"ADMIN user - all sites allowed: {allowed_sites}")
                # If location is All or has 2 or more, allow all sites
                elif (isinstance(user_location, list) and (len(user_location) > 1 or (len(user_location) == 1 and user_location[0].lower() == 'all'))) or (isinstance(user_location, str) and user_location.lower() == 'all'):
                    safe_site_servers = get_safe_site_servers()
                    allowed_sites = list(safe_site_servers.keys())
                    logger.info(f"All sites allowed: {allowed_sites}")
                else:
                    # If location is 1, allow only that site
                    allowed_sites = user_location if isinstance(user_location, list) else [user_location]
                    # Force site value to allowed_sites[0]
                    if allowed_sites:
                        site = allowed_sites[0]
                        logger.info(f"Single site allowed: {allowed_sites}, selected site: {site}")
                    else:
                        # Set default if allowed_sites is empty
                        allowed_sites = [site]
                        logger.warning(f"allowed_sites is empty, setting default: {allowed_sites}")

                if site not in allowed_sites:
                    flash(f'You are not allowed to access {site}.', 'error')
                    return redirect(url_for('home'))

                # Step 1: Clean up Data folder first (delete existing files)
                cache_policy = get_cache_policy()
                if cache_policy['cleanup_data_on_login']:
                    cleanup_success = cleanup_data_folder()
                    if cleanup_success:
                        logger.info("Data folder cleanup succeeded - old files deleted")
                    else:
                        logger.warning("Data folder cleanup failed")
                else:
                    logger.info("Skipping data folder cleanup due to cache policy")

                # Step 2: Query data from DB (removed JSON file creation)
                # DB is updated daily at 3 AM, so API calls on login are unnecessary
                logger.info(f"Auto-collecting site data on login - site: {site}")
                
                # Step 3: Auto-collect site-specific data
                try:
                    # 3-1. Collect client data (every time)

                    from api_client import fetch_client_information
                    logger.info(f"🔍 DEBUG: fetch_client_information imported, calling now...")
                    import time
                    start_time = time.time()
                    client_success, client_info = fetch_client_information(site)
                    elapsed_time = time.time() - start_time
                    logger.info(f"🔍 DEBUG: fetch_client_information returned after {elapsed_time:.2f} seconds - success: {client_success}")
                    if client_success:
                        logger.info(f"Client data collection succeeded - {site}: {len(client_info)} residents")
                    else:
                        logger.warning(f"Client data collection failed - {site}")
                    
                    # 3-2. Collect Progress Notes data (cache not needed in DB direct access mode)
                    # Check DB direct access mode
                    import sqlite3
                    import os
                    
                    use_db_direct = False
                    try:
                        conn = sqlite3.connect('progress_report.db', timeout=10)
                        cursor = conn.cursor()
                        cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
                        result = cursor.fetchone()
                        conn.close()
                        
                        if result and result[0]:
                            use_db_direct = result[0].lower() == 'true'
                        else:
                            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
                    except:
                        use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
                    
                    if use_db_direct:
                        # DB direct access mode: cache not needed - query directly when needed
                        logger.info(f"🔌 Direct DB access mode: Progress Notes are fetched in real time (no cache) - {site}")
                    else:
                        # API mode: use cache (reduce API call costs)
                        from progress_notes_json_cache import json_cache
                        from api_progressnote_fetch import fetch_progress_notes_for_site
                        logger.info(f"🌐 API mode: Fetch and cache Progress Notes - {site}")
                        progress_success, progress_notes, _ = fetch_progress_notes_for_site(site, 7)
                        if progress_success and progress_notes:
                            json_cache.update_cache(site, progress_notes)
                            logger.info(f"Progress Notes fetched and cached - {site}: {len(progress_notes)} items")
                        else:
                            logger.warning(f"Progress Notes fetch failed - {site}")
                    
                    # 3-3. Collect Care Area and Event Type data (DB direct access)
                    if use_db_direct:
                        # DB direct access mode
                        try:
                            from manad_db_connector import MANADDBConnector
                            import json
                            
                            connector = MANADDBConnector(site)
                            
                            # Query Care Area
                            logger.info(f"🔌 Direct DB access mode: Fetching Care Area - {site}")
                            care_success, care_areas = connector.fetch_care_areas()
                            if care_success and care_areas:
                                # Save as JSON file (maintain existing format)
                                os.makedirs('data', exist_ok=True)
                                with open('data/carearea.json', 'w', encoding='utf-8') as f:
                                    json.dump(care_areas, f, ensure_ascii=False, indent=4)
                                logger.info(f"✅ Care Area fetched from DB - {site}: {len(care_areas)} items")
                            else:
                                error_msg = f"❌ Direct DB access failed: {site} - Care Area result is empty."
                                logger.error(error_msg)
                                raise Exception(error_msg)
                            
                            # Query Event Type
                            logger.info(f"🔌 Direct DB access mode: Fetching Event Types - {site}")
                            event_success, event_types = connector.fetch_event_types()
                            if event_success and event_types:
                                # Save as JSON file (maintain existing format)
                                os.makedirs('data', exist_ok=True)
                                site_filename = f'data/eventtype_{site}.json'
                                with open(site_filename, 'w', encoding='utf-8') as f:
                                    json.dump(event_types, f, ensure_ascii=False, indent=4)
                                with open('data/eventtype.json', 'w', encoding='utf-8') as f:
                                    json.dump(event_types, f, ensure_ascii=False, indent=4)
                                logger.info(f"✅ Event Types fetched from DB - {site}: {len(event_types)} items")
                            else:
                                error_msg = f"❌ Direct DB access failed: {site} - Event Type result is empty."
                                logger.error(error_msg)
                                raise Exception(error_msg)
                        except Exception as db_error:
                            error_msg = (
                                f"❌ Direct DB access failed: {site} - {str(db_error)}. "
                                f"Check DB connection settings and driver installation."
                            )
                            logger.error(error_msg)
                            raise Exception(error_msg)
                    else:
                        # API mode
                        from daily_data_manager import daily_data_manager
                        daily_results = daily_data_manager.collect_daily_data_if_needed(site)
                        if daily_results['care_area']:
                            logger.info(f"Care Area data collection completed - {site}")
                        if daily_results['event_type']:
                            logger.info(f"Event Type data collection completed - {site}")
                    
                    logger.info(f"Site data collection completed - site: {site}")
                    
                    # Step 4: Login processing using Flask-Login
                    user = User(username, user_info)
                    user_role = user_info.get('role', 'USER').upper()
                    logger.info(f"🔍 DEBUG: User object created, role: {user_role}")
                   
                    
                    # Apply same session settings to all users
                    login_user(user, remember=False)  # All users: session expires when browser closes
                    session.permanent = False
                    logger.info(f"User login: remember=False, session.permanent=False (role: {user_role})")
                    
                    # Set session timeout based on user role

                    set_session_permanent(user_role)
                    logger.info(f"🔍 DEBUG: Session permanent set")
                    
                    # Record session creation time

                    session['_created'] = get_australian_time().isoformat()
                    session['user_role'] = user_role  # Store user role in session
                    
                    # Store additional information in session
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # Store allowed site information
                    
                    logger.info(f"Session saved: site={site}, allowed_sites={allowed_sites}")
                    logger.info(f"Full session contents after login: {dict(session)}")
                    
                    flash('Login successful!', 'success')
                    logger.info(f"Login succeeded - user: {username}, site: {site}")
                    logger.info(f"🔍 DEBUG: About to determine redirect destination")
                    
                    # Log successful login
                    success_user_info = {
                        "username": username,
                        "display_name": user_info.get('display_name', username),
                        "role": user_info.get('role', 'unknown'),
                        "position": user_info.get('position', 'unknown')
                    }
                    usage_logger.log_access(success_user_info)
                    
                    # Redirect users with landing_page set to that page
                    landing_page = user_info.get('landing_page')
                    if landing_page:
                        logger.info(f"🔍 DEBUG: Landing page found: {landing_page}, redirecting...")
                        logger.info(f"Login succeeded - user {username}, landing_page set: {landing_page}")
                        return redirect(landing_page)
                    
                    # Redirect ROD users to dedicated dashboard (case-insensitive)
                    username_upper = username.upper()
                    logger.info(f"Login username check: {username} -> {username_upper}")
                    logger.info(f"🔍 DEBUG: Checking user type for redirect - username_upper: {username_upper}, user_role: {user_role}")
                    if username_upper == 'ROD':
                        logger.info("Login succeeded - ROD user detected, redirecting to rod_dashboard")
                        return redirect(url_for('rod_dashboard', site=site))
                    elif username_upper == 'YKROD':
                        logger.info("Login succeeded - YKROD user detected, redirecting to Yankalilla ROD dashboard")
                        session['site'] = 'Yankalilla'
                        session['allowed_sites'] = ['Yankalilla']
                        return redirect(url_for('rod_dashboard', site='Yankalilla'))
                    elif username_upper == 'PGROD':
                        logger.info(
                            "Login succeeded - PGROD user detected, multi-site access enabled, redirecting to "
                            "Parafield Gardens ROD dashboard"
                        )
                        session['site'] = 'Parafield Gardens'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
                        return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
                    elif username_upper == 'WPROD':
                        logger.info("Login succeeded - WPROD user detected, redirecting to West Park ROD dashboard")
                        session['site'] = 'West Park'
                        session['allowed_sites'] = ['West Park']
                        return redirect(url_for('rod_dashboard', site='West Park'))
                    elif username_upper == 'RSROD':
                        logger.info(
                            "Login succeeded - RSROD user detected, multi-site access enabled, redirecting to "
                            "Ramsay ROD dashboard"
                        )
                        session['site'] = 'Ramsay'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Ramsay'))
                    elif username_upper == 'NROD':
                        logger.info("Login succeeded - NROD user detected, redirecting to Nerrilda ROD dashboard")
                        session['site'] = 'Nerrilda'
                        session['allowed_sites'] = ['Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Nerrilda'))
                    elif user_role == 'SITE_ADMIN':
                        logger.info("🔍 DEBUG: SITE_ADMIN detected, redirecting to callbell")
                        logger.info("Login succeeded - SITE_ADMIN user detected, redirecting to callbell")
                        return redirect(url_for('callbell.callbell_page'))
                    else:
                        logger.info(f"🔍 DEBUG: Regular user detected, redirecting to progress_notes for site: {site}")
                        logger.info("Login succeeded - regular user, redirecting to progress_notes")
                        redirect_url = url_for('progress_notes', site=site)
                        logger.info(f"🔍 DEBUG: Redirect URL generated: {redirect_url}, about to return redirect()")
                        return redirect(redirect_url)
                        
                except Exception as e:
                    logger.error(f"🔍 DEBUG: Exception caught in login data collection: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"🔍 DEBUG: Full traceback:\n{traceback.format_exc()}")
                    logger.error(f"Error saving data: {str(e)}")
                    # Allow login even if data collection fails
                    try:
                        logger.info(f"🔍 DEBUG: Attempting fallback login despite data collection error")
                        user = User(username, user_info)
                        user_role = user_info.get('role', 'USER').upper()
                        login_user(user, remember=False)
                        session.permanent = False
                        set_session_permanent(user_role)
                        session['_created'] = get_australian_time().isoformat()
                        session['user_role'] = user_role
                        session['site'] = site
                        session['allowed_sites'] = allowed_sites
                        logger.info(f"Login processing completed despite data collection error: site={site}, allowed_sites={allowed_sites}")
                        flash('Login successful! (Some data may not be available)', 'warning')
                        # Regular users redirect to progress_notes
                        return redirect(url_for('progress_notes', site=site))
                    except Exception as login_error:
                        logger.error(f"Error during login processing: {str(login_error)}")
                        flash('Login failed due to system error.', 'error')
                        return redirect(url_for('home'))
            except Exception as e:
                logger.error(f"Error during API call: {str(e)}")
                # Allow login even on API error
                try:
                    # Login processing using Flask-Login
                    user = User(username, user_info)
                    user_role = user_info.get('role', 'USER').upper()
                    
                    # Apply same session settings to all users
                    login_user(user, remember=False)  # All users: session expires when browser closes
                    session.permanent = False
                    logger.info(f"User login (with API error): remember=False, session.permanent=False (role: {user_role})")
                    
                    # Set session timeout based on user role
                    set_session_permanent(user_role)
                    
                    # Record session creation time
                    session['_created'] = get_australian_time().isoformat()
                    session['user_role'] = user_role  # Store user role in session
                    
                    # Store additional information in session
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # Store allowed site information
                    
                    logger.info(f"Session saved (with API error): site={site}, allowed_sites={allowed_sites}")
                    logger.info(f"Full session contents after login (with API error): {dict(session)}")
                    
                    flash('Login successful! (Some data may not be available)', 'success')
                    logger.info(f"Login succeeded (with API error) - user: {username}, site: {site}")
                    
                    # Redirect ROD users to dedicated dashboard (case-insensitive)
                    username_upper = username.upper()
                    logger.info(f"Login username check (with API error): {username} -> {username_upper}")
                    if username_upper == 'ROD':
                        logger.info("Login succeeded (with API error) - ROD user detected, redirecting to rod_dashboard")
                        return redirect(url_for('rod_dashboard', site=site))
                    elif username_upper == 'YKROD':
                        logger.info(
                            "Login succeeded (with API error) - YKROD user detected, redirecting to "
                            "Yankalilla ROD dashboard"
                        )
                        session['site'] = 'Yankalilla'
                        session['allowed_sites'] = ['Yankalilla']
                        return redirect(url_for('rod_dashboard', site='Yankalilla'))
                    elif username_upper == 'PGROD':
                        logger.info(
                            "Login succeeded (with API error) - PGROD user detected, multi-site access enabled, "
                            "redirecting to Parafield Gardens ROD dashboard"
                        )
                        session['site'] = 'Parafield Gardens'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
                        return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
                    elif username_upper == 'WPROD':
                        logger.info(
                            "Login succeeded (with API error) - WPROD user detected, redirecting to West Park ROD dashboard"
                        )
                        session['site'] = 'West Park'
                        session['allowed_sites'] = ['West Park']
                        return redirect(url_for('rod_dashboard', site='West Park'))
                    elif username_upper == 'RSROD':
                        logger.info(
                            "Login succeeded (with API error) - RSROD user detected, multi-site access enabled, "
                            "redirecting to Ramsay ROD dashboard"
                        )
                        session['site'] = 'Ramsay'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Ramsay'))
                    elif username_upper == 'NROD':
                        logger.info(
                            "Login succeeded (with API error) - NROD user detected, redirecting to Nerrilda ROD dashboard"
                        )
                        session['site'] = 'Nerrilda'
                        session['allowed_sites'] = ['Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Nerrilda'))
                    elif user_role == 'SITE_ADMIN':
                        logger.info(
                            "Login succeeded (with API error) - SITE_ADMIN user detected, redirecting to callbell"
                        )
                        return redirect(url_for('callbell.callbell_page'))
                    else:
                        logger.info("Login succeeded (with API error) - regular user, redirecting to progress_notes")
                        return redirect(url_for('progress_notes', site=site))
                except Exception as login_error:
                    logger.error(f"Error during login processing: {str(login_error)}")
                    flash('Login failed due to system error.', 'error')
                    return redirect(url_for('home'))
        else:
            flash('{Invalid authentication information}', 'error')
            return redirect(url_for('home'))
            
    except Exception as e:
        logger.error(f"Exception during login processing: {str(e)}")
        flash('{An error occurred while connecting to the server}', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """Logout processing"""
    try:
        # Log session state before logout
        if current_user.is_authenticated:
            logger.info(f"Logout started - user: {current_user.username}, role: {current_user.role}")
            user_info = {
                "username": current_user.username,
                "display_name": current_user.display_name,
                "role": current_user.role,
                "position": current_user.position
            }
            usage_logger.log_access(user_info)
        else:
            logger.info("Logout started - unauthenticated user")
        
        # Flask-Login logout
        logout_user()
        logger.info("Flask-Login logout_user() completed")
        
        # Complete session cleanup
        session.clear()
        logger.info("session.clear() completed")
        
        # Additional session cleanup (Flask-Login related)
        if '_user_id' in session:
            del session['_user_id']
            logger.info("_user_id removed from session")
        
        if 'user_role' in session:
            del session['user_role']
            logger.info("user_role removed from session")
        
        if '_created' in session:
            del session['_created']
            logger.info("_created removed from session")
        
        if 'allowed_sites' in session:
            del session['allowed_sites']
            logger.info("allowed_sites removed from session")
        
        if 'site' in session:
            del session['site']
            logger.info("site removed from session")
        
        # Additional Flask-Login related session cleanup
        if '_fresh' in session:
            del session['_fresh']
            logger.info("_fresh removed from session")
        
        if '_permanent' in session:
            del session['_permanent']
            logger.info("_permanent removed from session")
        
        # Mark session as modified
        session.modified = True
        logger.info("Session update completed")
        
        # Clear Flask-Login session cookies as well
        response = make_response(redirect(url_for('home')))
        response.delete_cookie('remember_token')
        response.delete_cookie('session')
        logger.info("Session cookies cleared")
        
        flash('You have been logged out successfully.', 'info')
        logger.info("Logout completed - redirecting to home page")
        
        return response
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        # Try to clean up session even on error
        try:
            session.clear()
            logout_user()
        except:
            pass
        flash('Logout completed with errors.', 'warning')
        return redirect(url_for('home'))

@app.route('/api/clear-database', methods=['POST'])
@login_required
def clear_database():
    """Database initialization"""
    try:
        return jsonify({
            'success': True,
            'message': 'Database cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing database: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/index')
@login_required
def index():
    """Progress Note input page"""
    site = request.args.get('site', session.get('site', 'Parafield Gardens'))
    return render_template('index.html', selected_site=site, current_user=current_user)

@app.route('/rod-dashboard')
@login_required
def rod_dashboard():
    """ROD dedicated dashboard"""
    # Restrict access if not ROD user (case-insensitive)
    username_upper = current_user.username.upper()
    logger.info(f"ROD dashboard access attempt - username check: {current_user.username} -> {username_upper}")
    if username_upper not in ['ROD', 'YKROD', 'PGROD', 'WPROD', 'RSROD', 'NROD']:
        flash('Access denied. This dashboard is for ROD users only.', 'error')
        return redirect(url_for('progress_notes'))
    
    allowed_sites = session.get('allowed_sites', [])
    site = request.args.get('site', session.get('site', 'Parafield Gardens'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    # Get site information (site-specific ROD users see only their site)
    sites_info = []
    safe_site_servers = get_safe_site_servers()
    
    # Show only their site for site-specific ROD users
    if username_upper in ['YKROD', 'WPROD', 'NROD']:
        # Single site dedicated user
        allowed_sites = session.get('allowed_sites', [])
        if allowed_sites:
            site_name = allowed_sites[0]
            sites_info.append({
                'name': site_name,
                'server': safe_site_servers.get(site_name, 'Unknown'),
                'is_selected': True
            })
    elif username_upper in ['PGROD', 'RSROD']:
        # Multi-site access enabled user
        allowed_sites = session.get('allowed_sites', [])
        for site_name in allowed_sites:
            if site_name in safe_site_servers:
                sites_info.append({
                    'name': site_name,
                    'server': safe_site_servers[site_name],
                    'is_selected': site_name == site
                })
    else:
        # General ROD users see all sites
        for site_name in safe_site_servers.keys():
            sites_info.append({
                'name': site_name,
                'server': safe_site_servers[site_name],
                'is_selected': site_name == site
            })
    
    return render_template('RODDashboard.html', 
                         site=site, 
                         sites=sites_info,
                         current_user=current_user)


# ==================== Edenfield Dashboard ====================
@app.route('/edenfield-dashboard')
@login_required
def edenfield_dashboard():
    """
    Edenfield Dashboard - Executive comprehensive dashboard
    Shows overall status of 5 sites at a glance
    """
    try:
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        return render_template('edenfield_dashboard.html', 
                             sites=sites,
                             current_user=current_user)
    except Exception as e:
        logger.error(f"Edenfield Dashboard error: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/edenfield/stats')
@login_required
def get_edenfield_stats():
    """
    Edenfield overall statistics API
    - Integrated data from 5 sites
    - Resident, Incident, Progress Note statistics
    - Period filter: today, week, month (default)
    """
    try:
        # Process period parameter
        period = request.args.get('period', 'month')
        
        if period == 'today':
            days = 0  # Today only
            date_filter = "CAST(GETDATE() AS DATE)"
        elif period == 'week':
            days = 7
            date_filter = "DATEADD(day, -7, GETDATE())"
        else:  # month (default)
            days = 30
            date_filter = "DATEADD(day, -30, GETDATE())"
        
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        all_stats = []
        
        for site_name in sites:
            try:
                from manad_db_connector import MANADDBConnector
                connector = MANADDBConnector(site_name)
                
                with connector.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    site_stats = {'site': site_name}
                    
                    # 1. Client count (current residents only - active Clients where ClientService.EndDate is NULL)
                    cursor.execute("""
                        SELECT COUNT(DISTINCT c.Id) 
                        FROM Client c
                        INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                        WHERE c.IsDeleted = 0 
                        AND cs.IsDeleted = 0
                        AND cs.EndDate IS NULL
                    """)
                    site_stats['total_persons'] = cursor.fetchone()[0]
                    
                    # 2. AdverseEvent (Incident) statistics - within selected period
                    # StatusEnumId: 0=Open, 1=InProgress, 2=Closed
                    if period == 'today':
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND Date >= {date_filter}
                        """)
                    row = cursor.fetchone()
                    site_stats['incidents'] = {
                        'total': row[0] or 0,
                        'open': row[1] or 0,
                        'closed': row[2] or 0,
                        'ambulance': row[3] or 0,
                        'hospital': row[4] or 0
                    }
                    site_stats['incidents_30days'] = row[0] or 0  # Incidents within selected period
                    
                    # 3. Fall incident count - within selected period
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND CAST(ae.Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND ae.Date >= {date_filter}
                        """)
                    site_stats['fall_count'] = cursor.fetchone()[0]
                    
                    # 3-1. Skin & Wound incident count - within selected period
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND (at.Description LIKE '%Skin%' OR at.Description LIKE '%Wound%')
                            AND CAST(ae.Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND (at.Description LIKE '%Skin%' OR at.Description LIKE '%Wound%')
                            AND ae.Date >= {date_filter}
                        """)
                    site_stats['skin_wound_count'] = cursor.fetchone()[0]
                    
                    # 4. Progress Note count - within selected period
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND Date >= {date_filter}
                        """)
                    site_stats['progress_notes_30days'] = cursor.fetchone()[0]
                    
                    # 5. Activity count - within selected period
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM ActivityEvent 
                            WHERE IsDeleted = 0 
                            AND CAST(StartDate AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM ActivityEvent 
                            WHERE IsDeleted = 0 
                            AND StartDate >= {date_filter}
                        """)
                    site_stats['activities_30days'] = cursor.fetchone()[0]
                    
                    # 6. Activity distribution by type (top 5) - within selected period
                    if period == 'today':
                        cursor.execute("""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND CAST(ae.StartDate AS DATE) = CAST(GETDATE() AS DATE)
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    elif period == 'week':
                        cursor.execute("""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND ae.StartDate >= DATEADD(day, -7, GETDATE())
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    else:  # month
                        cursor.execute("""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND ae.StartDate >= DATEADD(day, -30, GETDATE())
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    site_stats['activity_types'] = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
                    
                    all_stats.append(site_stats)
                    
            except Exception as site_error:
                logger.warning(f"Failed to fetch stats for site {site_name}: {site_error}")
                all_stats.append({
                    'site': site_name,
                    'error': str(site_error),
                    'total_persons': 0,
                    'incidents': {'total': 0, 'open': 0, 'closed': 0, 'ambulance': 0, 'hospital': 0},
                    'incidents_30days': 0,
                    'fall_count': 0,
                    'skin_wound_count': 0,
                    'progress_notes_30days': 0,
                    'activities_30days': 0,
                    'activity_types': []
                })
        
        # Calculate total sums
        totals = {
            'total_persons': sum(s.get('total_persons', 0) for s in all_stats),
            'total_incidents': sum(s.get('incidents', {}).get('total', 0) for s in all_stats),
            'open_incidents': sum(s.get('incidents', {}).get('open', 0) for s in all_stats),
            'closed_incidents': sum(s.get('incidents', {}).get('closed', 0) for s in all_stats),
            'ambulance_calls': sum(s.get('incidents', {}).get('ambulance', 0) for s in all_stats),
            'hospital_admissions': sum(s.get('incidents', {}).get('hospital', 0) for s in all_stats),
            'incidents_30days': sum(s.get('incidents_30days', 0) for s in all_stats),
            'fall_count': sum(s.get('fall_count', 0) for s in all_stats),
            'skin_wound_count': sum(s.get('skin_wound_count', 0) for s in all_stats),
            'progress_notes_30days': sum(s.get('progress_notes_30days', 0) for s in all_stats),
            'activities_30days': sum(s.get('activities_30days', 0) for s in all_stats)
        }
        
        # Total sums by activity type
        activity_totals = {}
        for site in all_stats:
            for at in site.get('activity_types', []):
                name = at['name']
                if name in activity_totals:
                    activity_totals[name] += at['count']
                else:
                    activity_totals[name] = at['count']
        totals['activity_types'] = sorted(
            [{'name': k, 'count': v} for k, v in activity_totals.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]  # Top 10
        
        return jsonify({
            'success': True,
            'period': period,
            'sites': all_stats,
            'totals': totals
        })
        
    except Exception as e:
        logger.error(f"Edenfield stats error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/progress-notes')
@login_required
def progress_notes():
    try:
        allowed_sites = session.get('allowed_sites', [])
        site = request.args.get('site', session.get('site', 'Parafield Gardens'))
        logger.info(f"progress_notes: allowed_sites={allowed_sites} (type: {type(allowed_sites)}), site={site}")
        logger.info(f"progress_notes full session contents: {dict(session)}")
        logger.info(f"progress_notes request.args: {dict(request.args)}")
        
        # If allowed_sites is empty, select from default site list
        if not allowed_sites:
            safe_site_servers = get_safe_site_servers()
            allowed_sites = list(safe_site_servers.keys())
            # Save back to session
            session['allowed_sites'] = allowed_sites
            logger.warning(f"allowed_sites is empty, using default site list: {allowed_sites}")
        
        # If only one location, force that site
        if isinstance(allowed_sites, list) and len(allowed_sites) == 1:
            forced_site = allowed_sites[0]
            if site != forced_site:
                logger.info(f"Forced single-site redirect: {site} -> {forced_site}")
                return redirect(url_for('progress_notes', site=forced_site))
            site = forced_site
        
        # Record access log
        try:
            user_info = {
                "username": current_user.username,
                "display_name": current_user.display_name,
                "role": current_user.role,
                "position": current_user.position
            }
            usage_logger.log_access(user_info)
        except Exception as e:
            logger.error(f"Failed to write access log: {e}")
        
        logger.info(f"progress_notes final render - site: {site}, allowed_sites: {allowed_sites}")
        return render_template('ProgressNoteList.html', site=site)
    
    except Exception as e:
        logger.error(f"progress_notes error: {e}")
        # Redirect to login page on error
        flash('An error occurred while loading the page. Please log in again.', 'error')
        return redirect(url_for('login_page'))

@app.route('/save_progress_note', methods=['POST'])
@login_required
def save_progress_note():
    """Save Progress Note data and send to API"""
    try:
        # Receive JSON data
        form_data = request.get_json()
        
        if not form_data:
            return jsonify({'success': False, 'message': 'Data is empty'})
        
        logger.info(f"Received form data: {form_data}")
        
        # Collect user information
        user_info = {
            "username": current_user.username if current_user else None,
            "display_name": current_user.display_name if current_user else None,
            "role": current_user.role if current_user else None,
            "position": current_user.position if current_user else None
        }
        
        # Convert to Progress Note JSON format
        progress_note = create_progress_note_json(form_data)
        
        if not progress_note:
            return jsonify({'success': False, 'message': 'Failed to generate JSON.'})
        
        # Save to prepare_send.json
        if not save_prepare_send_json(progress_note):
            return jsonify({'success': False, 'message': 'Failed to save file.'})
        
        logger.info("prepare_send.json saved, starting API transmission...")
        
        # Send Progress Note to API
        try:
            from api_progressnote import send_progress_note_to_api
            
            # Get selected site information from session
            selected_site = session.get('site', 'Parafield Gardens')  # Default: Parafield Gardens
            
            api_success, api_response = send_progress_note_to_api(selected_site)
            
            if api_success:
                logger.info("Progress Note API transmission succeeded")
                # Record success log
                usage_logger.log_progress_note(form_data, user_info, success=True)
                return jsonify({
                    'success': True, 
                    'message': 'Progress Note saved and sent to API successfully.',
                    'data': progress_note,
                    'api_response': api_response
                })
            else:
                logger.warning(f"Progress Note API transmission failed: {api_response}")
                # Record failure log
                usage_logger.log_progress_note(form_data, user_info, success=False, error_message=api_response)
                # File save succeeded but API transmission failed
                return jsonify({
                    'success': True,  # File save succeeded
                    'message': 'Progress Note saved but API transmission failed.',
                    'data': progress_note,
                    'api_error': api_response,
                    'warning': 'API transmission failed. The file was saved successfully.'
                })
        except ImportError as e:
            logger.error(f"API module import error: {str(e)}")
            # Record failure log
            usage_logger.log_progress_note(form_data, user_info, success=False, error_message=f"Import error: {str(e)}")
            return jsonify({
                'success': True,  # File save succeeded
                'message': 'Progress Note saved but API module not available.',
                'data': progress_note,
                'warning': 'API transmission module not found. The file was saved successfully.'
            })
        except Exception as e:
            logger.error(f"Unexpected error during API transmission: {str(e)}")
            # Record failure log
            usage_logger.log_progress_note(form_data, user_info, success=False, error_message=str(e))
            return jsonify({
                'success': True,  # File save succeeded
                'message': 'Progress Note saved but API transmission failed.',
                'data': progress_note,
                'api_error': str(e),
                'warning': f'An error occurred while sending the API: {str(e)}. The file was saved successfully.'
            })
            
    except Exception as e:
        logger.error(f"Progress Note saving error: {str(e)}")
        # Record complete failure log
        user_info = {
            "username": current_user.username if current_user else None,
            "display_name": current_user.display_name if current_user else None,
            "role": current_user.role if current_user else None,
            "position": current_user.position if current_user else None
        }
        usage_logger.log_progress_note(form_data, user_info, success=False, error_message=str(e))
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

# ==============================
# API Endpoints
# ==============================

@app.route('/data/Client_list.json')
def get_client_list():
    """Return client list JSON"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'Client_list.json')
    except FileNotFoundError:
        return jsonify([]), 404

@app.route('/api/clients/<site>')
@login_required
def get_clients_for_site(site):
    """Return client list for specific site"""
    try:
        from api_client import fetch_client_information
        
        success, client_data = fetch_client_information(site)
        
        if not success or not client_data:
            logger.warning(f"Unable to fetch client data: {site}")
            return jsonify([]), 404
        
        # Convert client data format (to match API format)
        clients = []
        if isinstance(client_data, list):
            for client in client_data:
                # Create ClientName (FirstName + LastName)
                first_name = client.get('FirstName', '')
                last_name = client.get('LastName', '')
                client_name = f"{first_name} {last_name}".strip() if first_name or last_name else 'Unknown'
                
                # Get PersonId/ClientId (Id field is Client ID)
                client_id = client.get('Id') or client.get('PersonId') or client.get('ClientId')
                
                if client_id:
                    # Process BirthDate
                    birth_date = client.get('BirthDate')
                    birth_date_str = None
                    age = None
                    if birth_date:
                        if isinstance(birth_date, str):
                            birth_date_str = birth_date
                        else:
                            birth_date_str = birth_date.isoformat() if hasattr(birth_date, 'isoformat') else str(birth_date)
                        
                        # Calculate age
                        try:
                            from datetime import datetime
                            if isinstance(birth_date, str):
                                birth_dt = datetime.fromisoformat(birth_date.split('T')[0])
                            else:
                                birth_dt = birth_date if isinstance(birth_date, datetime) else datetime.fromisoformat(str(birth_date).split('T')[0])
                            today = datetime.now()
                            age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))
                        except:
                            pass
                    
                    # Process AdmissionDate
                    admission_date = client.get('AdmissionDate')
                    admission_date_str = None
                    admission_duration = None
                    if admission_date:
                        if isinstance(admission_date, str):
                            admission_date_str = admission_date
                        else:
                            admission_date_str = admission_date.isoformat() if hasattr(admission_date, 'isoformat') else str(admission_date)
                        
                        # Calculate admission duration
                        try:
                            from datetime import datetime, timedelta
                            if isinstance(admission_date, str):
                                adm_dt = datetime.fromisoformat(admission_date.split('T')[0])
                            else:
                                adm_dt = admission_date if isinstance(admission_date, datetime) else datetime.fromisoformat(str(admission_date).split('T')[0])
                            today = datetime.now()
                            delta = today - adm_dt
                            years = delta.days // 365
                            months = (delta.days % 365) // 30
                            days = delta.days % 30
                            if years > 0:
                                admission_duration = f"{years} year{'s' if years > 1 else ''} {months} month{'s' if months > 1 else ''} {days} day{'s' if days > 1 else ''}"
                            elif months > 0:
                                admission_duration = f"{months} month{'s' if months > 1 else ''} {days} day{'s' if days > 1 else ''}"
                            else:
                                admission_duration = f"{days} day{'s' if days > 1 else ''}"
                        except:
                            pass
                    
                    clients.append({
                        'PersonId': client_id,  # Use Client ID as PersonId (used in dropdown)
                        'ClientName': client_name,
                        'FirstName': first_name,
                        'MiddleName': client.get('MiddleName', ''),
                        'LastName': last_name,
                        'Surname': last_name,  # Also provide LastName as Surname
                        'PreferredName': client.get('PreferredName', ''),
                        'BirthDate': birth_date_str,
                        'Age': age,
                        'WingName': client.get('WingName', ''),
                        'RoomName': client.get('RoomName', '') or client.get('RoomNumber', ''),
                        'RoomNumber': client.get('RoomNumber', ''),
                        'LocationName': client.get('LocationName', ''),
                        'AdmissionDate': admission_date_str,
                        'AdmissionDuration': admission_duration,
                        'CareType': client.get('CareType', 'Permanent'),
                        'MainClientServiceId': client.get('MainClientServiceId', ''),
                        'IsActive': client.get('IsActive', True)
                    })
        
        logger.info(f"✅ Returning client list: {site} - {len(clients)} residents")
        return jsonify(clients)
        
    except Exception as e:
        logger.error(f"Error retrieving client list ({site}): {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/data/carearea.json')
@login_required
def get_care_area_list():
    """Return Care Area list JSON"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'carearea.json')
    except FileNotFoundError:
        return jsonify([]), 404

@app.route('/data/eventtype.json')
@login_required
def get_event_type_list():
    """Return Event Type list JSON"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'eventtype.json')
    except FileNotFoundError:
        return jsonify([]), 404


@app.route('/api/event-types', methods=['POST'])
@login_required
def api_event_types():
    """Return event types for a site (for Event Type filter dropdown). DB direct or JSON fallback."""
    try:
        data = request.get_json() or {}
        site = data.get('site') or request.args.get('site')
        if not site:
            return jsonify({'success': False, 'message': 'site required'}), 400
        use_db_direct = False
        try:
            conn = sqlite3.connect('progress_report.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
            result = cursor.fetchone()
            conn.close()
            if result and result[0]:
                use_db_direct = result[0].lower() == 'true'
            else:
                use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        except Exception:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        if use_db_direct:
            from manad_db_connector import MANADDBConnector
            connector = MANADDBConnector(site)
            success, event_types = connector.fetch_event_types()
            if success and event_types:
                return jsonify({'success': True, 'data': event_types})
        from api_eventtype import get_site_event_types
        raw = get_site_event_types(site)
        event_types = raw if isinstance(raw, list) else (raw.get('data', []) if isinstance(raw, dict) else [])
        if event_types:
            return jsonify({'success': True, 'data': event_types})
        return jsonify({'success': False, 'data': [], 'message': 'No event types found'})
    except Exception as e:
        logger.error(f"Error fetching event types: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/rod-residence-status')
@login_required
def get_rod_residence_status():
    """Get Resident of the day status"""
    try:
        site = request.args.get('site', 'Parafield Gardens')
        year = int(request.args.get('year', get_australian_time().year))
        month = int(request.args.get('month', get_australian_time().month))
        
        logger.info(f"Fetching Resident of the day status for {site} - {year}/{month}")
        
        # Get Resident of the day notes and client data
        from api_progressnote_fetch import fetch_residence_of_day_notes_with_client_data
        residence_status = fetch_residence_of_day_notes_with_client_data(site, year, month)
        
        if not residence_status:
            logger.warning(f"No residence status data found for {site}")
            return jsonify({'error': 'No data found'}), 404
        
        # Calculate statistics
        total_residences = len(residence_status)
        total_rn_en_notes = sum(1 for status in residence_status.values() if status.get('rn_en_has_note', False))
        total_pca_notes = sum(1 for status in residence_status.values() if status.get('pca_has_note', False))
        
        # Calculate total note count
        total_rn_en_count = sum(status.get('rn_en_count', 0) for status in residence_status.values())
        total_pca_count = sum(status.get('pca_count', 0) for status in residence_status.values())
        total_notes_count = total_rn_en_count + total_pca_count
        
        # Calculate overall completion rate (ratio of Residences with both RN/EN and PCA completed)
        completed_residences = sum(1 for status in residence_status.values() 
                                if status.get('rn_en_has_note', False) and status.get('pca_has_note', False))
        overall_completion_rate = round((completed_residences / total_residences * 100) if total_residences > 0 else 0, 1)
        
        logger.info(f"Resident of the day status processed: {total_residences} residences, {total_rn_en_notes} RN/EN notes, {total_pca_notes} PCA notes, {completed_residences} completed, {overall_completion_rate}% completion rate")
        logger.info(f"Total notes found: {total_notes_count} (RN/EN: {total_rn_en_count}, PCA: {total_pca_count})")
        
        return jsonify({
            'residence_status': list(residence_status.values()),
            'total_residences': total_residences,
            'total_rn_en_notes': total_rn_en_notes,
            'total_pca_notes': total_pca_notes,
            'total_rn_en_count': total_rn_en_count,
            'total_pca_count': total_pca_count,
            'total_notes_count': total_notes_count,
            'overall_completion_rate': overall_completion_rate
        })
        
    except Exception as e:
        logger.error(f"Error in get_rod_residence_status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rod-residence-list', methods=['POST'])
@login_required
def get_rod_residence_list():
    """Return ROD-only Residence list (for empty table)"""
    try:
        # Only ROD users can access
        if current_user.username.upper() != 'ROD':
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        data = request.get_json()
        site = data.get('site', 'Parafield Gardens')

        try:
            from api_client import fetch_client_information
            
            # Get client data
            client_success, client_data = fetch_client_information(site)
            
            if not client_success:
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch client data'
                }), 500

            # Extract Residence list from client data
            residences = []
            if isinstance(client_data, list):
                residences = client_data
            elif isinstance(client_data, dict) and 'clients' in client_data:
                residences = client_data['clients']
            elif isinstance(client_data, dict) and 'data' in client_data:
                residences = client_data['data']
            else:
                # Use default Residence list
                residences = [
                    "Residence A", "Residence B", "Residence C", "Residence D", "Residence E",
                    "Residence F", "Residence G", "Residence H", "Residence I", "Residence J"
                ]

            # Extract Residence information
            residence_status = []
            for residence in residences:
                residence_name = None
                preferred_name = None
                wing_name = None
                
                if isinstance(residence, dict):
                    # Use actual client data fields
                    first_name = residence.get('FirstName', '')
                    surname = residence.get('Surname', '')
                    last_name = residence.get('LastName', '')
                    preferred_name = residence.get('PreferredName', '')
                    wing_name = residence.get('WingName', '')
                    
                    # Use FirstName + Surname combination for Residence Name
                    if first_name and surname:
                        residence_name = f"{first_name} {surname}"
                    elif first_name and last_name:
                        residence_name = f"{first_name} {last_name}"
                    elif first_name:
                        residence_name = first_name
                    else:
                        residence_name = ''
                    
                    # Fallback using ID
                    if not residence_name and 'PersonId' in residence:
                        residence_name = f"Client_{residence['PersonId']}"
                    elif not residence_name and 'id' in residence:
                        residence_name = f"Client_{residence['id']}"
                        
                elif isinstance(residence, str):
                    residence_name = residence
                
                if residence_name:
                    # Add MainClientServiceId field
                    main_client_service_id = residence.get('MainClientServiceId') or residence.get('ClientServiceId') or residence.get('Id')
                    
                    residence_status.append({
                        'residence_name': residence_name,
                        'preferred_name': preferred_name or '',
                        'wing_name': wing_name or '',
                        'MainClientServiceId': main_client_service_id,  # Add ID for matching
                        'rn_en_has_note': False,
                        'pca_has_note': False,
                        'rn_en_authors': [],
                        'pca_authors': []
                    })

            return jsonify({
                'success': True,
                'site': site,
                'residence_status': residence_status,
                'total_residences': len(residence_status)
            })

        except Exception as e:
            logger.error(f"Error fetching residence list for site {site}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Error fetching ROD residence list: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/rod-stats', methods=['POST'])
@login_required
def get_rod_stats():
    """Return ROD-only statistics information"""
    try:
        # Only ROD users can access
        if current_user.username.upper() not in ['ROD', 'YKROD', 'PGROD', 'WPROD', 'RSROD', 'NROD']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site', 'Parafield Gardens')
        
        # Logic to get actual statistics data (currently mock data)
        stats = {
            'totalNotes': 0,
            'todayNotes': 0,
            'activeUsers': 0,
            'systemStatus': '🟢'
        }
        
        try:
            # Get progress note count
            from api_progressnote_fetch import fetch_progress_notes_for_site
            success, progress_notes, _ = fetch_progress_notes_for_site(site, 30)  # 30 days
            
            if success and progress_notes:
                stats['totalNotes'] = len(progress_notes)
                
                # Calculate note count for today's date
                today = get_australian_time().date()
                today_notes = [note for note in progress_notes 
                             if note.get('EventDate') and 
                             datetime.fromisoformat(note['EventDate'].replace('Z', '+00:00')).date() == today]
                stats['todayNotes'] = len(today_notes)
            
            # Active user count (mock data)
            stats['activeUsers'] = len([user for user in ['admin', 'PaulVaska', 'walgampola', 'ROD'] 
                                      if user != current_user.username])
            
        except Exception as e:
            logger.error(f"Error fetching statistics data: {str(e)}")
            # Return default statistics even on error
            stats['totalNotes'] = 0
            stats['todayNotes'] = 0
            stats['activeUsers'] = 1
            stats['systemStatus'] = '🟡'
        
        return jsonify({
            'success': True,
            'stats': stats,
            'site': site,
            'timestamp': get_australian_time().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching ROD stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/user-info')
@login_required
def get_user_info():
    """Return currently logged-in user information"""
    try:
        user_info = {
            'username': current_user.username,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'role': current_user.role,
            'position': current_user.position,
            'site': session.get('site')
        }
        return jsonify(user_info)
    except Exception as e:
        logger.error(f"Error fetching user info: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/refresh-session', methods=['POST'])
@login_required
def refresh_session():
    """Refresh current session - reload user information"""
    try:
        username = current_user.username
        if not username:
            return jsonify({'success': False, 'message': 'No username in session'}), 400
            
        # Get user information again
        user_data = get_user(username)
        if not user_data:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        # Create new User object and refresh login
        user = User(username, user_data)
        user_role = user_data.get('role', 'USER').upper()
        
        # Set ADMIN users to remember=True to maintain session
        if user_role == 'ADMIN':
            login_user(user, remember=True)  # ADMIN: Maintain session even when browser closes
            session.permanent = True
            logger.info("Admin session refresh: remember=True, session.permanent=True")
        else:
            login_user(user, remember=False)  # Regular users: Session expires when browser closes
            session.permanent = False
            logger.info("Regular user session refresh: remember=False, session.permanent=False")
        
        # Set session timeout according to user role
        set_session_permanent(user_role)
        
        # Save user role to session
        session['user_role'] = user_role
        
        logger.info(f"Session refresh completed: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Session refreshed successfully',
            'user_info': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'position': user.position
            }
        })
    except Exception as e:
        logger.error(f"Error refreshing session: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/session-status')
@login_required
def get_session_status():
    """Check session status"""
    try:
        # Apply same session timeout to all users
        session_lifetime = timedelta(minutes=10)
        session_created = session.get('_created', get_australian_time())
        
        if isinstance(session_created, str):
            session_created = datetime.fromisoformat(session_created)
        
        session_expires = session_created + session_lifetime
        now = get_australian_time()
        
        # Calculate remaining time (in seconds)
        remaining_seconds = (session_expires - now).total_seconds()
        
        return jsonify({
            'success': True,
            'session_created': session_created.isoformat(),
            'session_expires': session_expires.isoformat(),
            'remaining_seconds': max(0, int(remaining_seconds)),
            'is_expired': remaining_seconds <= 0
        })
    except Exception as e:
        logger.error(f"Error checking session status: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/extend-session', methods=['POST'])
@login_required
def extend_session():
    """Extend session"""
    try:
        # Apply same session extension to all users
        session['_created'] = get_australian_time().isoformat()
        
        # Refresh Flask-Login session (direct session refresh to prevent recursion)
        session.permanent = True
        session.modified = True
        
        logger.info(f"Session extended: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Session extended successfully',
            'session_created': session['_created']
        })
    except Exception as e:
        logger.error(f"Error extending session: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/fetch-progress-notes', methods=['POST'])
@login_required
def fetch_progress_notes():
    """프로그레스 노트를 사이트에서 가져오기. days from request; default = DEFAULT_PERIOD_DAYS (matches frontend PERIOD_OPTIONS)."""
    try:
        data = request.get_json()
        site = data.get('site')
        days = int(data.get('days', DEFAULT_PERIOD_DAYS))
        page = data.get('page', 1)  # 페이지 번호
        per_page = data.get('per_page', 50)  # 페이지당 항목 수
        force_refresh = data.get('force_refresh', False)  # 강제 새로고침
        event_types = data.get('event_types', [])  # 이벤트 타입 필터
        year = data.get('year')  # 년도
        month = data.get('month')  # 월
        client_service_id = data.get('client_service_id')  # 클라이언트 서비스 ID 필터

        
        if not site:
            logger.error("Site parameter is missing in request")
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"Progress notes fetch request - site: {site}, days: {days}, page: {page}, per_page: {per_page}")
        logger.info(f"Request data: {data}")
        if client_service_id:
            logger.info(f"🔍 [FILTER] Client filter applied: client_service_id={client_service_id} (type: {type(client_service_id)})")
        else:
            logger.info("🔍 [FILTER] No client filter - fetching all clients")
        
        # Check site server configuration
        safe_site_servers = get_safe_site_servers()
        if site not in safe_site_servers:
            logger.error(f"Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}")
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}'
            }), 400
        
        # Check DB direct access mode
        use_db_direct = False
        try:
            conn = sqlite3.connect('progress_report.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                use_db_direct = result[0].lower() == 'true'
            else:
                use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        except:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
        from api_progressnote_fetch import fetch_progress_notes_for_site
        
        # Server pagination: page and per_page (default 50). Used in filter mode for performance.
        req_page = max(1, int(data.get('page', 1)))
        req_per_page = min(500, max(1, int(data.get('per_page', 50))))
        offset = (req_page - 1) * req_per_page
        
        # Fetch Progress Notes (DB direct access or API)
        if use_db_direct:
            logger.info(f"🔌 Direct DB access mode: Progress Notes fetched in real time (no cache) - {site}, page={req_page}, per_page={req_per_page}")
            # Server-side pagination: one page per request
            success, notes, total_count = fetch_progress_notes_for_site(
                site, days,
                event_types=event_types, year=year, month=month,
                client_service_id=client_service_id,
                limit=req_per_page, offset=offset, return_total=True
            )
            logger.info(f"🔍 [FILTER] fetch_progress_notes_for_site result - success={success}, notes_count={len(notes) if notes else 0}, total_count={total_count}")
        else:
            logger.info(f"🌐 API mode: Fetching Progress Notes - {site}")
            # API mode: no server pagination; fetch with limit, return one page by slicing
            fetch_limit = min(100000, max(req_per_page, 5000))
            success, notes, _ = fetch_progress_notes_for_site(
                site, days,
                event_types=event_types, year=year, month=month,
                client_service_id=client_service_id, limit=fetch_limit
            )
            total_count = len(notes) if notes else 0
            if success and notes:
                start_idx = (req_page - 1) * req_per_page
                notes = list(notes)[start_idx:start_idx + req_per_page]
                # Cache is not updated per-page in API mode to avoid partial cache
            logger.info(f"🔍 [FILTER] fetch_progress_notes_for_site result - success={success}, notes_count={len(notes) if notes else 0}")
        
        if not success:
            result = {
                'success': False,
                'notes': [],
                'page': req_page,
                'per_page': req_per_page,
                'total_count': 0,
                'total_pages': 0,
                'cache_status': 'no_data',
                'last_sync': None,
                'cache_age_hours': 0
            }
        else:
            notes_out = list(notes) if notes else []
            total_count = total_count if total_count is not None else len(notes_out)
            total_pages = max(1, (total_count + req_per_page - 1) // req_per_page) if total_count else 0
            result = {
                'success': True,
                'notes': notes_out,
                'page': req_page,
                'per_page': req_per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'cache_status': 'fresh_db_data' if use_db_direct else 'fresh_api_data',
                'last_sync': get_australian_time().isoformat(),
                'cache_age_hours': 0
            }
        
        # Build response data
        response_data = {
            'success': result['success'],
            'data': result['notes'],
            'pagination': {
                'page': result['page'],
                'per_page': result['per_page'],
                'total_count': result['total_count'],
                'total_pages': result['total_pages']
            },
            'cache_info': {
                'status': result['cache_status'],
                'last_sync': result['last_sync'],
                'cache_age_hours': result.get('cache_age_hours', 0)
            },
            'site': site,
            'count': result['total_count'],
            'fetched_at': get_australian_time().isoformat()
        }
        
        # Check if ROD dashboard request (when year, month are provided and event_types is None or empty array)
        if year is not None and month is not None and (not event_types or len(event_types) == 0):
            logger.info(f"ROD Dashboard request detected for {site} - {year}/{month}")
            from api_progressnote_fetch import fetch_residence_of_day_notes_with_client_data
            
            # Use ROD logic with real-time client data
            residence_status = fetch_residence_of_day_notes_with_client_data(site, year, month)
            
            if residence_status and 'residence_status' in residence_status:
                residence_data = residence_status['residence_status']
                logger.info(f"ROD data fetched successfully for {site}: {len(residence_data)} residences")
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched ROD data for {len(residence_data)} residences',
                    'data': residence_data,
                    'site': site,
                    'count': len(residence_data),
                    'fetched_at': get_australian_time().isoformat()
                })
            else:
                logger.warning(f"No ROD data found for {site}")
                return jsonify({
                    'success': True,
                    'message': 'No ROD data found',
                    'data': {},
                    'site': site,
                    'count': 0,
                    'fetched_at': get_australian_time().isoformat()
                })
        else:
            # Regular Progress Notes request
            logger.info(f"Regular Progress Notes request for {site}")
            logger.info(
                f"Progress notes fetch succeeded - {site}: {result['total_count']} items (page {page}/{result['total_pages']})"
            )
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Error fetching progress notes: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/fetch-progress-notes-incremental', methods=['POST'])
@login_required
def fetch_progress_notes_incremental():
    """Incremental update API - always returns 7 days of data (simplified)"""
    try:
        data = request.get_json()
        site = data.get('site')
        
        if not site:
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"Incremental update request (simplified) - site: {site}, always returning 7 days of data")
        
        try:
            from api_progressnote_fetch import fetch_progress_notes_for_site
            
            # Always fetch 7 days of data
            success, progress_notes, _ = fetch_progress_notes_for_site(site, 7)
            
            if success:
                logger.info(
                    f"Incremental update succeeded (simplified) - {site}: {len(progress_notes) if progress_notes else 0} items"
                )
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched {len(progress_notes) if progress_notes else 0} progress notes (1 week)',
                    'data': progress_notes,
                    'site': site,
                    'count': len(progress_notes) if progress_notes else 0,
                    'fetched_at': get_australian_time().isoformat()
                })
            else:
                logger.error(f"Incremental update failed (simplified) - {site}")
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch progress notes from server'
                }), 500
                
        except ImportError as e:
            logger.error(f"API module import error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Progress note fetch module not available'
            }), 500
            
    except Exception as e:
        logger.error(f"Error during incremental update: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/progress-notes-db-info')
@login_required
def get_progress_notes_db_info():
    """Query IndexedDB information (called from client)"""
    try:
        # Guide client to query IndexedDB information
        return jsonify({
            'success': True,
            'message': 'Use client-side IndexedDB API to get database info',
            'endpoints': {
                'fetch_notes': '/api/fetch-progress-notes',
                'fetch_incremental': '/api/fetch-progress-notes-incremental'
            }
        })
    except Exception as e:
        logger.error(f"Error retrieving database info: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/data/<filename>')
def serve_data_file(filename):
    """Serve JSON files from data directory"""
    # Allowed file extensions
    allowed_extensions = {'.json'}
    
    # Check file extension
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return jsonify({'error': 'Invalid file type'}), 400
    
    data_dir = os.path.join(app.root_path, 'data')
    file_path = os.path.join(data_dir, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_from_directory(data_dir, filename)

@app.route('/incident-viewer')
@login_required
def incident_viewer():
    """Incident Viewer page"""
    # Allow access only to admin and site admin
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # Get site parameter (use first registered site as default)
    safe_site_servers = get_safe_site_servers()
    default_site = list(safe_site_servers.keys())[0] if safe_site_servers else 'Parafield Gardens'
    site = request.args.get('site', default_site)
    
    # Create site list
    sites = []
    for site_name, server_info in safe_site_servers.items():
        sites.append({
            'name': site_name,
            'server': server_info,
            'is_selected': site_name == site
        })
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('IncidentViewer.html', 
                         site=site, 
                         sites=sites,
                         current_user=current_user)

@app.route('/log-viewer')
@login_required
def log_viewer():
    """Log viewer page"""
    # Allow access only to admin
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('LogViewer.html')

@app.route('/usage-log-viewer')
@login_required
def usage_log_viewer():
    """User activity log viewer page"""
    # Allow access only to admin
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('UsageLogViewer.html')

@app.route('/log_viewer/progress_notes')
@login_required
def progress_note_logs_viewer():
    """Progress Note Logs viewer page"""
    # Allow access only to admin
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # Get date from URL parameter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('ProgressNoteLogsViewer.html', start_date=start_date, end_date=end_date)

@app.route('/api/logs/summary')
@login_required
def get_log_summary():
    """Return log summary information"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_type = request.args.get('type', 'access')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        summary = usage_logger.get_log_summary(start_date, end_date, log_type)
        
        if summary:
            return jsonify({
                'success': True,
                'summary': summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get log summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting log summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/fetch-incidents', methods=['POST'])
@login_required
def fetch_incidents():
    """Fetch Incident data from site"""
    try:
        # Allow access only to admin and site admin
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not site or not start_date or not end_date:
            return jsonify({'success': False, 'message': 'Site, start_date, and end_date are required'}), 400
        
        logger.info(f"Fetching incidents for {site} from {start_date} to {end_date}")
        
        # Check site server configuration
        safe_site_servers = get_safe_site_servers()
        if site not in safe_site_servers:
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}'
            }), 400
        
        server_ip = safe_site_servers[site]
        logger.info(f"Target server for {site}: {server_ip}")
        
        try:
            # Fetch Incident data and client data (DB direct access)
            from manad_db_connector import fetch_incidents_with_client_data_from_db
            
            logger.info(f"🔌 Direct DB access mode: {site}")
            incidents_data = fetch_incidents_with_client_data_from_db(site, start_date, end_date, fetch_clients=True)
            
            if incidents_data:
                logger.info(f"Incidents fetched successfully for {site}: {len(incidents_data.get('incidents', []))} incidents, {len(incidents_data.get('clients', []))} clients")
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched {len(incidents_data.get("incidents", []))} incidents',
                    'data': incidents_data,
                    'site': site,
                    'count': len(incidents_data.get('incidents', [])),
                    'fetched_at': get_australian_time().isoformat()
                })
            else:
                logger.warning(f"No incidents found for {site}")
                return jsonify({
                    'success': True,
                    'message': 'No incidents found',
                    'data': {'incidents': [], 'clients': []},
                    'site': site,
                    'count': 0,
                    'fetched_at': get_australian_time().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error fetching incidents for {site}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error fetching incidents: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in fetch_incidents: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/access-hourly-summary')
@login_required
def get_access_hourly_summary():
    """Return hourly user activity summary from access log"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        hourly_summary = usage_logger.get_access_log_hourly_summary(start_date, end_date)
        
        if hourly_summary:
            return jsonify({
                'success': True,
                'summary': hourly_summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get access hourly summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting access hourly summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/daily-access-summary')
@login_required
def get_daily_access_summary():
    """Daily access status summary"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        daily_summary = usage_logger.get_daily_access_summary(start_date, end_date)
        
        if daily_summary:
            return jsonify({
                'success': True,
                'summary': daily_summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get daily access summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting daily access summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/user-daily-activity')
@login_required
def get_user_daily_activity():
    """Daily access status for specific user"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        username = request.args.get('username')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not username:
            return jsonify({'success': False, 'message': 'Username is required'}), 400
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        user_activity = usage_logger.get_user_daily_activity(username, start_date, end_date)
        
        if user_activity:
            return jsonify({
                'success': True,
                'activity': user_activity
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get user daily activity'
            })
            
    except Exception as e:
        logger.error(f"Error getting user daily activity: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/date-user-activity')
@login_required
def get_date_user_activity():
    """Access time and usage time per user for specific date"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'message': 'Date is required'}), 400
        
        target_date = datetime.fromisoformat(date_str)
        date_activity = usage_logger.get_date_user_activity(target_date)
        
        if date_activity:
            return jsonify({
                'success': True,
                'activity': date_activity
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get date user activity'
            })
            
    except Exception as e:
        logger.error(f"Error getting date user activity: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/log-rod-debug', methods=['POST'])
@login_required
def log_rod_debug():
    """Log ROD debug information to file instead of console"""
    try:
        debug_data = request.get_json()
        if not debug_data:
            return jsonify({'success': False, 'message': 'No debug data provided'})
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = get_australian_time().strftime('%Y-%m-%d_%H%M%S')
        filename = f'rod_debug_{timestamp}.json'
        filepath = os.path.join(logs_dir, filename)
        
        # Add server timestamp and user info
        debug_data['server_timestamp'] = get_australian_time().isoformat()
        debug_data['user'] = current_user.username if current_user.is_authenticated else 'Unknown'
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"ROD debug log saved to: {filepath}")
        return jsonify({'success': True, 'message': 'Debug log saved'})
        
    except Exception as e:
        logger.error(f"Error saving ROD debug log: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/logs/details')
@login_required
def get_log_details():
    """Return log details"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_type = request.args.get('type', 'progress_notes')
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'message': 'Date parameter is required'}), 400
        
        # Log file path for that date
        log_file = usage_logger.get_daily_log_file(log_type, datetime.fromisoformat(date_str))
        
        if not log_file.exists():
            return jsonify({'success': False, 'message': 'No logs found for this date'}), 404
        
        # Read log file
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        # Include details for progress_notes logs
        if log_type == 'progress_notes':
            for log_entry in logs:
                # Add style class based on success/failure status
                success = log_entry.get('result', {}).get('success', True)
                log_entry['status_class'] = 'success' if success else 'error'
                log_entry['status_text'] = 'Success' if success else 'Failed'
                
                # Convert timestamp to readable format
                timestamp = log_entry.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        log_entry['formatted_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        log_entry['formatted_time'] = timestamp
        
        return jsonify({
            'success': True,
            'logs': logs,
            'date': date_str,
            'type': log_type
        })
        
    except Exception as e:
        logger.error(f"Error getting log details: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/app-log')
@login_required
def get_app_log():
    """Query app.log file contents (for production server)"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'app.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'app.log file not found'}), 404
        
        # Read only recent 1000 lines (performance optimization)
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve app.log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logs/error-log')
@login_required
def get_error_log():
    """Query error.log file contents (for production server)"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'error.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'error.log file not found'}), 404
        
        # Read only recent 500 lines
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve error.log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logs/access-log')
@login_required
def get_access_log():
    """Query access.log file contents (for production server)"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'access.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'access.log file not found'}), 404
        
        # Read only recent 500 lines
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve access.log: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs')
@login_required
def get_usage_logs():
    """Return user activity log analysis data"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Collect log files from UsageLog directory
        usage_log_dir = "UsageLog"
        if not os.path.exists(usage_log_dir):
            return jsonify({'success': True, 'logs': [], 'summary': {}})
        
        all_logs = []
        login_sessions = {}  # Track login sessions per user
        
        # Read all JSON log files
        for root, dirs, files in os.walk(usage_log_dir):
            for filename in files:
                if filename.endswith('.json'):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            logs = json.load(f)
                            
                        # Date filtering
                        if start_date or end_date:
                            filtered_logs = []
                            for log in logs:
                                log_date = log.get('timestamp', '').split('T')[0]
                                if start_date and log_date < start_date:
                                    continue
                                if end_date and log_date > end_date:
                                    continue
                                filtered_logs.append(log)
                            logs = filtered_logs
                        
                        all_logs.extend(logs)
                    except Exception as e:
                        logger.error(f"Failed to read log file {filepath}: {str(e)}")
                        continue
        
        # Sort by time
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # Analyze login/logout sessions
        for log in all_logs:
            username = log.get('user', {}).get('username', 'Unknown')
            timestamp = log.get('timestamp', '')
            page = log.get('page', {}).get('path', '')
            
            if username not in login_sessions:
                login_sessions[username] = []
            
            # Detect login (access to home page or login page)
            if page in ['/', '/login'] or 'login' in page.lower():
                login_sessions[username].append({
                    'type': 'login',
                    'timestamp': timestamp,
                    'page': page
                })
            
            # Detect logout
            if page == '/logout':
                login_sessions[username].append({
                    'type': 'logout',
                    'timestamp': timestamp,
                    'page': page
                })
        
        # Summary statistics
        summary = {
            'total_logs': len(all_logs),
            'unique_users': len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs)),
            'date_range': {
                'start': all_logs[0].get('timestamp', '').split('T')[0] if all_logs else None,
                'end': all_logs[-1].get('timestamp', '').split('T')[0] if all_logs else None
            },
            'login_sessions': login_sessions
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs[-1000:],  # Return only recent 1000
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve user activity logs: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/months')
@login_required
def get_usage_log_months():
    """Return available month list"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        months = set()
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        # Extract month information from filename (e.g., access_2025-09-26.json)
                        if 'access_' in filename:
                            try:
                                date_part = filename.replace('access_', '').replace('.json', '')
                                year_month = '-'.join(date_part.split('-')[:2])  # YYYY-MM
                                months.add(year_month)
                            except:
                                continue
        
        return jsonify({
            'success': True,
            'months': sorted(list(months), reverse=True)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve month list: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/month/<month>')
@login_required
def get_usage_logs_by_month(month):
    """Return user activity logs for specific month"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        all_logs = []
        days = set()
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json') and month in filename:
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                            
                            for log in logs:
                                timestamp = log.get('timestamp', '')
                                if timestamp:
                                    log_date = timestamp.split('T')[0]
                                    if log_date.startswith(month):
                                        all_logs.append(log)
                                        day = log_date.split('-')[2]  # Extract day
                                        days.add(day)
                        except Exception as e:
                            logger.error(f"Failed to read log file {filepath}: {str(e)}")
                            continue
        
        # Sort by time
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # Calculate statistics
        unique_users = len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs))
        active_days = len(days)
        avg_daily_access = len(all_logs) / active_days if active_days > 0 else 0
        
        stats = {
            'totalAccess': len(all_logs),
            'uniqueUsers': unique_users,
            'activeDays': active_days,
            'avgDailyAccess': avg_daily_access
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs,
            'stats': stats,
            'days': sorted(list(days), reverse=True)
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve monthly logs: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/all')
@login_required
def get_all_usage_logs():
    """Return all user activity logs"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        all_logs = []
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                                all_logs.extend(logs)
                        except Exception as e:
                            logger.error(f"Failed to read log file {filepath}: {str(e)}")
                            continue
        
        # Sort by time
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # Calculate statistics
        unique_users = len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs))
        
        stats = {
            'totalAccess': len(all_logs),
            'uniqueUsers': unique_users,
            'activeDays': 0,
            'avgDailyAccess': 0
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs[-2000:],  # Return only recent 2000
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve all logs: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/monthly-stats')
@login_required
def get_monthly_usage_stats():
    """Return monthly statistics"""
    try:
        # Allow access only to admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        monthly_stats = {}
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                            
                            for log in logs:
                                timestamp = log.get('timestamp', '')
                                if timestamp:
                                    log_date = timestamp.split('T')[0]
                                    year_month = '-'.join(log_date.split('-')[:2])
                                    
                                    if year_month not in monthly_stats:
                                        monthly_stats[year_month] = 0
                                    monthly_stats[year_month] += 1
                        except Exception as e:
                            logger.error(f"Failed to read log file {filepath}: {str(e)}")
                            continue
        
        # Convert monthly statistics to list
        monthly_list = [{'month': month, 'totalAccess': count} for month, count in monthly_stats.items()]
        monthly_list.sort(key=lambda x: x['month'], reverse=True)
        
        return jsonify({
            'success': True,
            'monthlyStats': monthly_list
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve monthly stats: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/send-alarm', methods=['POST'])
@login_required
def send_alarm():
    """API to send alarm to mobile app"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['incident_id', 'event_type', 'client_name', 'site', 'risk_rating']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Get alarm manager
        alarm_manager = get_alarm_manager()
        
        # Send alarm
        result = alarm_manager.send_alarm(
            incident_id=data['incident_id'],
            event_type=data['event_type'],
            client_name=data['client_name'],
            site=data['site'],
            risk_rating=data['risk_rating'],
            template_id=data.get('template_id'),
            custom_message=data.get('custom_message'),
            custom_recipients=data.get('custom_recipients'),
            priority=data.get('priority', 'normal')
        )
        
        if result['success']:
            logger.info(f"Advanced alarm sent successfully: {result['alarm_id']} by {current_user.username}")
            return jsonify(result)
        else:
            logger.error(f"Failed to send advanced alarm: {result['error']}")
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error sending alarm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending alarm: {str(e)}'
        }), 500

@app.route('/api/alarm-history')
@login_required
def get_alarm_history():
    """API to return alarm send history"""
    try:
        # Alarm log file path
        logs_dir = os.path.join(os.getcwd(), 'logs')
        alarm_log_file = os.path.join(logs_dir, 'alarm_logs.json')
        
        if not os.path.exists(alarm_log_file):
            return jsonify({
                'success': True,
                'alarms': []
            })
        
        # Read alarm log
        with open(alarm_log_file, 'r', encoding='utf-8') as f:
            alarm_logs = json.load(f)
        
        # Return only recent 20 alarms (newest first)
        recent_alarms = sorted(alarm_logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:20]
        
        return jsonify({
            'success': True,
            'alarms': recent_alarms
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm history: {str(e)}'
        }), 500

# ==============================
# Advanced alarm management API endpoints
# ==============================

@app.route('/api/alarm-templates', methods=['GET'])
@login_required
def get_alarm_templates():
    """API to return alarm template list (SQLite based)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin privileges are required.'
            }), 403
        
        # Query actual data from SQLite
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT template_id, name, description, title_template, body_template, 
                   priority, category, created_at
            FROM alarm_templates 
            WHERE is_active = 1
            ORDER BY priority DESC, name
        ''')
        
        templates = []
        for row in cursor.fetchall():
            templates.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'title_template': row[3],
                'body_template': row[4],
                'priority': row[5],
                'category': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Error retrieving alarm templates: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while retrieving templates: {str(e)}'
        }), 500

@app.route('/api/alarm-templates', methods=['POST'])
@login_required
def create_alarm_template():
    """API to create new alarm template"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required_fields = ['name', 'title', 'body', 'priority', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        template_service, _, _ = get_alarm_services()
        template = template_service.create_template(data)
        
        return jsonify({
            'success': True,
            'template': asdict(template),
            'message': 'Template created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating alarm template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating alarm template: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients', methods=['GET'])
@login_required
def get_alarm_recipients():
    """API to return alarm recipient list (SQLite based)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin privileges are required.'
            }), 403
        
        # Query actual data from SQLite
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ar.user_id, ar.name, ar.email, ar.phone, ar.role, ar.team, ar.created_at,
                   u.username, u.is_active as user_active
            FROM alarm_recipients ar
            LEFT JOIN users u ON ar.user_id = u.id
            WHERE ar.is_active = 1
            ORDER BY ar.team, ar.name
        ''')
        
        recipients = []
        for row in cursor.fetchall():
            recipients.append({
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'role': row[4],
                'team': row[5],
                'created_at': row[6],
                'username': row[7],
                'user_active': row[8]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'recipients': recipients
        })
        
    except Exception as e:
        logger.error(f"Error retrieving alarm recipients: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while retrieving recipients: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients', methods=['POST'])
@login_required
def add_alarm_recipient():
    """API to add new alarm recipient"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required_fields = ['user_id', 'name', 'email', 'phone', 'role', 'team']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        _, recipient_service, _ = get_alarm_services()
        recipient = recipient_service.add_recipient(data)
        
        return jsonify({
            'success': True,
            'recipient': asdict(recipient),
            'message': 'Recipient added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding alarm recipient: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error adding alarm recipient: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients/<user_id>/fcm-token', methods=['PUT'])
@login_required
def update_fcm_token(user_id):
    """API to update user's FCM token"""
    try:
        data = request.get_json()
        
        if not data or 'fcm_token' not in data:
            return jsonify({'success': False, 'message': 'FCM token is required'}), 400
        
        _, recipient_service, _ = get_alarm_services()
        success = recipient_service.update_fcm_token(user_id, data['fcm_token'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'FCM token updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
    except Exception as e:
        logger.error(f"Error updating FCM token: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating FCM token: {str(e)}'
        }), 500

@app.route('/api/alarms/<alarm_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alarm(alarm_id):
    """API to acknowledge alarm"""
    try:
        data = request.get_json()
        user_id = data.get('user_id') if data else None
        
        if not user_id:
            user_id = current_user.username if current_user.is_authenticated else 'Unknown'
        
        alarm_manager = get_alarm_manager()
        result = alarm_manager.acknowledge_alarm(alarm_id, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error acknowledging alarm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error acknowledging alarm: {str(e)}'
        }), 500

@app.route('/api/alarms/escalations', methods=['GET'])
@login_required
def get_pending_escalations():
    """API to return pending escalation list"""
    try:
        alarm_manager = get_alarm_manager()
        pending_count = alarm_manager.get_pending_escalations_count()
        
        return jsonify({
            'success': True,
            'pending_escalations_count': pending_count
        })
        
    except Exception as e:
        logger.error(f"Error getting pending escalations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting pending escalations: {str(e)}'
        }), 500

@app.route('/api/alarms/<alarm_id>/escalations', methods=['GET'])
@login_required
def get_alarm_escalations(alarm_id):
    """API to return escalation information for specific alarm"""
    try:
        _, _, escalation_service = get_alarm_services()
        escalations = escalation_service.get_escalations_for_alarm(alarm_id)
        
        # Convert datetime objects to strings
        for escalation in escalations:
            escalation.created_at = escalation.created_at.isoformat()
            if escalation.sent_at:
                escalation.sent_at = escalation.sent_at.isoformat()
            if escalation.acknowledged_at:
                escalation.acknowledged_at = escalation.acknowledged_at.isoformat()
        
        return jsonify({
            'success': True,
            'escalations': [asdict(escalation) for escalation in escalations]
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm escalations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm escalations: {str(e)}'
        }), 500

# Add data folder cleanup function after login success
def cleanup_data_folder():
    """Clean up progress note related JSON files in data folder on login."""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        if os.path.exists(data_dir):
            # Find only progress note related files among JSON files (preserve client data)
            all_json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
            
            # Files to preserve (client data)
            preserve_files = [
                'Client_list.json',
                'carearea.json', 
                'eventtype.json'
            ]
            
            # Also preserve site-specific client files
            safe_site_servers = get_safe_site_servers()
            for site in safe_site_servers.keys():
                site_name = site.replace(' ', '_').lower()
                preserve_files.append(f"{site_name}_client.json")
            
            # Files to delete (progress note related)
            files_to_delete = []
            for json_file in all_json_files:
                if json_file not in preserve_files and not json_file.startswith('prepare_send'):
                    files_to_delete.append(json_file)
            
            if files_to_delete:
                logger.info(
                    f"Starting data folder cleanup - deleting {len(files_to_delete)} progress note JSON files"
                )
                logger.info(f"Files to preserve: {preserve_files}")
                logger.info(f"Files to delete: {files_to_delete}")
                
                # Directly delete progress note related JSON files
                deleted_count = 0
                for json_file in files_to_delete:
                    try:
                        file_path = os.path.join(data_dir, json_file)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted progress note JSON file: {json_file}")
                    except Exception as e:
                        logger.error(f"Failed to delete progress note JSON file {json_file}: {str(e)}")
                
                logger.info(
                    f"Data folder cleanup completed - deleted {deleted_count}/{len(files_to_delete)} progress note files"
                )
                return True
            else:
                logger.info("No progress note JSON files to delete")
                return True
        else:
            logger.warning("Data folder does not exist")
            return False
            
    except Exception as e:
        logger.error(f"Error during data folder cleanup: {str(e)}")
        return False

# ==============================
# FCM (Firebase Cloud Messaging) API endpoints
# ==============================

@app.route('/api/fcm/register-token', methods=['POST'])
def register_fcm_token():
    """API to register FCM token"""
    try:
        logger.info(
            f"FCM token registration request - user: {current_user.username if current_user.is_authenticated else 'Anonymous'}"
        )
        logger.info(f"Request headers: {dict(request.headers)}")
        
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        # Mobile app compatible: support both 'token' and 'fcm_token' fields
        token = data.get('token') or data.get('fcm_token')
        
        if not data or not token:
            logger.error("FCM token registration failed: missing token data")
            return jsonify({
                'success': False,
                'message': 'Token or fcm_token is required.'
            }), 400
        
        # Process device_info (support both string and object)
        device_info_raw = data.get('device_info', 'Unknown Device')
        if isinstance(device_info_raw, dict):
            # When mobile app sends as object
            platform = device_info_raw.get('platform', 'unknown')
            version = device_info_raw.get('version', '1.0.0')
            device_info = f"{platform.title()} App v{version}"
        else:
            device_info = str(device_info_raw)
        
        user_id = data.get('user_id', 'unknown_user')  # user_id provided from mobile app
        platform = data.get('platform', 'unknown')
        app_version = data.get('app_version', '1.0.0')
        
        logger.info(f"Attempting FCM token registration: user={user_id}, device={device_info}, token={token[:20]}...")
        
        # Register user's token
        token_manager = get_fcm_token_manager()
        logger.info(f"FCM token manager type: {type(token_manager)}")
        
        success = token_manager.register_token(user_id, token, device_info)
        logger.info(f"FCM token registration result: {success}")
        
        if success:
            logger.info(f"FCM token registration succeeded: {user_id}")
            return jsonify({
                'success': True,
                'message': 'FCM token registered successfully.',
                'user_id': user_id,
                'device_info': device_info,
                'platform': platform,
                'app_version': app_version
            })
        else:
            logger.error(f"FCM token registration failed: {user_id}")
            return jsonify({
                'success': False,
                'message': 'FCM token registration failed.'
            }), 500
            
    except Exception as e:
        logger.error(f"Exception during FCM token registration: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error occurred during token registration: {str(e)}'
        }), 500

@app.route('/api/fcm/unregister-token', methods=['POST'])
def unregister_fcm_token():
    """API to remove FCM token"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({
                'success': False,
                'message': 'Token is required.'
            }), 400
        
        token = data['token']
        user_id = data.get('user_id')  # user_id provided from mobile app (optional)
        
        logger.info(f"Attempting to unregister FCM token: user={user_id}, token={token[:20]}...")
        
        # Remove token (use with user_id if available, otherwise remove by token only)
        token_manager = get_fcm_token_manager()
        success = token_manager.unregister_token(user_id, token)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'FCM token deleted successfully.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'FCM token not found.'
            }), 404
            
    except Exception as e:
        logger.error(f"Error unregistering FCM token: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while removing the token: {str(e)}'
        }), 500

@app.route('/api/fcm/send-notification', methods=['POST'])
def send_fcm_notification():
    """API to send push notification via FCM"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required.'
            }), 400
        
        # Check required fields
        required_fields = ['title', 'body']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'{field} field is required.'
                }), 400
        
        title = data['title']
        body = data['body']
        user_ids = data.get('user_ids', [])  # Send only to specific users
        topic = data.get('topic')  # Send to topic
        custom_data = data.get('data', {})  # Additional data
        image_url = data.get('image_url')  # Image URL
        
        fcm_service = get_fcm_service()
        if fcm_service is None:
            return jsonify({
                'success': False,
                'message': 'Unable to initialize the FCM service. Please check your Firebase configuration.'
            }), 500
        
        token_manager = get_fcm_token_manager()
        
        if topic:
            # Send to topic
            result = fcm_service.send_topic_message(topic, title, body, custom_data)
        elif user_ids:
            # Send to specific users
            all_tokens = []
            for user_id in user_ids:
                user_tokens = token_manager.get_user_token_strings(user_id)
                all_tokens.extend(user_tokens)
            
            if all_tokens:
                result = fcm_service.send_notification_to_tokens(all_tokens, title, body, custom_data, image_url)
            else:
                return jsonify({
                    'success': False,
                    'message': 'No FCM tokens available to send.'
                }), 400
        else:
            # Send to all users
            all_tokens = token_manager.get_all_tokens()
            if all_tokens:
                result = fcm_service.send_notification_to_tokens(all_tokens, title, body, custom_data, image_url)
            else:
                return jsonify({
                    'success': False,
                    'message': 'No FCM tokens available to send.'
                }), 400
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Push notification sent successfully.',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send push notification: {result.get("error", "Unknown error")}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending FCM notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while sending the notification: {str(e)}'
        }), 500

@app.route('/api/fcm/tokens', methods=['GET'])
@login_required
def get_fcm_tokens():
    """API to return current user's FCM token information"""
    try:
        token_manager = get_fcm_token_manager()
        user_tokens = token_manager.get_user_tokens(current_user.id)
        
        tokens_data = [token.to_dict() for token in user_tokens]
        
        return jsonify({
            'success': True,
            'tokens': tokens_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching FCM tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while fetching tokens: {str(e)}'
        }), 500

@app.route('/api/fcm/stats', methods=['GET'])
@login_required
def get_fcm_stats():
    """API to return FCM token statistics (admin and site admin only)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin privileges are required.'
            }), 403
        
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching FCM stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while fetching stats: {str(e)}'
        }), 500

@app.route('/api/fcm/export-tokens', methods=['GET'])
@login_required
def export_fcm_tokens():
    """API to export token data from FCM token manager (admin and site admin only)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin permission required.'
            }), 403
        
        # Get statistics from FCM token manager
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        # Convert to format usable by Policy Management
        tokens_data = []
        for user_id, user_tokens in stats.get('user_tokens', {}).items():
            for token_info in user_tokens:
                tokens_data.append({
                    'user_id': user_id,
                    'token': token_info.get('token', ''),
                    'device_info': token_info.get('device_info', 'Unknown Device'),
                    'created_at': token_info.get('created_at', ''),
                    'last_used': token_info.get('last_used', ''),
                    'is_active': token_info.get('is_active', True)
                })
        
        logger.info(f"Exporting FCM tokens: {len(tokens_data)} tokens")
        
        return jsonify({
            'success': True,
            'tokens': tokens_data,
            'count': len(tokens_data)
        })
        
    except Exception as e:
        logger.error(f"Error exporting FCM tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while exporting tokens: {str(e)}'
        }), 500

@app.route('/api/active-users', methods=['GET'])
def get_active_users():
    """API to return currently logged-in users by site"""
    try:
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        # Group users by site
        site_users = {
            'Parafield Gardens': [],
            'Nerrilda': [],
            'Ramsay': [],
            'Yankalilla': []
        }
        
        # Process token information per user
        for user_id, user_tokens in stats.get('user_tokens', {}).items():
            active_tokens = [token for token in user_tokens if token.get('is_active', True)]
            
            if active_tokens:
                # Use most recently used token information
                latest_token = max(active_tokens, key=lambda x: x.get('last_used', ''))
                
                # Build user information
                user_info = {
                    'user_id': user_id,
                    'device_info': latest_token.get('device_info', 'Unknown Device'),
                    'last_used': latest_token.get('last_used', ''),
                    'created_at': latest_token.get('created_at', ''),
                    'token_count': len(active_tokens)
                }
                
                # Classify by site (estimated based on user ID or device information)
                # Actually should get site information from user table,
                # but currently simply classify by user ID pattern
                if 'pg' in user_id.lower() or 'parafield' in user_id.lower():
                    site_users['Parafield Gardens'].append(user_info)
                elif 'nerrilda' in user_id.lower():
                    site_users['Nerrilda'].append(user_info)
                elif 'ramsay' in user_id.lower():
                    site_users['Ramsay'].append(user_info)
                elif 'yankalilla' in user_id.lower():
                    site_users['Yankalilla'].append(user_info)
                else:
                    # Default to Parafield Gardens
                    site_users['Parafield Gardens'].append(user_info)
        
        # Calculate statistics per site
        site_stats = {}
        total_active_devices = 0
        for site, users in site_users.items():
            site_devices = sum(user['token_count'] for user in users)
            site_stats[site] = {
                'users': users,
                'total_users': len(users),
                'total_devices': site_devices
            }
            total_active_devices += site_devices
        
        return jsonify({
            'success': True,
            'site_users': site_stats,
            'total_active_users': sum(len(users) for users in site_users.values()),
            'total_active_devices': total_active_devices
        })
        
    except Exception as e:
        logger.error(f"Error fetching active users: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while fetching active users: {str(e)}'
        }), 500

@app.route('/api/fcm/cleanup', methods=['POST'])
@login_required
def cleanup_fcm_tokens():
    """API to clean up inactive FCM tokens (admin and site admin only)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin privileges are required.'
            }), 403
        
        data = request.get_json() or {}
        days_threshold = data.get('days_threshold', 30)
        
        token_manager = get_fcm_token_manager()
        cleanup_count = token_manager.cleanup_inactive_tokens(days_threshold)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {cleanup_count} inactive tokens.',
            'cleanup_count': cleanup_count
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up FCM tokens: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while cleaning up tokens: {str(e)}'
        }), 500

@app.route('/admin-settings')
@login_required
def admin_settings():
    """Admin Settings page (Admin only)"""
    # Check admin permissions
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": getattr(current_user, 'position', 'Unknown')
    }
    usage_logger.log_access(user_info, '/admin-settings')
    
    return render_template('admin_settings.html')

# ==============================
# User Management Routes
# ==============================

@app.route('/user-management')
@login_required
def user_management():
    """User management page (ADMIN only)"""
    # Check admin permissions
    if current_user.role != 'admin':
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": getattr(current_user, 'position', 'Unknown')
    }
    usage_logger.log_access(user_info, '/user-management')
    
    return render_template('user_management.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_all_users_api():
    """API to query all user list"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        from config_users import get_all_users
        users = get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"Failed to retrieve user list: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['GET'])
@login_required
def get_user_api(username):
    """API to query specific user information"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        user_data = get_user(username)
        if user_data:
            # Exclude password hash
            safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
            from config_users import get_username_by_lowercase
            actual_username = get_username_by_lowercase(username)
            safe_user['username'] = actual_username
            return jsonify({'success': True, 'user': safe_user})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Failed to retrieve user details: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
def add_user_api():
    """API to add new user"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        

        # Check required fields
        required_fields = ['username', 'password', 'first_name', 'last_name', 'role', 'position', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Validate user data (includes admin role check)
        is_valid, error_msg = validate_user_data(data)
        if not is_valid:
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Create user using user_management module
        success, message = create_new_user(data, USERS_DB)
        
        if success:
            logger.info(f"User created successfully: {data['username']} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['PUT'])
@login_required
def update_user_api(username):
    """API to update user information"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        from config_users import update_user
        success, message = update_user(
            username=username,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role=data.get('role'),
            position=data.get('position'),
            location=data.get('location'),
            password=data.get('password'),
            landing_page=data.get('landing_page')
        )
        
        if success:
            logger.info(f"User updated successfully: {username} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def delete_user_api(username):
    """API to delete user"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Cannot delete own account
        from config_users import get_username_by_lowercase
        actual_username = get_username_by_lowercase(username)
        if actual_username and actual_username.lower() == current_user.username.lower():
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        success, message = delete_user(username, USERS_DB)
        
        if success:
            logger.info(f"User deleted successfully: {username} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/options', methods=['GET'])
@login_required
def get_user_options_api():
    """API to query user options (role, position, location list)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        from config_users import get_unique_roles, get_unique_positions, get_unique_locations
        
        return jsonify({
            'success': True,
            'roles': get_unique_roles(),
            'positions': get_unique_positions(),
            'locations': get_unique_locations()
        })
    except Exception as e:
        logger.error(f"Failed to retrieve user options: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/fcm-admin-dashboard')
@login_required
def fcm_admin_dashboard():
    """FCM admin dashboard (ADMIN and SITE_ADMIN only)"""
    # Check admin and site admin permissions
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This dashboard is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('FCMAdminDashboard.html', current_user=current_user)



@app.route('/api/fcm/update-token', methods=['POST'])
@login_required
def update_fcm_token_info():
    """API to update FCM token information (field-based update)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required.'
            }), 400
        
        # Check required fields
        required_fields = ['token', 'field', 'value']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'{field} field is required.'
                }), 400
        
        token = data['token']
        field = data['field']
        value = data['value'].strip()
        
        # Check if value is not empty
        if not value:
            return jsonify({
                'success': False,
                'message': 'Value cannot be empty.'
            }), 400
        
        token_manager = get_fcm_token_manager()
        
        # Determine information to update based on field
        if field == 'user_id':
            success = token_manager.update_token_info(token, value, None)
        elif field == 'device_info':
            success = token_manager.update_token_info(token, None, value)
        elif field == 'token':
            # When changing token itself (replace with new token)
            success = token_manager.update_token_value(token, value)
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid field specified.'
            }), 400
        
        if success:
            logger.info(f"FCM token update successful: {token[:20]}... -> {field}: {value}")
            return jsonify({
                'success': True,
                'message': 'Token information updated successfully.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Token not found or cannot be updated.'
            }), 404
            
    except Exception as e:
        logger.error(f"FCM token update error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error occurred during token update: {str(e)}'
        }), 500

@app.route('/api/alarm-escalation-status', methods=['GET'])
@login_required
def get_alarm_escalation_status():
    """API to return alarm escalation status (SQLite based)"""
    try:
        # Check admin and site admin permissions
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin privileges are required.'
            }), 403
        
        # Query actual escalation policies from SQLite
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT policy_name, event_type, priority, is_active
            FROM escalation_policies
            ORDER BY priority DESC, event_type
        ''')
        
        policies = []
        status_summary = {
            'total_policies': 0,
            'active_policies': 0,
            'by_priority': {'high': 0, 'medium': 0, 'normal': 0},
            'by_type': {}
        }
        
        for row in cursor.fetchall():
            policy_name, event_type, priority, is_active = row
            
            policies.append({
                'name': policy_name,
                'event_type': event_type,
                'priority': priority,
                'is_active': is_active
            })
            
            status_summary['total_policies'] += 1
            if is_active:
                status_summary['active_policies'] += 1
                status_summary['by_priority'][priority] = status_summary['by_priority'].get(priority, 0) + 1
                status_summary['by_type'][event_type] = status_summary['by_type'].get(event_type, 0) + 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policies': policies,
            'status': status_summary
        })
        
    except Exception as e:
        logger.error(f"Error retrieving escalation status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while retrieving status: {str(e)}'
        }), 500



@app.route('/policy-management')
@login_required
def unified_policy_management():
    """Unified Policy & Recipients management page (ADMIN and SITE_ADMIN only)"""
    # Check admin and site admin permissions
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('UnifiedPolicyManagement.html', current_user=current_user)

# Redirect existing pages to new unified page
@app.route('/escalation-policy-management')
@login_required
def escalation_policy_management():
    """Escalation policy management page (redirects to unified page)"""
    return redirect(url_for('unified_policy_management'))

@app.route('/policy-alarm-management')
@login_required
def policy_alarm_management():
    """Policy & Alarm Management page (redirects to unified page)"""
    return redirect(url_for('unified_policy_management'))

@app.route('/api/escalation-policies', methods=['GET'])
@login_required
def get_escalation_policies():
    """Query escalation policy list (SQLite based)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # Query policy and step information together
        cursor.execute('''
            SELECT ep.id, ep.policy_name, ep.description, ep.event_type, ep.priority,
                   ep.is_active, ep.created_at,
                   COUNT(es.id) as step_count
            FROM escalation_policies ep
            LEFT JOIN escalation_steps es ON ep.id = es.policy_id AND es.is_active = 1
            WHERE ep.is_active = 1
            GROUP BY ep.id
            ORDER BY ep.priority DESC, ep.policy_name
        ''')
        
        policies = []
        for row in cursor.fetchall():
            policies.append({
                'id': row[0],
                'policy_name': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'is_active': row[5],
                'created_at': row[6],
                'step_count': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policies': policies
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch escalation policies: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['GET'])
@login_required
def get_escalation_policy_detail(policy_id):
    """Query specific escalation policy details"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # Policy basic information
        cursor.execute('''
            SELECT id, policy_name, description, event_type, priority, is_active, created_at
            FROM escalation_policies
            WHERE id = ? AND is_active = 1
        ''', (policy_id,))
        
        policy_row = cursor.fetchone()
        if not policy_row:
            return jsonify({'success': False, 'message': 'Policy not found.'}), 404
        
        policy = {
            'id': policy_row[0],
            'policy_name': policy_row[1],
            'description': policy_row[2],
            'event_type': policy_row[3],
            'priority': policy_row[4],
            'is_active': policy_row[5],
            'created_at': policy_row[6]
        }
        
        # Escalation step information
        cursor.execute('''
            SELECT step_number, delay_minutes, repeat_count, recipients, message_template
            FROM escalation_steps
            WHERE policy_id = ? AND is_active = 1
            ORDER BY step_number
        ''', (policy_id,))
        
        steps = []
        for row in cursor.fetchall():
            steps.append({
                'step_number': row[0],
                'delay_minutes': row[1],
                'repeat_count': row[2],
                'recipients': json.loads(row[3]) if row[3] else [],
                'message_template': row[4]
            })
        
        policy['steps'] = steps
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policy': policy
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch escalation policy details: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Client synchronization API endpoints
# ==============================

@app.route('/api/clients/refresh/<site>', methods=['POST'])
def refresh_clients_api(site):
    """API for manual client data refresh"""
    try:
        # For internal system use - authentication not required
        
        # Import unified data sync manager
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            logger.error("Unified data sync manager not found.")
            return jsonify({
                'success': False,
                'message': 'Unable to initialize the sync manager.'
            }), 500
        
        # Execute refresh (client data only)
        result = manager.sync_clients_data()
        
        if result['success'] > 0:
            changes = result['total_changes']
            return jsonify({
                'success': True,
                'message': f'{site} client data update completed',
                'changes': changes,
                'summary': f"Added {changes['added']}, updated {changes['updated']}, removed {changes['removed']}"
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{site} client data update failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Client refresh API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred during refresh: {str(e)}'
        }), 500

@app.route('/api/clients/sync-status', methods=['GET'])
def get_client_sync_status():
    """API to query client synchronization status"""
    try:
        # For internal system use - authentication not required
        
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'Sync manager not found.'
            }), 500
        
        # Query synchronization status (client data only)
        status = {}
        conn = manager.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT site, last_sync_time, sync_status, records_synced
                FROM sync_status 
                WHERE data_type = 'clients'
                ORDER BY site
            ''')
            
            for row in cursor.fetchall():
                site = row['site']
                status[site] = {
                    'last_sync': row['last_sync_time'],
                    'status': row['sync_status'],
                    'records': row['records_synced']
                }
        finally:
            conn.close()
        
        return jsonify({
            'success': True,
            'sync_status': status
        })
        
    except Exception as e:
        logger.error(f"Sync status API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred while fetching status: {str(e)}'
        }), 500

@app.route('/api/clients/refresh-all', methods=['POST'])
def refresh_all_clients_api():
    """API to refresh client data for all sites"""
    try:
        # For internal system use - authentication not required
        
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            return jsonify({
                'success': False,
                'message': 'Sync manager not found.'
            }), 500
        
        # Full data refresh (all data)
        results = manager.run_full_sync()
        
        return jsonify({
            'success': True,
            'message': f'Full data sync completed: {results["summary"]["total_records"]} records',
            'summary': results['summary']
        })
        
    except Exception as e:
        logger.error(f"Refresh-all API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An error occurred during full refresh: {str(e)}'
        }), 500

# ==============================
# Unified Policy & Recipients Management API
# ==============================

@app.route('/api/escalation-policies', methods=['POST'])
@login_required
def create_escalation_policy_unified():
    """Create unified escalation policy (FCM device based)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        data = request.get_json()
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # Insert policy basic information
            cursor.execute('''
                INSERT INTO escalation_policies 
                (policy_name, description, event_type, priority, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['policy_name'],
                data['description'],
                data['event_type'],
                data['priority'],
                current_user.id
            ))
            
            policy_id = cursor.lastrowid
            
            # Insert escalation steps
            for step in data['steps']:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    policy_id,
                    step['step_number'],
                    step['delay_minutes'],
                    step['repeat_count'],
                    json.dumps(step['recipients']),  # FCM device ID array
                    step['message_template']
                ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'policy_id': policy_id,
                'message': 'Escalation policy created successfully.',
                'steps_created': len(data['steps'])
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Failed to create escalation policy: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['PUT'])
@login_required
def update_escalation_policy_unified(policy_id):
    """Update unified escalation policy"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        data = request.get_json()
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # Update policy basic information
            cursor.execute('''
                UPDATE escalation_policies 
                SET policy_name = ?, description = ?, event_type = ?, priority = ?, updated_at = ?
                WHERE id = ? AND is_active = 1
            ''', (
                data['policy_name'],
                data['description'],
                data['event_type'],
                data['priority'],
                get_australian_time().isoformat(),
                policy_id
            ))
            
            # Delete existing steps
            cursor.execute('DELETE FROM escalation_steps WHERE policy_id = ?', (policy_id,))
            
            # Insert new steps
            for step in data['steps']:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    policy_id,
                    step['step_number'],
                    step['delay_minutes'],
                    step['repeat_count'],
                    json.dumps(step['recipients']),
                    step['message_template']
                ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Escalation policy updated successfully.',
                'steps_updated': len(data['steps'])
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Failed to update escalation policy: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_escalation_policy_unified(policy_id):
    """Delete unified escalation policy"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # Deactivate policy (instead of actual deletion)
            cursor.execute('''
                UPDATE escalation_policies 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            ''', (get_australian_time().isoformat(), policy_id))
            
            # Also deactivate related steps
            cursor.execute('''
                UPDATE escalation_steps 
                SET is_active = 0
                WHERE policy_id = ?
            ''', (policy_id,))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Escalation policy deleted successfully.'
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Failed to delete escalation policy: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/test', methods=['POST'])
@login_required
def test_escalation_policy_unified():
    """Test unified escalation policy"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        data = request.get_json()
        
        # Simulate policy execution
        total_notifications = 0
        total_duration = 0
        device_count = len(data.get('steps', [{}])[0].get('recipients', []))
        
        for step in data['steps']:
            step_notifications = step['repeat_count'] * device_count
            total_notifications += step_notifications
            
            # Calculate cumulative time
            step_duration = step['delay_minutes'] + (step['repeat_count'] - 1) * step['delay_minutes']
            total_duration = max(total_duration, step_duration)
        
        return jsonify({
            'success': True,
            'total_notifications': total_notifications,
            'total_duration': total_duration,
            'device_count': device_count,
            'message': f'Test complete: {total_notifications} notifications to {device_count} devices'
        })
        
    except Exception as e:
        logger.error(f"Escalation policy test failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipient-groups', methods=['POST'])
@login_required
def save_recipient_group():
    """Save recipient group (FCM device based)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        data = request.get_json()
        group_name = data.get('group_name')
        devices = data.get('devices', [])
        
        if not group_name or not devices:
            return jsonify({'success': False, 'message': 'Please select a group name and devices.'}), 400
        
        # Create recipient group table if it doesn't exist
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipient_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name VARCHAR(100) NOT NULL,
                devices TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Save group
        cursor.execute('''
            INSERT OR REPLACE INTO recipient_groups 
            (group_name, devices, created_by)
            VALUES (?, ?, ?)
        ''', (group_name, json.dumps(devices), current_user.id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Saved {len(devices)} devices to group {group_name}.'
        })
        
    except Exception as e:
        logger.error(f"Failed to save recipient group: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/test-group-notification', methods=['POST'])
@login_required
def test_group_notification():
    """Test group notification"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'You do not have permission.'}), 403
        
        data = request.get_json()
        devices = data.get('devices', [])
        message = data.get('message', 'This is a test notification.')
        
        if not devices:
            return jsonify({'success': False, 'message': 'Please select devices to test.'}), 400
        
        # Query FCM tokens
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in devices])
        cursor.execute(f'''
            SELECT user_id, token, device_info 
            FROM fcm_tokens 
            WHERE user_id IN ({placeholders}) AND is_active = 1
        ''', devices)
        
        tokens = cursor.fetchall()
        conn.close()
        
        if not tokens:
            return jsonify({'success': False, 'message': 'No active tokens found.'}), 404
        
        # Actual FCM send (simulation here)
        sent_count = len(tokens)
        
        # In actual implementation:
        # fcm_result = send_fcm_notification(tokens, message)
        
        return jsonify({
            'success': True,
            'message': f'Sent test notification to {sent_count} devices.',
            'sent_count': sent_count,
            'devices_tested': devices
        })
        
    except Exception as e:
        logger.error(f"Group notification test failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Workflow API endpoints (Mobile App compatible)
# ==============================

@app.route('/api/workflow/create', methods=['POST'])
def create_workflow_mobile():
    """Create workflow (mobile app compatible route)"""
    return create_task_workflow()

@app.route('/api/workflow/status', methods=['GET'])
def get_workflow_status():
    """Query workflow status"""
    try:
        incident_id = request.args.get('incident_id')
        if not incident_id:
            return jsonify({'success': False, 'message': 'incident_id required'}), 400
        
        # Task Manager disabled - JSON-only system
        # return get_incident_workflow_status(incident_id)
        
        # Temporary response (feature disabled)
        return jsonify({
            'success': False,
            'message': 'Task Manager is disabled because it is part of the JSON-only system.',
            'workflow_status': 'unavailable'
        })
        
    except Exception as e:
        logger.error(f"Workflow status lookup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/complete', methods=['POST'])
def complete_workflow_task():
    """Complete workflow task (mobile app compatible)"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data:
            return jsonify({'success': False, 'message': 'task_id required'}), 400
        
        task_id = data['task_id']
        return complete_task_api(task_id)
        
    except Exception as e:
        logger.error(f"Workflow task completion error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/details', methods=['GET'])
def get_workflow_task_details():
    """Workflow task details (mobile app compatible)"""
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'message': 'task_id required'}), 400
        
        return get_task_detail(task_id)
        
    except Exception as e:
        logger.error(f"Workflow task details lookup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/status', methods=['PUT'])
def update_workflow_task_status():
    """Update workflow task status"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'status' not in data:
            return jsonify({'success': False, 'message': 'task_id and status required'}), 400
        
        task_id = data['task_id']
        new_status = data['status']
        notes = data.get('notes', '')
        
        # Process based on status
        if new_status == 'completed':
            return complete_task_api(task_id)
        else:
            # Update other status
            
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (new_status, task_id))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Task not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Task status updated to {new_status}',
                'task_id': task_id,
                'status': new_status
            })
        
    except Exception as e:
        logger.error(f"Task status update error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/policies/details', methods=['GET'])
def get_policy_details_mobile():
    """Policy details (mobile app compatible)"""
    try:
        policy_id = request.args.get('policy_id')
        if not policy_id:
            return jsonify({'success': False, 'message': 'policy_id required'}), 400
        
        return get_escalation_policy_detail(int(policy_id))
        
    except Exception as e:
        logger.error(f"Policy details lookup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/incidents/details', methods=['GET'])
def get_incident_details_mobile():
    """Incident details (mobile app compatible)"""
    try:
        incident_id = request.args.get('incident_id')
        if not incident_id:
            return jsonify({'success': False, 'message': 'incident_id required'}), 400
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # Query incident details
        cursor.execute('''
            SELECT incident_id, client_id, client_name, incident_type, 
                   incident_date, description, severity, status, site, 
                   reported_by, workflow_status, total_tasks, completed_tasks,
                   policy_id, created_by, closed_at, closed_by, last_synced
            FROM incidents_cache
            WHERE incident_id = ?
        ''', (incident_id,))
        
        incident_row = cursor.fetchone()
        if not incident_row:
            return jsonify({'success': False, 'message': 'Incident not found'}), 404
        
        # Query related tasks
        cursor.execute('''
            SELECT task_id, task_type, task_description, status, 
                   priority, assigned_role, scheduled_time, due_time,
                   completed_at, completed_by, deep_link
            FROM scheduled_tasks
            WHERE incident_id = ?
            ORDER BY scheduled_time
        ''', (incident_id,))
        
        tasks = cursor.fetchall()
        
        incident_detail = {
            'incident_id': incident_row[0],
            'client_id': incident_row[1],
            'client_name': incident_row[2],
            'incident_type': incident_row[3],
            'incident_date': incident_row[4],
            'description': incident_row[5],
            'severity': incident_row[6],
            'status': incident_row[7],
            'site': incident_row[8],
            'reported_by': incident_row[9],
            'workflow_status': incident_row[10],
            'total_tasks': incident_row[11] or 0,
            'completed_tasks': incident_row[12] or 0,
            'policy_id': incident_row[13],
            'created_by': incident_row[14],
            'closed_at': incident_row[15],
            'closed_by': incident_row[16],
            'last_synced': incident_row[17],
            'completion_rate': round((incident_row[12] / incident_row[11] * 100) if incident_row[11] > 0 else 0, 1),
            'tasks': [
                {
                    'task_id': task[0],
                    'task_type': task[1],
                    'task_description': task[2],
                    'status': task[3],
                    'priority': task[4],
                    'assigned_role': task[5],
                    'scheduled_time': task[6],
                    'due_time': task[7],
                    'completed_at': task[8],
                    'completed_by': task[9],
                    'deep_link': task[10]
                }
                for task in tasks
            ]
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'incident': incident_detail
        })
        
    except Exception as e:
        logger.error(f"Incident details lookup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Task Management API endpoints
# ==============================

@app.route('/api/tasks/create-workflow', methods=['POST'])
def create_task_workflow():
    """Create incident-based task workflow"""
    try:
        data = request.get_json()
        required_fields = ['incident_id', 'policy_id', 'client_name', 'client_id', 'site', 'event_type', 'risk_rating']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400
        
        created_by = data.get('created_by', 'system')  # Provided from mobile app or default value
        
        logger.info(f"Workflow creation requested: incident_id={data['incident_id']}, created_by={created_by}")
        
        # Task Manager disabled - JSON-only system
        # task_manager = get_task_manager()
        # result = task_manager.create_incident_workflow(
        #     incident_id=data['incident_id'],
        #     policy_id=data['policy_id'],
        #     client_name=data['client_name'],
        #     client_id=data['client_id'],
        #     site=data['site'],
        #     event_type=data['event_type'],
        #     risk_rating=data['risk_rating'],
        #     created_by=created_by
        # )
        
        # Temporary response (feature disabled)
        result = {
            'success': False,
            'message': 'Task Manager is disabled because it is part of the JSON-only system.'
        }
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Workflow creation API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task_api(task_id):
    """API to process task completion"""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')
        completed_by = data.get('completed_by', 'mobile_user')  # Provided by mobile app
        
        logger.info(f"Task completion requested: task_id={task_id}, completed_by={completed_by}")
        
        # Task Manager disabled - JSON-only system
        # task_manager = get_task_manager()
        # result = task_manager.complete_task(
        #     task_id=task_id,
        #     completed_by=completed_by,
        #     notes=notes
        # )
        
        # Temporary response (feature disabled)
        result = {
            'success': False,
            'message': 'Task Manager is disabled because it is part of the JSON-only system.'
        }
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Task completion API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/my-tasks', methods=['GET'])
def get_my_tasks():
    """API to query user's assigned task list"""
    try:
        status = request.args.get('status')  # pending, in_progress, completed
        site = request.args.get('site', 'Parafield Gardens')
        user_role = request.args.get('user_role', 'RN')  # Provided from mobile app
        
        # Query tasks based on user role
        if user_role == 'doctor':
            assigned_role = 'doctor'
        elif user_role == 'physiotherapist':
            assigned_role = 'physiotherapist'
        else:
            assigned_role = 'RN'  # Default value
        
        logger.info(f"Fetching user tasks: user_role={user_role}, assigned_role={assigned_role}, site={site}, status={status}")
        
        # Task Manager disabled - JSON-only system
        # task_manager = get_task_manager()
        # tasks = task_manager.get_user_tasks(assigned_role, site, status)
        
        # Temporary response (feature disabled)
        tasks = []
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'user_role': assigned_role,
            'site': site
        })
        
    except Exception as e:
        logger.error(f"Task list API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    """API to query task details"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT st.*, ic.description as incident_description,
                   ic.severity, ic.reported_by
            FROM scheduled_tasks st
            LEFT JOIN incidents_cache ic ON st.incident_id = ic.incident_id
            WHERE st.task_id = ?
        ''', (task_id,))
        
        task_row = cursor.fetchone()
        if not task_row:
            return jsonify({'success': False, 'message': 'Task not found'}), 404
        
        # Query task execution logs
        cursor.execute('''
            SELECT action, performed_by, performed_at, details
            FROM task_execution_logs
            WHERE task_id = ?
            ORDER BY performed_at DESC
        ''', (task_id,))
        
        logs = cursor.fetchall()
        
        task_detail = {
            'task_id': task_row[1],
            'incident_id': task_row[2],
            'client_name': task_row[4],
            'client_id': task_row[5],
            'task_type': task_row[6],
            'task_description': task_row[7],
            'scheduled_time': task_row[8],
            'due_time': task_row[9],
            'status': task_row[10],
            'priority': task_row[11],
            'assigned_role': task_row[13],
            'site': task_row[14],
            'deep_link': task_row[15],
            'created_at': task_row[19],
            'completed_at': task_row[21],
            'completed_by': task_row[22],
            'completion_notes': task_row[23],
            'incident_description': task_row[24],
            'incident_severity': task_row[25],
            'incident_reported_by': task_row[26],
            'execution_logs': [
                {
                    'action': log[0],
                    'performed_by': log[1],
                    'performed_at': log[2],
                    'details': json.loads(log[3]) if log[3] else {}
                }
                for log in logs
            ]
        }
        
        return jsonify({
            'success': True,
            'task': task_detail
        })
        
    except Exception as e:
        logger.error(f"Task detail API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/send-notifications', methods=['POST'])
@login_required
def send_task_notifications():
    """Send scheduled task notifications (admin only)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Task Manager disabled - JSON-only system
        # task_manager = get_task_manager()
        # result = task_manager.send_scheduled_notifications()
        
        # Temporary response (feature disabled)
        result = {
            'success': False,
            'message': 'Task Manager is disabled because it is part of the JSON-only system.',
            'sent_count': 0,
            'failed_count': 0
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Task notification send API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# CIMS (Compliance-Driven Incident Management System) Routes
# ==============================

from cims_policy_engine import PolicyEngine
from app_locks import write_lock

# CIMS policy engine instance
policy_engine = PolicyEngine()

# Database connection function for CIMS
def get_db_connection(read_only: bool = False):
    """Database connection for CIMS"""
    # Use absolute path to prevent working directory issues
    import os
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'progress_report.db')
    
    if read_only:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', timeout=60.0, uri=True)
    else:
        conn = sqlite3.connect(db_path, timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass
    return conn

def optional_login_required(f):
    """Accessible without authentication in development, login required in production"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Accessible without authentication in development
        if app.config.get('DEBUG', False):
            return f(*args, **kwargs)
        # Login required in production
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'is_expired': True,
                'message': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/memory/status', methods=['GET'])
@optional_login_required
def get_memory_status():
    """Return memory usage status (accessible without authentication in development)"""
    try:
        monitor = get_memory_monitor()
        summary = monitor.get_summary()
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"Error fetching memory status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/memory/history', methods=['GET'])
@optional_login_required
def get_memory_history():
    """Return memory usage history (accessible without authentication in development)"""
    try:
        monitor = get_memory_monitor()
        limit = request.args.get('limit', 50, type=int)
        history = monitor.get_memory_history(limit=limit)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"Error retrieving memory history: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/memory/gc', methods=['POST'])
@optional_login_required
def force_garbage_collection():
    """Force garbage collection (accessible without authentication in development)"""
    try:
        monitor = get_memory_monitor()
        result = monitor.force_gc()
        return jsonify({
            'success': True,
            'data': result,
            'message': f'{result["freed_mb"]}MB memory freed'
        })
    except Exception as e:
        logger.error(f"Error running garbage collection: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/cache/status-current', methods=['GET'])
@login_required
def get_cache_status_current():
    """Return latest cache/sync status for dashboard indicator"""
    conn = None
    try:
        # Use regular connection instead of read_only (WAL mode compatibility)
        conn = get_db_connection(read_only=False)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, last_processed
            FROM cims_cache_management
            ORDER BY last_processed DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        
        # Query last sync time
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync_result = cursor.fetchone()
        last_sync_time = last_sync_result[0] if last_sync_result else None
        
        # Query sync completion event (so frontend can detect it)
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'sync_completion_event'
        """)
        sync_event_result = cursor.fetchone()
        sync_completion_event = sync_event_result[0] if sync_event_result else None
        
        # Query latest incident date from data
        cursor.execute("""
            SELECT MAX(incident_date) as latest_date
            FROM cims_incidents
            WHERE incident_date IS NOT NULL AND incident_date != ''
        """)
        latest_incident_result = cursor.fetchone()
        latest_incident_date = latest_incident_result[0] if latest_incident_result and latest_incident_result[0] else None
        
        status = row[0] if row else 'idle'
        last = row[1] if row else None
        
        # Log for debugging
        logger.debug(f"Sync status: status={status}, last_sync_time={last_sync_time}, sync_event={sync_completion_event}, latest_incident_date={latest_incident_date}")
        
        conn.close()
        return jsonify({
            'success': True, 
            'status': status, 
            'last_processed': last,
            'last_sync_time': last_sync_time,
            'sync_completion_event': sync_completion_event,  # Sync completion event timestamp
            'latest_incident_date': latest_incident_date
        })
    except Exception as e:
        # Handle quietly when table doesn't exist or is inaccessible (only log warning)
        # This API is for UI indicator, so failure doesn't affect app functionality
        if 'no such table' in str(e):
            # If table doesn't exist, treat as first run at debug level
            logger.debug(f"cims_cache_management table not found (first run?): {e}")
        else:
            # Log other errors as warning
            logger.warning(f"get_cache_status_current error: {e}")
        
        # Try to query last_sync_time and latest_incident_date even on error
        try:
            if conn:
                conn.close()
            conn = get_db_connection(read_only=True)
            cursor = conn.cursor()
            
            # Query last sync time
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'last_incident_sync_time'
            """)
            last_sync_result = cursor.fetchone()
            last_sync_time = last_sync_result[0] if last_sync_result else None
            
            # Query latest incident date from data
            cursor.execute("""
                SELECT MAX(incident_date) as latest_date
                FROM cims_incidents
                WHERE incident_date IS NOT NULL AND incident_date != ''
            """)
            latest_incident_result = cursor.fetchone()
            latest_incident_date = latest_incident_result[0] if latest_incident_result and latest_incident_result[0] else None
            
            conn.close()
            return jsonify({
                'success': True, 
                'status': 'idle',
                'last_sync_time': last_sync_time,
                'latest_incident_date': latest_incident_date
            }), 200
        except Exception as e2:
            logger.warning(f"Error fetching sync times in exception handler: {e2}")
            if conn:
                conn.close()
            return jsonify({
                'success': True, 
                'status': 'idle',
                'last_sync_time': None,
                'latest_incident_date': None
            }), 200
    finally:
        if conn:
            conn.close()

@app.route('/api/cims/incidents/<int:incident_db_id>/tasks', methods=['GET'], endpoint='get_incident_tasks_v2')
@login_required
def get_incident_tasks_v2(incident_db_id):
    """Return task list and summary count for given incident"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check incident existence and get basic information
        cursor.execute(
            """
            SELECT id, incident_id, resident_name, site, incident_date, status
            FROM cims_incidents
            WHERE id = ?
            """,
            (incident_db_id,)
        )
        incident = cursor.fetchone()
        if not incident:
            return jsonify({'success': False, 'message': 'Incident not found'}), 404

        # Query task list
        cursor.execute(
            """
            SELECT id, task_id, task_name, description, assigned_role,
                   due_date, priority, status, completed_at
            FROM cims_tasks
            WHERE incident_id = ?
            ORDER BY due_date ASC
            """,
            (incident_db_id,)
        )
        rows = cursor.fetchall()

        tasks = []
        counts = {
            'total': 0,
            'completed': 0,
            'pending': 0,
            'in_progress': 0,
            'overdue': 0
        }

        now_iso = datetime.now().isoformat()

        for r in rows:
            task = {
                'id': r['id'],
                'task_identifier': r['task_id'],
                'task_name': r['task_name'],
                'description': r['description'],
                'assigned_role': r['assigned_role'],
                'due_date': r['due_date'],
                'priority': r['priority'],
                'status': r['status'],
                'completed_at': r['completed_at']
            }
            tasks.append(task)

            counts['total'] += 1
            status = (r['status'] or '').lower()
            if status == 'completed':
                counts['completed'] += 1
            elif status in ('in_progress', 'in progress'):
                counts['in_progress'] += 1
            else:
                # pending, etc.
                counts['pending'] += 1
                # Calculate overdue: due_date < now and not completed
                try:
                    if r['due_date'] and r['completed_at'] is None and datetime.fromisoformat(r['due_date']) < datetime.fromisoformat(now_iso):
                        counts['overdue'] += 1
                except Exception:
                    pass

        return jsonify({
            'success': True,
            'incident': {
                'id': incident['id'],
                'incident_id': incident['incident_id'],
                'resident_name': incident['resident_name'],
                'site': incident['site'],
                'incident_date': incident['incident_date'],
                'status': incident['status']
            },
            'counts': counts,
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"Incident tasks fetch error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/incident_dashboard2')
@login_required
def incident_dashboard2():
    """Legacy CIMS dashboard - redirects to integrated dashboard"""
    return redirect(url_for('integrated_dashboard'))

@app.route('/api/cims/tasks')
@login_required
def get_cims_tasks():
    """API to query user tasks"""
    try:
        # Query tasks based on user role
        if current_user.is_admin() or current_user.is_clinical_manager():
            # Admin queries all tasks
            tasks = policy_engine.get_user_tasks(
                user_id=current_user.id, 
                role='admin', 
                status_filter=request.args.get('status')
            )
        else:
            # Regular users query only tasks assigned to them
            tasks = policy_engine.get_user_tasks(
                user_id=current_user.id, 
                role=current_user.role, 
                status_filter=request.args.get('status')
            )
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
        
    except Exception as e:
        logger.error(f"CIMS task fetch API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/incidents', methods=['GET', 'POST'])
@login_required
def cims_incidents():
    """API to query/create incidents"""
    if request.method == 'GET':
        return get_cims_incidents()
    else:
        return create_cims_incident()

@app.route('/api/cims/fall-statistics', methods=['GET'])
@login_required
def get_fall_statistics():
    """API to query Fall Policy statistics"""
    conn = None
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        # Import fall detector (safely)
        fall_detector = None
        try:
            from services.fall_policy_detector import fall_detector
        except ImportError as e:
            logger.warning(f"Unable to import fall_policy_detector module: {e}")
            fall_detector = None
        
        # Query Fall incidents (last 30 days) - including fall_type
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT id, incident_id, incident_type, incident_date, site, fall_type
            FROM cims_incidents
            WHERE incident_type LIKE '%Fall%'
            AND incident_date >= ?
            ORDER BY incident_date DESC
        """, (thirty_days_ago,))
        
        fall_incidents = cursor.fetchall()
        
        # Aggregate statistics
        stats = {
            'total_falls': len(fall_incidents),
            'witnessed': 0,
            'unwitnessed': 0,
            'unknown': 0,
            'visits_scheduled': 0,
            'visits_saved': 0,
            'by_site': {},
            'recent_falls': []
        }
        
        for incident in fall_incidents:
            incident_id = incident[0]
            incident_manad_id = incident[1]
            incident_type = incident[2]
            incident_date = incident[3]
            site = incident[4] or 'Unknown'
            fall_type = incident[5]  # Directly queried from DB
            
            # Calculate if fall_type is missing (legacy data handling)
            # Note: Read-only mode, so don't save to DB, use only in memory
            if not fall_type and fall_detector:
                try:
                    fall_type = fall_detector.detect_fall_type_from_incident(incident_id, cursor)
                    # Don't save to DB in read-only mode (use only in memory)
                    # DB updates are handled by sync process
                except Exception as detect_error:
                    logger.debug(f"Failed to detect fall_type for incident {incident_id}: {detect_error}")
                    fall_type = None
            
            # Validate fall_type and set default
            if fall_type not in ['witnessed', 'unwitnessed', 'unknown']:
                fall_type = 'unknown'
            
            # Update statistics
            if fall_type == 'witnessed':
                stats['witnessed'] += 1
                stats['visits_scheduled'] += 1
                stats['visits_saved'] += 35  # 36 - 1 = 35 visits saved
            elif fall_type == 'unwitnessed':
                stats['unwitnessed'] += 1
                stats['visits_scheduled'] += 36
            else:  # unknown
                stats['unknown'] += 1
                stats['visits_scheduled'] += 36  # Default to unwitnessed
            
            # Statistics by site
            if site not in stats['by_site']:
                stats['by_site'][site] = {
                    'total': 0,
                    'witnessed': 0,
                    'unwitnessed': 0,
                    'unknown': 0
                }
            
            stats['by_site'][site]['total'] += 1
            stats['by_site'][site][fall_type] += 1  # Now safe to access
            
            # Include details for only recent 5 Falls
            if len(stats['recent_falls']) < 5:
                stats['recent_falls'].append({
                    'incident_id': incident_manad_id,
                    'incident_type': incident_type,
                    'fall_type': fall_type,
                    'incident_date': incident_date,
                    'site': site
                })
        
        # Calculate percentages
        if stats['total_falls'] > 0:
            stats['witnessed_percentage'] = round(stats['witnessed'] / stats['total_falls'] * 100, 1)
            stats['unwitnessed_percentage'] = round(stats['unwitnessed'] / stats['total_falls'] * 100, 1)
            stats['unknown_percentage'] = round(stats['unknown'] / stats['total_falls'] * 100, 1)
        else:
            stats['witnessed_percentage'] = 0
            stats['unwitnessed_percentage'] = 0
            stats['unknown_percentage'] = 0
        
        logger.info(
            f"📊 Fall stats: {stats['total_falls']} (W: {stats['witnessed']}, UW: {stats['unwitnessed']})"
        )
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error fetching fall stats: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Fall stats detailed error:\n{error_trace}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'traceback': error_trace if app.debug else None
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/cims/schedule/<site_name>', methods=['GET'])
@login_required
def get_site_schedule(site_name):
    """Get visit schedule for a specific site"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate real schedule data from CIMS database
        schedule_data = generate_real_schedule(site_name)
        
        return jsonify(schedule_data)
        
    except Exception as e:
        logger.error(f"Error getting schedule for {site_name}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/schedule/complete', methods=['POST'])
@login_required
def complete_scheduled_task():
    """Mark a scheduled task as completed"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        task_id = data.get('task_id')
        site_name = data.get('site_name')
        
        if not task_id or not site_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Update the task in CIMS database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract CIMS task ID from the task_id
        if task_id.startswith('cims_task_'):
            cims_task_id = int(task_id.replace('cims_task_', ''))
        else:
            return jsonify({'error': 'Invalid task ID format'}), 400
        
        # Update task status
        cursor.execute("""
            UPDATE cims_tasks 
            SET status = 'Completed', 
                completed_at = ?,
                completed_by_user_id = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), current_user.id, cims_task_id))
        
        # Create audit log
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            current_user.id,
            'task_completed',
            'task',
            cims_task_id,
            json.dumps({
                'task_id': task_id,
                'site_name': site_name,
                'completed_at': datetime.now().isoformat()
            })
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Task {task_id} completed for site {site_name} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'task_id': task_id,
            'completed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error completing task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/integrator/start', methods=['POST'])
@login_required
def start_manad_integrator():
    """Start MANAD Plus integrator"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        # Start the integrator
        integrator = MANADPlusIntegrator()
        success = integrator.start_polling()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'MANAD Plus integrator started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start MANAD Plus integrator'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting MANAD integrator: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/integrator/status', methods=['GET'])
@login_required
def get_integrator_status():
    """Get MANAD Plus integrator status"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        integrator = MANADPlusIntegrator()
        status = integrator.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting integrator status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/sync-progress-notes', methods=['POST'])
@login_required
def trigger_progress_note_sync():
    """
    Manual trigger for Progress Note synchronization (Admin only)
    
    ⚠️ Temporarily disabled (2025-11-25)
    - Will be reimplemented with DB direct access later
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        logger.info(f"Progress Note sync manually triggered by {current_user.username} (disabled)")
        # result = sync_progress_notes_from_manad_to_cims()
        
        return jsonify({
            'success': True,
            'message': 'Progress Note sync temporarily disabled. Will be reimplemented with DB direct access.',
            'matched': 0
        })
        
    except Exception as e:
        logger.error(f"Progress Note sync trigger error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cims/check-progress-notes/<task_id>', methods=['GET'])
@login_required
def check_progress_notes(task_id):
    """Check progress notes for a specific task in MANAD Plus"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        # Get task details
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.id, i.manad_incident_id, i.resident_id, i.resident_name
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE t.id = ?
        """, (task_id,))
        
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        _, manad_incident_id, resident_id, resident_name = task
        
        if not manad_incident_id:
            return jsonify({'error': 'No MANAD incident ID associated'}), 400
        
        # Check progress notes in MANAD Plus
        integrator = MANADPlusIntegrator()
        has_progress_note = integrator.check_progress_notes(manad_incident_id, resident_id)
        
        return jsonify({
            'task_id': task_id,
            'manad_incident_id': manad_incident_id,
            'resident_name': resident_name,
            'has_progress_note': has_progress_note,
            'checked_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking progress notes: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def generate_real_schedule(site_name):
    """Generate real schedule data from CIMS database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get incomplete tasks for the site
        cursor.execute("""
            SELECT t.id, t.task_name, t.description, t.due_date, t.priority, t.status,
                   i.resident_name, i.incident_type, i.location, i.incident_date
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE i.site = ? AND t.status IN ('Open', 'In Progress', 'pending', 'Pending')
            ORDER BY t.due_date ASC
        """, (site_name,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        schedule = []
        now = datetime.now()
        
        for task in tasks:
            task_id, task_name, description, due_date, priority, status, resident_name, incident_type, location, incident_date = task
            
            # Parse due date
            if isinstance(due_date, str):
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            else:
                due_datetime = due_date
            
            # Determine status and urgency
            time_diff = (due_datetime - now).total_seconds()
            if time_diff < 0:
                task_status = 'overdue'
                urgency = 'overdue'
            elif time_diff < 2 * 3600:  # Less than 2 hours
                task_status = 'due-soon'
                urgency = 'urgent'
            else:
                task_status = 'pending'
                urgency = 'normal'
            
            # Extract room from location if available
            room = 'Unknown'
            if location:
                # Try to extract room number from location
                import re
                room_match = re.search(r'Room\s+(\d+)', location)
                if room_match:
                    room = f"Room {room_match.group(1)}"
                else:
                    room = location
            
            schedule.append({
                'id': f'cims_task_{task_id}',
                'time': due_datetime.isoformat(),
                'resident': resident_name or 'Unknown Resident',
                'room': room,
                'task': task_name or description or f'Follow-up for {incident_type}',
                'status': task_status,
                'urgency': urgency,
                'completed': status == 'Completed',
                'site': site_name,
                'priority': priority,
                'incident_type': incident_type
            })
        
        return sorted(schedule, key=lambda x: x['time'])
        
    except Exception as e:
        logger.error(f"Error generating real schedule for {site_name}: {str(e)}")
        # Return empty schedule on error
        return []

def _cache_clients_to_db(clients: list, site_name: str, cursor) -> None:
    """
    [DEPRECATED] Save client data to clients_cache table
    
    Cache is unnecessary in DB direct access mode as latest data is queried each time.
    This function is no longer used.
    
    Args:
        clients: Client list received from MANAD API
        site_name: Site name
        cursor: DB cursor
    """
    try:
        # Deactivate existing site clients
        cursor.execute("""
            UPDATE clients_cache 
            SET is_active = 0 
            WHERE site = ?
        """, (site_name,))
        
        # Insert new client data
        for client in clients:
            try:
                client_id = client.get('Id', 0)
                first_name = client.get('FirstName', '')
                middle_name = client.get('MiddleName', '')
                surname = client.get('LastName', client.get('Surname', ''))
                preferred_name = client.get('PreferredName', '')
                client_name = f"{first_name} {surname}".strip()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO clients_cache (
                        client_record_id, person_id, client_name, preferred_name,
                        title, first_name, middle_name, surname, gender, birth_date,
                        admission_date, room_name, room_number, wing_name,
                        location_id, location_name, main_client_service_id,
                        original_person_id, site, last_synced, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    client_id,
                    client.get('PersonId', 0),
                    client_name,
                    preferred_name,
                    client.get('Title', ''),
                    first_name,
                    middle_name,
                    surname,
                    client.get('Gender', ''),
                    client.get('BirthDate', None),
                    client.get('AdmissionDate', None),
                    client.get('RoomName', ''),
                    client.get('RoomNumber', ''),
                    client.get('WingName', ''),
                    client.get('LocationId', 0),
                    client.get('LocationName', ''),
                    client.get('MainClientServiceId', 0),
                    client.get('PersonId', 0),
                    site_name,
                    datetime.now().isoformat()
                ))
            except Exception as e:
                logger.warning(f"Client caching error (ID: {client.get('Id', 'unknown')}): {e}")
                continue
        
        logger.info(f"✅ Client cache completed: {site_name} - {len(clients)} clients")
        
    except Exception as e:
        logger.error(f"Client cache update error: {e}")

def get_api_config_for_site(site_name):
    """Create API configuration for site"""
    try:
        from config import get_server_info, get_api_headers
        server_info = get_server_info(site_name)
        api_headers = get_api_headers(site_name)
        
        return {
            'base_url': server_info['base_url'],
            'server_ip': server_info['server_ip'],
            'server_port': server_info['server_port'],
            'api_username': api_headers.get('x-api-username', 'ManadAPI'),
            'api_key': api_headers.get('x-api-key', ''),
            'timeout': 120
        }
    except Exception as e:
        logger.error(f"Failed to get API config for {site_name}: {e}")
        return None

def sync_progress_notes_from_manad_to_cims():
    """
    Synchronize Post Fall Progress Notes from MANAD Plus to update Task completion status
    
    ⚠️ Temporarily disabled (2025-11-25)
    - Will be reimplemented with DB direct access later
    - Currently only shows schedule, Task completion check logic removed
    """
    # TODO: Reimplement Post Fall Progress Note query and Task completion processing with DB direct access later
    # - Add Post Fall Progress Note query method in manad_db_connector
    # - Match with Tasks and auto-complete
    logger.info("⚠️ Progress Note sync is disabled (paused; will be reimplemented with direct DB access)")
    return {'success': True, 'matched': 0, 'message': 'Progress Note sync temporarily disabled'}

def ensure_fall_policy_exists():
    """
    Check if Fall Policy exists in DB and create default Policy if not
    """
    import json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if Fall policy exists
        cursor.execute("""
            SELECT COUNT(*) FROM cims_policies 
            WHERE policy_id = 'FALL-001' AND is_active = 1
        """)
        
        if cursor.fetchone()[0] > 0:
            logger.info("✅ Fall Policy already exists")
            conn.close()
            return
        
        # Create default Fall Policy
        logger.info("📝 Creating default Fall Policy...")
        
        default_policy_json = {
            "policy_name": "Fall Management Policy V3",
            "policy_id": "FALL-001",
            "incident_association": {
                "incident_type": "Fall"
            },
            "nurse_visit_schedule": [
                {
                    "phase": 1,
                    "interval": 30,
                    "interval_unit": "minutes",
                    "duration": 4,
                    "duration_unit": "hours"
                },
                {
                    "phase": 2,
                    "interval": 2,
                    "interval_unit": "hours",
                    "duration": 20,
                    "duration_unit": "hours"
                },
                {
                    "phase": 3,
                    "interval": 4,
                    "interval_unit": "hours",
                    "duration": 3,
                    "duration_unit": "days"
                }
            ],
            "common_assessment_tasks": "Complete neurological observations: GCS, pupil response, limb movement, vital signs"
        }
        
        cursor.execute("""
            INSERT INTO cims_policies 
            (policy_id, name, description, version, effective_date, rules_json, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'FALL-001',
            'Fall Management Policy V3',
            'Automatic post-fall neurological monitoring with phased visit schedule',
            '3.0',
            datetime.now().isoformat(),
            json.dumps(default_policy_json),
            1,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info("✅ Default Fall Policy created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating Fall Policy: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor):
    """
    Automatically generate tasks for Fall incident
    (Wraps CIMSService.auto_generate_fall_tasks)
    
    Args:
        incident_db_id: Incident ID in CIMS DB (integer)
        incident_date_iso: Incident occurrence time (ISO format string)
        cursor: DB cursor
        
    Returns:
        Number of tasks created
    """
    from services.cims_service import CIMSService
    return CIMSService.auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor)

def sync_incidents_from_manad_to_cims(full_sync=False):
    """
    Synchronize latest incidents from MANAD DB to CIMS DB (DB direct access)
    
    Args:
        full_sync: True for full sync (30 days), False for incremental sync (since last sync)
    """
    try:
        safe_site_servers = get_safe_site_servers()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if first sync (check if incidents exist in DB)
        cursor.execute("SELECT COUNT(*) FROM cims_incidents")
        incident_count = cursor.fetchone()[0]
        is_first_sync = incident_count == 0 or full_sync
        
        if is_first_sync:
            # First sync: last 30 days (or more)
            logger.info("🔄 Initial sync starting: last 30 days of data")
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            # Incremental sync: since last sync time
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'last_incident_sync_time'
            """)
            last_sync_result = cursor.fetchone()
            
            if last_sync_result:
                # Use last sync time (from 1 hour before to allow slight overlap)
                last_sync_dt = datetime.fromisoformat(last_sync_result[0])
                start_date = (last_sync_dt - timedelta(hours=1)).strftime('%Y-%m-%d')
                logger.info(f"📥 Incremental sync: changes since {last_sync_result[0]}")
            else:
                # If no sync record, use last 7 days
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                logger.info("🔄 No sync record: last 7 days of data")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        conn.close()
        
        total_synced = 0
        total_updated = 0
        
        for site_name in safe_site_servers.keys():
            try:
                logger.info(f"Syncing incidents from {site_name}...")
                
                # Get MANAD data (always use DB direct access)
                try:
                    from manad_db_connector import fetch_incidents_with_client_data_from_db
                    logger.info(f"🔌 Direct DB access mode: {site_name}")
                    incidents_data = fetch_incidents_with_client_data_from_db(
                        site_name, start_date, end_date, 
                        fetch_clients=is_first_sync
                    )
                    # Error only if DB query result is None (empty list is normal)
                    if incidents_data is None:
                        error_msg = f"❌ DB direct access failed: {site_name} - DB connection failed."
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    # 0 incidents is normal (no incidents in that period)
                    incident_count = len(incidents_data.get('incidents', []))
                    if incident_count == 0:
                        logger.info(
                            f"📭 {site_name}: no incidents in the last "
                            f"{(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days} "
                            f"days (OK)"
                        )
                except Exception as db_error:
                    error_msg = f"❌ DB direct access failed: {site_name} - {str(db_error)}. Please check DB connection settings and driver installation."
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                if not incidents_data or 'incidents' not in incidents_data:
                    logger.warning(f"No incident data from {site_name}")
                    continue
                
                incidents = incidents_data.get('incidents', [])
                clients = incidents_data.get('clients', [])
                
                # Convert client data to dictionary (for fast lookup)
                # In DB direct access mode, latest data is queried each time, so cache is unnecessary
                clients_dict = {client.get('id', client.get('Id', '')): client for client in clients}
                
                logger.info(f"📋 Client mapping completed: {len(clients_dict)} clients (latest data)")
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                for incident in incidents:
                    try:
                        # Extract incident ID (MANAD API uses capital 'Id')
                        incident_id = str(incident.get('Id', ''))
                        if not incident_id:
                            continue
                        
                        # Get resident information
                        resident_id = incident.get('ClientId', '')
                        resident_name = 'Unknown'
                        
                        # Try to get name from incident data first
                        first_name = incident.get('FirstName', '')
                        last_name = incident.get('LastName', '')
                        if first_name and last_name:
                            resident_name = f"{first_name} {last_name}".strip()
                        elif resident_id and resident_id in clients_dict:
                            # Fallback to client data (use capital FirstName/LastName)
                            client = clients_dict[resident_id]
                            first = client.get('FirstName', '')
                            last = client.get('LastName', '')
                            if first or last:
                                resident_name = f"{first} {last}".strip()
                        
                        # Parse incident date
                        incident_date_str = incident.get('Date', incident.get('ReportedDate', ''))
                        try:
                            # Convert to ISO format
                            if incident_date_str:
                                incident_date = datetime.fromisoformat(incident_date_str.replace('Z', '+00:00'))
                                incident_date_iso = incident_date.isoformat()
                            else:
                                incident_date_iso = datetime.now().isoformat()
                        except:
                            incident_date_iso = datetime.now().isoformat()
                        
                        # Check if already exists (based on MANAD incident ID)
                        cursor.execute("""
                            SELECT id, status FROM cims_incidents 
                            WHERE manad_incident_id = ?
                        """, (incident_id,))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Update existing incident
                            existing_db_id = existing[0]
                            existing_status = existing[1]
                            
                            # Check incident status from MANAD
                            manad_status = incident.get('Status', 'Open')
                            is_closed = manad_status.lower() in ['closed', 'close'] or incident.get('StatusEnumId') == 2
                            
                            # Prepare incident type
                            event_types = incident.get('EventTypeNames', [])
                            incident_type_str = ', '.join(event_types) if isinstance(event_types, list) else str(event_types)
                            
                            # When incident status changes to Closed
                            if is_closed and existing_status != 'Closed':
                                # Update incident status to Closed
                                cursor.execute("""
                                    UPDATE cims_incidents
                                    SET incident_type = ?,
                                        severity = ?,
                                        description = ?,
                                        initial_actions_taken = ?,
                                        reported_by_name = ?,
                                        resident_name = ?,
                                        incident_date = ?,
                                        status = 'Closed',
                                        updated_at = ?
                                    WHERE manad_incident_id = ?
                                """, (
                                    incident_type_str if incident_type_str else 'Unknown',
                                    incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',
                                    incident.get('Description', ''),
                                    incident.get('ActionTaken', ''),
                                    incident.get('ReportedByName', ''),
                                    resident_name,
                                    incident_date_iso,
                                    datetime.now().isoformat(),
                                    incident_id
                                ))
                                
                                # Change all Tasks to Completed
                                cursor.execute("""
                                    UPDATE cims_tasks
                                    SET status = 'completed',
                                        completed_at = ?,
                                        updated_at = ?
                                    WHERE incident_id = ? AND status != 'completed'
                                """, (
                                    datetime.now().isoformat(),
                                    datetime.now().isoformat(),
                                    existing_db_id
                                ))
                                
                                tasks_closed = cursor.rowcount
                                if tasks_closed > 0:
                                    logger.info(f"✅ Incident {existing_db_id} Closed: {tasks_closed} tasks automatically closed")
                                
                                total_updated += 1
                            
                            # Update and create tasks only for Open status
                            elif existing_status == 'Open' and not is_closed:
                                cursor.execute("""
                                    UPDATE cims_incidents
                                    SET incident_type = ?,
                                        severity = ?,
                                        description = ?,
                                        initial_actions_taken = ?,
                                        reported_by_name = ?,
                                        resident_name = ?,
                                        incident_date = ?
                                    WHERE manad_incident_id = ?
                                """, (
                                    incident_type_str if incident_type_str else 'Unknown',
                                    incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',
                                    incident.get('Description', ''),
                                    incident.get('ActionTaken', ''),
                                    incident.get('ReportedByName', ''),
                                    resident_name,
                                    incident_date_iso,
                                    incident_id
                                ))
                                total_updated += 1
                                
                                # 🚀 Auto-generate tasks if Fall incident has no tasks
                                if 'fall' in incident_type_str.lower():
                                    # Check if tasks exist
                                    cursor.execute("""
                                        SELECT COUNT(*) FROM cims_tasks 
                                        WHERE incident_id = ?
                                    """, (existing_db_id,))
                                    task_count = cursor.fetchone()[0]
                                    
                                    if task_count == 0:
                                        try:
                                            tasks_created = auto_generate_fall_tasks(existing_db_id, incident_date_iso, cursor)
                                            if tasks_created > 0:
                                                logger.info(f"✅ Auto-generated {tasks_created} tasks for existing Fall incident {existing_db_id}")
                                        except Exception as task_error:
                                            logger.error(f"Failed to auto-generate tasks for existing incident {existing_db_id}: {str(task_error)}")
                        else:
                            # Create new incident
                            cims_incident_id = f"INC-{incident_id}"
                            
                            # Extract room information
                            room = incident.get('RoomName', '')
                            wing = incident.get('WingName', '')
                            department = incident.get('DepartmentName', '')
                            location_parts = [p for p in [room, wing, department] if p]
                            location = ', '.join(location_parts) if location_parts else 'Unknown'
                            
                            # Process incident type (may be a list)
                            event_types = incident.get('EventTypeNames', [])
                            incident_type = ', '.join(event_types) if isinstance(event_types, list) else str(event_types)
                            
                            # Use 0 as reported_by for MANAD-synced incidents (system user)
                            cursor.execute("""
                                INSERT INTO cims_incidents (
                                    incident_id, manad_incident_id, resident_id, resident_name, 
                                    incident_type, severity, status, incident_date, 
                                    location, description, initial_actions_taken, 
                                    reported_by, reported_by_name, site, created_at,
                                    risk_rating, is_review_closed, is_ambulance_called,
                                    is_admitted_to_hospital, is_major_injury, reviewed_date, status_enum_id
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                cims_incident_id,
                                incident_id,
                                str(resident_id),
                                resident_name,
                                incident_type if incident_type else 'Unknown',
                                incident.get('SeverityRating') or 'Unknown',
                                incident.get('Status', 'Open'),
                                incident_date_iso,
                                location,
                                incident.get('Description', ''),
                                incident.get('ActionTaken', ''),
                                0,  # System user ID for MANAD-synced incidents
                                incident.get('ReportedByName', ''),
                                site_name,
                                datetime.now().isoformat(),
                                incident.get('RiskRatingName', ''),
                                1 if incident.get('IsReviewClosed') else 0,
                                1 if incident.get('IsAmbulanceCalled') else 0,
                                1 if incident.get('IsAdmittedToHospital') else 0,
                                1 if incident.get('IsMajorInjury') else 0,
                                incident.get('ReviewedDate'),
                                incident.get('StatusEnumId')
                            ))
                            total_synced += 1
                            
                            # 🚀 NEW: Auto-generate tasks if Fall incident
                            new_incident_db_id = cursor.lastrowid
                            if 'fall' in incident_type.lower():
                                try:
                                    tasks_created = auto_generate_fall_tasks(new_incident_db_id, incident_date_iso, cursor)
                                    if tasks_created > 0:
                                        logger.info(f"✅ Auto-generated {tasks_created} tasks for Fall incident {cims_incident_id}")
                                except Exception as task_error:
                                    logger.error(f"Failed to auto-generate tasks for {cims_incident_id}: {str(task_error)}")
                    
                    except Exception as e:
                        logger.error(f"Error processing incident {incident.get('Id', 'unknown')}: {str(e)}")
                        continue
                
                conn.commit()
                
                # Update last sync time per site
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (
                    f'last_sync_{site_name.lower().replace(" ", "_")}',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
                conn.close()
                
                logger.info(f"✅ {site_name}: {total_synced} new, {total_updated} updated")
                
            except Exception as e:
                logger.error(f"Error syncing incidents from {site_name}: {str(e)}")
                continue
        
        logger.info(f"Incident sync completed: {total_synced} new, {total_updated} updated")
        
        # Update overall last sync time (for frontend event trigger)
        sync_completion_time = datetime.now().isoformat()
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES ('last_incident_sync_time', ?, ?)
            """, (sync_completion_time, sync_completion_time))
            conn.commit()
            
            # Set sync completion event flag (so frontend can detect it)
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES ('sync_completion_event', ?, ?)
            """, (sync_completion_time, sync_completion_time))
            conn.commit()
            conn.close()
            logger.info(f"✅ last_incident_sync_time updated: {sync_completion_time}")
            logger.info(
                f"📡 Sync completion event emitted: {sync_completion_time} (frontend will detect and auto-refresh)"
            )
        except Exception as e:
            logger.error(f"❌ Failed to update last_incident_sync_time: {e}")
        
        # 🚀 Generate tasks for Fall incidents without tasks after background sync completes
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Query Open status Fall incidents without tasks
            cursor.execute("""
                SELECT i.id, i.incident_id, i.incident_date, i.incident_type
                FROM cims_incidents i
                LEFT JOIN cims_tasks t ON i.id = t.incident_id
                WHERE i.status = 'Open'
                AND LOWER(i.incident_type) LIKE '%fall%'
                AND t.id IS NULL
                ORDER BY i.incident_date DESC
                LIMIT 50
            """)
            
            fall_incidents_without_tasks = cursor.fetchall()
            
            if fall_incidents_without_tasks:
                logger.info(
                    f"🔍 {len(fall_incidents_without_tasks)} fall incidents have no tasks - starting auto-generation..."
                )
                tasks_generated = 0
                
                for incident_row in fall_incidents_without_tasks:
                    incident_db_id = incident_row[0]
                    incident_id = incident_row[1]
                    incident_date_iso = incident_row[2]
                    incident_type = incident_row[3]
                    
                    try:
                        num_tasks = auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor)
                        if num_tasks > 0:
                            tasks_generated += num_tasks
                            logger.info(f"✅ Incident {incident_id}: {num_tasks} tasks created")
                    except Exception as task_error:
                        logger.warning(f"⚠️ Incident {incident_id} task creation failed: {task_error}")
                
                if tasks_generated > 0:
                    conn.commit()
                    logger.info(f"✅ Total tasks created: {tasks_generated}")
                else:
                    conn.rollback()
            
            conn.close()
        except Exception as task_gen_error:
            logger.error(f"❌ Error during background task generation: {task_gen_error}")
        
        return {'success': True, 'synced': total_synced, 'updated': total_updated}
        
    except Exception as e:
        logger.error(f"Error in sync_incidents_from_manad_to_cims: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/api/cims/force-sync', methods=['POST'])
@login_required
def force_sync_all():
    """
    Force Synchronization - Full DB forced synchronization
    - Synchronize incidents from all sites
    - Auto-generate missing tasks for Fall incidents
    - Progress note synchronization
    - Incident status update
    
    Available only to Admin/Clinical Manager
    """
    try:
        if not (current_user.is_admin() or current_user.role == 'clinical_manager'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        logger.info(f"🔄 Force Sync initiated by {current_user.username}")
        
        # 1. Full incident sync (30 days)
        logger.info("1️⃣  Full incident sync (30 days)...")
        sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
        
        # 2. Check for Fall incidents without tasks and generate them
        logger.info("2️⃣  Checking for Fall incidents without tasks...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.id, i.incident_id, i.incident_date, i.incident_type
            FROM cims_incidents i
            WHERE i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            AND NOT EXISTS (
                SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id
            )
        """)
        
        incidents_without_tasks = cursor.fetchall()
        tasks_generated = 0
        
        for inc in incidents_without_tasks:
            try:
                num_tasks = auto_generate_fall_tasks(inc[0], inc[2], cursor)
                tasks_generated += num_tasks
                logger.info(f"✅ Generated {num_tasks} tasks for {inc[1]}")
            except Exception as e:
                logger.error(f"Failed to generate tasks for {inc[1]}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Generated {tasks_generated} tasks for {len(incidents_without_tasks)} incidents")
        
        # 3. Progress note sync
        logger.info("3️⃣  Progress note sync...")
        # Progress Note synchronization is temporarily disabled (will be reimplemented with DB direct access later)
        # pn_sync_result = sync_progress_notes_from_manad_to_cims()
        
        # 4. Update incident statuses
        logger.info("4️⃣  Updating incident statuses...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT i.id
            FROM cims_incidents i
            JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.status IN ('Open', 'Overdue')
        """)
        
        incidents_to_update = cursor.fetchall()
        updated_count = 0
        
        for inc in incidents_to_update:
            try:
                check_and_update_incident_status(inc[0])
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update status for incident {inc[0]}: {str(e)}")
        
        conn.close()
        
        logger.info(f"✅ Updated status for {updated_count} incidents")
        
        return jsonify({
            'success': True,
            'message': 'Force sync completed successfully',
            'details': {
                'incidents_synced': sync_result.get('synced', 0),
                'incidents_updated': sync_result.get('updated', 0),
                'tasks_generated': tasks_generated,
                'incidents_with_new_tasks': len(incidents_without_tasks),
                'statuses_updated': updated_count
            }
        })
        
    except Exception as e:
        logger.error(f"Force sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_cims_incidents():
    """Query incident list (all statuses included, with auto synchronization)"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Check request parameters
        force_sync = request.args.get('sync', 'false').lower() == 'true'
        full_sync = request.args.get('full', 'false').lower() == 'true'  # Full sync (30 days)
        
        # Check last sync time (use read-only connection to prevent lock conflicts)
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        # Check incident count (detect initial load)
        cursor.execute("SELECT COUNT(*) FROM cims_incidents")
        incident_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync_result = cursor.fetchone()
        
        # Auto initial sync conditions:
        # 1. Force sync request
        # 2. Or when there are no incidents and sync has never been performed
        should_sync = force_sync or (incident_count == 0 and not last_sync_result)
        
        # Switch to full sync if initial sync
        if incident_count == 0 and not last_sync_result and should_sync:
            full_sync = True
            logger.info(f"🆕 Initial load detected - starting automatic full sync (incidents: {incident_count})")
        
        # Execute sync if needed (in background)
        if should_sync:
            # Update sync time first (prevent duplicate execution)
            # Use write connection only when write is needed
            conn.close()
            conn = get_db_connection(read_only=False)
            cursor = conn.cursor()
            with write_lock():
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                    VALUES ('last_incident_sync_time', ?, ?)
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                conn.commit()
            
            # Execute sync in background thread (doesn't block page loading)
            import threading
            def background_sync():
                try:
                    sync_type = "Full sync (30 days)" if full_sync else "Incremental sync"
                    logger.info(f"🔄 Starting background sync: {sync_type}")
                    sync_result = sync_incidents_from_manad_to_cims(full_sync=full_sync)
                    
                    # Progress Note synchronization is temporarily disabled (will be reimplemented with DB direct access later)
                    # logger.info("🔄 Starting Progress Note sync...")
                    # pn_sync_result = sync_progress_notes_from_manad_to_cims()
                    
                    logger.info(f"✅ Background sync completed: Incidents={sync_result}")
                except Exception as e:
                    logger.error(f"❌ Background sync error: {e}")
            
            sync_thread = threading.Thread(target=background_sync, daemon=True)
            sync_thread.start()
            logger.info("⚡ Background sync started (page load continues immediately...)")
        
        # Check filter parameters
        site_filter = request.args.get('site')
        date_filter = request.args.get('date')
        
        # 🔧 Modified: Query directly from MANAD DB to match KPI
        # Dashboard KPI uses direct MANAD DB queries, so incident list is handled the same way
        # This ensures data consistency between production/development servers
        use_db_direct = True  # Use direct MANAD DB query (matches KPI)
        
        # Commented out: Original DB direct access mode check logic (not currently used)
        # try:
        #     conn_check = get_db_connection(read_only=True)
        #     cursor_check = conn_check.cursor()
        #     cursor_check.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
        #     result = cursor_check.fetchone()
        #     conn_check.close()
        #     
        #     if result and result[0]:
        #         use_db_direct = result[0].lower() == 'true'
        #     else:
        #         use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        # except:
        #     use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
        incidents = []
        
        if use_db_direct:
            # 🔌 DB direct access mode: Query latest incidents from MANAD DB
            # ⚠️ Note: This mode may cause inconsistencies as data source differs from KPI
            logger.info("🔌 Direct DB access mode: integrated_dashboard incident query")
            
            try:
                from manad_db_connector import fetch_incidents_with_client_data_from_db
                
                # Set date range (last 30 days, or according to filter)
                if date_filter:
                    date_obj = datetime.fromisoformat(date_filter)
                    five_days_before = date_obj - timedelta(days=5)
                    start_date = five_days_before.strftime('%Y-%m-%d')
                else:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                # Query by site
                safe_site_servers = get_safe_site_servers()
                sites_to_query = [site_filter] if site_filter else list(safe_site_servers.keys())
                
                all_manad_incidents = []
                for site_name in sites_to_query:
                    if site_name not in safe_site_servers:
                        continue
                    
                    try:
                        incidents_data = fetch_incidents_with_client_data_from_db(
                            site_name, start_date, end_date, fetch_clients=False
                        )
                        
                        if incidents_data and incidents_data.get('incidents'):
                            for inc in incidents_data['incidents']:
                                # Convert MANAD incident to CIMS format
                                incident_date_str = inc.get('Date', inc.get('ReportedDate', ''))
                                if incident_date_str:
                                    try:
                                        incident_date = datetime.fromisoformat(incident_date_str.replace('Z', '+00:00'))
                                        incident_date_iso = incident_date.isoformat()
                                    except:
                                        incident_date_iso = datetime.now().isoformat()
                                else:
                                    incident_date_iso = datetime.now().isoformat()
                                
                                # Query existing incident from CIMS DB (includes Task information)
                                conn_cims = get_db_connection(read_only=True)
                                cursor_cims = conn_cims.cursor()
                                cursor_cims.execute("""
                                    SELECT id, incident_id, status, fall_type
                                    FROM cims_incidents
                                    WHERE manad_incident_id = ?
                                """, (str(inc.get('Id', '')),))
                                existing = cursor_cims.fetchone()
                                conn_cims.close()
                                
                                # Determine status: Use status from CIMS DB if exists, otherwise Open
                                status = existing[2] if existing else 'Open'
                                cims_id = existing[0] if existing else None
                                fall_type = existing[3] if existing and len(existing) > 3 else None
                                
                                # Include all statuses (to match KPI)
                                # Display Open, Closed, In Progress, Overdue
                                
                                # Process incident type
                                event_type = inc.get('EventTypeNames', '')
                                if isinstance(event_type, list):
                                    incident_type = ', '.join(event_type)
                                else:
                                    incident_type = str(event_type) if event_type else 'Unknown'
                                
                                # Location information
                                room = inc.get('RoomName', '')
                                wing = inc.get('WingName', '')
                                dept = inc.get('DepartmentName', '')
                                location_parts = [p for p in [room, wing, dept] if p]
                                location = ', '.join(location_parts) if location_parts else 'Unknown'
                                
                                # Resident name
                                resident_name = f"{inc.get('FirstName', '')} {inc.get('LastName', '')}".strip()
                                if not resident_name:
                                    resident_name = 'Unknown'
                                
                                # Convert to CIMS format tuple (compatible with existing code)
                                incidents.append((
                                    cims_id,  # id (CIMS DB ID, None if not exists)
                                    f"INC-{inc.get('Id', '')}",  # incident_id
                                    str(inc.get('ClientId', '')),  # resident_id
                                    resident_name,  # resident_name
                                    incident_type,  # incident_type
                                    inc.get('SeverityRating') or inc.get('RiskRatingName') or 'Unknown',  # severity
                                    status,  # status
                                    incident_date_iso,  # incident_date
                                    location,  # location
                                    inc.get('Description', ''),  # description
                                    site_name,  # site
                                    datetime.now().isoformat()  # created_at (temporary)
                                ))
                    except Exception as site_error:
                        logger.error(f"❌ Incident query failed for {site_name}: {site_error}")
                        continue
                
                logger.info(f"✅ Direct DB access: fetched {len(incidents)} incidents")
                
            except Exception as db_error:
                logger.error(f"❌ Direct DB access failed: {db_error}")
                # Fallback: Query from CIMS DB
                use_db_direct = False
        
        if not use_db_direct:
            # ✅ Query from CIMS DB (use same data source as KPI)
            # Include all statuses (to match KPI)
            # Remove date filter (filter on client side)
            # Use same data source to match KPI
            query = """
                SELECT id, incident_id, resident_id, resident_name, incident_type, severity, status, 
                       incident_date, location, description, site, created_at
                FROM cims_incidents 
                WHERE status IS NOT NULL
            """
            params = []
            
            if site_filter:
                query += " AND site = ?"
                params.append(site_filter)
            
            # Remove date filter: filter on client side (matches KPI)
            
            query += " ORDER BY incident_date DESC LIMIT 1000"
            
            # Re-execute query with read-only connection + simple retry
            try:
                conn.close()
            except Exception:
                pass
            conn = get_db_connection(read_only=True)
            cursor = conn.cursor()
            for attempt in range(5):
                try:
                    cursor.execute(query, params)
                    break
                except sqlite3.OperationalError as e:
                    if 'database is locked' in str(e) and attempt < 4:
                        time.sleep(0.25 * (attempt + 1))
                        continue
                    logger.error("Open incident query error: database is locked (fallback)")
                    return jsonify({'incidents': [], 'stale': True}), 200
            
            incidents = cursor.fetchall()
            conn.close()
        
        # Convert to list of dictionaries (use frontend-compatible field names)
        result = []
        
        # Create cursor for Fall type detection
        conn_fall = get_db_connection(read_only=True)
        try:
            cursor_fall = conn_fall.cursor()
            
            for incident in incidents:
                # Convert incident_type to EventTypeNames array
                incident_types = incident[4].split(', ') if incident[4] else []
                
                # Detect Fall type (only for Fall incidents)
                fall_type = None
                if incident[4] and 'fall' in incident[4].lower():
                    from services.fall_policy_detector import fall_detector
                    
                    # Query from DB if CIMS DB ID exists
                    if incident[0] is not None:  # if cims_id exists
                        fall_type = fall_detector.detect_fall_type_from_incident(
                            incident[0],  # incident_id (CIMS DB ID)
                            cursor_fall
                        )
                        
                        # Save calculated fall_type to DB
                        if fall_type and fall_type != 'unknown':
                            try:
                                cursor_fall.execute("""
                                    UPDATE cims_incidents
                                    SET fall_type = ?
                                    WHERE id = ? AND (fall_type IS NULL OR fall_type = '')
                                """, (fall_type, incident[0]))
                                cursor_fall.connection.commit()
                            except:
                                pass
                    else:
                        # If CIMS DB ID doesn't exist (new incident in DB direct access mode)
                        # Detect directly from Description
                        description = incident[9] if len(incident) > 9 else ''
                        fall_type = fall_detector.detect_fall_type_from_notes(description) if description else 'unknown'
                
                result.append({
                    'id': incident[0],
                    'incident_id': incident[1],
                    'resident_id': incident[2],
                    'resident_name': incident[3],
                    'incident_type': incident[4],  # Backward compatibility
                    'EventTypeNames': incident_types,  # Format expected by frontend
                    'severity': incident[5],
                    'status': incident[6],
                    'incident_date': incident[7],
                    'location': incident[8],
                    'description': incident[9],
                    'site': incident[10],  # Backward compatibility
                    'SiteName': incident[10],  # Format expected by frontend
                    'created_at': incident[11],
                    'fall_type': fall_type  # Add Fall type information
                })
        finally:
            conn_fall.close()
        
        logger.info(f"📤 API response: returning {len(result)} incidents (all statuses)")
        return jsonify({'incidents': result, 'stale': False})
        
    except Exception as e:
        logger.error(f"Open incident query error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def create_cims_incident():
    """API to create new incident"""
    try:
        if not current_user.can_manage_incidents():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['resident_id', 'resident_name', 'incident_type', 'severity', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate incident ID
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Save incident
        cursor.execute("""
            INSERT INTO cims_incidents (
                incident_id, resident_id, resident_name, incident_type, severity,
                status, incident_date, location, description, initial_actions_taken,
                witnesses, reported_by, site, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id,
            data['resident_id'],
            data['resident_name'],
            data['incident_type'],
            data['severity'],
            'Open',
            datetime.now().isoformat(),
            data.get('location', ''),
            data['description'],
            data.get('initial_actions', ''),
            data.get('witnesses', ''),
            current_user.id,
            data.get('site', 'Unknown'),
            datetime.now().isoformat()
        ))
        
        incident_db_id = cursor.lastrowid
        conn.commit()
        
        # Prepare incident data
        incident_data = {
            'id': incident_db_id,
            'incident_id': incident_id,
            'type': data['incident_type'],
            'severity': data['severity'],
            'incident_date': datetime.now().isoformat(),
            'resident_id': data['resident_id'],
            'resident_name': data['resident_name']
        }
        
        # Auto-generate tasks through policy engine
        generated_tasks = policy_engine.apply_policies_to_incident(incident_data)
        
        # Add audit log
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'incident_created',
            'incident',
            incident_db_id,
            json.dumps({
                'incident_type': data['incident_type'],
                'severity': data['severity'],
                'tasks_generated': len(generated_tasks)
            })
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'tasks_generated': len(generated_tasks),
            'message': f'Incident created successfully with {len(generated_tasks)} tasks generated'
        })
        
    except Exception as e:
        logger.error(f"CIMS incident create API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_cims_task(task_id):
    """API to complete task"""
    try:
        if not current_user.can_complete_tasks():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        completion_notes = data.get('notes', '')
        
        # Process task completion
        success = policy_engine.complete_task(task_id, current_user.id, completion_notes)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to complete task'
            }), 500
        
    except Exception as e:
        logger.error(f"CIMS task completion API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/progress-notes', methods=['POST'])
@login_required
def create_cims_progress_note():
    """API to create progress note"""
    try:
        if not current_user.can_complete_tasks():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['incident_id', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate progress note ID
        note_id = f"NOTE-{uuid.uuid4().hex[:8].upper()}"
        
        # Save progress note
        cursor.execute("""
            INSERT INTO cims_progress_notes (
                note_id, incident_id, task_id, author_id, content, note_type,
                vitals_data, assessment_data, attachments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id,
            data['incident_id'],
            data.get('task_id'),
            current_user.id,
            data['content'],
            data.get('note_type', ''),
            json.dumps(data.get('vitals_data', {})),
            json.dumps(data.get('assessment_data', {})),
            json.dumps(data.get('attachments', [])),
            datetime.now().isoformat()
        ))
        
        note_db_id = cursor.lastrowid
        
        # Mark task as completed if task_id exists
        if data.get('task_id'):
            completed_at = datetime.now().isoformat()
            cursor.execute("""
                UPDATE cims_tasks
                SET status = 'completed',
                    completed_by_user_id = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (current_user.id, completed_at, completed_at, data['task_id']))
            
            logger.info(f"✅ Task {data['task_id']} marked as completed via progress note")
        
        # Add audit log
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'progress_note_created',
            'progress_note',
            note_db_id,
            json.dumps({
                'incident_id': data['incident_id'],
                'task_id': data.get('task_id'),
                'note_type': data.get('note_type', '')
            })
        ))
        
        conn.commit()
        conn.close()
        
        # Check and update incident status
        if data.get('task_id'):
            check_and_update_incident_status(data['incident_id'])
        
        return jsonify({
            'success': True,
            'note_id': note_id,
            'message': 'Progress note created successfully'
        })
        
    except Exception as e:
        logger.error(f"CIMS progress note create API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def check_and_update_incident_status(incident_id):
    """
    Check all task statuses for incident and update incident status
    - Change to 'Closed' if all tasks are completed
    - Change to 'Overdue' if last task due time has passed but there are incomplete tasks
    - Includes retry logic for DB locks
    """
    import time
    import sqlite3
    
    max_retries = 3
    retry_delay = 0.5  # Start from 0.5 seconds
    
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            conn.execute("PRAGMA busy_timeout = 5000")  # Set 5 second timeout
            cursor = conn.cursor()
            
            # Query all tasks for that incident
            cursor.execute("""
                SELECT id, status, due_date
                FROM cims_tasks
                WHERE incident_id = ?
                ORDER BY due_date DESC
            """, (incident_id,))
            tasks = cursor.fetchall()
            
            if not tasks:
                conn.close()
                return
            
            # Analyze task status
            all_completed = all(task[1] == 'completed' for task in tasks)
            now = datetime.now()
            last_task_due = datetime.fromisoformat(tasks[0][2]) if tasks[0][2] else None
            
            # Update incident status
            if all_completed:
                # All tasks completed → Closed
                cursor.execute("""
                    UPDATE cims_incidents
                    SET status = 'Closed'
                    WHERE id = ?
                """, (incident_id,))
                logger.info(f"✅ Incident {incident_id} closed: All tasks completed")
            elif last_task_due and now > last_task_due and not all_completed:
                # Last task due time passed but incomplete → Overdue
                cursor.execute("""
                    UPDATE cims_incidents
                    SET status = 'Overdue'
                    WHERE id = ?
                """, (incident_id,))
                logger.info(f"⏰ Incident {incident_id} marked as overdue")
            
            conn.commit()
            conn.close()
            return  # Exit on success
            
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                logger.warning(
                    f"⏳ Retrying incident status update ({attempt + 1}/{max_retries}): Incident {incident_id} - DB locked"
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            else:
                logger.error(f"Incident status update error: Incident {incident_id} - {str(e)}")
                return
        except Exception as e:
            logger.error(f"Incident status update error: Incident {incident_id} - {str(e)}")
            return

@app.route('/api/cims/dashboard-kpis')
@login_required
def get_dashboard_kpis():
    """
    Dashboard KPI calculation API - Direct query from MANAD DB
    
    Changes:
    - Query directly from MANAD DB instead of CIMS DB
    - Ensure real-time data
    - Ensure data consistency between development/production servers
    """
    try:
        # Check permissions
        user_role = current_user.role if current_user.is_authenticated else None
        is_admin = current_user.is_admin() if current_user.is_authenticated else False
        
        logger.info(f"Dashboard KPI request - User: {current_user.username if current_user.is_authenticated else 'Anonymous'}, Role: {user_role}, Is Admin: {is_admin}")
        
        if not (is_admin or user_role in ['clinical_manager', 'doctor']):
            logger.warning(f"Access denied for user {current_user.username if current_user.is_authenticated else 'Anonymous'} with role {user_role}")
            return jsonify({'error': 'Access denied', 'user_role': user_role}), 403
        
        # Filter parameters
        period = request.args.get('period', 'week')  # today, week, month
        incident_type = request.args.get('incident_type', 'all')  # all, Fall, Wound/Skin, etc.
        
        logger.info(f"Fetching KPI data from MANAD DB: period={period}, incident_type={incident_type}")
        
        # Period filter
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = now.strftime('%Y-%m-%d')
        
        logger.info(f"Date filter: period={period}, start_date={start_date_str}, end_date={end_date_str}")
        
        # Query incidents from all sites in MANAD DB
        from manad_db_connector import MANADDBConnector
        safe_site_servers = get_safe_site_servers()
        
        all_incidents = []
        for site_name in safe_site_servers.keys():
            try:
                connector = MANADDBConnector(site_name)
                success, incidents = connector.fetch_incidents(start_date_str, end_date_str)
                if success and incidents:
                    # Add site information
                    for incident in incidents:
                        incident['site'] = site_name
                    all_incidents.extend(incidents)
                    logger.debug(f"✅ {site_name}: {len(incidents)} incidents")
            except Exception as site_error:
                logger.warning(f"⚠️ Failed to fetch incidents from {site_name}: {site_error}")
                continue
        
        logger.info(f"📊 Total incidents from MANAD DB: {len(all_incidents)}")
        
        # Apply incident type filter
        if incident_type != 'all':
            filtered_incidents = []
            for incident in all_incidents:
                event_type = incident.get('EventTypeName', '').lower()
                if incident_type == 'fall' and 'fall' in event_type:
                    filtered_incidents.append(incident)
                elif incident_type == 'wound' and ('wound' in event_type or 'skin' in event_type):
                    filtered_incidents.append(incident)
                elif incident_type == 'medication' and 'medication' in event_type:
                    filtered_incidents.append(incident)
                elif incident_type == 'behaviour' and ('behaviour' in event_type or 'behavior' in event_type):
                    filtered_incidents.append(incident)
                elif incident_type == 'other':
                    if 'fall' not in event_type and 'wound' not in event_type and 'skin' not in event_type and 'medication' not in event_type and 'behaviour' not in event_type and 'behavior' not in event_type:
                        filtered_incidents.append(incident)
            all_incidents = filtered_incidents
        
        # Apply date filter (data from MANAD DB is already filtered, but double-check)
        filtered_by_date = []
        for incident in all_incidents:
            incident_date = incident.get('Date') or incident.get('ReportedDate')
            if incident_date:
                try:
                    if isinstance(incident_date, str):
                        incident_dt = datetime.fromisoformat(incident_date.replace('Z', '+00:00'))
                    else:
                        incident_dt = incident_date
                    if incident_dt >= start_date:
                        filtered_by_date.append(incident)
                except:
                    # Include if date parsing fails
                    filtered_by_date.append(incident)
            else:
                # Don't include if no date
                pass
        all_incidents = filtered_by_date
        
        # ==========================================
        # 1. Incident status statistics (based on StatusEnumId)
        # StatusEnumId: 0=Open, 1=In Progress, 2=Closed
        # ==========================================
        total_incidents = len(all_incidents)
        open_incidents = 0
        in_progress_incidents = 0
        closed_incidents = 0
        other_status_incidents = 0
        
        for incident in all_incidents:
            status_enum_id = incident.get('StatusEnumId')
            if status_enum_id == 0:
                open_incidents += 1
            elif status_enum_id == 2:
                closed_incidents += 1
            elif status_enum_id == 1:
                in_progress_incidents += 1
            else:
                other_status_incidents += 1
        
        logger.info(f"KPI Query Result: total={total_incidents}, open={open_incidents}, in_progress={in_progress_incidents}, closed={closed_incidents}, other={other_status_incidents}")
        
        # ==========================================
        # 2. Fall count
        # ==========================================
        fall_count = 0
        for incident in all_incidents:
            event_type = incident.get('EventTypeName', '').lower()
            if 'fall' in event_type:
                fall_count += 1
        
        logger.info(f"Fall count query result: {fall_count}")
        
        # ==========================================
        # 3. Calculate Compliance Rate (Closed / Total * 100)
        # ==========================================
        if total_incidents > 0:
            compliance_rate = round((closed_incidents / total_incidents) * 100, 1)
        else:
            compliance_rate = 0
        
        # ==========================================
        # 4. Return response
        # ==========================================
        return jsonify({
            'total_incidents': total_incidents,
            'closed_incidents': closed_incidents,
            'open_incidents': open_incidents,
            'in_progress_incidents': in_progress_incidents,
            'fall_count': fall_count,
            'compliance_rate': compliance_rate,
            'period': period,
            'incident_type': incident_type
        })
        
    except Exception as e:
        logger.error(f"Dashboard KPI query error: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'trace': error_trace if app.config.get('DEBUG', False) else None
        }), 500


@app.route('/api/cims/dashboard-stats')
@login_required
def get_dashboard_stats():
    """
    Dashboard statistics API - Chart data (Direct query from MANAD DB)
    
    Changes:
    - Query directly from MANAD DB instead of CIMS DB
    - Ensure real-time data
    - Ensure data consistency between development/production servers
    
    Return data:
    - All sites statistics: Event type, Risk Rating, Severity Rating distribution
    - Per-site statistics: Open/Closed, Reviewed status
    - Additional KPIs: Ambulance, Hospital, Major Injury, etc.
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        period = request.args.get('period', 'week')
        
        # Period filter
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = now.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching dashboard stats from MANAD DB: period={period}, start_date={start_date_str}")
        
        # Query incidents from all sites in MANAD DB
        from manad_db_connector import MANADDBConnector
        safe_site_servers = get_safe_site_servers()
        
        all_incidents = []
        for site_name in safe_site_servers.keys():
            try:
                connector = MANADDBConnector(site_name)
                success, incidents = connector.fetch_incidents(start_date_str, end_date_str)
                if success and incidents:
                    # Add site information
                    for incident in incidents:
                        incident['site'] = site_name
                    all_incidents.extend(incidents)
            except Exception as site_error:
                logger.warning(f"⚠️ Failed to fetch incidents from {site_name}: {site_error}")
                continue
        
        logger.info(f"📊 Total incidents from MANAD DB: {len(all_incidents)}")
        
        # Apply date filter
        filtered_incidents = []
        for incident in all_incidents:
            incident_date = incident.get('Date') or incident.get('ReportedDate')
            if incident_date:
                try:
                    if isinstance(incident_date, str):
                        incident_dt = datetime.fromisoformat(incident_date.replace('Z', '+00:00'))
                    else:
                        incident_dt = incident_date
                    if incident_dt >= start_date:
                        filtered_incidents.append(incident)
                except:
                    pass
        all_incidents = filtered_incidents
        
        # ==========================================
        # 1. Event type distribution (Event Type Distribution)
        # ==========================================
        event_type_counts = {}
        for incident in all_incidents:
            event_type = incident.get('EventTypeName', '').lower()
            if 'fall' in event_type:
                category = 'Fall'
            elif 'wound' in event_type or 'skin' in event_type:
                category = 'Wound/Skin'
            elif 'medication' in event_type:
                category = 'Medication'
            elif 'behaviour' in event_type or 'behavior' in event_type:
                category = 'Behaviour'
            elif 'danger' in event_type:
                category = 'Danger'
            else:
                category = 'Other'
            event_type_counts[category] = event_type_counts.get(category, 0) + 1
        
        event_type_distribution = [{'name': k, 'value': v} for k, v in sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True)]
        
        # ==========================================
        # 2. Risk Rating distribution
        # ==========================================
        risk_counts = {}
        for incident in all_incidents:
            risk = incident.get('RiskRatingName', '') or 'Not Set'
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        risk_distribution = [{'name': k, 'value': v} for k, v in sorted(risk_counts.items(), key=lambda x: x[1], reverse=True)]
        
        # ==========================================
        # 3. Severity Rating distribution
        # ==========================================
        severity_counts = {}
        for incident in all_incidents:
            severity = incident.get('SeverityRating', '') or 'Not Set'
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        severity_distribution = [{'name': k, 'value': v} for k, v in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True)]
        
        # ==========================================
        # 4. Per-site Open/Closed statistics
        # ==========================================
        site_stats = {}
        for incident in all_incidents:
            site = incident.get('site', 'Unknown')
            if site not in site_stats:
                site_stats[site] = {'open': 0, 'closed': 0, 'in_progress': 0, 'total': 0}
            
            status_enum_id = incident.get('StatusEnumId')
            if status_enum_id == 0:
                site_stats[site]['open'] += 1
            elif status_enum_id == 2:
                site_stats[site]['closed'] += 1
            elif status_enum_id == 1:
                site_stats[site]['in_progress'] += 1
            site_stats[site]['total'] += 1
        
        site_status_stats = [{'site': k, 'open': v['open'], 'closed': v['closed'], 'in_progress': v['in_progress'], 'total': v['total']} 
                            for k, v in sorted(site_stats.items(), key=lambda x: x[1]['total'], reverse=True)]
        
        # ==========================================
        # 5. Per-site Review statistics
        # ==========================================
        site_review = {}
        for incident in all_incidents:
            site = incident.get('site', 'Unknown')
            if site not in site_review:
                site_review[site] = {'reviewed': 0, 'not_reviewed': 0, 'total': 0}
            
            status_enum_id = incident.get('StatusEnumId')
            is_review_closed = incident.get('IsReviewClosed', False)
            
            # Reviewed: Closed incidents or IsReviewClosed = True
            if status_enum_id == 2 or is_review_closed:
                site_review[site]['reviewed'] += 1
            else:
                site_review[site]['not_reviewed'] += 1
            site_review[site]['total'] += 1
        
        site_review_stats = [{'site': k, 'reviewed': v['reviewed'], 'not_reviewed': v['not_reviewed'], 'total': v['total']} 
                            for k, v in sorted(site_review.items(), key=lambda x: x[1]['total'], reverse=True)]
        
        # ==========================================
        # 6. Additional KPI statistics
        # ==========================================
        ambulance_called = sum(1 for i in all_incidents if i.get('IsAmbulanceCalled', False))
        hospital_admitted = sum(1 for i in all_incidents if i.get('IsAdmittedToHospital', False))
        major_injuries = sum(1 for i in all_incidents if i.get('IsMajorInjury', False))
        
        reviewed_count = sum(1 for i in all_incidents if i.get('StatusEnumId') == 2 or i.get('IsReviewClosed', False))
        pending_review = len(all_incidents) - reviewed_count
        
        additional_kpis = {
            'ambulance_called': ambulance_called,
            'hospital_admitted': hospital_admitted,
            'major_injuries': major_injuries,
            'reviewed_count': reviewed_count,
            'pending_review': pending_review,
            'total': len(all_incidents)
        }
        
        # ==========================================
        # 7. Fall-specific statistics (Witnessed vs Unwitnessed)
        # ==========================================
        fall_stats = {'witnessed': 0, 'unwitnessed': 0, 'unknown': 0}
        for incident in all_incidents:
            event_type = incident.get('EventTypeName', '').lower()
            if 'fall' in event_type:
                is_witnessed = incident.get('IsWitnessed', None)
                if is_witnessed is True:
                    fall_stats['witnessed'] += 1
                elif is_witnessed is False:
                    fall_stats['unwitnessed'] += 1
                else:
                    fall_stats['unknown'] += 1
        
        fall_stats_list = [{'type': k, 'count': v} for k, v in fall_stats.items() if v > 0]
        
        return jsonify({
            'success': True,
            'period': period,
            'event_type_distribution': event_type_distribution,
            'risk_distribution': risk_distribution,
            'severity_distribution': severity_distribution,
            'site_status_stats': site_status_stats,
            'site_review_stats': site_review_stats,
            'additional_kpis': additional_kpis,
            'fall_stats': fall_stats_list
        })
        
    except Exception as e:
        logger.error(f"Dashboard Stats query error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/cims/reset-database', methods=['POST'])
@login_required
def reset_cims_database():
    """
    CIMS DB initialization API
    - Delete all CIMS-related table data
    - Search and clean up unnecessary columns
    - Execute initial forced synchronization
    """
    try:
        if not (current_user.is_admin() or current_user.role == 'clinical_manager'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        logger.info(f"🗑️ CIMS DB reset started - User: {current_user.username}")
        
        conn = get_db_connection(read_only=False)
        cursor = conn.cursor()
        
        reset_info = {
            'tables_cleared': [],
            'rows_deleted': {},
            'columns_checked': {},
            'sync_result': None
        }
        
        # 1. Delete CIMS-related table data (order matters: consider foreign key references)
        cims_tables = [
            'cims_audit_logs',
            'cims_progress_notes',
            'cims_tasks',
            'cims_incidents',
            'cims_notifications',
            'cims_task_assignments',
            'cims_dashboard_kpi_cache',
            'cims_cache_management',
            'cims_incident_summary_cache',
            'cims_site_analysis_cache',
            'cims_task_schedule_cache',
            'cims_user_task_cache'
        ]
        
        for table in cims_tables:
            try:
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    # Check data count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        # Delete data
                        cursor.execute(f"DELETE FROM {table}")
                        reset_info['tables_cleared'].append(table)
                        reset_info['rows_deleted'][table] = count
                        logger.info(f"✅ Deleted {count} rows from {table}")
                    else:
                        logger.info(f"ℹ️ {table} is already empty")
                else:
                    logger.warning(f"⚠️ Table {table} does not exist")
            except Exception as e:
                logger.error(f"❌ Error clearing {table}: {e}")
                reset_info['rows_deleted'][table] = f"Error: {str(e)}"
        
        # 2. Search and clean up unnecessary columns (cims_incidents table)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
            if cursor.fetchone():
                # Check table schema
                cursor.execute("PRAGMA table_info(cims_incidents)")
                columns = cursor.fetchall()
                
                # Expected column list (required columns)
                expected_columns = {
                    'id', 'incident_id', 'manad_incident_id', 'resident_id', 'resident_name',
                    'incident_type', 'severity', 'status', 'incident_date', 'location', 'description',
                    'initial_actions_taken', 'reported_by', 'reported_by_name', 'site', 'workflow_status',
                    'total_tasks', 'completed_tasks', 'policy_applied', 'closed_at', 'closed_by',
                    'created_at', 'updated_at', 'risk_rating', 'is_review_closed', 'is_ambulance_called',
                    'is_admitted_to_hospital', 'is_major_injury', 'reviewed_date', 'status_enum_id', 'fall_type'
                }
                
                actual_columns = {col[1] for col in columns}
                unexpected_columns = actual_columns - expected_columns
                
                reset_info['columns_checked'] = {
                    'total_columns': len(actual_columns),
                    'expected_columns': len(expected_columns),
                    'unexpected_columns': list(unexpected_columns) if unexpected_columns else []
                }
                
                if unexpected_columns:
                    logger.warning(f"⚠️ Unexpected columns found: {unexpected_columns}")
                    logger.info("ℹ️ Note: SQLite does not support DROP COLUMN directly. Manual migration may be needed.")
                else:
                    logger.info("✅ All columns are expected")
        except Exception as e:
            logger.error(f"❌ Error checking columns: {e}")
            reset_info['columns_checked'] = {'error': str(e)}
        
        # 3. Initialize CIMS-related sync times in system_settings
        try:
            cursor.execute("""
                DELETE FROM system_settings 
                WHERE key LIKE 'last_sync_%' OR key = 'last_incident_sync_time'
            """)
            deleted_settings = cursor.rowcount
            logger.info(f"✅ Cleared {deleted_settings} sync time settings")
            reset_info['sync_settings_cleared'] = deleted_settings
        except Exception as e:
            logger.error(f"❌ Error clearing sync settings: {e}")
        
        # 4. Commit
        conn.commit()
        conn.close()
        
        logger.info("✅ CIMS DB reset completed")
        
        # 5. Execute initial forced synchronization
        try:
            logger.info("🔄 Starting initial force sync after reset...")
            sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
            reset_info['sync_result'] = sync_result
            logger.info(f"✅ Initial sync completed: {sync_result}")
        except Exception as e:
            logger.error(f"❌ Error during initial sync: {e}")
            reset_info['sync_result'] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'message': 'CIMS database reset completed successfully',
            'details': reset_info
        })
        
    except Exception as e:
        logger.error(f"❌ CIMS DB reset error: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e),
            'trace': error_trace if app.config.get('DEBUG', False) else None
        }), 500


@app.route('/api/cims/schedule-batch/<site>/<date>')
@login_required
def get_schedule_batch(site, date):
    """
    🚀 Phase 2: Batch API - Return full schedule in a single call
    
    Query and return Incidents + Tasks + Policy in one go
    - Optimized for Mobile Dashboard
    - 99.9% reduction in DB queries (2328 → 3 calls)
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Query Incidents + Tasks together using JOIN
        date_obj = datetime.fromisoformat(date)
        five_days_before = (date_obj - timedelta(days=5)).isoformat()
        
        cursor.execute("""
            SELECT 
                i.id, i.incident_id, i.incident_type, i.incident_date,
                i.resident_name, i.resident_id, i.description,
                i.severity, i.status, i.location, i.site, i.fall_type,
                t.id as task_db_id, t.task_id, t.task_name, t.due_date, 
                t.status as task_status, t.completed_at, t.completed_by_user_id
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.site = ? 
            AND DATE(i.incident_date) >= DATE(?)
            AND i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            ORDER BY i.incident_date DESC, t.due_date ASC
        """, (site, five_days_before))
        
        rows = cursor.fetchall()
        
        # 2. Group by incidents
        incidents_map = {}
        for row in rows:
            incident_id = row[0]
            if incident_id not in incidents_map:
                incidents_map[incident_id] = {
                    'id': row[0],
                    'incident_id': row[1],
                    'incident_type': row[2],
                    'incident_date': row[3],
                    'resident_name': row[4],
                    'resident_id': row[5],
                    'description': row[6],
                    'severity': row[7],
                    'status': row[8],
                    'location': row[9],
                    'site': row[10],
                    'fall_type': row[11],  # Add Fall type
                    'tasks': []
                }
            
            # Add task if exists (index increases by 1)
            if row[12] is not None:  # task_db_id
                task_data = {
                    'id': row[12],
                    'task_id': row[13],
                    'task_name': row[14],
                    'due_date': row[15],
                    'status': row[16] or 'pending',  # 'pending' if NULL
                    'completed_at': row[17],
                    'completed_by': row[18]
                }
                incidents_map[incident_id]['tasks'].append(task_data)
                # Debug: task addition log
                if len(incidents_map[incident_id]['tasks']) <= 3:  # Log only first 3
                    logger.debug(f"Task added to incident {incident_id}: {task_data['task_id']} (due_date={task_data['due_date']}, status={task_data['status']})")
        
        # 2.5. Calculate and update Fall type (if NULL or empty)
        from services.fall_policy_detector import fall_detector
        
        for incident_data in incidents_map.values():
            if not incident_data['fall_type']:
                # Calculate Fall type (correct signature: incident_id, cursor)
                fall_type = fall_detector.detect_fall_type_from_incident(
                    incident_data['id'],  # incident DB ID
                    cursor  # DB cursor
                )
                
                # Update DB
                try:
                    cursor.execute("""
                        UPDATE cims_incidents 
                        SET fall_type = ? 
                        WHERE id = ?
                    """, (fall_type, incident_data['id']))
                    conn.commit()
                    
                    # Update incidents_map
                    incident_data['fall_type'] = fall_type
                    logger.info(f"📝 Incident {incident_data['incident_id']}: fall_type={fall_type} (calculated)")
                except Exception as update_err:
                    logger.warning(f"⚠️ Failed to update fall_type for incident {incident_data['incident_id']}: {update_err}")
        
        # 3. Query Fall Policy (return all Fall policies)
        cursor.execute("""
            SELECT id, policy_id, name, rules_json
            FROM cims_policies
            WHERE is_active = 1 AND policy_id LIKE 'FALL-%'
            ORDER BY policy_id
        """)
        
        policy_rows = cursor.fetchall()
        fall_policies = {}  # policy_code -> policy_data
        
        for policy_row in policy_rows:
            try:
                policy_code = policy_row[1]  # FALL-001-UNWITNESSED or FALL-002-WITNESSED
                rules = json.loads(policy_row[3])
                
                fall_policies[policy_code] = {
                    'id': policy_row[0],
                    'policy_id': policy_code,
                    'name': policy_row[2],
                    'rules': rules
                }
            except Exception as e:
                logger.warning(f"Failed to parse policy {policy_row[1]}: {e}")
                continue
        
        # Backwards compatibility: fall_policy is the first policy
        fall_policy = list(fall_policies.values())[0] if fall_policies else None
        
        logger.info(f"📋 Policies loaded: {list(fall_policies.keys())}")
        for policy_id, policy_data in fall_policies.items():
            schedule = policy_data['rules'].get('nurse_visit_schedule', [])
            logger.info(f"  - {policy_id}: {len(schedule)} phases")
        
        conn.close()
        
        total_tasks = sum(len(i['tasks']) for i in incidents_map.values())
        logger.info(f"🚀 Batch API: {site}/{date} - {len(incidents_map)} incidents, {total_tasks} tasks")
        
        # Debug: log task count per incident
        for inc_id, inc_data in list(incidents_map.items())[:5]:  # Only first 5
            logger.debug(f"  Incident {inc_data['incident_id']}: {len(inc_data['tasks'])} tasks")
        
        # Attempt auto-generation if no tasks and Fall incidents exist
        if len(incidents_map) > 0 and total_tasks == 0 and fall_policy:
            logger.info("💡 No tasks found - attempting auto-generation...")
            conn_gen = None
            try:
                conn_gen = get_db_connection()
                cursor_gen = conn_gen.cursor()
                
                tasks_generated = 0
                # Generate tasks for each incident
                for incident_data in incidents_map.values():
                    try:
                        num_tasks = auto_generate_fall_tasks(
                            incident_data['id'], 
                            incident_data['incident_date'], 
                            cursor_gen
                        )
                        tasks_generated += num_tasks
                        logger.info(f"✅ Incident {incident_data['incident_id']}: {num_tasks} tasks created")
                    except Exception as gen_err:
                        logger.warning(f"⚠️ Incident {incident_data['incident_id']} task creation failed: {gen_err}")
                
                conn_gen.commit()
                
                logger.info(f"✅ Total tasks created: {tasks_generated}")
                
            except Exception as e:
                logger.warning(f"⚠️ Task auto-generation failed: {e}")
                if conn_gen:
                    try:
                        conn_gen.rollback()
                    except:
                        pass
            finally:
                if conn_gen:
                    try:
                        conn_gen.close()
                    except:
                        pass
        
        # Debug: check policies keys
        logger.debug(f"📋 Policies keys in response: {list(fall_policies.keys())}")
        logger.debug(f"📋 Policies count: {len(fall_policies)}")
        
        return jsonify({
            'success': True,
            'incidents': list(incidents_map.values()),
            'policy': fall_policy,  # Backwards compatibility
            'policies': fall_policies,  # All Fall policies by policy_id (dict with policy_id as key)
            'site': site,
            'date': date,
            'cached': False,  # Change to True when server-side caching is enabled
            'timestamp': datetime.now().isoformat(),
            'auto_generated': total_tasks == 0 and len(incidents_map) > 0 and fall_policy  # Whether tasks were auto-generated
        })
        
    except Exception as e:
        logger.error(f"Batch API error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/incident/<int:incident_id>/tasks')
@login_required
def get_incident_tasks(incident_id):
    """API to query all tasks and completion status for incident"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tasks for the incident with completion status
        cursor.execute("""
            SELECT id, task_id, task_name, due_date, status, completed_at, completed_by_user_id
            FROM cims_tasks
            WHERE incident_id = ?
            ORDER BY due_date ASC
        """, (incident_id,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        result = []
        for task in tasks:
            result.append({
                'id': task[0],
                'task_id': task[1],
                'task_name': task[2],
                'due_date': task[3],
                'status': task[4],
                'completed_at': task[5],
                'completed_by': task[6]
            })
        
        return jsonify({'tasks': result})
        
    except Exception as e:
        logger.error(f"Incident tasks query error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/overdue-tasks')
@login_required
def get_overdue_tasks():
    """API to query overdue tasks (admin only)"""
    try:
        if not (current_user.is_admin() or current_user.is_clinical_manager()):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        overdue_tasks = policy_engine.get_overdue_tasks()
        
        return jsonify({
            'success': True,
            'tasks': overdue_tasks
        })
        
    except Exception as e:
        logger.error(f"Overdue tasks query API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/upcoming-tasks')
@login_required
def get_upcoming_tasks():
    """API to query tasks due soon"""
    try:
        hours_ahead = request.args.get('hours', 2, type=int)
        upcoming_tasks = policy_engine.get_upcoming_tasks(hours_ahead)
        
        return jsonify({
            'success': True,
            'tasks': upcoming_tasks
        })
        
    except Exception as e:
        logger.error(f"Tasks due soon query API error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Register CIMS API Blueprint
# ==============================

# Register CIMS API Blueprint
from cims_api_endpoints import cims_api
from cims_cache_api import cache_api
from cims_background_processor import start_background_processing, stop_background_processing
from memory_monitor import get_memory_monitor, start_memory_monitoring, stop_memory_monitoring
app.register_blueprint(cims_api)
app.register_blueprint(cache_api)

# ==============================
# CIMS Admin Dashboard Routes
# ==============================

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    """Legacy admin dashboard - redirects to integrated dashboard"""
    return redirect(url_for('integrated_dashboard'))

@app.route('/policy_admin')
@login_required
def policy_admin():
    """Policy management interface"""
    try:
        # Check admin permissions
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('policy_admin_interface.html', current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading policy management interface: {str(e)}")
        flash('Error loading policy management interface', 'error')
        return redirect(url_for('rod_dashboard'))

@app.route('/mobile_dashboard')
@login_required
def mobile_dashboard():
    """Mobile-optimized task dashboard"""
    try:
        # Check user permissions
        if not current_user.can_complete_tasks() and not current_user.is_admin():
            flash('Access denied. You do not have permission to access the task dashboard.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        # Check Policy and Tasks on initial load
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check Active Fall Policy
        cursor.execute("""
            SELECT COUNT(*) FROM cims_policies WHERE is_active = 1
        """)
        policy_count = cursor.fetchone()[0]
        
        # Check Fall incidents
        cursor.execute("""
            SELECT COUNT(*) FROM cims_incidents 
            WHERE incident_type LIKE '%Fall%' AND status IN ('Open', 'Overdue')
        """)
        fall_incident_count = cursor.fetchone()[0]
        
        # Check Tasks
        cursor.execute("SELECT COUNT(*) FROM cims_tasks")
        task_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Initialization needed if no policy or Fall incidents exist but no tasks
        needs_init = (policy_count == 0) or (fall_incident_count > 0 and task_count == 0)
        
        if needs_init:
            logger.info(
                f"🆕 Mobile Dashboard initialization needed - Policy: {policy_count}, Fall: {fall_incident_count}, Tasks: {task_count}"
            )
            logger.info(
                "💡 Tip: Run Force Synchronization on the Settings page to auto-create Policies and Tasks."
            )
        
        return render_template('mobile_task_dashboard.html', 
                             current_user=current_user,
                             needs_init=needs_init)
        
    except Exception as e:
        logger.error(f"Error loading mobile dashboard: {str(e)}")
        flash('Error loading mobile dashboard', 'error')
        return redirect(url_for('rod_dashboard'))

@app.route('/task_confirmation')
@login_required
def task_confirmation():
    """Task completion confirmation page"""
    try:
        # Check user permissions
        if not current_user.can_complete_tasks() and not current_user.is_admin():
            flash('Access denied. You do not have permission to complete tasks.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('task_completion_confirmation.html', current_user=current_user)
        
    except Exception as e:
        logger.error(f"Error loading task confirmation page: {str(e)}")
        flash('Error loading task confirmation page', 'error')
        return redirect(url_for('rod_dashboard'))

# ==============================
# CIMS Policy Management API Endpoints
# ==============================

@app.route('/api/cims/policies', methods=['GET'])
@login_required
def get_policies():
    """Query policy list"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, policy_id, name, description, version, effective_date, 
                   rules_json, is_active, created_at
            FROM cims_policies 
            ORDER BY created_at DESC
        """)
        
        policies = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(policy) for policy in policies])
        
    except Exception as e:
        logger.error(f"Error fetching policy list: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['GET'])
@login_required
def get_policy(policy_id):
    """Query specific policy"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cims_policies WHERE id = ?", (policy_id,))
        policy = cursor.fetchone()
        conn.close()
        
        if not policy:
            return jsonify({'error': 'Policy not found'}), 404
        
        return jsonify(dict(policy))
        
    except Exception as e:
        logger.error(f"Error fetching policy: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies', methods=['POST'])
@login_required
def create_policy():
    """Create new policy"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'version', 'rules_json']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generate policy ID
        policy_id = f"POL-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute("""
            INSERT INTO cims_policies (
                policy_id, name, description, version, effective_date, 
                rules_json, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy_id,
            data['name'],
            data.get('description', ''),
            data['version'],
            datetime.now().isoformat(),
            data['rules_json'],
            data.get('is_active', True),
            datetime.now().isoformat()
        ))
        
        new_policy_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': new_policy_id,
            'policy_id': policy_id,
            'message': 'Policy created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Policy creation error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['PUT'])
@login_required
def update_policy(policy_id):
    """Update policy"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if policy exists
        cursor.execute("SELECT id FROM cims_policies WHERE id = ?", (policy_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Policy not found'}), 404
        
        # Update policy
        cursor.execute("""
            UPDATE cims_policies 
            SET name = ?, description = ?, version = ?, rules_json = ?, is_active = ?
            WHERE id = ?
        """, (
            data.get('name'),
            data.get('description'),
            data.get('version'),
            data.get('rules_json'),
            data.get('is_active'),
            policy_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Policy updated successfully'})
        
    except Exception as e:
        logger.error(f"Policy update error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_policy(policy_id):
    """Delete policy"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if policy exists
        cursor.execute("SELECT id, policy_id, name FROM cims_policies WHERE id = ?", (policy_id,))
        policy = cursor.fetchone()
        
        if not policy:
            conn.close()
            return jsonify({'error': 'Policy not found'}), 404
        
        # Delete policy (actually safer to set is_active to False)
        # But use DELETE if complete deletion is desired
        cursor.execute("DELETE FROM cims_policies WHERE id = ?", (policy_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Policy deleted: {policy['name']} (ID: {policy_id})")
        return jsonify({'message': 'Policy deleted successfully'})
        
    except Exception as e:
        logger.error(f"Policy deletion error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# Integrated Dashboard Routes
# ==============================

@app.route('/integrated_dashboard')
@login_required
def integrated_dashboard():
    """Integrated dashboard - auto-switch by role"""
    try:
        # Check user role
        user_role = current_user.role if hasattr(current_user, 'role') else 'nurse'
        
        # Check permissions by role
        if user_role not in ['admin', 'clinical_manager', 'registered_nurse', 'nurse', 'carer']:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('integrated_dashboard.html', 
                             user_role=user_role,
                             current_user=current_user)
        
    except Exception as e:
        logger.error(f"Integrated dashboard error: {str(e)}")
        flash('Unable to load the dashboard.', 'error')
        return redirect(url_for('rod_dashboard'))

# ==============================
# Blueprint Registration
# ==============================

# Register Admin API Blueprint
app.register_blueprint(admin_api)
# Progress Notes Cached API Blueprint 등록 (DEFAULT_PERIOD_DAYS = default period for cached API; must match frontend PERIOD_OPTIONS[0])
from fetch_progress_notes_cached import progress_notes_cached_bp, DEFAULT_PERIOD_DAYS

app.register_blueprint(progress_notes_cached_bp)

# ==============================
# Multi-Site Callbell Monitor (modular system)
# ==============================
from callbell_monitor_multi import init_callbell_system, callbell_bp
app.register_blueprint(callbell_bp)
# Initialize callbell monitors
# To enable/disable monitors, modify the sites_to_monitor list:
#   ['parafield_gardens'] - Only Parafield (Ramsay OFF)
#   ['ramsay', 'parafield_gardens'] - Both sites
#   [] - All monitors disabled
init_callbell_system(app, sites_to_monitor=['ramsay', 'parafield_gardens'])

# ==============================
# App Execution
# ==============================

def start_periodic_sync():
    """Start periodic background synchronization scheduler (incremental sync every 5 minutes)"""
    
    def initial_sync_job():
        """Initial synchronization on server start (full 30 days)"""
        try:
            # Start initial sync after 5 second wait (wait for server to fully start)
            time.sleep(5)
            
            logger.info("=" * 60)
            logger.info("🚀 Server start - initial data sync started (last 30 days)")
            logger.info("=" * 60)
            
            sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
            
            logger.info(f"✅ Initial data sync completed: {sync_result}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ Initial data sync error: {e}")
    
    def periodic_sync_job():
        """Incremental synchronization job that runs every 10 minutes"""
        try:
            logger.info("=" * 60)
            logger.info("🔄 [PERIODIC SYNC] Starting periodic background sync (incremental)")
            logger.info(f"⏰ Sync start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
            
            sync_result = sync_incidents_from_manad_to_cims(full_sync=False)
            
            # Progress Note synchronization is temporarily disabled (will be reimplemented with DB direct access later)
            # logger.info("🔄 Starting Progress Note sync...")
            # pn_sync_result = sync_progress_notes_from_manad_to_cims()
            
            logger.info("=" * 60)
            logger.info(f"✅ [PERIODIC SYNC] Periodic background sync completed: Incidents={sync_result}")
            logger.info(f"⏰ Sync end time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ [PERIODIC SYNC] Periodic background sync error: {e}")
            logger.error("=" * 60)
    
    # Initial synchronization on server start (in background)
    initial_thread = threading.Thread(target=initial_sync_job, daemon=True)
    initial_thread.start()
    logger.info("🚀 Initial data sync thread started (runs after 5 seconds)")
    
    # Execute incremental sync every 10 minutes
    schedule.every(10).minutes.do(periodic_sync_job)
    
    def run_scheduler():
        """Scheduler execution loop"""
        logger.info("🔄 Periodic background sync scheduler started (every 10 minutes)")
        last_log_time = None
        while True:
            try:
                schedule.run_pending()
                
                # Log next sync time (once per minute)
                current_time = datetime.now()
                if last_log_time is None or (current_time - last_log_time).total_seconds() >= 60:
                    jobs = schedule.get_jobs()
                    if jobs:
                        next_run = jobs[0].next_run
                        if next_run:
                            time_until_next = (next_run - current_time).total_seconds()
                            minutes = int(time_until_next // 60)
                            seconds = int(time_until_next % 60)
                            logger.debug(
                                f"⏰ Next sync scheduled in {minutes}m {seconds}s ({next_run.strftime('%H:%M:%S')})"
                            )
                    last_log_time = current_time
                
                time.sleep(30)  # Check schedule every 30 seconds
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    # Run in background thread
    sync_thread = threading.Thread(target=run_scheduler, daemon=True)
    sync_thread.start()
    logger.info("✅ Periodic background sync scheduler started (every 10 minutes)")

if __name__ == '__main__':
    # CIMS Background Data Processor (optional)
    # Function: Generate Dashboard KPI cache (every 10 minutes) → Performance improvement
    # Development environment: Disabled (can check immediate response)
    # Production environment: Recommended to enable (set PROD_ENABLE_BACKGROUND_PROCESSOR=True in .env)
    if flask_config.get('ENABLE_BACKGROUND_PROCESSOR', False):
        try:
            start_background_processing()
            logger.info("✅ CIMS Background Processor started (improves dashboard performance)")
        except Exception as e:
            logger.warning(f"⚠️ Background Processor failed to start: {e}")
    # else: Don't output unnecessary messages in development environment
    
    # Start memory monitoring (detect memory leaks in development environment)
    try:
        start_memory_monitoring()
        logger.info("✅ Memory monitoring started")
    except Exception as e:
        logger.warning(f"⚠️ Failed to start memory monitoring: {e}")
    
    # Start periodic background synchronization (incremental sync every 5 minutes)
    try:
        start_periodic_sync()
    except Exception as e:
        logger.warning(f"⚠️ Failed to start periodic background sync: {e}")
    
    # MANAD Plus Integrator (background polling - optional)
    # Current: Incremental sync is sufficient (auto-syncs every 5 minutes on API calls)
    # Future: If real-time polling is needed, set 'manad_integrator_enabled'=true in system_settings
    # Note: Mostly unnecessary (incremental sync is more efficient)
    
    try:
        app.run(
            debug=flask_config['DEBUG'], 
            host=flask_config['HOST'],
            port=flask_config['PORT']
        )
    finally:
        # Stop memory monitoring
        try:
            stop_memory_monitoring()
            logger.info("Memory monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping memory monitoring: {e}")
        
        # Stop background processor when app shuts down (only if it was started)
        if flask_config.get('ENABLE_BACKGROUND_PROCESSOR', False):
            try:
                stop_background_processing()
                logger.info("Background data processor stopped")
            except Exception as e:
                logger.error(f"Error stopping background processor: {e}")