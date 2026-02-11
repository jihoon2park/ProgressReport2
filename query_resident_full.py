#!/usr/bin/env python3
"""
Query resident (client) full information - trimmed for Residents tab.
READ-ONLY: SELECT queries only - no INSERT, UPDATE, DELETE.

Excludes: ref_Address, ref_ContactDetail, Residency, Restraint, RestraintFollowUp, Sleep,
  Therapy, Vaccination, Notice, NeuroObservation, InfectionFollowUp, Infection, ClientCareDocument,
  QuestionnaireResponse, FinanceSupplement, Observation, person_photo, photo_file, etc.

Includes: Client, Person, ClientService (with WingName, LocationName), emergency_contacts (joined
  ClientContact + Person + ContactDetail + ContactRelationshipType for name, phone, email),
  and other core resident tables.

Usage:
    python query_resident_full.py <client_id> [site_name]
    python query_resident_full.py 1256 "Parafield Gardens"

Output: data/resident_full_<client_id>.json
"""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

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
    cols = [c[0] for c in cursor.description]
    return {cols[i]: _serialize_val(row[i]) if i < len(row) else None for i in range(len(cols))}


def _fetch_one(cursor, table: str, id_col: str, id_val) -> Optional[dict]:
    try:
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{id_col}] = ?", (id_val,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row) if row else None
    except Exception as e:
        return {'__error__': str(e)}


MAX_ROWS_PER_TABLE = 500


def _fetch_many(cursor, table: str, filter_col: str, filter_val, limit: int = MAX_ROWS_PER_TABLE) -> list:
    try:
        cursor.execute(
            f"SELECT TOP ({limit}) * FROM [{table}] WHERE [{filter_col}] = ?",
            (filter_val,)
        )
        return [_row_to_dict(cursor, r) for r in cursor.fetchall()]
    except Exception as e:
        return [{'__error__': str(e)}]


def _fetch_many_multi(cursor, table: str, filters: dict, limit: int = MAX_ROWS_PER_TABLE) -> list:
    try:
        cols = list(filters.keys())
        vals = [filters[c] for c in cols]
        where = ' AND '.join(f'[{c}] = ?' for c in cols)
        cursor.execute(f"SELECT TOP ({limit}) * FROM [{table}] WHERE {where}", vals)
        return [_row_to_dict(cursor, r) for r in cursor.fetchall()]
    except Exception as e:
        return [{'__error__': str(e)}]


