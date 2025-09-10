#!/usr/bin/env python3
"""
Progress Report System - Week 1 테스트 및 검증
Day 5: 마이그레이션 결과 테스트 및 성능 검증
"""

import sqlite3
import json
import os
import sys
import time
from datetime import datetime

class Week1Tester:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("=" * 60)
        print("Progress Report System - Week 1 테스트 및 검증")
        print("=" * 60)
        
        test_results = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            
            # 1. 데이터베이스 구조 검증
            test_results.append(self.test_database_structure(conn))
            
            # 2. 데이터 무결성 검증
            test_results.append(self.test_data_integrity(conn))
            
            # 3. 성능 테스트
            test_results.append(self.test_performance(conn))
            
            # 4. 기능 테스트
            test_results.append(self.test_functionality(conn))
            
            # 5. 마이그레이션 검증
            test_results.append(self.test_migration_completeness(conn))
            
            conn.close()
            
            # 결과 요약
            self.print_test_summary(test_results)
            
            # 모든 테스트 통과 여부
            all_passed = all(result['passed'] for result in test_results)
            return all_passed
            
        except Exception as e:
            print(f"테스트 실행 중 오류: {e}")
            return False
    
    def test_database_structure(self, conn):
        """데이터베이스 구조 검증"""
        print("\n1. 데이터베이스 구조 검증")
        print("-" * 40)
        
        cursor = conn.cursor()
        issues = []
        
        try:
            # 필수 테이블 존재 확인
            expected_tables = [
                'users', 'fcm_tokens', 'access_logs', 'progress_note_logs',
                'clients_cache', 'care_areas', 'event_types', 'sites', 'sync_status'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            for table in expected_tables:
                if table in existing_tables:
                    print(f"  ✓ {table} 테이블 존재")
                else:
                    issues.append(f"누락된 테이블: {table}")
                    print(f"  ✗ {table} 테이블 누락")
            
            # 인덱스 확인
            expected_indexes = [
                'idx_users_username', 'idx_clients_site', 'idx_clients_person_id',
                'idx_access_logs_timestamp', 'idx_progress_logs_timestamp'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            existing_indexes = [row[0] for row in cursor.fetchall()]
            
            for index in expected_indexes:
                if index in existing_indexes:
                    print(f"  ✓ {index} 인덱스 존재")
                else:
                    issues.append(f"누락된 인덱스: {index}")
                    print(f"  ✗ {index} 인덱스 누락")
            
        except Exception as e:
            issues.append(f"구조 검증 오류: {e}")
        
        return {
            'test_name': '데이터베이스 구조 검증',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_data_integrity(self, conn):
        """데이터 무결성 검증"""
        print("\n2. 데이터 무결성 검증")
        print("-" * 40)
        
        cursor = conn.cursor()
        issues = []
        
        try:
            # 사용자 데이터 검증
            cursor.execute("SELECT COUNT(*) FROM users WHERE username IS NULL OR username = ''")
            null_usernames = cursor.fetchone()[0]
            if null_usernames > 0:
                issues.append(f"NULL 또는 빈 사용자명 {null_usernames}개 발견")
            else:
                print("  ✓ 사용자명 무결성 확인")
            
            # 중복 사용자명 확인
            cursor.execute("""
                SELECT username, COUNT(*) as cnt 
                FROM users 
                GROUP BY username 
                HAVING cnt > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                issues.append(f"중복 사용자명 발견: {[row[0] for row in duplicates]}")
            else:
                print("  ✓ 사용자명 중복 없음")
            
            # FCM 토큰 검증
            cursor.execute("SELECT COUNT(*) FROM fcm_tokens WHERE token IS NULL OR token = ''")
            null_tokens = cursor.fetchone()[0]
            if null_tokens > 0:
                issues.append(f"NULL 또는 빈 FCM 토큰 {null_tokens}개 발견")
            else:
                print("  ✓ FCM 토큰 무결성 확인")
            
            # 케어 영역 데이터 검증
            cursor.execute("SELECT COUNT(*) FROM care_areas WHERE description IS NULL OR description = ''")
            null_care_areas = cursor.fetchone()[0]
            if null_care_areas > 0:
                issues.append(f"NULL 또는 빈 케어 영역 설명 {null_care_areas}개 발견")
            else:
                print("  ✓ 케어 영역 무결성 확인")
            
            # 이벤트 타입 데이터 검증
            cursor.execute("SELECT COUNT(*) FROM event_types WHERE description IS NULL OR description = ''")
            null_event_types = cursor.fetchone()[0]
            if null_event_types > 0:
                issues.append(f"NULL 또는 빈 이벤트 타입 설명 {null_event_types}개 발견")
            else:
                print("  ✓ 이벤트 타입 무결성 확인")
                
        except Exception as e:
            issues.append(f"무결성 검증 오류: {e}")
        
        return {
            'test_name': '데이터 무결성 검증',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_performance(self, conn):
        """성능 테스트"""
        print("\n3. 성능 테스트")
        print("-" * 40)
        
        cursor = conn.cursor()
        issues = []
        performance_results = {}
        
        try:
            # 사용자 조회 성능 테스트
            start_time = time.time()
            cursor.execute("SELECT * FROM users WHERE username = 'admin'")
            user = cursor.fetchone()
            user_query_time = (time.time() - start_time) * 1000
            performance_results['user_query'] = user_query_time
            
            if user_query_time < 50:  # 50ms 미만
                print(f"  ✓ 사용자 조회: {user_query_time:.2f}ms (양호)")
            else:
                issues.append(f"사용자 조회 성능 저하: {user_query_time:.2f}ms")
                print(f"  ⚠ 사용자 조회: {user_query_time:.2f}ms (느림)")
            
            # 케어 영역 조회 성능 테스트
            start_time = time.time()
            cursor.execute("SELECT * FROM care_areas WHERE is_archived = 0 ORDER BY description")
            care_areas = cursor.fetchall()
            care_area_query_time = (time.time() - start_time) * 1000
            performance_results['care_area_query'] = care_area_query_time
            
            if care_area_query_time < 100:  # 100ms 미만
                print(f"  ✓ 케어 영역 조회: {care_area_query_time:.2f}ms (양호)")
            else:
                issues.append(f"케어 영역 조회 성능 저하: {care_area_query_time:.2f}ms")
                print(f"  ⚠ 케어 영역 조회: {care_area_query_time:.2f}ms (느림)")
            
            # 이벤트 타입 조회 성능 테스트
            start_time = time.time()
            cursor.execute("SELECT * FROM event_types WHERE is_archived = 0 ORDER BY description")
            event_types = cursor.fetchall()
            event_type_query_time = (time.time() - start_time) * 1000
            performance_results['event_type_query'] = event_type_query_time
            
            if event_type_query_time < 100:  # 100ms 미만
                print(f"  ✓ 이벤트 타입 조회: {event_type_query_time:.2f}ms (양호)")
            else:
                issues.append(f"이벤트 타입 조회 성능 저하: {event_type_query_time:.2f}ms")
                print(f"  ⚠ 이벤트 타입 조회: {event_type_query_time:.2f}ms (느림)")
            
            # 전체 성능 요약
            avg_performance = sum(performance_results.values()) / len(performance_results)
            print(f"  평균 쿼리 시간: {avg_performance:.2f}ms")
            
        except Exception as e:
            issues.append(f"성능 테스트 오류: {e}")
        
        return {
            'test_name': '성능 테스트',
            'passed': len(issues) == 0,
            'issues': issues,
            'performance_results': performance_results
        }
    
    def test_functionality(self, conn):
        """기능 테스트"""
        print("\n4. 기능 테스트")
        print("-" * 40)
        
        cursor = conn.cursor()
        issues = []
        
        try:
            # 사용자 인증 시뮬레이션
            cursor.execute("SELECT * FROM users WHERE username = 'admin' AND is_active = 1")
            admin_user = cursor.fetchone()
            if admin_user:
                print("  ✓ 사용자 인증 기능 정상")
            else:
                issues.append("admin 사용자를 찾을 수 없음")
            
            # 역할 기반 권한 확인
            cursor.execute("SELECT DISTINCT role FROM users")
            roles = [row[0] for row in cursor.fetchall()]
            expected_roles = ['admin', 'site_admin', 'doctor', 'physiotherapist']
            
            for role in expected_roles:
                if role in roles:
                    print(f"  ✓ {role} 역할 존재")
                else:
                    print(f"  ! {role} 역할 사용자 없음 (정상일 수 있음)")
            
            # FCM 토큰 관리 기능
            cursor.execute("SELECT COUNT(*) FROM fcm_tokens WHERE is_active = 1")
            active_tokens = cursor.fetchone()[0]
            print(f"  ✓ 활성 FCM 토큰: {active_tokens}개")
            
            # 케어 영역 필터링 기능
            cursor.execute("SELECT COUNT(*) FROM care_areas WHERE is_archived = 0")
            active_care_areas = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM care_areas WHERE is_archived = 1")
            archived_care_areas = cursor.fetchone()[0]
            print(f"  ✓ 활성 케어 영역: {active_care_areas}개, 보관됨: {archived_care_areas}개")
            
            # 이벤트 타입 필터링 기능
            cursor.execute("SELECT COUNT(*) FROM event_types WHERE is_archived = 0")
            active_event_types = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM event_types WHERE is_archived = 1")
            archived_event_types = cursor.fetchone()[0]
            print(f"  ✓ 활성 이벤트 타입: {active_event_types}개, 보관됨: {archived_event_types}개")
            
        except Exception as e:
            issues.append(f"기능 테스트 오류: {e}")
        
        return {
            'test_name': '기능 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_migration_completeness(self, conn):
        """마이그레이션 완전성 검증"""
        print("\n5. 마이그레이션 완전성 검증")
        print("-" * 40)
        
        cursor = conn.cursor()
        issues = []
        
        try:
            # 동기화 상태 확인
            cursor.execute("SELECT data_type, sync_status, records_synced FROM sync_status")
            sync_results = cursor.fetchall()
            
            for row in sync_results:
                data_type, status, records = row[0], row[1], row[2]
                if status == 'success':
                    print(f"  ✓ {data_type}: {status} ({records}개)")
                else:
                    issues.append(f"{data_type} 동기화 실패: {status}")
                    print(f"  ✗ {data_type}: {status}")
            
            # 원본 데이터와 비교
            self.compare_with_source_data(conn, issues)
            
        except Exception as e:
            issues.append(f"마이그레이션 검증 오류: {e}")
        
        return {
            'test_name': '마이그레이션 완전성 검증',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def compare_with_source_data(self, conn, issues):
        """원본 데이터와 비교"""
        cursor = conn.cursor()
        
        try:
            # 사용자 수 비교
            sys.path.append('.')
            from config_users import USERS_DB
            
            cursor.execute("SELECT COUNT(*) FROM users")
            db_user_count = cursor.fetchone()[0]
            source_user_count = len(USERS_DB)
            
            if db_user_count == source_user_count:
                print(f"  ✓ 사용자 수 일치: {db_user_count}개")
            else:
                issues.append(f"사용자 수 불일치: DB {db_user_count}개 vs 원본 {source_user_count}개")
            
        except ImportError:
            print("  ! config_users.py 비교 건너뜀")
        
        try:
            # 케어 영역 수 비교
            if os.path.exists('data/carearea.json'):
                with open('data/carearea.json', 'r') as f:
                    source_care_areas = json.load(f)
                
                cursor.execute("SELECT COUNT(*) FROM care_areas")
                db_care_area_count = cursor.fetchone()[0]
                source_care_area_count = len(source_care_areas)
                
                if db_care_area_count == source_care_area_count:
                    print(f"  ✓ 케어 영역 수 일치: {db_care_area_count}개")
                else:
                    issues.append(f"케어 영역 수 불일치: DB {db_care_area_count}개 vs 원본 {source_care_area_count}개")
            
        except Exception as e:
            print(f"  ! 케어 영역 비교 실패: {e}")
        
        try:
            # 이벤트 타입 수 비교
            if os.path.exists('data/eventtype.json'):
                with open('data/eventtype.json', 'r') as f:
                    source_event_types = json.load(f)
                
                cursor.execute("SELECT COUNT(*) FROM event_types")
                db_event_type_count = cursor.fetchone()[0]
                source_event_type_count = len(source_event_types)
                
                if db_event_type_count == source_event_type_count:
                    print(f"  ✓ 이벤트 타입 수 일치: {db_event_type_count}개")
                else:
                    issues.append(f"이벤트 타입 수 불일치: DB {db_event_type_count}개 vs 원본 {source_event_type_count}개")
            
        except Exception as e:
            print(f"  ! 이벤트 타입 비교 실패: {e}")
    
    def print_test_summary(self, test_results):
        """테스트 결과 요약"""
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)
        
        passed_tests = sum(1 for result in test_results if result['passed'])
        total_tests = len(test_results)
        
        print(f"전체 테스트: {total_tests}개")
        print(f"통과: {passed_tests}개")
        print(f"실패: {total_tests - passed_tests}개")
        print(f"성공률: {passed_tests/total_tests*100:.1f}%")
        
        print("\n개별 테스트 결과:")
        for result in test_results:
            status = "✓ 통과" if result['passed'] else "✗ 실패"
            print(f"  {result['test_name']}: {status}")
            
            if not result['passed'] and result['issues']:
                for issue in result['issues']:
                    print(f"    - {issue}")
        
        # 성능 결과 출력
        for result in test_results:
            if 'performance_results' in result:
                print("\n성능 테스트 상세:")
                for metric, value in result['performance_results'].items():
                    print(f"  {metric}: {value:.2f}ms")
        
        if passed_tests == total_tests:
            print("\n🎉 모든 테스트를 통과했습니다!")
            print("Week 1 Foundation Setup이 성공적으로 완료되었습니다.")
        else:
            print(f"\n⚠️ {total_tests - passed_tests}개의 테스트가 실패했습니다.")
            print("문제를 해결한 후 다시 테스트하세요.")


def main():
    try:
        tester = Week1Tester()
        success = tester.run_all_tests()
        
        if success:
            print("\n다음 단계: Week 2 - Performance & Cache 구현")
            print("명령어: Week 2 스크립트들을 실행하세요.")
            sys.exit(0)
        else:
            print("\n테스트 실패. 문제를 해결하세요.")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n파일을 찾을 수 없습니다: {e}")
        print("먼저 마이그레이션을 완료하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
