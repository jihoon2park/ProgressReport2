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

# api_client에서 통합 함수 import
try:
    from api_client import fetch_client_information
except ImportError:
    print("Warning: api_client module not found. Some features may be limited.")

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
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
    
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
            logger.error(f"Failed to check cache expiry ({site}): {e}")
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
            logger.error(f"Failed to check cache age ({site}): {e}")
            return None
    
    def refresh_site_clients(self, site: str) -> Dict[str, Any]:
        """
        특정 사이트의 거주자 데이터 새로고침 (단순화)
        
        DB 직접 접속 모드에서는 매번 최신 데이터를 조회하므로,
        별도의 캐시 업데이트는 불필요합니다.
        """
        result = {
            'success': False,
            'site': site,
            'message': '',
            'client_count': 0
        }
        
        try:
            logger.info(f"Starting resident data fetch for {site}")
            
            # DB에서 최신 데이터 가져오기 (캐시 없이 직접 조회)
            api_success, latest_clients = fetch_client_information(site)
            
            if not api_success:
                result['message'] = f"Unable to fetch resident data for {site}"
                return result
            
            client_count = len(latest_clients) if latest_clients else 0
            result['client_count'] = client_count
            result['success'] = True
            result['message'] = f"Resident data fetch completed for {site}: {client_count} residents"
            
            logger.info(f"Resident data fetch completed for {site}: {client_count} residents")
            
        except Exception as e:
            result['message'] = f"Resident data fetch failed for {site}: {str(e)}"
            logger.error(f"Resident data fetch failed for {site}: {e}")
        
        return result
    
    # update_sqlite_cache 메서드 제거됨
    # DB 직접 접속 모드에서는 매번 최신 데이터를 조회하므로 캐시 업데이트 불필요
    
    def refresh_all_sites(self) -> Dict[str, Any]:
        """모든 사이트의 거주자 데이터 새로고침"""
        results = {}
        total_clients = 0
        
        for site in self.sites:
            result = self.refresh_site_clients(site)
            results[site] = result
            
            if result['success']:
                total_clients += result['client_count']
        
        return {
            'results': results,
            'total_clients': total_clients,
            'success_count': sum(1 for r in results.values() if r['success']),
            'total_sites': len(self.sites)
        }
    
    def get_clients_with_auto_refresh(self, site: str) -> List[Dict]:
        """
        거주자 데이터 가져오기 (단순화)
        
        DB 직접 접속 모드에서는 매번 최신 데이터를 직접 조회합니다.
        캐시를 사용하지 않습니다.
        """
        from api_client import fetch_client_information
        
        try:
            success, clients = fetch_client_information(site)
            if success and clients:
                return clients if isinstance(clients, list) else []
            return []
        except Exception as e:
            logger.error(f"Resident data fetch failed for {site}: {e}")
            return []
    
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
            logger.info("Starting daily 3 AM resident data check")
            results = self.refresh_all_sites()
            
            success_count = results['success_count']
            total_sites = results['total_sites']
            total_clients = results['total_clients']
            
            logger.info(
                f"Daily automatic check completed: {success_count}/{total_sites} sites succeeded, "
                f"total {total_clients} residents"
            )
        
        # 스케줄 설정 - 매일 새벽 3시만
        schedule.every().day.at("03:00").do(daily_sync_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 스케줄 확인
        
        # 백그라운드 스레드로 실행
        sync_thread = threading.Thread(target=run_scheduler, daemon=False)
        sync_thread.start()
        
        logger.info("Background sync started (daily at 3 AM)")


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
            app.logger.info("Client sync manager initialized")
        
        return True
        
    except Exception as e:
        if app:
            app.logger.error(f"Failed to initialize client sync manager: {e}")
        else:
            logger.error(f"Failed to initialize client sync manager: {e}")
        return False


# 명령줄에서 직접 실행 시 테스트
if __name__ == "__main__":
    print("Client Sync Manager test")
    
    try:
        manager = ClientSyncManager()
        
        # 현재 동기화 상태 확인
        print("\nCurrent sync status:")
        status = manager.get_sync_status_summary()
        for site, info in status.items():
            age = info['cache_age_minutes']
            age_str = f"{age} min ago" if age is not None else "N/A"
            expired = "expired" if info['is_expired'] else "valid"
            print(f"  {site}: {info['records']} residents, last sync {age_str} ({expired})")
        
        # 테스트: 한 사이트 새로고침
        print("\nParafield Gardens refresh test...")
        result = manager.refresh_site_clients('Parafield Gardens')
        
        if result['success']:
            changes = result['changes']
            print(f"✅ Success: added {changes['added']}, updated {changes['updated']}, removed {changes['removed']}")
        else:
            print(f"❌ Failed: {result['message']}")
        
        # 캐시된 클라이언트 조회 테스트
        print("\nCached client fetch test...")
        clients = manager.get_clients_with_auto_refresh('Parafield Gardens')
        print(f"Fetched clients: {len(clients)}")
        
        if clients:
            print("First 3:")
            for i, client in enumerate(clients[:3]):
                print(f"  {i+1}. {client['client_name']} (Room: {client['room_number']})")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
