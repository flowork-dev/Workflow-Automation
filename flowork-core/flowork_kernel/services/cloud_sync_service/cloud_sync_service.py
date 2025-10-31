#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\cloud_sync_service\cloud_sync_service.py JUMLAH BARIS 172 
#######################################################################

import os
import shutil
import base64
import requests
from ..base_service import BaseService
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import zipfile
import tempfile
class CloudSyncService(BaseService):
    """
    Manages the End-to-End Encrypted (E2EE) backup and restore process.
    This service handles zipping, password-based key derivation, encryption,
    and communication with the Gateway for storing the encrypted blob.
    """
    TIER_REQUIREMENT = "creator"  # Fitur ini butuh minimal tier Creator
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.users_data_path = os.path.join(self.kernel.data_path, "users")
    def _generate_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Menghasilkan kunci enkripsi 32-byte dari password user menggunakan PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # Iterasi tinggi untuk keamanan
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.logger("Successfully derived encryption key from password.", "DEBUG")
        return key
    def _get_user_data_path(self, user_id: str) -> str:
        """Mendapatkan path ke folder data spesifik milik user."""
        return os.path.join(self.users_data_path, user_id)
    def _create_zip_from_user_data(self, user_id: str) -> str:
        """Meng-kompres seluruh folder data user menjadi satu file zip sementara."""
        user_folder = self._get_user_data_path(user_id)
        if not os.path.isdir(user_folder):
            raise FileNotFoundError(
                f"User data directory not found for user_id: {user_id}"
            )
        temp_dir = os.path.join(self.kernel.data_path, "temp_sync")
        os.makedirs(temp_dir, exist_ok=True)
        output_zip_path = os.path.join(temp_dir, f"backup_{user_id}")
        self.logger(f"Creating zip archive for user '{user_id}'...", "INFO")
        shutil.make_archive(output_zip_path, "zip", user_folder)
        self.logger(
            f"Successfully created zip archive at: {output_zip_path}.zip", "SUCCESS"
        )
        return f"{output_zip_path}.zip"
    def encrypt_and_upload_backup(self, user_id: str, password: str):
        """
        Fungsi utama untuk menjalankan proses backup: zip, enkripsi, dan upload.
        """
        permission_manager = self.kernel.get_service("permission_manager_service")
        if permission_manager:
            permission_manager.check_permission(self.TIER_REQUIREMENT)
        if not password:
            return False, "Password is required for encryption."
        try:
            zip_path = self._create_zip_from_user_data(user_id)
            salt = os.urandom(16)
            key = self._generate_key_from_password(password, salt)
            fernet = Fernet(key)
            self.logger(f"Encrypting data for user '{user_id}'...", "INFO")
            with open(zip_path, "rb") as f:
                zip_data = f.read()
            encrypted_data = fernet.encrypt(zip_data)
            self.logger(f"Encryption successful.", "SUCCESS")
            os.remove(zip_path)
            files = {
                "backup_file": (
                    "backup.zip.enc",
                    encrypted_data,
                    "application/octet-stream",
                )
            }
            payload = {
                "user_id": user_id,
                "salt": base64.b64encode(salt).decode("utf-8"),
            }
            self.logger(f"Uploading encrypted backup to Gateway...", "INFO")
            gateway_url = "https://api.flowork.cloud"
            upload_endpoint = f"{gateway_url}/api/v1/engine/sync/upload-backup"
            headers = {"X-API-Key": os.getenv("GATEWAY_SECRET_TOKEN")}
            response = requests.post(
                upload_endpoint, files=files, data=payload, headers=headers
            )
            response.raise_for_status()
            self.logger(
                f"Upload successful! Gateway responded: {response.json()}", "SUCCESS"
            )
            return True, "Backup successful!"
        except Exception as e:
            self.logger(f"An error occurred during the backup process: {e}", "CRITICAL")
            import traceback
            self.logger(traceback.format_exc(), "DEBUG")
            return False, str(e)
    def download_and_decrypt_backup(self, user_id: str, password: str):
        """
        Fungsi utama untuk menjalankan proses restore: download, dekripsi, dan ekstrak.
        """
        permission_manager = self.kernel.get_service("permission_manager_service")
        if permission_manager:
            permission_manager.check_permission(self.TIER_REQUIREMENT)
        if not password:
            return False, "Password is required for decryption."
        self.logger(f"Starting restore process for user '{user_id}'...", "INFO")
        try:
            gateway_url = "https://api.flowork.cloud"
            download_endpoint = f"{gateway_url}/api/v1/engine/sync/download-backup"
            headers = {"X-API-Key": os.getenv("GATEWAY_SECRET_TOKEN")}
            params = {"user_id": user_id}
            self.logger(f"Requesting encrypted backup from Gateway...", "INFO")
            response = requests.get(download_endpoint, headers=headers, params=params)
            response.raise_for_status()
            encrypted_data = response.content
            salt_b64 = response.headers.get("X-Flowork-Salt")
            if not salt_b64:
                raise ValueError("Salt not found in response headers from Gateway.")
            salt = base64.b64decode(salt_b64)
            key = self._generate_key_from_password(password, salt)
            fernet = Fernet(key)
            self.logger(f"Decrypting user data...", "INFO")
            decrypted_zip_data = fernet.decrypt(encrypted_data)
            self.logger(f"Decryption successful.", "SUCCESS")
            temp_zip_path = os.path.join(
                tempfile.gettempdir(), f"restore_{user_id}.zip"
            )
            with open(temp_zip_path, "wb") as f:
                f.write(decrypted_zip_data)
            user_data_path = self._get_user_data_path(user_id)
            if os.path.isdir(user_data_path):
                self.logger(f"Removing old user data at '{user_data_path}'...", "WARN")
                shutil.rmtree(user_data_path)
            os.makedirs(user_data_path, exist_ok=True)
            self.logger(f"Extracting backup to '{user_data_path}'...", "INFO")
            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                zip_ref.extractall(user_data_path)
            os.remove(temp_zip_path)  # Hapus file zip sementara
            self.logger(
                f"Restore process for user '{user_id}' completed successfully!",
                "SUCCESS",
            )
            self.kernel.hot_reload_components()  # Contohnya
            return True, "Restore completed successfully."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.logger(
                    f"No backup found on the server for user '{user_id}'.", "WARN"
                )
                return False, "No backup found on the server."
            else:
                self.logger(
                    f"An HTTP error occurred during the restore process: {e.response.text}",
                    "CRITICAL",
                )
                return False, f"Server error: {e.response.text}"
        except Exception as e:
            self.logger(
                f"An error occurred during the restore process: {e}", "CRITICAL"
            )
            import traceback
            self.logger(traceback.format_exc(), "DEBUG")
            return False, str(e)
