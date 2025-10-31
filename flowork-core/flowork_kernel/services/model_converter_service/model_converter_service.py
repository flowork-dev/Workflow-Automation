#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\model_converter_service\model_converter_service.py JUMLAH BARIS 138 
#######################################################################

import os
import threading
import uuid
import subprocess
import sys
from ..base_service import BaseService
class ModelConverterService(BaseService):
    """
    Manages the conversion of fine-tuned models to the GGUF format.
    [FIXED V2] Uses subprocess.run to prevent hangs from stdout pipe buffer overflow.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.conversion_jobs = {}
        self.job_lock = threading.Lock()
        self.llama_cpp_path = os.path.join(self.kernel.project_root_path, "vendor", "llama.cpp")
        self.is_ready = self._check_dependencies()
        if not self.is_ready:
            self.logger("ModelConverterService is NOT READY. Dependencies are missing. Please check the logs.", "CRITICAL")
        else:
            self.logger("ModelConverterService is ready. All dependencies found.", "SUCCESS")
    def _check_dependencies(self):
        self.logger("ModelConverterService: Checking for llama.cpp dependencies...", "INFO")
        convert_script_path = os.path.join(self.llama_cpp_path, "convert_hf_to_gguf.py")
        quantize_executable_path = os.path.join(self.llama_cpp_path, "build", "bin", "Release", "llama-quantize")
        if sys.platform == "win32" and not os.path.exists(quantize_executable_path):
            quantize_executable_path += ".exe"
        all_found = True
        if not os.path.exists(convert_script_path):
            self.logger(f"Dependency check FAILED: 'convert_hf_to_gguf.py' not found at '{convert_script_path}'.", "ERROR")
            all_found = False
        if not os.path.exists(quantize_executable_path):
            self.logger(f"Dependency check FAILED: 'llama-quantize' executable not found at '{quantize_executable_path}'. Make sure llama.cpp is compiled successfully.", "ERROR")
            all_found = False
        return all_found
    def start_requantize_job(self, source_gguf_path: str, output_gguf_name: str, quantize_method: str = "Q4_K_M"):
        if not self.is_ready:
            return {"error": "ModelConverterService is not ready. Check logs for llama.cpp dependencies."}
        if self.job_lock.locked():
            return {"error": "Another conversion or quantization job is already in progress."}
        job_id = f"requantize-{uuid.uuid4()}"
        self.conversion_jobs[job_id] = {
            "status": "QUEUED", "progress": 0, "message": "Re-quantization job has been queued.",
            "source_model": source_gguf_path, "output_name": output_gguf_name, "log": []
        }
        thread = threading.Thread(target=self._requantize_worker, args=(job_id, source_gguf_path, output_gguf_name, quantize_method), daemon=True)
        thread.start()
        self.logger(f"Started re-quantization job {job_id} for model '{os.path.basename(source_gguf_path)}'.", "INFO")
        return {"job_id": job_id}
    def start_conversion_job(self, source_model_folder: str, output_gguf_name: str, quantize_method: str = "Q4_K_M"):
        if not self.is_ready:
            return {"error": "ModelConverterService is not ready. Check application logs for details on missing dependencies (llama.cpp)."}
        if self.job_lock.locked():
            return {"error": "Another conversion job is already in progress. Please wait."}
        job_id = f"convert-{uuid.uuid4()}"
        self.conversion_jobs[job_id] = {
            "status": "QUEUED", "progress": 0, "message": "Job has been queued.",
            "source_model": source_model_folder, "output_name": output_gguf_name, "log": []
        }
        thread = threading.Thread(target=self._conversion_worker, args=(job_id, source_model_folder, output_gguf_name, quantize_method), daemon=True)
        thread.start()
        self.logger(f"Started model conversion job {job_id} for model '{source_model_folder}'.", "INFO")
        return {"job_id": job_id}
    def get_job_status(self, job_id: str):
        return self.conversion_jobs.get(job_id, {"error": "Job not found."})
    def _log_job_update(self, job_id, message, level="INFO"):
        self.logger(f"Job {job_id}: {message}", level)
        if job_id in self.conversion_jobs:
            self.conversion_jobs[job_id]['message'] = message
            self.conversion_jobs[job_id]['log'].append(message)
    def _run_subprocess(self, job_id, command):
        """ (MODIFIKASI) Uses subprocess.run to prevent hangs from pipe buffer overflow. """
        self.logger(f"Executing command for job {job_id}: {' '.join(command)}", "DETAIL")
        process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        for line in process.stdout.splitlines():
            self._log_job_update(job_id, line, "DETAIL")
        if process.returncode != 0:
            self.logger(f"Subprocess for job {job_id} failed with stderr:\n{process.stderr}", "ERROR")
            raise subprocess.CalledProcessError(process.returncode, command, output=process.stdout, stderr=process.stderr)
    def _requantize_worker(self, job_id, source_gguf_path, output_gguf_name, quantize_method):
        self.job_lock.acquire()
        try:
            output_folder = os.path.dirname(source_gguf_path)
            final_gguf_path = os.path.join(output_folder, f"{output_gguf_name}.gguf")
            quantize_executable = os.path.join(self.llama_cpp_path, "build", "bin", "Release", "llama-quantize")
            if sys.platform == "win32" and not os.path.exists(quantize_executable):
                quantize_executable += ".exe"
            command_quantize = [quantize_executable, source_gguf_path, final_gguf_path, quantize_method]
            self.conversion_jobs[job_id]["status"] = "RUNNING"
            self._log_job_update(job_id, f"Quantizing model to {quantize_method}...")
            self._run_subprocess(job_id, command_quantize)
            self.conversion_jobs[job_id]["status"] = "COMPLETED"
            self._log_job_update(job_id, f"Quantization complete! Model saved to {final_gguf_path}", "SUCCESS")
        except Exception as e:
            self.conversion_jobs[job_id]["status"] = "FAILED"
            self._log_job_update(job_id, f"Quantization failed: {e}", "CRITICAL")
        finally:
            self.job_lock.release()
    def _conversion_worker(self, job_id, source_model_folder, output_gguf_name, quantize_method):
        self.job_lock.acquire()
        fp16_gguf_path = os.path.join(self.kernel.data_path, f"temp_fp16_{job_id}.gguf")
        try:
            source_model_path = os.path.join(self.kernel.project_root_path, "ai_models", "text", source_model_folder)
            output_folder = os.path.join(self.kernel.project_root_path, "ai_models")
            os.makedirs(output_folder, exist_ok=True)
            convert_script = os.path.join(self.llama_cpp_path, "convert_hf_to_gguf.py")
            if not os.path.exists(convert_script):
                raise FileNotFoundError("FATAL: llama.cpp convert_hf_to_gguf.py script not found.")
            command_convert = [sys.executable, convert_script, source_model_path, "--outfile", fp16_gguf_path, "--outtype", "f16"]
            self.conversion_jobs[job_id]["status"] = "RUNNING"
            self._log_job_update(job_id, "Step 1/2: Converting model to FP16 GGUF format...")
            self._run_subprocess(job_id, command_convert)
            quantize_executable = os.path.join(self.llama_cpp_path, "build", "bin", "Release", "llama-quantize")
            if sys.platform == "win32" and not os.path.exists(quantize_executable):
                quantize_executable += ".exe"
            if not os.path.exists(quantize_executable):
                raise FileNotFoundError("FATAL: llama.cpp quantize executable not found. Make sure you have compiled llama.cpp.")
            final_gguf_path = os.path.join(output_folder, f"{output_gguf_name}.gguf")
            command_quantize = [quantize_executable, fp16_gguf_path, final_gguf_path, quantize_method]
            self._log_job_update(job_id, f"Step 2/2: Quantizing model to {quantize_method}...")
            self._run_subprocess(job_id, command_quantize)
            self.conversion_jobs[job_id]["status"] = "COMPLETED"
            self._log_job_update(job_id, f"Conversion complete! Model saved to {final_gguf_path}", "SUCCESS")
        except Exception as e:
            self.conversion_jobs[job_id]["status"] = "FAILED"
            self._log_job_update(job_id, f"Conversion failed: {e}", "CRITICAL")
        finally:
            if os.path.exists(fp16_gguf_path):
                os.remove(fp16_gguf_path)
            self.job_lock.release()
