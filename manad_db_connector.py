"""
MANAD MSSQL Database Direct Connector (READ-ONLY)
Module for direct connection to MANAD MSSQL database to retrieve data

⚠️  Important: Works in READ-ONLY mode only
- All methods execute SELECT queries only
- Does not perform INSERT/UPDATE/DELETE operations
- autocommit=False + rollback() configuration to prevent mistakes
- Uses ApplicationIntent=ReadOnly connection option

Advantages:
- Real-time data access (no API latency)
- Performance improvement (batch queries, JOIN possible)
- No background synchronization needed (direct query when needed)
- Data accuracy (direct access to original data)
- Read-only guarantee (data integrity protection)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import json

logger = logging.getLogger(__name__)

# ============================================
# Site Config JSON Loader
# ============================================
_site_config_cache = None
_site_config_file = os.path.join(os.path.dirname(__file__), "data", "api_keys", "site_config.json")

def _load_site_config() -> List[Dict[str, Any]]:
    """Load site configuration from site_config.json (uses cache)"""
    global _site_config_cache
    
    if _site_config_cache is not None:
        return _site_config_cache
    
    try:
        if os.path.exists(_site_config_file):
            with open(_site_config_file, 'r', encoding='utf-8') as f:
                _site_config_cache = json.load(f)
                logger.info(f"✅ Loaded site_config.json: {len(_site_config_cache)} sites")
                return _site_config_cache
        else:
            logger.warning(f"⚠️ site_config.json file not found: {_site_config_file}")
            return []
    except Exception as e:
        logger.error(f"❌ Error loading site_config.json: {e}")
        return []

def get_site_db_config(site_name: str) -> Optional[Dict[str, Any]]:
    """Return DB configuration for a specific site"""
    configs = _load_site_config()
    
    for config in configs:
        if config.get('site_name') == site_name:
            db_config = config.get('database', {}).copy()
            # Try to convert server name to IP address if it's a hostname
            server = db_config.get('server', '')
            if server and '\\' in server:
                # Server name format: SQLSVR04\SQLEXPRESS or 192.168.1.1\SQLEXPRESS
                parts = server.split('\\')
                hostname_or_ip = parts[0]
                instance = parts[1] if len(parts) > 1 else ''
                
                # If not an IP address (hostname), get IP from API configuration
                if not hostname_or_ip.replace('.', '').isdigit():
                    api_config = config.get('api', {})
                    server_ip = api_config.get('server_ip')
                    if server_ip:
                        # Convert to IP address
                        db_config['server'] = f"{server_ip}\\{instance}" if instance else server_ip
                        logger.debug(f"🔧 Server name conversion: {server} -> {db_config['server']}")
            
            return db_config
    
    return None

def get_all_site_configs() -> List[Dict[str, Any]]:
    """Return all site configurations"""
    return _load_site_config()

# Library for MSSQL connection (pyodbc or pymssql)
def _install_driver_package(driver_name='pyodbc'):
    """Attempt to install MSSQL driver package"""
    import subprocess
    import sys
    
    try:
        logger.info(f"🔧 Attempting to install MSSQL driver: {driver_name}")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', driver_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {driver_name} installed")
            # Retry import
            if driver_name == 'pyodbc':
                import pyodbc  # type: ignore
                return 'pyodbc'
            elif driver_name == 'pymssql':
                import pymssql  # type: ignore
                return 'pymssql'
        else:
            logger.error(f"❌ {driver_name} install failed: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        logger.error(f"❌ {driver_name} install timed out (over 60 seconds)")
        return None
    except Exception as e:
        logger.error(f"❌ Error while installing {driver_name}: {e}")
        return None

# Check driver and attempt automatic installation
try:
    import pyodbc  # type: ignore
    DRIVER_AVAILABLE = 'pyodbc'
    logger.debug("✅ pyodbc driver available")
except ImportError:
    try:
        import pymssql  # type: ignore
        DRIVER_AVAILABLE = 'pymssql'
        logger.debug("✅ pymssql driver available")
    except ImportError:
        # Attempt automatic installation (pyodbc first)
        logger.warning("⚠️ MSSQL driver is not installed. Attempting automatic installation...")
        DRIVER_AVAILABLE = _install_driver_package('pyodbc')
        
        if not DRIVER_AVAILABLE:
            # Try pymssql if pyodbc installation failed
            logger.warning("⚠️ pyodbc install failed. Trying pymssql...")
            DRIVER_AVAILABLE = _install_driver_package('pymssql')
        
        if not DRIVER_AVAILABLE:
            logger.error("""
❌ MSSQL Driver Installation Failed

Automatic installation failed. Please install manually using the following methods:

1. Install via pip:
   pip install pyodbc
   or
   pip install pymssql

2. Check ODBC Driver on Windows:
   - If using pyodbc, ODBC Driver 17 for SQL Server is required.
   - Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

