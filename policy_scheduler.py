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
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=False)
        self.scheduler_thread.start()
        
        logger.info("정책 스케줄러가 백그라운드에서 시작되었습니다.")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        self.is_running = False
        schedule.clear()
        logger.info("정책 스케줄러가 중지되었습니다.")
    
    def _check_and_send_notifications(self):
        """스케줄된 알림 확인 및 전송 - 10분, 5분, 1분 전 알림"""
        try:
            import sqlite3
            
            now = datetime.now()
            conn = sqlite3.connect('progress_report.db')
            cursor = conn.cursor()
            
            # 10분, 5분, 1분 전 알림 체크
            alert_times = [
                (10, '10분 전 마감 알림'),
                (5, '5분 전 마감 알림'), 
                (1, '1분 전 마감 알림')
            ]
            
            for minutes, alert_type in alert_times:
                alert_time = now + timedelta(minutes=minutes)
                # ±30초 범위에서 체크
                start_time = alert_time - timedelta(seconds=30)
                end_time = alert_time + timedelta(seconds=30)
                
                # CIMS 태스크 테이블에서 확인
                cursor.execute("""
                    SELECT t.id, t.task_name, t.due_date, t.assigned_user_id,
                           i.resident_name, i.site
                    FROM cims_tasks t
                    JOIN cims_incidents i ON t.incident_id = i.id
                    WHERE t.status IN ('Open', 'In Progress') 
                    AND t.due_date BETWEEN ? AND ?
                    AND t.notification_sent_10min = 0
                """, (start_time.isoformat(), end_time.isoformat()))
                
                tasks = cursor.fetchall()
                
                for task in tasks:
                    task_id, task_name, due_date, assigned_user_id, resident_name, site = task
                    
                    # 알림 전송
                    result = self._send_deadline_alert(task_id, alert_type, minutes, task_name, resident_name, site)
                    
                    if result.get('success'):
                        # 알림 전송 완료 표시
                        if minutes == 10:
                            cursor.execute("UPDATE cims_tasks SET notification_sent_10min = 1 WHERE id = ?", (task_id,))
                        elif minutes == 5:
                            cursor.execute("UPDATE cims_tasks SET notification_sent_5min = 1 WHERE id = ?", (task_id,))
                        elif minutes == 1:
                            cursor.execute("UPDATE cims_tasks SET notification_sent_1min = 1 WHERE id = ?", (task_id,))
                        
                        conn.commit()
                        logger.info(f"{alert_type} 전송 완료: {task_id}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"알림 확인 중 오류: {e}")
    
    def _send_deadline_alert(self, task_id, alert_type, minutes, task_name, resident_name, site):
        """마감 알림 전송"""
        try:
            from alarm_manager import AlarmManager
            
            alarm_manager = AlarmManager()
            
            # 알림 메시지 생성
            message = f"⚠️ {alert_type}\n\n거주자: {resident_name}\n작업: {task_name}\n사이트: {site}\n남은 시간: {minutes}분"
            
            # FCM 알림 전송
            result = alarm_manager.send_alarm(
                incident_id=f"ALERT-{task_id}",
                event_type="Deadline Alert",
                client_name=resident_name,
                site=site,
                risk_rating="High" if minutes <= 5 else "Medium",
                custom_message=message,
                priority="high" if minutes <= 5 else "normal"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"마감 알림 전송 오류: {e}")
            return {'success': False, 'message': str(e)}
    
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
                      SELECT task_name FROM scheduled_tasks 
                      WHERE is_active = 0 AND last_run < ?
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
