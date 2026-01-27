#!/usr/bin/env python3
"""
CIMS 데이터베이스 스키마 마이그레이션 스크립트
Production 서버의 데이터베이스에 누락된 컬럼들을 자동으로 추가합니다.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

def check_column_exists(cursor, table_name, column_name):
    """컬럼이 존재하는지 확인"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    return column_name in column_names

def migrate_cims_incidents_table(db_path='progress_report.db'):
    """cims_incidents 테이블에 누락된 컬럼들을 추가"""
    
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 테이블이 존재하는지 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cims_incidents'")
        if not cursor.fetchone():
            # 신규 설치/아직 CIMS 테이블을 만들지 않은 환경에서는 정상적인 상태입니다.
            # 스키마 마이그레이션은 "추가 컬럼 보강" 목적이므로, 대상 테이블이 없으면 스킵합니다.
            logger.info("⏭️  Skipping migration: cims_incidents table does not exist")
            return True
        
        # 추가할 컬럼 목록 (컬럼명, 타입, 기본값)
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
    """마이그레이션 실행"""
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

