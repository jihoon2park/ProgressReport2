from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
from functools import wraps
from flask import session, redirect, url_for
from api_client import APIClient
import logging
from config import SITE_SERVERS  # config.py에서 SITE_SERVERS import 추가
import json
import os
from datetime import datetime

# Login required decorator

# 로깅 설정 (app.py 시작 부분에 추가)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key_here'

VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"

AUTH_SESSION_KEY = 'logged_in'

def require_authentication(wrapped_function):
    @wraps(wrapped_function)
    def decorated_function(*args, **kwargs):
        if not _is_authenticated():
            return redirect(url_for('home'))
        return wrapped_function(*args, **kwargs)
    return decorated_function

def _is_authenticated():
    return AUTH_SESSION_KEY in session

def process_client_information(client_info):
    """
    클라이언트 정보를 가공하여 필요한 정보만 추출하는 함수
    """
    processed_clients = []

    for client in client_info:
        processed_client = {
            'PersonId': client.get('PersonId'),
            'ClientName': f"{client.get('Title', '')} {client.get('FirstName', '')} {client.get('LastName', '')}".strip(),
            'BirthDate': client.get('BirthDate'),
            'WingName': client.get('WingName'),
            'RoomName': client.get('RoomName')
        }
        processed_clients.append(processed_client)

    # 가공된 데이터를 JSON 파일로 저장
    try:
        with open('data/Client_list.json', 'w', encoding='utf-8') as f:
            json.dump(processed_clients, f, ensure_ascii=False, indent=4)
        logger.info("Client_list.json 파일 생성 완료")
    except Exception as e:
        logger.error(f"JSON 파일 저장 중 오류 발생: {str(e)}")

    return None #processed_clients

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return render_template('progressnote.html', sites=SITE_SERVERS.keys())


# 로그인 페이지 렌더링을 위한 GET 메소드 라우트 추가
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('ProgressNote.html', sites=SITE_SERVERS.keys())

logger = logging.getLogger(__name__)

def fetch_client_information(site):
    """클라이언트 정보를 가져오고 처리하는 함수"""
    logger.info(f"클라이언트 정보 요청 시작 - 사이트: {site}")
    try:
        api_client = APIClient(site)  # SITE_SERVERS 인자 제거
        client_info = api_client.get_client_information()
        logger.info(f"클라이언트 정보 가져오기 성공 - 사이트: {site}")

        # 클라이언트 정보 가공
        processed_client_info = process_client_information(client_info)

        return True, client_info
    except requests.RequestException as e:
        logger.error(f"클라이언트 정보 가져오기 실패 - 사이트: {site}, 에러: {str(e)}")
        return False, None

# 서버 IP 조회 API 엔드포인트 추가
@app.route('/get_server_ip', methods=['POST'])
def get_server_ip():
    site = request.json.get('site')
    if site in SITE_SERVERS:
        return jsonify({
            'success': True,
            'server_ip': SITE_SERVERS[site]
        })
    return jsonify({
        'success': False,
        'message': 'Invalid site selected'
    })

@app.route('/data/Client_list.json')
def get_client_list():
    try:
        with open('data/Client_list.json', 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify([]), 404

def save_client_data(username, site, client_info):
    """클라이언트 데이터를 JSON 파일로 저장"""
    try:
        data = {
            'username': username,
            'site': site,
            'server_ip': SITE_SERVERS[site],
            'client_info': client_info,
            'timestamp': datetime.now().isoformat()
        }
        
        # data 디렉토리가 없으면 생성
        if not os.path.exists('data'):
            os.makedirs('data')
            logger.info("data 디렉토리 생성됨")
        
        # 사이트명에서 공백을 언더스코어로 변환하고 소문자로 변경
        site_name = site.replace(' ', '_').lower()
        filename = f"data/{site_name}_client.json"
        
        logger.info(f"파일 저장 시도: {filename}")
        
        # 파일 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"파일이 성공적으로 저장됨: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"파일 저장 중 오류 발생: {str(e)}")
        raise

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    site = request.form.get('site')
    
    logger.info(f"로그인 시도 - 사용자: {username}, 사이트: {site}")

    if username == VALID_USERNAME and password == VALID_PASSWORD:
        logger.info("인증 성공")
        success, client_info = fetch_client_information(site)
        
        if success:
            try:
                logger.info(f"클라이언트 정보 가져오기 성공: {client_info}")
                # JSON 파일로 저장
                filename = save_client_data(username, site, client_info)
                
                # 세션에는 최소한의 정보만 저장
                session['logged_in'] = True
                session['username'] = username
                session['current_file'] = filename
                
                flash('클라이언트 정보를 성공적으로 저장했습니다.', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"데이터 저장 중 오류 발생: {str(e)}")
                flash('데이터 저장 중 오류가 발생했습니다.', 'error')
                return redirect(url_for('home'))
        else:
            logger.error(f"클라이언트 정보 가져오기 실패 - 사이트: {site}")    
            flash('클라이언트 정보를 가져오는데 실패했습니다.', 'error')
            return redirect(url_for('home'))
    else:
        logger.warning(f"인증 실패 - 사용자: {username}")
        flash('잘못된 인증 정보입니다.', 'error')
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/index')
@require_authentication
def index():
    if 'logged_in' not in session:
        return redirect(url_for('home'))

    # JSON 파일에서 데이터 읽기
    filename = session.get('current_file')
    if filename and os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return render_template('index.html',
                                selected_site=data['site'],
                                client_info=data['client_info'])
    
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)