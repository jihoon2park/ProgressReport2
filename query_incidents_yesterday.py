#!/usr/bin/env python3
"""
Fetch ALL incidents (client + staff) for Parafield Gardens.
READ-ONLY: SELECT queries only - no INSERT, UPDATE, DELETE.

Incident types:
- AdverseEvent: Client incidents (ClientId, ClientServiceId) - resident-related
- PersonnelIncident: Staff incidents (PersonnelId) - workforce-related

Site filter: LocationId from Location WHERE Name LIKE '%Parafield%' (LocationId=1 for Parafield Gardens).

Joins for full info:
- AdverseEvent: Client, Person (resident), ClientService, Wing, Location, AdverseEventType,
  AdverseEventRiskRating, RiskCategory, WitnessPerson
- PersonnelIncident: Personnel, Person (staff), Location, Department, Area,
  PersonnelIncidentRiskRating, PersonnelIncidentSeverityRating, RiskCategory,
  WitnessPerson, BodyLocation, PersonnelIncidentCause, PersonnelIncidentOutcome

Usage:
    python query_incidents_yesterday.py

Output: data/incidents_last_30_days_parafield_gardens.json (Parafield Gardens, last 30 days, date DESC)
"""

import json
import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8', errors='replace')
        except Exception:
            return '<binary>'
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def _serialize_val(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, bytes):
        return '<binary>'
    if isinstance(val, Decimal):
        return float(val)
    return val


def _row_to_dict(cursor, row):
    cols = [c[0] for c in cursor.description]
    return {cols[i]: _serialize_val(row[i]) if i < len(row) else None for i in range(len(cols))}


def _fetch_one(cursor, table: str, id_col: str, id_val):
    try:
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{id_col}] = ?", (id_val,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row) if row else None
    except Exception as e:
        return {'__error__': str(e)}


def _fetch_many(cursor, table: str, filter_col: str, filter_val):
    try:
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{filter_col}] = ?", (filter_val,))
        return [_row_to_dict(cursor, r) for r in cursor.fetchall()]
    except Exception as e:
        return [{'__error__': str(e)}]


# StatusEnumId: 0=open, 2=closed (used in AdverseEvent and PersonnelIncident)
STATUS_ENUM_MEANINGS = {'0': 'open', '2': 'closed'}


def _safe_name(row, *keys):
    """Get first non-null value from row for given keys; return None if row has __error__."""
    if not row or row.get('__error__'):
        return None
    for k in keys:
        v = row.get(k)
        if v is not None and v != '':
            return str(v).strip() or None
    return None


def _get_location_ids_for_site(cursor, site_name: str) -> list:
    """Get LocationId(s) for site (e.g. Parafield Gardens)."""
    try:
        # Match "Parafield" in Location.Name (e.g. "Edenfield Family Care - Parafield Gardens")
        cursor.execute(
            "SELECT Id FROM [Location] WHERE [Name] LIKE ? AND (IsArchived = 0 OR IsArchived IS NULL) AND (IsDeleted = 0 OR IsDeleted IS NULL)",
            (f'%{site_name.split()[0]}%',)  # "Parafield" from "Parafield Gardens"
        )
        return [r[0] for r in cursor.fetchall()]
    except Exception as e:
        print(f"Warning: Could not get LocationIds: {e}")
        return []


