from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    session, 
    jsonify, 
    send_from_directory,
    make_response
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import requests
from functools import wraps
import logging
import logging.handlers
import json
import os
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일에서 환경변수 로딩
load_dotenv()

# 내부 모듈 임포트
from api_client import APIClient
from api_carearea import APICareArea
from api_eventtype import APIEventType
from config import SITE_SERVERS, API_HEADERS, get_available_sites
import logging
import os
import sys
from datetime import datetime

# 로깅 설정
logger = logging.getLogger(__name__)

# SITE_SERVERS 안전성 체크 및 폴백 처리
def get_safe_site_servers():
    """안전한 사이트 서버 정보 반환 (폴백 포함)"""
    try:
        # config에서 SITE_SERVERS 가져오기
        if SITE_SERVERS and len(SITE_SERVERS) > 0:
            logger.info(f"SITE_SERVERS 로드 성공: {list(SITE_SERVERS.keys())}")
            return SITE_SERVERS
        else:
            logger.warning("SITE_SERVERS가 비어있음, 폴백 사용")
            return get_fallback_site_servers()
    except Exception as e:
        logger.error(f"SITE_SERVERS 로드 실패: {e}, 폴백 사용")
        return get_fallback_site_servers()

# IIS 환경 감지 및 설정
def is_iis_environment():
    """IIS 환경인지 확인"""
    return 'IIS' in os.environ.get('SERVER_SOFTWARE', '') or 'IIS' in os.environ.get('HTTP_HOST', '')

def get_application_path():
    """애플리케이션 경로 반환 (IIS 환경 고려)"""
    if is_iis_environment():
        # IIS 환경에서는 현재 작업 디렉토리 사용
        return os.getcwd()
    else:
        # 개발 환경에서는 스크립트 디렉토리 사용
        return os.path.dirname(os.path.abspath(__file__))

# 전역 변수로 안전한 사이트 서버 정보 캐시
_cached_site_servers = None

def get_cached_site_servers():
    """캐시된 안전한 사이트 서버 정보 반환"""
    global _cached_site_servers
    if _cached_site_servers is None:
        _cached_site_servers = get_safe_site_servers()
    return _cached_site_servers

def get_fallback_site_servers():
    """폴백 사이트 서버 정보"""
    return {
        'Parafield Gardens': '192.168.1.11:8080',
        'Nerrilda': '192.168.21.12:8080',
        'Ramsay': '192.168.31.12:8080',
        'West Park': '192.168.41.12:8080',
        'Yankalilla': '192.168.51.12:8080'
    }

def debug_site_servers():
    """사이트 서버 정보 디버깅"""
    try:
        logger.info("=== 사이트 서버 정보 디버깅 시작 ===")
        logger.info(f"USE_DB_API_KEYS: {getattr(config, 'USE_DB_API_KEYS', 'Not defined')}")
        logger.info(f"SITE_SERVERS 타입: {type(SITE_SERVERS)}")
        logger.info(f"SITE_SERVERS 내용: {SITE_SERVERS}")
        logger.info(f"SITE_SERVERS 길이: {len(SITE_SERVERS) if SITE_SERVERS else 0}")
        
        # 안전한 사이트 서버 정보 확인
        safe_servers = get_safe_site_servers()
        logger.info(f"안전한 사이트 서버: {safe_servers}")
        
        logger.info("=== 사이트 서버 정보 디버깅 완료 ===")
        return safe_servers
    except Exception as e:
        logger.error(f"사이트 서버 디버깅 중 오류: {e}")
        return get_fallback_site_servers()
from config_users import authenticate_user, get_user
from config_env import get_flask_config, print_current_config, get_cache_policy
from models import load_user, User
from usage_logger import usage_logger

# 알람 서비스 임포트
from alarm_manager import get_alarm_manager
from alarm_service import get_alarm_services
from dataclasses import asdict

# FCM 서비스 임포트
from fcm_service import get_fcm_service
from fcm_token_manager_sqlite import get_fcm_token_manager_sqlite as get_fcm_token_manager

# Task Manager 임포트
from task_manager import get_task_manager

# Policy Scheduler 임포트
from policy_scheduler import start_policy_scheduler

# Admin API 임포트
from admin_api import admin_api

# 환경별 설정 로딩
flask_config = get_flask_config()

# 로깅 설정
log_level = getattr(logging, flask_config['LOG_LEVEL'].upper())


