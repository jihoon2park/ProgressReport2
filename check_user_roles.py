#!/usr/bin/env python3
"""
Check existing user roles and CIMS permissions
"""

from config_users import USERS_DB

def check_cims_permissions():
    """Check CIMS permissions for existing users"""
    print("Existing Users and CIMS Permissions:")
    print("=" * 50)
    
    for username, user_data in USERS_DB.items():
        role = user_data.get('role', 'unknown')
        name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"
        
        # CIMS 권한 확인
        cims_permissions = []
        
        if role == 'admin':
            cims_permissions = [
                "Full CIMS Access",
                "Policy Management", 
                "User Management",
                "All Incidents View",
                "Compliance Monitoring"
            ]
        elif role == 'site_admin':
            cims_permissions = [
                "Site CIMS Access",
                "Incident Management",
                "Task Monitoring",
                "Site Compliance View"
            ]
        elif role == 'doctor':
            cims_permissions = [
                "Clinical Manager Role",
                "Incident Review",
                "Task Assignment",
                "Medical Assessment Tasks"
            ]
        elif role == 'physiotherapist':
            cims_permissions = [
                "Clinical Manager Role",
                "Mobility Assessment Tasks",
                "Fall Risk Evaluation"
            ]
        else:
            cims_permissions = ["Limited Access"]
        
        print(f"Username: {username}")
        print(f"Name: {name.strip()}")
        print(f"Current Role: {role}")
        print(f"CIMS Permissions: {', '.join(cims_permissions)}")
        print("-" * 30)

if __name__ == "__main__":
    check_cims_permissions()
