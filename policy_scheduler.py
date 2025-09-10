"""
Policy-driven Task Scheduler
정책 기반 작업 스케줄러 - 백그라운드에서 실행되는 알림 전송 시스템
"""

import threading
import time
import schedule
import logging
from datetime import datetime, timedelta
from task_manager import get_task_manager

logger = logging.getLogger(__name__)

class PolicyScheduler:
    """정책 기반 스케줄러 클래스"""
    
    def __init__(self):
        self.task_manager = get_task_manager()
        self.is_running = False
        self.scheduler_thread = None
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return
        
        # 1분마다 스케줄된 알림 확인
        schedule.every(1).minutes.do(self._check_and_send_notifications)
        
        # 5분마다 만료된 작업 확인
        schedule.every(5).minutes.do(self._check_overdue_tasks)
        
        # 1시간마다 정리 작업
        schedule.every().hour.do(self._cleanup_old_logs)
        
        def run_scheduler():
            """스케줄러 실행 루프"""
            logger.info("정책 스케줄러 시작됨")
            self.is_running = True
            
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(30)  # 30초마다 체크
                except Exception as e:
                    logger.error(f"스케줄러 실행 중 오류: {e}")
                    time.sleep(60)  # 오류 시 1분 대기
        
        # 백그라운드 스레드로 실행
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("정책 스케줄러가 백그라운드에서 시작되었습니다.")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        schedule.clear()
        logger.info("정책 스케줄러가 중지되었습니다.")
    
    def _check_and_send_notifications(self):
        """스케줄된 알림 확인 및 전송"""
        try:
            logger.debug("스케줄된 알림 확인 중...")
            result = self.task_manager.send_scheduled_notifications()
            
            if result['success'] and result['sent_count'] > 0:
                logger.info(f"알림 전송 완료: {result['sent_count']}개 전송, {result['failed_count']}개 실패")
            
        except Exception as e:
            logger.error(f"알림 확인 중 오류: {e}")
    
    def _check_overdue_tasks(self):
        """만료된 작업 확인 및 상태 업데이트"""
        try:
            import sqlite3
            
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # 마감 시간이 지난 작업들을 overdue 상태로 변경
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = 'overdue',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status IN ('pending', 'in_progress') 
                  AND due_time < ?
            ''', (datetime.now(),))
            
            overdue_count = cursor.rowcount
            
            if overdue_count > 0:
                logger.warning(f"{overdue_count}개의 작업이 만료되어 overdue 상태로 변경되었습니다.")
                
                # 만료된 작업에 대한 에스컬레이션 알림 (선택사항)
                # 여기에 관리자에게 만료 알림을 보내는 로직 추가 가능
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"만료 작업 확인 중 오류: {e}")
        finally:
            if conn:
                conn.close()
    
    def _cleanup_old_logs(self):
        """오래된 로그 정리"""
        try:
            import sqlite3
            
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # 30일 이전의 완료된 작업 로그 삭제
            cutoff_date = datetime.now() - timedelta(days=30)
            
            cursor.execute('''
                DELETE FROM task_execution_logs 
                WHERE performed_at < ? 
                  AND task_id IN (
                      SELECT task_id FROM scheduled_tasks 
                      WHERE status = 'completed' AND completed_at < ?
                  )
            ''', (cutoff_date, cutoff_date))
            
            cleaned_count = cursor.rowcount
            
            if cleaned_count > 0:
                logger.info(f"오래된 작업 로그 {cleaned_count}개 정리 완료")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"로그 정리 중 오류: {e}")
        finally:
            if conn:
                conn.close()


# Flask 앱에서 사용할 전역 인스턴스
policy_scheduler = None

def get_policy_scheduler() -> PolicyScheduler:
    """PolicyScheduler 싱글톤 인스턴스 반환"""
    global policy_scheduler
    if policy_scheduler is None:
        policy_scheduler = PolicyScheduler()
    return policy_scheduler

def start_policy_scheduler():
    """정책 스케줄러 시작 (앱 초기화 시 호출)"""
    scheduler = get_policy_scheduler()
    scheduler.start_scheduler()
    return scheduler