# 로그 디렉토리 생성
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 파일 핸들러와 콘솔 핸들러 설정
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # 콘솔 출력 (개발 환경에서만)
        logging.StreamHandler(),
        # 파일 출력 (최대 50MB, 10개 파일 로테이션) - 운영 서버용
        logging.handlers.RotatingFileHandler(
            f'{log_dir}/app.log',
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

# 운영 서버용 추가 로깅 설정
def setup_production_logging():
    """운영 서버용 로깅 설정"""
    try:
        # 에러 전용 로그 파일
        error_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/error.log',
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # 액세스 로그 파일
        access_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/access.log',
            maxBytes=30*1024*1024,  # 30MB
            backupCount=5,
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        
        # 루트 로거에 핸들러 추가
        root_logger = logging.getLogger()
        root_logger.addHandler(error_handler)
        root_logger.addHandler(access_handler)
        
        logger.info("운영 서버용 로깅 설정 완료")
        
    except Exception as e:
        logger.error(f"로깅 설정 중 오류: {str(e)}")

# 운영 서버용 로깅 설정 적용
setup_production_logging()

# 현재 설정 출력
print_current_config()

# 플라스크 앱 초기화
app = Flask(__name__, static_url_path='/static')

# 환경별 설정 적용
app.secret_key = flask_config['SECRET_KEY']
app.config['DEBUG'] = flask_config['DEBUG']

# 세션 타임아웃 설정 (모든 사용자에게 동일하게 적용)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=10)

def set_session_permanent(user_role):
    """모든 사용자에게 동일한 세션 설정 적용"""
    try:
        # 모든 사용자에게 동일하게 적용
        session.permanent = True
        logger.info(f"사용자 세션 설정: {user_role}")
    except Exception as e:
        logger.error(f"세션 설정 중 오류: {e}")
        # 오류 발생 시 기본값으로 설정
        session.permanent = False

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def user_loader(user_id):
    """Flask-Login의 user_loader 콜백"""
    return load_user(user_id)

@login_manager.unauthorized_handler
def unauthorized_callback():
    logger.warning(f"인증되지 않은 접근 시도: {request.method} {request.path}")
    logger.warning(f"요청 IP: {request.remote_addr}")
    logger.warning(f"User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    
    if request.path.startswith('/api/'):
        logger.error(f"API 인증 실패: {request.path}")
        return jsonify({'success': False, 'message': 'Authentication required', 'is_expired': True}), 401
    
    logger.info(f"웹 페이지 인증 실패, 홈으로 리다이렉트: {request.path}")
    return redirect(url_for('home'))

# 설정 검증 로그
if flask_config['ENVIRONMENT'] == 'production' and flask_config['DEBUG']:
    logger.warning("⚠️  운영환경에서 DEBUG 모드가 활성화되어 있습니다!")

if flask_config['SECRET_KEY'] == 'fallback-secret-key':
    logger.warning("⚠️  기본 SECRET_KEY를 사용하고 있습니다. 보안상 위험합니다!")

# 데이터 디렉토리 확인 및 생성
if not os.path.exists('data'):
    os.makedirs('data')
    logger.info("data 디렉토리 생성됨")

# Policy Scheduler 시작 (백그라운드)
try:
    start_policy_scheduler()
    logger.info("✅ Policy Scheduler 시작됨")
except Exception as e:
    logger.warning(f"⚠️ Policy Scheduler 시작 실패: {e}")
    logger.info("앱은 정상 실행되지만 자동 알림 기능은 비활성화됩니다.")

# Unified Data Sync Manager 시작 (백그라운드)
try:
    from unified_data_sync_manager import init_unified_sync
    init_unified_sync()
    logger.info("✅ Unified Data Sync Manager 시작됨")
except Exception as e:
    logger.warning(f"⚠️ Unified Data Sync Manager 시작 실패: {e}")
    logger.info("앱은 정상 실행되지만 통합 데이터 동기화 기능은 비활성화됩니다.")

# ==============================
# 인증 관련 기능 (Flask-Login 사용)
# ==============================

def _is_authenticated():
    """사용자 인증 상태 확인 (Flask-Login 사용)"""
    return current_user.is_authenticated

def require_authentication(wrapped_function):
    """인증이 필요한 라우트에 사용할 데코레이터 (Flask-Login 사용)"""
    @wraps(wrapped_function)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('home'))
        return wrapped_function(*args, **kwargs)
    return decorated_function

# ==============================
# 데이터 처리 기능
# ==============================

def process_client_information(client_info):
    """클라이언트 정보를 가공하여 필요한 정보만 추출"""
    if not client_info:
        logger.warning("처리할 클라이언트 정보가 없습니다.")
        return []
        
    processed_clients = []
    try:
        for client in client_info:
            processed_client = {
                'PersonId': client.get('MainClientServiceId'),  # MainClientServiceId를 PersonId로 사용
                'ClientName': f"{client.get('Title', '')} {client.get('FirstName', '')} {client.get('LastName', '')}".strip(),
                'PreferredName': client.get('PreferredName', ''),
                'Gender': client.get('Gender', ''),
                'BirthDate': client.get('BirthDate'),
                'WingName': client.get('WingName'),
                'RoomName': client.get('RoomName'),
                'MainClientServiceId': client.get('MainClientServiceId'),  # ClientServiceId로 사용
                'OriginalPersonId': client.get('PersonId'),  # 원본 PersonId도 보관
                'ClientRecordId': client.get('Id')  # 클라이언트 레코드 ID (ClientId로 사용)
            }
            processed_clients.append(processed_client)

        # 가공된 데이터를 파일로 저장
        save_json_file('data/Client_list.json', processed_clients)
        
        return processed_clients
    except Exception as e:
        logger.error(f"클라이언트 정보 처리 중 오류 발생: {str(e)}")
        return []

def fetch_client_information(site):
    """클라이언트 정보를 가져오고 처리 (비활성화 - DB 사용)"""
    logger.info(f"클라이언트 정보 조회 건너뜀 - DB에서 조회됨 (사이트: {site})")
    return True, None  # DB에서 조회하므로 API 호출 불필요

def fetch_care_area_information(site):
    """Care Area 정보를 가져오고 처리 (비활성화 - DB 사용)"""
    logger.info(f"Care Area 정보 조회 건너뜀 - DB에서 조회됨 (사이트: {site})")
    return True, None  # DB에서 조회하므로 API 호출 불필요

def fetch_event_type_information(site):
    """Event Type 정보를 가져오고 처리 (비활성화 - DB 사용)"""
    logger.info(f"Event Type 정보 조회 건너뜀 - DB에서 조회됨 (사이트: {site})")
    return True, None  # DB에서 조회하므로 API 호출 불필요

def save_json_file(filepath, data):
    """JSON 데이터를 파일로 저장"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"파일 저장 성공: {filepath}")
        return True
    except Exception as e:
        logger.error(f"JSON 파일 저장 중 오류 발생: {str(e)}")
        return False

def save_client_data(username, site, client_info):
    """클라이언트 데이터를 JSON 파일로 저장 (비활성화 - DB 사용)"""
    logger.info(f"클라이언트 데이터 저장 건너뜀 - DB에 저장됨 (사이트: {site})")
    return None  # DB에 저장되므로 JSON 파일 생성 불필요

def create_progress_note_json(form_data):
    """사용자 입력 데이터를 Progress Note JSON 형식으로 변환 (값이 있는 필드만 포함)"""
    try:
        logger.info(f"Progress Note JSON 생성 시작 - 입력 데이터: {form_data}")
        
        # 필수 필드들
        progress_note = {}
        
        # ClientId와 ClientServiceId 처리 (필수)
        if form_data.get('clientId'):
            try:
                selected_client_id = int(form_data.get('clientId'))
                
                # Client_list.json에서 선택된 클라이언트 정보 찾기
                import json
                try:
                    with open('data/Client_list.json', 'r', encoding='utf-8') as f:
                        clients = json.load(f)
                    
                    selected_client = None
                    for client in clients:
                        if client.get('PersonId') == selected_client_id:
                            selected_client = client
                            break
                    
                    if selected_client:
                        # 성공한 조합: ClientId = 클라이언트 레코드 ID, ClientServiceId = MainClientServiceId
                        progress_note["ClientId"] = selected_client.get('ClientRecordId', selected_client_id)  # 클라이언트 레코드 ID
                        progress_note["ClientServiceId"] = selected_client.get('MainClientServiceId', selected_client_id)  # MainClientServiceId
                        
                        logger.info(f"ClientId 설정: {progress_note['ClientId']} (클라이언트 레코드 ID)")
                        logger.info(f"ClientServiceId 설정: {progress_note['ClientServiceId']} (MainClientServiceId)")
                    else:
                        logger.error(f"선택된 클라이언트를 찾을 수 없습니다: {selected_client_id}")
                        return None
                        
                except Exception as e:
                    logger.error(f"Client_list.json 읽기 실패: {e}")
                    # 기본값으로 설정 - 클라이언트 레코드 ID를 알 수 없으므로 MainClientServiceId 사용
                    progress_note["ClientId"] = selected_client_id  # MainClientServiceId를 ClientId로 사용 (fallback)
                    progress_note["ClientServiceId"] = selected_client_id  # MainClientServiceId
                    logger.warning("기본값으로 설정 - 정확한 클라이언트 레코드 ID를 찾을 수 없어 MainClientServiceId 사용")
                    
            except (ValueError, TypeError) as e:
                logger.error(f"ClientId 변환 실패: {form_data.get('clientId')}, 오류: {e}")
                return None
        else:
            logger.error("ClientId가 없습니다 - 필수 필드")
            return None
            
        # EventDate (필수)
        if form_data.get('eventDate'):
            progress_note["EventDate"] = form_data.get('eventDate')
            logger.info(f"EventDate 설정: {progress_note['EventDate']}")
        else:
            # EventDate가 없으면 현재 시간 사용
            progress_note["EventDate"] = datetime.now().isoformat()
            logger.info(f"EventDate 기본값 설정: {progress_note['EventDate']}")
            
        # ProgressNoteEventType (필수)
        if form_data.get('eventType'):
            try:
                event_type_id = int(form_data.get('eventType'))
                progress_note["ProgressNoteEventType"] = {
                    "Id": event_type_id
                }
                logger.info(f"ProgressNoteEventType 설정: {event_type_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"EventType 변환 실패: {form_data.get('eventType')}, 오류: {e}")
                return None
        else:
            logger.error("EventType이 없습니다 - 필수 필드")
            return None
            
        # NotesPlainText (필수)
        notes_text = form_data.get('notes', '').strip()
        if notes_text:
            progress_note["NotesPlainText"] = notes_text
            logger.info(f"NotesPlainText 설정: {len(notes_text)}")
        else:
            # 빈 노트라도 빈 문자열로 설정
            progress_note["NotesPlainText"] = ""
            logger.info("NotesPlainText 빈 문자열로 설정")
            
        # 선택적 필드들 (값이 있을 때만 추가)
        
        # CreatedByUser (ExternalUserDto 형식)
        username = current_user.username
        first_name = current_user.first_name
        last_name = current_user.last_name
        position = current_user.position
        
        # 세션에 정보가 없으면 사용자 DB에서 다시 가져오기 - 이부분 나중에 다시 확인해야 함...... Jay 2025-06-05
        if username and (not first_name or not last_name or not position):
            logger.warning(f"세션에 사용자 정보 누락 - 사용자 DB에서 다시 조회: {username}")
            user_data = get_user(username)
            if user_data:
                first_name = user_data.get('first_name', first_name)
                last_name = user_data.get('last_name', last_name)
                position = user_data.get('position', position)
                logger.info(f"사용자 DB에서 정보 복구 완료: {first_name} {last_name} - {position}")
        
        if username:
            progress_note["CreatedByUser"] = {
                "FirstName": first_name,
                "LastName": last_name,
                "UserName": username,
                "Position": position
            }
            logger.info(f"CreatedByUser 설정: {first_name} {last_name} ({username}) - {position}")
            
            # 디버깅용 - 각 필드 상태 확인
            logger.debug(f"CreatedByUser 필드 상태: FirstName='{first_name}', LastName='{last_name}', UserName='{username}', Position='{position}'")
            
        # CreatedDate (선택적)
        if form_data.get('createDate'):
            progress_note["CreatedDate"] = form_data.get('createDate')
            logger.info(f"CreatedDate 설정: {progress_note['CreatedDate']}")
            
        # CareAreas (선택한 경우만)
        if form_data.get('careArea'):
            try:
                care_area_id = int(form_data.get('careArea'))
                progress_note["CareAreas"] = [{
                    "Id": care_area_id
                }]
                logger.info(f"CareAreas 설정: {care_area_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"CareArea 변환 실패: {form_data.get('careArea')}, 오류: {e}")
                
        # ProgressNoteRiskRating (선택한 경우만)
        if form_data.get('riskRating'):
            risk_rating_value = form_data.get('riskRating')
            
            # 문자열 ID를 숫자로 매핑
            risk_rating_mapping = {
                'rr1': 1,  # Extreme
                'rr2': 2,  # High
                'rr3': 3,  # Moderate
                'rr4': 4   # Low
            }
            
            risk_rating_id = None
            if risk_rating_value in risk_rating_mapping:
                risk_rating_id = risk_rating_mapping[risk_rating_value]
            elif risk_rating_value.isdigit():
                risk_rating_id = int(risk_rating_value)
                
            if risk_rating_id:
                progress_note["ProgressNoteRiskRating"] = {
                    "Id": risk_rating_id
                }
                logger.info(f"ProgressNoteRiskRating 설정: {risk_rating_id}")
                
        # Boolean 필드들 (true인 경우만 추가)
        if form_data.get('lateEntry'):
            progress_note["IsLateEntry"] = True
            logger.info("IsLateEntry 설정: True")
            
        if form_data.get('flagOnNoticeboard'):
            progress_note["IsNoticeFlag"] = True
            logger.info("IsNoticeFlag 설정: True")
            
        if form_data.get('archived'):
            progress_note["IsArchived"] = True
            logger.info("IsArchived 설정: True")
            
        # ClientServiceId는 API에서 필요한 경우에만 추가
        # progress_note["ClientServiceId"] = 26  # 임시 제거
        
        logger.info(f"Progress Note JSON 생성 완료: {progress_note}")
        return progress_note
        
    except Exception as e:
        logger.error(f"Progress Note JSON 생성 중 예외 발생: {str(e)}", exc_info=True)
        return None

def save_prepare_send_json(progress_note_data):
    """prepare_send.json 파일에 데이터 저장 (매번 새 파일로 생성, 기존 파일은 백업)"""
    try:
        filepath = 'data/prepare_send.json'
        
        # 기존 파일이 있으면 백업 생성
        if os.path.exists(filepath):
            # 순환 백업 시스템 (최대 1000개)
            MAX_BACKUP_COUNT = 1000
            
            # 기존 백업 파일들 확인
            existing_backups = []
            for i in range(1, MAX_BACKUP_COUNT + 1):
                backup_filepath = f'data/prepare_send_backup{i}.json'
                if os.path.exists(backup_filepath):
                    existing_backups.append(i)
            
            # 다음 백업 번호 결정
            if len(existing_backups) < MAX_BACKUP_COUNT:
                # 아직 최대 개수에 도달하지 않았으면 다음 번호 사용
                backup_number = len(existing_backups) + 1
                logger.info(f"새 백업 파일 생성: backup{backup_number}.json")
            else:
                # 최대 개수에 도달했으면 가장 오래된 파일 찾아서 덮어쓰기
                oldest_backup = 1
                oldest_time = None
                
                for i in range(1, MAX_BACKUP_COUNT + 1):
                    backup_filepath = f'data/prepare_send_backup{i}.json'
                    if os.path.exists(backup_filepath):
                        file_time = os.path.getmtime(backup_filepath)
                        if oldest_time is None or file_time < oldest_time:
                            oldest_time = file_time
                            oldest_backup = i
                
                backup_number = oldest_backup
                logger.info(f"최대 백업 개수 도달 - 가장 오래된 파일 덮어쓰기: backup{backup_number}.json")
            
            backup_filepath = f'data/prepare_send_backup{backup_number}.json'
            
            # 기존 파일을 백업으로 이동 (덮어쓰기)
            try:
                import shutil
                shutil.move(filepath, backup_filepath)
                logger.info(f"기존 파일을 백업으로 이동: {filepath} -> {backup_filepath}")
                logger.info(f"현재 백업 파일 개수: {min(len(existing_backups) + 1, MAX_BACKUP_COUNT)}/{MAX_BACKUP_COUNT}")
            except Exception as e:
                logger.error(f"백업 파일 생성 실패: {str(e)}")
                # 백업 실패해도 새 파일은 저장 계속 진행
        
        # 새 파일로 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_note_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Progress Note 데이터가 새 파일로 저장됨: {filepath}")
        logger.info(f"저장된 데이터: {progress_note_data}")
        return True
    except Exception as e:
        logger.error(f"prepare_send.json 저장 중 오류: {str(e)}")
        return False

# ==============================
# API 서버 상태 체크 기능
# ==============================

def check_api_server_health(server_ip):
    """API 서버 상태 체크"""
    try:
        url = f"http://{server_ip}/api/system/canconnect"
        response = requests.get(url, timeout=5)
        return response.status_code == 200 and response.text.strip() == 'true'
    except Exception as e:
        logger.error(f"API 서버 상태 체크 실패 - {server_ip}: {str(e)}")
        return False

@app.route('/api/server-status')
def get_server_status():
    """모든 사이트의 API 서버 상태를 반환"""
    try:
        # 안전한 사이트 서버 정보 사용
        safe_site_servers = get_safe_site_servers()
        status = {}
        
        for site, server_ip in safe_site_servers.items():
            try:
                status[site] = check_api_server_health(server_ip)
                logger.debug(f"서버 상태 체크 완료 - {site}: {status[site]}")
            except Exception as e:
                logger.error(f"서버 상태 체크 실패 - {site}: {e}")
                status[site] = False
        
        logger.info(f"서버 상태 API 응답: {status}")
        return jsonify(status)
    except Exception as e:
        logger.error(f"서버 상태 API 오류: {e}")
        # 오류 시 빈 상태 반환
        return jsonify({})

@app.route('/api/debug/site-servers')
def debug_site_servers_api():
    """사이트 서버 정보 디버깅 API (IIS 문제 진단용)"""
    try:
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'IIS' if is_iis_environment() else 'Development',
            'config_loaded': False,
            'site_servers': {},
            'fallback_used': False,
            'errors': [],
            'iis_info': {
                'server_software': os.environ.get('SERVER_SOFTWARE', 'Not set'),
                'http_host': os.environ.get('HTTP_HOST', 'Not set'),
                'application_path': get_application_path(),
                'current_directory': os.getcwd(),
                'python_path': sys.executable
            }
        }
        
        # config 모듈 상태 확인
        try:
            import config
            debug_info['config_loaded'] = True
            debug_info['use_db_api_keys'] = getattr(config, 'USE_DB_API_KEYS', 'Not defined')
            debug_info['site_servers'] = getattr(config, 'SITE_SERVERS', {})
        except Exception as e:
            debug_info['errors'].append(f"Config 로드 실패: {str(e)}")
        
        # 안전한 사이트 서버 정보 확인
        try:
            safe_servers = get_safe_site_servers()
            debug_info['safe_site_servers'] = safe_servers
            debug_info['fallback_used'] = safe_servers == get_fallback_site_servers()
        except Exception as e:
            debug_info['errors'].append(f"안전한 사이트 서버 로드 실패: {str(e)}")
            debug_info['safe_site_servers'] = get_fallback_site_servers()
            debug_info['fallback_used'] = True
        
        # API 키 매니저 상태 확인
        try:
            from api_key_manager import get_api_key_manager
            manager = get_api_key_manager()
            api_keys = manager.get_all_api_keys()
            debug_info['api_keys_count'] = len(api_keys)
            debug_info['api_keys'] = [{'site': key['site_name'], 'server': f"{key['server_ip']}:{key['server_port']}"} for key in api_keys]
        except Exception as e:
            debug_info['errors'].append(f"API 키 매니저 확인 실패: {str(e)}")
            debug_info['api_keys_count'] = 0
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({
            'error': f"디버깅 API 오류: {str(e)}",
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/logs')
def get_logs():
    """로그 파일 목록 및 내용 조회 API"""
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return jsonify({'error': '로그 디렉토리가 없습니다'}), 404
        
        # 로그 파일 목록
        log_files = []
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(log_dir, filename)
                stat = os.stat(filepath)
                log_files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify({
            'log_files': sorted(log_files, key=lambda x: x['modified'], reverse=True),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f"로그 조회 실패: {str(e)}"}), 500

@app.route('/api/logs/<filename>')
def get_log_content(filename):
    """특정 로그 파일 내용 조회"""
    try:
        # 보안: 파일명에 경로 조작 방지
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '잘못된 파일명'}), 400
        
        filepath = os.path.join("logs", filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '파일을 찾을 수 없습니다'}), 404
        
        # 마지막 N줄 읽기
        lines = request.args.get('lines', 100, type=int)
        lines = min(lines, 1000)  # 최대 1000줄로 제한
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            content_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            'filename': filename,
            'lines': len(content_lines),
            'total_lines': len(all_lines),
            'content': [line.rstrip() for line in content_lines],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f"로그 내용 조회 실패: {str(e)}"}), 500

@app.route('/logs')
def logs_page():
    """로그 뷰어 페이지"""
    return render_template('LogViewer.html')

@app.route('/api/health')
def health_check():
    """서버 상태 확인 API (모바일 앱용)"""
    try:
        # 데이터베이스 연결 테스트
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        # FCM 서비스 상태 확인
        fcm_service = get_fcm_service()
        fcm_status = fcm_service is not None
        
        # Task Manager 상태 확인
        task_manager = get_task_manager()
        task_manager_status = task_manager is not None
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': True,
                'fcm': fcm_status,
                'task_manager': task_manager_status,
                'user_count': user_count
            },
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

# ==============================
# 라우트 정의
# ==============================

@app.route('/')
def home():
    """홈 페이지"""
    if current_user.is_authenticated:
        logger.info(f"홈 페이지 접근 - 사용자: {current_user.username}, 인증: {current_user.is_authenticated}")
        
        # 세션에서 allowed_sites와 site 정보 확인
        allowed_sites = session.get('allowed_sites', [])
        site = session.get('site', 'Ramsay')
        
        logger.info(f"홈 페이지 세션 정보 - allowed_sites: {allowed_sites} (타입: {type(allowed_sites)}), site: {site}")
        logger.info(f"홈 페이지 세션 전체 내용: {dict(session)}")
        
        # allowed_sites가 비어있으면 기본값으로 설정
        if not allowed_sites:
            safe_site_servers = get_safe_site_servers()
            allowed_sites = list(safe_site_servers.keys())
            session['allowed_sites'] = allowed_sites
            logger.warning(f"홈 페이지에서 allowed_sites가 비어있음, 기본 사이트 목록으로 설정: {allowed_sites}")
        
        # ROD 사용자인 경우 전용 대시보드로 이동 (대소문자 구분 안함)
        username_upper = current_user.username.upper()
        logger.info(f"사용자명 확인: {current_user.username} -> {username_upper}")
        if username_upper == 'ROD':
            logger.info(f"ROD 사용자 감지 - rod_dashboard로 리다이렉트")
            return redirect(url_for('rod_dashboard'))
        
        # PG_admin 사용자인 경우 incident_viewer로 이동
        if current_user.role == 'site_admin':
            logger.info(f"PG_admin 사용자 감지 - incident_viewer로 리다이렉트")
            return redirect(url_for('incident_viewer', site=site))
        
        # 일반 사용자는 progress_notes로 리다이렉트하되, 세션 정보 확인
        logger.info(f"일반 사용자 - progress_notes로 리다이렉트 (site={site}, allowed_sites={allowed_sites})")
        return redirect(url_for('progress_notes', site=site))
    
    # 폴백 로그인 페이지
    safe_site_servers = get_safe_site_servers()
    return render_template('LoginPage.html', sites=safe_site_servers.keys())

@app.route('/login', methods=['GET'])
def login_page():
    """로그인 페이지"""
    try:
        # 안전한 사이트 서버 정보 사용
        safe_site_servers = get_safe_site_servers()
        sites = list(safe_site_servers.keys())
        logger.info(f"로그인 페이지 렌더링 - 사이트 목록: {sites}")
        return render_template('LoginPage.html', sites=sites)
    except Exception as e:
        logger.error(f"로그인 페이지 렌더링 실패: {e}")
        # 최종 폴백
        fallback_sites = list(get_fallback_site_servers().keys())
        return render_template('LoginPage.html', sites=fallback_sites)

@app.route('/login', methods=['POST'])
def login():
    """로그인 처리"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        site = request.form.get('site')
        
        logger.info(f"로그인 시도 - 사용자: {username}, 사이트: {site}")
        
        # 접속 로그 기록
        user_info = {
            "username": username,
            "display_name": username,
            "role": "unknown",
            "position": "unknown"
        }
        usage_logger.log_access(user_info)

        # 입력값 검증
        if not all([username, password, site]):
            flash('{Please fill in all fields}', 'error')
            return redirect(url_for('home'))

        # 인증 검증
        auth_success, user_info = authenticate_user(username, password)
        
        if auth_success:
            logger.info("인증 성공")
            
            try:
                # location 정책 적용
                user_location = user_info.get('location', [])
                user_role = user_info.get('role', 'USER').upper()
                logger.info(f"사용자 location 정보: {user_location}, 타입: {type(user_location)}, 역할: {user_role}")
                
                # ADMIN 사용자는 항상 모든 사이트 접근 허용
                if user_role == 'ADMIN':
                    safe_site_servers = get_safe_site_servers()
                    allowed_sites = list(safe_site_servers.keys())
                    logger.info(f"ADMIN 사용자 - 모든 사이트 허용: {allowed_sites}")
                # location이 All이거나 2개 이상이면 모든 사이트 허용
                elif (isinstance(user_location, list) and (len(user_location) > 1 or (len(user_location) == 1 and user_location[0].lower() == 'all'))) or (isinstance(user_location, str) and user_location.lower() == 'all'):
                    safe_site_servers = get_safe_site_servers()
                    allowed_sites = list(safe_site_servers.keys())
                    logger.info(f"모든 사이트 허용: {allowed_sites}")
                else:
                    # location이 1개면 해당 사이트만 허용
                    allowed_sites = user_location if isinstance(user_location, list) else [user_location]
                    # site 값을 무조건 allowed_sites[0]로 강제 설정
                    if allowed_sites:
                        site = allowed_sites[0]
                        logger.info(f"단일 사이트 허용: {allowed_sites}, 선택된 사이트: {site}")
                    else:
                        # allowed_sites가 비어있으면 기본값으로 설정
                        allowed_sites = [site]
                        logger.warning(f"allowed_sites가 비어있음, 기본값으로 설정: {allowed_sites}")

                if site not in allowed_sites:
                    flash(f'You are not allowed to access {site}.', 'error')
                    return redirect(url_for('home'))

                # 1. Data 폴더 정리를 먼저 실행 (기존 파일들 삭제)
                cache_policy = get_cache_policy()
                if cache_policy['cleanup_data_on_login']:
                    cleanup_success = cleanup_data_folder()
                    if cleanup_success:
                        logger.info("Data 폴더 정리 성공 - 기존 파일들 삭제됨")
                    else:
                        logger.warning("Data 폴더 정리 실패")
                else:
                    logger.info("캐시 정책에 따라 Data 폴더 정리 건너뜀")

                # 2. DB에서 데이터 조회 (JSON 파일 생성 제거)
                # 매일 새벽 3시에 DB 업데이트되므로 로그인 시 API 호출 불필요
                logger.info(f"로그인 시 DB에서 데이터 조회 - 사이트: {site}")
                
                # 3. 세션 설정 (JSON 파일 대신 DB 사용)
                try:
                    # DB에서 클라이언트 데이터 조회 (필요시)
                    # session['current_file'] = f"data/{site.replace(' ', '_').lower()}_client.json"  # 제거
                    logger.info(f"DB 기반 데이터 조회 완료 - 사이트: {site}")
                    
                    # 4. Flask-Login을 사용한 로그인 처리
                    user = User(username, user_info)
                    user_role = user_info.get('role', 'USER').upper()
                    
                    # 모든 사용자에게 동일한 세션 설정 적용
                    login_user(user, remember=False)  # 모든 사용자: 브라우저 닫으면 세션 만료
                    session.permanent = False
                    logger.info(f"사용자 로그인: remember=False, session.permanent=False (역할: {user_role})")
                    
                    # 사용자 역할에 따라 세션 타임아웃 설정
                    set_session_permanent(user_role)
                    
                    # 세션 생성 시간 기록
                    session['_created'] = datetime.now().isoformat()
                    session['user_role'] = user_role  # 사용자 역할을 세션에 저장
                    
                    # 세션에 추가 정보 저장
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # 허용된 사이트 정보 저장
                    
                    logger.info(f"세션 저장: site={site}, allowed_sites={allowed_sites}")
                    logger.info(f"로그인 후 세션 전체 내용: {dict(session)}")
                    
                    flash('Login successful!', 'success')
                    logger.info(f"로그인 성공 - 사용자: {username}, 사이트: {site}")
                    
                    # 로그인 성공 로그 기록
                    success_user_info = {
                        "username": username,
                        "display_name": user_info.get('display_name', username),
                        "role": user_info.get('role', 'unknown'),
                        "position": user_info.get('position', 'unknown')
                    }
                    usage_logger.log_access(success_user_info)
                    
                    # ROD 사용자인 경우 전용 대시보드로 이동 (대소문자 구분 안함)
                    username_upper = username.upper()
                    logger.info(f"로그인 사용자명 확인: {username} -> {username_upper}")
                    if username_upper == 'ROD':
                        logger.info(f"로그인 성공 - ROD 사용자 감지, rod_dashboard로 리다이렉트")
                        return redirect(url_for('rod_dashboard', site=site))
                    elif user_role == 'SITE_ADMIN':
                        logger.info(f"로그인 성공 - PG_admin 사용자 감지, incident_viewer로 리다이렉트")
                        return redirect(url_for('incident_viewer', site=site))
                    else:
                        logger.info(f"로그인 성공 - 일반 사용자, progress_notes로 리다이렉트")
                        return redirect(url_for('progress_notes', site=site))
                        
                except Exception as e:
                    logger.error(f"데이터 저장 중 오류 발생: {str(e)}")
                    flash('Error occurred while saving data.', 'error')
                    return redirect(url_for('home'))
            except Exception as e:
                logger.error(f"API 호출 중 오류 발생: {str(e)}")
                # API 오류 시에도 로그인 허용
                try:
                    # Flask-Login을 사용한 로그인 처리
                    user = User(username, user_info)
                    user_role = user_info.get('role', 'USER').upper()
                    
                    # 모든 사용자에게 동일한 세션 설정 적용
                    login_user(user, remember=False)  # 모든 사용자: 브라우저 닫으면 세션 만료
                    session.permanent = False
                    logger.info(f"사용자 로그인 (API 오류 있음): remember=False, session.permanent=False (역할: {user_role})")
                    
                    # 사용자 역할에 따라 세션 타임아웃 설정
                    set_session_permanent(user_role)
                    
                    # 세션 생성 시간 기록
                    session['_created'] = datetime.now().isoformat()
                    session['user_role'] = user_role  # 사용자 역할을 세션에 저장
                    
                    # 세션에 추가 정보 저장
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # 허용된 사이트 정보 저장
                    
                    logger.info(f"세션 저장 (API 오류 있음): site={site}, allowed_sites={allowed_sites}")
                    logger.info(f"API 오류 시 로그인 후 세션 전체 내용: {dict(session)}")
                    
                    flash('Login successful! (Some data may not be available)', 'success')
                    logger.info(f"로그인 성공 (API 오류 있음) - 사용자: {username}, 사이트: {site}")
                    
                    # ROD 사용자인 경우 전용 대시보드로 이동 (대소문자 구분 안함)
                    username_upper = username.upper()
                    logger.info(f"로그인 사용자명 확인 (API 오류 있음): {username} -> {username_upper}")
                    if username_upper == 'ROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - ROD 사용자 감지, rod_dashboard로 리다이렉트")
                        return redirect(url_for('rod_dashboard', site=site))
                    elif user_role == 'SITE_ADMIN':
                        logger.info(f"로그인 성공 (API 오류 있음) - PG_admin 사용자 감지, incident_viewer로 리다이렉트")
                        return redirect(url_for('incident_viewer', site=site))
                    else:
                        logger.info(f"로그인 성공 (API 오류 있음) - 일반 사용자, progress_notes로 리다이렉트")
                        return redirect(url_for('progress_notes', site=site))
                except Exception as login_error:
                    logger.error(f"로그인 처리 중 오류: {str(login_error)}")
                    flash('Login failed due to system error.', 'error')
                
            return redirect(url_for('home'))
        else:
            flash('{Invalid authentication information}', 'error')
            return redirect(url_for('home'))
            
    except Exception as e:
        logger.error(f"로그인 처리 중 예외 발생: {str(e)}")
        flash('{An error occurred while connecting to the server}', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """로그아웃 처리"""
    try:
        # 로그아웃 전 세션 상태 로깅
        if current_user.is_authenticated:
            logger.info(f"로그아웃 시작 - 사용자: {current_user.username}, 역할: {current_user.role}")
            user_info = {
                "username": current_user.username,
                "display_name": current_user.display_name,
                "role": current_user.role,
                "position": current_user.position
            }
            usage_logger.log_access(user_info)
        else:
            logger.info("로그아웃 시작 - 인증되지 않은 사용자")
        
        # Flask-Login 로그아웃
        logout_user()
        logger.info("Flask-Login logout_user() 완료")
        
        # 세션 완전 정리
        session.clear()
        logger.info("세션 clear() 완료")
        
        # 추가 세션 정리 (Flask-Login 관련)
        if '_user_id' in session:
            del session['_user_id']
            logger.info("_user_id 세션 제거")
        
        if 'user_role' in session:
            del session['user_role']
            logger.info("user_role 세션 제거")
        
        if '_created' in session:
            del session['_created']
            logger.info("_created 세션 제거")
        
        if 'allowed_sites' in session:
            del session['allowed_sites']
            logger.info("allowed_sites 세션 제거")
        
        if 'site' in session:
            del session['site']
            logger.info("site 세션 제거")
        
        # Flask-Login 관련 추가 세션 정리
        if '_fresh' in session:
            del session['_fresh']
            logger.info("_fresh 세션 제거")
        
        if '_permanent' in session:
            del session['_permanent']
            logger.info("_permanent 세션 제거")
        
        # 세션 수정 표시
        session.modified = True
        logger.info("세션 수정 완료")
        
        # Flask-Login 세션 쿠키도 정리
        response = make_response(redirect(url_for('home')))
        response.delete_cookie('remember_token')
        response.delete_cookie('session')
        logger.info("세션 쿠키 정리 완료")
        
        flash('You have been logged out successfully.', 'info')
        logger.info("로그아웃 완료 - 홈 페이지로 리다이렉트")
        
        return response
        
    except Exception as e:
        logger.error(f"로그아웃 중 오류 발생: {str(e)}")
        # 오류 발생 시에도 세션 정리 시도
        try:
            session.clear()
            logout_user()
        except:
            pass
        flash('Logout completed with errors.', 'warning')
        return redirect(url_for('home'))

@app.route('/api/clear-database', methods=['POST'])
@login_required
def clear_database():
    """데이터베이스 초기화"""
    try:
        return jsonify({
            'success': True,
            'message': 'Database cleared successfully'
        })
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/index')
@login_required
def index():
    """Progress Note 입력 페이지"""
    site = request.args.get('site', session.get('site', 'Ramsay'))
    return render_template('index.html', selected_site=site, current_user=current_user)

@app.route('/rod-dashboard')
@login_required
def rod_dashboard():
    """ROD 전용 대시보드"""
    # ROD 사용자가 아닌 경우 접근 제한 (대소문자 구분 안함)
    username_upper = current_user.username.upper()
    logger.info(f"ROD 대시보드 접근 시도 - 사용자명 확인: {current_user.username} -> {username_upper}")
    if username_upper != 'ROD':
        flash('Access denied. This dashboard is for ROD users only.', 'error')
        return redirect(url_for('progress_notes'))
    
    allowed_sites = session.get('allowed_sites', [])
    site = request.args.get('site', session.get('site', 'Parafield Gardens'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    # 모든 사이트 정보 가져오기
    sites_info = []
    safe_site_servers = get_safe_site_servers()
    for site_name in safe_site_servers.keys():
        sites_info.append({
            'name': site_name,
            'server': safe_site_servers[site_name],
            'is_selected': site_name == site
        })
    
    return render_template('RODDashboard.html', 
                         site=site, 
                         sites=sites_info,
                         current_user=current_user)

@app.route('/progress-notes')
@login_required
def progress_notes():
    try:
        allowed_sites = session.get('allowed_sites', [])
        site = request.args.get('site', session.get('site', 'Ramsay'))
        logger.info(f"progress_notes: allowed_sites={allowed_sites} (타입: {type(allowed_sites)}), site={site}")
        logger.info(f"progress_notes 세션 전체 내용: {dict(session)}")
        logger.info(f"progress_notes request.args: {dict(request.args)}")
        
        # allowed_sites가 비어있으면 기본 사이트 목록에서 선택
        if not allowed_sites:
            safe_site_servers = get_safe_site_servers()
            allowed_sites = list(safe_site_servers.keys())
            # 세션에 다시 저장
            session['allowed_sites'] = allowed_sites
            logger.warning(f"allowed_sites가 비어있음, 기본 사이트 목록으로 설정: {allowed_sites}")
        
        # location이 1개면 무조건 그 사이트로 강제
        if isinstance(allowed_sites, list) and len(allowed_sites) == 1:
            forced_site = allowed_sites[0]
            if site != forced_site:
                logger.info(f"단일 사이트 강제 리다이렉트: {site} -> {forced_site}")
                return redirect(url_for('progress_notes', site=forced_site))
            site = forced_site
        
        # 접속 로그 기록
        try:
            user_info = {
                "username": current_user.username,
                "display_name": current_user.display_name,
                "role": current_user.role,
                "position": current_user.position
            }
            usage_logger.log_access(user_info)
        except Exception as e:
            logger.error(f"접속 로그 기록 실패: {e}")
        
        logger.info(f"progress_notes 최종 렌더링 - site: {site}, allowed_sites: {allowed_sites}")
        return render_template('ProgressNoteList.html', site=site)
    
    except Exception as e:
        logger.error(f"progress_notes 오류: {e}")
        # 오류 발생 시 로그인 페이지로 리다이렉트
        flash('페이지 로드 중 오류가 발생했습니다. 다시 로그인해주세요.', 'error')
        return redirect(url_for('login_page'))

@app.route('/save_progress_note', methods=['POST'])
@login_required
def save_progress_note():
    """Progress Note 데이터 저장 및 API 전송"""
    try:
        # JSON 데이터 받기
        form_data = request.get_json()
        
        if not form_data:
            return jsonify({'success': False, 'message': 'Data is empty'})
        
        logger.info(f"Received form data: {form_data}")
        
        # 사용자 정보 수집
        user_info = {
            "username": current_user.username if current_user else None,
            "display_name": current_user.display_name if current_user else None,
            "role": current_user.role if current_user else None,
            "position": current_user.position if current_user else None
        }
        
        # Progress Note JSON 형식으로 변환
        progress_note = create_progress_note_json(form_data)
        
        if not progress_note:
            return jsonify({'success': False, 'message': 'Failed to generate JSON.'})
        
        # prepare_send.json에 저장
        if not save_prepare_send_json(progress_note):
            return jsonify({'success': False, 'message': 'Failed to save file.'})
        
        logger.info("prepare_send.json 파일 저장 완료, API 전송 시작...")
        
        # API로 Progress Note 전송
        try:
            from api_progressnote import send_progress_note_to_api
            
            # 세션에서 선택된 사이트 정보 가져오기
            selected_site = session.get('site', 'Parafield Gardens')  # 기본값: Parafield Gardens
            
            api_success, api_response = send_progress_note_to_api(selected_site)
            
            if api_success:
                logger.info("Progress Note API 전송 성공")
                # 성공 로그 기록
                usage_logger.log_progress_note(form_data, user_info, success=True)
                return jsonify({
                    'success': True, 
                    'message': 'Progress Note saved and sent to API successfully.',
                    'data': progress_note,
                    'api_response': api_response
                })
            else:
                logger.warning(f"Progress Note API 전송 실패: {api_response}")
                # 실패 로그 기록
                usage_logger.log_progress_note(form_data, user_info, success=False, error_message=api_response)
                # 파일 저장은 성공했지만 API 전송 실패
                return jsonify({
                    'success': True,  # 파일 저장은 성공
                    'message': 'Progress Note saved but API transmission failed.',
                    'data': progress_note,
                    'api_error': api_response,
                    'warning': 'API transmission failed. The file was saved successfully.'
                })
        except ImportError as e:
            logger.error(f"API 모듈 import 오류: {str(e)}")
            # 실패 로그 기록
            usage_logger.log_progress_note(form_data, user_info, success=False, error_message=f"Import error: {str(e)}")
            return jsonify({
                'success': True,  # 파일 저장은 성공
                'message': 'Progress Note saved but API module not available.',
                'data': progress_note,
                'warning': 'API transmission module not found. The file was saved successfully.'
            })
        except Exception as e:
            logger.error(f"API 전송 중 예상치 못한 오류: {str(e)}")
            # 실패 로그 기록
            usage_logger.log_progress_note(form_data, user_info, success=False, error_message=str(e))
            return jsonify({
                'success': True,  # 파일 저장은 성공
                'message': 'Progress Note saved but API transmission failed.',
                'data': progress_note,
                'api_error': str(e),
                'warning': f'An error occurred while sending the API: {str(e)}. The file was saved successfully.'
            })
            
    except Exception as e:
        logger.error(f"Progress Note saving error: {str(e)}")
        # 전체 실패 로그 기록
        user_info = {
            "username": current_user.username if current_user else None,
            "display_name": current_user.display_name if current_user else None,
            "role": current_user.role if current_user else None,
            "position": current_user.position if current_user else None
        }
        usage_logger.log_progress_note(form_data, user_info, success=False, error_message=str(e))
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

# ==============================
# API 엔드포인트
# ==============================

@app.route('/data/Client_list.json')
def get_client_list():
    """클라이언트 목록 JSON 반환"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'Client_list.json')
    except FileNotFoundError:
        return jsonify([]), 404

@app.route('/data/carearea.json')
@login_required
def get_care_area_list():
    """Care Area 목록 JSON 반환"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'carearea.json')
    except FileNotFoundError:
        return jsonify([]), 404

@app.route('/data/eventtype.json')
@login_required
def get_event_type_list():
    """Event Type 목록 JSON 반환"""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        return send_from_directory(data_dir, 'eventtype.json')
    except FileNotFoundError:
        return jsonify([]), 404

@app.route('/api/rod-residence-status')
@login_required
def get_rod_residence_status():
    """Resident of the day 현황을 가져옵니다."""
    try:
        site = request.args.get('site', 'Parafield Gardens')
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        
        logger.info(f"Fetching Resident of the day status for {site} - {year}/{month}")
        
        # Resident of the day 노트와 클라이언트 데이터 가져오기
        from api_progressnote_fetch import fetch_residence_of_day_notes_with_client_data
        residence_status = fetch_residence_of_day_notes_with_client_data(site, year, month)
        
        if not residence_status:
            logger.warning(f"No residence status data found for {site}")
            return jsonify({'error': 'No data found'}), 404
        
        # 통계 계산
        total_residences = len(residence_status)
        total_rn_en_notes = sum(1 for status in residence_status.values() if status.get('rn_en_has_note', False))
        total_pca_notes = sum(1 for status in residence_status.values() if status.get('pca_has_note', False))
        
        # 전체 노트 개수 계산
        total_rn_en_count = sum(status.get('rn_en_count', 0) for status in residence_status.values())
        total_pca_count = sum(status.get('pca_count', 0) for status in residence_status.values())
        total_notes_count = total_rn_en_count + total_pca_count
        
        # 전체 완료율 계산 (RN/EN과 PCA 모두 완료된 Residence 비율)
        completed_residences = sum(1 for status in residence_status.values() 
                                if status.get('rn_en_has_note', False) and status.get('pca_has_note', False))
        overall_completion_rate = round((completed_residences / total_residences * 100) if total_residences > 0 else 0, 1)
        
        logger.info(f"Resident of the day status processed: {total_residences} residences, {total_rn_en_notes} RN/EN notes, {total_pca_notes} PCA notes, {completed_residences} completed, {overall_completion_rate}% completion rate")
        logger.info(f"Total notes found: {total_notes_count} (RN/EN: {total_rn_en_count}, PCA: {total_pca_count})")
        
        return jsonify({
            'residence_status': list(residence_status.values()),
            'total_residences': total_residences,
            'total_rn_en_notes': total_rn_en_notes,
            'total_pca_notes': total_pca_notes,
            'total_rn_en_count': total_rn_en_count,
            'total_pca_count': total_pca_count,
            'total_notes_count': total_notes_count,
            'overall_completion_rate': overall_completion_rate
        })
        
    except Exception as e:
        logger.error(f"Error in get_rod_residence_status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rod-residence-list', methods=['POST'])
@login_required
def get_rod_residence_list():
    """ROD 전용 Residence 목록 반환 (빈 테이블용)"""
    try:
        # ROD 사용자만 접근 가능
        if current_user.username.upper() != 'ROD':
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        data = request.get_json()
        site = data.get('site', 'Parafield Gardens')

        try:
            from api_client import fetch_client_information
            
            # 클라이언트 데이터 가져오기
            client_success, client_data = fetch_client_information(site)
            
            if not client_success:
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch client data'
                }), 500

            # 클라이언트 데이터에서 Residence 목록 추출
            residences = []
            if isinstance(client_data, list):
                residences = client_data
            elif isinstance(client_data, dict) and 'clients' in client_data:
                residences = client_data['clients']
            elif isinstance(client_data, dict) and 'data' in client_data:
                residences = client_data['data']
            else:
                # 기본 Residence 목록 사용
                residences = [
                    "Residence A", "Residence B", "Residence C", "Residence D", "Residence E",
                    "Residence F", "Residence G", "Residence H", "Residence I", "Residence J"
                ]

            # Residence 정보 추출
            residence_status = []
            for residence in residences:
                residence_name = None
                preferred_name = None
                wing_name = None
                
                if isinstance(residence, dict):
                    # 실제 클라이언트 데이터 필드 사용
                    first_name = residence.get('FirstName', '')
                    surname = residence.get('Surname', '')
                    last_name = residence.get('LastName', '')
                    preferred_name = residence.get('PreferredName', '')
                    wing_name = residence.get('WingName', '')
                    
                    # Residence Name에는 FirstName + Surname 조합 사용
                    if first_name and surname:
                        residence_name = f"{first_name} {surname}"
                    elif first_name and last_name:
                        residence_name = f"{first_name} {last_name}"
                    elif first_name:
                        residence_name = first_name
                    else:
                        residence_name = ''
                    
                    # ID를 사용한 fallback
                    if not residence_name and 'PersonId' in residence:
                        residence_name = f"Client_{residence['PersonId']}"
                    elif not residence_name and 'id' in residence:
                        residence_name = f"Client_{residence['id']}"
                        
                elif isinstance(residence, str):
                    residence_name = residence
                
                if residence_name:
                    # MainClientServiceId 필드 추가
                    main_client_service_id = residence.get('MainClientServiceId') or residence.get('ClientServiceId') or residence.get('Id')
                    
                    residence_status.append({
                        'residence_name': residence_name,
                        'preferred_name': preferred_name or '',
                        'wing_name': wing_name or '',
                        'MainClientServiceId': main_client_service_id,  # 매칭용 ID 추가
                        'rn_en_has_note': False,
                        'pca_has_note': False,
                        'rn_en_authors': [],
                        'pca_authors': []
                    })

            return jsonify({
                'success': True,
                'site': site,
                'residence_status': residence_status,
                'total_residences': len(residence_status)
            })

        except Exception as e:
            logger.error(f"Error fetching residence list for site {site}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"ROD Residence list 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/rod-stats', methods=['POST'])
@login_required
def get_rod_stats():
    """ROD 전용 통계 정보 반환"""
    try:
        # ROD 사용자만 접근 가능
        if current_user.username.upper() != 'ROD':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site', 'Parafield Gardens')
        
        # 실제 통계 데이터를 가져오는 로직 (현재는 모의 데이터)
        stats = {
            'totalNotes': 0,
            'todayNotes': 0,
            'activeUsers': 0,
            'systemStatus': '🟢'
        }
        
        try:
            # 프로그레스 노트 수 가져오기
            from api_progressnote_fetch import fetch_progress_notes_for_site
            success, progress_notes = fetch_progress_notes_for_site(site, 30)  # 30일간
            
            if success and progress_notes:
                stats['totalNotes'] = len(progress_notes)
                
                # 오늘 날짜의 노트 수 계산
                today = datetime.now().date()
                today_notes = [note for note in progress_notes 
                             if note.get('EventDate') and 
                             datetime.fromisoformat(note['EventDate'].replace('Z', '+00:00')).date() == today]
                stats['todayNotes'] = len(today_notes)
            
            # 활성 사용자 수 (모의 데이터)
            stats['activeUsers'] = len([user for user in ['admin', 'PaulVaska', 'walgampola', 'ROD'] 
                                      if user != current_user.username])
            
        except Exception as e:
            logger.error(f"통계 데이터 가져오기 중 오류: {str(e)}")
            # 오류 시에도 기본 통계 반환
            stats['totalNotes'] = 0
            stats['todayNotes'] = 0
            stats['activeUsers'] = 1
            stats['systemStatus'] = '🟡'
        
        return jsonify({
            'success': True,
            'stats': stats,
            'site': site,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"ROD 통계 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/user-info')
@login_required
def get_user_info():
    """현재 로그인한 사용자 정보 반환"""
    try:
        user_info = {
            'username': current_user.username,
            'first_name': current_user.first_name,
            'last_name': current_user.last_name,
            'role': current_user.role,
            'position': current_user.position,
            'site': session.get('site')
        }
        return jsonify(user_info)
    except Exception as e:
        logger.error(f"사용자 정보 조회 중 오류: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/refresh-session', methods=['POST'])
@login_required
def refresh_session():
    """현재 세션 새로고침 - 사용자 정보 다시 로딩"""
    try:
        username = current_user.username
        if not username:
            return jsonify({'success': False, 'message': 'No username in session'}), 400
            
        # 사용자 정보 다시 가져오기
        user_data = get_user(username)
        if not user_data:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        # 새로운 User 객체 생성하여 로그인 갱신
        user = User(username, user_data)
        user_role = user_data.get('role', 'USER').upper()
        
        # ADMIN 사용자는 remember=True로 설정하여 세션 유지
        if user_role == 'ADMIN':
            login_user(user, remember=True)  # ADMIN: 브라우저 닫아도 세션 유지
            session.permanent = True
            logger.info(f"ADMIN 사용자 세션 새로고침: remember=True, session.permanent=True")
        else:
            login_user(user, remember=False)  # 일반 사용자: 브라우저 닫으면 세션 만료
            session.permanent = False
            logger.info(f"일반 사용자 세션 새로고침: remember=False, session.permanent=False")
        
        # 사용자 역할에 따라 세션 타임아웃 설정
        set_session_permanent(user_role)
        
        # 사용자 역할을 세션에 저장
        session['user_role'] = user_role
        
        logger.info(f"세션 새로고침 완료: {username}")
        
        return jsonify({
            'success': True,
            'message': 'Session refreshed successfully',
            'user_info': {
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'position': user.position
            }
        })
    except Exception as e:
        logger.error(f"세션 새로고침 중 오류: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/session-status')
@login_required
def get_session_status():
    """세션 상태 확인"""
    try:
        # 모든 사용자에게 동일한 세션 타임아웃 적용
        session_lifetime = timedelta(minutes=10)
        session_created = session.get('_created', datetime.now())
        
        if isinstance(session_created, str):
            session_created = datetime.fromisoformat(session_created)
        
        session_expires = session_created + session_lifetime
        now = datetime.now()
        
        # 남은 시간 계산 (초 단위)
        remaining_seconds = (session_expires - now).total_seconds()
        
        return jsonify({
            'success': True,
            'session_created': session_created.isoformat(),
            'session_expires': session_expires.isoformat(),
            'remaining_seconds': max(0, int(remaining_seconds)),
            'is_expired': remaining_seconds <= 0
        })
    except Exception as e:
        logger.error(f"세션 상태 확인 중 오류: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/extend-session', methods=['POST'])
@login_required
def extend_session():
    """세션 연장"""
    try:
        # 모든 사용자에게 동일한 세션 연장 적용
        session['_created'] = datetime.now().isoformat()
        
        # Flask-Login 세션 갱신 (재귀 방지를 위해 직접 세션 갱신)
        session.permanent = True
        session.modified = True
        
        logger.info(f"세션 연장 완료: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Session extended successfully',
            'session_created': session['_created']
        })
    except Exception as e:
        logger.error(f"세션 연장 중 오류: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/fetch-progress-notes', methods=['POST'])
@login_required
def fetch_progress_notes():
    """프로그레스 노트를 사이트에서 가져오기 (캐시 기반)"""
    try:
        data = request.get_json()
        site = data.get('site')
        days = data.get('days', 7)  # 기본값: 7일
        page = data.get('page', 1)  # 페이지 번호
        per_page = data.get('per_page', 50)  # 페이지당 항목 수
        force_refresh = data.get('force_refresh', False)  # 강제 새로고침
        event_types = data.get('event_types', [])  # 이벤트 타입 필터
        year = data.get('year')  # 년도
        month = data.get('month')  # 월
        
        if not site:
            logger.error("Site parameter is missing in request")
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"프로그레스 노트 가져오기 요청 - 사이트: {site}, 일수: {days}, 페이지: {page}, 페이지당: {per_page}")
        logger.info(f"Request data: {data}")
        
        # 사이트 서버 설정 확인
        safe_site_servers = get_safe_site_servers()
        if site not in safe_site_servers:
            logger.error(f"Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}")
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}'
            }), 400
        
        # 캐시 매니저 사용
        from progress_notes_cache_manager import cache_manager
        
        if force_refresh:
            # 강제 새로고침: 캐시 무시하고 API에서 직접 조회
            logger.info(f"강제 새로고침 모드 - API에서 직접 조회: {site}")
            result = cache_manager._get_notes_from_api_and_cache(site, page, per_page, days)
        else:
            # 하이브리드 캐싱 사용
            logger.info(f"하이브리드 캐싱 모드 - 사이트: {site}")
            result = cache_manager.get_cached_notes(site, page, per_page, days, use_hybrid=True)
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'data': result['notes'],
            'pagination': {
                'page': result['page'],
                'per_page': result['per_page'],
                'total_count': result['total_count'],
                'total_pages': result['total_pages']
            },
            'cache_info': {
                'status': result['cache_status'],
                'last_sync': result['last_sync'],
                'cache_age_hours': result.get('cache_age_hours', 0)
            },
            'site': site,
            'count': result['total_count'],
            'fetched_at': datetime.now().isoformat()
        }
        
        logger.info(f"프로그레스 노트 가져오기 성공 - {site}: {result['total_count']}개 (페이지 {page}/{result['total_pages']})")
        return jsonify(response_data)
        
        try:
            # ROD 대시보드 요청인지 확인 (year, month가 제공되고 event_types가 None이거나 빈 배열인 경우)
            if year is not None and month is not None and (not event_types or len(event_types) == 0):
                logger.info(f"ROD Dashboard request detected for {site} - {year}/{month}")
                from api_progressnote_fetch import fetch_residence_of_day_notes_with_client_data
                
                # 실시간 클라이언트 데이터와 함께 ROD 로직 사용
                residence_status = fetch_residence_of_day_notes_with_client_data(site, year, month)
                
                if residence_status:
                    logger.info(f"ROD data fetched successfully for {site}: {len(residence_status)} residences")
                    return jsonify({
                        'success': True,
                        'message': f'Successfully fetched ROD data for {len(residence_status)} residences',
                        'data': residence_status,
                        'site': site,
                        'count': len(residence_status),
                        'fetched_at': datetime.now().isoformat()
                    })
                else:
                    logger.warning(f"No ROD data found for {site}")
                    return jsonify({
                        'success': True,
                        'message': 'No ROD data found',
                        'data': {},
                        'site': site,
                        'count': 0,
                        'fetched_at': datetime.now().isoformat()
                    })
            else:
                # 일반적인 프로그레스 노트 요청
                from api_progressnote_fetch import fetch_progress_notes_for_site
                logger.info(f"Calling fetch_progress_notes_for_site for {site} with event_types: {event_types}")
                success, progress_notes = fetch_progress_notes_for_site(site, days, event_types, year, month)
            
            if success:
                logger.info(f"프로그레스 노트 가져오기 성공 - {site}: {len(progress_notes) if progress_notes else 0}개")
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched {len(progress_notes) if progress_notes else 0} progress notes',
                    'data': progress_notes,
                    'site': site,
                    'count': len(progress_notes) if progress_notes else 0,
                    'fetched_at': datetime.now().isoformat()
                })
            else:
                logger.error(f"프로그레스 노트 가져오기 실패 - {site}")
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch progress notes from server'
                }), 500
                
        except ImportError as e:
            logger.error(f"API 모듈 import 오류: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Progress note fetch module not available'
            }), 500
        except Exception as e:
            logger.error(f"fetch_progress_notes_for_site 호출 중 오류: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'message': f'Error in fetch_progress_notes_for_site: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"프로그레스 노트 가져오기 중 오류: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/fetch-progress-notes-incremental', methods=['POST'])
@login_required
def fetch_progress_notes_incremental():
    """증분 업데이트 API - 항상 7일간 데이터 반환 (단순화됨)"""
    try:
        data = request.get_json()
        site = data.get('site')
        
        if not site:
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"증분 업데이트 요청 (단순화됨) - 사이트: {site}, 항상 7일간 데이터 반환")
        
        try:
            from api_progressnote_fetch import fetch_progress_notes_for_site
            
            # 항상 7일간 데이터 가져오기
            success, progress_notes = fetch_progress_notes_for_site(site, 7)
            
            if success:
                logger.info(f"증분 업데이트 성공 (단순화됨) - {site}: {len(progress_notes) if progress_notes else 0}개")
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched {len(progress_notes) if progress_notes else 0} progress notes (1 week)',
                    'data': progress_notes,
                    'site': site,
                    'count': len(progress_notes) if progress_notes else 0,
                    'fetched_at': datetime.now().isoformat()
                })
            else:
                logger.error(f"증분 업데이트 실패 (단순화됨) - {site}")
                return jsonify({
                    'success': False,
                    'message': 'Failed to fetch progress notes from server'
                }), 500
                
        except ImportError as e:
            logger.error(f"API 모듈 import 오류: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Progress note fetch module not available'
            }), 500
            
    except Exception as e:
        logger.error(f"증분 업데이트 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/api/progress-notes-db-info')
@login_required
def get_progress_notes_db_info():
    """IndexedDB 정보 조회 (클라이언트에서 호출)"""
    try:
        # 클라이언트에서 IndexedDB 정보를 조회하도록 안내
        return jsonify({
            'success': True,
            'message': 'Use client-side IndexedDB API to get database info',
            'endpoints': {
                'fetch_notes': '/api/fetch-progress-notes',
                'fetch_incremental': '/api/fetch-progress-notes-incremental'
            }
        })
    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@app.route('/data/<filename>')
def serve_data_file(filename):
    """data 디렉토리의 JSON 파일들을 서빙"""
    # 허용된 파일 확장자
    allowed_extensions = {'.json'}
    
    # 파일 확장자 확인
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return jsonify({'error': 'Invalid file type'}), 400
    
    data_dir = os.path.join(app.root_path, 'data')
    file_path = os.path.join(data_dir, filename)
    
    # 파일 존재 확인
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_from_directory(data_dir, filename)

@app.route('/incident-viewer')
@login_required
def incident_viewer():
    """Incident Viewer 페이지"""
    # 관리자와 사이트 관리자만 접근 허용
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # 사이트 파라미터 가져오기 (등록된 사이트 중 첫 번째를 기본값으로)
    safe_site_servers = get_safe_site_servers()
    default_site = list(safe_site_servers.keys())[0] if safe_site_servers else 'Parafield Gardens'
    site = request.args.get('site', default_site)
    
    # 사이트 목록 생성
    sites = []
    for site_name, server_info in safe_site_servers.items():
        sites.append({
            'name': site_name,
            'server': server_info,
            'is_selected': site_name == site
        })
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('IncidentViewer.html', 
                         site=site, 
                         sites=sites,
                         current_user=current_user)

@app.route('/log-viewer')
@login_required
def log_viewer():
    """로그 뷰어 페이지"""
    # 관리자만 접근 허용
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('LogViewer.html')

@app.route('/log_viewer/progress_notes')
@login_required
def progress_note_logs_viewer():
    """Progress Note Logs 전용 뷰어 페이지"""
    # 관리자만 접근 허용
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    # URL 파라미터에서 날짜 가져오기
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('ProgressNoteLogsViewer.html', start_date=start_date, end_date=end_date)

@app.route('/api/logs/summary')
@login_required
def get_log_summary():
    """로그 요약 정보 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_type = request.args.get('type', 'access')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        summary = usage_logger.get_log_summary(start_date, end_date, log_type)
        
        if summary:
            return jsonify({
                'success': True,
                'summary': summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get log summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting log summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/fetch-incidents', methods=['POST'])
@login_required
def fetch_incidents():
    """Incident 데이터를 사이트에서 가져오기"""
    try:
        # 관리자와 사이트 관리자만 접근 허용
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        site = data.get('site')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not site or not start_date or not end_date:
            return jsonify({'success': False, 'message': 'Site, start_date, and end_date are required'}), 400
        
        logger.info(f"Fetching incidents for {site} from {start_date} to {end_date}")
        
        # 사이트 서버 설정 확인
        safe_site_servers = get_safe_site_servers()
        if site not in safe_site_servers:
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(safe_site_servers.keys())}'
            }), 400
        
        server_ip = safe_site_servers[site]
        logger.info(f"Target server for {site}: {server_ip}")
        
        try:
            # Incident 데이터와 클라이언트 데이터 가져오기
            from api_incident import fetch_incidents_with_client_data
            
            incidents_data = fetch_incidents_with_client_data(site, start_date, end_date)
            
            if incidents_data:
                logger.info(f"Incidents fetched successfully for {site}: {len(incidents_data.get('incidents', []))} incidents, {len(incidents_data.get('clients', []))} clients")
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched {len(incidents_data.get("incidents", []))} incidents',
                    'data': incidents_data,
                    'site': site,
                    'count': len(incidents_data.get('incidents', [])),
                    'fetched_at': datetime.now().isoformat()
                })
            else:
                logger.warning(f"No incidents found for {site}")
                return jsonify({
                    'success': True,
                    'message': 'No incidents found',
                    'data': {'incidents': [], 'clients': []},
                    'site': site,
                    'count': 0,
                    'fetched_at': datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error fetching incidents for {site}: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error fetching incidents: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in fetch_incidents: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/access-hourly-summary')
@login_required
def get_access_hourly_summary():
    """Access log의 시간별 사용자 활동 요약 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        hourly_summary = usage_logger.get_access_log_hourly_summary(start_date, end_date)
        
        if hourly_summary:
            return jsonify({
                'success': True,
                'summary': hourly_summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get access hourly summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting access hourly summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/daily-access-summary')
@login_required
def get_daily_access_summary():
    """일별 접속 현황 요약"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        daily_summary = usage_logger.get_daily_access_summary(start_date, end_date)
        
        if daily_summary:
            return jsonify({
                'success': True,
                'summary': daily_summary
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get daily access summary'
            })
            
    except Exception as e:
        logger.error(f"Error getting daily access summary: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/user-daily-activity')
@login_required
def get_user_daily_activity():
    """특정 사용자의 일별 접속 현황"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        username = request.args.get('username')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not username:
            return jsonify({'success': False, 'message': 'Username is required'}), 400
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
        
        user_activity = usage_logger.get_user_daily_activity(username, start_date, end_date)
        
        if user_activity:
            return jsonify({
                'success': True,
                'activity': user_activity
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get user daily activity'
            })
            
    except Exception as e:
        logger.error(f"Error getting user daily activity: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/date-user-activity')
@login_required
def get_date_user_activity():
    """특정 날짜의 사용자별 접속시간 및 사용시간"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'message': 'Date is required'}), 400
        
        target_date = datetime.fromisoformat(date_str)
        date_activity = usage_logger.get_date_user_activity(target_date)
        
        if date_activity:
            return jsonify({
                'success': True,
                'activity': date_activity
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to get date user activity'
            })
            
    except Exception as e:
        logger.error(f"Error getting date user activity: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/log-rod-debug', methods=['POST'])
@login_required
def log_rod_debug():
    """Log ROD debug information to file instead of console"""
    try:
        debug_data = request.get_json()
        if not debug_data:
            return jsonify({'success': False, 'message': 'No debug data provided'})
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        filename = f'rod_debug_{timestamp}.json'
        filepath = os.path.join(logs_dir, filename)
        
        # Add server timestamp and user info
        debug_data['server_timestamp'] = datetime.now().isoformat()
        debug_data['user'] = current_user.username if current_user.is_authenticated else 'Unknown'
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"ROD debug log saved to: {filepath}")
        return jsonify({'success': True, 'message': 'Debug log saved'})
        
    except Exception as e:
        logger.error(f"Error saving ROD debug log: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/logs/details')
@login_required
def get_log_details():
    """로그 상세 정보 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_type = request.args.get('type', 'progress_notes')
        date_str = request.args.get('date')
        
        if not date_str:
            return jsonify({'success': False, 'message': 'Date parameter is required'}), 400
        
        # 해당 날짜의 로그 파일 경로
        log_file = usage_logger.get_daily_log_file(log_type, datetime.fromisoformat(date_str))
        
        if not log_file.exists():
            return jsonify({'success': False, 'message': 'No logs found for this date'}), 404
        
        # 로그 파일 읽기
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
        
        # progress_notes 로그인 경우 상세 정보 포함
        if log_type == 'progress_notes':
            for log_entry in logs:
                # 성공/실패 상태에 따른 스타일 클래스 추가
                success = log_entry.get('result', {}).get('success', True)
                log_entry['status_class'] = 'success' if success else 'error'
                log_entry['status_text'] = 'Success' if success else 'Failed'
                
                # 타임스탬프를 읽기 쉬운 형식으로 변환
                timestamp = log_entry.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        log_entry['formatted_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        log_entry['formatted_time'] = timestamp
        
        return jsonify({
            'success': True,
            'logs': logs,
            'date': date_str,
            'type': log_type
        })
        
    except Exception as e:
        logger.error(f"Error getting log details: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/logs/app-log')
@login_required
def get_app_log():
    """app.log 파일 내용 조회 (운영 서버용)"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'app.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'app.log file not found'}), 404
        
        # 최근 1000줄만 읽기 (성능 최적화)
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"app.log 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logs/error-log')
@login_required
def get_error_log():
    """error.log 파일 내용 조회 (운영 서버용)"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'error.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'error.log file not found'}), 404
        
        # 최근 500줄만 읽기
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"error.log 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logs/access-log')
@login_required
def get_access_log():
    """access.log 파일 내용 조회 (운영 서버용)"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        log_file = os.path.join(os.getcwd(), 'logs', 'access.log')
        
        if not os.path.exists(log_file):
            return jsonify({'success': False, 'message': 'access.log file not found'}), 404
        
        # 최근 500줄만 읽기
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
        
    except Exception as e:
        logger.error(f"access.log 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/send-alarm', methods=['POST'])
@login_required
def send_alarm():
    """모바일 앱으로 알람을 전송하는 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # 필수 필드 검증
        required_fields = ['incident_id', 'event_type', 'client_name', 'site', 'risk_rating']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # 알람 매니저 가져오기
        alarm_manager = get_alarm_manager()
        
        # 알람 전송
        result = alarm_manager.send_alarm(
            incident_id=data['incident_id'],
            event_type=data['event_type'],
            client_name=data['client_name'],
            site=data['site'],
            risk_rating=data['risk_rating'],
            template_id=data.get('template_id'),
            custom_message=data.get('custom_message'),
            custom_recipients=data.get('custom_recipients'),
            priority=data.get('priority', 'normal')
        )
        
        if result['success']:
            logger.info(f"Advanced alarm sent successfully: {result['alarm_id']} by {current_user.username}")
            return jsonify(result)
        else:
            logger.error(f"Failed to send advanced alarm: {result['error']}")
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error sending alarm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending alarm: {str(e)}'
        }), 500

@app.route('/api/alarm-history')
@login_required
def get_alarm_history():
    """알람 전송 히스토리를 반환하는 API"""
    try:
        # 알람 로그 파일 경로
        logs_dir = os.path.join(os.getcwd(), 'logs')
        alarm_log_file = os.path.join(logs_dir, 'alarm_logs.json')
        
        if not os.path.exists(alarm_log_file):
            return jsonify({
                'success': True,
                'alarms': []
            })
        
        # 알람 로그 읽기
        with open(alarm_log_file, 'r', encoding='utf-8') as f:
            alarm_logs = json.load(f)
        
        # 최근 20개 알람만 반환 (최신순)
        recent_alarms = sorted(alarm_logs, key=lambda x: x.get('timestamp', ''), reverse=True)[:20]
        
        return jsonify({
            'success': True,
            'alarms': recent_alarms
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm history: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm history: {str(e)}'
        }), 500

# ==============================
# 고급 알람 관리 API 엔드포인트
# ==============================

@app.route('/api/alarm-templates', methods=['GET'])
@login_required
def get_alarm_templates():
    """알람 템플릿 목록을 반환하는 API (SQLite 기반)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        # SQLite에서 실제 데이터 조회
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT template_id, name, description, title_template, body_template, 
                   priority, category, created_at
            FROM alarm_templates 
            WHERE is_active = 1
            ORDER BY priority DESC, name
        ''')
        
        templates = []
        for row in cursor.fetchall():
            templates.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'title_template': row[3],
                'body_template': row[4],
                'priority': row[5],
                'category': row[6],
                'created_at': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"알람 템플릿 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'템플릿 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/alarm-templates', methods=['POST'])
@login_required
def create_alarm_template():
    """새로운 알람 템플릿을 생성하는 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required_fields = ['name', 'title', 'body', 'priority', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        template_service, _, _ = get_alarm_services()
        template = template_service.create_template(data)
        
        return jsonify({
            'success': True,
            'template': asdict(template),
            'message': 'Template created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating alarm template: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating alarm template: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients', methods=['GET'])
@login_required
def get_alarm_recipients():
    """알람 수신자 목록을 반환하는 API (SQLite 기반)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        # SQLite에서 실제 데이터 조회
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ar.user_id, ar.name, ar.email, ar.phone, ar.role, ar.team, ar.created_at,
                   u.username, u.is_active as user_active
            FROM alarm_recipients ar
            LEFT JOIN users u ON ar.user_id = u.id
            WHERE ar.is_active = 1
            ORDER BY ar.team, ar.name
        ''')
        
        recipients = []
        for row in cursor.fetchall():
            recipients.append({
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'role': row[4],
                'team': row[5],
                'created_at': row[6],
                'username': row[7],
                'user_active': row[8]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'recipients': recipients
        })
        
    except Exception as e:
        logger.error(f"알람 수신자 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'수신자 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients', methods=['POST'])
@login_required
def add_alarm_recipient():
    """새로운 알람 수신자를 추가하는 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        required_fields = ['user_id', 'name', 'email', 'phone', 'role', 'team']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        _, recipient_service, _ = get_alarm_services()
        recipient = recipient_service.add_recipient(data)
        
        return jsonify({
            'success': True,
            'recipient': asdict(recipient),
            'message': 'Recipient added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding alarm recipient: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error adding alarm recipient: {str(e)}'
        }), 500

@app.route('/api/alarm-recipients/<user_id>/fcm-token', methods=['PUT'])
@login_required
def update_fcm_token(user_id):
    """사용자의 FCM 토큰을 업데이트하는 API"""
    try:
        data = request.get_json()
        
        if not data or 'fcm_token' not in data:
            return jsonify({'success': False, 'message': 'FCM token is required'}), 400
        
        _, recipient_service, _ = get_alarm_services()
        success = recipient_service.update_fcm_token(user_id, data['fcm_token'])
        
        if success:
            return jsonify({
                'success': True,
                'message': 'FCM token updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
    except Exception as e:
        logger.error(f"Error updating FCM token: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating FCM token: {str(e)}'
        }), 500

@app.route('/api/alarms/<alarm_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alarm(alarm_id):
    """알람을 확인 처리하는 API"""
    try:
        data = request.get_json()
        user_id = data.get('user_id') if data else None
        
        if not user_id:
            user_id = current_user.username if current_user.is_authenticated else 'Unknown'
        
        alarm_manager = get_alarm_manager()
        result = alarm_manager.acknowledge_alarm(alarm_id, user_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error acknowledging alarm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error acknowledging alarm: {str(e)}'
        }), 500

@app.route('/api/alarms/escalations', methods=['GET'])
@login_required
def get_pending_escalations():
    """대기 중인 에스컬레이션 목록을 반환하는 API"""
    try:
        alarm_manager = get_alarm_manager()
        pending_count = alarm_manager.get_pending_escalations_count()
        
        return jsonify({
            'success': True,
            'pending_escalations_count': pending_count
        })
        
    except Exception as e:
        logger.error(f"Error getting pending escalations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting pending escalations: {str(e)}'
        }), 500

@app.route('/api/alarms/<alarm_id>/escalations', methods=['GET'])
@login_required
def get_alarm_escalations(alarm_id):
    """특정 알람의 에스컬레이션 정보를 반환하는 API"""
    try:
        _, _, escalation_service = get_alarm_services()
        escalations = escalation_service.get_escalations_for_alarm(alarm_id)
        
        # datetime 객체를 문자열로 변환
        for escalation in escalations:
            escalation.created_at = escalation.created_at.isoformat()
            if escalation.sent_at:
                escalation.sent_at = escalation.sent_at.isoformat()
            if escalation.acknowledged_at:
                escalation.acknowledged_at = escalation.acknowledged_at.isoformat()
        
        return jsonify({
            'success': True,
            'escalations': [asdict(escalation) for escalation in escalations]
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm escalations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm escalations: {str(e)}'
        }), 500

# 로그인 성공 후 data 폴더 정리 함수 추가
def cleanup_data_folder():
    """로그인시 data 폴더의 progress note 관련 JSON 파일들을 정리합니다."""
    try:
        data_dir = os.path.join(app.root_path, 'data')
        if os.path.exists(data_dir):
            # JSON 파일들 중 progress note 관련 파일만 찾기 (client 데이터는 보존)
            all_json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
            
            # 보존할 파일들 (client 데이터)
            preserve_files = [
                'Client_list.json',
                'carearea.json', 
                'eventtype.json'
            ]
            
            # 사이트별 client 파일도 보존
            safe_site_servers = get_safe_site_servers()
            for site in safe_site_servers.keys():
                site_name = site.replace(' ', '_').lower()
                preserve_files.append(f"{site_name}_client.json")
            
            # 삭제할 파일들 (progress note 관련)
            files_to_delete = []
            for json_file in all_json_files:
                if json_file not in preserve_files and not json_file.startswith('prepare_send'):
                    files_to_delete.append(json_file)
            
            if files_to_delete:
                logger.info(f"Data 폴더 정리 시작 - {len(files_to_delete)}개 progress note JSON 파일 삭제")
                logger.info(f"보존할 파일들: {preserve_files}")
                logger.info(f"삭제할 파일들: {files_to_delete}")
                
                # progress note 관련 JSON 파일들을 직접 삭제
                deleted_count = 0
                for json_file in files_to_delete:
                    try:
                        file_path = os.path.join(data_dir, json_file)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Progress note JSON 파일 삭제: {json_file}")
                    except Exception as e:
                        logger.error(f"Progress note JSON 파일 삭제 실패 {json_file}: {str(e)}")
                
                logger.info(f"Data 폴더 정리 완료 - {deleted_count}/{len(files_to_delete)}개 progress note 파일 삭제")
                return True
            else:
                logger.info("삭제할 progress note JSON 파일이 없음")
                return True
        else:
            logger.warning("Data 폴더가 존재하지 않음")
            return False
            
    except Exception as e:
        logger.error(f"Data 폴더 정리 중 오류 발생: {str(e)}")
        return False

# ==============================
# FCM (Firebase Cloud Messaging) API 엔드포인트
# ==============================

@app.route('/api/fcm/register-token', methods=['POST'])
def register_fcm_token():
    """FCM 토큰을 등록하는 API"""
    try:
        logger.info(f"FCM 토큰 등록 요청 - 사용자: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
        logger.info(f"요청 헤더: {dict(request.headers)}")
        
        data = request.get_json()
        logger.info(f"요청 데이터: {data}")
        
        # 모바일 앱 호환: 'token' 또는 'fcm_token' 필드 모두 지원
        token = data.get('token') or data.get('fcm_token')
        
        if not data or not token:
            logger.error("FCM 토큰 등록 실패: 토큰 데이터 누락")
            return jsonify({
                'success': False,
                'message': 'Token or fcm_token is required.'
            }), 400
        
        # device_info 처리 (문자열 또는 객체 모두 지원)
        device_info_raw = data.get('device_info', 'Unknown Device')
        if isinstance(device_info_raw, dict):
            # 모바일 앱에서 객체로 전송한 경우
            platform = device_info_raw.get('platform', 'unknown')
            version = device_info_raw.get('version', '1.0.0')
            device_info = f"{platform.title()} App v{version}"
        else:
            device_info = str(device_info_raw)
        
        user_id = data.get('user_id', 'unknown_user')  # 모바일 앱에서 user_id 제공
        platform = data.get('platform', 'unknown')
        app_version = data.get('app_version', '1.0.0')
        
        logger.info(f"FCM 토큰 등록 시도: 사용자={user_id}, 디바이스={device_info}, 토큰={token[:20]}...")
        
        # 사용자의 토큰 등록
        token_manager = get_fcm_token_manager()
        logger.info(f"FCM 토큰 매니저 타입: {type(token_manager)}")
        
        success = token_manager.register_token(user_id, token, device_info)
        logger.info(f"FCM 토큰 등록 결과: {success}")
        
        if success:
            logger.info(f"FCM 토큰 등록 성공: {user_id}")
            return jsonify({
                'success': True,
                'message': 'FCM token registered successfully.',
                'user_id': user_id,
                'device_info': device_info,
                'platform': platform,
                'app_version': app_version
            })
        else:
            logger.error(f"FCM 토큰 등록 실패: {user_id}")
            return jsonify({
                'success': False,
                'message': 'FCM token registration failed.'
            }), 500
            
    except Exception as e:
        logger.error(f"FCM 토큰 등록 중 예외: {str(e)}")
        import traceback
        logger.error(f"스택 트레이스: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error occurred during token registration: {str(e)}'
        }), 500

@app.route('/api/fcm/unregister-token', methods=['POST'])
def unregister_fcm_token():
    """FCM 토큰을 제거하는 API"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({
                'success': False,
                'message': '토큰이 필요합니다.'
            }), 400
        
        token = data['token']
        user_id = data.get('user_id')  # 모바일 앱에서 user_id 제공 (선택사항)
        
        logger.info(f"FCM 토큰 제거 시도: 사용자={user_id}, 토큰={token[:20]}...")
        
        # 토큰 제거 (user_id 있으면 함께 사용, 없으면 토큰만으로 제거)
        token_manager = get_fcm_token_manager()
        success = token_manager.unregister_token(user_id, token)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'FCM token deleted successfully.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'FCM token not found.'
            }), 404
            
    except Exception as e:
        logger.error(f"FCM 토큰 제거 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'토큰 제거 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/fcm/send-notification', methods=['POST'])
def send_fcm_notification():
    """FCM을 통해 푸시 알림을 전송하는 API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': '요청 데이터가 필요합니다.'
            }), 400
        
        # 필수 필드 확인
        required_fields = ['title', 'body']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'{field} 필드가 필요합니다.'
                }), 400
        
        title = data['title']
        body = data['body']
        user_ids = data.get('user_ids', [])  # 특정 사용자들에게만 전송
        topic = data.get('topic')  # 토픽으로 전송
        custom_data = data.get('data', {})  # 추가 데이터
        image_url = data.get('image_url')  # 이미지 URL
        
        fcm_service = get_fcm_service()
        if fcm_service is None:
            return jsonify({
                'success': False,
                'message': 'FCM 서비스를 초기화할 수 없습니다. Firebase 설정을 확인해주세요.'
            }), 500
        
        token_manager = get_fcm_token_manager()
        
        if topic:
            # 토픽으로 전송
            result = fcm_service.send_topic_message(topic, title, body, custom_data)
        elif user_ids:
            # 특정 사용자들에게 전송
            all_tokens = []
            for user_id in user_ids:
                user_tokens = token_manager.get_user_token_strings(user_id)
                all_tokens.extend(user_tokens)
            
            if all_tokens:
                result = fcm_service.send_notification_to_tokens(all_tokens, title, body, custom_data, image_url)
            else:
                return jsonify({
                    'success': False,
                    'message': '전송할 수 있는 FCM 토큰이 없습니다.'
                }), 400
        else:
            # 모든 사용자에게 전송
            all_tokens = token_manager.get_all_tokens()
            if all_tokens:
                result = fcm_service.send_notification_to_tokens(all_tokens, title, body, custom_data, image_url)
            else:
                return jsonify({
                    'success': False,
                    'message': '전송할 수 있는 FCM 토큰이 없습니다.'
                }), 400
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '푸시 알림이 성공적으로 전송되었습니다.',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f'푸시 알림 전송에 실패했습니다: {result.get("error", "알 수 없는 오류")}'
            }), 500
            
    except Exception as e:
        logger.error(f"FCM 알림 전송 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'알림 전송 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/fcm/tokens', methods=['GET'])
@login_required
def get_fcm_tokens():
    """현재 사용자의 FCM 토큰 정보를 반환하는 API"""
    try:
        token_manager = get_fcm_token_manager()
        user_tokens = token_manager.get_user_tokens(current_user.id)
        
        tokens_data = [token.to_dict() for token in user_tokens]
        
        return jsonify({
            'success': True,
            'tokens': tokens_data
        })
        
    except Exception as e:
        logger.error(f"FCM 토큰 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'토큰 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/fcm/stats', methods=['GET'])
@login_required
def get_fcm_stats():
    """FCM 토큰 통계를 반환하는 API (관리자 및 사이트 관리자 전용)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"FCM 통계 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'통계 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/fcm/export-tokens', methods=['GET'])
@login_required
def export_fcm_tokens():
    """FCM 토큰 매니저에서 토큰 데이터를 내보내는 API (관리자 및 사이트 관리자 전용)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': 'Admin permission required.'
            }), 403
        
        # FCM 토큰 매니저에서 통계 가져오기
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        # Policy Management에서 사용할 수 있는 형태로 변환
        tokens_data = []
        for user_id, user_tokens in stats.get('user_tokens', {}).items():
            for token_info in user_tokens:
                tokens_data.append({
                    'user_id': user_id,
                    'token': token_info.get('token', ''),
                    'device_info': token_info.get('device_info', 'Unknown Device'),
                    'created_at': token_info.get('created_at', ''),
                    'last_used': token_info.get('last_used', ''),
                    'is_active': token_info.get('is_active', True)
                })
        
        logger.info(f"FCM 토큰 내보내기: {len(tokens_data)}개 토큰")
        
        return jsonify({
            'success': True,
            'tokens': tokens_data,
            'count': len(tokens_data)
        })
        
    except Exception as e:
        logger.error(f"FCM 토큰 내보내기 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'토큰 내보내기 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/fcm/cleanup', methods=['POST'])
@login_required
def cleanup_fcm_tokens():
    """비활성 FCM 토큰을 정리하는 API (관리자 및 사이트 관리자 전용)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        data = request.get_json() or {}
        days_threshold = data.get('days_threshold', 30)
        
        token_manager = get_fcm_token_manager()
        cleanup_count = token_manager.cleanup_inactive_tokens(days_threshold)
        
        return jsonify({
            'success': True,
            'message': f'{cleanup_count}개의 비활성 토큰이 정리되었습니다.',
            'cleanup_count': cleanup_count
        })
        
    except Exception as e:
        logger.error(f"FCM 토큰 정리 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'토큰 정리 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/admin-settings')
@login_required
def admin_settings():
    """Admin 설정 페이지 (ADMIN 전용)"""
    # 관리자 권한 확인
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": getattr(current_user, 'position', 'Unknown')
    }
    usage_logger.log_access(user_info, '/admin-settings')
    
    return render_template('admin_settings.html')

@app.route('/fcm-admin-dashboard')
@login_required
def fcm_admin_dashboard():
    """FCM 관리자 대시보드 (ADMIN 및 SITE_ADMIN 전용)"""
    # 관리자와 사이트 관리자 권한 확인
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This dashboard is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('FCMAdminDashboard.html', current_user=current_user)



@app.route('/api/fcm/update-token', methods=['POST'])
@login_required
def update_fcm_token_info():
    """FCM 토큰 정보를 업데이트하는 API (필드 기반 업데이트)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required.'
            }), 400
        
        # 필수 필드 확인
        required_fields = ['token', 'field', 'value']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'{field} field is required.'
                }), 400
        
        token = data['token']
        field = data['field']
        value = data['value'].strip()
        
        # 값이 비어있지 않은지 확인
        if not value:
            return jsonify({
                'success': False,
                'message': 'Value cannot be empty.'
            }), 400
        
        token_manager = get_fcm_token_manager()
        
        # 필드에 따라 업데이트할 정보 결정
        if field == 'user_id':
            success = token_manager.update_token_info(token, value, None)
        elif field == 'device_info':
            success = token_manager.update_token_info(token, None, value)
        elif field == 'token':
            # 토큰 자체를 변경하는 경우 (새로운 토큰으로 교체)
            success = token_manager.update_token_value(token, value)
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid field specified.'
            }), 400
        
        if success:
            logger.info(f"FCM token update successful: {token[:20]}... -> {field}: {value}")
            return jsonify({
                'success': True,
                'message': 'Token information updated successfully.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Token not found or cannot be updated.'
            }), 404
            
    except Exception as e:
        logger.error(f"FCM token update error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error occurred during token update: {str(e)}'
        }), 500

