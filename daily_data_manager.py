#!/usr/bin/env python3
"""
Daily Data Manager
Manager that collects Care Area and Event Type data only on first access each day
"""

import json
import os
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DailyDataManager:
    """Daily Data Collection Manager"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.daily_status_file = os.path.join(data_dir, "daily_status.json")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_daily_status(self) -> Dict[str, Any]:
        """Load daily status"""
        try:
            if not os.path.exists(self.daily_status_file):
                return {}
            
            with open(self.daily_status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load daily status: {e}")
            return {}
    
    def _save_daily_status(self, status: Dict[str, Any]) -> bool:
        """Save daily status"""
        try:
            with open(self.daily_status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save daily status: {e}")
            return False
    
    def is_first_access_today(self) -> bool:
        """Check if this is the first access today"""
        today = date.today().isoformat()
        status = self._load_daily_status()
        
        last_access = status.get('last_access_date')
        if last_access != today:
            # First access today
            status['last_access_date'] = today
            status['care_area_collected'] = False
            status['event_type_collected'] = False
            self._save_daily_status(status)
            return True
        
        return False
    
    def mark_care_area_collected(self):
        """Mark Care Area collection as complete"""
        status = self._load_daily_status()
        status['care_area_collected'] = True
        self._save_daily_status(status)
        logger.info("Care Area collection marked as complete")
    
    def mark_event_type_collected(self):
        """Mark Event Type collection as complete"""
        status = self._load_daily_status()
        status['event_type_collected'] = True
        self._save_daily_status(status)
        logger.info("Event Type collection marked as complete")
    
    def should_collect_care_area(self) -> bool:
        """Check if Care Area should be collected"""
        if self.is_first_access_today():
            return True
        
        status = self._load_daily_status()
        return not status.get('care_area_collected', False)
    
    def should_collect_event_type(self) -> bool:
        """Check if Event Type should be collected"""
        if self.is_first_access_today():
            return True
        
        status = self._load_daily_status()
        return not status.get('event_type_collected', False)
    
    def collect_care_area_data(self, site: str) -> bool:
        """Collect Care Area data"""
        try:
            from api_carearea import APICareArea
            
            logger.info(f"Starting Care Area data collection - Site: {site}")
            api_carearea = APICareArea(site)
            care_area_data = api_carearea.get_care_area_information()
            
            if care_area_data:
                self.mark_care_area_collected()
                logger.info(f"Care Area data collection completed - Site: {site}")
                return True
            else:
                logger.warning(f"Care Area data collection failed - Site: {site}")
                return False
                
        except Exception as e:
            logger.error(f"Error during Care Area data collection - Site: {site}, Error: {e}")
            return False
    
    def collect_event_type_data(self, site: str) -> bool:
        """Collect Event Type data"""
        try:
            from api_eventtype import APIEventType
            
            logger.info(f"Starting Event Type data collection - Site: {site}")
            api_eventtype = APIEventType(site)
            event_type_data = api_eventtype.get_event_type_information()
            
            if event_type_data:
                self.mark_event_type_collected()
                logger.info(f"Event Type data collection completed - Site: {site}")
                return True
            else:
                logger.warning(f"Event Type data collection failed - Site: {site}")
                return False
                
        except Exception as e:
            logger.error(f"Error during Event Type data collection - Site: {site}, Error: {e}")
            return False
    
    def collect_daily_data_if_needed(self, site: str) -> Dict[str, bool]:
        """Collect daily data if needed"""
        results = {
            'care_area': False,
            'event_type': False
        }
        
        # Check Care Area collection
        if self.should_collect_care_area():
            results['care_area'] = self.collect_care_area_data(site)
        
        # Check Event Type collection
        if self.should_collect_event_type():
            results['event_type'] = self.collect_event_type_data(site)
        
        return results

# Global instance
daily_data_manager = DailyDataManager()
