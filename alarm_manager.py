"""
통합 알람 관리 서비스 모듈
FCM, 템플릿, 수신자 관리, 에스컬레이션을 통합하여 관리합니다.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from threading import Timer
import time

from fcm_service import get_fcm_service
from alarm_service import get_alarm_services

logger = logging.getLogger(__name__)

class AlarmManager:
    """통합 알람 관리 클래스"""
    
    def __init__(self):
        """알람 매니저 초기화"""
        self.fcm_service = get_fcm_service()
        self.template_service, self.recipient_service, self.escalation_service = get_alarm_services()
        self.active_alarms: Dict[str, Dict[str, Any]] = {}
        self.escalation_timers: Dict[str, List[Timer]] = {}
        
        # 에스컬레이션 체크 타이머 시작
        self._start_escalation_checker()
    
    def _start_escalation_checker(self):
        """에스컬레이션 체크 타이머를 시작합니다."""
        def check_escalations():
            try:
                self._process_pending_escalations()
            except Exception as e:
                logger.error(f"에스컬레이션 체크 중 오류 발생: {e}")
            finally:
                # 1분마다 체크
                Timer(60.0, check_escalations).start()
        
        Timer(60.0, check_escalations).start()
        logger.info("에스컬레이션 체크 타이머 시작")
    
    def send_alarm(
        self,
        incident_id: str,
        event_type: str,
        client_name: str,
        site: str,
        risk_rating: str,
        template_id: Optional[str] = None,
        custom_message: Optional[str] = None,
        custom_recipients: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        알람을 전송합니다.
        
        Args:
            incident_id: 사고 ID
            event_type: 사고 유형
            client_name: 클라이언트 이름
            site: 사이트
            risk_rating: 위험도
            template_id: 사용할 템플릿 ID (None이면 자동 선택)
            custom_message: 사용자 정의 메시지
            custom_recipients: 사용자 정의 수신자 리스트
            priority: 우선순위
            
        Returns:
            알람 전송 결과
        """
        try:
            # 1. 템플릿 선택 또는 생성
            if template_id:
                template = self.template_service.get_template(template_id)
                if not template:
                    return {"success": False, "error": f"템플릿을 찾을 수 없습니다: {template_id}"}
            else:
                # 위험도에 따라 자동으로 템플릿 선택
                template = self._select_template_by_risk(risk_rating)
            
            # 2. 수신자 결정
            recipients = custom_recipients or template.recipients
            if not recipients:
                return {"success": False, "error": "수신자가 지정되지 않았습니다"}
            
            # 3. 메시지 구성
            if custom_message:
                title = custom_message
                body = f"{event_type} - {client_name} at {site} (Risk: {risk_rating})"
            else:
                title = template.title
                body = f"{template.body}\n\n사고: {event_type}\n클라이언트: {client_name}\n사이트: {site}\n위험도: {risk_rating}"
            
            # 4. FCM 토큰 수집
            fcm_tokens = self._get_fcm_tokens(recipients)
            if not fcm_tokens:
                logger.warning(f"FCM 토큰이 없는 수신자들: {recipients}")
            
            # 5. 알람 데이터 구성
            alarm_data = {
                "alarm_id": f"alarm_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{incident_id}",
                "incident_id": incident_id,
                "event_type": event_type,
                "client_name": client_name,
                "site": site,
                "risk_rating": risk_rating,
                "template_id": template.id,
                "title": title,
                "body": body,
                "priority": priority,
                "recipients": recipients,
                "fcm_tokens": fcm_tokens,
                "status": "sent",
                "created_at": datetime.now().isoformat(),
                "escalation_enabled": template.escalation_enabled
            }
            
            # 6. FCM 알림 전송
            fcm_result = None
            if fcm_tokens:
                if len(fcm_tokens) == 1:
                    fcm_result = self.fcm_service.send_notification(
                        token=fcm_tokens[0],
                        title=title,
                        body=body,
                        data={
                            "alarm_id": alarm_data["alarm_id"],
                            "incident_id": incident_id,
                            "event_type": event_type,
                            "client_name": client_name,
                            "site": site,
                            "risk_rating": risk_rating,
                            "priority": priority
                        },
                        priority=priority
                    )
                else:
                    fcm_result = self.fcm_service.send_multicast_notification(
                        tokens=fcm_tokens,
                        title=title,
                        body=body,
                        data={
                            "alarm_id": alarm_data["alarm_id"],
                            "incident_id": incident_id,
                            "event_type": event_type,
                            "client_name": client_name,
                            "site": site,
                            "risk_rating": risk_rating,
                            "priority": priority
                        },
                        priority=priority
                    )
            
            # 7. 알람 로그 저장
            self._save_alarm_log(alarm_data, fcm_result)
            
            # 8. 에스컬레이션 계획 생성 및 타이머 설정
            if template.escalation_enabled:
                escalations = self.escalation_service.create_escalation_plan(
                    alarm_data["alarm_id"], template, recipients
                )
                self._setup_escalation_timers(alarm_data["alarm_id"], escalations)
            
            # 9. 활성 알람에 추가
            self.active_alarms[alarm_data["alarm_id"]] = alarm_data
            
            logger.info(f"알람 전송 완료: {alarm_data['alarm_id']} - {len(fcm_tokens)}개 디바이스")
            
            return {
                "success": True,
                "alarm_id": alarm_data["alarm_id"],
                "message": "알람이 성공적으로 전송되었습니다",
                "fcm_result": fcm_result,
                "recipients_count": len(recipients),
                "fcm_tokens_count": len(fcm_tokens)
            }
            
        except Exception as e:
            logger.error(f"알람 전송 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _select_template_by_risk(self, risk_rating: str) -> Any:
        """위험도에 따라 적절한 템플릿을 선택합니다."""
        risk_mapping = {
            "High": "incident_high_risk",
            "Medium": "incident_normal",
            "Low": "incident_normal"
        }
        
        template_id = risk_mapping.get(risk_rating, "incident_normal")
        template = self.template_service.get_template(template_id)
        
        if not template:
            # 기본 템플릿이 없으면 생성
            template = self.template_service.get_template("incident_normal")
        
        return template
    
    def _get_fcm_tokens(self, recipients: List[str]) -> List[str]:
        """수신자들의 FCM 토큰을 수집합니다."""
        tokens = []
        for recipient_id in recipients:
            recipient = self.recipient_service.get_recipient(recipient_id)
            if recipient and recipient.is_active and recipient.fcm_token:
                if recipient.notification_preferences.get('push', True):
                    tokens.append(recipient.fcm_token)
        
        return tokens
    
    def _save_alarm_log(self, alarm_data: Dict[str, Any], fcm_result: Optional[Dict[str, Any]]):
        """알람 로그를 파일에 저장합니다."""
        try:
            log_file = "data/alarm_logs.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 기존 로그 로드
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 새 로그 추가
            log_entry = {
                **alarm_data,
                "fcm_result": fcm_result,
                "log_timestamp": datetime.now().isoformat()
            }
            logs.append(log_entry)
            
            # 최근 1000개만 유지
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # 로그 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"알람 로그 저장 실패: {e}")
    
    def _setup_escalation_timers(self, alarm_id: str, escalations: List[Any]):
        """에스컬레이션 타이머를 설정합니다."""
        if alarm_id not in self.escalation_timers:
            self.escalation_timers[alarm_id] = []
        
        for escalation in escalations:
            if escalation.status == "pending":
                # 지연 시간 후 에스컬레이션 실행
                timer = Timer(
                    escalation.delay_minutes * 60.0,
                    self._execute_escalation,
                    args=[alarm_id, escalation.level]
                )
                timer.start()
                self.escalation_timers[alarm_id].append(timer)
                
                logger.info(f"에스컬레이션 타이머 설정: {alarm_id} 레벨 {escalation.level} - {escalation.delay_minutes}분 후")
    
    def _execute_escalation(self, alarm_id: str, level: int):
        """에스컬레이션을 실행합니다."""
        try:
            escalations = self.escalation_service.get_escalations_for_alarm(alarm_id)
            escalation = next((e for e in escalations if e.level == level), None)
            
            if not escalation or escalation.status != "pending":
                return
            
            # 에스컬레이션 수신자들에게 알림 전송
            fcm_tokens = self._get_fcm_tokens(escalation.recipients)
            
            if fcm_tokens:
                title = f"🚨 에스컬레이션 알림 (레벨 {level})"
                body = escalation.message
                
                if len(fcm_tokens) == 1:
                    fcm_result = self.fcm_service.send_notification(
                        token=fcm_tokens[0],
                        title=title,
                        body=body,
                        data={"alarm_id": alarm_id, "escalation_level": level},
                        priority="high"
                    )
                else:
                    fcm_result = self.fcm_service.send_multicast_notification(
                        tokens=fcm_tokens,
                        title=title,
                        body=body,
                        data={"alarm_id": alarm_id, "escalation_level": level},
                        priority="high"
                    )
                
                # 에스컬레이션 상태 업데이트
                self.escalation_service.mark_escalation_sent(alarm_id, level)
                
                logger.info(f"에스컬레이션 실행 완료: {alarm_id} 레벨 {level} - {len(fcm_tokens)}개 디바이스")
            
        except Exception as e:
            logger.error(f"에스컬레이션 실행 실패: {e}")
    
    def _process_pending_escalations(self):
        """대기 중인 에스컬레이션들을 처리합니다."""
        try:
            pending_escalations = self.escalation_service.get_pending_escalations()
            
            for escalation in pending_escalations:
                # 타이머가 만료되지 않은 경우 스킵
                if datetime.now() < escalation.created_at + timedelta(minutes=escalation.delay_minutes):
                    continue
                
                # 에스컬레이션 실행
                self._execute_escalation(escalation.alarm_id, escalation.level)
                
        except Exception as e:
            logger.error(f"대기 중인 에스컬레이션 처리 실패: {e}")
    
    def acknowledge_alarm(self, alarm_id: str, user_id: str) -> Dict[str, Any]:
        """알람을 확인 처리합니다."""
        try:
            if alarm_id not in self.active_alarms:
                return {"success": False, "error": "알람을 찾을 수 없습니다"}
            
            alarm = self.active_alarms[alarm_id]
            
            # 에스컬레이션 확인 처리
            escalations = self.escalation_service.get_escalations_for_alarm(alarm_id)
            for escalation in escalations:
                if escalation.status == "sent" and user_id in escalation.recipients:
                    self.escalation_service.mark_escalation_acknowledged(alarm_id, escalation.level)
            
            # 확인 로그 저장
            self._save_acknowledgment_log(alarm_id, user_id)
            
            logger.info(f"알람 확인 완료: {alarm_id} by {user_id}")
            
            return {
                "success": True,
                "message": "알람이 확인되었습니다",
                "acknowledged_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"알람 확인 처리 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_acknowledgment_log(self, alarm_id: str, user_id: str):
        """알람 확인 로그를 저장합니다."""
        try:
            log_file = "data/alarm_acknowledgments.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # 기존 로그 로드
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 새 확인 로그 추가
            acknowledgment = {
                "alarm_id": alarm_id,
                "user_id": user_id,
                "acknowledged_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            logs.append(acknowledgment)
            
            # 최근 1000개만 유지
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # 로그 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"알람 확인 로그 저장 실패: {e}")
    
    def get_alarm_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """알람 히스토리를 가져옵니다."""
        try:
            log_file = "data/alarm_logs.json"
            if not os.path.exists(log_file):
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # 최근 순으로 정렬하고 제한
            sorted_logs = sorted(logs, key=lambda x: x.get('log_timestamp', ''), reverse=True)
            return sorted_logs[:limit]
            
        except Exception as e:
            logger.error(f"알람 히스토리 로드 실패: {e}")
            return []
    
    def get_alarm_status(self, alarm_id: str) -> Optional[Dict[str, Any]]:
        """특정 알람의 상태를 가져옵니다."""
        return self.active_alarms.get(alarm_id)
    
    def get_pending_escalations_count(self) -> int:
        """대기 중인 에스컬레이션 개수를 반환합니다."""
        return len(self.escalation_service.get_pending_escalations())
    
    def cleanup_expired_alarms(self, days: int = 7):
        """만료된 알람들을 정리합니다."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            expired_alarms = []
            
            for alarm_id, alarm in self.active_alarms.items():
                created_at = datetime.fromisoformat(alarm['created_at'])
                if created_at < cutoff_date:
                    expired_alarms.append(alarm_id)
            
            for alarm_id in expired_alarms:
                del self.active_alarms[alarm_id]
                
                # 에스컬레이션 타이머 정리
                if alarm_id in self.escalation_timers:
                    for timer in self.escalation_timers[alarm_id]:
                        timer.cancel()
                    del self.escalation_timers[alarm_id]
            
            if expired_alarms:
                logger.info(f"만료된 알람 {len(expired_alarms)}개 정리 완료")
                
        except Exception as e:
            logger.error(f"만료된 알람 정리 실패: {e}")

# 전역 알람 매니저 인스턴스
alarm_manager = None

def get_alarm_manager() -> AlarmManager:
    """전역 알람 매니저 인스턴스를 반환합니다."""
    global alarm_manager
    if alarm_manager is None:
        alarm_manager = AlarmManager()
    return alarm_manager


