"""
Database Connection Manager
통합된 DB 연결 관리 및 Context Manager 제공
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """데이터베이스 연결 관리 클래스"""
    
    def __init__(self, db_name: str = 'progress_report.db'):
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            db_name
        )
    
    def get_connection(self, read_only: bool = False) -> sqlite3.Connection:
        """
        데이터베이스 연결 반환
        
        Args:
            read_only: True면 읽기 전용 모드
            
        Returns:
            sqlite3.Connection 객체
        """
        if read_only:
            conn = sqlite3.connect(
                f'file:{self.db_path}?mode=ro', 
                timeout=60.0, 
                uri=True
            )
        else:
            conn = sqlite3.connect(self.db_path, timeout=60.0)
        
        conn.row_factory = sqlite3.Row
        
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
        except Exception as e:
            logger.warning(f"Failed to set PRAGMA settings: {e}")
        
        return conn
    
    @contextmanager
    def transaction(self, read_only: bool = False):
        """
        Context Manager로 트랜잭션 관리
        
        Usage:
            with db.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = self.get_connection(read_only)
        try:
            yield conn
            if not read_only:
                conn.commit()
        except Exception as e:
            if not read_only:
                conn.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            conn.close()
    
    @contextmanager
    def cursor(self, read_only: bool = False):
        """
        Context Manager로 커서 관리
        
        Usage:
            with db.cursor() as cursor:
                cursor.execute(...)
                results = cursor.fetchall()
        """
        conn = self.get_connection(read_only)
        cursor = conn.cursor()
        try:
            yield cursor
            if not read_only:
                conn.commit()
        except Exception as e:
            if not read_only:
                conn.rollback()
            logger.error(f"Database cursor error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


# 전역 인스턴스
_db = DatabaseConnection()


def get_db_connection(read_only: bool = False) -> sqlite3.Connection:
    """
    레거시 호환성을 위한 함수 (기존 코드와 호환)
    
    Args:
        read_only: True면 읽기 전용 모드
        
    Returns:
        sqlite3.Connection 객체
    """
    return _db.get_connection(read_only)


@contextmanager
def db_transaction(read_only: bool = False):
    """
    트랜잭션 Context Manager (간편 사용)
    
    Usage:
        with db_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    with _db.transaction(read_only) as conn:
        yield conn


@contextmanager
def db_cursor(read_only: bool = False):
    """
    커서 Context Manager (간편 사용)
    
    Usage:
        with db_cursor() as cursor:
            cursor.execute(...)
            results = cursor.fetchall()
    """
    with _db.cursor(read_only) as cursor:
        yield cursor

