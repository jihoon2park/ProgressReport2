#!/usr/bin/env python3
"""
Task Manager 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from task_manager import get_task_manager
from datetime import datetime
import json

def test_task_manager():
    """Task Manager 기능 테스트"""
    print("🧪 Task Manager 테스트 시작")
    print("=" * 50)
    
    try:
        # Task Manager 인스턴스 생성
        task_manager = get_task_manager()
        print("✅ Task Manager 인스턴스 생성 성공")
        
        # 테스트용 데이터
        test_data = {
            'incident_id': 'TEST-INC-001',
            'policy_id': 1,  # 기본 정책 ID
            'client_name': 'Test Client',
            'client_id': 1,
            'site': 'Parafield Gardens',
            'event_type': 'emergency',
            'risk_rating': 'high',
            'created_by': 'test_user'
        }
        
        print(f"📋 테스트 데이터: {test_data}")
        
        # 1. 워크플로우 생성 테스트
        print("\n1️⃣ 워크플로우 생성 테스트...")
        
        # 먼저 기본 정책이 있는지 확인
        import sqlite3
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 테스트용 기본 정책 생성
        cursor.execute('''
            INSERT OR IGNORE INTO escalation_policies 
            (id, policy_name, description, event_type, priority, created_by)
            VALUES (1, 'Test Emergency Policy', 'Test policy for emergency situations', 'emergency', 'high', 1)
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO escalation_steps 
            (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
            VALUES (1, 1, 0, 1, '["RN", "doctor"]', 'Emergency situation - immediate attention required')
        ''')
        
        cursor.execute('''
            INSERT OR IGNORE INTO escalation_steps 
            (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
            VALUES (1, 2, 15, 2, '["admin", "site_admin"]', 'Emergency escalation - 15 minute follow-up')
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ 테스트용 정책 생성 완료")
        
        # 워크플로우 생성 실행
        result = task_manager.create_incident_workflow(**test_data)
        
        if result['success']:
            print(f"✅ 워크플로우 생성 성공: {result['total_tasks_created']}개 작업 생성")
            print(f"   생성된 작업들: {len(result['tasks'])}개")
            
            # 생성된 첫 번째 작업 ID 저장
            first_task_id = result['tasks'][0]['task_id'] if result['tasks'] else None
            
        else:
            print(f"❌ 워크플로우 생성 실패: {result['message']}")
            return False
        
        # 2. 사용자 작업 목록 조회 테스트
        print("\n2️⃣ 사용자 작업 목록 조회 테스트...")
        
        user_tasks = task_manager.get_user_tasks('RN', 'Parafield Gardens', 'pending')
        print(f"✅ RN 역할 사용자 작업 조회: {len(user_tasks)}개 작업")
        
        for task in user_tasks[:3]:  # 처음 3개만 표시
            print(f"   - {task['task_id']}: {task['task_type']} ({task['status']})")
        
        # 3. 작업 완료 테스트 (첫 번째 작업이 있는 경우)
        if first_task_id:
            print(f"\n3️⃣ 작업 완료 테스트 (작업 ID: {first_task_id})...")
            
            complete_result = task_manager.complete_task(
                task_id=first_task_id,
                completed_by='test_user',
                notes='Test completion notes'
            )
            
            if complete_result['success']:
                print(f"✅ 작업 완료 성공")
                print(f"   진행률: {complete_result['progress']['completion_rate']}%")
                print(f"   인시던트 종료: {complete_result['incident_closed']}")
            else:
                print(f"❌ 작업 완료 실패: {complete_result['message']}")
        
        # 4. 알림 전송 테스트 (실제 FCM 전송은 하지 않음)
        print("\n4️⃣ 알림 전송 시스템 테스트...")
        
        # FCM 서비스 초기화 확인
        if task_manager.fcm_service:
            print("✅ FCM 서비스 초기화 완료")
        else:
            print("⚠️ FCM 서비스 초기화되지 않음 (Firebase 설정 필요)")
        
        if task_manager.token_manager:
            print("✅ FCM 토큰 매니저 초기화 완료")
        else:
            print("⚠️ FCM 토큰 매니저 초기화되지 않음")
        
        print("\n🎉 모든 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"\n💥 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_database_status():
    """데이터베이스 상태 확인"""
    print("\n📊 데이터베이스 상태 확인")
    print("-" * 30)
    
    try:
        import sqlite3
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 새로 생성된 테이블 확인
        tables_to_check = ['scheduled_tasks', 'task_execution_logs', 'policy_execution_results']
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count}개 레코드")
        
        # incidents_cache의 새 컬럼 확인
        cursor.execute("PRAGMA table_info(incidents_cache)")
        columns = cursor.fetchall()
        new_columns = [col[1] for col in columns if col[1] in ['workflow_status', 'total_tasks', 'completed_tasks']]
        print(f"  incidents_cache 새 컬럼: {new_columns}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 데이터베이스 상태 확인 실패: {e}")

if __name__ == "__main__":
    success = test_task_manager()
    show_database_status()
    
    if success:
        print("\n✅ Task Manager 테스트 성공!")
        print("다음 단계: Policy Scheduler 통합")
    else:
        print("\n❌ Task Manager 테스트 실패!")
        sys.exit(1)
