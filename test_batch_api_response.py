#!/usr/bin/env python3
"""
Batch API 응답 테스트
실제로 policies가 제대로 반환되는지 확인
"""

import requests
import json
from datetime import datetime

# API 엔드포인트
base_url = "http://192.168.1.124:5000"
site = "Parafield Gardens"
date = datetime.now().strftime("%Y-%m-%d")

url = f"{base_url}/api/cims/schedule-batch/{site}/{date}"

print("=" * 80)
print(f"Testing Batch API: {url}")
print("=" * 80)

try:
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\n✅ API Response Status: {response.status_code}")
        print(f"✅ Success: {data.get('success')}")
        print(f"✅ Incidents: {len(data.get('incidents', []))}")
        
        # Policies 확인
        policies = data.get('policies', {})
        print(f"\n📋 Policies in response: {len(policies)}")
        print(f"   Policy keys: {list(policies.keys())}")
        
        for policy_id, policy_data in policies.items():
            rules = policy_data.get('rules', {})
            schedule = rules.get('nurse_visit_schedule', [])
            print(f"\n   {policy_id}:")
            print(f"     - Name: {policy_data.get('name')}")
            print(f"     - Phases: {len(schedule)}")
            for idx, phase in enumerate(schedule, 1):
                print(f"       Phase {idx}: Every {phase.get('interval')} {phase.get('interval_unit')} for {phase.get('duration')} {phase.get('duration_unit')}")
        
        # Incidents 확인
        incidents = data.get('incidents', [])
        print(f"\n📋 Incidents with fall_type:")
        for inc in incidents[:5]:  # 처음 5개만
            print(f"   {inc.get('incident_id')}: fall_type={inc.get('fall_type')}")
        
        # Legacy policy 확인
        legacy_policy = data.get('policy')
        if legacy_policy:
            print(f"\n⚠️ Legacy policy also present: {legacy_policy.get('name', 'N/A')}")
        
    else:
        print(f"\n❌ API Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

