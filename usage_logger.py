import os
import json
from datetime import datetime, date, timedelta
from flask import request, session
import logging
from pathlib import Path

class UsageLogger:
    def __init__(self, base_dir="UsageLog"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # 로깅 설정
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('logs/usage_system.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_monthly_dir(self, target_date=None):
        """월별 디렉토리 경로 반환"""
        if target_date is None:
            target_date = datetime.now()
        
        year_month = target_date.strftime("%Y-%m")
        monthly_dir = self.base_dir / year_month
        monthly_dir.mkdir(exist_ok=True)
        
        return monthly_dir
    
    def get_daily_log_file(self, log_type, target_date=None):
        """일별 로그 파일 경로 반환"""
        if target_date is None:
            target_date = datetime.now()
        
        monthly_dir = self.get_monthly_dir(target_date)
        date_str = target_date.strftime("%Y-%m-%d")
        log_file = monthly_dir / f"{log_type}_{date_str}.json"
        
        return log_file
    
    def log_access(self, user_info=None, page_info=None):
        """접속 로그 기록"""
        try:
            now = datetime.now()
            log_file = self.get_daily_log_file("access", now)
            
            # 접속 정보 수집
            access_info = {
                "timestamp": now.isoformat(),
                "user": {
                    "id": user_info.get("id") if user_info else None,
                    "username": user_info.get("username") if user_info else None,
                    "display_name": user_info.get("display_name") if user_info else None,
                    "role": user_info.get("role") if user_info else None,
                    "position": user_info.get("position") if user_info else None
                },
                "page": {
                    "url": request.url if request else None,
                    "method": request.method if request else None,
                    "endpoint": request.endpoint if request else None,
                    "path": request.path if request else None
                },
                "client": {
                    "ip": request.remote_addr if request else None,
                    "user_agent": request.headers.get('User-Agent') if request else None,
                    "referer": request.headers.get('Referer') if request else None
                },
                "session": {
                    "session_id": session.get("session_id") if session else None,
                    "login_time": session.get("login_time") if session else None
                }
            }
            
            # 기존 로그 읽기
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # 새 로그 추가
            existing_logs.append(access_info)
            
            # 로그 파일 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Access log recorded: {user_info.get('username', 'Unknown')} - {request.path if request else 'Unknown'}")
            
        except Exception as e:
            self.logger.error(f"Error logging access: {str(e)}")
    
    def log_progress_note(self, note_data, user_info=None, success=True, error_message=None):
        """Progress Note 로그 기록"""
        try:
            now = datetime.now()
            log_file = self.get_daily_log_file("progress_notes", now)
            
            # Progress Note 정보 수집
            note_log = {
                "timestamp": now.isoformat(),
                "user": {
                    "id": user_info.get("id") if user_info else None,
                    "username": user_info.get("username") if user_info else None,
                    "display_name": user_info.get("display_name") if user_info else None,
                    "role": user_info.get("role") if user_info else None,
                    "position": user_info.get("position") if user_info else None
                },
                "note_data": {
                    "client_id": note_data.get("clientId"),
                    "event_type": note_data.get("eventType"),
                    "care_area": note_data.get("careArea"),
                    "risk_rating": note_data.get("riskRating"),
                    "create_date": note_data.get("createDate"),
                    "event_date": note_data.get("eventDate"),
                    "late_entry": note_data.get("lateEntry", False),
                    "notes_length": len(note_data.get("notes", "")),
                    "notes_preview": note_data.get("notes", "")[:200] + "..." if len(note_data.get("notes", "")) > 200 else note_data.get("notes", ""),
                    "notes_full": note_data.get("notes", ""),  # 전체 노트 내용 저장
                    "create_time": note_data.get("createTime"),
                    "event_time": note_data.get("eventTime"),
                    "site": note_data.get("site", "Unknown")
                },
                "result": {
                    "success": success,
                    "error_message": error_message
                },
                "client": {
                    "ip": request.remote_addr if request else None,
                    "user_agent": request.headers.get('User-Agent') if request else None
                }
            }
            
            # 기존 로그 읽기
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # 새 로그 추가
            existing_logs.append(note_log)
            
            # 로그 파일 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            status = "success" if success else "failed"
            self.logger.info(f"Progress note log recorded: {user_info.get('username', 'Unknown')} - {status}")
            
        except Exception as e:
            self.logger.error(f"Error logging progress note: {str(e)}")
    
    def log_api_call(self, api_endpoint, request_data=None, response_data=None, user_info=None, success=True, error_message=None):
        """API 호출 로그 기록"""
        try:
            now = datetime.now()
            log_file = self.get_daily_log_file("api_calls", now)
            
            # API 호출 정보 수집
            api_log = {
                "timestamp": now.isoformat(),
                "user": {
                    "id": user_info.get("id") if user_info else None,
                    "username": user_info.get("username") if user_info else None,
                    "display_name": user_info.get("display_name") if user_info else None,
                    "role": user_info.get("role") if user_info else None,
                    "position": user_info.get("position") if user_info else None
                },
                "api_call": {
                    "endpoint": api_endpoint,
                    "method": request.method if request else None,
                    "request_data": request_data,
                    "response_data": response_data
                },
                "result": {
                    "success": success,
                    "error_message": error_message
                },
                "client": {
                    "ip": request.remote_addr if request else None,
                    "user_agent": request.headers.get('User-Agent') if request else None
                }
            }
            
            # 기존 로그 읽기
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # 새 로그 추가
            existing_logs.append(api_log)
            
            # 로그 파일 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            status = "success" if success else "failed"
            self.logger.info(f"API call log recorded: {api_endpoint} - {user_info.get('username', 'Unknown')} - {status}")
            
        except Exception as e:
            self.logger.error(f"Error logging API call: {str(e)}")
    
    def get_log_summary(self, start_date=None, end_date=None, log_type="access"):
        """로그 요약 정보 반환"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(day=1)
            if end_date is None:
                end_date = datetime.now()
            
            summary = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_entries": 0,
                "unique_users": set(),
                "daily_counts": {},
                "error_count": 0
            }
            
            current_date = start_date
            while current_date <= end_date:
                log_file = self.get_daily_log_file(log_type, current_date)
                date_str = current_date.strftime("%Y-%m-%d")
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            daily_logs = json.load(f)
                        
                        summary["total_entries"] += len(daily_logs)
                        summary["daily_counts"][date_str] = len(daily_logs)
                        
                        for log_entry in daily_logs:
                            user_info = log_entry.get("user", {})
                            username = user_info.get("username") or user_info.get("display_name")
                            if username:
                                summary["unique_users"].add(username)
                            
                            # 에러 카운트 (progress_notes와 api_calls의 경우)
                            if log_type in ["progress_notes", "api_calls"]:
                                if not log_entry.get("result", {}).get("success", True):
                                    summary["error_count"] += 1
                    
                    except Exception as e:
                        self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                
                current_date = current_date + timedelta(days=1) # Increment date correctly
            
            # set을 list로 변환
            summary["unique_users"] = list(summary["unique_users"])
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting log summary: {str(e)}")
            return None

# 전역 로거 인스턴스
usage_logger = UsageLogger() 