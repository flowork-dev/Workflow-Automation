#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\scanners\core_compiler_health_scan.py JUMLAH BARIS 78 
#######################################################################

import os
import ast
from .base_scanner import BaseScanner
class CoreCompilerHealthScan(BaseScanner):
    """
    Ensures the CoreCompilerModule's logic is intact and its output is syntactically valid.
    [UPGRADE] Now provides a file preview on failure for easier debugging.
    [FIXED] Corrected the check string for source_workflow logic.
    """
    def run_scan(self) -> str:
        self.report("\n[SCAN] === Starting Core Compiler Health & Integrity Scan ===", "SCAN")
        compiler_path = os.path.join(self.kernel.project_root_path, "modules", "core_compiler_module", "processor.py")
        generated_services_path = os.path.join(self.kernel.project_root_path, "generated_services")
        checks_passed = 0
        total_checks = 2
        found, preview = self._check_file_content(compiler_path, "if service_filename == 'core_lifecycle.flowork':")
        if found:
            checks_passed += 1
            self.report("  [OK] -> Compiler correctly handles 'core_lifecycle.flowork' special case.", "OK")
        else:
            error_message = "  [CRITICAL] -> Compiler is missing the check for 'core_lifecycle.flowork'. This could cause startup errors."
            if preview:
                error_message += f"\n    -> File preview for '{os.path.basename(compiler_path)}' starts with:\n---\n{preview}\n---"
            self._register_finding(error_message, context={"file": compiler_path})
        found, preview = self._check_file_content(compiler_path, "\"source_workflow\": target_preset_path")
        if found:
            checks_passed += 1
            self.report("  [OK] -> Compiler correctly leaves a 'source_workflow' trail for idempotency.", "OK")
        else:
            error_message = "  [CRITICAL] -> Compiler is missing the 'source_workflow' logic. Recompiling will fail."
            if preview:
                error_message += f"\n    -> File preview for '{os.path.basename(compiler_path)}' starts with:\n---\n{preview}\n---"
            self._register_finding(error_message, context={"file": compiler_path})
        self.report("\n[SCAN] --- Scanning Generated Services for Syntax Errors ---", "SCAN")
        if not os.path.isdir(generated_services_path):
            self.report("  [INFO] -> 'generated_services' directory not found. Skipping syntax validation.", "INFO")
        else:
            found_files = 0
            for root, _, files in os.walk(generated_services_path):
                for file in files:
                    if file.endswith("service.py"):
                        found_files += 1
                        total_checks += 1
                        service_path = os.path.join(root, file)
                        try:
                            with open(service_path, 'r', encoding='utf-8') as f:
                                ast.parse(f.read())
                            self.report(f"  [OK] -> Generated file is syntactically valid: {os.path.relpath(service_path, self.kernel.project_root_path)}", "OK")
                            checks_passed += 1
                        except SyntaxError as e:
                            self._register_finding(f"  [CRITICAL] -> Generated file has a SyntaxError: {os.path.relpath(service_path, self.kernel.project_root_path)} | Error: {e}", context={"file": service_path})
                        except Exception as e:
                            self._register_finding(f"  [CRITICAL] -> Could not parse generated file: {os.path.relpath(service_path, self.kernel.project_root_path)} | Error: {e}", context={"file": service_path})
            if found_files == 0:
                self.report("  [INFO] -> No generated 'service.py' files found to validate.", "INFO")
        summary = f"Core Compiler Health Scan: {checks_passed}/{total_checks} checks passed."
        self.report(f"[DONE] {summary}", "SUCCESS" if checks_passed == total_checks else "WARN")
        return summary
    def _check_file_content(self, file_path, content_to_find):
        """Helper to check file content and return a preview on failure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content_to_find in content:
                    return True, None
                else:
                    preview = "\n".join(content.splitlines()[:5])
                    return False, preview
        except FileNotFoundError:
            self._register_finding(f"  [ERROR] -> File not found: {file_path}", "ERROR")
            return False, None
