#!/usr/bin/env python3
"""
CIMS Cache API Endpoints
Provides cached data for improved performance
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Blueprint for cache API
cache_api = Blueprint('cache_api', __name__, url_prefix='/api/cache')

def get_db_connection():
    """Get database connection with WAL mode for better concurrency"""
    conn = sqlite3.connect('progress_report.db', timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def require_role(*allowed_roles):
    """Role-based access control decorator"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = current_user.role
            if user_role not in allowed_roles:
                return jsonify({'error': 'Access denied'}), 403
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__  # Preserve original function name
        return decorated_function
    return decorator

@cache_api.route('/dashboard/kpi', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_cached_dashboard_kpi():
    """Get cached dashboard KPI data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest cached KPI data
        cursor.execute("""
            SELECT compliance_rate, overdue_tasks_count, open_incidents_count, total_tasks_count, created_at
            FROM cims_dashboard_kpi_cache 
            WHERE expires_at > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        kpi_data = cursor.fetchone()
        conn.close()
        
        if kpi_data:
            return jsonify({
                'incident_counts': {
                    'total_incidents': 0,  # Not cached separately
                    'open_incidents': kpi_data['open_incidents_count'],
                    'closed_incidents': 0  # Not cached separately
                },
                'compliance_metrics': {
                    'overall_compliance_rate': kpi_data['compliance_rate'],
                    'overdue_tasks_count': kpi_data['overdue_tasks_count'],
                    'total_tasks': kpi_data['total_tasks_count'],
                    'overdue_staff': [],  # Not cached
                    'avg_completion_time_min': 15.4  # Static value
                },
                'cached_at': kpi_data['created_at'],
                'from_cache': True
            }), 200
        else:
            # No cached data available, return empty data
            return jsonify({
                'incident_counts': {
                    'total_incidents': 0,
                    'open_incidents': 0,
                    'closed_incidents': 0
                },
                'compliance_metrics': {
                    'overall_compliance_rate': 0,
                    'overdue_tasks_count': 0,
                    'total_tasks': 0,
                    'overdue_staff': [],
                    'avg_completion_time_min': 0
                },
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached dashboard KPI: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/site-analysis/<site_name>', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager', 'site_admin')
def get_cached_site_analysis(site_name):
    """Get cached site analysis data"""
    try:
        period = request.args.get('period', 1, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cached site analysis data
        cursor.execute("""
            SELECT incidents_by_type, compliance_by_staff, total_incidents, open_incidents, closed_incidents, created_at
            FROM cims_site_analysis_cache 
            WHERE site_name = ? AND period_days = ? AND expires_at > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        """, (site_name, period))
        
        analysis_data = cursor.fetchone()
        conn.close()
        
        if analysis_data:
            return jsonify({
                'incidents_by_type': json.loads(analysis_data['incidents_by_type']),
                'compliance_by_staff': json.loads(analysis_data['compliance_by_staff']),
                'total_incidents': analysis_data['total_incidents'],
                'open_incidents': analysis_data['open_incidents'],
                'closed_incidents': analysis_data['closed_incidents'],
                'cached_at': analysis_data['created_at'],
                'from_cache': True
            }), 200
        else:
            # No cached data available
            return jsonify({
                'incidents_by_type': {},
                'compliance_by_staff': {'closed_on_time': 0, 'overdue': 0, 'open': 0},
                'total_incidents': 0,
                'open_incidents': 0,
                'closed_incidents': 0,
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached site analysis: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/task-schedule/<site_name>', methods=['GET'])
@login_required
def get_cached_task_schedule(site_name):
    """Get cached task schedule for a site"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cached task schedule data
        cursor.execute("""
            SELECT schedule_data, task_count, overdue_count, due_today_count, created_at
            FROM cims_task_schedule_cache 
            WHERE site_name = ? AND expires_at > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        """, (site_name,))
        
        schedule_data = cursor.fetchone()
        conn.close()
        
        if schedule_data:
            return jsonify({
                'schedule': json.loads(schedule_data['schedule_data']),
                'task_count': schedule_data['task_count'],
                'overdue_count': schedule_data['overdue_count'],
                'due_today_count': schedule_data['due_today_count'],
                'cached_at': schedule_data['created_at'],
                'from_cache': True
            }), 200
        else:
            # No cached data available
            return jsonify({
                'schedule': [],
                'task_count': 0,
                'overdue_count': 0,
                'due_today_count': 0,
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached task schedule: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/user-tasks/<int:user_id>', methods=['GET'])
@login_required
def get_cached_user_tasks(user_id):
    """Get cached user tasks"""
    try:
        # Check if user is requesting their own tasks or is admin
        if current_user.id != user_id and not current_user.is_admin():
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cached user task data
        cursor.execute("""
            SELECT task_data, total_tasks, overdue_tasks, due_today_tasks, created_at
            FROM cims_user_task_cache 
            WHERE user_id = ? AND expires_at > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id,))
        
        task_data = cursor.fetchone()
        conn.close()
        
        if task_data:
            return jsonify({
                'tasks': json.loads(task_data['task_data']),
                'total_tasks': task_data['total_tasks'],
                'overdue_tasks': task_data['overdue_tasks'],
                'due_today_tasks': task_data['due_today_tasks'],
                'cached_at': task_data['created_at'],
                'from_cache': True
            }), 200
        else:
            # No cached data available
            return jsonify({
                'tasks': [],
                'total_tasks': 0,
                'overdue_tasks': 0,
                'due_today_tasks': 0,
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached user tasks: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/incident-summary', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager', 'site_admin')
def get_cached_incident_summary():
    """Get cached incident summary"""
    try:
        period = request.args.get('period', 1, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cached incident summary data
        cursor.execute("""
            SELECT summary_data, total_incidents, open_incidents, closed_incidents, created_at
            FROM cims_incident_summary_cache 
            WHERE period_days = ? AND expires_at > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        """, (period,))
        
        summary_data = cursor.fetchone()
        conn.close()
        
        if summary_data:
            return jsonify({
                'summary': json.loads(summary_data['summary_data']),
                'total_incidents': summary_data['total_incidents'],
                'open_incidents': summary_data['open_incidents'],
                'closed_incidents': summary_data['closed_incidents'],
                'cached_at': summary_data['created_at'],
                'from_cache': True
            }), 200
        else:
            # No cached data available
            return jsonify({
                'summary': {},
                'total_incidents': 0,
                'open_incidents': 0,
                'closed_incidents': 0,
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached incident summary: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/external-sites', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager', 'site_admin')
def get_cached_external_sites():
    """Get cached external site data"""
    try:
        period = request.args.get('period', 1, type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get cached external site data
        cursor.execute("""
            SELECT site_name, incidents_data, clients_data, total_incidents, total_clients, created_at
            FROM cims_external_sites_cache 
            WHERE period_days = ? AND expires_at > datetime('now')
            ORDER BY created_at DESC
        """, (period,))
        
        site_data = cursor.fetchall()
        conn.close()
        
        if site_data:
            result = {}
            for site in site_data:
                result[site['site_name']] = {
                    'incidents': json.loads(site['incidents_data']) if site['incidents_data'] else [],
                    'clients': json.loads(site['clients_data']) if site['clients_data'] else [],
                    'total_incidents': site['total_incidents'],
                    'total_clients': site['total_clients'],
                    'cached_at': site['created_at']
                }
            
            return jsonify({
                'sites': result,
                'from_cache': True
            }), 200
        else:
            # No cached data available
            return jsonify({
                'sites': {},
                'from_cache': False
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting cached external sites: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@cache_api.route('/status', methods=['GET'])
@login_required
@require_role('admin', 'clinical_manager')
def get_cache_status():
    """Get cache processing status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest cache management status
        cursor.execute("""
            SELECT cache_type, last_processed, processing_duration_ms, records_processed, status, error_message
            FROM cims_cache_management 
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        status_data = cursor.fetchall()
        
        # Get cache statistics
        cursor.execute("""
            SELECT 
                'dashboard_kpi' as cache_type, COUNT(*) as count, MAX(created_at) as last_updated
            FROM cims_dashboard_kpi_cache WHERE expires_at > datetime('now')
            UNION ALL
            SELECT 
                'site_analysis' as cache_type, COUNT(*) as count, MAX(created_at) as last_updated
            FROM cims_site_analysis_cache WHERE expires_at > datetime('now')
            UNION ALL
            SELECT 
                'task_schedule' as cache_type, COUNT(*) as count, MAX(created_at) as last_updated
            FROM cims_task_schedule_cache WHERE expires_at > datetime('now')
            UNION ALL
            SELECT 
                'incident_summary' as cache_type, COUNT(*) as count, MAX(created_at) as last_updated
            FROM cims_incident_summary_cache WHERE expires_at > datetime('now')
            UNION ALL
            SELECT 
                'user_tasks' as cache_type, COUNT(*) as count, MAX(created_at) as last_updated
            FROM cims_user_task_cache WHERE expires_at > datetime('now')
        """)
        
        cache_stats = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'processing_history': [
                {
                    'cache_type': row['cache_type'],
                    'last_processed': row['last_processed'],
                    'processing_duration_ms': row['processing_duration_ms'],
                    'records_processed': row['records_processed'],
                    'status': row['status'],
                    'error_message': row['error_message']
                }
                for row in status_data
            ],
            'cache_statistics': [
                {
                    'cache_type': row['cache_type'],
                    'active_entries': row['count'],
                    'last_updated': row['last_updated']
                }
                for row in cache_stats
            ]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        return jsonify({'error': 'Internal server error'}), 500
