import os
import subprocess
import threading
from typing import Optional, Callable

class FFmpegManager:
    def __init__(self, stream_dir="streams"):
        """
        Initialize FFmpeg Manager.
        :param stream_dir: Directory to store HLS stream files
        """
        self.stream_dir = stream_dir
        os.makedirs(self.stream_dir, exist_ok=True)
        self.processes = {}  # type: dict[str, subprocess.Popen]
        self.lock = threading.Lock()  # Ensure thread-safe access

    def start_stream(self, stream_id: str, rtsp_url: str, on_stop: Optional[Callable[[str], None]] = None) -> str:
        """
        Start an FFmpeg process to convert RTSP to HLS.
        :param stream_id: Unique ID for stream
        :param rtsp_url: RTSP stream source URL
        :param on_stop: Optional callback(stream_id) when stream stops
        :return: HLS path (.m3u8)
        """
        output_dir = os.path.join(self.stream_dir, stream_id)
        os.makedirs(output_dir, exist_ok=True)
        hls_path = os.path.join(output_dir, "index.m3u8")

        with self.lock:
            if stream_id in self.processes:
                print(f"[INFO] Stream {stream_id} already running.")
                return hls_path

        command = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-c:a", "aac",
            "-f", "hls",
            "-hls_time", "2",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments",
            hls_path
        ]

        print(f"[INFO] Starting FFmpeg stream: {stream_id}")

        thread = threading.Thread(target=self._run_ffmpeg, args=(stream_id, command, on_stop), daemon=True)
        thread.start()

        return hls_path

    def _run_ffmpeg(self, stream_id: str, command: list, on_stop: Optional[Callable[[str], None]] = None):
        """
        Run FFmpeg command in a subprocess.
        """
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with self.lock:
            self.processes[stream_id] = process

        stdout, stderr = process.communicate()
        print(f"[FFmpeg {stream_id}] stopped.")
        print(stderr.decode())

        with self.lock:
            self.processes.pop(stream_id, None)

        if on_stop:
            try:
                on_stop(stream_id)
            except Exception as e:
                print(f"[FFmpeg {stream_id}] on_stop callback error: {e}")

    def stop_stream(self, stream_id: str) -> bool:
        """
        Stop an active FFmpeg process.
        :return: True if stopped, False if not running
        """
        with self.lock:
            process = self.processes.get(stream_id)
            if not process:
                return False

            print(f"[INFO] Stopping stream: {stream_id}")
            process.terminate()
            self.processes.pop(stream_id, None)
            return True

    def get_hls_path(self, stream_id: str) -> str:
        """
        Return the HLS stream path (.m3u8)
        """
        return os.path.join(self.stream_dir, stream_id, "index.m3u8")
