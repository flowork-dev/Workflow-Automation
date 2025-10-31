#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\modules\video_storyboard_stitcher_d5e6\processor.py JUMLAH BARIS 334 
#######################################################################

import os
import sys
import subprocess
from flowork_kernel.api_contract import BaseModule, IExecutable  # , IConfigurableUI
from flowork_kernel.utils.file_helper import sanitize_filename
import random
import uuid
import json
class VideoStoryboardStitcherModule(BaseModule, IExecutable):
    TIER = "architect"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.ffmpeg_path = self._find_ffmpeg()
        self.section_counter = 0
    def _find_ffmpeg(self):
        ffmpeg_executable = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = os.path.join(
            self.kernel.project_root_path, "vendor", "ffmpeg", "bin", ffmpeg_executable
        )
        if os.path.exists(path):
            return path
        return None
    def _run_ffmpeg_stitch(
        self,
        clip_list,
        output_path,
        status_updater,
        music_path=None,
        music_volume_percent=20,
        original_audio_mode="replace",
        original_audio_volume=20,
    ):  # ADDED: new parameters
        temp_list_path = os.path.join(
            self.kernel.data_path, f"concat_{uuid.uuid4()}.txt"
        )
        with open(temp_list_path, "w", encoding="utf-8") as f:
            for clip_path in clip_list:
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
        command = [
            self.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            temp_list_path,
        ]
        audio_filter_command = []
        if music_path and os.path.exists(music_path):
            status_updater("Adding background music...", "INFO")  # English Log
            command.extend(
                ["-i", music_path]
            )  # MODIFICATION: Changed stream_loop to input
            if original_audio_mode == "merge":
                self.logger("Audio mode: Merge", "DEBUG")  # English Log
                original_vol = int(original_audio_volume) / 100.0
                music_vol = int(music_volume_percent) / 100.0
                filter_complex = f"[0:a]volume={original_vol}[a_orig]; [1:a]volume={music_vol}[a_music]; [a_orig][a_music]amix=inputs=2:duration=longest[a_out]"
                command.extend(
                    [
                        "-filter_complex",
                        filter_complex,
                        "-map",
                        "0:v:0",
                        "-map",
                        "[a_out]",
                        "-shortest",
                    ]
                )
            else:  # Default to 'replace'
                self.logger("Audio mode: Replace", "DEBUG")  # English Log
                command.extend(["-map", "0:v:0", "-map", "1:a:0"])
                command.extend(["-shortest"])
                try:
                    volume_level = int(music_volume_percent) / 100.0
                    if (
                        volume_level > 0 and volume_level != 1.0
                    ):  # Only add filter if not default 100%
                        audio_filter_command = ["-af", f"volume={volume_level}"]
                except (ValueError, TypeError):
                    self.logger(
                        f"Invalid music volume '{music_volume_percent}'. Using default.",
                        "WARN",
                    )  # English Log
        else:
            command.extend(["-map", "0:v:0", "-map", "0:a?"])
        base_command_end = [
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-r",
            "30",
            output_path,
        ]
        command.extend(audio_filter_command)
        command.extend(base_command_end)
        try:
            creation_flags = (
                subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                creationflags=creation_flags,
            )
            self.logger(f"FFmpeg STDOUT: {result.stdout}", "DEBUG")  # English Log
            self.logger(f"FFmpeg STDERR: {result.stderr}", "DEBUG")  # English Log
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode, e.cmd, output=e.stdout, stderr=e.stderr
            )
        finally:
            if os.path.exists(temp_list_path):
                os.remove(temp_list_path)
    def execute(
        self, payload: dict, config: dict, status_updater, mode="EXECUTE", **kwargs
    ):  # ADD CODE
        if not self.ffmpeg_path:
            return {
                "payload": {"data": {"error": "FFmpeg is not available."}},
                "output_name": "error",
            }
        video_sections = config.get("video_sections", [])
        output_folder = config.get("output_folder")
        prefix = sanitize_filename(config.get("output_filename_prefix", "storyboard"))
        generation_mode = config.get("generation_mode", "match_largest")
        delete_after_use = config.get("delete_after_use", False)
        music_folder_path = config.get("music_folder_path")
        music_volume = config.get("music_volume_percent", 20)
        original_audio_mode = config.get("original_audio_mode", "replace")
        original_audio_volume = config.get("original_audio_volume", 20)
        all_music_files = []
        if music_folder_path and os.path.isdir(music_folder_path):
            all_music_files = [
                os.path.join(music_folder_path, f)
                for f in os.listdir(music_folder_path)
                if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))
            ]
            if not all_music_files:
                self.logger(
                    f"Music folder '{music_folder_path}' is provided but contains no valid audio files. Proceeding without music.",
                    "WARN",
                )  # English Log
        if not video_sections:
            return {
                "payload": {"data": {"error": "No video sections configured."}},
                "output_name": "error",
            }
        if not output_folder or not os.path.isdir(output_folder):
            return {
                "payload": {
                    "data": {"error": f"Output folder is invalid: {output_folder}"}
                },
                "output_name": "error",
            }
        if generation_mode == "match_largest":
            if delete_after_use:
                self.logger(
                    "'Delete after use' is incompatible with 'Maximize Quantity' mode and will be ignored.",
                    "WARN",
                )  # English Log
            result_payload = self._execute_match_largest(
                video_sections,
                output_folder,
                prefix,
                all_music_files,
                music_volume,
                original_audio_mode,
                original_audio_volume,
                status_updater,
            )  # MODIFIED: Pass music list
        else:  # limit_by_smallest
            result_payload = self._execute_limit_by_smallest(
                video_sections,
                output_folder,
                prefix,
                delete_after_use,
                all_music_files,
                music_volume,
                original_audio_mode,
                original_audio_volume,
                status_updater,
            )  # MODIFIED: Pass music list
        if "data" not in payload:
            payload["data"] = {}
        payload["data"].update(result_payload)
        return {"payload": payload, "output_name": "success"}
    def _execute_limit_by_smallest(
        self,
        sections,
        output_folder,
        prefix,
        delete_after_use,
        music_files_list,
        music_volume,
        original_audio_mode,
        original_audio_volume,
        status_updater,
    ):  # MODIFIED: Accept music list
        section_clip_pools = []
        min_clips = float("inf")
        for section in sections:
            path = section.get("path")
            if not path or not os.path.isdir(path):
                raise FileNotFoundError(
                    f"Folder for section '{section.get('name')}' not found."
                )
            clips = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.lower().endswith((".mp4", ".mov"))
            ]
            if not clips:
                raise ValueError(
                    f"Folder for section '{section.get('name')}' is empty."
                )
            random.shuffle(clips)
            section_clip_pools.append(clips)
            min_clips = min(min_clips, len(clips))
        status_updater(
            f"Found {min_clips} possible unique videos (limited by smallest folder).",
            "INFO",
        )
        all_stitched_videos = []
        for i in range(min_clips):
            status_updater(f"Generating video {i+1}/{min_clips}...", "INFO")
            clips_for_this_video = []
            for clip_pool in section_clip_pools:
                clip = clip_pool.pop(0)
                clips_for_this_video.append(clip)
            selected_music = (
                random.choice(music_files_list) if music_files_list else None
            )
            output_filename = f"{prefix}_{i+1:03d}.mp4"
            output_path = os.path.normpath(os.path.join(output_folder, output_filename))
            self._run_ffmpeg_stitch(
                clips_for_this_video,
                output_path,
                status_updater,
                music_path=selected_music,
                music_volume_percent=music_volume,
                original_audio_mode=original_audio_mode,
                original_audio_volume=original_audio_volume,
            )  # ADDED PARAMS
            all_stitched_videos.append(output_path)
            if delete_after_use:
                for clip_path in clips_for_this_video:
                    try:
                        os.remove(clip_path)
                        self.logger(
                            f"Deleted used clip: {os.path.basename(clip_path)}", "INFO"
                        )  # English Log
                    except OSError as e:
                        self.logger(
                            f"Failed to delete {clip_path}: {e}", "ERROR"
                        )  # English Log
        return {"stitched_video_paths": all_stitched_videos}
    def _execute_match_largest(
        self,
        sections,
        output_folder,
        prefix,
        music_files_list,
        music_volume,
        original_audio_mode,
        original_audio_volume,
        status_updater,
    ):  # MODIFIED: Accept music list
        pools = {}
        max_clips = 0
        for section in sections:
            path = section.get("path")
            if not path or not os.path.isdir(path):
                raise FileNotFoundError(
                    f"Folder for section '{section.get('name')}' not found."
                )
            clips = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.lower().endswith((".mp4", ".mov"))
            ]
            if not clips:
                raise ValueError(
                    f"Folder for section '{section.get('name')}' is empty."
                )
            pools[section["name"]] = {"original": clips, "current": clips.copy()}
            random.shuffle(pools[section["name"]]["current"])
            max_clips = max(max_clips, len(clips))
        status_updater(
            f"Will generate {max_clips} videos (matching largest folder).", "INFO"
        )
        all_stitched_videos = []
        for i in range(max_clips):
            status_updater(f"Generating video {i+1}/{max_clips}...", "INFO")
            clips_for_this_video = []
            for section in sections:
                section_pool = pools[section["name"]]
                if not section_pool["current"]:
                    self.logger(
                        f"Refilling pool for section '{section['name']}'.", "DEBUG"
                    )  # English Log
                    section_pool["current"] = section_pool["original"].copy()
                    random.shuffle(section_pool["current"])
                clip = section_pool["current"].pop(0)
                clips_for_this_video.append(clip)
            selected_music = (
                random.choice(music_files_list) if music_files_list else None
            )
            output_filename = f"{prefix}_{i+1:03d}.mp4"
            output_path = os.path.normpath(os.path.join(output_folder, output_filename))
            self._run_ffmpeg_stitch(
                clips_for_this_video,
                output_path,
                status_updater,
                music_path=selected_music,
                music_volume_percent=music_volume,
                original_audio_mode=original_audio_mode,
                original_audio_volume=original_audio_volume,
            )  # ADDED PARAMS
            all_stitched_videos.append(output_path)
        return {"stitched_video_paths": all_stitched_videos}
