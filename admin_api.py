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
    from api_key_manager import get_api_key_manager
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
        
        manager = get_api_key_manager()
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
        
        manager = get_api_key_manager()
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
        
        manager = get_api_key_manager()
        
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
        manager = get_api_key_manager()
        
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
        
        manager = get_api_key_manager()
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
        
        manager = get_api_key_manager()
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
        
        manager = get_api_key_manager()
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
        
        manager = get_api_key_manager()
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
        # 데이터베이스 연결 상태 확인
        db_status = {'connected': False}
        try:
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            db_status['connected'] = True
        except Exception as e:
            db_status['error'] = str(e)
        
        # 암호화 키 상태 확인
        encryption_status = {'available': False}
        try:
            if API_KEY_MANAGER_AVAILABLE:
                manager = get_api_key_manager()
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
