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
    "ChanduraVadeen": {
        "password_hash": hash_password("Chandura123!"),
        "first_name": "Chandura",
        "last_name": "Vadeen",
        "role": "doctor",
        "position": "GP",
        "location": ["All"]
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
    },
    "YKROD": {
        "password_hash": hash_password("ykpassword"),
        "first_name": "ROD",
        "last_name": "Yankalilla",
        "role": "admin",
        "position": "Admin",
        "location": ["Yankalilla"]
    },
    "PGROD": {
        "password_hash": hash_password("pgpassword"),
        "first_name": "ROD",
        "last_name": "Parafield Gardens",
        "role": "admin",
        "position": "Admin",
        "location": ["Ramsay", "Nerrilda", "Parafield Gardens"]
    },
    "WPROD": {
        "password_hash": hash_password("wppassword"),
        "first_name": "ROD",
        "last_name": "West Park",
        "role": "admin",
        "position": "Admin",
        "location": ["West Park"]
    },
    "RSROD": {
        "password_hash": hash_password("rspassword"),
        "first_name": "ROD",
        "last_name": "Ramsay",
        "role": "admin",
        "position": "Admin",
        "location": ["Ramsay", "Nerrilda"]
    },
    "NROD": {
        "password_hash": hash_password("nrpassword"),
        "first_name": "ROD",
        "last_name": "Nerrilda",
        "role": "admin",
        "position": "Admin",
        "location": ["Nerrilda"]
    },
    "philipd": {
        "password_hash": hash_password("philip1234!"),
        "first_name": "Philip",
        "last_name": "West Park",
        "role": "doctor",
        "position": "GP",
        "location": ["West Park"]
    },
    "operation": {
        "password_hash": hash_password("password123"),
        "first_name": "Operation",
        "last_name": "User",
        "role": "admin",
        "position": "Operations Manager",
        "location": ["All"],
        "landing_page": "/edenfield-dashboard"
    },

    "physio1": {
        "password_hash": hash_password("password123"),
        "first_name": "Physio",
        "last_name": "",
        "role": "doctor",
        "position": "Physiotherapist",
        "location": ["All"]
    },
    "physio2": {
        "password_hash": hash_password("password123"),
        "first_name": "Physio",
        "last_name": "",
        "role": "doctor",
        "position": "Physiotherapist",
        "location": ["All"]
    },
    "physio3": {
        "password_hash": hash_password("password123"),
        "first_name": "Physio",
        "last_name": "",
        "role": "doctor",
        "position": "Physiotherapist",
        "location": ["All"]
    },
    "esm.pg": {
        "password_hash": hash_password("Edenfield2026!"),
        "first_name": "ESM.PG",
        "last_name": "Admin",
        "role": "site_admin",
        "position": "Site Administrator",
        "location": ["Parafield Gardens"]
    },
    "esm.pa": {
        "password_hash": hash_password("Edenfield2026!"),
        "first_name": "ESM.PA",
        "last_name": "Admin",
        "role": "site_admin",
        "position": "Site Administrator",
        "location": ["Ramsay"]
    },
    "staff.parafield": {
        "password_hash": hash_password("2036"),
        "first_name": "Staff",
        "last_name": "Parafield",
        "role": "staff",
        "position": "Staff",
        "location": ["Parafield Gardens"]
    },
    "staff.ramsay": {
        "password_hash": hash_password("password123"),
        "first_name": "Staff",
        "last_name": "Ramsay",
        "role": "staff",
        "position": "Staff",
        "location": ["Ramsay"]
    },
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

def get_all_users():
    """모든 사용자 정보 조회 (패스워드 해시 제외)"""
    users = []
    for username, user_data in USERS_DB.items():
        safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
        safe_user["username"] = username
        users.append(safe_user)
    return users

def get_username_by_lowercase(username):
    """대소문자 구분 없이 실제 username 찾기"""
    username_lower = username.lower()
    for key in USERS_DB.keys():
        if key.lower() == username_lower:
            return key
    return None

def add_user(username, password, first_name, last_name, role, position, location, landing_page=None):
    """새로운 사용자 추가"""
    if get_user(username):
        return False, "User already exists"
    
    user_data = {
        "password_hash": hash_password(password),
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "position": position,
        "location": location
    }
    
    if landing_page:
        user_data["landing_page"] = landing_page
    
    USERS_DB[username] = user_data
    return True, "User added successfully"

def update_user(username, first_name=None, last_name=None, role=None, position=None, location=None, password=None, landing_page=None):
    """사용자 정보 수정"""
    actual_username = get_username_by_lowercase(username)
    if not actual_username:
        return False, "User not found"
    
    if first_name is not None:
        USERS_DB[actual_username]["first_name"] = first_name
    if last_name is not None:
        USERS_DB[actual_username]["last_name"] = last_name
    if role is not None:
        USERS_DB[actual_username]["role"] = role
    if position is not None:
        USERS_DB[actual_username]["position"] = position
    if location is not None:
        USERS_DB[actual_username]["location"] = location
    if password is not None:
        USERS_DB[actual_username]["password_hash"] = hash_password(password)
    if landing_page is not None:
        if landing_page:
            USERS_DB[actual_username]["landing_page"] = landing_page
        elif "landing_page" in USERS_DB[actual_username]:
            del USERS_DB[actual_username]["landing_page"]
    
    return True, "User updated successfully"

def delete_user(username):
    """사용자 삭제"""
    actual_username = get_username_by_lowercase(username)
    if not actual_username:
        return False, "User not found"
    
    del USERS_DB[actual_username]
    return True, "User deleted successfully"

def get_unique_roles():
    """시스템의 모든 고유한 역할 목록 반환"""
    roles = set()
    for user_data in USERS_DB.values():
        roles.add(user_data.get("role", ""))
    return sorted(list(roles))

def get_unique_positions():
    """시스템의 모든 고유한 직책 목록 반환"""
    positions = set()
    for user_data in USERS_DB.values():
        positions.add(user_data.get("position", ""))
    return sorted(list(positions))

def get_unique_locations():
    """시스템의 모든 고유한 위치 목록 반환"""
    locations = set()
    for user_data in USERS_DB.values():
        location_list = user_data.get("location", [])
        if isinstance(location_list, list):
            locations.update(location_list)
    return sorted(list(locations))

 