#!/usr/bin/env python3
"""
Progress Report System - 클라이언트 동기화 매니저
새로운 거주자 추가/변경 시 SQLite 캐시 자동 업데이트
"""

import sqlite3
import json
import os
import sys
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 기존 앱의 함수들 import
try:
    from app import fetch_client_information, SITE_SERVERS
    from api_client import get_api_client
except ImportError:
    print("Warning: app.py 모듈을 찾을 수 없습니다. 일부 기능이 제한될 수 있습니다.")

logger = logging.getLogger(__name__)

class ClientSyncManager:
    """클라이언트 데이터 동기화 매니저"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        self.cache_expiry_minutes = 30  # 캐시 만료 시간 (30분)
        self.sync_interval_minutes = 30  # 자동 동기화 간격 (30분)
        self.sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        # 데이터베이스 존재 확인
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def get_db_connection(self):
        """데이터베이스 연결"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def is_cache_expired(self, site: str) -> bool:
        """캐시가 만료되었는지 확인"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_sync_time FROM sync_status 
                WHERE data_type = 'clients' AND site = ?
            ''', (site,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result['last_sync_time']:
                return True  # 동기화 기록이 없으면 만료된 것으로 간주
            
            last_sync = datetime.fromisoformat(result['last_sync_time'])
            expiry_time = datetime.now() - timedelta(minutes=self.cache_expiry_minutes)
            
            return last_sync < expiry_time
            
        except Exception as e:
            logger.error(f"캐시 만료 확인 실패 ({site}): {e}")
            return True  # 오류 시 만료된 것으로 간주
    
    def get_cache_age(self, site: str) -> Optional[int]:
        """캐시 나이를 분 단위로 반환"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_sync_time FROM sync_status 
                WHERE data_type = 'clients' AND site = ?
            ''', (site,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result['last_sync_time']:
                return None
            
            last_sync = datetime.fromisoformat(result['last_sync_time'])
            age = datetime.now() - last_sync
            
            return int(age.total_seconds() / 60)  # 분 단위
            
        except Exception as e:
            logger.error(f"캐시 나이 확인 실패 ({site}): {e}")
            return None
    
    def refresh_site_clients(self, site: str) -> Dict[str, Any]:
        """특정 사이트의 클라이언트 데이터 새로고침"""
        result = {
            'success': False,
            'site': site,
            'message': '',
            'changes': {
                'added': 0,
                'updated': 0,
                'removed': 0,
                'total': 0
            }
        }
        
        try:
            logger.info(f"{site} 클라이언트 데이터 새로고침 시작")
            
            # API에서 최신 데이터 가져오기
            api_success, latest_clients = fetch_client_information(site)
            
            if not api_success:
                result['message'] = f"{site} API에서 데이터를 가져올 수 없습니다"
                return result
            
            # SQLite 캐시 업데이트
            changes = self.update_sqlite_cache(site, latest_clients)
            result['changes'] = changes
            result['success'] = True
            result['message'] = f"{site} 클라이언트 데이터 업데이트 완료"
            
            logger.info(f"{site} 동기화 완료: 신규 {changes['added']}명, 업데이트 {changes['updated']}명, 제거 {changes['removed']}명")
            
        except Exception as e:
            result['message'] = f"{site} 동기화 실패: {str(e)}"
            logger.error(f"{site} 동기화 실패: {e}")
        
        return result
    
    def update_sqlite_cache(self, site: str, latest_clients: List[Dict]) -> Dict[str, int]:
        """SQLite 캐시 업데이트 및 변경사항 추적"""
        changes = {'added': 0, 'updated': 0, 'removed': 0, 'total': len(latest_clients)}
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 기존 클라이언트 목록 가져오기
            cursor.execute('''
                SELECT person_id, client_name, room_number, last_synced 
                FROM clients_cache 
                WHERE site = ? AND is_active = 1
            ''', (site,))
            
            existing_clients = {row['person_id']: dict(row) for row in cursor.fetchall()}
            
            # 새 클라이언트 처리
            current_person_ids = set()
            
            for client in latest_clients:
                person_id = (client.get('PersonId') or 
                           client.get('MainClientServiceId') or 
                           client.get('ClientRecordId'))
                
                if not person_id:
                    continue
                
                current_person_ids.add(person_id)
                
                client_name = (client.get('ClientName') or 
                             f"{client.get('FirstName', '')} {client.get('Surname', '')}".strip() or
                             client.get('PreferredName', 'Unknown'))
                
                if person_id in existing_clients:
                    # 기존 클라이언트 업데이트
                    cursor.execute('''
                        UPDATE clients_cache 
                        SET client_name = ?, preferred_name = ?, title = ?, first_name = ?,
                            middle_name = ?, surname = ?, gender = ?, birth_date = ?,
                            admission_date = ?, room_name = ?, room_number = ?, wing_name = ?,
                            location_id = ?, location_name = ?, main_client_service_id = ?,
                            original_person_id = ?, client_record_id = ?, last_synced = ?
                        WHERE person_id = ? AND site = ?
                    ''', (
                        client_name,
                        client.get('PreferredName'),
                        client.get('Title'),
                        client.get('FirstName'),
                        client.get('MiddleName'),
                        client.get('Surname') or client.get('LastName'),
                        client.get('Gender') or client.get('GenderDesc'),
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
                        datetime.now().isoformat(),
                        person_id,
                        site
                    ))
                    changes['updated'] += 1
                else:
                    # 새 클라이언트 추가
                    cursor.execute('''
                        INSERT INTO clients_cache 
                        (person_id, client_name, preferred_name, title, first_name, 
                         middle_name, surname, gender, birth_date, admission_date,
                         room_name, room_number, wing_name, location_id, location_name,
                         main_client_service_id, original_person_id, client_record_id, 
                         site, last_synced, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        person_id,
                        client_name,
                        client.get('PreferredName'),
                        client.get('Title'),
                        client.get('FirstName'),
                        client.get('MiddleName'),
                        client.get('Surname') or client.get('LastName'),
                        client.get('Gender') or client.get('GenderDesc'),
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
                        site,
                        datetime.now().isoformat(),
                        True
                    ))
                    changes['added'] += 1
            
            # 제거된 클라이언트 처리 (비활성화)
            removed_person_ids = set(existing_clients.keys()) - current_person_ids
            for person_id in removed_person_ids:
                cursor.execute('''
                    UPDATE clients_cache 
                    SET is_active = 0, last_synced = ?
                    WHERE person_id = ? AND site = ?
                ''', (datetime.now().isoformat(), person_id, site))
                changes['removed'] += 1
            
            # 동기화 상태 업데이트
            cursor.execute('''
                UPDATE sync_status 
                SET last_sync_time = ?, sync_status = 'success', records_synced = ?
                WHERE data_type = 'clients' AND site = ?
            ''', (datetime.now().isoformat(), len(latest_clients), site))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
        
        return changes
    
    def refresh_all_sites(self) -> Dict[str, Any]:
        """모든 사이트의 클라이언트 데이터 새로고침"""
        results = {}
        total_changes = {'added': 0, 'updated': 0, 'removed': 0, 'total': 0}
        
        for site in self.sites:
            result = self.refresh_site_clients(site)
            results[site] = result
            
            if result['success']:
                for key in total_changes:
                    total_changes[key] += result['changes'][key]
        
        return {
            'results': results,
            'summary': total_changes,
            'success_count': sum(1 for r in results.values() if r['success']),
            'total_sites': len(self.sites)
        }
    
    def get_clients_with_auto_refresh(self, site: str) -> List[Dict]:
        """캐시가 만료되면 자동으로 새로고침하여 클라이언트 반환"""
        
        # 캐시 만료 확인
        if self.is_cache_expired(site):
            logger.info(f"{site} 캐시 만료, 자동 새로고침 실행")
            self.refresh_site_clients(site)
        
        # SQLite에서 데이터 반환
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM clients_cache 
                WHERE site = ? AND is_active = 1
                ORDER BY client_name
            ''', (site,))
            
            clients = [dict(row) for row in cursor.fetchall()]
            return clients
            
        finally:
            conn.close()
    
    def get_sync_status_summary(self) -> Dict[str, Any]:
        """동기화 상태 요약"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT site, last_sync_time, sync_status, records_synced
                FROM sync_status 
                WHERE data_type = 'clients'
                ORDER BY site
            ''')
            
            status_data = {}
            for row in cursor.fetchall():
                site = row['site']
                cache_age = self.get_cache_age(site)
                
                status_data[site] = {
                    'last_sync': row['last_sync_time'],
                    'status': row['sync_status'],
                    'records': row['records_synced'],
                    'cache_age_minutes': cache_age,
                    'is_expired': self.is_cache_expired(site)
                }
            
            return status_data
            
        finally:
            conn.close()
    
    def start_background_sync(self):
        """백그라운드 동기화 시작"""
        def daily_sync_job():
            """매일 새벽 3시 동기화 작업"""
            logger.info("매일 새벽 3시 자동 동기화 시작")
            results = self.refresh_all_sites()
            
            success_count = results['success_count']
            total_sites = results['total_sites']
            total_changes = results['summary']
            
            logger.info(f"매일 자동 동기화 완료: {success_count}/{total_sites} 사이트 성공")
            logger.info(f"변경사항: 신규 {total_changes['added']}명, 업데이트 {total_changes['updated']}명, 제거 {total_changes['removed']}명")
        
        # 스케줄 설정 - 매일 새벽 3시만
        schedule.every().day.at("03:00").do(daily_sync_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 스케줄 확인
        
        # 백그라운드 스레드로 실행
        sync_thread = threading.Thread(target=run_scheduler, daemon=True)
        sync_thread.start()
        
        logger.info("백그라운드 동기화 시작됨 (매일 새벽 3시)")


# Flask 앱에서 사용할 전역 인스턴스
client_sync_manager = None

def get_client_sync_manager():
    """클라이언트 동기화 매니저 싱글톤 인스턴스"""
    global client_sync_manager
    if client_sync_manager is None:
        client_sync_manager = ClientSyncManager()
    return client_sync_manager

def init_client_sync(app=None):
    """Flask 앱 초기화 시 호출"""
    try:
        manager = get_client_sync_manager()
        
        # 백그라운드 동기화 시작
        manager.start_background_sync()
        
        if app:
            app.logger.info("클라이언트 동기화 매니저 초기화 완료")
        
        return True
        
    except Exception as e:
        if app:
            app.logger.error(f"클라이언트 동기화 매니저 초기화 실패: {e}")
        else:
            logger.error(f"클라이언트 동기화 매니저 초기화 실패: {e}")
        return False


# 명령줄에서 직접 실행 시 테스트
if __name__ == "__main__":
    print("클라이언트 동기화 매니저 테스트")
    
    try:
        manager = ClientSyncManager()
        
        # 현재 동기화 상태 확인
        print("\n현재 동기화 상태:")
        status = manager.get_sync_status_summary()
        for site, info in status.items():
            age = info['cache_age_minutes']
            age_str = f"{age}분 전" if age is not None else "없음"
            expired = "만료됨" if info['is_expired'] else "유효함"
            print(f"  {site}: {info['records']}명, 마지막 동기화 {age_str} ({expired})")
        
        # 테스트: 한 사이트 새로고침
        print(f"\nParafield Gardens 새로고침 테스트...")
        result = manager.refresh_site_clients('Parafield Gardens')
        
        if result['success']:
            changes = result['changes']
            print(f"✅ 성공: 신규 {changes['added']}명, 업데이트 {changes['updated']}명, 제거 {changes['removed']}명")
        else:
            print(f"❌ 실패: {result['message']}")
        
        # 캐시된 클라이언트 조회 테스트
        print(f"\n캐시된 클라이언트 조회 테스트...")
        clients = manager.get_clients_with_auto_refresh('Parafield Gardens')
        print(f"조회된 클라이언트: {len(clients)}명")
        
        if clients:
            print("처음 3명:")
            for i, client in enumerate(clients[:3]):
                print(f"  {i+1}. {client['client_name']} (방: {client['room_number']})")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
