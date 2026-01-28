"""
CIMS Policy Engine
Engine that parses policy rules and automatically generates tasks based on incidents
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

class PolicyEngine:
    """Policy Engine - Automatically generates tasks based on incidents"""
    
    def __init__(self, db_path: str = "progress_report.db"):
        self.db_path = db_path
    
    def get_db_connection(self):
        """Return database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def apply_policies_to_incident(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply policies to incident and generate tasks
        
        Args:
            incident_data: Incident information
            
        Returns:
            List of generated tasks
        """
        try:
            # Analyze Post Fall Timeline for Fall Incidents
            if incident_data.get('type') == 'Fall':
                logger.info(f"Fall incident detected: {incident_data.get('incident_id')}")
                return self._apply_fall_policy_with_timeline(incident_data)
            
            # Find applicable policies
            applicable_policies = self._find_applicable_policies(incident_data)
            
            if not applicable_policies:
                logger.warning(f"No applicable policies found for incident: {incident_data}")
                return []
            
            # Generate tasks
            generated_tasks = []
            for policy in applicable_policies:
                tasks = self._generate_tasks_from_policy(policy, incident_data)
                generated_tasks.extend(tasks)
            
            # Save tasks to database
            saved_tasks = self._save_tasks_to_database(generated_tasks)
            
            logger.info(f"Generated {len(saved_tasks)} tasks for incident {incident_data.get('incident_id')}")
            return saved_tasks
            
        except Exception as e:
            logger.error(f"Error applying policies to incident: {e}")
            return []
    
    def _find_applicable_policies(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find applicable policies for incident"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Query active policies
            cursor.execute("""
                SELECT * FROM cims_policies 
                WHERE is_active = 1 
                AND effective_date <= ? 
                AND (expiry_date IS NULL OR expiry_date > ?)
                ORDER BY effective_date DESC
            """, (datetime.now(), datetime.now()))
            
            policies = cursor.fetchall()
            applicable_policies = []
            
            for policy in policies:
                try:
                    rules_json = json.loads(policy['rules_json'])
                    if self._check_policy_conditions(rules_json, incident_data):
                        applicable_policies.append({
                            'id': policy['id'],
                            'policy_id': policy['policy_id'],
                            'name': policy['name'],
                            'rules_json': rules_json
                        })
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in policy {policy['policy_id']}: {e}")
                    continue
            
            conn.close()
            return applicable_policies
            
        except Exception as e:
            logger.error(f"Error finding applicable policies: {e}")
            return []
    
    def _check_policy_conditions(self, rules_json: Dict[str, Any], incident_data: Dict[str, Any]) -> bool:
        """Check if policy conditions match incident"""
        try:
            # Check incident association first (new format)
            if 'incident_association' in rules_json:
                return self._check_incident_association(rules_json['incident_association'], incident_data)
            
            # Fallback to old rule_sets format
            rule_sets = rules_json.get('rule_sets', [])
            
            for rule_set in rule_sets:
                trigger_condition = rule_set.get('trigger_condition', {})
                if self._evaluate_condition(trigger_condition, incident_data):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking policy conditions: {e}")
            return False
    
    def _check_incident_association(self, incident_association: Dict[str, Any], incident_data: Dict[str, Any]) -> bool:
        """Check incident association conditions"""
        try:
            # Check incident type
            policy_incident_type = incident_association.get('incident_type')
            incident_type = incident_data.get('type') or incident_data.get('incident_type')
            
            if policy_incident_type and incident_type != policy_incident_type:
                return False
            
            # Check severity level
            policy_severity = incident_association.get('severity_level')
            incident_severity = incident_data.get('severity')
            
            if policy_severity and incident_severity != policy_severity:
                return False
            
            # Check applicable sites
            applicable_sites = incident_association.get('applicable_sites', [])
            incident_site = incident_data.get('site')
            
            if applicable_sites and 'All' not in applicable_sites:
                if not incident_site or incident_site not in applicable_sites:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking incident association: {e}")
            return False
    
    def _evaluate_condition(self, condition: Dict[str, Any], incident_data: Dict[str, Any]) -> bool:
        """Evaluate condition"""
        try:
            field = condition.get('incident_field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not field or not operator:
                return False
            
            incident_value = incident_data.get(field)
            
            # Evaluate basic condition
            result = False
            if operator == 'EQUALS':
                result = incident_value == value
            elif operator == 'IN':
                result = incident_value in value if isinstance(value, list) else False
            elif operator == 'NOT_EQUALS':
                result = incident_value != value
            elif operator == 'CONTAINS':
                result = value in str(incident_value) if incident_value else False
            
            # Handle AND conditions
            if result and 'AND' in condition:
                and_conditions = condition['AND']
                for and_condition in and_conditions:
                    if not self._evaluate_condition(and_condition, incident_data):
                        result = False
                        break
            
            # Handle OR conditions
            if not result and 'OR' in condition:
                or_conditions = condition['OR']
                for or_condition in or_conditions:
                    if self._evaluate_condition(or_condition, incident_data):
                        result = True
                        break
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _generate_tasks_from_policy(self, policy: Dict[str, Any], incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate tasks from policy"""
        try:
            tasks = []
            rules_json = policy['rules_json']
            rule_sets = rules_json.get('rule_sets', [])
            
            for rule_set in rule_sets:
                trigger_condition = rule_set.get('trigger_condition', {})
                
                # Generate tasks only if conditions match
                if self._evaluate_condition(trigger_condition, incident_data):
                    tasks_to_generate = rule_set.get('tasks_to_generate', [])
                    
                    for task_template in tasks_to_generate:
                        task = self._create_task_from_template(
                            task_template, 
                            policy, 
                            incident_data
                        )
                        if task:
                            tasks.append(task)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error generating tasks from policy: {e}")
            return []
    
    def _create_task_from_template(self, task_template: Dict[str, Any], policy: Dict[str, Any], incident_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create actual task from task template"""
        try:
            # Calculate due date
            due_offset = task_template.get('due_offset', 0)
            due_unit = task_template.get('due_unit', 'hours')
            
            incident_date = datetime.fromisoformat(incident_data['incident_date'].replace('Z', '+00:00'))
            
            if due_unit == 'minutes':
                due_date = incident_date + timedelta(minutes=due_offset)
            elif due_unit == 'hours':
                due_date = incident_date + timedelta(hours=due_offset)
            elif due_unit == 'days':
                due_date = incident_date + timedelta(days=due_offset)
            else:
                due_date = incident_date + timedelta(hours=due_offset)
            
            # Determine priority
            priority = 'normal'
            if due_offset <= 15 and due_unit == 'minutes':
                priority = 'urgent'
            elif due_offset <= 60 and due_unit == 'minutes':
                priority = 'high'
            elif due_offset <= 2 and due_unit == 'hours':
                priority = 'high'
            
            task = {
                'task_id': f"TASK-{uuid.uuid4().hex[:8].upper()}",
                'incident_id': incident_data['id'],
                'policy_id': policy['id'],
                'task_name': task_template.get('task_name', ''),
                'description': task_template.get('description', ''),
                'assigned_role': task_template.get('assigned_role', ''),
                'due_date': due_date.isoformat(),
                'priority': priority,
                'status': 'pending',
                'documentation_required': task_template.get('documentation_required', True),
                'note_type': task_template.get('note_type', ''),
                'created_at': datetime.now().isoformat()
            }
            
            return task
            
        except Exception as e:
            logger.error(f"Error creating task from template: {e}")
            return None
    
    def _apply_fall_policy_with_timeline(self, incident_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Special handling for Fall Incident - Post Fall Timeline tracking
        
        Args:
            incident_data: Fall incident information
            
        Returns:
            List of generated tasks
        """
        try:
            # Fall incident occurrence time
            fall_date_str = incident_data.get('incident_date')
            if not fall_date_str:
                logger.error("No incident_date in fall incident data")
                return []
            
            # Handle timezone-aware datetime
            if isinstance(fall_date_str, str):
                if 'Z' in fall_date_str:
                    fall_date = datetime.fromisoformat(fall_date_str.replace('Z', '+00:00'))
                elif '+' in fall_date_str or fall_date_str.endswith('+00:00'):
                    fall_date = datetime.fromisoformat(fall_date_str)
                else:
                    fall_date = datetime.fromisoformat(fall_date_str)
            else:
                fall_date = fall_date_str
            
            # Convert to timezone-naive (for comparison)
            if fall_date.tzinfo is not None:
                fall_date = fall_date.replace(tzinfo=None)
            
            # Query and analyze Post Fall Progress Notes
            post_fall_timeline = self._get_post_fall_timeline(
                incident_data.get('resident_id'),
                incident_data.get('manad_incident_id'),
                fall_date
            )
            
            # Generate Tasks based on Timeline
            tasks_to_create = self._generate_tasks_from_timeline(
                post_fall_timeline,
                incident_data,
                fall_date
            )
            
            # Save tasks to database
            saved_tasks = self._save_tasks_to_database(tasks_to_create)
            
            logger.info(f"Fall Policy applied with timeline: {len(saved_tasks)} tasks created")
            logger.info(f"Post Fall notes found: {post_fall_timeline['total_notes']}")
            
            return saved_tasks
            
        except Exception as e:
            logger.error(f"Error applying fall policy with timeline: {e}")
            return []
    
    def _get_post_fall_timeline(self, resident_id: str, manad_incident_id: str, 
                                fall_date: datetime) -> Dict:
        """
        Query Post Fall Progress Notes from MANAD Plus API and analyze timeline
        
        Args:
            resident_id: Resident ID
            manad_incident_id: MANAD Fall Incident Progress Note ID (trigger)
            fall_date: Fall occurrence time
            
        Returns:
            Timeline analysis result
        """
        try:
            # Query Progress Notes from MANAD Plus API
            from manad_plus_integrator import get_manad_integrator
            integrator = get_manad_integrator()
            
            # Query Post Fall Progress Notes (use Fall Incident ID as trigger)
            result = integrator.get_post_fall_progress_notes(manad_incident_id)
            
            # Return empty timeline if query fails
            if not result or not isinstance(result, dict):
                logger.warning(f"Failed to get Post Fall notes for incident {manad_incident_id}")
                return {
                    'total_notes': 0,
                    'post_fall_notes': [],
                    'initial_assessment': {'completed': False, 'time': None, 'note_id': None},
                    'neuro_monitoring_4h': {'completed': False, 'time': None, 'note_id': None},
                    'follow_up_24h': {'completed': False, 'time': None, 'note_id': None},
                    'final_assessment_72h': {'completed': False, 'time': None, 'note_id': None}
                }
            
            fall_trigger_date = result.get('fall_trigger_date')
            post_fall_notes = result.get('post_fall_notes', [])
            
            # Timeline analysis
            timeline = {
                'total_notes': len(post_fall_notes),
                'post_fall_notes': post_fall_notes,
                'fall_trigger_date': fall_trigger_date,
                'initial_assessment': {'completed': False, 'time': None, 'note_id': None},
                'neuro_monitoring_4h': {'completed': False, 'time': None, 'note_id': None},
                'follow_up_24h': {'completed': False, 'time': None, 'note_id': None},
                'final_assessment_72h': {'completed': False, 'time': None, 'note_id': None}
            }
            
            # Classify Post Fall notes by time period
            for note in post_fall_notes:
                note_date_str = note.get('CreatedDate', '')
                
                # Parse datetime
                if isinstance(note_date_str, str):
                    note_date_clean = note_date_str.replace('Z', '')
                    try:
                        note_date = datetime.fromisoformat(note_date_clean)
                    except:
                        continue
                else:
                    note_date = note_date_str
                
                # Calculate time difference (hours) - based on Fall Incident trigger
                time_diff = (note_date - fall_trigger_date).total_seconds() / 3600
                
                # Classify by time period (assign only first note to each slot)
                if time_diff <= 0.5 and not timeline['initial_assessment']['completed']:
                    # Initial Assessment (within 30 minutes)
                    timeline['initial_assessment']['completed'] = True
                    timeline['initial_assessment']['time'] = time_diff * 60  # minutes
                    timeline['initial_assessment']['note_id'] = note.get('Id')
                    
                elif 0.5 < time_diff <= 4 and not timeline['neuro_monitoring_4h']['completed']:
                    # Neurological Monitoring (within 4 hours)
                    timeline['neuro_monitoring_4h']['completed'] = True
                    timeline['neuro_monitoring_4h']['time'] = time_diff
                    timeline['neuro_monitoring_4h']['note_id'] = note.get('Id')
                    
                elif 4 < time_diff <= 24 and not timeline['follow_up_24h']['completed']:
                    # 24-Hour Follow-up
                    timeline['follow_up_24h']['completed'] = True
                    timeline['follow_up_24h']['time'] = time_diff
                    timeline['follow_up_24h']['note_id'] = note.get('Id')
                    
                elif 24 < time_diff <= 72 and not timeline['final_assessment_72h']['completed']:
                    # Final Assessment (72 hours)
                    timeline['final_assessment_72h']['completed'] = True
                    timeline['final_assessment_72h']['time'] = time_diff
                    timeline['final_assessment_72h']['note_id'] = note.get('Id')
            
            logger.info(f"Timeline analysis: {timeline['total_notes']} Post Fall notes, " +
                       f"Completed steps: {sum(1 for k in ['initial_assessment', 'neuro_monitoring_4h', 'follow_up_24h', 'final_assessment_72h'] if timeline[k]['completed'])}/4")
            return timeline
            
        except Exception as e:
            logger.error(f"Error getting post fall timeline: {e}")
            return {
                'total_notes': 0,
                'post_fall_notes': [],
                'initial_assessment': {'completed': False, 'time': None, 'note_id': None},
                'neuro_monitoring_4h': {'completed': False, 'time': None, 'note_id': None},
                'follow_up_24h': {'completed': False, 'time': None, 'note_id': None},
                'final_assessment_72h': {'completed': False, 'time': None, 'note_id': None}
            }
    
    def _generate_tasks_from_timeline(self, timeline: Dict, incident_data: Dict, 
                                     fall_date: datetime) -> List[Dict[str, Any]]:
        """
        Generate all Tasks based on Fall Policy, then mark completion status according to Post Fall Timeline
        
        Args:
            timeline: Post Fall timeline analysis result
            incident_data: Incident information
            fall_date: Fall occurrence time (actually uses Fall Incident trigger date)
            
        Returns:
            List of tasks to create (including completion status)
        """
        # Use Fall Incident trigger date
        trigger_date = timeline.get('fall_trigger_date', fall_date)
        
        tasks = []
        
        # 1. Initial Assessment Task (within 30 minutes) - always create
        task_initial = {
            'task_name': 'Post Fall Assessment (Initial - 30min)',
            'task_description': 'Immediate post-fall assessment and vital signs check',
            'priority': 'High',
            'due_date': trigger_date + timedelta(minutes=30),
            'assigned_role': 'Registered Nurse',
            'incident_id': incident_data.get('id'),
            'policy_id': 'FALL-001',
            'documentation_required': True,
            'note_type': 'Post Fall',
            'status': 'Completed' if timeline['initial_assessment']['completed'] else 'Open',
            'completed_at': trigger_date + timedelta(hours=timeline['initial_assessment']['time']/60) if timeline['initial_assessment']['completed'] else None,
            'completion_method': 'post_fall_note_found' if timeline['initial_assessment']['completed'] else None,
            'linked_note_id': timeline['initial_assessment']['note_id'] if timeline['initial_assessment']['completed'] else None
        }
        tasks.append(task_initial)
        
        # 2. Neurological Monitoring Task (within 4 hours) - always create
        task_neuro = {
            'task_name': '4-Hour Neurological Monitoring',
            'task_description': 'Neurological observations and monitoring',
            'priority': 'High',
            'due_date': trigger_date + timedelta(hours=4),
            'assigned_role': 'Registered Nurse',
            'incident_id': incident_data.get('id'),
            'policy_id': 'FALL-001',
            'documentation_required': True,
            'note_type': 'Post Fall',
            'status': 'Completed' if timeline['neuro_monitoring_4h']['completed'] else 'Open',
            'completed_at': trigger_date + timedelta(hours=timeline['neuro_monitoring_4h']['time']) if timeline['neuro_monitoring_4h']['completed'] else None,
            'completion_method': 'post_fall_note_found' if timeline['neuro_monitoring_4h']['completed'] else None,
            'linked_note_id': timeline['neuro_monitoring_4h']['note_id'] if timeline['neuro_monitoring_4h']['completed'] else None
        }
        tasks.append(task_neuro)
        
        # 3. 24-Hour Follow-up Task - always create
        task_24h = {
            'task_name': '24-Hour Post Fall Follow-up',
            'task_description': '24-hour post-fall condition assessment',
            'priority': 'Medium',
            'due_date': trigger_date + timedelta(hours=24),
            'assigned_role': 'Registered Nurse',
            'incident_id': incident_data.get('id'),
            'policy_id': 'FALL-001',
            'documentation_required': True,
            'note_type': 'Post Fall',
            'status': 'Completed' if timeline['follow_up_24h']['completed'] else 'Open',
            'completed_at': trigger_date + timedelta(hours=timeline['follow_up_24h']['time']) if timeline['follow_up_24h']['completed'] else None,
            'completion_method': 'post_fall_note_found' if timeline['follow_up_24h']['completed'] else None,
            'linked_note_id': timeline['follow_up_24h']['note_id'] if timeline['follow_up_24h']['completed'] else None
        }
        tasks.append(task_24h)
        
        # 4. Final Assessment Task (72 hours) - always create
        task_72h = {
            'task_name': 'Final Post Fall Assessment (72h)',
            'task_description': 'Final post-fall assessment and incident closure review',
            'priority': 'Medium',
            'due_date': trigger_date + timedelta(hours=72),
            'assigned_role': 'Clinical Manager',
            'incident_id': incident_data.get('id'),
            'policy_id': 'FALL-001',
            'documentation_required': True,
            'note_type': 'Post Fall',
            'status': 'Completed' if timeline['final_assessment_72h']['completed'] else 'Open',
            'completed_at': trigger_date + timedelta(hours=timeline['final_assessment_72h']['time']) if timeline['final_assessment_72h']['completed'] else None,
            'completion_method': 'post_fall_note_found' if timeline['final_assessment_72h']['completed'] else None,
            'linked_note_id': timeline['final_assessment_72h']['note_id'] if timeline['final_assessment_72h']['completed'] else None
        }
        tasks.append(task_72h)
        
        completed_count = sum(1 for task in tasks if task['status'] == 'Completed')
        logger.info(f"Generated {len(tasks)} Fall Policy tasks: {completed_count} already completed, {len(tasks)-completed_count} open")
        
        return tasks
    
    def _save_tasks_to_database(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Save tasks to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            saved_tasks = []
            
            for task in tasks:
                cursor.execute("""
                    INSERT INTO cims_tasks (
                        task_id, incident_id, policy_id, task_name, description,
                        assigned_role, due_date, priority, status, 
                        documentation_required, note_type, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task['task_id'],
                    task['incident_id'],
                    task['policy_id'],
                    task['task_name'],
                    task['description'],
                    task['assigned_role'],
                    task['due_date'],
                    task['priority'],
                    task['status'],
                    task['documentation_required'],
                    task['note_type'],
                    task['created_at']
                ))
                
                task['id'] = cursor.lastrowid
                saved_tasks.append(task)
            
            conn.commit()
            conn.close()
            
            return saved_tasks
            
        except Exception as e:
            logger.error(f"Error saving tasks to database: {e}")
            return []
    
    def get_user_tasks(self, user_id: int, role: str, status_filter: str = None) -> List[Dict[str, Any]]:
        """Query tasks assigned to user"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Base query (exclude Tasks from Closed Incidents)
            query = """
                SELECT t.*, i.incident_id as incident_number, i.resident_name, i.incident_type, i.severity
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE (t.assigned_user_id = ? OR t.assigned_role = ? OR t.assigned_role LIKE ?)
                AND i.status != 'Closed'
            """
            params = [user_id, role, f"%{role}%"]
            
            # Add status filter
            if status_filter:
                query += " AND t.status = ?"
                params.append(status_filter)
            
            query += " ORDER BY t.priority DESC, t.due_date ASC"
            
            cursor.execute(query, params)
            tasks = cursor.fetchall()
            
            conn.close()
            
            # Convert to dictionary
            return [dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return []
    
    def complete_task(self, task_id: int, user_id: int, completion_notes: str = None) -> bool:
        """Process task completion"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Update task completion
            cursor.execute("""
                UPDATE cims_tasks 
                SET status = 'completed', 
                    completed_by_user_id = ?, 
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (user_id, datetime.now(), datetime.now(), task_id))
            
            # Add audit log
            cursor.execute("""
                INSERT INTO cims_audit_logs (
                    log_id, user_id, action, target_entity_type, target_entity_id, details
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"LOG-{uuid.uuid4().hex[:8].upper()}",
                user_id,
                'task_completed',
                'task',
                task_id,
                json.dumps({'completion_notes': completion_notes})
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False
    
    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Query overdue tasks"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.*, i.incident_id as incident_number, i.resident_name, i.incident_type
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status IN ('pending', 'in_progress') 
                AND t.due_date < ?
                ORDER BY t.due_date ASC
            """, (datetime.now(),))
            
            tasks = cursor.fetchall()
            conn.close()
            
            return [dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Error getting overdue tasks: {e}")
            return []
    
    def get_upcoming_tasks(self, hours_ahead: int = 2) -> List[Dict[str, Any]]:
        """Query tasks approaching deadline"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            upcoming_time = datetime.now() + timedelta(hours=hours_ahead)
            
            cursor.execute("""
                SELECT t.*, i.incident_id as incident_number, i.resident_name, i.incident_type
                FROM cims_tasks t
                JOIN cims_incidents i ON t.incident_id = i.id
                WHERE t.status IN ('pending', 'in_progress') 
                AND t.due_date BETWEEN ? AND ?
                ORDER BY t.due_date ASC
            """, (datetime.now(), upcoming_time))
            
            tasks = cursor.fetchall()
            conn.close()
            
            return [dict(task) for task in tasks]
            
        except Exception as e:
            logger.error(f"Error getting upcoming tasks: {e}")
            return []
