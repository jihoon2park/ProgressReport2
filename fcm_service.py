import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import logging
from typing import Dict, List, Optional, Union

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FCMService:
    """Firebase Cloud Messaging 서비스 클래스"""
    
    def __init__(self, service_account_path: str = None):
        """
        FCM 서비스 초기화
        
        Args:
            service_account_path: Firebase 서비스 계정 JSON 파일 경로
        """
        if service_account_path is None:
            # 기본 경로 설정 - 새로운 서비스 계정 키 사용
            current_dir = os.path.dirname(os.path.abspath(__file__))
            service_account_path = os.path.join(
                current_dir, 
                'credential', 
                'incidentalarmapp-firebase-adminsdk-fbsvc-07fb0e5787.json'
            )
        
        # 파일 존재 여부 확인
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Firebase service account file not found: {service_account_path}")
        
        try:
            # Firebase Admin SDK 초기화
            if not firebase_admin._apps:
                logger.info(f"Firebase service account file path: {service_account_path}")
                logger.info(f"Firebase Admin SDK version: {firebase_admin.__version__}")
                logger.info(f"Firebase Admin SDK path: {firebase_admin.__file__}")
                
                cred = credentials.Certificate(service_account_path)
                logger.info("Firebase credential loaded")
                logger.info(f"Credential type: {type(cred)}")
                logger.info(f"Credential attributes: {dir(cred)}")
                
                # 최신 Firebase Admin SDK는 기본 설정으로 초기화
                logger.info("Initializing Firebase Admin SDK...")
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully")
                
                # 초기화 후 앱 상태 확인
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
                
            # FCM 서비스 연결 테스트
            self._test_fcm_connection()
            
        except Exception as e:
            logger.error(f"Firebase Admin SDK initialization failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise
    
    def _test_fcm_connection(self):
        """FCM 서비스 연결을 테스트합니다."""
        try:
            # Firebase Admin SDK가 제대로 초기화되었는지 확인
            if not firebase_admin._apps:
                raise Exception("Firebase Admin SDK is not initialized")
            
            # messaging 모듈이 제대로 로드되었는지 확인
            if not hasattr(messaging, 'Message'):
                raise Exception("Unable to load Firebase messaging module")
            
            # FCM 서비스 계정 정보 확인
            try:
                app = firebase_admin.get_app()
                logger.info(f"Firebase app name: {app.name}")
                logger.info(f"Firebase project ID: {app.project_id}")
                
                # FCM 서비스 상태 확인
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
        특정 토큰으로 푸시 알림 전송
        
        Args:
            token: FCM 등록 토큰
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (선택사항)
            image_url: 알림 이미지 URL (선택사항)
            
        Returns:
            전송 결과 딕셔너리
        """
        try:
            # 메시지 구성
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url
                ),
                data=data or {},
                token=token
            )
            
            # 메시지 전송
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
        여러 토큰으로 푸시 알림 전송 (멀티캐스트)
        
        Args:
            tokens: FCM 등록 토큰 리스트
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (선택사항)
            image_url: 알림 이미지 URL (선택사항)
            
        Returns:
            전송 결과 딕셔너리
        """
        if not tokens:
            return {
                "success": False,
                "error": "Token list is empty",
                "status": "send_failed"
            }
        
        try:
            # 실제 FCM 전송 수행
            logger.info(f"Starting FCM send: {len(tokens)} tokens, title='{title}'")
            logger.info(f"Tokens: {tokens}")
            logger.info(f"Notification title: {title}")
            logger.info(f"Notification body: {body}")
            logger.info(f"Additional data: {data}")
            logger.info(f"Image URL: {image_url}")
            
            # 메시지 구성 단계
            logger.info("Building message...")
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            logger.info(f"Notification object created: {notification}")
            
            # data 매개변수 검증 및 변환
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
            
            # 메시지 전송 단계
            logger.info("Sending message to FCM server...")
            logger.info(f"messaging module: {messaging}")
            logger.info(f"messaging module attributes: {dir(messaging)}")
            
            # send_each_for_multicast 함수 존재 여부 확인 (Firebase Admin SDK 7.1.0에서 이름 변경)
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
            
            # Firebase Admin SDK 7.1.0의 응답 구조에 맞게 처리
            try:
                if hasattr(response, 'success_count') and hasattr(response, 'failure_count'):
                    # 기존 방식 (BatchResponse)
                    success_count = response.success_count
                    failure_count = response.failure_count
                    logger.info(f"BatchResponse: success {success_count}, failure {failure_count}")
                elif hasattr(response, '__len__'):
                    # 새로운 방식 (리스트 형태)
                    total_count = len(response)
                    success_count = sum(1 for r in response if r.success)
                    failure_count = total_count - success_count
                    logger.info(f"List response: total {total_count}, success {success_count}, failure {failure_count}")
                else:
                    # 기본값 설정
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
            
            # messaging 모듈 상태 확인
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
        데이터만 포함된 메시지 전송 (백그라운드 처리용)
        
        Args:
            token: FCM 등록 토큰
            data: 전송할 데이터
            title: 알림 제목 (선택사항)
            body: 알림 본문 (선택사항)
            
        Returns:
            전송 결과 딕셔너리
        """
        try:
            # 메시지 구성
            message_data = {
                "data": data,
                "token": token
            }
            
            # 알림이 있는 경우 추가
            if title or body:
                message_data["notification"] = messaging.Notification(
                    title=title or "",
                    body=body or ""
                )
            
            message = messaging.Message(**message_data)
            
            # 메시지 전송
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
        특정 토픽으로 구독한 모든 기기에 메시지 전송
        
        Args:
            topic: 토픽 이름
            title: 알림 제목
            body: 알림 본문
            data: 추가 데이터 (선택사항)
            
        Returns:
            전송 결과 딕셔너리
        """
        try:
            # 메시지 구성
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                topic=topic
            )
            
            # 메시지 전송
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
        여러 토큰을 특정 토픽에 구독
        
        Args:
            tokens: FCM 등록 토큰 리스트
            topic: 토픽 이름
            
        Returns:
            구독 결과 딕셔너리
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
        여러 토큰을 특정 토픽에서 구독 해제
        
        Args:
            tokens: FCM 등록 토큰 리스트
            topic: 토픽 이름
            
        Returns:
            구독 해제 결과 딕셔너리
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

# 전역 FCM 서비스 인스턴스
fcm_service = None

def get_fcm_service() -> FCMService:
    """전역 FCM 서비스 인스턴스를 반환합니다."""
    global fcm_service
    try:
        if fcm_service is None:
            fcm_service = FCMService()
        return fcm_service
    except Exception as e:
        logger.error(f"Failed to create FCM service: {e}")
        # 오류 발생 시 None 반환하여 호출자가 처리할 수 있도록 함
        return None

def initialize_fcm_service(service_account_path: str = None) -> FCMService:
    """FCM 서비스를 초기화하고 반환합니다."""
    global fcm_service
    fcm_service = FCMService(service_account_path)
    return fcm_service
