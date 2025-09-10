# 클라이언트 업데이트 로직 분석

## 🔍 현재 시스템의 클라이언트 업데이트 상황

### 📊 **현재 구현된 업데이트 방식**

#### 1. **수동 업데이트 (현재 방식)**
```python
# update_client_list.py
success, client_info = fetch_client_information('Parafield Gardens')
```
- ✅ 기존에 `update_client_list.py` 파일 존재
- ✅ API에서 최신 클라이언트 정보를 가져와서 JSON 파일 업데이트
- ❌ **수동 실행 필요** - 자동화되지 않음

#### 2. **로그인 시 업데이트**
```python
# app.py - 로그인 라우트에서
client_success, client_info = fetch_client_information(site)
```
- ✅ 사용자가 로그인할 때마다 최신 데이터 가져옴
- ❌ **로그인할 때만 업데이트** - 실시간 반영 안됨

#### 3. **SQLite 캐시 업데이트**
```python
# migration_phase3.py
cursor.execute('DELETE FROM clients_cache WHERE site = ?', (site_name,))
# 새 데이터 삽입
```
- ✅ 기존 데이터 삭제 후 새 데이터 삽입
- ❌ **일회성 마이그레이션** - 지속적 업데이트 없음

---

## 🚨 **새로운 거주자 추가 시 문제점**

### **현재 상황**
1. **새 거주자가 시설에 입소** → 외부 시스템(API)에 등록
2. **우리 시스템은 모름** → SQLite 캐시에 반영 안됨
3. **사용자가 로그인해야** → 그때서야 최신 데이터 가져옴
4. **SQLite는 업데이트 안됨** → 캐시된 데이터 그대로 사용

### **문제 시나리오**
```
시간 09:00 - 새 거주자 "김철수" 입소 (외부 시스템에 등록)
시간 09:30 - 간병사가 Progress Note 작성하려고 함
         → SQLite 캐시에는 "김철수" 없음
         → 드롭다운에 "김철수" 안 나타남
시간 10:00 - 간병사가 로그아웃 후 재로그인
         → 로그인 시 API 호출로 최신 데이터 가져옴
         → 하지만 SQLite는 여전히 이전 데이터
```

---

## 💡 **해결 방안 제안**

### **Option 1: 실시간 동기화 시스템 (권장)**

```python
# realtime_sync.py
class RealtimeClientSync:
    def __init__(self):
        self.sync_interval = 300  # 5분마다
        
    async def auto_sync_clients(self):
        """모든 사이트의 클라이언트 데이터 자동 동기화"""
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        
        for site in sites:
            try:
                # API에서 최신 데이터 가져오기
                success, latest_clients = fetch_client_information(site)
                
                if success:
                    # SQLite 캐시 업데이트
                    self.update_sqlite_cache(site, latest_clients)
                    
                    # 변경사항 로그
                    changes = self.detect_changes(site, latest_clients)
                    if changes:
                        self.log_client_changes(site, changes)
                        
            except Exception as e:
                logger.error(f"{site} 동기화 실패: {e}")
    
    def update_sqlite_cache(self, site, latest_clients):
        """SQLite 캐시 업데이트"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 기존 데이터 비활성화
            cursor.execute(
                'UPDATE clients_cache SET is_active = 0 WHERE site = ?', 
                (site,)
            )
            
            # 새 데이터 삽입/업데이트
            for client in latest_clients:
                cursor.execute('''
                    INSERT OR REPLACE INTO clients_cache 
                    (person_id, client_name, preferred_name, room_number, 
                     site, last_synced, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    client['PersonId'],
                    client['ClientName'],
                    client['PreferredName'],
                    client['RoomNumber'],
                    site,
                    datetime.now().isoformat(),
                    True
                ))
            
            conn.commit()
    
    def detect_changes(self, site, latest_clients):
        """변경사항 감지"""
        changes = {
            'new_clients': [],
            'updated_clients': [],
            'removed_clients': []
        }
        
        # 기존 데이터와 비교하여 변경사항 감지
        # ... 구현 로직
        
        return changes
```

### **Option 2: 웹훅 기반 업데이트**

