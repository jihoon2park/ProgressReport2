#!/usr/bin/env python3
"""
Debug test for incident sync
"""

import sys
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sync_specific_site():
    """Test sync for Parafield Gardens only"""
    try:
        sys.path.insert(0, '.')
        from api_incident import fetch_incidents_with_client_data
        from app import get_db_connection
        
        logger.info("=" * 60)
        logger.info("Testing Sync for Parafield Gardens - Incident 4938")
        logger.info("=" * 60)
        
        # Fetch data
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        logger.info(f"Fetching incidents from {start_date} to {end_date}")
        incidents_data = fetch_incidents_with_client_data('Parafield Gardens', start_date, end_date)
        
        if not incidents_data:
            logger.error("No data fetched!")
            return
        
        incidents = incidents_data.get('incidents', [])
        logger.info(f"Total incidents fetched: {len(incidents)}")
        
        # Find incident 4938
        incident_4938 = None
        for inc in incidents:
            if inc.get('Id') == 4938:
                incident_4938 = inc
                break
        
        if not incident_4938:
            logger.error("Incident 4938 not found in fetched data!")
            return
        
        logger.info(f"Found incident 4938:")
        logger.info(f"  ID: {incident_4938.get('Id')}")
        logger.info(f"  Date: {incident_4938.get('Date')}")
        logger.info(f"  Resident: {incident_4938.get('FirstName')} {incident_4938.get('LastName')}")
        logger.info(f"  Type: {incident_4938.get('EventTypeNames')}")
        logger.info(f"  Status: {incident_4938.get('Status')}")
        logger.info(f"  Description: {incident_4938.get('Description')[:50]}...")
        
        # Check if it exists in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, incident_id, status FROM cims_incidents 
            WHERE manad_incident_id = ?
        """, ('4938',))
        
        existing = cursor.fetchone()
        if existing:
            logger.info(f"Incident 4938 EXISTS in database:")
            logger.info(f"  DB ID: {existing[0]}")
            logger.info(f"  Incident ID: {existing[1]}")
            logger.info(f"  Status: {existing[2]}")
        else:
            logger.info("Incident 4938 DOES NOT exist in database - should be inserted")
        
        # Now test the full sync
        logger.info("\n" + "=" * 60)
        logger.info("Running full sync function...")
        logger.info("=" * 60)
        
        from app import sync_incidents_from_manad_to_cims
        result = sync_incidents_from_manad_to_cims()
        
        logger.info(f"Sync result: {result}")
        
        # Check again
        cursor.execute("""
            SELECT id, incident_id, resident_name, incident_type, status, manad_incident_id 
            FROM cims_incidents 
            WHERE manad_incident_id = '4938'
        """)
        
        result_after = cursor.fetchone()
        if result_after:
            logger.info(f"✅ Incident 4938 NOW EXISTS in database:")
            logger.info(f"  DB ID: {result_after[0]}")
            logger.info(f"  Incident ID: {result_after[1]}")
            logger.info(f"  Resident: {result_after[2]}")
            logger.info(f"  Type: {result_after[3]}")
            logger.info(f"  Status: {result_after[4]}")
            logger.info(f"  MANAD ID: {result_after[5]}")
        else:
            logger.error("❌ Incident 4938 STILL NOT in database after sync!")
        
        conn.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("Test completed")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sync_specific_site()

