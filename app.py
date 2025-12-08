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
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
import time
import threading
import schedule
from dotenv import load_dotenv
import uuid
from dataclasses import asdict

# .env 파일에서 환경변수 로딩
load_dotenv()

# 호주 동부 표준시 (AEST, UTC+10) 헬퍼 함수
def get_australian_time():
    """호주 동부 표준시 반환"""
    aest = timezone(timedelta(hours=10))
    return datetime.now(aest)

# 내부 모듈 임포트
from api_client import APIClient
from api_carearea import APICareArea
from api_eventtype import APIEventType
from config import SITE_SERVERS, API_HEADERS, get_available_sites
from config_users import authenticate_user, get_user
from config_env import get_flask_config, print_current_config, get_cache_policy
from models import load_user, User
from usage_logger import usage_logger
from admin_api import admin_api
from alarm_manager import get_alarm_manager
from alarm_service import get_alarm_services
from fcm_service import get_fcm_service
from fcm_token_manager import get_fcm_token_manager

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
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
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

# Note: Policy Scheduler와 Unified Data Sync Manager는 JSON 기반 시스템용이므로
# CIMS (DB 기반) 시스템에서는 사용하지 않습니다.
# - Policy Scheduler → CIMS Policy Engine으로 대체
# - Unified Data Sync → CIMS 증분 동기화 + 클라이언트 캐싱으로 대체

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
    """Event Type 정보를 가져오고 처리 (ROD 대시보드용 활성화)"""
    try:
        from api_eventtype import APIEventType
        logger.info(f"Event Type 정보 조회 시작 - 사이트: {site}")
        
        api_eventtype = APIEventType(site)
        event_type_data = api_eventtype.get_event_type_information()
        
        if event_type_data:
            # Event Type 데이터가 리스트 형태로 직접 반환됨
            if isinstance(event_type_data, list):
                logger.info(f"Event Type 정보 조회 성공 - 사이트: {site}, {len(event_type_data)}개")
                return True, event_type_data
            elif isinstance(event_type_data, dict) and 'data' in event_type_data:
                logger.info(f"Event Type 정보 조회 성공 - 사이트: {site}, {len(event_type_data['data'])}개")
                return True, event_type_data['data']
            else:
                logger.warning(f"Event Type 데이터 구조 예상과 다름 - 사이트: {site}, 타입: {type(event_type_data)}")
                return False, None
        else:
            logger.warning(f"Event Type 정보 조회 실패 - 사이트: {site}")
            return False, None
            
    except Exception as e:
        logger.error(f"Event Type 정보 조회 중 오류 - 사이트: {site}, 오류: {e}")
        return False, None

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
            progress_note["EventDate"] = get_australian_time().isoformat()
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
            'timestamp': get_australian_time().isoformat(),
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

        
        logger.info(f"debug_info: {debug_info}")
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
            'timestamp': get_australian_time().isoformat()
        }), 500

@app.route('/api/logs')
def get_logs():
    """로그 파일 목록 및 내용 조회 API"""
    try:
        log_files = []
        
        # 1. 일반 로그 파일 (logs 디렉토리) - 의미없는 로그 파일 제외
        log_dir = "logs"
        excluded_files = ['test.log', 'app.log', 'usage_system.log']
        
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.endswith('.log') and filename not in excluded_files:
                    filepath = os.path.join(log_dir, filename)
                    stat = os.stat(filepath)
                    log_files.append({
                        'name': filename,
                        'type': 'system',
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'path': filepath
                    })
        
        # 2. Usage 로그 파일 (UsageLog 디렉토리)
        usage_log_dir = "UsageLog"
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        stat = os.stat(filepath)
                        # 상대 경로로 표시 (Windows 경로 구분자를 슬래시로 통일)
                        rel_path = os.path.relpath(filepath, usage_log_dir).replace('\\', '/')
                        log_files.append({
                            'name': f"UsageLog/{rel_path}",
                            'type': 'usage',
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'path': filepath
                        })
        
        return jsonify({
            'log_files': sorted(log_files, key=lambda x: x['modified'], reverse=True),
            'timestamp': get_australian_time().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f"로그 조회 실패: {str(e)}"}), 500

