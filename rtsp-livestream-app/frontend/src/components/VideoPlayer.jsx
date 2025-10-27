

import React, { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { Button } from "@/components/ui/button";
import OverlayEditor from "./OverlayEditor";
import axios from "axios";

/**
 * VideoPlayer.jsx
 * - Plays HLS (.m3u8) stream generated from RTSP via backend.
 * - Allows start/stop of RTSP stream.
 * - Integrates OverlayEditor on top of video.
 */
export default function VideoPlayer() {
  const videoRef = useRef(null);
  const [rtspUrl, setRtspUrl] = useState("");
  const [hlsUrl, setHlsUrl] = useState(null);
  const [streamId] = useState("default");
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (hlsUrl && videoRef.current) {
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
        });
        hls.loadSource(hlsUrl);
        hls.attachMedia(videoRef.current);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log("HLS Manifest loaded, playing video...");
          videoRef.current.play();
          setPlaying(true);
        });
        return () => hls.destroy();
      } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
        videoRef.current.src = hlsUrl;
        videoRef.current.addEventListener("loadedmetadata", () => {
          videoRef.current.play();
          setPlaying(true);
        });
      } else {
        alert("HLS not supported in this browser.");
      }
    }
  }, [hlsUrl]);

  const startStream = async () => {
    if (!rtspUrl.trim()) {
      alert("Please enter an RTSP URL!");
      return;
    }
    try {
      const res = await axios.post("http://127.0.0.1:5000/start", {
        stream_id: streamId,
        rtsp_url: rtspUrl,
      });
      const hlsPath = res.data.hls_path.replace(/\\/g, "/");
      setHlsUrl(`http://127.0.0.1:5000/${hlsPath}`);
    } catch (err) {
      console.error("Error starting stream:", err);
      alert("Failed to start stream. Check your RTSP URL or FFmpeg setup.");
    }
  };

  const stopStream = async () => {
    try {
      await axios.post(`http://127.0.0.1:5000/stop/${streamId}`);
      setHlsUrl(null);
      setPlaying(false);
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.src = "";
      }
    } catch (err) {
      console.error("Error stopping stream:", err);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      {/* Header */}
      <h1 className="text-2xl font-bold mb-4 text-gray-700">
        🎥 RTSP Livestream Player
      </h1>

      {/* Input */}
      <div className="flex items-center gap-2 mb-4 w-[500px]">
        <input
          type="text"
          className="border border-gray-300 rounded p-2 flex-1"
          placeholder="Enter RTSP URL (e.g., rtsp://...)"
          value={rtspUrl}
          onChange={(e) => setRtspUrl(e.target.value)}
        />
        <Button onClick={startStream}>Start</Button>
        <Button
          variant="destructive"
          onClick={stopStream}
          disabled={!playing}
        >
          Stop
        </Button>
      </div>

      {/* Video Container */}
      <div className="relative w-[800px] h-[450px] bg-black rounded-lg overflow-hidden shadow-lg">
        <video
          ref={videoRef}
          controls
          autoPlay
          muted
          className="w-full h-full object-contain"
        />
        {/* Overlay editor (on top of video) */}
        {playing && <OverlayEditor videoRef={videoRef} />}
      </div>

      {/* Info */}
      <p className="mt-4 text-sm text-gray-500">
        Enter a valid RTSP URL (e.g., from <a href="https://www.rtsp.me" target="_blank" rel="noreferrer" className="text-blue-500 underline">rtsp.me</a>)  
        — the app converts it to HLS for browser playback.
      </p>
    </div>
  );
}
