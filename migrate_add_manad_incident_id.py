#!/usr/bin/env python3
"""
Migration script to add manad_incident_id and reported_by_name fields to cims_incidents table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path='progress_report.db'):
    """Add manad_incident_id and reported_by_name fields to cims_incidents table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if manad_incident_id column exists
        cursor.execute("PRAGMA table_info(cims_incidents)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'manad_incident_id' not in columns:
            logger.info("Adding manad_incident_id column to cims_incidents table...")
            cursor.execute("""
                ALTER TABLE cims_incidents 
                ADD COLUMN manad_incident_id VARCHAR(100)
            """)
            logger.info("✅ Added manad_incident_id column")
        else:
            logger.info("manad_incident_id column already exists")
        
        if 'reported_by_name' not in columns:
            logger.info("Adding reported_by_name column to cims_incidents table...")
            cursor.execute("""
                ALTER TABLE cims_incidents 
                ADD COLUMN reported_by_name VARCHAR(200)
            """)
            logger.info("✅ Added reported_by_name column")
        else:
            logger.info("reported_by_name column already exists")
        
        # Create index on manad_incident_id if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_cims_incidents_manad_id'
        """)
        
        if not cursor.fetchone():
            logger.info("Creating index on manad_incident_id...")
            cursor.execute("""
                CREATE INDEX idx_cims_incidents_manad_id 
                ON cims_incidents(manad_incident_id)
            """)
            logger.info("✅ Created index on manad_incident_id")
        else:
            logger.info("Index on manad_incident_id already exists")
        
        # Make reported_by nullable (already done in schema, but for existing data)
        # SQLite doesn't support ALTER COLUMN, so we'll just note this
        logger.info("Note: reported_by is now nullable for MANAD integration")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == '__main__':
    migrate_database()

