import json
import os
import requests
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProgressNoteAPIClient:
    def __init__(self, site=None):
        """Progress Note API 클라이언트 초기화"""
        from config import SITE_SERVERS, get_api_headers
        
        self.site = site
        if site and site in SITE_SERVERS:
            self.api_url = f"http://{SITE_SERVERS[site]}/api/progressnote"
        else:
            # 기본값 (Parafield Gardens)
            self.site = 'Parafield Gardens'
            self.api_url = f"http://{SITE_SERVERS['Parafield Gardens']}/api/progressnote"
            
        self.prepare_send_file = "data/prepare_send.json"
        
        # 세션 설정 (사이트별 API 헤더 사용)
        self.session = requests.Session()
        self.session.headers.update(get_api_headers(self.site))
        
        logger.info(f"ProgressNoteAPIClient initialized for site '{self.site}' with API URL: {self.api_url}")
        logger.info(f"API 헤더: {dict(self.session.headers)}")

    def load_prepare_send_data(self) -> Optional[Dict[str, Any]]:
        """prepare_send.json 파일을 로드합니다."""
        try:
            if not os.path.exists(self.prepare_send_file):
                logger.error(f"prepare_send.json 파일이 존재하지 않습니다: {self.prepare_send_file}")
                return None
            
            with open(self.prepare_send_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("prepare_send.json 파일 로드 성공")
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"파일 로드 오류: {str(e)}")
            return None

    def validate_progress_note_data(self, data: Dict[str, Any]) -> bool:
        """Progress Note 데이터의 유효성을 검사합니다."""
        required_fields = [
            'ClientId',
            'EventDate', 
            'ProgressNoteEventType',
            'NotesPlainText',
            'CreatedByUser',
            'CreatedDate'
        ]
        
        # 필수 필드 확인
        for field in required_fields:
            if field not in data:
                logger.error(f"필수 필드 누락: {field}")
                return False
        
        # ProgressNoteEventType 구조 확인
        if 'Id' not in data.get('ProgressNoteEventType', {}):
            logger.error("ProgressNoteEventType.Id 필드 누락")
            return False
        
        # CreatedByUser 구조 확인
        user_required_fields = ['FirstName', 'LastName', 'UserName', 'Position']
        created_by_user = data.get('CreatedByUser', {})
        for field in user_required_fields:
            if field not in created_by_user:
                logger.error(f"CreatedByUser.{field} 필드 누락")
                return False
        
        logger.info("Progress Note 데이터 유효성 검사 통과")
        return True

    def send_progress_note(self, data: Optional[Dict[str, Any]] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Progress Note를 API로 전송합니다."""
        try:
            # 데이터가 제공되지 않으면 파일에서 로드
            if data is None:
                data = self.load_prepare_send_data()
                if data is None:
                    return False, {"error": "데이터 로드 실패"}
            
            # 데이터 유효성 검사
            if not self.validate_progress_note_data(data):
                return False, {"error": "데이터 유효성 검사 실패"}
            
            # API 요청 전송
            logger.info(f"Progress Note API 요청 시작: {self.api_url}")
            logger.info(f"전송 데이터: ClientId={data.get('ClientId')}, "
                       f"EventType={data.get('ProgressNoteEventType', {}).get('Id')}, "
                       f"User={data.get('CreatedByUser', {}).get('UserName')}")
            
            response = self.session.post(
                self.api_url,
                json=data,
                timeout=30
            )
            
            logger.info(f"API 응답 상태 코드: {response.status_code}")
            
            # 응답 처리
            if response.status_code == 200 or response.status_code == 201:
                try:
                    response_data = response.json()
                    logger.info("Progress Note 전송 성공")
                    self._log_success(data, response_data)
                    return True, response_data
                except json.JSONDecodeError:
                    # JSON 응답이 없는 경우도 성공으로 처리
                    logger.info("Progress Note 전송 성공 (응답 데이터 없음)")
                    self._log_success(data, {"status": "success"})
                    return True, {"status": "success"}
            else:
                error_msg = f"API 요청 실패 - 상태 코드: {response.status_code}"
                try:
                    error_response = response.json()
                    error_msg += f", 응답: {error_response}"
                    logger.error(error_msg)
                    return False, error_response
                except json.JSONDecodeError:
                    error_msg += f", 응답 텍스트: {response.text}"
                    logger.error(error_msg)
                    return False, {"error": error_msg, "status_code": response.status_code}

        except requests.Timeout:
            error_msg = "API 요청 시간 초과 (30초)"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except requests.ConnectionError:
            error_msg = f"API 서버 연결 실패: {self.api_url}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except requests.RequestException as e:
            error_msg = f"API 요청 오류: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    return False, error_response
                except:
                    pass
            return False, {"error": error_msg}
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.error(error_msg)
            return False, {"error": error_msg}

    def _log_success(self, sent_data: Dict[str, Any], response_data: Dict[str, Any]):
        """성공 로그를 기록합니다."""
        success_log = {
            "timestamp": datetime.now().isoformat(),
            "client_id": sent_data.get('ClientId'),
            "event_type_id": sent_data.get('ProgressNoteEventType', {}).get('Id'),
            "created_by": sent_data.get('CreatedByUser', {}).get('UserName'),
            "api_response": response_data
        }
        
        # 성공 로그를 파일에 기록 (선택사항)
        try:
            log_file = "data/progress_note_success.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(success_log, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"성공 로그 파일 기록 실패: {str(e)}")

    def test_connection(self) -> bool:
        """API 서버 연결 테스트"""
        try:
            # 간단한 HEAD 요청으로 연결 테스트
            response = self.session.head(self.api_url, timeout=10)
            if response.status_code in [200, 201, 404, 405]:  # 404, 405도 연결은 성공
                logger.info("API 서버 연결 테스트 성공")
                return True
            else:
                logger.warning(f"API 서버 응답 이상 - 상태 코드: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"API 서버 연결 테스트 실패: {str(e)}")
            return False


def send_progress_note_to_api(site=None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    Progress Note를 API로 전송하는 편의 함수
    
    Args:
        site: 대상 사이트 이름 (예: 'Parafield Gardens')
        
    Returns:
        tuple: (성공 여부, 응답 데이터 또는 에러 정보)
    """
    logger.info(f"Progress Note API 전송 시작 - 사이트: {site}")
    
    try:
        api_client = ProgressNoteAPIClient(site)
        
        # 연결 테스트 (선택사항)
        if not api_client.test_connection():
            logger.warning("API 서버 연결 테스트 실패, 하지만 전송 시도 계속")
        
        # Progress Note 전송
        success, response = api_client.send_progress_note()
        
        if success:
            logger.info(f"Progress Note API 전송 성공 - 사이트: {site}")
        else:
            logger.error(f"Progress Note API 전송 실패 - 사이트: {site}, 응답: {response}")
        
        return success, response
        
    except Exception as e:
        error_msg = f"Progress Note API 전송 중 예상치 못한 오류: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}


def send_specific_progress_note(data: Dict[str, Any], site=None) -> tuple[bool, Optional[Dict[str, Any]]]:
    """
    특정 Progress Note 데이터를 API로 전송하는 함수
    
    Args:
        data: 전송할 Progress Note 데이터
        site: 대상 사이트 이름 (예: 'Parafield Gardens')
        
    Returns:
        tuple: (성공 여부, 응답 데이터 또는 에러 정보)
    """
    logger.info(f"특정 Progress Note 데이터 API 전송 시작 - 사이트: {site}")
    
    try:
        api_client = ProgressNoteAPIClient(site)
        success, response = api_client.send_progress_note(data)
        
        if success:
            logger.info(f"특정 Progress Note 데이터 API 전송 성공 - 사이트: {site}")
        else:
            logger.error(f"특정 Progress Note 데이터 API 전송 실패 - 사이트: {site}, 응답: {response}")
        
        return success, response
        
    except Exception as e:
        error_msg = f"특정 Progress Note 데이터 API 전송 중 예상치 못한 오류: {str(e)}"
        logger.error(error_msg)
        return False, {"error": error_msg}


if __name__ == "__main__":
    # 테스트용 코드
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Parafield Gardens 사이트로 테스트
    success, response = send_progress_note_to_api('Parafield Gardens')
    if success:
        print("✅ Progress Note 전송 성공!")
        print(f"응답: {response}")
    else:
        print("❌ Progress Note 전송 실패!")
        print(f"오류: {response}") 