#!/usr/bin/env python3
"""JSON 파일에서 RIAM 검색"""
import json
import os

def search_in_json_file(filepath, search_name):
    """JSON 파일에서 이름 검색"""
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        
        # 리스트인 경우
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    first = str(item.get('FirstName', '')).upper()
                    last = str(item.get('LastName', '')).upper()
                    surname = str(item.get('Surname', '')).upper()
                    pref = str(item.get('PreferredName', '')).upper()
                    
                    if (search_name.upper() in first or 
                        search_name.upper() in last or 
                        search_name.upper() in surname or
                        search_name.upper() in pref):
                        results.append(item)
        
        # 딕셔너리인 경우
        elif isinstance(data, dict):
            # 'clients' 키가 있는 경우
            if 'clients' in data:
                for item in data['clients']:
                    if isinstance(item, dict):
                        first = str(item.get('FirstName', '')).upper()
                        last = str(item.get('LastName', '')).upper()
                        surname = str(item.get('Surname', '')).upper()
                        pref = str(item.get('PreferredName', '')).upper()
                        
                        if (search_name.upper() in first or 
                            search_name.upper() in last or 
                            search_name.upper() in surname or
                            search_name.upper() in pref):
                            results.append(item)
        
        return results
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return []

if __name__ == '__main__':
    search_name = 'RIAM'
    data_dir = 'data'
    
    json_files = [
        'nerrilda_client.json',
        'parafield_gardens_client.json',
        'ramsay_client.json',
        'yankalilla_client.json'
    ]
    
    print(f"Searching for '{search_name}' in JSON files...\n")
    
    found_any = False
    for json_file in json_files:
        filepath = os.path.join(data_dir, json_file)
        site_name = json_file.replace('_client.json', '').replace('_', ' ').title()
        
        results = search_in_json_file(filepath, search_name)
        
        if results:
            found_any = True
            print(f"=== {site_name} ===")
            for item in results:
                first = item.get('FirstName', '')
                last = item.get('LastName', '') or item.get('Surname', '')
                pref = item.get('PreferredName', '')
                client_id = item.get('Id', '') or item.get('ClientId', '')
                
                name = f"{first} {last}".strip()
                pref_str = f" ({pref})" if pref else ""
                
                print(f"  - {name}{pref_str} (ID: {client_id})")
            print()
    
    if not found_any:
        print("No results found in JSON files.")
        print("\nTrying to fetch fresh data from MANAD DB...")
        
        # 최신 데이터 가져오기
        try:
            from api_client import fetch_client_information
            
            for site in ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']:
                try:
                    success, clients = fetch_client_information(site)
                    if success and clients:
                        found = []
                        for client in clients:
                            if isinstance(client, dict):
                                first = str(client.get('FirstName', '')).upper()
                                last = str(client.get('LastName', '')).upper()
                                surname = str(client.get('Surname', '')).upper()
                                pref = str(client.get('PreferredName', '')).upper()
                                
                                if (search_name.upper() in first or 
                                    search_name.upper() in last or 
                                    search_name.upper() in surname or
                                    search_name.upper() in pref):
                                    found.append(client)
                        
                        if found:
                            print(f"\n=== {site} (Fresh Data) ===")
                            for client in found:
                                first = client.get('FirstName', '')
                                last = client.get('LastName', '') or client.get('Surname', '')
                                pref = client.get('PreferredName', '')
                                client_id = client.get('Id', '') or client.get('ClientId', '')
                                
                                name = f"{first} {last}".strip()
                                pref_str = f" ({pref})" if pref else ""
                                
                                print(f"  - {name}{pref_str} (ID: {client_id})")
                except Exception as e:
                    print(f"  {site}: Error - {e}")
                    continue
        except Exception as e:
            print(f"Error fetching from MANAD DB: {e}")

