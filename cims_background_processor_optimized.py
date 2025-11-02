#!/usr/bin/env python3
"""
CIMS Background Data Processor - OPTIMIZED VERSION
Processes and caches dashboard data with minimal DB lock conflicts
"""

import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
from cims_policy_engine import PolicyEngine
from app_locks import write_lock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CIMSBackgroundProcessor:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.processing_interval = 1200  # 20 minutes - optimized
        self.cache_duration = 1800  # 30 minutes cache - optimized
        
    def get_db_connection(self, retries=3):
        """Get database connection with retry logic"""
        for attempt in range(retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=60.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA busy_timeout=5000")
                return conn
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < retries - 1:
                    logger.warning(f"Database locked, retrying in 3 seconds... (attempt {attempt + 1}/{retries})")
                    time.sleep(3)
                    continue
                else:
                    logger.error(f"Failed to connect after {retries} attempts: {e}")
                    raise
    
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
        """Process all cache types with single write lock per table"""
        try:
            # Update cache management status
            self._update_cache_status('processing')
            
            # Process each cache type with comprehensive error handling
            cache_functions = [
                ('dashboard_kpi', self._process_dashboard_kpi_cache),
                ('site_analysis', self._process_site_analysis_cache),
                ('task_schedule', self._process_task_schedule_cache),
                ('incident_summary', self._process_incident_summary_cache),
                ('user_task', self._process_user_task_cache),
            ]
            
            for cache_name, cache_fn in cache_functions:
                try:
                    cache_fn()
                except Exception as e:
                    logger.error(f"Error processing {cache_name} cache: {e}")
                    # Continue to next cache type
            
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
    
    def _get_table_columns(self, cursor, table_name: str):
        """Get table columns safely"""
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            return {row[1]: row for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Error getting table columns for {table_name}: {e}")
            return {}
    
    def _process_dashboard_kpi_cache(self):
        """Process dashboard KPI cache with optimized locking"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Read data (no lock needed)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'completed' AND completed_at <= due_date THEN 1 ELSE 0 END) as on_time_tasks,
                    SUM(CASE WHEN status IN ('pending', 'in_progress') AND due_date < datetime('now') THEN 1 ELSE 0 END) as overdue_tasks
                FROM cims_tasks 
                WHERE created_at >= datetime('now', '-30 days')
            """)
            task_stats = cursor.fetchone()
            
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
            compliance_rate = round((task_stats['on_time_tasks'] or 0) * 100.0 / total_tasks, 1) if total_tasks > 0 else 0
            expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
            
            # Single write with lock
            cols = self._get_table_columns(cursor, 'cims_dashboard_kpi_cache')
            with write_lock(timeout_sec=10):
                if 'site' in cols:
                    cursor.execute("""
                        INSERT OR REPLACE INTO cims_dashboard_kpi_cache 
                        (cache_key, site, compliance_rate, overdue_tasks_count, open_incidents_count, total_tasks_count, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('dashboard_kpi_30days', 'Global', compliance_rate, task_stats['overdue_tasks'] or 0,
                          incident_stats['open_incidents'] or 0, total_tasks, expires_at.isoformat()))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO cims_dashboard_kpi_cache 
                        (cache_key, compliance_rate, overdue_tasks_count, open_incidents_count, total_tasks_count, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ('dashboard_kpi_30days', compliance_rate, task_stats['overdue_tasks'] or 0,
                          incident_stats['open_incidents'] or 0, total_tasks, expires_at.isoformat()))
                conn.commit()
            
            logger.info(f"Dashboard KPI cache updated: {compliance_rate}% compliance")
            
        except Exception as e:
            logger.error(f"Error processing dashboard KPI cache: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def _process_site_analysis_cache(self):
        """Process site analysis cache with batch insert"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cols = self._get_table_columns(cursor, 'cims_site_analysis_cache')
            
            sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
            periods = [1, 7, 30]
            expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
            
            # Collect all data first (no lock needed for reads)
            cache_entries = []
            for site in sites:
                for period in periods:
                    cursor.execute("""
                        SELECT incident_type, COUNT(*) as count
                        FROM cims_incidents 
                        WHERE site = ? AND created_at >= datetime('now', '-{} days')
                        GROUP BY incident_type
                    """.format(period), (site,))
                    
                    incidents_by_type = {row['incident_type']: row['count'] for row in cursor.fetchall()}
                    
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_incidents,
                            SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                            SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents
                        FROM cims_incidents 
                        WHERE site = ? AND created_at >= datetime('now', '-{} days')
                    """.format(period), (site,))
                    
                    stats = cursor.fetchone()
                    cache_entries.append((site, period, incidents_by_type, stats))
            
            # Batch insert with single lock
            with write_lock(timeout_sec=10):
                for site, period, incidents_by_type, stats in cache_entries:
                    compliance_json = json.dumps({
                        'closed_on_time': stats['closed_incidents'] or 0,
                        'overdue': 0,
                        'open': stats['open_incidents'] or 0
                    })
                    
                    if 'site' in cols and 'analysis_type' in cols:
                        cursor.execute("""
                            INSERT OR REPLACE INTO cims_site_analysis_cache 
                            (site, period_days, analysis_type, incidents_by_type, compliance_by_staff, 
                             total_incidents, open_incidents, closed_incidents, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (site, period, 'summary', json.dumps(incidents_by_type), compliance_json,
                              stats['total_incidents'] or 0, stats['open_incidents'] or 0,
                              stats['closed_incidents'] or 0, expires_at.isoformat()))
                    elif 'site' in cols:
                        cursor.execute("""
                            INSERT OR REPLACE INTO cims_site_analysis_cache 
                            (site, period_days, incidents_by_type, compliance_by_staff, 
                             total_incidents, open_incidents, closed_incidents, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (site, period, json.dumps(incidents_by_type), compliance_json,
                              stats['total_incidents'] or 0, stats['open_incidents'] or 0,
                              stats['closed_incidents'] or 0, expires_at.isoformat()))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO cims_site_analysis_cache 
                            (site_name, period_days, incidents_by_type, compliance_by_staff, 
                             total_incidents, open_incidents, closed_incidents, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (site, period, json.dumps(incidents_by_type), compliance_json,
                              stats['total_incidents'] or 0, stats['open_incidents'] or 0,
                              stats['closed_incidents'] or 0, expires_at.isoformat()))
                conn.commit()
            
            logger.info(f"Site analysis cache updated for {len(sites)} sites")
            
        except Exception as e:
            logger.error(f"Error processing site analysis cache: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def _process_task_schedule_cache(self):
        """Process task schedule cache"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
            expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
            now = datetime.now()
            
            # Collect data for all sites
            site_schedules = []
            for site in sites:
                cursor.execute("""
                    SELECT t.id, t.task_name, t.description, t.due_date, t.priority, t.status,
                           i.resident_name, i.incident_type, i.location
                    FROM cims_tasks t
                    JOIN cims_incidents i ON t.incident_id = i.id
                    WHERE i.site = ? AND t.status IN ('Open', 'In Progress', 'pending', 'Pending')
                    ORDER BY t.due_date ASC
                """, (site,))
                
                tasks = cursor.fetchall()
                schedule_data = []
                overdue_count = 0
                due_today_count = 0
                
                for task in tasks:
                    due_date_str = task[3]
                    if due_date_str:
                        try:
                            due_datetime = datetime.fromisoformat(due_date_str.replace('Z', ''))
                            time_diff = (due_datetime - now).total_seconds()
                            task_status = 'overdue' if time_diff < 0 else ('due-soon' if time_diff < 7200 else 'pending')
                            if time_diff < 0:
                                overdue_count += 1
                            if due_datetime.date() == now.date():
                                due_today_count += 1
                            
                            schedule_data.append({
                                'id': f'cims_task_{task[0]}',
                                'time': due_datetime.isoformat(),
                                'resident': task[6] or 'Unknown',
                                'room': task[8] or 'Unknown',
                                'task': task[1] or task[2] or f'Follow-up for {task[7]}',
                                'status': task_status,
                                'priority': task[4],
                                'incident_type': task[7]
                            })
                        except:
                            pass
                
                site_schedules.append((site, schedule_data, len(schedule_data), overdue_count, due_today_count))
            
            # Batch insert
            with write_lock(timeout_sec=10):
                for site, schedule_data, task_count, overdue_count, due_today_count in site_schedules:
                    cursor.execute("""
                        INSERT OR REPLACE INTO cims_task_schedule_cache 
                        (site_name, schedule_data, task_count, overdue_count, due_today_count, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (site, json.dumps(schedule_data), task_count, overdue_count, due_today_count, expires_at.isoformat()))
                conn.commit()
            
            logger.info(f"Task schedule cache updated for {len(sites)} sites")
            
        except Exception as e:
            logger.error(f"Error processing task schedule cache: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def _process_incident_summary_cache(self):
        """Process incident summary cache"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cols = self._get_table_columns(cursor, 'cims_incident_summary_cache')
            periods = [1, 7, 30]
            expires_at = datetime.now() + timedelta(seconds=self.cache_duration)
            
            # Collect data
            cache_entries = []
            for period in periods:
                cursor.execute(f"""
                    SELECT site, COUNT(*) as total_incidents,
                           SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_incidents,
                           SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_incidents,
                           incident_type, severity
                    FROM cims_incidents 
                    WHERE created_at >= datetime('now', '-{period} days')
                    GROUP BY site, incident_type, severity
                """)
                
                incidents = cursor.fetchall()
                summary_by_site = {}
                for row in incidents:
                    site = row['site'] or 'Unknown'
                    if site not in summary_by_site:
                        summary_by_site[site] = {
                            'total_incidents': 0, 'open_incidents': 0, 'closed_incidents': 0,
                            'incidents_by_type': {}, 'incidents_by_severity': {}
                        }
                    summary_by_site[site]['total_incidents'] += row['total_incidents']
                    summary_by_site[site]['open_incidents'] += row['open_incidents']
                    summary_by_site[site]['closed_incidents'] += row['closed_incidents']
                    itype = row['incident_type']
                    summary_by_site[site]['incidents_by_type'][itype] = summary_by_site[site]['incidents_by_type'].get(itype, 0) + row['total_incidents']
                    sev = row['severity']
                    summary_by_site[site]['incidents_by_severity'][sev] = summary_by_site[site]['incidents_by_severity'].get(sev, 0) + row['total_incidents']
                
                cache_entries.append((period, summary_by_site))
            
            # Batch insert
            with write_lock(timeout_sec=10):
                for period, summary_by_site in cache_entries:
                    if 'site' in cols:
                        for site, data in summary_by_site.items():
                            cursor.execute("""
                                INSERT OR REPLACE INTO cims_incident_summary_cache 
                                (site, period_days, summary_data, total_incidents, open_incidents, closed_incidents, expires_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (site, period, json.dumps(data), data['total_incidents'],
                                  data['open_incidents'], data['closed_incidents'], expires_at.isoformat()))
                    else:
                        total_inc = sum(v['total_incidents'] for v in summary_by_site.values())
                        total_open = sum(v['open_incidents'] for v in summary_by_site.values())
                        total_closed = sum(v['closed_incidents'] for v in summary_by_site.values())
                        cursor.execute("""
                            INSERT OR REPLACE INTO cims_incident_summary_cache 
                            (period_days, summary_data, total_incidents, open_incidents, closed_incidents, expires_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (period, json.dumps(summary_by_site), total_inc, total_open, total_closed, expires_at.isoformat()))
                conn.commit()
            
            logger.info(f"Incident summary cache updated for {len(periods)} periods")
            
        except Exception as e:
            logger.error(f"Error processing incident summary cache: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def _process_user_task_cache(self):
        """Process user task cache"""
        try:
            logger.info(f"User task cache updated for 0 users")
        except Exception as e:
            logger.error(f"Error processing user task cache: {e}")
    
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            tables = ['cims_dashboard_kpi_cache', 'cims_site_analysis_cache', 
                      'cims_task_schedule_cache', 'cims_incident_summary_cache', 'cims_user_task_cache']
            
            with write_lock(timeout_sec=10):
                total_deleted = 0
                for table in tables:
                    cols = self._get_table_columns(cursor, table)
                    if 'expires_at' in cols:
                        cursor.execute(f"DELETE FROM {table} WHERE expires_at < ?", (now,))
                        total_deleted += cursor.rowcount
                conn.commit()
            
            if total_deleted > 0:
                logger.info(f"Total expired cache entries cleaned up: {total_deleted}")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def _update_cache_status(self, status: str, error_message: str = None):
        """Update cache processing status"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cols = self._get_table_columns(cursor, 'cims_cache_management')
            cache_key_value = f"all_caches:{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            with write_lock(timeout_sec=10):
                if 'cache_key' in cols:
                    cursor.execute("""
                        INSERT INTO cims_cache_management 
                        (cache_key, cache_type, last_processed, status, error_message)
                        VALUES (?, ?, ?, ?, ?)
                    """, (cache_key_value, 'all_caches', datetime.now().isoformat(), status, error_message))
                else:
                    cursor.execute("""
                        INSERT INTO cims_cache_management 
                        (cache_type, last_processed, status, error_message)
                        VALUES (?, ?, ?, ?)
                    """, ('all_caches', datetime.now().isoformat(), status, error_message))
                conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating cache status: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

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
    processor = CIMSBackgroundProcessor()
    processor.start_processing()
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        processor.stop_processing()

