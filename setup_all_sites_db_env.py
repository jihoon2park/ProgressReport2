#!/usr/bin/env python3
"""
모든 사이트 DB 환경 변수 설정 스크립트
.env 파일에 필요한 환경 변수를 자동으로 추가합니다.
"""

import os
from pathlib import Path
import re

def setup_all_sites_db_env():
    """모든 사이트 DB 환경 변수 설정"""
    env_file = Path('.env')
    
    # 모든 사이트 DB 설정값
    all_sites_settings = {
        'Parafield Gardens': {
            'MANAD_DB_SERVER_PARAFIELD_GARDENS': 'efsvr02\\sqlexpress',
            'MANAD_DB_NAME_PARAFIELD_GARDENS': 'ManadPlus_Edenfield',
            'MANAD_DB_USE_WINDOWS_AUTH_PARAFIELD_GARDENS': 'true'
        },
        'Nerrilda': {
            'MANAD_DB_SERVER_NERRILDA': 'SQLSVR02\\SQLEXPRESS',
            'MANAD_DB_NAME_NERRILDA': 'ManadPlus_Edenfield_Nerilda',
            'MANAD_DB_USE_WINDOWS_AUTH_NERRILDA': 'true'
        },
        'Ramsay': {
            'MANAD_DB_SERVER_RAMSAY': '192.168.31.12\\SQLExpress',
            'MANAD_DB_NAME_RAMSAY': 'ManadPlus_Edenfield_Ramsay',
            'MANAD_DB_USE_WINDOWS_AUTH_RAMSAY': 'true'
        },
        'West Park': {
            'MANAD_DB_SERVER_WEST_PARK': 'SQLSVR04\\SQLEXPRESS',
            'MANAD_DB_NAME_WEST_PARK': 'ManadPlus_EdenfieldWestPark',
            'MANAD_DB_USE_WINDOWS_AUTH_WEST_PARK': 'true'
        },
        'Yankalilla': {
            'MANAD_DB_SERVER_YANKALILLA': 'SQLSVR05\\SQLEXPRESS',
            'MANAD_DB_NAME_YANKALILLA': 'ManadPlus_EdenfieldYankalilla',
            'MANAD_DB_USE_WINDOWS_AUTH_YANKALILLA': 'true'
        }
    }
    
    # .env 파일이 없으면 생성
    if not env_file.exists():
        print("📝 .env 파일이 없습니다. 새로 생성합니다...")
        env_file.write_text('', encoding='utf-8')
    
    # 기존 .env 파일 읽기
    try:
        content = env_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"❌ .env 파일 읽기 실패: {e}")
        return False
    
    # 각 사이트별 설정 섹션 추가
    updated = False
    lines = content.split('\n')
    
    # DB 설정 섹션 확인
    db_section_exists = any('# DB' in line or 'MANAD_DB_SERVER' in line for line in lines)
    
    if not db_section_exists:
        # DB 설정 섹션 추가
        content += '\n\n# ============================================\n'
        content += '# MANAD Plus DB 직접 접속 설정\n'
        content += '# ============================================\n'
        updated = True
    
    # 각 사이트별 설정 추가/업데이트
    for site_name, settings in all_sites_settings.items():
        # 사이트별 섹션 추가
        site_key = site_name.upper().replace(' ', '_')
        section_marker = f'# {site_name} DB'
        
        if section_marker not in content:
            content += f'\n# {site_name} DB 설정\n'
            updated = True
        
        # 각 환경 변수 확인 및 추가/업데이트
        for key, value in settings.items():
            pattern = rf'^{re.escape(key)}\s*='
            found = any(re.match(pattern, line) for line in lines)
            
            if not found:
                # 환경 변수가 없으면 추가
                content += f'{key}={value}\n'
                print(f"✅ 추가됨: {key}={value}")
                updated = True
            else:
                # 환경 변수가 있으면 업데이트
                new_lines = []
                for line in lines:
                    if re.match(pattern, line):
                        new_lines.append(f'{key}={value}\n')
                        if line.strip() != f'{key}={value}':
                            print(f"🔄 업데이트됨: {key}={value}")
                            updated = True
                    else:
                        new_lines.append(line + '\n' if not line.endswith('\n') else line)
                lines = [line.rstrip('\n') for line in new_lines]
                content = '\n'.join(lines)
                lines = content.split('\n')  # 업데이트된 lines 다시 설정
    
    # USE_DB_DIRECT_ACCESS 확인
    if 'USE_DB_DIRECT_ACCESS' not in content:
        content += '\n# DB 직접 접속 활성화\n'
        content += 'USE_DB_DIRECT_ACCESS=true\n'
        print("✅ 추가됨: USE_DB_DIRECT_ACCESS=true")
        updated = True
    
    # 파일 저장
    if updated:
        try:
            env_file.write_text(content, encoding='utf-8')
            print("\n✅ .env 파일 업데이트 완료!")
            print("\n📋 설정된 환경 변수:")
            print("\n# DB 직접 접속 활성화")
            print("USE_DB_DIRECT_ACCESS=true")
            print("\n# 각 사이트별 DB 설정:")
            for site_name, settings in all_sites_settings.items():
                print(f"\n# {site_name}:")
                for key, value in settings.items():
                    print(f"   {key}={value}")
            print("\n⚠️ 변경 사항 적용을 위해 서버를 재시작하세요.")
            return True
        except Exception as e:
            print(f"\n❌ .env 파일 저장 실패: {e}")
            return False
    else:
        print("✅ 모든 환경 변수가 이미 설정되어 있습니다.")
        return True

if __name__ == '__main__':
    print("=" * 60)
    print("모든 사이트 DB 환경 변수 설정")
    print("=" * 60)
    print()
    
    success = setup_all_sites_db_env()
    
    if success:
        print("\n✅ 설정 완료!")
    else:
        print("\n❌ 설정 실패")

