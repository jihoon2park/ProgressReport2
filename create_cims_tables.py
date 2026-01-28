#!/usr/bin/env python3
"""
CIMS Table Creation Script
Creates cims_incidents and related tables.
"""

import sqlite3
import os
import sys

# Configure UTF-8 output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def create_cims_tables():
    """Create CIMS tables"""
    db_path = 'progress_report.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing CIMS tables: {existing_tables if existing_tables else 'none'}")
        
        # Read cims_database_schema.sql file
        schema_file = 'cims_database_schema.sql'
        if not os.path.exists(schema_file):
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Remove comments and clean up
        lines = []
        for line in schema_sql.split('\n'):
            line = line.strip()
            # Remove comments
            if line.startswith('--'):
                continue
            if line:
                lines.append(line)
        
        # Combine all SQL into one string
        clean_sql = ' '.join(lines)
        
        # Split SQL statements by semicolon
        statements = []
        current = []
        in_string = False
        string_char = None
        
        for char in clean_sql:
            if char in ("'", '"') and (not current or current[-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            current.append(char)
            
            if not in_string and char == ';':
                statement = ''.join(current).strip()
                if statement and statement != ';':
                    statements.append(statement)
                current = []
        
        # Process remaining statement
        if current:
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
        
        # Execute each SQL statement
        created_tables = []
        for statement in statements:
            try:
                statement_upper = statement.upper().strip()
                
                # Handle CREATE TABLE statements
                if statement_upper.startswith('CREATE TABLE'):
                    # Extract table name
                    table_name = None
                    parts = statement.split()
                    for i, part in enumerate(parts):
                        if part.upper() == 'TABLE' and i + 1 < len(parts):
                            table_name = parts[i + 1].strip('(').strip()
                            break
                    
                    if table_name:
                        # Check if table already exists
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if cursor.fetchone():
                            print(f"⏭️  Table already exists: {table_name}")
                            continue
                    
                    cursor.execute(statement)
                    if table_name:
                        created_tables.append(table_name)
                        print(f"✅ Table created: {table_name}")
                
                # Handle CREATE INDEX statements
                elif statement_upper.startswith('CREATE INDEX'):
                    try:
                        cursor.execute(statement)
                        print("✅ Index created")
                    except sqlite3.OperationalError as e:
                        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                            print("⏭️  Index already exists")
                        else:
                            print(f"⚠️  Index creation error: {str(e)[:100]}")
                
                # Handle INSERT statements
                elif statement_upper.startswith('INSERT'):
                    try:
                        cursor.execute(statement)
                        print("✅ Initial data inserted")
                    except sqlite3.IntegrityError as e:
                        if 'UNIQUE constraint' in str(e):
                            print("⏭️  Data already exists")
                        else:
                            print(f"⚠️  Data insert error: {str(e)[:100]}")
                
                # Handle other SQL statements
                else:
                    try:
                        cursor.execute(statement)
                    except sqlite3.Error as e:
                        print(f"⚠️  SQL execution error (ignored): {str(e)[:100]}")
                        
            except sqlite3.Error as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    print(f"⏭️  Already exists: {str(e)[:50]}")
                else:
                    print(f"⚠️  SQL execution error: {str(e)[:100]}")
        
        conn.commit()
        
        # Verify created tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cims%'")
        all_cims_tables = [row[0] for row in cursor.fetchall()]
        
        print("\n" + "=" * 60)
        print("✅ CIMS table creation completed!")
        print(f"Tables created: {len(created_tables)}")
        for table in created_tables:
            print(f"  - {table}")
        print(f"\nTotal CIMS tables: {len(all_cims_tables)}")
        for table in all_cims_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} records")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting CIMS table creation...")
    success = create_cims_tables()
    if success:
        print("\n✅ Done!")
        sys.exit(0)
    else:
        print("\n❌ Failed!")
        sys.exit(1)

