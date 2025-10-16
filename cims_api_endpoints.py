#!/usr/bin/env python3
"""
CIMS RESTful API Endpoints
Mobile Application과 Web Dashboard를 위한 API 엔드포인트
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import uuid
import base64
import os
from cims_policy_engine import PolicyEngine
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Blueprint 생성
cims_api = Blueprint('cims_api', __name__, url_prefix='/api/v1')

def get_db_connection():
    """데이터베이스 연결"""
    conn = sqlite3.connect('progress_report.db', timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def require_role(*allowed_roles):
    """역할 기반 접근 제어 데코레이터"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = current_user.role
            print(f"User role: {user_role}, Allowed roles: {allowed_roles}")
            
            # admin은 모든 역할에 접근 가능
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # 직접 역할 확인
            if user_role in allowed_roles:
                return f(*args, **kwargs)
            
            # clinical_manager는 admin 권한도 가짐
            if user_role == 'clinical_manager' and 'admin' in allowed_roles:
                return f(*args, **kwargs)
            
            return jsonify({'error': 'Insufficient permissions'}), 403
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# ==============================
# Core Endpoint 1: Incident Reporting
# ==============================

@cims_api.route('/incidents', methods=['POST'])
@login_required
@require_role('registered_nurse', 'nurse', 'carer')
def create_incident():
    """
    POST /api/v1/incidents
    새 인시던트 생성 및 정책 엔진 트리거
    """
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['resident_id', 'type', 'severity', 'incident_time', 'brief_description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 인시던트 ID 생성
        incident_id = f"I-{uuid.uuid4().hex[:6].upper()}"
        
        # 사진 첨부파일 처리
        photo_attachments = []
        if data.get('photo_attachments'):
            for i, photo_data in enumerate(data['photo_attachments']):
                if photo_data.startswith('data:image'):
                    # Base64 이미지 저장
                    photo_filename = f"incident_{incident_id}_{i+1}.jpg"
                    photo_path = save_base64_image(photo_data, photo_filename)
                    photo_attachments.append(photo_path)
        
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
            data.get('resident_name', f"Resident {data['resident_id']}"),
            data['type'],
            data['severity'],
            'Open',
            data['incident_time'],
            data.get('location', ''),
            data['brief_description'],
            json.dumps(data.get('initial_actions_taken', [])),
            data.get('witnesses', ''),
            current_user.id,
            data.get('site', 'Unknown'),
            datetime.now().isoformat()
        ))
        
        incident_db_id = cursor.lastrowid
        conn.commit()
        
        # 정책 엔진 트리거
        policy_engine = PolicyEngine()
        incident_data = {
            'id': incident_db_id,
            'incident_id': incident_id,
            'type': data['type'],
            'severity': data['severity'],
            'incident_date': data['incident_time'],
            'resident_id': data['resident_id'],
            'resident_name': data.get('resident_name', f"Resident {data['resident_id']}")
        }
        
        generated_tasks = policy_engine.apply_policies_to_incident(incident_data)
        
        # 감사 로그
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
                'incident_type': data['type'],
                'severity': data['severity'],
                'tasks_generated': len(generated_tasks),
                'photo_attachments': len(photo_attachments)
            })
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'incident_id': incident_id,
            'status': 'Open',
            'message': f'Incident reported successfully. {len(generated_tasks)} tasks have been generated by the Policy Engine.',
            'generated_tasks': [task.get('task_id') for task in generated_tasks]
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# Core Endpoint 2: Personalized Task Dashboard
# ==============================

