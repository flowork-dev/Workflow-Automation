#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\cache_integrity_scan.py JUMLAH BARIS 53 
#######################################################################

import os
import json
from .base_scanner import BaseScanner
class CacheIntegrityScan(BaseScanner):
    """
    Ensures that the component discovery caching mechanisms are intact and functional.
    It verifies that managers use the cache and that the cache files are valid.
    """
    def run_scan(self) -> str:
        self.report("\n[SCAN] === Starting Component Cache Integrity Scan ===", "SCAN")
        services_to_check = [
            ("ModuleManager", "flowork_kernel/services/module_manager_service/module_manager_service.py", "module_index.cache"),
            ("WidgetManager", "flowork_kernel/services/widget_manager_service/widget_manager_service.py", "widget_index.cache"),
            ("TriggerManager", "flowork_kernel/services/trigger_manager_service/trigger_manager_service.py", "trigger_index.cache")
        ]
        checks_passed = 0
        total_checks = len(services_to_check) * 2 # Logic check + cache file check for each
        for service_name, service_path_rel, cache_filename in services_to_check:
            service_path_abs = os.path.join(self.kernel.project_root_path, service_path_rel)
            cache_path_abs = os.path.join(self.kernel.data_path, cache_filename)
            if os.path.exists(service_path_abs):
                with open(service_path_abs, 'r', encoding='utf-8') as f:
                    content = f.read()
                if "_is_cache_valid" in content:
                    self.report(f"  [OK] -> {service_name} contains cache validation logic.", "OK")
                    checks_passed += 1
                else:
                    self._register_finding(f"  [CRITICAL] -> {service_name} is missing its `_is_cache_valid` logic. Performance will be degraded.", context={"file": service_path_abs})
            else:
                self._register_finding(f"  [CRITICAL] -> Service file for {service_name} not found at {service_path_rel}.", context={"file": service_path_abs})
            if os.path.exists(cache_path_abs):
                try:
                    with open(cache_path_abs, 'r', encoding='utf-8') as f:
                        json.load(f)
                    self.report(f"  [OK] -> Cache file '{cache_filename}' is valid JSON.", "OK")
                    checks_passed += 1
                except json.JSONDecodeError:
                    self._register_finding(f"  [MAJOR] -> Cache file '{cache_filename}' is corrupted (invalid JSON).", context={"file": cache_path_abs})
                except Exception as e:
                    self._register_finding(f"  [MAJOR] -> Could not read cache file '{cache_filename}': {e}", context={"file": cache_path_abs})
            else:
                self.report(f"  [INFO] -> Cache file '{cache_filename}' does not exist yet. Will be created on next run.", "INFO")
                checks_passed += 1
        summary = f"Cache Integrity Scan: {checks_passed}/{total_checks} checks passed."
        self.report(f"[DONE] {summary}", "SUCCESS" if checks_passed == total_checks else "WARN")
        return summary
