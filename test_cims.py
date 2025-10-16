#!/usr/bin/env python3
"""
Simple CIMS test script
"""

import sys
import os

def test_cims():
    """Test CIMS system"""
    try:
        print("Testing CIMS system...")
        
        # Test database connection
        import sqlite3
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # Check CIMS tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims_%'")
        tables = cursor.fetchall()
        print(f"CIMS tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check sample policy
        cursor.execute("SELECT COUNT(*) FROM cims_policies")
        policy_count = cursor.fetchone()[0]
        print(f"Policies in database: {policy_count}")
        
        conn.close()
        
        # Test Flask imports
        try:
            from flask import Flask
            print("Flask import: OK")
        except ImportError as e:
            print(f"Flask import failed: {e}")
            return False
        
        try:
            from cims_policy_engine import PolicyEngine
            print("Policy Engine import: OK")
        except ImportError as e:
            print(f"Policy Engine import failed: {e}")
            return False
        
        print("CIMS system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"CIMS test failed: {e}")
        return False

if __name__ == "__main__":
    print("CIMS System Test")
    print("=" * 30)
    
    if test_cims():
        print("\nSUCCESS: CIMS system is ready!")
        print("\nTo start the system:")
        print("1. Run: python app.py")
        print("2. Open: http://127.0.0.1:5000/incident_dashboard2")
    else:
        print("\nERROR: CIMS system has issues")
