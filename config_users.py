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
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "position": "System Administrator",
        "email": "admin@hospital.com",
        "department": "IT"
    },
    "doctor1": {
        "password_hash": hash_password("password123"), 
        "display_name": "Dr. Smith",
        "first_name": "John",
        "last_name": "Smith",
        "role": "doctor",
        "position": "Doctor",
        "email": "dr.smith@hospital.com",
        "department": "Internal Medicine"
    },
    "physio1": {
        "password_hash": hash_password("password123"),
        "display_name": "Physiotherapist Jones", 
        "first_name": "Sarah",
        "last_name": "Jones",
        "role": "physiotherapist",
        "position": "Physiotherapist",
        "email": "physio.jones@hospital.com",
        "department": "Rehabilitation"
    },
    "PaulVaska": {
        "password_hash": hash_password("password123"),
        "display_name": "Dr. Paul Vaska",
        "first_name": "Paul",
        "last_name": "Vaska",
        "role": "doctor",
        "position": "GP",
        "email": "paul.vaska@hospital.com",
        "department": "Internal Medicine"
    },
    "VadeenChandura": {
        "password_hash": hash_password("password123"),
        "display_name": "Dr. Vadeen Chandura",
        "first_name": "Vadeen",
        "last_name": "Chandura",
        "role": "doctor",
        "position": "GP",
        "email": "vadeen.chandura@hospital.com",
        "department": "Internal Medicine"
    },
    "PrasanthaWalgampola": {
        "password_hash": hash_password("password123"),
        "display_name": "Dr. Prasantha Walgampola",
        "first_name": "Prasantha",
        "last_name": "Walgampola",
        "role": "doctor",
        "position": "GP",
        "email": "prasantha.walgampola@hospital.com",
        "department": "Internal Medicine"
    },
    "KimWong": {
        "password_hash": hash_password("password123"),
        "display_name": "Kim Wong",
        "first_name": "Kim",
        "last_name": "Wong",
        "role": "physiotherapist",
        "position": "Physiotherapist",
        "email": "kim.wong@hospital.com",
        "department": "Rehabilitation"
    },
    "PeterWang": {
        "password_hash": hash_password("password123"),
        "display_name": "Peter Wang",
        "first_name": "Peter",
        "last_name": "Wang",
        "role": "physiotherapist",
        "position": "Physiotherapist",
        "email": "peter.wang@hospital.com",
        "department": "Rehabilitation"
    },
    "ThaiTrinh": {
        "password_hash": hash_password("password123"),
        "display_name": "Thai Trinh",
        "first_name": "Thai",
        "last_name": "Trinh",
        "role": "physiotherapist",
        "position": "Physiotherapist",
        "email": "thai.trinh@hospital.com",
        "department": "Rehabilitation"
    },
    "EdmondGrosser": {
        "password_hash": hash_password("password123"),
        "display_name": "Edmond Grosser",
        "first_name": "Edmond",
        "last_name": "Grosser",
        "role": "physiotherapist",
        "position": "Physiotherapist",
        "email": "edmond.grosser@hospital.com",
        "department": "Rehabilitation"
    }
}

def verify_password(password, password_hash):
    """패스워드 검증"""
    return hash_password(password) == password_hash

def get_user(username):
    """사용자 정보 조회 (대소문자 구분 안함)"""
    # 대소문자 구분하지 않기 위해 모든 키를 소문자로 변환하여 비교
    username_lower = username.lower()
    for key, value in USERS_DB.items():
        if key.lower() == username_lower:
            return value
    return None

def authenticate_user(username, password):
    """사용자 인증 (대소문자 구분 안함)"""
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