def _load_schema_cache() -> dict:
    path = os.path.join(os.path.dirname(__file__), 'data', 'manad_db_schema_sample.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        out = {}
        for key, val in data.get('tables', {}).items():
            tname = key.replace('dbo.', '')
            cols = [s['column'] for s in val.get('schema', [])]
            out[tname] = {'ClientId': 'ClientId' in cols, 'ClientServiceId': 'ClientServiceId' in cols}
        return out
    except Exception:
        return {}


# Tables to SKIP (heavy, audit, finance, or user-requested exclusions)
SKIP_TABLES = {
    'AuditLog', 'Charge', 'Invoice', 'AssignedCreditNoteAllocation', 'AssignedReceiptAllocation',
    'EpicorTransaction', 'InervaTransaction', 'MedSigTransaction', 'MpsTransaction', 'OneviewTransaction',
    'Message', 'HiServiceLog', 'MhrUploadLog', 'TaskWorkflow',
    # User-requested exclusions
    'QuestionnaireResponseQuestion', 'ClientRiskScale',
    'QuestionnaireResponseQuestion_ClientCareDocument', 'QuestionnaireResponseQuestionReferenceItem',
    'QuestionnaireResponseQuestionLinkedItem', 'ProgressNoteDetail', 'MedicareEvent', 'Maintenance',
    'Alert', 'Anacc', 'ActivityEventAttendee', 'Bladder', 'BloodGlucoseLevel', 'ClientConsumerExperience',
    # User-requested: remove these tables entirely
    'Residency', 'Restraint', 'RestraintFollowUp', 'Sleep', 'Therapy', 'Vaccination', 'Notice',
    'NeuroObservation', 'InfectionFollowUp', 'Infection', 'ClientCareDocument',
    'QuestionnaireResponse', 'FinanceSupplement', 'Observation',
    # ClientContact: fetched via JOIN as emergency_contacts
    'ClientContact',
    # User-requested: remove Client_Hcp, ClientDocument
    'Client_Hcp', 'ClientDocument',
}

# Maximum recent items to keep for array tables (last N items = most recent)
MAX_RECENT_ITEMS = 3

# Resident-relevant tables (ClientId and/or ClientServiceId) - EXCLUDING skip list
# ClientContact fetched via JOIN as emergency_contacts; ref_Address/ref_ContactDetail not stored
# Client_Hcp and ClientDocument removed per user request
TABLES_RESIDENT = [
    'AccommodationAgreement', 'AcfiAppraisal', 'AcfiRcsAppraisal', 'AdverseEvent',
    'AlertRule_FilterClient', 'ArgusMessage', 'AssetRegister', 'Behaviour', 'BodyMeasurement',
    'BowelManagement', 'BowelMonitoring', 'CareMeasure', 'CaseConference', 'ChargeBatchRateList',
    'ClientAccommodationAgreement', 'ClientAcwsServiceCorrespondence', 'ClientAssetAssessment', 'ClientCard',
    'ClientCorrespondence', 'ClientDiagnosis',
    'ClientExternalLocation', 'ClientExtraService', 'ClientForward_ClientContact', 'ClientLeave',
    'ClientNotification', 'ClientPettyCashFund', 'ClientVehicle', 'Client_MedicalPractice',
    'Client_Pharmacy', 'Client_SpiritualAdvisor', 'ClinicalRange', 'ComfortCare', 'ComplianceAudit_Client',
    'ConferenceDiscussionItem', 'DayCareVisit', 'Feedback_Client',
    'FoodAndFluid', 'HbA1c', 'HomeCare',
    'Inr', 'MedicationTiming', 'NeurovascularObservation',
    'Occupancy', 'Ostomy', 'Outing', 'OxygenSaturation',
    'Pain', 'PainFollowUp', 'PalliativeSymptom', 'PeakFlow', 'PegNgt', 'PersonalHygiene', 'PersonnelIncident',
    'ProgressNote_Staging', 'QuestionnaireResponseQuestion_Client', 'Repositioning',
    'RespiteBooking', 'Service', 'Sighting',
    'SundryItem', 'Supplement', 'SurgicalProcedure', 'Task', 'Task_RegardingClient',
    'UnexplainedAbsence', 'Urinalysis', 'Urostomy', 'Waiting', 'Weight',
    'Wound', 'WoundFollowUp',
]


def _get_table_schema(cursor, table: str) -> Optional[list]:
    try:
        cursor.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            (table,)
        )
        return [r[0] for r in cursor.fetchall()]
    except Exception:
        return None


def _trim_arrays_to_recent(tables: dict, max_items: int = MAX_RECENT_ITEMS) -> dict:
    """
    Trim all arrays in tables dict to keep only the most recent N items.
    The last item in each array is assumed to be the most recent.
    Returns new dict with trimmed arrays.
    """
    trimmed = {}
    for key, arr in tables.items():
        if isinstance(arr, list) and len(arr) > max_items:
            # Keep last N items (most recent = last)
            trimmed[key] = arr[-max_items:]
        else:
            trimmed[key] = arr
    return trimmed


def _sort_arrays_by_date_desc(tables: dict) -> dict:
    """
    Sort arrays that have a 'Date' field by Date descending (most recent first).
    Returns new dict with sorted arrays.
    """
    sorted_tables = {}
    for key, arr in tables.items():
        if not isinstance(arr, list) or len(arr) == 0:
            sorted_tables[key] = arr
            continue
        first = arr[0]
        if isinstance(first, dict) and 'Date' in first:
            sorted_arr = sorted(
                arr,
                key=lambda x: (x.get('Date') or '') if isinstance(x, dict) else '',
                reverse=True,
            )
            sorted_tables[key] = sorted_arr
        else:
            sorted_tables[key] = arr
    return sorted_tables


def _fetch_emergency_contacts(cursor, client_id: int) -> list:
    """Fetch ClientContact with JOINed Person, ContactDetail, ContactRelationshipType for full contact info."""
    try:
        cursor.execute("""
            SELECT
                cc.Id, cc.ClientId, cc.[Order], cc.Notes,
                crt.Description AS Relationship,
                ISNULL(p.PreferredName, '') AS ContactPreferredName,
                ISNULL(p.FirstName, '') AS ContactFirstName,
                ISNULL(p.LastName, '') AS ContactLastName,
                cd.MobilePhone, cd.AfterHoursPhone, cd.BusinessHoursPhone,
                cd.Email, cd.OtherPhone1, cd.OtherPhone2
            FROM ClientContact cc
            LEFT JOIN Person p ON cc.PersonId = p.Id
            LEFT JOIN ContactDetail cd ON p.ContactDetailId = cd.Id
            LEFT JOIN ContactRelationshipType crt ON cc.ContactRelationshipTypeId = crt.Id
            WHERE cc.ClientId = ? AND cc.IsDeleted = 0 AND cc.IsArchived = 0
            ORDER BY cc.[Order], cc.Id
        """, (client_id,))
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        out = []
        for r in rows:
            d = {cols[i]: _serialize_val(r[i]) if i < len(r) else None for i in range(len(cols))}
            # Build display name
            pref = (d.get('ContactPreferredName') or '').strip()
            first = (d.get('ContactFirstName') or '').strip()
            last = (d.get('ContactLastName') or '').strip()
            d['ContactName'] = pref if pref else f"{first} {last}".strip() or None
            out.append(d)
        return out
    except Exception as e:
        return [{'__error__': str(e)}]


