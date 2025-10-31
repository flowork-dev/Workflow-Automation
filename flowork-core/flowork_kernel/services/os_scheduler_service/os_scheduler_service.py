#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\os_scheduler_service\os_scheduler_service.py JUMLAH BARIS 133 
#######################################################################

import sys
import subprocess
from datetime import datetime  # --- [PERBAIKAN] Import datetime untuk konversi timezone
import os
from ..base_service import BaseService
class OsSchedulerService(BaseService):
    """
    Service to interact with the operating system's native one-time task scheduler.
    Uses 'schtasks' on Windows and 'at' on Linux/macOS.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger("Service 'OsSchedulerService' initialized.", "DEBUG")
    def schedule_action(
        self, action_type: str, scheduled_dt: datetime, task_name: str
    ) -> bool:
        """
        Schedules a system action (shutdown or restart).
        Returns True on success, False on failure.
        """
        self.logger(
            f"Attempting to schedule '{action_type}' for {scheduled_dt} with task name '{task_name}'",
            "INFO",
        )
        try:
            if sys.platform == "win32":
                return self._schedule_windows(action_type, scheduled_dt, task_name)
            else:  # Linux and macOS
                return self._schedule_linux(action_type, scheduled_dt)
        except Exception as e:
            self.logger(f"Failed to schedule action '{action_type}': {e}", "CRITICAL")
            return False
    def cancel_task(self, task_name: str) -> bool:
        """
        Cancels a previously scheduled task.
        """
        self.logger(f"Attempting to cancel scheduled task: '{task_name}'", "WARN")
        try:
            if sys.platform == "win32":
                return self._cancel_windows(task_name)
            else:  # Linux and macOS, task_name is the job ID for 'at'
                return self._cancel_linux(task_name)
        except Exception as e:
            self.logger(f"Failed to cancel task '{task_name}': {e}", "ERROR")
            return False
    def _schedule_windows(
        self, action_type: str, scheduled_dt: datetime, task_name: str
    ) -> bool:
        flag = "/r" if action_type == "restart" else "/s"
        command = f"shutdown.exe {flag} /t 0"
        local_dt = scheduled_dt.astimezone()
        date_str = local_dt.strftime("%d/%m/%Y")
        time_str = local_dt.strftime("%H:%M")
        schtasks_command = [
            "schtasks",
            "/create",
            "/tn",
            task_name,
            "/tr",
            command,
            "/sc",
            "ONCE",
            "/sd",
            date_str,
            "/st",
            time_str,
            "/rl",
            "HIGHEST",
            "/f",
        ]
        try:
            result = subprocess.run(
                schtasks_command,
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            self.logger(
                f"schtasks command executed. Full command sent: '{' '.join(schtasks_command)}'. Output: {result.stdout}",
                "DEBUG",
            )
            return "SUCCESS" in result.stdout.upper()
        except subprocess.CalledProcessError as e:
            self.logger(
                f"schtasks command failed with exit code {e.returncode}. Stderr: {e.stderr}",
                "CRITICAL",
            )
            raise e
    def _cancel_windows(self, task_name: str) -> bool:
        schtasks_command = ["schtasks", "/delete", "/tn", task_name, "/f"]
        result = subprocess.run(
            schtasks_command,
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.logger(
            f"schtasks delete command executed. Output: {result.stdout}", "DEBUG"
        )
        return "SUCCESS" in result.stdout.upper()  # (COMMENT) Case-insensitive check
    def _schedule_linux(self, action_type: str, scheduled_dt: datetime) -> bool:
        flag = "-r" if action_type == "restart" else "-h"
        command_to_run = f"shutdown {flag} now"
        time_str = scheduled_dt.strftime("%H:%M %m%d%y")
        process = subprocess.Popen(
            ["at", time_str],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=command_to_run)
        if process.returncode != 0:
            self.logger(f"'at' command failed. Stderr: {stderr}", "ERROR")
            raise Exception(stderr)
        self.logger(f"'at' command successful. Output: {stderr}", "INFO")
        return True
    def _cancel_linux(self, task_name: str) -> bool:
        atrm_command = ["atrm", str(task_name)]
        result = subprocess.run(
            atrm_command, capture_output=True, text=True, check=True
        )
        self.logger(f"'atrm' command executed. Output: {result.stdout}", "DEBUG")
        return result.returncode == 0
