#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\diagnostics_service\diagnostics_service.py JUMLAH BARIS 86 
#######################################################################

import os
import re
import importlib
import inspect
import sys
import time
from ..base_service import BaseService
from scanners.base_scanner import BaseScanner
class DiagnosticsService(BaseService):
    """
    A dedicated service to discover and run all system diagnostic scanners.
    This service centralizes the logic previously held by the system_diagnostics_plugin.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger(f"Service '{self.service_id}' initialized.", "DEBUG")
    def _discover_scanners(self):
        """Helper to discover all available scanner classes from the new top-level directory."""
        all_scanners = []
        scanners_dir = os.path.join(self.kernel.project_root_path, 'scanners')
        if os.path.isdir(scanners_dir):
            if scanners_dir not in sys.path:
                sys.path.insert(0, scanners_dir)
            for entry in os.scandir(scanners_dir):
                if entry.name.endswith('.py') and not entry.name.startswith('__'):
                    module_name = f"scanners.{entry.name[:-3]}"
                    try:
                        module = importlib.import_module(module_name)
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if issubclass(obj, BaseScanner) and obj is not BaseScanner:
                                all_scanners.append(obj)
                    except Exception as e:
                        self.logger(f"DiagnosticsService: Failed to import scanner from '{entry.name}': {e}", "ERROR")
        return all_scanners
    def start_scan_headless(self, scan_id: str, target_scanner_id: str = None) -> dict:
        """
        Runs all or a specific scanner module synchronously and returns a dictionary with the results.
        This is designed to be called by an API endpoint.
        """
        log_target = 'ALL' if not target_scanner_id else target_scanner_id.upper()
        self.logger(f"API-DIAG: Starting Headless Scan for ID: {scan_id} (Target: {log_target})", "INFO")
        report_lines = []
        def headless_report_handler(message, level, context=None):
            report_lines.append(f"[{level}] {message}")
        summaries = []
        all_scanners = self._discover_scanners()
        if not all_scanners:
            headless_report_handler("No scanner modules found.", "ERROR")
        scanners_to_run = []
        if target_scanner_id:
            found = False
            for scanner_class in all_scanners:
                class_id = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', scanner_class.__name__.replace("Core", "")).lower()
                class_id = class_id.replace("_scan", "")
                if class_id == target_scanner_id:
                    scanners_to_run.append(scanner_class)
                    found = True
                    break
            if not found:
                headless_report_handler(f"Scanner with ID '{target_scanner_id}' not found.", "ERROR")
        else:
            scanners_to_run = all_scanners
        for scanner_class in scanners_to_run:
            try:
                scanner_instance = scanner_class(self.kernel, headless_report_handler)
                summary = scanner_instance.run_scan()
                summaries.append(summary)
            except Exception as e:
                summary = f"FATAL ERROR while running {scanner_class.__name__}: {e}"
                summaries.append(summary)
                headless_report_handler(summary, "ERROR")
        full_report_str = "\n".join(report_lines)
        final_summary = "\n".join(summaries)
        result_data = {
            "scan_id": scan_id, "status": "completed", "timestamp": time.time(),
            "summary": final_summary, "full_log": full_report_str
        }
        self.logger(f"API-DIAG: Scan {scan_id} complete. Returning results.", "SUCCESS")
        return result_data
