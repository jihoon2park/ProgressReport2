#!/usr/bin/env python3
"""
Query a single ProgressNote by Id and return ALL columns from ALL related tables.

Usage:
    python query_progress_note_full.py <progress_note_id> [site_name]
    python query_progress_note_full.py 335325 "Parafield Gardens"

Output: JSON with full rows from: ProgressNote, Client, Person, ClientService,
        Wing, Location, ProgressNoteEventType, ProgressNoteRiskRating,
        ProgressNoteBatch, Personnel (created_by), ProgressNoteDetail(s),
        ProgressNote_CareArea + CareArea (full), ProgressNote_RiskCategory,
        MpsObject_ProgressNote.
"""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _json_serial(obj):
    if isinstance(obj, datetime):
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
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, bytes):
        return '<binary>'
    if isinstance(val, Decimal):
        return float(val)
    return val


def _row_to_dict(cursor, row):
    """Convert a DB row to dict with proper serialization."""
    cols = [c[0] for c in cursor.description]
    return {cols[i]: _serialize_val(row[i]) if i < len(row) else None for i in range(len(cols))}


def _fetch_one(cursor, table: str, id_col: str, id_val) -> dict | None:
    """SELECT * FROM table WHERE id_col = ?; return first row as dict or None."""
    try:
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{id_col}] = ?", (id_val,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row) if row else None
    except Exception as e:
        return {'__error__': str(e)}


def _fetch_many(cursor, table: str, filter_col: str, filter_val) -> list:
    """SELECT * FROM table WHERE filter_col = ?; return all rows as dicts."""
    try:
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{filter_col}] = ?", (filter_val,))
        return [_row_to_dict(cursor, r) for r in cursor.fetchall()]
    except Exception as e:
        return [{'__error__': str(e)}]


