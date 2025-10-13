#!/usr/bin/env python3
"""
CIMS Background Data Processor
Processes and caches dashboard data every 5 minutes to improve performance
"""

import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
from cims_policy_engine import PolicyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CIMSBackgroundProcessor:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.processing_interval = 600  # 10 minutes in seconds (increased to reduce DB conflicts)
        self.cache_duration = 900  # 15 minutes cache duration (increased)
        
    def get_db_connection(self, retries=3):
        """Get database connection with retry logic"""
        for attempt in range(retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    logger.warning(f"Database locked, retrying in 3 seconds... (attempt {attempt + 1}/{retries})")
                    time.sleep(3)
                    continue
                else:
                    raise e
    
    def start_processing(self):
        """Start background processing thread"""
        if self.running:
            logger.warning("Background processor is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._processing_loop, daemon=False)
        self.thread.start()
        logger.info("Background data processor started")
    
    def stop_processing(self):
        """Stop background processing"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Background data processor stopped")
    
    def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                start_time = time.time()
                self._process_all_caches()
                processing_time = (time.time() - start_time) * 1000
                
                logger.info(f"Cache processing completed in {processing_time:.2f}ms")
                
                # Wait for next processing cycle
                time.sleep(self.processing_interval)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _process_all_caches(self):
        """Process all cache types"""
        try:
            # Update cache management status
            self._update_cache_status('processing')
            
            # Process different cache types with individual error handling
            try:
                self._process_dashboard_kpi_cache()
            except Exception as e:
                logger.error(f"Error processing dashboard KPI cache: {e}")
            
            try:
                self._process_site_analysis_cache()
            except Exception as e:
                logger.error(f"Error processing site analysis cache: {e}")
            
            try:
                self._process_task_schedule_cache()
            except Exception as e:
                logger.error(f"Error processing task schedule cache: {e}")
            
            try:
                self._process_incident_summary_cache()
            except Exception as e:
                logger.error(f"Error processing incident summary cache: {e}")
            
            try:
                self._process_user_task_cache()
            except Exception as e:
                logger.error(f"Error processing user task cache: {e}")
            
            # Clean up expired cache entries
            try:
                self._cleanup_expired_cache()
            except Exception as e:
                logger.error(f"Error cleaning up expired cache: {e}")
            
            # Update cache management status
            self._update_cache_status('idle')
            
        except Exception as e:
            logger.error(f"Error in main cache processing: {e}")
            self._update_cache_status('error', str(e))
    
    def _process_dashboard_kpi_cache(self):
        """Process dashboard KPI cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Calculate compliance metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' AND completed_at <= due_date THEN 1 ELSE 0 END) as on_time_tasks,
                    SUM(CASE WHEN status IN ('pending', 'in_progress') AND due_date < datetime('now') THEN 1 ELSE 0 END) as overdue_tasks
                FROM cims_tasks 
                WHERE created_at >= datetime('now', '-30 days')
            """)
            
            task_stats = cursor.fetchone()
            
            # Calculate incident counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_incidents,
                    SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                    SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents
                FROM cims_incidents 
                WHERE created_at >= datetime('now', '-30 days')
            """)
            
            incident_stats = cursor.fetchone()
            
            # Calculate compliance rate
            total_tasks = task_stats['total_tasks'] or 0
            if total_tasks > 0:
                compliance_rate = round((task_stats['on_time_tasks'] or 0) * 100.0 / total_tasks, 1)
            else:
                compliance_rate = 0
            
            # Store in cache
            expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
            cursor.execute("""
                INSERT OR REPLACE INTO cims_dashboard_kpi_cache 
                (cache_key, compliance_rate, overdue_tasks_count, open_incidents_count, total_tasks_count, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                'dashboard_kpi_30days',
                compliance_rate,
                task_stats['overdue_tasks'] or 0,
                incident_stats['open_incidents'] or 0,
                total_tasks,
                expires_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Dashboard KPI cache updated: {compliance_rate}% compliance, {task_stats['overdue_tasks'] or 0} overdue")
            
        except Exception as e:
            logger.error(f"Error processing dashboard KPI cache: {e}")
    
    def _process_site_analysis_cache(self):
        """Process site analysis cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
            periods = [1, 7, 30]  # 1 day, 7 days, 30 days
            
            for site in sites:
                for period in periods:
                    # Get incidents by type for this site and period
                    cursor.execute("""
                        SELECT 
                            incident_type,
                            COUNT(*) as count
                        FROM cims_incidents 
                        WHERE site = ? AND created_at >= datetime('now', '-{} days')
                        GROUP BY incident_type
                    """.format(period), (site,))
                    
                    incidents_by_type = {row['incident_type']: row['count'] for row in cursor.fetchall()}
                    
                    # Get compliance by staff (simplified)
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_incidents,
                            SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                            SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents
                        FROM cims_incidents 
                        WHERE site = ? AND created_at >= datetime('now', '-{} days')
                    """.format(period), (site,))
                    
                    compliance_stats = cursor.fetchone()
                    
                    # Store in cache
                    expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
                    cursor.execute("""
                        INSERT OR REPLACE INTO cims_site_analysis_cache 
                        (site_name, period_days, incidents_by_type, compliance_by_staff, 
                         total_incidents, open_incidents, closed_incidents, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        site,
                        period,
                        json.dumps(incidents_by_type),
                        json.dumps({
                            'closed_on_time': compliance_stats['closed_incidents'] or 0,
                            'overdue': 0,  # Simplified for now
                            'open': compliance_stats['open_incidents'] or 0
                        }),
                        compliance_stats['total_incidents'] or 0,
                        compliance_stats['open_incidents'] or 0,
                        compliance_stats['closed_incidents'] or 0,
                        expires_at.isoformat()
                    ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Site analysis cache updated for {len(sites)} sites")
            
        except Exception as e:
            logger.error(f"Error processing site analysis cache: {e}")
    
    def _process_task_schedule_cache(self):
        """Process task schedule cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
            
            for site in sites:
                # Get tasks for this site
                cursor.execute("""
                    SELECT t.id, t.task_name, t.description, t.due_date, t.priority, t.status,
                           i.resident_name, i.incident_type, i.location, i.incident_date
                    FROM cims_tasks t
                    JOIN cims_incidents i ON t.incident_id = i.id
                    WHERE i.site = ? AND t.status IN ('Open', 'In Progress', 'pending', 'Pending')
                    ORDER BY t.due_date ASC
                """, (site,))
                
                tasks = cursor.fetchall()
                
                # Process schedule data
                schedule_data = []
                now = datetime.now()
                overdue_count = 0
                due_today_count = 0
                
                for task in tasks:
                    task_id, task_name, description, due_date, priority, status, resident_name, incident_type, location, incident_date = task
                    
                    # Parse due date
                    if isinstance(due_date, str):
                        try:
                            due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        except:
                            due_datetime = datetime.fromisoformat(due_date)
                    else:
                        due_datetime = due_date
                    
                    # Ensure timezone awareness
                    if due_datetime.tzinfo is None:
                        due_datetime = due_datetime.replace(tzinfo=None)
                    
                    # Determine status and urgency
                    time_diff = (due_datetime - now).total_seconds()
                    if time_diff < 0:
                        task_status = 'overdue'
                        overdue_count += 1
                    elif time_diff < 2 * 3600:  # Less than 2 hours
                        task_status = 'due-soon'
                    else:
                        task_status = 'pending'
                    
                    # Check if due today
                    if due_datetime.date() == now.date():
                        due_today_count += 1
                    
                    schedule_data.append({
                        'id': f'cims_task_{task_id}',
                        'time': due_datetime.isoformat(),
                        'resident': resident_name or 'Unknown Resident',
                        'room': location or 'Unknown',
                        'task': task_name or description or f'Follow-up for {incident_type}',
                        'status': task_status,
                        'priority': priority,
                        'incident_type': incident_type
                    })
                
                # Store in cache
                expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
                cursor.execute("""
                    INSERT OR REPLACE INTO cims_task_schedule_cache 
                    (site_name, schedule_data, task_count, overdue_count, due_today_count, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    site,
                    json.dumps(schedule_data),
                    len(schedule_data),
                    overdue_count,
                    due_today_count,
                    expires_at.isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Task schedule cache updated for {len(sites)} sites")
            
        except Exception as e:
            logger.error(f"Error processing task schedule cache: {e}")
    
    def _process_incident_summary_cache(self):
        """Process incident summary cache"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            periods = [1, 7, 30]  # 1 day, 7 days, 30 days
            
            for period in periods:
                # Get incident summary for this period
                cursor.execute("""
                    SELECT 
                        site,
                        COUNT(*) as total_incidents,
                        SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                        SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents,
                        incident_type,
                        severity
                    FROM cims_incidents 
                    WHERE created_at >= datetime('now', '-{} days')
                    GROUP BY site, incident_type, severity
                """.format(period))
                
                incidents = cursor.fetchall()
                
                # Process summary data
                summary_data = {}
                total_incidents = 0
                total_open = 0
                total_closed = 0
                
                for incident in incidents:
                    site = incident['site']
                    if site not in summary_data:
                        summary_data[site] = {
                            'total_incidents': 0,
                            'open_incidents': 0,
                            'closed_incidents': 0,
                            'incidents_by_type': {},
                            'incidents_by_severity': {}
                        }
                    
                    summary_data[site]['total_incidents'] += incident['total_incidents']
                    summary_data[site]['open_incidents'] += incident['open_incidents']
                    summary_data[site]['closed_incidents'] += incident['closed_incidents']
                    
                    # Group by type
                    incident_type = incident['incident_type']
                    if incident_type not in summary_data[site]['incidents_by_type']:
                        summary_data[site]['incidents_by_type'][incident_type] = 0
                    summary_data[site]['incidents_by_type'][incident_type] += incident['total_incidents']
                    
                    # Group by severity
                    severity = incident['severity']
                    if severity not in summary_data[site]['incidents_by_severity']:
                        summary_data[site]['incidents_by_severity'][severity] = 0
                    summary_data[site]['incidents_by_severity'][severity] += incident['total_incidents']
                    
                    total_incidents += incident['total_incidents']
                    total_open += incident['open_incidents']
                    total_closed += incident['closed_incidents']
                
                # Store in cache
                expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
                cursor.execute("""
                    INSERT OR REPLACE INTO cims_incident_summary_cache 
                    (period_days, summary_data, total_incidents, open_incidents, closed_incidents, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    period,
                    json.dumps(summary_data),
                    total_incidents,
                    total_open,
                    total_closed,
                    expires_at.isoformat()
                ))
            
            conn.commit()
            
            logger.info(f"Incident summary cache updated for {len(periods)} periods")
            
        except Exception as e:
            logger.error(f"Error processing incident summary cache: {e}")
        finally:
            if conn:
                conn.close()
    
    def _process_user_task_cache(self):
        """Process user task cache"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get all users with tasks
            cursor.execute("""
                SELECT DISTINCT assigned_user_id, assigned_role
                FROM cims_tasks 
                WHERE assigned_user_id IS NOT NULL
            """)
            
            users = cursor.fetchall()
            
            for user in users:
                user_id = user['assigned_user_id']
                user_role = user['assigned_role']
                
                # Get tasks for this user
                cursor.execute("""
                    SELECT t.id, t.task_name, t.description, t.due_date, t.priority, t.status,
                           i.resident_name, i.incident_type, i.location
                    FROM cims_tasks t
                    JOIN cims_incidents i ON t.incident_id = i.id
                    WHERE t.assigned_user_id = ?
                    ORDER BY t.due_date ASC
                """, (user_id,))
                
                tasks = cursor.fetchall()
                
                # Process task data
                task_data = []
                overdue_count = 0
                due_today_count = 0
                now = datetime.now()
                
                for task in tasks:
                    task_id, task_name, description, due_date, priority, status, resident_name, incident_type, location = task
                    
                    # Parse due date
                    if isinstance(due_date, str):
                        due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    else:
                        due_datetime = due_date
                    
                    # Determine urgency
                    time_diff = (due_datetime - now).total_seconds()
                    if time_diff < 0:
                        urgency = 'Overdue'
                        overdue_count += 1
                    elif time_diff < 4 * 3600:  # Less than 4 hours
                        urgency = 'High'
                    elif time_diff < 24 * 3600:  # Less than 24 hours
                        urgency = 'Medium'
                    else:
                        urgency = 'Low'
                    
                    # Check if due today
                    if due_datetime.date() == now.date():
                        due_today_count += 1
                    
                    task_data.append({
                        'task_id': task_id,
                        'incident_id': f'INC-{task_id}',
                        'resident_name': resident_name or 'Unknown',
                        'description': task_name or description or f'Follow-up for {incident_type}',
                        'assigned_role': user_role,
                        'due_date': due_date,
                        'urgency': urgency,
                        'status': 'active' if status in ['Open', 'In Progress', 'pending', 'Pending'] else 'completed',
                        'note_type': f'{incident_type} Follow-up',
                        'priority': priority or 'normal'
                    })
                
                # Store in cache
                expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
                cursor.execute("""
                    INSERT OR REPLACE INTO cims_user_task_cache 
                    (user_id, user_role, task_data, total_tasks, overdue_tasks, due_today_tasks, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    user_role,
                    json.dumps(task_data),
                    len(task_data),
                    overdue_count,
                    due_today_count,
                    expires_at.isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"User task cache updated for {len(users)} users")
            
        except Exception as e:
            logger.error(f"Error processing user task cache: {e}")
    
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Clean up expired entries
            tables = [
                'cims_dashboard_kpi_cache',
                'cims_site_analysis_cache', 
                'cims_task_schedule_cache',
                'cims_incident_summary_cache',
                'cims_user_task_cache'
            ]
            
            total_deleted = 0
            for table in tables:
                cursor.execute(f"DELETE FROM {table} WHERE expires_at < ?", (now,))
                deleted = cursor.rowcount
                total_deleted += deleted
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} expired entries from {table}")
            
            conn.commit()
            
            if total_deleted > 0:
                logger.info(f"Total expired cache entries cleaned up: {total_deleted}")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
        finally:
            if conn:
                conn.close()
    
    def _update_cache_status(self, status: str, error_message: str = None):
        """Update cache processing status"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cims_cache_management 
                (cache_type, last_processed, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (
                'all_caches',
                datetime.now().isoformat(),
                status,
                error_message
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
        finally:
            if conn:
                conn.close()

# Global processor instance
_processor = None

def get_processor() -> CIMSBackgroundProcessor:
    """Get global processor instance"""
    global _processor
    if _processor is None:
        _processor = CIMSBackgroundProcessor()
    return _processor

def start_background_processing():
    """Start background processing"""
    processor = get_processor()
    processor.start_processing()

def stop_background_processing():
    """Stop background processing"""
    processor = get_processor()
    processor.stop_processing()

if __name__ == '__main__':
    # Test the processor
    processor = CIMSBackgroundProcessor()
    processor.start_processing()
    
    try:
        # Run for 1 minute to test
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        processor.stop_processing()
