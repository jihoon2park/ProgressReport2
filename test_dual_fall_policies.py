"""
Dual Fall Policies 테스트 스크립트
"""
import sqlite3
import os


def test_fall_type_detection():
    """Fall 유형 감지 테스트"""
    print("=" * 60)
    print("1. Fall 유형 감지 테스트")
    print("=" * 60)
    
    from services.fall_policy_detector import FallPolicyDetector
    
    # Test cases
    test_cases = [
        ("Patient had an unwitnessed fall in bathroom", "unwitnessed"),
        ("Staff witnessed the resident falling", "witnessed"),
        ("Found on floor, not witnessed by anyone", "unwitnessed"),
        ("The fall was observed by carer", "witnessed"),
        ("Discovered lying on ground", "unwitnessed"),
        ("No information about fall", "unknown"),
    ]
    
    passed = 0
    for note, expected in test_cases:
        result = FallPolicyDetector.detect_fall_type_from_notes([note])
        status = "✅" if result == expected else "❌"
        print(f"{status} '{note[:50]}...'")
        print(f"   Expected: {expected}, Got: {result}")
        if result == expected:
            passed += 1
    
    print(f"\n통과: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_policy_selection():
    """Policy 선택 테스트"""
    print("\n" + "=" * 60)
    print("2. Policy 선택 테스트")
    print("=" * 60)
    
    from services.fall_policy_detector import FallPolicyDetector
    
    db_path = os.path.join(os.path.dirname(__file__), 'progress_report.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test policy selection for each fall type
        test_cases = [
            ("unwitnessed", "FALL-001-UNWITNESSED"),
            ("witnessed", "FALL-002-WITNESSED"),
            ("unknown", "FALL-001-UNWITNESSED"),  # Default to unwitnessed
        ]
        
        passed = 0
        for fall_type, expected_policy_id in test_cases:
            policy = FallPolicyDetector.get_policy_for_fall_type(fall_type, cursor)
            
            if policy and policy['policy_id'] == expected_policy_id:
                print(f"✅ {fall_type} → {policy['policy_id']}")
                passed += 1
            else:
                actual = policy['policy_id'] if policy else "None"
                print(f"❌ {fall_type} → Expected: {expected_policy_id}, Got: {actual}")
        
        print(f"\n통과: {passed}/{len(test_cases)}")
        return passed == len(test_cases)
        
    finally:
        conn.close()


def test_policy_visit_schedules():
    """Policy별 방문 스케줄 확인"""
    print("\n" + "=" * 60)
    print("3. Policy 방문 스케줄 확인")
    print("=" * 60)
    
    db_path = os.path.join(os.path.dirname(__file__), 'progress_report.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        import json
        
        cursor.execute("""
            SELECT policy_id, name, rules_json
            FROM cims_policies
            WHERE policy_id LIKE 'FALL-%' AND is_active = 1
            ORDER BY policy_id
        """)
        
        policies = cursor.fetchall()
        
        for policy_row in policies:
            policy_id = policy_row[0]
            policy_name = policy_row[1]
            rules = json.loads(policy_row[2])
            
            visit_schedule = rules.get('nurse_visit_schedule', [])
            
            print(f"\n📋 {policy_id}")
            print(f"   Name: {policy_name}")
            print(f"   Phases: {len(visit_schedule)}")
            
            total_visits = 0
            for phase in visit_schedule:
                interval = phase.get('interval', 0)
                interval_unit = phase.get('interval_unit', 'minutes')
                duration = phase.get('duration', 0)
                duration_unit = phase.get('duration_unit', 'minutes')
                
                # Calculate visits
                interval_minutes = interval * 60 if interval_unit == 'hours' else interval
                duration_minutes = duration * 60 if duration_unit == 'hours' else duration * 24 * 60 if duration_unit == 'days' else duration
                
                num_visits = max(1, duration_minutes // interval_minutes) if interval_minutes > 0 else 1
                total_visits += num_visits
                
                print(f"   - Phase {phase.get('phase')}: {num_visits}회 방문 ({interval}{interval_unit} intervals for {duration}{duration_unit})")
            
            print(f"   Total visits: {total_visits}회")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()


def test_policy_exists():
    """두 Policy가 모두 존재하는지 확인"""
    print("\n" + "=" * 60)
    print("4. Policy 존재 여부 확인")
    print("=" * 60)
    
    db_path = os.path.join(os.path.dirname(__file__), 'progress_report.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        required_policies = [
            'FALL-001-UNWITNESSED',
            'FALL-002-WITNESSED'
        ]
        
        passed = 0
        for policy_id in required_policies:
            cursor.execute("""
                SELECT COUNT(*) FROM cims_policies 
                WHERE policy_id = ? AND is_active = 1
            """, (policy_id,))
            
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"✅ {policy_id} exists and is active")
                passed += 1
            else:
                print(f"❌ {policy_id} not found or inactive")
        
        print(f"\n통과: {passed}/{len(required_policies)}")
        return passed == len(required_policies)
        
    finally:
        conn.close()


def main():
    """전체 테스트 실행"""
    print("\n🚀 Dual Fall Policies 테스트 시작\n")
    
    results = []
    results.append(("Policy 존재 확인", test_policy_exists()))
    results.append(("Fall 유형 감지", test_fall_type_detection()))
    results.append(("Policy 선택", test_policy_selection()))
    results.append(("방문 스케줄 확인", test_policy_visit_schedules()))
    
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n총 {total}개 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! Dual Fall Policies 정상 작동")
        return 0
    else:
        print("\n⚠️  일부 테스트 실패 - 확인 필요")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

