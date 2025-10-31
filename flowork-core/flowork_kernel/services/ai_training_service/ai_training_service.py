#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\ai_training_service\ai_training_service.py JUMLAH BARIS 188 
#######################################################################

import os
import threading
import uuid
from ..base_service import BaseService
import sys
import tempfile
try:
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        Trainer,
        TrainingArguments,
        TextDataset,
        DataCollatorForLanguageModeling,
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
class AITrainingService(BaseService):
    """
    (REMASTERED V3) Manages the AI model fine-tuning process.
    Now correctly resolves model paths by querying the AIProviderManagerService.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        if not TRANSFORMERS_AVAILABLE:
            self.logger(
                "AITrainingService: CRITICAL - 'transformers' library not found. Fine-tuning will not be available.",
                "CRITICAL",
            )
        self.dataset_manager = self.kernel.get_service("dataset_manager_service")
        self.ai_manager = self.kernel.get_service("ai_provider_manager_service")
        self.training_jobs = {}
        self.job_lock = threading.Lock()
    def start_fine_tuning_job(
        self,
        base_model_id: str,
        dataset_name: str,
        new_model_name: str,
        training_args: dict,
    ):
        if not TRANSFORMERS_AVAILABLE:
            return {"error": "Transformers library is not installed."}
        if self.job_lock.locked():
            return {
                "error": "Another training job is already in progress. Please wait for it to complete."
            }
        if not self.ai_manager:
            return {
                "error": "AIProviderManagerService is not available to resolve model path."
            }
        model_info = self.ai_manager.local_models.get(f"(Local Model) {base_model_id}")
        if not model_info or not model_info.get("full_path"):
            return {
                "error": f"Base model '{base_model_id}' could not be found by the AI Manager."
            }
        model_full_path = model_info.get("full_path")
        self.job_lock.acquire()
        job_id = f"ft-{uuid.uuid4()}"
        self.training_jobs[job_id] = {
            "status": "QUEUED",
            "progress": 0,
            "message": "Job has been queued.",
            "base_model": base_model_id,
            "dataset": dataset_name,
            "new_model_name": new_model_name,
        }
        thread = threading.Thread(
            target=self._training_worker,
            args=(job_id, model_full_path, dataset_name, new_model_name, training_args),
            daemon=True,
        )
        thread.start()
        self.logger(
            f"Started fine-tuning job {job_id} for model '{new_model_name}'.", "INFO"
        )
        return {"job_id": job_id}
    def get_job_status(self, job_id: str):
        return self.training_jobs.get(job_id, {"error": "Job not found."})
    def _training_worker(
        self, job_id, base_model_path, dataset_name, new_model_name, training_args
    ):
        """The core worker function that runs the fine-tuning process."""
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        temp_log_path = os.path.join(
            tempfile.gettempdir(), f"flowork-train-{job_id}.log"
        )
        try:
            with open(temp_log_path, "w", encoding="utf-8") as log_file:
                sys.stdout = log_file
                sys.stderr = log_file
                self.training_jobs[job_id]["status"] = "PREPARING"
                self.training_jobs[job_id]["message"] = "Preparing dataset and paths..."
                output_dir = os.path.join(
                    self.kernel.project_root_path, "ai_models", "text", new_model_name
                )
                model_to_load_path = ""
                if os.path.isdir(output_dir):
                    self.logger(
                        f"Continue training existing model: '{new_model_name}'", "WARN"
                    )
                    model_to_load_path = output_dir
                else:
                    self.logger(
                        f"Starting new training from base model at: '{base_model_path}'",
                        "INFO",
                    )
                    model_to_load_path = base_model_path
                if not os.path.isdir(model_to_load_path):
                    raise FileNotFoundError(
                        f"Base model directory not found: {model_to_load_path}"
                    )
                dataset_data = self.dataset_manager.get_dataset_data(dataset_name)
                if not dataset_data:
                    raise ValueError(f"Dataset '{dataset_name}' is empty or not found.")
                temp_folder = os.path.join(self.kernel.data_path, "temp_training_files")
                hf_cache_dir = os.path.join(self.kernel.data_path, "hf_cache")
                os.makedirs(temp_folder, exist_ok=True)
                os.makedirs(hf_cache_dir, exist_ok=True)
                os.environ["TRANSFORMERS_CACHE"] = hf_cache_dir
                temp_file_path = os.path.join(temp_folder, f"temp_train_{job_id}.txt")
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    for item in dataset_data:
                        f.write(f"{item['prompt']}\n{item['response']}\n")
                self.training_jobs[job_id][
                    "message"
                ] = "Loading base model and tokenizer..."
                tokenizer = AutoTokenizer.from_pretrained(model_to_load_path)
                model = AutoModelForCausalLM.from_pretrained(model_to_load_path)
                train_dataset = TextDataset(
                    tokenizer=tokenizer, file_path=temp_file_path, block_size=128
                )
                data_collator = DataCollatorForLanguageModeling(
                    tokenizer=tokenizer, mlm=False
                )
                training_arguments = TrainingArguments(
                    output_dir=output_dir,
                    num_train_epochs=training_args.get("epochs", 1),
                    per_device_train_batch_size=training_args.get("batch_size", 4),
                    save_steps=10_000,
                    save_total_limit=2,
                    logging_steps=100,
                )
                self.training_jobs[job_id]["status"] = "TRAINING"
                self.training_jobs[job_id]["message"] = "Fine-tuning in progress..."
                trainer = Trainer(
                    model=model,
                    args=training_arguments,
                    data_collator=data_collator,
                    train_dataset=train_dataset,
                )
                trainer.train()
                self.training_jobs[job_id]["message"] = "Saving final model..."
                trainer.save_model(output_dir)
                self.training_jobs[job_id]["status"] = "COMPLETED"
                self.training_jobs[job_id][
                    "message"
                ] = f"Fine-tuning complete. Model '{new_model_name}' saved/updated."
                self.logger(f"Job {job_id} completed successfully.", "SUCCESS")
        except Exception as e:
            error_msg = f"Training job {job_id} failed: {e}"
            self.logger(error_msg, "CRITICAL")
            self.training_jobs[job_id]["status"] = "FAILED"
            self.training_jobs[job_id]["message"] = str(e)
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            if os.path.exists(temp_log_path):
                with open(temp_log_path, "r", encoding="utf-8") as f:
                    training_log_content = f.read()
                if self.training_jobs[job_id]["status"] == "FAILED":
                    self.logger(
                        f"--- Full Training Log for Failed Job {job_id} ---\n{training_log_content}\n--- End of Log ---",
                        "DETAIL",
                    )
                os.remove(temp_log_path)
            if "temp_file_path" in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            self.job_lock.release()