def query_progress_note_full(progress_note_id: int, site: str = "Parafield Gardens") -> dict:
    """Fetch ProgressNote and ALL columns from ALL related tables."""
    from manad_db_connector import MANADDBConnector

    connector = MANADDBConnector(site)
    result = {
        'progress_note_id': progress_note_id,
        'site': site,
        'queried_at': datetime.now().isoformat(),
        'progress_note': None,
        'client': None,
        'person': None,
        'client_service': None,
        'wing': None,
        'location': None,
        'event_type': None,
        'risk_rating': None,
        'batch': None,
        'created_by_personnel': None,
        'created_by_person': None,
        'details': [],
        'care_area_links': [],
        'care_areas_full': [],
        'risk_category_links': [],
        'mps_objects': [],
        'error': None,
    }

    try:
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            pid = progress_note_id

            # 1. ProgressNote - full row
            pn = _fetch_one(cursor, 'ProgressNote', 'Id', pid)
            if not pn or pn.get('__error__'):
                result['error'] = pn.get('__error__', f'ProgressNote Id={pid} not found')
                return result

            result['progress_note'] = pn
            client_id = pn.get('ClientId')
            client_service_id = pn.get('ClientServiceId')
            event_type_id = pn.get('ProgressNoteEventTypeId')
            risk_rating_id = pn.get('ProgressNoteRiskRatingId')
            batch_id = pn.get('BatchId')
            created_by_user_id = pn.get('CreatedByUserId')

            # 2. Client - full row
            if client_id:
                result['client'] = _fetch_one(cursor, 'Client', 'Id', client_id)
                person_id = result['client'].get('PersonId') if result['client'] and not result['client'].get('__error__') else None
            else:
                person_id = None

            # 3. Person (resident) - full row
            if person_id:
                result['person'] = _fetch_one(cursor, 'Person', 'Id', person_id)

            # 4. ClientService - full row
            if client_service_id:
                cs = _fetch_one(cursor, 'ClientService', 'Id', client_service_id)
                result['client_service'] = cs
                wing_id = cs.get('WingId') if cs and not cs.get('__error__') else None
                location_id = cs.get('LocationId') if cs and not cs.get('__error__') else None
            else:
                wing_id, location_id = None, None

            # 5. Wing - full row
            if wing_id:
                result['wing'] = _fetch_one(cursor, 'Wing', 'Id', wing_id)

            # 6. Location - full row
            if location_id:
                result['location'] = _fetch_one(cursor, 'Location', 'Id', location_id)

            # 7. ProgressNoteEventType - full row
            if event_type_id:
                result['event_type'] = _fetch_one(cursor, 'ProgressNoteEventType', 'Id', event_type_id)

            # 8. ProgressNoteRiskRating - full row (nullable)
            if risk_rating_id:
                result['risk_rating'] = _fetch_one(cursor, 'ProgressNoteRiskRating', 'Id', risk_rating_id)

            # 9. ProgressNoteBatch - full row (nullable)
            if batch_id:
                result['batch'] = _fetch_one(cursor, 'ProgressNoteBatch', 'Id', batch_id)

            # 10. CreatedBy - Personnel (staff) + Person for name
            if created_by_user_id:
                result['created_by_personnel'] = _fetch_one(cursor, 'Personnel', 'Id', created_by_user_id)
                if result['created_by_personnel'] and not result['created_by_personnel'].get('__error__'):
                    staff_person_id = result['created_by_personnel'].get('PersonId')
                    if staff_person_id:
                        result['created_by_person'] = _fetch_one(cursor, 'Person', 'Id', staff_person_id)

            # 11. ProgressNoteDetail - all rows, full columns
            result['details'] = _fetch_many(cursor, 'ProgressNoteDetail', 'ProgressNoteId', pid)

            # 12. ProgressNote_CareArea - all links, then full CareArea for each
            result['care_area_links'] = _fetch_many(cursor, 'ProgressNote_CareArea', 'ProgressNoteId', pid)
            care_area_ids = []
            for link in result['care_area_links']:
                if link and not link.get('__error__') and link.get('CareAreaId'):
                    care_area_ids.append(link['CareAreaId'])
            for ca_id in care_area_ids:
                ca = _fetch_one(cursor, 'CareArea', 'Id', ca_id)
                if ca and not ca.get('__error__'):
                    result['care_areas_full'].append(ca)

            # 13. ProgressNote_RiskCategory - all links
            result['risk_category_links'] = _fetch_many(cursor, 'ProgressNote_RiskCategory', 'ProgressNoteId', pid)

            # 14. MpsObject_ProgressNote - all links
            result['mps_objects'] = _fetch_many(cursor, 'MpsObject_ProgressNote', 'ProgressNoteId', pid)

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python query_progress_note_full.py <progress_note_id> [site_name]")
        print("Example: python query_progress_note_full.py 335325 \"Parafield Gardens\"")
        sys.exit(1)

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print("Error: progress_note_id must be an integer")
        sys.exit(1)

    site = sys.argv[2] if len(sys.argv) > 2 else "Parafield Gardens"

    print(f"Querying ProgressNote Id={pid} for site={site} (full rows from all related tables)...")
    result = query_progress_note_full(pid, site)

    out_path = os.path.join(os.path.dirname(__file__), 'data', f'progress_note_{pid}_full.json')
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=_json_serial)
    print(f"Wrote: {out_path}")

    if result.get('error'):
        print(f"Error: {result['error']}")
        sys.exit(1)

    # Summary
    pn = result.get('progress_note', {})
    person = result.get('person', {})
    print("\n--- Summary ---")
    print(f"ProgressNote: {pn.get('Id')} | Date: {pn.get('Date')}")
    print(f"Client/Person: {person.get('FirstName', '')} {person.get('LastName', '')}")
    print(f"Event Type: {result.get('event_type', {}).get('Description', 'N/A')}")
    print(f"Details: {len(result.get('details', []))} | Care Areas: {len(result.get('care_areas_full', []))}")
    print(f"Risk Category links: {len(result.get('risk_category_links', []))} | MPS: {len(result.get('mps_objects', []))}")


if __name__ == '__main__':
    main()
