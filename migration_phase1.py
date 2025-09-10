#!/usr/bin/env python3
"""
Progress Report System - Phase 1 마이그레이션
Week 1 - Day 1-2: 사용자, FCM 토큰, 로그 데이터 마이그레이션
"""

import sqlite3
import json
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_phase1.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class Phase1Migration:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        
        # 데이터베이스 존재 확인
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다. 먼저 init_database.py를 실행하세요.")
    
    def run_phase1_migration(self):
        """Phase 1 마이그레이션 실행"""
        logger.info("🚀 Phase 1 마이그레이션 시작")
        logger.info("대상: 사용자, FCM 토큰, 사용 로그 데이터")
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # 1. 사용자 데이터 마이그레이션
            self.migrate_users(conn)
            
            # 2. FCM 토큰 마이그레이션
            self.migrate_fcm_tokens(conn)
            
            # 3. 사용 로그 마이그레이션
            self.migrate_usage_logs(conn)
            
            # 4. 마이그레이션 결과 요약
            self.print_migration_summary(conn)
            
            conn.close()
            logger.info("✅ Phase 1 마이그레이션 완료!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Phase 1 마이그레이션 실패: {e}")
            return False
    
    def migrate_users(self, conn):
        """사용자 데이터 마이그레이션 (config_users.py)"""
        logger.info("👥 사용자 데이터 마이그레이션 시작...")
        
        try:
            # config_users.py에서 USERS_DB 가져오기
            sys.path.append('.')
            from config_users import USERS_DB
            
            cursor = conn.cursor()
            migrated_count = 0
            
            for username, user_data in USERS_DB.items():
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO users 
                        (username, password_hash, first_name, last_name, role, position, location, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        username,
                        user_data['password_hash'],
                        user_data['first_name'],
                        user_data['last_name'],
                        user_data['role'],
                        user_data['position'],
                        json.dumps(user_data.get('location', [])),
                        True
                    ))
                    migrated_count += 1
                    logger.debug(f"사용자 {username} 마이그레이션 완료")
                    
                except Exception as e:
                    logger.error(f"사용자 {username} 마이그레이션 실패: {e}")
            
            conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'users'
            ''', (datetime.now().isoformat(), migrated_count))
            
            conn.commit()
            logger.info(f"✅ 사용자 {migrated_count}명 마이그레이션 완료")
            
        except ImportError:
            logger.error("config_users.py 파일을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"사용자 마이그레이션 실패: {e}")
    
    def migrate_fcm_tokens(self, conn):
        """FCM 토큰 마이그레이션 (credential/fcm_tokens.json)"""
        logger.info("🔥 FCM 토큰 데이터 마이그레이션 시작...")
        
        fcm_file = 'credential/fcm_tokens.json'
        
        if not os.path.exists(fcm_file):
            logger.warning(f"FCM 토큰 파일 {fcm_file}을 찾을 수 없습니다. 건너뜁니다.")
            return
        
        try:
            with open(fcm_file, 'r', encoding='utf-8') as f:
                fcm_data = json.load(f)
            
            cursor = conn.cursor()
            migrated_count = 0
            
            for user_id, tokens in fcm_data.items():
                if isinstance(tokens, list):
                    for token_info in tokens:
                        try:
                            cursor.execute('''
                                INSERT OR REPLACE INTO fcm_tokens 
                                (user_id, token, device_info, created_at, last_used, is_active)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                token_info.get('user_id', user_id),
                                token_info.get('token', ''),
                                token_info.get('device_info', ''),
                                token_info.get('created_at'),
                                token_info.get('last_used'),
                                token_info.get('is_active', True)
                            ))
                            migrated_count += 1
                            
                        except Exception as e:
                            logger.error(f"FCM 토큰 마이그레이션 실패 (user: {user_id}): {e}")
            
            conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'fcm_tokens'
            ''', (datetime.now().isoformat(), migrated_count))
            
            conn.commit()
            logger.info(f"✅ FCM 토큰 {migrated_count}개 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"FCM 토큰 마이그레이션 실패: {e}")
    
    def migrate_usage_logs(self, conn):
        """사용 로그 마이그레이션 (UsageLog/**/*.json)"""
        logger.info("📊 사용 로그 데이터 마이그레이션 시작...")
        
        usage_log_dir = 'UsageLog'
        if not os.path.exists(usage_log_dir):
            logger.warning(f"사용 로그 디렉토리 {usage_log_dir}를 찾을 수 없습니다. 건너뜁니다.")
            return
        
        cursor = conn.cursor()
        access_count = 0
        progress_count = 0
        
        try:
            # 연도/월 폴더 순회
            for year_month in os.listdir(usage_log_dir):
                year_month_path = os.path.join(usage_log_dir, year_month)
                if not os.path.isdir(year_month_path):
                    continue
                
                logger.info(f"📅 {year_month} 로그 처리 중...")
                
                for log_file in os.listdir(year_month_path):
                    log_path = os.path.join(year_month_path, log_file)
                    
                    if not log_file.endswith('.json'):
                        continue
                    
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            log_data = json.load(f)
                        
                        if 'access_' in log_file:
                            # 접근 로그 마이그레이션
                            for entry in log_data:
                                user_info = entry.get('user', {})
                                try:
                                    cursor.execute('''
                                        INSERT INTO access_logs 
                                        (timestamp, username, display_name, role, position, page_accessed)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (
                                        entry.get('timestamp'),
                                        user_info.get('username'),
                                        user_info.get('display_name'),
                                        user_info.get('role'),
                                        user_info.get('position'),
                                        entry.get('page', 'unknown')
                                    ))
                                    access_count += 1
                                except Exception as e:
                                    logger.debug(f"접근 로그 항목 처리 실패: {e}")
                        
                        elif 'progress_notes_' in log_file:
                            # Progress Note 로그 마이그레이션
                            for entry in log_data:
                                user_info = entry.get('user', {})
                                try:
                                    cursor.execute('''
                                        INSERT INTO progress_note_logs 
                                        (timestamp, username, display_name, role, position, 
                                         client_name, note_content, site)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        entry.get('timestamp'),
                                        user_info.get('username'),
                                        user_info.get('display_name'),
                                        user_info.get('role'),
                                        user_info.get('position'),
                                        entry.get('client_name'),
                                        entry.get('note_content'),
                                        entry.get('site')
                                    ))
                                    progress_count += 1
                                except Exception as e:
                                    logger.debug(f"Progress Note 로그 항목 처리 실패: {e}")
                    
                    except Exception as e:
                        logger.error(f"로그 파일 {log_path} 처리 실패: {e}")
                
                # 중간 커밋 (메모리 절약)
                conn.commit()
            
            conn.commit()
            logger.info(f"✅ 접근 로그 {access_count:,}개, Progress Note 로그 {progress_count:,}개 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"사용 로그 마이그레이션 실패: {e}")
    
    def print_migration_summary(self, conn):
        """마이그레이션 결과 요약"""
        logger.info("📊 Phase 1 마이그레이션 결과 요약")
        logger.info("=" * 50)
        
        cursor = conn.cursor()
        
        # 각 테이블의 레코드 수 확인
        tables = ['users', 'fcm_tokens', 'access_logs', 'progress_note_logs']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"📋 {table}: {count:,}개 레코드")
            except sqlite3.Error as e:
                logger.error(f"{table} 테이블 조회 실패: {e}")
        
        # 동기화 상태 확인
        logger.info("\n🔄 동기화 상태:")
        cursor.execute('''
            SELECT data_type, sync_status, records_synced, last_sync_time 
            FROM sync_status 
            WHERE data_type IN ('users', 'fcm_tokens')
            ORDER BY data_type
        ''')
        
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]} ({row[2]}개, {row[3]})")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🚀 Progress Report System - Phase 1 마이그레이션")
    print("Week 1 - Day 1-2: 사용자, FCM, 로그 데이터")
    print("=" * 60)
    
    try:
        migration = Phase1Migration()
        success = migration.run_phase1_migration()
        
        if success:
            print("\n✅ Phase 1 마이그레이션이 성공적으로 완료되었습니다!")
            print("다음 단계: Phase 2 마이그레이션을 실행하세요.")
            print("명령어: python migration_phase2.py")
        else:
            print("\n❌ Phase 1 마이그레이션에 실패했습니다.")
            print("migration_phase1.log 파일을 확인하세요.")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다: {e}")
        print("먼저 init_database.py를 실행하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
