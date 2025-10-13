"""
Progress Report - Admin Management System
Handles: Incident Viewer, Policy Management, FCM Dashboard
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_required, current_user, login_user, logout_user

# Add parent directory to path to import shared modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Change working directory to parent directory for proper file paths
os.chdir(parent_dir)

from shared.config import AdminConfig
from shared.auth import auth_manager, User
from shared.usage_logger import usage_logger

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(AdminConfig)
AdminConfig.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access the Admin Management System.'

# Setup logging
logging.basicConfig(
    level=getattr(logging, app.config['LOG_LEVEL']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return auth_manager.get_user_by_id(user_id)

# ==============================
# Authentication Routes
# ==============================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for Admin System"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = auth_manager.authenticate_user(username, password)
        if user and user.can_access_admin_system():
            login_user(user, remember=True)
            
            # Log successful login
            user_info = {
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "position": user.position
            }
            usage_logger.log_access(user_info)
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or insufficient permissions for Admin System.', 'error')
    
    return render_template('login.html', system_name=app.config['SYSTEM_NAME'])

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ==============================
# Main Routes
# ==============================

@app.route('/')
@login_required
def dashboard():
    """Admin Dashboard - Main landing page"""
    if not current_user.can_access_admin_system():
        flash('Access denied. Admin system access required.', 'error')
        return redirect(url_for('login'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('dashboard.html', current_user=current_user)

@app.route('/incident-viewer')
@login_required
def incident_viewer():
    """Incident Viewer page"""
    if not current_user.can_access_admin_system():
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('login'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    # Get site parameter
    site = request.args.get('site', 'Parafield Gardens')
    
    return render_template('incident_viewer.html', 
                         site=site, 
                         current_user=current_user)

@app.route('/policy-management')
@login_required
def policy_management():
    """Policy Management page"""
    if not current_user.can_access_admin_system():
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('login'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('policy_management.html', current_user=current_user)

@app.route('/fcm-dashboard')
@login_required
def fcm_dashboard():
    """FCM Admin Dashboard page"""
    if not current_user.can_access_admin_system():
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('login'))
    
    # Log access
    user_info = {
        "username": current_user.username,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "position": current_user.position
    }
    usage_logger.log_access(user_info)
    
    return render_template('fcm_dashboard.html', current_user=current_user)

# ==============================
# API Routes (to be migrated from main app.py)
# ==============================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'system': 'Admin Management System',
        'timestamp': datetime.now().isoformat()
    })

# ==============================
# Error Handlers
# ==============================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('error.html', 
                         error_code=403, 
                         error_message="Access forbidden"), 403

# ==============================
# Application Entry Point
# ==============================

if __name__ == '__main__':
    logger.info(f"Starting {app.config['SYSTEM_NAME']}")
    logger.info(f"Database path: {app.config['DATABASE_PATH']}")
    logger.info(f"Port: {app.config['PORT']}")
    
    app.run(
        host='0.0.0.0',
        port=app.config['PORT'],
        debug=True
    )
