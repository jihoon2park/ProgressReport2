import json
import os
import requests
from typing import Dict, Any
import logging

# Test configuration
SITE_SERVERS = {
    "test_site": "http://192.168.1.11:8080"
}

API_HEADERS = {
    'x-api-username': 'ManadAPI',
    'x-api-key': '6RU+gahOFDvf/aF2dC7hAV+flYNe+dMb8Ts2xMsR0QM=',
    'Content-Type': 'application/json'
    # Add authentication headers if needed
}

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, site: str):
        self.site = site
        self.base_url = SITE_SERVERS.get(site)
        self.session = requests.Session()
        self.session.headers.update(API_HEADERS)
        self.client_data_path = 'templates/client_data'
        
        if not os.path.exists(self.client_data_path):
            os.makedirs(self.client_data_path)

    def get_client_information(self) -> Dict[str, Any]:
        """
        Function to get client information
        No cache usage - error occurs on API failure
        """
        try:
            endpoint = f"{self.base_url}/api/client"
            response = self.session.get(endpoint)
            response.raise_for_status()
            client_data = response.json()
            
            # Save to cache if successfully retrieved (read-only backup)
            self._cache_client_data(client_data)
            return client_data
            
        except requests.RequestException as e:
            # Error occurs on API call failure (no cache usage)
            logger.error(f"API call failed: {str(e)}")
            raise e  # Don't use cached data, raise error

    def _cache_client_data(self, data: Dict[str, Any]) -> None:
        """Cache client data to file"""
        cache_path = self._get_client_cache_path()
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_cached_client_data(self) -> Dict[str, Any]:
        """Load cached client data"""
        cache_path = self._get_client_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _get_client_cache_path(self) -> str:
        """Return client data cache file path"""
        return os.path.join(self.client_data_path, f'{self.site}_client.json')

def test_api_client():
    # Create test API client
    client = APIClient("test_site")
    
    try:
        # Test API call
        client_info = client.get_client_information()
        print("API call successful:", client_info)
        
    except requests.RequestException as e:
        print("API call failed:", str(e))
        print("No cache usage - error occurred")
        
    except Exception as e:
        print("Unexpected error:", str(e))

if __name__ == "__main__":
    test_api_client()