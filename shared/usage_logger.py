import os
import json
from datetime import datetime, date, timedelta, timezone
from flask import request, session
import logging
from pathlib import Path

class UsageLogger:
    def __init__(self, base_dir="UsageLog"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Logging configuration
        self.setup_logging()
    
    def setup_logging(self):
        """Logging configuration"""
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
    
    def get_adelaide_timezone(self):
        """Return Adelaide timezone (considering DST)"""
        from datetime import datetime, timezone, timedelta
        
        # Current UTC time
        utc_now = datetime.now(timezone.utc)
        year = utc_now.year
        
        # DST start: First Sunday of October at 2:00 AM
        dst_start = datetime(year, 10, 1, 2, 0, 0, tzinfo=timezone.utc)
        while dst_start.weekday() != 6:  # Find Sunday
            dst_start = dst_start + timedelta(days=1)
        
        # DST end: First Sunday of April at 2:00 AM
        dst_end = datetime(year, 4, 1, 2, 0, 0, tzinfo=timezone.utc)
        while dst_end.weekday() != 6:  # Find Sunday
            dst_end = dst_end + timedelta(days=1)
        
        # Check DST period (October ~ March of next year)
        if utc_now >= dst_start or utc_now < dst_end:
            # ACDT: UTC+10:30 (Daylight Saving Time)
            return timezone(timedelta(hours=10, minutes=30))
        else:
            # ACST: UTC+9:30 (Standard Time)
            return timezone(timedelta(hours=9, minutes=30))
    
    def get_monthly_dir(self, target_date=None):
        """Return monthly directory path"""
        if target_date is None:
            target_date = datetime.now()
        
        year_month = target_date.strftime("%Y-%m")
        monthly_dir = self.base_dir / year_month
        monthly_dir.mkdir(exist_ok=True)
        
        return monthly_dir
    
    def get_daily_log_file(self, log_type, target_date=None):
        """Return daily log file path"""
        if target_date is None:
            target_date = datetime.now()
        
        monthly_dir = self.get_monthly_dir(target_date)
        date_str = target_date.strftime("%Y-%m-%d")
        log_file = monthly_dir / f"{log_type}_{date_str}.json"
        
        return log_file
    
    def log_access(self, user_info=None, page_info=None):
        """Record access log"""
        try:
            # Use Adelaide timezone (ACST: UTC+9:30, ACDT: UTC+10:30)
            adelaide_tz = self.get_adelaide_timezone()
            now = datetime.now(adelaide_tz)
            log_file = self.get_daily_log_file("access", now)
            
            # Collect access information
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
            
            # Read existing logs
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # Add new log
            existing_logs.append(access_info)
            
            # Save log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Access log recorded: {user_info.get('username', 'Unknown')} - {request.path if request else 'Unknown'}")
            
        except Exception as e:
            self.logger.error(f"Error logging access: {str(e)}")
    
    def log_progress_note(self, note_data, user_info=None, success=True, error_message=None):
        """Record Progress Note log"""
        try:
            # Use Adelaide timezone (ACST: UTC+9:30, ACDT: UTC+10:30)
            adelaide_tz = self.get_adelaide_timezone()
            now = datetime.now(adelaide_tz)
            log_file = self.get_daily_log_file("progress_notes", now)
            
            # Collect Progress Note information
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
                    "notes_full": note_data.get("notes", ""),  # Store full note content
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
            
            # Read existing logs
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # Add new log
            existing_logs.append(note_log)
            
            # Save log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            status = "success" if success else "failed"
            self.logger.info(f"Progress note log recorded: {user_info.get('username', 'Unknown')} - {status}")
            
        except Exception as e:
            self.logger.error(f"Error logging progress note: {str(e)}")
    
    def log_api_call(self, api_endpoint, request_data=None, response_data=None, user_info=None, success=True, error_message=None):
        """Record API call log"""
        try:
            # Use Adelaide timezone (ACST: UTC+9:30, ACDT: UTC+10:30)
            adelaide_tz = self.get_adelaide_timezone()
            now = datetime.now(adelaide_tz)
            log_file = self.get_daily_log_file("api_calls", now)
            
            # Collect API call information
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
            
            # Read existing logs
            existing_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_logs = []
            
            # Add new log
            existing_logs.append(api_log)
            
            # Save log file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            status = "success" if success else "failed"
            self.logger.info(f"API call log recorded: {api_endpoint} - {user_info.get('username', 'Unknown')} - {status}")
            
        except Exception as e:
            self.logger.error(f"Error logging API call: {str(e)}")
    
    def get_log_summary(self, start_date=None, end_date=None, log_type="access"):
        """Return log summary information"""
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
                            
                            # Error count (for progress_notes and api_calls)
                            if log_type in ["progress_notes", "api_calls"]:
                                if not log_entry.get("result", {}).get("success", True):
                                    summary["error_count"] += 1
                    
                    except Exception as e:
                        self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                
                current_date = current_date + timedelta(days=1) # Increment date correctly
            
            # Convert set to list
            summary["unique_users"] = list(summary["unique_users"])
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting log summary: {str(e)}")
            return None

    def get_access_log_hourly_summary(self, start_date=None, end_date=None):
        """Return hourly user activity summary for Access log"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(day=1)
            if end_date is None:
                end_date = datetime.now()
            
            hourly_summary = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_entries": 0,
                "unique_users": set(),
                "hourly_activity": {},  # Hourly activity
                "user_activity": {},    # User activity
                "page_activity": {}     # Page activity
            }
            
            current_date = start_date
            while current_date <= end_date:
                log_file = self.get_daily_log_file("access", current_date)
                date_str = current_date.strftime("%Y-%m-%d")
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            daily_logs = json.load(f)
                        
                        hourly_summary["total_entries"] += len(daily_logs)
                        
                        for log_entry in daily_logs:
                            user_info = log_entry.get("user", {})
                            username = user_info.get("username") or user_info.get("display_name")
                            display_name = user_info.get("display_name")
                            role = user_info.get("role")
                            
                            if username:
                                hourly_summary["unique_users"].add(username)
                            
                            # Extract hour from timestamp
                            timestamp = log_entry.get("timestamp", "")
                            if timestamp:
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    hour_key = dt.strftime("%Y-%m-%d %H:00")
                                    date_hour_key = dt.strftime("%Y-%m-%d")
                                    
                                    # Count hourly activity
                                    if hour_key not in hourly_summary["hourly_activity"]:
                                        hourly_summary["hourly_activity"][hour_key] = {
                                            "total_visits": 0,
                                            "unique_users": set(),
                                            "pages": {}
                                        }
                                    
                                    hourly_summary["hourly_activity"][hour_key]["total_visits"] += 1
                                    if username:
                                        hourly_summary["hourly_activity"][hour_key]["unique_users"].add(username)
                                    
                                    # Page information
                                    page_info = log_entry.get("page", {})
                                    page_path = page_info.get("path", "unknown")
                                    if page_path not in hourly_summary["hourly_activity"][hour_key]["pages"]:
                                        hourly_summary["hourly_activity"][hour_key]["pages"][page_path] = 0
                                    hourly_summary["hourly_activity"][hour_key]["pages"][page_path] += 1
                                    
                                    # User activity
                                    if username:
                                        if username not in hourly_summary["user_activity"]:
                                            hourly_summary["user_activity"][username] = {
                                                "display_name": display_name,
                                                "role": role,
                                                "total_visits": 0,
                                                "last_visit": "",
                                                "pages_visited": {},
                                                "hourly_visits": {}
                                            }
                                        
                                        hourly_summary["user_activity"][username]["total_visits"] += 1
                                        hourly_summary["user_activity"][username]["last_visit"] = timestamp
                                        
                                        # User page visits
                                        if page_path not in hourly_summary["user_activity"][username]["pages_visited"]:
                                            hourly_summary["user_activity"][username]["pages_visited"][page_path] = 0
                                        hourly_summary["user_activity"][username]["pages_visited"][page_path] += 1
                                        
                                        # User hourly visits
                                        if hour_key not in hourly_summary["user_activity"][username]["hourly_visits"]:
                                            hourly_summary["user_activity"][username]["hourly_visits"][hour_key] = 0
                                        hourly_summary["user_activity"][username]["hourly_visits"][hour_key] += 1
                                    
                                    # Page activity
                                    if page_path not in hourly_summary["page_activity"]:
                                        hourly_summary["page_activity"][page_path] = {
                                            "total_visits": 0,
                                            "unique_users": set(),
                                            "hourly_visits": {}
                                        }
                                    
                                    hourly_summary["page_activity"][page_path]["total_visits"] += 1
                                    if username:
                                        hourly_summary["page_activity"][page_path]["unique_users"].add(username)
                                    
                                    if hour_key not in hourly_summary["page_activity"][page_path]["hourly_visits"]:
                                        hourly_summary["page_activity"][page_path]["hourly_visits"][hour_key] = 0
                                    hourly_summary["page_activity"][page_path]["hourly_visits"][hour_key] += 1
                                    
                                except Exception as e:
                                    self.logger.warning(f"Error parsing timestamp {timestamp}: {str(e)}")
                    
                    except Exception as e:
                        self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                
                current_date = current_date + timedelta(days=1)
            
            # Convert set to list
            hourly_summary["unique_users"] = list(hourly_summary["unique_users"])
            
            # Convert unique_users in hourly_activity to list
            for hour_key in hourly_summary["hourly_activity"]:
                hourly_summary["hourly_activity"][hour_key]["unique_users"] = list(
                    hourly_summary["hourly_activity"][hour_key]["unique_users"]
                )
            
            # Convert unique_users in page_activity to list
            for page_path in hourly_summary["page_activity"]:
                hourly_summary["page_activity"][page_path]["unique_users"] = list(
                    hourly_summary["page_activity"][page_path]["unique_users"]
                )
            
            return hourly_summary
            
        except Exception as e:
            self.logger.error(f"Error getting access log hourly summary: {str(e)}")
            return None

    def get_daily_access_summary(self, start_date=None, end_date=None):
        """Daily access status summary"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(day=1)
            if end_date is None:
                end_date = datetime.now()
            
            daily_summary = {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "daily_stats": {}  # Daily statistics
            }
            
            current_date = start_date
            while current_date <= end_date:
                log_file = self.get_daily_log_file("access", current_date)
                date_str = current_date.strftime("%Y-%m-%d")
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            daily_logs = json.load(f)
                        
                        # Calculate daily statistics
                        daily_users = set()
                        daily_visits = len(daily_logs)
                        
                        for log_entry in daily_logs:
                            user_info = log_entry.get("user", {})
                            username = user_info.get("username") or user_info.get("display_name")
                            if username:
                                daily_users.add(username)
                        
                        daily_summary["daily_stats"][date_str] = {
                            "total_visits": daily_visits,
                            "unique_users": len(daily_users),
                            "users": list(daily_users)
                        }
                    
                    except Exception as e:
                        self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                else:
                    # Record days without logs
                    daily_summary["daily_stats"][date_str] = {
                        "total_visits": 0,
                        "unique_users": 0,
                        "users": []
                    }
                
                current_date = current_date + timedelta(days=1)
            
            return daily_summary
            
        except Exception as e:
            self.logger.error(f"Error getting daily access summary: {str(e)}")
            return None

    def get_user_daily_activity(self, username, start_date=None, end_date=None):
        """Daily access status for specific user"""
        try:
            if start_date is None:
                start_date = datetime.now().replace(day=1)
            if end_date is None:
                end_date = datetime.now()
            
            user_activity = {
                "username": username,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "daily_activity": {}  # Daily activity
            }
            
            current_date = start_date
            while current_date <= end_date:
                log_file = self.get_daily_log_file("access", current_date)
                date_str = current_date.strftime("%Y-%m-%d")
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            daily_logs = json.load(f)
                        
                        # Filter only logs for this user
                        user_logs = []
                        for log_entry in daily_logs:
                            user_info = log_entry.get("user", {})
                            log_username = user_info.get("username") or user_info.get("display_name")
                            if log_username == username:
                                user_logs.append(log_entry)
                        
                        if user_logs:
                            # Calculate user's daily activity
                            first_visit = None
                            last_visit = None
                            total_visits = len(user_logs)
                            
                            for log_entry in user_logs:
                                timestamp = log_entry.get("timestamp", "")
                                if timestamp:
                                    try:
                                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                        if first_visit is None or dt < first_visit:
                                            first_visit = dt
                                        if last_visit is None or dt > last_visit:
                                            last_visit = dt
                                    except:
                                        pass
                            
                            # Calculate usage time (in minutes)
                            usage_minutes = 0
                            if first_visit and last_visit:
                                usage_minutes = int((last_visit - first_visit).total_seconds() / 60)
                            
                            user_activity["daily_activity"][date_str] = {
                                "total_visits": total_visits,
                                "first_visit": first_visit.isoformat() if first_visit else None,
                                "last_visit": last_visit.isoformat() if last_visit else None,
                                "usage_minutes": usage_minutes
                            }
                        else:
                            # No activity on this date
                            user_activity["daily_activity"][date_str] = {
                                "total_visits": 0,
                                "first_visit": None,
                                "last_visit": None,
                                "usage_minutes": 0
                            }
                    
                    except Exception as e:
                        self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                else:
                    # Day without log file
                    user_activity["daily_activity"][date_str] = {
                        "total_visits": 0,
                        "first_visit": None,
                        "last_visit": None,
                        "usage_minutes": 0
                    }
                
                current_date = current_date + timedelta(days=1)
            
            return user_activity
            
        except Exception as e:
            self.logger.error(f"Error getting user daily activity: {str(e)}")
            return None

    def get_date_user_activity(self, target_date):
        """User access time and usage time by user for specific date"""
        try:
            log_file = self.get_daily_log_file("access", target_date)
            
            if not log_file.exists():
                return {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "users": {}
                }
            
            with open(log_file, 'r', encoding='utf-8') as f:
                daily_logs = json.load(f)
            
            user_activities = {}
            
            for log_entry in daily_logs:
                user_info = log_entry.get("user", {})
                username = user_info.get("username") or user_info.get("display_name")
                display_name = user_info.get("display_name")
                role = user_info.get("role")
                
                if username:
                    if username not in user_activities:
                        user_activities[username] = {
                            "display_name": display_name,
                            "role": role,
                            "visits": [],
                            "first_visit": None,
                            "last_visit": None,
                            "usage_minutes": 0
                        }
                    
                    timestamp = log_entry.get("timestamp", "")
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            user_activities[username]["visits"].append(dt)
                            
                            if user_activities[username]["first_visit"] is None or dt < user_activities[username]["first_visit"]:
                                user_activities[username]["first_visit"] = dt
                            if user_activities[username]["last_visit"] is None or dt > user_activities[username]["last_visit"]:
                                user_activities[username]["last_visit"] = dt
                        except:
                            pass
            
            # Calculate usage time for each user
            for username, activity in user_activities.items():
                if activity["first_visit"] and activity["last_visit"]:
                    activity["usage_minutes"] = int((activity["last_visit"] - activity["first_visit"]).total_seconds() / 60)
                    activity["first_visit"] = activity["first_visit"].isoformat()
                    activity["last_visit"] = activity["last_visit"].isoformat()
                else:
                    activity["usage_minutes"] = 0
                    activity["first_visit"] = None
                    activity["last_visit"] = None
            
            return {
                "date": target_date.strftime("%Y-%m-%d"),
                "users": user_activities
            }
            
        except Exception as e:
            self.logger.error(f"Error getting date user activity: {str(e)}")
            return None

# Global logger instance
usage_logger = UsageLogger() 