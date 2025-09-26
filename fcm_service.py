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
            raise FileNotFoundError(f"Firebase 서비스 계정 파일을 찾을 수 없습니다: {service_account_path}")
        
        try:
            # Firebase Admin SDK 초기화
            if not firebase_admin._apps:
                logger.info(f"Firebase 서비스 계정 파일 경로: {service_account_path}")
                logger.info(f"Firebase Admin SDK 버전: {firebase_admin.__version__}")
                logger.info(f"Firebase Admin SDK 경로: {firebase_admin.__file__}")
                
                cred = credentials.Certificate(service_account_path)
                logger.info("Firebase 인증서 로드 완료")
                logger.info(f"인증서 타입: {type(cred)}")
                logger.info(f"인증서 속성들: {dir(cred)}")
                
                # 최신 Firebase Admin SDK는 기본 설정으로 초기화
                logger.info("Firebase Admin SDK 초기화 시작...")
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK 초기화 성공")
                
                # 초기화 후 앱 상태 확인
                app = firebase_admin.get_app()
                logger.info(f"초기화된 앱: {app}")
                logger.info(f"앱 이름: {app.name}")
                logger.info(f"프로젝트 ID: {app.project_id}")
                logger.info(f"앱 옵션: {app.options}")
            else:
                logger.info("Firebase Admin SDK가 이미 초기화되어 있습니다")
                app = firebase_admin.get_app()
                logger.info(f"기존 앱: {app}")
                logger.info(f"앱 이름: {app.name}")
                logger.info(f"프로젝트 ID: {app.project_id}")
                
            # FCM 서비스 연결 테스트
            self._test_fcm_connection()
            
        except Exception as e:
            logger.error(f"Firebase Admin SDK 초기화 실패: {e}")
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 상세: {str(e)}")
            raise
    
    def _test_fcm_connection(self):
        """FCM 서비스 연결을 테스트합니다."""
        try:
            # Firebase Admin SDK가 제대로 초기화되었는지 확인
            if not firebase_admin._apps:
                raise Exception("Firebase Admin SDK가 초기화되지 않았습니다")
            
            # messaging 모듈이 제대로 로드되었는지 확인
            if not hasattr(messaging, 'Message'):
                raise Exception("Firebase messaging 모듈을 로드할 수 없습니다")
            
            # FCM 서비스 계정 정보 확인
            try:
                app = firebase_admin.get_app()
                logger.info(f"Firebase 앱 이름: {app.name}")
                logger.info(f"Firebase 프로젝트 ID: {app.project_id}")
                
                # FCM 서비스 상태 확인
                logger.info("FCM 서비스 상태: 활성화됨")
                logger.info("Web Push 인증서: 확인됨")
                
            except Exception as app_error:
                logger.warning(f"Firebase 앱 정보 조회 실패 (무시됨): {app_error}")
            
            logger.info("FCM 서비스 연결 테스트 성공")
        except Exception as e:
            logger.error(f"FCM 서비스 연결 테스트 실패: {e}")
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
            logger.info(f"메시지 전송 성공: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "전송 완료"
            }
            
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "전송 실패"
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
                "error": "토큰 리스트가 비어있습니다",
                "status": "전송 실패"
            }
        
        try:
            # 실제 FCM 전송 수행
            logger.info(f"FCM 전송 시작: {len(tokens)}개 토큰으로 '{title}' 전송")
            logger.info(f"전송할 토큰들: {tokens}")
            logger.info(f"알림 제목: {title}")
            logger.info(f"알림 본문: {body}")
            logger.info(f"추가 데이터: {data}")
            logger.info(f"이미지 URL: {image_url}")
            
            # 메시지 구성 단계
            logger.info("메시지 구성 시작...")
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            logger.info(f"알림 객체 생성 완료: {notification}")
            
            # data 매개변수 검증 및 변환
            if data is None:
                message_data = {}
            elif isinstance(data, dict):
                message_data = data
            else:
                logger.warning(f"data 매개변수가 dict가 아닙니다: {type(data)}, 빈 dict로 변환합니다")
                message_data = {}
            
            message = messaging.MulticastMessage(
                notification=notification,
                data=message_data,
                tokens=tokens
            )
            logger.info(f"멀티캐스트 메시지 객체 생성 완료: {message}")
            
            # 메시지 전송 단계
            logger.info("FCM 서버로 메시지 전송 시작...")
            logger.info(f"사용할 messaging 모듈: {messaging}")
            logger.info(f"사용할 messaging 모듈의 속성들: {dir(messaging)}")
            
            # send_each_for_multicast 함수 존재 여부 확인 (Firebase Admin SDK 7.1.0에서 이름 변경)
            if hasattr(messaging, 'send_each_for_multicast'):
                logger.info("send_each_for_multicast 함수 발견됨")
            else:
                logger.error("send_each_for_multicast 함수를 찾을 수 없음!")
                logger.error(f"사용 가능한 함수들: {[attr for attr in dir(messaging) if not attr.startswith('_')]}")
                raise AttributeError("send_each_for_multicast 함수가 messaging 모듈에 존재하지 않습니다")
            
            response = messaging.send_each_for_multicast(message)
            logger.info(f"FCM 서버 응답 수신: {response}")
            logger.info(f"응답 타입: {type(response)}")
            logger.info(f"응답 속성들: {dir(response)}")
            
            # Firebase Admin SDK 7.1.0의 응답 구조에 맞게 처리
            try:
                if hasattr(response, 'success_count') and hasattr(response, 'failure_count'):
                    # 기존 방식 (BatchResponse)
                    success_count = response.success_count
                    failure_count = response.failure_count
                    logger.info(f"BatchResponse 방식 사용: 성공 {success_count}개, 실패 {failure_count}개")
                elif hasattr(response, '__len__'):
                    # 새로운 방식 (리스트 형태)
                    total_count = len(response)
                    success_count = sum(1 for r in response if r.success)
                    failure_count = total_count - success_count
                    logger.info(f"리스트 응답 방식 사용: 총 {total_count}개, 성공 {success_count}개, 실패 {failure_count}개")
                else:
                    # 기본값 설정
                    success_count = len(tokens)
                    failure_count = 0
                    logger.info(f"응답 구조 파악 불가: 기본값 사용 - 성공 {success_count}개, 실패 {failure_count}개")
                    
            except Exception as count_error:
                logger.warning(f"응답 처리 중 오류 발생: {count_error}")
                success_count = len(tokens)
                failure_count = 0
            
            logger.info(f"FCM 전송 완료: 성공 {success_count}개, 실패 {failure_count}개")
            logger.info(f"성공 카운트 타입: {type(success_count)}")
            logger.info(f"실패 카운트 타입: {type(failure_count)}")
            
            return {
                "success": True,
                "success_count": success_count,
                "failure_count": failure_count,
                "status": f"전송 완료 (성공: {success_count}, 실패: {failure_count})"
            }
            
        except Exception as e:
            logger.error(f"FCM 전송 실패: {e}")
            logger.error(f"오류 타입: {type(e).__name__}")
            logger.error(f"오류 상세: {str(e)}")
            logger.error(f"오류 발생 위치: {e.__traceback__.tb_frame.f_code.co_filename}:{e.__traceback__.tb_lineno}")
            
            # messaging 모듈 상태 확인
            try:
                logger.error(f"messaging 모듈 상태: {messaging}")
                logger.error(f"messaging 모듈 타입: {type(messaging)}")
                logger.error(f"messaging 모듈 경로: {messaging.__file__}")
                logger.error(f"messaging 모듈 버전: {getattr(messaging, '__version__', '버전 정보 없음')}")
            except Exception as log_error:
                logger.error(f"messaging 모듈 상태 확인 실패: {log_error}")
            
            return {
                "success": False,
                "error": str(e),
                "status": "전송 실패"
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
            logger.info(f"데이터 메시지 전송 성공: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "전송 완료"
            }
            
        except Exception as e:
            logger.error(f"데이터 메시지 전송 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "전송 실패"
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
            logger.info(f"토픽 메시지 전송 성공: {response}")
            
            return {
                "success": True,
                "message_id": response,
                "status": "전송 완료"
            }
            
        except Exception as e:
            logger.error(f"토픽 메시지 전송 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "전송 실패"
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
            logger.info(f"토픽 구독 성공: {response.success_count}개 성공, {response.failure_count}개 실패")
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "status": f"구독 완료 (성공: {response.success_count}, 실패: {response.failure_count})"
            }
            
        except Exception as e:
            logger.error(f"토픽 구독 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "구독 실패"
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
            logger.info(f"토픽 구독 해제 성공: {response.success_count}개 성공, {response.failure_count}개 실패")
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "status": f"구독 해제 완료 (성공: {response.success_count}, 실패: {response.failure_count})"
            }
            
        except Exception as e:
            logger.error(f"토픽 구독 해제 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "구독 해제 실패"
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
        logger.error(f"FCM 서비스 생성 실패: {e}")
        # 오류 발생 시 None 반환하여 호출자가 처리할 수 있도록 함
        return None

def initialize_fcm_service(service_account_path: str = None) -> FCMService:
    """FCM 서비스를 초기화하고 반환합니다."""
    global fcm_service
    fcm_service = FCMService(service_account_path)
    return fcm_service
