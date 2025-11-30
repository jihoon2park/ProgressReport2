#!/usr/bin/env python3
"""
Witnessed Fall의 잘못된 tasks 수정
- 잘못된 tasks (FALL-001-UNWITNESSED) 삭제
- 올바른 policy (FALL-002-WITNESSED)로 tasks 재생성
"""

import sqlite3
import sys
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_witnessed_fall_tasks():
    """Witnessed Fall의 tasks를 올바른 policy로 수정"""
    
    conn = sqlite3.connect('progress_report.db')
    cursor = conn.cursor()
    
    try:
        # 1. Witnessed Fall incidents 중 잘못된 tasks가 있는 것 찾기
        cursor.execute('''
            SELECT DISTINCT i.id, i.incident_id, i.fall_type, COUNT(t.id) as task_count
            FROM cims_incidents i
            INNER JOIN cims_tasks t ON i.id = t.incident_id
            INNER JOIN cims_policies p ON t.policy_id = p.id
            WHERE i.incident_type LIKE "%Fall%"
            AND i.status IN ("Open", "Overdue")
            AND i.fall_type = "witnessed"
            AND p.policy_id = "FALL-001-UNWITNESSED"
            GROUP BY i.id, i.incident_id, i.fall_type
        ''')
        
        wrong_incidents = cursor.fetchall()
        
        if not wrong_incidents:
            logger.info("✅ 수정할 witnessed fall incidents가 없습니다.")
            return
        
        logger.info(f"🔍 {len(wrong_incidents)}개의 witnessed fall incidents가 잘못된 tasks를 가지고 있습니다.")
        
        for incident_id, incident_code, fall_type, task_count in wrong_incidents:
            logger.info(f"\n📋 {incident_code} (ID: {incident_id}, fall_type: {fall_type})")
            logger.info(f"   현재 tasks: {task_count}개 (FALL-001-UNWITNESSED)")
            
            # 2. 기존 tasks 삭제
            cursor.execute('''
                DELETE FROM cims_tasks 
                WHERE incident_id = ?
            ''', (incident_id,))
            
            deleted_count = cursor.rowcount
            logger.info(f"   🗑️  {deleted_count}개의 잘못된 tasks 삭제됨")
            
            # 3. 올바른 policy (FALL-002-WITNESSED)로 tasks 재생성
            # Get incident details
            cursor.execute('''
                SELECT incident_date 
                FROM cims_incidents 
                WHERE id = ?
            ''', (incident_id,))
            
            incident_date_iso = cursor.fetchone()[0]
            
            # Auto-generate tasks with correct policy
            from services.cims_service import CIMSService
            
            num_tasks = CIMSService.auto_generate_fall_tasks(
                incident_id, 
                incident_date_iso, 
                cursor
            )
            
            logger.info(f"   ✅ {num_tasks}개의 새 tasks 생성됨 (FALL-002-WITNESSED)")
        
        # Commit changes
        conn.commit()
        logger.info(f"\n✅ 총 {len(wrong_incidents)}개의 witnessed fall incidents 수정 완료!")
        
        # Verify
        logger.info("\n" + "=" * 60)
        logger.info("=== 수정 후 검증 ===")
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
    logger.info("Witnessed Fall Tasks 수정 시작")
    logger.info("=" * 60)
    
    fix_witnessed_fall_tasks()

