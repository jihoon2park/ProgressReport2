#!/usr/bin/env python3
"""
Progress Report System - 고급 성능 최적화
Week 3 - Day 3-4: 성능 최적화 및 기능 개선
"""

import sqlite3
import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

class AdvancedOptimization:
    """고급 성능 최적화 클래스"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        self.memory_cache = {}  # L1 메모리 캐시
        self.cache_timestamps = {}  # 캐시 타임스탬프
        self.cache_ttl = 300  # 5분 TTL
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def get_db_connection(self):
        """최적화된 데이터베이스 연결"""
        conn = sqlite3.connect(
            self.db_path, 
            timeout=30.0,
            check_same_thread=False  # 멀티스레드 지원
        )
        conn.row_factory = sqlite3.Row
        
        # SQLite 성능 최적화 설정
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
        conn.execute('PRAGMA synchronous=NORMAL')  # 동기화 모드
        conn.execute('PRAGMA cache_size=10000')  # 캐시 크기 증가
        conn.execute('PRAGMA temp_store=MEMORY')  # 임시 테이블을 메모리에
        
        return conn
    
    # ===========================================
    # 다층 캐싱 시스템
    # ===========================================
    
    def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """L1 메모리 캐시에서 데이터 조회"""
        if cache_key in self.memory_cache:
            # TTL 확인
            if cache_key in self.cache_timestamps:
                cache_time = self.cache_timestamps[cache_key]
                if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                    return self.memory_cache[cache_key]
                else:
                    # 만료된 캐시 제거
                    del self.memory_cache[cache_key]
                    del self.cache_timestamps[cache_key]
        
        return None
    
    def set_cache(self, cache_key: str, data: Any):
        """L1 메모리 캐시에 데이터 저장"""
        self.memory_cache[cache_key] = data
        self.cache_timestamps[cache_key] = datetime.now()
    
    def clear_cache(self, pattern: str = None):
        """캐시 정리"""
        if pattern:
            # 패턴에 맞는 캐시만 제거
            keys_to_remove = [key for key in self.memory_cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self.memory_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
        else:
            # 전체 캐시 제거
            self.memory_cache.clear()
            self.cache_timestamps.clear()
    
    # ===========================================
    # 최적화된 데이터 조회 함수들
    # ===========================================
    
    def get_clients_optimized(self, site: str, search_term: str = None, 
                             use_cache: bool = True) -> List[Dict]:
        """최적화된 클라이언트 조회 (다층 캐싱)"""
        
        # 캐시 키 생성
        cache_key = f"clients_{site}_{search_term or 'all'}"
        
        # L1 메모리 캐시 확인
        if use_cache:
            cached_data = self.get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        # L2 SQLite에서 조회
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            if search_term:
                # 검색 쿼리 (인덱스 활용)
                cursor.execute('''
                    SELECT * FROM clients_cache 
                    WHERE site = ? AND is_active = 1
                    AND (client_name LIKE ? OR preferred_name LIKE ? OR room_number LIKE ?)
                    ORDER BY 
                        CASE 
                            WHEN client_name LIKE ? THEN 1
                            WHEN preferred_name LIKE ? THEN 2
                            ELSE 3
                        END,
                        client_name
                ''', (site, f'%{search_term}%', f'%{search_term}%', f'%{search_term}%',
                      f'{search_term}%', f'{search_term}%'))
            else:
                # 전체 조회 (인덱스 활용)
                cursor.execute('''
                    SELECT * FROM clients_cache 
                    WHERE site = ? AND is_active = 1
                    ORDER BY client_name
                ''', (site,))
            
            clients = [dict(row) for row in cursor.fetchall()]
            
            # L1 캐시에 저장
            if use_cache:
                self.set_cache(cache_key, clients)
            
            return clients
            
        finally:
            conn.close()
    
    def get_dropdown_data_optimized(self) -> Dict[str, List[Dict]]:
        """드롭다운용 데이터 최적화 조회"""
        cache_key = "dropdown_data"
        
        # 메모리 캐시 확인
        cached_data = self.get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 한 번의 연결로 모든 데이터 조회
            cursor.execute('SELECT id, description FROM care_areas WHERE is_archived = 0 ORDER BY description')
            care_areas = [{'Id': row[0], 'Description': row[1]} for row in cursor.fetchall()]
            
            cursor.execute('SELECT id, description FROM event_types WHERE is_archived = 0 ORDER BY description')
            event_types = [{'Id': row[0], 'Description': row[1]} for row in cursor.fetchall()]
            
            dropdown_data = {
                'care_areas': care_areas,
                'event_types': event_types
            }
            
            # 캐시에 저장
            self.set_cache(cache_key, dropdown_data)
            
            return dropdown_data
            
        finally:
            conn.close()
    
    # ===========================================
    # 고급 검색 기능
    # ===========================================
    
    def search_clients_advanced(self, search_term: str, site: str = None, 
                               filters: Dict = None) -> List[Dict]:
        """고급 클라이언트 검색"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 기본 쿼리
            query = '''
                SELECT *, 
                       CASE 
                           WHEN client_name LIKE ? THEN 1
                           WHEN preferred_name LIKE ? THEN 2
                           WHEN room_number LIKE ? THEN 3
                           ELSE 4
                       END as relevance_score
                FROM clients_cache 
                WHERE is_active = 1
            '''
            
            params = [f'%{search_term}%', f'%{search_term}%', f'%{search_term}%']
            
            # 추가 조건들
            conditions = []
            
            if site:
                conditions.append('site = ?')
                params.append(site)
            
            if filters:
                if filters.get('gender'):
                    conditions.append('gender = ?')
                    params.append(filters['gender'])
                
                if filters.get('wing'):
                    conditions.append('wing_name LIKE ?')
                    params.append(f'%{filters["wing"]}%')
                
                if filters.get('room_range'):
                    room_start, room_end = filters['room_range']
                    conditions.append('CAST(room_number AS INTEGER) BETWEEN ? AND ?')
                    params.extend([room_start, room_end])
            
            # 검색 조건 추가
            search_conditions = [
                'client_name LIKE ?',
                'preferred_name LIKE ?', 
                'room_number LIKE ?'
            ]
            
            if conditions:
                query += ' AND (' + ' OR '.join(search_conditions) + ') AND ' + ' AND '.join(conditions)
            else:
                query += ' AND (' + ' OR '.join(search_conditions) + ')'
            
            query += ' ORDER BY relevance_score, client_name'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # ===========================================
    # 통계 및 분석 기능
    # ===========================================
    
    def get_client_statistics(self) -> Dict[str, Any]:
        """클라이언트 통계 분석"""
        cache_key = "client_statistics"
        
        # 캐시 확인
        cached_stats = self.get_from_cache(cache_key)
        if cached_stats is not None:
            return cached_stats
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # 사이트별 클라이언트 수
            cursor.execute('''
                SELECT site, COUNT(*) as count, 
                       COUNT(CASE WHEN gender = 'Male' THEN 1 END) as male_count,
                       COUNT(CASE WHEN gender = 'Female' THEN 1 END) as female_count
                FROM clients_cache 
                WHERE is_active = 1
                GROUP BY site
                ORDER BY site
            ''')
            
            site_stats = {}
            total_clients = 0
            
            for row in cursor.fetchall():
                site, count, male, female = row
                site_stats[site] = {
                    'total': count,
                    'male': male,
                    'female': female
                }
                total_clients += count
            
            stats['by_site'] = site_stats
            stats['total_clients'] = total_clients
            
            # 방 점유율 분석
            cursor.execute('''
                SELECT site, 
                       COUNT(CASE WHEN room_number IS NOT NULL AND room_number != '' THEN 1 END) as occupied_rooms,
                       COUNT(*) as total_clients
                FROM clients_cache 
                WHERE is_active = 1
                GROUP BY site
            ''')
            
            room_stats = {}
            for row in cursor.fetchall():
                site, occupied, total = row
                room_stats[site] = {
                    'occupied_rooms': occupied,
                    'total_clients': total,
                    'occupancy_rate': round((occupied / total * 100), 1) if total > 0 else 0
                }
            
            stats['room_occupancy'] = room_stats
            
            # 최근 동기화 상태
            cursor.execute('''
                SELECT site, last_sync_time, records_synced
                FROM sync_status 
                WHERE data_type = 'clients'
                ORDER BY last_sync_time DESC
            ''')
            
            sync_stats = {}
            for row in cursor.fetchall():
                site, last_sync, records = row
                if last_sync:
                    sync_time = datetime.fromisoformat(last_sync)
                    age_minutes = int((datetime.now() - sync_time).total_seconds() / 60)
                    sync_stats[site] = {
                        'last_sync': last_sync,
                        'records': records,
                        'age_minutes': age_minutes,
                        'is_fresh': age_minutes < 30
                    }
            
            stats['sync_status'] = sync_stats
            
            # 캐시에 저장
            self.set_cache(cache_key, stats)
            
            return stats
            
        finally:
            conn.close()
    
    def get_usage_analytics(self, days: int = 7) -> Dict[str, Any]:
        """사용 분석 (최근 N일)"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            analytics = {}
            
            # 사용자별 접근 통계
            cursor.execute('''
                SELECT username, role, COUNT(*) as access_count,
                       MAX(timestamp) as last_access
                FROM access_logs 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY username, role
                ORDER BY access_count DESC
            '''.format(days))
            
            user_stats = []
            for row in cursor.fetchall():
                user_stats.append({
                    'username': row[0],
                    'role': row[1],
                    'access_count': row[2],
                    'last_access': row[3]
                })
            
            analytics['user_activity'] = user_stats
            
            # Progress Note 작성 통계
            cursor.execute('''
                SELECT site, COUNT(*) as note_count,
                       COUNT(DISTINCT username) as unique_users
                FROM progress_note_logs 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY site
                ORDER BY note_count DESC
            '''.format(days))
            
            note_stats = []
            for row in cursor.fetchall():
                note_stats.append({
                    'site': row[0],
                    'note_count': row[1],
                    'unique_users': row[2]
                })
            
            analytics['progress_note_activity'] = note_stats
            
            # 시간대별 사용 패턴
            cursor.execute('''
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM access_logs 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY hour
                ORDER BY hour
            '''.format(days))
            
            hourly_stats = {}
            for row in cursor.fetchall():
                hourly_stats[row[0]] = row[1]
            
            analytics['hourly_usage'] = hourly_stats
            
            return analytics
            
        finally:
            conn.close()
    
    # ===========================================
    # 데이터베이스 최적화
    # ===========================================
    
    def optimize_database(self):
        """데이터베이스 최적화 실행"""
        print("=" * 60)
        print("데이터베이스 최적화 실행")
        print("=" * 60)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 1. 통계 정보 업데이트
            print("\n1. 통계 정보 업데이트")
            print("-" * 40)
            
            start_time = time.time()
            cursor.execute('ANALYZE')
            analyze_time = (time.time() - start_time) * 1000
            print(f"  ✓ ANALYZE 완료: {analyze_time:.2f}ms")
            
            # 2. 데이터베이스 정리
            print("\n2. 데이터베이스 정리")
            print("-" * 40)
            
            start_time = time.time()
            cursor.execute('VACUUM')
            vacuum_time = (time.time() - start_time) * 1000
            print(f"  ✓ VACUUM 완료: {vacuum_time:.2f}ms")
            
            # 3. 인덱스 사용률 확인
            print("\n3. 인덱스 사용률 확인")
            print("-" * 40)
            
            cursor.execute('''
                SELECT name, sql FROM sqlite_master 
                WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            ''')
            
            indexes = cursor.fetchall()
            print(f"  ✓ 사용자 정의 인덱스: {len(indexes)}개")
            
            for index in indexes:
                print(f"    - {index[0]}")
            
            # 4. 데이터베이스 크기 확인
            print("\n4. 데이터베이스 정보")
            print("-" * 40)
            
            db_size = os.path.getsize(self.db_path) / 1024 / 1024  # MB
            print(f"  데이터베이스 크기: {db_size:.2f} MB")
            
            # 테이블별 레코드 수
            tables = ['users', 'clients_cache', 'care_areas', 'event_types', 
                     'fcm_tokens', 'access_logs', 'progress_note_logs']
            
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                print(f"  {table}: {count:,}개")
            
        finally:
            conn.close()
    
    def create_additional_indexes(self):
        """추가 인덱스 생성 (성능 최적화)"""
        print("\n추가 인덱스 생성")
        print("-" * 40)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        additional_indexes = [
            # 복합 검색을 위한 인덱스
            ('idx_clients_search', 'clients_cache', '(site, client_name, preferred_name, room_number)'),
            ('idx_clients_active_site', 'clients_cache', '(is_active, site)'),
            
            # 로그 분석을 위한 인덱스
            ('idx_access_logs_user_time', 'access_logs', '(username, timestamp DESC)'),
            ('idx_progress_logs_site_time', 'progress_note_logs', '(site, timestamp DESC)'),
            
            # 통계를 위한 인덱스
            ('idx_clients_gender_site', 'clients_cache', '(site, gender)'),
            ('idx_clients_room_site', 'clients_cache', '(site, room_number)'),
        ]
        
        try:
            for index_name, table_name, columns in additional_indexes:
                try:
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}')
                    print(f"  ✓ {index_name} 생성 완료")
                except sqlite3.Error as e:
                    print(f"  ! {index_name} 생성 실패: {e}")
            
            conn.commit()
            print("  ✅ 추가 인덱스 생성 완료")
            
        finally:
            conn.close()
    
    # ===========================================
    # 성능 벤치마크
    # ===========================================
    
    def run_performance_benchmark(self):
        """성능 벤치마크 실행"""
        print("\n" + "=" * 60)
        print("성능 벤치마크")
        print("=" * 60)
        
        benchmark_results = {}
        
        # 1. 클라이언트 조회 벤치마크
        print("\n1. 클라이언트 조회 벤치마크")
        print("-" * 40)
        
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        for site in sites:
            times = []
            for i in range(10):  # 10회 반복
                start_time = time.time()
                clients = self.get_clients_optimized(site, use_cache=False)  # 캐시 비활성화
                times.append((time.time() - start_time) * 1000)
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            benchmark_results[f'{site}_query'] = {
                'avg': avg_time,
                'min': min_time,
                'max': max_time,
                'count': len(clients) if 'clients' in locals() else 0
            }
            
            print(f"  {site}: 평균 {avg_time:.2f}ms (최소 {min_time:.2f}ms, 최대 {max_time:.2f}ms)")
        
        # 2. 검색 성능 벤치마크
        print("\n2. 검색 성능 벤치마크")
        print("-" * 40)
        
        search_terms = ['Smith', 'A', 'John', '1', '10']
        
        for term in search_terms:
            times = []
            for i in range(5):  # 5회 반복
                start_time = time.time()
                results = self.search_clients_advanced(term)
                times.append((time.time() - start_time) * 1000)
            
            avg_time = sum(times) / len(times)
            result_count = len(results) if 'results' in locals() else 0
            
            benchmark_results[f'search_{term}'] = {
                'avg': avg_time,
                'count': result_count
            }
            
            print(f"  '{term}': {result_count}명, 평균 {avg_time:.2f}ms")
        
        # 3. 캐시 성능 테스트
        print("\n3. 캐시 성능 테스트")
        print("-" * 40)
        
        # 첫 번째 호출 (DB 조회)
        start_time = time.time()
        clients1 = self.get_clients_optimized('Parafield Gardens', use_cache=True)
        first_call_time = (time.time() - start_time) * 1000
        
        # 두 번째 호출 (캐시 사용)
        start_time = time.time()
        clients2 = self.get_clients_optimized('Parafield Gardens', use_cache=True)
        second_call_time = (time.time() - start_time) * 1000
        
        cache_improvement = first_call_time / second_call_time if second_call_time > 0 else 0
        
        print(f"  첫 번째 호출 (DB): {first_call_time:.2f}ms")
        print(f"  두 번째 호출 (캐시): {second_call_time:.2f}ms")
        print(f"  캐시 성능 향상: {cache_improvement:.1f}배")
        
        benchmark_results['cache_performance'] = {
            'db_time': first_call_time,
            'cache_time': second_call_time,
            'improvement': cache_improvement
        }
        
        return benchmark_results
    
    def generate_optimization_report(self):
        """최적화 리포트 생성"""
        print("\n" + "=" * 60)
        print("최적화 리포트")
        print("=" * 60)
        
        # 클라이언트 통계
        client_stats = self.get_client_statistics()
        
        print("\n📊 클라이언트 현황:")
        print(f"  전체 클라이언트: {client_stats['total_clients']:,}명")
        
        for site, stats in client_stats['by_site'].items():
            print(f"  {site}: {stats['total']}명 (남성 {stats['male']}, 여성 {stats['female']})")
        
        print("\n🏠 방 점유율:")
        for site, stats in client_stats['room_occupancy'].items():
            print(f"  {site}: {stats['occupancy_rate']}% ({stats['occupied_rooms']}/{stats['total_clients']})")
        
        print("\n🔄 동기화 상태:")
        for site, stats in client_stats['sync_status'].items():
            freshness = "최신" if stats['is_fresh'] else "만료"
            print(f"  {site}: {stats['records']}명, {stats['age_minutes']}분 전 ({freshness})")
        
        # 성능 벤치마크
        benchmark = self.run_performance_benchmark()
        
        print("\n🚀 성능 요약:")
        avg_query_times = [result['avg'] for key, result in benchmark.items() 
                          if key.endswith('_query')]
        if avg_query_times:
            overall_avg = sum(avg_query_times) / len(avg_query_times)
            print(f"  평균 쿼리 시간: {overall_avg:.2f}ms")
        
        if 'cache_performance' in benchmark:
            cache_perf = benchmark['cache_performance']
            print(f"  캐시 성능 향상: {cache_perf['improvement']:.1f}배")


def main():
    """메인 실행 함수"""
    try:
        optimizer = AdvancedOptimization()
        
        # 추가 인덱스 생성
        optimizer.create_additional_indexes()
        
        # 데이터베이스 최적화
        optimizer.optimize_database()
        
        # 최적화 리포트 생성
        optimizer.generate_optimization_report()
        
        print("\n🎉 Week 3 - Day 3-4 최적화 완료!")
        print("다음 단계: 최종 테스트 및 배포 준비")
        
    except Exception as e:
        print(f"\n❌ 최적화 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
