#!/usr/bin/env python3
"""Resident search script"""
import sqlite3
import sys

def search_resident_in_cache(name):
    """Search resident in SQLite cache"""
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT client_name, first_name, surname, site, client_record_id, person_id
            FROM clients_cache 
            WHERE client_name LIKE ? 
               OR first_name LIKE ? 
               OR surname LIKE ? 
               OR preferred_name LIKE ?
            COLLATE NOCASE
        """, (f'%{name}%', f'%{name}%', f'%{name}%', f'%{name}%'))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    except Exception as e:
        print(f"SQLite search error: {e}")
        return []

def search_resident_in_manad(name, site=None):
    """Search resident in MANAD DB (direct query)"""
    try:
        from manad_db_connector import MANADDBConnector
        
        sites = [site] if site else ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']
        all_results = []
        
        for site_name in sites:
            try:
                connector = MANADDBConnector(site_name)
                
                with connector.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Query to search by name (case-insensitive)
                    query = """
                        SELECT DISTINCT
                            c.Id,
                            ISNULL(p.FirstName, '') AS FirstName,
                            ISNULL(p.LastName, '') AS LastName,
                            ISNULL(p.PreferredName, '') AS PreferredName
                        FROM Client c
                        INNER JOIN ClientService cs ON c.MainClientServiceId = cs.Id
                        LEFT JOIN Person p ON c.PersonId = p.Id
                        WHERE c.IsDeleted = 0 
                            AND cs.IsDeleted = 0
                            AND cs.EndDate IS NULL
                            AND (
                                UPPER(p.FirstName) LIKE UPPER(?)
                                OR UPPER(p.LastName) LIKE UPPER(?)
                                OR UPPER(p.PreferredName) LIKE UPPER(?)
                            )
                        ORDER BY ISNULL(p.LastName, ''), ISNULL(p.FirstName, '')
                    """
                    
                    search_pattern = f'%{name}%'
                    cursor.execute(query, (search_pattern, search_pattern, search_pattern))
                    
                    rows = cursor.fetchall()
                    for row in rows:
                        client_id, first_name, last_name, preferred_name = row
                        full_name = f"{first_name} {last_name}".strip()
                        
                        all_results.append({
                            'site': site_name,
                            'name': full_name,
                            'first_name': first_name,
                            'last_name': last_name,
                            'preferred_name': preferred_name or '',
                            'client_id': client_id
                        })
                        
            except Exception as e:
                print(f"  {site_name} search failed: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return all_results
    except Exception as e:
        print(f"MANAD DB search error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    import sys
    import io
    # Configure Windows console encoding
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    search_name = sys.argv[1] if len(sys.argv) > 1 else 'RIAM'
    
    print(f"Searching for '{search_name}' resident...\n")
    
    # 1. Search in SQLite cache
    print("SQLite Cache Search:")
    cache_results = search_resident_in_cache(search_name)
    if cache_results:
        for row in cache_results:
            print(f"  - {row[0]} ({row[1]} {row[2]}) - {row[3]} (ID: {row[4]})")
    else:
        print("  No results found")
    
    print("\n" + "="*60 + "\n")
    
    # 2. Search in MANAD DB
    print("MANAD DB Search (All Sites):")
    manad_results = search_resident_in_manad(search_name)
    if manad_results:
        for result in manad_results:
            pref = f" ({result['preferred_name']})" if result['preferred_name'] else ""
            print(f"  - {result['name']}{pref} - {result['site']} (ID: {result['client_id']})")
    else:
        print("  No results found")
        print("\n  Trying to list all residents to find similar names...")
        # Find similar names from all resident list
        try:
            from manad_db_connector import MANADDBConnector
            for site_name in ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'West Park', 'Yankalilla']:
                try:
                    connector = MANADDBConnector(site_name)
                    success, clients = connector.fetch_clients()
                    if success and clients:
                        # Find names containing RIAM
                        found = []
                        for client in clients:
                            first = client.get('FirstName', '')
                            last = client.get('LastName', '')
                            pref = client.get('PreferredName', '')
                            full = f"{first} {last}".strip()
                            
                            if (search_name.upper() in first.upper() or 
                                search_name.upper() in last.upper() or 
                                search_name.upper() in pref.upper() or
                                search_name.upper() in full.upper()):
                                found.append((full, pref, client.get('Id', '')))
                        
                        if found:
                            print(f"\n  {site_name}:")
                            for name, pref_name, cid in found:
                                pref_str = f" ({pref_name})" if pref_name else ""
                                print(f"    - {name}{pref_str} (ID: {cid})")
                except Exception as e:
                    print(f"  {site_name}: Error - {e}")
                    continue
        except Exception as e:
            print(f"  Error listing all residents: {e}")
    
    print(f"\nSearch complete: Cache {len(cache_results)} results, MANAD DB {len(manad_results)} results")

