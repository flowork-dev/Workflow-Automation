#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\prompt_manager_service\prompt_manager_service.py JUMLAH BARIS 105 
#######################################################################

import uuid
import sqlite3
from ..base_service import BaseService
class PromptManagerService(BaseService):
    """
    Manages the lifecycle (CRUD) of prompt templates in the database.
    This is a standard class-based service for reliability.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger("PromptManagerService Initialized.", "SUCCESS")
    def _get_db_connection(self):
        """Helper to get the DB service and connection just-in-time."""
        db_service = self.kernel.get_service("database_service")
        if not db_service:
            self.logger("PromptManagerService CRITICAL: DatabaseService is not available.", "CRITICAL")
            return None
        return db_service.get_connection()
    def get_all_prompts(self):
        """Fetches a list of all prompt templates."""
        try:
            with self._get_db_connection() as db_conn:
                if not db_conn: return []
                cursor = db_conn.cursor()
                cursor.execute("SELECT id, name, content FROM prompt_templates ORDER BY name ASC")
                return cursor.fetchall()
        except Exception as e:
            self.logger(f"PromptManagerService(get_all_prompts): Error - {e}", "ERROR")
            return []
    def get_prompt(self, prompt_id: str):
        """Fetches a single prompt by its ID."""
        try:
            with self._get_db_connection() as db_conn:
                if not db_conn: return None
                cursor = db_conn.cursor()
                cursor.execute("SELECT * FROM prompt_templates WHERE id = ?", (prompt_id,))
                return cursor.fetchone()
        except Exception as e:
            self.logger(f"PromptManagerService(get_prompt): Error - {e}", "ERROR")
            return None
    def create_prompt(self, prompt_data: dict):
        """Creates a new prompt template."""
        name = prompt_data.get('name')
        content = prompt_data.get('content')
        if not name or not content:
            return {'error': 'Name and content are required'}
        new_id = str(uuid.uuid4())
        try:
            with self._get_db_connection() as db_conn:
                if not db_conn: return {'error': 'DatabaseService not available'}
                cursor = db_conn.cursor()
                cursor.execute("INSERT INTO prompt_templates (id, name, content) VALUES (?, ?, ?)", (new_id, name, content))
                db_conn.commit()
            return {'id': new_id, 'name': name, 'status': 'created'}
        except sqlite3.IntegrityError:
            return {'error': f"A prompt with the name '{name}' already exists."}
        except Exception as e:
            self.logger(f"PromptManagerService(create_prompt): Error - {e}", "ERROR")
            return {'error': str(e)}
    def update_prompt(self, prompt_id: str, prompt_data: dict):
        """Updates an existing prompt template."""
        name = prompt_data.get('name')
        content = prompt_data.get('content')
        if not name or content is None:
            return {'error': 'Name and content are required'}
        try:
            with self._get_db_connection() as db_conn:
                if not db_conn: return {'error': 'DatabaseService not available'}
                cursor = db_conn.cursor()
                cursor.execute("UPDATE prompt_templates SET name = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (name, content, prompt_id))
                if cursor.rowcount == 0:
                    return {'error': 'Prompt not found'}
                db_conn.commit()
            return {'id': prompt_id, 'status': 'updated'}
        except sqlite3.IntegrityError:
            return {'error': f"A prompt with the name '{name}' already exists."}
        except Exception as e:
            self.logger(f"PromptManagerService(update_prompt): Error - {e}", "ERROR")
            return {'error': str(e)}
    def delete_prompt(self, prompt_id: str):
        """Deletes a prompt template."""
        try:
            with self._get_db_connection() as db_conn:
                if not db_conn: return {'error': 'DatabaseService not available'}
                cursor = db_conn.cursor()
                cursor.execute("DELETE FROM prompt_templates WHERE id = ?", (prompt_id,))
                if cursor.rowcount == 0:
                    return {'error': 'Prompt not found'}
                db_conn.commit()
            return {'id': prompt_id, 'status': 'deleted'}
        except Exception as e:
            self.logger(f"PromptManagerService(delete_prompt): Error - {e}", "ERROR")
            return {'error': str(e)}
    def _dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
