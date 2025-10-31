#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\license_and_integrity_scan.py JUMLAH BARIS 73 
#######################################################################

import os
import re
from .base_scanner import BaseScanner
class PhaseOneIntegrityScan(BaseScanner):
    """
    Scans the UI layer to enforce the rules of Phase 1: Total Independence.
    This "Doctor Code" scanner not only finds violations but also attempts to
    auto-patch them by replacing direct kernel calls with their ApiClient equivalents.
    """
    def run_scan(self) -> str:
        self.report("\n[SCAN] === Starting Phase 1: Independence Integrity Scan (Doctor Code Mode) ===", "SCAN")
        ui_paths = [
            os.path.join(self.kernel.project_root_path, "flowork_kernel", "ui_shell"),
            os.path.join(self.kernel.project_root_path, "widgets"),
            os.path.join(self.kernel.project_root_path, "plugins")
        ]
        illegal_pattern = re.compile(r"self\.kernel\.get_service\([\"']([\w_]+)[\"']\)\.([\w_]+)\((.*)\)")
        files_scanned = 0
        total_violations_found = 0
        total_violations_healed = 0
        for path in ui_paths:
            if not os.path.isdir(path):
                continue
            for root, _, files in os.walk(path):
                if 'system_diagnostics_plugin' in root:
                    continue
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        files_scanned += 1
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                original_content = f.read()
                            content_to_patch = original_content
                            patches_made_in_file = 0
                            matches = list(illegal_pattern.finditer(original_content))
                            if matches:
                                for match in matches:
                                    total_violations_found += 1
                                    line_num = original_content.count('\n', 0, match.start()) + 1
                                    full_match_text = match.group(0)
                                    self.report(f"  [CRITICAL] -> Found violation in '{os.path.relpath(file_path, self.kernel.project_root_path)}' on line {line_num}:", "CRITICAL", context={"file": file_path, "line": line_num})
                                    self.report(f"    -> Code: {full_match_text}", "DEBUG")
                                    healed_code = None # Forcing manual fix for now
                                    if healed_code:
                                        self.report(f"    -> [HEALED] Auto-patched to: self.{healed_code}", "SUCCESS")
                                        content_to_patch = patched_content
                                        total_violations_healed += 1
                                        patches_made_in_file += 1
                                    else:
                                        self.report("    -> [MANUAL FIX NEEDED] Could not automatically determine the ApiClient equivalent.", "MAJOR")
                        except Exception as e:
                            self.report(f"  [ERROR] -> Could not read or process file: {file_path}. Reason: {e}", "CRITICAL")
        if total_violations_found == 0:
            self.report(f"  [OK] -> Scan complete. No violations found in {files_scanned} scanned files. All UI components are independent.", "OK")
        summary = f"Phase 1 Integrity Scan complete. Scanned {files_scanned} files. Found {total_violations_found} violations. Auto-healed {total_violations_healed}."
        self.report(f"[DONE] {summary}", "SUCCESS" if total_violations_found == total_violations_healed else "WARN")
        return summary
    def _auto_patch_file(self, file_path, current_content, match):
        """
        The core healing logic. Takes the file content and a regex match,
        and returns the patched content if successful.
        NOTE: This is a complex and potentially risky function. It is disabled by default in this version
        to prefer manual, controlled fixes.
        """
        return None, current_content
