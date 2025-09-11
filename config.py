# config.py


# 기존 하드코딩된 설정을 DB 기반으로 변경

# 기본 API 인증 헤더 (공통 부분)
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# 기본 사이트 서버 정보 (폴백용)
SITE_SERVERS = {
    'Parafield Gardens': '192.168.1.11:8080',
    'Nerrilda': '192.168.21.12:8080',
    'Ramsay': '192.168.31.12:8080',
    'West Park': '192.168.41.12:8080',
    'Yankalilla': '192.168.51.12:8080'
}

# JSON 기반 API 키 관리자 사용
try:
    from api_key_manager_json import get_api_headers, get_server_info, get_site_servers
    USE_DB_API_KEYS = True
    print("JSON 기반 API 키 관리자 로드 성공")
except ImportError as e:
    # 폴백: 기본 설정 (개발/테스트용)
    USE_DB_API_KEYS = False
    print(f"JSON 기반 API 키 관리자 로드 실패, 폴백 사용: {e}")
except Exception as e:
    # 기타 오류도 폴백으로 처리
    USE_DB_API_KEYS = False
    print(f"JSON 기반 API 키 관리자 로드 중 오류, 폴백 사용: {e}")
    
    def get_api_headers(site):
        """사이트에 맞는 API 헤더 반환 (폴백)"""
        headers = API_HEADERS.copy()
        headers['x-api-username'] = 'ManadAPI'
        # 폴백에서는 기본 키 사용
        headers['x-api-key'] = 'default-key'
        return headers
    
    def get_server_info(site):
        """서버 정보 반환 (폴백)"""
        server_info = SITE_SERVERS.get(site, SITE_SERVERS['Parafield Gardens'])
        ip, port = server_info.split(':')
        return {
            'server_ip': ip,
            'server_port': port,
            'base_url': f"http://{server_info}"
        }
    
    def get_site_servers():
        """사이트 서버 정보 반환 (폴백)"""
        return SITE_SERVERS

def get_available_sites():
    """사용 가능한 사이트 목록을 DB 또는 폴백에서 가져오기"""
    try:
        if USE_DB_API_KEYS:
            return list(get_site_servers().keys())
        else:
            return list(SITE_SERVERS.keys())
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"사이트 정보 조회 실패: {e}")
        return list(SITE_SERVERS.keys())  # 폴백

# SITE_SERVERS는 하위 호환성을 위해 유지 (DB에서 동적으로 생성)
if USE_DB_API_KEYS:
    def get_site_servers():
        """DB에서 사이트 서버 정보 조회"""
        try:
            from api_key_manager_json import get_api_key_manager
            manager = get_api_key_manager()
            servers = {}
            
            for api_data in manager.get_all_api_keys():
                servers[api_data['site_name']] = f"{api_data['server_ip']}:{api_data['server_port']}"
            
            print(f"JSON에서 사이트 서버 정보 로드 성공: {list(servers.keys())}")
            return servers
        except Exception as e:
            print(f"JSON에서 사이트 서버 정보 로드 실패, 폴백 사용: {e}")
            return SITE_SERVERS  # 기본값 반환
    
    try:
        SITE_SERVERS = get_site_servers()
        # DB에서 로드된 사이트가 비어있으면 기본값 사용
        if not SITE_SERVERS:
            print("DB에서 로드된 사이트가 비어있음, 기본값 사용")
            SITE_SERVERS = {
                'Parafield Gardens': '192.168.1.11:8080',
                'Nerrilda': '192.168.21.12:8080',
                'Ramsay': '192.168.31.12:8080',
                'West Park': '192.168.41.12:8080',
                'Yankalilla': '192.168.51.12:8080'
            }
    except Exception as e:
        print(f"SITE_SERVERS 초기화 실패, 기본값 사용: {e}")
        # 기본값은 이미 위에서 정의됨
else:
    # 기존 방식 사용
    print("폴백 모드: 기본 SITE_SERVERS 사용")
    pass