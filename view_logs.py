#!/usr/bin/env python3
"""
IIS 서버 로그 뷰어
실시간으로 로그를 모니터링할 수 있는 도구
"""

import os
import sys
import time
import argparse
from datetime import datetime
import glob

def get_log_files():
    """사용 가능한 로그 파일 목록 반환"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return []
    
    log_files = []
    for pattern in ["*.log", "*.txt"]:
        log_files.extend(glob.glob(os.path.join(log_dir, pattern)))
    
    return sorted(log_files)

def tail_file(filepath, lines=50):
    """파일의 마지막 N줄 읽기"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception as e:
        return [f"파일 읽기 오류: {e}\n"]

def monitor_file(filepath, follow=True):
    """파일 실시간 모니터링"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            # 파일 끝으로 이동
            f.seek(0, 2)
            
            while follow:
                line = f.readline()
                if line:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {line.rstrip()}")
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n모니터링 중단됨")
    except Exception as e:
        print(f"모니터링 오류: {e}")

def show_log_files():
    """로그 파일 목록 표시"""
    log_files = get_log_files()
    
    if not log_files:
        print("❌ 로그 파일을 찾을 수 없습니다.")
        return
    
    print("📋 사용 가능한 로그 파일:")
    print("-" * 50)
    for i, filepath in enumerate(log_files, 1):
        filename = os.path.basename(filepath)
        size = os.path.getsize(filepath)
        modified = datetime.fromtimestamp(os.path.getmtime(filepath))
        print(f"{i:2d}. {filename:<20} ({size:,} bytes, {modified.strftime('%Y-%m-%d %H:%M:%S')})")
    print("-" * 50)

def main():
    parser = argparse.ArgumentParser(description="IIS 서버 로그 뷰어")
    parser.add_argument("--list", "-l", action="store_true", help="로그 파일 목록 표시")
    parser.add_argument("--file", "-f", help="특정 로그 파일 보기")
    parser.add_argument("--lines", "-n", type=int, default=50, help="표시할 줄 수 (기본: 50)")
    parser.add_argument("--follow", action="store_true", help="실시간 모니터링")
    parser.add_argument("--all", "-a", action="store_true", help="모든 로그 파일 보기")
    
    args = parser.parse_args()
    
    print("🔍 IIS 서버 로그 뷰어")
    print("=" * 50)
    
    if args.list:
        show_log_files()
        return
    
    if args.all:
        log_files = get_log_files()
        for filepath in log_files:
            filename = os.path.basename(filepath)
            print(f"\n📄 {filename}")
            print("-" * len(filename))
            lines = tail_file(filepath, args.lines)
            for line in lines:
                print(line.rstrip())
        return
    
    if args.file:
        filepath = args.file
        if not os.path.exists(filepath):
            # logs 폴더에서 찾기
            filepath = os.path.join("logs", args.file)
            if not os.path.exists(filepath):
                print(f"❌ 파일을 찾을 수 없습니다: {args.file}")
                return
        
        if args.follow:
            print(f"🔄 실시간 모니터링: {filepath}")
            print("Ctrl+C로 중단")
            print("-" * 50)
            monitor_file(filepath)
        else:
            print(f"📄 {filepath} (마지막 {args.lines}줄)")
            print("-" * 50)
            lines = tail_file(filepath, args.lines)
            for line in lines:
                print(line.rstrip())
        return
    
    # 기본: 로그 파일 목록 표시
    show_log_files()
    print("\n사용법:")
    print("  python view_logs.py --file app.log --lines 100")
    print("  python view_logs.py --file app.log --follow")
    print("  python view_logs.py --all")

if __name__ == "__main__":
    main()
