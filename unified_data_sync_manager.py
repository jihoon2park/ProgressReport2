#!/usr/bin/env python3
"""
Unified Data Sync Manager - Unified Data Synchronization Manager
System that synchronizes all data daily at 3 AM
"""

import sqlite3
import json
import os
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Directly import required functions (prevent circular imports)
try:
    from api_client import get_api_client, fetch_client_information
    from config import SITE_SERVERS
except ImportError as e:
    print(f"Warning: some modules could not be found: {e}")
    SITE_SERVERS = {}

# Optional imports (continue even if failed)
try:
    from api_carearea import APICareArea
except ImportError:
    APICareArea = None

try:
    from api_eventtype import APIEventType
except ImportError:
    APIEventType = None

try:
    from manad_db_connector import fetch_incidents_with_client_data_from_db
except ImportError:
    fetch_incidents_with_client_data_from_db = None

logger = logging.getLogger(__name__)

class UnifiedDataSyncManager:
    """Unified data synchronization manager"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        self.sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        # Check if database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
    
    def get_db_connection(self):
        """Connect to database"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn
    
    def update_sync_status(self, data_type: str, site: Optional[str] = None, 
                          status: str = 'success', records: int = 0, error: str = None):
        """Update synchronization status"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Set timeout
            cursor.execute('PRAGMA busy_timeout = 30000')  # 30 second timeout
            
            cursor.execute('''
                INSERT OR REPLACE INTO sync_status 
                (data_type, site, last_sync_time, sync_status, records_synced, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data_type, site, datetime.now().isoformat(), status, records, error))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update sync status: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def sync_clients_data(self) -> Dict[str, Any]:
        """
        Synchronize client data (simplified)
        
        In direct DB access mode, latest data is queried each time,
        so separate cache updates are unnecessary.
        Only synchronization status is recorded.
        """
        logger.info("🔄 Starting resident data sync status check")
        results = {'success': 0, 'failed': 0, 'total_clients': 0}
        
        for site in self.sites:
            try:
                logger.info(f"  📍 Checking resident data for {site}...")
                
                # Get latest data from DB (direct query without cache)
                api_success, latest_clients = fetch_client_information(site)
                
                if not api_success:
                    logger.error(f"  ❌ Unable to fetch resident data for {site}")
                    self.update_sync_status('clients', site, 'failed', 0, 'Data fetch failed')
                    results['failed'] += 1
                    continue
                
                client_count = len(latest_clients) if latest_clients else 0
                self.update_sync_status('clients', site, 'success', client_count)
                results['success'] += 1
                results['total_clients'] += client_count
                
                logger.info(f"  ✅ {site} completed: {client_count} residents")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to check resident data for {site}: {e}")
                self.update_sync_status('clients', site, 'failed', 0, str(e))
                results['failed'] += 1
        
        logger.info(
            f"🔄 Resident data sync status check completed: "
            f"{results['success']}/{len(self.sites)} sites succeeded, total {results['total_clients']} residents"
        )
        return results
    
    def sync_care_areas_data(self) -> Dict[str, Any]:
        """Synchronize care area data"""
        logger.info("🔄 Starting care area data sync")
        
        if APICareArea is None:
            logger.warning("⚠️ APICareArea module not found. Skipping care area sync.")
            return {'success': False, 'message': 'APICareArea module not found'}
        
        try:
            # Get care area data from API (using first site)
            api_carearea = APICareArea(self.sites[0])  # Use Parafield Gardens
            care_areas = api_carearea.get_care_area_information()
            
            if not care_areas:
                logger.error("❌ Unable to fetch care area data from API")
                self.update_sync_status('carearea', None, 'failed', 0, 'API call failed')
                return {'success': False, 'message': 'API call failed'}
            
            # Update SQLite cache
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
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
            
            conn.commit()
            conn.close()
            
            self.update_sync_status('carearea', None, 'success', len(care_areas))
            logger.info(f"✅ Care area sync completed: {len(care_areas)} items")
            
            return {'success': True, 'records': len(care_areas)}
            
        except Exception as e:
            logger.error(f"❌ Care area sync failed: {e}")
            self.update_sync_status('carearea', None, 'failed', 0, str(e))
            return {'success': False, 'message': str(e)}
    
    def sync_event_types_data(self) -> Dict[str, Any]:
        """Synchronize event type data"""
        logger.info("🔄 Starting event type data sync")
        
        if APIEventType is None:
            logger.warning("⚠️ APIEventType module not found. Skipping event type sync.")
            return {'success': False, 'message': 'APIEventType module not found'}
        
        try:
            # Get event type data from API (using first site)
            api_eventtype = APIEventType(self.sites[0])  # Use Parafield Gardens
            event_types = api_eventtype.get_event_type_information()
            
            if not event_types:
                logger.error("❌ Unable to fetch event type data from API")
                self.update_sync_status('eventtype', None, 'failed', 0, 'API call failed')
                return {'success': False, 'message': 'API call failed'}
            
            # Update SQLite cache
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            for event_type in event_types:
                cursor.execute('''
                    INSERT OR REPLACE INTO event_types 
                    (id, description, color_argb, is_archived, is_external, last_updated_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_type['Id'],
                    event_type['Description'],
                    event_type.get('ColorArgb'),
                    event_type.get('IsArchived', False),
                    event_type.get('IsExternal', False),
                    event_type.get('LastUpdatedDate')
                ))
            
            conn.commit()
            conn.close()
            
            self.update_sync_status('eventtype', None, 'success', len(event_types))
            logger.info(f"✅ Event type sync completed: {len(event_types)} items")
            
            return {'success': True, 'records': len(event_types)}
            
        except Exception as e:
            logger.error(f"❌ Event type sync failed: {e}")
            self.update_sync_status('eventtype', None, 'failed', 0, str(e))
            return {'success': False, 'message': str(e)}
    
    def sync_incidents_data(self) -> Dict[str, Any]:
        """Synchronize incident data (direct DB access)"""
        logger.info("🔄 Starting incident data sync (direct DB access)")
        results = {'success': 0, 'failed': 0, 'total_incidents': 0}
        
        if fetch_incidents_with_client_data_from_db is None:
            logger.warning("⚠️ fetch_incidents_with_client_data_from_db function not found. Skipping incident sync.")
            return {'success': False, 'message': 'fetch_incidents_with_client_data_from_db function not found'}
        
        # Synchronize incident data for the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        for site in self.sites:
            try:
                logger.info(f"  📍 Syncing incidents for {site}... (direct DB access)")
                
                # Get incident data directly from DB
                incident_data = fetch_incidents_with_client_data_from_db(
                    site, 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d'),
                    fetch_clients=False
                )
                
                if not incident_data or 'incidents' not in incident_data:
                    logger.error(f"  ❌ Unable to fetch incident data for {site}")
                    self.update_sync_status('incidents', site, 'failed', 0, 'DB query failed')
                    results['failed'] += 1
                    continue
                
                incidents = incident_data['incidents']
                
                # Update SQLite cache
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                try:
                    # Set timeout
                    cursor.execute('PRAGMA busy_timeout = 30000')  # 30 second timeout
                    
                    for incident in incidents:
                        # Skip if incident_id is missing
                        incident_id = incident.get('IncidentId') or incident.get('Id') or incident.get('incident_id')
                        if not incident_id:
                            logger.warning(f"  ⚠️ Skipping incident with no ID for {site}: {incident}")
                            continue
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO incidents_cache 
                            (incident_id, client_id, client_name, incident_type, incident_date, 
                             description, severity, status, site, reported_by, last_synced)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            str(incident_id),  # Convert to string
                            incident.get('ClientId'),
                            incident.get('ClientName'),
                            incident.get('IncidentType'),
                            incident.get('IncidentDate'),
                            incident.get('Description'),
                            incident.get('Severity'),
                            incident.get('Status'),
                            site,
                            incident.get('ReportedBy'),
                            datetime.now().isoformat()
                        ))
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    raise e
                finally:
                    conn.close()
                
                self.update_sync_status('incidents', site, 'success', len(incidents))
                results['success'] += 1
                results['total_incidents'] += len(incidents)
                
                logger.info(f"  ✅ {site} completed: {len(incidents)} incidents")
                
            except Exception as e:
                logger.error(f"  ❌ Incident sync failed for {site}: {e}")
                self.update_sync_status('incidents', site, 'failed', 0, str(e))
                results['failed'] += 1
        
        logger.info(
            f"🔄 Incident data sync completed: {results['success']}/{len(self.sites)} sites succeeded, "
            f"total {results['total_incidents']} incidents"
        )
        return results
    
    # _update_clients_cache method removed
    # Cache updates unnecessary in direct DB access mode as latest data is queried each time
    
    def run_full_sync(self) -> Dict[str, Any]:
        """Run full data synchronization"""
        logger.info("🌅 Starting unified data sync at 3 AM")
        start_time = datetime.now()
        
        results = {
            'start_time': start_time.isoformat(),
            'clients': {},
            'care_areas': {},
            'event_types': {},
            'incidents': {},
            'summary': {
                'total_success': 0,
                'total_failed': 0,
                'total_records': 0
            }
        }
        
        try:
            # 1. Check resident data synchronization status
            results['clients'] = self.sync_clients_data()
            results['summary']['total_success'] += results['clients']['success']
            results['summary']['total_failed'] += results['clients']['failed']
            results['summary']['total_records'] += results['clients']['total_clients']
            
            # 2. Synchronize care area data
            results['care_areas'] = self.sync_care_areas_data()
            if results['care_areas']['success']:
                results['summary']['total_success'] += 1
                results['summary']['total_records'] += results['care_areas']['records']
            else:
                results['summary']['total_failed'] += 1
            
            # 3. Synchronize event type data
            results['event_types'] = self.sync_event_types_data()
            if results['event_types']['success']:
                results['summary']['total_success'] += 1
                results['summary']['total_records'] += results['event_types']['records']
            else:
                results['summary']['total_failed'] += 1
            
            # 4. Synchronize incident data
            results['incidents'] = self.sync_incidents_data()
            results['summary']['total_success'] += results['incidents']['success']
            results['summary']['total_failed'] += results['incidents']['failed']
            results['summary']['total_records'] += results['incidents']['total_incidents']
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = duration
            
            logger.info(f"🌅 Unified data sync completed: {duration:.1f}s")
            logger.info(
                f"📊 Result: success {results['summary']['total_success']}, "
                f"failed {results['summary']['total_failed']}, "
                f"total {results['summary']['total_records']} records"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Unified data sync failed: {e}")
            results['error'] = str(e)
            return results
    
    def start_daily_sync(self):
        """Start synchronization scheduler at 3 AM daily"""
        def daily_sync_job():
            """Daily synchronization job at 3 AM"""
            logger.info("🌅 Starting unified data sync at 3 AM")
            results = self.run_full_sync()
            
            # Log results
            if 'error' in results:
                logger.error(f"❌ Sync failed: {results['error']}")
            else:
                logger.info(f"✅ Sync completed: processed {results['summary']['total_records']} records")
        
        # Set schedule - daily at 3 AM
        schedule.every().day.at("03:00").do(daily_sync_job)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check schedule every minute
        
        # Run in background thread
        sync_thread = threading.Thread(target=run_scheduler, daemon=False)
        sync_thread.start()
        
        logger.info("🌅 Unified data sync scheduler started (daily at 3 AM)")


# Global instance for Flask app
unified_sync_manager = None

def get_unified_sync_manager():
    """Unified data synchronization manager singleton instance"""
    global unified_sync_manager
    if unified_sync_manager is None:
        unified_sync_manager = UnifiedDataSyncManager()
    return unified_sync_manager

def init_unified_sync():
    """Called when Flask app initializes"""
    try:
        manager = get_unified_sync_manager()
        manager.start_daily_sync()
        logger.info("✅ Unified data sync manager initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified data sync manager: {e}")
        return False


# Test when run directly from command line
if __name__ == "__main__":
    print("🌅 Unified Data Sync Manager test")
    
    try:
        manager = UnifiedDataSyncManager()
        
        # Manually run full synchronization
        print("\n🔄 Running full data sync...")
        results = manager.run_full_sync()
        
        print(f"\n📊 Sync results:")
        print(f"  - Clients: {results['clients']['success']}/{len(manager.sites)} sites succeeded")
        print(f"  - Care areas: {'success' if results['care_areas']['success'] else 'failed'}")
        print(f"  - Event types: {'success' if results['event_types']['success'] else 'failed'}")
        print(f"  - Incidents: {results['incidents']['success']}/{len(manager.sites)} sites succeeded")
        print(f"  - Total records: {results['summary']['total_records']}")
        print(f"  - Duration: {results.get('duration_seconds', 0):.1f}s")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def init_unifiedd_sync():
    """Unified data synchronization initialization function"""
    try:
        manager = UnifiedDataSyncManager()
        manager.start_background_sync()
        logger.info("✅ Unified data sync manager initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified data sync manager: {e}")
        return False
