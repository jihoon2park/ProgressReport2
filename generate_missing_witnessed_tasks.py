#!/usr/bin/env python3
"""
Witnessed Fall의 누락된 tasks 생성
"""

import sqlite3
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_missing_tasks():
    """Tasks가 없는 witnessed falls에 대해 tasks 생성"""
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 1. Witnessed Fall incidents 중 tasks가 없는 것 찾기
        cursor.execute('''
            SELECT i.id, i.incident_id, i.fall_type, i.incident_date
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            WHERE i.incident_type LIKE "%Fall%"
            AND i.status IN ("Open", "Overdue")
            AND i.fall_type = "witnessed"
            GROUP BY i.id, i.incident_id, i.fall_type, i.incident_date
            HAVING COUNT(t.id) = 0
        ''')
        
        missing_incidents = cursor.fetchall()
        
        if not missing_incidents:
            logger.info("✅ tasks가 누락된 witnessed fall incidents가 없습니다.")
            return
        
        logger.info(f"🔍 {len(missing_incidents)}개의 witnessed fall incidents가 tasks가 없습니다.")
        
        from services.cims_service import CIMSService
        
        for incident_id, incident_code, fall_type, incident_date_iso in missing_incidents:
            logger.info(f"\n📋 {incident_code} (ID: {incident_id}, fall_type: {fall_type})")
            
            # Auto-generate tasks
            num_tasks = CIMSService.auto_generate_fall_tasks(
                incident_id, 
                incident_date_iso, 
                cursor
            )
            
            logger.info(f"   ✅ {num_tasks}개의 tasks 생성됨 (FALL-002-WITNESSED)")
        
        # Commit changes
        conn.commit()
        logger.info(f"\n✅ 총 {len(missing_incidents)}개의 witnessed fall incidents에 tasks 생성 완료!")
        
        # Verify
        logger.info("\n" + "=" * 60)
        logger.info("=== 생성 후 검증 ===")
        logger.info("=" * 60)
        
        cursor.execute('''
            SELECT i.incident_id, i.fall_type, COUNT(t.id) as task_count, 
                   p.policy_id as policy_code
            FROM cims_incidents i
            LEFT JOIN cims_tasks t ON i.id = t.incident_id
            LEFT JOIN cims_policies p ON t.policy_id = p.id
            WHERE i.incident_type LIKE "%Fall%"
            AND i.status IN ("Open", "Overdue")
            AND i.fall_type = "witnessed"
            GROUP BY i.incident_id, i.fall_type, p.policy_id
        ''')
        
        verified = cursor.fetchall()
        
        for incident_code, fall_type, task_count, policy_code in verified:
            status = "✅" if task_count == 1 and policy_code == "FALL-002-WITNESSED" else "❌"
            logger.info(f"{status} {incident_code}: {task_count} tasks (Policy: {policy_code or 'N/A'})")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Witnessed Fall 누락 Tasks 생성 시작")
    logger.info("=" * 60)
    
    generate_missing_tasks()