def query_incidents_yesterday(site: str = "Parafield Gardens", target_date: date = None, days: int = None) -> dict:
    """Fetch all client + staff incidents. Use days=N for last N days, or target_date for single day."""
    from manad_db_connector import MANADDBConnector

    connector = MANADDBConnector(site)
    today = date.today()
    if days is not None and days > 0:
        date_start = datetime.combine(today - timedelta(days=days), datetime.min.time())
        date_end = datetime.combine(today, datetime.max.time())
        date_label = f"last_{days}_days"
    else:
        target = target_date or (today - timedelta(days=1))
        date_start = datetime.combine(target, datetime.min.time())
        date_end = datetime.combine(target, datetime.max.time())
        date_label = target.isoformat()

    result = {
        'site': site,
        'date_from': date_start.date().isoformat(),
        'date_to': date_end.date().isoformat(),
        'date': date_label,
        'queried_at': datetime.now().isoformat(),
        'location_ids': [],
        'id_meanings': {
            'StatusEnumId': STATUS_ENUM_MEANINGS,
        },
        'adverse_events': [],   # Client incidents
        'personnel_incidents': [],  # Staff incidents
        'error': None,
    }

    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Get LocationId(s) for Parafield
            location_ids = _get_location_ids_for_site(cursor, site)
            result['location_ids'] = location_ids
            if not location_ids:
                result['error'] = f'No Location found for site: {site}'
                return result

            loc_placeholders = ','.join('?' * len(location_ids))

            # 2. AdverseEvent (client incidents) - yesterday, this location
            cursor.execute(f"""
                SELECT * FROM [AdverseEvent]
                WHERE [LocationId] IN ({loc_placeholders})
                  AND [Date] >= ? AND [Date] <= ?
                  AND (IsDeleted = 0 OR IsDeleted IS NULL)
                ORDER BY [Date] DESC
            """, (*location_ids, date_start, date_end))
            ae_rows = [_row_to_dict(cursor, r) for r in cursor.fetchall()]

            for ae in ae_rows:
                inc = {
                    'summary': {},  # Top-level: resident_name, wing, event_type, etc.
                    'adverse_event': ae,
                    'client': None,
                    'person': None,
                    'client_service': None,
                    'wing': None,
                    'location': None,
                    'adverse_event_types': [],
                    'risk_rating': None,
                    'risk_categories': [],
                    'witnesses': [],
                }
                # Client
                if ae.get('ClientId'):
                    inc['client'] = _fetch_one(cursor, 'Client', 'Id', ae['ClientId'])
                    if inc['client'] and not inc['client'].get('__error__') and inc['client'].get('PersonId'):
                        inc['person'] = _fetch_one(cursor, 'Person', 'Id', inc['client']['PersonId'])
                # ClientService, Wing, Location
                if ae.get('ClientServiceId'):
                    inc['client_service'] = _fetch_one(cursor, 'ClientService', 'Id', ae['ClientServiceId'])
                    if inc['client_service'] and not inc['client_service'].get('__error__'):
                        if inc['client_service'].get('WingId'):
                            inc['wing'] = _fetch_one(cursor, 'Wing', 'Id', inc['client_service']['WingId'])
                if ae.get('LocationId'):
                    inc['location'] = _fetch_one(cursor, 'Location', 'Id', ae['LocationId'])
                # Department, Area, Wing (from ae), Room - for summary merged info only
                if ae.get('DepartmentId'):
                    inc['department'] = _fetch_one(cursor, 'Department', 'Id', ae['DepartmentId'])
                if ae.get('AreaId'):
                    inc['area'] = _fetch_one(cursor, 'Area', 'Id', ae['AreaId'])
                if ae.get('WingId'):
                    inc['wing'] = inc.get('wing') or _fetch_one(cursor, 'Wing', 'Id', ae['WingId'])
                if ae.get('RoomId'):
                    inc['room'] = _fetch_one(cursor, 'Room', 'Id', ae['RoomId'])
                    if inc['room'] and not inc['room'].get('__error__') and inc['room'].get('CurrentRoomStructureId'):
                        inc['room_structure'] = _fetch_one(cursor, 'RoomStructure', 'Id', inc['room']['CurrentRoomStructureId'])
                # AdverseEventType (via link table)
                for link in _fetch_many(cursor, 'AdverseEvent_AdverseEventType', 'AdverseEventId', ae['Id']):
                    if link and not link.get('__error__') and link.get('AdverseEventTypeId'):
                        et = _fetch_one(cursor, 'AdverseEventType', 'Id', link['AdverseEventTypeId'])
                        if et and not et.get('__error__'):
                            inc['adverse_event_types'].append(et)
                # Risk rating
                if ae.get('AdverseEventRiskRatingId'):
                    inc['risk_rating'] = _fetch_one(cursor, 'AdverseEventRiskRating', 'Id', ae['AdverseEventRiskRatingId'])
                # Risk categories
                for link in _fetch_many(cursor, 'AdverseEvent_RiskCategory', 'AdverseEventId', ae['Id']):
                    if link and not link.get('__error__') and link.get('RiskCategoryId'):
                        rc = _fetch_one(cursor, 'RiskCategory', 'Id', link['RiskCategoryId'])
                        if rc and not rc.get('__error__'):
                            inc['risk_categories'].append(rc)
                # Witnesses
                for link in _fetch_many(cursor, 'AdverseEvent_WitnessPerson', 'AdverseEventId', ae['Id']):
                    if link and not link.get('__error__') and link.get('PersonId'):
                        p = _fetch_one(cursor, 'Person', 'Id', link['PersonId'])
                        if p and not p.get('__error__'):
                            inc['witnesses'].append(p)

                # Summary: merged lookup info (LocationId→location_name, DepartmentId→department_name, etc.)
                p = inc.get('person') or {}
                status_id = ae.get('StatusEnumId')
                status_meaning = STATUS_ENUM_MEANINGS.get(str(status_id)) if status_id is not None else None
                inc['summary'] = {
                    'resident_name': f"{p.get('FirstName', '')} {p.get('MiddleName', '')} {p.get('LastName', '')}".replace('  ', ' ').strip() or None,
                    'client_id': ae.get('ClientId'),
                    'location_name': _safe_name(inc.get('location'), 'Name'),
                    'department_name': _safe_name(inc.get('department'), 'Description', 'Name'),
                    'area_name': _safe_name(inc.get('area'), 'Description', 'Name'),
                    'wing_name': _safe_name(inc.get('wing'), 'Name'),
                    'status_meaning': status_meaning,
                    'event_types': [t.get('Description') for t in (inc.get('adverse_event_types') or []) if t and not t.get('__error__')],
                    'risk_rating': _safe_name(inc.get('risk_rating'), 'Description'),
                    'date': ae.get('Date'),
                    'description': (ae.get('Description') or '')[:500],
                    'action_taken': (ae.get('ActionTaken') or '')[:500],
                }

                result['adverse_events'].append(inc)

            # 3. PersonnelIncident (staff incidents) - yesterday, this location
            cursor.execute(f"""
                SELECT * FROM [PersonnelIncident]
                WHERE [LocationId] IN ({loc_placeholders})
                  AND [Date] >= ? AND [Date] <= ?
                  AND (IsDeleted = 0 OR IsDeleted IS NULL)
                ORDER BY [Date] DESC
            """, (*location_ids, date_start, date_end))
            pi_rows = [_row_to_dict(cursor, r) for r in cursor.fetchall()]

            for pi in pi_rows:
                inc = {
                    'summary': {},  # Top-level: staff_name, location, etc.
                    'personnel_incident': pi,
                    'personnel': None,
                    'person': None,
                    'location': None,
                    'department': None,
                    'area': None,
                    'risk_rating': None,
                    'severity_rating': None,
                    'risk_categories': [],
                    'witnesses': [],
                    'body_locations': [],
                    'causes': [],
                    'outcomes': [],
                }
                # Personnel -> Person
                if pi.get('PersonnelId'):
                    inc['personnel'] = _fetch_one(cursor, 'Personnel', 'Id', pi['PersonnelId'])
                    if inc['personnel'] and not inc['personnel'].get('__error__') and inc['personnel'].get('PersonId'):
                        inc['person'] = _fetch_one(cursor, 'Person', 'Id', inc['personnel']['PersonId'])
                # Location, Department, Area
                if pi.get('LocationId'):
                    inc['location'] = _fetch_one(cursor, 'Location', 'Id', pi['LocationId'])
                if pi.get('DepartmentId'):
                    inc['department'] = _fetch_one(cursor, 'Department', 'Id', pi['DepartmentId'])
                if pi.get('AreaId'):
                    inc['area'] = _fetch_one(cursor, 'Area', 'Id', pi['AreaId'])
                # Risk/Severity
                if pi.get('PersonnelIncidentRiskRatingId'):
                    inc['risk_rating'] = _fetch_one(cursor, 'PersonnelIncidentRiskRating', 'Id', pi['PersonnelIncidentRiskRatingId'])
                if pi.get('PersonnelIncidentSeverityRatingId'):
                    inc['severity_rating'] = _fetch_one(cursor, 'PersonnelIncidentSeverityRating', 'Id', pi['PersonnelIncidentSeverityRatingId'])
                # Risk categories
                for link in _fetch_many(cursor, 'PersonnelIncident_RiskCategory', 'PersonnelIncidentId', pi['Id']):
                    if link and not link.get('__error__') and link.get('RiskCategoryId'):
                        rc = _fetch_one(cursor, 'RiskCategory', 'Id', link['RiskCategoryId'])
                        if rc and not rc.get('__error__'):
                            inc['risk_categories'].append(rc)
                # Witnesses
                for link in _fetch_many(cursor, 'PersonnelIncident_WitnessPerson', 'PersonnelIncidentId', pi['Id']):
                    if link and not link.get('__error__') and link.get('PersonId'):
                        p = _fetch_one(cursor, 'Person', 'Id', link['PersonId'])
                        if p and not p.get('__error__'):
                            inc['witnesses'].append(p)
                # Body locations
                for link in _fetch_many(cursor, 'PersonnelIncident_BodyLocation', 'PersonnelIncidentId', pi['Id']):
                    if link and not link.get('__error__') and link.get('BodyLocationId'):
                        bl = _fetch_one(cursor, 'BodyLocation', 'Id', link['BodyLocationId'])
                        if bl and not bl.get('__error__'):
                            inc['body_locations'].append(bl)
                # Causes
                for link in _fetch_many(cursor, 'PersonnelIncident_PersonnelIncidentCause', 'PersonnelIncidentId', pi['Id']):
                    if link and not link.get('__error__') and link.get('PersonnelIncidentCauseId'):
                        c = _fetch_one(cursor, 'PersonnelIncidentCause', 'Id', link['PersonnelIncidentCauseId'])
                        if c and not c.get('__error__'):
                            inc['causes'].append(c)
                # Outcomes
                for link in _fetch_many(cursor, 'PersonnelIncident_PersonnelIncidentOutcome', 'PersonnelIncidentId', pi['Id']):
                    if link and not link.get('__error__') and link.get('PersonnelIncidentOutcomeId'):
                        o = _fetch_one(cursor, 'PersonnelIncidentOutcome', 'Id', link['PersonnelIncidentOutcomeId'])
                        if o and not o.get('__error__'):
                            inc['outcomes'].append(o)

                # Summary: merged lookup info (LocationId→location_name, DepartmentId→department_name, etc.)
                p = inc.get('person') or {}
                status_id = pi.get('StatusEnumId')
                status_meaning = STATUS_ENUM_MEANINGS.get(str(status_id)) if status_id is not None else None
                inc['summary'] = {
                    'staff_name': f"{p.get('FirstName', '')} {p.get('MiddleName', '')} {p.get('LastName', '')}".replace('  ', ' ').strip() or None,
                    'personnel_id': pi.get('PersonnelId'),
                    'location_name': _safe_name(inc.get('location'), 'Name'),
                    'department_name': _safe_name(inc.get('department'), 'Description', 'Name'),
                    'area_name': _safe_name(inc.get('area'), 'Description', 'Name'),
                    'status_meaning': status_meaning,
                    'risk_rating': _safe_name(inc.get('risk_rating'), 'Description'),
                    'date': pi.get('Date'),
                    'description': (pi.get('Description') or '')[:500],
                }

                result['personnel_incidents'].append(inc)

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def main():
    site = "Parafield Gardens"
    days = 30
    print(f"Fetching incidents for last {days} days at {site} [READ-ONLY]...", flush=True)
    result = query_incidents_yesterday(site, days=days)

    slug = site.lower().replace(' ', '_')
    date_str = result.get('date', 'last_30_days').replace('-', '')
    out_path = os.path.join(os.path.dirname(__file__), 'data', f'incidents_{date_str}_{slug}.json')
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=_json_serial)
    print(f"Wrote: {out_path}")

    if result.get('error'):
        print(f"Error: {result['error']}")
        sys.exit(1)

    ae_count = len(result.get('adverse_events', []))
    pi_count = len(result.get('personnel_incidents', []))
    print(f"\n--- Summary ---")
    print(f"Range: {result.get('date_from')} to {result.get('date_to')} | LocationIds: {result.get('location_ids')}")
    print(f"Client incidents (AdverseEvent): {ae_count}")
    print(f"Staff incidents (PersonnelIncident): {pi_count}")


if __name__ == '__main__':
    main()
