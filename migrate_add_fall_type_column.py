"""
DB 마이그레이션: cims_incidents 테이블에 fall_type 컬럼 추가

Step 1: 컬럼 추가
Step 2: 기존 데이터 업데이트
"""

import sqlite3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_fall_type_column():
    """fall_type 컬럼 추가 및 기존 데이터 업데이트"""
    
    try:
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # Step 1: 테이블 스키마 확인
        cursor.execute("PRAGMA table_info(cims_incidents)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'fall_type' in column_names:
            logger.info("✅ fall_type 컬럼이 이미 존재합니다.")
        else:
            logger.info("📝 fall_type 컬럼 추가 중...")
            cursor.execute("""
                ALTER TABLE cims_incidents
                ADD COLUMN fall_type VARCHAR(20) DEFAULT NULL
            """)
            conn.commit()
            logger.info("✅ fall_type 컬럼 추가 완료!")
        
        # Step 2: 기존 Fall incidents 데이터 업데이트
        logger.info("\n📊 기존 Fall incidents 업데이트 시작...")
        
        # Fall incidents 조회
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute("""
            SELECT id, incident_id, description
            FROM cims_incidents
            WHERE incident_type LIKE '%Fall%'
            AND incident_date >= ?
            AND (fall_type IS NULL OR fall_type = '')
            ORDER BY incident_date DESC
        """, (thirty_days_ago,))
        
        fall_incidents = cursor.fetchall()
        logger.info(f"🔍 업데이트할 Fall incidents: {len(fall_incidents)}개")
        
        if len(fall_incidents) == 0:
            logger.info("✅ 업데이트할 데이터가 없습니다.")
            conn.close()
            return
        
        # Fall detector 임포트
        from services.fall_policy_detector import fall_detector
        
        # 통계
        stats = {'witnessed': 0, 'unwitnessed': 0, 'unknown': 0}
        
        # 배치 업데이트 (10개씩)
        batch_size = 10
        total = len(fall_incidents)
        
        for i in range(0, total, batch_size):
            batch = fall_incidents[i:i+batch_size]
            
            for incident in batch:
                incident_id = incident[0]
                incident_manad_id = incident[1]
                
                try:
                    # Fall 유형 감지
                    fall_type = fall_detector.detect_fall_type_from_incident(incident_id, cursor)
                    stats[fall_type] += 1
                    
                    # DB 업데이트
                    cursor.execute("""
                        UPDATE cims_incidents
                        SET fall_type = ?
                        WHERE id = ?
                    """, (fall_type, incident_id))
                    
                    logger.debug(f"  ✓ {incident_manad_id}: {fall_type}")
                
                except Exception as e:
                    logger.error(f"  ✗ {incident_manad_id}: {e}")
            
            # 배치 커밋
            conn.commit()
            progress = min(i + batch_size, total)
            logger.info(f"  진행: {progress}/{total} ({progress/total*100:.1f}%)")
        
        conn.close()
        
        # 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("📊 마이그레이션 완료!")
        logger.info("=" * 80)
        logger.info(f"✅ Witnessed:   {stats['witnessed']:3d}개 ({stats['witnessed']/total*100:5.1f}%)")
        logger.info(f"✅ Unwitnessed: {stats['unwitnessed']:3d}개 ({stats['unwitnessed']/total*100:5.1f}%)")
        logger.info(f"⚠️  Unknown:     {stats['unknown']:3d}개 ({stats['unknown']/total*100:5.1f}%)")
        logger.info(f"\n🎯 분류 정확도: {(stats['witnessed']+stats['unwitnessed'])/total*100:.1f}%")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🚀 DB 마이그레이션 시작...\n")
    migrate_add_fall_type_column()
    print("\n✅ 마이그레이션 완료!")