3. Verify installation:
   python -c "import pyodbc; print('pyodbc installation complete')"
   or
   python -c "import pymssql; print('pymssql installation complete')"

DB direct access mode is currently enabled, but driver is missing. Switching to API mode.
            """)


class MANADDBConnector:
    """MANAD MSSQL Database Direct Connection Class"""
    
    def __init__(self, site: str):
        """
        Args:
            site: Site name (e.g., 'Parafield Gardens')
        """
        self.site = site
        self.connection_string = self._get_connection_string(site)
        self._connection_pool = {}
    
    def _get_connection_string(self, site: str) -> Optional[str]:
        """Generate MSSQL connection string for each site
        
        Configuration priority:
        1. site_config.json (recommended)
        2. Environment variables (fallback)
        """
        # Step 1: Try to get DB settings from site_config.json
        db_config = get_site_db_config(site)
        
        if db_config:
            server = db_config.get('server')
            database = db_config.get('database')
            use_windows_auth = db_config.get('use_windows_auth', True)
            username = db_config.get('username')
            password = db_config.get('password')
            
            if server and database:
                logger.info(f"📄 Loaded DB settings from site_config.json: {site}")
            else:
                logger.warning(f"⚠️ DB info for {site} is incomplete in site_config.json.")
                db_config = None  # Proceed with fallback
        
        # Step 2: Get DB connection info from environment variables (fallback)
        if not db_config:
            site_key = site.upper().replace(' ', '_').replace('-', '_')
            
            server = os.environ.get(f'MANAD_DB_SERVER_{site_key}')
            database = os.environ.get(f'MANAD_DB_NAME_{site_key}') or os.environ.get('MANAD_DB_NAME')
            
            # Windows Authentication support
            use_windows_auth = os.environ.get(f'MANAD_DB_USE_WINDOWS_AUTH_{site_key}', '').lower() == 'true'
            use_windows_auth = use_windows_auth or os.environ.get('MANAD_DB_USE_WINDOWS_AUTH', 'false').lower() == 'true'
            
            if not server or not database:
                logger.warning(
                    f"⚠️ DB server/database is not configured for {site}. (Check site_config.json or environment variables)"
                )
                return None
            
            username = os.environ.get(f'MANAD_DB_USER_{site_key}') or os.environ.get('MANAD_DB_USER')
            password = os.environ.get(f'MANAD_DB_PASSWORD_{site_key}') or os.environ.get('MANAD_DB_PASSWORD')
            
            logger.info(f"📄 Loaded DB settings from environment (fallback): {site}")
        
        # Check if Windows Authentication is used
        if not use_windows_auth:
            if not username or not password:
                logger.warning(f"⚠️ DB username/password is not configured for {site}.")
                return None
        
        # pyodbc connection string
        if DRIVER_AVAILABLE == 'pyodbc':
            # Check available drivers
            try:
                import pyodbc
                available_drivers = pyodbc.drivers()
                # Priority: ODBC Driver 17/18 > SQL Server Native Client > SQL Server
                preferred_drivers = [
                    '{ODBC Driver 17 for SQL Server}',
                    '{ODBC Driver 18 for SQL Server}',
                    'ODBC Driver 17 for SQL Server',
                    'ODBC Driver 18 for SQL Server',
                    'SQL Server Native Client 11.0',
                    'SQL Server'
                ]
                driver = None
                for preferred in preferred_drivers:
                    if preferred in available_drivers:
                        driver = preferred
                        break
                
                if not driver:
                    # Use driver specified in environment variable
                    driver = os.environ.get('MANAD_DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
                    logger.warning(f"⚠️ Using default driver: {driver} (may not be installed on this system)")
                else:
                    logger.debug(f"✅ Driver to use: {driver}")
            except Exception as e:
                # Fallback: environment variable or default value
                driver = os.environ.get('MANAD_DB_DRIVER', 'SQL Server')
                logger.warning(f"⚠️ Driver check failed, using default: {driver} ({e})")
            
            # Use Windows Authentication
            if use_windows_auth:
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                    f"Connection Timeout=30;"
                    f"ApplicationIntent=ReadOnly;"  # Read-only mode
                )
                logger.info(f"✅ Using Windows Authentication (READ-ONLY): {site} ({server})")
            else:
                # Use SQL Server Authentication
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"UID={username};"
                    f"PWD={password};"
                    f"TrustServerCertificate=yes;"
                    f"Connection Timeout=30;"
                    f"ApplicationIntent=ReadOnly;"  # Read-only mode
                )
                logger.info(f"✅ Using SQL Server Authentication (READ-ONLY): {site} ({server})")
                logger.debug(f"   Connection info: UID={username}, DATABASE={database}")
            
            return conn_str
        
        # pymssql connection info (return as dictionary)
        elif DRIVER_AVAILABLE == 'pymssql':
            if use_windows_auth:
                # pymssql does not directly support Windows Authentication, so warn
                logger.warning("⚠️ pymssql does not support Windows Authentication. Use pyodbc instead.")
                return None
            
            return {
                'server': server,
                'database': database,
                'user': username,
                'password': password,
                'timeout': 30
            }
        
        return None
    
    @contextmanager
    def get_connection(self):
        """
        Database connection context manager (READ-ONLY mode)
        
        ⚠️  Important: This is a read-only connection
        
        Security policy:
        1. ApplicationIntent=ReadOnly: Set in connection string
        2. autocommit=False: Auto-commit disabled
        3. rollback(): Automatic rollback in finally block
        4. commit() not called: Never commit data changes
        
        Usage example:
            with connector.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Event")  # ✅ OK
                # cursor.execute("INSERT INTO ...")    # ⚠️ Will be rolled back even if executed
        """
        conn = None
        try:
            if not self.connection_string:
                raise ValueError(f"DB connection information for {self.site} is not configured.")
            
            if DRIVER_AVAILABLE == 'pyodbc':
                # Ensure module name is available even if driver was auto-installed
                import pyodbc  # type: ignore
                conn = pyodbc.connect(self.connection_string)  # type: ignore
                
                # Read-only security settings
                conn.autocommit = False  # Cannot change without explicit commit
                
                # Improve read performance with READ UNCOMMITTED (minimize locks)
                cursor = conn.cursor()
                try:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                    logger.debug(f"🔒 READ-ONLY mode: {self.site}")
                except:
                    pass  # May not be supported in some environments
                cursor.close()
                
            elif DRIVER_AVAILABLE == 'pymssql':
                # Ensure module name is available even if driver was auto-installed
                import pymssql  # type: ignore
                conn = pymssql.connect(**self.connection_string)  # type: ignore
                conn.autocommit = False
            else:
                error_msg = (
                    "MSSQL driver is not installed.\n"
                    "Please install using:\n"
                    "  pip install pyodbc\n"
                    "or\n"
                    "  pip install pymssql\n\n"
                    "Windows users also need ODBC Driver 17 for SQL Server."
                )
                raise ImportError(error_msg)
            
            yield conn
            
            # ⚠️ Important: commit() is not called (READ-ONLY guarantee)
            # All changes are automatically rolled back in finally block
            
        except Exception as e:
            logger.error(f"❌ DB connection error ({self.site}): {e}")
            raise
        finally:
            if conn:
                try:
                    # Read-only guarantee: rollback all changes
                    if not conn.autocommit:
                        conn.rollback()
                    conn.close()
                    logger.debug(f"🔒 Connection closed (rollback complete): {self.site}")
                except:
                    pass
    
    def fetch_incidents(self, start_date: str, end_date: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Query Incident data directly from DB
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            (Success status, Incident list)
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL driver is not installed.\n"
                "Please install using:\n"
                "  pip install pyodbc\n"
                "or\n"
                "  pip install pymssql\n\n"
                "Windows users also need ODBC Driver 17 for SQL Server:\n"
                "https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
            )
            logger.error(error_msg)
            raise ImportError("MSSQL driver is not installed. Please run: pip install pyodbc or pip install pymssql")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query matching actual MANAD DB structure
                # AdverseEvent table: Actual table where Incident data is stored
                # StatusEnumId: 0=Open, 1=In Progress(?), 2=Closed
                query = """
                    SELECT 
                        ae.Id,
                        ae.ClientId,
                        ae.Date,
                        ae.ReportedDate,
                        ae.Description,
                        ISNULL(aesr.Description, '') AS SeverityRating,
                        ISNULL(aerr.Description, '') AS RiskRatingName,
                        ae.StatusEnumId,
                        CASE 
                            WHEN ae.StatusEnumId = 0 THEN 'Open'
                            WHEN ae.StatusEnumId = 2 THEN 'Closed'
                            ELSE 'In Progress'
                        END AS Status,
                        ae.ActionTaken,
                        ISNULL(pr_reported.FirstName + ' ' + pr_reported.LastName, '') AS ReportedByName,
                        '' AS RoomName,
                        '' AS WingName,
                        '' AS DepartmentName,
                        ISNULL(p_client.FirstName, '') AS FirstName,
                        ISNULL(p_client.LastName, '') AS LastName,
                        ae.IsWitnessed,
                        ae.IsReviewClosed,
                        ae.IsAmbulanceCalled,
                        ae.IsAdmittedToHospital,
                        ae.IsMajorInjury,
                        ae.ReviewedDate,
                        -- Event Types (using AdverseEvent_AdverseEventType junction table)
                        ISNULL(
                            (SELECT TOP 1 aet.Description 
                             FROM AdverseEvent_AdverseEventType ae_aet 
                             JOIN AdverseEventType aet ON ae_aet.AdverseEventTypeId = aet.Id 
                             WHERE ae_aet.AdverseEventId = ae.Id), 
                            ''
                        ) AS EventTypeName
                    FROM AdverseEvent ae
                    LEFT JOIN Person p_client ON ae.ClientId = p_client.Id
                    LEFT JOIN AdverseEventSeverityRating aesr ON ae.AdverseEventSeverityRatingId = aesr.Id
                    LEFT JOIN AdverseEventRiskRating aerr ON ae.AdverseEventRiskRatingId = aerr.Id
                    LEFT JOIN Person pr_reported ON ae.ReportedById = pr_reported.Id
                    WHERE ae.Date >= ? AND ae.Date <= ?
                    AND ae.IsDeleted = 0
                    ORDER BY ae.Date DESC
                """
                
                # Convert date parameters
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)  # Add one day to include end date
                
                logger.info(f"🔍 Executing DB query: {self.site} ({start_date} ~ {end_date})")
                
                cursor.execute(query, (start_dt, end_dt))
                
                # Convert results to dictionary
                columns = [column[0] for column in cursor.description]
                incidents = []
                
                for row in cursor.fetchall():
                    incident_dict = dict(zip(columns, row))
                    
                    # Convert to API format
                    formatted_incident = self._format_incident_for_api(incident_dict)
                    incidents.append(formatted_incident)
                
                logger.info(f"✅ Incident fetch completed: {self.site} - {len(incidents)} incidents")
                
                return True, incidents
                
        except Exception as e:
            logger.error(f"❌ Incident fetch error ({self.site}): {e}")
            return False, None
    
    def fetch_clients(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Query Client data directly from DB
        
        Returns:
            (Success status, Client list)
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL driver is not installed.\n"
                "Please install using:\n"
                "  pip install pyodbc\n"
                "or\n"
                "  pip install pymssql\n\n"
                "Windows users also need ODBC Driver 17 for SQL Server:\n"
                "https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
            )
            logger.error(error_msg)
            raise ImportError("MSSQL driver is not installed. Please run: pip install pyodbc or pip install pymssql")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query matching actual MANAD DB Client table structure
                # Client -> Person JOIN required (name information is in Person table)
                # Query only active residents (using same logic as Edenfield Dashboard)
                # Check active service via MainClientServiceId (only those with EndDate NULL)
                query_with_service = """
                    SELECT 
                        c.Id,
                        c.MainClientServiceId,
                        ISNULL(p.FirstName, '') AS FirstName,
                        ISNULL(p.MiddleName, '') AS MiddleName,
                        ISNULL(p.LastName, '') AS LastName,
                        ISNULL(p.PreferredName, '') AS PreferredName,
                        p.BirthDate AS BirthDate,
                        ISNULL(w.Name, '') AS WingName,
                        ISNULL(cs.WingId, 0) AS WingId,
                        ISNULL(cs.LocationId, 0) AS LocationId,
                        ISNULL(loc.Name, '') AS LocationName,
                        cs.StartDate AS AdmissionDate,
                        cs.EndDate AS DepartureDate,
                        CASE WHEN cs.EndDate IS NULL THEN 'Permanent' ELSE 'Temporary' END AS CareType,
                        CASE WHEN c.IsDeleted = 0 THEN 1 ELSE 0 END AS IsActive
                    FROM Client c
                    INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                    LEFT JOIN Person p ON c.PersonId = p.Id
                    LEFT JOIN Wing w ON cs.WingId = w.Id
                    LEFT JOIN Location loc ON cs.LocationId = loc.Id
                    WHERE c.IsDeleted = 0 
                        AND cs.IsDeleted = 0
                        AND cs.EndDate IS NULL
                    ORDER BY ISNULL(p.LastName, ''), ISNULL(p.FirstName, '')
                """
                
                query_simple = """
                    SELECT 
                        c.Id,
                        c.MainClientServiceId,
                        ISNULL(p.FirstName, '') AS FirstName,
                        ISNULL(p.MiddleName, '') AS MiddleName,
                        ISNULL(p.LastName, '') AS LastName,
                        ISNULL(p.PreferredName, '') AS PreferredName,
                        p.BirthDate AS BirthDate,
                        ISNULL(w.Name, '') AS WingName,
                        ISNULL(cs.WingId, 0) AS WingId,
                        ISNULL(cs.LocationId, 0) AS LocationId,
                        ISNULL(loc.Name, '') AS LocationName,
                        cs.StartDate AS AdmissionDate,
                        NULL AS DepartureDate,
                        'Permanent' AS CareType,
                        CASE WHEN c.IsDeleted = 0 THEN 1 ELSE 0 END AS IsActive
                    FROM Client c
                    INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                    LEFT JOIN Person p ON c.PersonId = p.Id
                    LEFT JOIN Wing w ON cs.WingId = w.Id
                    LEFT JOIN Location loc ON cs.LocationId = loc.Id
                    WHERE c.IsDeleted = 0 
                        AND cs.IsDeleted = 0
                        AND cs.EndDate IS NULL
                    ORDER BY ISNULL(p.LastName, ''), ISNULL(p.FirstName, '')
                """
                
                logger.info(f"🔍 Fetching clients: {self.site}")
                
                # First try query with ClientService
                try:
                    cursor.execute(query_with_service)
                except Exception as e:
                    # Use simple query if ClientService table doesn't exist or error occurs
                    logger.warning(f"ClientService filtering query failed; using simple query: {e}")
                    cursor.execute(query_simple)
                
                columns = [column[0] for column in cursor.description]
                clients = []
                
                for row in cursor.fetchall():
                    client_dict = dict(zip(columns, row))
                    
                    # Convert to API format
                    formatted_client = self._format_client_for_api(client_dict)
                    clients.append(formatted_client)
                
                logger.info(f"✅ Client fetch completed: {self.site} - {len(clients)} clients")
                
                return True, clients
                
        except Exception as e:
            logger.error(f"❌ Client fetch error ({self.site}): {e}")
            return False, None
    
    def _format_incident_for_api(self, db_row: Dict) -> Dict[str, Any]:
        """Convert DB result to API format"""
        # Parse EventTypeName (single or multiple)
        event_types = []
        event_type_name = db_row.get('EventTypeName') or db_row.get('EventTypeNames')
        if event_type_name:
            event_types = [et.strip() for et in str(event_type_name).split(',') if et.strip()]
        
        # Match API response format
        return {
            'Id': db_row.get('Id'),
            'ClientId': db_row.get('ClientId'),
            'Date': db_row.get('Date').isoformat() if db_row.get('Date') else None,
            'ReportedDate': db_row.get('ReportedDate').isoformat() if db_row.get('ReportedDate') else None,
            'Description': db_row.get('Description', ''),
            'SeverityRating': db_row.get('SeverityRating'),
            'RiskRatingName': db_row.get('RiskRatingName'),
            'StatusEnumId': db_row.get('StatusEnumId'),
            'Status': db_row.get('Status', 'Open'),
            'ActionTaken': db_row.get('ActionTaken', ''),
            'ReportedByName': db_row.get('ReportedByName', ''),
            'RoomName': db_row.get('RoomName', ''),
            'WingName': db_row.get('WingName', ''),
            'DepartmentName': db_row.get('DepartmentName', ''),
            'FirstName': db_row.get('FirstName', ''),
            'LastName': db_row.get('LastName', ''),
            'EventTypeNames': event_types,
            'EventTypeName': event_type_name or '',
            'IsWitnessed': bool(db_row.get('IsWitnessed', False)),
            'IsReviewClosed': bool(db_row.get('IsReviewClosed', False)),
            'IsAmbulanceCalled': bool(db_row.get('IsAmbulanceCalled', False)),
            'IsAdmittedToHospital': bool(db_row.get('IsAdmittedToHospital', False)),
            'IsMajorInjury': bool(db_row.get('IsMajorInjury', False)),
            'ReviewedDate': db_row.get('ReviewedDate').isoformat() if db_row.get('ReviewedDate') else None
        }
    
    def _format_client_for_api(self, db_row: Dict) -> Dict[str, Any]:
        """Convert DB result to API format"""
        birth_date = db_row.get('BirthDate')
        admission_date = db_row.get('AdmissionDate')
        departure_date = db_row.get('DepartureDate')
        
        return {
            'Id': db_row.get('Id'),
            'FirstName': db_row.get('FirstName', ''),
            'MiddleName': db_row.get('MiddleName', ''),
            'LastName': db_row.get('LastName', ''),
            'PreferredName': db_row.get('PreferredName', ''),
            'BirthDate': birth_date.isoformat() if birth_date and hasattr(birth_date, 'isoformat') else (str(birth_date) if birth_date else None),
            'WingName': db_row.get('WingName', ''),
            'LocationId': db_row.get('LocationId', 0),
            'LocationName': db_row.get('LocationName', ''),
            'AdmissionDate': admission_date.isoformat() if admission_date and hasattr(admission_date, 'isoformat') else (str(admission_date) if admission_date else None),
            'DepartureDate': departure_date.isoformat() if departure_date and hasattr(departure_date, 'isoformat') else (str(departure_date) if departure_date else None),
            'CareType': db_row.get('CareType', 'Permanent'),
            'MainClientServiceId': db_row.get('MainClientServiceId'),  # Add MainClientServiceId needed for filtering
            'IsActive': bool(db_row.get('IsActive', False))
        }
    
    def fetch_progress_notes(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             limit: int = 500,
                             progress_note_event_type_id: Optional[int] = None,
                             client_service_id: Optional[int] = None) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Query Progress Notes data directly from DB
        
        Args:
            start_date: Start date (datetime, default: 14 days ago)
            end_date: End date (datetime, default: now)
            limit: Maximum number of records to fetch
            progress_note_event_type_id: Filter by specific event type ID
            client_service_id: Filter by specific client service ID
            
        Returns:
            (Success status, Progress Notes list) - Same format as API response
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL driver is not installed.\n"
                "Please install using:\n"
                "  pip install pyodbc\n"
                "or\n"
                "  pip install pymssql\n\n"
                "Windows users also need ODBC Driver 17 for SQL Server."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL driver is not installed.")
        
        try:
            # Set default values
            if start_date is None:
                start_date = datetime.now() - timedelta(days=14)
            if end_date is None:
                end_date = datetime.now()
            
            logger.info(f"🔍 [FILTER] Starting fetch_progress_notes - site={self.site}, client_service_id={client_service_id}, limit={limit}")
            logger.info(f"🔍 [FILTER] Date range: {start_date.date()} ~ {end_date.date()}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # ProgressNote query (matching API response format)
                # Includes Client, Wing, Location information
                query = """
                    SELECT TOP (?)
                        pn.Id,
                        pn.ClientId,
                        pn.ClientServiceId,
                        pn.Date AS EventDate,
                        pn.CreatedDate,
                        pn.IsLateEntry,
                        pn.ProgressNoteRiskRatingId,
                        pn.ProgressNoteEventTypeId,
                        pn.IsArchived,
                        pn.IsDeleted,
                        -- Person information (ClientId -> Client -> PersonId -> Person)
                        ISNULL(p.FirstName, '') AS ClientFirstName,
                        ISNULL(p.LastName, '') AS ClientLastName,
                        ISNULL(p.PreferredName, '') AS ClientPreferredName,
                        '' AS ClientTitle,  -- Person table does not have Title column
                        -- ClientService information (Service Wing, Location)
                        ISNULL(cs.WingId, 0) AS WingId,
                        ISNULL(w.Name, '') AS WingName,
                        ISNULL(cs.LocationId, 0) AS LocationId,
                        ISNULL(loc.Name, '') AS LocationName,
                        -- ProgressNoteEventType
                        ISNULL(pne.Id, 0) AS EventTypeId,
                        ISNULL(pne.Description, '') AS EventTypeDescription,
                        ISNULL(pne.ColorArgb, 0) AS EventTypeColorArgb,
                        -- ProgressNoteDetail (Note text)
                        (SELECT TOP 1 Note FROM ProgressNoteDetail WHERE ProgressNoteId = pn.Id) AS NotesPlainText,
                        -- CreatedByUser information (simple version)
                        ISNULL(pn.CreatedByUserId, 0) AS CreatedByUserId
                    FROM ProgressNote pn
                    LEFT JOIN Client c ON pn.ClientId = c.Id
                    LEFT JOIN Person p ON c.PersonId = p.Id
                    LEFT JOIN ClientService cs ON pn.ClientServiceId = cs.Id
                    LEFT JOIN Wing w ON cs.WingId = w.Id
                    LEFT JOIN Location loc ON cs.LocationId = loc.Id
                    LEFT JOIN ProgressNoteEventType pne ON pn.ProgressNoteEventTypeId = pne.Id
                    WHERE pn.IsDeleted = 0
                    AND pn.Date >= ? AND pn.Date <= ?
                """
                
                # Event Type filtering
                if progress_note_event_type_id is not None:
                    query += " AND pn.ProgressNoteEventTypeId = ?"
                    logger.info(f"🔍 [FILTER] Added Event Type filter: {progress_note_event_type_id}")
                
                # Client Service ID filtering
                if client_service_id is not None:
                    query += " AND pn.ClientServiceId = ?"
                    logger.info(f"🔍 [FILTER] Adding Client Service ID filter: {client_service_id} (type: {type(client_service_id)})")
                else:
                    logger.info("🔍 [FILTER] No Client Service ID filter - fetching all clients")
                
                query += " ORDER BY pn.Date DESC"
                
                params = [limit, start_date, end_date]
                if progress_note_event_type_id is not None:
                    params.append(progress_note_event_type_id)
                if client_service_id is not None:
                    params.append(client_service_id)
                
                logger.info("🔍 [FILTER] SQL query prepared")
                logger.info(f"🔍 [FILTER] Query params: limit={limit}, start_date={start_date}, end_date={end_date}, client_service_id={client_service_id}")
                logger.info(f"🔍 Fetching Progress Notes: {self.site} ({start_date.date()} ~ {end_date.date()})")
                logger.info("🔍 [FILTER] Executing SQL query...")
                
                cursor.execute(query, params)
                logger.info("🔍 [FILTER] SQL query completed")
                
                columns = [column[0] for column in cursor.description]
                progress_notes = []
                progress_note_ids = []
                
                logger.info(f"🔍 [FILTER] Query column count: {len(columns)}")
                logger.info("🔍 [FILTER] Calling fetchall()...")
                rows = cursor.fetchall()
                logger.info(f"🔍 [FILTER] fetchall() returned {len(rows)} rows")
                for row in rows:
                    note_dict = dict(zip(columns, row))
                    progress_note_ids.append(note_dict['Id'])
                
                # Get CareArea mapping information (grouped by ProgressNote ID)
                care_area_mappings = {}
                if progress_note_ids:
                    placeholders = ','.join('?' * len(progress_note_ids))
                    care_area_query = f"""
                        SELECT ProgressNoteId, CareAreaId
                        FROM ProgressNote_CareArea
                        WHERE ProgressNoteId IN ({placeholders})
                    """
                    cursor.execute(care_area_query, progress_note_ids)
                    for mapping_row in cursor.fetchall():
                        progress_note_id, care_area_id = mapping_row
                        if progress_note_id not in care_area_mappings:
                            care_area_mappings[progress_note_id] = []
                        care_area_mappings[progress_note_id].append(care_area_id)
                    
                    # Get CareArea detail information
                    if care_area_mappings:
                        all_care_area_ids = []
                        for mapping_ids in care_area_mappings.values():
                            all_care_area_ids.extend(mapping_ids)
                        
                        if all_care_area_ids:
                            unique_ca_ids = list(set(all_care_area_ids))
                            ca_placeholders = ','.join('?' * len(unique_ca_ids))
                            care_area_detail_query = f"""
                                SELECT Id, Description
                                FROM CareArea
                                WHERE Id IN ({ca_placeholders})
                            """
                            cursor.execute(care_area_detail_query, unique_ca_ids)
                            care_area_details = {}
                            for ca_row in cursor.fetchall():
                                care_area_details[ca_row[0]] = ca_row[1]
                        else:
                            care_area_details = {}
                    else:
                        care_area_details = {}
                
                # Build ProgressNote data
                for row in rows:
                    note_dict = dict(zip(columns, row))
                    
                    # Generate Care Areas information
                    care_areas = []
                    progress_note_id = note_dict['Id']
                    if progress_note_id in care_area_mappings:
                        for ca_id in care_area_mappings[progress_note_id]:
                            if ca_id in care_area_details:
                                care_areas.append({
                                    'Id': ca_id,
                                    'Description': care_area_details[ca_id]
                                })
                    
                    # Convert to API response format
                    formatted_note = {
                        'Id': note_dict['Id'],
                        'ClientId': note_dict['ClientId'],
                        'ClientServiceId': note_dict.get('ClientServiceId'),
                        'EventDate': note_dict['EventDate'].isoformat() if note_dict['EventDate'] else None,
                        'CreatedDate': note_dict['CreatedDate'].isoformat() if note_dict['CreatedDate'] else None,
                        'IsLateEntry': bool(note_dict.get('IsLateEntry', False)),
                        'ProgressNoteRiskRatingId': note_dict.get('ProgressNoteRiskRatingId'),
                        'IsArchived': bool(note_dict.get('IsArchived', False)),
                        'IsDeleted': bool(note_dict.get('IsDeleted', False)),
                        'NotesPlainText': note_dict.get('NotesPlainText', ''),
                        'ProgressNoteEventType': {
                            'Id': note_dict.get('EventTypeId', 0),
                            'Description': note_dict.get('EventTypeDescription', ''),
                            'ColorArgb': note_dict.get('EventTypeColorArgb', 0)
                        },
                        'CreatedByUser': {
                            'Id': note_dict.get('CreatedByUserId', 0)
                        },
                        # Add Client information
                        'Client': {
                            'FirstName': note_dict.get('ClientFirstName', ''),
                            'LastName': note_dict.get('ClientLastName', ''),
                            'PreferredName': note_dict.get('ClientPreferredName', ''),
                            'Title': note_dict.get('ClientTitle', '')
                        },
                        # Add Service Wing, Location information
                        'WingName': note_dict.get('WingName', ''),
                        'LocationName': note_dict.get('LocationName', ''),
                        # Add Care Areas
                        'CareAreas': care_areas
                    }
                    
                    progress_notes.append(formatted_note)
                
                logger.info(f"✅ Progress Notes fetch completed: {self.site} - {len(progress_notes)} notes")
                if client_service_id:
                    logger.info(
                        f"🔍 [FILTER] Client filter result: client_service_id={client_service_id}, notes={len(progress_notes)}"
                    )
                    if len(progress_notes) > 0:
                        sample_note = progress_notes[0]
                        logger.info(
                            f"🔍 [FILTER] First note sample: Id={sample_note.get('Id')}, ClientServiceId={sample_note.get('ClientServiceId')}"
                        )
                
                return True, progress_notes
                
        except Exception as e:
            logger.error(f"🔍 [FILTER] Error fetching Progress Notes: {e}")
            logger.error(f"🔍 [FILTER] client_service_id={client_service_id}, start_date={start_date}, end_date={end_date}")
            logger.error(f"❌ Progress Notes fetch error ({self.site}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None
    
    def fetch_care_areas(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Query Care Area data directly from DB
        
        Returns:
            (Success status, Care Area list) - Same format as API response
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL driver is not installed.\n"
                "Please install using:\n"
                "  pip install pyodbc\n"
                "or\n"
                "  pip install pymssql\n\n"
                "Windows users also need ODBC Driver 17 for SQL Server."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL driver is not installed.")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT 
                        Id,
                        Description,
                        IsArchived,
                        IsLocked,
                        CreatedDate,
                        LastUpdatedDate
                    FROM CareArea
                    WHERE IsArchived = 0
                    ORDER BY Description
                """
                
                logger.info(f"🔍 Fetching Care Areas: {self.site}")
                
                cursor.execute(query)
                
                columns = [column[0] for column in cursor.description]
                care_areas = []
                
                for row in cursor.fetchall():
                    area_dict = dict(zip(columns, row))
                    
                    # Convert to API response format
                    formatted_area = {
                        'Id': area_dict['Id'],
                        'Description': area_dict['Description'],
                        'IsArchived': bool(area_dict.get('IsArchived', False)),
                        'IsLocked': bool(area_dict.get('IsLocked', False)),
                        'CreatedDate': area_dict['CreatedDate'].isoformat() if area_dict.get('CreatedDate') else None,
                        'LastUpdatedDate': area_dict['LastUpdatedDate'].isoformat() if area_dict.get('LastUpdatedDate') else None
                    }
                    
                    care_areas.append(formatted_area)
                
                logger.info(f"✅ Care Area fetch completed: {self.site} - {len(care_areas)} items")
                
                return True, care_areas
                
        except Exception as e:
            logger.error(f"❌ Care Area fetch error ({self.site}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None
    
    def fetch_event_types(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Query Progress Note Event Type data directly from DB
        
        Returns:
            (Success status, Event Type list) - Same format as API response
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL driver is not installed.\n"
                "Please install using:\n"
                "  pip install pyodbc\n"
                "or\n"
                "  pip install pymssql\n\n"
                "Windows users also need ODBC Driver 17 for SQL Server."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL driver is not installed.")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT 
                        Id,
                        Description,
                        ColorArgb,
                        IsArchived,
                        IsLocked,
                        CreatedDate,
                        LastUpdatedDate
                    FROM ProgressNoteEventType
                    WHERE IsArchived = 0
                    ORDER BY Description
                """
                
                logger.info(f"🔍 Fetching Progress Note Event Types: {self.site}")
                
                cursor.execute(query)
                
                columns = [column[0] for column in cursor.description]
                event_types = []
                
                for row in cursor.fetchall():
                    type_dict = dict(zip(columns, row))
                    
                    # Convert to API response format
                    formatted_type = {
                        'Id': type_dict['Id'],
                        'Description': type_dict['Description'],
                        'ColorArgb': type_dict.get('ColorArgb', 0),
                        'IsArchived': bool(type_dict.get('IsArchived', False)),
                        'IsLocked': bool(type_dict.get('IsLocked', False)),
                        'CreatedDate': type_dict['CreatedDate'].isoformat() if type_dict.get('CreatedDate') else None,
                        'LastUpdatedDate': type_dict['LastUpdatedDate'].isoformat() if type_dict.get('LastUpdatedDate') else None
                    }
                    
                    event_types.append(formatted_type)
                
                logger.info(f"✅ Event Type fetch completed: {self.site} - {len(event_types)} items")
                
                return True, event_types
                
        except Exception as e:
            logger.error(f"❌ Event Type fetch error ({self.site}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None


def fetch_incidents_with_client_data_from_db(
    site: str, 
    start_date: str, 
    end_date: str, 
    fetch_clients: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Function to fetch Incident and Client data directly from DB
    (Same interface as existing API function)
    
    Args:
        site: Site name
        start_date: Start date
        end_date: End date
        fetch_clients: Whether to also fetch Client data
        
    Returns:
        Dictionary in format {'incidents': [...], 'clients': [...]}
    """
    try:
        connector = MANADDBConnector(site)
        
        # Query Incidents
        incidents_success, incidents = connector.fetch_incidents(start_date, end_date)
        if not incidents_success:
            logger.error(f"Failed to fetch incidents from DB for {site}")
            return None
        
        # Query Clients (optional)
        clients = []
        if fetch_clients:
            clients_success, clients = connector.fetch_clients()
            if not clients_success:
                logger.warning(f"Failed to fetch clients from DB for {site}, proceeding with empty client list")
                clients = []
        
        # Return in same format as API
        return {
            'incidents': incidents or [],
            'clients': clients or []
        }
        
    except Exception as e:
        logger.error(f"❌ DB query error ({site}): {e}")
        return None

