from flask import (
    Flask, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash, 
    session, 
    jsonify, 
    send_from_directory
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import requests
from functools import wraps
import logging
import logging.handlers
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일에서 환경변수 로딩
load_dotenv()

# 내부 모듈 임포트
from api_client import APIClient
from api_carearea import APICareArea
from api_eventtype import APIEventType
from config import SITE_SERVERS, API_HEADERS
from config_users import authenticate_user, get_user
from config_env import get_flask_config, print_current_config
from models import load_user, User

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
        # 콘솔 출력
        logging.StreamHandler(),
        # 파일 출력 (최대 10MB, 5개 파일 로테이션)
        logging.handlers.RotatingFileHandler(
            f'{log_dir}/app.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)

# 현재 설정 출력
print_current_config()

# 플라스크 앱 초기화
app = Flask(__name__, static_url_path='/static')

# 환경별 설정 적용
app.secret_key = flask_config['SECRET_KEY']
app.config['DEBUG'] = flask_config['DEBUG']

# 세션 타임아웃 설정 (5분)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=5)

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
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Session expired', 'is_expired': True}), 401
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
    """클라이언트 정보를 가져오고 처리"""
    logger.info(f"클라이언트 정보 요청 시작 - 사이트: {site}")
    try:
        api_client = APIClient(site)
        client_info = api_client.get_client_information()
        logger.info(f"클라이언트 정보 가져오기 성공 - 사이트: {site}")

        # 클라이언트 정보 가공
        processed_client_info = process_client_information(client_info)
        return True, client_info
    except requests.RequestException as e:
        logger.error(f"클라이언트 정보 가져오기 실패 - 사이트: {site}, 에러: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"클라이언트 정보 처리 중 예외 발생: {str(e)}")
        return False, None

def fetch_care_area_information(site):
    """Care Area 정보를 가져오고 처리"""
    logger.info(f"Care Area 정보 요청 시작 - 사이트: {site}")
    try:
        api_care_area = APICareArea(site)
        care_area_info = api_care_area.get_care_area_information()
        logger.info("Care Area 정보 가져오기 성공")
        return True, care_area_info
    except Exception as e:
        logger.error(f"Care Area 정보 가져오기 실패: {str(e)}")
        return False, None

def fetch_event_type_information(site):
    """Event Type 정보를 가져오고 처리"""
    logger.info(f"Event Type 정보 요청 시작 - 사이트: {site}")
    try:
        api_event_type = APIEventType(site)
        event_type_info = api_event_type.get_event_type_information()
        logger.info("Event Type 정보 가져오기 성공")
        return True, event_type_info
    except Exception as e:
        logger.error(f"Event Type 정보 가져오기 실패: {str(e)}")
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
    """클라이언트 데이터를 JSON 파일로 저장"""
    try:
        data = {
            'username': username,
            'site': site,
            'server_ip': SITE_SERVERS.get(site, ''),
            'client_info': client_info,
            'timestamp': datetime.now().isoformat()
        }
        
        # 사이트명에서 공백을 언더스코어로 변환하고 소문자로 변경
        site_name = site.replace(' ', '_').lower()
        filename = f"data/{site_name}_client.json"
        
        logger.info(f"파일 저장 시도: {filename}")
        save_json_file(filename, data)
        
        return filename
        
    except Exception as e:
        logger.error(f"파일 저장 중 오류 발생: {str(e)}")
        raise

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
    status = {}
    for site, server_ip in SITE_SERVERS.items():
        status[site] = check_api_server_health(server_ip)
    return jsonify(status)

# ==============================
# 라우트 정의
# ==============================

@app.route('/')
def home():
    """홈 페이지"""
    if current_user.is_authenticated:
        return redirect(url_for('progress_notes'))
    return render_template('LoginPage.html', sites=SITE_SERVERS.keys())

@app.route('/login', methods=['GET'])
def login_page():
    """로그인 페이지"""
    return render_template('LoginPage.html', sites=SITE_SERVERS.keys())

@app.route('/login', methods=['POST'])
def login():
    """로그인 처리"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        site = request.form.get('site')
        
        logger.info(f"로그인 시도 - 사용자: {username}, 사이트: {site}")

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
                # location이 All이거나 2개 이상이면 모든 사이트 허용
                if (isinstance(user_location, list) and (len(user_location) > 1 or (len(user_location) == 1 and user_location[0].lower() == 'all'))) or (isinstance(user_location, str) and user_location.lower() == 'all'):
                    allowed_sites = list(SITE_SERVERS.keys())
                else:
                    # location이 1개면 해당 사이트만 허용
                    allowed_sites = user_location if isinstance(user_location, list) else [user_location]
                    # site 값을 무조건 allowed_sites[0]로 강제 설정
                    site = allowed_sites[0] if allowed_sites else site

                if site not in allowed_sites:
                    flash(f'You are not allowed to access {site}.', 'error')
                    return redirect(url_for('home'))

                # 클라이언트 정보 가져오기 (실패해도 로그인 진행)
                client_success, client_info = fetch_client_information(site)
                
                # Care Area 정보 가져오기 (실패해도 로그인 진행)
                care_area_success, care_area_info = fetch_care_area_information(site)
                
                # Event Type 정보 가져오기 (실패해도 로그인 진행)
                event_type_success, event_type_info = fetch_event_type_information(site)
                
                # API 서버 연결 실패 시에도 로그인 허용
                try:
                    if client_info:  # client_info가 있을 때만 저장
                        filename = save_client_data(username, site, client_info)
                        session['current_file'] = filename
                    
                    # Flask-Login을 사용한 로그인 처리
                    user = User(username, user_info)
                    login_user(user, remember=False)  # 브라우저 닫으면 세션 만료
                    session.permanent = False
                    
                    # 세션 생성 시간 기록
                    session['_created'] = datetime.now().isoformat()
                    
                    # 세션에 추가 정보 저장
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # 허용된 사이트 정보 저장
                    logger.info(f"세션 저장: site={site}, allowed_sites={allowed_sites}")
                    
                    flash('Login successful!', 'success')
                    logger.info(f"로그인 성공 - 사용자: {username}, 사이트: {site}")
                    
                    return redirect(url_for('progress_notes', site=site))
                except Exception as e:
                    logger.error(f"데이터 저장 중 오류 발생: {str(e)}")
                    flash('Error occurred while saving data.', 'error')
                    
            except Exception as e:
                logger.error(f"API 호출 중 오류 발생: {str(e)}")
                # API 오류 시에도 로그인 허용
                try:
                    # Flask-Login을 사용한 로그인 처리
                    user = User(username, user_info)
                    login_user(user, remember=False)
                    
                    # 세션 생성 시간 기록
                    session['_created'] = datetime.now().isoformat()
                    
                    # 세션에 추가 정보 저장
                    session['site'] = site
                    session['allowed_sites'] = allowed_sites # 허용된 사이트 정보 저장
                    logger.info(f"세션 저장: site={site}, allowed_sites={allowed_sites}")
                    
                    flash('Login successful! (Some data may not be available)', 'success')
                    logger.info(f"로그인 성공 (API 오류 있음) - 사용자: {username}, 사이트: {site}")
                    
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
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
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

@app.route('/progress-notes')
@login_required
def progress_notes():
    allowed_sites = session.get('allowed_sites', [])
    site = request.args.get('site', session.get('site', 'Ramsay'))
    logger.info(f"progress_notes: allowed_sites={allowed_sites}, site={site}")
    # location이 1개면 무조건 그 사이트로 강제
    if isinstance(allowed_sites, list) and len(allowed_sites) == 1:
        forced_site = allowed_sites[0]
        if site != forced_site:
            return redirect(url_for('progress_notes', site=forced_site))
        site = forced_site
    return render_template('ProgressNoteList.html', site=site)

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
                return jsonify({
                    'success': True, 
                    'message': 'Progress Note saved and sent to API successfully.',
                    'data': progress_note,
                    'api_response': api_response
                })
            else:
                logger.warning(f"Progress Note API 전송 실패: {api_response}")
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
            return jsonify({
                'success': True,  # 파일 저장은 성공
                'message': 'Progress Note saved but API module not available.',
                'data': progress_note,
                'warning': 'API transmission module not found. The file was saved successfully.'
            })
        except Exception as e:
            logger.error(f"API 전송 중 예상치 못한 오류: {str(e)}")
            return jsonify({
                'success': True,  # 파일 저장은 성공
                'message': 'Progress Note saved but API transmission failed.',
                'data': progress_note,
                'api_error': str(e),
                'warning': f'An error occurred while sending the API: {str(e)}. The file was saved successfully.'
            })
            
    except Exception as e:
        logger.error(f"Progress Note saving error: {str(e)}")
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
        login_user(user, remember=False)
        
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
        # 세션 만료 시간 계산 (5분)
        session_lifetime = timedelta(minutes=5)
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
        # 세션 생성 시간 업데이트
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
    """프로그레스 노트를 사이트에서 가져오기"""
    try:
        data = request.get_json()
        site = data.get('site')
        days = data.get('days', 7)  # 기본값: 7일
        force_refresh = data.get('force_refresh', False)  # 강제 새로고침
        
        if not site:
            logger.error("Site parameter is missing in request")
            return jsonify({'success': False, 'message': 'Site is required'}), 400
        
        logger.info(f"프로그레스 노트 가져오기 요청 - 사이트: {site}, 일수: {days}")
        logger.info(f"Request data: {data}")
        
        # 사이트 서버 설정 확인
        from config import SITE_SERVERS
        if site not in SITE_SERVERS:
            logger.error(f"Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}")
            return jsonify({
                'success': False, 
                'message': f'Unknown site: {site}. Available sites: {list(SITE_SERVERS.keys())}'
            }), 400
        
        server_ip = SITE_SERVERS[site]
        logger.info(f"Target server for {site}: {server_ip}")
        
        try:
            from api_progressnote_fetch import fetch_progress_notes_for_site
            
            # 프로그레스 노트 가져오기
            logger.info(f"Calling fetch_progress_notes_for_site for {site}")
            success, progress_notes = fetch_progress_notes_for_site(site, days)
            
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
    from flask import send_from_directory
    import os
    
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

# ==============================
# 앱 실행
# ==============================

if __name__ == '__main__':
    app.run(
        debug=flask_config['DEBUG'], 
        host=flask_config['HOST'],
        port=flask_config['PORT']
    )