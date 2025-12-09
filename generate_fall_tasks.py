#!/usr/bin/env python3
"""
Generate tasks for existing Fall incidents
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_fall_tasks():
    """Generate tasks for Fall incidents using the active policy"""
    try:
        conn = sqlite3.connect('progress_report.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get active Fall policy
        cursor.execute("""
            SELECT * FROM cims_policies 
            WHERE is_active = 1 
            AND (name LIKE '%Fall%' OR policy_id LIKE '%FALL%')
            LIMIT 1
        """)
        policy = cursor.fetchone()
        
        if not policy:
            logger.error("No active Fall policy found!")
            return False
        
        logger.info(f"Using policy: {policy['name']} (v{policy['version']})")
        
        # Parse policy rules
        rules = json.loads(policy['rules_json'])
        schedule = rules.get('nurse_visit_schedule', [])
        
        logger.info(f"Policy has {len(schedule)} visit phases")
        
        # Get Fall incidents without tasks
        cursor.execute("""
            SELECT i.* FROM cims_incidents i
            WHERE i.incident_type LIKE '%Fall%'
            AND NOT EXISTS (
                SELECT 1 FROM cims_tasks t WHERE t.incident_id = i.id
            )
            ORDER BY i.incident_date DESC
        """)
        
        incidents = cursor.fetchall()
        logger.info(f"Found {len(incidents)} Fall incidents without tasks")
        
        if len(incidents) == 0:
            logger.info("All Fall incidents already have tasks")
            return True
        
        total_tasks_created = 0
        
        for incident in incidents:
            logger.info(f"\nProcessing incident: {incident['incident_id']} - {incident['resident_name']}")
            
            incident_time = datetime.fromisoformat(incident['incident_date'].replace('Z', '+00:00'))
            task_number = 0
            
            # Generate tasks based on policy schedule
            for phase_idx, phase in enumerate(schedule, 1):
                interval = phase['interval']
                interval_unit = phase['interval_unit']
                duration = phase['duration']
                duration_unit = phase['duration_unit']
                
                # Convert to minutes
                interval_minutes = interval if interval_unit == 'minutes' else interval * 60
                duration_minutes = duration if duration_unit == 'minutes' else duration * 60
                
                # Calculate number of visits in this phase
                num_visits = int(duration_minutes / interval_minutes)
                
                logger.info(f"  Phase {phase_idx}: Every {interval} {interval_unit} for {duration} {duration_unit} = {num_visits} visits")
                
                # Generate tasks for this phase
                current_time = incident_time
                if task_number > 0:
                    # Start from the end of the previous phase
                    prev_phase_duration = sum([
                        (s['duration'] if s['duration_unit'] == 'minutes' else s['duration'] * 60)
                        for s in schedule[:phase_idx-1]
                    ])
                    current_time = incident_time + timedelta(minutes=prev_phase_duration)
                
                for visit_num in range(num_visits):
                    task_number += 1
                    due_time = current_time + timedelta(minutes=interval_minutes * visit_num)
                    
                    task_id = f"TASK-{incident['incident_id']}-P{phase_idx}-V{visit_num + 1}"
                    task_name = f"Nurse Visit #{task_number} - Post-Fall Assessment"
                    
                    # Determine status based on due time
                    now = datetime.now()
                    if due_time < now:
                        status = 'overdue'
                    else:
                        status = 'pending'
                    
                    # Insert task
                    cursor.execute("""
                        INSERT INTO cims_tasks (
                            task_id, incident_id, policy_id, task_name, description,
                            assigned_role, due_date, priority, status,
                            documentation_required, note_type, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task_id,
                        incident['id'],
                        policy['id'],
                        task_name,
                        f"Phase {phase_idx}, Visit {visit_num + 1}: {rules.get('common_assessment_tasks', 'Monitor resident condition')}",
                        'Registered Nurse',
                        due_time.isoformat(),
                        'high' if phase_idx == 1 else 'normal',
                        status,
                        True,
                        'Dynamic Form - Post Fall Assessment',
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    
                    total_tasks_created += 1
            
            logger.info(f"  ✅ Created {task_number} tasks for incident {incident['incident_id']}")
            
            # Update incident with policy applied
            cursor.execute("""
                UPDATE cims_incidents 
                SET policy_applied = ?, updated_at = ?
                WHERE id = ?
            """, (policy['id'], datetime.now().isoformat(), incident['id']))
        
        conn.commit()
        conn.close()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ Successfully created {total_tasks_created} tasks for {len(incidents)} incidents")
        logger.info("=" * 60)
        
        return True
            
    except Exception as e:
        logger.error(f"Error generating tasks: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FALL INCIDENT TASK GENERATOR")
    print("=" * 60)
    
    if generate_fall_tasks():
        print("\n✅ SUCCESS: Tasks generated for Fall incidents!")
        print("\nRefresh the dashboard to see the data.")
    else:
        print("\n❌ ERROR: Failed to generate tasks")

