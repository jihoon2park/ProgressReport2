#!/usr/bin/env python3
"""
Progress Report System - Client Synchronization Manager
Automatically update SQLite cache when new residents are added/changed
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

# Import unified function from api_client
try:
    from api_client import fetch_client_information
except ImportError:
    print("Warning: api_client module not found. Some features may be limited.")

logger = logging.getLogger(__name__)

class ClientSyncManager:
    """Client data synchronization manager"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        self.cache_expiry_minutes = 30  # Cache expiry time (30 minutes)
        self.sync_interval_minutes = 30  # Auto sync interval (30 minutes)
        self.sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
    
    def get_db_connection(self):
        """Connect to database"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def is_cache_expired(self, site: str) -> bool:
        """Check if cache is expired"""
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
                return True  # Consider expired if no sync record exists
            
            last_sync = datetime.fromisoformat(result['last_sync_time'])
            expiry_time = datetime.now() - timedelta(minutes=self.cache_expiry_minutes)
            
            return last_sync < expiry_time
            
        except Exception as e:
            logger.error(f"Failed to check cache expiry ({site}): {e}")
            return True  # Consider expired on error
    
    def get_cache_age(self, site: str) -> Optional[int]:
        """Return cache age in minutes"""
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
            
            return int(age.total_seconds() / 60)  # In minutes
            
        except Exception as e:
            logger.error(f"Failed to check cache age ({site}): {e}")
            return None
    
    def refresh_site_clients(self, site: str) -> Dict[str, Any]:
        """
        Refresh resident data for specific site (simplified)
        
        In direct DB access mode, latest data is queried each time,
        so separate cache updates are unnecessary.
        """
        result = {
            'success': False,
            'site': site,
            'message': '',
            'client_count': 0
        }
        
        try:
            logger.info(f"Starting resident data fetch for {site}")
            
            # Get latest data from DB (direct query without cache)
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
    
    # update_sqlite_cache method removed
    # Cache updates unnecessary in direct DB access mode as latest data is queried each time
    
    def refresh_all_sites(self) -> Dict[str, Any]:
        """Refresh resident data for all sites"""
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
        Get resident data (simplified)
        
        In direct DB access mode, latest data is queried directly each time.
        Cache is not used.
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
        """Get synchronization status summary"""
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
        """Start background synchronization"""
        def daily_sync_job():
            """Daily synchronization job at 3 AM"""
            logger.info("Starting daily 3 AM resident data check")
            results = self.refresh_all_sites()
            
            success_count = results['success_count']
            total_sites = results['total_sites']
            total_clients = results['total_clients']
            
            logger.info(
                f"Daily automatic check completed: {success_count}/{total_sites} sites succeeded, "
                f"total {total_clients} residents"
            )
        
        # Set schedule - daily at 3 AM only
        schedule.every().day.at("03:00").do(daily_sync_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check schedule every minute
        
        # Run in background thread
        sync_thread = threading.Thread(target=run_scheduler, daemon=False)
        sync_thread.start()
        
        logger.info("Background sync started (daily at 3 AM)")


# Global instance for Flask app
client_sync_manager = None

def get_client_sync_manager():
    """Client synchronization manager singleton instance"""
    global client_sync_manager
    if client_sync_manager is None:
        client_sync_manager = ClientSyncManager()
    return client_sync_manager

def init_client_sync(app=None):
    """Called when Flask app initializes"""
    try:
        manager = get_client_sync_manager()
        
        # Start background synchronization
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


# Test when run directly from command line
if __name__ == "__main__":
    print("Client Sync Manager test")
    
    try:
        manager = ClientSyncManager()
        
        # Check current sync status
        print("\nCurrent sync status:")
        status = manager.get_sync_status_summary()
        for site, info in status.items():
            age = info['cache_age_minutes']
            age_str = f"{age} min ago" if age is not None else "N/A"
            expired = "expired" if info['is_expired'] else "valid"
            print(f"  {site}: {info['records']} residents, last sync {age_str} ({expired})")
        
        # Test: refresh one site
        print("\nParafield Gardens refresh test...")
        result = manager.refresh_site_clients('Parafield Gardens')
        
        if result['success']:
            print(f"✅ Success: {result['client_count']} residents")
        else:
            print(f"❌ Failed: {result['message']}")
        
        # Test cached client fetch
        print("\nCached client fetch test...")
        clients = manager.get_clients_with_auto_refresh('Parafield Gardens')
        print(f"Fetched clients: {len(clients)}")
        
        if clients:
            print("First 3:")
            for i, client in enumerate(clients[:3]):
                client_name = client.get('ClientName') or client.get('client_name', 'Unknown')
                print(f"  {i+1}. {client_name}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
