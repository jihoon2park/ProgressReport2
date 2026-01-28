from flask_login import UserMixin
from config_users import get_user
from datetime import datetime

class User(UserMixin):
    """User class for Flask-Login"""
    
    def __init__(self, username, user_data):
        self.id = username
        self.username = username
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.role = user_data.get('role', '')
        self.position = user_data.get('position', '')
        # Add display_name attribute (combination of first_name and last_name)
        self.display_name = f"{self.first_name} {self.last_name}".strip() if (self.first_name or self.last_name) else username
        
    def get_id(self):
        """Return user ID required by Flask-Login"""
        return self.username
        
    @property
    def is_authenticated(self):
        """Check if user is authenticated"""
        return True
        
    def is_active(self):
        """Check if user is active"""
        return True
        
    def is_anonymous(self):
        """Check if user is anonymous"""
        return False
        
    def get_full_name(self):
        """Return full name"""
        return self.display_name
        
    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role
        
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
        
    def is_doctor(self):
        """Check if user is doctor"""
        return self.role == 'doctor'
        
    def is_physiotherapist(self):
        """Check if user is physiotherapist"""
        return self.role == 'physiotherapist'
        
    def is_site_admin(self):
        """Check if user is site admin"""
        return self.role == 'site_admin'

class FCMToken:
    """FCM Token Management Model"""
    
    def __init__(self, user_id: str, token: str, device_info: str = None, created_at: datetime = None):
        self.user_id = user_id
        self.token = token
        self.device_info = device_info or "Unknown Device"
        self.created_at = created_at or datetime.now()
        self.last_used = datetime.now()
        self.is_active = True
    
    def to_dict(self):
        """Convert to dictionary format"""
        return {
            'user_id': self.user_id,
            'token': self.token,
            'device_info': self.device_info,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create object from dictionary"""
        created_at = None
        last_used = None
        
        if data.get('created_at'):
            try:
                created_at = datetime.fromisoformat(data['created_at'])
            except:
                created_at = datetime.now()
        
        if data.get('last_used'):
            try:
                last_used = datetime.fromisoformat(data['last_used'])
            except:
                last_used = datetime.now()
        
        return cls(
            user_id=data['user_id'],
            token=data['token'],
            device_info=data.get('device_info', 'Unknown Device'),
            created_at=created_at
        )

def load_user(user_id):
    """Flask-Login user_loader callback function"""
    user_data = get_user(user_id)
    if user_data:
        return User(user_id, user_data)
    return None 