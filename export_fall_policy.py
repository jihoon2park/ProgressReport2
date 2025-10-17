#!/usr/bin/env python3
"""
Fall Policy Export/Import 스크립트
개발 서버에서 Fall Policy를 export하여 상용 서버로 import할 수 있습니다.
"""
import sqlite3
import json
import sys
from datetime import datetime

def get_db_connection():
    """DB 연결"""
    conn = sqlite3.connect('progress_report.db')
    conn.row_factory = sqlite3.Row
    return conn

def export_fall_policy(output_file='fall_policy.json'):
    """Fall Policy를 JSON 파일로 export"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📤 Fall Policy Export")
    print("=" * 80)
    print()
    
    # Find active Fall policy
    cursor.execute("""
        SELECT id, policy_id, name, description, version, 
               effective_date, expiry_date, rules_json, is_active,
               created_by, created_at, updated_at
        FROM cims_policies
        WHERE is_active = 1
    """)
    
    policies = cursor.fetchall()
    fall_policy = None
    
    for policy in policies:
        try:
            rules = json.loads(policy['rules_json'])
            association = rules.get('incident_association', {})
            if association.get('incident_type') == 'Fall':
                fall_policy = policy
                break
        except:
            continue
    
    if not fall_policy:
        print("❌ Active Fall Policy를 찾을 수 없습니다.")
        conn.close()
        return False
    
    # Convert to dict
    policy_data = {
        'exported_at': datetime.now().isoformat(),
        'exported_from': 'development',
        'policy': {
            'policy_id': fall_policy['policy_id'],
            'name': fall_policy['name'],
            'description': fall_policy['description'],
            'version': fall_policy['version'],
            'effective_date': fall_policy['effective_date'],
            'expiry_date': fall_policy['expiry_date'],
            'rules_json': fall_policy['rules_json'],
            'is_active': fall_policy['is_active']
        }
    }
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(policy_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Fall Policy exported successfully!")
    print(f"   File: {output_file}")
    print(f"   Policy: {fall_policy['name']}")
    print(f"   Version: {fall_policy['version']}")
    
    # Show policy details
    try:
        rules = json.loads(fall_policy['rules_json'])
        schedule = rules.get('nurse_visit_schedule', [])
        print(f"   Visit Schedule: {len(schedule)} phases")
        for idx, phase in enumerate(schedule, 1):
            print(f"     Phase {idx}: {phase.get('phase_name', 'N/A')}")
    except:
        pass
    
    print()
    print("📋 다음 단계:")
    print(f"   1. {output_file} 파일을 상용 서버로 복사")
    print(f"   2. 상용 서버에서 실행: python3 export_fall_policy.py import {output_file}")
    print()
    
    conn.close()
    return True

def import_fall_policy(input_file='fall_policy.json'):
    """JSON 파일에서 Fall Policy를 import"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📥 Fall Policy Import")
    print("=" * 80)
    print()
    
    # Read file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            policy_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        conn.close()
        return False
    except json.JSONDecodeError:
        print(f"❌ JSON 파싱 오류: {input_file}")
        conn.close()
        return False
    
    policy = policy_data['policy']
    
    print(f"📄 Import할 Policy:")
    print(f"   Name: {policy['name']}")
    print(f"   Version: {policy['version']}")
    print(f"   Exported: {policy_data.get('exported_at', 'N/A')}")
    print()
    
    # Check if cims_policies table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cims_policies'
    """)
    
    if not cursor.fetchone():
        print("❌ cims_policies 테이블이 없습니다!")
        print("   먼저 Policy 테이블을 생성해야 합니다:")
        print("   python3 create_policy_tables.py")
        conn.close()
        return False
    
    # Check if policy already exists
    cursor.execute("""
        SELECT id, name, version FROM cims_policies 
        WHERE policy_id = ?
    """, (policy['policy_id'],))
    
    existing = cursor.fetchone()
    
    if existing:
        print(f"⚠️  동일한 policy_id가 이미 존재합니다:")
        print(f"   ID: {existing['id']}")
        print(f"   Name: {existing['name']}")
        print(f"   Version: {existing['version']}")
        print()
        
        response = input("덮어쓰시겠습니까? (y/N): ").strip().lower()
        if response != 'y':
            print("❌ Import 취소됨")
            conn.close()
            return False
        
        # Update existing policy
        cursor.execute("""
            UPDATE cims_policies
            SET name = ?,
                description = ?,
                version = ?,
                effective_date = ?,
                expiry_date = ?,
                rules_json = ?,
                is_active = ?,
                updated_at = ?
            WHERE policy_id = ?
        """, (
            policy['name'],
            policy['description'],
            policy['version'],
            policy['effective_date'],
            policy['expiry_date'],
            policy['rules_json'],
            policy['is_active'],
            datetime.now().isoformat(),
            policy['policy_id']
        ))
        
        print(f"✅ Policy 업데이트 완료 (ID: {existing['id']})")
    else:
        # Insert new policy
        cursor.execute("""
            INSERT INTO cims_policies 
            (policy_id, name, description, version, effective_date, expiry_date, 
             rules_json, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy['policy_id'],
            policy['name'],
            policy['description'],
            policy['version'],
            policy['effective_date'],
            policy['expiry_date'],
            policy['rules_json'],
            policy['is_active'],
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        new_id = cursor.lastrowid
        print(f"✅ 새 Policy 생성 완료 (ID: {new_id})")
    
    conn.commit()
    
    # Verify
    print()
    print("🔍 Import 검증:")
    
    cursor.execute("""
        SELECT id, name, version, is_active, rules_json
        FROM cims_policies
        WHERE policy_id = ?
    """, (policy['policy_id'],))
    
    imported = cursor.fetchone()
    if imported:
        print(f"   ✅ Policy 존재 확인")
        print(f"   ID: {imported['id']}")
        print(f"   Name: {imported['name']}")
        print(f"   Active: {'Yes' if imported['is_active'] else 'No'}")
        
        try:
            rules = json.loads(imported['rules_json'])
            schedule = rules.get('nurse_visit_schedule', [])
            print(f"   Visit Schedule: {len(schedule)} phases")
            
            if len(schedule) == 0:
                print("   ⚠️  Visit schedule이 비어있습니다!")
            else:
                for idx, phase in enumerate(schedule, 1):
                    print(f"     Phase {idx}: {phase.get('phase_name', 'N/A')} - {len(phase.get('tasks', []))} tasks")
        except Exception as e:
            print(f"   ⚠️  Rules JSON 검증 실패: {str(e)}")
    else:
        print("   ❌ Import 검증 실패!")
        conn.close()
        return False
    
    print()
    print("=" * 80)
    print("✅ Import 완료!")
    print("=" * 80)
    print()
    print("📋 다음 단계:")
    print("   1. Force Sync를 다시 실행하세요")
    print("   2. Task가 정상적으로 생성되는지 확인하세요")
    print()
    
    conn.close()
    return True

def show_current_policies():
    """현재 DB의 policy 목록 표시"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📋 현재 Policy 목록")
    print("=" * 80)
    print()
    
    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cims_policies'
    """)
    
    if not cursor.fetchone():
        print("❌ cims_policies 테이블이 없습니다!")
        conn.close()
        return
    
    cursor.execute("""
        SELECT id, policy_id, name, version, is_active
        FROM cims_policies
        ORDER BY is_active DESC, id
    """)
    
    policies = cursor.fetchall()
    
    if not policies:
        print("📭 Policy가 없습니다.")
    else:
        print(f"Total: {len(policies)}개\n")
        for policy in policies:
            status = "🟢 Active" if policy['is_active'] else "⚪ Inactive"
            print(f"{status} | ID: {policy['id']:2d} | {policy['name']}")
            print(f"         Policy ID: {policy['policy_id']}")
            print(f"         Version: {policy['version']}")
            
            # Check if it's Fall policy
            cursor.execute("SELECT rules_json FROM cims_policies WHERE id = ?", (policy['id'],))
            rules_row = cursor.fetchone()
            if rules_row:
                try:
                    rules = json.loads(rules_row['rules_json'])
                    association = rules.get('incident_association', {})
                    if association.get('incident_type') == 'Fall':
                        schedule = rules.get('nurse_visit_schedule', [])
                        print(f"         → Fall Policy | {len(schedule)} phases")
                except:
                    pass
            print()
    
    conn.close()

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print(f"  {sys.argv[0]} export [output_file]     # Policy 내보내기")
        print(f"  {sys.argv[0]} import [input_file]      # Policy 가져오기")
        print(f"  {sys.argv[0]} list                     # 현재 Policy 목록")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'export':
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'fall_policy.json'
        export_fall_policy(output_file)
    elif command == 'import':
        input_file = sys.argv[2] if len(sys.argv) > 2 else 'fall_policy.json'
        import_fall_policy(input_file)
    elif command == 'list':
        show_current_policies()
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        print("사용 가능한 명령어: export, import, list")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

