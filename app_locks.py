import threading
import time

DB_WRITE_LOCK = threading.Lock()

class write_lock:
    def __init__(self, timeout_sec: float = 8.0):
        self.timeout_sec = timeout_sec
        self.acquired = False

    def __enter__(self):
        deadline = time.time() + self.timeout_sec
        while time.time() < deadline and not self.acquired:
            self.acquired = DB_WRITE_LOCK.acquire(timeout=0.25)
        if not self.acquired:
            raise TimeoutError("DB write lock acquire timeout")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.acquired:
            DB_WRITE_LOCK.release()
        return False


