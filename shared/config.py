"""
Shared configuration for both Core and Admin systems
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'progress_report.db')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # API configuration
    USE_DB_API_KEYS = True
    
    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    
    # Data directories
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    USERS_DIR = os.path.join(DATA_DIR, 'users')
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        # Ensure log directory exists
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.USERS_DIR, exist_ok=True)

class CoreConfig(Config):
    """Configuration for Core System (ROD + Progress Notes)"""
    SYSTEM_NAME = "Progress Report - Core System"
    PORT = 5000
    
class AdminConfig(Config):
    """Configuration for Admin System (Incident + Policy + FCM)"""
    SYSTEM_NAME = "Progress Report - Admin Management System"
    PORT = 5001
    
    # Admin system specific settings
    ADMIN_ONLY_ACCESS = True
