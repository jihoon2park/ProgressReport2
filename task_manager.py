"""
Task Manager for Policy-Driven Workflow System
정책 기반 워크플로우 시스템을 위한 작업 관리자
"""

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import uuid4

from fcm_service import get_fcm_service
from fcm_token_manager_sqlite import get_fcm_token_manager_sqlite as get_fcm_token_manager

logger = logging.getLogger(__name__)

class TaskManager:
    """정책 기반 작업 관리 클래스"""
    
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.fcm_service = get_fcm_service()
        self.token_manager = get_fcm_token_manager()
    
    def create_incident_workflow(
        self, 
        incident_id: str, 
        policy_id: int, 
        client_name: str,
        client_id: int,
        site: str,
        event_type: str,
        risk_rating: str,
        created_by: str
    ) -> Dict[str, Any]:
        """
        인시던트 발생 시 정책에 따른 워크플로우 생성
        1단계: 인시던트 발생 및 업무 생성 (서버)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 정책 정보 조회
            cursor.execute('''
                SELECT ep.*, es.step_number, es.delay_minutes, es.repeat_count, 
                       es.recipients, es.message_template
                FROM escalation_policies ep
                JOIN escalation_steps es ON ep.id = es.policy_id
                WHERE ep.id = ? AND ep.is_active = 1 AND es.is_active = 1
                ORDER BY es.step_number
            ''', (policy_id,))
            
            policy_steps = cursor.fetchall()
            if not policy_steps:
                return {'success': False, 'message': 'Policy not found or inactive'}
            
            policy_info = policy_steps[0]  # 첫 번째 행에서 정책 기본 정보 추출
            
            # 2. 인시던트 상태 업데이트
            cursor.execute('''
                UPDATE incidents_cache 
                SET workflow_status = 'in_progress', 
                    policy_id = ?, 
                    created_by = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE incident_id = ?
            ''', (policy_id, created_by, incident_id))
            
            # 3. 각 에스컬레이션 단계별로 스케줄된 작업 생성
            created_tasks = []
            total_tasks = 0
            
            for step in policy_steps:
                step_number, delay_minutes, repeat_count, recipients_json, message_template = step[7:12]
                
                try:
                    recipients = json.loads(recipients_json) if recipients_json else []
                except:
                    recipients = []
                
                # 반복 횟수만큼 작업 생성
                for repeat in range(repeat_count):
                    # 스케줄 시간 계산
                    schedule_time = datetime.now() + timedelta(
                        minutes=delay_minutes + (repeat * delay_minutes)
                    )
                    
                    # 각 수신자별로 작업 생성
                    for recipient in recipients:
                        task_id = f"TASK-{uuid4().hex[:8].upper()}"
                        deep_link = f"nursingapp://task/{task_id}"
                        
                        # 작업 유형 결정 (이벤트 타입에 따라)
                        task_type = self._determine_task_type(event_type, risk_rating)
                        task_description = self._generate_task_description(
                            task_type, client_name, message_template
                        )
                        
                        cursor.execute('''
                            INSERT INTO scheduled_tasks (
                                task_id, incident_id, policy_id, client_name, client_id,
                                task_type, task_description, scheduled_time, due_time,
                                priority, assigned_role, site, deep_link, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                        ''', (
                            task_id, incident_id, policy_id, client_name, client_id,
                            task_type, task_description, schedule_time, 
                            schedule_time + timedelta(hours=2),  # 2시간 마감
                            risk_rating.lower(), recipient, site, deep_link
                        ))
                        
                        created_tasks.append({
                            'task_id': task_id,
                            'scheduled_time': schedule_time.isoformat(),
                            'assigned_role': recipient,
                            'task_type': task_type,
                            'deep_link': deep_link
                        })
                        
                        total_tasks += 1
                        
                        # 작업 생성 로그
                        self._log_task_action(task_id, 'created', created_by, {
                            'incident_id': incident_id,
                            'policy_id': policy_id,
                            'step_number': step_number,
                            'repeat_number': repeat + 1
                        })
            
            # 4. 인시던트의 총 작업 수 업데이트
            cursor.execute('''
                UPDATE incidents_cache 
                SET total_tasks = ? 
                WHERE incident_id = ?
            ''', (total_tasks, incident_id))
            
            conn.commit()
            
            logger.info(f"인시던트 워크플로우 생성 완료: {incident_id}, 총 {total_tasks}개 작업")
            
            return {
                'success': True,
                'incident_id': incident_id,
                'policy_id': policy_id,
                'total_tasks_created': total_tasks,
                'tasks': created_tasks
            }
            
        except Exception as e:
            logger.error(f"워크플로우 생성 실패: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def send_scheduled_notifications(self) -> Dict[str, Any]:
        """
        스케줄된 알림 전송
        2단계: 알림 발송 (서버 → 모바일 앱)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 현재 시간에 실행해야 할 작업 조회
            current_time = datetime.now()
            cursor.execute('''
                SELECT task_id, incident_id, client_name, task_type, task_description,
                       assigned_role, site, deep_link, priority
                FROM scheduled_tasks 
                WHERE status = 'pending' 
                  AND scheduled_time <= ? 
                  AND notification_sent = 0
                ORDER BY priority DESC, scheduled_time ASC
                LIMIT 50
            ''', (current_time,))
            
            pending_tasks = cursor.fetchall()
            sent_count = 0
            failed_count = 0
            
            for task in pending_tasks:
                task_id, incident_id, client_name, task_type, task_description, \
                assigned_role, site, deep_link, priority = task
                
                # FCM 메시지 구성
                title = f"📋 Task Assignment - {client_name}"
                body = f"{task_description}. Please complete on PC and confirm in app."
                
                # 딥링크 데이터
                fcm_data = {
                    'type': 'task_notification',
                    'deep_link': deep_link,
                    'task_id': task_id,
                    'incident_id': incident_id,
                    'task_type': task_type,
                    'priority': priority,
                    'client_name': client_name,
                    'site': site
                }
                
                # 해당 역할의 사용자들에게 전송
                success = self._send_fcm_to_role(assigned_role, site, title, body, fcm_data)
                
                if success:
                    # 알림 전송 완료 상태 업데이트
                    cursor.execute('''
                        UPDATE scheduled_tasks 
                        SET notification_sent = 1, 
                            notification_count = notification_count + 1,
                            last_notification_time = CURRENT_TIMESTAMP,
                            status = 'in_progress'
                        WHERE task_id = ?
                    ''', (task_id,))
                    
                    # 알림 전송 로그
                    self._log_task_action(task_id, 'notified', 'system', {
                        'fcm_data': fcm_data,
                        'assigned_role': assigned_role
                    })
                    
                    sent_count += 1
                    logger.info(f"작업 알림 전송 완료: {task_id} -> {assigned_role}")
                else:
                    failed_count += 1
                    logger.error(f"작업 알림 전송 실패: {task_id}")
            
            conn.commit()
            
            return {
                'success': True,
                'sent_count': sent_count,
                'failed_count': failed_count,
                'total_processed': len(pending_tasks)
            }
            
        except Exception as e:
            logger.error(f"스케줄된 알림 전송 실패: {e}")
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def complete_task(self, task_id: str, completed_by: str, notes: str = None) -> Dict[str, Any]:
        """
        작업 완료 처리
        4단계: 완료 처리 및 상태 동기화 (PC/모바일 → 서버)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. 작업 정보 조회
            cursor.execute('''
                SELECT incident_id, status FROM scheduled_tasks 
                WHERE task_id = ?
            ''', (task_id,))
            
            task_info = cursor.fetchone()
            if not task_info:
                return {'success': False, 'message': 'Task not found'}
            
            incident_id, current_status = task_info
            
            if current_status == 'completed':
                return {'success': False, 'message': 'Task already completed'}
            
            # 2. 작업 완료 상태 업데이트
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    completed_by = ?,
                    completion_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (completed_by, notes, task_id))
            
            # 3. 완료 로그 기록
            self._log_task_action(task_id, 'completed', completed_by, {
                'completion_notes': notes,
                'completed_at': datetime.now().isoformat()
            })
            
            # 4. 인시던트 완료 상태 확인 및 업데이트
            cursor.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM scheduled_tasks 
                WHERE incident_id = ?
            ''', (incident_id,))
            
            task_counts = cursor.fetchone()
            total_tasks, completed_tasks = task_counts
            
            # 인시던트 완료 상태 업데이트
            cursor.execute('''
                UPDATE incidents_cache 
                SET completed_tasks = ?,
                    workflow_status = CASE 
                        WHEN ? = ? THEN 'closed' 
                        ELSE 'in_progress' 
                    END,
                    closed_at = CASE 
                        WHEN ? = ? THEN CURRENT_TIMESTAMP 
                        ELSE closed_at 
                    END,
                    closed_by = CASE 
                        WHEN ? = ? THEN ? 
                        ELSE closed_by 
                    END
                WHERE incident_id = ?
            ''', (completed_tasks, completed_tasks, total_tasks, 
                  completed_tasks, total_tasks, completed_tasks, total_tasks, 
                  completed_by, incident_id))
            
            conn.commit()
            
            # 5단계: 인시던트 종결 처리
            incident_closed = (completed_tasks == total_tasks)
            if incident_closed:
                logger.info(f"인시던트 완료: {incident_id} (모든 작업 완료)")
            
            return {
                'success': True,
                'task_id': task_id,
                'incident_id': incident_id,
                'incident_closed': incident_closed,
                'progress': {
                    'completed_tasks': completed_tasks,
                    'total_tasks': total_tasks,
                    'completion_rate': round((completed_tasks / total_tasks) * 100, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"작업 완료 처리 실패: {e}")
            if conn:
                conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            if conn:
                conn.close()
    
    def get_user_tasks(self, user_role: str, site: str, status: str = None) -> List[Dict[str, Any]]:
        """사용자의 할당된 작업 목록 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT task_id, incident_id, client_name, task_type, task_description,
                       scheduled_time, due_time, status, priority, deep_link,
                       notification_sent, created_at
                FROM scheduled_tasks 
                WHERE assigned_role = ? AND site = ?
            '''
            params = [user_role, site]
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY priority DESC, scheduled_time ASC'
            
            cursor.execute(query, params)
            tasks = cursor.fetchall()
            
            task_list = []
            for task in tasks:
                task_list.append({
                    'task_id': task[0],
                    'incident_id': task[1],
                    'client_name': task[2],
                    'task_type': task[3],
                    'task_description': task[4],
                    'scheduled_time': task[5],
                    'due_time': task[6],
                    'status': task[7],
                    'priority': task[8],
                    'deep_link': task[9],
                    'notification_sent': bool(task[10]),
                    'created_at': task[11]
                })
            
            return task_list
            
        except Exception as e:
            logger.error(f"사용자 작업 목록 조회 실패: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def _determine_task_type(self, event_type: str, risk_rating: str) -> str:
        """이벤트 타입과 위험도에 따른 작업 타입 결정"""
        task_type_mapping = {
            'emergency': 'emergency_assessment',
            'medication': 'medication_check',
            'handover': 'handover_notes',
            'maintenance': 'facility_check',
            'medical': 'medical_assessment',
            'normal': 'routine_check'
        }
        
        base_type = task_type_mapping.get(event_type, 'general_task')
        
        # 위험도가 높으면 vital_chart 추가
        if risk_rating.lower() in ['high', 'extreme']:
            return 'vital_chart'
        
        return base_type
    
    def _generate_task_description(self, task_type: str, client_name: str, template: str) -> str:
        """작업 설명 생성"""
        task_descriptions = {
            'vital_chart': f"{client_name} - Vital signs chart required",
            'medication_check': f"{client_name} - Medication administration check",
            'emergency_assessment': f"{client_name} - Emergency situation assessment",
            'routine_check': f"{client_name} - Routine care check"
        }
        
        base_description = task_descriptions.get(task_type, f"{client_name} - Care task")
        
        if template and template != base_description:
            return f"{base_description}. {template}"
        
        return base_description
    
    def _send_fcm_to_role(self, role: str, site: str, title: str, body: str, data: Dict[str, str]) -> bool:
        """특정 역할의 사용자들에게 FCM 메시지 전송"""
        try:
            if not self.fcm_service or not self.token_manager:
                logger.error("FCM 서비스 또는 토큰 매니저가 초기화되지 않음")
                return False
            
            # 해당 역할과 사이트의 사용자 토큰 조회 (실제로는 더 정교한 필터링 필요)
            all_tokens = self.token_manager.get_all_tokens()
            
            if not all_tokens:
                logger.warning(f"전송할 FCM 토큰이 없음 (역할: {role}, 사이트: {site})")
                return False
            
            # FCM 전송
            result = self.fcm_service.send_notification_to_tokens(
                all_tokens, title, body, data
            )
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"FCM 전송 실패: {e}")
            return False
    
    def _log_task_action(self, task_id: str, action: str, performed_by: str, details: Dict[str, Any]):
        """작업 실행 로그 기록"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO task_execution_logs (
                    task_id, action, performed_by, details
                ) VALUES (?, ?, ?, ?)
            ''', (task_id, action, performed_by, json.dumps(details)))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"작업 로그 기록 실패: {e}")
        finally:
            if conn:
                conn.close()


# Flask 앱에서 사용할 전역 인스턴스
task_manager = None

def get_task_manager() -> TaskManager:
    """TaskManager 싱글톤 인스턴스 반환"""
    global task_manager
    if task_manager is None:
        task_manager = TaskManager()
    return task_manager
