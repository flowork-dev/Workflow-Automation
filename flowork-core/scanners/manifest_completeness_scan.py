#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\manifest_completeness_scan.py JUMLAH BARIS 74 
#######################################################################

import os
import json
from collections import OrderedDict
from .base_scanner import BaseScanner
class ManifestCompletenessScanCore(BaseScanner):
    """
    Scans all component manifests to ensure they contain essential metadata.
    [V2] This version doesn't just add missing fields, it also REBUILDS the
    manifest to enforce a standard, readable key order.
    """
    REQUIRED_FIELDS = {
        "icon_file": "icon.png",
        "author": "Flowork Contributor",
        "email": "Contributor@teetah.art",
        "website": "www.teetah.art"
    }
    IDEAL_KEY_ORDER = [
        "id", "name", "version", "icon_file", "author", "email", "website",
        "description", "type", "entry_point"
    ]
    def run_scan(self) -> str:
        self.report("\n[INFO] === Starting Manifest Completeness & Order Scan (V2) ===", "INFO")
        module_manager = self.kernel.get_service("module_manager_service")
        widget_manager = self.kernel.get_service("widget_manager_service")
        if not module_manager or not widget_manager:
            self._register_finding("  [ERROR] -> Core services not found!", "CRITICAL")
            return "Scan Failed: Core service missing."
        all_components = {**module_manager.loaded_modules, **widget_manager.loaded_widgets}
        patched_files_count = 0
        for component_id, data in all_components.items():
            component_path = data.get("path")
            if not component_path: continue
            manifest_path = os.path.join(component_path, 'manifest.json')
            if not os.path.exists(manifest_path): continue
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    original_manifest_data = json.load(f)
                current_manifest = original_manifest_data.copy()
                keys_to_add = []
                for key, default_value in self.REQUIRED_FIELDS.items():
                    if key not in current_manifest:
                        keys_to_add.append(key)
                        current_manifest[key] = default_value
                reordered_manifest = OrderedDict()
                for key in self.IDEAL_KEY_ORDER:
                    if key in current_manifest:
                        reordered_manifest[key] = current_manifest.pop(key)
                for key, value in current_manifest.items():
                    reordered_manifest[key] = value
                if keys_to_add or list(reordered_manifest.keys()) != list(original_manifest_data.keys()):
                    self.report(f"----------------------------------------\n[SCAN] Analyzing manifest for: '{component_id}'", "SCAN")
                    with open(manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(reordered_manifest, f, indent=4, ensure_ascii=False)
                    action_log = "tidied up key order."
                    if keys_to_add:
                        action_log = f"added missing keys: {', '.join(keys_to_add)} and tidied up order."
                    message = (f"  [WARN] -> Patched manifest for '{component_id}': {action_log}")
                    self._register_finding(message, context={"component_id": component_id})
                    patched_files_count += 1
            except Exception as e:
                self.report(f"----------------------------------------\n[SCAN] Analyzing manifest for: '{component_id}'", "SCAN")
                self._register_finding(f"  [ERROR] -> Could not process manifest for '{component_id}': {e}", "ERROR")
        if patched_files_count == 0:
            self.report("  [OK] -> All component manifests are already complete and well-ordered.", "OK")
        summary = f"Manifest Scan: {patched_files_count} manifests were patched for completeness or consistency."
        self.report(f"[DONE] {summary}", "SUCCESS")
        return summary
