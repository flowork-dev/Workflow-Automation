#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\database_service\database_service.py JUMLAH BARIS 62 
#######################################################################

import sqlite3
import os
from contextlib import contextmanager
from ..base_service import BaseService
class DatabaseService(BaseService):
    """
    (REPAIRED - FINAL VERSION) Manages the database connection lifecycle.
    This version uses a context manager to ensure a fresh, safe connection
    is provided for every transaction, preventing cross-thread and state issues.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.db_path = os.path.join(self.kernel.data_path, 'flowork_data.db')
        self._initialize_database()
    def _initialize_database(self):
        """Ensures the database file and initial tables exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                conn.commit()
            self.logger("DatabaseService: Database and tables initialized successfully.", "SUCCESS")
        except Exception as e:
            self.logger(f"CRITICAL FAILURE during DatabaseService initialization: {e}", "CRITICAL")
    @contextmanager
    def get_connection(self):
        """
        Provides a database connection as a context manager,
        ensuring it is always closed and transactions are handled safely.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = self._dict_factory
            yield conn
        except Exception as e:
            self.logger(f"Database connection error: {e}", "ERROR")
            raise
        finally:
            if conn:
                conn.close()
    def _dict_factory(self, cursor, row):
        """Helper to return query results as dictionaries."""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
