# Progress Report System - 성능 최적화 전략

## 🎯 성능 목표

| 작업 | 현재 (JSON) | 목표 (SQLite) | 개선율 |
|------|-------------|---------------|--------|
| 사용자 로그인 | 100ms | 20ms | **5x** |
| 클라이언트 검색 | 500ms | 50ms | **10x** |
| 드롭다운 로딩 | 200ms | 20ms | **10x** |
| Progress Note 저장 | 300ms | 30ms | **10x** |
| 로그 조회 | 1000ms | 100ms | **10x** |

## 🔧 최적화 기법

### 1. **데이터베이스 최적화**

#### 인덱스 전략
```sql
-- 자주 사용되는 쿼리 패턴별 인덱스
CREATE INDEX idx_clients_search ON clients_cache(site, client_name, room_number);
CREATE INDEX idx_logs_user_time ON access_logs(user_id, timestamp DESC);
CREATE INDEX idx_progress_notes_client_time ON progress_note_logs(client_id, timestamp DESC);

-- 복합 인덱스로 커버링 인덱스 활용
CREATE INDEX idx_clients_list ON clients_cache(site, is_active) 
    INCLUDE (client_name, preferred_name, room_number);
```

#### 쿼리 최적화
```python
# Before: 전체 데이터 로드 후 필터링
def get_clients_old(site, room_filter=None):
    with open(f'{site}_client.json', 'r') as f:
        all_clients = json.load(f)
    
    if room_filter:
        return [c for c in all_clients if room_filter in c.get('room_number', '')]
    return all_clients

# After: DB에서 필터링된 결과만 조회
def get_clients_new(site, room_filter=None):
    query = "SELECT * FROM clients_cache WHERE site = ? AND is_active = 1"
    params = [site]
    
    if room_filter:
        query += " AND room_number LIKE ?"
        params.append(f"%{room_filter}%")
    
    with get_db_connection() as conn:
        return conn.execute(query, params).fetchall()
```

### 2. **캐싱 전략**

#### 다층 캐싱
```python
class MultiLevelCache:
    def __init__(self):
        self.memory_cache = {}  # L1: 메모리 캐시
        self.db_cache = None    # L2: SQLite 캐시
        self.json_backup = None # L3: JSON 백업
    
    def get_data(self, key):
        # L1: 메모리에서 확인
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2: DB에서 확인
        data = self.get_from_db(key)
        if data:
            self.memory_cache[key] = data  # L1에 캐시
            return data
        
        # L3: JSON에서 로드
        data = self.get_from_json(key)
        if data:
            self.save_to_db(key, data)      # L2에 저장
            self.memory_cache[key] = data   # L1에 캐시
            return data
        
        return None
```

#### 스마트 캐시 무효화
```python
class SmartCacheInvalidation:
    def __init__(self):
        self.cache_dependencies = {
            'clients': ['progress_notes', 'incidents'],
            'care_areas': ['progress_notes'],
            'event_types': ['progress_notes']
        }
    
    def invalidate_cache(self, data_type):
        """연관된 캐시들도 함께 무효화"""
        # 직접 무효화
        self.clear_cache(data_type)
        
        # 의존성이 있는 캐시들도 무효화
        for dependent in self.cache_dependencies.get(data_type, []):
            self.clear_cache(dependent)
```

### 3. **비동기 처리**

