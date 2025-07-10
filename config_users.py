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
        "position": "System Administrator"
    },
    "doctor1": {
        "password_hash": hash_password("password123"), 
        "first_name": "John",
        "last_name": "Smith",
        "role": "doctor",
        "position": "Doctor"
    },
    "physio1": {
        "password_hash": hash_password("password123"),
        "first_name": "Sarah",
        "last_name": "Jones",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "PaulVaska": {
        "password_hash": hash_password("password123"),
        "first_name": "Paul",
        "last_name": "Vaska",
        "role": "doctor",
        "position": "GP"
    },
    "VadeenChandura": {
        "password_hash": hash_password("password123"),
        "first_name": "Vadeen",
        "last_name": "Chandura",
        "role": "doctor",
        "position": "GP"
    },
    "PrasanthaWalgampola": {
        "password_hash": hash_password("password123"),
        "first_name": "Prasantha",
        "last_name": "Walgampola",
        "role": "doctor",
        "position": "GP"
    },
    "KimWong": {
        "password_hash": hash_password("password123"),
        "first_name": "Kim",
        "last_name": "Wong",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "PeterWang": {
        "password_hash": hash_password("password123"),
        "first_name": "Peter",
        "last_name": "Wang",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "ThaiTrinh": {
        "password_hash": hash_password("password123"),
        "first_name": "Thai",
        "last_name": "Trinh",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "EdmondGrosser": {
        "password_hash": hash_password("password123"),
        "first_name": "Edmond",
        "last_name": "Grosser",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "SarahJones": {
        "password_hash": hash_password("password123"),
        "first_name": "Sarah",
        "last_name": "Jones",
        "role": "physiotherapist",
        "position": "Physiotherapist"
    },
    "LawJohn": {
        "password_hash": hash_password("John123!"),
        "first_name": "Siew Won (John)",
        "last_name": "Law",
        "role": "doctor",
        "position": "GP"
    },
    "LauKin": {
        "password_hash": hash_password("Kin456@"),
        "first_name": "Kin",
        "last_name": "Lau",
        "role": "doctor",
        "position": "GP"
    },
    "WorleyPaul": {
        "password_hash": hash_password("Paul789#"),
        "first_name": "Paul",
        "last_name": "Worley",
        "role": "doctor",
        "position": "GP"
    },
    "HorKC": {
        "password_hash": hash_password("KC234$"),
        "first_name": "Kok Chung (KC)",
        "last_name": "Hor",
        "role": "doctor",
        "position": "GP"
    },
    "SallehAudrey": {
        "password_hash": hash_password("Audrey567%"),
        "first_name": "Audrey",
        "last_name": "Salleh",
        "role": "doctor",
        "position": "GP"
    },
    "LiNini": {
        "password_hash": hash_password("Nini890@"),
        "first_name": "Xiaoni (Nini)",
        "last_name": "Li",
        "role": "doctor",
        "position": "GP"
    },
    "KiranantawatSoravee": {
        "password_hash": hash_password("Soravee345&"),
        "first_name": "Soravee",
        "last_name": "Kiranantawat",
        "role": "doctor",
        "position": "GP"
    },
    "BansalShiveta": {
        "password_hash": hash_password("Shiveta678*"),
        "first_name": "Shiveta",
        "last_name": "Bansal",
        "role": "doctor",
        "position": "GP"
    },
    "BehanStephen": {
        "password_hash": hash_password("Stephen901?"),
        "first_name": "Stephen",
        "last_name": "Behan",
        "role": "doctor",
        "position": "GP"
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

 