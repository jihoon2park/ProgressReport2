#!/usr/bin/env python3
import sqlite3
import os
import json
from datetime import datetime, timedelta

def check_real_incident_data():
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    print('=== Checking for Real Incident Data ===')
    
    # Check database tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    all_tables = cursor.fetchall()
    
    real_data_tables = []
    for table in all_tables:
        table_name = table[0]
        if any(keyword in table_name.lower() for keyword in ['incident', 'event', 'adverse', 'client', 'resident']):
            try:
                cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                count = cursor.fetchone()[0]
                if count > 0:
                    real_data_tables.append((table_name, count))
            except:
                pass
    
    if real_data_tables:
        print('Database tables with real data:')
        for table_name, count in real_data_tables:
            print(f'  {table_name}: {count} records')
            
            # Show sample data from each table
            try:
                cursor.execute(f'SELECT * FROM {table_name} LIMIT 2')
                sample_data = cursor.fetchall()
                print(f'    Sample data: {sample_data[:2]}')
            except Exception as e:
                print(f'    Error accessing sample data: {e}')
    else:
        print('No database tables with real incident data found')
    
    # Check JSON files
    print('\n=== Checking JSON Files ===')
    json_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.json') and any(keyword in file.lower() for keyword in ['incident', 'event', 'adverse', 'client', 'resident']):
                json_files.append(os.path.join(root, file))
    
    if json_files:
        print('JSON files with potential real data:')
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        print(f'  {json_file}: {len(data)} records')
                    elif isinstance(data, dict):
                        print(f'  {json_file}: {len(data)} keys')
                    else:
                        print(f'  {json_file}: {type(data)}')
            except Exception as e:
                print(f'  {json_file}: Error reading file - {e}')
    else:
        print('No JSON files with real incident data found')
    
    # Check if there's a way to fetch real data
    print('\n=== Checking for Real Data Fetching Capabilities ===')
    
    # Check if there are any API configuration files
    config_files = ['config.py', 'config_env.py', 'config_users.py']
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f'  {config_file}: Found')
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'api' in content.lower() or 'server' in content.lower():
                        print(f'    Contains API/server configuration')
            except:
                pass
        else:
            print(f'  {config_file}: Not found')
    
    conn.close()

if __name__ == '__main__':
    check_real_incident_data()
