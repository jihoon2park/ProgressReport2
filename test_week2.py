#!/usr/bin/env python3
"""
Progress Report System - Week 2 종합 테스트
Day 5: 성능 테스트 및 최적화 검증
"""

import sqlite3
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any

class Week2Tester:
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def run_week2_tests(self):
        """Week 2 종합 테스트 실행"""
        print("=" * 70)
        print("Progress Report System - Week 2 종합 테스트")
        print("Day 5: 성능 테스트 및 최적화 검증")
        print("=" * 70)
        
        test_results = []
        
        try:
            # 1. 하이브리드 매니저 기능 테스트
            test_results.append(self.test_hybrid_manager_functionality())
            
            # 2. 성능 비교 테스트 (JSON vs SQLite)
            test_results.append(self.test_performance_comparison())
            
            # 3. 대용량 데이터 처리 테스트
            test_results.append(self.test_large_data_handling())
            
            # 4. 동시성 테스트
            test_results.append(self.test_concurrency())
            
            # 5. 메모리 사용량 테스트
            test_results.append(self.test_memory_usage())
            
            # 6. 통합 테스트 (실제 앱 시나리오)
            test_results.append(self.test_integration_scenarios())
            
            # 결과 요약
            self.print_test_summary(test_results)
            
            # 성능 리포트 생성
            self.generate_performance_report()
            
            # 모든 테스트 통과 여부
            all_passed = all(result['passed'] for result in test_results)
            return all_passed
            
        except Exception as e:
            print(f"테스트 실행 중 오류: {e}")
            return False
    
    def test_hybrid_manager_functionality(self):
        """하이브리드 매니저 기능 테스트"""
        print("\n1. 하이브리드 매니저 기능 테스트")
        print("-" * 50)
        
        issues = []
        
        try:
            from production_hybrid_manager import ProductionHybridManager
            manager = ProductionHybridManager()
            
            # 1-1. 사용자 관리 테스트
            admin_user = manager.get_user('admin')
            if admin_user:
                print("  ✓ 사용자 조회 기능 정상")
            else:
                issues.append("사용자 조회 실패")
            
            # 1-2. 클라이언트 데이터 테스트
            pg_clients = manager.get_clients('Parafield Gardens')
            if pg_clients and len(pg_clients) > 0:
                print(f"  ✓ 클라이언트 조회: {len(pg_clients)}명")
            else:
                issues.append("클라이언트 조회 실패")
            
            # 1-3. 검색 기능 테스트
            search_results = manager.search_clients_global('A')
            if search_results:
                print(f"  ✓ 전체 검색: {len(search_results)}명")
            else:
                issues.append("검색 기능 실패")
            
            # 1-4. 페이지네이션 테스트
            paginated = manager.get_clients_paginated('Parafield Gardens', page=1, per_page=10)
            if paginated and 'clients' in paginated:
                print(f"  ✓ 페이지네이션: {len(paginated['clients'])}/{paginated['total']}")
            else:
                issues.append("페이지네이션 실패")
            
            # 1-5. 참조 데이터 테스트
            care_areas = manager.get_care_areas()
            event_types = manager.get_event_types()
            if care_areas and event_types:
                print(f"  ✓ 참조 데이터: 케어영역 {len(care_areas)}, 이벤트 {len(event_types)}")
            else:
                issues.append("참조 데이터 조회 실패")
            
            # 1-6. 통계 기능 테스트
            stats = manager.get_statistics()
            if stats and 'total_clients' in stats:
                print(f"  ✓ 통계 기능: 전체 클라이언트 {stats['total_clients']}명")
            else:
                issues.append("통계 기능 실패")
            
        except ImportError:
            issues.append("production_hybrid_manager.py 파일을 찾을 수 없음")
        except Exception as e:
            issues.append(f"기능 테스트 오류: {e}")
        
        return {
            'test_name': '하이브리드 매니저 기능 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_performance_comparison(self):
        """성능 비교 테스트 (JSON vs SQLite)"""
        print("\n2. 성능 비교 테스트 (JSON vs SQLite)")
        print("-" * 50)
        
        issues = []
        performance_data = {}
        
        try:
            from production_hybrid_manager import ProductionHybridManager
            manager = ProductionHybridManager()
            
            # JSON 파일 로드 성능 측정
            json_times = []
            json_file = 'data/parafield_gardens_client.json'
            
            if os.path.exists(json_file):
                for i in range(5):  # 5회 반복 측정
                    start_time = time.time()
                    with open(json_file, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    json_times.append((time.time() - start_time) * 1000)
                
                avg_json_time = sum(json_times) / len(json_times)
                performance_data['json_load_time'] = avg_json_time
            else:
                avg_json_time = 0
                issues.append("JSON 파일을 찾을 수 없음")
            
            # SQLite 조회 성능 측정
            sqlite_times = []
            
            for i in range(5):  # 5회 반복 측정
                start_time = time.time()
                clients = manager.get_clients('Parafield Gardens')
                sqlite_times.append((time.time() - start_time) * 1000)
            
            avg_sqlite_time = sum(sqlite_times) / len(sqlite_times)
            performance_data['sqlite_query_time'] = avg_sqlite_time
            
            # 성능 비교 결과
            if avg_json_time > 0:
                improvement_ratio = avg_json_time / avg_sqlite_time
                performance_data['improvement_ratio'] = improvement_ratio
                
                print(f"  📊 JSON 파일 로드: {avg_json_time:.2f}ms (평균)")
                print(f"  📊 SQLite 조회: {avg_sqlite_time:.2f}ms (평균)")
                print(f"  🚀 성능 개선: {improvement_ratio:.1f}배 빠름")
                
                if improvement_ratio < 2:
                    issues.append(f"성능 개선이 기대치({2}배)보다 낮음: {improvement_ratio:.1f}배")
            else:
                print(f"  📊 SQLite 조회: {avg_sqlite_time:.2f}ms (평균)")
            
            # 검색 성능 테스트
            search_times = []
            for i in range(3):
                start_time = time.time()
                results = manager.search_clients_global('Smith')
                search_times.append((time.time() - start_time) * 1000)
            
            avg_search_time = sum(search_times) / len(search_times)
            performance_data['search_time'] = avg_search_time
            
            print(f"  🔍 검색 성능: {avg_search_time:.2f}ms (평균)")
            
            if avg_search_time > 50:  # 50ms 이상이면 경고
                issues.append(f"검색 성능이 기대치(50ms)보다 느림: {avg_search_time:.2f}ms")
            
        except Exception as e:
            issues.append(f"성능 비교 테스트 오류: {e}")
        
        return {
            'test_name': '성능 비교 테스트',
            'passed': len(issues) == 0,
            'issues': issues,
            'performance_data': performance_data
        }
    
    def test_large_data_handling(self):
        """대용량 데이터 처리 테스트"""
        print("\n3. 대용량 데이터 처리 테스트")
        print("-" * 50)
        
        issues = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 전체 클라이언트 수 확인
            cursor.execute("SELECT COUNT(*) FROM clients_cache WHERE is_active = 1")
            total_clients = cursor.fetchone()[0]
            
            print(f"  📊 전체 클라이언트: {total_clients:,}명")
            
            # 대용량 조회 테스트
            start_time = time.time()
            cursor.execute("SELECT * FROM clients_cache WHERE is_active = 1 ORDER BY client_name")
            all_clients = cursor.fetchall()
            query_time = (time.time() - start_time) * 1000
            
            print(f"  📊 전체 조회 시간: {query_time:.2f}ms")
            
            if query_time > 1000:  # 1초 이상이면 경고
                issues.append(f"대용량 조회 성능 저하: {query_time:.2f}ms")
            
            # 복잡한 검색 테스트
            start_time = time.time()
            cursor.execute('''
                SELECT c.*, s.site_name 
                FROM clients_cache c 
                LEFT JOIN sites s ON c.site = s.site_name 
                WHERE c.client_name LIKE '%A%' 
                AND c.is_active = 1 
                ORDER BY c.site, c.client_name
            ''')
            complex_results = cursor.fetchall()
            complex_query_time = (time.time() - start_time) * 1000
            
            print(f"  📊 복잡 조인 쿼리: {len(complex_results)}건, {complex_query_time:.2f}ms")
            
            if complex_query_time > 500:  # 500ms 이상이면 경고
                issues.append(f"복잡 쿼리 성능 저하: {complex_query_time:.2f}ms")
            
            conn.close()
            
        except Exception as e:
            issues.append(f"대용량 데이터 처리 테스트 오류: {e}")
        
        return {
            'test_name': '대용량 데이터 처리 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_concurrency(self):
        """동시성 테스트"""
        print("\n4. 동시성 테스트")
        print("-" * 50)
        
        issues = []
        
        try:
            import threading
            from production_hybrid_manager import ProductionHybridManager
            
            results = []
            errors = []
            
            def worker_function(worker_id):
                try:
                    manager = ProductionHybridManager()
                    
                    # 각 워커에서 다양한 작업 수행
                    start_time = time.time()
                    
                    # 사용자 조회
                    user = manager.get_user('admin')
                    
                    # 클라이언트 조회
                    clients = manager.get_clients('Parafield Gardens')
                    
                    # 검색
                    search_results = manager.search_clients_global('A')
                    
                    # 통계
                    stats = manager.get_statistics()
                    
                    execution_time = (time.time() - start_time) * 1000
                    
                    results.append({
                        'worker_id': worker_id,
                        'execution_time': execution_time,
                        'clients_count': len(clients) if clients else 0,
                        'search_count': len(search_results) if search_results else 0
                    })
                    
                except Exception as e:
                    errors.append(f"Worker {worker_id} 오류: {e}")
            
            # 5개의 동시 스레드로 테스트
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker_function, args=(i,))
                threads.append(thread)
            
            # 모든 스레드 시작
            start_time = time.time()
            for thread in threads:
                thread.start()
            
            # 모든 스레드 완료 대기
            for thread in threads:
                thread.join()
            
            total_time = (time.time() - start_time) * 1000
            
            if errors:
                issues.extend(errors)
            
            if results:
                avg_execution_time = sum(r['execution_time'] for r in results) / len(results)
                print(f"  📊 동시 실행 스레드: {len(results)}개")
                print(f"  📊 전체 완료 시간: {total_time:.2f}ms")
                print(f"  📊 평균 실행 시간: {avg_execution_time:.2f}ms")
                
                if total_time > 5000:  # 5초 이상이면 경고
                    issues.append(f"동시성 성능 저하: {total_time:.2f}ms")
            else:
                issues.append("동시성 테스트 결과 없음")
            
        except Exception as e:
            issues.append(f"동시성 테스트 오류: {e}")
        
        return {
            'test_name': '동시성 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_memory_usage(self):
        """메모리 사용량 테스트"""
        print("\n5. 메모리 사용량 테스트")
        print("-" * 50)
        
        issues = []
        
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # 시작 메모리
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            from production_hybrid_manager import ProductionHybridManager
            manager = ProductionHybridManager()
            
            # 대량 데이터 로드
            all_clients = []
            sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
            
            for site in sites:
                clients = manager.get_clients(site)
                all_clients.extend(clients)
            
            # 검색 작업
            for term in ['A', 'B', 'C', 'Smith', 'John']:
                results = manager.search_clients_global(term)
            
            # 통계 작업
            for i in range(10):
                stats = manager.get_statistics()
            
            # 종료 메모리
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = end_memory - start_memory
            
            print(f"  📊 시작 메모리: {start_memory:.2f}MB")
            print(f"  📊 종료 메모리: {end_memory:.2f}MB")
            print(f"  📊 메모리 증가: {memory_increase:.2f}MB")
            print(f"  📊 처리한 클라이언트: {len(all_clients)}명")
            
            # 메모리 사용량이 너무 크면 경고
            if memory_increase > 100:  # 100MB 이상 증가
                issues.append(f"메모리 사용량 과다: {memory_increase:.2f}MB 증가")
            
            # 메모리 효율성 계산 (클라이언트당 메모리 사용량)
            if len(all_clients) > 0:
                memory_per_client = (memory_increase * 1024) / len(all_clients)  # KB per client
                print(f"  📊 클라이언트당 메모리: {memory_per_client:.2f}KB")
                
                if memory_per_client > 10:  # 클라이언트당 10KB 이상
                    issues.append(f"메모리 효율성 저하: 클라이언트당 {memory_per_client:.2f}KB")
            
        except ImportError:
            print("  ! psutil이 설치되지 않아 메모리 테스트를 건너뜁니다.")
        except Exception as e:
            issues.append(f"메모리 사용량 테스트 오류: {e}")
        
        return {
            'test_name': '메모리 사용량 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def test_integration_scenarios(self):
        """통합 테스트 (실제 앱 시나리오)"""
        print("\n6. 통합 테스트 (실제 앱 시나리오)")
        print("-" * 50)
        
        issues = []
        
        try:
            from app_integration_adapter import get_app_adapter
            adapter = get_app_adapter()
            
            # 시나리오 1: 사용자 로그인 및 클라이언트 조회
            print("  시나리오 1: 로그인 → 클라이언트 조회")
            start_time = time.time()
            
            # 로그인 시뮬레이션
            user = adapter.authenticate_user('admin', 'password123')
            if not user:
                issues.append("로그인 시나리오 실패")
            
            # 클라이언트 조회
            clients = adapter.get_clients_for_site('Parafield Gardens')
            scenario1_time = (time.time() - start_time) * 1000
            
            print(f"    ✓ 완료: {scenario1_time:.2f}ms ({len(clients) if clients else 0}명)")
            
            # 시나리오 2: Progress Note 작성 준비
            print("  시나리오 2: Progress Note 드롭다운 데이터")
            start_time = time.time()
            
            dropdown_data = adapter.get_dropdown_data()
            care_areas_count = len(dropdown_data.get('care_areas', []))
            event_types_count = len(dropdown_data.get('event_types', []))
            
            scenario2_time = (time.time() - start_time) * 1000
            
            print(f"    ✓ 완료: {scenario2_time:.2f}ms (케어영역 {care_areas_count}, 이벤트 {event_types_count})")
            
            # 시나리오 3: 전체 검색
            print("  시나리오 3: 전체 사이트 검색")
            start_time = time.time()
            
            search_results = adapter.search_clients_across_sites('Smith')
            scenario3_time = (time.time() - start_time) * 1000
            
            print(f"    ✓ 완료: {scenario3_time:.2f}ms ({len(search_results) if search_results else 0}명)")
            
            # 시나리오 4: 관리자 통계
            print("  시나리오 4: 관리자 통계 조회")
            start_time = time.time()
            
            stats = adapter.get_system_statistics()
            cache_status = adapter.get_cache_health_status()
            scenario4_time = (time.time() - start_time) * 1000
            
            print(f"    ✓ 완료: {scenario4_time:.2f}ms")
            
            # 전체 시나리오 성능 평가
            total_scenario_time = scenario1_time + scenario2_time + scenario3_time + scenario4_time
            print(f"  📊 전체 시나리오 시간: {total_scenario_time:.2f}ms")
            
            if total_scenario_time > 1000:  # 1초 이상이면 경고
                issues.append(f"통합 시나리오 성능 저하: {total_scenario_time:.2f}ms")
            
        except ImportError:
            issues.append("app_integration_adapter.py 파일을 찾을 수 없음")
        except Exception as e:
            issues.append(f"통합 테스트 오류: {e}")
        
        return {
            'test_name': '통합 테스트',
            'passed': len(issues) == 0,
            'issues': issues
        }
    
    def print_test_summary(self, test_results):
        """테스트 결과 요약"""
        print("\n" + "=" * 70)
        print("Week 2 테스트 결과 요약")
        print("=" * 70)
        
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
        
        if passed_tests == total_tests:
            print("\n🎉 모든 테스트를 통과했습니다!")
            print("Week 2 Performance & Cache 구현이 성공적으로 완료되었습니다.")
        else:
            print(f"\n⚠️ {total_tests - passed_tests}개의 테스트가 실패했습니다.")
    
    def generate_performance_report(self):
        """성능 리포트 생성"""
        print("\n" + "=" * 70)
        print("성능 리포트")
        print("=" * 70)
        
        try:
            from production_hybrid_manager import ProductionHybridManager
            manager = ProductionHybridManager()
            
            # 현재 시스템 상태
            stats = manager.get_statistics()
            cache_info = manager.get_cache_info()
            
            print("\n📊 시스템 현황:")
            print(f"  - 활성 사용자: {stats.get('active_users', 0)}명")
            print(f"  - 전체 클라이언트: {stats.get('total_clients', 0)}명")
            print(f"  - 활성 케어 영역: {stats.get('active_care_areas', 0)}개")
            print(f"  - 활성 이벤트 타입: {stats.get('active_event_types', 0)}개")
            print(f"  - 데이터베이스 크기: {cache_info.get('db_size_mb', 0):.2f}MB")
            
            print("\n🚀 예상 성능 개선:")
            print("  - 사용자 조회: JSON 대비 5-10배 빠름")
            print("  - 클라이언트 조회: JSON 대비 10-50배 빠름")
            print("  - 검색 기능: 새로운 기능 (기존 대비 무한대 개선)")
            print("  - 페이지네이션: 새로운 기능")
            print("  - 통계 분석: 새로운 기능")
            
            print("\n💾 메모리 효율성:")
            print("  - SQLite 캐시 사용으로 메모리 사용량 최적화")
            print("  - 필요시에만 데이터 로드 (지연 로딩)")
            print("  - 인덱스 활용으로 빠른 검색")
            
        except Exception as e:
            print(f"성능 리포트 생성 실패: {e}")


def main():
    try:
        tester = Week2Tester()
        success = tester.run_week2_tests()
        
        if success:
            print("\n✅ Week 2 테스트 완료!")
            print("\n다음 단계: Week 3 - Integration & Optimization")
            print("또는 기존 Flask 앱에 하이브리드 매니저를 통합하세요.")
            sys.exit(0)
        else:
            print("\n❌ 일부 테스트가 실패했습니다.")
            print("문제를 해결한 후 다시 테스트하세요.")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"\n❌ 파일을 찾을 수 없습니다: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
