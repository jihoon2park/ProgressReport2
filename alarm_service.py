"""
알람 서비스 모듈
알람 템플릿, 수신자 관리, 에스컬레이션 기능을 담당합니다.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from croniter import croniter

logger = logging.getLogger(__name__)

@dataclass
class AlarmTemplate:
    """알람 템플릿 데이터 클래스"""
    id: str
    name: str
    title: str
    body: str
    priority: str  # low, normal, high, urgent
    category: str  # incident, maintenance, emergency, general
    escalation_enabled: bool
    escalation_delay_minutes: int
    recipients: List[str]  # 사용자 ID 또는 팀 ID 리스트
    created_at: datetime
    updated_at: datetime

@dataclass
class AlarmRecipient:
    """알람 수신자 데이터 클래스"""
    user_id: str
    name: str
    email: str
    phone: str
    fcm_token: Optional[str]
    role: str
    team: str
    notification_preferences: Dict[str, bool]  # email, sms, push
    is_active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class AlarmEscalation:
    """알람 에스컬레이션 데이터 클래스"""
    alarm_id: str
    level: int  # 1, 2, 3...
    recipients: List[str]
    delay_minutes: int
    message: str
    status: str  # pending, sent, acknowledged, escalated
    created_at: datetime
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]

class AlarmTemplateService:
    """알람 템플릿 서비스 클래스"""
    
    def __init__(self, templates_file: str = "data/alarm_templates.json"):
        self.templates_file = templates_file
        self.templates: Dict[str, AlarmTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """템플릿 파일에서 템플릿들을 로드합니다."""
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_data in data:
                        template = AlarmTemplate(
                            id=template_data['id'],
                            name=template_data['name'],
                            title=template_data['title'],
                            body=template_data['body'],
                            priority=template_data['priority'],
                            category=template_data['category'],
                            escalation_enabled=template_data['escalation_enabled'],
                            escalation_delay_minutes=template_data['escalation_delay_minutes'],
                            recipients=template_data['recipients'],
                            created_at=datetime.fromisoformat(template_data['created_at']),
                            updated_at=datetime.fromisoformat(template_data['updated_at'])
                        )
                        self.templates[template.id] = template
                logger.info(f"알람 템플릿 {len(self.templates)}개 로드 완료")
            else:
                self._create_default_templates()
        except Exception as e:
            logger.error(f"알람 템플릿 로드 실패: {e}")
            self._create_default_templates()
    
    def _create_default_templates(self):
        """기본 알람 템플릿들을 생성합니다."""
        default_templates = [
            {
                "id": "incident_high_risk",
                "name": "고위험 사고 알람",
                "title": "🚨 고위험 사고 발생",
                "body": "고위험 사고가 발생했습니다. 즉시 확인이 필요합니다.",
                "priority": "urgent",
                "category": "incident",
                "escalation_enabled": True,
                "escalation_delay_minutes": 5,
                "recipients": ["emergency_team", "management"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "incident_normal",
                "name": "일반 사고 알람",
                "title": "⚠️ 사고 발생",
                "body": "사고가 발생했습니다. 확인 후 조치해주세요.",
                "priority": "normal",
                "category": "incident",
                "escalation_enabled": False,
                "escalation_delay_minutes": 0,
                "recipients": ["supervisors"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "maintenance_scheduled",
                "name": "정기 점검 알람",
                "title": "🔧 정기 점검 예정",
                "body": "정기 점검이 예정되어 있습니다. 준비해주세요.",
                "priority": "low",
                "category": "maintenance",
                "escalation_enabled": False,
                "escalation_delay_minutes": 0,
                "recipients": ["maintenance_team"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        
        for template_data in default_templates:
            template = AlarmTemplate(
                id=template_data['id'],
                name=template_data['name'],
                title=template_data['title'],
                body=template_data['body'],
                priority=template_data['priority'],
                category=template_data['category'],
                escalation_enabled=template_data['escalation_enabled'],
                escalation_delay_minutes=template_data['escalation_delay_minutes'],
                recipients=template_data['recipients'],
                created_at=datetime.fromisoformat(template_data['created_at']),
                updated_at=datetime.fromisoformat(template_data['updated_at'])
            )
            self.templates[template.id] = template
        
        self._save_templates()
        logger.info("기본 알람 템플릿 생성 완료")
    
    def _save_templates(self):
        """템플릿들을 파일에 저장합니다."""
        try:
            os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                templates_data = []
                for template in self.templates.values():
                    template_dict = asdict(template)
                    template_dict['created_at'] = template.created_at.isoformat()
                    template_dict['updated_at'] = template.updated_at.isoformat()
                    templates_data.append(template_dict)
                json.dump(templates_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알람 템플릿 저장 실패: {e}")
    
    def get_template(self, template_id: str) -> Optional[AlarmTemplate]:
        """템플릿 ID로 템플릿을 가져옵니다."""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[AlarmTemplate]:
        """카테고리별로 템플릿들을 가져옵니다."""
        return [t for t in self.templates.values() if t.category == category]
    
    def get_templates_by_priority(self, priority: str) -> List[AlarmTemplate]:
        """우선순위별로 템플릿들을 가져옵니다."""
        return [t for t in self.templates.values() if t.priority == priority]
    
    def create_template(self, template_data: Dict[str, Any]) -> AlarmTemplate:
        """새로운 템플릿을 생성합니다."""
        template_id = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        template = AlarmTemplate(
            id=template_id,
            name=template_data['name'],
            title=template_data['title'],
            body=template_data['body'],
            priority=template_data.get('priority', 'normal'),
            category=template_data.get('category', 'general'),
            escalation_enabled=template_data.get('escalation_enabled', False),
            escalation_delay_minutes=template_data.get('escalation_delay_minutes', 0),
            recipients=template_data.get('recipients', []),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.templates[template_id] = template
        self._save_templates()
        logger.info(f"새로운 알람 템플릿 생성: {template_id}")
        return template
    
    def update_template(self, template_id: str, template_data: Dict[str, Any]) -> Optional[AlarmTemplate]:
        """기존 템플릿을 업데이트합니다."""
        if template_id not in self.templates:
            return None
        
        template = self.templates[template_id]
        for key, value in template_data.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.now()
        self._save_templates()
        logger.info(f"알람 템플릿 업데이트: {template_id}")
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """템플릿을 삭제합니다."""
        if template_id in self.templates:
            del self.templates[template_id]
            self._save_templates()
            logger.info(f"알람 템플릿 삭제: {template_id}")
            return True
        return False

class AlarmRecipientService:
    """알람 수신자 서비스 클래스"""
    
    def __init__(self, recipients_file: str = "data/alarm_recipients.json"):
        self.recipients_file = recipients_file
        self.recipients: Dict[str, AlarmRecipient] = {}
        self._load_recipients()
    
    def _load_recipients(self):
        """수신자 파일에서 수신자들을 로드합니다."""
        try:
            if os.path.exists(self.recipients_file):
                with open(self.recipients_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for recipient_data in data:
                        recipient = AlarmRecipient(
                            user_id=recipient_data['user_id'],
                            name=recipient_data['name'],
                            email=recipient_data['email'],
                            phone=recipient_data['phone'],
                            fcm_token=recipient_data.get('fcm_token'),
                            role=recipient_data['role'],
                            team=recipient_data['team'],
                            notification_preferences=recipient_data.get('notification_preferences', {
                                'email': True,
                                'sms': False,
                                'push': True
                            }),
                            is_active=recipient_data.get('is_active', True),
                            created_at=datetime.fromisoformat(recipient_data['created_at']),
                            updated_at=datetime.fromisoformat(recipient_data['updated_at'])
                        )
                        self.recipients[recipient.user_id] = recipient
                logger.info(f"알람 수신자 {len(self.recipients)}명 로드 완료")
            else:
                self._create_default_recipients()
        except Exception as e:
            logger.error(f"알람 수신자 로드 실패: {e}")
            self._create_default_recipients()
    
    def _create_default_recipients(self):
        """기본 수신자들을 생성합니다."""
        default_recipients = [
            {
                "user_id": "emergency_team",
                "name": "긴급 대응팀",
                "email": "emergency@company.com",
                "phone": "010-0000-0000",
                "fcm_token": None,
                "role": "emergency",
                "team": "emergency",
                "notification_preferences": {"email": True, "sms": True, "push": True},
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "user_id": "management",
                "name": "관리팀",
                "email": "management@company.com",
                "phone": "010-0000-0001",
                "fcm_token": None,
                "role": "management",
                "team": "management",
                "notification_preferences": {"email": True, "sms": False, "push": True},
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "user_id": "supervisors",
                "name": "감독관",
                "email": "supervisors@company.com",
                "phone": "010-0000-0002",
                "fcm_token": None,
                "role": "supervisor",
                "team": "supervision",
                "notification_preferences": {"email": True, "sms": False, "push": True},
                "is_active": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
        
        for recipient_data in default_recipients:
            recipient = AlarmRecipient(
                user_id=recipient_data['user_id'],
                name=recipient_data['name'],
                email=recipient_data['email'],
                phone=recipient_data['phone'],
                fcm_token=recipient_data['fcm_token'],
                role=recipient_data['role'],
                team=recipient_data['team'],
                notification_preferences=recipient_data['notification_preferences'],
                is_active=recipient_data['is_active'],
                created_at=datetime.fromisoformat(recipient_data['created_at']),
                updated_at=datetime.fromisoformat(recipient_data['updated_at'])
            )
            self.recipients[recipient.user_id] = recipient
        
        self._save_recipients()
        logger.info("기본 알람 수신자 생성 완료")
    
    def _save_recipients(self):
        """수신자들을 파일에 저장합니다."""
        try:
            os.makedirs(os.path.dirname(self.recipients_file), exist_ok=True)
            with open(self.recipients_file, 'w', encoding='utf-8') as f:
                recipients_data = []
                for recipient in self.recipients.values():
                    recipient_dict = asdict(recipient)
                    recipient_dict['created_at'] = recipient.created_at.isoformat()
                    recipient_dict['updated_at'] = recipient.updated_at.isoformat()
                    recipients_data.append(recipient_dict)
                json.dump(recipients_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알람 수신자 저장 실패: {e}")
    
    def get_recipient(self, user_id: str) -> Optional[AlarmRecipient]:
        """사용자 ID로 수신자를 가져옵니다."""
        return self.recipients.get(user_id)
    
    def get_recipients_by_team(self, team: str) -> List[AlarmRecipient]:
        """팀별로 수신자들을 가져옵니다."""
        return [r for r in self.recipients.values() if r.team == team and r.is_active]
    
    def get_recipients_by_role(self, role: str) -> List[AlarmRecipient]:
        """역할별로 수신자들을 가져옵니다."""
        return [r for r in self.recipients.values() if r.role == role and r.is_active]
    
    def get_active_recipients(self) -> List[AlarmRecipient]:
        """활성화된 수신자들을 가져옵니다."""
        return [r for r in self.recipients.values() if r.is_active]
    
    def add_recipient(self, recipient_data: Dict[str, Any]) -> AlarmRecipient:
        """새로운 수신자를 추가합니다."""
        recipient = AlarmRecipient(
            user_id=recipient_data['user_id'],
            name=recipient_data['name'],
            email=recipient_data['email'],
            phone=recipient_data['phone'],
            fcm_token=recipient_data.get('fcm_token'),
            role=recipient_data['role'],
            team=recipient_data['team'],
            notification_preferences=recipient_data.get('notification_preferences', {
                'email': True,
                'sms': False,
                'push': True
            }),
            is_active=recipient_data.get('is_active', True),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.recipients[recipient.user_id] = recipient
        self._save_recipients()
        logger.info(f"새로운 알람 수신자 추가: {recipient.user_id}")
        return recipient
    
    def update_recipient(self, user_id: str, recipient_data: Dict[str, Any]) -> Optional[AlarmRecipient]:
        """기존 수신자를 업데이트합니다."""
        if user_id not in self.recipients:
            return None
        
        recipient = self.recipients[user_id]
        for key, value in recipient_data.items():
            if hasattr(recipient, key):
                setattr(recipient, key, value)
        
        recipient.updated_at = datetime.now()
        self._save_recipients()
        logger.info(f"알람 수신자 업데이트: {user_id}")
        return recipient
    
    def update_fcm_token(self, user_id: str, fcm_token: str) -> bool:
        """사용자의 FCM 토큰을 업데이트합니다."""
        if user_id in self.recipients:
            self.recipients[user_id].fcm_token = fcm_token
            self.recipients[user_id].updated_at = datetime.now()
            self._save_recipients()
            logger.info(f"FCM 토큰 업데이트: {user_id}")
            return True
        return False
    
    def deactivate_recipient(self, user_id: str) -> bool:
        """수신자를 비활성화합니다."""
        if user_id in self.recipients:
            self.recipients[user_id].is_active = False
            self.recipients[user_id].updated_at = datetime.now()
            self._save_recipients()
            logger.info(f"알람 수신자 비활성화: {user_id}")
            return True
        return False

class AlarmEscalationService:
    """알람 에스컬레이션 서비스 클래스"""
    
    def __init__(self, escalations_file: str = "data/alarm_escalations.json"):
        self.escalations_file = escalations_file
        self.escalations: Dict[str, List[AlarmEscalation]] = {}  # alarm_id -> escalations
        self._load_escalations()
    
    def _load_escalations(self):
        """에스컬레이션 파일에서 에스컬레이션들을 로드합니다."""
        try:
            if os.path.exists(self.escalations_file):
                with open(self.escalations_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for alarm_id, escalations_data in data.items():
                        escalations = []
                        for escalation_data in escalations_data:
                            escalation = AlarmEscalation(
                                alarm_id=escalation_data['alarm_id'],
                                level=escalation_data['level'],
                                recipients=escalation_data['recipients'],
                                delay_minutes=escalation_data['delay_minutes'],
                                message=escalation_data['message'],
                                status=escalation_data['status'],
                                created_at=datetime.fromisoformat(escalation_data['created_at']),
                                sent_at=datetime.fromisoformat(escalation_data['sent_at']) if escalation_data.get('sent_at') else None,
                                acknowledged_at=datetime.fromisoformat(escalation_data['acknowledged_at']) if escalation_data.get('acknowledged_at') else None
                            )
                            escalations.append(escalation)
                        self.escalations[alarm_id] = escalations
                logger.info(f"알람 에스컬레이션 로드 완료")
        except Exception as e:
            logger.error(f"알람 에스컬레이션 로드 실패: {e}")
    
    def _save_escalations(self):
        """에스컬레이션들을 파일에 저장합니다."""
        try:
            os.makedirs(os.path.dirname(self.escalations_file), exist_ok=True)
            with open(self.escalations_file, 'w', encoding='utf-8') as f:
                escalations_data = {}
                for alarm_id, escalations in self.escalations.items():
                    escalations_data[alarm_id] = []
                    for escalation in escalations:
                        escalation_dict = asdict(escalation)
                        escalation_dict['created_at'] = escalation.created_at.isoformat()
                        escalation_dict['sent_at'] = escalation.sent_at.isoformat() if escalation.sent_at else None
                        escalation_dict['acknowledged_at'] = escalation.acknowledged_at.isoformat() if escalation.acknowledged_at else None
                        escalations_data[alarm_id].append(escalation_dict)
                json.dump(escalations_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알람 에스컬레이션 저장 실패: {e}")
    
    def create_escalation_plan(
        self,
        alarm_id: str,
        template: AlarmTemplate,
        base_recipients: List[str]
    ) -> List[AlarmEscalation]:
        """템플릿을 기반으로 에스컬레이션 계획을 생성합니다."""
        if not template.escalation_enabled:
            return []
        
        escalations = []
        escalation_levels = [
            {"level": 1, "delay": template.escalation_delay_minutes, "recipients": base_recipients},
            {"level": 2, "delay": template.escalation_delay_minutes * 2, "recipients": ["management"]},
            {"level": 3, "delay": template.escalation_delay_minutes * 4, "recipients": ["emergency_team"]}
        ]
        
        for level_info in escalation_levels:
            escalation = AlarmEscalation(
                alarm_id=alarm_id,
                level=level_info["level"],
                recipients=level_info["recipients"],
                delay_minutes=level_info["delay"],
                message=f"에스컬레이션 레벨 {level_info['level']}: {template.name}",
                status="pending",
                created_at=datetime.now(),
                sent_at=None,
                acknowledged_at=None
            )
            escalations.append(escalation)
        
        if alarm_id not in self.escalations:
            self.escalations[alarm_id] = []
        self.escalations[alarm_id].extend(escalations)
        self._save_escalations()
        
        logger.info(f"알람 {alarm_id}에 대한 에스컬레이션 계획 생성: {len(escalations)}개 레벨")
        return escalations
    
    def get_pending_escalations(self) -> List[AlarmEscalation]:
        """대기 중인 에스컬레이션들을 가져옵니다."""
        pending = []
        for escalations in self.escalations.values():
            for escalation in escalations:
                if escalation.status == "pending":
                    # 지연 시간이 지났는지 확인
                    if datetime.now() >= escalation.created_at + timedelta(minutes=escalation.delay_minutes):
                        pending.append(escalation)
        return pending
    
    def mark_escalation_sent(self, alarm_id: str, level: int) -> bool:
        """에스컬레이션이 전송되었음을 표시합니다."""
        if alarm_id in self.escalations:
            for escalation in self.escalations[alarm_id]:
                if escalation.level == level:
                    escalation.status = "sent"
                    escalation.sent_at = datetime.now()
                    self._save_escalations()
                    logger.info(f"에스컬레이션 전송 완료: {alarm_id} 레벨 {level}")
                    return True
        return False
    
    def mark_escalation_acknowledged(self, alarm_id: str, level: int) -> bool:
        """에스컬레이션이 확인되었음을 표시합니다."""
        if alarm_id in self.escalations:
            for escalation in self.escalations[alarm_id]:
                if escalation.level == level:
                    escalation.status = "acknowledged"
                    escalation.acknowledged_at = datetime.now()
                    self._save_escalations()
                    logger.info(f"에스컬레이션 확인 완료: {alarm_id} 레벨 {level}")
                    return True
        return False
    
    def get_escalations_for_alarm(self, alarm_id: str) -> List[AlarmEscalation]:
        """특정 알람의 에스컬레이션들을 가져옵니다."""
        return self.escalations.get(alarm_id, [])

# 전역 서비스 인스턴스들
template_service = AlarmTemplateService()
recipient_service = AlarmRecipientService()
escalation_service = AlarmEscalationService()

def get_alarm_services():
    """알람 관련 서비스들을 반환합니다."""
    return template_service, recipient_service, escalation_service


