from typing import Dict, Any
import requests
import logging
import json
import os

from flask import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIEventType:
    def __init__(self, site: str):
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site not in SITE_SERVERS:
            raise ValueError(f"Invalid site: {site}")
            
        self.base_url = f"http://{SITE_SERVERS[site]}"
        logger.info(f"APIEventType initialized with base_url: {self.base_url}")
        
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(site))

    def get_event_type_information(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.base_url}/api/referencetable/progressnoteeventtype"
            logger.info(f"Requesting event type information from: {endpoint}")
            
            response = self.session.get(endpoint)
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            event_type_data = response.json()
            
            # Save data to file
            self._save_event_type_data(event_type_data)
            
            return event_type_data

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Error response: {e.response.text}")
            raise e

    def _save_event_type_data(self, event_type_data: Dict[str, Any]):
        """Save Event Type data to JSON file (site-specific + unified)"""
        try:
            # Create data directory if it doesn't exist
            if not os.path.exists('data'):
                os.makedirs('data')
                logger.info("data directory created")

            # 1. Save as site-specific JSON file
            site_filename = f'data/eventtype_{self.site}.json'
            with open(site_filename, 'w', encoding='utf-8') as f:
                json.dump(event_type_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Event Type data saved per site: {site_filename}")
            
            # 2. Also save as unified JSON file (maintain backward compatibility)
            with open('data/eventtype.json', 'w', encoding='utf-8') as f:
                json.dump(event_type_data, f, ensure_ascii=False, indent=4)
            logger.info("Event Type data saved to unified file: data/eventtype.json")
            
        except Exception as e:
            logger.error(f"Error saving Event Type data: {str(e)}")
            raise

def fetch_all_sites_event_types():
    """Fetch Event Types from all sites and save per site"""
    from config import SITE_SERVERS
    
    results = {}
    for site in SITE_SERVERS.keys():
        try:
            logger.info(f"Fetching event types for site: {site}")
            api_event_type = APIEventType(site)
            event_types = api_event_type.get_event_type_information()
            results[site] = event_types
            logger.info(f"Successfully fetched {len(event_types)} event types for {site}")
        except Exception as e:
            logger.error(f"Failed to fetch event types for {site}: {str(e)}")
            results[site] = []
    
    return results

def get_site_event_types(site: str):
    """Load Event Types for specific site from JSON file"""
    try:
        site_filename = f'data/eventtype_{site}.json'
        
        # Load if site-specific file exists
        if os.path.exists(site_filename):
            with open(site_filename, 'r', encoding='utf-8') as f:
                event_types = json.load(f)
            logger.info(f"Loaded {len(event_types)} event types for site {site} from {site_filename}")
            return event_types
        
        # Load from unified file if site-specific file doesn't exist
        elif os.path.exists('data/eventtype.json'):
            with open('data/eventtype.json', 'r', encoding='utf-8') as f:
                event_types = json.load(f)
            logger.info(f"Loaded {len(event_types)} event types for site {site} from data/eventtype.json (fallback)")
            return event_types
        
        else:
            logger.warning(f"No event type files found for site {site}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading event types for site {site}: {str(e)}")
        return [] 