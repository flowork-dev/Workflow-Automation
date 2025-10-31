#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\core_integrity_scan.py JUMLAH BARIS 39 
#######################################################################

import os
from .base_scanner import BaseScanner
class CoreIntegrityScan(BaseScanner):
    """
    Ensures that the IntegrityCheckerService is being called by the StartupService.
    This is a "Doctor Code" check for our "Benteng Baja" feature.
    """
    def run_scan(self) -> str:
        self.report("\n[SCAN] === Starting Core Integrity Vitals Scan ===", "SCAN")
        startup_service_path = os.path.join(self.kernel.project_root_path, "flowork_kernel", "services", "startup_service", "startup_service.py")
        checks_passed = 0
        total_checks = 1
        if self._check_content(startup_service_path, "self.kernel.get_service(\"integrity_checker_service\").verify_core_files()"):
            checks_passed += 1
            self.report("  [OK] -> Vitals check passed: File integrity check is correctly called at startup.", "OK")
        else:
            self._register_finding(
                "  [CRITICAL] -> Regression detected! The 'Benteng Baja' integrity check is missing from StartupService.",
                context={"file": startup_service_path}
            )
        summary = f"Core Integrity Vitals Scan: {checks_passed}/{total_checks} critical checks passed."
        self.report(f"[DONE] {summary}", "SUCCESS" if checks_passed == total_checks else "WARN")
        return summary
    def _check_content(self, file_path, text_to_find):
        """Helper to check if a text exists in a file."""
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return text_to_find in f.read()
        except Exception:
            return False
