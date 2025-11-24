"""
CIMS Service Layer
CIMS 관련 비즈니스 로직 처리
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sqlite3

logger = logging.getLogger(__name__)


class CIMSService:
    """CIMS 비즈니스 로직 처리 서비스"""
    
    @staticmethod
    def ensure_fall_policy_exists(conn: sqlite3.Connection) -> bool:
        """
        Fall Policy가 DB에 존재하는지 확인하고 없으면 기본 Policy 생성
        
        Args:
            conn: DB 연결 객체
            
        Returns:
            bool: Policy가 존재하거나 생성 성공하면 True
        """
        cursor = conn.cursor()
        
        try:
            # Check if Fall policy exists
            cursor.execute("""
                SELECT COUNT(*) FROM cims_policies 
                WHERE policy_id = 'FALL-001' AND is_active = 1
            """)
            
            if cursor.fetchone()[0] > 0:
                logger.info("✅ Fall Policy already exists")
                return True
            
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
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating Fall Policy: {str(e)}")
            conn.rollback()
            return False
    
    @staticmethod
    def auto_generate_fall_tasks(
        incident_db_id: int, 
        incident_date_iso: str, 
        cursor: sqlite3.Cursor
    ) -> int:
        """
        Fall incident에 대해 자동으로 task 생성
        Progress Note를 분석하여 Witnessed/Unwitnessed를 자동 감지하고 적절한 Policy 적용
        
        Args:
            incident_db_id: CIMS DB의 incident ID (integer)
            incident_date_iso: Incident 발생 시간 (ISO format string)
            cursor: DB cursor
            
        Returns:
            생성된 task 수
        """
        try:
            # Fall 유형 감지 및 적절한 Policy 선택
            from services.fall_policy_detector import fall_detector
            
            fall_policy = fall_detector.get_appropriate_policy_for_incident(
                incident_db_id, 
                cursor
            )
            
            if not fall_policy:
                logger.warning(f"No active Fall policy found for task generation")
                return 0
            
            policy_id = fall_policy['id']
            visit_schedule = fall_policy['rules'].get('nurse_visit_schedule', [])
            common_tasks = fall_policy['rules'].get('common_assessment_tasks', '')
            
            if not visit_schedule:
                logger.warning(f"No visit schedule in Fall policy")
                return 0
            
            # Calculate visit times
            incident_time = datetime.fromisoformat(incident_date_iso)
            phase_start_time = incident_time
            tasks_created = 0
            
            for phase_idx, phase in enumerate(visit_schedule, 1):
                interval = int(phase.get('interval', 30))
                interval_unit = phase.get('interval_unit', 'minutes')
                duration = int(phase.get('duration', 2))
                duration_unit = phase.get('duration_unit', 'hours')
                
                interval_minutes = interval * 60 if interval_unit == 'hours' else interval
                duration_minutes = duration * 60 if duration_unit == 'hours' else duration * 24 * 60 if duration_unit == 'days' else duration
                
                num_visits = max(1, duration_minutes // interval_minutes)
                
                for visit_num in range(num_visits):
                    visit_time = phase_start_time + timedelta(minutes=visit_num * interval_minutes)
                    
                    task_name = f"Phase {phase_idx} Visit {visit_num + 1}: Nurse Assessment"
                    task_description = common_tasks if common_tasks else "Complete neurological observations and monitor for changes"
                    task_id = f"TASK-INC{incident_db_id}-P{phase_idx}-V{visit_num + 1}"
                    
                    cursor.execute("""
                        INSERT INTO cims_tasks 
                        (incident_id, policy_id, task_id, task_name, description, 
                         assigned_role, due_date, status, priority, 
                         documentation_required, note_type, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        incident_db_id,
                        policy_id,
                        task_id,
                        task_name,
                        task_description,
                        'Registered Nurse',
                        visit_time.isoformat(),
                        'pending',
                        'high',
                        1,
                        'Dynamic Form - Post Fall Assessment',
                        datetime.now().isoformat()
                    ))
                    
                    tasks_created += 1
                
                phase_start_time = phase_start_time + timedelta(minutes=duration_minutes)
            
            return tasks_created
            
        except Exception as e:
            logger.error(f"Error generating fall tasks: {str(e)}")
            return 0
    
    @staticmethod
    def get_fall_policy(cursor: sqlite3.Cursor) -> Optional[Dict]:
        """
        활성화된 Fall Policy 조회
        
        Args:
            cursor: DB cursor
            
        Returns:
            Fall Policy 정보 또는 None
        """
        try:
            cursor.execute("""
                SELECT id, name, rules_json
                FROM cims_policies
                WHERE is_active = 1
            """)
            
            policies = cursor.fetchall()
            
            for policy_row in policies:
                try:
                    rules = json.loads(policy_row[2])
                    association = rules.get('incident_association', {})
                    if association.get('incident_type') == 'Fall':
                        return {
                            'id': policy_row[0],
                            'name': policy_row[1],
                            'rules': rules
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting fall policy: {str(e)}")
            return None
    
    @staticmethod
    def check_and_update_incident_status(
        incident_id: int,
        cursor: sqlite3.Cursor
    ) -> bool:
        """
        Incident의 모든 태스크 완료 여부를 확인하여 status 업데이트
        
        Args:
            incident_id: Incident DB ID
            cursor: DB cursor
            
        Returns:
            업데이트 성공 여부
        """
        try:
            # Get all tasks for the incident
            cursor.execute("""
                SELECT COUNT(*) as total_tasks,
                       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tasks
                FROM cims_tasks
                WHERE incident_id = ?
            """, (incident_id,))
            
            result = cursor.fetchone()
            total_tasks = result[0]
            completed_tasks = result[1]
            
            if total_tasks == 0:
                return False
            
            # Update incident status based on task completion
            if completed_tasks == total_tasks:
                new_status = 'Closed'
            else:
                # Check for overdue tasks
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM cims_tasks
                    WHERE incident_id = ? 
                    AND status != 'Completed'
                    AND due_date < datetime('now')
                """, (incident_id,))
                
                overdue_count = cursor.fetchone()[0]
                new_status = 'Overdue' if overdue_count > 0 else 'Open'
            
            cursor.execute("""
                UPDATE cims_incidents 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (new_status, datetime.now().isoformat(), incident_id))
            
            logger.info(f"Updated incident {incident_id} status to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating incident status: {str(e)}")
            return False


# 전역 서비스 인스턴스
cims_service = CIMSService()

