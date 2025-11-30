#!/usr/bin/env python3
"""
Admin API 엔드포인트 - API 키 관리 및 시스템 설정
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import sqlite3
from datetime import datetime

# API 키 관리자 import
try:
    from api_key_manager_json import APIKeyManagerJSON
    API_KEY_MANAGER_AVAILABLE = True
except ImportError:
    API_KEY_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

# Admin API Blueprint
admin_api = Blueprint('admin_api', __name__)

def admin_required(f):
    """Admin 권한이 필요한 함수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
        
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': 'Admin 권한이 필요합니다.'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@admin_api.route('/api/admin/api-keys', methods=['GET'])
@login_required
@admin_required
def get_api_keys():
    """모든 API 키 목록 조회"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_keys = manager.get_all_api_keys()
        
        # 보안을 위해 API 키는 일부만 표시
        for api_key in api_keys:
            if api_key['api_key']:
                api_key['api_key'] = api_key['api_key'][:20] + '...'
        
        return jsonify({
            'success': True,
            'api_keys': api_keys
        })
        
    except Exception as e:
        logger.error(f"API 키 목록 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 목록 조회 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['GET'])
@login_required
@admin_required
def get_api_key(site_name):
    """특정 사이트의 API 키 조회"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_key = manager.get_api_key(site_name)
        
        if not api_key:
            return jsonify({
                'success': False,
                'message': f'API 키를 찾을 수 없습니다: {site_name}'
            }), 404
        
        return jsonify({
            'success': True,
            'api_key': api_key
        })
        
    except Exception as e:
        logger.error(f"API 키 조회 실패 ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 조회 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys', methods=['POST'])
@login_required
@admin_required
def add_api_key():
    """새 API 키 추가"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['siteName', 'apiUsername', 'apiKey', 'serverIp']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'필수 필드가 누락되었습니다: {field}'
                }), 400
        
        manager = APIKeyManagerJSON()
        
        success = manager.add_api_key(
            site_name=data['siteName'],
            api_username=data['apiUsername'],
            api_key=data['apiKey'],
            server_ip=data['serverIp'],
            server_port=int(data.get('serverPort', 8080)),
            notes=data.get('notes', '')
        )
        
        if success:
            logger.info(f"API 키 추가됨: {data['siteName']} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API 키가 성공적으로 추가되었습니다: {data["siteName"]}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'API 키 추가에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"API 키 추가 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 추가 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['PUT'])
@login_required
@admin_required
def update_api_key(site_name):
    """API 키 업데이트"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        data = request.get_json()
        manager = APIKeyManagerJSON()
        
        # 업데이트할 필드들
        update_data = {}
        if 'apiUsername' in data:
            update_data['api_username'] = data['apiUsername']
        if 'apiKey' in data:
            update_data['api_key'] = data['apiKey']
        if 'serverIp' in data:
            update_data['server_ip'] = data['serverIp']
        if 'serverPort' in data:
            update_data['server_port'] = int(data['serverPort'])
        if 'notes' in data:
            update_data['notes'] = data['notes']
        
        success = manager.update_api_key(site_name, **update_data)
        
        if success:
            logger.info(f"API 키 업데이트됨: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API 키가 성공적으로 업데이트되었습니다: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'API 키 업데이트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"API 키 업데이트 실패 ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 업데이트 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>', methods=['DELETE'])
@login_required
@admin_required
def delete_api_key(site_name):
    """API 키 삭제"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        manager = APIKeyManagerJSON()
        success = manager.deactivate_api_key(site_name)
        
        if success:
            logger.info(f"API 키 삭제됨: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API 키가 성공적으로 삭제되었습니다: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'API 키 삭제에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"API 키 삭제 실패 ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 삭제 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_api_key(site_name):
    """API 키 활성화/비활성화"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        data = request.get_json()
        is_active = data.get('is_active', True)
        
        manager = APIKeyManagerJSON()
        success = manager.update_api_key(site_name, is_active=is_active)
        
        if success:
            action = '활성화' if is_active else '비활성화'
            logger.info(f"API 키 {action}됨: {site_name} by {current_user.username}")
            return jsonify({
                'success': True,
                'message': f'API 키가 성공적으로 {action}되었습니다: {site_name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'API 키 {action}에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"API 키 토글 실패 ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'API 키 토글 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/<site_name>/test', methods=['POST'])
@login_required
@admin_required
def test_api_connection(site_name):
    """API 연결 테스트"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_data = manager.get_api_key(site_name)
        
        if not api_data:
            return jsonify({
                'success': False,
                'message': f'API 키를 찾을 수 없습니다: {site_name}'
            }), 404
        
        # API 연결 테스트
        import requests
        from config import get_api_headers
        
        headers = get_api_headers(site_name)
        base_url = f"http://{api_data['server_ip']}:{api_data['server_port']}"
        test_url = f"{base_url}/api/client"
        
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            return jsonify({
                'success': True,
                'message': f'연결 성공 (상태 코드: {response.status_code})'
            })
        except requests.RequestException as e:
            return jsonify({
                'success': False,
                'message': f'연결 실패: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"API 연결 테스트 실패 ({site_name}): {e}")
        return jsonify({
            'success': False,
            'message': f'연결 테스트 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/api-keys/test-all', methods=['POST'])
@login_required
@admin_required
def test_all_api_connections():
    """모든 API 연결 테스트"""
    try:
        if not API_KEY_MANAGER_AVAILABLE:
            return jsonify({
                'success': False, 
                'message': 'API 키 관리자가 사용할 수 없습니다.'
            }), 500
        
        manager = APIKeyManagerJSON()
        api_keys = manager.get_all_api_keys()
        
        results = []
        success_count = 0
        
        for api_key in api_keys:
            if not api_key['is_active']:
                continue
                
            try:
                import requests
                from config import get_api_headers
                
                headers = get_api_headers(api_key['site_name'])
                base_url = f"http://{api_key['server_ip']}:{api_key['server_port']}"
                test_url = f"{base_url}/api/client"
                
                response = requests.get(test_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                results.append({
                    'site_name': api_key['site_name'],
                    'status': 'success',
                    'message': f'연결 성공 (상태 코드: {response.status_code})'
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    'site_name': api_key['site_name'],
                    'status': 'error',
                    'message': f'연결 실패: {str(e)}'
                })
        
        return jsonify({
            'success': True,
            'message': f'테스트 완료: {success_count}/{len(results)} 성공',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"전체 API 연결 테스트 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'전체 연결 테스트 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/system-status', methods=['GET'])
@login_required
@admin_required
def get_system_status():
    """시스템 상태 조회"""
    try:
        # 데이터베이스 연결 상태 확인 - JSON 전용 시스템으로 변경됨
        db_status = {'connected': True, 'type': 'JSON'}
        try:
            # JSON 파일 기반 시스템이므로 항상 연결됨으로 간주
            data_dir = 'data'
            if os.path.exists(data_dir):
                db_status['connected'] = True
                db_status['type'] = 'JSON Files'
            else:
                db_status['connected'] = False
                db_status['error'] = 'Data directory not found'
        except Exception as e:
            db_status['error'] = str(e)
        
        # 암호화 키 상태 확인
        encryption_status = {'available': False}
        try:
            if API_KEY_MANAGER_AVAILABLE:
                manager = APIKeyManagerJSON()
                # 암호화 키 파일 존재 확인
                encryption_status['available'] = os.path.exists('api_key_encryption.key')
            else:
                encryption_status['error'] = 'API 키 관리자를 사용할 수 없습니다.'
        except Exception as e:
            encryption_status['error'] = str(e)
        
        return jsonify({
            'success': True,
            'db_status': db_status,
            'encryption_status': encryption_status,
            'api_key_manager_available': API_KEY_MANAGER_AVAILABLE
        })
        
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'시스템 상태 조회 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/system-logs', methods=['GET'])
@login_required
@admin_required
def get_system_logs():
    """시스템 로그 조회"""
    try:
        log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'message': '로그 파일을 찾을 수 없습니다.'
            }), 404
        
        # 최근 100줄만 읽기
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({
            'success': True,
            'logs': ''.join(recent_lines),
            'total_lines': len(lines)
        })
        
    except Exception as e:
        logger.error(f"시스템 로그 조회 실패: {e}")
        return jsonify({
            'success': False,
            'message': f'시스템 로그 조회 실패: {str(e)}'
        }), 500

def get_db_connection():
    """데이터베이스 연결"""
    conn = sqlite3.connect('progress_report.db', timeout=60.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
    except:
        pass
    return conn

@admin_api.route('/api/admin/data-source-mode', methods=['GET'])
@login_required
@admin_required
def get_data_source_mode():
    """데이터 소스 모드 조회 (DB 또는 API)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # system_settings에서 조회
        cursor.execute("""
            SELECT value FROM system_settings 
            WHERE key = 'USE_DB_DIRECT_ACCESS'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        # DB에 저장된 값이 있으면 사용, 없으면 환경 변수 확인, 둘 다 없으면 'api'
        if result and result[0]:
            mode = result[0].lower()
        else:
            mode = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower()
        
        # 'true'/'false' 문자열을 'db'/'api'로 변환
        if mode == 'true' or mode == 'db':
            mode = 'db'
        else:
            mode = 'api'
        
        return jsonify({
            'success': True,
            'mode': mode
        })
        
    except Exception as e:
        logger.error(f"데이터 소스 모드 조회 실패: {e}")
        # 오류 시 기본값 반환
        mode = os.environ.get('USE_DB_DIRECT_ACCESS', 'false').lower()
        return jsonify({
            'success': True,
            'mode': 'db' if mode == 'true' or mode == 'db' else 'api'
        })

@admin_api.route('/api/admin/data-source-mode', methods=['POST'])
@login_required
@admin_required
def set_data_source_mode():
    """데이터 소스 모드 설정 (DB 또는 API)"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'api')  # 'db' or 'api'
        
        if mode not in ['db', 'api']:
            return jsonify({
                'success': False,
                'error': 'Invalid mode. Must be "db" or "api"'
            }), 400
        
        # 'db'/'api'를 'true'/'false'로 변환하여 저장
        value = 'true' if mode == 'db' else 'false'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # system_settings에 저장
        cursor.execute("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES ('USE_DB_DIRECT_ACCESS', ?, ?)
        """, (value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # 환경 변수도 업데이트 (현재 프로세스에만 적용)
        os.environ['USE_DB_DIRECT_ACCESS'] = value
        
        logger.info(f"데이터 소스 모드 변경: {mode} (by {current_user.username})")
        
        return jsonify({
            'success': True,
            'mode': mode,
            'message': f'데이터 소스 모드가 "{mode}" 모드로 변경되었습니다. 변경 사항 적용을 위해 서버 재시작을 권장합니다.'
        })
        
    except Exception as e:
        logger.error(f"데이터 소스 모드 설정 실패: {e}")
        return jsonify({
            'success': False,
            'error': f'데이터 소스 모드 설정 실패: {str(e)}'
        }), 500

@admin_api.route('/api/admin/restart-server', methods=['POST'])
@login_required
@admin_required
def restart_server():
    """서버 재시작 (배치 파일 실행)"""
    import subprocess
    import os
    import sys
    from pathlib import Path
    
    try:
        logger.info(f"서버 재시작 요청: {current_user.username}")
        
        # 프로젝트 루트 디렉토리 찾기
        project_root = Path(__file__).parent.absolute()
        restart_script = project_root / 'restart_server_simple.bat'
        
        if not restart_script.exists():
            return jsonify({
                'success': False,
                'error': '재시작 스크립트를 찾을 수 없습니다.'
            }), 404
        
        # 배치 파일을 백그라운드에서 실행
        # Windows에서는 CREATE_NEW_CONSOLE 플래그 사용
        if sys.platform == 'win32':
            subprocess.Popen(
                [str(restart_script)],
                cwd=str(project_root),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                shell=True
            )
        else:
            # Linux/Mac의 경우
            subprocess.Popen(
                ['bash', str(restart_script)],
                cwd=str(project_root)
            )
        
        logger.info("서버 재시작 스크립트 실행됨")
        
        return jsonify({
            'success': True,
            'message': '서버 재시작이 시작되었습니다. 잠시 후 자동으로 연결됩니다.'
        })
        
    except Exception as e:
        logger.error(f"서버 재시작 실패: {e}")
        return jsonify({
            'success': False,
            'error': f'서버 재시작 실패: {str(e)}'
        }), 500
