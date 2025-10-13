from flask_login import UserMixin
from config_users import get_user
from datetime import datetime

class User(UserMixin):
    """Flask-Login을 위한 User 클래스"""
    
    def __init__(self, username, user_data):
        self.id = username
        self.username = username
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.role = user_data.get('role', '')
        self.position = user_data.get('position', '')
        # display_name 속성 추가 (first_name과 last_name 조합)
        self.display_name = f"{self.first_name} {self.last_name}".strip() if (self.first_name or self.last_name) else username
        
    def get_id(self):
        """Flask-Login에서 요구하는 사용자 ID 반환"""
        return self.username
        
    @property
    def is_authenticated(self):
        """인증된 사용자인지 확인"""
        return True
        
    def is_active(self):
        """활성 사용자인지 확인"""
        return True
        
    def is_anonymous(self):
        """익명 사용자인지 확인"""
        return False
        
    def get_full_name(self):
        """전체 이름 반환"""
        return self.display_name
        
    def has_role(self, role):
        """특정 역할을 가지고 있는지 확인"""
        return self.role == role
        
    def is_admin(self):
        """관리자인지 확인"""
        return self.role == 'admin'
        
    def is_doctor(self):
        """의사인지 확인"""
        return self.role == 'doctor'
        
    def is_physiotherapist(self):
        """물리치료사인지 확인"""
        return self.role == 'physiotherapist'
        
    def is_site_admin(self):
        """사이트 관리자인지 확인"""
        return self.role == 'site_admin'

class FCMToken:
    """FCM 토큰 관리 모델"""
    
    def __init__(self, user_id: str, token: str, device_info: str = None, created_at: datetime = None):
        self.user_id = user_id
        self.token = token
        self.device_info = device_info or "Unknown Device"
        self.created_at = created_at or datetime.now()
        self.last_used = datetime.now()
        self.is_active = True
    
    def to_dict(self):
        """딕셔너리 형태로 변환"""
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
        """딕셔너리에서 객체 생성"""
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
    """Flask-Login의 user_loader 콜백 함수"""
    user_data = get_user(user_id)
    if user_data:
        return User(user_id, user_data)
    return None 