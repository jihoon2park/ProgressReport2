#!/usr/bin/env python3
"""
Check policy structure
"""

import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_policy():
    """Check policy structure"""
    try:
        conn = sqlite3.connect('progress_report.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cims_policies WHERE is_active = 1")
        policy = cursor.fetchone()
        
        if not policy:
            print("❌ No active policy found!")
            return False
        
        print("=" * 60)
        print("ACTIVE POLICY")
        print("=" * 60)
        print(f"ID: {policy['id']}")
        print(f"Policy ID: {policy['policy_id']}")
        print(f"Name: {policy['name']}")
        print(f"Version: {policy['version']}")
        print(f"Active: {policy['is_active']}")
        
        print("\n" + "=" * 60)
        print("POLICY RULES (JSON)")
        print("=" * 60)
        
        rules_json = policy['rules_json']
        print(rules_json[:500] + "..." if len(rules_json) > 500 else rules_json)
        
        print("\n" + "=" * 60)
        print("PARSED RULES")
        print("=" * 60)
        
        try:
            rules = json.loads(rules_json)
            print(json.dumps(rules, indent=2))
            
            if 'nurse_visit_schedule' in rules:
                schedule = rules['nurse_visit_schedule']
                print(f"\n✅ Found nurse_visit_schedule with {len(schedule)} phases")
                for i, phase in enumerate(schedule, 1):
                    print(f"  Phase {i}: {phase}")
            else:
                print("\n❌ No 'nurse_visit_schedule' key found in rules!")
                print(f"Available keys: {list(rules.keys())}")
                
        except Exception as e:
            print(f"❌ Error parsing JSON: {e}")
        
        conn.close()
        return True
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_policy()