```python
# webhook_handler.py
@app.route('/webhook/client-update', methods=['POST'])
def handle_client_update():
    """외부 시스템에서 클라이언트 변경 시 호출되는 웹훅"""
    data = request.get_json()
    
    site = data.get('site')
    action = data.get('action')  # 'add', 'update', 'remove'
    client_info = data.get('client')
    
    if action == 'add':
        add_new_client_to_cache(site, client_info)
    elif action == 'update':
        update_client_in_cache(site, client_info)
    elif action == 'remove':
        remove_client_from_cache(site, client_info['PersonId'])
    
    return jsonify({'success': True})
```

### **Option 3: 온디맨드 새로고침**

```python
# 기존 앱에 추가
@app.route('/api/refresh-clients/<site>', methods=['POST'])
@login_required
def refresh_clients(site):
    """클라이언트 데이터 수동 새로고침"""
    try:
        # API에서 최신 데이터 가져오기
        success, latest_clients = fetch_client_information(site)
        
        if success:
            # SQLite 업데이트
            update_clients_cache(site, latest_clients)
            
            return jsonify({
                'success': True,
                'message': f'{site} 클라이언트 데이터 업데이트 완료',
                'count': len(latest_clients)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'API에서 데이터를 가져올 수 없습니다'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
```

---

## 🛠️ **즉시 구현 가능한 개선안**

### **1. 캐시 만료 기반 자동 업데이트**
```python
def get_clients_with_auto_refresh(site, max_age_minutes=30):
    """캐시가 오래되면 자동으로 새로고침"""
    
    # 마지막 동기화 시간 확인
    last_sync = get_last_sync_time(site)
    
    if not last_sync or is_cache_expired(last_sync, max_age_minutes):
        # 캐시가 만료되었으면 API에서 새로 가져오기
        refresh_clients_cache(site)
    
    # SQLite에서 데이터 반환
    return get_clients_from_sqlite(site)
```

### **2. 백그라운드 동기화 작업**
```python
# background_sync.py
import schedule
import time
import threading

def background_client_sync():
    """백그라운드에서 주기적으로 클라이언트 데이터 동기화"""
    
    def sync_all_sites():
        sites = ['Parafield Gardens', 'Nerrilda', 'Ramsay', 'Yankalilla']
        for site in sites:
            try:
                refresh_clients_cache(site)
                print(f"{site} 동기화 완료")
            except Exception as e:
                print(f"{site} 동기화 실패: {e}")
    
    # 매 30분마다 실행
    schedule.every(30).minutes.do(sync_all_sites)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 스케줄 확인

# Flask 앱 시작 시 백그라운드 스레드 시작
def start_background_sync():
    sync_thread = threading.Thread(target=background_client_sync, daemon=True)
    sync_thread.start()
```

### **3. UI에서 새로고침 버튼 추가**
```javascript
// Progress Note 페이지에 추가
function refreshClientList() {
    const site = getCurrentSite();
    
    // 로딩 표시
    showLoading('클라이언트 데이터 업데이트 중...');
    
    fetch(`/api/refresh-clients/${site}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 클라이언트 드롭다운 새로고침
            reloadClientDropdown();
            showMessage(`${data.count}명의 클라이언트 데이터가 업데이트되었습니다.`);
        } else {
            showError(data.message);
        }
    })
    .finally(() => {
        hideLoading();
    });
}
```

---

## 📋 **구현 우선순위**

### **🚀 즉시 구현 (Week 3)**
1. **캐시 만료 확인 로직** - 30분 이상 된 캐시 자동 갱신
2. **수동 새로고침 API** - `/api/refresh-clients/<site>`
3. **UI 새로고침 버튼** - Progress Note 페이지에 추가

### **📅 단기 구현 (1-2주)**
4. **백그라운드 동기화** - 30분마다 자동 동기화
5. **변경사항 감지** - 신규/수정/삭제 클라이언트 로그

### **🔮 장기 구현 (1개월+)**
6. **웹훅 시스템** - 외부 시스템과 실시간 연동
7. **실시간 알림** - 새 거주자 추가 시 사용자에게 알림

---

## 💭 **결론**

**현재 상황**: 새로운 거주자가 추가되어도 SQLite 캐시에 즉시 반영되지 않음

**해결책**: 
1. **즉시**: 캐시 만료 기반 자동 갱신
2. **단기**: 백그라운드 동기화 시스템  
3. **장기**: 실시간 웹훅 연동

이렇게 하면 새로운 거주자가 추가되어도 30분 이내에는 시스템에 반영되고, 필요시 수동으로 즉시 새로고침할 수 있습니다.
