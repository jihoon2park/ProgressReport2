/**
 * 프로그레스 노트 IndexedDB 관리 모듈
 * 사이트별로 프로그레스 노트를 저장하고 조회하는 기능
 */

class ProgressNoteDB {
    constructor() {
        this.dbName = 'ProgressNoteDB';
        this.version = 3;
        this.db = null;
        this.isInitialized = false;
    }

    /**
     * IndexedDB 초기화
     */
    async init() {
        if (this.isInitialized) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                console.error('IndexedDB 초기화 실패:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                this.isInitialized = true;
                console.log('IndexedDB 초기화 성공');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 프로그레스 노트 저장소 생성
                if (!db.objectStoreNames.contains('progressNotes')) {
                    const store = db.createObjectStore('progressNotes', { 
                        autoIncrement: true // 자동 생성 키 사용
                    });
                    
                    // 인덱스 생성
                    store.createIndex('site', 'site', { unique: false });
                    store.createIndex('Id', 'Id', { unique: false });
                    store.createIndex('eventDate', 'eventDate', { unique: false });
                    store.createIndex('clientId', 'clientId', { unique: false });
                    store.createIndex('createdDate', 'createdDate', { unique: false });
                    
                    console.log('progressNotes 저장소 생성됨');
                }

                // 사이트별 마지막 업데이트 시간 저장소 생성
                if (!db.objectStoreNames.contains('siteLastUpdate')) {
                    const updateStore = db.createObjectStore('siteLastUpdate', { 
                        keyPath: 'site' 
                    });
                    console.log('siteLastUpdate 저장소 생성됨');
                }
            };
        });
    }

    /**
     * 프로그레스 노트 저장
     */
    async saveProgressNotes(site, progressNotes) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes'], 'readwrite');
            const store = transaction.objectStore('progressNotes');

            let savedCount = 0;
            let errorCount = 0;

            progressNotes.forEach(note => {
                // 사이트 정보 추가
                const noteWithSite = {
                    ...note,
                    site: site,
                    savedAt: new Date().toISOString()
                };

                const request = store.put(noteWithSite);

                request.onsuccess = () => {
                    savedCount++;
                };

                request.onerror = () => {
                    console.error('프로그레스 노트 저장 실패:', request.error);
                    errorCount++;
                };
            });

            transaction.oncomplete = () => {
                console.log(`${site}: ${savedCount}개 저장, ${errorCount}개 실패`);
                resolve({ savedCount, errorCount });
            };

            transaction.onerror = () => {
                reject(transaction.error);
            };
        });
    }

    /**
     * 사이트별 프로그레스 노트 조회
     */
    async getProgressNotes(site, options = {}) {
        await this.init();

        const { 
            limit = 100, 
            offset = 0, 
            sortBy = 'eventDate', 
            sortOrder = 'desc',
            clientId = null,
            startDate = null,
            endDate = null
        } = options;

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes'], 'readonly');
            const store = transaction.objectStore('progressNotes');
            const siteIndex = store.index('site');

            const request = siteIndex.getAll(site);

            request.onsuccess = () => {
                let notes = request.result;

                // 필터링
                if (clientId) {
                    notes = notes.filter(note => note.clientId === clientId);
                }

                if (startDate) {
                    notes = notes.filter(note => new Date(note.eventDate) >= new Date(startDate));
                }

                if (endDate) {
                    notes = notes.filter(note => new Date(note.eventDate) <= new Date(endDate));
                }

                // 정렬
                notes.sort((a, b) => {
                    let aValue = a[sortBy];
                    let bValue = b[sortBy];

                    if (sortBy === 'eventDate' || sortBy === 'createdDate') {
                        aValue = new Date(aValue);
                        bValue = new Date(bValue);
                    }

                    if (sortOrder === 'desc') {
                        return bValue - aValue;
                    } else {
                        return aValue - bValue;
                    }
                });

                // 페이징
                const totalCount = notes.length;
                notes = notes.slice(offset, offset + limit);

                resolve({
                    notes,
                    totalCount,
                    hasMore: offset + limit < totalCount
                });
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 특정 프로그레스 노트 조회
     */
    async getProgressNote(site, id) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes'], 'readonly');
            const store = transaction.objectStore('progressNotes');

            const request = store.get([site, id]);

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 사이트별 마지막 업데이트 시간 저장
     */
    async saveLastUpdateTime(site, lastUpdateTime) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['siteLastUpdate'], 'readwrite');
            const store = transaction.objectStore('siteLastUpdate');

            const data = {
                site: site,
                lastUpdateTime: lastUpdateTime,
                updatedAt: new Date().toISOString()
            };

            const request = store.put(data);

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 사이트별 마지막 업데이트 시간 조회
     */
    async getLastUpdateTime(site) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['siteLastUpdate'], 'readonly');
            const store = transaction.objectStore('siteLastUpdate');

            const request = store.get(site);

            request.onsuccess = () => {
                const result = request.result;
                resolve(result ? result.lastUpdateTime : null);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 사이트별 데이터 개수 조회
     */
    async getProgressNoteCount(site) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes'], 'readonly');
            const store = transaction.objectStore('progressNotes');
            const siteIndex = store.index('site');

            const request = siteIndex.count(site);

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 사이트별 데이터 삭제
     */
    async deleteProgressNotes(site) {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes'], 'readwrite');
            const store = transaction.objectStore('progressNotes');
            const siteIndex = store.index('site');

            const request = siteIndex.openCursor(site);

            let deletedCount = 0;

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    cursor.delete();
                    deletedCount++;
                    cursor.continue();
                } else {
                    console.log(`${site}: ${deletedCount}개 삭제됨`);
                    resolve(deletedCount);
                }
            };

            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    /**
     * 전체 데이터베이스 초기화
     */
    async clearAll() {
        await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['progressNotes', 'siteLastUpdate'], 'readwrite');
            
            const progressNotesStore = transaction.objectStore('progressNotes');
            const siteLastUpdateStore = transaction.objectStore('siteLastUpdate');

            const progressNotesRequest = progressNotesStore.clear();
            const siteLastUpdateRequest = siteLastUpdateStore.clear();

            transaction.oncomplete = () => {
                console.log('전체 데이터베이스 초기화 완료');
                resolve();
            };

            transaction.onerror = () => {
                reject(transaction.error);
            };
        });
    }

    /**
     * 데이터베이스 정보 조회
     */
    async getDatabaseInfo() {
        await this.init();

        const sites = ['Parafield Gardens', 'Nerrilda']; // config에서 가져올 수 있음
        const info = {};

        for (const site of sites) {
            const count = await this.getProgressNoteCount(site);
            const lastUpdate = await this.getLastUpdateTime(site);
            
            info[site] = {
                count,
                lastUpdate
            };
        }

        return info;
    }
}

// 전역 인스턴스 생성
const progressNoteDB = new ProgressNoteDB();

// 전역으로 내보내기
window.ProgressNoteDB = ProgressNoteDB;
window.progressNoteDB = progressNoteDB; 