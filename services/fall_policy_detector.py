"""
Fall Type Detection Service
Progress Note에서 Fall 유형 감지 (Witnessed vs Unwitnessed)
"""
import logging
from typing import List, Dict, Optional
import sqlite3
from functools import lru_cache

logger = logging.getLogger(__name__)


class FallPolicyDetector:
    """Fall incident 유형 감지 및 Policy 선택"""
    
    # Priority 1: Explicit keywords (가장 명확한 지표)
    EXPLICIT_UNWITNESSED = [
        "unwitnessed fall",
        "unwitnessed",
        "unwithnessed",  # 오타 포함
        "not witnessed",
        "un-witnessed"
    ]
    
    EXPLICIT_WITNESSED = [
        "witnessed fall",
        "witnessed",
        "guided fall",  # Staff가 의도적으로 guide한 경우
        "guided down",
        "guided to",
        "assisted fall",
        "assisted down"
    ]
    
    # Priority 2: Strong Unwitnessed Indicators (99% 확률)
    STRONG_UNWITNESSED = [
        "found",  # 가장 강력한 지표 (found + sitting/lying/on floor = 99% unwitnessed)
        "discovered",
        "heard",  # 소리를 듣고 확인 = 미목격
        "buzzer",
        "call bell",
        "alarm",
        "sensor mat",
        "sensor activated",
        "emergency buzzer"
    ]
    
    # Priority 3: Unwitnessed Context Indicators
    UNWITNESSED_CONTEXT = [
        "found lying",
        "found sitting",
        "found on floor",
        "found on the floor",
        "found on ground",
        "found resident on",
        "found resident lying",
        "found resident sitting",
        "responded to buzzer",
        "responded to alarm",
        "alerted by"
    ]
    
    # Priority 4: Witnessed Indicators
    WITNESSED_INDICATORS = [
        "staff witnessed",
        "observed falling",
        "seen falling",
        "saw falling",
        "observed the fall",
        "saw the fall",
        "staff observed",
        "carer observed",
        "nurse observed",
        "staff helping",
        "staff assisting",
        "during transfer",
        "while assisting",
        "staff present",
        "staff attending"
    ]
    
    # Contextual words for "saw" analysis
    FALL_ACTION_WORDS = ["fall", "falling", "fell", "slip", "slipping", "slipped", "trip", "tripping", "tripped"]
    FALL_STATE_WORDS = ["sitting", "lying", "laying", "on floor", "on the floor", "on ground"]
    
    @classmethod
    def detect_fall_type_from_notes(cls, progress_notes: List[str]) -> str:
        """
        Progress Notes에서 Fall 유형 감지 (우선순위 기반)
        
        우선순위:
        1. Explicit keywords (unwitnessed/witnessed 명시)
        2. Strong Unwitnessed Indicators (found, heard, buzzer - 99% 확률)
        3. Unwitnessed Context
        4. Witnessed Indicators
        
        Args:
            progress_notes: Progress Note 텍스트 리스트
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        if not progress_notes:
            return 'unknown'
        
        # 모든 노트를 하나의 텍스트로 결합
        combined_text = ' '.join([note for note in progress_notes if note])
        text_lower = combined_text.lower()
        
        # Priority 1: Explicit Unwitnessed (가장 명확)
        for pattern in cls.EXPLICIT_UNWITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ EXPLICIT Unwitnessed detected: '{pattern}'")
                return 'unwitnessed'
        
        # Priority 1: Explicit Witnessed (가장 명확)
        for pattern in cls.EXPLICIT_WITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ EXPLICIT Witnessed detected: '{pattern}'")
                return 'witnessed'
        
        # Priority 2: Strong Unwitnessed Indicators (99% 확률)
        for pattern in cls.STRONG_UNWITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ STRONG Unwitnessed indicator: '{pattern}' (99% confidence)")
                return 'unwitnessed'
        
        # Special: "saw" 문맥 분석
        if " saw " in text_lower or text_lower.startswith("saw "):
            # saw + fall action words = Witnessed
            for action_word in cls.FALL_ACTION_WORDS:
                if action_word in text_lower:
                    logger.info(f"✅ Witnessed detected: 'saw' + '{action_word}' (action context)")
                    return 'witnessed'
            
            # saw + fall state words = Unwitnessed
            for state_word in cls.FALL_STATE_WORDS:
                if state_word in text_lower:
                    logger.info(f"✅ Unwitnessed detected: 'saw' + '{state_word}' (state context)")
                    return 'unwitnessed'
        
        # Priority 3: Unwitnessed Context
        for pattern in cls.UNWITNESSED_CONTEXT:
            if pattern in text_lower:
                logger.info(f"✅ Unwitnessed context detected: '{pattern}'")
                return 'unwitnessed'
        
        # Priority 4: Witnessed Indicators
        for pattern in cls.WITNESSED_INDICATORS:
            if pattern in text_lower:
                logger.info(f"✅ Witnessed indicator: '{pattern}'")
                return 'witnessed'
        
        logger.warning("⚠️  Fall type not detected, defaulting to 'unknown'")
        return 'unknown'
    
    @classmethod
    @lru_cache(maxsize=1000)
    def _cached_detect_fall_type(cls, incident_id: int, description: str, notes_hash: int) -> str:
        """
        캐시된 Fall 유형 감지 (메모리 캐싱)
        
        Args:
            incident_id: CIMS Incident DB ID
            description: Incident description
            notes_hash: Progress notes의 해시값
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        # 실제 감지 로직은 description을 사용
        # notes_hash는 캐시 키로만 사용
        if description:
            fall_type = cls.detect_fall_type_from_notes([description])
            if fall_type != 'unknown':
                return fall_type
        return 'unknown'
    
    @classmethod
    def detect_fall_type_from_incident(
        cls, 
        incident_id: int, 
        cursor: sqlite3.Cursor
    ) -> str:
        """
        Incident ID로부터 Progress Notes 및 Description을 조회하여 Fall 유형 감지
        (메모리 캐싱 적용)
        
        Args:
            incident_id: CIMS Incident DB ID
            cursor: DB cursor
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        try:
            # 1. DB에 저장된 fall_type 먼저 확인 (가장 빠름)
            cursor.execute("""
                SELECT fall_type, description
                FROM cims_incidents
                WHERE id = ?
            """, (incident_id,))
            
            incident_row = cursor.fetchone()
            
            # DB에 fall_type이 있으면 바로 반환
            if incident_row and incident_row[0]:
                logger.debug(f"✅ Fall type from DB cache: {incident_row[0]}")
                return incident_row[0]
            
            # 2. Description으로 감지 (캐싱 적용)
            if incident_row and incident_row[1]:
                description = incident_row[1]
                
                # Progress notes 해시 계산 (캐시 키용)
                cursor.execute("""
                    SELECT COUNT(*), MAX(created_at)
                    FROM cims_progress_notes
                    WHERE incident_id = ?
                """, (incident_id,))
                notes_info = cursor.fetchone()
                notes_hash = hash((notes_info[0] or 0, notes_info[1] or ''))
                
                # 캐시된 감지 사용
                fall_type = cls._cached_detect_fall_type(incident_id, description, notes_hash)
                if fall_type != 'unknown':
                    logger.debug(f"✅ Fall type detected from description (cached): {fall_type}")
                    return fall_type
            
            # 2. Progress Notes 조회 (Description에 정보 없으면)
            cursor.execute("""
                SELECT pn.content, pn.note_type
                FROM cims_progress_notes pn
                WHERE pn.incident_id = ?
                ORDER BY pn.created_at DESC
            """, (incident_id,))
            
            notes = cursor.fetchall()
            
            if not notes:
                logger.debug(f"ℹ️  No progress notes or clear info for incident {incident_id}")
                return 'unknown'
            
            # Post Fall Assessment Note를 우선 검색
            post_fall_notes = [
                note[0] for note in notes 
                if note[1] and 'post fall' in note[1].lower()
            ]
            
            if post_fall_notes:
                fall_type = cls.detect_fall_type_from_notes(post_fall_notes)
                if fall_type != 'unknown':
                    return fall_type
            
            # 모든 Note에서 검색
            all_notes = [note[0] for note in notes if note[0]]
            return cls.detect_fall_type_from_notes(all_notes)
            
        except Exception as e:
            logger.error(f"Error detecting fall type for incident {incident_id}: {e}")
            return 'unknown'
    
    @classmethod
    def get_policy_for_fall_type(
        cls, 
        fall_type: str, 
        cursor: sqlite3.Cursor
    ) -> Optional[Dict]:
        """
        Fall 유형에 맞는 Policy 조회
        
        Args:
            fall_type: 'unwitnessed' | 'witnessed' | 'unknown'
            cursor: DB cursor
            
        Returns:
            Policy 정보 dict 또는 None
        """
        import json
        
        try:
            # Policy ID 결정 (unknown은 unwitnessed로 처리 - 안전 우선)
            if fall_type == 'witnessed':
                policy_id = 'FALL-002-WITNESSED'
            else:  # unwitnessed or unknown
                policy_id = 'FALL-001-UNWITNESSED'
            
            cursor.execute("""
                SELECT id, policy_id, name, rules_json
                FROM cims_policies
                WHERE policy_id = ? AND is_active = 1
            """, (policy_id,))
            
            policy_row = cursor.fetchone()
            
            if policy_row:
                return {
                    'id': policy_row[0],
                    'policy_id': policy_row[1],
                    'name': policy_row[2],
                    'rules': json.loads(policy_row[3])
                }
            
            # 해당 Policy가 없으면 기본 Fall Policy 조회
            logger.warning(f"⚠️  Policy {policy_id} not found, using default")
            cursor.execute("""
                SELECT id, policy_id, name, rules_json
                FROM cims_policies
                WHERE policy_id LIKE 'FALL-%' AND is_active = 1
                ORDER BY policy_id
                LIMIT 1
            """)
            
            fallback_row = cursor.fetchone()
            if fallback_row:
                return {
                    'id': fallback_row[0],
                    'policy_id': fallback_row[1],
                    'name': fallback_row[2],
                    'rules': json.loads(fallback_row[3])
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting policy for fall type {fall_type}: {e}")
            return None
    
    @classmethod
    def get_appropriate_policy_for_incident(
        cls,
        incident_id: int,
        cursor: sqlite3.Cursor
    ) -> Optional[Dict]:
        """
        Incident에 적합한 Policy 자동 선택
        
        Args:
            incident_id: CIMS Incident DB ID
            cursor: DB cursor
            
        Returns:
            선택된 Policy 정보
        """
        # 1. Fall 유형 감지
        fall_type = cls.detect_fall_type_from_incident(incident_id, cursor)
        logger.info(f"📋 Incident {incident_id}: Fall type = {fall_type}")
        
        # 2. 적합한 Policy 조회
        policy = cls.get_policy_for_fall_type(fall_type, cursor)
        
        if policy:
            logger.info(f"✅ Selected policy: {policy['policy_id']} for {fall_type} fall")
        else:
            logger.warning(f"❌ No policy found for {fall_type} fall")
        
        return policy


# 전역 인스턴스
fall_detector = FallPolicyDetector()

