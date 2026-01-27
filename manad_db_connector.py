"""
MANAD MSSQL Database Direct Connector (READ-ONLY)
MANAD MSSQL 데이터베이스에 직접 접속하여 데이터를 가져오는 모듈

⚠️  중요: READ-ONLY 모드로만 작동합니다
- 모든 메서드는 SELECT 쿼리만 실행합니다
- INSERT/UPDATE/DELETE 작업을 수행하지 않습니다
- autocommit=False + rollback() 설정으로 실수 방지
- ApplicationIntent=ReadOnly 연결 옵션 사용

장점:
- 실시간 데이터 접근 (API 레이턴시 없음)
- 성능 향상 (배치 쿼리, JOIN 가능)
- 백그라운드 동기화 불필요 (필요할 때마다 직접 조회)
- 데이터 정확성 (원본 데이터 직접 접근)
- 읽기 전용 보장 (데이터 무결성 보호)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import os
import json

logger = logging.getLogger(__name__)

# ============================================
# Site Config JSON 로더
# ============================================
_site_config_cache = None
_site_config_file = os.path.join(os.path.dirname(__file__), "data", "api_keys", "site_config.json")

def _load_site_config() -> List[Dict[str, Any]]:
    """site_config.json에서 사이트 설정 로드 (캐시 사용)"""
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
    """특정 사이트의 DB 설정 반환"""
    configs = _load_site_config()
    
    for config in configs:
        if config.get('site_name') == site_name:
            db_config = config.get('database', {}).copy()
            # 서버 이름이 호스트명인 경우 IP 주소로 변환 시도
            server = db_config.get('server', '')
            if server and '\\' in server:
                # 서버 이름 형식: SQLSVR04\SQLEXPRESS 또는 192.168.1.1\SQLEXPRESS
                parts = server.split('\\')
                hostname_or_ip = parts[0]
                instance = parts[1] if len(parts) > 1 else ''
                
                # IP 주소가 아닌 경우 (호스트명인 경우) API 설정에서 IP 가져오기
                if not hostname_or_ip.replace('.', '').isdigit():
                    api_config = config.get('api', {})
                    server_ip = api_config.get('server_ip')
                    if server_ip:
                        # IP 주소로 변환
                        db_config['server'] = f"{server_ip}\\{instance}" if instance else server_ip
                        logger.debug(f"🔧 Server name conversion: {server} -> {db_config['server']}")
            
            return db_config
    
    return None

def get_all_site_configs() -> List[Dict[str, Any]]:
    """모든 사이트 설정 반환"""
    return _load_site_config()

# MSSQL 연결을 위한 라이브러리 (pyodbc 또는 pymssql)
def _install_driver_package(driver_name='pyodbc'):
    """MSSQL 드라이버 패키지 설치 시도"""
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
            # 재import 시도
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

# 드라이버 확인 및 자동 설치 시도
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
        # 자동 설치 시도 (pyodbc 우선)
        logger.warning("⚠️ MSSQL driver is not installed. Attempting automatic installation...")
        DRIVER_AVAILABLE = _install_driver_package('pyodbc')
        
        if not DRIVER_AVAILABLE:
            # pyodbc 설치 실패 시 pymssql 시도
            logger.warning("⚠️ pyodbc install failed. Trying pymssql...")
            DRIVER_AVAILABLE = _install_driver_package('pymssql')
        
        if not DRIVER_AVAILABLE:
            logger.error("""
❌ MSSQL 드라이버 설치 실패

자동 설치가 실패했습니다. 다음 방법으로 수동 설치를 진행하세요:

1. pip로 설치:
   pip install pyodbc
   또는
   pip install pymssql

2. Windows에서 ODBC Driver 확인:
   - pyodbc를 사용하는 경우 ODBC Driver 17 for SQL Server가 필요합니다.
   - https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server 에서 다운로드

3. 설치 확인:
   python -c "import pyodbc; print('pyodbc 설치 완료')"
   또는
   python -c "import pymssql; print('pymssql 설치 완료')"