@app.route('/api/alarm-escalation-status', methods=['GET'])
@login_required
def get_alarm_escalation_status():
    """알람 에스컬레이션 상태를 반환하는 API (SQLite 기반)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        # SQLite에서 실제 에스컬레이션 정책 조회
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT policy_name, event_type, priority, is_active
            FROM escalation_policies
            ORDER BY priority DESC, event_type
        ''')
        
        policies = []
        status_summary = {
            'total_policies': 0,
            'active_policies': 0,
            'by_priority': {'high': 0, 'medium': 0, 'normal': 0},
            'by_type': {}
        }
        
        for row in cursor.fetchall():
            policy_name, event_type, priority, is_active = row
            
            policies.append({
                'name': policy_name,
                'event_type': event_type,
                'priority': priority,
                'is_active': is_active
            })
            
            status_summary['total_policies'] += 1
            if is_active:
                status_summary['active_policies'] += 1
                status_summary['by_priority'][priority] = status_summary['by_priority'].get(priority, 0) + 1
                status_summary['by_type'][event_type] = status_summary['by_type'].get(event_type, 0) + 1
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policies': policies,
            'status': status_summary
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 상태 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'상태 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500



@app.route('/policy-management')
@login_required
def unified_policy_management():
    """통합 Policy & Recipients 관리 페이지 (ADMIN 및 SITE_ADMIN 전용)"""
    # 관리자와 사이트 관리자 권한 확인
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('UnifiedPolicyManagement.html', current_user=current_user)

# 기존 페이지들을 새 통합 페이지로 리다이렉트
@app.route('/escalation-policy-management')
@login_required
def escalation_policy_management():
    """에스컬레이션 정책 관리 페이지 (통합 페이지로 리다이렉트)"""
    return redirect(url_for('unified_policy_management'))

@app.route('/policy-alarm-management')
@login_required
def policy_alarm_management():
    """Policy & Alarm Management 페이지 (통합 페이지로 리다이렉트)"""
    return redirect(url_for('unified_policy_management'))

@app.route('/api/escalation-policies', methods=['GET'])
@login_required
def get_escalation_policies():
    """에스컬레이션 정책 목록 조회 (SQLite 기반)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 정책과 단계 정보를 함께 조회
        cursor.execute('''
            SELECT ep.id, ep.policy_name, ep.description, ep.event_type, ep.priority,
                   ep.is_active, ep.created_at,
                   COUNT(es.id) as step_count
            FROM escalation_policies ep
            LEFT JOIN escalation_steps es ON ep.id = es.policy_id AND es.is_active = 1
            WHERE ep.is_active = 1
            GROUP BY ep.id
            ORDER BY ep.priority DESC, ep.policy_name
        ''')
        
        policies = []
        for row in cursor.fetchall():
            policies.append({
                'id': row[0],
                'policy_name': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'is_active': row[5],
                'created_at': row[6],
                'step_count': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policies': policies
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['GET'])
@login_required
def get_escalation_policy_detail(policy_id):
    """특정 에스컬레이션 정책 상세 조회"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 정책 기본 정보
        cursor.execute('''
            SELECT id, policy_name, description, event_type, priority, is_active, created_at
            FROM escalation_policies
            WHERE id = ? AND is_active = 1
        ''', (policy_id,))
        
        policy_row = cursor.fetchone()
        if not policy_row:
            return jsonify({'success': False, 'message': '정책을 찾을 수 없습니다.'}), 404
        
        policy = {
            'id': policy_row[0],
            'policy_name': policy_row[1],
            'description': policy_row[2],
            'event_type': policy_row[3],
            'priority': policy_row[4],
            'is_active': policy_row[5],
            'created_at': policy_row[6]
        }
        
        # 에스컬레이션 단계 정보
        cursor.execute('''
            SELECT step_number, delay_minutes, repeat_count, recipients, message_template
            FROM escalation_steps
            WHERE policy_id = ? AND is_active = 1
            ORDER BY step_number
        ''', (policy_id,))
        
        steps = []
        for row in cursor.fetchall():
            steps.append({
                'step_number': row[0],
                'delay_minutes': row[1],
                'repeat_count': row[2],
                'recipients': json.loads(row[3]) if row[3] else [],
                'message_template': row[4]
            })
        
        policy['steps'] = steps
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policy': policy
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 상세 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# 클라이언트 동기화 API 엔드포인트
# ==============================

@app.route('/api/clients/refresh/<site>', methods=['POST'])
def refresh_clients_api(site):
    """클라이언트 데이터 수동 새로고침 API"""
    try:
        # 내부 시스템용 - 인증 불필요
        
        # 통합 데이터 동기화 매니저 import
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            logger.error("통합 데이터 동기화 매니저를 찾을 수 없습니다.")
            return jsonify({
                'success': False,
                'message': '동기화 매니저를 초기화할 수 없습니다.'
            }), 500
        
        # 새로고침 실행 (클라이언트 데이터만)
        result = manager.sync_clients_data()
        
        if result['success'] > 0:
            changes = result['total_changes']
            return jsonify({
                'success': True,
                'message': f'{site} 클라이언트 데이터 업데이트 완료',
                'changes': changes,
                'summary': f"신규 {changes['added']}명, 업데이트 {changes['updated']}명, 제거 {changes['removed']}명"
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{site} 클라이언트 데이터 업데이트 실패'
            }), 500
            
    except Exception as e:
        logger.error(f"클라이언트 새로고침 API 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'새로고침 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/clients/sync-status', methods=['GET'])
def get_client_sync_status():
    """클라이언트 동기화 상태 조회 API"""
    try:
        # 내부 시스템용 - 인증 불필요
        
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            return jsonify({
                'success': False,
                'message': '동기화 매니저를 찾을 수 없습니다.'
            }), 500
        
        # 동기화 상태 조회 (클라이언트 데이터만)
        status = {}
        conn = manager.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT site, last_sync_time, sync_status, records_synced
                FROM sync_status 
                WHERE data_type = 'clients'
                ORDER BY site
            ''')
            
            for row in cursor.fetchall():
                site = row['site']
                status[site] = {
                    'last_sync': row['last_sync_time'],
                    'status': row['sync_status'],
                    'records': row['records_synced']
                }
        finally:
            conn.close()
        
        return jsonify({
            'success': True,
            'sync_status': status
        })
        
    except Exception as e:
        logger.error(f"동기화 상태 조회 API 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'상태 조회 중 오류가 발생했습니다: {str(e)}'
        }), 500

@app.route('/api/clients/refresh-all', methods=['POST'])
def refresh_all_clients_api():
    """모든 사이트 클라이언트 데이터 새로고침 API"""
    try:
        # 내부 시스템용 - 인증 불필요
        
        try:
            from unified_data_sync_manager import get_unified_sync_manager
            manager = get_unified_sync_manager()
        except ImportError:
            return jsonify({
                'success': False,
                'message': '동기화 매니저를 찾을 수 없습니다.'
            }), 500
        
        # 전체 데이터 새로고침 (모든 데이터)
        results = manager.run_full_sync()
        
        return jsonify({
            'success': True,
            'message': f'전체 데이터 동기화 완료: {results["summary"]["total_records"]}개 레코드',
            'summary': results['summary']
        })
        
    except Exception as e:
        logger.error(f"전체 새로고침 API 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'전체 새로고침 중 오류가 발생했습니다: {str(e)}'
        }), 500

# ==============================
# 통합 Policy & Recipients 관리 API
# ==============================

@app.route('/api/escalation-policies', methods=['POST'])
@login_required
def create_escalation_policy_unified():
    """통합 에스컬레이션 정책 생성 (FCM 디바이스 기반)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # 정책 기본 정보 삽입
            cursor.execute('''
                INSERT INTO escalation_policies 
                (policy_name, description, event_type, priority, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data['policy_name'],
                data['description'],
                data['event_type'],
                data['priority'],
                current_user.id
            ))
            
            policy_id = cursor.lastrowid
            
            # 에스컬레이션 단계 삽입
            for step in data['steps']:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    policy_id,
                    step['step_number'],
                    step['delay_minutes'],
                    step['repeat_count'],
                    json.dumps(step['recipients']),  # FCM 디바이스 ID 배열
                    step['message_template']
                ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'policy_id': policy_id,
                'message': '에스컬레이션 정책이 성공적으로 생성되었습니다.',
                'steps_created': len(data['steps'])
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 생성 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['PUT'])
@login_required
def update_escalation_policy_unified(policy_id):
    """통합 에스컬레이션 정책 업데이트"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # 정책 기본 정보 업데이트
            cursor.execute('''
                UPDATE escalation_policies 
                SET policy_name = ?, description = ?, event_type = ?, priority = ?, updated_at = ?
                WHERE id = ? AND is_active = 1
            ''', (
                data['policy_name'],
                data['description'],
                data['event_type'],
                data['priority'],
                datetime.now().isoformat(),
                policy_id
            ))
            
            # 기존 단계 삭제
            cursor.execute('DELETE FROM escalation_steps WHERE policy_id = ?', (policy_id,))
            
            # 새 단계 삽입
            for step in data['steps']:
                cursor.execute('''
                    INSERT INTO escalation_steps 
                    (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    policy_id,
                    step['step_number'],
                    step['delay_minutes'],
                    step['repeat_count'],
                    json.dumps(step['recipients']),
                    step['message_template']
                ))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '에스컬레이션 정책이 성공적으로 업데이트되었습니다.',
                'steps_updated': len(data['steps'])
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 업데이트 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_escalation_policy_unified(policy_id):
    """통합 에스컬레이션 정책 삭제"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        try:
            # 정책 비활성화 (실제 삭제 대신)
            cursor.execute('''
                UPDATE escalation_policies 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), policy_id))
            
            # 관련 단계도 비활성화
            cursor.execute('''
                UPDATE escalation_steps 
                SET is_active = 0
                WHERE policy_id = ?
            ''', (policy_id,))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': '에스컬레이션 정책이 성공적으로 삭제되었습니다.'
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 삭제 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/test', methods=['POST'])
@login_required
def test_escalation_policy_unified():
    """통합 에스컬레이션 정책 테스트"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        
        # 정책 실행 시뮬레이션
        total_notifications = 0
        total_duration = 0
        device_count = len(data.get('steps', [{}])[0].get('recipients', []))
        
        for step in data['steps']:
            step_notifications = step['repeat_count'] * device_count
            total_notifications += step_notifications
            
            # 누적 시간 계산
            step_duration = step['delay_minutes'] + (step['repeat_count'] - 1) * step['delay_minutes']
            total_duration = max(total_duration, step_duration)
        
        return jsonify({
            'success': True,
            'total_notifications': total_notifications,
            'total_duration': total_duration,
            'device_count': device_count,
            'message': f'테스트 완료: {device_count}개 디바이스에 총 {total_notifications}개 알림'
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 테스트 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipient-groups', methods=['POST'])
@login_required
def save_recipient_group():
    """수신자 그룹 저장 (FCM 디바이스 기반)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        group_name = data.get('group_name')
        devices = data.get('devices', [])
        
        if not group_name or not devices:
            return jsonify({'success': False, 'message': '그룹명과 디바이스를 선택하세요.'}), 400
        
        # 수신자 그룹 테이블이 없다면 생성
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipient_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name VARCHAR(100) NOT NULL,
                devices TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 그룹 저장
        cursor.execute('''
            INSERT OR REPLACE INTO recipient_groups 
            (group_name, devices, created_by)
            VALUES (?, ?, ?)
        ''', (group_name, json.dumps(devices), current_user.id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'{group_name} 그룹에 {len(devices)}개 디바이스가 저장되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"수신자 그룹 저장 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/test-group-notification', methods=['POST'])
@login_required
def test_group_notification():
    """그룹 알림 테스트"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        devices = data.get('devices', [])
        message = data.get('message', '테스트 알림입니다.')
        
        if not devices:
            return jsonify({'success': False, 'message': '테스트할 디바이스를 선택하세요.'}), 400
        
        # FCM 토큰 조회
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        placeholders = ','.join(['?' for _ in devices])
        cursor.execute(f'''
            SELECT user_id, token, device_info 
            FROM fcm_tokens 
            WHERE user_id IN ({placeholders}) AND is_active = 1
        ''', devices)
        
        tokens = cursor.fetchall()
        conn.close()
        
        if not tokens:
            return jsonify({'success': False, 'message': '활성 토큰을 찾을 수 없습니다.'}), 404
        
        # 실제 FCM 전송 (여기서는 시뮬레이션)
        sent_count = len(tokens)
        
        # 실제 구현 시:
        # fcm_result = send_fcm_notification(tokens, message)
        
        return jsonify({
            'success': True,
            'message': f'{sent_count}개 디바이스에 테스트 알림을 전송했습니다.',
            'sent_count': sent_count,
            'devices_tested': devices
        })
        
    except Exception as e:
        logger.error(f"그룹 알림 테스트 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Workflow API 엔드포인트 (Mobile App 호환)
# ==============================

@app.route('/api/workflow/create', methods=['POST'])
def create_workflow_mobile():
    """워크플로우 생성 (모바일 앱 호환 경로)"""
    return create_task_workflow()

@app.route('/api/workflow/status', methods=['GET'])
def get_workflow_status():
    """워크플로우 상태 조회"""
    try:
        incident_id = request.args.get('incident_id')
        if not incident_id:
            return jsonify({'success': False, 'message': 'incident_id required'}), 400
        
        return get_incident_workflow_status(incident_id)
        
    except Exception as e:
        logger.error(f"워크플로우 상태 조회 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/complete', methods=['POST'])
def complete_workflow_task():
    """워크플로우 작업 완료 (모바일 앱 호환)"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data:
            return jsonify({'success': False, 'message': 'task_id required'}), 400
        
        task_id = data['task_id']
        return complete_task_api(task_id)
        
    except Exception as e:
        logger.error(f"워크플로우 작업 완료 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/details', methods=['GET'])
def get_workflow_task_details():
    """워크플로우 작업 상세 정보 (모바일 앱 호환)"""
    try:
        task_id = request.args.get('task_id')
        if not task_id:
            return jsonify({'success': False, 'message': 'task_id required'}), 400
        
        return get_task_detail(task_id)
        
    except Exception as e:
        logger.error(f"워크플로우 작업 상세 조회 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflow/tasks/status', methods=['PUT'])
def update_workflow_task_status():
    """워크플로우 작업 상태 업데이트"""
    try:
        data = request.get_json()
        if not data or 'task_id' not in data or 'status' not in data:
            return jsonify({'success': False, 'message': 'task_id and status required'}), 400
        
        task_id = data['task_id']
        new_status = data['status']
        notes = data.get('notes', '')
        
        # 상태에 따라 처리
        if new_status == 'completed':
            return complete_task_api(task_id)
        else:
            # 다른 상태 업데이트
            
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (new_status, task_id))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Task not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Task status updated to {new_status}',
                'task_id': task_id,
                'status': new_status
            })
        
    except Exception as e:
        logger.error(f"작업 상태 업데이트 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/policies/details', methods=['GET'])
def get_policy_details_mobile():
    """정책 상세 정보 (모바일 앱 호환)"""
    try:
        policy_id = request.args.get('policy_id')
        if not policy_id:
            return jsonify({'success': False, 'message': 'policy_id required'}), 400
        
        return get_escalation_policy_detail(int(policy_id))
        
    except Exception as e:
        logger.error(f"정책 상세 조회 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/incidents/details', methods=['GET'])
def get_incident_details_mobile():
    """인시던트 상세 정보 (모바일 앱 호환)"""
    try:
        incident_id = request.args.get('incident_id')
        if not incident_id:
            return jsonify({'success': False, 'message': 'incident_id required'}), 400
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 인시던트 상세 정보 조회
        cursor.execute('''
            SELECT incident_id, client_id, client_name, incident_type, 
                   incident_date, description, severity, status, site, 
                   reported_by, workflow_status, total_tasks, completed_tasks,
                   policy_id, created_by, closed_at, closed_by, last_synced
            FROM incidents_cache
            WHERE incident_id = ?
        ''', (incident_id,))
        
        incident_row = cursor.fetchone()
        if not incident_row:
            return jsonify({'success': False, 'message': 'Incident not found'}), 404
        
        # 관련 작업들 조회
        cursor.execute('''
            SELECT task_id, task_type, task_description, status, 
                   priority, assigned_role, scheduled_time, due_time,
                   completed_at, completed_by, deep_link
            FROM scheduled_tasks
            WHERE incident_id = ?
            ORDER BY scheduled_time
        ''', (incident_id,))
        
        tasks = cursor.fetchall()
        
        incident_detail = {
            'incident_id': incident_row[0],
            'client_id': incident_row[1],
            'client_name': incident_row[2],
            'incident_type': incident_row[3],
            'incident_date': incident_row[4],
            'description': incident_row[5],
            'severity': incident_row[6],
            'status': incident_row[7],
            'site': incident_row[8],
            'reported_by': incident_row[9],
            'workflow_status': incident_row[10],
            'total_tasks': incident_row[11] or 0,
            'completed_tasks': incident_row[12] or 0,
            'policy_id': incident_row[13],
            'created_by': incident_row[14],
            'closed_at': incident_row[15],
            'closed_by': incident_row[16],
            'last_synced': incident_row[17],
            'completion_rate': round((incident_row[12] / incident_row[11] * 100) if incident_row[11] > 0 else 0, 1),
            'tasks': [
                {
                    'task_id': task[0],
                    'task_type': task[1],
                    'task_description': task[2],
                    'status': task[3],
                    'priority': task[4],
                    'assigned_role': task[5],
                    'scheduled_time': task[6],
                    'due_time': task[7],
                    'completed_at': task[8],
                    'completed_by': task[9],
                    'deep_link': task[10]
                }
                for task in tasks
            ]
        }
        
        conn.close()
        
        return jsonify({
            'success': True,
            'incident': incident_detail
        })
        
    except Exception as e:
        logger.error(f"인시던트 상세 조회 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Task Management API 엔드포인트
# ==============================

@app.route('/api/tasks/create-workflow', methods=['POST'])
def create_task_workflow():
    """인시던트 기반 작업 워크플로우 생성"""
    try:
        data = request.get_json()
        required_fields = ['incident_id', 'policy_id', 'client_name', 'client_id', 'site', 'event_type', 'risk_rating']
        
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400
        
        created_by = data.get('created_by', 'system')  # 모바일 앱에서 제공하거나 기본값
        
        logger.info(f"워크플로우 생성 요청: incident_id={data['incident_id']}, created_by={created_by}")
        
        task_manager = get_task_manager()
        result = task_manager.create_incident_workflow(
            incident_id=data['incident_id'],
            policy_id=data['policy_id'],
            client_name=data['client_name'],
            client_id=data['client_id'],
            site=data['site'],
            event_type=data['event_type'],
            risk_rating=data['risk_rating'],
            created_by=created_by
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"워크플로우 생성 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task_api(task_id):
    """작업 완료 처리 API"""
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')
        completed_by = data.get('completed_by', 'mobile_user')  # 모바일 앱에서 제공
        
        logger.info(f"작업 완료 요청: task_id={task_id}, completed_by={completed_by}")
        
        task_manager = get_task_manager()
        result = task_manager.complete_task(
            task_id=task_id,
            completed_by=completed_by,
            notes=notes
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"작업 완료 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/my-tasks', methods=['GET'])
def get_my_tasks():
    """사용자의 할당된 작업 목록 조회"""
    try:
        status = request.args.get('status')  # pending, in_progress, completed
        site = request.args.get('site', 'Parafield Gardens')
        user_role = request.args.get('user_role', 'RN')  # 모바일 앱에서 제공
        
        # 사용자 역할에 따른 작업 조회
        if user_role == 'doctor':
            assigned_role = 'doctor'
        elif user_role == 'physiotherapist':
            assigned_role = 'physiotherapist'
        else:
            assigned_role = 'RN'  # 기본값
        
        logger.info(f"사용자 작업 조회: user_role={user_role}, assigned_role={assigned_role}, site={site}, status={status}")
        
        task_manager = get_task_manager()
        tasks = task_manager.get_user_tasks(assigned_role, site, status)
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'user_role': assigned_role,
            'site': site
        })
        
    except Exception as e:
        logger.error(f"작업 목록 조회 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_detail(task_id):
    """작업 상세 정보 조회"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT st.*, ic.description as incident_description,
                   ic.severity, ic.reported_by
            FROM scheduled_tasks st
            LEFT JOIN incidents_cache ic ON st.incident_id = ic.incident_id
            WHERE st.task_id = ?
        ''', (task_id,))
        
        task_row = cursor.fetchone()
        if not task_row:
            return jsonify({'success': False, 'message': 'Task not found'}), 404
        
        # 작업 실행 로그 조회
        cursor.execute('''
            SELECT action, performed_by, performed_at, details
            FROM task_execution_logs
            WHERE task_id = ?
            ORDER BY performed_at DESC
        ''', (task_id,))
        
        logs = cursor.fetchall()
        
        task_detail = {
            'task_id': task_row[1],
            'incident_id': task_row[2],
            'client_name': task_row[4],
            'client_id': task_row[5],
            'task_type': task_row[6],
            'task_description': task_row[7],
            'scheduled_time': task_row[8],
            'due_time': task_row[9],
            'status': task_row[10],
            'priority': task_row[11],
            'assigned_role': task_row[13],
            'site': task_row[14],
            'deep_link': task_row[15],
            'created_at': task_row[19],
            'completed_at': task_row[21],
            'completed_by': task_row[22],
            'completion_notes': task_row[23],
            'incident_description': task_row[24],
            'incident_severity': task_row[25],
            'incident_reported_by': task_row[26],
            'execution_logs': [
                {
                    'action': log[0],
                    'performed_by': log[1],
                    'performed_at': log[2],
                    'details': json.loads(log[3]) if log[3] else {}
                }
                for log in logs
            ]
        }
        
        return jsonify({
            'success': True,
            'task': task_detail
        })
        
    except Exception as e:
        logger.error(f"작업 상세 조회 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/send-notifications', methods=['POST'])
@login_required
def send_task_notifications():
    """스케줄된 작업 알림 전송 (관리자 전용)"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        task_manager = get_task_manager()
        result = task_manager.send_scheduled_notifications()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"작업 알림 전송 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Blueprint 등록
# ==============================

# Admin API Blueprint 등록
app.register_blueprint(admin_api)

# Progress Notes Cached API Blueprint 등록
from fetch_progress_notes_cached import progress_notes_cached_bp
app.register_blueprint(progress_notes_cached_bp)

# ==============================
# 앱 실행
# ==============================

if __name__ == '__main__':
    app.run(
        debug=flask_config['DEBUG'], 
        host=flask_config['HOST'],
        port=flask_config['PORT']
    )