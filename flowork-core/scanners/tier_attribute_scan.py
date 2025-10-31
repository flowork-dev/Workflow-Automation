#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\tier_attribute_scan.py JUMLAH BARIS 52 
#######################################################################

import os
import re
from .base_scanner import BaseScanner
class TierAttributeScanCore(BaseScanner):
    """
    Ensures that every component's main class has a TIER attribute.
    This is critical for controlling access to free vs. premium features at the code level.
    [V3 - FINAL] This version NO LONGER auto-patches files. It only reports the issue,
    adhering to the principle that a diagnostic tool should not modify source code.
    """
    def run_scan(self) -> str:
        self.report("\n[INFO] === Starting Tier Attribute Scan (V3 - Reporting Mode) ===", "INFO")
        module_manager = self.kernel.get_service("module_manager_service")
        widget_manager = self.kernel.get_service("widget_manager_service")
        if not module_manager or not widget_manager:
            self._register_finding("  [ERROR] -> Core services (ModuleManager, WidgetManager) not found!", "CRITICAL")
            return "Scan Failed: Core service missing."
        all_components = {**module_manager.loaded_modules, **widget_manager.loaded_widgets}
        missing_tier_count = 0
        for component_id, data in all_components.items():
            manifest = data.get("manifest", {})
            entry_point = manifest.get("entry_point")
            component_path = data.get("path")
            if not all([entry_point, component_path]):
                continue
            try:
                module_filename, class_name = entry_point.split('.')
                processor_path = os.path.join(component_path, f"{module_filename}.py")
                if not os.path.exists(processor_path):
                    continue
                with open(processor_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tier_pattern = re.compile(rf"class\s+{re.escape(class_name)}[^:]*:\s*\n\s*TIER\s*=")
                if not tier_pattern.search(content):
                    message = (f"  [MAJOR] -> Module '{component_id}' is missing the required 'TIER' class attribute.")
                    self._register_finding(message, context={"component_id": component_id, "file": processor_path})
                    missing_tier_count += 1
            except Exception as e:
                self.report(f"----------------------------------------\n[SCAN] Analyzing code for: '{component_id}'", "SCAN")
                self._register_finding(f"  [ERROR] -> Could not process processor file for '{component_id}': {e}", "ERROR")
        if missing_tier_count == 0:
            self.report("  [OK] -> All components have a TIER attribute.", "OK")
        summary = f"Tier Attribute Scan: Found {missing_tier_count} components missing the TIER attribute."
        self.report(f"[DONE] {summary}", "SUCCESS" if missing_tier_count == 0 else "WARN")
        return summary
