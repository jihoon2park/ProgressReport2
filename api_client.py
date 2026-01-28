import json
import os
import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, site: str):
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APIClient initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(site))

    def get_client_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/client"
            logger.info(f"Requesting client information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            client_data = response.json()
            
            return client_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e



def get_api_client(site):
    """Function to return API client instance"""
    return APIClient(site)

def fetch_client_information(site):
    """
    Integrated function to get resident (Client) information
    
    In DB direct access mode, queries latest data directly from DB each time.
    Does not use cache and always returns latest data.
    
    Args:
        site: Site name (e.g., 'Parafield Gardens')
        
    Returns:
        (Success status, client list)
    """
    import os
    import sqlite3
    
    # Check DB direct access mode
    use_db_direct = False
    try:
        conn = sqlite3.connect('progress_report.db', timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            use_db_direct = result[0].lower() == 'true'
        else:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
    except:
        use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
    
    # DB direct access mode (recommended - query latest data each time)
    if use_db_direct:
        try:
            logger.info(f"🔍 DEBUG: use_db_direct=True, importing MANADDBConnector")
            from manad_db_connector import MANADDBConnector
            logger.info(f"🔌 DB direct access: Querying resident information - {site} (latest data)")

            connector = MANADDBConnector(site)
            logger.info(f"🔍 DEBUG: MANADDBConnector instance created, about to call fetch_clients()")
            import time
            start_time = time.time()
            success, client_info = connector.fetch_clients()
            elapsed_time = time.time() - start_time
            logger.info(f"🔍 DEBUG: fetch_clients() returned after {elapsed_time:.2f} seconds - success: {success}")
            
            if success and client_info:

                # Save as JSON file (for reference, not read)
                save_client_data_to_json(site, client_info)
                logger.info(f"✅ Resident information query succeeded - {site}: {len(client_info)} residents")
                return True, client_info
            else:
                error_msg = f"❌ DB direct access failed: {site} - Resident information query result is empty."
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as db_error:
            error_msg = f"❌ DB direct access failed: {site} - {str(db_error)}"

            logger.error(error_msg)
            raise Exception(error_msg)
    
    # API mode (fallback)
    logger.info(f"🌐 API mode: Querying resident information - {site}")
    try:
        api_client = APIClient(site)
        client_info = api_client.get_client_information()
        
        # Save as JSON file (for reference)
        if client_info:
            save_client_data_to_json(site, client_info)
            logger.info(f"✅ Resident information query succeeded - {site}: {len(client_info) if isinstance(client_info, list) else 'N/A'} residents")
        
        return True, client_info
    except requests.RequestException as e:
        logger.error(f"❌ Resident information query failed - {site}: {str(e)}")
        return False, None

def save_client_data_to_json(site, client_data):
    """Save client data to JSON file"""
    try:
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
        # Generate filename (convert site name to lowercase and replace spaces with underscores)
        filename = f"data/{site.replace(' ', '_').lower()}_client.json"
        
        # Save as JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(client_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Client data JSON save completed - {filename}")
        
    except Exception as e:
        logger.error(f"Client data JSON save failed - site: {site}, error: {str(e)}")

