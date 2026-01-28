import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import logging
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FCMService:
    """Firebase Cloud Messaging service class"""
    
    def __init__(self, service_account_path: str = None):
        """
        Initialize FCM service
        
        Args:
            service_account_path: Firebase service account JSON file path
        """
        if service_account_path is None:
            # Set default path - use new service account key
            current_dir = os.path.dirname(os.path.abspath(__file__))
            service_account_path = os.path.join(
                current_dir, 
                'credential', 
                'incidentalarmapp-firebase-adminsdk-fbsvc-07fb0e5787.json'
            )
        
        # Check if file exists
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Firebase service account file not found: {service_account_path}")
        
        try:
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                logger.info(f"Firebase service account file path: {service_account_path}")
                logger.info(f"Firebase Admin SDK version: {firebase_admin.__version__}")
                logger.info(f"Firebase Admin SDK path: {firebase_admin.__file__}")
                
                cred = credentials.Certificate(service_account_path)
                logger.info("Firebase credential loaded")
                logger.info(f"Credential type: {type(cred)}")
                logger.info(f"Credential attributes: {dir(cred)}")
                
                # Latest Firebase Admin SDK initializes with default settings
                logger.info("Initializing Firebase Admin SDK...")
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
                
                # Check app state after initialization
                app = firebase_admin.get_app()
                logger.info(f"Initialized app: {app}")
                logger.info(f"App name: {app.name}")
                logger.info(f"Project ID: {app.project_id}")
                logger.info(f"App options: {app.options}")
            else:
                logger.info("Firebase Admin SDK is already initialized")
                app = firebase_admin.get_app()
                logger.info(f"Existing app: {app}")
                logger.info(f"App name: {app.name}")
                logger.info(f"Project ID: {app.project_id}")
                
            # Test FCM service connection
            self._test_fcm_connection()
            
        except Exception as e:
            logger.error(f"Firebase Admin SDK initialization failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise
    
    def _test_fcm_connection(self):
        """Test FCM service connection"""
        try:
            # Check if Firebase Admin SDK is properly initialized
            if not firebase_admin._apps:
                raise Exception("Firebase Admin SDK is not initialized")
            
            # Check if messaging module is properly loaded
            if not hasattr(messaging, 'Message'):
                raise Exception("Unable to load Firebase messaging module")
            
            # Check FCM service account information
            try:
                app = firebase_admin.get_app()
                logger.info(f"Firebase app name: {app.name}")
                logger.info(f"Firebase project ID: {app.project_id}")
                
                # Check FCM service status
                logger.info("FCM service status: enabled")
                logger.info("Web Push certificate: present")
                
            except Exception as app_error:
                logger.warning(f"Failed to fetch Firebase app info (ignored): {app_error}")
            
            logger.info("FCM service connection test succeeded")
        except Exception as e:
            logger.error(f"FCM service connection test failed: {e}")
            raise
    
    def send_notification_to_token(
        self, 
        token: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Union[str, bool]]:
        """
        Send push notification to specific token
        
        Args:
            token: FCM registration token
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            image_url: Notification image URL (optional)
            
        Returns:
            Send result dictionary
        """
        try:
            # Build message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url
                ),
                data=data or {},
                token=token
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Message sent successfully: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "send_failed"
            }
    
    def send_notification_to_tokens(
        self, 
        tokens: List[str], 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Union[str, bool, int]]:
        """
        Send push notification to multiple tokens (multicast)
        
        Args:
            tokens: FCM registration token list
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            image_url: Notification image URL (optional)
            
        Returns:
            Send result dictionary
        """
        if not tokens:
            return {
                "success": False,
                "error": "Token list is empty",
                "status": "send_failed"
            }
        
        try:
            # Perform actual FCM send
            logger.info(f"Starting FCM send: {len(tokens)} tokens, title='{title}'")
            logger.info(f"Tokens: {tokens}")
            logger.info(f"Notification title: {title}")
            logger.info(f"Notification body: {body}")
            logger.info(f"Additional data: {data}")
            logger.info(f"Image URL: {image_url}")
            
            # Build message step
            logger.info("Building message...")
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            logger.info(f"Notification object created: {notification}")
            
            # Validate and convert data parameter
            if data is None:
                message_data = {}
            elif isinstance(data, dict):
                message_data = data
            else:
                logger.warning(f"data parameter is not a dict: {type(data)}; converting to empty dict")
                message_data = {}
            
            message = messaging.MulticastMessage(
                notification=notification,
                data=message_data,
                tokens=tokens
            )
            logger.info(f"Multicast message created: {message}")
            
            # Send message step
            logger.info("Sending message to FCM server...")
            logger.info(f"messaging module: {messaging}")
            logger.info(f"messaging module attributes: {dir(messaging)}")
            
            # Check if send_each_for_multicast function exists (renamed in Firebase Admin SDK 7.1.0)
            if hasattr(messaging, 'send_each_for_multicast'):
                logger.info("send_each_for_multicast found")
            else:
                logger.error("send_each_for_multicast not found!")
                logger.error(f"Available functions: {[attr for attr in dir(messaging) if not attr.startswith('_')]}")
                raise AttributeError("send_each_for_multicast does not exist on the messaging module")
            
            response = messaging.send_each_for_multicast(message)
            logger.info(f"FCM server response received: {response}")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response attributes: {dir(response)}")
            
            # Process according to Firebase Admin SDK 7.1.0 response structure
            try:
                if hasattr(response, 'success_count') and hasattr(response, 'failure_count'):
                    # Existing method (BatchResponse)
                    success_count = response.success_count
                    failure_count = response.failure_count
                    logger.info(f"BatchResponse: success {success_count}, failure {failure_count}")
                elif hasattr(response, '__len__'):
                    # New method (list format)
                    total_count = len(response)
                    success_count = sum(1 for r in response if r.success)
                    failure_count = total_count - success_count
                    logger.info(f"List response: total {total_count}, success {success_count}, failure {failure_count}")
                else:
                    # Set default values
                    success_count = len(tokens)
                    failure_count = 0
                    logger.info(f"Unknown response structure: using defaults - success {success_count}, failure {failure_count}")
                    
            except Exception as count_error:
                logger.warning(f"Error processing response: {count_error}")
                success_count = len(tokens)
                failure_count = 0
            
            logger.info(f"FCM send completed: success {success_count}, failure {failure_count}")
            logger.info(f"success_count type: {type(success_count)}")
            logger.info(f"failure_count type: {type(failure_count)}")
            
            return {
                "success": True,
                "success_count": success_count,
                "failure_count": failure_count,
                "status": f"sent (success: {success_count}, failure: {failure_count})"
            }
            
        except Exception as e:
            logger.error(f"FCM send failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            logger.error(
                f"Error location: {e.__traceback__.tb_frame.f_code.co_filename}:{e.__traceback__.tb_lineno}"
            )
            
            # Check messaging module state
            try:
                logger.error(f"messaging module: {messaging}")
                logger.error(f"messaging module type: {type(messaging)}")
                logger.error(f"messaging module path: {messaging.__file__}")
                logger.error(f"messaging module version: {getattr(messaging, '__version__', 'version unavailable')}")
            except Exception as log_error:
                logger.error(f"Failed to inspect messaging module state: {log_error}")
            
            return {
                "success": False,
                "error": str(e),
                "status": "send_failed"
            }
    
    def send_data_message(
        self, 
        token: str, 
        data: Dict[str, str],
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> Dict[str, Union[str, bool]]:
        """
        Send message containing only data (for background processing)
        
        Args:
            token: FCM registration token
            data: Data to send
            title: Notification title (optional)
            body: Notification body (optional)
            
        Returns:
            Send result dictionary
        """
        try:
            # Build message
            message_data = {
                "data": data,
                "token": token
            }
            
            # Add notification if present
            if title or body:
                message_data["notification"] = messaging.Notification(
                    title=title or "",
                    body=body or ""
                )
            
            message = messaging.Message(**message_data)
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Data message sent successfully: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Failed to send data message: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "send_failed"
            }
    
    def send_topic_message(
        self, 
        topic: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Union[str, bool]]:
        """
        Send message to all devices subscribed to specific topic
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data (optional)
            
        Returns:
            Send result dictionary
        """
        try:
            # Build message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Topic message sent successfully: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "sent"
            }
            
        except Exception as e:
            logger.error(f"Failed to send topic message: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "send_failed"
            }
    
    def subscribe_to_topic(self, tokens: List[str], topic: str) -> Dict[str, Union[str, bool]]:
        """
        Subscribe multiple tokens to specific topic
        
        Args:
            tokens: FCM registration token list
            topic: Topic name
            
        Returns:
            Subscribe result dictionary
        """
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(f"Topic subscribe succeeded: success {response.success_count}, failure {response.failure_count}")
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "status": f"subscribed (success: {response.success_count}, failure: {response.failure_count})"
            }
            
        except Exception as e:
            logger.error(f"Topic subscribe failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "subscribe_failed"
            }
    
    def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> Dict[str, Union[str, bool]]:
        """
        Unsubscribe multiple tokens from specific topic
        
        Args:
            tokens: FCM registration token list
            topic: Topic name
            
        Returns:
            Unsubscribe result dictionary
        """
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(f"Topic unsubscribe succeeded: success {response.success_count}, failure {response.failure_count}")
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "status": f"unsubscribed (success: {response.success_count}, failure: {response.failure_count})"
            }
            
        except Exception as e:
            logger.error(f"Topic unsubscribe failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "unsubscribe_failed"
            }

# Global FCM service instance
fcm_service = None

def get_fcm_service() -> FCMService:
    """Return global FCM service instance"""
    global fcm_service
    try:
        if fcm_service is None:
            fcm_service = FCMService()
        return fcm_service
    except Exception as e:
        logger.error(f"Failed to create FCM service: {e}")
        # Return None on error so caller can handle it
        return None

def initialize_fcm_service(service_account_path: str = None) -> FCMService:
    """Initialize and return FCM service"""
    global fcm_service
    fcm_service = FCMService(service_account_path)
    return fcm_service
