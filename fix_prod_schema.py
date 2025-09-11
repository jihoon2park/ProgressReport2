#!/usr/bin/env python3
"""
운영 서버 DB 스키마 수정 스크립트
site_name 컬럼 추가 및 기타 누락된 컬럼들 수정
"""

import sqlite3
import os
from datetime import datetime

def fix_production_schema(db_path):
    """운영 서버 DB 스키마 수정"""
    print(f"🔧 운영 서버 DB 스키마 수정: {db_path}")
    
    # 백업 생성
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 백업 완료: {backup_path}")
    except Exception as e:
        print(f"❌ 백업 실패: {e}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. progress_notes_cache 테이블에 site_name 컬럼 추가
        print("📝 progress_notes_cache 테이블 수정 중...")
        try:
            cursor.execute("ALTER TABLE progress_notes_cache ADD COLUMN site_name TEXT")
            print("✅ site_name 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  site_name 컬럼이 이미 존재합니다")
            else:
                print(f"❌ site_name 컬럼 추가 실패: {e}")
        
        # 2. progress_notes_sync 테이블에 site_name 컬럼 추가
        print("📝 progress_notes_sync 테이블 수정 중...")
        try:
            cursor.execute("ALTER TABLE progress_notes_sync ADD COLUMN site_name TEXT")
            print("✅ site_name 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  site_name 컬럼이 이미 존재합니다")
            else:
                print(f"❌ site_name 컬럼 추가 실패: {e}")
        
        # 3. 기존 데이터에 site_name 값 설정 (기본값으로 'Unknown' 설정)
        print("📝 기존 데이터 site_name 값 설정 중...")
        try:
            cursor.execute("UPDATE progress_notes_cache SET site_name = 'Unknown' WHERE site_name IS NULL")
            cursor.execute("UPDATE progress_notes_sync SET site_name = 'Unknown' WHERE site_name IS NULL")
            print("✅ 기존 데이터 site_name 값 설정 완료")
        except Exception as e:
            print(f"❌ 기존 데이터 site_name 값 설정 실패: {e}")
        
        # 4. api_keys 테이블이 없으면 생성
        print("📝 api_keys 테이블 확인 중...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_name TEXT NOT NULL UNIQUE,
                    api_key TEXT NOT NULL,
                    server_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ api_keys 테이블 확인/생성 완료")
        except Exception as e:
            print(f"❌ api_keys 테이블 생성 실패: {e}")
        
        # 5. progress_notes_cache 테이블에 누락된 컬럼들 추가
        print("📝 progress_notes_cache 테이블 누락 컬럼 추가 중...")
        
        # api_created_at 컬럼 추가
        try:
            cursor.execute("ALTER TABLE progress_notes_cache ADD COLUMN api_created_at TIMESTAMP")
            print("✅ api_created_at 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  api_created_at 컬럼이 이미 존재합니다")
            else:
                print(f"❌ api_created_at 컬럼 추가 실패: {e}")
        
        # api_updated_at 컬럼 추가
        try:
            cursor.execute("ALTER TABLE progress_notes_cache ADD COLUMN api_updated_at TIMESTAMP")
            print("✅ api_updated_at 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  api_updated_at 컬럼이 이미 존재합니다")
            else:
                print(f"❌ api_updated_at 컬럼 추가 실패: {e}")
        
        # 6. progress_notes_sync 테이블에 누락된 컬럼들 추가
        print("📝 progress_notes_sync 테이블 누락 컬럼 추가 중...")
        
        # api_created_at 컬럼 추가
        try:
            cursor.execute("ALTER TABLE progress_notes_sync ADD COLUMN api_created_at TIMESTAMP")
            print("✅ api_created_at 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  api_created_at 컬럼이 이미 존재합니다")
            else:
                print(f"❌ api_created_at 컬럼 추가 실패: {e}")
        
        # api_updated_at 컬럼 추가
        try:
            cursor.execute("ALTER TABLE progress_notes_sync ADD COLUMN api_updated_at TIMESTAMP")
            print("✅ api_updated_at 컬럼 추가 완료")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  api_updated_at 컬럼이 이미 존재합니다")
            else:
                print(f"❌ api_updated_at 컬럼 추가 실패: {e}")
        
        conn.commit()
        print("🎉 스키마 수정 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 스키마 수정 실패: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("🔧 운영 서버 DB 스키마 수정 도구")
    print("=" * 50)
    
    # DB 경로 설정
    db_path = input("운영 서버 DB 경로를 입력하세요 (기본값: progress_report.db): ").strip()
    if not db_path:
        db_path = "progress_report.db"
    
    if not os.path.exists(db_path):
        print(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return
    
    print(f"📁 대상 DB: {db_path}")
    
    # 스키마 수정 실행
    if fix_production_schema(db_path):
        print("\n✅ 스키마 수정이 성공적으로 완료되었습니다!")
        print("📋 수정된 내용:")
        print("  - progress_notes_cache 테이블에 site_name 컬럼 추가")
        print("  - progress_notes_sync 테이블에 site_name 컬럼 추가")
        print("  - api_keys 테이블 생성/확인")
        print("  - 누락된 컬럼들 추가")
        print("\n🚀 이제 서비스를 재시작하면 정상적으로 작동할 것입니다!")
    else:
        print("\n❌ 스키마 수정에 실패했습니다. 로그를 확인하세요.")

if __name__ == "__main__":
    main()
