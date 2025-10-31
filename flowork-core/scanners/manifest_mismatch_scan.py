#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\manifest_mismatch_scan.py JUMLAH BARIS 76 
#######################################################################

import os
import json
from .base_scanner import BaseScanner
class ManifestMismatchScan(BaseScanner):
    """
    Scans for discrepancies between the files on disk and the entries in the
    core_integrity.json manifest. This helps detect untracked or missing files.
    """
    def run_scan(self) -> str:
        self.report("\n[SCAN] === Starting Manifest vs. Filesystem Mismatch Scan ===", "SCAN")
        manifest_path = os.path.join(self.kernel.project_root_path, "core_integrity.json")
        if not os.path.exists(manifest_path):
            self._register_finding(
                "  [CRITICAL] -> core_integrity.json manifest file is missing. Cannot perform scan."
            )
            return "Scan failed: Manifest file not found."
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_files = set(json.load(f).keys())
        except json.JSONDecodeError:
            self._register_finding(
                "  [CRITICAL] -> core_integrity.json is corrupted and cannot be parsed as JSON.",
                context={"file": manifest_path}
            )
            return "Scan failed: Manifest file is corrupted."
        core_dirs_to_scan = [
            "flowork_kernel", "modules", "plugins", "widgets", "ai_providers",
            "triggers", "core_services", "formatters", "themes", "locales"
        ]
        ignore_list = ["__pycache__", ".pyc", "node_modules", ".git", "temp_uploads", "data", "logs", "core_integrity.json"]
        disk_files = set()
        for item in os.listdir(self.kernel.project_root_path):
            item_path = os.path.join(self.kernel.project_root_path, item)
            if os.path.isfile(item_path) and not any(ignored in item for ignored in ignore_list):
                 relative_path = os.path.relpath(item_path, self.kernel.project_root_path).replace(os.sep, '/')
                 disk_files.add(relative_path)
        for core_dir in core_dirs_to_scan:
            full_dir_path = os.path.join(self.kernel.project_root_path, core_dir)
            if not os.path.isdir(full_dir_path):
                continue
            for root, dirs, files in os.walk(full_dir_path):
                dirs[:] = [d for d in dirs if d not in ignore_list]
                for file in files:
                    if any(ignored in file for ignored in ignore_list):
                        continue
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.kernel.project_root_path).replace(os.sep, '/')
                    disk_files.add(relative_path)
        untracked_files = disk_files - manifest_files
        missing_files = manifest_files - disk_files
        if untracked_files:
            for file_path in sorted(list(untracked_files)):
                self._register_finding(
                    f"  [MAJOR] -> Untracked file found on disk but not in manifest: {file_path}. Run generate_integrity_manifest.py to fix.",
                    context={"file": file_path}
                )
        if missing_files:
            for file_path in sorted(list(missing_files)):
                self._register_finding(
                    f"  [CRITICAL] -> Missing file! Listed in manifest but not found on disk: {file_path}.",
                    context={"file": file_path}
                )
        if not untracked_files and not missing_files:
            self.report("  [OK] -> Manifest is perfectly in sync with the filesystem.", "OK")
            summary = "Manifest Integrity Scan: Passed. All files match."
        else:
            summary = f"Manifest Integrity Scan: Found {len(untracked_files)} untracked and {len(missing_files)} missing files."
        self.report(f"[DONE] {summary}", "SUCCESS" if not (untracked_files or missing_files) else "WARN")
        return summary
