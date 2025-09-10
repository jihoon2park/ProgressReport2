#!/usr/bin/env python3
"""
FCM (Firebase Cloud Messaging) 기능 테스트 스크립트

이 스크립트는 FCM 서비스의 기본 기능을 테스트합니다.
실제 사용하기 전에 Firebase 서비스 계정 JSON 파일이 올바르게 설정되어 있는지 확인하세요.
"""

import os
import sys
import json
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_fcm_service():
    """FCM 서비스 기본 기능 테스트"""
    print("🔥 FCM 서비스 테스트 시작")
    print("=" * 50)
    
    try:
        # FCM 서비스 임포트 및 초기화
        from fcm_service import get_fcm_service
        from fcm_token_manager import get_fcm_token_manager
        
        print("✅ FCM 서비스 모듈 임포트 성공")
        
        # FCM 서비스 초기화
        fcm_service = get_fcm_service()
        print("✅ FCM 서비스 초기화 성공")
        
        # FCM 토큰 매니저 초기화
        token_manager = get_fcm_token_manager()
        print("✅ FCM 토큰 매니저 초기화 성공")
        
        # 테스트 토큰 (실제 FCM 토큰으로 교체해야 함)
        test_token = "test_fcm_token_12345"
        test_user_id = "test_user"
        
        print(f"\n📱 테스트 토큰 등록: {test_token}")
        
        # 테스트 토큰 등록
        success = token_manager.register_token(test_user_id, test_token, "Test Device")
        if success:
            print("✅ 테스트 토큰 등록 성공")
        else:
            print("❌ 테스트 토큰 등록 실패")
            return False
        
        # 등록된 토큰 조회
        user_tokens = token_manager.get_user_tokens(test_user_id)
        print(f"✅ 사용자 토큰 조회 성공: {len(user_tokens)}개 토큰")
        
        # 토큰 통계 조회
        stats = token_manager.get_token_stats()
        print(f"✅ 토큰 통계 조회 성공:")
        print(f"   - 총 사용자: {stats['total_users']}")
        print(f"   - 총 토큰: {stats['total_tokens']}")
        print(f"   - 활성 토큰: {stats['active_tokens']}")
        
        # 테스트 알림 전송 (실제 토큰이 아닌 경우 실패할 수 있음)
        print(f"\n📢 테스트 알림 전송 시도")
        try:
            result = fcm_service.send_notification_to_token(
                test_token,
                "테스트 알림",
                "FCM 서비스 테스트 알림입니다.",
                {"test": "true", "timestamp": datetime.now().isoformat()}
            )
            
            if result['success']:
                print("✅ 테스트 알림 전송 성공")
                print(f"   - 메시지 ID: {result.get('message_id', 'N/A')}")
            else:
                print("⚠️ 테스트 알림 전송 실패 (예상됨 - 테스트 토큰)")
                print(f"   - 오류: {result.get('error', 'N/A')}")
        except Exception as e:
            print(f"⚠️ 테스트 알림 전송 중 오류 (예상됨): {e}")
        
        # 테스트 토큰 제거
        print(f"\n🗑️ 테스트 토큰 제거")
        success = token_manager.unregister_token(test_user_id, test_token)
        if success:
            print("✅ 테스트 토큰 제거 성공")
        else:
            print("❌ 테스트 토큰 제거 실패")
        
        print("\n✅ FCM 서비스 테스트 완료!")
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        print("   필요한 패키지가 설치되어 있는지 확인하세요:")
        print("   pip install firebase-admin")
        return False
        
    except Exception as e:
        print(f"❌ FCM 서비스 테스트 실패: {e}")
        return False

def test_fcm_configuration():
    """FCM 설정 확인"""
    print("\n🔧 FCM 설정 확인")
    print("=" * 30)
    
    # Firebase 서비스 계정 JSON 파일 확인
    json_file_path = "static/json/incidentalarmapp-firebase-adminsdk-fbsvc-4d91dd4606.json"
    
    if os.path.exists(json_file_path):
        print(f"✅ Firebase 서비스 계정 JSON 파일 발견: {json_file_path}")
        
        try:
            with open(json_file_path, 'r') as f:
                config = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in config]
            
            if not missing_fields:
                print("✅ JSON 파일 형식이 올바릅니다")
                print(f"   - 프로젝트 ID: {config.get('project_id', 'N/A')}")
                print(f"   - 클라이언트 이메일: {config.get('client_email', 'N/A')}")
            else:
                print(f"❌ JSON 파일에 필요한 필드가 누락되었습니다: {missing_fields}")
                return False
                
        except json.JSONDecodeError:
            print("❌ JSON 파일 형식이 올바르지 않습니다")
            return False
        except Exception as e:
            print(f"❌ JSON 파일 읽기 실패: {e}")
            return False
    else:
        print(f"❌ Firebase 서비스 계정 JSON 파일을 찾을 수 없습니다: {json_file_path}")
        print("   Firebase Console에서 서비스 계정 키를 다운로드하여 해당 경로에 저장하세요")
        return False
    
    return True

def main():
    """메인 함수"""
    print("🚀 FCM 기능 테스트 스크립트")
    print("=" * 50)
    
    # 설정 확인
    if not test_fcm_configuration():
        print("\n❌ FCM 설정 확인 실패. 설정을 확인한 후 다시 시도하세요.")
        return
    
    # FCM 서비스 테스트
    if test_fcm_service():
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        print("\n다음 단계:")
        print("1. 실제 FCM 토큰을 사용하여 테스트")
        print("2. 웹 인터페이스에서 /fcm-test 페이지 접속")
        print("3. 안드로이드 앱에서 FCM 토큰을 서버로 전송")
    else:
        print("\n❌ 일부 테스트가 실패했습니다. 로그를 확인하고 문제를 해결하세요.")

if __name__ == "__main__":
    main()
