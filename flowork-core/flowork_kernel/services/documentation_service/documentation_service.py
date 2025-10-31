#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE https://github.com/FLOWORK-gif/FLOWORK
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\documentation_service\documentation_service.py
# JUMLAH BARIS : 79
#######################################################################

import os
import subprocess
import threading
from ..base_service import BaseService
import platform
import signal
class DocumentationService(BaseService):
    """
    A service that automatically runs 'mkdocs serve' in the background
    during development to provide live documentation.
    (FIXED V2) Now uses robust process management to ensure the mkdocs
    child process is terminated when the main application exits, even if
    the console window is closed abruptly.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.process = None
        self.dev_mode = self.kernel.is_dev_mode
        if not self.dev_mode:
            self.logger("DocumentationService: 'devmode.on' not found. Documentation server will not be started.", "INFO")
    def start(self):
        """Starts the mkdocs serve process in a background thread if in dev mode."""
        if not self.dev_mode:
            return
        project_root = self.kernel.project_root_path
        if not os.path.exists(os.path.join(project_root, 'mkdocs.yml')):
            self.logger("DocumentationService: mkdocs.yml not found. Skipping server start.", "WARN")
            return
        thread = threading.Thread(target=self._run_mkdocs_serve, daemon=True)
        thread.start()
    def _run_mkdocs_serve(self):
        """The actual worker that runs the subprocess with improved termination handling."""
        self.logger("DocumentationService: Starting 'mkdocs serve' in the background...", "INFO")
        command = ['poetry', 'run', 'mkdocs', 'serve']
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        try:
            self.process = subprocess.Popen(
                command,
                cwd=self.kernel.project_root_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=creation_flags # (DIPERBAIKI) Terapkan flag di sini
            )
            self.logger(f"DocumentationService: 'mkdocs serve' is running with PID: {self.process.pid}", "SUCCESS")
        except FileNotFoundError:
            self.logger("DocumentationService: 'poetry' command not found. Make sure you are in a Poetry environment.", "CRITICAL")
        except Exception as e:
            self.logger(f"DocumentationService: Failed to start 'mkdocs serve': {e}", "CRITICAL")
    def stop(self):
        """
        (DIPERBAIKI) Stops the mkdocs serve process more forcefully to prevent zombie processes.
        """
        if self.process and self.process.poll() is None:
            self.logger(f"DocumentationService: Stopping 'mkdocs serve' process (PID: {self.process.pid})...", "INFO")
            try:
                if platform.system() == "Windows":
                    self.process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=3)
                self.logger("DocumentationService: Process terminated gracefully.", "SUCCESS")
            except (ProcessLookupError, PermissionError):
                 self.logger("DocumentationService: Process was already gone before it could be stopped.", "INFO")
            except subprocess.TimeoutExpired:
                self.logger("DocumentationService: Process did not terminate in time, forcing kill.", "WARN")
                self.process.kill() # Cara paling sadis
            except Exception as e:
                self.logger(f"DocumentationService: An unexpected error occurred during shutdown: {e}", "ERROR")
