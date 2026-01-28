import json
import os
import requests
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProgressNoteAPIClient:
    def __init__(self, site=None):
        """Initialize Progress Note API client"""
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site and site in SITE_SERVERS:
            self.api_url = f"http://{SITE_SERVERS[site]}/api/progressnote"
        else:
            # Default value (Parafield Gardens)
            self.site = 'Parafield Gardens'
            self.api_url = f"http://{SITE_SERVERS['Parafield Gardens']}/api/progressnote"
            
        self.prepare_send_file = "data/prepare_send.json"
        
        # Session configuration (use site-specific API headers)
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(self.site))
        
        logger.info(f"ProgressNoteAPIClient initialized for site '{self.site}' with API URL: {self.api_url}")
        logger.info(f"API headers: {dict(self.session.headers)}")

    def load_prepare_send_data(self) -> Optional[Dict[str, Any]]:
        """Load prepare_send.json file"""
        try:
            if not os.path.exists(self.prepare_send_file):
                logger.error(f"prepare_send.json file does not exist: {self.prepare_send_file}")
                return None
            
            with open(self.prepare_send_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("prepare_send.json file loaded successfully")
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"File load error: {str(e)}")
            return None

    def validate_progress_note_data(self, data: Dict[str, Any]) -> bool:
        """Validate Progress Note data"""
        required_fields = [
            'ClientId',
            'EventDate', 
            'ProgressNoteEventType',
            'NotesPlainText',
            'CreatedByUser',
            'CreatedDate'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                logger.error(f"Required field missing: {field}")
                return False
        
        # Check ProgressNoteEventType structure
        if 'Id' not in data.get('ProgressNoteEventType', {}):
            logger.error("ProgressNoteEventType.Id field missing")
            return False
        
        # Check CreatedByUser structure
        user_required_fields = ['FirstName', 'LastName', 'UserName', 'Position']
        created_by_user = data.get('CreatedByUser', {})
        for field in user_required_fields:
            if field not in created_by_user:
                logger.error(f"CreatedByUser.{field} field missing")
                return False
        
        logger.info("Progress Note data validation passed")
        return True

    def send_progress_note(self, data: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Send Progress Note to API"""
        try:
            # Load from file if data not provided
            if data is None:
                data = self.load_prepare_send_data()
                if data is None:
                    return False, {"error": "Data load failed"}
            
            # Validate data
            if not self.validate_progress_note_data(data):
                return False, {"error": "Data validation failed"}
            
            # Send API request
            logger.info(f"Progress Note API request started: {self.api_url}")
            logger.info(f"Send data: ClientId={data.get('ClientId')}, "
                       f"EventType={data.get('ProgressNoteEventType', {}).get('Id')}, "
                       f"User={data.get('CreatedByUser', {}).get('UserName')}")
            
            response = self.session.post(
                self.api_url,
                json=data,
                timeout=30
            )
            
            logger.info(f"API response status code: {response.status_code}")
            
            # Process response
            if response.status_code == 200 or response.status_code == 201:
                try:
                    response_data = response.json()
                    logger.info("Progress Note send succeeded")
                    self._log_success(data, response_data)
                    return True, response_data
                except json.JSONDecodeError:
                    # Treat as success even if no JSON response
                    logger.info("Progress Note send succeeded (no response data)")
                    self._log_success(data, {"status": "success"})
                    return True, {"status": "success"}
            else:
                error_msg = f"API request failed - status code: {response.status_code}"
                try:
                    error_response = response.json()
                    error_msg += f", response: {error_response}"
                    logger.error(error_msg)
                    return False, error_response
                except json.JSONDecodeError:
                    error_msg += f", response text: {response.text}"
                    logger.error(error_msg)
                    return False, {"error": error_msg, "status_code": response.status_code}

        except requests.Timeout:
            error_msg = "API request timeout (30 seconds)"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except requests.ConnectionError:
            error_msg = f"API server connection failed: {self.api_url}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except requests.RequestException as e:
            error_msg = f"API request error: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    return False, error_response
                except:
                    pass
            return False, {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}

    def _log_success(self, sent_data: Dict[str, Any], response_data: Dict[str, Any]):
        """Record success log"""
        success_log = {
            "timestamp": datetime.now().isoformat(),
            "client_id": sent_data.get('ClientId'),
            "event_type_id": sent_data.get('ProgressNoteEventType', {}).get('Id'),
            "created_by": sent_data.get('CreatedByUser', {}).get('UserName'),
            "api_response": response_data
        }
        
        # Write success log to file (optional)
        try:
            log_file = "data/progress_note_success.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(success_log, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write success log file: {str(e)}")

    def test_connection(self) -> bool:
        """Test API server connection"""
        try:
            # Test connection with simple HEAD request
            response = self.session.head(self.api_url, timeout=10)
            if response.status_code in [200, 201, 404, 405]:  # 404, 405 also indicate successful connection
                logger.info("API server connection test succeeded")
                return True
            else:
                logger.warning(f"API server response abnormal - status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"API server connection test failed: {str(e)}")
            return False


def send_progress_note_to_api(site=None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Convenience function to send Progress Note to API
    
    Args:
        site: Target site name (e.g., 'Parafield Gardens')
        
    Returns:
        tuple: (Success status, response data or error information)
    """
    logger.info(f"Progress Note API send started - site: {site}")
    
    try:
        api_client = ProgressNoteAPIClient(site)
        
        # Connection test (optional)
        if not api_client.test_connection():
            logger.warning("API server connection test failed, but continuing with send attempt")
        
        # Send Progress Note
        success, response = api_client.send_progress_note()
        
        if success:
            logger.info(f"Progress Note API send succeeded - site: {site}")
        else:
            logger.error(f"Progress Note API send failed - site: {site}, response: {response}")
        
        return success, response
        
    except Exception as e:
        error_msg = f"Unexpected error during Progress Note API send: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}


def send_specific_progress_note(data: Dict[str, Any], site=None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Function to send specific Progress Note data to API
    
    Args:
        data: Progress Note data to send
        site: Target site name (e.g., 'Parafield Gardens')
        
    Returns:
        tuple: (Success status, response data or error information)
    """
    logger.info(f"Specific Progress Note data API send started - site: {site}")
    
    try:
        api_client = ProgressNoteAPIClient(site)
        success, response = api_client.send_progress_note(data)
        
        if success:
            logger.info(f"Specific Progress Note data API send succeeded - site: {site}")
        else:
            logger.error(f"Specific Progress Note data API send failed - site: {site}, response: {response}")
        
        return success, response
        
    except Exception as e:
        error_msg = f"Unexpected error during specific Progress Note data API send: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}


if __name__ == "__main__":
    # Test code
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test with Parafield Gardens site
    success, response = send_progress_note_to_api('Parafield Gardens')
    if success:
        print("✅ Progress Note send succeeded!")
        print(f"Response: {response}")
    else:
        print("❌ Progress Note send failed!")
        print(f"Error: {response}") 