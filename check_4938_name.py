#!/usr/bin/env python3
import json

data = json.load(open('data/incidents_Parafield Gardens_2025-10-01_2025-10-08_20251008_145513.json'))
inc = [i for i in data['incidents'] if i['Id'] == 4938][0]

print(f"Incident 4938 Name Data:")
print(f"  FirstName: '{inc.get('FirstName')}'")
print(f"  LastName: '{inc.get('LastName')}'")
print(f"  ClientId: {inc.get('ClientId')}")

# Check if name is in client data
data2 = json.load(open('data/clients_Parafield Gardens_20251008_145514.json'))
client = [c for c in data2 if c.get('id', c.get('Id')) == inc.get('ClientId')]
if client:
    print(f"\nClient {inc.get('ClientId')} found:")
    print(f"  firstName: '{client[0].get('firstName')}'")
    print(f"  lastName: '{client[0].get('lastName')}'")
else:
    print(f"\nClient {inc.get('ClientId')} NOT found in client data")

