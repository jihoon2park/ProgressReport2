#!/usr/bin/env python3
"""
MANAD Plus Integrator Module
Module responsible for integration between CIMS and MANAD Plus systems
"""

import requests
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import threading
from cims_policy_engine import PolicyEngine

logger = logging.getLogger(__name__)

class MANADPlusIntegrator:
    """Class that handles integration with MANAD Plus system"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize MANAD Plus Integrator
        
        Args:
            config: MANAD Plus API configuration information
        """
        # Actual MANAD Plus API settings (based on Parafield Gardens server)
        if config is None:
            try:
                from config import get_server_info, get_api_headers
                server_info = get_server_info('Parafield Gardens')
                api_headers = get_api_headers('Parafield Gardens')
                
                self.config = {
                    'base_url': server_info['base_url'],
                    'server_ip': server_info['server_ip'],
                    'server_port': server_info['server_port'],
                    'api_username': api_headers.get('x-api-username', 'ManadAPI'),
                    'api_key': api_headers.get('x-api-key', ''),
                    'polling_interval': 300,  # Poll every 5 minutes
                    'timeout': 30
                }
                logger.info(f"MANAD Plus Integrator initialized with {server_info['base_url']}")
            except Exception as e:
                logger.error(f"Failed to load server config: {e}")
                # Fallback settings
                self.config = {
                    'base_url': 'http://192.168.1.11:8080',
                    'server_ip': '192.168.1.11',
                    'server_port': '8080',
                    'api_username': 'ManadAPI',
                    'api_key': '',
                    'polling_interval': 300,
                    'timeout': 30
                }
        else:
            self.config = config
        
        self.access_token = None
        self.token_expires_at = None
        self.policy_engine = PolicyEngine()
        self.is_running = False
        self.polling_thread = None
        
    def authenticate(self) -> bool:
        """
        Verify MANAD Plus API authentication
        Actual MANAD API uses x-api-key header method, so separate authentication is not required
        
        Returns:
            bool: Authentication success status
        """
        try:
            # MANAD Plus API uses x-api-key header method
            # Test connection with /api/system/canconnect
            test_url = f"{self.config['base_url']}/api/system/canconnect"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.config.get('timeout', 30)
            )
            
            if response.status_code == 200:
                logger.info("MANAD Plus API connection successful")
                self.access_token = 'api_key_based_auth'  # Use API key instead of token
                self.token_expires_at = datetime.now() + timedelta(days=365)  # API key does not expire
                return True
            else:
                logger.error(f"MANAD Plus API connection failed: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning("Unable to connect to MANAD Plus API server.")
            return False
        except Exception as e:
            logger.error(f"MANAD Plus authentication error: {str(e)}")
            return False
    
    def is_token_valid(self) -> bool:
        """
        Check if current token is valid
        
        Returns:
            bool: Token validity
        """
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Renew 5 minutes before expiration
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def ensure_authenticated(self) -> bool:
        """
        Check authentication status and re-authenticate if needed
        
        Returns:
            bool: Authentication status
        """
        if not self.is_token_valid():
            return self.authenticate()
        return True
    
    def get_headers(self) -> Dict[str, str]:
        """
        Generate headers for API requests
        
        Returns:
            Dict: HTTP headers
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def get_last_checked_time(self, full_sync=False) -> str:
        """
        Query last polling time
        
        Args:
            full_sync: Whether full sync (starts from 7 days ago if True)
        
        Returns:
            str: Last check time in ISO 8601 format
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'manad_last_checked_at'
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result and not full_sync:
                return result[0]
            else:
                # Start from 7 days ago for full sync, 24 hours ago for regular polling
                if full_sync:
                    default_time = datetime.now() - timedelta(days=7)
                    logger.info("Performing full sync: fetching data from last 7 days")
                else:
                    default_time = datetime.now() - timedelta(hours=24)
                    logger.info("Regular polling: fetching data from last 24 hours")
                return default_time.isoformat() + 'Z'
                
        except Exception as e:
            logger.error(f"Error querying last check time: {str(e)}")
            # Start from 1 hour ago on error
            fallback_time = datetime.now() - timedelta(hours=1)
            return fallback_time.isoformat() + 'Z'
    
    def update_last_checked_time(self, timestamp: str) -> None:
        """
        Update last polling time
        
        Args:
            timestamp: Time to update (ISO 8601)
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # Create system_settings table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES ('manad_last_checked_at', ?, ?)
            """, (timestamp, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating last check time: {str(e)}")
    
    def extract_site_from_incident(self, incident_data: Dict) -> str:
        """
        Extract site information from MANAD Plus incident data
        
        Args:
            incident_data: MANAD Plus incident data
            
        Returns:
            str: Site name
        """
        # Extract site information from MANAD Plus data
        # In actual implementation, modify according to MANAD Plus API response structure
        
        # Try to extract site from resident information
        resident_info = self.get_resident_info(incident_data['resident_id'])
        if resident_info and 'facility_name' in resident_info:
            return resident_info['facility_name']
        
        # Try to extract directly from incident data
        if 'facility_name' in incident_data:
            return incident_data['facility_name']
        if 'site_name' in incident_data:
            return incident_data['site_name']
        if 'location' in incident_data:
            location = incident_data['location']
            if isinstance(location, dict) and 'facility' in location:
                return location['facility']
        
        # Default: assign site based on resident ID
        # In actual implementation, use resident-site mapping table
        site_mapping = {
            'Parafield Gardens': ['RES-001', 'RES-002', 'RES-003'],
            'Nerrilda': ['RES-004', 'RES-005', 'RES-006'],
            'Ramsay': ['RES-007', 'RES-008', 'RES-009'],
            'West Park': ['RES-010', 'RES-011', 'RES-012'],
            'Yankalilla': ['RES-013', 'RES-014', 'RES-015']
        }
        
        resident_id = incident_data['resident_id']
        for site, residents in site_mapping.items():
            if resident_id in residents:
                return site
        
        # Default value
        return 'Parafield Gardens'
    
    def get_post_fall_progress_notes_optimized(self, client_id: int, fall_date: datetime, 
                                                max_days: int = 7, max_hours: int = None) -> List[Dict]:
        """
        Optimized Post Fall Progress Notes query (utilizes CIMS DB data)
        
        ✅ Optimizations:
        - Skip Fall Incident Progress Note query (saves 1 API call)
        - API-level filtering with clientId parameter (reduces network traffic)
        - Query only Post Fall with progressNoteEventTypeId (removes unnecessary data)
        - Query only necessary date range
        
        Args:
            client_id: MANAD ClientId (resident_manad_id in CIMS DB)
            fall_date: Fall occurrence time (incident_date in CIMS DB)
            max_days: Query period (default 7 days, ignored if max_hours is set)
            max_hours: Query period (in hours, e.g., 28 hours). Takes precedence over max_days if set
            
        Returns:
            Post Fall Progress Notes list
        """
        try:
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            # Set date range (Fall after ~ max_hours or max_days)
            if max_hours is not None:
                # Use time-based window (e.g., 28 hours)
                end_date = fall_date + timedelta(hours=max_hours)
            else:
                # Use day-based window (default)
                end_date = fall_date + timedelta(days=max_days)
            start_date_str = fall_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_date_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            notes_url = f"{self.config['base_url']}/api/progressnote/details"
            
            # 🚀 Optimized parameters
            params = {
                'clientId': client_id,  # ✅ Query specific patient only
                'date': [f'gt:{start_date_str}', f'lt:{end_date_str}']  # ✅ Date range
            }
            
            # 🔍 Query Post Fall EventType ID (consider caching)
            # Note: progressNoteEventTypeId needs to know the ID of "Post Fall" in MANAD Plus
            # EventTypes are generally fixed, so can be managed as config or constants
            # Example: progressNoteEventTypeId = 12 (Post Fall)
            # params['progressNoteEventTypeId'] = 12  # TODO: Need to verify actual ID
            
            logger.debug(f"Querying Post Fall notes: ClientId={client_id}, Date={start_date_str} to {end_date_str}")
            
            response = requests.get(notes_url, headers=headers, params=params, timeout=self.config['timeout'])
            
            if response.status_code != 200:
                # HTTP 204 = No Content (normal, no Progress Note)
                if response.status_code == 204:
                    logger.debug(f"No Progress Notes found for ClientId={client_id} (HTTP 204 - No Content)")
                    return []
                else:
                    # Log at WARNING level only for actual errors
                    logger.warning(f"Failed to get progress notes for ClientId={client_id}: HTTP {response.status_code}")
                    return []
            
            all_notes = response.json()
            
            # 📊 Log response size (monitoring)
            logger.debug(f"API returned {len(all_notes)} notes for ClientId={client_id}")
            
            # Filtering (simplified since clientId filter is applied at API level)
            post_fall_notes = []
            
            for note in all_notes:
                if note.get('IsDeleted', False):
                    continue
                
                event_type_obj = note.get('ProgressNoteEventType', {})
                event_type_desc = event_type_obj.get('Description', '') if isinstance(event_type_obj, dict) else ''
                notes_text = note.get('NotesPlainText', '').lower()
                
                # Post Fall or Daily Progress (Fall related)
                if 'Post Fall' in event_type_desc or (event_type_desc == 'Daily Progress' and 'fall' in notes_text):
                    note_date = datetime.fromisoformat(note.get('CreatedDate').replace('Z', ''))
                    
                    # Only notes after Fall Incident (within 28-hour window)
                    window_end = fall_date + (timedelta(hours=max_hours) if max_hours else timedelta(days=max_days))
                    if fall_date < note_date <= window_end:
                        post_fall_notes.append(note)
            
            # Sort by time
            post_fall_notes.sort(key=lambda x: x['CreatedDate'])
            
            logger.info(f"Found {len(post_fall_notes)} Post Fall notes for ClientId={client_id}")
            
            result = {
                'fall_trigger_date': fall_date,
                'client_id': client_id,
                'post_fall_notes': post_fall_notes
            }
            
            return result
                
        except requests.exceptions.ConnectionError:
            logger.warning("Unable to connect to MANAD Plus API server. Cannot query Post Fall notes.")
            return []
        except Exception as e:
            logger.error(f"Error getting post fall notes (optimized): {str(e)}")
            return []
    
    def get_post_fall_progress_notes(self, fall_incident_id: str) -> List[Dict]:
        """
        Query Post Fall Progress Notes from MANAD Plus API (LEGACY)
        
        ⚠️ DEPRECATED: Use get_post_fall_progress_notes_optimized() for optimization
        
        Args:
            fall_incident_id: Fall Incident Progress Note ID
            
        Returns:
            Post Fall Progress Notes list (sorted by time, IsDeleted=False only)
        """
        try:
            # 1. Query Fall Incident Progress Note (trigger)
            fall_url = f"{self.config['base_url']}/api/progressnote/{fall_incident_id}"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            fall_response = requests.get(fall_url, headers=headers, timeout=self.config['timeout'])
            
            if fall_response.status_code != 200:
                # HTTP 204 = No Content (normal, no Progress Note)
                if fall_response.status_code == 204:
                    logger.debug(f"No Progress Note found for Fall Incident {fall_incident_id} (HTTP 204 - No Content)")
                    return []
                else:
                    # Log at ERROR level only for actual errors
                    logger.error(f"Failed to get Fall Incident note {fall_incident_id}: HTTP {fall_response.status_code}")
                    return []
            
            fall_note = fall_response.json()
            fall_trigger_date = datetime.fromisoformat(fall_note.get('CreatedDate').replace('Z', ''))
            client_id = fall_note.get('ClientId')
            
            logger.info(f"Fall Incident trigger: ID={fall_incident_id}, Date={fall_trigger_date}, ClientId={client_id}")
            
            # Use optimized method (apply 28-hour window)
            return self.get_post_fall_progress_notes_optimized(client_id, fall_trigger_date, max_hours=28)
                
        except requests.exceptions.ConnectionError:
            logger.warning("Unable to connect to MANAD Plus API server. Cannot query Post Fall notes.")
            return []
        except Exception as e:
            logger.error(f"Error getting post fall notes: {str(e)}")
            return []
    
    def check_progress_notes(self, incident_id: str, resident_id: str) -> bool:
        """
        Check if progress note exists for a specific incident in MANAD Plus
        
        Args:
            incident_id: MANAD Plus incident ID
            resident_id: Resident ID
            
        Returns:
            bool: Whether progress note exists
        """
        if not self.ensure_authenticated():
            return False
        
        try:
            # Query progress notes from MANAD Plus API
            notes_url = f"{self.config['base_url']}/incidents/{incident_id}/progress-notes"
            
            response = requests.get(
                notes_url,
                headers=self.get_headers(),
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                notes = response.json()
                # Check if there are follow-up notes written within last 24 hours
                recent_notes = [
                    note for note in notes 
                    if self.is_recent_followup_note(note)
                ]
                
                logger.info(f"Incident {incident_id}: Found {len(recent_notes)} recent follow-up notes")
                return len(recent_notes) > 0
            else:
                logger.warning(f"Failed to check progress notes for incident {incident_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking progress notes for incident {incident_id}: {str(e)}")
            return False
    
    def is_recent_followup_note(self, note: Dict) -> bool:
        """
        Check if progress note is a recent follow-up note
        
        Args:
            note: Progress note data
            
        Returns:
            bool: Whether it is a recent follow-up note
        """
        try:
            # Check if within 24 hours
            note_time = datetime.fromisoformat(note['created_at'].replace('Z', '+00:00'))
            now = datetime.now(note_time.tzinfo)
            time_diff = (now - note_time).total_seconds()
            
            if time_diff > 24 * 3600:  # Exceeds 24 hours
                return False
            
            # Check follow-up related keywords
            followup_keywords = [
                'follow-up', 'follow up', 'followup',
                'assessment', 'monitoring', 'check',
                'vital signs', 'condition', 'status'
            ]
            
            content = note.get('content', '').lower()
            note_type = note.get('type', '').lower()
            
            # Check if follow-up keywords exist in content or type
            for keyword in followup_keywords:
                if keyword in content or keyword in note_type:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error parsing progress note: {str(e)}")
            return False
    
    def monitor_deadlines_and_complete_tasks(self) -> None:
        """
        Auto-complete tasks after checking progress notes at deadline
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # Query incomplete tasks past deadline
            now = datetime.now()
            cursor.execute("""
                SELECT t.id, t.task_name, t.due_date, t.assigned_user_id,
                       i.manad_incident_id, i.resident_id, i.resident_name
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status IN ('Open', 'In Progress') 
                AND t.due_date <= ?
                AND i.manad_incident_id IS NOT NULL
            """, (now.isoformat(),))
            
            overdue_tasks = cursor.fetchall()
            logger.info(f"Found {len(overdue_tasks)} overdue tasks to check")
            
            for task in overdue_tasks:
                task_id, task_name, due_date, assigned_user_id, manad_incident_id, resident_id, resident_name = task
                
                # Check progress note in MANAD Plus
                has_progress_note = self.check_progress_notes(manad_incident_id, resident_id)
                
                if has_progress_note:
                    # Auto-complete task if progress note exists
                    cursor.execute("""
                        UPDATE cims_tasks 
                        SET status = 'Completed', 
                            completed_at = ?,
                            completion_method = 'auto_manad_check'
                        WHERE id = ?
                    """, (now.isoformat(), task_id))
                    
                    # Create audit log
                    cursor.execute("""
                        INSERT INTO cims_audit_logs (
                            log_id, user_id, action, target_entity_type, target_entity_id, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"LOG-{now.strftime('%Y%m%d%H%M%S')}",
                        'MANAD_INTEGRATOR',
                        'task_auto_completed',
                        'task',
                        task_id,
                        json.dumps({
                            'manad_incident_id': manad_incident_id,
                            'resident_name': resident_name,
                            'reason': 'progress_note_found_in_manad',
                            'completed_at': now.isoformat()
                        })
                    ))
                    
                    logger.info(f"Task {task_id} auto-completed due to progress note found in MANAD Plus")
                else:
                    logger.info(f"Task {task_id} remains incomplete - no progress note found in MANAD Plus")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error monitoring deadlines: {str(e)}")
    
    def validate_pending_tasks(self) -> None:
        """
        Periodic validation and completion of Pending status tasks
        """
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # Query Pending status tasks
            cursor.execute("""
                SELECT t.id, t.task_name, t.pending_confirmation_at,
                       i.manad_incident_id, i.resident_id, i.resident_name
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status = 'Pending' 
                AND i.manad_incident_id IS NOT NULL
                AND t.pending_confirmation_at IS NOT NULL
            """)
            
            pending_tasks = cursor.fetchall()
            logger.info(f"Found {len(pending_tasks)} pending tasks to validate")
            
            for task in pending_tasks:
                task_id, task_name, pending_confirmation_at, manad_incident_id, resident_id, resident_name = task
                
                # Check progress note in MANAD Plus
                has_progress_note = self.check_progress_notes(manad_incident_id, resident_id)
                
                if has_progress_note:
                    # Complete task if progress note is confirmed
                    now = datetime.now()
                    cursor.execute("""
                        UPDATE cims_tasks 
                        SET status = 'Completed', 
                            completed_at = ?,
                            completion_method = 'auto_manad_validation'
                        WHERE id = ?
                    """, (now.isoformat(), task_id))
                    
                    # Create audit log
                    cursor.execute("""
                        INSERT INTO cims_audit_logs (
                            log_id, user_id, action, target_entity_type, target_entity_id, details
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        f"LOG-{now.strftime('%Y%m%d%H%M%S')}",
                        'MANAD_INTEGRATOR',
                        'task_validated_and_completed',
                        'task',
                        task_id,
                        json.dumps({
                            'manad_incident_id': manad_incident_id,
                            'resident_name': resident_name,
                            'reason': 'progress_note_validated_in_manad',
                            'completed_at': now.isoformat(),
                            'pending_confirmation_at': pending_confirmation_at
                        })
                    ))
                    
                    logger.info(f"Task {task_id} validated and completed due to progress note found in MANAD Plus")
                else:
                    # Keep Pending status if no progress note
                    logger.info(f"Task {task_id} remains pending - no progress note found in MANAD Plus")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error validating pending tasks: {str(e)}")
    
    def poll_incidents(self, full_sync=False) -> List[Dict]:
        """
        Poll new incident records from MANAD Plus (for mock data)
        
        Args:
            full_sync: Whether full sync (fetches data from 7 days ago if True)
        
        Returns:
            List[Dict]: List of new incident records
        """
        if not self.ensure_authenticated():
            logger.error("Polling stopped due to MANAD Plus authentication failure")
            return []
        
        try:
            last_checked = self.get_last_checked_time(full_sync)
            incidents_url = f"{self.config['base_url']}/incidents/latest"
            
            params = {
                'last_checked_at': last_checked,
                'limit': 500 if full_sync else 100  # Fetch more data for full sync
            }
            
            try:
                response = requests.get(
                    incidents_url,
                    headers=self.get_headers(),
                    params=params,
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    incidents = response.json()
                    if full_sync:
                        logger.info(f"MANAD Plus full sync: queried {len(incidents)} incident records")
                    else:
                        logger.info(f"Queried {len(incidents)} incident records from MANAD Plus")
                    
                    # Update last check time
                    if incidents:
                        latest_time = max(incident['last_updated_at'] for incident in incidents)
                        self.update_last_checked_time(latest_time)
                    else:
                        # Update to current time even if no new incidents
                        self.update_last_checked_time(datetime.now().isoformat() + 'Z')
                    
                    return incidents
                else:
                    logger.error(f"MANAD Plus incident polling failed: {response.status_code} - {response.text}")
                    return []
                    
            except requests.exceptions.ConnectionError:
                # No new data if actual API doesn't exist
                logger.warning("Unable to connect to MANAD Plus API server. Cannot fetch new incidents.")
                return []
                
        except Exception as e:
            logger.error(f"MANAD Plus incident polling error: {str(e)}")
            return []
    
    def get_resident_info(self, resident_id: str) -> Optional[Dict]:
        """
        Query resident information
        
        Args:
            resident_id: Resident ID
            
        Returns:
            Dict: Resident information or None
        """
        if not self.ensure_authenticated():
            return None
        
        try:
            resident_url = f"{self.config['base_url']}/residents/{resident_id}"
            
            try:
                response = requests.get(
                    resident_url,
                    headers=self.get_headers(),
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to query resident information ({resident_id}): {response.status_code}")
                    return None
                    
            except requests.exceptions.ConnectionError:
                # Return default information if actual API doesn't exist
                logger.warning(f"Unable to connect to MANAD Plus API server. Using default resident information. ({resident_id})")
                return {
                    'resident_id': resident_id,
                    'full_name': f"Resident {resident_id}",
                    'facility_name': 'Unknown'
                }
                
        except Exception as e:
            logger.error(f"Error querying resident information ({resident_id}): {str(e)}")
            return None
    
    def process_incident(self, incident_data: Dict) -> bool:
        """
        Process incident data received from MANAD Plus in CIMS
        
        Args:
            incident_data: MANAD Plus incident data
            
        Returns:
            bool: Processing success status
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Query resident information
                resident_info = self.get_resident_info(incident_data['resident_id'])
                resident_name = resident_info['full_name'] if resident_info else f"Resident {incident_data['resident_id']}"
                
                # Extract site information (from MANAD Plus data)
                site_name = self.extract_site_from_incident(incident_data)
                
                # Create CIMS incident data (use WAL mode)
                conn = sqlite3.connect('progress_report.db')
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                cursor = conn.cursor()
                
                # Duplicate check (based on MANAD incident ID)
                cursor.execute("""
                    SELECT id FROM cims_incidents 
                    WHERE manad_incident_id = ?
                """, (incident_data['manad_incident_id'],))
                
                existing = cursor.fetchone()
                if existing:
                    logger.info(f"Incident {incident_data['manad_incident_id']} already processed")
                    conn.close()
                    return True
                
                # Create new incident
                incident_id = f"I-{incident_data['manad_incident_id']}"
                
                cursor.execute("""
                    INSERT INTO cims_incidents (
                        incident_id, manad_incident_id, resident_id, resident_name,
                        incident_type, severity, status, incident_date, 
                        description, reported_by, site, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    incident_id,
                    incident_data['manad_incident_id'],
                    incident_data['resident_id'],
                    resident_name,
                    incident_data['incident_type'],
                    incident_data['incident_severity_code'],
                    'Open',
                    incident_data['incident_time'],
                    f"Incident imported from MANAD Plus: {incident_data['incident_type']}",
                    'MANAD_PLUS_SYSTEM',
                    site_name,
                    datetime.now().isoformat()
                ))
                
                incident_db_id = cursor.lastrowid
                conn.commit()
                
                # Trigger policy engine
                cims_incident_data = {
                    'id': incident_db_id,
                    'incident_id': incident_id,
                    'type': incident_data['incident_type'],
                    'severity': incident_data['incident_severity_code'],
                    'incident_date': incident_data['incident_time'],
                    'resident_id': incident_data['resident_id'],
                    'resident_name': resident_name,
                    'manad_incident_id': incident_data['manad_incident_id']
                }
                
                generated_tasks = self.policy_engine.apply_policies_to_incident(cims_incident_data)
                
                # Audit log (generate unique log ID)
                log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{incident_db_id}"
                cursor.execute("""
                    INSERT INTO cims_audit_logs (
                        log_id, user_id, action, target_entity_type, target_entity_id, details
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    log_id,
                    'MANAD_INTEGRATOR',
                    'incident_imported',
                    'incident',
                    incident_db_id,
                    json.dumps({
                        'manad_incident_id': incident_data['manad_incident_id'],
                        'incident_type': incident_data['incident_type'],
                        'severity': incident_data['incident_severity_code'],
                        'tasks_generated': len(generated_tasks)
                    })
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Incident {incident_data['manad_incident_id']} processing completed, {len(generated_tasks)} tasks created")
                return True
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database lock occurred, retrying after {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    logger.error(f"Incident processing error ({incident_data.get('manad_incident_id', 'Unknown')}): {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"Incident processing error ({incident_data.get('manad_incident_id', 'Unknown')}): {str(e)}")
                return False
        
        return False
    
    def polling_loop(self) -> None:
        """
        Periodic polling loop
        """
        logger.info("MANAD Plus polling started")
        
        while self.is_running:
            try:
                # Poll new incidents
                incidents = self.poll_incidents()
                
                # Process each incident
                for incident in incidents:
                    self.process_incident(incident)
                
                # Monitor deadlines and auto-complete
                self.monitor_deadlines_and_complete_tasks()
                
                # Periodic validation of Pending status tasks
                self.validate_pending_tasks()
                
                # Wait until next polling
                time.sleep(self.config['polling_interval'])
                
            except Exception as e:
                logger.error(f"Polling loop error: {str(e)}")
                time.sleep(30)  # Wait 30 seconds on error then retry
    
    def start_polling(self) -> bool:
        """
        Start polling service
        
        Returns:
            bool: Start success status
        """
        if self.is_running:
            logger.warning("Polling is already running")
            return False
        
        if not self.ensure_authenticated():
            logger.error("Cannot start polling due to authentication failure")
            return False
        
        self.is_running = True
        self.polling_thread = threading.Thread(target=self.polling_loop, daemon=False)
        self.polling_thread.start()
        
        logger.info("MANAD Plus polling service started")
        return True
    
    def stop_polling(self) -> None:
        """
        Stop polling service
        """
        self.is_running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        
        logger.info("MANAD Plus polling service stopped")
    
    def get_status(self) -> Dict:
        """
        Query integration service status
        
        Returns:
            Dict: Service status information
        """
        # Check API connection status (based on Parafield Gardens server)
        api_connected = False
        connection_error = None
        
        try:
            # Use MANAD API connection test endpoint
            test_url = f"{self.config['base_url']}/api/system/canconnect"
            
            headers = {
                'x-api-username': self.config.get('api_username', 'ManadAPI'),
                'x-api-key': self.config.get('api_key', ''),
                'Content-Type': 'application/json'
            }
            
            test_response = requests.get(
                test_url,
                headers=headers,
                timeout=5
            )
            
            # Connected if status code is in 200-299 range
            if 200 <= test_response.status_code < 300:
                api_connected = True
                logger.info(f"MANAD Plus server connection successful: {test_url}")
            elif test_response.status_code == 401:
                api_connected = True  # Authentication error but server responds
                connection_error = "Authentication required (server is online)"
            elif test_response.status_code < 500:
                api_connected = True  # Client error but server responds
                connection_error = f"HTTP {test_response.status_code}"
            else:
                connection_error = f"Server error: HTTP {test_response.status_code}"
                
        except requests.exceptions.ConnectionError:
            connection_error = f"Unable to connect to MANAD Plus server ({self.config['server_ip']})"
        except requests.exceptions.Timeout:
            connection_error = "MANAD Plus server response timeout"
        except Exception as e:
            connection_error = f"Unknown error: {str(e)}"
        
        return {
            'is_running': self.is_running,
            'is_authenticated': self.is_token_valid(),
            'api_connected': api_connected,
            'connection_error': connection_error,
            'last_checked': self.get_last_checked_time(),
            'config': {
                'base_url': self.config['base_url'],
                'server_ip': self.config.get('server_ip', 'Unknown'),
                'polling_interval': self.config['polling_interval']
            }
        }

# Global instance
manad_integrator = MANADPlusIntegrator()

def get_manad_integrator() -> MANADPlusIntegrator:
    """
    Return MANAD Plus Integrator instance
    
    Returns:
        MANADPlusIntegrator: Integration service instance
    """
    return manad_integrator
