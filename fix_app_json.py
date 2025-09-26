#!/usr/bin/env python3
"""
app.py를 JSON 전용으로 수정
"""

import re

def fix_app_json():
    """app.py를 JSON 전용으로 수정"""
    
    # app.py 파일 읽기
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # DB 관련 함수들을 JSON 전용으로 교체
    def replace_alarm_templates(match):
        return '''@app.route('/api/alarm-templates', methods=['GET'])
@login_required
def get_alarm_templates():
    """알람 템플릿 목록을 반환하는 API (JSON 기반)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        # JSON에서 실제 데이터 조회
        templates = json_manager.load_json_file('alarm_templates.json')
        
        return jsonify({
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm templates: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm templates: {str(e)}'
        }), 500'''
    
    def replace_alarm_recipients(match):
        return '''@app.route('/api/alarm-recipients', methods=['GET'])
@login_required
def get_alarm_recipients():
    """알람 수신자 목록을 반환하는 API (JSON 기반)"""
    try:
        # 관리자와 사이트 관리자 권한 확인
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({
                'success': False,
                'message': '관리자 권한이 필요합니다.'
            }), 403
        
        # JSON에서 실제 데이터 조회
        recipients = json_manager.load_json_file('alarm_recipients.json')
        
        return jsonify({
            'success': True,
            'recipients': recipients
        })
        
    except Exception as e:
        logger.error(f"Error getting alarm recipients: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting alarm recipients: {str(e)}'
        }), 500'''
    
    # 알람 템플릿 함수 교체
    content = re.sub(
        r'@app\.route\(\'/api/alarm-templates\'.*?def get_alarm_templates\(\):.*?except Exception as e:.*?return jsonify.*?500',
        replace_alarm_templates,
        content,
        flags=re.DOTALL
    )
    
    # 알람 수신자 함수 교체
    content = re.sub(
        r'@app\.route\(\'/api/alarm-recipients\'.*?def get_alarm_recipients\(\):.*?except Exception as e:.*?return jsonify.*?500',
        replace_alarm_recipients,
        content,
        flags=re.DOTALL
    )
    
    # 나머지 DB 관련 코드 제거
    content = re.sub(r'.*cursor.*\n', '', content)
    content = re.sub(r'.*conn.*\n', '', content)
    content = re.sub(r'.*sqlite.*\n', '', content)
    content = re.sub(r'.*existing_tables.*\n', '', content)
    content = re.sub(r'.*FROM.*\n', '', content)
    content = re.sub(r'.*SELECT.*\n', '', content)
    content = re.sub(r'.*INSERT.*\n', '', content)
    content = re.sub(r'.*UPDATE.*\n', '', content)
    content = re.sub(r'.*DELETE.*\n', '', content)
    
    # 빈 줄 정리
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # 파일 저장
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("app.py JSON 전용 수정 완료")

if __name__ == "__main__":
    fix_app_json()
