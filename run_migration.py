#!/usr/bin/env python3
"""
Progress Report System - Unified Database Migration Script
Performs all necessary database migrations to run the app in local environment.

This script handles:
- Base database schema creation
- CIMS database schema creation
- CIMS incidents table column additions
- Database structure validation

Usage:
    python run_migration.py
"""

import sqlite3
import os
import sys
import logging
from datetime import datetime

# Configure UTF-8 output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Database migration class that handles all schema migrations"""
    
    def __init__(self, db_path: str = 'progress_report.db'):
        """Initialize migrator with database and schema file paths"""
        self.db_path = db_path
        self.schema_file = 'database_schema.sql'
        self.cims_schema_file = 'cims_database_schema.sql'
        
    def run_all_migrations(self):
        """Execute all migration steps in sequence"""
        logger.info("=" * 70)
        logger.info("🚀 Progress Report System - 통합 데이터베이스 마이그레이션 시작")
        logger.info("=" * 70)
        
        try:
            # Step 1: Ensure database file exists
            self.ensure_database_exists()
            
            # Step 2: Migrate base schema
            logger.info("\n📋 Step 1: Base database schema migration")
            self.migrate_base_schema()
            
            # Step 3: Migrate CIMS schema
            logger.info("\n📋 Step 2: CIMS database schema migration")
            self.migrate_cims_schema()
            
            # Step 4: Add missing columns to CIMS incidents table
            logger.info("\n📋 Step 3: CIMS incidents table column addition migration")
            self.migrate_cims_incidents_columns()
            
            # Step 5: Verify database structure
            logger.info("\n📋 Step 4: Database verification")
            self.verify_database()
            
            logger.info("\n" + "=" * 70)
            logger.info("✅ All migrations completed successfully!")
            logger.info("=" * 70)
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Migration failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def ensure_database_exists(self):
        """Check if database file exists, create if it doesn't"""
        if not os.path.exists(self.db_path):
            logger.info(f"📦 Database file not found. Creating new database: {self.db_path}")
            # Create empty database file
            conn = sqlite3.connect(self.db_path)
            conn.close()
            logger.info("✅ Database file created successfully")
        else:
            logger.info(f"✅ Existing database file found: {self.db_path}")
            # Suggest backup
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"💡 To backup, run: copy {self.db_path} {backup_path}")
    
    def migrate_base_schema(self):
        """Migrate base database schema from database_schema.sql"""
        if not os.path.exists(self.schema_file):
            logger.warning(f"⚠️  Schema file not found: {self.schema_file}")
            logger.info("Skipping base schema migration.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Read schema file
            with open(self.schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Parse and execute SQL statements
            statements = self.parse_sql_statements(schema_sql)
            
            executed = 0
            skipped = 0
            
            for statement in statements:
                if not statement.strip():
                    continue
                
                try:
                    # Check if table exists before creating (for CREATE TABLE statements)
                    if statement.strip().upper().startswith('CREATE TABLE'):
                        table_name = self.extract_table_name(statement)
                        if table_name:
                            cursor.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                                (table_name,)
                            )
                            if cursor.fetchone():
                                skipped += 1
                                logger.debug(f"⏭️  Table already exists: {table_name}")
                                continue
                    
                    cursor.execute(statement)
                    executed += 1
                    
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        skipped += 1
                        logger.debug(f"⏭️  Already exists: {str(e)[:50]}")
                    else:
                        logger.warning(f"⚠️  SQL execution error (ignored): {str(e)[:100]}")
                except sqlite3.Error as e:
                    logger.warning(f"⚠️  SQL execution error (ignored): {str(e)[:100]}")
            
            conn.commit()
            logger.info(f"✅ Base schema migration completed (executed: {executed}, skipped: {skipped})")
            
        except Exception as e:
            logger.error(f"❌ Base schema migration failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def migrate_cims_schema(self):
        """Migrate CIMS database schema from cims_database_schema.sql"""
        if not os.path.exists(self.cims_schema_file):
            logger.warning(f"⚠️  CIMS schema file not found: {self.cims_schema_file}")
            logger.info("Skipping CIMS schema migration.")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Read CIMS schema file
            with open(self.cims_schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Parse and execute SQL statements
            statements = self.parse_sql_statements(schema_sql)
            
            executed = 0
            skipped = 0
            
            for statement in statements:
                if not statement.strip():
                    continue
                
                try:
                    statement_upper = statement.strip().upper()
                    
                    # Handle CREATE TABLE statements
                    if statement_upper.startswith('CREATE TABLE'):
                        table_name = self.extract_table_name(statement)
                        if table_name:
                            cursor.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                                (table_name,)
                            )
                            if cursor.fetchone():
                                skipped += 1
                                logger.debug(f"⏭️  Table already exists: {table_name}")
                                continue
                        
                        cursor.execute(statement)
                        executed += 1
                        if table_name:
                            logger.info(f"  ✅ Table created: {table_name}")
                    
                    # Handle CREATE INDEX statements
                    elif statement_upper.startswith('CREATE INDEX'):
                        try:
                            cursor.execute(statement)
                            executed += 1
                        except sqlite3.OperationalError as e:
                            if 'already exists' in str(e).lower():
                                skipped += 1
                            else:
                                logger.warning(f"⚠️  Index creation error: {str(e)[:100]}")
                    
                    # Handle INSERT statements
                    elif statement_upper.startswith('INSERT'):
                        try:
                            cursor.execute(statement)
                            executed += 1
                        except sqlite3.IntegrityError as e:
                            if 'UNIQUE constraint' in str(e):
                                skipped += 1
                            else:
                                logger.warning(f"⚠️  Data insertion error: {str(e)[:100]}")
                    
                    # Handle other SQL statements
                    else:
                        try:
                            cursor.execute(statement)
                            executed += 1
                        except sqlite3.Error as e:
                            logger.debug(f"⏭️  SQL execution (ignored): {str(e)[:50]}")
                            
                except sqlite3.Error as e:
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        skipped += 1
                    else:
                        logger.debug(f"⏭️  SQL execution (ignored): {str(e)[:50]}")
            
            conn.commit()
            logger.info(f"✅ CIMS schema migration completed (executed: {executed}, skipped: {skipped})")
            
        except Exception as e:
            logger.error(f"❌ CIMS schema migration failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def migrate_cims_incidents_columns(self):
        """Add missing columns to cims_incidents table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if cims_incidents table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
            if not cursor.fetchone():
                logger.info("⏭️  cims_incidents table does not exist. Skipping.")
                return
            
            # List of columns to add
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
                # Check if column already exists
                cursor.execute("PRAGMA table_info(cims_incidents)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if column_name in column_names:
                    logger.debug(f"⏭️  Column already exists: {column_name}")
                    continue
                
                try:
                    if default_value == 'NULL':
                        alter_sql = f"ALTER TABLE cims_incidents ADD COLUMN {column_name} {column_type}"
                    else:
                        alter_sql = f"ALTER TABLE cims_incidents ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                    
                    cursor.execute(alter_sql)
                    added_columns.append(column_name)
                    logger.info(f"  ✅ Column added: {column_name}")
                    
                except sqlite3.OperationalError as e:
                    logger.error(f"❌ Failed to add column {column_name}: {str(e)}")
            
            conn.commit()
            
            if added_columns:
                logger.info(f"✅ Added {len(added_columns)} columns: {', '.join(added_columns)}")
            else:
                logger.info("✅ All columns already exist. No migration needed.")
            
        except Exception as e:
            logger.error(f"❌ CIMS incidents column migration failed: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def verify_database(self):
        """Verify database structure and check for required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"\n📊 Database information:")
            logger.info(f"  - Total tables: {len(tables)}")
            logger.info(f"  - Database file: {self.db_path}")
            
            # Check for required tables
            expected_tables = [
                'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
                'clients_cache', 'care_areas', 'event_types', 'incidents_cache',
                'sites', 'sync_status', 'alarm_templates', 'alarm_recipients',
                'cims_policies', 'cims_incidents', 'cims_tasks', 'cims_progress_notes',
                'cims_audit_logs', 'cims_notifications', 'cims_task_assignments'
            ]
            
            missing_tables = []
            for table in expected_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    logger.info(f"  ✅ {table}: {count} records")
                else:
                    missing_tables.append(table)
                    logger.warning(f"  ⚠️  {table}: table not found")
            
            if missing_tables:
                logger.warning(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
            else:
                logger.info("\n✅ All required tables exist.")
            
        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            raise
        finally:
            conn.close()
    
    def parse_sql_statements(self, sql_content):
        """Parse SQL content and split into individual statements"""
        statements = []
        
        # Remove comments
        lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        # Split by semicolon
        full_content = ' '.join(lines)
        raw_statements = full_content.split(';')
        
        for statement in raw_statements:
            statement = statement.strip()
            if statement:
                statements.append(statement + ';')
        
        return statements
    
    def extract_table_name(self, create_table_sql):
        """Extract table name from CREATE TABLE statement"""
        try:
            parts = create_table_sql.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE' and i + 1 < len(parts):
                    table_name = parts[i + 1].strip('(').strip()
                    # Handle IF NOT EXISTS clause
                    if table_name.upper() == 'IF':
                        if i + 3 < len(parts):
                            table_name = parts[i + 3].strip('(').strip()
                    return table_name
        except:
            pass
        return None


def main():
    """Main execution function"""
    print("\n" + "=" * 70)
    print("🚀 Progress Report System - Unified Database Migration")
    print("=" * 70)
    print("\nThis script will perform the following operations:")
    print("  1. Base database schema creation")
    print("  2. CIMS database schema creation")
    print("  3. CIMS incidents table column additions")
    print("  4. Database structure verification")
    print("\n" + "=" * 70 + "\n")
    
    migrator = DatabaseMigrator()
    success = migrator.run_all_migrations()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print("\nYou can now run the application:")
        print("  python app.py")
        print("\nor")
        print("  flask run")
        print("=" * 70 + "\n")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ Migration failed.")
        print("=" * 70)
        print("\nPlease check the log file: migration.log")
        print("=" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
