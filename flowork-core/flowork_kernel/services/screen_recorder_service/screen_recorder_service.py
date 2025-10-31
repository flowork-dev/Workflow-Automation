#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\screen_recorder_service\screen_recorder_service.py JUMLAH BARIS 147 
#######################################################################

import os
import threading
import time
import shutil
import wave
import pyaudio
import numpy as np
import mss
import subprocess
import tempfile
from ..base_service import BaseService
class ScreenRecorderService(BaseService):
    """
    Manages the screen and audio recording lifecycle.
    [V5] Added software-based audio gain (amplification).
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.is_recording = False
        self.temp_dir = None
        self.audio_thread = None
        self.video_thread = None
        self.current_gain = 1.0
        ffmpeg_executable = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        self.ffmpeg_path = os.path.join(self.kernel.project_root_path, "vendor", "ffmpeg", "bin", ffmpeg_executable)
    def start(self):
        self.kernel.write_to_log("Screen Recorder Service is ready.", "SUCCESS")
    def start_recording(self, monitor_num=1, record_audio=True, gain=1.0):
        if self.is_recording:
            self.kernel.write_to_log("Recording is already in progress.", "WARN")
            return False
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="flowork_rec_")
            self.kernel.write_to_log(f"Temporary recording directory created: {self.temp_dir}", "INFO")
            self.is_recording = True
            if record_audio:
                self.current_gain = gain # Store the gain for the audio worker
                self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
                self.audio_thread.start()
            else:
                self.kernel.write_to_log("Recording video only, as requested by user.", "INFO")
            self.video_thread = threading.Thread(target=self._capture_worker, args=(monitor_num,), daemon=True)
            self.video_thread.start()
            return True
        except Exception as e:
            self.kernel.write_to_log(f"Failed to start recording process: {e}", "CRITICAL")
            self.is_recording = False
            return False
    def stop_recording(self):
        if not self.is_recording: return None
        self.is_recording = False
        self.kernel.write_to_log("Stopping recording threads...", "INFO")
        if self.audio_thread: self.audio_thread.join(timeout=2)
        if self.video_thread: self.video_thread.join(timeout=2)
        self.kernel.write_to_log("Threads stopped. Starting final video merge...", "INFO")
        final_path = self._merge_with_ffmpeg()
        return final_path
    def _audio_worker(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        audio_file = os.path.join(self.temp_dir, 'output.wav')
        p = pyaudio.PyAudio()
        stream = None
        frames = []
        INT16_MAX = 32767
        try:
            stream = p.open(format=FORMAT,
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)
            self.kernel.write_to_log(f"PyAudio stream opened for default input device with gain: {self.current_gain}x", "INFO")
            while self.is_recording:
                data = stream.read(CHUNK)
                audio_as_np_int16 = np.frombuffer(data, dtype=np.int16)
                amplified_audio = audio_as_np_int16 * self.current_gain
                clipped_audio = np.clip(amplified_audio, -INT16_MAX, INT16_MAX)
                final_audio_bytes = clipped_audio.astype(np.int16).tobytes()
                frames.append(final_audio_bytes)
        except Exception as e:
            self.kernel.write_to_log(f"PyAudio recording failed: {e}", "ERROR")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            p.terminate()
            if frames:
                wf = wave.open(audio_file, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                self.kernel.write_to_log(f"Audio stream saved to {audio_file}", "SUCCESS")
    def _capture_worker(self, monitor_num):
        frame_rate = 15
        sleep_interval = 1 / frame_rate
        frame_count = 0
        with mss.mss() as sct:
            if monitor_num >= len(sct.monitors):
                self.kernel.write_to_log(f"Invalid monitor number {monitor_num}. Defaulting to primary.", "WARN")
                monitor_num = 1
            monitor = sct.monitors[monitor_num]
            while self.is_recording:
                screenshot = sct.grab(monitor)
                frame_path = os.path.join(self.temp_dir, f"frame_{frame_count:06d}.png")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=frame_path)
                frame_count += 1
                time.sleep(sleep_interval)
        self.kernel.write_to_log(f"Video capture finished. Total frames: {frame_count}", "INFO")
    def _merge_with_ffmpeg(self):
        output_filename = f"Flowork_Tutorial_{time.strftime('%Y%m%d_%H%M%S')}.mp4"
        default_save_path = os.path.join(os.path.expanduser("~"), "Videos", "Flowork Tutorials")
        save_path = self.loc.get_setting("recorder_save_path", default_save_path)
        os.makedirs(save_path, exist_ok=True)
        final_video_path = os.path.join(save_path, output_filename)
        audio_input = os.path.join(self.temp_dir, 'output.wav')
        video_input = os.path.join(self.temp_dir, 'frame_%06d.png')
        if not os.path.exists(audio_input):
            self.kernel.write_to_log("No audio file found, merging video only.", "WARN")
            cmd = [ self.ffmpeg_path, '-y', '-framerate', '15', '-i', video_input, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', final_video_path ]
        else:
            cmd = [ self.ffmpeg_path, '-y', '-framerate', '15', '-i', video_input, '-i', audio_input, '-c:v', 'libx264', '-c:a', 'aac', '-strict', 'experimental', '-shortest', '-pix_fmt', 'yuv420p', final_video_path ]
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, capture_output=True, text=True, startupinfo=startupinfo)
            self.kernel.write_to_log(f"Video merged successfully: {final_video_path}", "SUCCESS")
            return final_video_path
        except subprocess.CalledProcessError as e:
            self.kernel.write_to_log(f"FFmpeg merge failed: {e.stderr}", "ERROR")
            return None
        finally:
            if self.temp_dir and os.path.isdir(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.kernel.write_to_log(f"Cleaned up temp directory: {self.temp_dir}", "INFO")
