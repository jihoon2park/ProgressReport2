#!/usr/bin/env python3
"""
Progress Note Query API Client
Functionality to fetch progress notes by site and store them in IndexedDB
"""

import requests
import logging
import os
import json
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List


def _range_last_n_days(days: int) -> tuple[datetime, datetime]:
    """Return (start, end) for 'last N days' as full calendar days: start-of first day, end-of today."""
    today = date.today()
    first_day = today - timedelta(days=days)
    start = datetime.combine(first_day, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())
    return start, end
from config import SITE_SERVERS, API_HEADERS, get_api_headers

# Logging configuration
logger = logging.getLogger(__name__)

class ProgressNoteFetchClient:
    """Progress Note Query API Client"""
    
    def __init__(self, site: str):
        """
        Args:
            site: Site name (e.g., 'Parafield Gardens', 'Nerrilda')
        """
        self.site = site
        self.server_ip = SITE_SERVERS.get(site)
        
        if not self.server_ip:
            logger.error(f"Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}")
            raise ValueError(f"Unknown site: {site}")
        
        # Use server_ip as-is since it already includes port
        self.base_url = f"http://{self.server_ip}"
        self.api_url = f"{self.base_url}/api/progressnote/details"
        
        # Create session
        self.session = requests.Session()
        # Set site-specific API headers
        site_headers = get_api_headers(site)
        self.session.headers.update(site_headers)
        
        logger.info(f"ProgressNoteFetchClient initialized for site: {site} ({self.server_ip})")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Session headers: {dict(self.session.headers)}")
    
    def fetch_progress_notes(self, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           limit: int = 500, # Default limit
                           progress_note_event_type_id: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Fetch progress notes matching specific conditions.
        
        Args:
            start_date: Start date (default: 14 days ago)
            end_date: End date (default: current time)
            limit: Maximum number to fetch (default: 500)
            progress_note_event_type_id: Filter by specific event type ID
            
        Returns:
            (success status, data list or None)
        """
        try:
            # Set default values
            if start_date is None:
                start_date = datetime.now() - timedelta(days=14)
            if end_date is None:
                end_date = datetime.now()
            
            # Set API parameters
            params = {}
            
            # Convert date format (use same format as POSTMAN)
            start_date_str = start_date.strftime('%Y-%m-%dT00:00:00Z')
            end_date_str = end_date.strftime('%Y-%m-%dT23:59:59Z')
            
            # Filter by event type
            if progress_note_event_type_id is not None:
                params['progressNoteEventTypeId'] = progress_note_event_type_id
            
            # Apply date filter - use same format as POSTMAN (gt: >, lt: <)
            params['date'] = [f'gt:{start_date_str}', f'lt:{end_date_str}']
            
            # Set Limit parameter
            if limit is not None:
                params['limit'] = limit
            
            # API request
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=120  # Increase timeout to 2 minutes
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} progress notes from {self.site}")
                
                # Log response data sample (save to file only)
                if data and len(data) > 0:
                    debug_info = {
                        'timestamp': datetime.now().isoformat(),
                        'site': self.site,
                        'api_url': self.api_url,
                        'params': params,
                        'date_range': f"{start_date_str} to {end_date_str}",
                        'event_type_filter': progress_note_event_type_id,
                        'limit': params.get('limit'),
                        'response_status': response.status_code,
                        'records_fetched': len(data),
                        'sample_records': []
                    }
                    
                    for i, record in enumerate(data[:3]):
                        event_type = record.get('ProgressNoteEventType', {})
                        debug_info['sample_records'].append({
                            'index': i+1,
                            'id': record.get('Id'),
                            'event_date': record.get('EventDate'),
                            'event_type': event_type.get('Description', 'N/A')
                        })
                    
                    # Save debug info to file
                    try:
                        logs_dir = os.path.join(os.getcwd(), 'logs')
                        os.makedirs(logs_dir, exist_ok=True)
                        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                        filename = f'api_debug_{timestamp}.json'
                        filepath = os.path.join(logs_dir, filename)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(debug_info, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.error(f"Failed to save debug log: {str(e)}")
                else:
                    logger.info("No data returned from API")
                
                return True, data
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                # Provide detailed error information when API fails
                error_details = {
                    'status_code': response.status_code,
                    'response_text': response.text,
                    'api_url': self.api_url,
                    'params': params,
                    'site': self.site,
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"API failure details: {error_details}")
                return False, None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out after 120 seconds for {self.site}")
            return False, None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error while fetching progress notes from {self.site}: {str(e)}")
            return False, None
    
    def fetch_recent_progress_notes(self, days: int = 14, limit: Optional[int] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Fetch progress notes for the last N days.
        
        Args:
            days: Number of days to fetch (default: 14 days)
            
        Returns:
            (success status, data list or None)
        """
        start_date, end_date = _range_last_n_days(days)
        effective_limit = limit if limit is not None else 500
        return self.fetch_progress_notes(start_date, end_date, limit=effective_limit)
    
    def fetch_progress_notes_since(self, since_date: datetime) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Fetch progress notes since a specific date (for incremental updates).
        
        Args:
            since_date: Start date
            
        Returns:
            (success status, data list or None)
        """
        end_date = datetime.now()
        logger.info(f"Incremental update - since_date: {since_date}, end_date: {end_date}")
        logger.info(f"Time difference: {end_date - since_date}")
        
        success, data = self.fetch_progress_notes(since_date, end_date)
        
        if success and data:
            logger.info(f"Incremental update found {len(data)} records")
            # Log a few latest records
            if len(data) > 0:
                logger.info("Latest records in incremental update:")
                for i, record in enumerate(data[:5]):
                    logger.info(f"  {i+1}. ID: {record.get('Id')}, EventDate: {record.get('EventDate')}, CreatedDate: {record.get('CreatedDate', 'N/A')}")
        else:
            logger.info("No new records found in incremental update")
            
        return success, data

    def fetch_rod_progress_notes(self, year: int, month: int, event_types: List[str] = None) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Fetch progress notes for ROD dashboard.
        
        Args:
            year: Year
            month: Month
            event_types: List of event types to filter (if None, automatically find "Resident of the day" event types)
            
        Returns:
            (success status, data list or None)
        """
        try:
            logger.info(f"Fetching ROD progress notes for {year}-{month}, event_types: {event_types}")
            
            # Calculate date range for year/month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Automatically find "Resident of the day" event types if not provided
            if not event_types or len(event_types) == 0:
                logger.info("No event types provided, searching for 'Resident of the day' event types")
                event_types = self.find_resident_of_day_event_types()
                if not event_types:
                    logger.error("No Resident of the day event types found")
                    return False, None
                logger.info(f"Found Resident of the day event types: {event_types}")
            
            # Find event type IDs
            event_type_ids = []
            for event_type_name in event_types:
                event_type_id = self._find_event_type_id(event_type_name)
                if event_type_id:
                    event_type_ids.append(event_type_id)
                    logger.info(f"Found event type ID {event_type_id} for '{event_type_name}'")
                else:
                    logger.warning(f"Event type '{event_type_name}' not found")
            
            if not event_type_ids:
                logger.error("No valid event type IDs found")
                return False, None
            
            # Fetch progress notes for each event type
            all_notes = []
            for event_type_id in event_type_ids:
                logger.info(f"Fetching notes for event type ID: {event_type_id}")
                success, notes = self.fetch_progress_notes(
                    start_date=start_date,
                    end_date=end_date,
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes:
                    logger.info(f"Found {len(notes)} notes for event type ID {event_type_id}")
                    all_notes.extend(notes)
                else:
                    logger.warning(f"No notes found for event type ID {event_type_id}")
            
            logger.info(f"Total ROD notes found: {len(all_notes)}")
            return True, all_notes
            
        except Exception as e:
            logger.error(f"Error fetching ROD progress notes: {str(e)}")
            return False, None
    
    def fetch_progress_notes_by_event_types(self, days: int, event_types: List[str]) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Fetch progress notes filtered by specific event types.
        
        Args:
            days: Number of days to fetch
            event_types: List of event types to filter
            
        Returns:
            (success status, data list or None)
        """
        try:
            logger.info(f"Fetching progress notes by event types: {event_types} for {days} days")
            
            start_date, end_date = _range_last_n_days(days)
            logger.info(f"Date range: {start_date} to {end_date}")
            
            # Find event type IDs
            event_type_ids = []
            for event_type_name in event_types:
                event_type_id = self._find_event_type_id(event_type_name)
                if event_type_id:
                    event_type_ids.append(event_type_id)
                    logger.info(f"Found event type ID {event_type_id} for '{event_type_name}'")
                else:
                    logger.warning(f"Event type '{event_type_name}' not found")
            
            if not event_type_ids:
                logger.error("No valid event type IDs found")
                return False, None
            
            # Fetch progress notes for each event type (performance optimization: remove limit)
            all_notes = []
            for event_type_id in event_type_ids:
                logger.info(f"Fetching notes for event type ID: {event_type_id}")
                success, notes = self.fetch_progress_notes(
                    start_date=start_date,
                    end_date=end_date,
                    limit=None,  # Performance optimization: remove limit
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes:
                    logger.info(f"Found {len(notes)} notes for event type ID {event_type_id}")
                    all_notes.extend(notes)
                else:
                    logger.warning(f"No notes found for event type ID {event_type_id}")
            
            logger.info(f"Total notes found for event types: {len(all_notes)}")
            return True, all_notes
            
        except Exception as e:
            logger.error(f"Error fetching progress notes by event types: {str(e)}")
            return False, None
    
    def find_resident_of_day_event_types(self) -> List[str]:
        """
        Find event types related to "Resident of the day".
        
        Returns:
            List of "Resident of the day" related event type names
        """
        try:
            logger.info(f"Finding Resident of the day event types for site: {self.site}")
            
            # Load event types from site-specific JSON file
            from api_eventtype import get_site_event_types
            event_types = get_site_event_types(self.site)
            
            if not event_types:
                logger.error(f"Failed to load event types from JSON for site {self.site}")
                return []
            
            logger.info(f"Searching through {len(event_types)} event types for 'Resident of the day'")
            resident_of_day_types = []
            
            for event_type in event_types:
                description = event_type.get('Description', '')
                event_id = event_type.get('Id')
                
                if 'resident of the day' in description.lower():
                    logger.info(f"Found Resident of the day event type: '{description}' (ID: {event_id})")
                    resident_of_day_types.append(description)
            
            logger.info(f"Found {len(resident_of_day_types)} Resident of the day event types: {resident_of_day_types}")
            return resident_of_day_types
            
        except Exception as e:
            logger.error(f"Error finding Resident of the day event types: {str(e)}")
            return []
    
    def _find_event_type_id(self, event_type_name: str) -> Optional[int]:
        """
        Find ID by event type name.
        
        Args:
            event_type_name: Event type name
            
        Returns:
            Event type ID or None
        """
        try:
            logger.info(f"Finding event type ID for '{event_type_name}' in site: {self.site}")
            
            # Load event types from site-specific JSON file
            from api_eventtype import get_site_event_types
            event_types = get_site_event_types(self.site)
            
            if not event_types:
                logger.error(f"Failed to load event types from JSON for site {self.site}")
                return None
            
            logger.info(f"Found {len(event_types)} event types for site {self.site}")
            # Find ID by event type name
            for event_type in event_types:
                description = event_type.get('Description', '')
                event_id = event_type.get('Id')
                if event_type_name.lower() in description.lower():
                    logger.info(f"Found matching event type: '{description}' (ID: {event_id})")
                    return event_id
            
            logger.warning(f"Event type '{event_type_name}' not found in {len(event_types)} available types")
            return None
            
        except Exception as e:
            logger.error(f"Error finding event type ID for '{event_type_name}': {str(e)}")
            return None

def fetch_progress_notes_for_site(site: str, days: int = 14, event_types: List[str] = None, year: int = None, month: int = None, client_service_id: int = None, limit: Optional[int] = None, offset: int = 0, return_total: bool = False) -> tuple[bool, Optional[List[Dict[str, Any]]], Optional[int]]:
    """
    Convenience function to fetch progress notes for a specific site (DB direct access or API)
    
    Args:
        site: Site name
        days: Number of days to fetch
        event_types: List of event types to filter
        year: Year (for ROD dashboard)
        month: Month (for ROD dashboard)
        client_service_id: Filter by specific client service ID
        limit: Max rows to return (default 500 when not set)
        offset: Rows to skip for server pagination
        return_total: If True, return (success, notes, total_count); total_count only in DB mode when set
        
    Returns:
        (success status, data list or None, total_count or None)
    """
    import sqlite3
    import os
    
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
    
    # DB direct access mode
    if use_db_direct:
        try:
            from manad_db_connector import MANADDBConnector
            from datetime import datetime, timedelta
            
            logger.info(f"🔌 DB direct access mode: Progress Notes query - {site}")
            connector = MANADDBConnector(site)
            
            # Special handling for ROD dashboard
            if year is not None and month is not None:
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            else:
                start_date, end_date = _range_last_n_days(days)
            
            # Event Type filtering (ID conversion if needed)
            event_type_id = None
            if event_types and len(event_types) > 0:
                # Find ID by Event Type name (simple version, may be more complex in practice)
                logger.warning(f"Event Type filtering is not yet fully supported in DB direct access mode: {event_types}")
            
            effective_limit = limit if limit is not None else 500

            logger.info(f"🔍 [FILTER] Calling connector.fetch_progress_notes - client_service_id={client_service_id}, offset={offset}, return_total={return_total}")
            logger.info(f"🔍 [FILTER] Parameters: start_date={start_date}, end_date={end_date}, limit={effective_limit}, event_type_id={event_type_id}, client_service_id={client_service_id}")
            progress_success, progress_notes, total_count = connector.fetch_progress_notes(
                start_date, end_date, limit=effective_limit, offset=offset,
                progress_note_event_type_id=event_type_id, client_service_id=client_service_id,
                return_total=return_total
            )
            logger.info(f"🔍 [FILTER] connector.fetch_progress_notes result - success={progress_success}, notes_count={len(progress_notes) if progress_notes else 0}, total_count={total_count}")
            
            if not progress_success:
                error_msg = f"❌ DB direct access failed: {site} - Progress Notes query failed. Please check DB connection settings."
                logger.error(error_msg)
                raise Exception(error_msg)
            # Empty list is valid (e.g. no notes in range)
            notes_out = progress_notes if progress_notes else []
            return (True, notes_out, total_count)
            
        except Exception as db_error:
            error_msg = f"❌ DB direct access failed: {site} - {str(db_error)}. Please check DB connection settings and driver installation."
            logger.error(error_msg)
            raise Exception(error_msg)
    
    # API mode
    try:
        logger.info(f"🌐 API mode: Progress Notes query - {site}")
        client = ProgressNoteFetchClient(site)
        logger.info(f"Fetching progress notes for site {site} with {days} days range, event_types: {event_types}")
        
        # Special handling for ROD dashboard (when year and month are provided and event_types is null or empty array)
        logger.info(f"Checking ROD mode conditions: year={year}, month={month}, event_types={event_types}, event_types type={type(event_types)}")
        logger.info(f"Condition check: year is not None = {year is not None}, month is not None = {month is not None}")
        logger.info(f"Condition check: not event_types = {not event_types}, len(event_types) == 0 = {len(event_types) == 0 if event_types else 'N/A'}")
        
        # ROD mode condition: year and month exist, and event_types is None or empty array or list of empty strings
        is_rod_mode = (year is not None and 
                      month is not None and 
                      (event_types is None or 
                       len(event_types) == 0 or 
                       (isinstance(event_types, list) and all(not et for et in event_types))))
        
        logger.info(f"ROD mode determination: {is_rod_mode}")
        
        if is_rod_mode:
            logger.info(f"ROD dashboard mode - fetching for year: {year}, month: {month}, event_types: {event_types}")
            s, n = client.fetch_rod_progress_notes(year, month, event_types)
            return (s, n, None)
        else:
            # General progress note request
            # Note: API mode does not support client_service_id filtering
            # Client filtering is performed on the client side
            if event_types:
                logger.info(f"General request with event type filtering: {event_types}")
                s, n = client.fetch_progress_notes_by_event_types(days, event_types)
                return (s, n, None)
            else:
                logger.info("No event types specified, fetching all progress notes")
                if client_service_id:
                    logger.warning(f"Client service ID filter ({client_service_id}) is not supported in API mode. Filtering will be done client-side.")
                s, n = client.fetch_recent_progress_notes(days, limit=limit)
                return (s, n, None)
    except Exception as e:
        logger.error(f"Error creating client for site {site}: {str(e)}")
        return (False, None, None)

def fetch_progress_notes_for_all_sites(days: int = 14) -> Dict[str, tuple[bool, Optional[List[Dict[str, Any]]]]]:
    """
    Function to fetch progress notes for all sites
    
    Args:
        days: Number of days to fetch
        
    Returns:
        Dictionary of results by site
    """
    results = {}
    
    for site in SITE_SERVERS.keys():
        logger.info(f"Fetching progress notes for site: {site}")
        success, data, _ = fetch_progress_notes_for_site(site, days)
        results[site] = (success, data)
        
        if success:
            logger.info(f"Successfully fetched {len(data) if data else 0} progress notes from {site}")
        else:
            logger.error(f"Failed to fetch progress notes from {site}")
    
    return results

# Test function
def test_progress_note_fetch():
    """Test progress note query functionality"""
    print("=== Progress Note Query Test ===")
    
    # Print available sites
    print(f"Available sites: {list(SITE_SERVERS.keys())}")
    
    # Test each site
    for site in SITE_SERVERS.keys():
        print(f"\n--- {site} Test ---")
        
        try:
            client = ProgressNoteFetchClient(site)
            success, data = client.fetch_recent_progress_notes(days=7)  # Test only 7 days
            
            if success:
                print(f"✅ Success: {len(data) if data else 0} progress notes queried")
                if data and len(data) > 0:
                    # Print sample of first item
                    sample = data[0]
                    print(f"   Sample data:")
                    print(f"   - ID: {sample.get('Id')}")
                    print(f"   - ClientId: {sample.get('ClientId')}")
                    print(f"   - EventDate: {sample.get('EventDate')}")
                    print(f"   - Notes: {sample.get('NotesPlainText', '')[:50]}...")
            else:
                print(f"❌ Failed: Progress note query failed")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def fetch_event_types_for_site(site: str) -> tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    Fetch event type list for a specific site (uses site-specific JSON file).
    
    Args:
        site (str): Site name
    
    Returns:
        (success status, event type list or None)
    """
    try:
        from api_eventtype import get_site_event_types
        event_types = get_site_event_types(site)
        
        if event_types:
            logger.info(f"Successfully loaded {len(event_types)} event types for site {site}")
            return True, event_types
        else:
            logger.warning(f"No event types found for site {site}")
            return False, None
            
    except Exception as e:
        logger.error(f"Error fetching event types for site {site}: {str(e)}")
        return False, None

# Site-specific Resident of the day event type IDs (hardcoded)
SITE_EVENT_TYPE_IDS = {
    'Parafield Gardens': {'rn_en': 30, 'pca': 121},
    'Nerrilda': {'rn_en': 30, 'pca': 85},
    'Ramsay': {'rn_en': 82, 'pca': 30},
    'West Park': {'rn_en': 30, 'pca': 100},
    'Yankalilla': {'rn_en': 30, 'pca': 63}
}

def find_resident_of_day_event_types(event_types: List[Dict[str, Any]] = None, site: str = None) -> tuple[Optional[int], Optional[int]]:
    """
    Return Resident of the day event type IDs by site.
    
    Args:
        event_types: Event type list (not used, kept for compatibility)
        site: Site name (not used, kept for compatibility)
    
    Returns:
        (RN/EN event type ID, PCA event type ID)
    """
    # Return event type ID for current site (use hardcoded values)
    # Site is retrieved from ProgressNoteFetchClient's self.site
    return None, None  # This function is no longer used

def get_site_event_type_ids(site: str) -> tuple[Optional[int], Optional[int]]:
    """
    Return Resident of the day event type IDs for a specific site.
    
    Args:
        site: Site name
    
    Returns:
        (RN/EN event type ID, PCA event type ID)
    """
    site_ids = SITE_EVENT_TYPE_IDS.get(site)
    if site_ids:
        rn_en_id = site_ids.get('rn_en')
        pca_id = site_ids.get('pca')
        logger.info(f"Using hardcoded event type IDs for {site}: RN/EN={rn_en_id}, PCA={pca_id}")
        return rn_en_id, pca_id
    else:
        logger.error(f"No event type IDs found for site: {site}")
        return None, None

# Logic to fetch event types from existing API (commented out)
"""
def find_resident_of_day_event_types_from_api(event_types: List[Dict[str, Any]]) -> tuple[Optional[int], Optional[int]]:
    # Find Resident of the day related event type IDs from event type list.
    rn_en_id = None
    pca_id = None
    
    for event_type in event_types:
        description = event_type.get('Description', '').lower()
        event_id = event_type.get('Id')
        
        if 'resident of the day' in description:
            # Exclude lifestyle
            if 'lifestyle' in description:
                logger.info(f"Skipping lifestyle event type: ID {event_id} - {event_type.get('Description')}")
                continue
            elif 'pca' in description:
                pca_id = event_id
                logger.info(f"Found PCA Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
            elif any(keyword in description for keyword in ['rn', 'en', 'nurse']):
                rn_en_id = event_id
                logger.info(f"Found RN/EN Resident of the day event type: ID {event_id} - {event_type.get('Description')}")
    
    return rn_en_id, pca_id
"""

def fetch_residence_of_day_notes_with_client_data(site, year, month):
    """
    Fetch "Resident of the day" notes for a specific year/month with client data.
    
    Args:
        site (str): Site name
        year (int): Year
        month (int): Month
    
    Returns:
        dict: Status information by Residence
    """
    try:
        logger.info(f"Fetching Resident of the day notes for {site} - {year}/{month}")
        
        # Create debug info for file logging
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'site': site,
            'year': year,
            'month': month,
            'steps': []
        }
        
        # 1. Get client information
        from api_client import fetch_client_information
        client_success, client_data = fetch_client_information(site)
        if not client_success or not client_data:
            logger.error(f"Failed to fetch client data for {site}")
            return {}
        
        debug_info['steps'].append({
            'step': 'client_data_fetch',
            'success': client_success,
            'client_count': len(client_data) if client_data else 0,
            'sample_clients': []
        })
        
        # Add sample client data to debug info
        if client_data:
            for i, client in enumerate(client_data[:3]):
                first_name = client.get('FirstName', '')
                surname = client.get('Surname', '')
                last_name = client.get('LastName', '')
                main_id = client.get('MainClientServiceId', '')
                debug_info['steps'][-1]['sample_clients'].append({
                    'index': i+1,
                    'name': f"{first_name} {surname or last_name}",
                    'main_client_service_id': main_id
                })
        
        # 2. Set date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        debug_info['steps'].append({
            'step': 'date_range_setup',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        # 3. Get site-specific Resident of the day related EventType IDs (hardcoded)
        rn_en_id, pca_id = get_site_event_type_ids(site)
        
        # Logic to fetch event types from existing API (commented out)
        # event_success, event_types = fetch_event_types_for_site(site)
        # if not event_success or not event_types:
        #     logger.error(f"Failed to fetch event types for {site}")
        #     return {}
        # rn_en_id, pca_id = find_resident_of_day_event_types(event_types)
        
        debug_info['steps'].append({
            'step': 'event_type_fetch',
            'success': True,  # Use hardcoded values
            'event_types_count': 0,  # Not fetched from API
            'rn_en_id': rn_en_id,
            'pca_id': pca_id
        })
        
        if not rn_en_id and not pca_id:
            logger.warning(f"No Resident of the day event types found for {site}")
            return {}
        
        # 4. Fetch all Resident of the day notes at once (optimization)
        all_resident_notes = []
        event_type_mapping = {}  # Mapping to classify notes as RN/EN and PCA
        rn_en_notes = []  # Store RN/EN notes separately
        pca_notes = []    # Store PCA notes separately
        
        # First, try to find data from saved files
        logs_dir = os.path.join(os.getcwd(), 'data')
        timestamp_pattern = f"{year}_{month:02d}"
        
        # Find May data files (exact pattern matching)
        rn_en_files = [f for f in os.listdir(logs_dir) if f.startswith(f'progress_notes_rn_en_{site}_{timestamp_pattern}_')]
        pca_files = [f for f in os.listdir(logs_dir) if f.startswith(f'progress_notes_pca_{site}_{timestamp_pattern}_')]
        
        logger.info(f"Looking for files with pattern: {timestamp_pattern}")
        logger.info(f"Site: {site}")
        logger.info(f"All files in data directory: {[f for f in os.listdir(logs_dir) if 'Parafield' in f and '2025_05' in f]}")
        logger.info(f"Found RN/EN files: {rn_en_files}")
        logger.info(f"Found PCA files: {pca_files}")
        
        if rn_en_files and pca_files:
            # Select most recent file
            rn_en_files.sort(reverse=True)
            pca_files.sort(reverse=True)
            
            try:
                # Load RN/EN notes
                rn_en_filepath = os.path.join(logs_dir, rn_en_files[0])
                with open(rn_en_filepath, 'r', encoding='utf-8') as f:
                    rn_en_notes = json.load(f)
                logger.info(f"Loaded {len(rn_en_notes)} RN/EN notes from file: {rn_en_files[0]}")
                
                # Load PCA notes
                pca_filepath = os.path.join(logs_dir, pca_files[0])
                with open(pca_filepath, 'r', encoding='utf-8') as f:
                    pca_notes = json.load(f)
                logger.info(f"Loaded {len(pca_notes)} PCA notes from file: {pca_files[0]}")
                
                # Combine all notes
                all_resident_notes = rn_en_notes + pca_notes
                
                # Classify notes by type
                for note in rn_en_notes:
                    event_type_mapping[note.get('Id')] = "RN/EN"
                for note in pca_notes:
                    event_type_mapping[note.get('Id')] = "PCA"
                
                logger.info(f"Successfully loaded {len(all_resident_notes)} notes from saved files")
                
            except Exception as e:
                logger.error(f"Failed to load notes from files: {str(e)}")
                # Fetch from API if file load fails
                all_resident_notes = []
                rn_en_notes = []
                pca_notes = []
        else:
            logger.info(f"No saved files found for {site} {year}/{month}, fetching from API")
        
        # Fetch from API if no saved files or load failed
        if not all_resident_notes:
            # Fetch all at once including RN/EN, PCA event type IDs
            event_type_ids = []
            if rn_en_id:
                event_type_ids.append(rn_en_id)
            if pca_id:
                event_type_ids.append(pca_id)
            
            if event_type_ids:
                # Fetch all event types at once
                client = ProgressNoteFetchClient(site)
            
            # Set date range slightly wider (include 1 day before and after)
            extended_start_date = start_date - timedelta(days=1)
            extended_end_date = end_date + timedelta(days=1)
            
            debug_info['steps'].append({
                'step': 'fetch_notes_optimized',
                'event_type_ids': event_type_ids,
                'date_range': f"{extended_start_date.isoformat()} to {extended_end_date.isoformat()}",
                'notes_fetched': 0
            })
            
            # Individual calls per event type (if API doesn't support OR conditions)
            for event_type_id in event_type_ids:
                success, notes = client.fetch_progress_notes(
                    start_date=extended_start_date,
                    end_date=extended_end_date,
                    limit=None,  # No limit
                    progress_note_event_type_id=event_type_id
                )
                
                if success and notes is not None:
                    all_resident_notes.extend(notes)
                    
                    # Classify notes by type
                    if event_type_id == rn_en_id:
                        event_type_name = "RN/EN"
                    elif event_type_id == pca_id:
                        event_type_name = "PCA"
                    else:
                        event_type_name = "Unknown"
                    
                    for note in notes:
                        event_type_mapping[note.get('Id')] = event_type_name
                    
                    # Store notes separately by Event Type
                    if event_type_name == "RN/EN":
                        rn_en_notes = notes
                    elif event_type_name == "PCA":
                        pca_notes = notes
                    
                    debug_info['steps'][-1]['notes_fetched'] += len(notes)
                    logger.info(f"Fetched {len(notes)} notes for event type ID {event_type_id} ({event_type_name})")
                else:
                    logger.warning(f"No notes found for EventType ID {event_type_id}")
        else:
            logger.warning("No Resident of the day event types found")
        
        # Save Progress Notes to JSON file (separated by Event Type)
        try:
            logs_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save RN/EN notes
            if rn_en_notes:
                rn_en_filename = f'progress_notes_rn_en_{site}_{year}_{month:02d}_{timestamp}.json'
                rn_en_filepath = os.path.join(logs_dir, rn_en_filename)
                with open(rn_en_filepath, 'w', encoding='utf-8') as f:
                    json.dump(rn_en_notes, f, indent=2, ensure_ascii=False)
                logger.info(f"RN/EN notes saved to: {rn_en_filename}")
            
            # Save PCA notes
            if pca_notes:
                pca_filename = f'progress_notes_pca_{site}_{year}_{month:02d}_{timestamp}.json'
                pca_filepath = os.path.join(logs_dir, pca_filename)
                with open(pca_filepath, 'w', encoding='utf-8') as f:
                    json.dump(pca_notes, f, indent=2, ensure_ascii=False)
                logger.info(f"PCA notes saved to: {pca_filename}")
                
        except Exception as e:
            logger.error(f"Failed to save progress notes to JSON files: {str(e)}")
        
        debug_info['steps'].append({
            'step': 'total_notes_summary',
            'total_notes': len(all_resident_notes),
            'sample_notes': []
        })
        
        # Add sample notes to debug info
        if all_resident_notes:
            for i, note in enumerate(all_resident_notes[:3]):
                debug_info['steps'][-1]['sample_notes'].append({
                    'index': i+1,
                    'id': note.get('Id'),
                    'client_service_id': note.get('ClientServiceId'),
                    'event_type': note.get('ProgressNoteEventType', {}).get('Description', 'N/A'),
                    'event_date': note.get('EventDate', 'N/A')
                })
        
        # 5. Match notes by Residence and create status
        residence_status = {}
        unmatched_notes = []  # Track notes that failed to match
        
        # Check and process client data structure
        if isinstance(client_data, dict):
            client_list = list(client_data.values()) if client_data else []
        elif isinstance(client_data, list):
            client_list = client_data
        else:
            logger.error(f"Unexpected client data type: {type(client_data)}")
            client_list = []
        
        logger.info(f"Processing {len(client_list)} clients")
        
        # First, collect ClientRecordId for all residences
        residence_client_mapping = {}
        for residence in client_list:
            if isinstance(residence, dict):
                first_name = residence.get('FirstName', '')
                surname = residence.get('Surname', '')
                last_name = residence.get('LastName', '')
                preferred_name = residence.get('PreferredName', '')
                wing_name = residence.get('WingName', '')
                
                # Create Residence name - combine FirstName and Surname/LastName
                if first_name and surname:
                    residence_name = f"{first_name} {surname}"
                elif first_name and last_name:
                    residence_name = f"{first_name} {last_name}"
                elif first_name:
                    residence_name = first_name
                else:
                    continue
                
                # Find Residence's ClientRecordId (different field names used in real-time API data)
                residence_client_record_id = residence.get('ClientRecordId') or residence.get('Id') or residence.get('ClientId')
                
                # Store mapping of Residence name and ClientRecordId
                residence_client_mapping[residence_name] = residence_client_record_id
                
                # Display all residents on screen (even if no notes)
                residence_notes = []
                
                if residence_client_record_id:
                    # Find notes for that Residence (only matched notes)
                    for note in all_resident_notes:
                        note_client_id = note.get('ClientId')
                        
                        # Matching logic: match by ClientRecordId only
                        if note_client_id == residence_client_record_id:
                            residence_notes.append(note)
                
                # Add to residence_status even if no notes (display all residences)
                

                
                # Create status by Residence (create even if no notes)
                rn_en_has_note = False
                pca_has_note = False
                rn_en_count = 0
                pca_count = 0
                
                for note in residence_notes:
                    note_id = note.get('Id')
                    event_type_name = event_type_mapping.get(note_id)
                    
                    if event_type_name == "RN/EN":
                        rn_en_has_note = True
                        rn_en_count += 1
                    elif event_type_name == "PCA":
                        pca_has_note = True
                        pca_count += 1
                
                residence_status[residence_name] = {
                    'residence_name': residence_name,
                    'preferred_name': preferred_name,
                    'wing_name': wing_name,
                    'rn_en_has_note': rn_en_has_note,
                    'pca_has_note': pca_has_note,
                    'rn_en_count': rn_en_count,
                    'pca_count': pca_count,
                    'total_count': rn_en_count + pca_count
                }
        
        # Calculate unmatched notes (efficient method)
        matched_note_ids = set()
        
        logger.info(f"Total notes to process: {len(all_resident_notes)}")
        logger.info(f"Total residences available: {len(residence_client_mapping)}")
        
        # Check which residence each note matches
        for note in all_resident_notes:
            note_client_id = note.get('ClientId')
            note_matched = False
            
            # Compare with all residences' ClientRecordId
            for residence_name, residence_client_record_id in residence_client_mapping.items():
                if residence_client_record_id and note_client_id == residence_client_record_id:
                    matched_note_ids.add(note.get('Id'))
                    note_matched = True
                    break
            
            # Add unmatched notes
            if not note_matched:
                unmatched_note_info = {
                    'note_id': note.get('Id'),
                    'client_id': note_client_id,
                    'event_type': note.get('ProgressNoteEventType', {}).get('Description', 'Unknown'),
                    'event_date': note.get('EventDate', 'Unknown'),
                    'residence_name': 'Unknown',
                    'residence_client_record_id': 'Unknown'
                }
                unmatched_notes.append(unmatched_note_info)
        
        logger.info(f"Matched notes: {len(matched_note_ids)}")
        logger.info(f"Unmatched notes: {len(unmatched_notes)}")
        
        # Save debug info to file
        try:
            logs_dir = os.path.join(os.getcwd(), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f'rod_processing_{site}_{year}_{month:02d}_{timestamp}.json'
            filepath = os.path.join(logs_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save ROD processing debug log: {str(e)}")
        
        # Remove duplicates from unmatched notes
        unique_unmatched_notes = []
        seen_notes = set()
        for note in unmatched_notes:
            note_key = f"{note['note_id']}_{note['client_id']}"
            if note_key not in seen_notes:
                unique_unmatched_notes.append(note)
                seen_notes.add(note_key)
        
        # Save unmatched notes to JSON file
        if unique_unmatched_notes:
            try:
                logs_dir = os.path.join(os.getcwd(), 'data')
                os.makedirs(logs_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                unmatched_filename = f'unmatched_notes_{site}_{year}_{month:02d}_{timestamp}.json'
                unmatched_filepath = os.path.join(logs_dir, unmatched_filename)
                
                unmatched_data = {
                    'site': site,
                    'year': year,
                    'month': month,
                    'timestamp': datetime.now().isoformat(),
                    'total_notes': len(all_resident_notes),
                    'matched_notes': len(matched_note_ids),
                    'unmatched_notes_count': len(unique_unmatched_notes),
                    'unmatched_notes': unique_unmatched_notes,
                    'summary': {
                        'total_residences': len(residence_client_mapping),
                        'available_client_ids': list(residence_client_mapping.values()),
                        'unmatched_client_ids': list(set([note['client_id'] for note in unique_unmatched_notes]))
                    }
                }
                
                with open(unmatched_filepath, 'w', encoding='utf-8') as f:
                    json.dump(unmatched_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved {len(unique_unmatched_notes)} unmatched notes to: {unmatched_filename}")
                
            except Exception as e:
                logger.error(f"Failed to save unmatched notes to file: {str(e)}")
        else:
            logger.info("No unmatched notes found")
        
        logger.info(f"ROD processing completed for {site}: {len(residence_status)} residences, {len(unique_unmatched_notes)} unmatched notes")
        if len(residence_status) == 0:
            logger.warning("No residences found in residence_status!")
        
        # Add unmatched_notes information to residence_status
        result = {
            'residence_status': residence_status,
            'unmatched_notes': unique_unmatched_notes
        }
        return result
        
    except Exception as e:
        logger.error(f"Error in fetch_residence_of_day_notes_with_client_data: {str(e)}")
        return {}

def save_data_to_file(site: str, year: int, month: int, all_notes: list, residence_status: dict, debug_info: dict = None):
    """
    Save received data to JSON file.
    
    Args:
        site (str): Site name
        year (int): Year
        month (int): Month
        all_notes (list): All Progress Note data
        residence_status (dict): Status information by Residence
        debug_info (dict): Debugging information (optional)
    """
    try:
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{site}_{year:04d}{month:02d}_{timestamp}.json"
        filepath = os.path.join('data', filename)
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Compose JSON data
        data_to_save = {
            'site': site,
            'year': year,
            'month': month,
            'timestamp': timestamp,
            'raw_progress_notes': all_notes,
            'processed_residence_status': residence_status
        }
        
        # Add debugging information if available
        if debug_info:
            data_to_save['debug_info'] = debug_info
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to file: {filepath}")
        
    except Exception as e:
        logger.error(f"Error saving data to file: {str(e)}")

def fetch_residence_of_day_notes(site: str, start_date: datetime, end_date: datetime) -> tuple[bool, Optional[Dict[str, List[Dict[str, Any]]]]]:
    """
    Fetch notes with "Resident of the day" title from a specific site, grouped by Residence.
    
    Args:
        site: Site name
        start_date: Start date
        end_date: End date
        
    Returns:
        (success status, dictionary of notes by Residence or None)
    """
    try:
        client = ProgressNoteFetchClient(site)
        success, all_notes = client.fetch_progress_notes(start_date, end_date, limit=1000)
        
        if not success or not all_notes:
            logger.warning(f"No progress notes found for site {site}")
            return True, {}
        
        # Filter notes with "Resident of the day" title and group by Residence
        resident_notes = {}
        for note in all_notes:
            # Check if NotesDetailTitle is "Resident of the day"
            if note.get('NotesDetailTitle') and 'resident of the day' in note['NotesDetailTitle'].lower():
                # Extract Residence name (from "Resident of the day - [Residence Name]" format in NotesDetailTitle)
                title = note.get('NotesDetailTitle', '')
                residence_name = extract_residence_name_from_title(title)
                
                if residence_name:
                    if residence_name not in resident_notes:
                        resident_notes[residence_name] = []
                    resident_notes[residence_name].append(note)
        
        logger.info(f"Found Resident of the day notes for {len(resident_notes)} residences in site {site}")
        return True, resident_notes
        
    except Exception as e:
        logger.error(f"Error fetching Resident of the day notes for site {site}: {str(e)}")
        return False, None

def extract_residence_name_from_title(title: str) -> Optional[str]:
    """
    Extract Residence name from NotesDetailTitle.
    
    Args:
        title: NotesDetailTitle string
        
    Returns:
        Residence name or None
    """
    try:
        # Extract Residence name from "Resident of the day - [Residence Name]" format
        if 'resident of the day' in title.lower():
            # Consider text after dash (-) as Residence name
            parts = title.split('-')
            if len(parts) > 1:
                residence_name = parts[1].strip()
                return residence_name if residence_name else None
        
        # Try other formats
        if 'resident of the day' in title.lower():
            # "Resident of the day [Residence Name]" format
            import re
            match = re.search(r'resident of the day\s*[-:]\s*(.+)', title, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    except Exception as e:
        logger.error(f"Error extracting residence name from title '{title}': {str(e)}")
        return None

def fetch_residence_of_day_notes_for_all_sites(start_date: datetime, end_date: datetime) -> Dict[str, tuple[bool, Optional[List[Dict[str, Any]]]]]:
    """
    Fetch "Resident of the day" notes from all sites.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Dictionary of (success status, Resident of the day notes list) by site
    """
    results = {}
    
    for site in SITE_SERVERS.keys():
        try:
            success, data = fetch_residence_of_day_notes(site, start_date, end_date)
            results[site] = (success, data)
            logger.info(f"Site {site}: {'Success' if success else 'Failed'} - {len(data) if data else 0} Resident of the day notes")
        except Exception as e:
            logger.error(f"Error fetching Resident of the day data for site {site}: {str(e)}")
            results[site] = (False, None)
    
    return results

if __name__ == "__main__":
    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    test_progress_note_fetch() 