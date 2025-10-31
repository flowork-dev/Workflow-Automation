#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\update_service\update_service.py JUMLAH BARIS 134 
#######################################################################

import os
import json
import hashlib
import requests
from ..base_service import BaseService
import threading
import base64
try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
class UpdateService(BaseService):
    """
    (MODIFIED: INTERNAL SERVER MODE) Handles the SECURE automatic update process.
    This version defaults to local configuration and skips all external network checks
    to align with the private server architecture.
    """
    UPDATE_SIGNATURE_PUBLIC_KEY = (
        "-----BEGIN PUBLIC KEY-----\n"
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAysqZG2+F82W0TgLHmF3Y\n"
        "0GRPEZvXvmndTY84N/wA1ljt+JxMBVsmcVTkv8f1TrmFRD19IDzl2Yzb2lgqEbEy\n"
        "GFxHhudC28leDsVEIp8B+oYWVm8Mh242YKYK8r5DAvr9CPQivnIjZ4BWgKKddMTd\n"
        "harVxLF2CoSoTs00xWKd6VlXfoW9wdBvoDVifL+hCMepgLLdQQE4HbamPDJ3bpra\n"
        "pCgcAD5urmVoJEUJdjd+Iic27RBK7jD1dWDO2MASMh/0IyXyM8i7RDymQ88gZier\n"
        "U0OdWzeCWGyl4EquvR8lj5GNz4vg2f+oEY7h9AIC1f4ARtoihc+apSntqz7nAqa/\n"
        "sQIDAQAB\n"
        "-----END PUBLIC KEY-----"
    )
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.dev_mode_file = "devmode.on"
        self.public_key = self._load_public_key()
    def _load_public_key(self):
        if not CRYPTO_AVAILABLE:
            self.logger(
                "UpdateService: Cryptography library not found. Security features will be disabled.",
                "CRITICAL",
            )
            return None
        try:
            pem_data = self.UPDATE_SIGNATURE_PUBLIC_KEY.strip().encode("utf-8")
            return serialization.load_pem_public_key(pem_data)
        except Exception as e:
            self.logger(
                f"UpdateService: Failed to load public key for update verification: {e}",
                "CRITICAL",
            )
            return None
    def _calculate_local_sha256(self, file_path):
        """Calculates the SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except IOError:
            return None
    def _get_verified_remote_fingerprints(self):
        """(COMMENT) Downloads the fingerprint manifest from a remote source and verifies the signature. This is now disabled."""
        self.logger("UpdateService: External update check is DISABLED.", "INFO")
        return None
    def _download_file(self, relative_path):
        """(COMMENT) Downloads a single file from a remote source. This is now disabled."""
        self.logger(
            f"UpdateService: Download request for '{relative_path}' is BLOCKED.", "WARN"
        )
        return False
    def run_update_check(self):
        """
        [MODIFIED] The main method now skips external checks for private server mode.
        """
        if self.kernel.is_dev_mode:
            self.logger("DEVELOPER MODE ACTIVE: Auto-update check is disabled.", "WARN")
            return
        self.logger(
            "--- Starting SECURE Automatic Update Check (INTERNAL MODE) ---", "INFO"
        )
        remote_fingerprints = self._get_verified_remote_fingerprints()
        if not remote_fingerprints:
            self.logger(
                "Update check skipped. Core running in private server mode.", "SUCCESS"
            )
            return
        files_to_update = []
        for relative_path, remote_hash in remote_fingerprints.items():
            local_path = os.path.join(
                self.kernel.project_root_path, relative_path.replace("/", os.sep)
            )
            if not os.path.exists(local_path):
                files_to_update.append({"path": relative_path, "reason": "New file"})
            else:
                local_hash = self._calculate_local_sha256(local_path)
                if local_hash != remote_hash:
                    files_to_update.append(
                        {"path": relative_path, "reason": "File changed"}
                    )
        if not files_to_update:
            self.logger(
                "Application is up to date. No new files to download.", "SUCCESS"
            )
            return
        self.logger(
            f"Found {len(files_to_update)} file(s) to update/add. Starting download process...",
            "WARN",
        )
        success_count = 0
        for file_info in files_to_update:
            if self._download_file(file_info["path"]):
                success_count += 1
        self.logger(
            f"Update process finished. {success_count}/{len(files_to_update)} files updated successfully.",
            "SUCCESS",
        )
        if success_count > 0:
            event_bus = self.kernel.get_service("event_bus")
            if event_bus:
                self.logger(
                    "Files were updated. Requesting application restart...", "WARN"
                )
                event_bus.publish(
                    "RESTART_APP_AFTER_UPDATE",
                    {"message": f"{success_count} file(s) have been updated."},
                )
