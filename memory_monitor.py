#!/usr/bin/env python3
"""
Memory Monitor for Flask Application
Server memory usage monitoring and leak detection
"""

import os
import gc
import sys
import threading
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# psutil is an optional dependency (basic functionality works without it)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil is not installed. Memory monitoring is limited. Install: pip install psutil")

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Memory Usage Monitoring Class"""
    
    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: Memory check interval (seconds)
        """
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.memory_history: List[Dict[str, Any]] = []
        self.max_history_size = 100  # Keep maximum 100 records
        
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process(os.getpid())
        else:
            self.process = None
        
        self.initial_memory = self._get_memory_info()
        
    def _get_memory_info(self) -> Dict[str, Any]:
        """Return current memory usage information"""
        if not PSUTIL_AVAILABLE:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': 'psutil is not installed. Install it with pip install psutil.',
                'psutil_required': True
            }
        
        try:
            mem_info = self.process.memory_info()
            mem_percent = self.process.memory_percent()
            
            # System-wide memory information
            system_mem = psutil.virtual_memory()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'rss_mb': round(mem_info.rss / 1024 / 1024, 2),  # Resident Set Size (actual memory)
                'vms_mb': round(mem_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
                'percent': round(mem_percent, 2),
                'available_mb': round(system_mem.available / 1024 / 1024, 2),
                'system_total_mb': round(system_mem.total / 1024 / 1024, 2),
                'system_percent': round(system_mem.percent, 2),
            }
        except Exception as e:
            logger.error(f"Error collecting memory info: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_current_memory(self) -> Dict[str, Any]:
        """Return current memory usage"""
        current = self._get_memory_info()
        
        # Compare with initial memory
        if 'rss_mb' in current and 'rss_mb' in self.initial_memory:
            current['increase_mb'] = round(
                current['rss_mb'] - self.initial_memory['rss_mb'], 2
            )
            current['increase_percent'] = round(
                (current['rss_mb'] - self.initial_memory['rss_mb']) / self.initial_memory['rss_mb'] * 100, 2
            ) if self.initial_memory['rss_mb'] > 0 else 0
        
        # Garbage collection statistics
        gc_stats = gc.get_stats()
        current['gc_stats'] = {
            'collections': sum(stat['collections'] for stat in gc_stats),
            'collected': sum(stat['collected'] for stat in gc_stats),
        }
        
        # Thread count
        try:
            current['thread_count'] = threading.active_count()
        except:
            current['thread_count'] = 0
        
        return current
    
    def get_memory_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return memory usage history"""
        return self.memory_history[-limit:]
    
    def detect_memory_leak(self) -> Optional[Dict[str, Any]]:
        """Detect memory leak"""
        if len(self.memory_history) < 10:
            return None
        
        # Calculate average increase rate of recent 10 records
        recent = self.memory_history[-10:]
        rss_values = [m.get('rss_mb', 0) for m in recent if 'rss_mb' in m]
        
        if len(rss_values) < 10:
            return None
        
        # Check linear increasing trend
        first_half = sum(rss_values[:5]) / 5
        second_half = sum(rss_values[5:]) / 5
        
        increase = second_half - first_half
        increase_percent = (increase / first_half * 100) if first_half > 0 else 0
        
        # Suspect leak if increase is 10% or more
        if increase_percent > 10:
            return {
                'leak_detected': True,
                'increase_mb': round(increase, 2),
                'increase_percent': round(increase_percent, 2),
                'current_mb': round(rss_values[-1], 2),
                'recommendation': 'A memory leak is suspected. Run garbage collection or restart the server.'
            }
        
        return None
    
    def start_monitoring(self):
        """Start memory monitoring"""
        if self.monitoring:
            logger.warning("Memory monitoring is already running.")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"Memory monitoring started (interval: {self.check_interval}s)")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            try:
                self.monitor_thread.join(timeout=5)
            except Exception as e:
                logger.warning(f"Error while stopping memory monitoring thread (can be ignored): {e}")
        logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self):
        """Monitoring loop"""
        while self.monitoring:
            try:
                mem_info = self._get_memory_info()
                self.memory_history.append(mem_info)
                
                # Limit history size
                if len(self.memory_history) > self.max_history_size:
                    self.memory_history.pop(0)
                
                # Warn if memory usage is high
                if 'rss_mb' in mem_info:
                    if mem_info['rss_mb'] > 1000:  # 1GB or more
                        logger.warning(
                            f"⚠️ High memory usage: {mem_info['rss_mb']}MB "
                            f"({mem_info['percent']}%)"
                        )
                    
                    # Detect leak
                    leak_info = self.detect_memory_leak()
                    if leak_info:
                        logger.warning(
                            f"🚨 Memory leak detected: +{leak_info['increase_mb']}MB "
                            f"({leak_info['increase_percent']}%)"
                        )
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
            
            time.sleep(self.check_interval)
    
    def force_gc(self) -> Dict[str, Any]:
        """Force garbage collection"""
        before = self._get_memory_info()
        
        # Run garbage collection for all generations
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
        """Memory usage summary information"""
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


# Global instance
_memory_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor() -> MemoryMonitor:
    """Return memory monitor instance"""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(check_interval=60)
    return _memory_monitor

def start_memory_monitoring():
    """Start memory monitoring"""
    monitor = get_memory_monitor()
    monitor.start_monitoring()

def stop_memory_monitoring():
    """Stop memory monitoring"""
    global _memory_monitor
    if _memory_monitor:
        _memory_monitor.stop_monitoring()

