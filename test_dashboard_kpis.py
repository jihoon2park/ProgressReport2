#!/usr/bin/env python3
"""
Dashboard KPI API 테스트 스크립트
"""

import requests
import json

# 서버 URL 설정
BASE_URL = "http://202.90.243.226"  # Production
# BASE_URL = "http://localhost:5000"  # Development

# 로그인 정보
USERNAME = "admin"  # 실제 사용자명으로 변경
PASSWORD = "your_password"  # 실제 비밀번호로 변경

def test_dashboard_kpis():
    """Dashboard KPI API 테스트"""
    
    # 세션 생성
    session = requests.Session()
    
    # 1. 로그인
    print("🔐 Logging in...")
    login_url = f"{BASE_URL}/login"
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'site': 'Parafield Gardens'  # 사이트 선택
    }
    
    login_response = session.post(login_url, data=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"Response: {login_response.text}")
        return
    
    print("✅ Login successful")
    
    # 2. Dashboard KPI API 호출
    print("\n📊 Fetching Dashboard KPIs...")
    kpi_url = f"{BASE_URL}/api/cims/dashboard-kpis"
    params = {
        'period': 'week',
        'incident_type': 'all'
    }
    
    kpi_response = session.get(kpi_url, params=params)
    
    print(f"Status Code: {kpi_response.status_code}")
    
    if kpi_response.status_code == 200:
        data = kpi_response.json()
        print("\n✅ KPI Data:")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n❌ Error: {kpi_response.status_code}")
        print(f"Response: {kpi_response.text}")
    
    # 3. 다른 기간 테스트
    print("\n📊 Testing different periods...")
    periods = ['today', 'week', 'month']
    
    for period in periods:
        params = {
            'period': period,
            'incident_type': 'all'
        }
        response = session.get(kpi_url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"\n{period.upper()}:")
            print(f"  Total: {data.get('total_incidents', 0)}")
            print(f"  Open: {data.get('open_incidents', 0)}")
            print(f"  Closed: {data.get('closed_incidents', 0)}")
            print(f"  In Progress: {data.get('in_progress_incidents', 0)}")
            print(f"  Fall Count: {data.get('fall_count', 0)}")
            print(f"  Compliance Rate: {data.get('compliance_rate', 0)}%")
        else:
            print(f"  ❌ {period}: Error {response.status_code}")

if __name__ == '__main__':
    test_dashboard_kpis()

