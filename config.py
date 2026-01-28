# config.py


# Change hardcoded settings to DB-based

# Default API authentication headers (common part)
API_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Default site server information (for fallback)
SITE_SERVERS = {
    'Parafield Gardens': '192.168.1.11:8080',
    'Nerrilda': '192.168.21.12:8080',
    'Ramsay': '192.168.31.12:8080',
    'West Park': '192.168.41.12:8080',
    'Yankalilla': '192.168.51.12:8080'
}

# Use JSON-based API key manager
try:
    from api_key_manager_json import get_api_headers, get_server_info, get_site_servers
    USE_DB_API_KEYS = True
    print("JSON API key manager loaded successfully")
except ImportError as e:
    # Fallback: default settings (for development/testing)
    USE_DB_API_KEYS = False
    print(f"JSON API key manager load failed, using fallback: {e}")
except Exception as e:
    # Handle other errors with fallback
    USE_DB_API_KEYS = False
    print(f"JSON API key manager error, using fallback: {e}")
    
    def get_api_headers(site):
        """Return API headers for site (fallback)"""
        headers = API_HEADERS.copy()
        headers['x-api-username'] = 'ManadAPI'
        # Use default key in fallback
        headers['x-api-key'] = 'default-key'
        return headers
    
    def get_server_info(site):
        """Return server information (fallback)"""
        server_info = SITE_SERVERS.get(site, SITE_SERVERS['Parafield Gardens'])
        ip, port = server_info.split(':')
        return {
            'server_ip': ip,
            'server_port': port,
            'base_url': f"http://{server_info}"
        }
    
    def get_site_servers():
        """Return site server information (fallback)"""
        return SITE_SERVERS

def get_available_sites():
    """Get available site list from DB or fallback"""
    try:
        if USE_DB_API_KEYS:
            return list(get_site_servers().keys())
        else:
            return list(SITE_SERVERS.keys())
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to fetch site information: {e}")
        return list(SITE_SERVERS.keys())  # Fallback

# SITE_SERVERS maintained for backward compatibility (dynamically generated from DB)
if USE_DB_API_KEYS:
    def get_site_servers():
        """Query site server information from DB"""
        try:
            from api_key_manager_json import get_api_key_manager
            manager = get_api_key_manager()
            servers = {}
            
            for api_data in manager.get_all_api_keys():
                servers[api_data['site_name']] = f"{api_data['server_ip']}:{api_data['server_port']}"
            
            print(f"JSON site server info loaded successfully: {list(servers.keys())}")
            return servers
        except Exception as e:
            print(f"JSON site server info load failed, using fallback: {e}")
            return SITE_SERVERS  # Return default value
    
    try:
        SITE_SERVERS = get_site_servers()
        # Use default values if DB-loaded sites are empty
        if not SITE_SERVERS:
            print("DB loaded sites empty, using default values")
            SITE_SERVERS = {
                'Parafield Gardens': '192.168.1.11:8080',
                'Nerrilda': '192.168.21.12:8080',
                'Ramsay': '192.168.31.12:8080',
                'West Park': '192.168.41.12:8080',
                'Yankalilla': '192.168.51.12:8080'
            }
    except Exception as e:
        print(f"SITE_SERVERS initialization failed, using default: {e}")
        # Default value already defined above
else:
    # Use existing method
    print("Fallback mode: using default SITE_SERVERS")
    pass