def query_resident_full(client_id: int, site: str = "Parafield Gardens", verbose: bool = True) -> dict:
    """Fetch resident (client) full information - trimmed, with photo."""
    from manad_db_connector import MANADDBConnector

    connector = MANADDBConnector(site)
    result = {
        'client_id': client_id,
        'site': site,
        'queried_at': datetime.now().isoformat(),
        'client': None,
        'person': None,
        'client_service': None,
        'emergency_contacts': [],
        'tables': {},
        'error': None,
    }

    schema_cache = _load_schema_cache()

    try:
        if verbose:
            print("Connecting (READ-ONLY)...", flush=True)
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            cid = client_id

            # 1. Client
            if verbose:
                print("  Client...", flush=True)
            client = _fetch_one(cursor, 'Client', 'Id', cid)
            if not client or client.get('__error__'):
                result['error'] = client.get('__error__', f'Client Id={cid} not found')
                return result

            result['client'] = client
            person_id = client.get('PersonId')
            client_service_id = client.get('MainClientServiceId')

            # 2. Person
            if person_id:
                if verbose:
                    print("  Person...", flush=True)
                result['person'] = _fetch_one(cursor, 'Person', 'Id', person_id)

            # 3. ClientService (with Wing, Location names)
            if client_service_id:
                if verbose:
                    print("  ClientService...", flush=True)
                cs = _fetch_one(cursor, 'ClientService', 'Id', client_service_id)
                if cs and not cs.get('__error__'):
                    # Enrich with WingName, LocationName
                    for ref_tbl, id_col, fk, name_col in [
                        ('Wing', 'Id', 'WingId', 'Name'),
                        ('Location', 'Id', 'LocationId', 'Name'),
                    ]:
                        ref_id = cs.get(fk)
                        if ref_id:
                            row = _fetch_one(cursor, ref_tbl, id_col, ref_id)
                            if row and not row.get('__error__'):
                                cs[f'{ref_tbl}Name'] = row.get(name_col)
                    result['client_service'] = cs

            # 4. Emergency contacts (ClientContact JOIN Person, ContactDetail, ContactRelationshipType)
            if verbose:
                print("  Emergency contacts...", flush=True)
            result['emergency_contacts'] = _fetch_emergency_contacts(cursor, cid)

            # 7. ClientId / ClientServiceId tables (trimmed)
            for tbl in TABLES_RESIDENT:
                if tbl in SKIP_TABLES:
                    continue
                if verbose:
                    print(f"  {tbl}...", flush=True)
                if schema_cache:
                    sc = schema_cache.get(tbl, {})
                    has_c, has_cs = sc.get('ClientId', False), sc.get('ClientServiceId', False)
                else:
                    schema = _get_table_schema(cursor, tbl)
                    if not schema:
                        continue
                    has_c, has_cs = 'ClientId' in schema, 'ClientServiceId' in schema
                if not (has_c or has_cs):
                    continue
                if has_c and has_cs and client_service_id:
                    rows = _fetch_many_multi(
                        cursor, tbl, {'ClientId': cid, 'ClientServiceId': client_service_id}
                    )
                elif has_c:
                    rows = _fetch_many(cursor, tbl, 'ClientId', cid)
                elif has_cs and client_service_id:
                    rows = _fetch_many(cursor, tbl, 'ClientServiceId', client_service_id)
                else:
                    continue
                if rows:
                    result['tables'][tbl] = rows

            # 8. Child tables (ACFI, diagnosis) - NOT ClientCareDocument, NOT QuestionnaireResponse children
            if verbose:
                print("  Child tables (ACFI, diagnosis)...", flush=True)
            _fetch_resident_child_tables(cursor, result, cid, client_service_id, verbose=verbose)

            # 9. Trim arrays to most recent N items (last N = most recent)
            # Note: emergency_contacts is kept separately and NOT trimmed
            if verbose:
                print(f"  Trimming arrays to most recent {MAX_RECENT_ITEMS} items...", flush=True)
            result['tables'] = _trim_arrays_to_recent(result['tables'], MAX_RECENT_ITEMS)
            # 10. Sort arrays by Date descending (most recent first)
            if verbose:
                print("  Sorting arrays by date descending...", flush=True)
            result['tables'] = _sort_arrays_by_date_desc(result['tables'])

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def _fetch_resident_child_tables(cursor, result: dict, client_id: int, client_service_id: Optional[int],
                                  verbose: bool = False):
    """Fetch child tables - EXCLUDING QuestionnaireResponseQuestion, ClientRiskScale, etc."""
    # AcfiAppraisal
    acfi_ids = []
    for row in result['tables'].get('AcfiAppraisal', []):
        if row and not row.get('__error__') and row.get('Id'):
            acfi_ids.append(row['Id'])
    for aid in acfi_ids:
        for child in ['AcfiCognitiveSkill', 'AcfiComplexHealthCare', 'AcfiContinence', 'AcfiDepression',
                      'AcfiMedication', 'AcfiMobility', 'AcfiNutrition', 'AcfiPersonalHygiene',
                      'AcfiPhysicalBehaviour', 'AcfiToileting', 'AcfiVerbalBehaviour', 'AcfiWandering']:
            rows = _fetch_many(cursor, child, 'AcfiAppraisalId', aid)
            if rows:
                key = f'{child}_AcfiAppraisal_{aid}'
                result['tables'][key] = rows

    # ClientDiagnosis
    for row in result['tables'].get('ClientDiagnosis', []):
        if row and not row.get('__error__') and row.get('Id'):
            for child, fk in [('ClientDiagnosis_MedicalCondition', 'ClientDiagnosisId'),
                              ('ClientDiagnosis_MedicareDiagnosisSource', 'ClientDiagnosisId')]:
                rows = _fetch_many(cursor, child, fk, row['Id'])
                if rows:
                    result['tables'].setdefault(child, []).extend(rows)

    # MedicalConditionDiagnosis
    for row in result['tables'].get('MedicalConditionDiagnosis', []):
        if row and not row.get('__error__') and row.get('Id'):
            for child, fk in [('MedicalConditionDiagnosis_MedicalConditionCondition', 'MedicalConditionDiagnosisId'),
                              ('MedicalConditionDiagnosis_MedicalConditionSource', 'MedicalConditionDiagnosisId')]:
                rows = _fetch_many(cursor, child, fk, row['Id'])
                if rows:
                    result['tables'].setdefault(child, []).extend(rows)

    # QuestionnaireResponse - fetch only, NO children (QuestionnaireResponseQuestion, ClientRiskScale excluded)
    # ClientCareDocument - excluded per user request