@app.route('/api/logs/<path:filename>')
def get_log_content(filename):
    """특정 로그 파일 내용 조회"""
    try:
        # 보안: 파일명에 경로 조작 방지
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'error': '잘못된 파일명'}), 400
        
        # UsageLog 파일인지 확인
        if filename.startswith('UsageLog/'):
            # Windows 경로 구분자를 실제 경로로 변환
            filepath = filename.replace('/', os.sep)
        else:
            filepath = os.path.join("logs", filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': '파일을 찾을 수 없습니다'}), 404
        
        # JSON 파일인지 확인
        if filename.endswith('.json'):
            # JSON 파일인 경우 파싱하여 보기 좋게 표시
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # JSON을 보기 좋게 포맷팅
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            content_lines = formatted_json.split('\n')
            
            # 마지막 N줄 읽기
            lines = request.args.get('lines', 100, type=int)
            lines = min(lines, 1000)  # 최대 1000줄로 제한
            
            if len(content_lines) > lines:
                content_lines = content_lines[-lines:]
            
            return jsonify({
                'filename': filename,
                'type': 'json',
                'lines': len(content_lines),
                'total_lines': len(formatted_json.split('\n')),
                'content': content_lines,
                'timestamp': get_australian_time().isoformat()
            })
        else:
            # 일반 로그 파일인 경우
            lines = request.args.get('lines', 100, type=int)
            lines = min(lines, 1000)  # 최대 1000줄로 제한
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                content_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return jsonify({
                'filename': filename,
                'type': 'text',
                'lines': len(content_lines),
                'total_lines': len(all_lines),
                'content': [line.rstrip() for line in content_lines],
                'timestamp': get_australian_time().isoformat()
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
        
        # Task Manager 상태 확인 - JSON 전용 시스템으로 변경되어 비활성화
        # task_manager = get_task_manager()
        task_manager_status = False  # 비활성화됨
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': get_australian_time().isoformat(),
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
            'timestamp': get_australian_time().isoformat(),
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
        site = session.get('site', 'Parafield Gardens')
        
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
        elif username_upper == 'YKROD':
            logger.info(f"YKROD 사용자 감지 - Yankalilla ROD 대시보드로 리다이렉트")
            return redirect(url_for('rod_dashboard', site='Yankalilla'))
        elif username_upper == 'PGROD':
            logger.info(f"PGROD 사용자 감지 - 다중 사이트 접근 가능, Parafield Gardens로 기본 리다이렉트")
            session['site'] = 'Parafield Gardens'
            session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
            return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
        elif username_upper == 'WPROD':
            logger.info(f"WPROD 사용자 감지 - West Park ROD 대시보드로 리다이렉트")
            return redirect(url_for('rod_dashboard', site='West Park'))
        elif username_upper == 'RSROD':
            logger.info(f"RSROD 사용자 감지 - 다중 사이트 접근 가능, Ramsay로 기본 리다이렉트")
            session['site'] = 'Ramsay'
            session['allowed_sites'] = ['Ramsay', 'Nerrilda']
            return redirect(url_for('rod_dashboard', site='Ramsay'))
        elif username_upper == 'NROD':
            logger.info(f"NROD 사용자 감지 - Nerrilda ROD 대시보드로 리다이렉트")
            return redirect(url_for('rod_dashboard', site='Nerrilda'))
        
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
                logger.info(f"로그인 시 사이트별 데이터 자동 수집 - 사이트: {site}")
                
                # 3. 사이트별 데이터 자동 수집
                try:
                    # 3-1. 클라이언트 데이터 수집 (매번)
                    from api_client import fetch_client_information
                    client_success, client_info = fetch_client_information(site)
                    if client_success:
                        logger.info(f"클라이언트 데이터 수집 성공 - {site}: {len(client_info)}명")
                    else:
                        logger.warning(f"클라이언트 데이터 수집 실패 - {site}")
                    
                    # 3-2. Progress Notes 데이터 수집 (DB 직접 접속 모드에서는 캐시 불필요)
                    # DB 직접 접속 모드 확인
                    import sqlite3
                    import os
                    
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
                    
                    if use_db_direct:
                        # DB 직접 접속 모드: 캐시 불필요 - 필요할 때마다 직접 조회
                        logger.info(f"🔌 DB 직접 접속 모드: Progress Notes는 실시간 조회됨 (캐시 불필요) - {site}")
                    else:
                        # API 모드: 캐시 사용 (API 호출 비용 절감)
                        from progress_notes_json_cache import json_cache
                        from api_progressnote_fetch import fetch_progress_notes_for_site
                        logger.info(f"🌐 API 모드: Progress Notes 조회 및 캐시 - {site}")
                        progress_success, progress_notes = fetch_progress_notes_for_site(site, 7)
                        if progress_success and progress_notes:
                            json_cache.update_cache(site, progress_notes)
                            logger.info(f"Progress Notes 데이터 수집 및 캐시 완료 - {site}: {len(progress_notes)}개")
                        else:
                            logger.warning(f"Progress Notes 데이터 수집 실패 - {site}")
                    
                    # 3-3. Care Area 및 Event Type 데이터 수집 (DB 직접 접속)
                    if use_db_direct:
                        # DB 직접 접속 모드
                        try:
                            from manad_db_connector import MANADDBConnector
                            import json
                            
                            connector = MANADDBConnector(site)
                            
                            # Care Area 조회
                            logger.info(f"🔌 DB 직접 접속 모드: Care Area 조회 - {site}")
                            care_success, care_areas = connector.fetch_care_areas()
                            if care_success and care_areas:
                                # JSON 파일로 저장 (기존 형식 유지)
                                os.makedirs('data', exist_ok=True)
                                with open('data/carearea.json', 'w', encoding='utf-8') as f:
                                    json.dump(care_areas, f, ensure_ascii=False, indent=4)
                                logger.info(f"✅ DB에서 Care Area 조회 성공 - {site}: {len(care_areas)}개")
                            else:
                                error_msg = f"❌ DB 직접 접속 실패: {site} - Care Area 조회 결과가 비어있습니다."
                                logger.error(error_msg)
                                raise Exception(error_msg)
                            
                            # Event Type 조회
                            logger.info(f"🔌 DB 직접 접속 모드: Event Type 조회 - {site}")
                            event_success, event_types = connector.fetch_event_types()
                            if event_success and event_types:
                                # JSON 파일로 저장 (기존 형식 유지)
                                os.makedirs('data', exist_ok=True)
                                site_filename = f'data/eventtype_{site}.json'
                                with open(site_filename, 'w', encoding='utf-8') as f:
                                    json.dump(event_types, f, ensure_ascii=False, indent=4)
                                with open('data/eventtype.json', 'w', encoding='utf-8') as f:
                                    json.dump(event_types, f, ensure_ascii=False, indent=4)
                                logger.info(f"✅ DB에서 Event Type 조회 성공 - {site}: {len(event_types)}개")
                            else:
                                error_msg = f"❌ DB 직접 접속 실패: {site} - Event Type 조회 결과가 비어있습니다."
                                logger.error(error_msg)
                                raise Exception(error_msg)
                        except Exception as db_error:
                            error_msg = f"❌ DB 직접 접속 실패: {site} - {str(db_error)}. DB 연결 설정 및 드라이버 설치를 확인하세요."
                            logger.error(error_msg)
                            raise Exception(error_msg)
                    else:
                        # API 모드
                        from daily_data_manager import daily_data_manager
                        daily_results = daily_data_manager.collect_daily_data_if_needed(site)
                        if daily_results['care_area']:
                            logger.info(f"Care Area 데이터 수집 완료 - {site}")
                        if daily_results['event_type']:
                            logger.info(f"Event Type 데이터 수집 완료 - {site}")
                    
                    logger.info(f"사이트별 데이터 수집 완료 - 사이트: {site}")
                    
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
                    session['_created'] = get_australian_time().isoformat()
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
                    
                    # landing_page가 설정된 사용자는 해당 페이지로 이동
                    landing_page = user_info.get('landing_page')
                    if landing_page:
                        logger.info(f"로그인 성공 - {username} 사용자, landing_page 설정됨: {landing_page}")
                        return redirect(landing_page)
                    
                    # ROD 사용자인 경우 전용 대시보드로 이동 (대소문자 구분 안함)
                    username_upper = username.upper()
                    logger.info(f"로그인 사용자명 확인: {username} -> {username_upper}")
                    if username_upper == 'ROD':
                        logger.info(f"로그인 성공 - ROD 사용자 감지, rod_dashboard로 리다이렉트")
                        return redirect(url_for('rod_dashboard', site=site))
                    elif username_upper == 'YKROD':
                        logger.info(f"로그인 성공 - YKROD 사용자 감지, Yankalilla ROD 대시보드로 리다이렉트")
                        session['site'] = 'Yankalilla'
                        session['allowed_sites'] = ['Yankalilla']
                        return redirect(url_for('rod_dashboard', site='Yankalilla'))
                    elif username_upper == 'PGROD':
                        logger.info(f"로그인 성공 - PGROD 사용자 감지, 다중 사이트 접근 가능, Parafield Gardens ROD 대시보드로 리다이렉트")
                        session['site'] = 'Parafield Gardens'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
                        return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
                    elif username_upper == 'WPROD':
                        logger.info(f"로그인 성공 - WPROD 사용자 감지, West Park ROD 대시보드로 리다이렉트")
                        session['site'] = 'West Park'
                        session['allowed_sites'] = ['West Park']
                        return redirect(url_for('rod_dashboard', site='West Park'))
                    elif username_upper == 'RSROD':
                        logger.info(f"로그인 성공 - RSROD 사용자 감지, 다중 사이트 접근 가능, Ramsay ROD 대시보드로 리다이렉트")
                        session['site'] = 'Ramsay'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Ramsay'))
                    elif username_upper == 'NROD':
                        logger.info(f"로그인 성공 - NROD 사용자 감지, Nerrilda ROD 대시보드로 리다이렉트")
                        session['site'] = 'Nerrilda'
                        session['allowed_sites'] = ['Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Nerrilda'))
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
                    session['_created'] = get_australian_time().isoformat()
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
                    elif username_upper == 'YKROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - YKROD 사용자 감지, Yankalilla ROD 대시보드로 리다이렉트")
                        session['site'] = 'Yankalilla'
                        session['allowed_sites'] = ['Yankalilla']
                        return redirect(url_for('rod_dashboard', site='Yankalilla'))
                    elif username_upper == 'PGROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - PGROD 사용자 감지, 다중 사이트 접근 가능, Parafield Gardens ROD 대시보드로 리다이렉트")
                        session['site'] = 'Parafield Gardens'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda', 'Parafield Gardens']
                        return redirect(url_for('rod_dashboard', site='Parafield Gardens'))
                    elif username_upper == 'WPROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - WPROD 사용자 감지, West Park ROD 대시보드로 리다이렉트")
                        session['site'] = 'West Park'
                        session['allowed_sites'] = ['West Park']
                        return redirect(url_for('rod_dashboard', site='West Park'))
                    elif username_upper == 'RSROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - RSROD 사용자 감지, 다중 사이트 접근 가능, Ramsay ROD 대시보드로 리다이렉트")
                        session['site'] = 'Ramsay'
                        session['allowed_sites'] = ['Ramsay', 'Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Ramsay'))
                    elif username_upper == 'NROD':
                        logger.info(f"로그인 성공 (API 오류 있음) - NROD 사용자 감지, Nerrilda ROD 대시보드로 리다이렉트")
                        session['site'] = 'Nerrilda'
                        session['allowed_sites'] = ['Nerrilda']
                        return redirect(url_for('rod_dashboard', site='Nerrilda'))
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
    site = request.args.get('site', session.get('site', 'Parafield Gardens'))
    return render_template('index.html', selected_site=site, current_user=current_user)

@app.route('/rod-dashboard')
@login_required
def rod_dashboard():
    """ROD 전용 대시보드"""
    # ROD 사용자가 아닌 경우 접근 제한 (대소문자 구분 안함)
    username_upper = current_user.username.upper()
    logger.info(f"ROD 대시보드 접근 시도 - 사용자명 확인: {current_user.username} -> {username_upper}")
    if username_upper not in ['ROD', 'YKROD', 'PGROD', 'WPROD', 'RSROD', 'NROD']:
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
    
    # 사이트 정보 가져오기 (사이트 전용 ROD 사용자는 자신의 사이트만)
    sites_info = []
    safe_site_servers = get_safe_site_servers()
    
    # 사이트 전용 ROD 사용자인 경우 자신의 사이트만 표시
    if username_upper in ['YKROD', 'WPROD', 'NROD']:
        # 단일 사이트 전용 사용자
        allowed_sites = session.get('allowed_sites', [])
        if allowed_sites:
            site_name = allowed_sites[0]
            sites_info.append({
                'name': site_name,
                'server': safe_site_servers.get(site_name, 'Unknown'),
                'is_selected': True
            })
    elif username_upper in ['PGROD', 'RSROD']:
        # 다중 사이트 접근 가능 사용자
        allowed_sites = session.get('allowed_sites', [])
        for site_name in allowed_sites:
            if site_name in safe_site_servers:
                sites_info.append({
                    'name': site_name,
                    'server': safe_site_servers[site_name],
                    'is_selected': site_name == site
                })
    else:
        # 일반 ROD 사용자는 모든 사이트 표시
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


# ==================== Edenfield Dashboard ====================
@app.route('/edenfield-dashboard')
@login_required
def edenfield_dashboard():
    """
    Edenfield Dashboard - 경영진용 종합 대시보드
    5개 사이트 전체 현황을 한눈에 보여줌
    """
    try:
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        return render_template('edenfield_dashboard.html', 
                             sites=sites,
                             current_user=current_user)
    except Exception as e:
        logger.error(f"Edenfield Dashboard 오류: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/edenfield/stats')
@login_required
def get_edenfield_stats():
    """
    Edenfield 전체 통계 API
    - 5개 사이트 통합 데이터
    - Resident, Incident, Progress Note 통계
    - 기간 필터: today, week, month (기본값)
    """
    try:
        # 기간 파라미터 처리
        period = request.args.get('period', 'month')
        
        if period == 'today':
            days = 0  # 오늘만
            date_filter = "CAST(GETDATE() AS DATE)"
        elif period == 'week':
            days = 7
            date_filter = "DATEADD(day, -7, GETDATE())"
        else:  # month (기본값)
            days = 30
            date_filter = "DATEADD(day, -30, GETDATE())"
        
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        all_stats = []
        
        for site_name in sites:
            try:
                from manad_db_connector import MANADDBConnector
                connector = MANADDBConnector(site_name)
                
                with connector.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    site_stats = {'site': site_name}
                    
                    # 1. Client 수 (현재 입주자만 - ClientService.EndDate가 NULL인 활성 Client)
                    cursor.execute("""
                        SELECT COUNT(DISTINCT c.Id) 
                        FROM Client c
                        INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                        WHERE c.IsDeleted = 0 
                        AND cs.IsDeleted = 0
                        AND cs.EndDate IS NULL
                    """)
                    site_stats['total_persons'] = cursor.fetchone()[0]
                    
                    # 2. AdverseEvent (Incident) 통계 - 선택된 기간 내
                    # StatusEnumId: 0=Open, 1=InProgress, 2=Closed
                    if period == 'today':
                        cursor.execute("""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN StatusEnumId = 0 THEN 1 ELSE 0 END) as open_count,
                                SUM(CASE WHEN StatusEnumId = 2 THEN 1 ELSE 0 END) as closed_count,
                                SUM(CASE WHEN IsAmbulanceCalled = 1 THEN 1 ELSE 0 END) as ambulance,
                                SUM(CASE WHEN IsAdmittedToHospital = 1 THEN 1 ELSE 0 END) as hospital
                            FROM AdverseEvent
                            WHERE IsDeleted = 0
                            AND Date >= {date_filter}
                        """)
                    row = cursor.fetchone()
                    site_stats['incidents'] = {
                        'total': row[0] or 0,
                        'open': row[1] or 0,
                        'closed': row[2] or 0,
                        'ambulance': row[3] or 0,
                        'hospital': row[4] or 0
                    }
                    site_stats['incidents_30days'] = row[0] or 0  # 선택된 기간 내 incident
                    
                    # 3. Fall 사고 수 - 선택된 기간 내
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND CAST(ae.Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND at.Description LIKE '%Fall%'
                            AND ae.Date >= {date_filter}
                        """)
                    site_stats['fall_count'] = cursor.fetchone()[0]
                    
                    # 3-1. Skin & Wound 사고 수 - 선택된 기간 내
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND (at.Description LIKE '%Skin%' OR at.Description LIKE '%Wound%')
                            AND CAST(ae.Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM AdverseEvent ae
                            JOIN AdverseEvent_AdverseEventType aet ON ae.Id = aet.AdverseEventId
                            JOIN AdverseEventType at ON aet.AdverseEventTypeId = at.Id
                            WHERE ae.IsDeleted = 0 AND (at.Description LIKE '%Skin%' OR at.Description LIKE '%Wound%')
                            AND ae.Date >= {date_filter}
                        """)
                    site_stats['skin_wound_count'] = cursor.fetchone()[0]
                    
                    # 4. Progress Note 수 - 선택된 기간 내
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND CAST(Date AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM ProgressNote 
                            WHERE IsDeleted = 0 
                            AND Date >= {date_filter}
                        """)
                    site_stats['progress_notes_30days'] = cursor.fetchone()[0]
                    
                    # 5. Activity 수 - 선택된 기간 내
                    if period == 'today':
                        cursor.execute("""
                            SELECT COUNT(*) FROM ActivityEvent 
                            WHERE IsDeleted = 0 
                            AND CAST(StartDate AS DATE) = CAST(GETDATE() AS DATE)
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM ActivityEvent 
                            WHERE IsDeleted = 0 
                            AND StartDate >= {date_filter}
                        """)
                    site_stats['activities_30days'] = cursor.fetchone()[0]
                    
                    # 6. Activity 종류별 분포 (상위 5개)
                    if period == 'today':
                        cursor.execute("""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND CAST(ae.StartDate AS DATE) = CAST(GETDATE() AS DATE)
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    else:
                        cursor.execute(f"""
                            SELECT TOP 5 a.Description, COUNT(ae.Id) as cnt
                            FROM ActivityEvent ae
                            INNER JOIN Activity a ON ae.ActivityId = a.Id
                            WHERE ae.IsDeleted = 0
                            AND ae.StartDate >= {date_filter}
                            GROUP BY a.Description
                            ORDER BY cnt DESC
                        """)
                    site_stats['activity_types'] = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
                    
                    all_stats.append(site_stats)
                    
            except Exception as site_error:
                logger.warning(f"Site {site_name} 통계 조회 실패: {site_error}")
                all_stats.append({
                    'site': site_name,
                    'error': str(site_error),
                    'total_persons': 0,
                    'incidents': {'total': 0, 'open': 0, 'closed': 0, 'ambulance': 0, 'hospital': 0},
                    'incidents_30days': 0,
                    'fall_count': 0,
                    'skin_wound_count': 0,
                    'progress_notes_30days': 0,
                    'activities_30days': 0,
                    'activity_types': []
                })
        
        # 전체 합계 계산
        totals = {
            'total_persons': sum(s.get('total_persons', 0) for s in all_stats),
            'total_incidents': sum(s.get('incidents', {}).get('total', 0) for s in all_stats),
            'open_incidents': sum(s.get('incidents', {}).get('open', 0) for s in all_stats),
            'closed_incidents': sum(s.get('incidents', {}).get('closed', 0) for s in all_stats),
            'ambulance_calls': sum(s.get('incidents', {}).get('ambulance', 0) for s in all_stats),
            'hospital_admissions': sum(s.get('incidents', {}).get('hospital', 0) for s in all_stats),
            'incidents_30days': sum(s.get('incidents_30days', 0) for s in all_stats),
            'fall_count': sum(s.get('fall_count', 0) for s in all_stats),
            'skin_wound_count': sum(s.get('skin_wound_count', 0) for s in all_stats),
            'progress_notes_30days': sum(s.get('progress_notes_30days', 0) for s in all_stats),
            'activities_30days': sum(s.get('activities_30days', 0) for s in all_stats)
        }
        
        # Activity 종류별 전체 합계
        activity_totals = {}
        for site in all_stats:
            for at in site.get('activity_types', []):
                name = at['name']
                if name in activity_totals:
                    activity_totals[name] += at['count']
                else:
                    activity_totals[name] = at['count']
        totals['activity_types'] = sorted(
            [{'name': k, 'count': v} for k, v in activity_totals.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]  # 상위 10개
        
        return jsonify({
            'success': True,
            'period': period,
            'sites': all_stats,
            'totals': totals
        })
        
    except Exception as e:
        logger.error(f"Edenfield Stats 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/progress-notes')
@login_required
def progress_notes():
    try:
        allowed_sites = session.get('allowed_sites', [])
        site = request.args.get('site', session.get('site', 'Parafield Gardens'))
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
        year = int(request.args.get('year', get_australian_time().year))
        month = int(request.args.get('month', get_australian_time().month))
        
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
        if current_user.username.upper() not in ['ROD', 'YKROD', 'PGROD', 'WPROD', 'RSROD', 'NROD']:
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
                today = get_australian_time().date()
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
            'timestamp': get_australian_time().isoformat()
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
        session_created = session.get('_created', get_australian_time())
        
        if isinstance(session_created, str):
            session_created = datetime.fromisoformat(session_created)
        
        session_expires = session_created + session_lifetime
        now = get_australian_time()
        
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
        session['_created'] = get_australian_time().isoformat()
        
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
        
        # DB 직접 접속 모드 확인
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
        
        from api_progressnote_fetch import fetch_progress_notes_for_site
        
        # Progress Notes 조회 (DB 직접 접속 또는 API)
        if use_db_direct:
            logger.info(f"🔌 DB 직접 접속 모드: Progress Notes 실시간 조회 (캐시 없음) - {site}")
        else:
            logger.info(f"🌐 API 모드: Progress Notes 조회 - {site}")
        
        success, notes = fetch_progress_notes_for_site(site, days)
        
        if not success or not notes:
            result = {
                'success': False,
                'notes': [],
                'page': page,
                'per_page': per_page,
                'total_count': 0,
                'total_pages': 0,
                'cache_status': 'no_data',
                'last_sync': None,
                'cache_age_hours': 0
            }
        else:
            # API 모드일 때만 캐시에 저장 (DB 직접 접속 모드는 캐시 불필요)
            if not use_db_direct:
                from progress_notes_json_cache import json_cache
                json_cache.update_cache(site, notes)
            
            # 페이지네이션 적용
            total_count = len(notes)
            total_pages = (total_count + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_notes = notes[start_idx:end_idx]
            
            result = {
                'success': True,
                'notes': paginated_notes,
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'cache_status': 'fresh_db_data' if use_db_direct else 'fresh_api_data',
                'last_sync': get_australian_time().isoformat(),
                'cache_age_hours': 0
            }
        
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
            'fetched_at': get_australian_time().isoformat()
        }
        
        # ROD 대시보드 요청인지 확인 (year, month가 제공되고 event_types가 None이거나 빈 배열인 경우)
        if year is not None and month is not None and (not event_types or len(event_types) == 0):
            logger.info(f"ROD Dashboard request detected for {site} - {year}/{month}")
            from api_progressnote_fetch import fetch_residence_of_day_notes_with_client_data
            
            # 실시간 클라이언트 데이터와 함께 ROD 로직 사용
            residence_status = fetch_residence_of_day_notes_with_client_data(site, year, month)
            
            if residence_status and 'residence_status' in residence_status:
                residence_data = residence_status['residence_status']
                logger.info(f"ROD data fetched successfully for {site}: {len(residence_data)} residences")
                return jsonify({
                    'success': True,
                    'message': f'Successfully fetched ROD data for {len(residence_data)} residences',
                    'data': residence_data,
                    'site': site,
                    'count': len(residence_data),
                    'fetched_at': get_australian_time().isoformat()
                })
            else:
                logger.warning(f"No ROD data found for {site}")
                return jsonify({
                    'success': True,
                    'message': 'No ROD data found',
                    'data': {},
                    'site': site,
                    'count': 0,
                    'fetched_at': get_australian_time().isoformat()
                })
        else:
            # 일반 Progress Notes 요청
            logger.info(f"Regular Progress Notes request for {site}")
            logger.info(f"프로그레스 노트 가져오기 성공 - {site}: {result['total_count']}개 (페이지 {page}/{result['total_pages']})")
            return jsonify(response_data)
            
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
                    'fetched_at': get_australian_time().isoformat()
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

@app.route('/usage-log-viewer')
@login_required
def usage_log_viewer():
    """사용자 활동 로그 전용 뷰어 페이지"""
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
    
    return render_template('UsageLogViewer.html')

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
                    'fetched_at': get_australian_time().isoformat()
                })
            else:
                logger.warning(f"No incidents found for {site}")
                return jsonify({
                    'success': True,
                    'message': 'No incidents found',
                    'data': {'incidents': [], 'clients': []},
                    'site': site,
                    'count': 0,
                    'fetched_at': get_australian_time().isoformat()
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
        timestamp = get_australian_time().strftime('%Y-%m-%d_%H%M%S')
        filename = f'rod_debug_{timestamp}.json'
        filepath = os.path.join(logs_dir, filename)
        
        # Add server timestamp and user info
        debug_data['server_timestamp'] = get_australian_time().isoformat()
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

@app.route('/api/usage-logs')
@login_required
def get_usage_logs():
    """사용자 활동 로그 분석 데이터 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # 날짜 범위 파라미터
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # UsageLog 디렉토리에서 로그 파일들 수집
        usage_log_dir = "UsageLog"
        if not os.path.exists(usage_log_dir):
            return jsonify({'success': True, 'logs': [], 'summary': {}})
        
        all_logs = []
        login_sessions = {}  # 사용자별 로그인 세션 추적
        
        # 모든 JSON 로그 파일 읽기
        for root, dirs, files in os.walk(usage_log_dir):
            for filename in files:
                if filename.endswith('.json'):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            logs = json.load(f)
                            
                        # 날짜 필터링
                        if start_date or end_date:
                            filtered_logs = []
                            for log in logs:
                                log_date = log.get('timestamp', '').split('T')[0]
                                if start_date and log_date < start_date:
                                    continue
                                if end_date and log_date > end_date:
                                    continue
                                filtered_logs.append(log)
                            logs = filtered_logs
                        
                        all_logs.extend(logs)
                    except Exception as e:
                        logger.error(f"로그 파일 읽기 실패 {filepath}: {str(e)}")
                        continue
        
        # 시간순 정렬
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # 로그인/로그아웃 세션 분석
        for log in all_logs:
            username = log.get('user', {}).get('username', 'Unknown')
            timestamp = log.get('timestamp', '')
            page = log.get('page', {}).get('path', '')
            
            if username not in login_sessions:
                login_sessions[username] = []
            
            # 로그인 감지 (홈 페이지나 로그인 페이지 접근)
            if page in ['/', '/login'] or 'login' in page.lower():
                login_sessions[username].append({
                    'type': 'login',
                    'timestamp': timestamp,
                    'page': page
                })
            
            # 로그아웃 감지
            if page == '/logout':
                login_sessions[username].append({
                    'type': 'logout',
                    'timestamp': timestamp,
                    'page': page
                })
        
        # 요약 통계
        summary = {
            'total_logs': len(all_logs),
            'unique_users': len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs)),
            'date_range': {
                'start': all_logs[0].get('timestamp', '').split('T')[0] if all_logs else None,
                'end': all_logs[-1].get('timestamp', '').split('T')[0] if all_logs else None
            },
            'login_sessions': login_sessions
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs[-1000:],  # 최근 1000개만 반환
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"사용자 활동 로그 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/months')
@login_required
def get_usage_log_months():
    """사용 가능한 월 목록 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        months = set()
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        # 파일명에서 월 정보 추출 (예: access_2025-09-26.json)
                        if 'access_' in filename:
                            try:
                                date_part = filename.replace('access_', '').replace('.json', '')
                                year_month = '-'.join(date_part.split('-')[:2])  # YYYY-MM
                                months.add(year_month)
                            except:
                                continue
        
        return jsonify({
            'success': True,
            'months': sorted(list(months), reverse=True)
        })
        
    except Exception as e:
        logger.error(f"월 목록 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/month/<month>')
@login_required
def get_usage_logs_by_month(month):
    """특정 월의 사용자 활동 로그 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        all_logs = []
        days = set()
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json') and month in filename:
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                            
                            for log in logs:
                                timestamp = log.get('timestamp', '')
                                if timestamp:
                                    log_date = timestamp.split('T')[0]
                                    if log_date.startswith(month):
                                        all_logs.append(log)
                                        day = log_date.split('-')[2]  # 일자 추출
                                        days.add(day)
                        except Exception as e:
                            logger.error(f"로그 파일 읽기 실패 {filepath}: {str(e)}")
                            continue
        
        # 시간순 정렬
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # 통계 계산
        unique_users = len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs))
        active_days = len(days)
        avg_daily_access = len(all_logs) / active_days if active_days > 0 else 0
        
        stats = {
            'totalAccess': len(all_logs),
            'uniqueUsers': unique_users,
            'activeDays': active_days,
            'avgDailyAccess': avg_daily_access
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs,
            'stats': stats,
            'days': sorted(list(days), reverse=True)
        })
        
    except Exception as e:
        logger.error(f"월별 로그 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/all')
@login_required
def get_all_usage_logs():
    """전체 사용자 활동 로그 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        all_logs = []
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                                all_logs.extend(logs)
                        except Exception as e:
                            logger.error(f"로그 파일 읽기 실패 {filepath}: {str(e)}")
                            continue
        
        # 시간순 정렬
        all_logs.sort(key=lambda x: x.get('timestamp', ''))
        
        # 통계 계산
        unique_users = len(set(log.get('user', {}).get('username', 'Unknown') for log in all_logs))
        
        stats = {
            'totalAccess': len(all_logs),
            'uniqueUsers': unique_users,
            'activeDays': 0,
            'avgDailyAccess': 0
        }
        
        return jsonify({
            'success': True,
            'logs': all_logs[-2000:],  # 최근 2000개만 반환
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"전체 로그 조회 실패: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/usage-logs/monthly-stats')
@login_required
def get_monthly_usage_stats():
    """월별 통계 반환"""
    try:
        # 관리자만 접근 허용
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        usage_log_dir = "UsageLog"
        monthly_stats = {}
        
        if os.path.exists(usage_log_dir):
            for root, dirs, files in os.walk(usage_log_dir):
                for filename in files:
                    if filename.endswith('.json'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                logs = json.load(f)
                            
                            for log in logs:
                                timestamp = log.get('timestamp', '')
                                if timestamp:
                                    log_date = timestamp.split('T')[0]
                                    year_month = '-'.join(log_date.split('-')[:2])
                                    
                                    if year_month not in monthly_stats:
                                        monthly_stats[year_month] = 0
                                    monthly_stats[year_month] += 1
                        except Exception as e:
                            logger.error(f"로그 파일 읽기 실패 {filepath}: {str(e)}")
                            continue
        
        # 월별 통계를 리스트로 변환
        monthly_list = [{'month': month, 'totalAccess': count} for month, count in monthly_stats.items()]
        monthly_list.sort(key=lambda x: x['month'], reverse=True)
        
        return jsonify({
            'success': True,
            'monthlyStats': monthly_list
        })
        
    except Exception as e:
        logger.error(f"월별 통계 조회 실패: {str(e)}")
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

@app.route('/api/active-users', methods=['GET'])
def get_active_users():
    """현재 로그인된 사용자들을 사이트별로 반환하는 API"""
    try:
        token_manager = get_fcm_token_manager()
        stats = token_manager.get_token_stats()
        
        # 사이트별로 사용자 그룹화
        site_users = {
            'Parafield Gardens': [],
            'Nerrilda': [],
            'Ramsay': [],
            'Yankalilla': []
        }
        
        # 사용자별 토큰 정보 처리
        for user_id, user_tokens in stats.get('user_tokens', {}).items():
            active_tokens = [token for token in user_tokens if token.get('is_active', True)]
            
            if active_tokens:
                # 가장 최근에 사용된 토큰 정보 사용
                latest_token = max(active_tokens, key=lambda x: x.get('last_used', ''))
                
                # 사용자 정보 구성
                user_info = {
                    'user_id': user_id,
                    'device_info': latest_token.get('device_info', 'Unknown Device'),
                    'last_used': latest_token.get('last_used', ''),
                    'created_at': latest_token.get('created_at', ''),
                    'token_count': len(active_tokens)
                }
                
                # 사이트별로 분류 (사용자 ID나 디바이스 정보 기반으로 추정)
                # 실제로는 사용자 테이블에서 사이트 정보를 가져와야 하지만, 
                # 현재는 간단히 사용자 ID 패턴으로 분류
                if 'pg' in user_id.lower() or 'parafield' in user_id.lower():
                    site_users['Parafield Gardens'].append(user_info)
                elif 'nerrilda' in user_id.lower():
                    site_users['Nerrilda'].append(user_info)
                elif 'ramsay' in user_id.lower():
                    site_users['Ramsay'].append(user_info)
                elif 'yankalilla' in user_id.lower():
                    site_users['Yankalilla'].append(user_info)
                else:
                    # 기본적으로 Parafield Gardens에 배치
                    site_users['Parafield Gardens'].append(user_info)
        
        # 각 사이트별 통계 계산
        site_stats = {}
        total_active_devices = 0
        for site, users in site_users.items():
            site_devices = sum(user['token_count'] for user in users)
            site_stats[site] = {
                'users': users,
                'total_users': len(users),
                'total_devices': site_devices
            }
            total_active_devices += site_devices
        
        return jsonify({
            'success': True,
            'site_users': site_stats,
            'total_active_users': sum(len(users) for users in site_users.values()),
            'total_active_devices': total_active_devices
        })
        
    except Exception as e:
        logger.error(f"활성 사용자 조회 중 오류: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'활성 사용자 조회 중 오류가 발생했습니다: {str(e)}'
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

# ==============================
# User Management Routes
# ==============================

@app.route('/user-management')
@login_required
def user_management():
    """사용자 관리 페이지 (ADMIN 전용)"""
    # 관리자 권한 확인
    if current_user.role != 'admin':
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    # 접속 로그 기록
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": getattr(current_user, 'position', 'Unknown')
    }
    usage_logger.log_access(user_info, '/user-management')
    
    return render_template('user_management.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_all_users_api():
    """모든 사용자 목록 조회 API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        from config_users import get_all_users
        users = get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"사용자 목록 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['GET'])
@login_required
def get_user_api(username):
    """특정 사용자 정보 조회 API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        user_data = get_user(username)
        if user_data:
            # 패스워드 해시는 제외
            safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
            from config_users import get_username_by_lowercase
            actual_username = get_username_by_lowercase(username)
            safe_user['username'] = actual_username
            return jsonify({'success': True, 'user': safe_user})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        logger.error(f"사용자 정보 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users', methods=['POST'])
@login_required
def add_user_api():
    """새 사용자 추가 API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        # 필수 필드 확인
        required_fields = ['username', 'password', 'first_name', 'last_name', 'role', 'position', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        from config_users import add_user
        success, message = add_user(
            username=data['username'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            position=data['position'],
            location=data['location'],
            landing_page=data.get('landing_page')
        )
        
        if success:
            logger.info(f"사용자 추가 성공: {data['username']} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"사용자 추가 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['PUT'])
@login_required
def update_user_api(username):
    """사용자 정보 수정 API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        from config_users import update_user
        success, message = update_user(
            username=username,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role=data.get('role'),
            position=data.get('position'),
            location=data.get('location'),
            password=data.get('password'),
            landing_page=data.get('landing_page')
        )
        
        if success:
            logger.info(f"사용자 수정 성공: {username} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"사용자 수정 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
def delete_user_api(username):
    """사용자 삭제 API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # 자기 자신은 삭제할 수 없음
        from config_users import get_username_by_lowercase
        actual_username = get_username_by_lowercase(username)
        if actual_username and actual_username.lower() == current_user.username.lower():
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        from config_users import delete_user
        success, message = delete_user(username)
        
        if success:
            logger.info(f"사용자 삭제 성공: {username} by {current_user.username}")
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"사용자 삭제 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/options', methods=['GET'])
@login_required
def get_user_options_api():
    """사용자 옵션 조회 API (role, position, location 목록)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        from config_users import get_unique_roles, get_unique_positions, get_unique_locations
        
        return jsonify({
            'success': True,
            'roles': get_unique_roles(),
            'positions': get_unique_positions(),
            'locations': get_unique_locations()
        })
    except Exception as e:
        logger.error(f"사용자 옵션 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
                get_australian_time().isoformat(),
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
            ''', (get_australian_time().isoformat(), policy_id))
            
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
        
        # Task Manager 비활성화됨 - JSON 전용 시스템
        # return get_incident_workflow_status(incident_id)
        
        # 임시 응답 (기능 비활성화)
        return jsonify({
            'success': False,
            'message': 'Task Manager는 JSON 전용 시스템으로 인해 비활성화되었습니다.',
            'workflow_status': 'unavailable'
        })
        
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
        
        # Task Manager 비활성화됨 - JSON 전용 시스템
        # task_manager = get_task_manager()
        # result = task_manager.create_incident_workflow(
        #     incident_id=data['incident_id'],
        #     policy_id=data['policy_id'],
        #     client_name=data['client_name'],
        #     client_id=data['client_id'],
        #     site=data['site'],
        #     event_type=data['event_type'],
        #     risk_rating=data['risk_rating'],
        #     created_by=created_by
        # )
        
        # 임시 응답 (기능 비활성화)
        result = {
            'success': False,
            'message': 'Task Manager는 JSON 전용 시스템으로 인해 비활성화되었습니다.'
        }
        
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
        
        # Task Manager 비활성화됨 - JSON 전용 시스템
        # task_manager = get_task_manager()
        # result = task_manager.complete_task(
        #     task_id=task_id,
        #     completed_by=completed_by,
        #     notes=notes
        # )
        
        # 임시 응답 (기능 비활성화)
        result = {
            'success': False,
            'message': 'Task Manager는 JSON 전용 시스템으로 인해 비활성화되었습니다.'
        }
        
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
        
        # Task Manager 비활성화됨 - JSON 전용 시스템
        # task_manager = get_task_manager()
        # tasks = task_manager.get_user_tasks(assigned_role, site, status)
        
        # 임시 응답 (기능 비활성화)
        tasks = []
        
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
        
        # Task Manager 비활성화됨 - JSON 전용 시스템
        # task_manager = get_task_manager()
        # result = task_manager.send_scheduled_notifications()
        
        # 임시 응답 (기능 비활성화)
        result = {
            'success': False,
            'message': 'Task Manager는 JSON 전용 시스템으로 인해 비활성화되었습니다.',
            'sent_count': 0,
            'failed_count': 0
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"작업 알림 전송 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# CIMS (Compliance-Driven Incident Management System) Routes
# ==============================

from cims_policy_engine import PolicyEngine
from app_locks import write_lock

# CIMS 정책 엔진 인스턴스
policy_engine = PolicyEngine()

# CIMS용 데이터베이스 연결 함수
def get_db_connection(read_only: bool = False):
    """CIMS용 데이터베이스 연결"""
    if read_only:
        conn = sqlite3.connect('file:progress_report.db?mode=ro', timeout=60.0, uri=True)
    else:
        conn = sqlite3.connect('progress_report.db', timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except Exception:
        pass
    return conn

@app.route('/api/cache/status-current', methods=['GET'])
@login_required
def get_cache_status_current():
    """Return latest cache/sync status for dashboard indicator"""
    conn = None
    try:
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, last_processed
            FROM cims_cache_management
            ORDER BY last_processed DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        status = row[0] if row else 'idle'
        last = row[1] if row else None
        return jsonify({'success': True, 'status': status, 'last_processed': last})
    except Exception as e:
        logger.error(f"get_cache_status_current error: {e}")
        return jsonify({'success': True, 'status': 'idle'}), 200
    finally:
        if conn:
            conn.close()

@app.route('/api/cims/incidents/<int:incident_db_id>/tasks', methods=['GET'], endpoint='get_incident_tasks_v2')
@login_required
def get_incident_tasks_v2(incident_db_id):
    """주어진 인시던트의 태스크 목록과 요약 카운트 반환"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Incident 존재 확인 및 기본 정보
        cursor.execute(
            """
            SELECT id, incident_id, resident_name, site, incident_date, status
            FROM cims_incidents
            WHERE id = ?
            """,
            (incident_db_id,)
        )
        incident = cursor.fetchone()
        if not incident:
            return jsonify({'success': False, 'message': 'Incident not found'}), 404

        # 태스크 목록 조회
        cursor.execute(
            """
            SELECT id, task_id, task_name, description, assigned_role,
                   due_date, priority, status, completed_at
            FROM cims_tasks
            WHERE incident_id = ?
            ORDER BY due_date ASC
            """,
            (incident_db_id,)
        )
        rows = cursor.fetchall()

        tasks = []
        counts = {
            'total': 0,
            'completed': 0,
            'pending': 0,
            'in_progress': 0,
            'overdue': 0
        }

        now_iso = datetime.now().isoformat()

        for r in rows:
            task = {
                'id': r['id'],
                'task_identifier': r['task_id'],
                'task_name': r['task_name'],
                'description': r['description'],
                'assigned_role': r['assigned_role'],
                'due_date': r['due_date'],
                'priority': r['priority'],
                'status': r['status'],
                'completed_at': r['completed_at']
            }
            tasks.append(task)

            counts['total'] += 1
            status = (r['status'] or '').lower()
            if status == 'completed':
                counts['completed'] += 1
            elif status in ('in_progress', 'in progress'):
                counts['in_progress'] += 1
            else:
                # pending 등
                counts['pending'] += 1
                # overdue 계산: due_date < now and not completed
                try:
                    if r['due_date'] and r['completed_at'] is None and datetime.fromisoformat(r['due_date']) < datetime.fromisoformat(now_iso):
                        counts['overdue'] += 1
                except Exception:
                    pass

        return jsonify({
            'success': True,
            'incident': {
                'id': incident['id'],
                'incident_id': incident['incident_id'],
                'resident_name': incident['resident_name'],
                'site': incident['site'],
                'incident_date': incident['incident_date'],
                'status': incident['status']
            },
            'counts': counts,
            'tasks': tasks
        })
    except Exception as e:
        logger.error(f"Incident tasks fetch error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/incident_dashboard2')
@login_required
def incident_dashboard2():
    """기존 CIMS 대시보드 - 통합 대시보드로 리다이렉트"""
    return redirect(url_for('integrated_dashboard'))

@app.route('/api/cims/tasks')
@login_required
def get_cims_tasks():
    """사용자 태스크 조회 API"""
    try:
        # 사용자 역할에 따른 태스크 조회
        if current_user.is_admin() or current_user.is_clinical_manager():
            # 관리자는 모든 태스크 조회
            tasks = policy_engine.get_user_tasks(
                user_id=current_user.id, 
                role='admin', 
                status_filter=request.args.get('status')
            )
        else:
            # 일반 사용자는 자신에게 할당된 태스크만 조회
            tasks = policy_engine.get_user_tasks(
                user_id=current_user.id, 
                role=current_user.role, 
                status_filter=request.args.get('status')
            )
        
        return jsonify({
            'success': True,
            'tasks': tasks
        })
        
    except Exception as e:
        logger.error(f"CIMS 태스크 조회 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/incidents', methods=['GET', 'POST'])
@login_required
def cims_incidents():
    """인시던트 조회/생성 API"""
    if request.method == 'GET':
        return get_cims_incidents()
    else:
        return create_cims_incident()

@app.route('/api/cims/fall-statistics', methods=['GET'])
@login_required
def get_fall_statistics():
    """Fall Policy별 통계 조회 API"""
    conn = None
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        from services.fall_policy_detector import fall_detector
        
        # Fall incidents 조회 (최근 30일) - fall_type 포함
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT id, incident_id, incident_type, incident_date, site, fall_type
            FROM cims_incidents
            WHERE incident_type LIKE '%Fall%'
            AND incident_date >= ?
            ORDER BY incident_date DESC
        """, (thirty_days_ago,))
        
        fall_incidents = cursor.fetchall()
        
        # 통계 집계
        stats = {
            'total_falls': len(fall_incidents),
            'witnessed': 0,
            'unwitnessed': 0,
            'unknown': 0,
            'visits_scheduled': 0,
            'visits_saved': 0,
            'by_site': {},
            'recent_falls': []
        }
        
        for incident in fall_incidents:
            incident_id = incident[0]
            incident_manad_id = incident[1]
            incident_type = incident[2]
            incident_date = incident[3]
            site = incident[4]
            fall_type = incident[5]  # DB에서 직접 조회
            
            # fall_type이 없으면 계산 (레거시 데이터 처리)
            if not fall_type:
                fall_type = fall_detector.detect_fall_type_from_incident(incident_id, cursor)
                
                # 계산된 fall_type을 DB에 저장
                try:
                    cursor.execute("""
                        UPDATE cims_incidents
                        SET fall_type = ?
                        WHERE id = ?
                    """, (fall_type, incident_id))
                    conn.commit()
                except:
                    pass
            
            # 통계 업데이트
            if fall_type == 'witnessed':
                stats['witnessed'] += 1
                stats['visits_scheduled'] += 1
                stats['visits_saved'] += 35  # 36 - 1 = 35 visits saved
            elif fall_type == 'unwitnessed':
                stats['unwitnessed'] += 1
                stats['visits_scheduled'] += 36
            else:
                stats['unknown'] += 1
                stats['visits_scheduled'] += 36  # Default to unwitnessed
            
            # 사이트별 통계
            if site not in stats['by_site']:
                stats['by_site'][site] = {
                    'total': 0,
                    'witnessed': 0,
                    'unwitnessed': 0,
                    'unknown': 0
                }
            
            stats['by_site'][site]['total'] += 1
            stats['by_site'][site][fall_type] += 1
            
            # 최근 5개 Fall만 상세 정보 포함
            if len(stats['recent_falls']) < 5:
                stats['recent_falls'].append({
                    'incident_id': incident_manad_id,
                    'incident_type': incident_type,
                    'fall_type': fall_type,
                    'incident_date': incident_date,
                    'site': site
                })
        
        # 비율 계산
        if stats['total_falls'] > 0:
            stats['witnessed_percentage'] = round(stats['witnessed'] / stats['total_falls'] * 100, 1)
            stats['unwitnessed_percentage'] = round(stats['unwitnessed'] / stats['total_falls'] * 100, 1)
            stats['unknown_percentage'] = round(stats['unknown'] / stats['total_falls'] * 100, 1)
        else:
            stats['witnessed_percentage'] = 0
            stats['unwitnessed_percentage'] = 0
            stats['unknown_percentage'] = 0
        
        logger.info(f"📊 Fall 통계 조회: {stats['total_falls']}개 (W: {stats['witnessed']}, UW: {stats['unwitnessed']})")
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Fall 통계 조회 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/cims/schedule/<site_name>', methods=['GET'])
@login_required
def get_site_schedule(site_name):
    """Get visit schedule for a specific site"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate real schedule data from CIMS database
        schedule_data = generate_real_schedule(site_name)
        
        return jsonify(schedule_data)
        
    except Exception as e:
        logger.error(f"Error getting schedule for {site_name}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/schedule/complete', methods=['POST'])
@login_required
def complete_scheduled_task():
    """Mark a scheduled task as completed"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        task_id = data.get('task_id')
        site_name = data.get('site_name')
        
        if not task_id or not site_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Update the task in CIMS database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract CIMS task ID from the task_id
        if task_id.startswith('cims_task_'):
            cims_task_id = int(task_id.replace('cims_task_', ''))
        else:
            return jsonify({'error': 'Invalid task ID format'}), 400
        
        # Update task status
        cursor.execute("""
            UPDATE cims_tasks 
            SET status = 'Completed', 
                completed_at = ?,
                completed_by_user_id = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), current_user.id, cims_task_id))
        
        # Create audit log
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            current_user.id,
            'task_completed',
            'task',
            cims_task_id,
            json.dumps({
                'task_id': task_id,
                'site_name': site_name,
                'completed_at': datetime.now().isoformat()
            })
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Task {task_id} completed for site {site_name} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'task_id': task_id,
            'completed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error completing task: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/integrator/start', methods=['POST'])
@login_required
def start_manad_integrator():
    """Start MANAD Plus integrator"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        # Start the integrator
        integrator = MANADPlusIntegrator()
        success = integrator.start_polling()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'MANAD Plus integrator started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start MANAD Plus integrator'
            }), 500
            
    except Exception as e:
        logger.error(f"Error starting MANAD integrator: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/integrator/status', methods=['GET'])
@login_required
def get_integrator_status():
    """Get MANAD Plus integrator status"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        integrator = MANADPlusIntegrator()
        status = integrator.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting integrator status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/sync-progress-notes', methods=['POST'])
@login_required
def trigger_progress_note_sync():
    """
    Progress Note 동기화 수동 트리거 (Admin only)
    
    ⚠️ 일시적으로 비활성화됨 (2025-11-25)
    - 나중에 DB 직접 접속으로 재구현 예정
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager']):
            return jsonify({'error': 'Access denied'}), 403
        
        logger.info(f"Progress Note 동기화 수동 트리거 by {current_user.username} (비활성화됨)")
        # result = sync_progress_notes_from_manad_to_cims()
        
        return jsonify({
            'success': True,
            'message': 'Progress Note sync temporarily disabled. Will be reimplemented with DB direct access.',
            'matched': 0
        })
        
    except Exception as e:
        logger.error(f"Progress Note 동기화 트리거 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cims/check-progress-notes/<task_id>', methods=['GET'])
@login_required
def check_progress_notes(task_id):
    """Check progress notes for a specific task in MANAD Plus"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        from manad_plus_integrator import MANADPlusIntegrator
        
        # Get task details
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.id, i.manad_incident_id, i.resident_id, i.resident_name
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE t.id = ?
        """, (task_id,))
        
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        _, manad_incident_id, resident_id, resident_name = task
        
        if not manad_incident_id:
            return jsonify({'error': 'No MANAD incident ID associated'}), 400
        
        # Check progress notes in MANAD Plus
        integrator = MANADPlusIntegrator()
        has_progress_note = integrator.check_progress_notes(manad_incident_id, resident_id)
        
        return jsonify({
            'task_id': task_id,
            'manad_incident_id': manad_incident_id,
            'resident_name': resident_name,
            'has_progress_note': has_progress_note,
            'checked_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error checking progress notes: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def generate_real_schedule(site_name):
    """Generate real schedule data from CIMS database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get incomplete tasks for the site
        cursor.execute("""
            SELECT t.id, t.task_name, t.description, t.due_date, t.priority, t.status,
                   i.resident_name, i.incident_type, i.location, i.incident_date
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE i.site = ? AND t.status IN ('Open', 'In Progress', 'pending', 'Pending')
            ORDER BY t.due_date ASC
        """, (site_name,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        schedule = []
        now = datetime.now()
        
        for task in tasks:
            task_id, task_name, description, due_date, priority, status, resident_name, incident_type, location, incident_date = task
            
            # Parse due date
            if isinstance(due_date, str):
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            else:
                due_datetime = due_date
            
            # Determine status and urgency
            time_diff = (due_datetime - now).total_seconds()
            if time_diff < 0:
                task_status = 'overdue'
                urgency = 'overdue'
            elif time_diff < 2 * 3600:  # Less than 2 hours
                task_status = 'due-soon'
                urgency = 'urgent'
            else:
                task_status = 'pending'
                urgency = 'normal'
            
            # Extract room from location if available
            room = 'Unknown'
            if location:
                # Try to extract room number from location
                import re
                room_match = re.search(r'Room\s+(\d+)', location)
                if room_match:
                    room = f"Room {room_match.group(1)}"
                else:
                    room = location
            
            schedule.append({
                'id': f'cims_task_{task_id}',
                'time': due_datetime.isoformat(),
                'resident': resident_name or 'Unknown Resident',
                'room': room,
                'task': task_name or description or f'Follow-up for {incident_type}',
                'status': task_status,
                'urgency': urgency,
                'completed': status == 'Completed',
                'site': site_name,
                'priority': priority,
                'incident_type': incident_type
            })
        
        return sorted(schedule, key=lambda x: x['time'])
        
    except Exception as e:
        logger.error(f"Error generating real schedule for {site_name}: {str(e)}")
        # Return empty schedule on error
        return []

def _cache_clients_to_db(clients: list, site_name: str, cursor) -> None:
    """
    클라이언트 데이터를 clients_cache 테이블에 저장
    
    Args:
        clients: MANAD API에서 받은 클라이언트 리스트
        site_name: 사이트 이름
        cursor: DB 커서
    """
    try:
        # 기존 사이트 클라이언트 비활성화
        cursor.execute("""
            UPDATE clients_cache 
            SET is_active = 0 
            WHERE site = ?
        """, (site_name,))
        
        # 새 클라이언트 데이터 삽입
        for client in clients:
            try:
                client_id = client.get('Id', 0)
                first_name = client.get('FirstName', '')
                middle_name = client.get('MiddleName', '')
                surname = client.get('LastName', client.get('Surname', ''))
                preferred_name = client.get('PreferredName', '')
                client_name = f"{first_name} {surname}".strip()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO clients_cache (
                        client_record_id, person_id, client_name, preferred_name,
                        title, first_name, middle_name, surname, gender, birth_date,
                        admission_date, room_name, room_number, wing_name,
                        location_id, location_name, main_client_service_id,
                        original_person_id, site, last_synced, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    client_id,
                    client.get('PersonId', 0),
                    client_name,
                    preferred_name,
                    client.get('Title', ''),
                    first_name,
                    middle_name,
                    surname,
                    client.get('Gender', ''),
                    client.get('BirthDate', None),
                    client.get('AdmissionDate', None),
                    client.get('RoomName', ''),
                    client.get('RoomNumber', ''),
                    client.get('WingName', ''),
                    client.get('LocationId', 0),
                    client.get('LocationName', ''),
                    client.get('MainClientServiceId', 0),
                    client.get('PersonId', 0),
                    site_name,
                    datetime.now().isoformat()
                ))
            except Exception as e:
                logger.warning(f"클라이언트 캐싱 오류 (ID: {client.get('Id', 'unknown')}): {e}")
                continue
        
        logger.info(f"✅ {len(clients)}명의 클라이언트 캐시 완료: {site_name}")
        
    except Exception as e:
        logger.error(f"클라이언트 캐시 업데이트 오류: {e}")

def get_api_config_for_site(site_name):
    """사이트별 API 설정 생성"""
    try:
        from config import get_server_info, get_api_headers
        server_info = get_server_info(site_name)
        api_headers = get_api_headers(site_name)
        
        return {
            'base_url': server_info['base_url'],
            'server_ip': server_info['server_ip'],
            'server_port': server_info['server_port'],
            'api_username': api_headers.get('x-api-username', 'ManadAPI'),
            'api_key': api_headers.get('x-api-key', ''),
            'timeout': 120
        }
    except Exception as e:
        logger.error(f"Failed to get API config for {site_name}: {e}")
        return None

def sync_progress_notes_from_manad_to_cims():
    """
    MANAD Plus에서 Post Fall Progress Notes를 동기화하여 Task 완료 상태 업데이트
    
    ⚠️ 일시적으로 비활성화됨 (2025-11-25)
    - 나중에 DB 직접 접속으로 재구현 예정
    - 현재는 스케줄만 표시, Task 완료 체크 로직은 제거
    """
    # TODO: 나중에 DB 직접 접속으로 Post Fall Progress Note 조회 및 Task 완료 처리 재구현
    # - manad_db_connector에서 Post Fall Progress Note 조회 메서드 추가
    # - Task와 매칭하여 자동 완료 처리
    logger.info("⚠️ Progress Note 동기화 비활성화됨 (일시 중단 - DB 직접 접속으로 재구현 예정)")
    return {'success': True, 'matched': 0, 'message': 'Progress Note sync temporarily disabled'}

def ensure_fall_policy_exists():
    """
    Fall Policy가 DB에 존재하는지 확인하고 없으면 기본 Policy 생성
    """
    import json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if Fall policy exists
        cursor.execute("""
            SELECT COUNT(*) FROM cims_policies 
            WHERE policy_id = 'FALL-001' AND is_active = 1
        """)
        
        if cursor.fetchone()[0] > 0:
            logger.info("✅ Fall Policy already exists")
            conn.close()
            return
        
        # Create default Fall Policy
        logger.info("📝 Creating default Fall Policy...")
        
        default_policy_json = {
            "policy_name": "Fall Management Policy V3",
            "policy_id": "FALL-001",
            "incident_association": {
                "incident_type": "Fall"
            },
            "nurse_visit_schedule": [
                {
                    "phase": 1,
                    "interval": 30,
                    "interval_unit": "minutes",
                    "duration": 4,
                    "duration_unit": "hours"
                },
                {
                    "phase": 2,
                    "interval": 2,
                    "interval_unit": "hours",
                    "duration": 20,
                    "duration_unit": "hours"
                },
                {
                    "phase": 3,
                    "interval": 4,
                    "interval_unit": "hours",
                    "duration": 3,
                    "duration_unit": "days"
                }
            ],
            "common_assessment_tasks": "Complete neurological observations: GCS, pupil response, limb movement, vital signs"
        }
        
        cursor.execute("""
            INSERT INTO cims_policies 
            (policy_id, name, description, version, effective_date, rules_json, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'FALL-001',
            'Fall Management Policy V3',
            'Automatic post-fall neurological monitoring with phased visit schedule',
            '3.0',
            datetime.now().isoformat(),
            json.dumps(default_policy_json),
            1,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        logger.info("✅ Default Fall Policy created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating Fall Policy: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor):
    """
    Fall incident에 대해 자동으로 task 생성
    (CIMSService.auto_generate_fall_tasks를 래핑)
    
    Args:
        incident_db_id: CIMS DB의 incident ID (integer)
        incident_date_iso: Incident 발생 시간 (ISO format string)
        cursor: DB cursor
        
    Returns:
        생성된 task 수
    """
    from services.cims_service import CIMSService
    return CIMSService.auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor)

def sync_incidents_from_manad_to_cims(full_sync=False):
    """
    MANAD API에서 최신 인시던트를 가져와 CIMS DB에 동기화
    
    Args:
        full_sync: True면 전체 동기화 (30일), False면 증분 동기화 (마지막 동기화 이후)
    """
    try:
        from api_incident import fetch_incidents_with_client_data
        
        safe_site_servers = get_safe_site_servers()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 첫 동기화 여부 확인 (DB에 인시던트가 있는지 체크)
        cursor.execute("SELECT COUNT(*) FROM cims_incidents")
        incident_count = cursor.fetchone()[0]
        is_first_sync = incident_count == 0 or full_sync
        
        if is_first_sync:
            # 첫 동기화: 최근 30일 (또는 더 많이)
            logger.info("🔄 첫 동기화 시작: 최근 30일 데이터")
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        else:
            # 증분 동기화: 마지막 동기화 시간 이후
            cursor.execute("""
                SELECT value FROM system_settings 
                WHERE key = 'last_incident_sync_time'
            """)
            last_sync_result = cursor.fetchone()
            
            if last_sync_result:
                # 마지막 동기화 시간 사용 (약간의 중복 허용을 위해 1시간 전부터)
                last_sync_dt = datetime.fromisoformat(last_sync_result[0])
                start_date = (last_sync_dt - timedelta(hours=1)).strftime('%Y-%m-%d')
                logger.info(f"📥 증분 동기화: {last_sync_result[0]} 이후 변경분")
            else:
                # 동기화 기록 없으면 최근 7일
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                logger.info("🔄 동기화 기록 없음: 최근 7일 데이터")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        conn.close()
        
        total_synced = 0
        total_updated = 0
        
        for site_name in safe_site_servers.keys():
            try:
                logger.info(f"Syncing incidents from {site_name}...")
                
                # MANAD 데이터 가져오기 (DB 직접 접속 또는 API)
                # system_settings 테이블 우선 확인, 없으면 환경 변수 확인
                use_db_direct = False
                try:
                    cursor_check = conn.cursor()
                    cursor_check.execute("""
                        SELECT value FROM system_settings 
                        WHERE key = 'USE_DB_DIRECT_ACCESS'
                    """)
                    result = cursor_check.fetchone()
                    if result and result[0]:
                        use_db_direct = result[0].lower() == 'true'
                    else:
                        # DB에 없으면 환경 변수 확인
                        use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
                except:
                    # 오류 시 환경 변수만 확인
                    use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
                
                if use_db_direct:
                    # DB 직접 접속 모드 (fallback 비활성화 - 에러 발생)
                    try:
                        from manad_db_connector import fetch_incidents_with_client_data_from_db
                        logger.info(f"🔌 DB 직접 접속 모드: {site_name} (fallback 비활성화)")
                        incidents_data = fetch_incidents_with_client_data_from_db(
                            site_name, start_date, end_date, 
                            fetch_clients=is_first_sync
                        )
                        # DB 조회 결과가 None인 경우에만 에러 (빈 리스트는 정상)
                        if incidents_data is None:
                            error_msg = f"❌ DB 직접 접속 실패: {site_name} - DB 연결에 실패했습니다."
                            logger.error(error_msg)
                            raise Exception(error_msg)
                        
                        # Incident가 0개인 경우는 정상 (해당 기간에 Incident가 없을 수 있음)
                        incident_count = len(incidents_data.get('incidents', []))
                        if incident_count == 0:
                            logger.info(f"📭 {site_name}: 최근 {(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days}일간 Incident 없음 (정상)")
                    except Exception as db_error:
                        error_msg = f"❌ DB 직접 접속 실패: {site_name} - {str(db_error)}. DB 연결 설정 및 드라이버 설치를 확인하세요."
                        logger.error(error_msg)
                        raise Exception(error_msg)
                else:
                    # 기존 API 방식
                    logger.info(f"🌐 API 모드: {site_name}")
                    try:
                        incidents_data = fetch_incidents_with_client_data(
                            site_name, start_date, end_date, 
                            fetch_clients=is_first_sync
                        )
                    except Exception as api_error:
                        logger.error(f"❌ API 조회 실패 - {site_name}: {api_error}")
                        continue
                
                if not incidents_data or 'incidents' not in incidents_data:
                    logger.warning(f"No incident data from {site_name}")
                    continue
                
                incidents = incidents_data.get('incidents', [])
                clients = incidents_data.get('clients', [])
                
                # 클라이언트 데이터 캐싱 (첫 동기화 또는 하루 경과 시)
                conn_temp = get_db_connection()
                cursor_temp = conn_temp.cursor()
                
                # 마지막 클라이언트 캐시 시간 확인
                cursor_temp.execute("""
                    SELECT MAX(last_synced) FROM clients_cache 
                    WHERE site = ?
                """, (site_name,))
                last_client_sync = cursor_temp.fetchone()[0]
                
                should_cache_clients = is_first_sync
                if not should_cache_clients and last_client_sync:
                    try:
                        last_client_sync_dt = datetime.fromisoformat(last_client_sync)
                        hours_since = (datetime.now() - last_client_sync_dt).total_seconds() / 3600
                        should_cache_clients = hours_since >= 24  # 하루 경과
                    except:
                        should_cache_clients = True
                else:
                    should_cache_clients = True
                
                if should_cache_clients and clients:
                    logger.info(f"💾 클라이언트 캐시 업데이트: {site_name} ({len(clients)}명)")
                    _cache_clients_to_db(clients, site_name, cursor_temp)
                    conn_temp.commit()
                
                # 클라이언트 데이터를 딕셔너리로 변환 (빠른 검색용)
                # 1. 먼저 API에서 받은 데이터 사용 (최신)
                clients_dict = {client.get('id', client.get('Id', '')): client for client in clients}
                
                # 2. API에 없는 경우 로컬 캐시에서 보완
                cursor_temp.execute("""
                    SELECT client_record_id, first_name, surname 
                    FROM clients_cache 
                    WHERE site = ? AND is_active = 1
                """, (site_name,))
                cached_clients = cursor_temp.fetchall()
                for cached in cached_clients:
                    client_id, first_name, surname = cached
                    if client_id not in clients_dict:
                        clients_dict[client_id] = {
                            'Id': client_id,
                            'FirstName': first_name,
                            'LastName': surname
                        }
                
                conn_temp.close()
                logger.info(f"📋 클라이언트 매핑 완료: {len(clients_dict)}명")
                
                conn = get_db_connection()
                cursor = conn.cursor()
                
                for incident in incidents:
                    try:
                        # 인시던트 ID 추출 (MANAD API uses capital 'Id')
                        incident_id = str(incident.get('Id', ''))
                        if not incident_id:
                            continue
                        
                        # 거주자 정보 가져오기
                        resident_id = incident.get('ClientId', '')
                        resident_name = 'Unknown'
                        
                        # Try to get name from incident data first
                        first_name = incident.get('FirstName', '')
                        last_name = incident.get('LastName', '')
                        if first_name and last_name:
                            resident_name = f"{first_name} {last_name}".strip()
                        elif resident_id and resident_id in clients_dict:
                            # Fallback to client data (use capital FirstName/LastName)
                            client = clients_dict[resident_id]
                            first = client.get('FirstName', '')
                            last = client.get('LastName', '')
                            if first or last:
                                resident_name = f"{first} {last}".strip()
                        
                        # 인시던트 날짜 파싱
                        incident_date_str = incident.get('Date', incident.get('ReportedDate', ''))
                        try:
                            # ISO 형식으로 변환
                            if incident_date_str:
                                incident_date = datetime.fromisoformat(incident_date_str.replace('Z', '+00:00'))
                                incident_date_iso = incident_date.isoformat()
                            else:
                                incident_date_iso = datetime.now().isoformat()
                        except:
                            incident_date_iso = datetime.now().isoformat()
                        
                        # 이미 존재하는지 확인 (MANAD incident ID 기준)
                        cursor.execute("""
                            SELECT id, status FROM cims_incidents 
                            WHERE manad_incident_id = ?
                        """, (incident_id,))
                        
                        existing = cursor.fetchone()
                        
                        if existing:
                            # 기존 인시던트 업데이트 (Open 상태만)
                            existing_db_id = existing[0]
                            if existing[1] == 'Open':
                                # Prepare incident type
                                event_types = incident.get('EventTypeNames', [])
                                incident_type_str = ', '.join(event_types) if isinstance(event_types, list) else str(event_types)
                                
                                cursor.execute("""
                                    UPDATE cims_incidents
                                    SET incident_type = ?,
                                        severity = ?,
                                        description = ?,
                                        initial_actions_taken = ?,
                                        reported_by_name = ?,
                                        resident_name = ?,
                                        incident_date = ?
                                    WHERE manad_incident_id = ?
                                """, (
                                    incident_type_str if incident_type_str else 'Unknown',
                                    incident.get('SeverityRating') or incident.get('RiskRatingName') or 'Unknown',  # Default to 'Unknown' if both are None
                                    incident.get('Description', ''),
                                    incident.get('ActionTaken', ''),
                                    incident.get('ReportedByName', ''),
                                    resident_name,
                                    incident_date_iso,
                                    incident_id
                                ))
                                total_updated += 1
                                
                                # 🚀 Fall incident인 경우 타스크가 없으면 자동 생성
                                if 'fall' in incident_type_str.lower():
                                    # 타스크 존재 여부 확인
                                    cursor.execute("""
                                        SELECT COUNT(*) FROM cims_tasks 
                                        WHERE incident_id = ?
                                    """, (existing_db_id,))
                                    task_count = cursor.fetchone()[0]
                                    
                                    if task_count == 0:
                                        try:
                                            tasks_created = auto_generate_fall_tasks(existing_db_id, incident_date_iso, cursor)
                                            if tasks_created > 0:
                                                logger.info(f"✅ Auto-generated {tasks_created} tasks for existing Fall incident {existing_db_id}")
                                        except Exception as task_error:
                                            logger.error(f"Failed to auto-generate tasks for existing incident {existing_db_id}: {str(task_error)}")
                        else:
                            # 새 인시던트 생성
                            cims_incident_id = f"INC-{incident_id}"
                            
                            # 방 정보 추출
                            room = incident.get('RoomName', '')
                            wing = incident.get('WingName', '')
                            department = incident.get('DepartmentName', '')
                            location_parts = [p for p in [room, wing, department] if p]
                            location = ', '.join(location_parts) if location_parts else 'Unknown'
                            
                            # 인시던트 타입 처리 (리스트일 수 있음)
                            event_types = incident.get('EventTypeNames', [])
                            incident_type = ', '.join(event_types) if isinstance(event_types, list) else str(event_types)
                            
                            # Use 0 as reported_by for MANAD-synced incidents (system user)
                            cursor.execute("""
                                INSERT INTO cims_incidents (
                                    incident_id, manad_incident_id, resident_id, resident_name, 
                                    incident_type, severity, status, incident_date, 
                                    location, description, initial_actions_taken, 
                                    reported_by, reported_by_name, site, created_at,
                                    risk_rating, is_review_closed, is_ambulance_called,
                                    is_admitted_to_hospital, is_major_injury, reviewed_date, status_enum_id
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                cims_incident_id,
                                incident_id,
                                str(resident_id),
                                resident_name,
                                incident_type if incident_type else 'Unknown',
                                incident.get('SeverityRating') or 'Unknown',
                                incident.get('Status', 'Open'),
                                incident_date_iso,
                                location,
                                incident.get('Description', ''),
                                incident.get('ActionTaken', ''),
                                0,  # System user ID for MANAD-synced incidents
                                incident.get('ReportedByName', ''),
                                site_name,
                                datetime.now().isoformat(),
                                incident.get('RiskRatingName', ''),
                                1 if incident.get('IsReviewClosed') else 0,
                                1 if incident.get('IsAmbulanceCalled') else 0,
                                1 if incident.get('IsAdmittedToHospital') else 0,
                                1 if incident.get('IsMajorInjury') else 0,
                                incident.get('ReviewedDate'),
                                incident.get('StatusEnumId')
                            ))
                            total_synced += 1
                            
                            # 🚀 NEW: Fall incident인 경우 자동으로 task 생성
                            new_incident_db_id = cursor.lastrowid
                            if 'fall' in incident_type.lower():
                                try:
                                    tasks_created = auto_generate_fall_tasks(new_incident_db_id, incident_date_iso, cursor)
                                    if tasks_created > 0:
                                        logger.info(f"✅ Auto-generated {tasks_created} tasks for Fall incident {cims_incident_id}")
                                except Exception as task_error:
                                    logger.error(f"Failed to auto-generate tasks for {cims_incident_id}: {str(task_error)}")
                    
                    except Exception as e:
                        logger.error(f"Error processing incident {incident.get('Id', 'unknown')}: {str(e)}")
                        continue
                
                conn.commit()
                
                # 사이트별 마지막 동기화 시간 업데이트
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                """, (
                    f'last_sync_{site_name.lower().replace(" ", "_")}',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
                conn.close()
                
                logger.info(f"✅ {site_name}: {total_synced} new, {total_updated} updated")
                
            except Exception as e:
                logger.error(f"Error syncing incidents from {site_name}: {str(e)}")
                continue
        
        logger.info(f"Incident sync completed: {total_synced} new, {total_updated} updated")
        
        # 🚀 백그라운드 싱크 완료 후 타스크가 없는 Fall 인시던트에 대해 타스크 생성
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 타스크가 없는 Open 상태의 Fall 인시던트 조회
            cursor.execute("""
                SELECT i.id, i.incident_id, i.incident_date, i.incident_type
                FROM cims_incidents i
                LEFT JOIN cims_tasks t ON i.id = t.incident_id
                WHERE i.status = 'Open'
                AND LOWER(i.incident_type) LIKE '%fall%'
                AND t.id IS NULL
                ORDER BY i.incident_date DESC
                LIMIT 50
            """)
            
            fall_incidents_without_tasks = cursor.fetchall()
            
            if fall_incidents_without_tasks:
                logger.info(f"🔍 {len(fall_incidents_without_tasks)}개 Fall 인시던트에 타스크가 없음 - 자동 생성 시작...")
                tasks_generated = 0
                
                for incident_row in fall_incidents_without_tasks:
                    incident_db_id = incident_row[0]
                    incident_id = incident_row[1]
                    incident_date_iso = incident_row[2]
                    incident_type = incident_row[3]
                    
                    try:
                        num_tasks = auto_generate_fall_tasks(incident_db_id, incident_date_iso, cursor)
                        if num_tasks > 0:
                            tasks_generated += num_tasks
                            logger.info(f"✅ Incident {incident_id}: {num_tasks} tasks 생성됨")
                    except Exception as task_error:
                        logger.warning(f"⚠️ Incident {incident_id} task 생성 실패: {task_error}")
                
                if tasks_generated > 0:
                    conn.commit()
                    logger.info(f"✅ 총 {tasks_generated}개 tasks 생성 완료")
                else:
                    conn.rollback()
            
            conn.close()
        except Exception as task_gen_error:
            logger.error(f"❌ 백그라운드 타스크 생성 중 오류: {task_gen_error}")
        
        return {'success': True, 'synced': total_synced, 'updated': total_updated}
        
    except Exception as e:
        logger.error(f"Error in sync_incidents_from_manad_to_cims: {str(e)}")
        return {'success': False, 'error': str(e)}

@app.route('/api/cims/force-sync', methods=['POST'])
@login_required
def force_sync_all():
    """
    Force Synchronization - 전체 DB 강제 동기화
    - 모든 사이트에서 incident 동기화
    - Fall incident에 대해 누락된 task 자동 생성
    - Progress note 동기화
    - Incident status 업데이트
    
    Admin/Clinical Manager만 사용 가능
    """
    try:
        if not (current_user.is_admin() or current_user.role == 'clinical_manager'):
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        logger.info(f"🔄 Force Sync initiated by {current_user.username}")
        
        # 1. Full incident sync (30 days)
        logger.info("1️⃣  Full incident sync (30 days)...")
        sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
        
        # 2. Check for Fall incidents without tasks and generate them
        logger.info("2️⃣  Checking for Fall incidents without tasks...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.id, i.incident_id, i.incident_date, i.incident_type
            FROM cims_incidents i
            WHERE i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            AND NOT EXISTS (
                SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id
            )
        """)
        
        incidents_without_tasks = cursor.fetchall()
        tasks_generated = 0
        
        for inc in incidents_without_tasks:
            try:
                num_tasks = auto_generate_fall_tasks(inc[0], inc[2], cursor)
                tasks_generated += num_tasks
                logger.info(f"✅ Generated {num_tasks} tasks for {inc[1]}")
            except Exception as e:
                logger.error(f"Failed to generate tasks for {inc[1]}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Generated {tasks_generated} tasks for {len(incidents_without_tasks)} incidents")
        
        # 3. Progress note sync
        logger.info("3️⃣  Progress note sync...")
        # Progress Note 동기화는 일시적으로 비활성화됨 (나중에 DB 직접 접속으로 재구현 예정)
        # pn_sync_result = sync_progress_notes_from_manad_to_cims()
        
        # 4. Update incident statuses
        logger.info("4️⃣  Updating incident statuses...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT i.id
            FROM cims_incidents i
            JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.status IN ('Open', 'Overdue')
        """)
        
        incidents_to_update = cursor.fetchall()
        updated_count = 0
        
        for inc in incidents_to_update:
            try:
                check_and_update_incident_status(inc[0])
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update status for incident {inc[0]}: {str(e)}")
        
        conn.close()
        
        logger.info(f"✅ Updated status for {updated_count} incidents")
        
        return jsonify({
            'success': True,
            'message': 'Force sync completed successfully',
            'details': {
                'incidents_synced': sync_result.get('synced', 0),
                'incidents_updated': sync_result.get('updated', 0),
                'tasks_generated': tasks_generated,
                'incidents_with_new_tasks': len(incidents_without_tasks),
                'statuses_updated': updated_count
            }
        })
        
    except Exception as e:
        logger.error(f"Force sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_cims_incidents():
    """Open 상태 인시던트 목록 조회 (자동 동기화 포함)"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        # 요청 파라미터 확인
        force_sync = request.args.get('sync', 'false').lower() == 'true'
        full_sync = request.args.get('full', 'false').lower() == 'true'  # 전체 동기화 (30일)
        
        # 마지막 동기화 시간 확인 (읽기 전용 연결로 잠금 충돌 방지)
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        # 인시던트 개수 확인 (초기 로드 감지)
        cursor.execute("SELECT COUNT(*) FROM cims_incidents")
        incident_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'last_incident_sync_time'
        """)
        last_sync_result = cursor.fetchone()
        
        # 자동 초기 동기화 조건:
        # 1. Force sync 요청
        # 2. 또는 인시던트가 하나도 없고 한 번도 동기화하지 않았을 때
        should_sync = force_sync or (incident_count == 0 and not last_sync_result)
        
        # 초기 동기화인 경우 전체 동기화로 전환
        if incident_count == 0 and not last_sync_result and should_sync:
            full_sync = True
            logger.info(f"🆕 초기 로드 감지 - 자동 전체 동기화 시작 (인시던트: {incident_count}개)")
        
        # 필요시 동기화 실행 (백그라운드로)
        if should_sync:
            # 동기화 시간 먼저 업데이트 (중복 실행 방지)
            # 쓰기가 필요한 시점에만 쓰기 연결 사용
            conn.close()
            conn = get_db_connection(read_only=False)
            cursor = conn.cursor()
            with write_lock():
                cursor.execute("""
                    INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                    VALUES ('last_incident_sync_time', ?, ?)
                """, (datetime.now().isoformat(), datetime.now().isoformat()))
                conn.commit()
            
            # 백그라운드 스레드로 동기화 실행 (페이지 로딩 차단하지 않음)
            import threading
            def background_sync():
                try:
                    sync_type = "전체 동기화 (30일)" if full_sync else "증분 동기화"
                    logger.info(f"🔄 백그라운드 동기화 시작: {sync_type}")
                    sync_result = sync_incidents_from_manad_to_cims(full_sync=full_sync)
                    
                    # Progress Note 동기화는 일시적으로 비활성화됨 (나중에 DB 직접 접속으로 재구현 예정)
                    # logger.info(f"🔄 Progress Note 동기화 시작...")
                    # pn_sync_result = sync_progress_notes_from_manad_to_cims()
                    
                    logger.info(f"✅ 백그라운드 동기화 완료: Incidents={sync_result}")
                except Exception as e:
                    logger.error(f"❌ 백그라운드 동기화 오류: {e}")
            
            sync_thread = threading.Thread(target=background_sync, daemon=True)
            sync_thread.start()
            logger.info(f"⚡ 백그라운드 동기화 시작됨 (페이지 로딩은 즉시 계속...)")
        
        # 필터 파라미터 확인
        site_filter = request.args.get('site')
        date_filter = request.args.get('date')
        
        # DB 직접 접속 모드 확인
        use_db_direct = False
        try:
            conn_check = get_db_connection(read_only=True)
            cursor_check = conn_check.cursor()
            cursor_check.execute("SELECT value FROM system_settings WHERE key = 'USE_DB_DIRECT_ACCESS'")
            result = cursor_check.fetchone()
            conn_check.close()
            
            if result and result[0]:
                use_db_direct = result[0].lower() == 'true'
            else:
                use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        except:
            use_db_direct = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower() == 'true'
        
        incidents = []
        
        if use_db_direct:
            # 🔌 DB 직접 접속 모드: MANAD DB에서 최신 인시던트 조회
            logger.info(f"🔌 DB 직접 접속 모드: integrated_dashboard 인시던트 조회")
            
            try:
                from manad_db_connector import fetch_incidents_with_client_data_from_db
                
                # 날짜 범위 설정 (최근 30일, 또는 필터에 따라)
                if date_filter:
                    date_obj = datetime.fromisoformat(date_filter)
                    five_days_before = date_obj - timedelta(days=5)
                    start_date = five_days_before.strftime('%Y-%m-%d')
                else:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                end_date = datetime.now().strftime('%Y-%m-%d')
                
                # 사이트별로 조회
                safe_site_servers = get_safe_site_servers()
                sites_to_query = [site_filter] if site_filter else list(safe_site_servers.keys())
                
                all_manad_incidents = []
                for site_name in sites_to_query:
                    if site_name not in safe_site_servers:
                        continue
                    
                    try:
                        incidents_data = fetch_incidents_with_client_data_from_db(
                            site_name, start_date, end_date, fetch_clients=False
                        )
                        
                        if incidents_data and incidents_data.get('incidents'):
                            for inc in incidents_data['incidents']:
                                # MANAD 인시던트를 CIMS 형식으로 변환
                                incident_date_str = inc.get('Date', inc.get('ReportedDate', ''))
                                if incident_date_str:
                                    try:
                                        incident_date = datetime.fromisoformat(incident_date_str.replace('Z', '+00:00'))
                                        incident_date_iso = incident_date.isoformat()
                                    except:
                                        incident_date_iso = datetime.now().isoformat()
                                else:
                                    incident_date_iso = datetime.now().isoformat()
                                
                                # CIMS DB에서 기존 인시던트 조회 (Task 정보 포함)
                                conn_cims = get_db_connection(read_only=True)
                                cursor_cims = conn_cims.cursor()
                                cursor_cims.execute("""
                                    SELECT id, incident_id, status, fall_type
                                    FROM cims_incidents
                                    WHERE manad_incident_id = ?
                                """, (str(inc.get('Id', '')),))
                                existing = cursor_cims.fetchone()
                                conn_cims.close()
                                
                                # Status 결정: CIMS DB에 있으면 그 상태 사용, 없으면 Open
                                status = existing[2] if existing else 'Open'
                                cims_id = existing[0] if existing else None
                                fall_type = existing[3] if existing and len(existing) > 3 else None
                                
                                # Open 상태만 필터링
                                if status != 'Open':
                                    continue
                                
                                # 인시던트 타입 처리
                                event_type = inc.get('EventTypeNames', '')
                                if isinstance(event_type, list):
                                    incident_type = ', '.join(event_type)
                                else:
                                    incident_type = str(event_type) if event_type else 'Unknown'
                                
                                # 위치 정보
                                room = inc.get('RoomName', '')
                                wing = inc.get('WingName', '')
                                dept = inc.get('DepartmentName', '')
                                location_parts = [p for p in [room, wing, dept] if p]
                                location = ', '.join(location_parts) if location_parts else 'Unknown'
                                
                                # 거주자 이름
                                resident_name = f"{inc.get('FirstName', '')} {inc.get('LastName', '')}".strip()
                                if not resident_name:
                                    resident_name = 'Unknown'
                                
                                # CIMS 형식의 튜플로 변환 (기존 코드와 호환)
                                incidents.append((
                                    cims_id,  # id (CIMS DB ID, 없으면 None)
                                    f"INC-{inc.get('Id', '')}",  # incident_id
                                    str(inc.get('ClientId', '')),  # resident_id
                                    resident_name,  # resident_name
                                    incident_type,  # incident_type
                                    inc.get('SeverityRating') or inc.get('RiskRatingName') or 'Unknown',  # severity
                                    status,  # status
                                    incident_date_iso,  # incident_date
                                    location,  # location
                                    inc.get('Description', ''),  # description
                                    site_name,  # site
                                    datetime.now().isoformat()  # created_at (임시)
                                ))
                    except Exception as site_error:
                        logger.error(f"❌ {site_name} 인시던트 조회 실패: {site_error}")
                        continue
                
                logger.info(f"✅ DB 직접 접속: {len(incidents)}개 인시던트 조회 완료")
                
            except Exception as db_error:
                logger.error(f"❌ DB 직접 접속 실패: {db_error}")
                # Fallback: CIMS DB에서 조회
                use_db_direct = False
        
        if not use_db_direct:
            # 🌐 API 모드 또는 Fallback: CIMS DB에서 조회
            query = """
                SELECT id, incident_id, resident_id, resident_name, incident_type, severity, status, 
                       incident_date, location, description, site, created_at
                FROM cims_incidents 
                WHERE status = 'Open'
            """
            params = []
            
            if site_filter:
                query += " AND site = ?"
                params.append(site_filter)
            
            if date_filter:
                date_obj = datetime.fromisoformat(date_filter)
                five_days_before = (date_obj - timedelta(days=5)).isoformat()
                query += " AND incident_date >= ?"
                params.append(five_days_before)
            
            query += " ORDER BY incident_date DESC LIMIT 500"
            
            # 조회는 읽기 전용 연결로 재수행 + 간단 재시도
            try:
                conn.close()
            except Exception:
                pass
            conn = get_db_connection(read_only=True)
            cursor = conn.cursor()
            for attempt in range(5):
                try:
                    cursor.execute(query, params)
                    break
                except sqlite3.OperationalError as e:
                    if 'database is locked' in str(e) and attempt < 4:
                        time.sleep(0.25 * (attempt + 1))
                        continue
                    logger.error("Open 인시던트 조회 오류: database is locked (fallback)")
                    return jsonify({'incidents': [], 'stale': True}), 200
            
            incidents = cursor.fetchall()
            conn.close()
        
        # Convert to list of dictionaries (프론트엔드 호환 필드명 사용)
        result = []
        
        # Fall 유형 감지를 위한 cursor 생성
        conn_fall = get_db_connection(read_only=True)
        try:
            cursor_fall = conn_fall.cursor()
            
            for incident in incidents:
                # incident_type을 EventTypeNames 배열로 변환
                incident_types = incident[4].split(', ') if incident[4] else []
                
                # Fall 유형 감지 (Fall incident인 경우만)
                fall_type = None
                if incident[4] and 'fall' in incident[4].lower():
                    from services.fall_policy_detector import fall_detector
                    
                    # CIMS DB ID가 있는 경우 DB에서 조회
                    if incident[0] is not None:  # cims_id가 있는 경우
                        fall_type = fall_detector.detect_fall_type_from_incident(
                            incident[0],  # incident_id (CIMS DB ID)
                            cursor_fall
                        )
                        
                        # 계산된 fall_type을 DB에 저장
                        if fall_type and fall_type != 'unknown':
                            try:
                                cursor_fall.execute("""
                                    UPDATE cims_incidents
                                    SET fall_type = ?
                                    WHERE id = ? AND (fall_type IS NULL OR fall_type = '')
                                """, (fall_type, incident[0]))
                                cursor_fall.connection.commit()
                            except:
                                pass
                    else:
                        # CIMS DB ID가 없는 경우 (DB 직접 접속 모드에서 새 인시던트)
                        # Description에서 직접 감지
                        description = incident[9] if len(incident) > 9 else ''
                        fall_type = fall_detector.detect_fall_type_from_notes(description) if description else 'unknown'
                
                result.append({
                    'id': incident[0],
                    'incident_id': incident[1],
                    'resident_id': incident[2],
                    'resident_name': incident[3],
                    'incident_type': incident[4],  # 하위 호환성
                    'EventTypeNames': incident_types,  # 프론트엔드가 기대하는 형식
                    'severity': incident[5],
                    'status': incident[6],
                    'incident_date': incident[7],
                    'location': incident[8],
                    'description': incident[9],
                    'site': incident[10],  # 하위 호환성
                    'SiteName': incident[10],  # 프론트엔드가 기대하는 형식
                    'created_at': incident[11],
                    'fall_type': fall_type  # Fall 유형 정보 추가
                })
        finally:
            conn_fall.close()
        
        logger.info(f"📤 API 응답: {len(result)}개 Open 인시던트 반환")
        return jsonify({'incidents': result, 'stale': False})
        
    except Exception as e:
        logger.error(f"Open 인시던트 조회 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def create_cims_incident():
    """새 인시던트 생성 API"""
    try:
        if not current_user.can_manage_incidents():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['resident_id', 'resident_name', 'incident_type', 'severity', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 인시던트 ID 생성
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # 인시던트 저장
        cursor.execute("""
            INSERT INTO cims_incidents (
                incident_id, resident_id, resident_name, incident_type, severity,
                status, incident_date, location, description, initial_actions_taken,
                witnesses, reported_by, site, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_id,
            data['resident_id'],
            data['resident_name'],
            data['incident_type'],
            data['severity'],
            'Open',
            datetime.now().isoformat(),
            data.get('location', ''),
            data['description'],
            data.get('initial_actions', ''),
            data.get('witnesses', ''),
            current_user.id,
            data.get('site', 'Unknown'),
            datetime.now().isoformat()
        ))
        
        incident_db_id = cursor.lastrowid
        conn.commit()
        
        # 인시던트 데이터 준비
        incident_data = {
            'id': incident_db_id,
            'incident_id': incident_id,
            'type': data['incident_type'],
            'severity': data['severity'],
            'incident_date': datetime.now().isoformat(),
            'resident_id': data['resident_id'],
            'resident_name': data['resident_name']
        }
        
        # 정책 엔진을 통해 태스크 자동 생성
        generated_tasks = policy_engine.apply_policies_to_incident(incident_data)
        
        # 감사 로그 추가
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'incident_created',
            'incident',
            incident_db_id,
            json.dumps({
                'incident_type': data['incident_type'],
                'severity': data['severity'],
                'tasks_generated': len(generated_tasks)
            })
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'tasks_generated': len(generated_tasks),
            'message': f'Incident created successfully with {len(generated_tasks)} tasks generated'
        })
        
    except Exception as e:
        logger.error(f"CIMS 인시던트 생성 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_cims_task(task_id):
    """태스크 완료 API"""
    try:
        if not current_user.can_complete_tasks():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        completion_notes = data.get('notes', '')
        
        # 태스크 완료 처리
        success = policy_engine.complete_task(task_id, current_user.id, completion_notes)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to complete task'
            }), 500
        
    except Exception as e:
        logger.error(f"CIMS 태스크 완료 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/progress-notes', methods=['POST'])
@login_required
def create_cims_progress_note():
    """진행 노트 생성 API"""
    try:
        if not current_user.can_complete_tasks():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['incident_id', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 진행 노트 ID 생성
        note_id = f"NOTE-{uuid.uuid4().hex[:8].upper()}"
        
        # 진행 노트 저장
        cursor.execute("""
            INSERT INTO cims_progress_notes (
                note_id, incident_id, task_id, author_id, content, note_type,
                vitals_data, assessment_data, attachments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id,
            data['incident_id'],
            data.get('task_id'),
            current_user.id,
            data['content'],
            data.get('note_type', ''),
            json.dumps(data.get('vitals_data', {})),
            json.dumps(data.get('assessment_data', {})),
            json.dumps(data.get('attachments', [])),
            datetime.now().isoformat()
        ))
        
        note_db_id = cursor.lastrowid
        
        # task_id가 있으면 해당 태스크를 완료 처리
        if data.get('task_id'):
            completed_at = datetime.now().isoformat()
            cursor.execute("""
                UPDATE cims_tasks
                SET status = 'completed',
                    completed_by_user_id = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (current_user.id, completed_at, completed_at, data['task_id']))
            
            logger.info(f"✅ Task {data['task_id']} marked as completed via progress note")
        
        # 감사 로그 추가
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'progress_note_created',
            'progress_note',
            note_db_id,
            json.dumps({
                'incident_id': data['incident_id'],
                'task_id': data.get('task_id'),
                'note_type': data.get('note_type', '')
            })
        ))
        
        conn.commit()
        conn.close()
        
        # 인시던트 상태 업데이트 체크
        if data.get('task_id'):
            check_and_update_incident_status(data['incident_id'])
        
        return jsonify({
            'success': True,
            'note_id': note_id,
            'message': 'Progress note created successfully'
        })
        
    except Exception as e:
        logger.error(f"CIMS 진행 노트 생성 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def check_and_update_incident_status(incident_id):
    """
    인시던트의 모든 태스크 상태를 확인하고 인시던트 상태를 업데이트
    - 모든 태스크가 완료되면 'Closed'로 변경
    - 마지막 태스크 마감 시간이 지났는데 미완료 태스크가 있으면 'Overdue'로 변경
    - DB 잠금 시 재시도 로직 포함
    """
    import time
    import sqlite3
    
    max_retries = 3
    retry_delay = 0.5  # 0.5초부터 시작
    
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            conn.execute("PRAGMA busy_timeout = 5000")  # 5초 타임아웃 설정
            cursor = conn.cursor()
            
            # 해당 인시던트의 모든 태스크 조회
            cursor.execute("""
                SELECT id, status, due_date
                FROM cims_tasks
                WHERE incident_id = ?
                ORDER BY due_date DESC
            """, (incident_id,))
            tasks = cursor.fetchall()
            
            if not tasks:
                conn.close()
                return
            
            # 태스크 상태 분석
            all_completed = all(task[1] == 'completed' for task in tasks)
            now = datetime.now()
            last_task_due = datetime.fromisoformat(tasks[0][2]) if tasks[0][2] else None
            
            # 인시던트 상태 업데이트
            if all_completed:
                # 모든 태스크 완료 → Closed
                cursor.execute("""
                    UPDATE cims_incidents
                    SET status = 'Closed'
                    WHERE id = ?
                """, (incident_id,))
                logger.info(f"✅ Incident {incident_id} closed: All tasks completed")
            elif last_task_due and now > last_task_due and not all_completed:
                # 마지막 태스크 마감 시간 지났는데 미완료 → Overdue
                cursor.execute("""
                    UPDATE cims_incidents
                    SET status = 'Overdue'
                    WHERE id = ?
                """, (incident_id,))
                logger.info(f"⏰ Incident {incident_id} marked as overdue")
            
            conn.commit()
            conn.close()
            return  # 성공 시 종료
            
        except sqlite3.OperationalError as e:
            if 'database is locked' in str(e) and attempt < max_retries - 1:
                logger.warning(f"⏳ 인시던트 상태 업데이트 재시도 ({attempt + 1}/{max_retries}): Incident {incident_id} - DB 잠금")
                time.sleep(retry_delay)
                retry_delay *= 2  # 지수 백오프
                continue
            else:
                logger.error(f"인시던트 상태 업데이트 오류: Incident {incident_id} - {str(e)}")
                return
        except Exception as e:
            logger.error(f"인시던트 상태 업데이트 오류: Incident {incident_id} - {str(e)}")
            return

@app.route('/api/cims/dashboard-kpis')
@login_required
def get_dashboard_kpis():
    """
    대시보드 KPI 계산 API (SQL 최적화 버전)
    
    개선사항:
    - N+1 쿼리 문제 해결 (SQL로 한 번에 계산)
    - Overdue Tasks: 실제 Task 개수 카운트 (Incident 개수 아님)
    - 3단계 Incident 상태 구분: Open / In Progress / Completed
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        # 필터 파라미터
        period = request.args.get('period', 'week')  # today, week, month
        incident_type = request.args.get('incident_type', 'all')  # all, Fall, Wound/Skin, etc.
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기간 필터
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        # 사고 유형 필터 조건 생성
        type_filter = ""
        type_params = []
        
        if incident_type != 'all':
            if incident_type == 'fall':
                type_filter = "AND LOWER(i.incident_type) LIKE ?"
                type_params.append('%fall%')
            elif incident_type == 'wound':
                type_filter = "AND (LOWER(i.incident_type) LIKE ? OR LOWER(i.incident_type) LIKE ?)"
                type_params.extend(['%wound%', '%skin%'])
            elif incident_type == 'medication':
                type_filter = "AND LOWER(i.incident_type) LIKE ?"
                type_params.append('%medication%')
            elif incident_type == 'behaviour':
                type_filter = "AND (LOWER(i.incident_type) LIKE ? OR LOWER(i.incident_type) LIKE ?)"
                type_params.extend(['%behaviour%', '%behavior%'])
            elif incident_type == 'other':
                type_filter = """
                    AND LOWER(i.incident_type) NOT LIKE '%fall%'
                    AND LOWER(i.incident_type) NOT LIKE '%wound%'
                    AND LOWER(i.incident_type) NOT LIKE '%skin%'
                    AND LOWER(i.incident_type) NOT LIKE '%medication%'
                    AND LOWER(i.incident_type) NOT LIKE '%behaviour%'
                    AND LOWER(i.incident_type) NOT LIKE '%behavior%'
                """
        
        # ==========================================
        # 1. Incident 상태 통계 (status_enum_id 기반)
        # StatusEnumId: 0=Open, 1=InProgress, 2=Closed
        # ==========================================
        incident_stats_query = f"""
            SELECT 
                COUNT(*) as total_incidents,
                
                -- Open Incidents: status_enum_id = 0
                SUM(CASE WHEN status_enum_id = 0 THEN 1 ELSE 0 END) as open_incidents,
                
                -- In Progress Incidents: status_enum_id = 1
                SUM(CASE WHEN status_enum_id = 1 THEN 1 ELSE 0 END) as in_progress_incidents,
                
                -- Closed Incidents: status_enum_id = 2
                SUM(CASE WHEN status_enum_id = 2 THEN 1 ELSE 0 END) as closed_incidents
                
            FROM cims_incidents i
            WHERE i.incident_date >= ?
            {type_filter}
        """
        
        cursor.execute(incident_stats_query, [start_date.isoformat()] + type_params)
        incident_stats = cursor.fetchone()
        
        # ==========================================
        # 2. Fall 카운트
        # ==========================================
        fall_query = f"""
            SELECT COUNT(*) as fall_count
            FROM cims_incidents i
            WHERE i.incident_date >= ?
            AND LOWER(i.incident_type) LIKE '%fall%'
            {type_filter}
        """
        
        cursor.execute(fall_query, [start_date.isoformat()] + type_params)
        fall_result = cursor.fetchone()
        fall_count = fall_result['fall_count'] if fall_result else 0
        
        # ==========================================
        # 3. Compliance Rate 계산 (Closed / Total * 100)
        # ==========================================
        total_incidents = incident_stats['total_incidents'] or 0
        closed_incidents = incident_stats['closed_incidents'] or 0
        
        if total_incidents > 0:
            compliance_rate = round((closed_incidents / total_incidents) * 100, 1)
        else:
            compliance_rate = 0
        
        conn.close()
        
        # ==========================================
        # 4. 응답 반환
        # ==========================================
        return jsonify({
            'total_incidents': incident_stats['total_incidents'] or 0,
            'closed_incidents': incident_stats['closed_incidents'] or 0,
            'open_incidents': incident_stats['open_incidents'] or 0,
            'in_progress_incidents': incident_stats['in_progress_incidents'] or 0,
            'fall_count': fall_count,
            'compliance_rate': compliance_rate,
            'period': period,
            'incident_type': incident_type
        })
        
    except Exception as e:
        logger.error(f"Dashboard KPI 조회 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/cims/dashboard-stats')
@login_required
def get_dashboard_stats():
    """
    Dashboard 통계 API - 차트용 데이터
    
    반환 데이터:
    - 전체 사이트 통계: 이벤트 유형, Risk Rating, Severity Rating 분포
    - 사이트별 통계: Open/Closed, Reviewed 현황
    - 추가 KPI: Ambulance, Hospital, Major Injury 등
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        period = request.args.get('period', 'week')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 기간 필터
        now = datetime.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        else:  # month
            start_date = now - timedelta(days=30)
        
        # ==========================================
        # 1. 이벤트 유형 분포 (Event Type Distribution)
        # ==========================================
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN LOWER(incident_type) LIKE '%fall%' THEN 'Fall'
                    WHEN LOWER(incident_type) LIKE '%wound%' OR LOWER(incident_type) LIKE '%skin%' THEN 'Wound/Skin'
                    WHEN LOWER(incident_type) LIKE '%medication%' THEN 'Medication'
                    WHEN LOWER(incident_type) LIKE '%behaviour%' OR LOWER(incident_type) LIKE '%behavior%' THEN 'Behaviour'
                    WHEN LOWER(incident_type) LIKE '%danger%' THEN 'Danger'
                    ELSE 'Other'
                END as event_category,
                COUNT(*) as count
            FROM cims_incidents
            WHERE incident_date >= ?
            GROUP BY 
                CASE 
                    WHEN LOWER(incident_type) LIKE '%fall%' THEN 'Fall'
                    WHEN LOWER(incident_type) LIKE '%wound%' OR LOWER(incident_type) LIKE '%skin%' THEN 'Wound/Skin'
                    WHEN LOWER(incident_type) LIKE '%medication%' THEN 'Medication'
                    WHEN LOWER(incident_type) LIKE '%behaviour%' OR LOWER(incident_type) LIKE '%behavior%' THEN 'Behaviour'
                    WHEN LOWER(incident_type) LIKE '%danger%' THEN 'Danger'
                    ELSE 'Other'
                END
            ORDER BY count DESC
        """, [start_date.isoformat()])
        
        event_type_distribution = [{'name': row['event_category'], 'value': row['count']} for row in cursor.fetchall()]
        
        # ==========================================
        # 2. Risk Rating 분포
        # ==========================================
        cursor.execute("""
            SELECT 
                COALESCE(NULLIF(risk_rating, ''), 'Not Set') as risk,
                COUNT(*) as count
            FROM cims_incidents
            WHERE incident_date >= ?
            GROUP BY COALESCE(NULLIF(risk_rating, ''), 'Not Set')
            ORDER BY count DESC
        """, [start_date.isoformat()])
        
        risk_distribution = [{'name': row['risk'], 'value': row['count']} for row in cursor.fetchall()]
        
        # ==========================================
        # 3. Severity Rating 분포
        # ==========================================
        cursor.execute("""
            SELECT 
                COALESCE(NULLIF(severity, ''), 'Not Set') as severity_level,
                COUNT(*) as count
            FROM cims_incidents
            WHERE incident_date >= ?
            GROUP BY COALESCE(NULLIF(severity, ''), 'Not Set')
            ORDER BY count DESC
        """, [start_date.isoformat()])
        
        severity_distribution = [{'name': row['severity_level'], 'value': row['count']} for row in cursor.fetchall()]
        
        # ==========================================
        # 4. 사이트별 Open/Closed 통계
        # ==========================================
        cursor.execute("""
            SELECT 
                site,
                SUM(CASE WHEN status = 'Open' OR status_enum_id = 0 THEN 1 ELSE 0 END) as open_count,
                SUM(CASE WHEN status = 'Closed' OR status_enum_id = 2 THEN 1 ELSE 0 END) as closed_count,
                SUM(CASE WHEN status = 'In Progress' OR status_enum_id = 1 THEN 1 ELSE 0 END) as in_progress_count,
                COUNT(*) as total
            FROM cims_incidents
            WHERE incident_date >= ?
            GROUP BY site
            ORDER BY total DESC
        """, [start_date.isoformat()])
        
        site_status_stats = []
        for row in cursor.fetchall():
            site_status_stats.append({
                'site': row['site'],
                'open': row['open_count'],
                'closed': row['closed_count'],
                'in_progress': row['in_progress_count'],
                'total': row['total']
            })
        
        # ==========================================
        # 5. 사이트별 Review 통계
        # ==========================================
        cursor.execute("""
            SELECT 
                site,
                SUM(CASE WHEN is_review_closed = 1 THEN 1 ELSE 0 END) as reviewed,
                SUM(CASE WHEN is_review_closed = 0 OR is_review_closed IS NULL THEN 1 ELSE 0 END) as not_reviewed,
                COUNT(*) as total
            FROM cims_incidents
            WHERE incident_date >= ?
            GROUP BY site
            ORDER BY total DESC
        """, [start_date.isoformat()])
        
        site_review_stats = []
        for row in cursor.fetchall():
            site_review_stats.append({
                'site': row['site'],
                'reviewed': row['reviewed'],
                'not_reviewed': row['not_reviewed'],
                'total': row['total']
            })
        
        # ==========================================
        # 6. 추가 KPI 통계
        # ==========================================
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN is_ambulance_called = 1 THEN 1 ELSE 0 END) as ambulance_called,
                SUM(CASE WHEN is_admitted_to_hospital = 1 THEN 1 ELSE 0 END) as hospital_admitted,
                SUM(CASE WHEN is_major_injury = 1 THEN 1 ELSE 0 END) as major_injuries,
                SUM(CASE WHEN is_review_closed = 1 THEN 1 ELSE 0 END) as reviewed_count,
                SUM(CASE WHEN is_review_closed = 0 OR is_review_closed IS NULL THEN 1 ELSE 0 END) as pending_review,
                COUNT(*) as total
            FROM cims_incidents
            WHERE incident_date >= ?
        """, [start_date.isoformat()])
        
        additional_kpis = cursor.fetchone()
        
        # ==========================================
        # 7. Fall 전용 통계 (Witnessed vs Unwitnessed)
        # ==========================================
        cursor.execute("""
            SELECT 
                fall_type,
                COUNT(*) as count
            FROM cims_incidents
            WHERE incident_date >= ?
            AND LOWER(incident_type) LIKE '%fall%'
            GROUP BY fall_type
        """, [start_date.isoformat()])
        
        fall_stats = [{'type': row['fall_type'] or 'unknown', 'count': row['count']} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'period': period,
            'event_type_distribution': event_type_distribution,
            'risk_distribution': risk_distribution,
            'severity_distribution': severity_distribution,
            'site_status_stats': site_status_stats,
            'site_review_stats': site_review_stats,
            'additional_kpis': {
                'ambulance_called': additional_kpis['ambulance_called'] or 0,
                'hospital_admitted': additional_kpis['hospital_admitted'] or 0,
                'major_injuries': additional_kpis['major_injuries'] or 0,
                'reviewed_count': additional_kpis['reviewed_count'] or 0,
                'pending_review': additional_kpis['pending_review'] or 0,
                'total': additional_kpis['total'] or 0
            },
            'fall_stats': fall_stats
        })
        
    except Exception as e:
        logger.error(f"Dashboard Stats 조회 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/cims/schedule-batch/<site>/<date>')
@login_required
def get_schedule_batch(site, date):
    """
    🚀 Phase 2: Batch API - 한 번의 호출로 전체 스케줄 반환
    
    Incidents + Tasks + Policy를 한 번에 조회하여 반환
    - Mobile Dashboard 최적화용
    - DB 쿼리 99.9% 감소 (2328 → 3회)
    """
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Incidents + Tasks를 JOIN으로 한 번에 조회
        date_obj = datetime.fromisoformat(date)
        five_days_before = (date_obj - timedelta(days=5)).isoformat()
        
        cursor.execute("""
            SELECT 
                i.id, i.incident_id, i.incident_type, i.incident_date,
                i.resident_name, i.resident_id, i.description,
                i.severity, i.status, i.location, i.site, i.fall_type,
                t.id as task_db_id, t.task_id, t.task_name, t.due_date, 
                t.status as task_status, t.completed_at, t.completed_by_user_id
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.site = ? 
            AND DATE(i.incident_date) >= DATE(?)
            AND i.incident_type LIKE '%Fall%'
            AND i.status IN ('Open', 'Overdue')
            ORDER BY i.incident_date DESC, t.due_date ASC
        """, (site, five_days_before))
        
        rows = cursor.fetchall()
        
        # 2. Incidents별로 그룹화
        incidents_map = {}
        for row in rows:
            incident_id = row[0]
            if incident_id not in incidents_map:
                incidents_map[incident_id] = {
                    'id': row[0],
                    'incident_id': row[1],
                    'incident_type': row[2],
                    'incident_date': row[3],
                    'resident_name': row[4],
                    'resident_id': row[5],
                    'description': row[6],
                    'severity': row[7],
                    'status': row[8],
                    'location': row[9],
                    'site': row[10],
                    'fall_type': row[11],  # Fall type 추가
                    'tasks': []
                }
            
            # Task가 있으면 추가 (인덱스가 1씩 증가)
            if row[12] is not None:  # task_db_id
                incidents_map[incident_id]['tasks'].append({
                    'id': row[12],
                    'task_id': row[13],
                    'task_name': row[14],
                    'due_date': row[15],
                    'status': row[16],
                    'completed_at': row[17],
                    'completed_by': row[18]
                })
        
        # 2.5. Fall type 계산 및 업데이트 (NULL이거나 비어있는 경우)
        from services.fall_policy_detector import fall_detector
        
        for incident_data in incidents_map.values():
            if not incident_data['fall_type']:
                # Fall type 계산 (올바른 시그니처: incident_id, cursor)
                fall_type = fall_detector.detect_fall_type_from_incident(
                    incident_data['id'],  # incident DB ID
                    cursor  # DB cursor
                )
                
                # DB 업데이트
                try:
                    cursor.execute("""
                        UPDATE cims_incidents 
                        SET fall_type = ? 
                        WHERE id = ?
                    """, (fall_type, incident_data['id']))
                    conn.commit()
                    
                    # incidents_map 업데이트
                    incident_data['fall_type'] = fall_type
                    logger.info(f"📝 Incident {incident_data['incident_id']}: fall_type={fall_type} (calculated)")
                except Exception as update_err:
                    logger.warning(f"⚠️ Failed to update fall_type for incident {incident_data['incident_id']}: {update_err}")
        
        # 3. Fall Policy 조회 (모든 Fall policies 반환)
        cursor.execute("""
            SELECT id, policy_id, name, rules_json
            FROM cims_policies
            WHERE is_active = 1 AND policy_id LIKE 'FALL-%'
            ORDER BY policy_id
        """)
        
        policy_rows = cursor.fetchall()
        fall_policies = {}  # policy_code -> policy_data
        
        for policy_row in policy_rows:
            try:
                policy_code = policy_row[1]  # FALL-001-UNWITNESSED or FALL-002-WITNESSED
                rules = json.loads(policy_row[3])
                
                fall_policies[policy_code] = {
                    'id': policy_row[0],
                    'policy_id': policy_code,
                    'name': policy_row[2],
                    'rules': rules
                }
            except Exception as e:
                logger.warning(f"Failed to parse policy {policy_row[1]}: {e}")
                continue
        
        # Backwards compatibility: fall_policy는 첫 번째 policy
        fall_policy = list(fall_policies.values())[0] if fall_policies else None
        
        logger.info(f"📋 Policies loaded: {list(fall_policies.keys())}")
        for policy_id, policy_data in fall_policies.items():
            schedule = policy_data['rules'].get('nurse_visit_schedule', [])
            logger.info(f"  - {policy_id}: {len(schedule)} phases")
        
        conn.close()
        
        total_tasks = sum(len(i['tasks']) for i in incidents_map.values())
        logger.info(f"🚀 Batch API: {site}/{date} - {len(incidents_map)} incidents, {total_tasks} tasks")
        
        # Tasks가 없고 Fall incidents가 있으면 자동 생성 시도
        if len(incidents_map) > 0 and total_tasks == 0 and fall_policy:
            logger.info(f"💡 Tasks가 없습니다 - 자동 생성 시도 중...")
            conn_gen = None
            try:
                conn_gen = get_db_connection()
                cursor_gen = conn_gen.cursor()
                
                tasks_generated = 0
                # 각 incident에 대해 tasks 생성
                for incident_data in incidents_map.values():
                    try:
                        num_tasks = auto_generate_fall_tasks(
                            incident_data['id'], 
                            incident_data['incident_date'], 
                            cursor_gen
                        )
                        tasks_generated += num_tasks
                        logger.info(f"✅ Incident {incident_data['incident_id']}: {num_tasks} tasks 생성됨")
                    except Exception as gen_err:
                        logger.warning(f"⚠️ Incident {incident_data['incident_id']} task 생성 실패: {gen_err}")
                
                conn_gen.commit()
                
                logger.info(f"✅ 총 {tasks_generated}개 tasks 생성 완료")
                
            except Exception as e:
                logger.warning(f"⚠️ Task 자동 생성 실패: {e}")
                if conn_gen:
                    try:
                        conn_gen.rollback()
                    except:
                        pass
            finally:
                if conn_gen:
                    try:
                        conn_gen.close()
                    except:
                        pass
        
        return jsonify({
            'success': True,
            'incidents': list(incidents_map.values()),
            'policy': fall_policy,  # Backwards compatibility
            'policies': fall_policies,  # All Fall policies by policy_id
            'site': site,
            'date': date,
            'cached': False,  # Server-side 캐싱 시 True로 변경
            'timestamp': datetime.now().isoformat(),
            'auto_generated': total_tasks == 0 and len(incidents_map) > 0 and fall_policy  # Tasks 자동 생성 여부
        })
        
    except Exception as e:
        logger.error(f"Batch API 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/incident/<int:incident_id>/tasks')
@login_required
def get_incident_tasks(incident_id):
    """인시던트의 모든 태스크와 완료 상태 조회 API"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'nurse', 'carer']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all tasks for the incident with completion status
        cursor.execute("""
            SELECT id, task_id, task_name, due_date, status, completed_at, completed_by_user_id
            FROM cims_tasks
            WHERE incident_id = ?
            ORDER BY due_date ASC
        """, (incident_id,))
        
        tasks = cursor.fetchall()
        conn.close()
        
        result = []
        for task in tasks:
            result.append({
                'id': task[0],
                'task_id': task[1],
                'task_name': task[2],
                'due_date': task[3],
                'status': task[4],
                'completed_at': task[5],
                'completed_by': task[6]
            })
        
        return jsonify({'tasks': result})
        
    except Exception as e:
        logger.error(f"Incident tasks 조회 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/overdue-tasks')
@login_required
def get_overdue_tasks():
    """기한 초과 태스크 조회 API (관리자 전용)"""
    try:
        if not (current_user.is_admin() or current_user.is_clinical_manager()):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        overdue_tasks = policy_engine.get_overdue_tasks()
        
        return jsonify({
            'success': True,
            'tasks': overdue_tasks
        })
        
    except Exception as e:
        logger.error(f"기한 초과 태스크 조회 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cims/upcoming-tasks')
@login_required
def get_upcoming_tasks():
    """곧 마감될 태스크 조회 API"""
    try:
        hours_ahead = request.args.get('hours', 2, type=int)
        upcoming_tasks = policy_engine.get_upcoming_tasks(hours_ahead)
        
        return jsonify({
            'success': True,
            'tasks': upcoming_tasks
        })
        
    except Exception as e:
        logger.error(f"곧 마감될 태스크 조회 API 오류: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# CIMS API Blueprint 등록
# ==============================

# CIMS API Blueprint 등록
from cims_api_endpoints import cims_api
from cims_cache_api import cache_api
from cims_background_processor import start_background_processing, stop_background_processing
app.register_blueprint(cims_api)
app.register_blueprint(cache_api)

# ==============================
# CIMS 관리자 대시보드 라우트
# ==============================

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    """기존 관리자 대시보드 - 통합 대시보드로 리다이렉트"""
    return redirect(url_for('integrated_dashboard'))

@app.route('/policy_admin')
@login_required
def policy_admin():
    """정책 관리 인터페이스"""
    try:
        # 관리자 권한 확인
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            flash('Access denied. Administrator privileges required.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('policy_admin_interface.html', current_user=current_user)
        
    except Exception as e:
        logger.error(f"정책 관리 인터페이스 로드 오류: {str(e)}")
        flash('Error loading policy management interface', 'error')
        return redirect(url_for('rod_dashboard'))

@app.route('/mobile_dashboard')
@login_required
def mobile_dashboard():
    """모바일 최적화 태스크 대시보드"""
    try:
        # 사용자 권한 확인
        if not current_user.can_complete_tasks() and not current_user.is_admin():
            flash('Access denied. You do not have permission to access the task dashboard.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        # 초기 로드 시 Policy 및 Tasks 확인
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Active Fall Policy 확인
        cursor.execute("""
            SELECT COUNT(*) FROM cims_policies WHERE is_active = 1
        """)
        policy_count = cursor.fetchone()[0]
        
        # Fall incidents 확인
        cursor.execute("""
            SELECT COUNT(*) FROM cims_incidents 
            WHERE incident_type LIKE '%Fall%' AND status IN ('Open', 'Overdue')
        """)
        fall_incident_count = cursor.fetchone()[0]
        
        # Tasks 확인
        cursor.execute("SELECT COUNT(*) FROM cims_tasks")
        task_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Policy가 없거나 Fall incidents가 있는데 tasks가 없으면 초기화 필요
        needs_init = (policy_count == 0) or (fall_incident_count > 0 and task_count == 0)
        
        if needs_init:
            logger.info(f"🆕 Mobile Dashboard 초기화 필요 감지 - Policy: {policy_count}, Fall: {fall_incident_count}, Tasks: {task_count}")
            logger.info(f"💡 Tip: Settings 페이지에서 Force Synchronization을 실행하면 Policy와 Tasks가 자동 생성됩니다.")
        
        return render_template('mobile_task_dashboard.html', 
                             current_user=current_user,
                             needs_init=needs_init)
        
    except Exception as e:
        logger.error(f"모바일 대시보드 로드 오류: {str(e)}")
        flash('Error loading mobile dashboard', 'error')
        return redirect(url_for('rod_dashboard'))

@app.route('/task_confirmation')
@login_required
def task_confirmation():
    """태스크 완료 확인 페이지"""
    try:
        # 사용자 권한 확인
        if not current_user.can_complete_tasks() and not current_user.is_admin():
            flash('Access denied. You do not have permission to complete tasks.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('task_completion_confirmation.html', current_user=current_user)
        
    except Exception as e:
        logger.error(f"태스크 확인 페이지 로드 오류: {str(e)}")
        flash('Error loading task confirmation page', 'error')
        return redirect(url_for('rod_dashboard'))

# ==============================
# CIMS 정책 관리 API 엔드포인트
# ==============================

@app.route('/api/cims/policies', methods=['GET'])
@login_required
def get_policies():
    """정책 목록 조회"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, policy_id, name, description, version, effective_date, 
                   rules_json, is_active, created_at
            FROM cims_policies 
            ORDER BY created_at DESC
        """)
        
        policies = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(policy) for policy in policies])
        
    except Exception as e:
        logger.error(f"정책 목록 조회 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['GET'])
@login_required
def get_policy(policy_id):
    """특정 정책 조회"""
    try:
        if not (current_user.is_admin() or current_user.role in ['clinical_manager', 'doctor']):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cims_policies WHERE id = ?", (policy_id,))
        policy = cursor.fetchone()
        conn.close()
        
        if not policy:
            return jsonify({'error': 'Policy not found'}), 404
        
        return jsonify(dict(policy))
        
    except Exception as e:
        logger.error(f"정책 조회 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies', methods=['POST'])
@login_required
def create_policy():
    """새 정책 생성"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['name', 'version', 'rules_json']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 정책 ID 생성
        policy_id = f"POL-{uuid.uuid4().hex[:6].upper()}"
        
        cursor.execute("""
            INSERT INTO cims_policies (
                policy_id, name, description, version, effective_date, 
                rules_json, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy_id,
            data['name'],
            data.get('description', ''),
            data['version'],
            datetime.now().isoformat(),
            data['rules_json'],
            data.get('is_active', True),
            datetime.now().isoformat()
        ))
        
        new_policy_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': new_policy_id,
            'policy_id': policy_id,
            'message': 'Policy created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"정책 생성 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['PUT'])
@login_required
def update_policy(policy_id):
    """정책 업데이트"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 정책 존재 확인
        cursor.execute("SELECT id FROM cims_policies WHERE id = ?", (policy_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Policy not found'}), 404
        
        # 정책 업데이트
        cursor.execute("""
            UPDATE cims_policies 
            SET name = ?, description = ?, version = ?, rules_json = ?, is_active = ?
            WHERE id = ?
        """, (
            data.get('name'),
            data.get('description'),
            data.get('version'),
            data.get('rules_json'),
            data.get('is_active'),
            policy_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Policy updated successfully'})
        
    except Exception as e:
        logger.error(f"정책 업데이트 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cims/policies/<int:policy_id>', methods=['DELETE'])
@login_required
def delete_policy(policy_id):
    """정책 삭제"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 정책 존재 확인
        cursor.execute("SELECT id, policy_id, name FROM cims_policies WHERE id = ?", (policy_id,))
        policy = cursor.fetchone()
        
        if not policy:
            conn.close()
            return jsonify({'error': 'Policy not found'}), 404
        
        # 정책 삭제 (실제로는 is_active를 False로 설정하는 것이 안전)
        # 하지만 완전 삭제를 원하면 DELETE 사용
        cursor.execute("DELETE FROM cims_policies WHERE id = ?", (policy_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Policy deleted: {policy['name']} (ID: {policy_id})")
        return jsonify({'message': 'Policy deleted successfully'})
        
    except Exception as e:
        logger.error(f"정책 삭제 오류: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# 통합 대시보드 라우트
# ==============================

@app.route('/integrated_dashboard')
@login_required
def integrated_dashboard():
    """통합 대시보드 - 역할별 자동 전환"""
    try:
        # 사용자 역할 확인
        user_role = current_user.role if hasattr(current_user, 'role') else 'nurse'
        
        # 역할별 권한 확인
        if user_role not in ['admin', 'clinical_manager', 'registered_nurse', 'nurse', 'carer']:
            flash('접근 권한이 없습니다.', 'error')
            return redirect(url_for('rod_dashboard'))
        
        return render_template('integrated_dashboard.html', 
                             user_role=user_role,
                             current_user=current_user)
        
    except Exception as e:
        logger.error(f"통합 대시보드 오류: {str(e)}")
        flash('대시보드를 불러올 수 없습니다.', 'error')
        return redirect(url_for('rod_dashboard'))

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

def start_periodic_sync():
    """주기적 백그라운드 동기화 스케줄러 시작 (5분마다 증분 동기화)"""
    
    def initial_sync_job():
        """서버 시작 시 초기 동기화 (전체 30일)"""
        try:
            # 5초 대기 후 초기 동기화 시작 (서버 완전 시작 대기)
            time.sleep(5)
            
            logger.info("=" * 60)
            logger.info("🚀 서버 시작 - 초기 데이터 동기화 시작 (최근 30일)")
            logger.info("=" * 60)
            
            sync_result = sync_incidents_from_manad_to_cims(full_sync=True)
            
            logger.info(f"✅ 초기 데이터 동기화 완료: {sync_result}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ 초기 데이터 동기화 오류: {e}")
    
    def periodic_sync_job():
        """5분마다 실행되는 증분 동기화 작업"""
        try:
            logger.info("🔄 주기적 백그라운드 동기화 시작 (증분 동기화)")
            sync_result = sync_incidents_from_manad_to_cims(full_sync=False)
            
            # Progress Note 동기화는 일시적으로 비활성화됨 (나중에 DB 직접 접속으로 재구현 예정)
            # logger.info("🔄 Progress Note 동기화 시작...")
            # pn_sync_result = sync_progress_notes_from_manad_to_cims()
            
            logger.info(f"✅ 주기적 백그라운드 동기화 완료: Incidents={sync_result}")
        except Exception as e:
            logger.error(f"❌ 주기적 백그라운드 동기화 오류: {e}")
    
    # 서버 시작 시 초기 동기화 (백그라운드에서)
    initial_thread = threading.Thread(target=initial_sync_job, daemon=True)
    initial_thread.start()
    logger.info("🚀 초기 데이터 동기화 스레드 시작됨 (5초 후 실행)")
    
    # 5분마다 증분 동기화 실행
    schedule.every(5).minutes.do(periodic_sync_job)
    
    def run_scheduler():
        """스케줄러 실행 루프"""
        logger.info("🔄 주기적 백그라운드 동기화 스케줄러 시작됨 (5분마다)")
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)  # 30초마다 스케줄 확인
            except Exception as e:
                logger.error(f"스케줄러 실행 중 오류: {e}")
                time.sleep(60)  # 오류 시 1분 대기
    
    # 백그라운드 스레드로 실행
    sync_thread = threading.Thread(target=run_scheduler, daemon=True)
    sync_thread.start()
    logger.info("✅ 주기적 백그라운드 동기화 스케줄러 시작됨 (5분마다)")

if __name__ == '__main__':
    # CIMS Background Data Processor (선택적)
    # 기능: Dashboard KPI 캐시 생성 (10분마다) → 성능 향상
    # 개발 환경: 비활성화 (즉시 응답 확인 가능)
    # 운영 환경: 활성화 추천 (.env에 PROD_ENABLE_BACKGROUND_PROCESSOR=True)
    if flask_config.get('ENABLE_BACKGROUND_PROCESSOR', False):
        try:
            start_background_processing()
            logger.info("✅ CIMS Background Processor 시작됨 (Dashboard 성능 향상)")
        except Exception as e:
            logger.warning(f"⚠️ Background Processor 시작 실패: {e}")
    # else: 개발 환경에서는 불필요한 메시지 출력 안 함
    
    # 주기적 백그라운드 동기화 시작 (5분마다 증분 동기화)
    try:
        start_periodic_sync()
    except Exception as e:
        logger.warning(f"⚠️ 주기적 백그라운드 동기화 시작 실패: {e}")
    
    # MANAD Plus Integrator (백그라운드 폴링 - 선택적)
    # 현재: 증분 동기화로 충분 (API 호출 시 5분마다 자동 동기화)
    # 향후: 실시간 폴링 필요 시 system_settings에서 'manad_integrator_enabled'=true 설정
    # Note: 대부분의 경우 불필요 (증분 동기화가 더 효율적)
    
    try:
        app.run(
            debug=flask_config['DEBUG'], 
            host=flask_config['HOST'],
            port=flask_config['PORT']
        )
    finally:
        # Stop background processor when app shuts down (only if it was started)
        if flask_config.get('ENABLE_BACKGROUND_PROCESSOR', False):
            try:
                stop_background_processing()
                logger.info("Background data processor stopped")
            except Exception as e:
                logger.error(f"Error stopping background processor: {e}")