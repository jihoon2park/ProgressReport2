#!/usr/bin/env python3
"""
Memory Monitor for Flask Application
서버 메모리 사용량 모니터링 및 누수 감지
"""

import os
import gc
import sys
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# psutil은 선택적 의존성 (없어도 기본 기능은 작동)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil이 설치되지 않았습니다. 메모리 모니터링 기능이 제한됩니다. 설치: pip install psutil")

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """메모리 사용량 모니터링 클래스"""
    
    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: 메모리 체크 간격 (초)
        """
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.memory_history: List[Dict[str, Any]] = []
        self.max_history_size = 100  # 최대 100개 기록 보관
        
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
        
        self.initial_memory = self._get_memory_info()
        
    def _get_memory_info(self) -> Dict[str, Any]:
        """현재 메모리 사용량 정보 반환"""
        if not PSUTIL_AVAILABLE:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': 'psutil이 설치되지 않았습니다. pip install psutil로 설치하세요.',
                'psutil_required': True
            }
        
        try:
            mem_info = self.process.memory_info()
            mem_percent = self.process.memory_percent()
            
            # 시스템 전체 메모리 정보
            system_mem = psutil.virtual_memory()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'rss_mb': round(mem_info.rss / 1024 / 1024, 2),  # Resident Set Size (실제 메모리)
                'vms_mb': round(mem_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
                'percent': round(mem_percent, 2),
                'available_mb': round(system_mem.available / 1024 / 1024, 2),
                'system_total_mb': round(system_mem.total / 1024 / 1024, 2),
                'system_percent': round(system_mem.percent, 2),
            }
        except Exception as e:
            logger.error(f"메모리 정보 수집 오류: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_current_memory(self) -> Dict[str, Any]:
        """현재 메모리 사용량 반환"""
        current = self._get_memory_info()
        
        # 초기 메모리와 비교
        if 'rss_mb' in current and 'rss_mb' in self.initial_memory:
            current['increase_mb'] = round(
                current['rss_mb'] - self.initial_memory['rss_mb'], 2
            )
            current['increase_percent'] = round(
                (current['rss_mb'] - self.initial_memory['rss_mb']) / self.initial_memory['rss_mb'] * 100, 2
            ) if self.initial_memory['rss_mb'] > 0 else 0
        
        # 가비지 컬렉션 통계
        gc_stats = gc.get_stats()
        current['gc_stats'] = {
            'collections': sum(stat['collections'] for stat in gc_stats),
            'collected': sum(stat['collected'] for stat in gc_stats),
        }
        
        # 스레드 수
        try:
            current['thread_count'] = threading.active_count()
        except:
            current['thread_count'] = 0
        
        return current
    
    def get_memory_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """메모리 사용량 히스토리 반환"""
        return self.memory_history[-limit:]
    
    def detect_memory_leak(self) -> Optional[Dict[str, Any]]:
        """메모리 누수 감지"""
        if len(self.memory_history) < 10:
            return None
        
        # 최근 10개 기록의 평균 증가율 계산
        recent = self.memory_history[-10:]
        rss_values = [m.get('rss_mb', 0) for m in recent if 'rss_mb' in m]
        
        if len(rss_values) < 10:
            return None
        
        # 선형 증가 추세 확인
        first_half = sum(rss_values[:5]) / 5
        second_half = sum(rss_values[5:]) / 5
        
        increase = second_half - first_half
        increase_percent = (increase / first_half * 100) if first_half > 0 else 0
        
        # 10% 이상 증가하면 누수 의심
        if increase_percent > 10:
            return {
                'leak_detected': True,
                'increase_mb': round(increase, 2),
                'increase_percent': round(increase_percent, 2),
                'current_mb': round(rss_values[-1], 2),
                'recommendation': '메모리 누수가 의심됩니다. 가비지 컬렉션을 실행하거나 서버를 재시작하세요.'
            }
        
        return None
    
    def start_monitoring(self):
        """메모리 모니터링 시작"""
        if self.monitoring:
            logger.warning("메모리 모니터링이 이미 실행 중입니다.")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"메모리 모니터링 시작됨 (간격: {self.check_interval}초)")
    
    def stop_monitoring(self):
        """메모리 모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("메모리 모니터링 중지됨")
    
    def _monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            try:
                mem_info = self._get_memory_info()
                self.memory_history.append(mem_info)
                
                # 히스토리 크기 제한
                if len(self.memory_history) > self.max_history_size:
                    self.memory_history.pop(0)
                
                # 메모리 사용량이 높으면 경고
                if 'rss_mb' in mem_info:
                    if mem_info['rss_mb'] > 1000:  # 1GB 이상
                        logger.warning(
                            f"⚠️ 높은 메모리 사용량: {mem_info['rss_mb']}MB "
                            f"({mem_info['percent']}%)"
                        )
                    
                    # 누수 감지
                    leak_info = self.detect_memory_leak()
                    if leak_info:
                        logger.warning(
                            f"🚨 메모리 누수 감지: {leak_info['increase_mb']}MB 증가 "
                            f"({leak_info['increase_percent']}%)"
                        )
                
            except Exception as e:
                logger.error(f"메모리 모니터링 오류: {e}")
            
            time.sleep(self.check_interval)
    
    def force_gc(self) -> Dict[str, Any]:
        """가비지 컬렉션 강제 실행"""
        before = self._get_memory_info()
        
        # 모든 세대의 가비지 컬렉션 실행
        collected = gc.collect()
        
        after = self._get_memory_info()
        
        freed_mb = 0
        if 'rss_mb' in before and 'rss_mb' in after:
            freed_mb = round(before['rss_mb'] - after['rss_mb'], 2)
        
        return {
            'collected_objects': collected,
            'freed_mb': freed_mb,
            'before_mb': before.get('rss_mb', 0),
            'after_mb': after.get('rss_mb', 0),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """메모리 사용량 요약 정보"""
        current = self.get_current_memory()
        leak_info = self.detect_memory_leak()
        
        summary = {
            'current': current,
            'initial': self.initial_memory,
            'monitoring': self.monitoring,
            'history_count': len(self.memory_history),
        }
        
        if leak_info:
            summary['leak_detected'] = leak_info
        
        return summary


# 전역 인스턴스
_memory_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor() -> MemoryMonitor:
    """메모리 모니터 인스턴스 반환"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(check_interval=60)
    return _memory_monitor

def start_memory_monitoring():
    """메모리 모니터링 시작"""
    monitor = get_memory_monitor()
    monitor.start_monitoring()

def stop_memory_monitoring():
    """메모리 모니터링 중지"""
    global _memory_monitor
    if _memory_monitor:
        _memory_monitor.stop_monitoring()

