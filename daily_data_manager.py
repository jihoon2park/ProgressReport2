#!/usr/bin/env python3
"""
Daily Data Manager
매일 최초 접속시에만 Care Area와 Event Type 데이터를 수집하는 매니저
"""

import json
import os
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DailyDataManager:
    """일일 데이터 수집 관리자"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.daily_status_file = os.path.join(data_dir, "daily_status.json")
        self._ensure_directories()
    
    def _ensure_directories(self):
        """필요한 디렉토리 생성"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_daily_status(self) -> Dict[str, Any]:
        """일일 상태 로드"""
        try:
            if not os.path.exists(self.daily_status_file):
                return {}
            
            with open(self.daily_status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"일일 상태 로드 실패: {e}")
            return {}
    
    def _save_daily_status(self, status: Dict[str, Any]) -> bool:
        """일일 상태 저장"""
        try:
            with open(self.daily_status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"일일 상태 저장 실패: {e}")
            return False
    
    def is_first_access_today(self) -> bool:
        """오늘 최초 접속인지 확인"""
        today = date.today().isoformat()
        status = self._load_daily_status()
        
        last_access = status.get('last_access_date')
        if last_access != today:
            # 오늘 최초 접속
            status['last_access_date'] = today
            status['care_area_collected'] = False
            status['event_type_collected'] = False
            self._save_daily_status(status)
            return True
        
        return False
    
    def mark_care_area_collected(self):
        """Care Area 수집 완료 표시"""
        status = self._load_daily_status()
        status['care_area_collected'] = True
        self._save_daily_status(status)
        logger.info("Care Area 수집 완료 표시")
    
    def mark_event_type_collected(self):
        """Event Type 수집 완료 표시"""
        status = self._load_daily_status()
        status['event_type_collected'] = True
        self._save_daily_status(status)
        logger.info("Event Type 수집 완료 표시")
    
    def should_collect_care_area(self) -> bool:
        """Care Area를 수집해야 하는지 확인"""
        if self.is_first_access_today():
            return True
        
        status = self._load_daily_status()
        return not status.get('care_area_collected', False)
    
    def should_collect_event_type(self) -> bool:
        """Event Type을 수집해야 하는지 확인"""
        if self.is_first_access_today():
            return True
        
        status = self._load_daily_status()
        return not status.get('event_type_collected', False)
    
    def collect_care_area_data(self, site: str) -> bool:
        """Care Area 데이터 수집"""
        try:
            from api_carearea import APICareArea
            
            logger.info(f"Care Area 데이터 수집 시작 - 사이트: {site}")
            api_carearea = APICareArea(site)
            care_area_data = api_carearea.get_care_area_information()
            
            if care_area_data:
                self.mark_care_area_collected()
                logger.info(f"Care Area 데이터 수집 완료 - 사이트: {site}")
                return True
            else:
                logger.warning(f"Care Area 데이터 수집 실패 - 사이트: {site}")
                return False
                
        except Exception as e:
            logger.error(f"Care Area 데이터 수집 중 오류 - 사이트: {site}, 오류: {e}")
            return False
    
    def collect_event_type_data(self, site: str) -> bool:
        """Event Type 데이터 수집"""
        try:
            from api_eventtype import APIEventType
            
            logger.info(f"Event Type 데이터 수집 시작 - 사이트: {site}")
            api_eventtype = APIEventType(site)
            event_type_data = api_eventtype.get_event_type_information()
            
            if event_type_data:
                self.mark_event_type_collected()
                logger.info(f"Event Type 데이터 수집 완료 - 사이트: {site}")
                return True
            else:
                logger.warning(f"Event Type 데이터 수집 실패 - 사이트: {site}")
                return False
                
        except Exception as e:
            logger.error(f"Event Type 데이터 수집 중 오류 - 사이트: {site}, 오류: {e}")
            return False
    
    def collect_daily_data_if_needed(self, site: str) -> Dict[str, bool]:
        """필요시 일일 데이터 수집"""
        results = {
            'care_area': False,
            'event_type': False
        }
        
        # Care Area 수집 확인
        if self.should_collect_care_area():
            results['care_area'] = self.collect_care_area_data(site)
        
        # Event Type 수집 확인
        if self.should_collect_event_type():
            results['event_type'] = self.collect_event_type_data(site)
        
        return results

# 전역 인스턴스
daily_data_manager = DailyDataManager()
