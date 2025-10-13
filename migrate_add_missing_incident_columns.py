#!/usr/bin/env python3
"""
Migration script to add missing columns to cims_incidents table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path='progress_report.db'):
    """Add missing columns to cims_incidents table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current columns
        cursor.execute("PRAGMA table_info(cims_incidents)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"Current columns: {columns}")
        
        # Add missing columns
        # Note: SQLite doesn't support DEFAULT CURRENT_TIMESTAMP in ALTER TABLE
        missing_columns = {
            'initial_actions_taken': 'TEXT',
            'witnesses': 'TEXT',
            'policy_applied': 'INTEGER',
            'updated_at': 'TIMESTAMP'
        }
        
        for col_name, col_type in missing_columns.items():
            if col_name not in columns:
                logger.info(f"Adding column {col_name}...")
                cursor.execute(f"""
                    ALTER TABLE cims_incidents 
                    ADD COLUMN {col_name} {col_type}
                """)
                logger.info(f"✅ Added {col_name} column")
            else:
                logger.info(f"{col_name} column already exists")
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == '__main__':
    migrate_database()

