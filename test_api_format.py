#!/usr/bin/env python3
"""
API 호출 형식 테스트
"""

from api_progressnote_fetch import ProgressNoteFetchClient
from datetime import datetime

def test_api_format():
    """API 호출 형식을 테스트합니다."""
    print("=" * 60)
    print("API 호출 형식 테스트")
    print("=" * 60)
    
    try:
        # Yankalilla 클라이언트 생성
        client = ProgressNoteFetchClient("Yankalilla")
        
        # 2025년 7월 1일 ~ 7월 11일 (POSTMAN과 동일한 날짜 범위)
        start_date = datetime(2025, 7, 1)
        end_date = datetime(2025, 7, 11)
        
        print(f"🔄 API 호출 테스트 - 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"🔄 Event Type ID: 30 (Resident of the day RN/EN)")
        
        # RN/EN 이벤트 타입으로 progress note 가져오기
        success, notes = client.fetch_progress_notes(
            start_date=start_date,
            end_date=end_date,
            progress_note_event_type_id=30
        )
        
        if success and notes:
            print(f"✅ 성공: {len(notes)}개의 노트를 가져왔습니다!")
            
            # 샘플 노트 출력
            if len(notes) > 0:
                sample = notes[0]
                print(f"📊 샘플 노트:")
                print(f"  - ID: {sample.get('Id')}")
                print(f"  - EventDate: {sample.get('EventDate')}")
                print(f"  - EventType: {sample.get('ProgressNoteEventType', {}).get('Description', 'N/A')}")
                print(f"  - ClientId: {sample.get('ClientId')}")
        else:
            print(f"❌ 실패: 노트를 가져올 수 없습니다")
            if not success:
                print(f"  오류: {notes}")
                
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_format()

