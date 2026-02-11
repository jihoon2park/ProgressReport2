#!/usr/bin/env python3
"""
Query ALL client-related data for a Progress Note record.
READ-ONLY: SELECT queries only - no INSERT, UPDATE, DELETE.

Uses ProgressNote ID to resolve ClientId, ClientServiceId, PersonId, then fetches
related tables: client details, care documents, medical/clinical, risk scales,
ACFI/complex health care, diagnoses, questionnaires, etc.

Usage:
    python query_client_full.py <progress_note_id> [site_name]
    python query_client_full.py 335324 "Parafield Gardens"

Output: data/client_full_<progress_note_id>.json
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


# Max rows per table to avoid slow queries (READ-ONLY, no data modification)
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
    """WHERE col1=? AND col2=? for composite keys. READ-ONLY."""
    try:
        cols = list(filters.keys())
        vals = [filters[c] for c in cols]
        where = ' AND '.join(f'[{c}] = ?' for c in cols)
        cursor.execute(f"SELECT TOP ({limit}) * FROM [{table}] WHERE {where}", vals)
        return [_row_to_dict(cursor, r) for r in cursor.fetchall()]
    except Exception as e:
        return [{'__error__': str(e)}]


# Schema cache: load from dump to avoid 100+ INFORMATION_SCHEMA queries
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

# Heavy tables to SKIP (audit logs, transactions, finance - can have 10k+ rows per client)
# READ-ONLY script - we only SELECT; these are skipped for speed
SKIP_TABLES = {
    'AuditLog', 'Charge', 'Invoice', 'AssignedCreditNoteAllocation', 'AssignedReceiptAllocation',
    'EpicorTransaction', 'InervaTransaction', 'MedSigTransaction', 'MpsTransaction', 'OneviewTransaction',
    'Message', 'HiServiceLog', 'MhrUploadLog', 'TaskWorkflow',
}

# Quick mode: only these tables (client details, medical, care docs, risk, ACFI)
QUICK_TABLES = [
    'ClientCareDocument', 'ClientDiagnosis', 'MedicalConditionDiagnosis', 'AcfiAppraisal', 'AcfiRcsAppraisal',
    'QuestionnaireResponse', 'ClientRiskScale', 'ClientContact', 'ClientDocument', 'ClinicalRange',
    'ProgressNoteDetail', 'ProgressNote_CareArea', 'ProgressNote_RiskCategory',
]

# All tables with ClientId and/or ClientServiceId (from schema analysis - 113 tables)
# Exclude: Client, ClientService (fetched separately), ProgressNote (entry point)
TABLES_CLIENT_OR_SERVICE = [
    'AccommodationAgreement', 'AcfiAppraisal', 'AcfiRcsAppraisal', 'ActivityEventAttendee', 'AdverseEvent',
    'Alert', 'AlertRule_FilterClient', 'Anacc', 'ArgusMessage', 'AssetRegister', 'AssignedCreditNoteAllocation',
    'AssignedReceiptAllocation', 'AuditLog', 'Behaviour', 'Bladder', 'BloodGlucoseLevel', 'BodyMeasurement',
    'BowelManagement', 'BowelMonitoring', 'CareMeasure', 'CaseConference', 'Charge', 'ChargeBatchRateList',
    'ClientAccommodationAgreement', 'ClientAcwsServiceCorrespondence', 'ClientAssetAssessment', 'ClientCard',
    'ClientCareDocument', 'ClientConsumerExperience', 'ClientContact', 'ClientCorrespondence', 'ClientDiagnosis',
    'ClientDocument', 'ClientExternalLocation', 'ClientExtraService', 'ClientForward_ClientContact', 'ClientLeave',
    'ClientNotification', 'ClientPettyCashFund', 'ClientVehicle', 'Client_Hcp', 'Client_MedicalPractice',
    'Client_Pharmacy', 'Client_SpiritualAdvisor', 'ClinicalRange', 'ComfortCare', 'ComplianceAudit_Client',
    'ConferenceDiscussionItem', 'DayCareVisit', 'EpicorTransaction', 'Feedback_Client', 'FinanceSupplement',
    'FoodAndFluid', 'HbA1c', 'HiServiceLog', 'HomeCare', 'InervaTransaction', 'Infection', 'InfectionFollowUp',
    'Inr', 'Invoice', 'Maintenance', 'MedSigTransaction', 'MedicalConditionDiagnosis', 'MedicareEvent',
    'MedicationTiming', 'Message', 'MhrUploadLog', 'MpsTransaction', 'NeuroObservation', 'NeurovascularObservation',
    'Notice', 'Observation', 'Occupancy', 'OneviewTransaction', 'Ostomy', 'Outing', 'OxygenSaturation',
    'Pain', 'PainFollowUp', 'PalliativeSymptom', 'PeakFlow', 'PegNgt', 'PersonalHygiene', 'PersonnelIncident',
    'ProgressNote_Staging', 'QuestionnaireResponse', 'QuestionnaireResponseQuestion_Client', 'Repositioning',
    'Residency', 'RespiteBooking', 'Restraint', 'RestraintFollowUp', 'Service', 'Sighting', 'Sleep',
    'SundryItem', 'Supplement', 'SurgicalProcedure', 'Task', 'TaskWorkflow', 'Task_RegardingClient',
    'Therapy', 'UnexplainedAbsence', 'Urinalysis', 'Urostomy', 'Vaccination', 'Waiting', 'Weight',
    'Wound', 'WoundFollowUp',
]

# Tables with PersonId (for resident - from Client.PersonId)
TABLES_PERSON_ID = [
    'Client', 'ClientContact', 'Person',
]

# Child tables: (parent_table, parent_id_col) -> list of (child_table, child_fk_col)
CHILD_TABLES = [
    # AcfiAppraisal -> ACFI sub-tables (Complex Health Care, etc.)
    ('AcfiAppraisal', 'Id', 'AcfiAppraisalId', [
        'AcfiCognitiveSkill', 'AcfiComplexHealthCare', 'AcfiContinence', 'AcfiDepression', 'AcfiMedication',
        'AcfiMobility', 'AcfiNutrition', 'AcfiPersonalHygiene', 'AcfiPhysicalBehaviour', 'AcfiToileting',
        'AcfiVerbalBehaviour', 'AcfiWandering',
    ]),
    # ClientDiagnosis -> diagnosis details
    ('ClientDiagnosis', 'Id', 'ClientDiagnosisId', [
        'ClientDiagnosis_MedicalCondition', 'ClientDiagnosis_MedicareDiagnosisSource',
    ]),
    # MedicalConditionDiagnosis -> condition details
    ('MedicalConditionDiagnosis', 'Id', 'MedicalConditionDiagnosisId', [
        'MedicalConditionDiagnosis_MedicalConditionCondition', 'MedicalConditionDiagnosis_MedicalConditionSource',
    ]),
    # QuestionnaireResponse -> risk scales, questionnaire answers
    ('QuestionnaireResponse', 'Id', 'QuestionnaireResponseId', [
        'QuestionnaireResponseQuestion', 'ClientRiskScale',
    ]),
    # QuestionnaireResponseQuestion -> linked items
    ('QuestionnaireResponseQuestion', 'Id', 'QuestionnaireResponseQuestionId', [
        'QuestionnaireResponseQuestionLinkedItem', 'QuestionnaireResponseQuestionReferenceItem',
        'QuestionnaireResponseQuestion_ClientCareDocument', 'QuestionnaireResponseQuestion_Client',
    ]),
    # ClientCareDocument -> care plans (care documents)
    ('ClientCareDocument', 'Id', 'ParentClientCareDocumentId', ['ClientCareDocument']),  # nested docs
    ('ClientCareDocument', 'Id', 'ParentClientCareDocumentId', ['ClientCarePlan']),
    # ClientCarePlan -> intervention/need items
    ('ClientCarePlan', 'Id', 'ClientCarePlanId', [
        'ClientCarePlanInterventionItem', 'ClientCarePlanNeedItem',
    ]),
]

# ProgressNote-specific tables
TABLES_PROGRESS_NOTE_ID = [
    ('ProgressNoteDetail', 'ProgressNoteId'),
    ('ProgressNote_CareArea', 'ProgressNoteId'),
    ('ProgressNote_RiskCategory', 'ProgressNoteId'),
    ('MpsObject_ProgressNote', 'ProgressNoteId'),
]

# Lookup/reference tables to enrich (optional - can add later)
# For now we focus on client data tables


def query_client_full(progress_note_id: int, site: str = "Parafield Gardens", verbose: bool = True, quick: bool = False) -> dict:
    """Fetch ALL client-related data for a Progress Note."""
    from manad_db_connector import MANADDBConnector

    connector = MANADDBConnector(site)
    result = {
        'progress_note_id': progress_note_id,
        'site': site,
        'queried_at': datetime.now().isoformat(),
        'client_id': None,
        'client_service_id': None,
        'person_id': None,
        'progress_note': None,
        'client': None,
        'person': None,
        'client_service': None,
        'tables': {},
        'error': None,
    }

    schema_cache = _load_schema_cache()

    try:
        if verbose:
            print("Connecting (READ-ONLY)...", flush=True)
        with connector.get_connection() as conn:
            cursor = conn.cursor()
            pid = progress_note_id

            # 1. ProgressNote (READ-ONLY SELECT)
            if verbose:
                print("  ProgressNote...", flush=True)
            pn = _fetch_one(cursor, 'ProgressNote', 'Id', pid)
            if not pn or pn.get('__error__'):
                result['error'] = pn.get('__error__', f'ProgressNote Id={pid} not found')
                return result

            result['progress_note'] = pn
            client_id = pn.get('ClientId')
            client_service_id = pn.get('ClientServiceId')

            if not client_id or not client_service_id:
                result['error'] = f'ProgressNote has no ClientId or ClientServiceId'
                return result

            result['client_id'] = client_id
            result['client_service_id'] = client_service_id

            # 2. Client -> PersonId
            client = _fetch_one(cursor, 'Client', 'Id', client_id)
            result['client'] = client
            person_id = client.get('PersonId') if client and not client.get('__error__') else None
            result['person_id'] = person_id

            # 3. Person
            if person_id:
                result['person'] = _fetch_one(cursor, 'Person', 'Id', person_id)

            # 4. ClientService
            result['client_service'] = _fetch_one(cursor, 'ClientService', 'Id', client_service_id)

            # 5. All tables with ClientId and/or ClientServiceId
            tables_to_query = QUICK_TABLES if quick else TABLES_CLIENT_OR_SERVICE
            for tbl in tables_to_query:
                if tbl in ('Client', 'ClientService', 'ProgressNote') or tbl in SKIP_TABLES:
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
                if has_c and has_cs:
                    rows = _fetch_many_multi(cursor, tbl, {'ClientId': client_id, 'ClientServiceId': client_service_id})
                elif has_c:
                    rows = _fetch_many(cursor, tbl, 'ClientId', client_id)
                elif has_cs:
                    rows = _fetch_many(cursor, tbl, 'ClientServiceId', client_service_id)
                else:
                    continue
                if rows:
                    result['tables'][tbl] = rows

            # 6. ProgressNote-specific tables
            for tbl, fk_col in TABLES_PROGRESS_NOTE_ID:
                if verbose:
                    print(f"  {tbl}...", flush=True)
                rows = _fetch_many(cursor, tbl, fk_col, pid)
                if rows:
                    result['tables'][tbl] = rows

            # 7. Child tables (ACFI, diagnosis, care docs, risk scales) - skip in quick mode
            if not quick:
                if verbose:
                    print("  Child tables (ACFI, diagnosis, care docs)...", flush=True)
                _fetch_child_tables(cursor, result, client_id, client_service_id, verbose=verbose)

            # 8. CareArea for ProgressNote_CareArea links
            for link in result['tables'].get('ProgressNote_CareArea', []):
                if link and not link.get('__error__') and link.get('CareAreaId'):
                    ca = _fetch_one(cursor, 'CareArea', 'Id', link['CareAreaId'])
                    if ca and not ca.get('__error__'):
                        result['tables'].setdefault('CareArea', []).append(ca)

            # 9. Wing, Location, EventType, Address, ContactDetail (reference data)
            cs = result.get('client_service')
            if cs and not cs.get('__error__'):
                for ref_tbl, id_col, fk in [
                    ('Wing', 'Id', 'WingId'),
                    ('Location', 'Id', 'LocationId'),
                ]:
                    ref_id = cs.get(fk)
                    if ref_id:
                        row = _fetch_one(cursor, ref_tbl, id_col, ref_id)
                        if row and not row.get('__error__'):
                            result['tables'][f'ref_{ref_tbl}'] = [row]

            if pn.get('ProgressNoteEventTypeId'):
                result['tables']['ref_ProgressNoteEventType'] = [
                    _fetch_one(cursor, 'ProgressNoteEventType', 'Id', pn['ProgressNoteEventTypeId']) or {}
                ]

            # 10. Person Address, ContactDetail (client/resident details)
            person = result.get('person')
            if person and not person.get('__error__'):
                for ref_tbl, id_col, fk in [
                    ('Address', 'Id', 'AddressId'),
                    ('Address', 'Id', 'MailingAddressId'),
                    ('ContactDetail', 'Id', 'ContactDetailId'),
                ]:
                    ref_id = person.get(fk)
                    if ref_id:
                        row = _fetch_one(cursor, ref_tbl, id_col, ref_id)
                        if row and not row.get('__error__'):
                            result['tables'].setdefault(f'ref_{ref_tbl}', []).append(row)

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return result


def _get_table_schema(cursor, table: str) -> Optional[list]:
    try:
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION", (table,))
        return [r[0] for r in cursor.fetchall()]
    except Exception:
        return None


def _fetch_child_tables(cursor, result: dict, client_id: int, client_service_id: int, verbose: bool = False):
    """Fetch child tables based on parent IDs from already-fetched data."""
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

    # QuestionnaireResponse -> QuestionnaireResponseQuestion, ClientRiskScale
    for row in result['tables'].get('QuestionnaireResponse', []):
        if row and not row.get('__error__') and row.get('Id'):
            qr_id = row['Id']
            for child, fk in [('QuestionnaireResponseQuestion', 'QuestionnaireResponseId'),
                              ('ClientRiskScale', 'QuestionnaireResponseId')]:
                rows = _fetch_many(cursor, child, fk, qr_id)
                if rows:
                    result['tables'].setdefault(child, []).extend(rows)

    # QuestionnaireResponseQuestion -> linked items, reference items
    for row in result['tables'].get('QuestionnaireResponseQuestion', []):
        if row and not row.get('__error__') and row.get('Id'):
            qrq_id = row['Id']
            for child, fk in [('QuestionnaireResponseQuestionLinkedItem', 'QuestionnaireResponseQuestionId'),
                              ('QuestionnaireResponseQuestionReferenceItem', 'QuestionnaireResponseQuestionId'),
                              ('QuestionnaireResponseQuestion_ClientCareDocument', 'QuestionnaireResponseQuestionId'),
                              ('QuestionnaireResponseQuestion_Client', 'QuestionnaireResponseQuestionId')]:
                rows = _fetch_many(cursor, child, fk, qrq_id)
                if rows:
                    result['tables'].setdefault(child, []).extend(rows)

    # ClientCareDocument -> ClientCarePlan, nested ClientCareDocument
    ccd_ids = []
    for row in result['tables'].get('ClientCareDocument', []):
        if row and not row.get('__error__') and row.get('Id'):
            ccd_ids.append(row['Id'])

    for ccd_id in ccd_ids:
        # ClientCarePlan (ParentClientCareDocumentId = ClientCareDocument.Id)
        plans = _fetch_many(cursor, 'ClientCarePlan', 'ParentClientCareDocumentId', ccd_id)
        for plan in plans:
            if plan and not plan.get('__error__') and plan.get('Id'):
                for child, fk in [('ClientCarePlanInterventionItem', 'ClientCarePlanId'),
                                  ('ClientCarePlanNeedItem', 'ClientCarePlanId')]:
                    rows = _fetch_many(cursor, child, fk, plan['Id'])
                    if rows:
                        result['tables'].setdefault(child, []).extend(rows)
        if plans:
            result['tables'].setdefault('ClientCarePlan', []).extend(plans)

    # Nested ClientCareDocument (children of root care docs)
    for ccd_id in ccd_ids:
        children = _fetch_many(cursor, 'ClientCareDocument', 'ParentClientCareDocumentId', ccd_id)
        if children:
            result['tables'].setdefault('ClientCareDocument_children', []).extend(children)


def main():
    if len(sys.argv) < 2:
        print("Usage: python query_client_full.py <progress_note_id> [site_name] [--full]")
        print("Example: python query_client_full.py 335324 \"Parafield Gardens\"")
        print("  Default: quick mode (core tables only, ~3 sec). Use --full for all 100+ tables.")
        sys.exit(1)

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print("Error: progress_note_id must be an integer")
        sys.exit(1)

    args = sys.argv[2:]
    site = args[0] if args and not args[0].startswith('--') else "Parafield Gardens"
    full_mode = '--full' in args
    quick = not full_mode

    print(f"Querying client data for ProgressNote Id={pid} (site={site}) [READ-ONLY]...", flush=True)
    if full_mode:
        print("Full mode: all tables", flush=True)
    result = query_client_full(pid, site, verbose=True, quick=quick)

    out_path = os.path.join(os.path.dirname(__file__), 'data', f'client_full_{pid}.json')
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
    tables = result.get('tables', {})
    print("\n--- Summary ---")
    print(f"ProgressNote: {pn.get('Id')} | Date: {pn.get('Date')}")
    print(f"Client: {result.get('client_id')} | ClientService: {result.get('client_service_id')} | Person: {result.get('person_id')}")
    print(f"Name: {person.get('FirstName', '')} {person.get('LastName', '')}")
    print(f"Tables with data: {len(tables)}")
    for k in sorted(tables.keys()):
        n = len(tables[k]) if isinstance(tables[k], list) else 1
        print(f"  - {k}: {n} row(s)")


if __name__ == '__main__':
    main()
