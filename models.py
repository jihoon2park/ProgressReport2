from flask_login import UserMixin
from config_users import get_user

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

def load_user(user_id):
    """Flask-Login의 user_loader 콜백 함수"""
    user_data = get_user(user_id)
    if user_data:
        return User(user_id, user_data)
    return None 