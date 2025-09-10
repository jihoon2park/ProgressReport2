# config.py
# 기존 하드코딩된 설정을 DB 기반으로 변경

# 기본 API 인증 헤더 (공통 부분)
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# DB 기반 API 키 관리자 사용
try:
    from api_key_manager import get_api_headers, get_server_info, get_site_servers
    USE_DB_API_KEYS = True
except ImportError:
    # 폴백: 기본 설정 (개발/테스트용)
    USE_DB_API_KEYS = False
    
    # 기본 사이트 서버 정보 (폴백용)
    SITE_SERVERS = {
        'Parafield Gardens': '192.168.1.11:8080',
        'Nerrilda': '192.168.21.12:8080',
        'Ramsay': '192.168.31.12:8080',
        'West Park': '192.168.41.12:8080',
        'Yankalilla': '192.168.51.12:8080'
    }
    
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

# SITE_SERVERS는 하위 호환성을 위해 유지 (DB에서 동적으로 생성)
if USE_DB_API_KEYS:
    def get_site_servers():
        """DB에서 사이트 서버 정보 조회"""
        from api_key_manager import get_api_key_manager
        manager = get_api_key_manager()
        servers = {}
        
        for api_data in manager.get_all_api_keys():
            servers[api_data['site_name']] = f"{api_data['server_ip']}:{api_data['server_port']}"
        
        return servers
    
    SITE_SERVERS = get_site_servers()
else:
    # 기존 방식 사용
    pass