@cims_api.route('/tasks/me', methods=['GET'])
@login_required
@require_role('registered_nurse', 'nurse', 'carer')
def get_my_tasks():
    """
    GET /api/v1/tasks/me
    현재 사용자에게 할당된 태스크 조회
    """
    try:
        status_filter = request.args.get('status', 'active')
        sort_by = request.args.get('sort_by', 'due_date')
        
        policy_engine = PolicyEngine()
        
        # 상태 필터 매핑
        status_mapping = {
            'active': ['pending', 'in_progress'],
            'overdue': ['overdue'],
            'completed': ['completed']
        }
        
        if status_filter in status_mapping:
            tasks = []
            for status in status_mapping[status_filter]:
                user_tasks = policy_engine.get_user_tasks(
                    user_id=current_user.id,
                    role=current_user.role,
                    status_filter=status
                )
                tasks.extend(user_tasks)
        else:
            tasks = policy_engine.get_user_tasks(
                user_id=current_user.id,
                role=current_user.role
            )
        
        # 태스크 포맷팅
        formatted_tasks = []
        for task in tasks:
            # 긴급도 계산
            due_date = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
            now = datetime.now()
            time_diff = due_date - now
            
            if time_diff.total_seconds() < 0:
                urgency = 'Overdue'
                status = 'overdue'
            elif time_diff.total_seconds() < 4 * 3600:  # 4시간 미만
                urgency = 'High'
                status = 'active'
            elif time_diff.total_seconds() < 24 * 3600:  # 24시간 미만
                urgency = 'Medium'
                status = 'active'
            else:
                urgency = 'Low'
                status = 'active'
            
            formatted_task = {
                'task_id': task.get('task_id'),
                'incident_id': task.get('incident_number'),
                'resident_name': task.get('resident_name'),
                'description': task.get('task_name'),
                'assigned_role': task.get('assigned_role'),
                'due_date': task.get('due_date'),
                'urgency': urgency,
                'status': status,
                'note_type': task.get('note_type', ''),
                'priority': task.get('priority', 'normal')
            }
            formatted_tasks.append(formatted_task)
        
        # 정렬
        if sort_by == 'due_date':
            formatted_tasks.sort(key=lambda x: x['due_date'])
        elif sort_by == 'urgency':
            urgency_order = {'Overdue': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            formatted_tasks.sort(key=lambda x: urgency_order.get(x['urgency'], 4))
        
        return jsonify(formatted_tasks), 200
        
    except Exception as e:
        logger.error(f"Error getting user tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# Core Endpoint 3: Task Completion & Progress Notes
# ==============================

@cims_api.route('/tasks/<task_id>/complete', methods=['POST'])
@login_required
@require_role('registered_nurse', 'nurse', 'carer')
def complete_task(task_id):
    """
    POST /api/v1/tasks/{task_id}/complete
    태스크 완료 및 진행 노트 제출
    """
    try:
        data = request.get_json()
        
        if not data.get('progress_note'):
            return jsonify({'error': 'Progress note is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 태스크 존재 확인
        cursor.execute("SELECT * FROM cims_tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 권한 확인 (할당된 사용자 또는 같은 역할)
        if task['assigned_user_id'] and task['assigned_user_id'] != current_user.id:
            if not current_user.is_admin():
                return jsonify({'error': 'Not authorized to complete this task'}), 403
        
        # 진행 노트 저장
        progress_note = data['progress_note']
        note_id = f"PN-{uuid.uuid4().hex[:8].upper()}"
        
        cursor.execute("""
            INSERT INTO cims_progress_notes (
                note_id, incident_id, task_id, author_id, content, note_type,
                vitals_data, assessment_data, attachments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            note_id,
            task['incident_id'],
            task['id'],
            current_user.id,
            progress_note.get('narrative_content', ''),
            progress_note.get('note_type', task['note_type']),
            json.dumps(progress_note.get('dynamic_fields', {})),
            json.dumps(progress_note.get('follow_up_checks', {})),
            json.dumps(progress_note.get('attachments', [])),
            datetime.now().isoformat()
        ))
        
        # 태스크 완료 처리
        completed_at = datetime.now()
        cursor.execute("""
            UPDATE cims_tasks 
            SET status = 'completed', 
                completed_by_user_id = ?, 
                completed_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (current_user.id, completed_at, completed_at, task['id']))
        
        # 컴플라이언스 상태 확인
        due_date = datetime.fromisoformat(task['due_date'])
        compliance_status = "On Time" if completed_at <= due_date else "Late"
        
        # 감사 로그
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'task_completed',
            'task',
            task['id'],
            json.dumps({
                'compliance_status': compliance_status,
                'completed_at': completed_at.isoformat(),
                'due_date': task['due_date']
            })
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'task_id': task_id,
            'status': 'Completed',
            'completed_at': completed_at.isoformat(),
            'progress_note_id': note_id,
            'message': f'Task completed and Progress Note saved successfully. Compliance status: {compliance_status}.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# Analytics Endpoints
# ==============================

@cims_api.route('/analytics/compliance-summary', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_compliance_summary():
    """
    GET /api/v1/analytics/compliance-summary
    컴플라이언스 요약 분석
    """
    try:
        period = request.args.get('period', 'last_30_days')
        
        # 기간 계산
        if period == 'last_7_days':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'last_30_days':
            start_date = datetime.now() - timedelta(days=30)
        elif period == 'quarter':
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 인시던트 통계
        cursor.execute("""
            SELECT 
                COUNT(*) as total_incidents,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents
            FROM cims_incidents 
            WHERE created_at >= ?
        """, (start_date.isoformat(),))
        
        incident_stats = cursor.fetchone()
        
        # 컴플라이언스 메트릭
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' AND completed_at <= due_date THEN 1 ELSE 0 END) as on_time_tasks,
                SUM(CASE WHEN status IN ('pending', 'in_progress') AND due_date < datetime('now') THEN 1 ELSE 0 END) as overdue_tasks
            FROM cims_tasks 
            WHERE created_at >= ?
        """, (start_date.isoformat(),))
        
        task_stats = cursor.fetchone()
        
        # 기한 초과 직원 (CIMS 시스템에서는 assigned_user_id를 직접 사용)
        cursor.execute("""
            SELECT DISTINCT assigned_user_id as username
            FROM cims_tasks t
            WHERE t.status IN ('pending', 'in_progress') 
            AND t.due_date < datetime('now')
            AND t.created_at >= ?
            LIMIT 10
        """, (start_date.isoformat(),))
        
        overdue_staff = cursor.fetchall()
        
        # 인시던트 유형별 위험 영역
        cursor.execute("""
            SELECT 
                incident_type as type,
                COUNT(*) as count,
                ROUND(
                    CAST(SUM(CASE WHEN t.status = 'completed' AND t.completed_at <= t.due_date THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / 
                    COUNT(t.id), 1
                ) as compliance_rate
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.created_at >= ?
            GROUP BY incident_type
            ORDER BY count DESC
            LIMIT 5
        """, (start_date.isoformat(),))
        
        risk_areas = cursor.fetchall()
        
        conn.close()
        
        # 컴플라이언스 비율 계산
        total_tasks = task_stats['total_tasks'] or 1
        compliance_rate = round((task_stats['on_time_tasks'] or 0) * 100.0 / total_tasks, 1)
        
        return jsonify({
            'incident_counts': {
                'total_incidents': incident_stats['total_incidents'] or 0,
                'open_incidents': incident_stats['open_incidents'] or 0,
                'closed_incidents': incident_stats['closed_incidents'] or 0
            },
            'compliance_metrics': {
                'overall_compliance_rate': compliance_rate,
                'overdue_tasks_count': task_stats['overdue_tasks'] or 0,
                'total_tasks': total_tasks,
                'overdue_staff': [f"User {staff['username']}" for staff in overdue_staff],
                'avg_completion_time_min': 15.4  # 임시 값
            },
            'top_risk_areas': [
                {
                    'type': area['type'],
                    'count': area['count'],
                    'compliance_rate': area['compliance_rate'] or 0
                }
                for area in risk_areas
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting compliance summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cims_api.route('/analytics/incidents-by-type', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_incidents_by_type():
    """인시던트 유형별 통계 조회"""
    try:
        period = request.args.get('period', 'last_30_days')
        
        # 기간 계산
        if period == 'last_7_days':
            start_date = datetime.now() - timedelta(days=7)
        elif period == 'last_30_days':
            start_date = datetime.now() - timedelta(days=30)
        elif period == 'quarter':
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                incident_type as type,
                COUNT(*) as count,
                SUM(CASE WHEN severity = 'High' THEN 1 ELSE 0 END) as severity_high,
                ROUND(
                    (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM cims_incidents WHERE created_at >= ?)), 
                    1
                ) as percentage
            FROM cims_incidents
            WHERE created_at >= ?
            GROUP BY incident_type
            ORDER BY count DESC
        """, (start_date.isoformat(), start_date.isoformat()))
        
        incidents_by_type = cursor.fetchall()
        conn.close()
        
        return jsonify([
            {
                'type': row['type'],
                'count': row['count'],
                'severity_high': row['severity_high'],
                'percentage': row['percentage']
            }
            for row in incidents_by_type
        ])
        
    except Exception as e:
        logger.error(f"Error getting incidents by type: {e}")
        return jsonify({'error': 'Failed to get incidents by type'}), 500

@cims_api.route('/tasks/overdue', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_overdue_tasks():
    """
    GET /api/v1/tasks/overdue
    기한 초과 태스크 목록
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                t.task_id,
                i.incident_id,
                i.resident_name,
                t.task_name as description,
                t.assigned_user_id as assigned_user,
                t.due_date,
                ROUND((julianday('now') - julianday(t.due_date)) * 24, 1) as overdue_by_hours
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE t.status IN ('pending', 'in_progress')
            AND t.due_date < datetime('now')
            ORDER BY t.due_date ASC
        """)
        
        overdue_tasks = cursor.fetchall()
        conn.close()
        
        return jsonify([
            {
                'task_id': task['task_id'],
                'incident_id': task['incident_id'],
                'resident_name': task['resident_name'],
                'description': task['description'],
                'assigned_user': task['assigned_user'] or 'Unassigned',
                'due_date': task['due_date'],
                'overdue_by_hours': task['overdue_by_hours']
            }
            for task in overdue_tasks
        ]), 200
        
    except Exception as e:
        logger.error(f"Error getting overdue tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# MANAD Plus Integration Endpoints
# ==============================

@cims_api.route('/tasks/<task_id>/confirm-completion', methods=['POST'])
@login_required
@require_role('registered_nurse', 'nurse', 'carer')
def confirm_task_completion(task_id):
    """
    POST /api/v1/tasks/{task_id}/confirm-completion
    MANAD Plus에서 완료된 태스크 확인 (Progress Note 작성 완료 확인)
    """
    try:
        data = request.get_json()
        
        if not data.get('confirmed_at'):
            return jsonify({'error': 'Confirmation timestamp is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 태스크 존재 확인
        cursor.execute("SELECT * FROM cims_tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 권한 확인 (할당된 사용자 또는 같은 역할)
        if task['assigned_user_id'] and task['assigned_user_id'] != current_user.id:
            if not current_user.is_admin():
                return jsonify({'error': 'Not authorized to complete this task'}), 403
        
        # 태스크 완료 확인 처리 (Pending 상태로 변경 - 시스템 검증 대기)
        confirmed_at = datetime.fromisoformat(data['confirmed_at'].replace('Z', '+00:00'))
        
        cursor.execute("""
            UPDATE cims_tasks 
            SET status = 'Pending', 
                completed_by_user_id = ?, 
                updated_at = ?,
                completion_method = 'manad_plus_confirmation',
                pending_confirmation_at = ?
            WHERE id = ?
        """, (current_user.id, confirmed_at, confirmed_at, task['id']))
        
        # 컴플라이언스 상태 확인
        due_date = datetime.fromisoformat(task['due_date'])
        compliance_status = "On Time" if confirmed_at <= due_date else "Late"
        
        # 감사 로그 (MANAD Plus 통합 방식)
        cursor.execute("""
            INSERT INTO cims_audit_logs (
                log_id, user_id, action, target_entity_type, target_entity_id, details
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"LOG-{uuid.uuid4().hex[:8].upper()}",
            current_user.id,
            'task_confirmed_manad_plus',
            'task',
            task['id'],
            json.dumps({
                'compliance_status': compliance_status,
                'confirmed_at': confirmed_at.isoformat(),
                'due_date': task['due_date'],
                'confirmation_method': 'manad_plus_completion',
                'local_confirmation_time': data.get('confirmed_at')
            })
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'task_id': task_id,
            'status': 'Pending',
            'confirmed_at': confirmed_at.isoformat(),
            'compliance_status': compliance_status,
            'message': f'Task completion confirmed. Awaiting system validation. Compliance status: {compliance_status}.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error confirming task completion: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cims_api.route('/tasks/<task_id>', methods=['GET'])
@login_required
@require_role('registered_nurse', 'nurse', 'carer')
def get_task_details(task_id):
    """
    GET /api/v1/tasks/{task_id}
    특정 태스크 상세 정보 조회
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.*, i.resident_name, i.incident_id as incident_number, i.manad_incident_id
            FROM cims_tasks t
            JOIN cims_incidents i ON t.incident_id = i.id
            WHERE t.task_id = ?
        """, (task_id,))
        
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 권한 확인
        if task['assigned_user_id'] and task['assigned_user_id'] != current_user.id:
            if not current_user.is_admin():
                return jsonify({'error': 'Not authorized to view this task'}), 403
        
        # 태스크 정보 포맷팅
        task_info = {
            'task_id': task['task_id'],
            'title': task['task_name'],
            'description': task['description'] or task['task_name'],
            'due_date': task['due_date'],
            'priority': task['priority'],
            'status': task['status'],
            'incident_id': task['incident_number'],
            'manad_incident_id': task['manad_incident_id'],
            'resident': {
                'name': task['resident_name'],
                'id': task.get('resident_id', 'Unknown'),
                'room': 'Unknown'  # 거주자 상세 정보는 별도 API에서 조회
            },
            'assigned_role': task['assigned_role'],
            'note_type': task['note_type']
        }
        
        return jsonify(task_info), 200
        
    except Exception as e:
        logger.error(f"Error getting task details: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cims_api.route('/integrator/status', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_integrator_status():
    """
    GET /api/v1/integrator/status
    MANAD Plus Integrator 상태 조회
    """
    try:
        from manad_plus_integrator import get_manad_integrator
        
        integrator = get_manad_integrator()
        status = integrator.get_status()
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error getting integrator status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cims_api.route('/integrator/start', methods=['POST'])
@login_required
@require_role('admin')
def start_integrator():
    """
    POST /api/v1/integrator/start
    MANAD Plus Integrator 시작
    """
    try:
        from manad_plus_integrator import get_manad_integrator
        
        integrator = get_manad_integrator()
        
        if integrator.start_polling():
            return jsonify({'message': 'MANAD Plus integrator started successfully'}), 200
        else:
            return jsonify({'error': 'Failed to start integrator'}), 500
        
    except Exception as e:
        logger.error(f"Error starting integrator: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cims_api.route('/integrator/stop', methods=['POST'])
@login_required
@require_role('admin')
def stop_integrator():
    """
    POST /api/v1/integrator/stop
    MANAD Plus Integrator 중지
    """
    try:
        from manad_plus_integrator import get_manad_integrator
        
        integrator = get_manad_integrator()
        integrator.stop_polling()
        
        return jsonify({'message': 'MANAD Plus integrator stopped successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error stopping integrator: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# ==============================
# Helper Functions
# ==============================

def save_base64_image(base64_data, filename):
    """Base64 이미지를 파일로 저장"""
    try:
        # data:image/jpeg;base64, 부분 제거
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # 저장 디렉토리 생성
        upload_dir = 'static/uploads/incidents'
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일 저장
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(base64_data))
        
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return None
