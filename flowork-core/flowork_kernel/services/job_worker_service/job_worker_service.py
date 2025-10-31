import threading
import time
import json
import logging
from datetime import datetime

try:
    from app.models import ExecutionJob, db
    from app.extensions import sse_message_queue
except ImportError as e:
    logging.error(f"FATAL: JobWorkerService failed to import Gateway dependencies: {e}")
    db = None
    ExecutionJob = None
    sse_message_queue = None

try:
    from flowork_kernel.services.workflow_executor_service.workflow_executor_service import WorkflowExecutorService
except ImportError as e:
    logging.error(f"FATAL: JobWorkerService failed to import WorkflowExecutorService: {e}")
    WorkflowExecutorService = None

MAX_CONCURRENT_JOBS = 4

class JobWorkerService:

    def __init__(self, kernel, flask_app):
        self.kernel = kernel
        self.flask_app = flask_app # (English Hardcode) We need 'app' to create DB contexts
        self.running = False
        self.active_jobs = 0
        self.active_job_threads = {} # (English Hardcode) To track threads

        if WorkflowExecutorService:
            # (COMMENT) Do not create a new instance. Get the one the Kernel already loaded.
            # self.executor_service = WorkflowExecutorService(kernel) # <-- This was the FIRST error.

            # (FIX) Get the existing service from the kernel.
            self.executor_service = self.kernel.get_service("workflow_executor_service")

            # (COMMENT) This was the SECOND error. Kernel has no 'register_service' method.
            # (COMMENT) We don't need it. We will just use self.executor_service.
            # if self.executor_service:
            #    self.kernel.register_service("workflow_executor", self.executor_service) # <-- (FIX 2) Remove this error line
            # else:
            #    logging.error("JobWorkerService: CRITICAL - Could not get 'workflow_executor_service' from Kernel.")

        else:
            self.executor_service = None
            logging.error("JobWorkerService: WorkflowExecutorService not loaded.")

    def start(self):
        if not db or not self.executor_service:
            logging.error("JobWorkerService: DB or ExecutorService not found. Worker will not start.")
            return
        self.running = True
        logging.warning(f"Job Worker Service started. Max concurrency: {MAX_CONCURRENT_JOBS}")
        while self.running:
            if self.active_jobs < MAX_CONCURRENT_JOBS:
                try:
                    job = self._find_pending_job()
                    if job:
                        self.active_jobs += 1
                        t = threading.Thread(target=self._execute_job, args=(job,))
                        self.active_job_threads[job.id] = t
                        t.start()
                    else:
                        time.sleep(2) # (English Hardcode) Wait if no job
                except Exception as e:
                    logging.error(f"Error in job worker loop: {e}")
                    time.sleep(5)
            else:
                time.sleep(1) # (English Hardcode) Wait if job slots are full

    def stop(self):
        self.running = False
        logging.warning("Job Worker Service stopping...")

    def _find_pending_job(self):
        with self.flask_app.app_context():
            try:
                job = db.session.query(ExecutionJob).filter_by(status='pending') \
                    .order_by(ExecutionJob.created_at.asc()) \
                    .with_for_update(skip_locked=True).first()
                if job:
                    job.status = 'running'
                    job.started_at = datetime.utcnow()
                    db.session.commit()
                    return job
                return None
            except Exception as e:
                db.session.rollback()
                if "database is locked" not in str(e):
                    logging.error(f"Error _find_pending_job: {e}")
                return None

    def _execute_job(self, job):
        logging.warning(f"Starting execution for job: {job.id}")
        with self.flask_app.app_context():
            try:
                self._publish_update('job_started', job.to_dict())
                execution_result = self.executor_service.execute_workflow(
                    workflow_data=job.payload,
                    job_id=job.id,
                    user_id=job.user_id # (English Hardcode) Pass user_id for logging
                )
                job.status = 'success'
                job.completed_at = datetime.utcnow()
                db.session.commit()
                self._publish_update('job_success', job.to_dict())
            except Exception as e:
                logging.error(f"Execution job {job.id} FAILED: {e}", exc_info=True)
                db.session.rollback() # (English Hardcode) Rollback on error
                job = db.session.query(ExecutionJob).get(job.id)
                if job:
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    self._publish_update('job_failed', job.to_dict())
            finally:
                self.active_jobs -= 1
                if job.id in self.active_job_threads:
                    del self.active_job_threads[job.id]
                logging.warning(f"Finished execution for job: {job.id}. Active jobs: {self.active_jobs}")

    def _publish_update(self, event_type, data):
        if not sse_message_queue:
            logging.error("Cannot publish update, sse_message_queue is None.")
            return
        try:
            message = json.dumps({
                "event": event_type,
                "data": data,
                "user_id": data.get('user_id')
            })
            sse_message_queue.put(message)
        except Exception as e:
            logging.error(f"Failed to publish update to In-Memory Queue: {e}")