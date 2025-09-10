# config.py
# 기존 하드코딩된 설정을 DB 기반으로 변경

# 기본 API 인증 헤더 (공통 부분)
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# DB 기반 API 키 관리자 사용
try:
    from api_key_manager import get_api_headers, get_server_info
    USE_DB_API_KEYS = True
except ImportError:
    # 폴백: 기존 하드코딩된 방식 (개발/테스트용)
    USE_DB_API_KEYS = False
    
    # 개발용 하드코딩된 설정 (프로덕션에서는 사용하지 않음)
    SITE_SERVERS = {
        'Parafield Gardens': '192.168.1.11:8080',
        'Nerrilda': '192.168.21.12:8080',
        'Ramsay': '192.168.31.12:8080',
        'West Park': '192.168.41.12:8080',
        'Yankalilla': '192.168.51.12:8080'
    }
    
    SITE_API_KEYS = {
        'Parafield Gardens': 'qPh+xiaSIvRCqQ5nB6gNBQl12IMLFED4C5s/xfjQ88k=',
        'Nerrilda': 'UYlsB9uLJt8pqc+82WKzLYcIH+hxWsF3IJCemHkc77w=',
        'Ramsay': 'DtQEnNJohGnYnzQory++De2NijWqINO+enhDdBNHYTM=',
        'West Park': 'oWhTkk0QwiXk/TWrqDDQNHpC30/htIVqwIZf8Fc+kaw=',
        'Yankalilla': 'RhU1zjQMJs2/BK/USVmVywy5SdimDTm28BRguF70c+I='
    }
    
    def get_api_headers(site):
        """사이트에 맞는 API 헤더 반환 (폴백)"""
        headers = API_HEADERS.copy()
        headers['x-api-username'] = 'ManadAPI'
        headers['x-api-key'] = SITE_API_KEYS.get(site, SITE_API_KEYS['Parafield Gardens'])
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