#!/usr/bin/env python3
"""
CIMS Database Schema Migration Script
Automatically adds missing columns to the database on production servers.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

def check_column_exists(cursor, table_name, column_name):
    """Check if column exists"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    return column_name in column_names

def migrate_cims_incidents_table(db_path='progress_report.db'):
    """Add missing columns to cims_incidents table"""
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
        if not cursor.fetchone():
            # This is normal for new installations or environments where CIMS tables haven't been created yet.
            # Schema migration is for "adding missing columns", so skip if target table doesn't exist.
            logger.info("⏭️  Skipping migration: cims_incidents table does not exist")
            return True
        
        # List of columns to add (column_name, type, default_value)
        columns_to_add = [
            ('risk_rating', 'VARCHAR(50)', 'NULL'),
            ('is_review_closed', 'INTEGER', '0'),
            ('is_ambulance_called', 'INTEGER', '0'),
            ('is_admitted_to_hospital', 'INTEGER', '0'),
            ('is_major_injury', 'INTEGER', '0'),
            ('reviewed_date', 'TIMESTAMP', 'NULL'),
            ('status_enum_id', 'INTEGER', 'NULL'),
        ]
        
        added_columns = []
        for column_name, column_type, default_value in columns_to_add:
            if not check_column_exists(cursor, 'cims_incidents', column_name):
                try:
                    if default_value == 'NULL':
                        alter_sql = f"ALTER TABLE cims_incidents ADD COLUMN {column_name} {column_type}"
                    else:
                        alter_sql = f"ALTER TABLE cims_incidents ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                    
                    cursor.execute(alter_sql)
                    added_columns.append(column_name)
                    logger.info(f"✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    logger.error(f"❌ Failed to add column {column_name}: {str(e)}")
            else:
                logger.debug(f"⏭️  Column already exists: {column_name}")
        
        conn.commit()
        
        if added_columns:
            logger.info(f"✅ Migration completed. Added {len(added_columns)} columns: {', '.join(added_columns)}")
        else:
            logger.info("✅ All columns already exist. No migration needed.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration error: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def run_migration(db_path='progress_report.db'):
    """Execute migration"""
    logger.info("🔄 Starting CIMS database migration...")
    success = migrate_cims_incidents_table(db_path)
    if success:
        logger.info("✅ Migration completed (or skipped) successfully")
    else:
        logger.error("❌ Migration failed")
    return success

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_migration()

