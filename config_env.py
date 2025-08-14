"""
환경별 설정 관리 모듈
개발환경과 운영환경 설정을 동적으로 로딩
"""
import os
from dotenv import load_dotenv

# .env 파일 로딩
load_dotenv()

def get_environment():
    """현재 환경을 반환 (development 또는 production)"""
    return os.environ.get('ENVIRONMENT', 'development').lower()

def get_config_value(key, default=None):
    """환경에 따라 설정값을 반환"""
    environment = get_environment()
    
    # 환경별 키 생성 (예: DEV_SECRET_KEY, PROD_SECRET_KEY)
    if environment == 'production':
        env_key = f"PROD_{key}"
    else:
        env_key = f"DEV_{key}"
    
    # 환경별 설정이 있으면 우선 사용, 없으면 공통 설정 사용
    return os.environ.get(env_key, os.environ.get(key, default))

def get_flask_config():
    """Flask 애플리케이션 설정을 반환"""
    environment = get_environment()
    
    config = {
        'SECRET_KEY': get_config_value('SECRET_KEY', 'fallback-secret-key'),
        'DEBUG': get_config_value('FLASK_DEBUG', 'False').lower() == 'true',
        'HOST': get_config_value('HOST', '127.0.0.1'),
        'PORT': int(get_config_value('PORT', '5000')),
        'ENVIRONMENT': environment,
        
        # 로깅 설정
        'LOG_LEVEL': get_config_value('LOG_LEVEL', 'INFO'),
        
        # API 설정
        'API_TIMEOUT': int(get_config_value('API_TIMEOUT', '30')),
        'API_RETRY_COUNT': int(get_config_value('API_RETRY_COUNT', '3')),
        
        # 데이터베이스 설정 (향후 사용)
        'DATABASE_URL': get_config_value('DATABASE_URL', None),
    }
    
    return config

def get_cache_policy():
    """캐시 사용 정책 설정"""
    environment = get_environment()
    
    if environment == 'production':
        return {
            'use_cache_on_failure': False,  # 서버에서는 캐시 사용 안함
            'cache_expiry_hours': 1,        # 캐시 만료 시간 짧게
            'force_api_refresh': True,      # 강제 API 새로고침
            'cleanup_data_on_login': True   # 로그인시 data 폴더 정리
        }
    else:
        return {
            'use_cache_on_failure': False,  # 로컬에서도 캐시 사용 안함 (일관성)
            'cache_expiry_hours': 1,        # 캐시 만료 시간 짧게
            'force_api_refresh': True,      # 강제 API 새로고침
            'cleanup_data_on_login': True   # 로그인시 data 폴더 정리
        }

def print_current_config():
    """현재 설정을 출력 (디버깅용)"""
    config = get_flask_config()
    cache_policy = get_cache_policy()
    environment = get_environment()
    
    print(f"\n=== 현재 환경: {environment.upper()} ===")
    print(f"SECRET_KEY: {'*' * len(config['SECRET_KEY'])}")  # 보안상 마스킹
    print(f"DEBUG: {config['DEBUG']}")
    print(f"HOST: {config['HOST']}")
    print(f"PORT: {config['PORT']}")
    print(f"LOG_LEVEL: {config['LOG_LEVEL']}")
    print(f"API_TIMEOUT: {config['API_TIMEOUT']}")
    print(f"캐시 사용 정책:")
    print(f"  - API 실패시 캐시 사용: {cache_policy['use_cache_on_failure']}")
    print(f"  - 캐시 만료 시간: {cache_policy['cache_expiry_hours']}시간")
    print(f"  - 강제 API 새로고침: {cache_policy['force_api_refresh']}")
    print(f"  - 로그인시 data 폴더 정리: {cache_policy['cleanup_data_on_login']}")
    print("=" * 50) 