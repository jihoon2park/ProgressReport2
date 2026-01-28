"""
Environment-specific configuration management module
Dynamically loads settings for development and production environments
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_environment():
    """Return current environment (development or production)"""
    return os.environ.get('ENVIRONMENT', 'development').lower()

def get_config_value(key, default=None):
    """Return configuration value based on environment"""
    environment = get_environment()
    
    # Generate environment-specific key (e.g., DEV_SECRET_KEY, PROD_SECRET_KEY)
    if environment == 'production':
        env_key = f"PROD_{key}"
    else:
        env_key = f"DEV_{key}"
    
    # Use environment-specific setting if available, otherwise use common setting
    return os.environ.get(env_key, os.environ.get(key, default))

def get_flask_config():
    """Return Flask application configuration"""
    environment = get_environment()
    
    config = {
        'SECRET_KEY': get_config_value('SECRET_KEY', 'fallback-secret-key'),
        'DEBUG': get_config_value('FLASK_DEBUG', 'False').lower() == 'true',
        'HOST': get_config_value('HOST', '0.0.0.0'),  # Default changed to 0.0.0.0 (allow network access)
        'PORT': int(get_config_value('PORT', '5000')),
        'ENVIRONMENT': environment,
        
        # Logging configuration
        'LOG_LEVEL': get_config_value('LOG_LEVEL', 'INFO'),
        
        # API configuration
        'API_TIMEOUT': int(get_config_value('API_TIMEOUT', '30')),
        'API_RETRY_COUNT': int(get_config_value('API_RETRY_COUNT', '3')),
        
        # Background processor configuration (disabled by default in development)
        'ENABLE_BACKGROUND_PROCESSOR': get_config_value('ENABLE_BACKGROUND_PROCESSOR', 'True' if environment == 'production' else 'False').lower() == 'true',
        
        # Database configuration (for future use)
        'DATABASE_URL': get_config_value('DATABASE_URL', None),
    }
    
    return config

def get_cache_policy():
    """Configure cache usage policy"""
    environment = get_environment()
    
    if environment == 'production':
        return {
            'use_cache_on_failure': False,  # Do not use cache on server
            'cache_expiry_hours': 1,        # Short cache expiry time
            'force_api_refresh': True,      # Force API refresh
            'cleanup_data_on_login': True   # Cleanup data folder on login
        }
    else:
        return {
            'use_cache_on_failure': False,  # Do not use cache locally (consistency)
            'cache_expiry_hours': 1,        # Short cache expiry time
            'force_api_refresh': True,      # Force API refresh
            'cleanup_data_on_login': True   # Cleanup data folder on login
        }

def print_current_config():
    """Print current configuration (for debugging)"""
    config = get_flask_config()
    cache_policy = get_cache_policy()
    environment = get_environment()
    
    print(f"\n=== Current Environment: {environment.upper()} ===")
    print(f"SECRET_KEY: {'*' * len(config['SECRET_KEY'])}")  # Masked for security
    print(f"DEBUG: {config['DEBUG']}")
    print(f"HOST: {config['HOST']}")
    print(f"PORT: {config['PORT']}")
    print(f"LOG_LEVEL: {config['LOG_LEVEL']}")
    print(f"API_TIMEOUT: {config['API_TIMEOUT']}")
    print(f"Cache Policy:")
    print(f"  - Use cache on API failure: {cache_policy['use_cache_on_failure']}")
    print(f"  - Cache expiry time: {cache_policy['cache_expiry_hours']} hours")
    print(f"  - Force API refresh: {cache_policy['force_api_refresh']}")
    print(f"  - Cleanup data folder on login: {cache_policy['cleanup_data_on_login']}")
    print("=" * 50) 