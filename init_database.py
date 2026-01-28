#!/usr/bin/env python3
"""
Progress Report System - Database Initialization
Week 1 - Day 1: Schema creation and initial setup
"""

import sqlite3
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.schema_file = 'database_schema.sql'
        
    def initialize_database(self):
        """Execute database initialization"""
        logger.info("🚀 Starting Progress Report System database initialization")
        
        try:
            # Step 1: Backup existing database (if exists)
            self.backup_existing_database()
            
            # Step 2: Verify schema file
            self.verify_schema_file()
            
            # Step 3: Create database and apply schema
            self.create_database_schema()
            
            # Step 4: Insert initial data
            self.insert_initial_data()
            
            # Step 5: Verify database
            self.verify_database()
            
            logger.info("✅ Database initialization completed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def backup_existing_database(self):
        """Backup existing database"""
        if os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.db_path, backup_path)
            logger.info(f"📦 Backed up existing database to {backup_path}.")
    
    def verify_schema_file(self):
        """Verify schema file exists"""
        if not os.path.exists(self.schema_file):
            raise FileNotFoundError(f"Schema file not found: {self.schema_file}")
        
        logger.info(f"📋 Schema file verified: {self.schema_file}")
    
    def create_database_schema(self):
        """Create database schema"""
        logger.info("🏗️ Creating database schema...")
        
        # Read schema file
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Connect to database and execute schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Parse and execute SQL statements
            statements = self.parse_sql_statements(schema_sql)
            
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        cursor.execute(statement)
                        logger.debug(f"SQL statement {i+1} executed")
                    except sqlite3.Error as e:
                        if "already exists" not in str(e):
                            logger.error(f"SQL statement {i+1} failed: {e}")
                            logger.error(f"Failed SQL statement: {statement[:100]}...")
                            raise
            
            conn.commit()
            logger.info("✅ Schema creation completed")
            
        finally:
            conn.close()
    
    def parse_sql_statements(self, sql_content):
<<<<<<< Updated upstream
        """
        SQL 문들을 파싱하여 개별 문장으로 분리.

        NOTE: 기존 구현은 모든 줄을 하나로 합쳐 inline `--` 주석이 이후 전체를
        주석 처리해버려 "incomplete input" / 테이블 누락을 유발할 수 있음.
        """
        statements: list[str] = []
        buf: list[str] = []

        in_single_quote = False
        in_double_quote = False
        in_line_comment = False
        in_block_comment = False

        i = 0
        n = len(sql_content)
        while i < n:
            ch = sql_content[i]
            nxt = sql_content[i + 1] if i + 1 < n else ''

            if in_line_comment:
                if ch == '\n':
                    in_line_comment = False
                    buf.append(ch)
                i += 1
                continue

            if in_block_comment:
                if ch == '*' and nxt == '/':
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if not in_single_quote and not in_double_quote:
                if ch == '-' and nxt == '-':
                    in_line_comment = True
                    i += 2
                    continue
                if ch == '/' and nxt == '*':
                    in_block_comment = True
                    i += 2
                    continue

            if ch == "'" and not in_double_quote:
                if in_single_quote and nxt == "'":  # escaped single quote ('')
                    buf.append(ch)
                    buf.append(nxt)
                    i += 2
                    continue
                in_single_quote = not in_single_quote
                buf.append(ch)
                i += 1
                continue

            if ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                buf.append(ch)
                i += 1
                continue

            if ch == ';' and not in_single_quote and not in_double_quote:
                stmt = ''.join(buf).strip()
                if stmt:
                    statements.append(stmt + ';')
                buf = []
                i += 1
                continue

            buf.append(ch)
            i += 1

        tail = ''.join(buf).strip()
        if tail:
            statements.append(tail)

=======
        """Parse SQL content and split into individual statements"""
        # Simple method to split SQL statements
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
        
>>>>>>> Stashed changes
        return statements
    
    def insert_initial_data(self):
        """Insert initial data"""
        logger.info("📝 Inserting initial data...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert default site information
            sites_data = [
                ('Parafield Gardens', '192.168.1.11:8080', 'Edenfield Family Care - Parafield Gardens'),
                ('Nerrilda', None, 'Nerrilda Care Facility'),
                ('Ramsay', None, 'Ramsay Care Center'),
                ('Yankalilla', None, 'Yankalilla Care Home')
            ]
            
            for site_name, server_ip, description in sites_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO sites (site_name, server_ip, description)
                    VALUES (?, ?, ?)
                ''', (site_name, server_ip, description))
            
            # Insert default sync status records
            sync_data = [
                ('clients', 'Parafield Gardens'),
                ('clients', 'Nerrilda'),
                ('clients', 'Ramsay'),
                ('clients', 'Yankalilla'),
                ('carearea', None),
                ('eventtype', None),
                ('fcm_tokens', None),
                ('users', None)
            ]
            
            for data_type, site in sync_data:
                cursor.execute('''
                    INSERT OR IGNORE INTO sync_status (data_type, site, sync_status, records_synced)
                    VALUES (?, ?, 'pending', 0)
                ''', (data_type, site))
            
            conn.commit()
            logger.info("✅ Initial data insertion completed")
            
        except Exception as e:
            logger.error(f"Initial data insertion failed: {e}")
            raise
        finally:
            conn.close()
    
    def verify_database(self):
        """Verify database structure"""
        logger.info("🔍 Verifying database structure...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
                'clients_cache', 'care_areas', 'event_types', 'incidents_cache',
                'sites', 'sync_status', 'alarm_templates', 'alarm_recipients'
            ]
            
            logger.info(f"📊 Tables created: {len(tables)}")
            for table in tables:
                logger.info(f"  ✓ {table}")
            
            # Check for missing tables
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"⚠️ Missing tables: {missing_tables}")
            
            # Check record count for each table
            logger.info("📈 Record count by table:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"  {table}: {count}")
            
            logger.info("✅ Database verification completed")
            
        finally:
            conn.close()
    
    def get_database_info(self):
        """Get database information"""
        if not os.path.exists(self.db_path):
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get database version
            cursor.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]
            
            # Get database size
            db_size = os.path.getsize(self.db_path)
            
            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            return {
                'sqlite_version': sqlite_version,
                'db_size_mb': round(db_size / 1024 / 1024, 2),
                'table_count': table_count,
                'db_path': self.db_path
            }
            
        finally:
            conn.close()


def main():
    """Main execution function"""
    print("=" * 60)
    print("🚀 Progress Report System - Database initialization")
    print("Week 1 - Day 1: Foundation Setup")
    print("=" * 60)
    
    initializer = DatabaseInitializer()
    
    # Execute initialization
    success = initializer.initialize_database()
    
    if success:
        # Print database information
        db_info = initializer.get_database_info()
        if db_info:
            print("\n" + "=" * 60)
            print("📊 Database info")
            print("=" * 60)
            print(f"SQLite version: {db_info['sqlite_version']}")
            print(f"Database size: {db_info['db_size_mb']} MB")
            print(f"Table count: {db_info['table_count']}")
            print(f"File path: {db_info['db_path']}")
        
        print("\n✅ Database initialization completed successfully!")
        print("Next step: run Phase 1 migration.")
        print("Command: python migration_phase1.py")
        
    else:
        print("\n❌ Database initialization failed.")
        print("Check the migration.log file.")
        sys.exit(1)


if __name__ == "__main__":
    main()
