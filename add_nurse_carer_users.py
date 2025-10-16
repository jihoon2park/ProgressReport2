#!/usr/bin/env python3
"""
Add sample Nurse and Carer users to config_users.py
"""

def generate_additional_users():
    """Generate additional user entries for Nurses and Carers"""
    
    additional_users = '''
    # CIMS 전용 사용자 (간호사 및 케어러)
    "nurse1": {
        "password_hash": hash_password("nurse123!"),
        "first_name": "Sarah",
        "last_name": "Johnson",
        "role": "registered_nurse",
        "position": "Registered Nurse",
        "location": ["Parafield Gardens"]
    },
    "nurse2": {
        "password_hash": hash_password("nurse456!"),
        "first_name": "Emma",
        "last_name": "Wilson",
        "role": "registered_nurse", 
        "position": "Registered Nurse",
        "location": ["Yankalilla"]
    },
    "carer1": {
        "password_hash": hash_password("carer123!"),
        "first_name": "Mike",
        "last_name": "Brown",
        "role": "carer",
        "position": "Personal Care Assistant",
        "location": ["Parafield Gardens"]
    },
    "carer2": {
        "password_hash": hash_password("carer456!"),
        "first_name": "Lisa",
        "last_name": "Davis",
        "role": "carer",
        "position": "Personal Care Assistant", 
        "location": ["Yankalilla"]
    },
    "clinical_mgr1": {
        "password_hash": hash_password("clinical123!"),
        "first_name": "Dr. Jennifer",
        "last_name": "Thompson",
        "role": "clinical_manager",
        "position": "Clinical Manager",
        "location": ["All"]
    }'''
    
    print("Additional CIMS Users to Add:")
    print("=" * 40)
    print("Username: nurse1 / Password: nurse123!")
    print("Role: Registered Nurse")
    print()
    print("Username: nurse2 / Password: nurse456!")
    print("Role: Registered Nurse")
    print()
    print("Username: carer1 / Password: carer123!")
    print("Role: Carer")
    print()
    print("Username: carer2 / Password: carer456!")
    print("Role: Carer")
    print()
    print("Username: clinical_mgr1 / Password: clinical123!")
    print("Role: Clinical Manager")
    print()
    print("To add these users, append the following to config_users.py USERS_DB:")
    print(additional_users)

if __name__ == "__main__":
    generate_additional_users()
