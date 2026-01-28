"""
Database Connection Manager
Unified DB connection management and Context Manager support
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database Connection Management Class"""
    
    def __init__(self, db_name: str = 'progress_report.db'):
        self.db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            db_name
        )
    
    def get_connection(self, read_only: bool = False) -> sqlite3.Connection:
        """
        Return database connection
        
        Args:
            read_only: True for read-only mode
            
        Returns:
            sqlite3.Connection object
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
        Transaction management with Context Manager
        
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
        Cursor management with Context Manager
        
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


# Global instance
_db = DatabaseConnection()


def get_db_connection(read_only: bool = False) -> sqlite3.Connection:
    """
    Function for legacy compatibility (compatible with existing code)
    
    Args:
        read_only: True for read-only mode
        
    Returns:
        sqlite3.Connection object
    """
    return _db.get_connection(read_only)


@contextmanager
def db_transaction(read_only: bool = False):
    """
    Transaction Context Manager (convenient usage)
    
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
    Cursor Context Manager (convenient usage)
    
    Usage:
        with db_cursor() as cursor:
            cursor.execute(...)
            results = cursor.fetchall()
    """
    with _db.cursor(read_only) as cursor:
        yield cursor

