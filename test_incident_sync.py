#!/usr/bin/env python3
"""
Test script to verify incident sync functionality
"""

import sys
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_incident_sync():
    """Test the incident sync from MANAD to CIMS"""
    try:
        # Import the sync function
        sys.path.insert(0, '.')
        from app import sync_incidents_from_manad_to_cims, get_db_connection
        
        logger.info("=" * 60)
        logger.info("Testing Incident Sync from MANAD API to CIMS Database")
        logger.info("=" * 60)
        
        # Check current incident count
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM cims_incidents WHERE status = 'Open'")
        before_count = cursor.fetchone()[0]
        logger.info(f"Current Open incidents in CIMS database: {before_count}")
        
        # Get some sample incidents to display
        cursor.execute("""
            SELECT incident_id, resident_name, incident_type, incident_date, site
            FROM cims_incidents 
            WHERE status = 'Open'
            ORDER BY incident_date DESC
            LIMIT 5
        """)
        
        before_incidents = cursor.fetchall()
        logger.info("\nCurrent Open Incidents (Top 5):")
        for inc in before_incidents:
            logger.info(f"  - ID: {inc[0]}, Resident: {inc[1]}, Type: {inc[2]}, Date: {inc[3]}, Site: {inc[4]}")
        
        conn.close()
        
        # Run the sync
        logger.info("\n" + "=" * 60)
        logger.info("Running sync_incidents_from_manad_to_cims()...")
        logger.info("=" * 60)
        
        result = sync_incidents_from_manad_to_cims()
        
        logger.info("\n" + "=" * 60)
        logger.info("Sync Result:")
        logger.info(f"  Success: {result.get('success', False)}")
        logger.info(f"  New incidents synced: {result.get('synced', 0)}")
        logger.info(f"  Incidents updated: {result.get('updated', 0)}")
        
        if 'error' in result:
            logger.error(f"  Error: {result['error']}")
        
        # Check after sync
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM cims_incidents WHERE status = 'Open'")
        after_count = cursor.fetchone()[0]
        logger.info(f"\nOpen incidents after sync: {after_count}")
        logger.info(f"Change: {after_count - before_count:+d}")
        
        # Get updated incidents
        cursor.execute("""
            SELECT incident_id, resident_name, incident_type, incident_date, site, manad_incident_id
            FROM cims_incidents 
            WHERE status = 'Open'
            ORDER BY incident_date DESC
            LIMIT 10
        """)
        
        after_incidents = cursor.fetchall()
        logger.info("\nOpen Incidents after sync (Top 10):")
        for inc in after_incidents:
            logger.info(f"  - ID: {inc[0]}, Resident: {inc[1]}, Type: {inc[2]}, Date: {inc[3]}, Site: {inc[4]}, MANAD ID: {inc[5]}")
        
        # Check for the specific incident mentioned by user (Marlene Hughes)
        cursor.execute("""
            SELECT incident_id, resident_name, incident_type, incident_date, site, description, manad_incident_id
            FROM cims_incidents 
            WHERE resident_name LIKE '%Marlene%Hughes%' OR resident_name LIKE '%Hughes%'
            ORDER BY incident_date DESC
            LIMIT 5
        """)
        
        marlene_incidents = cursor.fetchall()
        if marlene_incidents:
            logger.info("\n" + "=" * 60)
            logger.info("Found incidents for Marlene Hughes:")
            for inc in marlene_incidents:
                logger.info(f"  - ID: {inc[0]}")
                logger.info(f"    Resident: {inc[1]}")
                logger.info(f"    Type: {inc[2]}")
                logger.info(f"    Date: {inc[3]}")
                logger.info(f"    Site: {inc[4]}")
                logger.info(f"    Description: {inc[5][:100]}...")
                logger.info(f"    MANAD ID: {inc[6]}")
                logger.info("")
        else:
            logger.warning("\n⚠️  No incidents found for Marlene Hughes")
            logger.info("This may mean:")
            logger.info("  1. The incident hasn't been synced yet (check date range)")
            logger.info("  2. The incident might be in incident-viewer but not yet in MANAD API")
            logger.info("  3. The name might be stored differently in the API")
        
        conn.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("Test completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_incident_sync()