현재 DB 직접 접속 모드가 활성화되어 있지만, 드라이버가 없어 API 모드로 전환됩니다.
            """)


class MANADDBConnector:
    """MANAD MSSQL 데이터베이스 직접 접속 클래스"""
    
    def __init__(self, site: str):
        """
        Args:
            site: 사이트 이름 (예: 'Parafield Gardens')
        """
        self.site = site
        self.connection_string = self._get_connection_string(site)
        self._connection_pool = {}
    
    def _get_connection_string(self, site: str) -> Optional[str]:
        """사이트별 MSSQL 연결 문자열 생성
        
        설정 우선순위:
        1. site_config.json (권장)
        2. 환경 변수 (폴백)
        """
        # 1. site_config.json에서 DB 설정 시도
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
                db_config = None  # 폴백으로 진행
        
        # 2. 환경 변수에서 DB 연결 정보 가져오기 (폴백)
        if not db_config:
            site_key = site.upper().replace(' ', '_').replace('-', '_')
            
            server = os.environ.get(f'MANAD_DB_SERVER_{site_key}')
            database = os.environ.get(f'MANAD_DB_NAME_{site_key}') or os.environ.get('MANAD_DB_NAME')
            
            # Windows Authentication 지원
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
        
        # Windows Authentication 사용 여부 확인
        if not use_windows_auth:
            if not username or not password:
                logger.warning(f"⚠️ DB username/password is not configured for {site}.")
                return None
        
        # pyodbc 연결 문자열
        if DRIVER_AVAILABLE == 'pyodbc':
            # 사용 가능한 드라이버 확인
            try:
                import pyodbc
                available_drivers = pyodbc.drivers()
                # 우선순위: ODBC Driver 17/18 > SQL Server Native Client > SQL Server
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
                    # 환경 변수에서 지정된 드라이버 사용
                    driver = os.environ.get('MANAD_DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
                    logger.warning(f"⚠️ Using default driver: {driver} (may not be installed on this system)")
                else:
                    logger.debug(f"✅ Driver to use: {driver}")
            except Exception as e:
                # 폴백: 환경 변수 또는 기본값
                driver = os.environ.get('MANAD_DB_DRIVER', 'SQL Server')
                logger.warning(f"⚠️ Driver check failed, using default: {driver} ({e})")
            
            # Windows Authentication 사용
            if use_windows_auth:
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                    f"Connection Timeout=30;"
                    f"ApplicationIntent=ReadOnly;"  # 읽기 전용 모드
                )
                logger.info(f"✅ Using Windows Authentication (READ-ONLY): {site} ({server})")
            else:
                # SQL Server Authentication 사용
                conn_str = (
                    f"DRIVER={driver};"
                    f"SERVER={server};"
                    f"DATABASE={database};"
                    f"UID={username};"
                    f"PWD={password};"
                    f"TrustServerCertificate=yes;"
                    f"Connection Timeout=30;"
                    f"ApplicationIntent=ReadOnly;"  # 읽기 전용 모드
                )
                logger.info(f"✅ Using SQL Server Authentication (READ-ONLY): {site} ({server})")
                logger.debug(f"   Connection info: UID={username}, DATABASE={database}")
            
            return conn_str
        
        # pymssql 연결 정보 (딕셔너리로 반환)
        elif DRIVER_AVAILABLE == 'pymssql':
            if use_windows_auth:
                # pymssql은 Windows Authentication을 직접 지원하지 않으므로 경고
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
        데이터베이스 연결 컨텍스트 매니저 (READ-ONLY 모드)
        
        ⚠️  중요: 읽기 전용 연결입니다
        
        보안 정책:
        1. ApplicationIntent=ReadOnly: 연결 문자열에 설정됨
        2. autocommit=False: 자동 커밋 비활성화
        3. rollback(): finally 블록에서 자동 롤백
        4. commit() 미호출: 절대 데이터 변경 커밋하지 않음
        
        사용 예:
            with connector.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Event")  # ✅ OK
                # cursor.execute("INSERT INTO ...")    # ⚠️ 실행되어도 롤백됨
        """
        conn = None
        try:
            if not self.connection_string:
                raise ValueError(f"{self.site}의 DB 연결 정보가 설정되지 않았습니다.")
            
            if DRIVER_AVAILABLE == 'pyodbc':
                conn = pyodbc.connect(self.connection_string)  # type: ignore
                
                # 읽기 전용 보안 설정
                conn.autocommit = False  # 명시적 커밋 없이는 변경 불가
                
                # READ UNCOMMITTED로 읽기 성능 향상 (락 최소화)
                cursor = conn.cursor()
                try:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
                    logger.debug(f"🔒 READ-ONLY mode: {self.site}")
                except:
                    pass  # 일부 환경에서 지원 안 할 수 있음
                cursor.close()
                
            elif DRIVER_AVAILABLE == 'pymssql':
                conn = pymssql.connect(**self.connection_string)  # type: ignore
                conn.autocommit = False
            else:
                error_msg = (
                    "MSSQL 드라이버가 설치되지 않았습니다.\n"
                    "다음 명령어로 설치하세요:\n"
                    "  pip install pyodbc\n"
                    "또는\n"
                    "  pip install pymssql\n\n"
                    "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다."
                )
                raise ImportError(error_msg)
            
            yield conn
            
            # ⚠️ 중요: commit()을 호출하지 않음 (READ-ONLY 보장)
            # 모든 변경사항은 finally 블록에서 자동 롤백됨
            
        except Exception as e:
            logger.error(f"❌ DB connection error ({self.site}): {e}")
            raise
        finally:
            if conn:
                try:
                    # 읽기 전용 보장: 변경사항 모두 롤백
                    if not conn.autocommit:
                        conn.rollback()
                    conn.close()
                    logger.debug(f"🔒 Connection closed (rollback complete): {self.site}")
                except:
                    pass
    
    def fetch_incidents(self, start_date: str, end_date: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Incident 데이터를 DB에서 직접 조회
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            (성공 여부, Incident 리스트)
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL 드라이버가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요:\n"
                "  pip install pyodbc\n"
                "또는\n"
                "  pip install pymssql\n\n"
                "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다:\n"
                "https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
            )
            logger.error(error_msg)
            raise ImportError("MSSQL 드라이버가 설치되지 않았습니다. pip install pyodbc 또는 pip install pymssql을 실행하세요.")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # MANAD DB의 실제 구조에 맞춘 쿼리
                # AdverseEvent 테이블: 실제 Incident 데이터가 저장된 테이블
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
                        -- Event Types (AdverseEvent_AdverseEventType 연결 테이블 사용)
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
                
                # 날짜 파라미터 변환
                start_dt = datetime.fromisoformat(start_date)
                end_dt = datetime.fromisoformat(end_date) + timedelta(days=1)  # 포함하려면 하루 더
                
                logger.info(f"🔍 Executing DB query: {self.site} ({start_date} ~ {end_date})")
                
                cursor.execute(query, (start_dt, end_dt))
                
                # 결과를 딕셔너리로 변환
                columns = [column[0] for column in cursor.description]
                incidents = []
                
                for row in cursor.fetchall():
                    incident_dict = dict(zip(columns, row))
                    
                    # API 형식에 맞게 변환
                    formatted_incident = self._format_incident_for_api(incident_dict)
                    incidents.append(formatted_incident)
                
                logger.info(f"✅ Incident fetch completed: {self.site} - {len(incidents)} incidents")
                
                return True, incidents
                
        except Exception as e:
            logger.error(f"❌ Incident fetch error ({self.site}): {e}")
            return False, None
    
    def fetch_clients(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Client 데이터를 DB에서 직접 조회
        
        Returns:
            (성공 여부, Client 리스트)
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL 드라이버가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요:\n"
                "  pip install pyodbc\n"
                "또는\n"
                "  pip install pymssql\n\n"
                "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다:\n"
                "https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
            )
            logger.error(error_msg)
            raise ImportError("MSSQL 드라이버가 설치되지 않았습니다. pip install pyodbc 또는 pip install pymssql을 실행하세요.")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # MANAD DB의 실제 Client 테이블 구조에 맞춘 쿼리
                # Client -> Person JOIN 필요 (이름 정보는 Person 테이블에)
                # 활성 거주자만 조회 (Edenfield Dashboard와 동일한 로직 사용)
                # MainClientServiceId를 통해 활성 서비스 확인 (EndDate가 NULL인 것만)
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
                
                # 먼저 ClientService를 포함한 쿼리 시도
                try:
                    cursor.execute(query_with_service)
                except Exception as e:
                    # ClientService 테이블이 없거나 에러 발생 시 단순 쿼리 사용
                    logger.warning(f"ClientService filtering query failed; using simple query: {e}")
                    cursor.execute(query_simple)
                
                columns = [column[0] for column in cursor.description]
                clients = []
                
                for row in cursor.fetchall():
                    client_dict = dict(zip(columns, row))
                    
                    # API 형식에 맞게 변환
                    formatted_client = self._format_client_for_api(client_dict)
                    clients.append(formatted_client)
                
                logger.info(f"✅ Client fetch completed: {self.site} - {len(clients)} clients")
                
                return True, clients
                
        except Exception as e:
            logger.error(f"❌ Client fetch error ({self.site}): {e}")
            return False, None
    
    def _format_incident_for_api(self, db_row: Dict) -> Dict[str, Any]:
        """DB 결과를 API 형식으로 변환"""
        # EventTypeName 파싱 (단일 또는 복수)
        event_types = []
        event_type_name = db_row.get('EventTypeName') or db_row.get('EventTypeNames')
        if event_type_name:
            event_types = [et.strip() for et in str(event_type_name).split(',') if et.strip()]
        
        # API 응답 형식과 일치시키기
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
        """DB 결과를 API 형식으로 변환"""
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
            'MainClientServiceId': db_row.get('MainClientServiceId'),  # 필터링에 필요한 MainClientServiceId 추가
            'IsActive': bool(db_row.get('IsActive', False))
        }
    
    def fetch_progress_notes(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             limit: int = 500,
                             progress_note_event_type_id: Optional[int] = None,
                             client_service_id: Optional[int] = None) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Progress Notes 데이터를 DB에서 직접 조회
        
        Args:
            start_date: 시작 날짜 (datetime, 기본값: 14일 전)
            end_date: 종료 날짜 (datetime, 기본값: 현재)
            limit: 최대 조회 개수
            progress_note_event_type_id: 특정 이벤트 타입 ID로 필터링
            client_service_id: 특정 클라이언트 서비스 ID로 필터링
            
        Returns:
            (성공 여부, Progress Notes 리스트) - API 응답 형식과 동일
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL 드라이버가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요:\n"
                "  pip install pyodbc\n"
                "또는\n"
                "  pip install pymssql\n\n"
                "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL 드라이버가 설치되지 않았습니다.")
        
        try:
            # 기본값 설정
            if start_date is None:
                start_date = datetime.now() - timedelta(days=14)
            if end_date is None:
                end_date = datetime.now()
            
            logger.info(f"🔍 [FILTER] Starting fetch_progress_notes - site={self.site}, client_service_id={client_service_id}, limit={limit}")
            logger.info(f"🔍 [FILTER] Date range: {start_date.date()} ~ {end_date.date()}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # ProgressNote 조회 쿼리 (API 응답 형식에 맞춤)
                # Client, Wing, Location 정보 포함
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
                        -- Person 정보 (ClientId -> Client -> PersonId -> Person)
                        ISNULL(p.FirstName, '') AS ClientFirstName,
                        ISNULL(p.LastName, '') AS ClientLastName,
                        ISNULL(p.PreferredName, '') AS ClientPreferredName,
                        '' AS ClientTitle,  -- Person 테이블에 Title 컬럼이 없음
                        -- ClientService 정보 (Service Wing, Location)
                        ISNULL(cs.WingId, 0) AS WingId,
                        ISNULL(w.Name, '') AS WingName,
                        ISNULL(cs.LocationId, 0) AS LocationId,
                        ISNULL(loc.Name, '') AS LocationName,
                        -- ProgressNoteEventType
                        ISNULL(pne.Id, 0) AS EventTypeId,
                        ISNULL(pne.Description, '') AS EventTypeDescription,
                        ISNULL(pne.ColorArgb, 0) AS EventTypeColorArgb,
                        -- ProgressNoteDetail (Note 텍스트)
                        (SELECT TOP 1 Note FROM ProgressNoteDetail WHERE ProgressNoteId = pn.Id) AS NotesPlainText,
                        -- CreatedByUser 정보 (간단한 버전)
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
                
                # Event Type 필터링
                if progress_note_event_type_id is not None:
                    query += " AND pn.ProgressNoteEventTypeId = ?"
                    logger.info(f"🔍 [FILTER] Added Event Type filter: {progress_note_event_type_id}")
                
                # Client Service ID 필터링
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
                
                # CareArea 매핑 정보 가져오기 (ProgressNote ID별로 그룹화)
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
                    
                    # CareArea 상세 정보 가져오기
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
                
                # ProgressNote 데이터 구성
                for row in rows:
                    note_dict = dict(zip(columns, row))
                    
                    # Care Areas 정보 생성
                    care_areas = []
                    progress_note_id = note_dict['Id']
                    if progress_note_id in care_area_mappings:
                        for ca_id in care_area_mappings[progress_note_id]:
                            if ca_id in care_area_details:
                                care_areas.append({
                                    'Id': ca_id,
                                    'Description': care_area_details[ca_id]
                                })
                    
                    # API 응답 형식에 맞게 변환
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
                        # Client 정보 추가
                        'Client': {
                            'FirstName': note_dict.get('ClientFirstName', ''),
                            'LastName': note_dict.get('ClientLastName', ''),
                            'PreferredName': note_dict.get('ClientPreferredName', ''),
                            'Title': note_dict.get('ClientTitle', '')
                        },
                        # Service Wing, Location 정보 추가
                        'WingName': note_dict.get('WingName', ''),
                        'LocationName': note_dict.get('LocationName', ''),
                        # Care Areas 추가
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
        Care Area 데이터를 DB에서 직접 조회
        
        Returns:
            (성공 여부, Care Area 리스트) - API 응답 형식과 동일
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL 드라이버가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요:\n"
                "  pip install pyodbc\n"
                "또는\n"
                "  pip install pymssql\n\n"
                "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL 드라이버가 설치되지 않았습니다.")
        
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
                    
                    # API 응답 형식에 맞게 변환
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
        Progress Note Event Type 데이터를 DB에서 직접 조회
        
        Returns:
            (성공 여부, Event Type 리스트) - API 응답 형식과 동일
        """
        if not DRIVER_AVAILABLE:
            error_msg = (
                "❌ MSSQL 드라이버가 설치되지 않았습니다.\n"
                "다음 명령어로 설치하세요:\n"
                "  pip install pyodbc\n"
                "또는\n"
                "  pip install pymssql\n\n"
                "Windows 사용자는 ODBC Driver 17 for SQL Server도 필요합니다."
            )
            logger.error(error_msg)
            raise ImportError("MSSQL 드라이버가 설치되지 않았습니다.")
        
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
                    
                    # API 응답 형식에 맞게 변환
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
    DB에서 직접 Incident와 Client 데이터를 가져오는 함수
    (기존 API 함수와 동일한 인터페이스)
    
    Args:
        site: 사이트 이름
        start_date: 시작 날짜
        end_date: 종료 날짜
        fetch_clients: Client 데이터도 가져올지 여부
        
    Returns:
        {'incidents': [...], 'clients': [...]} 형식의 딕셔너리
    """
    try:
        connector = MANADDBConnector(site)
        
        # Incident 조회
        incidents_success, incidents = connector.fetch_incidents(start_date, end_date)
        if not incidents_success:
            logger.error(f"Failed to fetch incidents from DB for {site}")
            return None
        
        # Client 조회 (선택적)
        clients = []
        if fetch_clients:
            clients_success, clients = connector.fetch_clients()
            if not clients_success:
                logger.warning(f"Failed to fetch clients from DB for {site}, proceeding with empty client list")
                clients = []
        
        # API 형식과 동일하게 반환
        return {
            'incidents': incidents or [],
            'clients': clients or []
        }
        
    except Exception as e:
        logger.error(f"❌ DB query error ({site}): {e}")
        return None

