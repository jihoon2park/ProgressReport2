"""
Fall Type Detection Service
Detect Fall type from Progress Note (Witnessed vs Unwitnessed)
"""
import logging
from typing import List, Dict, Optional
import sqlite3
from functools import lru_cache

logger = logging.getLogger(__name__)


class FallPolicyDetector:
    """Fall incident type detection and Policy selection"""
    
    # Priority 1: Explicit keywords (most clear indicators)
    EXPLICIT_UNWITNESSED = [
        "unwitnessed fall",
        "unwitnessed",
        "unwithnessed",  # Including typo
        "not witnessed",
        "un-witnessed"
    ]
    
    EXPLICIT_WITNESSED = [
        "witnessed fall",
        "witnessed",
        "guided fall",  # Staff intentionally guided
        "guided down",
        "guided to",
        "assisted fall",
        "assisted down"
    ]
    
    # Priority 2: Strong Unwitnessed Indicators (99% probability)
    STRONG_UNWITNESSED = [
        "found",  # Strongest indicator (found + sitting/lying/on floor = 99% unwitnessed)
        "discovered",
        "heard",  # Heard sound and confirmed = unwitnessed
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
        Detect Fall type from Progress Notes (priority-based)
        
        Priority:
        1. Explicit keywords (unwitnessed/witnessed explicitly stated)
        2. Strong Unwitnessed Indicators (found, heard, buzzer - 99% probability)
        3. Unwitnessed Context
        4. Witnessed Indicators
        
        Args:
            progress_notes: List of Progress Note text
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        if not progress_notes:
            return 'unknown'
        
        # Combine all notes into a single text
        combined_text = ' '.join([note for note in progress_notes if note])
        text_lower = combined_text.lower()
        
        # Priority 1: Explicit Unwitnessed (most clear)
        for pattern in cls.EXPLICIT_UNWITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ EXPLICIT Unwitnessed detected: '{pattern}'")
                return 'unwitnessed'
        
        # Priority 1: Explicit Witnessed (most clear)
        for pattern in cls.EXPLICIT_WITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ EXPLICIT Witnessed detected: '{pattern}'")
                return 'witnessed'
        
        # Priority 2: Strong Unwitnessed Indicators (99% probability)
        for pattern in cls.STRONG_UNWITNESSED:
            if pattern in text_lower:
                logger.info(f"✅ STRONG Unwitnessed indicator: '{pattern}' (99% confidence)")
                return 'unwitnessed'
        
        # Special: "saw" context analysis
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
        Cached Fall type detection (memory caching)
        
        Args:
            incident_id: CIMS Incident DB ID
            description: Incident description
            notes_hash: Hash value of Progress notes
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        # Actual detection logic uses description
        # notes_hash is only used as cache key
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
        Detect Fall type by querying Progress Notes and Description from Incident ID
        (memory caching applied)
        
        Args:
            incident_id: CIMS Incident DB ID
            cursor: DB cursor
            
        Returns:
            'unwitnessed' | 'witnessed' | 'unknown'
        """
        try:
            # 1. Check stored fall_type in DB first (fastest)
            cursor.execute("""
                SELECT fall_type, description
                FROM cims_incidents
                WHERE id = ?
            """, (incident_id,))
            
            incident_row = cursor.fetchone()
            
            # Return immediately if fall_type exists in DB
            if incident_row and incident_row[0]:
                logger.debug(f"✅ Fall type from DB cache: {incident_row[0]}")
                return incident_row[0]
            
            # 2. Detect from Description (with caching)
            if incident_row and incident_row[1]:
                description = incident_row[1]
                
                # Calculate Progress notes hash (for cache key)
                cursor.execute("""
                    SELECT COUNT(*), MAX(created_at)
                    FROM cims_progress_notes
                    WHERE incident_id = ?
                """, (incident_id,))
                notes_info = cursor.fetchone()
                notes_hash = hash((notes_info[0] or 0, notes_info[1] or ''))
                
                # Use cached detection
                fall_type = cls._cached_detect_fall_type(incident_id, description, notes_hash)
                if fall_type != 'unknown':
                    logger.debug(f"✅ Fall type detected from description (cached): {fall_type}")
                    return fall_type
            
            # 2. Query Progress Notes (if no info in Description)
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
            
            # Search Post Fall Assessment Note first
            post_fall_notes = [
                note[0] for note in notes 
                if note[1] and 'post fall' in note[1].lower()
            ]
            
            if post_fall_notes:
                fall_type = cls.detect_fall_type_from_notes(post_fall_notes)
                if fall_type != 'unknown':
                    return fall_type
            
            # Search all Notes
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
        Query Policy matching Fall type
        
        Args:
            fall_type: 'unwitnessed' | 'witnessed' | 'unknown'
            cursor: DB cursor
            
        Returns:
            Policy information dict or None
        """
        import json
        
        try:
            # Determine Policy ID (treat unknown as unwitnessed - safety first)
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
            
            # Query default Fall Policy if the specific Policy doesn't exist
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
        Automatically select appropriate Policy for Incident
        
        Args:
            incident_id: CIMS Incident DB ID
            cursor: DB cursor
            
        Returns:
            Selected Policy information
        """
        # 1. Detect Fall type
        fall_type = cls.detect_fall_type_from_incident(incident_id, cursor)
        logger.info(f"📋 Incident {incident_id}: Fall type = {fall_type}")
        
        # 2. Query appropriate Policy
        policy = cls.get_policy_for_fall_type(fall_type, cursor)
        
        if policy:
            logger.info(f"✅ Selected policy: {policy['policy_id']} for {fall_type} fall")
        else:
            logger.warning(f"❌ No policy found for {fall_type} fall")
        
        return policy


# Global instance
fall_detector = FallPolicyDetector()

