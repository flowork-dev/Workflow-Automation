#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\scheduler_manager_service\scheduler_manager_service.py JUMLAH BARIS 86 
#######################################################################

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime
from ..base_service import BaseService
class SchedulerManagerService(BaseService):
    """
    Manages all scheduling tasks (Cron Jobs) for Flowork.
    Uses APScheduler to run presets at specified times.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.scheduler = BackgroundScheduler(daemon=False)
        self.kernel.write_to_log("Service 'SchedulerManager' initialized.", "DEBUG") # English Log
    def start(self):
        """Starts the scheduler in the background."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                self.kernel.write_to_log("Background scheduler started successfully.", "SUCCESS") # English Log
        except Exception as e:
            self.kernel.write_to_log(f"Failed to start scheduler: {e}", "ERROR") # English Log
    def stop(self):
        """Stops the scheduler safely when the application closes."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.kernel.write_to_log("Background scheduler stopped successfully.", "INFO") # English Log
        except Exception as e:
            self.kernel.write_to_log(f"Failed to stop scheduler: {e}", "ERROR") # English Log
    def schedule_rule(self, rule_id, rule_data):
        """Adds or updates a scheduled job based on a trigger rule."""
        preset_name = rule_data.get("preset_to_run")
        config = rule_data.get("config", {})
        cron_string = config.get("cron_string")
        if not all([preset_name, cron_string]):
            self.kernel.write_to_log(f"Scheduled rule '{rule_id}' is incomplete (missing preset or cron string).", "WARN") # English Log
            return
        api_service = self.kernel.get_service("api_server_service")
        if not api_service:
            self.kernel.write_to_log(f"Cannot schedule job for rule '{rule_id}', ApiServerService not available.", "ERROR") # English Log
            return
        def job_wrapper():
            self.kernel.write_to_log(f"Executing scheduled job '{rule_id}' for preset '{preset_name}'.", "INFO") # English Log
            api_service.trigger_workflow_by_api(preset_name, initial_payload={"triggered_by": "scheduler", "rule_id": rule_id})
            self.kernel.write_to_log(f"Job '{rule_id}' finished. It will run again on its next schedule.", "INFO") # English Log
        try:
            self.scheduler.add_job(
                job_wrapper, # (MODIFIED) We schedule our new wrapper function.
                trigger=CronTrigger.from_crontab(cron_string),
                id=str(rule_id),
                name=f"Cron for preset: {preset_name}",
                replace_existing=True
            )
            self.kernel.write_to_log(f"Scheduled job '{rule_data.get('name')}' for preset '{preset_name}' added/updated successfully.", "SUCCESS") # English Log
        except ValueError as e:
             self.kernel.write_to_log(f"Invalid Cron String format for rule '{rule_data.get('name')}': {e}", "ERROR") # English Log
        except Exception as e:
            self.kernel.write_to_log(f"Failed to add scheduled job '{rule_id}': {e}", "ERROR") # English Log
    def remove_scheduled_rule(self, rule_id):
        """Removes a scheduled job from the scheduler."""
        try:
            self.scheduler.remove_job(str(rule_id))
            self.kernel.write_to_log(f"Scheduled job with ID '{rule_id}' removed successfully.", "INFO") # English Log
        except JobLookupError:
            self.kernel.write_to_log(f"Attempted to remove a scheduled job '{rule_id}' that does not exist.", "WARN") # English Log
        except Exception as e:
            self.kernel.write_to_log(f"Failed to remove scheduled job '{rule_id}': {e}", "ERROR") # English Log
    def get_next_run_time(self, job_id: str) -> datetime | None:
        """
        Gets the next execution time for a scheduled job.
        """
        try:
            for job in self.scheduler.get_jobs():
                if job.id == str(job_id):
                    return job.next_run_time
        except Exception as e:
            self.kernel.write_to_log(f"Error while searching for scheduled job '{job_id}': {e}", "ERROR") # English Log
        return None