#### 백그라운드 동기화
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncDataSync:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def sync_all_data(self):
        """모든 데이터를 병렬로 동기화"""
        tasks = [
            self.sync_clients('Parafield Gardens'),
            self.sync_clients('Nerrilda'),
            self.sync_clients('Ramsay'),
            self.sync_clients('Yankalilla'),
            self.sync_reference_data()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def sync_clients(self, site):
        """개별 사이트 클라이언트 동기화"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._sync_clients_sync, 
            site
        )
```

### 4. **연결 풀링**

#### SQLite 연결 관리
```python
import sqlite3
from contextlib import contextmanager
import threading

class ConnectionPool:
    def __init__(self, db_path, max_connections=10):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool = []
        self.lock = threading.Lock()
    
    @contextmanager
    def get_connection(self):
        conn = self._get_connection()
        try:
            yield conn
        finally:
            self._return_connection(conn)
    
    def _get_connection(self):
        with self.lock:
            if self.pool:
                return self.pool.pop()
            else:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                conn.row_factory = sqlite3.Row
                return conn
    
    def _return_connection(self, conn):
        with self.lock:
            if len(self.pool) < self.max_connections:
                self.pool.append(conn)
            else:
                conn.close()
```

### 5. **메모리 최적화**

#### 지연 로딩
```python
class LazyDataLoader:
    def __init__(self):
        self._clients = None
        self._care_areas = None
        self._event_types = None
    
    @property
    def clients(self):
        if self._clients is None:
            self._clients = self.load_clients()
        return self._clients
    
    @property
    def care_areas(self):
        if self._care_areas is None:
            self._care_areas = self.load_care_areas()
        return self._care_areas
    
    def clear_cache(self):
        """메모리 사용량 정리"""
        self._clients = None
        self._care_areas = None
        self._event_types = None
```

#### 페이지네이션
```python
def get_clients_paginated(site, page=1, per_page=50, search_term=None):
    """페이지네이션으로 메모리 사용량 최적화"""
    offset = (page - 1) * per_page
    
    query = """
        SELECT * FROM clients_cache 
        WHERE site = ? AND is_active = 1
    """
    params = [site]
    
    if search_term:
        query += " AND (client_name LIKE ? OR room_number LIKE ?)"
        params.extend([f"%{search_term}%", f"%{search_term}%"])
    
    query += " ORDER BY client_name LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    
    with get_db_connection() as conn:
        clients = conn.execute(query, params).fetchall()
        
        # 전체 개수도 함께 반환
        count_query = query.replace("SELECT *", "SELECT COUNT(*)").split("ORDER BY")[0]
        total = conn.execute(count_query, params[:-2]).fetchone()[0]
        
        return {
            'clients': [dict(c) for c in clients],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
```

## 📊 성능 모니터링

### 쿼리 성능 측정
```python
import time
import logging
from functools import wraps

def measure_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = (end_time - start_time) * 1000  # ms
        logging.info(f"{func.__name__} 실행시간: {execution_time:.2f}ms")
        
        # 성능 임계값 경고
        if execution_time > 100:  # 100ms 이상
            logging.warning(f"{func.__name__} 성능 저하: {execution_time:.2f}ms")
        
        return result
    return wrapper

@measure_performance
def get_clients_with_monitoring(site):
    return get_clients(site)
```

### 캐시 히트율 모니터링
```python
class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    @property
    def hit_rate(self):
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def get_stats(self):
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{self.hit_rate:.1f}%",
            'total_requests': self.hits + self.misses
        }
```

## 🔍 성능 테스트 시나리오

### 1. 부하 테스트
```python
import asyncio
import time

async def load_test_clients():
    """클라이언트 조회 부하 테스트"""
    sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
    
    start_time = time.time()
    
    # 100개의 동시 요청
    tasks = []
    for i in range(100):
        site = sites[i % len(sites)]
        tasks.append(get_clients(site))
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"100개 요청 처리 시간: {total_time:.2f}초")
    print(f"평균 응답 시간: {total_time/100*1000:.2f}ms")
    print(f"초당 처리량: {100/total_time:.2f} req/sec")
```

### 2. 메모리 사용량 테스트
```python
import psutil
import os

def memory_usage_test():
    """메모리 사용량 측정"""
    process = psutil.Process(os.getpid())
    
    # 시작 메모리
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 대량 데이터 로드
    all_clients = []
    for site in ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']:
        clients = get_clients(site)
        all_clients.extend(clients)
    
    # 종료 메모리
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"시작 메모리: {start_memory:.2f}MB")
    print(f"종료 메모리: {end_memory:.2f}MB")
    print(f"메모리 증가: {end_memory - start_memory:.2f}MB")
    print(f"클라이언트 수: {len(all_clients)}")
```

## 🎯 최적화 체크리스트

### ✅ 데이터베이스 최적화
- [ ] 적절한 인덱스 생성
- [ ] 쿼리 실행 계획 분석
- [ ] 불필요한 데이터 정리
- [ ] VACUUM 실행으로 DB 최적화

### ✅ 캐싱 최적화
- [ ] 다층 캐싱 구현
- [ ] 캐시 만료 정책 설정
- [ ] 캐시 히트율 모니터링
- [ ] 메모리 사용량 제한

### ✅ 코드 최적화
- [ ] 비동기 처리 구현
- [ ] 연결 풀링 적용
- [ ] 지연 로딩 구현
- [ ] 페이지네이션 적용

### ✅ 모니터링
- [ ] 성능 메트릭 수집
- [ ] 로그 분석 시스템
- [ ] 알림 시스템 구축
- [ ] 정기적 성능 리포트

이 최적화 전략을 통해 **JSON 기반 시스템 대비 10배 이상의 성능 향상**을 달성할 수 있습니다!
