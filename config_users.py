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
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "position": "System Administrator",
        "location": ["All"]
    },
    "PG_admin": {
        "password_hash": hash_password("password"),
        "first_name": "PG",
        "last_name": "Admin",
        "role": "site_admin",
        "position": "Site Administrator",
        "location": ["Parafield Gardens"]
    },
    "PaulVaska": {
        "password_hash": hash_password("Paul123!"),
        "first_name": "Paul",
        "last_name": "Vaska",
        "role": "doctor",
        "position": "GP",
        "location": ["All"]
    },
    "walgampola": {
        "password_hash": hash_password("1Prasanta"),
        "first_name": "Prasantha",
        "last_name": "Walgampola",
        "role": "doctor",
        "position": "GP",
        "location": ["Parafield Gardens"]
    },
   "LawJohn": {
        "password_hash": hash_password("John123!"),
        "first_name": "Siew Won (John)",
        "last_name": "Law",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "LauKin": {
        "password_hash": hash_password("Kin456@"),
        "first_name": "Kin",
        "last_name": "Lau",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "WorleyPaul": {
        "password_hash": hash_password("Paul789#"),
        "first_name": "Paul",
        "last_name": "Worley",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "HorKC": {
        "password_hash": hash_password("KC234$"),
        "first_name": "Kok Chung (KC)",
        "last_name": "Hor",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "SallehAudrey": {
        "password_hash": hash_password("Audrey567%"),
        "first_name": "Audrey",
        "last_name": "Salleh",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "LiNini": {
        "password_hash": hash_password("Nini890@"),
        "first_name": "Xiaoni (Nini)",
        "last_name": "Li",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "KiranantawatSoravee": {
        "password_hash": hash_password("Soravee345&"),
        "first_name": "Soravee",
        "last_name": "Kiranantawat",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "BansalShiveta": {
        "password_hash": hash_password("Shiveta678*"),
        "first_name": "Shiveta",
        "last_name": "Bansal",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "BehanStephen": {
        "password_hash": hash_password("Stephen901?"),
        "first_name": "Stephen",
        "last_name": "Behan",
        "role": "doctor",
        "position": "GP",
        "location": ["Yankalilla"]
    },
    "ROD": {
        "password_hash": hash_password("rod1234!"),
        "first_name": "ROD",
        "last_name": "User",
        "role": "admin",
        "position": "Admin",
        "location": ["All"]
    },
        "ROD_NR": {
        "password_hash": hash_password("rodnr1234!"),
        "first_name": "ROD",
        "last_name": "Nerrilda",
        "role": "admin",
        "position": "Admin",
        "location": ["All"]
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

 