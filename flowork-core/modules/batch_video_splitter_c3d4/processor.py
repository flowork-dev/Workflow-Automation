#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\batch_video_splitter_c3d4\processor.py JUMLAH BARIS 200 
#######################################################################

import os
import sys
import subprocess
from flowork_kernel.api_contract import BaseModule, IExecutable, IDataPreviewer
from flowork_kernel.utils.file_helper import sanitize_filename
import uuid
class BatchVideoSplitterModule(BaseModule, IExecutable, IDataPreviewer):
    """
    Splits all video files in a source folder into smaller segments based on duration.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.ffmpeg_path = self._find_ffmpeg()
    def _find_ffmpeg(self):
        ffmpeg_executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = os.path.join(
            self.kernel.project_root_path, "vendor", "ffmpeg", "bin", ffmpeg_executable
        )
        if os.path.exists(path):
            return path
        self.logger(
            "FATAL: FFmpeg executable not found in vendor directory.", "CRITICAL"
        )  # English Log
        return None
    def execute(
        self, payload: dict, config: dict, status_updater, mode="EXECUTE", **kwargs
    ):
        if mode == "SIMULATE":
            status_updater("Simulating video split process.", "INFO")
            return {"payload": payload, "output_name": "success"}
        if not self.ffmpeg_path:
            error_msg = (
                "FFmpeg is not available. This module cannot function."  # English Log
            )
            if "data" not in payload:
                payload["data"] = {}
            payload["data"]["error"] = error_msg
            return {"payload": payload, "output_name": "error"}
        folder_pairs = config.get("folder_pairs", [])
        segment_duration = config.get("segment_duration", 3)
        if not folder_pairs:
            error_msg = (
                "No source/output folder pairs have been configured."  # English Log
            )
            if "data" not in payload:
                payload["data"] = {}
            payload["data"]["error"] = error_msg
            return {"payload": payload, "output_name": "error"}
        try:
            segment_duration = int(segment_duration)
            if segment_duration <= 0:
                raise ValueError(
                    "Segment duration must be a positive number."
                )  # English Log
        except (ValueError, TypeError):
            error_msg = "Segment duration must be a valid integer."  # English Log
            if "data" not in payload:
                payload["data"] = {}
            payload["data"]["error"] = error_msg
            return {"payload": payload, "output_name": "error"}
        all_results = []
        total_processed_all_jobs = 0
        total_segments_all_jobs = 0
        for i, pair in enumerate(folder_pairs):
            source_folder = pair.get("source")
            output_folder = pair.get("output")
            status_updater(
                f"Starting job {i+1}/{len(folder_pairs)}: Source '{os.path.basename(source_folder)}'",
                "INFO",
            )  # English Log
            if not source_folder or not os.path.isdir(source_folder):
                self.logger(
                    f"Job {i+1} skipped: Source folder not found or is not a directory: {source_folder}",
                    "WARN",
                )  # English Log
                all_results.append(
                    {
                        "source": source_folder,
                        "status": "skipped",
                        "reason": "Source not found",
                    }
                )
                continue
            if not output_folder:
                output_folder = os.path.join(source_folder, "split_output")
                self.logger(
                    f"Job {i+1}: Output folder not specified, using default: {output_folder}",
                    "WARN",
                )  # English Log
            os.makedirs(output_folder, exist_ok=True)
            video_files = [
                f
                for f in os.listdir(source_folder)
                if f.lower().endswith((".mp4", ".mov", ".mkv", ".avi"))
            ]
            if not video_files:
                self.logger(
                    f"Job {i+1}: No video files found in '{source_folder}'.", "WARN"
                )  # English Log
                all_results.append(
                    {
                        "source": source_folder,
                        "status": "skipped",
                        "reason": "No videos in source",
                    }
                )
                continue
            processed_count_job = 0
            total_segments_job = 0
            for j, filename in enumerate(video_files):
                status_updater(
                    f"Job {i+1} - Processing {j+1}/{len(video_files)}: {filename}",
                    "INFO",
                )  # English Log
                input_path = os.path.join(source_folder, filename)
                sanitized_base_name = sanitize_filename(os.path.splitext(filename)[0])
                output_pattern = os.path.join(
                    output_folder, f"{sanitized_base_name}_segment_%03d.mp4"
                )
                command = [
                    self.ffmpeg_path,
                    "-i",
                    input_path,
                    "-c",
                    "copy",
                    "-map",
                    "0",
                    "-segment_time",
                    str(segment_duration),
                    "-f",
                    "segment",
                    "-reset_timestamps",
                    "1",
                    output_pattern,
                ]
                try:
                    creation_flags = (
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                    subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,
                        creationflags=creation_flags,
                    )
                    segments_created = len(
                        [
                            f
                            for f in os.listdir(output_folder)
                            if f.startswith(f"{sanitized_base_name}_segment_")
                        ]
                    )
                    total_segments_job += segments_created
                    processed_count_job += 1
                except subprocess.CalledProcessError as e:
                    self.logger(
                        f"Failed to split video '{filename}'. FFmpeg error: {e.stderr}",
                        "ERROR",
                    )  # English Log
                    continue
            total_processed_all_jobs += processed_count_job
            total_segments_all_jobs += total_segments_job
            all_results.append(
                {
                    "source": source_folder,
                    "output": output_folder,
                    "status": "completed",
                    "files_processed": processed_count_job,
                    "segments_created": total_segments_job,
                }
            )
        status_updater(
            f"Batch split complete. Total files processed: {total_processed_all_jobs}, Total segments created: {total_segments_all_jobs}.",
            "SUCCESS",
        )  # English Log
        if "data" not in payload or not isinstance(payload["data"], dict):
            payload["data"] = {}
        payload["data"]["batch_results"] = all_results
        payload["data"]["total_files_processed"] = total_processed_all_jobs
        payload["data"]["total_segments_created"] = total_segments_all_jobs
        return {"payload": payload, "output_name": "success"}
    def get_data_preview(self, config: dict):
        """
        Provides a sample of what this module might output for the Data Canvas.
        """
        return [
            {
                "status": "preview_not_available",
                "reason": "Video processing is a live action.",
            }
        ]