def main():
    if len(sys.argv) < 2:
        print("Usage: python query_resident_full.py <client_id> [site_name]")
        print("Example: python query_resident_full.py 1256 \"Parafield Gardens\"")
        sys.exit(1)

    try:
        cid = int(sys.argv[1])
    except ValueError:
        print("Error: client_id must be an integer")
        sys.exit(1)

    args = sys.argv[2:]
    site = args[0] if args else "Parafield Gardens"

    print(f"Querying resident data for Client Id={cid} (site={site}) [READ-ONLY]...", flush=True)
    result = query_resident_full(cid, site, verbose=True)

    out_path = os.path.join(os.path.dirname(__file__), 'data', f'resident_full_{cid}.json')
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=_json_serial)
    print(f"Wrote: {out_path}")

    if result.get('error'):
        print(f"Error: {result['error']}")
        sys.exit(1)

    person = result.get('person', {})
    tables = result.get('tables', {})
    contacts = result.get('emergency_contacts', [])
    cs = result.get('client_service', {})
    print("\n--- Summary ---")
    print(f"Client: {result.get('client_id')} | Person: {result.get('person', {}).get('Id')}")
    print(f"Name: {person.get('FirstName', '')} {person.get('LastName', '')}")
    print(f"Wing: {cs.get('WingName', 'N/A')} | Location: {cs.get('LocationName', 'N/A')}")
    print(f"Emergency contacts: {len(contacts)}")
    print(f"Tables with data: {len(tables)}")
    for k in sorted(tables.keys())[:20]:
        n = len(tables[k]) if isinstance(tables[k], list) else 1
        print(f"  - {k}: {n} row(s)")
    if len(tables) > 20:
        print(f"  ... and {len(tables) - 20} more")


if __name__ == '__main__':
    main()
