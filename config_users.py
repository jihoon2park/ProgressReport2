# config_users.py
# 사용자 관리 설정 파일
# 보안상 이 파일은 .gitignore에 추가하여 버전 관리에서 제외해야 함

import hashlib
import os

def hash_password(password):
    """패스워드를 SHA-256으로 해시화"""
    return hashlib.sha256(password.encode()).hexdigest()

# 사용자 데이터베이스
# 실제 운영환경에서는 데이터베이스나 외부 인증 시스템 사용 권장
USERS_DB = {
    "admin": {
        "password_hash": hash_password("password123"),
        "display_name": "Administrator",
        "role": "admin",
        "email": "admin@hospital.com",
        "department": "IT"
    },
    "doctor1": {
        "password_hash": hash_password("password123"), 
        "display_name": "Dr. Smith",
        "role": "doctor",
        "email": "dr.smith@hospital.com",
        "department": "Internal Medicine"
    },
    "physio1": {
        "password_hash": hash_password("password123"),
        "display_name": "Physiotherapist Jones", 
        "role": "physiotherapist",
        "email": "physio.jones@hospital.com",
        "department": "Rehabilitation"
    }
}

def verify_password(password, password_hash):
    """패스워드 검증"""
    return hash_password(password) == password_hash

def get_user(username):
    """사용자 정보 조회"""
    return USERS_DB.get(username)

def authenticate_user(username, password):
    """사용자 인증"""
    user = get_user(username)
    if user and verify_password(password, user["password_hash"]):
        # 패스워드 해시는 반환하지 않음
        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return True, safe_user
    return False, None

# 환경변수에서 설정 읽기 (선택사항)
def load_from_env():
    """환경변수에서 사용자 설정 로드"""
    # 예: ADMIN_PASSWORD=newpassword123
    admin_password = os.getenv('ADMIN_PASSWORD')
    if admin_password:
        USERS_DB['admin']['password_hash'] = hash_password(admin_password)
    
    doctor_password = os.getenv('DOCTOR1_PASSWORD')
    if doctor_password:
        USERS_DB['doctor1']['password_hash'] = hash_password(doctor_password)
    
    physio_password = os.getenv('PHYSIO1_PASSWORD')
    if physio_password:
        USERS_DB['physio1']['password_hash'] = hash_password(physio_password)

# 애플리케이션 시작 시 환경변수 로드
load_from_env() 