"""
리팩토링된 모듈 검증 스크립트
"""
import sys

def test_db_connection():
    """DB 연결 모듈 테스트"""
    print("=" * 50)
    print("1. DB Connection 모듈 테스트")
    print("=" * 50)
    
    try:
        from repositories.db_connection import get_db_connection, db_cursor, db_transaction
        print("✅ 모듈 import 성공")
        
        # 연결 테스트
        conn = get_db_connection(read_only=True)
        print(f"✅ DB 연결 성공: {type(conn)}")
        conn.close()
        
        # Context Manager 테스트
        with db_cursor(read_only=True) as cursor:
            cursor.execute("SELECT COUNT(*) FROM cims_incidents")
            count = cursor.fetchone()[0]
            print(f"✅ Context Manager 작동: {count}개 incidents")
        
        print("✅ DB Connection 모듈 테스트 통과\n")
        return True
        
    except Exception as e:
        print(f"❌ DB Connection 테스트 실패: {e}\n")
        return False


def test_cims_service():
    """CIMS 서비스 모듈 테스트"""
    print("=" * 50)
    print("2. CIMS Service 모듈 테스트")
    print("=" * 50)
    
    try:
        from services.cims_service import cims_service
        from repositories.db_connection import get_db_connection
        print("✅ 모듈 import 성공")
        
        # Fall Policy 조회 테스트
        conn = get_db_connection(read_only=True)
        cursor = conn.cursor()
        
        policy = cims_service.get_fall_policy(cursor)
        if policy:
            print(f"✅ Fall Policy 조회 성공: {policy['name']}")
        else:
            print("⚠️  Fall Policy 없음 (정상 - 초기화 필요)")
        
        conn.close()
        
        print("✅ CIMS Service 모듈 테스트 통과\n")
        return True
        
    except Exception as e:
        print(f"❌ CIMS Service 테스트 실패: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_legacy_compatibility():
    """레거시 호환성 테스트"""
    print("=" * 50)
    print("3. 레거시 호환성 테스트")
    print("=" * 50)
    
    try:
        # 기존 방식으로 DB 연결
        from repositories.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cims_policies")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ 기존 방식 DB 연결 작동: {count}개 policies")
        
        print("✅ 레거시 호환성 테스트 통과\n")
        return True
        
    except Exception as e:
        print(f"❌ 레거시 호환성 테스트 실패: {e}\n")
        return False


def main():
    """전체 테스트 실행"""
    print("\n🚀 리팩토링된 모듈 검증 시작\n")
    
    results = []
    results.append(("DB Connection", test_db_connection()))
    results.append(("CIMS Service", test_cims_service()))
    results.append(("Legacy Compatibility", test_legacy_compatibility()))
    
    print("=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    
    for name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\n총 {total}개 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과! 리팩토링 성공")
        return 0
    else:
        print("\n⚠️  일부 테스트 실패 - 확인 필요")
        return 1


if __name__ == "__main__":
    sys.exit(main())

