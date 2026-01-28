"""
Unified Alarm Management Service Module
Manages FCM, templates, recipient management, and escalations in an integrated manner.
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
    """Unified Alarm Management Class"""
    
    def __init__(self):
        """Initialize Alarm Manager"""
        self.fcm_service = get_fcm_service()
        self.template_service, self.recipient_service, self.escalation_service = get_alarm_services()
        self.active_alarms: Dict[str, Dict[str, Any]] = {}
        self.escalation_timers: Dict[str, List[Timer]] = {}
        
        # Start escalation check timer
        self._start_escalation_checker()
    
    def _start_escalation_checker(self):
        """Start escalation check timer."""
        def check_escalations():
            try:
                self._process_pending_escalations()
            except Exception as e:
                logger.error(f"Error occurred during escalation check: {e}")
            finally:
                # Check every minute
                Timer(60.0, check_escalations).start()
        
        Timer(60.0, check_escalations).start()
        logger.info("Escalation check timer started")
    
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
        Send alarm.
        
        Args:
            incident_id: Incident ID
            event_type: Incident type
            client_name: Client name
            site: Site
            risk_rating: Risk rating
            template_id: Template ID to use (auto-select if None)
            custom_message: Custom message
            custom_recipients: Custom recipient list
            priority: Priority
            
        Returns:
            Alarm sending result
        """
        try:
            # 1. Select or create template
            if template_id:
                template = self.template_service.get_template(template_id)
                if not template:
                    return {"success": False, "error": f"Template not found: {template_id}"}
            else:
                # Automatically select template based on risk rating
                template = self._select_template_by_risk(risk_rating)
            
            # 2. Determine recipients
            recipients = custom_recipients or template.recipients
            if not recipients:
                return {"success": False, "error": "Recipients not specified"}
            
            # 3. Compose message
            if custom_message:
                title = custom_message
                body = f"{event_type} - {client_name} at {site} (Risk: {risk_rating})"
            else:
                title = template.title
                body = f"{template.body}\n\nIncident: {event_type}\nClient: {client_name}\nSite: {site}\nRisk Rating: {risk_rating}"
            
            # 4. Collect FCM tokens
            fcm_tokens = self._get_fcm_tokens(recipients)
            if not fcm_tokens:
                logger.warning(f"Recipients without FCM tokens: {recipients}")
            
            # 5. Compose alarm data
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
            
            # 6. Send FCM notification
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
            
            # 7. Save alarm log
            self._save_alarm_log(alarm_data, fcm_result)
            
            # 8. Create escalation plan and set timer
            if template.escalation_enabled:
                escalations = self.escalation_service.create_escalation_plan(
                    alarm_data["alarm_id"], template, recipients
                )
                self._setup_escalation_timers(alarm_data["alarm_id"], escalations)
            
            # 9. Add to active alarms
            self.active_alarms[alarm_data["alarm_id"]] = alarm_data
            
            logger.info(f"Alarm sent successfully: {alarm_data['alarm_id']} - {len(fcm_tokens)} devices")
            
            return {
                "success": True,
                "alarm_id": alarm_data["alarm_id"],
                "message": "Alarm sent successfully",
                "fcm_result": fcm_result,
                "recipients_count": len(recipients),
                "fcm_tokens_count": len(fcm_tokens)
            }
            
        except Exception as e:
            logger.error(f"Failed to send alarm: {e}")
            return {"success": False, "error": str(e)}
    
    def _select_template_by_risk(self, risk_rating: str) -> Any:
        """Select appropriate template based on risk rating."""
        risk_mapping = {
            "High": "incident_high_risk",
            "Medium": "incident_normal",
            "Low": "incident_normal"
        }
        
        template_id = risk_mapping.get(risk_rating, "incident_normal")
        template = self.template_service.get_template(template_id)
        
        if not template:
            # Create default template if it doesn't exist
            template = self.template_service.get_template("incident_normal")
        
        return template
    
    def _get_fcm_tokens(self, recipients: List[str]) -> List[str]:
        """Collect FCM tokens from recipients."""
        tokens = []
        for recipient_id in recipients:
            recipient = self.recipient_service.get_recipient(recipient_id)
            if recipient and recipient.is_active and recipient.fcm_token:
                if recipient.notification_preferences.get('push', True):
                    tokens.append(recipient.fcm_token)
        
        return tokens
    
    def _save_alarm_log(self, alarm_data: Dict[str, Any], fcm_result: Optional[Dict[str, Any]]):
        """Save alarm log to file."""
        try:
            log_file = "data/alarm_logs.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Load existing logs
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # Add new log
            log_entry = {
                **alarm_data,
                "fcm_result": fcm_result,
                "log_timestamp": datetime.now().isoformat()
            }
            logs.append(log_entry)
            
            # Keep only last 1000 entries
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save logs
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save alarm log: {e}")
    
    def _setup_escalation_timers(self, alarm_id: str, escalations: List[Any]):
        """Set up escalation timers."""
        if alarm_id not in self.escalation_timers:
            self.escalation_timers[alarm_id] = []
        
        for escalation in escalations:
            if escalation.status == "pending":
                # Execute escalation after delay
                timer = Timer(
                    escalation.delay_minutes * 60.0,
                    self._execute_escalation,
                    args=[alarm_id, escalation.level]
                )
                timer.start()
                self.escalation_timers[alarm_id].append(timer)
                
                logger.info(f"Escalation timer set: {alarm_id} level {escalation.level} - after {escalation.delay_minutes} minutes")
    
    def _execute_escalation(self, alarm_id: str, level: int):
        """Execute escalation."""
        try:
            escalations = self.escalation_service.get_escalations_for_alarm(alarm_id)
            escalation = next((e for e in escalations if e.level == level), None)
            
            if not escalation or escalation.status != "pending":
                return
            
            # Send notification to escalation recipients
            fcm_tokens = self._get_fcm_tokens(escalation.recipients)
            
            if fcm_tokens:
                title = f"🚨 Escalation Alert (Level {level})"
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
                
                # Update escalation status
                self.escalation_service.mark_escalation_sent(alarm_id, level)
                
                logger.info(f"Escalation executed: {alarm_id} level {level} - {len(fcm_tokens)} devices")
            
        except Exception as e:
            logger.error(f"Failed to execute escalation: {e}")
    
    def _process_pending_escalations(self):
        """Process pending escalations."""
        try:
            pending_escalations = self.escalation_service.get_pending_escalations()
            
            for escalation in pending_escalations:
                # Skip if timer hasn't expired
                if datetime.now() < escalation.created_at + timedelta(minutes=escalation.delay_minutes):
                    continue
                
                # Execute escalation
                self._execute_escalation(escalation.alarm_id, escalation.level)
                
        except Exception as e:
            logger.error(f"Failed to process pending escalations: {e}")
    
    def acknowledge_alarm(self, alarm_id: str, user_id: str) -> Dict[str, Any]:
        """Acknowledge alarm."""
        try:
            if alarm_id not in self.active_alarms:
                return {"success": False, "error": "Alarm not found"}
            
            alarm = self.active_alarms[alarm_id]
            
            # Process escalation acknowledgment
            escalations = self.escalation_service.get_escalations_for_alarm(alarm_id)
            for escalation in escalations:
                if escalation.status == "sent" and user_id in escalation.recipients:
                    self.escalation_service.mark_escalation_acknowledged(alarm_id, escalation.level)
            
            # Save acknowledgment log
            self._save_acknowledgment_log(alarm_id, user_id)
            
            logger.info(f"Alarm acknowledged: {alarm_id} by {user_id}")
            
            return {
                "success": True,
                "message": "Alarm acknowledged",
                "acknowledged_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alarm: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_acknowledgment_log(self, alarm_id: str, user_id: str):
        """Save alarm acknowledgment log."""
        try:
            log_file = "data/alarm_acknowledgments.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Load existing logs
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # Add new acknowledgment log
            acknowledgment = {
                "alarm_id": alarm_id,
                "user_id": user_id,
                "acknowledged_at": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            logs.append(acknowledgment)
            
            # Keep only last 1000 entries
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save logs
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save acknowledgment log: {e}")
    
    def get_alarm_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get alarm history."""
        try:
            log_file = "data/alarm_logs.json"
            if not os.path.exists(log_file):
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # Sort by most recent and limit
            sorted_logs = sorted(logs, key=lambda x: x.get('log_timestamp', ''), reverse=True)
            return sorted_logs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to load alarm history: {e}")
            return []
    
    def get_alarm_status(self, alarm_id: str) -> Optional[Dict[str, Any]]:
        """Get status of specific alarm."""
        return self.active_alarms.get(alarm_id)
    
    def get_pending_escalations_count(self) -> int:
        """Return count of pending escalations."""
        return len(self.escalation_service.get_pending_escalations())
    
    def cleanup_expired_alarms(self, days: int = 7):
        """Clean up expired alarms."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            expired_alarms = []
            
            for alarm_id, alarm in self.active_alarms.items():
                created_at = datetime.fromisoformat(alarm['created_at'])
                if created_at < cutoff_date:
                    expired_alarms.append(alarm_id)
            
            for alarm_id in expired_alarms:
                del self.active_alarms[alarm_id]
                
                # Clean up escalation timers
                if alarm_id in self.escalation_timers:
                    for timer in self.escalation_timers[alarm_id]:
                        timer.cancel()
                    del self.escalation_timers[alarm_id]
            
            if expired_alarms:
                logger.info(f"Cleaned up {len(expired_alarms)} expired alarms")
                
        except Exception as e:
            logger.error(f"Failed to clean up expired alarms: {e}")

# Global alarm manager instance
alarm_manager = None

def get_alarm_manager() -> AlarmManager:
    """Return global alarm manager instance."""
    global alarm_manager
    if alarm_manager is None:
        alarm_manager = AlarmManager()
    return alarm_manager


