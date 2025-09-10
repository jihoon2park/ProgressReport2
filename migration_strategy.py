#!/usr/bin/env python3
"""
Progress Report System - SQLite 마이그레이션 전략
전체 JSON 데이터를 SQLite로 단계별 마이그레이션
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProgressReportMigration:
    def __init__(self, db_path: str = 'progress_report.db'):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """데이터베이스 연결"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            self.conn.close()

    # ===========================================
    # PHASE 1: 핵심 영구 데이터 마이그레이션
    # ===========================================
    
    def phase1_migrate_core_data(self):
        """Phase 1: 사용자, FCM 토큰, 로그 데이터 마이그레이션"""
        logger.info("=== Phase 1: 핵심 영구 데이터 마이그레이션 시작 ===")
        
        # 1-1. 사용자 데이터 마이그레이션
        self.migrate_users()
        
        # 1-2. FCM 토큰 마이그레이션
        self.migrate_fcm_tokens()
        
        # 1-3. 사용 로그 마이그레이션
        self.migrate_usage_logs()
        
        logger.info("=== Phase 1 완료 ===")
    
    def migrate_users(self):
        """config_users.py에서 사용자 데이터 마이그레이션"""
        logger.info("사용자 데이터 마이그레이션 시작...")
        
        # config_users.py에서 USERS_DB 가져오기
        try:
            from config_users import USERS_DB
            
            cursor = self.conn.cursor()
            
            for username, user_data in USERS_DB.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (username, password_hash, first_name, last_name, role, position, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    username,
                    user_data['password_hash'],
                    user_data['first_name'],
                    user_data['last_name'],
                    user_data['role'],
                    user_data['position'],
                    json.dumps(user_data.get('location', []))
                ))
            
            self.conn.commit()
            logger.info(f"사용자 {len(USERS_DB)}명 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"사용자 마이그레이션 실패: {e}")
    
    def migrate_fcm_tokens(self):
        """credential/fcm_tokens.json 마이그레이션"""
        logger.info("FCM 토큰 데이터 마이그레이션 시작...")
        
        try:
            with open('credential/fcm_tokens.json', 'r') as f:
                fcm_data = json.load(f)
            
            cursor = self.conn.cursor()
            
            for user_id, tokens in fcm_data.items():
                if isinstance(tokens, list):
                    for token_info in tokens:
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
            
            self.conn.commit()
            logger.info("FCM 토큰 마이그레이션 완료")
            
        except FileNotFoundError:
            logger.warning("FCM 토큰 파일을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"FCM 토큰 마이그레이션 실패: {e}")
    
    def migrate_usage_logs(self):
        """UsageLog 폴더의 모든 로그 파일 마이그레이션"""
        logger.info("사용 로그 마이그레이션 시작...")
        
        usage_log_dir = 'UsageLog'
        if not os.path.exists(usage_log_dir):
            logger.warning("UsageLog 디렉토리를 찾을 수 없습니다.")
            return
        
        cursor = self.conn.cursor()
        access_count = 0
        progress_count = 0
        
        # 연도/월 폴더 순회
        for year_month in os.listdir(usage_log_dir):
            year_month_path = os.path.join(usage_log_dir, year_month)
            if not os.path.isdir(year_month_path):
                continue
            
            for log_file in os.listdir(year_month_path):
                log_path = os.path.join(year_month_path, log_file)
                
                try:
                    with open(log_path, 'r') as f:
                        log_data = json.load(f)
                    
                    if 'access_' in log_file:
                        # 접근 로그 마이그레이션
                        for entry in log_data:
                            user_info = entry.get('user', {})
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
                    
                    elif 'progress_notes_' in log_file:
                        # Progress Note 로그 마이그레이션
                        for entry in log_data:
                            user_info = entry.get('user', {})
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
                    logger.error(f"로그 파일 {log_path} 처리 실패: {e}")
        
        self.conn.commit()
        logger.info(f"접근 로그 {access_count}개, Progress Note 로그 {progress_count}개 마이그레이션 완료")

    # ===========================================
    # PHASE 2: 참조 데이터 마이그레이션
    # ===========================================
    
    def phase2_migrate_reference_data(self):
        """Phase 2: 케어 영역, 이벤트 타입 마이그레이션"""
        logger.info("=== Phase 2: 참조 데이터 마이그레이션 시작 ===")
        
        # 2-1. 케어 영역 마이그레이션
        self.migrate_care_areas()
        
        # 2-2. 이벤트 타입 마이그레이션
        self.migrate_event_types()
        
        logger.info("=== Phase 2 완료 ===")
    
    def migrate_care_areas(self):
        """data/carearea.json 마이그레이션"""
        logger.info("케어 영역 데이터 마이그레이션 시작...")
        
        try:
            with open('data/carearea.json', 'r') as f:
                care_areas = json.load(f)
            
            cursor = self.conn.cursor()
            
            for area in care_areas:
                cursor.execute('''
                    INSERT OR REPLACE INTO care_areas 
                    (id, description, is_archived, is_external, last_updated_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    area['Id'],
                    area['Description'],
                    area.get('IsArchived', False),
                    area.get('IsExternal', False),
                    area.get('LastUpdatedDate')
                ))
            
            self.conn.commit()
            logger.info(f"케어 영역 {len(care_areas)}개 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"케어 영역 마이그레이션 실패: {e}")
    
    def migrate_event_types(self):
        """data/eventtype.json 마이그레이션"""
        logger.info("이벤트 타입 데이터 마이그레이션 시작...")
        
        try:
            with open('data/eventtype.json', 'r') as f:
                event_types = json.load(f)
            
            cursor = self.conn.cursor()
            
            for event in event_types:
                cursor.execute('''
                    INSERT OR REPLACE INTO event_types 
                    (id, description, color_argb, is_archived, is_external, last_updated_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event['Id'],
                    event['Description'],
                    event.get('ColorArgb'),
                    event.get('IsArchived', False),
                    event.get('IsExternal', False),
                    event.get('LastUpdatedDate')
                ))
            
            self.conn.commit()
            logger.info(f"이벤트 타입 {len(event_types)}개 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"이벤트 타입 마이그레이션 실패: {e}")

    # ===========================================
    # PHASE 3: 클라이언트 데이터 캐시화
    # ===========================================
    
    def phase3_migrate_client_data(self):
        """Phase 3: 클라이언트 데이터 캐시 테이블 구축"""
        logger.info("=== Phase 3: 클라이언트 데이터 캐시화 시작 ===")
        
        # 3-1. 각 사이트별 클라이언트 데이터 마이그레이션
        sites = [
            ('parafield_gardens_client.json', 'Parafield Gardens'),
            ('nerrilda_client.json', 'Nerrilda'),
            ('ramsay_client.json', 'Ramsay'),
            ('yankalilla_client.json', 'Yankalilla')
        ]
        
        for filename, site_name in sites:
            self.migrate_site_clients(filename, site_name)
        
        # 3-2. Client_list.json도 백업으로 처리
        self.migrate_client_list()
        
        logger.info("=== Phase 3 완료 ===")
    
    def migrate_site_clients(self, filename: str, site_name: str):
        """개별 사이트의 클라이언트 데이터 마이그레이션"""
        filepath = f'data/{filename}'
        
        if not os.path.exists(filepath):
            logger.warning(f"{filepath} 파일을 찾을 수 없습니다.")
            return
        
        logger.info(f"{site_name} 클라이언트 데이터 마이그레이션 시작...")
        
        try:
            with open(filepath, 'r') as f:
                client_data = json.load(f)
            
            cursor = self.conn.cursor()
            count = 0
            
            # JSON 구조에 따라 처리
            if isinstance(client_data, dict) and 'client_info' in client_data:
                clients = client_data['client_info']
            elif isinstance(client_data, list):
                clients = client_data
            else:
                logger.error(f"{filename}의 JSON 구조를 인식할 수 없습니다.")
                return
            
            for client in clients:
                cursor.execute('''
                    INSERT OR REPLACE INTO clients_cache 
                    (person_id, client_name, preferred_name, title, first_name, 
                     middle_name, surname, gender, birth_date, admission_date,
                     room_name, room_number, wing_name, location_id, location_name,
                     main_client_service_id, original_person_id, client_record_id, site)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client.get('PersonId') or client.get('MainClientServiceId'),
                    client.get('ClientName') or f"{client.get('FirstName', '')} {client.get('Surname', '')}".strip(),
                    client.get('PreferredName'),
                    client.get('Title'),
                    client.get('FirstName'),
                    client.get('MiddleName'),
                    client.get('Surname') or client.get('LastName'),
                    client.get('Gender'),
                    client.get('BirthDate'),
                    client.get('AdmissionDate'),
                    client.get('RoomName'),
                    client.get('RoomNumber'),
                    client.get('WingName'),
                    client.get('LocationId'),
                    client.get('LocationName'),
                    client.get('MainClientServiceId'),
                    client.get('OriginalPersonId'),
                    client.get('ClientRecordId'),
                    site_name
                ))
                count += 1
            
            self.conn.commit()
            
            # 동기화 상태 업데이트
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status 
                (data_type, site, last_sync_time, sync_status, records_synced)
                VALUES (?, ?, ?, ?, ?)
            ''', ('clients', site_name, datetime.now().isoformat(), 'success', count))
            
            self.conn.commit()
            logger.info(f"{site_name} 클라이언트 {count}명 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"{site_name} 클라이언트 마이그레이션 실패: {e}")
    
    def migrate_client_list(self):
        """data/Client_list.json 마이그레이션 (백업 데이터)"""
        filepath = 'data/Client_list.json'
        
        if not os.path.exists(filepath):
            logger.warning(f"{filepath} 파일을 찾을 수 없습니다.")
            return
        
        logger.info("Client_list.json 백업 데이터 마이그레이션 시작...")
        
        try:
            with open(filepath, 'r') as f:
                clients = json.load(f)
            
            cursor = self.conn.cursor()
            count = 0
            
            for client in clients:
                # 중복 체크 후 없는 경우만 추가
                cursor.execute('''
                    SELECT COUNT(*) FROM clients_cache 
                    WHERE person_id = ? AND site = 'General'
                ''', (client.get('PersonId'),))
                
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO clients_cache 
                        (person_id, client_name, preferred_name, gender, birth_date,
                         room_name, wing_name, main_client_service_id, 
                         original_person_id, client_record_id, site)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        client.get('PersonId'),
                        client.get('ClientName'),
                        client.get('PreferredName'),
                        client.get('Gender'),
                        client.get('BirthDate'),
                        client.get('RoomName'),
                        client.get('WingName'),
                        client.get('MainClientServiceId'),
                        client.get('OriginalPersonId'),
                        client.get('ClientRecordId'),
                        'General'  # 일반 백업 데이터로 분류
                    ))
                    count += 1
            
            self.conn.commit()
            logger.info(f"Client_list 백업 데이터 {count}명 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"Client_list 마이그레이션 실패: {e}")

    # ===========================================
    # PHASE 4: 하이브리드 데이터 처리
    # ===========================================
    
    def phase4_migrate_hybrid_data(self):
        """Phase 4: 인시던트 등 하이브리드 데이터 처리"""
        logger.info("=== Phase 4: 하이브리드 데이터 마이그레이션 시작 ===")
        
        # 4-1. 인시던트 데이터 마이그레이션
        self.migrate_incidents()
        
        logger.info("=== Phase 4 완료 ===")
    
    def migrate_incidents(self):
        """incidents_*.json 파일들 마이그레이션"""
        data_dir = 'data'
        
        for filename in os.listdir(data_dir):
            if filename.startswith('incidents_') and filename.endswith('.json'):
                filepath = os.path.join(data_dir, filename)
                site_name = self.extract_site_from_filename(filename)
                self.migrate_incident_file(filepath, site_name)
    
    def extract_site_from_filename(self, filename: str) -> str:
        """파일명에서 사이트명 추출"""
        if 'Parafield Gardens' in filename:
            return 'Parafield Gardens'
        return 'Unknown'
    
    def migrate_incident_file(self, filepath: str, site_name: str):
        """개별 인시던트 파일 마이그레이션"""
        logger.info(f"{site_name} 인시던트 데이터 마이그레이션 시작...")
        
        try:
            with open(filepath, 'r') as f:
                incidents = json.load(f)
            
            cursor = self.conn.cursor()
            count = 0
            
            for incident in incidents:
                cursor.execute('''
                    INSERT OR REPLACE INTO incidents_cache 
                    (incident_id, client_name, incident_type, incident_date, 
                     description, severity, status, site, reported_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    incident.get('id') or f"{site_name}_{count}",
                    incident.get('client_name'),
                    incident.get('type'),
                    incident.get('date'),
                    incident.get('description'),
                    incident.get('severity'),
                    incident.get('status'),
                    site_name,
                    incident.get('reported_by')
                ))
                count += 1
            
            self.conn.commit()
            logger.info(f"{site_name} 인시던트 {count}개 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"{site_name} 인시던트 마이그레이션 실패: {e}")

    # ===========================================
    # 전체 마이그레이션 실행
    # ===========================================
    
    def run_full_migration(self):
        """전체 마이그레이션 실행"""
        logger.info("🚀 Progress Report System SQLite 마이그레이션 시작 🚀")
        start_time = datetime.now()
        
        try:
            # 데이터베이스 연결
            self.connect()
            
            # 스키마 생성
            self.create_schema()
            
            # Phase 1: 핵심 영구 데이터
            self.phase1_migrate_core_data()
            
            # Phase 2: 참조 데이터
            self.phase2_migrate_reference_data()
            
            # Phase 3: 클라이언트 데이터 캐시화
            self.phase3_migrate_client_data()
            
            # Phase 4: 하이브리드 데이터
            self.phase4_migrate_hybrid_data()
            
            # 마이그레이션 완료 로그
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"🎉 마이그레이션 완료! 소요시간: {duration}")
            self.log_migration_summary()
            
        except Exception as e:
            logger.error(f"마이그레이션 실패: {e}")
            raise
        finally:
            self.close()
    
    def create_schema(self):
        """데이터베이스 스키마 생성"""
        logger.info("데이터베이스 스키마 생성 중...")
        
        with open('database_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # SQL 문들을 분리해서 실행
        statements = schema_sql.split(';')
        cursor = self.conn.cursor()
        
        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                except sqlite3.Error as e:
                    if "already exists" not in str(e):
                        logger.error(f"스키마 생성 오류: {e}")
        
        self.conn.commit()
        logger.info("스키마 생성 완료")
    
    def log_migration_summary(self):
        """마이그레이션 요약 로그"""
        cursor = self.conn.cursor()
        
        # 각 테이블의 레코드 수 확인
        tables = [
            'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
            'clients_cache', 'care_areas', 'event_types', 'incidents_cache'
        ]
        
        logger.info("=== 마이그레이션 요약 ===")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"{table}: {count:,}개 레코드")
            except sqlite3.Error:
                logger.info(f"{table}: 테이블 없음")


# ===========================================
# 실행 스크립트
# ===========================================

if __name__ == "__main__":
    migration = ProgressReportMigration()
    migration.run_full_migration()
