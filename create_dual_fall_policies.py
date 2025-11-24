"""
Dual Fall Policies 생성 스크립트
Unwitnessed Fall vs Witnessed Fall
"""
import sqlite3
import json
from datetime import datetime
import os


def create_dual_fall_policies():
    """두 가지 Fall Policy 생성"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'progress_report.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("=" * 60)
        print("Dual Fall Policies 생성")
        print("=" * 60)
        
        # 1. Unwitnessed Fall Policy (기존 FALL-001 업데이트)
        print("\n1️⃣  Unwitnessed Fall Policy (FALL-001-UNWITNESSED)")
        
        unwitnessed_policy = {
            "policy_name": "Unwitnessed Fall Management Policy",
            "policy_id": "FALL-001-UNWITNESSED",
            "severity": "high",
            "description": "목격되지 않은 낙상 - 집중 모니터링 필요",
            "incident_association": {
                "incident_type": "Fall",
                "progress_note_keywords": [
                    "unwitnessed fall",
                    "not witnessed",
                    "found on floor",
                    "discovered on ground"
                ],
                "matching_logic": "OR"
            },
            "nurse_visit_schedule": [
                {
                    "phase": 1,
                    "description": "Critical monitoring (30 min intervals)",
                    "interval": 30,
                    "interval_unit": "minutes",
                    "duration": 4,
                    "duration_unit": "hours"
                },
                {
                    "phase": 2,
                    "description": "Extended monitoring (2 hour intervals)",
                    "interval": 2,
                    "interval_unit": "hours",
                    "duration": 20,
                    "duration_unit": "hours"
                },
                {
                    "phase": 3,
                    "description": "Observation period (4 hour intervals)",
                    "interval": 4,
                    "interval_unit": "hours",
                    "duration": 3,
                    "duration_unit": "days"
                }
            ],
            "common_assessment_tasks": "Complete neurological observations: GCS, pupil response, limb movement, vital signs, pain assessment, consciousness level",
            "escalation_criteria": [
                "GCS decrease",
                "New confusion",
                "Severe headache",
                "Vomiting",
                "Pupil changes",
                "Weakness"
            ]
        }
        
        # 기존 FALL-001이 있는지 확인
        cursor.execute("SELECT COUNT(*) FROM cims_policies WHERE policy_id = 'FALL-001'")
        if cursor.fetchone()[0] > 0:
            # 기존 Policy 업데이트
            cursor.execute("""
                UPDATE cims_policies 
                SET policy_id = ?, name = ?, description = ?, rules_json = ?
                WHERE policy_id = 'FALL-001'
            """, (
                'FALL-001-UNWITNESSED',
                'Unwitnessed Fall Management Policy',
                unwitnessed_policy['description'],
                json.dumps(unwitnessed_policy)
            ))
            print("   ✅ FALL-001 → FALL-001-UNWITNESSED 업데이트 완료")
        else:
            # 새로 생성
            cursor.execute("""
                INSERT INTO cims_policies 
                (policy_id, name, description, version, effective_date, rules_json, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'FALL-001-UNWITNESSED',
                'Unwitnessed Fall Management Policy',
                unwitnessed_policy['description'],
                '3.0',
                datetime.now().isoformat(),
                json.dumps(unwitnessed_policy),
                1
            ))
            print("   ✅ FALL-001-UNWITNESSED 생성 완료")
        
        # 2. Witnessed Fall Policy (신규)
        print("\n2️⃣  Witnessed Fall Policy (FALL-002-WITNESSED)")
        
        witnessed_policy = {
            "policy_name": "Witnessed Fall Management Policy",
            "policy_id": "FALL-002-WITNESSED",
            "severity": "medium",
            "description": "목격된 낙상 - 초기 평가만 필요",
            "incident_association": {
                "incident_type": "Fall",
                "progress_note_keywords": [
                    "witnessed fall",
                    "observed falling",
                    "staff witnessed",
                    "seen falling"
                ],
                "matching_logic": "OR"
            },
            "nurse_visit_schedule": [
                {
                    "phase": 1,
                    "description": "Initial assessment only",
                    "interval": 30,
                    "interval_unit": "minutes",
                    "duration": 30,
                    "duration_unit": "minutes"
                }
            ],
            "common_assessment_tasks": "Initial post-fall assessment: injury check, vital signs, mobility assessment, pain level, bruising/swelling",
            "escalation_criteria": [
                "Any signs of head injury",
                "Altered consciousness",
                "Severe pain",
                "Unable to weight bear",
                "Patient/family concern",
                "Abnormal vital signs"
            ],
            "escalation_policy": "FALL-001-UNWITNESSED",
            "escalation_note": "If any escalation criteria met, convert to Unwitnessed Fall Policy"
        }
        
        # 기존에 있는지 확인
        cursor.execute("SELECT COUNT(*) FROM cims_policies WHERE policy_id = 'FALL-002-WITNESSED'")
        if cursor.fetchone()[0] > 0:
            # 업데이트
            cursor.execute("""
                UPDATE cims_policies 
                SET name = ?, description = ?, rules_json = ?
                WHERE policy_id = 'FALL-002-WITNESSED'
            """, (
                'Witnessed Fall Management Policy',
                witnessed_policy['description'],
                json.dumps(witnessed_policy)
            ))
            print("   ✅ FALL-002-WITNESSED 업데이트 완료")
        else:
            # 새로 생성
            cursor.execute("""
                INSERT INTO cims_policies 
                (policy_id, name, description, version, effective_date, rules_json, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'FALL-002-WITNESSED',
                'Witnessed Fall Management Policy',
                witnessed_policy['description'],
                '1.0',
                datetime.now().isoformat(),
                json.dumps(witnessed_policy),
                1
            ))
            print("   ✅ FALL-002-WITNESSED 생성 완료")
        
        conn.commit()
        
        # 3. 결과 확인
        print("\n" + "=" * 60)
        print("생성된 Policies 확인")
        print("=" * 60)
        
        cursor.execute("""
            SELECT policy_id, name, description, is_active
            FROM cims_policies
            WHERE policy_id LIKE 'FALL-%'
            ORDER BY policy_id
        """)
        
        policies = cursor.fetchall()
        for policy in policies:
            status = "✅ Active" if policy[3] == 1 else "❌ Inactive"
            print(f"\n{policy[0]}")
            print(f"  Name: {policy[1]}")
            print(f"  Description: {policy[2]}")
            print(f"  Status: {status}")
        
        # 4. 통계
        print("\n" + "=" * 60)
        print("Fall Policy 통계")
        print("=" * 60)
        
        # Unwitnessed Policy visits
        unwitnessed_visits = (
            8 +   # Phase 1: 4시간 / 30분 = 8
            10 +  # Phase 2: 20시간 / 2시간 = 10
            18    # Phase 3: 3일 / 4시간 = 18
        )
        
        # Witnessed Policy visits
        witnessed_visits = 1
        
        print(f"\n📊 Unwitnessed Fall:")
        print(f"   - 총 방문 횟수: {unwitnessed_visits}회")
        print(f"   - 모니터링 기간: 72시간 (3일)")
        print(f"   - 심각도: High")
        
        print(f"\n📊 Witnessed Fall:")
        print(f"   - 총 방문 횟수: {witnessed_visits}회")
        print(f"   - 모니터링 기간: 30분 (초기 평가만)")
        print(f"   - 심각도: Medium")
        
        print(f"\n💡 리소스 절감:")
        print(f"   - Witnessed Fall 시: {unwitnessed_visits - witnessed_visits}회 방문 절감 (97%)")
        print(f"   - 전체 Fall 중 40%가 Witnessed로 가정 시:")
        print(f"     → 연간 약 1,000시간 간호사 시간 절감 예상")
        
        print("\n✅ Dual Fall Policies 생성 완료!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("\n🚀 Dual Fall Policies 생성 스크립트\n")
    success = create_dual_fall_policies()
    exit(0 if success else 1)

