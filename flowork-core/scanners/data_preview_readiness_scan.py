#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\data_preview_readiness_scan.py JUMLAH BARIS 135 
#######################################################################

import os
import ast
import re # ADDED: For more robust class definition finding
from .base_scanner import BaseScanner
from flowork_kernel.api_contract import IDataPreviewer
class DataPreviewReadinessScanCore(BaseScanner):
    """
    Scans modules to find which ones are good candidates for implementing the
    IDataPreviewer interface but haven't done so yet.
    [V2] This version uses a more robust patching mechanism to prevent partial updates.
    It intelligently decides whether to write a full implementation or a template.
    """
    def run_scan(self) -> str:
        self.report("\n[INFO] === Starting DYNAMIC Data Preview Readiness Scan (V2 - Fail-Safe) ===", "INFO")
        module_manager = self.kernel.get_service("module_manager_service")
        if not module_manager:
            self._register_finding("  [ERROR] -> ModuleManagerService not found!", "CRITICAL")
            return "Scan Failed: Core service missing."
        found_issues = 0
        for module_id, data in module_manager.loaded_modules.items():
            if not data.get("instance"): continue
            instance = data["instance"]
            manifest = data.get("manifest", {})
            if isinstance(instance, IDataPreviewer):
                continue
            is_candidate = False
            data_keywords = ["data", "scraper", "variable", "http", "api", "code", "runner", "ai_"]
            if manifest.get("output_schema"):
                is_candidate = True
            if not is_candidate:
                for keyword in data_keywords:
                    if keyword in module_id:
                        is_candidate = True
                        break
            if is_candidate:
                node_name = manifest.get('name', module_id)
                message = (
                    f"  [WARN] -> Module '{node_name}' detected as a candidate for data previews. Attempting to auto-patch..."
                )
                self._register_finding(message, context={"module_id": module_id})
                found_issues += 1
                self._auto_patch_module_v2(data)
        if found_issues == 0:
            self.report("  [OK] -> All candidate modules already support data previews.", "OK")
        summary = f"Data Preview Scan: Attempted to patch/implement {found_issues} modules."
        self.report(f"[DONE] {summary}", "SUCCESS")
        return summary
    def _auto_patch_module_v2(self, module_data):
        """
        [V2] A more robust method to inject the IDataPreviewer interface and method.
        It uses regex for better accuracy and constructs the full file in memory before writing.
        """
        module_id = module_data.get('manifest', {}).get('id')
        entry_point = module_data.get('manifest', {}).get('entry_point')
        module_path = module_data.get('path')
        if not all([module_id, entry_point, module_path]):
            self.report(f"    -> [ERROR] Auto-patching for '{module_id}' failed: missing manifest data.", "ERROR")
            return
        try:
            module_filename, class_name = entry_point.split('.')
            processor_path = os.path.join(module_path, f"{module_filename}.py")
            if not os.path.exists(processor_path):
                self.report(f"    -> [ERROR] Processor file not found at: {processor_path}", "ERROR")
                return
            with open(processor_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if "IDataPreviewer" in content and "def get_data_preview" in content:
                self.report(f"    -> [INFO] Module '{module_id}' seems to be already patched. Skipping.", "INFO")
                return
            patch_type = "template"
            method_template = ""
            if module_id == "set_variable_module":
                patch_type = "full implementation"
                method_template = """
    def get_data_preview(self, config: dict):
        \"\"\"
        Returns the dictionary of variables defined in the config.
        \"\"\"
        variables_to_set = config.get('variables', [])
        preview_data = {var.get('name'): var.get('value') for var in variables_to_set if var.get('name')}
        return preview_data
"""
            else:
                patch_type = "template"
                method_template = """
    def get_data_preview(self, config: dict):
        \"\"\"
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        \"\"\"
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
"""
            new_content = ""
            import_line = "from flowork_kernel.api_contract import IDataPreviewer\n"
            if import_line.strip() not in content:
                last_import_idx = content.rfind("\nfrom ")
                if last_import_idx == -1: last_import_idx = content.rfind("\nimport ")
                if last_import_idx != -1:
                    end_of_line = content.find('\n', last_import_idx + 1)
                    new_content = content[:end_of_line+1] + import_line + content[end_of_line+1:]
                else: # No imports found, add at top
                    new_content = import_line + content
            else:
                new_content = content
            class_def_pattern = re.compile(r"class\s+" + re.escape(class_name) + r"(\([^)]*\))?\s*:")
            match = class_def_pattern.search(new_content)
            if not match:
                self.report(f"    -> [ERROR] Could not find class definition for '{class_name}'. Skipping patch.", "ERROR")
                return
            original_class_def = match.group(0)
            existing_parents = match.group(1)
            if existing_parents: # Already has parents, e.g., class MyClass(BaseModule):
                if "IDataPreviewer" not in existing_parents:
                    new_parents = existing_parents.replace(")", ", IDataPreviewer)")
                    modified_class_def = f"class {class_name}{new_parents}:"
                    new_content = new_content.replace(original_class_def, modified_class_def)
            else: # No parents, e.g., class MyClass:
                modified_class_def = f"class {class_name}(IDataPreviewer):"
                new_content = new_content.replace(original_class_def, modified_class_def)
            new_content += method_template
            with open(processor_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            self.report(f"    -> [SUCCESS] Auto-patched '{os.path.basename(processor_path)}' with a {patch_type} successfully.", "SUCCESS")
        except Exception as e:
            self.report(f"    -> [FATAL] Auto-patching for '{module_id}' failed critically: {e}", "CRITICAL")
