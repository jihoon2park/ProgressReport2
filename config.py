# config.py
SITE_SERVERS = {
    'Parafield Gardens': '192.168.1.11:8080',
    'Nerrilda': '192.168.21.12:8080',
    'Ramsay': '192.168.31.12:8080',
    'West Park': '192.168.41.12:8080',
    'Yankalilla': '192.168.51.12:8080'
}

# 사이트별 API 키
SITE_API_KEYS = {
    'Parafield Gardens': '6RU+gahOFDvf/aF2dC7hAV+flYNe+dMb8Ts2xMsR0QM=',
    'Nerrilda': 'rcPYmmujoPHYwZ7w6U4nKttH2lt2GgLnnRD7BUwvm58=',
    'Ramsay': 'iKsCR/wbvEdTRa1cq0k4H7j8/dAKb5t4aAQqchXfmfQ=',
    'West Park': 'YjTVon6NmDLeIUF3S3kyWyJtiB+cHOtxiIxXYb0Z6zw=',
    'Yankalilla': 'RhU1zjQMJs2/BK/USVmVywy5SdimDTm28BRguF70c+I='
}

# 기본 API 인증 헤더
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'x-api-username': 'ManadAPI'
}

def get_api_headers(site):
    """사이트에 맞는 API 헤더 반환"""
    headers = API_HEADERS.copy()
    headers['x-api-key'] = SITE_API_KEYS.get(site, SITE_API_KEYS['Parafield Gardens'])
    return headers