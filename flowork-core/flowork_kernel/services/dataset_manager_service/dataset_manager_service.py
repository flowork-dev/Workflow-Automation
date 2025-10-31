#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\dataset_manager_service\dataset_manager_service.py JUMLAH BARIS 82 
#######################################################################

import os
import threading
import json
import uuid # [PENAMBAHAN] Import library untuk ID unik
from ..base_service import BaseService
class DatasetManagerService(BaseService):
    DB_NAME = "datasets.json"
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.db_path = os.path.join(self.kernel.data_path, self.DB_NAME)
        self.lock = threading.Lock()
    def _read_db(self):
        with self.lock:
            if not os.path.exists(self.db_path):
                return {}
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
    def _write_db(self, data):
        with self.lock:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
    def list_datasets(self):
        db = self._read_db()
        return [{"name": name} for name in db.keys()]
    def get_dataset_data(self, dataset_name: str):
        db = self._read_db()
        return db.get(dataset_name, [])
    def create_dataset(self, name: str):
        db = self._read_db()
        if name in db:
            return False
        db[name] = []
        self._write_db(db)
        return True
    def add_data_to_dataset(self, dataset_name: str, data_list: list):
        db = self._read_db()
        if dataset_name not in db:
            return False
        for item in data_list:
            if 'id' not in item or not item['id']:
                item['id'] = str(uuid.uuid4())
        db[dataset_name].extend(data_list)
        self._write_db(db)
        return True
    def delete_dataset(self, name: str):
        db = self._read_db()
        if name in db:
            del db[name]
            self._write_db(db)
            return True
        return False
    def update_dataset_row(self, dataset_name: str, row_data: dict):
        db = self._read_db()
        if dataset_name not in db or 'id' not in row_data:
            return False
        dataset = db[dataset_name]
        for i, row in enumerate(dataset):
            if row.get('id') == row_data['id']:
                dataset[i] = row_data # Replace the old row with the new one
                self._write_db(db)
                return True
        return False # Row ID not found
    def delete_dataset_row(self, dataset_name: str, row_id: str):
        db = self._read_db()
        if dataset_name not in db:
            return False
        original_count = len(db[dataset_name])
        db[dataset_name] = [row for row in db[dataset_name] if row.get('id') != row_id]
        if len(db[dataset_name]) < original_count:
            self._write_db(db)
            return True
        return False # Row ID not found
