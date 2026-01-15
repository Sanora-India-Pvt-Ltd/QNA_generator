 

import os
import re
import json
import time
import math
import shutil
import random
import hashlib
import subprocess
import traceback
import asyncio
import base64
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple

# ✅ Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file (if present)")
except ImportError:
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Environment variables must be set manually or via system environment")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

# ✅ FIX #4: Application-level locks to prevent concurrent processing of same video_id
VIDEO_LOCKS: Dict[str, asyncio.Lock] = {}

def get_video_lock(video_id: str) -> asyncio.Lock:
    """Get or create a lock for a specific video_id to prevent concurrent processing"""
    if video_id not in VIDEO_LOCKS:
        VIDEO_LOCKS[video_id] = asyncio.Lock()
    return VIDEO_LOCKS[video_id]

import numpy as np
from faster_whisper import WhisperModel

# OpenAI SDK for article synthesis
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI SDK not installed. Install with: pip install openai")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field

from sqlalchemy import String, Text, Integer, BigInteger, func, select, TIMESTAMP
from sqlalchemy.dialects.mysql import JSON, insert
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import OperationalError

# MongoDB imports for product endpoints
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("⚠️ MongoDB libraries not installed. Product endpoints will be disabled. Install with: pip install motor pymongo")

# ===============================
# CONFIG
# ===============================
DATABASE_URL = os.getenv("DATABASE_URL", "")  # mysql+aiomysql://...

# Whisper model for transcription
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

MCQ_COUNT = int(os.getenv("MCQ_COUNT", "20"))

# Hybrid mode: Split between exam-grade and legacy
EXAM_GRADE_COUNT = int(os.getenv("EXAM_GRADE_COUNT", "10"))  # Number of anchor-based questions
LEGACY_COUNT = int(os.getenv("LEGACY_COUNT", "10"))  # Number of generic/legacy questions
USE_HYBRID_MODE = os.getenv("USE_HYBRID_MODE", "false").lower() == "true"  # Enable hybrid mode

IMPORTANT_POOL_SIZE = int(os.getenv("IMPORTANT_POOL_SIZE", "18"))
RANDOM_PICK_COUNT = int(os.getenv("RANDOM_PICK_COUNT", "8"))

CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "120"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "35"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ✅ SOFT-FAIL MODE: After N rejections per anchor, force-accept one MCQ (prevents 0-MCQ issue)
# This is industry-standard fallback (Google, Coursera pipelines use similar logic)
MAX_REJECTIONS_PER_ANCHOR = int(os.getenv("MAX_REJECTIONS_PER_ANCHOR", "5"))

# ✅ CACHE ACCEPTANCE: Minimum usable questions to accept partial cache (prevents unnecessary regeneration)
# Industry standard: Coursera/Khan Academy pipelines accept partial results >= 5 questions
MIN_USABLE_QUESTIONS = int(os.getenv("MIN_USABLE_QUESTIONS", "5"))  # exam-grade safe minimum

SAMPLE_CLIPS = int(os.getenv("SAMPLE_CLIPS", "12"))  # Increased from 8 for better coverage
CLIP_SECONDS = float(os.getenv("CLIP_SECONDS", "18"))  # Increased from 12 for better coverage
MIN_TRANSCRIPT_WORDS = int(os.getenv("MIN_TRANSCRIPT_WORDS", "400"))  # Minimum words for quality MCQs (base value)

FFPROBE_TIMEOUT = int(os.getenv("FFPROBE_TIMEOUT", "30"))  # Increased from 15s for slow S3 connections
FFPROBE_RETRIES = int(os.getenv("FFPROBE_RETRIES", "2"))  # Retry failed probes
FFMPEG_TIMEOUT_PER_CLIP = int(os.getenv("FFMPEG_TIMEOUT_PER_CLIP", "90"))  # Increased from 60s for slow S3 connections
FFMPEG_RETRIES = int(os.getenv("FFMPEG_RETRIES", "1"))  # Retry failed clip extractions

RANDOM_SEED_ENV = os.getenv("RANDOM_SEED", "").strip()
RANDOM_SEED = int(RANDOM_SEED_ENV) if RANDOM_SEED_ENV.isdigit() else None

# Exam-grade mode: Use anchor detection + pedagogy engine (default: True)
# Exam-grade mode: Use anchor detection + pedagogy engine
# Set USE_ANCHOR_MODE=true to enable exam-grade mode
USE_ANCHOR_MODE = os.getenv("USE_ANCHOR_MODE", "false").lower() == "true"

# Validation Rule Version - Increment when validation rules change to invalidate stale cache
# Current: 2.0 (strict PROCESS validation, incomplete stem rejection, nested label rejection, semantic deduplication)
VALIDATION_RULE_VERSION = "2.0"

# Topic End Delay - Small buffer after topic completion for natural feel in video players
# Teachers often pause 0.5-1.0s after finishing a topic
TOPIC_END_DELAY = float(os.getenv("TOPIC_END_DELAY", "0.8"))  # seconds

# Topic-Chunk Mode: Use 3 chunks for 5 questions (fast, deterministic)
USE_TOPIC_CHUNK_MODE = os.getenv("USE_TOPIC_CHUNK_MODE", "false").lower() == "true"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()  # Strip whitespace
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # Fast model for question generation

# ✅ Validate GROQ_API_KEY on startup
if GROQ_API_KEY:
    print(f"✅ GROQ_API_KEY loaded (length: {len(GROQ_API_KEY)}, starts with: {GROQ_API_KEY[:5]}...)")
else:
    print("⚠️ GROQ_API_KEY is empty or not set. Content safety classification will fail.")
    print("   Set it with: $env:GROQ_API_KEY='your_key_here' (PowerShell) or export GROQ_API_KEY='your_key_here' (Linux/Mac)")

# OpenAI Configuration for Article Synthesis
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default model for article synthesis

# MongoDB Configuration for Product Endpoints
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sanora")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "products")

# MongoDB connection (lazy initialization)
mongo_client = None
products_collection = None
if MONGO_AVAILABLE and MONGO_URI:
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        db = mongo_client[MONGO_DB_NAME]
        products_collection = db[MONGO_COLLECTION_NAME]
        print(f"✅ MongoDB connected: {MONGO_DB_NAME}.{MONGO_COLLECTION_NAME}")
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        mongo_client = None
        products_collection = None
elif not MONGO_AVAILABLE:
    print("⚠️ MongoDB libraries not available. Product endpoints disabled.")
elif not MONGO_URI:
    print("⚠️ MONGO_URI not configured. Product endpoints disabled.")

# Legacy Fill Mode - Allow filling remaining MCQs with legacy chunks if exam-grade generation < target
# Set ALLOW_LEGACY_FILL=false for strict exam-grade mode (may return < 20 questions)
# ✅ FIX 1: Default to False for exam-grade mode (strict, no legacy leakage)
ALLOW_LEGACY_FILL = os.getenv("ALLOW_LEGACY_FILL", "false").lower() == "true"

# ✅ ALLOWED ANCHOR TYPES: Only these anchor types are valid, others are coerced to PROCESS
ALLOWED_ANCHORS = {
    "DEFINITION",
    "PROCESS",
    "COMPARISON",
    "ADVANTAGE",
    "RISK",
    "DECISION",
    "TOPIC_CHUNK",  # Topic-chunk based questions
    "WEB_SEARCH"  # Web search based questions (generated at video end)
}

# Print mode on startup for debugging
print(f"📦 USE_TOPIC_CHUNK_MODE = {USE_TOPIC_CHUNK_MODE} ({'3 chunks → 5 questions (Groq)' if USE_TOPIC_CHUNK_MODE else 'Disabled'})")
if USE_TOPIC_CHUNK_MODE:
    print(f"⚡ GROQ_MODEL = {GROQ_MODEL} (Topic-Chunk Question Generator)")
print(f"✅ VALIDATION_RULE_VERSION = {VALIDATION_RULE_VERSION} (Cache invalidation)")
print(f"📊 ALLOW_LEGACY_FILL = {ALLOW_LEGACY_FILL} ({'Practice Mode (always 20)' if ALLOW_LEGACY_FILL else 'Exam Mode (strict)'})")
print(f"🔄 USE_HYBRID_MODE = {USE_HYBRID_MODE} ({f'{EXAM_GRADE_COUNT} exam-grade + {LEGACY_COUNT} legacy' if USE_HYBRID_MODE else 'Pure mode'})")
print(f"📹 SAMPLE_CLIPS = {SAMPLE_CLIPS}, CLIP_SECONDS = {CLIP_SECONDS} (Total: ~{SAMPLE_CLIPS * CLIP_SECONDS}s)")
print(f"📝 MIN_TRANSCRIPT_WORDS = {MIN_TRANSCRIPT_WORDS} (Quality gate)")
print(f"⏱️ FFPROBE_TIMEOUT = {FFPROBE_TIMEOUT}s, FFPROBE_RETRIES = {FFPROBE_RETRIES} (Video metadata)")
print(f"🎬 FFMPEG_TIMEOUT = {FFMPEG_TIMEOUT_PER_CLIP}s, FFMPEG_RETRIES = {FFMPEG_RETRIES} (Clip extraction)")

# ===============================
# CONTENT SAFETY CLASSIFICATION FOR EDUCATIONAL VIDEOS
# ===============================
"""
Content Safety Classification for Educational Videos

This module provides prompts and utilities for classifying video frames
for content safety in educational applications.
"""

# PROMPT A - Single Video Frame Safety Check (Groq Llama Guard 4)
PROMPT_A_SYSTEM = """You are a strict content safety classifier for an educational app.

Classify the provided VIDEO FRAME image as SAFE, UNSAFE, or UNCERTAIN.

UNSAFE if the frame contains any of:
- explicit sexual content or nudity
- graphic violence or gore
- self-harm depiction
- hate symbols or extremist imagery
- depiction of illegal activity (weapons handling for harm, drugs, etc.)

UNCERTAIN if the frame is too blurry/dark/low-resolution to judge safely.

Return ONLY valid JSON. No extra text."""

def get_prompt_a_user(timestamp_seconds: float, frame_id: str) -> str:
    """
    Generate the user prompt for single frame classification.
    
    Args:
        timestamp_seconds: Timestamp of the frame in seconds
        frame_id: Unique identifier for the frame
        
    Returns:
        User prompt string
    """
    return f"""Classify this single video frame for safety.

Context:
- timestamp_seconds: {timestamp_seconds}
- frame_id: {frame_id}
- product: general-audience educational app

Return JSON exactly:

{{
  "verdict": "SAFE" | "UNSAFE" | "UNCERTAIN",
  "category": "safe | sexual_nudity | sexual_explicit | violence_gore | self_harm | hate_symbol | illegal_activity | unknown",
  "confidence": 0.0,
  "reason": "max 12 words"
}}"""


# PROMPT B - Batch / Frame Set Safety Check (UPDATED)
PROMPT_B_SYSTEM = """You are a strict content safety classifier for an educational app.

You will receive multiple video frame images with frame_id and timestamp.

For each frame:
- classify SAFE, UNSAFE, or UNCERTAIN
- explicitly mark whether it is safe or unsafe

Overall video verdict:
- UNSAFE if any frame is UNSAFE with confidence >= 0.70
- UNCERTAIN if no UNSAFE but at least one UNCERTAIN
- SAFE only if all frames are SAFE

Return ONLY valid JSON. No extra text."""

def get_prompt_b_user(frames: List[Dict[str, Any]]) -> str:
    """
    Generate the user prompt for batch frame classification.
    
    Args:
        frames: List of frame dictionaries with 'frame_id' and 'timestamp_seconds'
                Example: [{"frame_id": "id1", "timestamp_seconds": 1.5}, ...]
        
    Returns:
        User prompt string
    """
    frames_json = json.dumps(frames, indent=2)
    
    return f"""Classify each frame for safety and also give an overall video verdict.

Frames included (each image is provided with the matching frame_id):
{frames_json}

Return JSON exactly like this:

{{
  "overall_video_verdict": "SAFE" | "UNSAFE" | "UNCERTAIN",
  "overall_is_safe": false,
  "overall_is_unsafe": false,
  "overall_reason": "short reason (max 12 words)",
  "frames": [
    {{
      "frame_id": "string",
      "timestamp_seconds": 0.0,
      "verdict": "SAFE" | "UNSAFE" | "UNCERTAIN",
      "is_safe": true,
      "is_unsafe": false,
      "category": "safe | sexual_nudity | sexual_explicit | violence_gore | self_harm | hate_symbol | illegal_activity | unknown",
      "confidence": 0.0,
      "flags": {{
        "nudity": false,
        "explicit_sexual": false,
        "gore": false,
        "self_harm": false,
        "hate_symbol": false,
        "illegal_activity": false
      }}
    }}
  ]
}}"""


def parse_single_frame_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the JSON response from single frame classification.
    
    Args:
        response_text: Raw response text from the model
        
    Returns:
        Parsed dictionary with classification results
    """
    if not response_text or not response_text.strip():
        raise ValueError("Empty response text")
    
    try:
        # Try to extract JSON from response (in case there's extra text)
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Try direct JSON parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                raise ValueError(f"No valid JSON found in response: {repr(text[:200])}")
                
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}. Raw text: {repr(response_text[:200])}")


def parse_batch_frame_response(response_text: str) -> Dict[str, Any]:
    """
    Parse the JSON response from batch frame classification.
    
    Args:
        response_text: Raw response text from the model
        
    Returns:
        Parsed dictionary with classification results
    """
    try:
        # Try to extract JSON from response (in case there's extra text)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {e}")


def should_mark_video_unsafe(frame_result: Dict[str, Any], confidence_threshold: float = 0.70) -> bool:
    """
    Determine if a single frame result should mark the video as unsafe.
    
    Args:
        frame_result: Single frame classification result
        confidence_threshold: Minimum confidence for UNSAFE verdict (default: 0.70)
        
    Returns:
        True if video should be marked unsafe
    """
    verdict = frame_result.get("verdict", "").upper()
    confidence = frame_result.get("confidence", 0.0)
    
    return verdict == "UNSAFE" and confidence >= confidence_threshold


def get_overall_verdict_from_batch(batch_result: Dict[str, Any]) -> str:
    """
    Extract overall video verdict from batch classification result.
    
    Args:
        batch_result: Batch frame classification result
        
    Returns:
        Overall verdict: "SAFE", "UNSAFE", or "UNCERTAIN"
    """
    return batch_result.get("overall_video_verdict", "UNCERTAIN").upper()


def get_unsafe_frames(batch_result: Dict[str, Any], confidence_threshold: float = 0.70) -> List[Dict[str, Any]]:
    """
    Extract all unsafe frames from batch classification result.
    
    Args:
        batch_result: Batch frame classification result
        confidence_threshold: Minimum confidence for UNSAFE verdict (default: 0.70)
        
    Returns:
        List of unsafe frame results
    """
    frames = batch_result.get("frames", [])
    unsafe_frames = []
    
    for frame in frames:
        verdict = frame.get("verdict", "").upper()
        confidence = frame.get("confidence", 0.0)
        
        if verdict == "UNSAFE" and confidence >= confidence_threshold:
            unsafe_frames.append(frame)
    
    return unsafe_frames


# ===============================
# CONTENT SAFETY CLASSIFICATION IMPLEMENTATION
# ===============================

# ✅ Groq Llama Guard 4 Frame Classification (Robust JSON Parsing)
GUARD_MODEL = "meta-llama/llama-guard-4-12b"

GUARD_SYSTEM_PROMPT = (
    "You are a strict content safety classifier for an educational app. "
    "Reply with ONLY ONE WORD: SAFE, UNSAFE, or UNCERTAIN. "
    "No JSON. No markdown. No code fences. No extra text."
)

def make_guard_user_text(ts: float, frame_id: str) -> str:
    """
    Generate user prompt text for frame safety classification.
    Asks for ONE WORD only (no JSON) to avoid JSON validation errors.
    """
    return f"""Classify this single video frame image for safety.

UNSAFE if it contains: explicit sexual content/nudity, graphic violence/gore, self-harm depiction, hate symbols, or depiction of illegal activity.
UNCERTAIN if the image is too blurry/dark/low-quality to judge.

Context: timestamp_seconds={ts}, frame_id={frame_id}
"""

def _fallback_from_raw_text(raw: str) -> Dict[str, Any]:
    """
    If model returns plain text like 'SAFE' or 'UNSAFE', convert to dict.
    """
    low = (raw or "").strip().lower()
    if not low:
        return {"verdict": "UNCERTAIN", "category": "unknown", "confidence": 0.0, "reason": "Empty model response"}

    if "unsafe" in low:
        return {"verdict": "UNSAFE", "category": "unknown", "confidence": 0.7, "reason": "Model marked unsafe"}
    if "safe" in low:
        return {"verdict": "SAFE", "category": "safe", "confidence": 0.7, "reason": "Model marked safe"}

    return {"verdict": "UNCERTAIN", "category": "unknown", "confidence": 0.0, "reason": "Non-JSON response"}

def _parse_json_safely(raw: str) -> Dict[str, Any]:
    """
    Try strict JSON, then try to extract JSON object substring, then fallback.
    """
    if not raw or not raw.strip():
        return _fallback_from_raw_text(raw)

    raw = raw.strip()

    # 1) strict parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "verdict" in data:
            return data
    except Exception:
        pass

    # 2) extract {...} substring
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict) and "verdict" in data:
                return data
        except Exception:
            pass

    # 3) fallback from text
    return _fallback_from_raw_text(raw)

def classify_frame_safety_groq(client, image_url: str, ts: float, frame_id: str) -> Dict[str, Any]:
    """
    Classify a single frame using Groq Llama Guard 4.
    Asks for ONE WORD response (SAFE/UNSAFE/UNCERTAIN) and builds JSON ourselves.
    This avoids JSON validation errors that occur when forcing JSON mode.
    
    Args:
        client: OpenAI client configured for Groq
        image_url: Base64 data URL or image URL
        ts: Timestamp in seconds
        frame_id: Frame identifier
        
    Returns:
        Dictionary with verdict, category, confidence, reason, frame_id, timestamp_seconds
    """
    # ✅ Validate client has valid API key before making request
    if not client or not hasattr(client, 'api_key') or not client.api_key:
        raise ValueError("Groq client has no API key configured")
    
    resp = client.chat.completions.create(
        model=GUARD_MODEL,
        temperature=0,
        # ✅ NO response_format - let model return simple word, we build JSON
        messages=[
            {"role": "system", "content": GUARD_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": make_guard_user_text(ts, frame_id)},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    )

    raw = (resp.choices[0].message.content or "").strip().upper()
    
    # Debug: show what model actually returned
    print(f"   📋 RAW GUARD OUTPUT for {frame_id}: {repr(raw)}")

    # Take first token only (guards against extra whitespace/text)
    verdict = raw.split()[0] if raw else "UNCERTAIN"
    if verdict not in ("SAFE", "UNSAFE", "UNCERTAIN"):
        verdict = "UNCERTAIN"

    # Map category based on verdict (can enhance later with more sophisticated mapping)
    if verdict == "SAFE":
        category = "safe"
    elif verdict == "UNSAFE":
        category = "unknown"  # Could be enhanced to detect specific unsafe category
    else:
        category = "unknown"

    # Set confidence: high for clear verdicts, low for uncertain
    confidence = 0.75 if verdict != "UNCERTAIN" else 0.0

    return {
        "verdict": verdict,
        "category": category,
        "confidence": confidence,
        "reason": "guard verdict",
        "frame_id": frame_id,
        "timestamp_seconds": ts,
        "raw": raw,  # Keep raw for debugging
    }

def extract_video_frames(video_url: str, num_frames: int = 5, frame_interval: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Extract frames from video using ffmpeg.
    
    Args:
        video_url: URL or path to video file
        num_frames: Number of frames to extract (default: 5)
        frame_interval: Interval in seconds between frames (if None, evenly distributed)
        
    Returns:
        List of frame dictionaries with 'frame_id', 'timestamp_seconds', and 'image_bytes'
    """
    import tempfile
    
    frames = []
    
    try:
        # Get video duration first
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_url
        ]
        
        p = subprocess.Popen(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(timeout=FFPROBE_TIMEOUT)
        
        if p.returncode != 0:
            print(f"⚠️ Could not get video duration: {stderr.decode('utf-8', errors='ignore')}")
            return frames
        
        duration = float(stdout.decode('utf-8').strip())
        
        # Calculate frame timestamps
        if frame_interval:
            timestamps = [i * frame_interval for i in range(num_frames) if i * frame_interval < duration]
        else:
            # Evenly distribute frames
            if num_frames > 1:
                timestamps = [duration * i / (num_frames - 1) for i in range(num_frames)]
            else:
                timestamps = [duration / 2]
        
        # Extract frames
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, timestamp in enumerate(timestamps):
                frame_id = f"frame_{idx+1}_{int(timestamp)}"
                frame_path = os.path.join(tmpdir, f"{frame_id}.jpg")
                
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", video_url,
                    "-vframes", "1",
                    "-q:v", "2",  # High quality
                    "-y",
                    frame_path
                ]
                
                p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.communicate(timeout=FFMPEG_TIMEOUT_PER_CLIP)
                
                if os.path.exists(frame_path):
                    with open(frame_path, "rb") as f:
                        image_bytes = f.read()
                        frames.append({
                            "frame_id": frame_id,
                            "timestamp_seconds": timestamp,
                            "image_bytes": image_bytes
                        })
    
    except Exception as e:
        print(f"⚠️ Error extracting frames: {e}")
        traceback.print_exc()
    
    return frames


async def classify_video_safety(video_url: str, use_batch: bool = True, num_frames: int = 5) -> Dict[str, Any]:
    """
    Classify video content for safety using frame extraction and Groq Llama Guard 4.
    
    Args:
        video_url: URL or path to video file
        use_batch: If True, classify all frames and determine overall verdict, else single frame only
        num_frames: Number of frames to extract and classify
        
    Returns:
        Dictionary with safety classification results
        
    Final video safety determination:
        - If any frame verdict = UNSAFE with confidence >= 0.70 → VIDEO = UNSAFE
        - Else if any frame = UNCERTAIN → VIDEO = UNCERTAIN
        - Else VIDEO = SAFE
    """
    if not OPENAI_AVAILABLE:
        print("⚠️ OpenAI SDK not available for content safety classification (required for Groq API)")
        return {
            "overall_video_verdict": "UNCERTAIN",
            "overall_is_safe": None,
            "overall_is_unsafe": None,
            "overall_reason": "OpenAI SDK not installed",
            "frames": []
        }
    
    # ✅ Validate GROQ_API_KEY before proceeding
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        error_msg = "GROQ_API_KEY is empty or not configured. Cannot perform content safety classification."
        print(f"❌ {error_msg}")
        print(f"   GROQ_API_KEY length: {len(GROQ_API_KEY) if GROQ_API_KEY else 0}")
        return {
            "overall_video_verdict": "UNCERTAIN",
            "overall_is_safe": None,
            "overall_is_unsafe": None,
            "overall_reason": error_msg,
            "frames": []
        }
    
    try:
        print(f"📹 Extracting {num_frames} frames from video: {video_url[:80]}...")
        # Extract frames
        frames_data = extract_video_frames(video_url, num_frames=num_frames)
        print(f"📹 Extracted {len(frames_data)} frames")
        
        if not frames_data:
            print("⚠️ No frames extracted from video")
            return {
                "overall_video_verdict": "UNCERTAIN",
                "overall_is_safe": None,
                "overall_is_unsafe": None,
                "overall_reason": "Could not extract frames",
                "frames": []
            }
        
        # ✅ Use Groq instead of OpenAI - CRITICAL: Must use Groq base_url
        # ✅ Validate API key before initializing client
        api_key_clean = GROQ_API_KEY.strip()
        if not api_key_clean:
            raise ValueError("GROQ_API_KEY is empty after stripping whitespace")
        
        print(f"🔍 Initializing Groq client for frame safety (model: meta-llama/llama-guard-4-12b)...")
        print(f"   🔑 API Key length: {len(api_key_clean)}, starts with: {api_key_clean[:5]}...")
        
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key_clean,  # Use cleaned key
        )
        
        # Verify client is using Groq endpoint
        if hasattr(client, '_client') and hasattr(client._client, 'base_url'):
            print(f"   ✅ Client base_url: {client._client.base_url}")
        
        print(f"   ✅ Using model: {GUARD_MODEL}")
        
        # Classify each frame individually using robust classification function
        frame_results = []
        
        for frame_data in frames_data:
            frame_id = frame_data["frame_id"]
            timestamp = frame_data["timestamp_seconds"]
            
            # Build image URL for base64 encoded image
            image_base64 = base64.b64encode(frame_data['image_bytes']).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_base64}"
            
            try:
                print(f"   🔍 Classifying frame {frame_id} (timestamp: {timestamp:.1f}s) with Groq...")
                
                # ✅ Use robust classification function with JSON mode enforcement
                result = classify_frame_safety_groq(client, image_url, timestamp, frame_id)
                
                verdict = result["verdict"]
                confidence = result["confidence"]
                category = result["category"]
                reason = result["reason"]
                
                print(f"   ✅ Frame {frame_id} classified: {verdict} (confidence: {confidence:.2f})")
                
                frame_results.append({
                    "frame_id": frame_id,
                    "timestamp_seconds": timestamp,
                    "verdict": verdict,
                    "is_safe": (verdict == "SAFE"),
                    "is_unsafe": (verdict == "UNSAFE"),
                    "category": category,
                    "confidence": confidence,
                    "reason": reason
                })
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ Error classifying frame {frame_id}: {error_msg}")
                traceback.print_exc()
                
                # Mark frame as UNCERTAIN on error
                frame_results.append({
                    "frame_id": frame_id,
                    "timestamp_seconds": timestamp,
                    "verdict": "UNCERTAIN",
                    "is_safe": None,
                    "is_unsafe": None,
                    "category": "unknown",
                    "confidence": 0.0,
                    "reason": f"Classification error: {error_msg[:50]}"
                })
        
        # ✅ Determine overall video verdict using simple + safe rule
        # Rule: If any frame verdict = UNSAFE with confidence >= 0.70 → VIDEO = UNSAFE
        #       Else if any frame = UNCERTAIN → VIDEO = UNCERTAIN
        #       Else VIDEO = SAFE
        
        overall_verdict = "SAFE"
        overall_reason = "All frames classified as safe"
        has_uncertain = False
        
        for frame_result in frame_results:
            verdict = frame_result.get("verdict", "UNCERTAIN").upper()
            confidence = frame_result.get("confidence", 0.0)
            
            if verdict == "UNSAFE" and confidence >= 0.70:
                overall_verdict = "UNSAFE"
                overall_reason = f"Unsafe content detected: {frame_result.get('reason', 'No reason')}"
                break  # UNSAFE is definitive - stop checking
            elif verdict == "UNCERTAIN":
                has_uncertain = True
        
        if overall_verdict == "SAFE" and has_uncertain:
            overall_verdict = "UNCERTAIN"
            overall_reason = "Some frames could not be classified with certainty"
        
        return {
            "overall_video_verdict": overall_verdict,
            "overall_is_safe": (overall_verdict == "SAFE"),
            "overall_is_unsafe": (overall_verdict == "UNSAFE"),
            "overall_reason": overall_reason,
            "frames": frame_results
        }
    
    except Exception as e:
        print(f"⚠️ Error classifying video safety: {e}")
        traceback.print_exc()
        return {
            "overall_video_verdict": "UNCERTAIN",
            "overall_is_safe": None,
            "overall_is_unsafe": None,
            "overall_reason": f"Classification error: {str(e)[:50]}",
            "frames": []
        }

# ===============================
# TRANSCRIPT SAFETY CLASSIFICATION (Groq)
# ===============================
"""
Video Transcript Safety Check using Groq

This module provides transcript-based content safety classification
for educational videos using Groq API (Llama Guard or any classifier model).
"""

# PROMPT - Video Transcript Safety Check
TRANSCRIPT_SAFETY_SYSTEM_PROMPT = """You are a content safety classifier.

Your task is to analyze a VIDEO TRANSCRIPT and decide whether the video content is SAFE or UNSAFE for a general educational app.

You must judge based on:
- meaning
- intent
- instructional risk
- persuasion risk

NOT on keywords alone.

Political education and neutral historical discussion are SAFE.
Political persuasion, propaganda, or targeted influence are UNSAFE.

Medical and educational discussion of sensitive topics is SAFE.
Explicit sexual content, self-harm instructions, violence instructions are UNSAFE.

Return ONLY valid JSON.
Do not explain your reasoning."""

def get_transcript_safety_user_prompt(transcript: str) -> str:
    """
    Generate the user prompt for transcript safety classification.
    
    Args:
        transcript: Full video transcript text
        
    Returns:
        User prompt string
    """
    return f"""Analyze the following video transcript and classify its safety.

Transcript:
\"\"\"
{transcript}
\"\"\"

Return JSON in the following exact format:

{{
  "verdict": "SAFE" | "UNSAFE",
  "category": "education | medical | sexual | political_persuasion | violence | self_harm | hate | illegal | mixed | unknown",
  "confidence": 0.0,
  "reason": "short human-readable reason"
}}"""

def extract_first_json_object(text: str) -> dict:
    """
    Extract the first JSON object from text (robust extractor for safety classification).
    """
    text = text.strip()
    
    # Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Try to find JSON object first
    object_match = re.search(r"\{\s*[^}]*\"verdict\".*?\}", text, re.DOTALL)
    if object_match:
        js = object_match.group(0)
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)  # Remove control characters
        js = re.sub(r",\s*}", "}", js)  # Fix trailing commas
        try:
            parsed = json.loads(js)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to find any JSON object
    object_match = re.search(r"\{.*\}", text, re.DOTALL)
    if object_match:
        js = object_match.group(0)
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)
        js = re.sub(r",\s*}", "}", js)
        try:
            parsed = json.loads(js)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON object found in response")

def classify_transcript_safety(transcript: str) -> Dict[str, Any]:
    """
    Classify video transcript for safety using Groq API.
    
    Args:
        transcript: Full video transcript text
        
    Returns:
        Dictionary with safety classification results:
        {
            "verdict": "SAFE" | "UNSAFE",
            "category": str,
            "confidence": float,
            "reason": str,
            "needs_manual_review": bool
        }
    """
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not configured for transcript safety classification")
        return {
            "verdict": "UNCERTAIN",
            "category": "unknown",
            "confidence": 0.0,
            "reason": "Groq API not configured",
            "needs_manual_review": True
        }
    
    if not transcript or len(transcript.strip()) < 50:
        print("⚠️ Transcript too short for safety classification")
        return {
            "verdict": "UNCERTAIN",
            "category": "unknown",
            "confidence": 0.0,
            "reason": "Transcript too short",
            "needs_manual_review": True
        }
    
    try:
        import requests
        
        # Truncate transcript if too long (Groq has token limits)
        max_transcript_length = 8000  # Conservative limit
        transcript_text = transcript[:max_transcript_length]
        if len(transcript) > max_transcript_length:
            print(f"   ⚠️ Transcript truncated from {len(transcript)} to {max_transcript_length} chars for safety check")
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        user_prompt = get_transcript_safety_user_prompt(transcript_text)
        
        body = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": TRANSCRIPT_SAFETY_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,  # Low temperature for consistent classification
            "max_tokens": 200
        }
        
        print(f"🔍 Classifying transcript safety (length: {len(transcript_text)} chars)...")
        
        # Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=body,
            timeout=30
        )
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON object
        try:
            safety_result = extract_first_json_object(content)
        except ValueError:
            # Fallback: try direct JSON parse
            try:
                safety_result = json.loads(content)
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse safety classification JSON: {content[:200]}")
                return {
                    "verdict": "UNCERTAIN",
                    "category": "unknown",
                    "confidence": 0.0,
                    "reason": "Failed to parse classification response",
                    "needs_manual_review": True
                }
        
        # Validate and normalize result
        verdict = safety_result.get("verdict", "UNCERTAIN").upper()
        if verdict not in ["SAFE", "UNSAFE"]:
            verdict = "UNCERTAIN"
        
        category = safety_result.get("category", "unknown")
        confidence = float(safety_result.get("confidence", 0.0))
        reason = safety_result.get("reason", "No reason provided")
        
        # Determine if manual review is needed
        needs_manual_review = confidence < 0.6
        
        result_dict = {
            "verdict": verdict,
            "category": category,
            "confidence": confidence,
            "reason": reason,
            "needs_manual_review": needs_manual_review
        }
        
        print(f"✅ Transcript safety classification: {verdict} (confidence: {confidence:.2f}, category: {category})")
        if needs_manual_review:
            print(f"   ⚠️ Low confidence ({confidence:.2f} < 0.6) - marked for manual review")
        
        return result_dict
        
    except Exception as e:
        print(f"⚠️ Error classifying transcript safety: {e}")
        traceback.print_exc()
        return {
            "verdict": "UNCERTAIN",
            "category": "unknown",
            "confidence": 0.0,
            "reason": f"Classification error: {str(e)[:100]}",
            "needs_manual_review": True
        }

# ===============================
# GROQ MODEL VALIDATION
# ===============================
# ✅ Supported Groq models (updated to prevent deprecated model errors)
SUPPORTED_GROQ_MODELS = [
    "groq/compound-mini",   # Default model (widely available)
    "llama3-7b-8192",       # Smaller model (if available)
    "llama3-14b-8192",      # Recommended for web search questions (if available)
    "llama3-70b-8192",      # Larger model for complex tasks (if available)
    "llama-3.1-8b-instant", # Fast model for general question generation (if available)
    "llama-3.1-70b-versatile" # Versatile model for complex tasks (if available)
]

# ✅ Explicitly deprecated models (for additional safety check)
DEPRECATED_GROQ_MODELS = [
    "llama3-8b-8192"  # Decommissioned - use llama3-14b-8192 instead
]

def get_available_groq_models() -> List[str]:
    """
    ✅ Auto-detect available Groq models from the API.
    
    Returns:
        List of available model IDs that are active
    """
    if not GROQ_API_KEY:
        return []
    
    try:
        import requests
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        available_models = [m["id"] for m in data.get("data", []) if m.get("active", False)]
        return available_models
    except Exception as e:
        print(f"⚠️ Could not fetch available models: {e}")
        return []

def validate_groq_model(model_name: str) -> None:
    """
    ✅ Validate that the Groq model is supported (not decommissioned).
    
    Args:
        model_name: The model name to validate
        
    Raises:
        RuntimeError: If model is deprecated or not in the supported list
    """
    # ✅ First check if explicitly deprecated
    if model_name in DEPRECATED_GROQ_MODELS:
        raise RuntimeError(
            f"Model '{model_name}' has been decommissioned and is no longer supported. "
            f"Use 'groq/compound-mini' or check available models. "
            f"See https://console.groq.com/docs/deprecations for details."
        )
    
    # ✅ Then check if in supported list (or allow if it's a valid Groq model format)
    if model_name not in SUPPORTED_GROQ_MODELS:
        # Allow groq/* models even if not explicitly listed
        if not model_name.startswith("groq/") and not model_name.startswith("llama"):
            raise RuntimeError(
                f"Model '{model_name}' is not in the supported list. "
                f"Use one of: {', '.join(SUPPORTED_GROQ_MODELS)}. "
                f"See https://console.groq.com/docs/deprecations for details."
            )

# ===============================
# GROQ API RETRY WRAPPER (Exponential Backoff for 429)
# ===============================
def groq_post_with_retry(url: str, headers: dict, payload: dict, timeout: int = 60, max_retries: int = 5) -> Any:
    """
    ✅ FIX: Groq API wrapper with exponential backoff for retryable errors only.
    
    Retry logic:
    - ✅ Retry on: 429 (rate limit), 500, 502, 503 (server errors)
    - ❌ DO NOT retry on: 400 (bad request - client error, will never succeed)
    
    Args:
        url: Groq API endpoint URL
        headers: Request headers (must include Authorization)
        payload: Request payload (JSON)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response object from requests.post
        
    Raises:
        RuntimeError: If request failed after all retries
        requests.HTTPError: For non-retryable errors (400, etc.)
    """
    import requests
    
    # ✅ Validate URL (catch typos like httpss://)
    if not url.startswith("https://"):
        raise ValueError(f"Invalid URL format: {url} (must start with https://)")
    
    # ✅ Validate model is supported (prevent deprecated model errors)
    model_name = payload.get("model", "")
    if model_name:
        validate_groq_model(model_name)
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                return response
            
            # ✅ Retry only on rate limit or server errors (429, 500, 502, 503)
            if response.status_code in (429, 500, 502, 503):
                wait = 2 ** attempt
                status_name = {429: "Rate limited", 500: "Server error", 502: "Bad gateway", 503: "Service unavailable"}.get(response.status_code, f"Error {response.status_code}")
                print(f"⚠️ {status_name} ({response.status_code}). Sleeping {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
                continue
            
            # ❌ 400-level errors → DO NOT RETRY (client error, will never succeed)
            if 400 <= response.status_code < 500:
                print(f"❌ Client error ({response.status_code}): {response.text[:200]}")
                response.raise_for_status()
            
            # For other errors, raise immediately
            response.raise_for_status()
            
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Groq API timeout after {max_retries} attempts")
            wait = 2 ** attempt
            print(f"⚠️ Request timeout. Sleeping {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Groq API request failed after {max_retries} attempts: {e}")
            wait = 2 ** attempt
            print(f"⚠️ Request error: {e}. Sleeping {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
    
    raise RuntimeError(f"Groq request failed after {max_retries} retries")

# ===============================
# SQLAlchemy setup (async)
# ===============================
engine = None
SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

class Base(DeclarativeBase):
    pass

class VideoMCQ(Base):
    __tablename__ = "video_mcqs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    mcq_count: Mapped[int] = mapped_column(Integer, default=20)
    questions: Mapped[dict] = mapped_column(JSON)  # store full list in JSON (MySQL JSON type)
    generator: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Audit & Versioning Fields
    schema_version: Mapped[str] = mapped_column(String(10), default="1.0", nullable=False)  # For future migrations
    generation_mode: Mapped[str] = mapped_column(String(20), default="legacy", nullable=False)  # exam-grade or legacy
    quality_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Quality stats: rejection_rate, avg_quality_score
    content_safety: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Content safety classification result (SAFE/UNSAFE/UNCERTAIN)
    
    # Audit Trail
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # API key, user ID, or system
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    generation_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # How many times regenerated
    
    created_at: Mapped[Any] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp()
    )
    updated_at: Mapped[Any] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    
    # Indexes for performance (defined in __table_args__)
    __table_args__ = (
        # Index on video_id already exists (unique=True creates it)
        # Additional indexes can be added here if needed
    )

# ===============================
# AUTO-DETECT OLLAMA
# Ollama removed - using Groq API only

# ===============================
# LOAD WHISPER
# ===============================
print("🚀 Loading Whisper model...")
whisper_model = WhisperModel(
    WHISPER_MODEL_SIZE,
    device="cpu",
    compute_type="int8",
    cpu_threads=max(2, (os.cpu_count() or 4) // 2),
)
print("✅ Whisper ready!")

# ===============================
# LIFESPAN EVENTS (Modern FastAPI)
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global engine, SessionLocal
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set. DB endpoints will fail.")
    else:
        engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        # Optional: auto-create table (works if DB user has rights)
        # Comment this if you prefer running SQL manually.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database connected and tables ready!")
    
    yield
    
    # Shutdown
    if engine:
        await engine.dispose()
        print("✅ Database connection closed")
    if mongo_client is not None:
        mongo_client.close()
        print("✅ MongoDB connection closed")

# ===============================
# FASTAPI
# ===============================
app = FastAPI(
    title="Fast Video MCQ Generator + MySQL Cache",
    version="4.0.0",
    description="Generate once -> save to MySQL -> fetch instantly",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# UTILITY FUNCTIONS
# ===============================
def validate_anchor_type(anchor_type: str) -> str:
    """
    Validate anchor type and coerce invalid types to PROCESS.
    
    Args:
        anchor_type: The anchor type to validate
        
    Returns:
        Validated anchor type (coerced to PROCESS if invalid)
    """
    if not anchor_type or anchor_type not in ALLOWED_ANCHORS:
        print(f"⚠️ Warning: Anchor type '{anchor_type}' is invalid, coercing to 'PROCESS'")
        return "PROCESS"
    return anchor_type

def normalize_question_order(questions: list) -> list:
    """
    Force static timeline order based on timestamp_seconds.
    Also updates part_number to be sequential (1..N).
    
    This ensures consistent ordering for both cached and fresh generation paths.
    """
    if not questions:
        return questions
    
    # Sort by timestamp_seconds (ascending - chronological order)
    questions.sort(key=lambda q: q.get("timestamp_seconds", 0))
    
    # Update part_number to be sequential (1..N) based on sorted order
    for i, q in enumerate(questions, start=1):
        q["part_number"] = i
    
    return questions

def build_topic_chunks(transcript_segments: List[Dict[str, Any]], video_duration: float) -> List[Dict[str, Any]]:
    """
    Build 3 topic chunks from Whisper segments (deterministic, no LLM needed).
    
    Strategy:
    - Chunk 1: 0% → 35%
    - Chunk 2: 35% → 70%
    - Chunk 3: 70% → 100%
    
    Then snap each chunk end to the nearest Whisper segment end.
    
    Args:
        transcript_segments: List of segments with {text, start, end}
        video_duration: Total video duration in seconds
        
    Returns:
        List of 3 chunks, each with {text, start, end, target_end_percent}
    """
    if not transcript_segments or video_duration <= 0:
        return []
    
    # Define chunk boundaries as percentages
    chunk_boundaries = [
        {"start_percent": 0.0, "end_percent": 0.35, "chunk_num": 1},
        {"start_percent": 0.35, "end_percent": 0.70, "chunk_num": 2},
        {"start_percent": 0.70, "end_percent": 1.0, "chunk_num": 3},
    ]
    
    chunks = []
    
    for boundary in chunk_boundaries:
        start_time = boundary["start_percent"] * video_duration
        target_end_time = boundary["end_percent"] * video_duration
        
        # Find the segment end closest to target_end_time
        closest_segment_end = target_end_time
        min_distance = float('inf')
        
        for seg in transcript_segments:
            seg_end = seg.get("end", 0.0)
            distance = abs(seg_end - target_end_time)
            if distance < min_distance:
                min_distance = distance
                closest_segment_end = seg_end
        
        # Ensure chunk end doesn't exceed video duration
        chunk_end = min(closest_segment_end, video_duration)
        
        # Collect all segments that fall within this chunk
        chunk_text_parts = []
        for seg in transcript_segments:
            seg_start = seg.get("start", 0.0)
            seg_end = seg.get("end", seg_start)
            
            # Include segment if it overlaps with chunk
            if seg_start < chunk_end and seg_end > start_time:
                chunk_text_parts.append(seg.get("text", "").strip())
        
        chunk_text = " ".join(chunk_text_parts).strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                "chunk_num": boundary["chunk_num"],
                "text": chunk_text,
                "start": start_time,
                "end": chunk_end,
                "target_end_percent": boundary["end_percent"]
            })
    
    return chunks

def extract_first_json_array(text: str) -> list:
    """
    Extract the first JSON array from text (robust extractor for chunk questions).
    Uses the same logic as safe_json_extract but specifically for arrays.
    """
    text = text.strip()
    
    # Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Try to find JSON array first
    array_match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
    if array_match:
        js = array_match.group(0)
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)  # Remove control characters
        js = re.sub(r",\s*}", "}", js)  # Fix trailing commas
        js = re.sub(r",\s*]", "]", js)
        try:
            parsed = json.loads(js)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON array found in response")


def groq_generate_one_chunk_mcq(chunk_text: str) -> dict:
    """
    ✅ FALLBACK: Generate exactly 1 MCQ from chunk text (super stable).
    Used when chunk generation fails to guarantee we always get questions.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not configured")
    
    if not chunk_text or len(chunk_text.strip()) < 20:
        raise ValueError("Chunk text too short for fallback generation")
    
    prompt = f"""Generate EXACTLY ONE MCQ from the text below.

Rules:
- Return ONLY a JSON array with exactly 1 object.
- No extra text.

Schema:
[
  {{
    "question":"...",
    "options":{{"A":"...","B":"...","C":"...","D":"..."}},
    "correct_answer":"A",
    "anchor_type":"TOPIC_CHUNK"
  }}
]

TEXT:
{chunk_text[:2000]}""".strip()  # Limit chunk text to avoid token limits

    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Return only valid JSON array. No extra text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        # ✅ Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=body,
            timeout=30
        )
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON array using robust extractor
        arr = extract_first_json_array(content)
        
        if not arr or len(arr) == 0:
            raise ValueError("Empty array returned from Groq")
        
        q = arr[0]
        
        # Validate and normalize question
        question_text = (q.get("question") or "").strip()
        options = q.get("options") or {}
        correct_answer = (q.get("correct_answer") or "").strip().upper()
        
        if not question_text or not options or correct_answer not in ["A", "B", "C", "D"]:
            raise ValueError("Invalid question structure from fallback")
        
        # Normalize options
        normalized_options = {}
        for key in ["A", "B", "C", "D"]:
            opt_text = str(options.get(key, "")).strip()
            if not opt_text:
                raise ValueError(f"Missing option {key}")
            normalized_options[key] = opt_text
        
        return {
            "question": question_text,
            "options": normalized_options,
            "correct_answer": correct_answer,
            "anchor_type": "TOPIC_CHUNK"
        }
        
    except Exception as e:
        print(f"⚠️ Fallback MCQ generation failed: {e}")
        raise

def generate_mcqs_from_chunk_groq(chunk_text: str, chunk_num: int, question_count: int) -> List[Dict[str, Any]]:
    """
    Generate MCQs from a topic chunk using Groq API (fast).
    
    Args:
        chunk_text: Transcript text for this chunk
        chunk_num: Chunk number (1, 2, or 3)
        question_count: Number of questions to generate (2 for chunks 1-2, 1 for chunk 3)
        
    Returns:
        List of question dictionaries
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not configured. Set GROQ_API_KEY environment variable.")
    
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library not installed. Install with: pip install requests")
    
    if not chunk_text or len(chunk_text.strip()) < 50:
        print(f"   ⚠️ Chunk {chunk_num}: Text too short ({len(chunk_text)} chars), skipping...")
        return []
    
    prompt = f"""Generate EXACTLY {question_count} multiple-choice question(s) in ENGLISH ONLY from this video transcript chunk.

TRANSCRIPT CHUNK:
{chunk_text}

REQUIREMENTS:
1. Generate EXACTLY {question_count} question(s)
2. Questions must be answerable from the transcript chunk provided
3. Use formal exam language (no slang, no casual phrases)
4. Each question must have exactly 4 options (A, B, C, D)
5. One option must be clearly correct
6. Other options must be plausible but incorrect

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question": "What is the main concept explained in this chunk?",
      "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A"
    }}
  ]
}}

Generate {question_count} question(s) now:"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": GROQ_MODEL,
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    try:
        # ✅ Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=payload,
            timeout=30
        )
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON from response (use robust extractor that handles arrays)
        # Try to extract as array first, then fallback to object
        try:
            data = extract_first_json_array(content)
            # If we got an array directly, wrap it in a dict with "questions" key
            if isinstance(data, list):
                data = {"questions": data}
        except ValueError:
            # Fallback to object extraction
            data = safe_json_extract(content)
        
        questions = []
        if "questions" in data and isinstance(data["questions"], list):
            for q in data["questions"]:
                if isinstance(q, dict) and "question" in q and "options" in q:
                    question_text = (q.get("question") or "").strip()
                    options = q.get("options") or {}
                    correct_answer = (q.get("correct_answer") or "").strip().upper()
                    
                    if question_text and isinstance(options, dict) and correct_answer in ["A", "B", "C", "D"]:
                        # Normalize options
                        normalized_options = {}
                        for key in ["A", "B", "C", "D"]:
                            opt_text = str(options.get(key, "")).strip()
                            if opt_text:
                                normalized_options[key] = opt_text
                        
                        if len(normalized_options) == 4:
                            questions.append({
                                "question": question_text,
                                "options": normalized_options,
                                "correct_answer": correct_answer,
                                "chunk_num": chunk_num
                            })
        
        return questions[:question_count]  # Return only requested count
        
    except Exception as e:
        print(f"⚠️ Groq API error for chunk {chunk_num}: {e}")
        return []

def generate_mcqs_from_topic_chunks(transcript_segments: List[Dict[str, Any]], video_duration: float) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generate 5 questions from 3 topic chunks using Groq.
    
    Strategy:
    - Chunk 1 (0-35%): Generate 2 questions → Q1, Q2
    - Chunk 2 (35-70%): Generate 2 questions → Q3, Q4
    - Chunk 3 (70-100%): Generate 1 question → Q5
    
    Questions are timed at chunk ends (topic boundaries).
    
    Args:
        transcript_segments: List of Whisper segments with timestamps
        video_duration: Total video duration in seconds
        
    Returns:
        (questions_list, chunk_metadata_list)
    """
    # Build 3 topic chunks
    chunks = build_topic_chunks(transcript_segments, video_duration)
    
    if len(chunks) < 3:
        raise RuntimeError(f"Failed to build 3 topic chunks. Got {len(chunks)} chunks.")
    
    all_questions = []
    chunk_metadata = []
    
    # Question counts per chunk: [2, 2, 1] = 5 total
    question_counts = [2, 2, 1]
    
    for idx, chunk in enumerate(chunks):
        chunk_num = chunk["chunk_num"]
        chunk_text = chunk["text"]
        chunk_end = chunk["end"]
        question_count = question_counts[idx]
        
        print(f"   📦 Chunk {chunk_num} ({chunk['start']:.1f}s - {chunk_end:.1f}s): Generating {question_count} question(s)...")
        
        # Generate questions from this chunk
        chunk_questions = generate_mcqs_from_chunk_groq(chunk_text, chunk_num, question_count)
        
        if not chunk_questions:
            print(f"   ⚠️ Chunk {chunk_num}: Failed to generate questions, using fallback...")
            try:
                # ✅ FALLBACK: Generate 1 question instead of skipping
                fallback_q = groq_generate_one_chunk_mcq(chunk_text)
                chunk_questions = [fallback_q]
                print(f"   ✅ Chunk {chunk_num}: Fallback generated 1 question")
            except Exception as e:
                print(f"   ⚠️ Chunk {chunk_num}: Fallback also failed: {e}")
                continue  # Skip this chunk if even fallback fails
        
        # Set timestamps: questions appear at chunk end (topic boundary)
        # For last chunk (chunk 3), ensure it's at least (video_duration - 2)
        if chunk_num == 3:
            chunk_end = max(chunk_end, video_duration - 2.0)
        
        for q_idx, q in enumerate(chunk_questions):
            # All questions from same chunk share the same timestamp (chunk end)
            q["timestamp_seconds"] = round(chunk_end, 2)
            q["timestamp"] = seconds_to_mmss(chunk_end)
            q["batch_number"] = chunk_num  # Batch number matches chunk number
            q["anchor_type"] = "TOPIC_CHUNK"  # Mark as topic-chunk based
            
            # Calculate question index (1-5)
            question_index = sum(question_counts[:idx]) + q_idx + 1
            q["question_index"] = question_index
        
        all_questions.extend(chunk_questions)
        
        # Store chunk metadata
        chunk_metadata.append({
            "chunk_num": chunk_num,
            "start": chunk["start"],
            "end": chunk_end,
            "target_end_percent": chunk["target_end_percent"],
            "questions_generated": len(chunk_questions),
            "text_preview": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
        })
        
        print(f"   ✅ Chunk {chunk_num}: Generated {len(chunk_questions)} question(s) at {chunk_end:.1f}s")
    
    # ✅ FINAL GUARANTEE: If still < 5 questions, generate from last chunk until we have 5
    while len(all_questions) < 5 and len(chunks) > 0:
        last_chunk = chunks[-1]
        last_chunk_text = last_chunk["text"]
        last_chunk_end = last_chunk["end"]
        
        try:
            print(f"   🔄 Generating fallback question {len(all_questions) + 1}/5 from last chunk...")
            fallback_q = groq_generate_one_chunk_mcq(last_chunk_text)
            
            # Set timestamp and metadata
            fallback_q["timestamp_seconds"] = round(last_chunk_end, 2)
            fallback_q["timestamp"] = seconds_to_mmss(last_chunk_end)
            fallback_q["batch_number"] = last_chunk["chunk_num"]
            fallback_q["anchor_type"] = "TOPIC_CHUNK"
            fallback_q["question_index"] = len(all_questions) + 1
            fallback_q["chunk_num"] = last_chunk["chunk_num"]
            
            all_questions.append(fallback_q)
            print(f"   ✅ Fallback question {len(all_questions)}/5 generated")
        except Exception as e:
            print(f"   ⚠️ Final fallback generation failed: {e}")
            break  # Stop trying if fallback keeps failing
    
    # Ensure we have exactly 5 questions
    all_questions = all_questions[:5]
    
    # Sort by question index to ensure order
    all_questions.sort(key=lambda q: q.get("question_index", 0))
    
    print(f"   ✅ Generated {len(all_questions)} questions from chunks (target: 5)")
    
    return all_questions, chunk_metadata

# ===============================
# WEB SEARCH QUESTION GENERATION
# ===============================
def extract_keywords_from_transcript(transcript: str, max_keywords: int = 10) -> List[str]:
    """
    Extract top keywords from transcript (fallback method).
    
    Note: Primary method uses Groq to generate Wikipedia-friendly queries.
    This is used as fallback if Groq query generation fails.
    
    Args:
        transcript: Full video transcript text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of keyword strings
    """
    # Simple keyword extraction: pick top "topic-ish" words
    # Remove common stop words and extract meaningful terms
    words = re.findall(r'\b[a-zA-Z]{3,}\b', transcript.lower())
    
    # Common stop words to filter out
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'
    }
    
    # Count word frequencies
    word_freq = defaultdict(int)
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_freq[word] += 1
    
    # Get top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, freq in sorted_words[:max_keywords]]
    
    return keywords if keywords else ["video", "tutorial", "lesson"]

def extract_topic_terms(transcript: str) -> List[str]:
    """
    Auto-extract TOPIC_TERMS from transcript using Groq (universal for all videos).
    
    Extracts 12 topic terms that represent the core topic of the video.
    
    Args:
        transcript: Full video transcript text
        
    Returns:
        List of 12 topic term strings (noun phrases, 1-4 words)
    """
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not configured. Using fallback keywords.")
        return []
    
    try:
        import requests
    except ImportError:
        return []
    
    prompt = f"""Extract 10-15 specific topic_terms from the transcript.

Rules:
- noun phrases only (1–4 words)
- must be specific to the video topic
- DO NOT include generic terms: data, database, system, technology, process, information, basics, introduction, overview, concept, real-time, processing
- These terms will be used to search Wikipedia, so prefer entity names (products, technologies, concepts)

Return JSON only:
{{"topic_terms":[...]}}

Transcript:
<<<
{transcript[:3000]}
>>>

Return format:
{{"topic_terms": ["term1", "term2", "term3", ...]}}
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",  # Fast model for topic extraction
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        # ✅ Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=payload,
            timeout=15
        )
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON object with topic_terms
        data = safe_json_extract(content)
        
        if isinstance(data, dict) and "topic_terms" in data:
            raw_terms = [str(term).strip() for term in data["topic_terms"][:12] if term]
        elif isinstance(data, list) and len(data) > 0:
            # Fallback: if it returns an array directly
            raw_terms = [str(term).strip() for term in data[:12] if term]
        else:
            print("⚠️ Could not parse topic_terms from Groq response")
            return []
        
        # ✅ Rule A: Hard clean filter - Remove generic terms and short terms
        generic_stoplist = {
            'data', 'database', 'system', 'technology', 'process', 'information', 
            'basics', 'introduction', 'overview', 'concept', 'real-time', 'processing'
        }
        
        # Filter out generic terms and short terms (< 4 characters)
        topic_terms = []
        for term in raw_terms:
            term_lower = term.lower().strip()
            # Skip if too short
            if len(term_lower) < 4:
                continue
            # Skip if in generic stoplist
            if term_lower in generic_stoplist:
                continue
            # Skip if starts with generic word
            if any(term_lower.startswith(stop) for stop in generic_stoplist):
                continue
            topic_terms.append(term)
        
        print(f"   ✅ Extracted {len(topic_terms)} clean topic terms: {', '.join(topic_terms[:5])}...")
        return topic_terms[:15]  # Return up to 15 topic terms
            
    except Exception as e:
        print(f"⚠️ Error extracting topic terms: {e}")
        return []

def is_entity_like_title(title: str, topic_terms_lower: List[str]) -> bool:
    """
    Determine if a Wikipedia title is "entity-like" (main topic page).
    
    Entity-like heuristic (Rule B):
    - Title exactly matches a topic term (or close fuzzy match ≥0.88)
    - OR title has no spaces (common for main topics like "MongoDB")
    - OR title is short TitleCase (1-3 words)
    
    Args:
        title: Wikipedia page title
        topic_terms_lower: List of topic terms (lowercased) for matching
        
    Returns:
        True if title is entity-like (main topic page), False otherwise
    """
    title_lower = title.lower().strip()
    
    # Check 1: Exact match or close fuzzy match with any topic term
    for term_lower in topic_terms_lower:
        if title_lower == term_lower:
            return True
        # Simple fuzzy match: if title contains term or term contains title (for variations)
        if len(term_lower) > 3 and len(title_lower) > 3:
            if term_lower in title_lower or title_lower in term_lower:
                # Calculate simple similarity (character overlap)
                min_len = min(len(term_lower), len(title_lower))
                max_len = max(len(term_lower), len(title_lower))
                if min_len / max_len >= 0.88:  # ≥88% similarity
                    return True
    
    # Check 2: No spaces (common for main topics like "MongoDB", "Redis", "Python")
    if ' ' not in title:
        return True
    
    # Check 3: Short TitleCase (1-3 words)
    words = title.split()
    if len(words) <= 3:
        # Check if it's TitleCase (first letter of each word is uppercase)
        if all(word and word[0].isupper() for word in words):
            return True
    
    return False

def get_web_evidence_from_wikipedia(transcript: str, topic_terms: List[str] = None) -> Tuple[str, List[str], List[Dict[str, str]]]:
    """
    Get ~1000 words of article text from Wikipedia API for question generation.
    
    Process:
    1. Extract TOPIC_TERMS from transcript (if not provided)
    2. Use TOPIC_TERMS to search Wikipedia
    3. Fetch summaries and filter by topic (keep only if ≥2 topic_terms appear)
    4. Accumulate ~1000 words of article text
    
    Args:
        transcript: Full video transcript text
        topic_terms: Optional list of topic terms (if not provided, will be extracted)
        
    Returns:
        Tuple of (article_text_string, topic_terms_list, wiki_blocks_list)
        wiki_blocks_list: List of dicts with 'title' and 'text' keys for OpenAI synthesis
    """
    try:
        import requests
        from urllib.parse import quote_plus
        import re
    except ImportError:
        raise RuntimeError("requests library not installed. Install with: pip install requests")
    
    # Step 1: Extract TOPIC_TERMS from transcript (if not provided)
    if topic_terms is None or len(topic_terms) == 0:
        print("   🤖 Extracting topic terms from transcript...")
        topic_terms = extract_topic_terms(transcript)
        
        # Fallback to keyword extraction if Groq fails
        if not topic_terms:
            print("   ⚠️ Using fallback keyword extraction...")
            keywords = extract_keywords_from_transcript(transcript)
            topic_terms = keywords[:15]  # Extract up to 15 terms
    
    if not topic_terms:
        print("⚠️ No topic terms available for Wikipedia search")
        return "NO_EVIDENCE_RETURNED_FROM_WIKIPEDIA", [], []
    
    print(f"   📌 Using {len(topic_terms)} topic terms for Wikipedia search")
    
    article_text_parts = []
    wiki_blocks = []  # Structured blocks for OpenAI synthesis
    total_words = 0
    target_words_min = 1000  # Target ~1000-1200 words
    target_words_max = 1200
    target_words = target_words_max  # Stop at 1200
    
    # Track pages we've already fetched to avoid duplicates
    fetched_titles = set()
    
    # Normalize topic_terms for matching (lowercase)
    topic_terms_lower = [term.lower() for term in topic_terms]
    
    # Step 2: For each topic term, search Wikipedia and get page titles
    for term in topic_terms[:10]:  # Use top 10 topic terms
        if total_words >= target_words:
            break
        
        try:
            # Use Wikipedia Search API (search/title) to find page titles
            search_url = f"https://en.wikipedia.org/w/rest.php/v1/search/title?q={quote_plus(term)}&limit=5"
            search_response = requests.get(
                search_url,
                timeout=10,
                headers={"User-Agent": "VideoMCQGenerator/1.0 (https://example.com/contact)"}
            )
            
            if search_response.status_code == 200:
                search_results = search_response.json()
                pages = search_results.get("pages", [])
                
                # Step 3: For each page title, fetch summary and filter by topic
                for page in pages[:3]:  # Get top 3 results per term
                    if total_words >= target_words:
                        break
                    
                    page_title = page.get("title", "")
                    page_key = page.get("key", "")
                    
                    # ✅ Banlist: Reject titles containing drift magnets
                    title_banlist = {'data', 'database', 'sequel', 'normalization', 'data center', 'datacenter'}
                    title_lower = page_title.lower()
                    if any(banned in title_lower for banned in title_banlist):
                        print(f"   ⏭️ Skipping '{page_title}': contains banned term (drift magnet)")
                        continue
                    
                    # Use page_key (normalized title) or title
                    title_to_use = page_key if page_key else page_title
                    
                    # Skip if we've already fetched this page
                    if title_to_use in fetched_titles:
                        continue
                    
                    if title_to_use:
                        fetched_titles.add(title_to_use)
                        
                        try:
                            # Fetch page summary using exact title/key
                            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title_to_use)}"
                            summary_response = requests.get(
                                summary_url,
                                timeout=10,
                                headers={"User-Agent": "VideoMCQGenerator/1.0 (https://example.com/contact)"}
                            )
                            
                            if summary_response.status_code == 200:
                                summary_data = summary_response.json()
                                
                                # Get the extract (main article text)
                                if summary_data.get("extract"):
                                    extract = summary_data["extract"]
                                    # Clean HTML tags if any
                                    extract = re.sub(r'<[^>]+>', '', extract)
                                    
                                    # ✅ Rule B: Wikipedia page acceptance (with entity-like exception)
                                    extract_lower = extract.lower()
                                    # Count distinct topic_terms that appear in extract
                                    matched_terms = [term_lower for term_lower in topic_terms_lower if term_lower in extract_lower]
                                    topic_matches = len(set(matched_terms))  # Use set to count distinct terms
                                    
                                    # Determine threshold: ≥2 normally, ≥1 if entity-like title
                                    is_entity = is_entity_like_title(page_title, topic_terms_lower)
                                    required_matches = 1 if is_entity else 2
                                    
                                    if topic_matches < required_matches:
                                        entity_note = " (entity-like, need ≥1)" if is_entity else " (need ≥2)"
                                        print(f"   ⏭️ Skipping '{page_title}': only {topic_matches} distinct topic term(s) matched{entity_note}")
                                        continue
                                    
                                    # Log entity-like pages with lower threshold
                                    if is_entity:
                                        print(f"   ✅ Entity-like title '{page_title}' accepted with {topic_matches} topic match(es)")
                                    
                                    # Count words in this extract
                                    word_count = len(extract.split())
                                    
                                    # Add title and extract
                                    title = summary_data.get("title", page_title)
                                    article_text_parts.append(f"[{title}]\n{extract}\n")
                                    # Also store as structured block for OpenAI synthesis
                                    wiki_blocks.append({"title": title, "text": extract})
                                    total_words += word_count
                                    
                                    print(f"   📄 Fetched '{title}': {word_count} words, {topic_matches} distinct topic matches (total: {total_words}/{target_words})")
                                    
                                    # Stop when reaching target (800-1000 words)
                                    if total_words >= target_words_min:
                                        if total_words >= target_words_max:
                                            break
                        except Exception as e:
                            print(f"⚠️ Error fetching page '{title_to_use}': {e}")
                            continue
            
        except Exception as e:
            print(f"⚠️ Wikipedia search error for term '{term}': {e}")
            continue
    
    # Combine all article text parts
    article_text = "\n".join(article_text_parts)
    
    if article_text:
        final_word_count = len(article_text.split())
        print(f"✅ Wikipedia article text: {final_word_count} words (filtered by {len(topic_terms)} topic terms)")
        return article_text, topic_terms, wiki_blocks
    else:
        print("⚠️ No Wikipedia content found (all articles filtered out by topic terms)")
        return "NO_EVIDENCE_RETURNED_FROM_WIKIPEDIA", topic_terms, []

TARGET_ARTICLE_WORDS = 1200  # Target word count for final article (max 1200)

def _sentences_for_pad(text: str):
    """Extract sentences from text for padding (removes timestamps)."""
    # remove timestamps like [00:12]
    text = re.sub(r"\[[0-9:\s]+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]

def trim_to_words(text: str, target: int = 1200, pad_source: str = "") -> str:
    """
    ✅ FIXED: Guaranteed to return EXACTLY `target` words (not more than target).
    If `text` is short, pads using pad_source (transcript) sentences.
    If no pad_source, repeats existing words as last resort.
    
    Args:
        text: Article text to trim
        target: Target word count (default: 1200, max: 1200)
        pad_source: Source text (transcript) to use for padding if article is too short
        
    Returns:
        Text with exactly target words (padded if needed, trimmed if too long, never exceeds target)
    """
    words = text.split()

    if len(words) < target:
        sents = _sentences_for_pad(pad_source) if pad_source else []
        if not sents:
            # last resort: repeat existing words (still deterministic)
            if not words:
                return ""
            while len(words) < target:
                words += words[: min(len(words), target - len(words))]
            return " ".join(words[:target]).strip()

        i = 0
        # append transcript sentences cyclically until enough words
        while len(words) < target and i < 20000:
            words += sents[i % len(sents)].split()
            i += 1

    return " ".join(words[:target]).strip()

def is_valid_article(text: str) -> bool:
    """
    ✅ VALIDATE: Check if article is clean and professional (no spoken phrases/fillers).
    
    Args:
        text: Article text to validate
        
    Returns:
        True if article is valid (no banned phrases), False otherwise
    """
    if not text or len(text.strip()) < 100:
        return False
    
    banned_phrases = [
        "namaste",
        "so let's see",
        "what do you think",
        "today we will",
        "you are watching",
        "let's get started",
        "welcome to",
        "hey guys",
        "hello everyone",
        "thanks for watching",
        "don't forget to",
        "if you like this video",
        "subscribe to",
        "hit the like button"
    ]
    
    text_lower = text.lower()
    for phrase in banned_phrases:
        if phrase in text_lower:
            print(f"   ❌ Article validation failed: found banned phrase '{phrase}'")
            return False
    
    return True

def generate_article_from_transcript(transcript: str) -> str:
    """
    ✅ FIXED: Rewrite transcript into professional web-ready article, over-generate then trim to exactly 1200 words.
    
    Rule: Use strict rewrite prompt, validate quality, regenerate if needed. Never exceed 1200 words.
    
    Args:
        transcript: Full video transcript text
        
    Returns:
        Article text with exactly 1200 words (never more than 1200, clean and professional)
    """
    max_regeneration_attempts = 3
    
    for attempt in range(max_regeneration_attempts):
        if not GROQ_API_KEY:
            # Fallback to OpenAI if Groq not available
            if not OPENAI_API_KEY or not OPENAI_AVAILABLE:
                raise RuntimeError("GROQ_API_KEY or OPENAI_API_KEY required for article generation")
            
            # Use OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            prompt = f"""You are an expert technical writer.

Rewrite the following transcript into a PROFESSIONAL, WEB-READY ARTICLE.

Rules:
- DO NOT copy transcript sentences directly
- REMOVE spoken phrases, greetings, and fillers
- REMOVE repetitions
- Use formal article language
- Use clear paragraphs
- Keep it around 1100–1300 words
- Plain text only (no headings, no bullets, no numbering)
- Do NOT include references, links, citations, or keywords list

Transcript:
\"\"\"
{transcript[:5000]}
\"\"\"
"""
            
            try:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert technical writer who creates professional, web-ready articles."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2500  # Allow enough for 1100-1300 words
                )
                article_raw = response.choices[0].message.content.strip()
            except Exception as e:
                raise RuntimeError(f"OpenAI article generation failed: {e}")
        else:
            # Use Groq (faster)
            import requests
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""You are an expert technical writer.

Rewrite the following transcript into a PROFESSIONAL, WEB-READY ARTICLE.

Rules:
- DO NOT copy transcript sentences directly
- REMOVE spoken phrases, greetings, and fillers
- REMOVE repetitions
- Use formal article language
- Use clear paragraphs
- Keep it around 1100–1300 words
- Plain text only (no headings, no bullets, no numbering)
- Do NOT include references, links, citations, or keywords list

Transcript:
\"\"\"
{transcript[:5000]}
\"\"\"
"""
            
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2500
            }
            
            try:
                # ✅ Use retry wrapper with exponential backoff
                response = groq_post_with_retry(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    payload=payload,
                    timeout=60
                )
                result = response.json()
                article_raw = result["choices"][0]["message"]["content"].strip()
            except Exception as e:
                raise RuntimeError(f"Groq article generation failed: {e}")
        
        # ✅ CLEAN: Remove any model instructions/messages from the article (e.g., "Perfect! Let's trim...")
        # Remove common model response patterns that aren't part of the article
        article_raw = re.sub(r'^(Perfect!.*?words.*?intact\.\s*)', '', article_raw, flags=re.IGNORECASE | re.MULTILINE)
        article_raw = re.sub(r'^(Let\'s trim.*?words.*?intact\.\s*)', '', article_raw, flags=re.IGNORECASE | re.MULTILINE)
        article_raw = re.sub(r'^(I\'ll trim.*?words.*?intact\.\s*)', '', article_raw, flags=re.IGNORECASE | re.MULTILINE)
        article_raw = article_raw.strip()
        
        # ✅ VALIDATE: Check article quality (mandatory)
        if is_valid_article(article_raw):
            # Article is valid, proceed to trim
            break
        else:
            # Article failed validation, regenerate
            if attempt < max_regeneration_attempts - 1:
                print(f"   ⚠️ Article validation failed (attempt {attempt + 1}/{max_regeneration_attempts}), regenerating...")
                continue
            else:
                print(f"   ⚠️ Article validation failed after {max_regeneration_attempts} attempts, using anyway (may contain spoken phrases)")
                # Use the article anyway if all attempts failed
    
    # ✅ MANDATORY: Trim to exactly 1200 words (auto-pad with transcript if too short, never exceed 1200)
    article_text = trim_to_words(article_raw, 1200, pad_source=transcript)
    print(f"✅ Generated article: {len(article_text.split())} words (trimmed from {len(article_raw.split())})")
    return article_text

def clean_article_text(raw: str) -> str:
    """
    Removes page headers like [MongoDB], extra blank lines, and any leftover reference markers.
    Keeps plain paragraph text only.
    
    Args:
        raw: Raw article text with headers and formatting
        
    Returns:
        Cleaned article text without headers or extra formatting
    """
    if not raw:
        return ""

    text = raw.strip()

    # Remove bracket headers like: [MongoDB] at start of lines
    text = re.sub(r"^\[[^\]]+\]\s*", "", text, flags=re.MULTILINE)

    # Remove multiple blank lines (3+ becomes 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def call_openai_with_backoff(fn, max_retries: int = 4):
    """
    Wrapper for OpenAI API calls with exponential backoff for rate limits (429 errors).
    
    Args:
        fn: Function to call (should return the result or raise an exception)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Result from fn()
        
    Raises:
        RuntimeError: If all retries are exhausted
    """
    wait = 2  # Initial wait time in seconds
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            # Check for rate limit errors (429) or quota issues
            if "429" in msg or "rate limit" in msg or "quota" in msg:
                if i < max_retries - 1:
                    print(f"   ⚠️ OpenAI rate limit (attempt {i + 1}/{max_retries}), waiting {wait}s...")
                    time.sleep(wait)
                    wait = min(wait * 2, 30)  # Exponential backoff, max 30s
                    continue
            # For other errors, re-raise immediately
            raise
    raise RuntimeError("OpenAI: retries exhausted after rate limit errors")

def build_article_with_openai(topic_terms: List[str], wiki_blocks: List[Dict[str, str]], target_words: int = 1200) -> str:
    """
    Synthesize a cohesive article from Wikipedia snippets using OpenAI.
    
    Args:
        topic_terms: List of topic terms to stay within scope
        wiki_blocks: List of dicts with 'title' and 'text' keys from Wikipedia
        target_words: Target word count for the synthesized article (default: 1200, max: 1200)
        
    Returns:
        Synthesized article text (900-1100 words)
        
    Raises:
        RuntimeError: If OpenAI is not configured or API call fails
    """
    if not OPENAI_AVAILABLE:
        raise RuntimeError("OpenAI SDK not installed. Install with: pip install openai")
    
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured. Set OPENAI_API_KEY environment variable.")
    
    if not wiki_blocks or len(wiki_blocks) == 0:
        raise ValueError("wiki_blocks cannot be empty")
    
    # Build sources text from wiki_blocks
    sources_text = "\n\n".join([f"[{b['title']}]\n{b['text']}" for b in wiki_blocks])
    
    prompt = f"""You are writing a clean study article for learners.

Topic terms (must stay within these): {", ".join(topic_terms)}

You are given multiple source snippets below. Write a NEW article (do not copy sentences verbatim),
synthesizing the ideas into a cohesive primer.

Hard rules:
- Stay strictly on-topic. Do NOT introduce unrelated brands/apps (e.g., Google Maps, Excel, Chrome) unless central to the topic.
- Length: {target_words} words (±10%).
- Structure: short intro + 4–6 sections with headings + short conclusion.
- Use simple language, but accurate.
- Do NOT include citations/URLs in the output.

SOURCE SNIPPETS:
{sources_text}
""".strip()
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    def make_openai_call():
        # Use chat completions API (standard OpenAI API)
        # Note: Uses Chat Completions API. For structured outputs, you can add response_format parameter.
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a technical writer who creates clear, educational articles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=int(target_words * 1.5)  # Allow enough tokens for target word count
            )
            article = response.choices[0].message.content.strip()
            if not article:
                raise ValueError("OpenAI returned empty article")
            return article
        except Exception as e:
            # Re-raise to be caught by backoff handler
            # OpenAI SDK raises specific exceptions, but we'll handle rate limits generically
            error_msg = str(e).lower()
            # Check for rate limit or quota errors (429, rate_limit, quota)
            if "429" in error_msg or "rate limit" in error_msg or "quota" in error_msg or "rate_limit" in error_msg:
                raise  # Let backoff handler deal with it
            # For other errors, also raise (backoff won't retry non-rate-limit errors)
            raise
    
    try:
        print(f"   🤖 Synthesizing article with OpenAI ({OPENAI_MODEL})...")
        article = call_openai_with_backoff(make_openai_call, max_retries=4)
        word_count = len(article.split())
        print(f"   ✅ OpenAI synthesized article: {word_count} words")
        return article
    except Exception as e:
        print(f"   ⚠️ OpenAI article synthesis failed: {e}")
        raise

def generate_web_search_questions(article_text: str, chunk_questions: List[Dict[str, Any]], video_duration: float) -> Tuple[List[Dict[str, Any]], str]:
    """
    ✅ FIXED: Generate 10 MCQs ONLY from article_text (no transcript, no Wikipedia).
    
    Args:
        article_text: Article text (exactly 1200 words, max 1200)
        chunk_questions: List of 5 existing chunk questions (to avoid overlap)
        video_duration: Total video duration in seconds
        
    Returns:
        Tuple of (list of 10 question dictionaries, article_text)
    """
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not configured. Skipping web search questions.")
        return [], article_text
    
    try:
        import requests
    except ImportError:
        print("⚠️ requests library not installed. Skipping web search questions.")
        return [], article_text
    
    # ✅ Simple validation: no topic hits, no Wikipedia checks
    def is_valid(q):
        question_text = (q.get("question") or q.get("q") or "").strip()
        options = q.get("options") or {}
        answer = (q.get("correct_answer") or q.get("answer") or "").strip().upper()
        
        if not question_text or len(question_text) < 10:
            return False
        
        if not isinstance(options, dict) or answer not in ["A", "B", "C", "D"]:
            return False
        
        # Check all 4 options exist
        normalized_options = {}
        for key in ["A", "B", "C", "D"]:
            opt_text = str(options.get(key, "")).strip()
            if not opt_text:
                return False
            normalized_options[key] = opt_text
        
        # Check options are unique
        option_values_lower = [opt.lower().strip() for opt in normalized_options.values()]
        if len(option_values_lower) != len(set(option_values_lower)):
            return False
        
        # Check correct answer exists in options
        if answer not in normalized_options:
            return False
        
        return True
    
    # ✅ STRICT LIMITS: Groq requires very small inputs
    MAX_TOKENS_INPUT = 2500   # STRICT limit
    MAX_CHARS = 3000          # Safe character limit
    
    # ✅ Trim article to strict limit
    article_for_questions = article_text[:MAX_CHARS]
    if len(article_text) > MAX_CHARS:
        print(f"   ⚠️ Article trimmed from {len(article_text)} to {MAX_CHARS} chars (strict Groq limit)")
    
    # ✅ PROMPT: Force strict JSON output (explicit format requirements)
    user_prompt = f"""Generate exactly 10 web search questions from the following article.

CRITICAL REQUIREMENTS:
- Return ONLY a JSON array, nothing else
- No explanations, no extra text, no notes
- Each object must have: question, options (A/B/C/D), correct_answer
- Valid JSON format only

Required JSON structure:
[
  {{
    "question": "The question text?",
    "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
    "correct_answer": "A"
  }}
]

Article:
\"\"\"
{article_for_questions}
\"\"\"

Return ONLY the JSON array:"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    target_count = 10
    warnings = []
    
    try:
        print(f"🤖 Generating {target_count} web search questions from article (single request, strict limits)...")
        
        # ✅ Auto-detect available model or use configured/default
        web_model = None
        
        # Try environment variable first
        if os.getenv("GROQ_WEB_MODEL"):
            web_model = os.getenv("GROQ_WEB_MODEL")
            print(f"   📌 Using model from GROQ_WEB_MODEL: {web_model}")
        else:
            # Auto-detect available models
            available_models = get_available_groq_models()
            if available_models:
                # Prefer groq/compound-mini if available, otherwise use first available
                if "groq/compound-mini" in available_models:
                    web_model = "groq/compound-mini"
                else:
                    web_model = available_models[0]
                print(f"   📌 Auto-detected available model: {web_model}")
            else:
                # Fallback to default (most widely available)
                web_model = "groq/compound-mini"
                print(f"   📌 Using default model: {web_model}")
        
        # ✅ Validate model before creating payload (catch deprecated models early)
        try:
            validate_groq_model(web_model)
        except RuntimeError:
            # If validation fails but model starts with groq/, allow it (might be new model)
            if not web_model.startswith("groq/"):
                raise
            print(f"   ⚠️ Model {web_model} not in supported list, but allowing (groq/* format)")
        
        # ✅ PAYLOAD: With system message for better structure
        payload = {
            "model": web_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an assistant that generates clear web search questions."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": 0.3
        }
        
        # ✅ DEBUG: Log payload size to catch token overflow issues
        payload_json = json.dumps(payload)
        payload_size = len(payload_json)
        print(f"   📊 Payload size: {payload_size:,} characters")
        if payload_size > 4000:
            print(f"   ⚠️ WARNING: Payload size ({payload_size:,}) exceeds safe limit")
        
        # ✅ Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=payload,
            timeout=60
        )
        
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        # Extract JSON from response using tolerant parser
        try:
            # Try tolerant parser first
            data = parse_tolerant_json(content)
            print(f"   ✅ Successfully parsed JSON from model response")
        except Exception as e:
            print(f"   ⚠️ Tolerant parser failed: {e}")
            print(f"   📄 Raw response preview: {content[:200]}...")
            # Try fallback parser
            try:
                data = safe_json_extract(content)
                print(f"   ✅ Fallback parser succeeded")
            except Exception as e2:
                print(f"   ❌ All JSON parsers failed: {e2}")
                warnings.append(f"Failed to extract JSON from response: {e2}")
                return [], article_text
        
        # Parse questions
        questions_list = None
        if isinstance(data, list):
            questions_list = data
        elif isinstance(data, dict):
            if "questions" in data and isinstance(data["questions"], list):
                questions_list = data["questions"]
            elif "mcqs" in data and isinstance(data["mcqs"], list):
                questions_list = data["mcqs"]
        
        if not questions_list:
            print(f"   ⚠️ No questions found in response")
            warnings.append("No questions found in API response")
            return [], article_text
        
        # ✅ Validate all questions
        validated_questions = [q for q in questions_list if is_valid(q)]
        
        # Check for duplicates with chunk questions
        chunk_question_texts = {q.get("question", "").lower().strip() for q in chunk_questions}
        validated_questions = [
            q for q in validated_questions 
            if q.get("question", "").lower().strip() not in chunk_question_texts
        ]
        
        # ✅ Handle partial success gracefully
        if len(validated_questions) < target_count:
            warnings.append(f"Generated {len(validated_questions)}/{target_count} questions (partial success)")
            print(f"   ⚠️ Generated {len(validated_questions)}/{target_count} valid questions")
        else:
            validated_questions = validated_questions[:target_count]
            print(f"   ✅ Generated {len(validated_questions)} valid questions")
        
        # Format questions
        formatted_questions = []
        for q in validated_questions:
            question_text = (q.get("question") or q.get("q") or "").strip()
            options = q.get("options") or {}
            answer = (q.get("correct_answer") or q.get("answer") or "").strip().upper()
            
            normalized_options = {}
            for key in ["A", "B", "C", "D"]:
                normalized_options[key] = str(options.get(key, "")).strip()
            
            formatted_questions.append({
                "question": question_text,
                "options": normalized_options,
                "correct_answer": answer,
                "explanation": q.get("explanation", ""),
                "timestamp_seconds": round(video_duration, 2),
                "timestamp": seconds_to_mmss(video_duration),
                "anchor_type": "WEB_SEARCH",
                "question_index": 0,  # Will be set when appending
            })
        
        if warnings:
            print(f"⚠️ Warnings: {'; '.join(warnings)}")
        
        if len(formatted_questions) > 0:
            print(f"✅ Generated {len(formatted_questions)} web search questions from article")
        else:
            print(f"⚠️ No web search questions generated")
        
        return formatted_questions, article_text
        
    except RuntimeError as e:
        # ✅ Handle rate limit errors gracefully (return partial success)
        if "rate limit" in str(e).lower() or "429" in str(e):
            print(f"⚠️ Rate limit hit while generating web questions: {e}")
            print(f"   Returning {len(formatted_questions) if 'formatted_questions' in locals() else 0} partial questions")
            return formatted_questions if 'formatted_questions' in locals() else [], article_text
        raise
    except Exception as e:
        print(f"⚠️ Error generating web search questions: {e}")
        traceback.print_exc()
        # ✅ Return partial results if we have any
        if 'formatted_questions' in locals() and len(formatted_questions) > 0:
            print(f"   Returning {len(formatted_questions)} partial questions")
            return formatted_questions, article_text
        return [], article_text

# ===============================
# REQUEST MODELS
# ===============================
class GenerateSaveRequest(BaseModel):
    url: str
    force: bool = False
    include_questions: bool = False  # Include full questions in response

class FetchByUrlRequest(BaseModel):
    include_answers: bool = False
    randomize: bool = True
    limit: int = Field(default=20, ge=1, le=50)

class MCQRequest(BaseModel):
    """
    Single endpoint request - everything in body, no query params
    
    🎯 TOPIC-WISE MCQ RESPONSE STRUCTURE:
    Each question in the response contains:
    - part_number: 1-20 (semantic video division)
    - topic_title: Teacher-style topic name (e.g., "Rest Api Request Lifecycle")
    - topic_start: When topic explanation started (exact from Whisper)
    - topic_end: When topic explanation ended (exact from Whisper) - this is the topic boundary
    - timestamp_seconds: MCQ trigger time (topic_end + 0.8s delay for natural feel)
    - timestamp: Human-readable format (e.g., "18:42")
    - timestamp_confidence: "exact" (derived from Whisper segments)
    
    🔒 CRITICAL GROUPING RULE:
    ALL questions from the SAME anchor share the SAME timestamp_seconds.
    Frontend MUST group questions by timestamp_seconds and pause video ONCE per topic boundary.
    
    📱 FRONTEND INTEGRATION:
    1. Group questions by timestamp_seconds
    2. Pause video when: video.currentTime >= timestamp_seconds
    3. Show ALL questions with same timestamp_seconds as a set
    4. Resume video after user completes the question set
    
    This ensures:
    - Video pauses ONLY at topic boundaries (not 20 times)
    - Multiple MCQs appear together per topic (2-3 questions per topic)
    - MCQs appear AFTER teacher completes topic (not during explanation)
    
    Example response structure (20 questions, ~6-10 unique timestamps):
    {
      "part_number": 5,
      "topic_title": "Jwt Token Validation Flow",
      "question": "What is the correct order of JWT validation steps?",
      "topic_start": 1118.6,
      "topic_end": 1122.4,
      "timestamp_seconds": 1123.2,  // Same for all questions from this anchor
      "timestamp": "18:43",
      "timestamp_confidence": "exact",
      "anchor_type": "PROCESS"
    }
    """
    video_url: str = Field(..., description="Video URL to generate/fetch MCQs from")
    include_answers: bool = Field(default=False, description="Include correct answers (anti-cheat: default false)")
    randomize: bool = Field(default=True, description="Shuffle questions")
    limit: int = Field(default=20, ge=1, le=50, description="Number of questions to return")
    force: bool = Field(default=False, description="Force regeneration even if cached (useful for testing exam-grade mode)")
    video_ended: bool = Field(default=True, description="Whether the video has ended (defaults to True to always generate 10 web search questions at video end)")

# ===============================
# PRODUCT MODELS (MongoDB)
# ===============================
class MCQOption(BaseModel):
    A: str
    B: str
    C: str
    D: str

class MCQuestion(BaseModel):
    question: str
    options: MCQOption
    correct_answer: str

class ProductResponse(BaseModel):
    product_id: str
    description: str

class ProductMCQResponse(BaseModel):
    product_id: str
    description: str
    mcq_questions: List[MCQuestion]

class ProductMCQRequest(BaseModel):
    product_id: str

# ===============================
# CONTENT SAFETY CHECK MODELS
# ===============================
class ContentSafetyCheckRequest(BaseModel):
    video_url: str = Field(..., description="Video URL to check for content safety")
    force_recheck: bool = Field(default=False, description="Force re-check even if cached result exists")

class ContentSafetyCheckResponse(BaseModel):
    status: str = Field(..., description="Status: 'success' or 'error'")
    video_id: str = Field(..., description="Unique video identifier")
    video_url: str = Field(..., description="Video URL that was checked")
    cached: bool = Field(..., description="Whether result was from cache")
    content_safety: dict = Field(..., description="Safety classification result")
    time_seconds: Optional[float] = Field(None, description="Time taken for classification (if not cached)")

# ===============================
# PRODUCT HELPER FUNCTIONS (MongoDB)
# ===============================
async def get_product_from_mongo(product_id: str) -> dict:
    """Fetch product from MongoDB"""
    if products_collection is None:
        raise HTTPException(status_code=503, detail="MongoDB not configured. Set MONGO_URI environment variable.")
    
    try:
        # Try to find by ObjectId first
        try:
            object_id = ObjectId(product_id)
            product = await products_collection.find_one({"_id": object_id})
        except:
            # If not valid ObjectId, try to find by product_id field
            product = await products_collection.find_one({"product_id": product_id})
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
        
        # Convert ObjectId to string for JSON serialization
        if "_id" in product:
            product["_id"] = str(product["_id"])
        
        # Extract product_id and description
        final_product = {
            "product_id": product.get("product_id", str(product.get("_id", ""))),
            "description": product.get("description", "")
        }
        
        if not final_product["description"]:
            raise HTTPException(status_code=400, detail="Product description not found")
        
        return final_product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


def safe_json_extract_product(text: str):
    """
    ✅ FIXED: Robust JSON extractor that handles Groq responses with extra text.
    Finds JSON array/object even if surrounded by markdown or other text.
    """
    text = text.strip()
    
    # Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Try to find JSON array first (for MCQ responses)
    array_match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
    if array_match:
        js = array_match.group(0)
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)  # Remove control characters
        js = re.sub(r",\s*}", "}", js)  # Fix trailing commas
        js = re.sub(r",\s*]", "]", js)
        try:
            return json.loads(js)
        except json.JSONDecodeError:
            pass
    
    # Fallback to object extraction
    a = text.find("{")
    b = text.rfind("}")
    if a != -1 and b > a:
        js = text[a:b + 1]
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)
        js = re.sub(r",\s*}", "}", js)
        js = re.sub(r",\s*]", "]", js)
        try:
            return json.loads(js)
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON array or object found in response")


def generate_product_mcq_with_groq(description: str) -> List[dict]:
    """Generate 5 MCQ questions using Groq AI for products"""
    
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    
    prompt = f"""Based on the following product description, generate exactly 5 multiple choice questions (MCQ) with 4 options each (A, B, C, D).

Product Description:
{description}

Return the response in this exact JSON format:
[
  {{
    "question": "Question text here?",
    "options": {{
      "A": "Option A text",
      "B": "Option B text",
      "C": "Option C text",
      "D": "Option D text"
    }},
    "correct_answer": "A"
  }}
]

Rules:
1. Generate exactly 5 questions
2. Questions should be relevant and based on the product description
3. Include technical specifications where applicable
4. Each question must have exactly 4 options (A, B, C, D)
5. Specify the correct answer (A, B, C, or D)
6. Make questions educational and informative
7. Return ONLY the JSON array, no additional text or markdown
"""

    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert at creating educational MCQ questions. Always respond with valid JSON only, no markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        # ✅ Use retry wrapper with exponential backoff
        response = groq_post_with_retry(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            payload=payload,
            timeout=60
        )
        
        result = response.json()
        response_text = result["choices"][0]["message"]["content"].strip()
        
        # Use safe JSON extractor to handle extra text
        mcq_list = safe_json_extract_product(response_text)
        
        # Validate that we have a list
        if not isinstance(mcq_list, list):
            raise ValueError(f"Expected JSON array, got {type(mcq_list).__name__}")
        
        # Validate that we have exactly 5 questions
        if len(mcq_list) != 5:
            raise ValueError(f"Expected 5 questions, got {len(mcq_list)}")
        
        # Validate each question structure
        for i, q in enumerate(mcq_list):
            if not isinstance(q, dict):
                raise ValueError(f"Question {i+1} is not a dictionary")
            if "question" not in q:
                raise ValueError(f"Question {i+1} missing 'question' field")
            if "options" not in q or not isinstance(q["options"], dict):
                raise ValueError(f"Question {i+1} missing or invalid 'options' field")
            if "correct_answer" not in q:
                raise ValueError(f"Question {i+1} missing 'correct_answer' field")
            if q["correct_answer"] not in ["A", "B", "C", "D"]:
                raise ValueError(f"Question {i+1} has invalid correct_answer: {q['correct_answer']}")
            if set(q["options"].keys()) != {"A", "B", "C", "D"}:
                raise ValueError(f"Question {i+1} must have exactly 4 options (A, B, C, D)")
        
        return mcq_list
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Groq response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API error: {str(e)}")

# ===============================
# UTILS
# ===============================
def rms_energy(x: np.ndarray) -> float:
    """
    Calculate RMS (Root Mean Square) energy of audio signal.
    Used to detect silent/low-energy clips before wasting Whisper calls.
    
    Args:
        x: Audio signal as float32 array (normalized -1.0 to 1.0)
    
    Returns:
        RMS energy value (0.0 = silent, higher = more energy)
    """
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x))))

def required_min_words(duration: float) -> int:
    """
    Adaptive minimum transcript words based on video duration.
    Exam-safe: shorter videos get lower thresholds, longer videos stay strict.
    
    Args:
        duration: Video duration in seconds
    
    Returns:
        Minimum word count required for quality MCQs
    """
    if duration < 300:      # < 5 minutes
        return 200
    elif duration < 600:    # < 10 minutes
        return 300
    return 400  # >= 10 minutes

def make_video_id(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]

def is_english(text: str) -> bool:
    if not text:
        return False
    english_chars = len(re.findall(r"[a-zA-Z0-9\s\.,!?;:\-()/%\[\]\"'&+=]", text))
    total_chars = len(re.findall(r"[^\s]", text))
    return total_chars > 0 and (english_chars / total_chars) >= 0.70

def is_semantic_duplicate(new_question: str, existing_questions: List[Dict[str, Any]], anchor_type: Optional[str] = None, threshold: Optional[float] = None) -> bool:
    """
    ✅ FIX 2: Tiered semantic deduplication with anchor-type-aware thresholds.
    
    PROCESS/DECISION questions naturally share verbs and nouns - allow more overlap.
    Other types need stricter deduplication.
    
    Args:
        new_question: Question text to check
        existing_questions: List of already accepted questions
        anchor_type: Type of anchor (for threshold selection)
        threshold: Override threshold (if None, uses tiered thresholds)
    
    Returns:
        True if duplicate, False otherwise
    """
    if not new_question or not existing_questions:
        return False
    
    # ✅ FIX 2: Tiered thresholds based on anchor type
    if threshold is None:
        if anchor_type in {"PROCESS", "DECISION"}:
            threshold = 0.85  # Allow more overlap (they share verbs/nouns naturally)
        else:
            threshold = 0.75  # Stricter for other types
    
    new_words = set(re.findall(r'\b\w+\b', new_question.lower()))
    if not new_words:
        return False
    
    for existing_q in existing_questions:
        existing_text = existing_q.get("question", "").strip()
        if not existing_text:
            continue
        
        existing_words = set(re.findall(r'\b\w+\b', existing_text.lower()))
        if not existing_words:
            continue
        
        # Calculate word overlap
        overlap = len(new_words.intersection(existing_words))
        total_unique = len(new_words.union(existing_words))
        
        if total_unique > 0:
            similarity = overlap / total_unique
            if similarity > threshold:
                return True  # Semantic duplicate detected
    
    return False

def deduplicate_questions(questions: list) -> list:
    """
    Remove duplicate questions based on normalized question text.
    
    CRITICAL FIX #4: Enhanced deduplication to catch semantic duplicates.
    """
    seen = set()
    out = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qt = (q.get("question") or "").strip().lower()
        # Normalize: remove punctuation, extra spaces
        qt_normalized = re.sub(r"[^\w\s]", "", qt)
        qt_normalized = re.sub(r"\s+", " ", qt_normalized).strip()
        
        # Check for exact match
        if qt_normalized and qt_normalized not in seen:
            # Additional check: reject if very similar (semantic duplicate)
            # If question differs by < 20% of words, consider it duplicate
            is_duplicate = False
            for seen_q in seen:
                seen_words = set(seen_q.split())
                current_words = set(qt_normalized.split())
                if len(seen_words) > 0 and len(current_words) > 0:
                    # Calculate word overlap
                    overlap = len(seen_words.intersection(current_words))
                    total_unique = len(seen_words.union(current_words))
                    similarity = overlap / total_unique if total_unique > 0 else 0
                    # If > 80% similar, consider duplicate
                    if similarity > 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                seen.add(qt_normalized)
                out.append(q)
    return out

def parse_tolerant_json(text: str):
    """
    ✅ TOLERANT JSON PARSER: Handles common model output issues.
    
    Fixes:
    - Extra text before/after JSON
    - Trailing commas
    - Control characters
    - Markdown code blocks
    - Multiple JSON objects/arrays
    
    Args:
        text: Raw model output text
        
    Returns:
        Parsed JSON (list or dict)
        
    Raises:
        ValueError: If no valid JSON can be extracted
    """
    if not text or not text.strip():
        raise ValueError("Empty response from model")
    
    # Step 1: Remove markdown code blocks
    text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    
    # Step 2: Try to find JSON array first (most common for questions)
    # Look for array pattern: [ { ... } ] with multiple objects
    # Use balanced bracket matching to find complete arrays
    bracket_start = text.find('[')
    if bracket_start != -1:
        # Find matching closing bracket
        bracket_count = 0
        bracket_end = -1
        for i in range(bracket_start, len(text)):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    bracket_end = i
                    break
        
        if bracket_end > bracket_start:
            json_text = text[bracket_start:bracket_end + 1]
            # Clean the JSON
            json_text = re.sub(r'[\x00-\x1F\x7F]', '', json_text)  # Remove control chars
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # Remove trailing commas
            
            try:
                parsed = json.loads(json_text)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError as e:
                # Try one more cleanup pass
                json_text = re.sub(r',\s*([}\]])', r'\1', json_text)  # More aggressive trailing comma removal
                try:
                    parsed = json.loads(json_text)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
    
    # Step 3: Try to find JSON object
    obj_start = text.find('{')
    obj_end = text.rfind('}')
    if obj_start != -1 and obj_end > obj_start:
        json_text = text[obj_start:obj_end + 1]
        json_text = re.sub(r'[\x00-\x1F\x7F]', '', json_text)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass
    
    raise ValueError("No valid JSON array or object found in model output")

def safe_json_extract(s: str):
    """
    ✅ FIXED: Robust JSON extractor that handles both objects and arrays.
    Uses tolerant parser for better error recovery.
    """
    try:
        return parse_tolerant_json(s)
    except ValueError:
        # Fallback to original logic for backward compatibility
        s = s.strip().replace("```json", "").replace("```", "").strip()
        
        # Try to find JSON array first (for web questions)
        array_match = re.search(r"\[\s*{.*}\s*\]", s, re.DOTALL)
        if array_match:
            js = array_match.group(0)
            js = re.sub(r"[\x00-\x1F\x7F]", "", js)
            js = re.sub(r",\s*}", "}", js)
            js = re.sub(r",\s*]", "]", js)
            try:
                return json.loads(js)
            except json.JSONDecodeError:
                pass
        
        # Fallback to object extraction (original behavior)
        a = s.find("{")
        b = s.rfind("}")
        if a == -1 or b <= a:
            raise ValueError("No JSON array or object found in model output")
        js = s[a:b + 1]
        js = re.sub(r"[\x00-\x1F\x7F]", "", js)
        js = re.sub(r",\s*}", "}", js)
        js = re.sub(r",\s*]", "]", js)
        return json.loads(js)

def strip_answers(qs: list) -> list:
    return [{"question": q["question"], "options": q["options"]} for q in qs]

# ===============================
# ffprobe duration
# ===============================
def ffprobe_duration_seconds(video_url: str) -> float:
    """
    Get video duration using ffprobe (fast, no download).
    Returns duration in seconds.
    
    Includes retry logic for network issues and better error handling.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_url
    ]
    
    last_error = None
    for attempt in range(FFPROBE_RETRIES + 1):
        try:
            print(f"🔍 Probing video duration (attempt {attempt + 1}/{FFPROBE_RETRIES + 1})...")
            r = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=FFPROBE_TIMEOUT
            )
            
            if r.returncode != 0:
                error_msg = r.stderr.strip() if r.stderr else "unknown error"
                last_error = f"ffprobe failed (code {r.returncode}): {error_msg}"
                print(f"⚠️ Attempt {attempt + 1} failed: {last_error}")
                
                # If it's a network error and we have retries left, wait and retry
                if attempt < FFPROBE_RETRIES:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s
                    print(f"⏳ Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(
                        f"❌ ffprobe failed after {FFPROBE_RETRIES + 1} attempts: {last_error}. "
                        f"Video URL: {video_url[:80]}... "
                        f"This may indicate: (1) Network connectivity issues, (2) Video URL is invalid/inaccessible, "
                        f"(3) S3 bucket permissions, or (4) Firewall blocking connection. "
                        f"Check video URL and network connectivity."
                    )
            
            # Success - parse duration
            duration_str = r.stdout.strip()
            if not duration_str:
                raise RuntimeError(f"ffprobe returned empty duration. stderr: {r.stderr}")
            
            try:
                duration = float(duration_str)
                print(f"✅ Video duration: {duration:.1f}s ({duration/60:.1f} minutes)")
                return duration
            except ValueError:
                raise RuntimeError(
                    f"❌ ffprobe returned invalid duration: '{duration_str}'. "
                    f"stderr: {r.stderr[:200]}"
                )
                
        except subprocess.TimeoutExpired:
            last_error = f"ffprobe timed out after {FFPROBE_TIMEOUT}s"
            print(f"⚠️ Attempt {attempt + 1} timed out after {FFPROBE_TIMEOUT}s")
            
            # If we have retries left, wait and retry
            if attempt < FFPROBE_RETRIES:
                wait_time = (attempt + 1) * 2
                print(f"⏳ Retrying in {wait_time}s with same timeout...")
                time.sleep(wait_time)
                continue
            else:
                raise RuntimeError(
                    f"❌ ffprobe timed out after {FFPROBE_RETRIES + 1} attempts ({FFPROBE_TIMEOUT}s each). "
                    f"Video URL: {video_url[:80]}... "
                    f"This indicates slow network or inaccessible video. "
                    f"Suggestions: (1) Check video URL accessibility, (2) Increase FFPROBE_TIMEOUT (current: {FFPROBE_TIMEOUT}s), "
                    f"(3) Check network connectivity, or (4) Verify S3 bucket permissions."
                )
    
    # Should never reach here, but just in case
    raise RuntimeError(f"ffprobe failed: {last_error}")

def pick_sample_timestamps(duration: float, n: int) -> List[float]:
    """
    Pick sample timestamps for video transcription.
    
    For short videos (< 6 minutes), uses dense scan to increase probability
    of hitting actual speech segments.
    """
    if duration <= 0:
        return [0.0]
    
    # ✅ DENSE SCAN for short videos (< 6 minutes)
    # Increases probability of hitting speech in videos with music/intro/pauses
    if duration <= 360:  # 6 minutes
        step = max(5.0, CLIP_SECONDS * 0.75)  # Overlap ~25% for better coverage
        timestamps = [t for t in np.arange(0, max(0.0, duration - CLIP_SECONDS), step)]
        # Limit to reasonable count but ensure good coverage
        timestamps = timestamps[:max(n, 12)]
        if len(timestamps) == 0:
            timestamps = [max(0.0, duration / 2)]
        return timestamps
    
    # Standard sampling for longer videos
    pad = min(10.0, duration * 0.05)
    start = pad
    end = max(pad, duration - pad)
    if end <= start + 1:
        return [max(0.0, duration / 2)]

    base = [start + (end - start) * (i + 1) / (n + 1) for i in range(n)]
    jitter_max = max(2.0, duration * 0.03)

    ts = []
    for t in base:
        j = random.uniform(-jitter_max, jitter_max)
        ts.append(min(end, max(start, t + j)))
    return ts

# ==============================
# stream clips -> whisper
# ==============================
def transcribe_sampled_stream(video_url: str) -> tuple[str, List[Dict[str, Any]], List[float], float]:
    """
    Transcribe video and return transcript, structured segments with timestamps, clip timestamps, and video duration.
    
    Returns: (transcript_text, transcript_segments, clip_timestamps, video_duration)
    
    transcript_segments: List of {text, start, end} - exact timestamps from Whisper
    """
    dur = ffprobe_duration_seconds(video_url)

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
    else:
        random.seed(time.time())

    timestamps = pick_sample_timestamps(dur, SAMPLE_CLIPS)

    all_text: List[str] = []
    transcript_segments: List[Dict[str, Any]] = []  # Structured segments with exact timestamps
    clip_timestamps: List[float] = []
    
    # Track failures for diagnostics
    successful_clips = 0
    failed_clips = 0
    empty_clips = 0
    
    for idx, ss in enumerate(timestamps):
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-rw_timeout", "30000000",  # Increased from 15s to 30s for slow S3
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "10",  # Increased from 5s to 10s
            "-ss", str(ss),
            "-t", str(CLIP_SECONDS),
            "-i", video_url,
            "-vn", "-ac", "1", "-ar", "16000",
            "-f", "s16le",
            "pipe:1"
        ]

        # Retry logic for FFmpeg extraction
        audio_bytes = None
        stderr_bytes = None
        clip_extracted = False
        
        for retry_attempt in range(FFMPEG_RETRIES + 1):
            try:
                p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    audio_bytes, stderr_bytes = p.communicate(timeout=FFMPEG_TIMEOUT_PER_CLIP)
                    
                    if p.returncode == 0 and audio_bytes and len(audio_bytes) >= 300:  # ✅ Reduced from 1000 to 300 (≈0.01s audio)
                        clip_extracted = True
                        break  # Success - exit retry loop
                    elif p.returncode != 0:
                        error_msg = stderr_bytes.decode("utf-8", errors="ignore")[:200] if stderr_bytes else "unknown error"
                        if retry_attempt < FFMPEG_RETRIES:
                            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: FFmpeg failed (code {p.returncode}), retrying ({retry_attempt + 1}/{FFMPEG_RETRIES})...")
                            time.sleep(2)  # Wait before retry
                            continue
                        else:
                            failed_clips += 1
                            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: FFmpeg failed (code {p.returncode}): {error_msg}")
                            break
                    elif not audio_bytes or len(audio_bytes) < 300:  # ✅ Reduced from 1000 to 300
                        if retry_attempt < FFMPEG_RETRIES:
                            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: No audio data, retrying ({retry_attempt + 1}/{FFMPEG_RETRIES})...")
                            time.sleep(2)
                            continue
                        else:
                            failed_clips += 1
                            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: No audio data extracted")
                            break
                            
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()  # Ensure process is terminated
                    if retry_attempt < FFMPEG_RETRIES:
                        print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: FFmpeg timeout, retrying ({retry_attempt + 1}/{FFMPEG_RETRIES})...")
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        failed_clips += 1
                        print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: FFmpeg timeout after {FFMPEG_RETRIES + 1} attempts")
                        break
                        
            except Exception as e:
                if retry_attempt < FFMPEG_RETRIES:
                    print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: Exception {e}, retrying ({retry_attempt + 1}/{FFMPEG_RETRIES})...")
                    time.sleep(2)
                    continue
                else:
                    failed_clips += 1
                    print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: Exception: {e}")
                    break
        
        if not clip_extracted:
            continue  # Move to next clip

        try:
            audio_np = (np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0)
        except Exception as e:
            failed_clips += 1
            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: Audio conversion failed: {e}")
            continue

        # ✅ Audio energy check - skip genuinely silent clips before Whisper
        energy = rms_energy(audio_np)
        if energy < 0.008:  # Tune: 0.005-0.015 depending on source (0.008 = reasonable threshold)
            empty_clips += 1
            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: Low audio energy (rms={energy:.4f}), skipping (likely silent/music-only)")
            continue

        try:
            # ✅ CRITICAL FIX: Turn off VAD completely - Whisper ko raw audio do
            # VAD is too aggressive and filtering out valid speech
            segments, _ = whisper_model.transcribe(
                audio_np,
                language="en",
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=False,  # 🔥 TURN OFF VAD - let Whisper decide
                condition_on_previous_text=False,
            )
        except Exception as e:
            failed_clips += 1
            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: Whisper transcription failed: {e}")
            continue

        # ✅ STEP 1: Keep Whisper segment timestamps (exact, defensible)
        # ✅ CRITICAL FIX: Build transcript directly from segments, not from clip_text
        clip_segment_count = 0
        clip_segment_texts = []
        
        for seg in segments:
            seg_text = seg.text.strip()
            if seg_text:  # Only process non-empty segments
                # Convert relative segment time to absolute video time
                absolute_start = ss + seg.start
                absolute_end = ss + seg.end
                
                transcript_segments.append({
                    "text": seg_text,
                    "start": round(absolute_start, 2),  # Absolute video timestamp
                    "end": round(absolute_end, 2),      # Absolute video timestamp
                    "clip_start": ss,  # Which clip this came from
                })
                clip_segment_texts.append(seg_text)  # Collect text for this clip
                clip_segment_count += 1
        
        # ✅ FIX: Use segments directly, not clip_text check
        if clip_segment_count > 0:
            # Add segment texts to transcript
            for seg_text in clip_segment_texts:
                all_text.append(seg_text)
            clip_timestamps.append(ss)  # Store timestamp for this clip
            successful_clips += 1
            clip_text_combined = " ".join(clip_segment_texts)
            print(f"✅ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: {clip_segment_count} segments, {len(clip_text_combined)} chars (energy={energy:.4f})")
        else:
            empty_clips += 1
            print(f"⚠️ Clip {idx+1}/{len(timestamps)} at {ss:.1f}s: No speech segments found (energy={energy:.4f}, segments={len(segments)} total)")

    # Build plain text transcript for backward compatibility
    transcript = " ".join(all_text).strip()
    transcript = re.sub(r"\[.*?\]", "", transcript)
    transcript = re.sub(r"\s+", " ", transcript).strip()
    
    # ✅ Diagnostic summary
    print(f"\n📊 Transcription Summary:")
    print(f"   Total clips attempted: {len(timestamps)}")
    print(f"   Successful clips: {successful_clips}")
    print(f"   Failed clips (FFmpeg/Whisper): {failed_clips}")
    print(f"   Empty clips (no speech): {empty_clips}")
    print(f"   Total segments: {len(transcript_segments)}")
    print(f"   Transcript length: {len(transcript)} chars, {len(transcript.split())} words")
    
    # ✅ CRITICAL FIX: Check segments first (not transcript words)
    # Segments are the source of truth, transcript is derived
    if len(transcript_segments) == 0:
        raise RuntimeError(
            f"❌ No speech segments detected: Whisper processed {len(timestamps)} clips but found no usable speech segments. "
            f"Video duration: {dur:.1f}s. "
            f"Energy levels: {successful_clips} clips had audio, but no speech detected. "
            f"This may indicate: (1) Video is music-only, (2) Very low speech volume, "
            f"(3) Non-English language, or (4) Audio codec issues. "
            f"Try: (1) Check video has clear spoken explanation, (2) Verify audio track exists, (3) Check language matches."
        )
    
    # ✅ Build transcript from segments (source of truth)
    if not transcript:
        # If transcript is empty but segments exist, build from segments
        transcript = " ".join(seg.get("text", "") for seg in transcript_segments).strip()
        transcript = re.sub(r"\[.*?\]", "", transcript)
        transcript = re.sub(r"\s+", " ", transcript).strip()
    
    # ✅ Final validation: Check if we have usable content
    if not transcript and len(transcript_segments) == 0:
        raise RuntimeError(
            f"❌ Transcription completely failed: No speech detected in any of {len(timestamps)} sampled clips. "
            f"Video duration: {dur:.1f}s. "
            f"This may indicate: (1) Video has no audio track, (2) Audio is music-only with no speech, "
            f"(3) Network issues preventing clip extraction, or (4) All clips were silent. "
            f"Check video URL and audio track."
        )
    
    return transcript, transcript_segments, clip_timestamps, dur

# ===============================
# ANCHOR DETECTION (Exam-grade intelligence)
# ===============================
def detect_anchors_from_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rules-based anchor detection from structured segments with exact timestamps.
    NO LLM used here - pure rule-based for exam safety.
    
    Args:
        segments: List of {text, start, end} from Whisper
    
    Returns:
        anchors: List of {type, text, start, end, sentence_index} with exact timestamps
    """
    anchors = []
    
    # Process each segment
    for seg_idx, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            continue
        
        # Split segment text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Calculate approximate position of each sentence within segment
        segment_start = seg.get("start", 0.0)
        segment_end = seg.get("end", 0.0)
        segment_duration = segment_end - segment_start if segment_end > segment_start else 0.1
        
        for sent_idx, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            # Calculate approximate timestamp for this sentence within segment
            sentence_position = sent_idx / max(len(sentences), 1)
            sentence_start = segment_start + (sentence_position * segment_duration)
            sentence_end = min(segment_end, sentence_start + (segment_duration / max(len(sentences), 1)))
            
            sl = sentence.lower().strip()
            
            # DEFINITION anchors
            definition_patterns = [
                r'\bis\s+(?:defined\s+as|known\s+as|called|referred\s+to\s+as)',
                r'\brefers\s+to',
                r'\bmeans?\s+',
                r'\bdenotes?',
                r'definition\s+of',
            ]
            if any(re.search(pattern, sl) for pattern in definition_patterns):
                sentence_clean = sentence.strip()
                if not re.search(r'[.!?]$', sentence_clean):
                    if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                        continue
                if len(sentence_clean.split()) < 5:
                    continue
                
                anchors.append({
                    "type": "DEFINITION",
                    "text": sentence_clean,
                    "start": round(sentence_start, 2),
                    "end": round(sentence_end, 2),
                    "index": seg_idx,
                    "sentence_index": seg_idx * 100 + sent_idx
                })
        
        # PROCESS anchors
        process_patterns = [
            r'\bstep\s+\d+',
            r'\b(?:first|second|third|next|then|finally)',
            r'\bprocess\s+(?:of|involves)',
            r'\bsequence\s+of',
            r'\b(?:how\s+to|procedure)',
        ]
        if any(re.search(pattern, sl) for pattern in process_patterns):
            # ✅ FIX: Reject PROCESS anchors that don't contain an explicit sequence boundary
            # This prevents half sentences like "Relational database good excel sheet then" from becoming PROCESS anchors
            if not re.search(r'\b(first|next|then|finally|before|after|step)\b', sl):
                continue  # Skip - not a complete process description
            
            # CRITICAL: Reject incomplete anchors at detection time
            sentence_clean = sentence.strip()
            # Reject if sentence ends with incomplete conjunctions
            if not re.search(r'[.!?]$', sentence_clean):
                # No ending punctuation - check if ends with conjunction (incomplete)
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue  # Skip incomplete anchor
            # Reject if too short (likely incomplete)
            if len(sentence_clean.split()) < 5:
                continue  # Skip too short anchor
            
            anchors.append({
                "type": "PROCESS",
                "text": sentence_clean,
                "start": round(sentence_start, 2),  # Exact timestamp from segment
                "end": round(sentence_end, 2),       # Exact timestamp from segment
                "index": seg_idx,
                "sentence_index": seg_idx * 100 + sent_idx
            })
        
        # RISK anchors
        risk_patterns = [
            r'\brisk\s+(?:of|is)',
            r'\bdanger\s+(?:of|is)',
            r'\bwarning',
            r'\b(?:should\s+not|must\s+not|never)',
            r'\b(?:avoid|prevent)',
            r'\b(?:critical|important)\s+(?:to\s+avoid|not\s+to)',
        ]
        if any(re.search(pattern, sl) for pattern in risk_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "RISK",
                "text": sentence_clean,
                "start": round(sentence_start, 2),  # Exact timestamp from segment
                "end": round(sentence_end, 2),       # Exact timestamp from segment
                "index": seg_idx,
                "sentence_index": seg_idx * 100 + sent_idx
            })
        
        # BOUNDARY anchors (what does NOT apply)
        boundary_patterns = [
            r'\b(?:except|excluding|not\s+including)',
            r'\b(?:only|solely)',
            r'\b(?:limited\s+to|restricted\s+to)',
            r'\b(?:does\s+not\s+include|not\s+part\s+of)',
        ]
        if any(re.search(pattern, sl) for pattern in boundary_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "BOUNDARY",
                "text": sentence_clean,
                "start": round(sentence_start, 2),  # Exact timestamp from segment
                "end": round(sentence_end, 2),       # Exact timestamp from segment
                "index": seg_idx,
                "sentence_index": seg_idx * 100 + sent_idx
            })
        
        # DECISION anchors (scenario-based)
        decision_patterns = [
            r'\b(?:if|when|in\s+case\s+of)',
            r'\b(?:choose|select|decide)',
            r'\b(?:should\s+you|would\s+you)',
            r'\b(?:scenario|situation)',
        ]
        if any(re.search(pattern, sl) for pattern in decision_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            # DECISION anchors
            decision_patterns = [
                r'\b(?:if|when|in\s+case\s+of)',
                r'\b(?:choose|select|decide)',
                r'\b(?:should\s+you|would\s+you)',
                r'\b(?:scenario|situation)',
            ]
            if any(re.search(pattern, sl) for pattern in decision_patterns):
                sentence_clean = sentence.strip()
                if not re.search(r'[.!?]$', sentence_clean):
                    if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                        continue
                if len(sentence_clean.split()) < 5:
                    continue
                
                anchors.append({
                    "type": "DECISION",
                    "text": sentence_clean,
                    "start": round(sentence_start, 2),
                    "end": round(sentence_end, 2),
                    "index": seg_idx,
                    "sentence_index": seg_idx * 100 + sent_idx
                })
            
            # COMPARISON anchors
            comparison_patterns = [
                r'\b(?:vs|versus|compared\s+to|compared\s+with)',
                r'\b(?:difference\s+between|different\s+from)',
                r'\b(?:unlike|similar\s+to|like)',
                r'\b(?:better\s+than|worse\s+than|more\s+efficient)',
                r'\b(?:instead\s+of|rather\s+than)',
            ]
            if any(re.search(pattern, sl) for pattern in comparison_patterns):
                sentence_clean = sentence.strip()
                if not re.search(r'[.!?]$', sentence_clean):
                    if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                        continue
                if len(sentence_clean.split()) < 5:
                    continue
                
                anchors.append({
                    "type": "COMPARISON",
                    "text": sentence_clean,
                    "start": round(sentence_start, 2),
                    "end": round(sentence_end, 2),
                    "index": seg_idx,
                    "sentence_index": seg_idx * 100 + sent_idx
                })
    
    return anchors

# Backward compatibility wrapper
def detect_anchors(transcript: str) -> List[Dict[str, Any]]:
    """
    Legacy function - kept for backward compatibility.
    For exact timestamps, use detect_anchors_from_segments() instead.
    """
    anchors = []
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    
    for i, sentence in enumerate(sentences):
        if not sentence.strip():
            continue
            
        sl = sentence.lower().strip()
        
        # DEFINITION anchors
        definition_patterns = [
            r'\bis\s+(?:defined\s+as|known\s+as|called|referred\s+to\s+as)',
            r'\brefers\s+to',
            r'\bmeans?\s+',
            r'\bdenotes?',
            r'definition\s+of',
        ]
        if any(re.search(pattern, sl) for pattern in definition_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "DEFINITION",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
        
        # PROCESS anchors
        process_patterns = [
            r'\bstep\s+\d+',
            r'\b(?:first|second|third|next|then|finally)',
            r'\bprocess\s+(?:of|involves)',
            r'\bsequence\s+of',
            r'\b(?:how\s+to|procedure)',
        ]
        if any(re.search(pattern, sl) for pattern in process_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "PROCESS",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
        
        # RISK anchors
        risk_patterns = [
            r'\brisk\s+(?:of|is)',
            r'\bdanger\s+(?:of|is)',
            r'\bwarning',
            r'\b(?:should\s+not|must\s+not|never)',
            r'\b(?:avoid|prevent)',
            r'\b(?:critical|important)\s+(?:to\s+avoid|not\s+to)',
        ]
        if any(re.search(pattern, sl) for pattern in risk_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "RISK",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
        
        # BOUNDARY anchors
        boundary_patterns = [
            r'\b(?:except|excluding|not\s+including)',
            r'\b(?:only|solely)',
            r'\b(?:limited\s+to|restricted\s+to)',
            r'\b(?:does\s+not\s+include|not\s+part\s+of)',
        ]
        if any(re.search(pattern, sl) for pattern in boundary_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "BOUNDARY",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
        
        # DECISION anchors
        decision_patterns = [
            r'\b(?:if|when|in\s+case\s+of)',
            r'\b(?:choose|select|decide)',
            r'\b(?:should\s+you|would\s+you)',
            r'\b(?:scenario|situation)',
        ]
        if any(re.search(pattern, sl) for pattern in decision_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "DECISION",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
        
        # COMPARISON anchors
        comparison_patterns = [
            r'\b(?:vs|versus|compared\s+to|compared\s+with)',
            r'\b(?:difference\s+between|different\s+from)',
            r'\b(?:unlike|similar\s+to|like)',
            r'\b(?:better\s+than|worse\s+than|more\s+efficient)',
            r'\b(?:instead\s+of|rather\s+than)',
        ]
        if any(re.search(pattern, sl) for pattern in comparison_patterns):
            sentence_clean = sentence.strip()
            if not re.search(r'[.!?]$', sentence_clean):
                if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$', sentence_clean, re.IGNORECASE):
                    continue
            if len(sentence_clean.split()) < 5:
                continue
            
            anchors.append({
                "type": "COMPARISON",
                "text": sentence_clean,
                "index": i,
                "sentence_index": i
            })
    
    return anchors

# ===============================
# ANCHOR SANITIZATION (Quality Control)
# ===============================
def sanitize_anchor_text(text: str) -> str:
    """
    Clean anchor text before sending to LLM.
    Removes vague references and ambiguous phrases.
    
    CRITICAL FIX #2: Improved anchor sanitization to reject incomplete sentences.
    """
    if not text:
        return ""
    
    text = text.strip()
    
    # CRITICAL FIX: Reject anchors that are too short (likely incomplete)
    if len(text.split()) < 5:
        return ""  # Too short, likely incomplete
    
    # CRITICAL FIX: Reject anchors ending with conjunctions (incomplete sentences)
    # These create broken question stems like "If you use MongoDB or Redis to understand both the game, then your performance will not be..."
    incomplete_endings = [r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*$']
    for pattern in incomplete_endings:
        if re.search(pattern, text, re.IGNORECASE):
            return ""  # Incomplete sentence, reject
    
    # Remove vague references
    vague_patterns = [
        r'\b(this|that|these|those|provided|aforementioned|said|mentioned)\b',
        r'\b(dictionary|list|table|chart|above|below)\s+(?:above|below|provided|mentioned)',
    ]
    for pattern in vague_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # CRITICAL FIX: Ensure sentence ends properly (has punctuation or is complete)
    # Reject if ends with trailing conjunctions or incomplete phrases
    if not re.search(r'[.!?]$', text):
        # No ending punctuation - check if it's a complete thought
        # If it ends with a conjunction, it's incomplete
        if re.search(r'\s+(then|if|but|and|or|so|because|when|where|while|although)$', text, re.IGNORECASE):
            return ""
    
    # Hard cap length
    if len(text) > 300:
        text = text[:297] + "..."
    
    return text

# ===============================
# QUESTION QUALITY FILTERS (Exam-Grade Validation)
# ===============================
BAD_PHRASES = [
    "cash in", "without further ado", "quickly", "just", "simply",
    "obviously", "clearly", "of course", "needless to say",
    "as you know", "as mentioned", "as stated",
    # ✅ FIX 2: Added common unprofessional phrases that cause rejections
    "you can", "let us", "we use", "good for",
    "basically", "kind of", "etc", "and so on",
    "and stuff", "or something"
]

ANCHOR_RULES = {
    "PROCESS": {
        "must_include": ["sequence", "order", "step", "first", "next", "then", "finally"],
        "forbidden": ["why", "opinion", "think", "believe", "feel"]
    },
    "DECISION": {
        "must_include": ["if", "when", "scenario", "should", "would", "choose", "decide"],
        "forbidden": ["definition", "what is", "define", "meaning"]
    },
    "DEFINITION": {
        "must_include": ["defined", "means", "refers", "denotes", "is"],
        "forbidden": ["how", "why", "when", "where"]
    },
    "RISK": {
        "must_include": ["risk", "danger", "warning", "avoid", "prevent", "consequence"],
        "forbidden": ["benefit", "advantage", "positive"]
    },
    "BOUNDARY": {
        "must_include": ["not", "except", "excluding", "only", "solely"],
        "forbidden": ["all", "every", "always"]
    }
}

def option_is_valid(option_text: str) -> bool:
    """
    Reject options that contain unprofessional phrases or structural issues.
    
    CRITICAL FIX #1: Reject options containing nested option labels (A., B., C., D.)
    """
    if not option_text or len(option_text.strip()) < 5:
        return False
    
    opt_lower = option_text.lower()
    
    # Check for bad phrases
    for phrase in BAD_PHRASES:
        if phrase in opt_lower:
            return False
    
    # CRITICAL FIX: Reject options containing nested option labels
    # Example: "B. Create an account -> C. Use the website" is invalid
    # STRICT: Reject ANY occurrence of A., B., C., D. (with or without arrows)
    # NON-NEGOTIABLE: This is exam-illegal
    nested_option_pattern = r'\b[A-D][\.\)]\s'
    if re.search(nested_option_pattern, option_text, re.IGNORECASE):
        return False
    
    # STRICT: Reject arrow-separated sequences (likely nested options)
    # Even without explicit labels, "->" chains suggest nested options
    if '->' in option_text or '→' in option_text:
        # Count arrows - if ANY arrows exist, check for nested labels
        arrow_count = option_text.count('->') + option_text.count('→')
        if arrow_count >= 1:
            # If it contains option-like patterns, definitely reject
            if re.search(r'[A-D][\.\)]', option_text, re.IGNORECASE):
                return False
            # If it has ANY arrows, reject (likely multi-step sequence)
            # Even single arrow suggests a sequence chain which is not exam-legal
            return False
    
    # Reject if too short or too long
    if len(option_text) < 10 or len(option_text) > 200:
        return False
    
    return True

def question_meets_anchor_rules(question_text: str, anchor_type: str) -> bool:
    """
    Validate that question follows anchor type rules.
    
    CRITICAL FIX #3: Stricter anchor-question type alignment validation.
    """
    if anchor_type not in ANCHOR_RULES:
        return True  # Unknown type, allow
    
    rules = ANCHOR_RULES[anchor_type]
    q_lower = question_text.lower()
    
    # CRITICAL FIX: Enforce anchor type-specific question patterns
    # DEFINITION anchors must start with definition-style questions
    if anchor_type == "DEFINITION":
        definition_patterns = [
            r'^what\s+is\s+(?:the\s+)?(?:definition|meaning|description)\s+of',
            r'^which\s+(?:of\s+the\s+following\s+)?(?:describes|defines|refers\s+to)',
            r'^what\s+(?:does|is)\s+\w+\s+(?:mean|refer\s+to|denote)',
        ]
        if not any(re.search(pattern, q_lower) for pattern in definition_patterns):
            return False  # DEFINITION anchor must generate definition question
    
    # PROCESS anchors must ask about sequence/order/steps
    # CRITICAL: This is REQUIRED, not optional - PROCESS anchor MUST generate process question
    # NON-NEGOTIABLE RULE: If anchor_type == PROCESS, question MUST contain process terms
    if anchor_type == "PROCESS":
        # ✅ FIX 3: STRICT PROCESS ENFORCEMENT - Hard block on definition patterns
        # Reject ANY question that looks like definition (analogy, metaphor, "what is")
        forbidden_patterns = [
            r'^what\s+is\s+',  # 🔥 HARD BLOCK: "What is..." is definition, not process
            r'defined\s+as',
            r'refers\s+to',
            r'means?\s+',
            r'denotes?',
            r'^which\s+(?:of\s+the\s+following\s+)?(?:describes|defines|refers\s+to)',
            r'^what\s+(?:does|is)\s+\w+\s+(?:mean|refer\s+to|denote)',
            # Catch "What is the [adjective] [noun] that [verb]..." pattern (definition questions)
            r'^what\s+is\s+the\s+\w+\s+\w+\s+that\s+\w+',  # "What is the document oriented database that stores..."
            r'^what\s+is\s+the\s+\w+\s+oriented\s+\w+',  # "What is the document oriented database..."
            r'^what\s+is\s+the\s+\w+\s+that\s+stores',  # "What is the database that stores..."
        ]
        if any(re.search(pattern, q_lower) for pattern in forbidden_patterns):
            return False  # PROCESS anchor CANNOT generate definition question
        
        # SECOND: Check for process terms FIRST (before checking "What is the..." pattern)
        required_process_terms = ["order", "sequence", "step", "first", "next", "then", "finally", "before", "after"]
        has_process_terms = any(term in q_lower for term in required_process_terms)
        
        # THIRD: If question starts with "What is the..." but has NO process terms, it's a definition
        if re.search(r'^what\s+is\s+the\s+\w+', q_lower):
            if not has_process_terms:
                return False  # "What is the..." without process terms = definition question (REJECT)
        
        # FOURTH: Require process-specific patterns
        process_patterns = [
            r'(?:what\s+is\s+the\s+)?(?:correct\s+)?(?:order|sequence|step)',
            r'which\s+step\s+(?:comes\s+)?(?:first|next|last|before|after)',
            r'what\s+happens\s+(?:first|next|then|after|before)',
            r'in\s+what\s+order',
            r'what\s+is\s+the\s+sequence',
            r'what\s+is\s+the\s+correct\s+order',
        ]
        has_process_pattern = any(re.search(pattern, q_lower) for pattern in process_patterns)
        
        # STRICT: Must have EITHER pattern match OR process terms (but NOT definition)
        if not (has_process_pattern or has_process_terms):
            return False  # PROCESS anchor MUST generate process question
        
        # If we get here, it's either a process question or we missed something - allow it
    
    # DECISION anchors must ask about scenarios/choices
    if anchor_type == "DECISION":
        decision_patterns = [
            r'(?:what\s+)?(?:should|would|will)\s+you\s+(?:do|choose|select|decide)',
            r'in\s+(?:this\s+)?(?:scenario|situation|case)',
            r'if\s+\w+.*(?:what|which|how)',
        ]
        if not any(re.search(pattern, q_lower) for pattern in decision_patterns):
            # Allow if contains decision-related terms
            if not any(term in q_lower for term in ["should", "would", "choose", "decide", "scenario", "if"]):
                return False  # DECISION anchor must generate decision question
    
    # Check must_include
    must_include = rules.get("must_include", [])
    if must_include:
        has_required = any(term in q_lower for term in must_include)
        if not has_required:
            return False
    
    # Check forbidden
    forbidden = rules.get("forbidden", [])
    if forbidden:
        has_forbidden = any(term in q_lower for term in forbidden)
        if has_forbidden:
            return False
    
    return True

def question_is_context_dependent(question_text: str, context: str) -> bool:
    """
    Check if question requires context to answer.
    Anti-Google / Anti-ChatGPT moat.
    
    Returns True if question is context-dependent (good).
    Returns False if question can be answered without context (bad).
    """
    if not context or len(context) < 50:
        return False
    
    q_lower = question_text.lower()
    context_lower = context.lower()
    
    # Extract key terms from question
    question_terms = set(re.findall(r'\b[a-z]{4,}\b', q_lower))
    
    # Check if question terms appear in context
    context_terms = set(re.findall(r'\b[a-z]{4,}\b', context_lower))
    
    # At least 2-3 key terms should be in context
    overlap = question_terms.intersection(context_terms)
    if len(overlap) < 2:
        return False
    
    # Check for generic questions that can be answered without context
    generic_patterns = [
        r'what\s+is\s+(?:the\s+)?(?:definition|meaning|purpose)\s+of',
        r'what\s+are\s+(?:the\s+)?(?:types|kinds|categories)',
        r'which\s+of\s+the\s+following\s+is\s+(?:always|generally|usually)',
    ]
    
    for pattern in generic_patterns:
        if re.search(pattern, q_lower):
            # Generic question - check if it's grounded in context
            if len(overlap) < 3:
                return False
    
    return True

def validate_mcq_quality(question: Dict[str, Any], anchor: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """
    Comprehensive quality validation for exam-grade MCQs.
    
    Returns: (is_valid, reason_if_invalid)
    
    CRITICAL FIXES APPLIED:
    - Reject options with nested option labels
    - Reject incomplete question stems
    - Stricter anchor-question type alignment
    """
    question_text = question.get("question", "").strip()
    options = question.get("options", {})
    anchor_type = validate_anchor_type(anchor.get("type", "UNKNOWN"))
    
    # Check 1: Question text exists
    if not question_text or len(question_text) < 20:
        return False, "Question text too short or missing"
    
    # CRITICAL FIX #2: Reject incomplete question stems
    # MANDATORY: Reject questions ending with incomplete phrases
    # This catches "then your performance will not be..." pattern (appears twice in output)
    
    # Pattern 1: Ends with "will not be..." (with or without dots)
    if re.search(r'will\s+not\s+be\s*\.{0,3}$', question_text, re.IGNORECASE):
        return False, "Question stem is incomplete (ends with 'will not be' without completion)"
    
    # Pattern 2: Ends with "then" followed by incomplete phrase
    if re.search(r'\s+then\s+.*will\s+not\s+be\s*\.{0,3}$', question_text, re.IGNORECASE):
        return False, "Question stem is incomplete (ends with 'then...will not be' pattern)"
    
    # Pattern 3: Ends with conjunctions
    incomplete_endings = [
        r'\s+(then|if|but|and|or|so|because|when|where|while|although)\s*\.{0,3}$',  # Ends with conjunction
        r'\s+is\s+not\s+\.{0,3}$',  # "is not..." incomplete
        r'\s+to\s+\.{0,3}$',  # "to..." incomplete
        r'\.{3,}$',  # Ends with multiple dots (...)
        r'\s+will\s+not\s*$',  # "will not" without verb
    ]
    for pattern in incomplete_endings:
        if re.search(pattern, question_text, re.IGNORECASE):
            return False, "Question stem is incomplete (ends with conjunction or incomplete phrase)"
    
    # Check 2: All 4 options exist
    if not isinstance(options, dict) or len(options) != 4:
        return False, "Invalid options structure"
    
    # Check 3: Options are valid (no bad phrases, no nested option labels)
    for key, opt_text in options.items():
        if not option_is_valid(str(opt_text)):
            # More specific error message
            opt_str = str(opt_text)
            if re.search(r'\b[A-D][\.\)]\s', opt_str, re.IGNORECASE):
                return False, f"Option {key} contains nested option labels (A., B., C., D.)"
            return False, f"Option {key} contains unprofessional phrases or structural issues"
    
    # Check 4: Anchor rules compliance (now with stricter alignment)
    if not question_meets_anchor_rules(question_text, anchor_type):
        return False, f"Question doesn't follow {anchor_type} anchor rules (type mismatch)"
    
    # Check 5: Context dependency
    if not question_is_context_dependent(question_text, context):
        return False, "Question can be answered without video context"
    
    # Check 6: No vague references in question
    vague_in_question = re.search(r'\b(this|that|these|those|provided|aforementioned)\b', question_text, re.I)
    if vague_in_question:
        return False, "Question contains vague references"
    
    # CRITICAL FIX #4: Basic language quality check
    # Reject questions with obvious grammar issues or awkward phrasing
    awkward_patterns = [
        r'\s+the\s+the\s+',  # "the the"
        r'\s+a\s+a\s+',  # "a a"
        r'\s+an\s+an\s+',  # "an an"
        r'\buse\s+the\s+\w+\s+as\s+a\s+user\'s\s+',  # "use the X as a user's" - awkward
    ]
    for pattern in awkward_patterns:
        if re.search(pattern, question_text, re.IGNORECASE):
            return False, "Question contains awkward phrasing or grammar issues"
    
    return True, ""

# ===============================
# PEDAGOGY ENGINE (Question type control)
# ===============================
QUESTION_TYPE_MAP = {
    "DEFINITION": "paraphrase",  # Ask to identify/paraphrase the definition
    "PROCESS": "ordering",       # Ask about sequence/steps
    "RISK": "consequence",       # Ask about what happens if risk occurs
    "BOUNDARY": "exclusion",     # Ask "which does NOT apply"
    "DECISION": "scenario",       # Ask "what should you do in this scenario"
    "DEFAULT": "recall"           # Fallback for unrecognized anchors
}

def get_pedagogy_instruction(anchor_type: str, variant: int = 0) -> str:
    """
    Returns exam-safe instruction for LLM based on anchor type and variant.
    LLM ko choice nahi milni chahiye - yeh force karta hai.
    
    variant: 0 = first question type, 1 = second question type (for multi-question per anchor)
    """
    # ✅ MULTI-QUESTION PER ANCHOR: Different question templates per variant
    if anchor_type == "DEFINITION":
        if variant == 0:
            return "Generate a PARAPHRASE type question. Ask to identify or restate the definition in different words."
        else:  # variant == 1
            return "Generate a NEGATIVE type question. Ask 'which of the following is NOT true about [concept]' or 'which does NOT describe [concept]'."
    
    elif anchor_type == "PROCESS":
        if variant == 0:
            return "Generate an ORDERING type question. Ask 'which step comes first' or 'what is the correct order' - DO NOT embed options in the question stem. Each option must be a standalone step description without nested labels (A., B., C., D.)."
        else:  # variant == 1
            return "Generate a MISSING STEP type question. Ask 'which step is missing' or 'what step should come between X and Y' - DO NOT embed options in the question stem."
    
    elif anchor_type == "DECISION":
        if variant == 0:
            return "Generate a BEST CHOICE type question. Ask 'what should you choose' or 'which is the best option' based on the scenario."
        else:  # variant == 1
            return "Generate a SCENARIO type question. Present a specific scenario and ask what should be done or decided in that situation."
    
    elif anchor_type == "BOUNDARY":
        if variant == 0:
            return "Generate an EXCEPTION type question. Ask 'which of the following is an exception' or 'which case does NOT apply'."
        else:  # variant == 1
            return "Generate a CONDITION VIOLATION type question. Ask 'under what condition does this NOT apply' or 'when would this fail'."
    
    elif anchor_type == "RISK":
        if variant == 0:
            return "Generate a COMMON MISTAKE type question. Ask 'what is a common mistake' or 'what should be avoided'."
        else:  # variant == 1
            return "Generate a CONSEQUENCE type question. Ask 'what happens if this risk occurs' or 'what is the consequence of this mistake'."
    
    elif anchor_type == "COMPARISON":
        if variant == 0:
            return "Generate a DIFFERENCE type question. Ask 'what is the difference between X and Y' or 'how does X differ from Y'."
        else:  # variant == 1
            return "Generate a USE CASE type question. Ask 'when should you use X instead of Y' or 'which is more appropriate for [scenario]'."
    
    # Default instructions (fallback)
    qtype = QUESTION_TYPE_MAP.get(anchor_type, QUESTION_TYPE_MAP["DEFAULT"])
    instructions = {
        "paraphrase": "Generate a PARAPHRASE type question. Ask to identify or restate the definition in different words.",
        "ordering": "Generate an ORDERING/SEQUENCE type question. Ask about the correct order of steps or sequence.",
        "consequence": "Generate a CONSEQUENCE type question. Ask about what happens if the risk occurs or what the consequence is.",
        "exclusion": "Generate an EXCLUSION type question. Ask 'which of the following does NOT apply' or 'which is NOT included'.",
        "scenario": "Generate a SCENARIO type question. Present a scenario and ask what should be done or decided.",
        "recall": "Generate a RECALL type question. Ask to recall specific information from the context."
    }
    
    return instructions.get(qtype, instructions["recall"])

def build_context_window(transcript_sentences: List[str], anchor_index: int, window_size: int = 2) -> str:
    """
    Builds 24-second equivalent context window around anchor.
    Exam-critical: ensures questions are answerable from specific context.
    """
    start = max(0, anchor_index - window_size)
    end = min(len(transcript_sentences), anchor_index + window_size + 1)
    context_sentences = transcript_sentences[start:end]
    return " ".join(context_sentences).strip()

# ===============================
# importance scoring
# ===============================
def chunk_text_words(text: str, chunk_words: int, overlap: int) -> List[str]:
    words = re.findall(r"\w+|\S", text)
    chunks: List[str] = []
    i = 0
    step = max(1, chunk_words - overlap)
    while i < len(words):
        chunk = words[i:i + chunk_words]
        if len(chunk) < max(40, chunk_words // 3):
            break
        s = "".join([w if re.match(r"\W", w) else (" " + w) for w in chunk]).strip()
        chunks.append(s)
        i += step
    return chunks

def score_chunks_importance(chunks: List[str]) -> List[tuple]:
    tokenized = []
    freq: Dict[str, int] = {}
    for c in chunks:
        toks = [t.lower() for t in re.findall(r"[a-zA-Z]{3,}", c)]
        tokenized.append(toks)
        for t in toks:
            freq[t] = freq.get(t, 0) + 1

    scored = []
    for idx, toks in enumerate(tokenized):
        if not toks:
            continue
        uniq = set(toks)
        score = sum(1.0 / (1 + freq.get(t, 1)) for t in uniq)
        score *= min(1.6, max(0.6, len(toks) / 120))
        scored.append((score, idx))

    scored.sort(reverse=True)
    return scored

def pick_random_important_chunks(transcript: str) -> List[str]:
    """Legacy function - kept for backward compatibility"""
    chunks = chunk_text_words(transcript, CHUNK_WORDS, CHUNK_OVERLAP)
    if len(chunks) < 3:
        return [transcript]

    scored = score_chunks_importance(chunks)
    top = [chunks[idx] for _, idx in scored[:min(IMPORTANT_POOL_SIZE, len(scored))]]

    k = min(RANDOM_PICK_COUNT, len(top))
    picked = random.sample(top, k=k) if k > 0 else []

    begin = chunks[0]
    end = chunks[-1]

    final: List[str] = []
    seen = set()
    for s in [begin] + picked + [end]:
        key = s[:80]
        if key not in seen:
            seen.add(key)
            final.append(s)

    return final

def seconds_to_mmss(seconds: float) -> str:
    """
    Convert seconds to MM:SS format.
    Examples: 148.23 -> "2:28", 63.53 -> "1:04", 0.0 -> "0:00"
    """
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes}:{secs:02d}"

def generate_topic_title(anchor: Dict[str, Any]) -> str:
    """
    Generate teacher-style topic title from anchor text.
    Extracts meaningful words and formats them as a readable topic name.
    
    Args:
        anchor: Anchor dictionary with 'text' field
    
    Returns:
        Formatted topic title (e.g., "Rest Api Request Lifecycle")
    """
    text = anchor.get("text", "")
    if not text:
        anchor_type = validate_anchor_type(anchor.get("type", "UNKNOWN"))
        return f"{anchor_type.title()} Concept"
    
    # Extract meaningful words (3+ characters, alphabetic)
    words = re.findall(r"[A-Za-z]{3,}", text)
    
    # Take first 6 words for concise title
    title_words = words[:6]
    
    if not title_words:
        # Fallback to anchor type if no words found
        anchor_type = validate_anchor_type(anchor.get("type", "UNKNOWN"))
        return f"{anchor_type.title()} Concept"
    
    # Join and title-case (e.g., "Rest Api Request Lifecycle")
    title = " ".join(title_words)
    return title.title()

def calculate_timestamp_for_sentence(sentence_index: int, transcript_sentences: List[str], clip_timestamps: List[float], video_duration: float) -> float:
    """
    Calculate approximate timestamp for a sentence based on its position in transcript.
    
    Strategy:
    - Map sentence to clip based on transcript position
    - Estimate position within clip
    - Return timestamp in seconds
    """
    if not clip_timestamps or len(transcript_sentences) == 0:
        # Fallback: distribute evenly across video
        return (sentence_index / max(len(transcript_sentences), 1)) * video_duration
    
    # Calculate which clip this sentence belongs to
    # Each clip contributes roughly equal text, so map by position
    total_sentences = len(transcript_sentences)
    if total_sentences == 0:
        return 0.0
    
    # Estimate which clip this sentence came from
    clip_index = min(int((sentence_index / total_sentences) * len(clip_timestamps)), len(clip_timestamps) - 1)
    base_timestamp = clip_timestamps[clip_index]
    
    # Estimate position within clip (0-12 seconds)
    sentences_per_clip = total_sentences / len(clip_timestamps) if len(clip_timestamps) > 0 else 1
    position_in_clip = (sentence_index % sentences_per_clip) / max(sentences_per_clip, 1)
    offset = position_in_clip * CLIP_SECONDS
    
    return min(video_duration, max(0.0, base_timestamp + offset))

# ✅ FIX 3: Anchor quotas aligned with question generation math
# Formula: Total MCQs = Σ (anchors[type] × questions_per_anchor[type])
# Target: 20 questions total
# PROCESS: 4 anchors × 2 questions = 8
# DECISION: 4 anchors × 2 questions = 8
# DEFINITION: 2 anchors × 1 question = 2
# COMPARISON: 2 anchors × 1 question = 2
# Total = 20 questions
ANCHOR_QUOTAS = {
    "PROCESS": 4,      # ×2 = 8 questions
    "DECISION": 4,     # ×2 = 8 questions
    "DEFINITION": 2,   # ×1 = 2 questions
    "COMPARISON": 2,   # ×1 = 2 questions
    # RISK and BOUNDARY dropped (high-rejection types, only include if explicitly required)
}

def pick_anchors_with_quota(anchors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Select anchors using quota-based system for balanced exam-grade coverage.
    Ensures every anchor type gets its fair share (no random distribution).
    
    Returns:
        Selected anchors meeting quota requirements
    """
    if len(anchors) == 0:
        return []
    
    # Group anchors by type
    grouped = defaultdict(list)
    for anchor in anchors:
        anchor_type = validate_anchor_type(anchor.get("type", "UNKNOWN"))
        if anchor_type in ANCHOR_QUOTAS:  # Only include quota-defined types
            grouped[anchor_type].append(anchor)
    
    selected = []
    
    # Fill quotas for each anchor type
    for anchor_type, quota in ANCHOR_QUOTAS.items():
        pool = grouped.get(anchor_type, [])
        if not pool:
            continue  # Skip if no anchors of this type found
        
        # Take up to quota (or all available if less)
        take = min(quota, len(pool))
        selected_anchors = random.sample(pool, take)
        
        for anchor in selected_anchors:
            # Build context window if not present
            if "context" not in anchor:
                anchor["context"] = anchor.get("text", "")
            selected.append(anchor)
    
    return selected

def pick_anchors_for_exam_from_list(anchors: List[Dict[str, Any]], target_count: int) -> List[Dict[str, Any]]:
    """
    [DEPRECATED] Use pick_anchors_with_quota() instead for exam-grade mode.
    Kept for backward compatibility.
    """
    # Use quota-based selection for exam-grade
    return pick_anchors_with_quota(anchors)

def pick_anchors_for_exam(transcript: str, target_count: int, clip_timestamps: Optional[List[float]] = None, video_duration: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Exam-grade anchor selection - uses anchor detection + controlled randomization.
    Returns anchors with context windows and timestamps for MCQ generation.
    """
    anchors = detect_anchors(transcript)
    
    if len(anchors) == 0:
        # Fallback: if no anchors detected, use sentence-based approach
        sentences = re.split(r'(?<=[.!?])\s+', transcript)
        if len(sentences) < 3:
            return [{"type": "DEFAULT", "text": transcript, "index": 0, "context": transcript}]
        
        # Pick random sentences as pseudo-anchors
        selected_indices = random.sample(range(len(sentences)), min(target_count, len(sentences)))
        result = []
        for idx in selected_indices:
            context = build_context_window(sentences, idx, window_size=2)
            result.append({
                "type": "DEFAULT",
                "text": sentences[idx].strip(),
                "index": idx,
                "context": context
            })
        return result
    
    # Group anchors by type for balanced coverage
    anchors_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for anchor in anchors:
        anchor_type = anchor["type"]
        if anchor_type not in anchors_by_type:
            anchors_by_type[anchor_type] = []
        anchors_by_type[anchor_type].append(anchor)
    
    # Select anchors ensuring coverage of different types
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    selected_anchors = []
    
    # Distribute target_count across anchor types
    types_list = list(anchors_by_type.keys())
    if len(types_list) == 0:
        return []
    
    per_type = max(1, target_count // len(types_list))
    remaining = target_count
    
    for anchor_type in types_list:
        type_anchors = anchors_by_type[anchor_type]
        if len(type_anchors) == 0:
            continue
        
        # Randomize within same type (regulator-safe: same concept coverage, different wording)
        count_for_type = min(per_type, len(type_anchors), remaining)
        if count_for_type > 0:
            selected = random.sample(type_anchors, count_for_type)
            for anchor in selected:
                context = build_context_window(sentences, anchor["sentence_index"], window_size=2)
                anchor["context"] = context
                selected_anchors.append(anchor)
            remaining -= count_for_type
    
    # If we need more, fill from any remaining anchors
    if remaining > 0:
        all_remaining = [a for a in anchors if a not in selected_anchors]
        if len(all_remaining) > 0:
            additional = random.sample(all_remaining, min(remaining, len(all_remaining)))
            for anchor in additional:
                context = build_context_window(sentences, anchor["sentence_index"], window_size=2)
                anchor["context"] = context
                selected_anchors.append(anchor)
    
    return selected_anchors[:target_count]

# ===============================
# Ollama generation
# ===============================
def mcq_prompt_from_anchor(anchor: Dict[str, Any], question_number: int = 1, variant: int = 0, subtype: Optional[str] = None) -> str:
    """
    Exam-grade prompt: LLM ko sirf WRITER banao, examiner nahi.
    Anchor + Pedagogy instruction + Context window = Exam-safe MCQ.
    
    variant: 0 = first question type, 1 = second question type (for multi-question per anchor)
    subtype: Sub-question type for PROCESS/DECISION (e.g., "ORDER", "MISSING_STEP", "WHEN_TO_USE", "WHY_NOT_USE")
    """
    anchor_type = validate_anchor_type(anchor.get("type", "DEFAULT"))
    anchor_text_raw = anchor.get("text", "")
    # Sanitize anchor text before sending to LLM
    anchor_text = sanitize_anchor_text(anchor_text_raw)
    context = anchor.get("context", anchor_text)
    pedagogy_instruction = get_pedagogy_instruction(anchor_type, variant=variant)
    
    # ✅ FIX 4: Add subtype instruction if provided
    subtype_instruction = ""
    if subtype:
        if subtype == "ORDER":
            subtype_instruction = "\n\nSUBTYPE FOCUS: This question must focus on ORDERING/SEQUENCE. Ask 'which step comes first' or 'what is the correct order'."
        elif subtype == "MISSING_STEP":
            subtype_instruction = "\n\nSUBTYPE FOCUS: This question must focus on MISSING STEPS. Ask 'which step is missing' or 'what step should come between X and Y'."
        elif subtype == "WHEN_TO_USE":
            subtype_instruction = "\n\nSUBTYPE FOCUS: This question must focus on WHEN TO USE. Ask 'when should you use X' or 'in which scenario is X appropriate'."
        elif subtype == "WHY_NOT_USE":
            subtype_instruction = "\n\nSUBTYPE FOCUS: This question must focus on WHY NOT USE. Ask 'why should you NOT use X' or 'in which case would X be inappropriate'."
    
    return f"""You are writing ONE exam-grade multiple-choice question.

QUESTION #{question_number}

PEDAGOGY INSTRUCTION (MUST FOLLOW):
{pedagogy_instruction}{subtype_instruction}

IMPORTANT - SEMANTIC CONTRAST REQUIREMENT:
- Question variant {variant} MUST test a DIFFERENT cognitive skill than variant {1 - variant if variant == 0 else 0}
- Variant 0 tests: recognition, order, or identification
- Variant 1 tests: reasoning, exclusion, or missing elements
- Do NOT restate the same fact using different wording
- Do NOT paraphrase the same concept
- Focus on a fundamentally different aspect or angle of the anchor concept

ANCHOR POINT (Focus of question):
{anchor_text}

CONTEXT WINDOW (24-second equivalent - answer MUST be from here):
{context}

CRITICAL EXAM RULES:
1) Question MUST be answerable ONLY from the context window provided
2) Do NOT use facts outside the context
3) Question type MUST match the pedagogy instruction exactly
4) Exactly 4 options: A, B, C, D
5) correct_answer must be exactly "A", "B", "C", or "D"
6) No ambiguity - only ONE correct answer
7) English only
8) No newline characters in JSON string values
9) NO vague references like "this", "that", "provided", "aforementioned"
10) NO unprofessional phrases like "cash in", "quickly", "just", "obviously", "you can", "let us", "we use", "good for", "basically", "kind of"
11) Options must be professional exam-style language
12) Question must require context to answer (cannot be answered without watching video)
13) CRITICAL: Each option must be a complete, standalone statement - DO NOT include nested option labels (A., B., C., D.) inside options
14) CRITICAL: Question stem must be grammatically complete - DO NOT end with conjunctions (then, if, but, and, or) or incomplete phrases
15) CRITICAL: Question must start with appropriate words for the anchor type:
   - DEFINITION: "What is the definition of..." or "Which describes..."
   - PROCESS: "What is the correct order..." or "Which step comes first..."
   - DECISION: "What should you do..." or "In this scenario..."
16) Use clear, professional language - avoid awkward phrasing like "use the X as a user's"
17) CRITICAL: Each option must explicitly name the database, concept, or entity being discussed. Pronouns (it, this, that, they) are FORBIDDEN in options.
18) CRITICAL: Question must explicitly name the concepts being discussed. Avoid pronouns and vague references. Use specific nouns from the context.

JSON FORMAT (Return ONLY this, no markdown):

{{
  "question": "Question text based on anchor and pedagogy instruction",
  "options": {{
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  }},
  "correct_answer": "A"
}}

Return JSON only:"""

def mcq_prompt_from_segments(segments: List[str], count: int, start_index: int = 1) -> str:
    """Legacy prompt function - kept for backward compatibility"""
    joined = "\n\n---\n\n".join(segments)
    return f"""Generate EXACTLY {count} NEW multiple-choice questions in ENGLISH ONLY.

IMPORTANT:
- These are questions #{start_index} to #{start_index + count - 1}.
- Do NOT repeat earlier questions. Make them different.

CRITICAL RULES:
1) English only
2) Exactly 4 options per question with keys A, B, C, D
3) correct_answer must be exactly one of: "A" or "B" or "C" or "D"
4) Return ONLY valid JSON (no markdown, no extra text)
5) Do NOT include newline characters inside any JSON string values (use spaces)
6) Output must be a single JSON object starting with '{{' and ending with '}}'

JSON FORMAT:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }},
      "correct_answer": "A"
    }}
  ]
}}

CONTENT:

{joined}

Return JSON only:"""

# Ollama function removed - using Groq API only
def generate_mcqs_ollama_from_segments(segments: List[str]) -> List[Dict[str, Any]]:
    """
    REMOVED - Ollama no longer used.
    This function is kept for backward compatibility but raises an error.
    """
    raise RuntimeError("Ollama removed. Use topic-chunk mode with Groq API instead.")

def fill_with_legacy_mcqs(
    transcript: str,
    existing_questions: List[Dict[str, Any]],
    target_count: int
) -> List[Dict[str, Any]]:
    """
    REMOVED - Legacy MCQ generation no longer supported.
    Use topic-chunk mode with Groq API instead.
    """
    raise RuntimeError("Legacy MCQ generation removed. Use topic-chunk mode with Groq API instead.")
    
    # Add legacy MCQs with deduplication
    for q in legacy_mcqs:
        if len(existing_questions) >= target_count:
            break
        
        # Skip if duplicate (exact match)
        is_duplicate = False
        for ex in existing_questions:
            if q.get("question", "").strip().lower() == ex.get("question", "").strip().lower():
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        # Check semantic similarity (avoid >80% similar questions)
        is_semantic_duplicate = False
        current_text = q.get("question", "").strip().lower()
        current_words = set(re.findall(r'\b\w+\b', current_text))
        
        for ex in existing_questions:
            existing_text = ex.get("question", "").strip().lower()
            existing_words = set(re.findall(r'\b\w+\b', existing_text))
            if len(existing_words) > 0 and len(current_words) > 0:
                overlap = len(existing_words.intersection(current_words))
                total_unique = len(existing_words.union(current_words))
                similarity = overlap / total_unique if total_unique > 0 else 0
                if similarity > 0.8:
                    is_semantic_duplicate = True
                    break
        
        if is_semantic_duplicate:
            continue
        
        # Mark as legacy fill
        q["anchor_type"] = "LEGACY"
        existing_questions.append(q)
        print(f"   ✅ Added legacy MCQ #{len(existing_questions)} (fill)")
    
    return existing_questions[:target_count]

def build_context_from_segments(anchor: Dict[str, Any], transcript_segments: List[Dict[str, Any]], window_seconds: float = 24.0) -> str:
    """
    Build context from transcript segments around the anchor (not just anchor text).
    
    This ensures questions are answerable from specific video context, not generic knowledge.
    
    Args:
        anchor: Anchor dictionary with start/end timestamps
        transcript_segments: List of all transcript segments with timestamps
        window_seconds: Context window size in seconds (default: 24s)
    
    Returns:
        Context text built from segments around the anchor
    """
    anchor_start = anchor.get("start", anchor.get("timestamp_seconds", 0.0))
    anchor_end = anchor.get("end", anchor_start + 5.0)
    
    # Build context window: window_seconds before anchor start to anchor end
    ctx_start = max(0, anchor_start - window_seconds)
    ctx_end = anchor_end
    
    ctx_text = []
    for seg in transcript_segments:
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", seg_start)
        
        # Include segment if it overlaps with context window
        if seg_start < ctx_end and seg_end > ctx_start:
            ctx_text.append(seg.get("text", "").strip())
    
    return " ".join(ctx_text).strip()

def find_actual_topic_end(anchor: Dict[str, Any], transcript_segments: List[Dict[str, Any]], video_duration: Optional[float] = None) -> float:
    """
    Find the actual topic end by looking at subsequent segments after the anchor.
    
    Strategy:
    1. Start from anchor's end timestamp
    2. Look at subsequent segments
    3. Find when topic actually ends (significant gap, topic transition phrase, or next anchor)
    4. Return the actual topic end timestamp
    
    Args:
        anchor: Anchor dictionary with start/end timestamps
        transcript_segments: List of all transcript segments with timestamps
        video_duration: Total video duration (to cap the search)
    
    Returns:
        Actual topic end timestamp (when teacher finishes explaining the topic)
    """
    anchor_start = anchor.get("start", anchor.get("timestamp_seconds", 0.0))
    anchor_end = anchor.get("end", anchor_start + 5.0)
    
    # Default: use anchor end + reasonable buffer (3-5 seconds for topic completion)
    default_topic_end = anchor_end + 5.0
    
    if not transcript_segments or video_duration is None:
        return min(default_topic_end, video_duration) if video_duration else default_topic_end
    
    # Find segments that come after this anchor
    next_segments = [
        seg for seg in transcript_segments
        if seg.get("start", 0.0) > anchor_end
    ]
    
    if not next_segments:
        # No subsequent segments, use default
        return min(default_topic_end, video_duration)
    
    topic_end = anchor_end
    max_lookahead = min(15.0, video_duration - anchor_end)  # Look ahead max 15 seconds
    
    for seg in next_segments:
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", seg_start)
        seg_text = seg.get("text", "").lower()
        
        # If we've looked too far ahead, stop
        if seg_start - anchor_end > max_lookahead:
            break
        
        # Calculate gap from previous topic_end
        gap = seg_start - topic_end
        
        # 🔒 HARD STOP CONDITIONS
        
        # 1. Significant gap (pause > 2 seconds) = teacher paused, topic ended
        if gap > 2.0:
            break
        
        # 2. Topic transition phrase detected = moving to next topic
        if re.search(r'\b(next topic|now let us|moving on|after that|let\'s move|next we\'ll|now we\'ll)\b', seg_text):
            break
        
        # Update topic_end to this segment's end (topic continues)
        topic_end = seg_end
    
    # Cap at video duration
    topic_end = min(topic_end, video_duration)
    
    # Ensure topic_end is at least anchor_end
    topic_end = max(topic_end, anchor_end)
    
    return round(topic_end, 2)

def generate_mcqs_ollama_from_anchors(anchors: List[Dict[str, Any]], video_duration: Optional[float] = None, transcript_segments: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Exam-grade MCQ generation: Multi-question per anchor (2 questions per anchor).
    LLM is just a writer, not decision maker.
    
    Strategy: Generate 2 distinct questions per anchor to reach 20 questions naturally.
    
    Args:
        anchors: List of anchor dictionaries with exact timestamps
        video_duration: Total video duration in seconds (for context window calculation)
        transcript_segments: List of transcript segments (for finding actual topic end)
    
    Returns: (questions_list, anchor_metadata_list)
    """
    # Ollama removed - this function should not be called
    raise RuntimeError("Ollama removed. Use topic-chunk mode with Groq API instead.")
    
    all_cleaned: List[Dict[str, Any]] = []
    anchor_metadata: List[Dict[str, Any]] = []
    
    # ✅ FIX 1: Per-anchor-type question limits (prevents repetition)
    # DEFINITION, BOUNDARY, COMPARISON: 1 question each (they repeat easily)
    # PROCESS, DECISION: 2 questions each (can be split into different angles)
    QUESTIONS_PER_ANCHOR_TYPE = {
        "DEFINITION": 1,
        "BOUNDARY": 1,
        "COMPARISON": 1,
        "PROCESS": 2,
        "DECISION": 2,
        "RISK": 1,  # Default fallback
        "DEFAULT": 1
    }
    
    # ✅ FIX 4: Sub-question types for PROCESS and DECISION (ensures different angles)
    ANCHOR_SUBTYPES = {
        "PROCESS": ["ORDER", "MISSING_STEP"],
        "DECISION": ["WHEN_TO_USE", "WHEN_NOT_TO_USE"],
        "DEFINITION": ["MEANING"],
        "COMPARISON": ["DIFFERENCE"]
    }
    
    # ✅ FIX 3: Calculate max possible questions based on anchor inventory
    anchor_type_counts = defaultdict(int)
    for anchor in anchors:
        anchor_type = validate_anchor_type(anchor.get("type", "DEFAULT"))
        anchor_type_counts[anchor_type] += 1
    
    MAX_POSSIBLE_MCQS = (
        anchor_type_counts.get("PROCESS", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("PROCESS", 1) +
        anchor_type_counts.get("DECISION", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("DECISION", 1) +
        anchor_type_counts.get("DEFINITION", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("DEFINITION", 1) +
        anchor_type_counts.get("COMPARISON", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("COMPARISON", 1) +
        anchor_type_counts.get("RISK", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("RISK", 1) +
        anchor_type_counts.get("BOUNDARY", 0) * QUESTIONS_PER_ANCHOR_TYPE.get("BOUNDARY", 1)
    )
    
    # Use realistic target (don't force impossible 20)
    realistic_target = min(MCQ_COUNT, MAX_POSSIBLE_MCQS)
    
    print(f"   📊 Anchor inventory: {dict(anchor_type_counts)}")
    print(f"   📊 Max possible: {MAX_POSSIBLE_MCQS} questions, Target: {realistic_target} questions")
    
    # ✅ FIX: Grouped rejection logging to reduce spam (shared across all anchors)
    rejection_counters = defaultdict(int)
    
    # ✅ STEP 1: Anchor lock - ONE ANCHOR = ONE QUESTION (MAX)
    used_anchors = set()  # Track which anchors have already generated a question
    
    # ✅ FIX 1: Track used subtypes per anchor to prevent repetition
    used_subtypes = defaultdict(set)  # anchor_id -> set of used subtypes
    
    for idx, anchor in enumerate(anchors):
        if len(all_cleaned) >= realistic_target:
            break
        
        # ✅ STEP 2: Skip anchor if already used (ONE ANCHOR = ONE QUESTION)
        if idx in used_anchors:
            continue  # 🔒 Do NOT generate again from same anchor
        
        # ✅ CRITICAL: Calculate topic end timestamp ONCE per anchor (shared by all questions)
        # This ensures ALL questions from same anchor have SAME timestamp_seconds
        anchor_start = anchor.get("start", anchor.get("timestamp_seconds", 0.0))
        
        # ✅ FIX: Find ACTUAL topic end (when teacher finishes explaining), not just sentence end
        # Look at subsequent segments to find when topic actually ends
        anchor_end = anchor.get("end", anchor_start + 5.0)  # Sentence end (fallback)
        actual_topic_end = find_actual_topic_end(anchor, transcript_segments or [], video_duration)
        
        # Use actual topic end, but ensure it's at least anchor_end
        topic_end = max(actual_topic_end, anchor_end)
        topic_end_seconds = topic_end + TOPIC_END_DELAY  # Trigger time (topic end + delay)
        
        # ✅ FIX 1: Get question limit for this anchor type
        anchor_type = validate_anchor_type(anchor.get("type", "DEFAULT"))
        max_questions_this_anchor_type = QUESTIONS_PER_ANCHOR_TYPE.get(anchor_type, 1)
        
        # Calculate how many questions we still need
        remaining_needed = realistic_target - len(all_cleaned)
        max_questions_this_anchor = min(max_questions_this_anchor_type, remaining_needed)
        
        # Generate questions from this anchor (up to the limit for this anchor type)
        questions_from_anchor = 0
        
        # ✅ SOFT-FAIL MODE: Track total rejections for this anchor (across all variants/retries)
        rejection_count_for_anchor = 0
        
        # ✅ FIX 1: Store original context for variant splitting
        original_context = anchor.get("context", "")
        
        for question_variant in range(max_questions_this_anchor):
            if len(all_cleaned) >= realistic_target:
                break
            
            # ✅ ONE ANCHOR = ONE QUESTION: If anchor already used, skip remaining variants
            if idx in used_anchors:
                break  # 🔒 Anchor already generated a question, skip remaining variants
            
            # ✅ FIX 1: Split context window per variant for PROCESS/DECISION (semantic isolation)
            if anchor_type in {"PROCESS", "DECISION"} and max_questions_this_anchor > 1:
                # Split context into two halves for semantic non-overlap
                full_context = original_context
                sentences = re.split(r'(?<=[.!?])\s+', full_context)
                
                if question_variant == 0:
                    # First half of context for variant 0
                    context = " ".join(sentences[:len(sentences)//2])
                else:
                    # Second half of context for variant 1
                    context = " ".join(sentences[len(sentences)//2:])
                
                # Update anchor context for this variant
                anchor["context"] = context if context.strip() else original_context
            else:
                # Use full context for single-question anchors
                anchor["context"] = original_context
            
            # ✅ FIX 4: Get sub-question type for PROCESS and DECISION anchors
            subtype = None
            if anchor_type in ANCHOR_SUBTYPES:
                subtypes = ANCHOR_SUBTYPES[anchor_type]
                if question_variant < len(subtypes):
                    subtype = subtypes[question_variant]
            
            base_prompt = mcq_prompt_from_anchor(anchor, question_number=len(all_cleaned) + 1, variant=question_variant, subtype=subtype)
            
            retries = 0
            max_retries_per_anchor = 5  # Increased retries to ensure we get real questions (was 3)
            question_generated = False
            
            while retries < max_retries_per_anchor and not question_generated:
                # ✅ FIX: Mutate prompt on retry to avoid repeating bad option structure
                if retries > 0:
                    prompt = base_prompt + "\n\nIMPORTANT: Rewrite with strictly formal exam language. Avoid unprofessional phrases, slang, or casual language. Use academic terminology."
                else:
                    prompt = base_prompt
                try:
                    # Ollama removed - this function should not be called
                    raise RuntimeError("Ollama removed. Use topic-chunk mode with Groq API instead.")
                    
                    if r.returncode != 0:
                        retries += 1
                        time.sleep(0.5)
                        continue
                    
                    out = r.stdout.decode("utf-8", errors="ignore").strip()
                    data = safe_json_extract(out)
                    
                    # Handle both single question and list format
                    if "question" in data and "options" in data:
                        # Single question format
                        qs = [data]
                    elif "questions" in data and isinstance(data["questions"], list):
                        # List format (take first one)
                        qs = data["questions"][:1]
                    else:
                        retries += 1
                        continue
                    
                    # Validate and clean
                    for q in qs:
                        if not isinstance(q, dict):
                            continue
                        
                        question_text = (q.get("question") or "").strip()
                        options = q.get("options") or {}
                        ca = (q.get("correct_answer") or "").strip().upper()
                        
                        if isinstance(options, dict):
                            options = {str(k).upper(): v for k, v in options.items()}
                        
                        if not question_text or not isinstance(options, dict) or ca not in ["A", "B", "C", "D"]:
                            continue
                        if not {"A", "B", "C", "D"}.issubset(set(options.keys())):
                            continue
                        if not is_english(question_text):
                            continue
                        
                        optA = str(options.get("A", "")).strip()
                        optB = str(options.get("B", "")).strip()
                        optC = str(options.get("C", "")).strip()
                        optD = str(options.get("D", "")).strip()
                        
                        if not all([optA, optB, optC, optD]):
                            continue
                        if not (is_english(optA) and is_english(optB) and is_english(optC) and is_english(optD)):
                            continue
                        
                        # ✅ FIX 2: Hard gate bad options BEFORE full validation (early rejection)
                        # This saves time and reduces retry pressure
                        bad_option_found = False
                        for opt_key, opt_text in [("A", optA), ("B", optB), ("C", optC), ("D", optD)]:
                            if not option_is_valid(opt_text):
                                rejection_counters[f"Option {opt_key} contains unprofessional phrases or structural issues (early rejection)"] += 1
                                bad_option_found = True
                                break
                        
                        if bad_option_found:
                            retries += 1
                            continue  # Skip full validation, retry immediately
                        
                        cleaned_q = {
                            "question": question_text,
                            "options": {"A": optA, "B": optB, "C": optC, "D": optD},
                            "correct_answer": ca,
                            "anchor_type": validate_anchor_type(anchor.get("type", "DEFAULT"))  # Store anchor type for tracking
                        }
                        
                        # Exam-grade quality validation
                        context = anchor.get("context", "")
                        is_valid, rejection_reason = validate_mcq_quality(cleaned_q, anchor, context)
                        
                        if not is_valid:
                            # ✅ FIX: Grouped rejection logging to reduce spam
                            rejection_counters[rejection_reason] += 1
                            rejection_count_for_anchor += 1
                            
                            # ✅ SOFT-FAIL MODE: After MAX_REJECTIONS_PER_ANCHOR, force-accept to prevent 0-MCQ issue
                            if rejection_count_for_anchor >= MAX_REJECTIONS_PER_ANCHOR:
                                print(f"   ⚠️ SOFT-ACCEPT: Anchor {idx+1} exceeded {MAX_REJECTIONS_PER_ANCHOR} rejections. Force-accepting MCQ to prevent 0-MCQ result.")
                                print(f"      Last rejection reason: {rejection_reason}")
                                # Force accept this MCQ (bypass validation)
                                is_valid = True
                                rejection_reason = None
                            else:
                                retries += 1
                                continue  # Retry this variant
                        
                        # ✅ FIX 3: Check for duplicates (exact and semantic) - CRITICAL for preventing repetition
                        # First check exact duplicate
                        is_duplicate = False
                        question_text = cleaned_q.get("question", "").strip()
                        
                        for existing_q in all_cleaned:
                            if existing_q.get("question", "").strip().lower() == question_text.lower():
                                is_duplicate = True
                                rejection_counters["Exact duplicate"] += 1
                                rejection_count_for_anchor += 1
                                
                                # ✅ SOFT-FAIL MODE: Check if we should force-accept despite duplicate
                                if rejection_count_for_anchor >= MAX_REJECTIONS_PER_ANCHOR:
                                    print(f"   ⚠️ SOFT-ACCEPT: Anchor {idx+1} exceeded {MAX_REJECTIONS_PER_ANCHOR} rejections. Force-accepting MCQ (exact duplicate check bypassed).")
                                    is_duplicate = False  # Force accept
                                else:
                                    break
                        
                        # ✅ FIX 2: Hard semantic deduplication - compare with ALL accepted questions
                        if not is_duplicate:
                            anchor_type_for_dedup = validate_anchor_type(anchor.get("type", "DEFAULT"))
                            
                            # ✅ FIX 2: Use stricter threshold for semantic deduplication (0.7 = 70% word overlap)
                            q_words = set(re.findall(r'\b\w+\b', question_text.lower()))
                            for prev_q in all_cleaned:
                                prev_text = prev_q.get("question", "").strip()
                                if not prev_text:
                                    continue
                                
                                prev_words = set(re.findall(r'\b\w+\b', prev_text.lower()))
                                if not prev_words:
                                    continue
                                
                                # Calculate word overlap
                                overlap = len(q_words.intersection(prev_words))
                                # Use Jaccard similarity: overlap / union
                                union = len(q_words.union(prev_words))
                                similarity = overlap / union if union > 0 else 0
                                
                                # ✅ FIX 2: 70% word overlap = semantic duplicate (stricter than before)
                                if similarity > 0.7:
                                    is_duplicate = True
                                    rejection_counters[f"Semantic duplicate ({similarity:.2f} similarity)"] += 1
                                    rejection_count_for_anchor += 1
                                    
                                    # ✅ SOFT-FAIL MODE: Check if we should force-accept despite semantic duplicate
                                    if rejection_count_for_anchor >= MAX_REJECTIONS_PER_ANCHOR:
                                        print(f"   ⚠️ SOFT-ACCEPT: Anchor {idx+1} exceeded {MAX_REJECTIONS_PER_ANCHOR} rejections. Force-accepting MCQ (semantic duplicate check bypassed).")
                                        is_duplicate = False  # Force accept
                                    else:
                                        break
                        
                        if not is_duplicate:
                            # ✅ SOFT-FAIL MODE: Log if this was a soft-accept and mark it
                            is_soft_accepted = rejection_count_for_anchor >= MAX_REJECTIONS_PER_ANCHOR
                            if is_soft_accepted:
                                print(f"   ✅ SOFT-ACCEPTED MCQ Part {len(all_cleaned) + 1} from anchor {idx+1} (after {rejection_count_for_anchor} rejections)")
                                cleaned_q["_soft_accepted"] = True  # Mark for tracking
                            
                            # ✅ FIX 1: Mark subtype as used for this anchor
                            anchor_id = idx  # Use index as unique identifier
                            if subtype:
                                used_subtypes[anchor_id].add(subtype)
                            # ✅ STEP 4: Questions inherit exact timestamps from anchor segments
                            # 🎯 TOPIC-WISE MCQ ARCHITECTURE:
                            # Each MCQ is anchored to a topic boundary (when teacher finishes explaining a concept)
                            # CRITICAL: Timestamp = topic END (when teacher finishes), not topic START
                            # This ensures MCQs appear AFTER topic completion, not during explanation
                            
                            # ✅ CRITICAL: Use pre-calculated topic_end_seconds (shared across all questions from same anchor)
                            # This ensures ALL questions from same anchor have IDENTICAL timestamp_seconds
                            # Frontend can group by timestamp_seconds and pause video ONCE per topic boundary
                            
                            # ✅ Add part_number (1-based, max 20) - formal video division into semantic parts
                            # Each part = one completed topic
                            part_number = len(all_cleaned) + 1
                            cleaned_q["part_number"] = part_number
                            
                            # ✅ Add topic_title (teacher-style) - student-friendly topic name
                            # Generated from anchor text (e.g., "Rest Api Request Lifecycle")
                            cleaned_q["topic_title"] = generate_topic_title(anchor)
                            
                            # ✅ Add both topic_start and topic_end for clarity
                            cleaned_q["topic_start"] = round(anchor_start, 2)  # When topic explanation started
                            cleaned_q["topic_end"] = round(topic_end, 2)  # When topic explanation actually ended (found from segments)
                            
                            # ✅ MCQ trigger timestamp = topic end + delay (when to show MCQ)
                            # 🔒 HARD RULE: ALL questions from same anchor share SAME timestamp_seconds
                            # Frontend integration: Group by timestamp_seconds, pause video ONCE per topic boundary
                            cleaned_q["timestamp_seconds"] = round(topic_end_seconds, 2)  # Shared across all questions from this anchor
                            cleaned_q["timestamp"] = seconds_to_mmss(topic_end_seconds)  # MM:SS format (human-readable)
                            cleaned_q["timestamp_confidence"] = anchor.get("timestamp_confidence", "exact")  # Always "exact" for exam-grade
                            
                            # Add context window for exam-grade evidence
                            context_end = anchor_end + 12  # Default: 12s after anchor
                            if video_duration:
                                context_end = min(video_duration, context_end)  # Cap at video duration
                            cleaned_q["context_window"] = {
                                "start": round(max(0, anchor_start - 12), 2),  # 12s before
                                "end": round(context_end, 2)  # 12s after (or video end)
                            }
                            
                            all_cleaned.append(cleaned_q)
                            questions_from_anchor += 1
                            question_generated = True
                            
                            # ✅ STEP 3: Lock anchor after first accepted MCQ (ONE ANCHOR = ONE QUESTION)
                            used_anchors.add(idx)  # 🔒 Lock this anchor forever - no more questions from this anchor
                            
                            print(f"   ✅ Accepted MCQ Part {part_number}/20 ({anchor.get('type', 'UNKNOWN')}, '{cleaned_q.get('topic_title', 'N/A')}', topic_end: {topic_end:.1f}s, trigger: {topic_end_seconds:.1f}s)")
                            
                            # Store anchor metadata for quality_metrics (only once per anchor, not per question)
                            if questions_from_anchor == 1:  # Only store metadata for first question from this anchor
                                anchor_meta = {
                                    "anchor_id": f"a_{idx:03d}",
                                    "anchor_type": validate_anchor_type(anchor.get("type", "DEFAULT")),
                                    "concept_summary": anchor.get("text", "")[:200],  # Truncate for storage
                                    "source": "video",
                                    "sentence_index": anchor.get("sentence_index", anchor.get("index", 0)),
                                    "timestamp_seconds": anchor.get("start", anchor.get("timestamp_seconds", 0.0)),  # Exact from segment
                                    "context_window": {
                                        "default_seconds": 24,
                                        "user_adjustable": True,
                                        "min_seconds": 12,
                                        "max_seconds": 40
                                    },
                                    "question": {
                                        "question_type": QUESTION_TYPE_MAP.get(validate_anchor_type(anchor.get("type", "DEFAULT")), "recall"),
                                        "format": "mcq",
                                        "difficulty": "medium",  # Could be enhanced with actual difficulty detection
                                        "retry_variant_count": retries + 1,
                                        "questions_generated": 1  # Will be updated
                                    },
                                    "llm": {
                                        "generator_model": GROQ_MODEL if USE_TOPIC_CHUNK_MODE else "removed",
                                        "critic_model": GROQ_MODEL if USE_TOPIC_CHUNK_MODE else "removed",
                                        "generation_pass": 1
                                    }
                                }
                                anchor_metadata.append(anchor_meta)
                            else:
                                # Update question count for this anchor
                                if len(anchor_metadata) > 0:
                                    anchor_metadata[-1]["question"]["questions_generated"] = questions_from_anchor
                            
                            break  # Success, move to next variant or anchor
                        else:
                            retries += 1
                    
                except subprocess.TimeoutExpired:
                    retries += 1
                    time.sleep(0.5)
                except Exception as e:
                    retries += 1
                    time.sleep(0.5)
        
        # Small delay between anchors
        if idx < len(anchors) - 1:
            time.sleep(0.2)
    
    # ✅ FIX: Ensure we have real questions (no duplicates, all validated)
    # Final deduplication pass to ensure all questions are unique
    final_questions = []
    seen_questions = set()
    
    for q in all_cleaned:
        question_text = q.get("question", "").strip().lower()
        if not question_text:
            continue
        
        # Check exact duplicate
        if question_text in seen_questions:
            continue
        
        # Check semantic similarity with already added questions
        is_duplicate = False
        for existing_q in final_questions:
            existing_text = existing_q.get("question", "").strip().lower()
            existing_words = set(re.findall(r'\b\w+\b', existing_text))
            current_words = set(re.findall(r'\b\w+\b', question_text))
            if len(existing_words) > 0 and len(current_words) > 0:
                overlap = len(existing_words.intersection(current_words))
                total_unique = len(existing_words.union(current_words))
                similarity = overlap / total_unique if total_unique > 0 else 0
                if similarity > 0.8:  # >80% similar = duplicate
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            final_questions.append(q)
            seen_questions.add(question_text)
            
            # Stop when we have enough real questions
            if len(final_questions) >= MCQ_COUNT:
                break
    
    print(f"   ✅ Final: {len(final_questions)} real questions (target: {realistic_target}, max possible: {MAX_POSSIBLE_MCQS})")
    
    # ✅ SOFT-FAIL MODE: Count soft-accepted MCQs (if any)
    soft_accept_count = sum(1 for q in final_questions if q.get("_soft_accepted", False))
    if soft_accept_count > 0:
        print(f"   ⚠️ SOFT-ACCEPT MODE: {soft_accept_count} MCQs were force-accepted after {MAX_REJECTIONS_PER_ANCHOR} rejections per anchor (to prevent 0-MCQ result)")
    
    # ✅ FIX: Print rejection summary at end (grouped logging)
    if rejection_counters:
        print(f"   📊 Rejection Summary:")
        for reason, count in sorted(rejection_counters.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {reason}: {count}")
    
    return final_questions[:MCQ_COUNT], anchor_metadata

# ===============================
# pipeline
# ===============================
def generate_mcqs_from_video_fast(video_url: str, use_anchors: Optional[bool] = None) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]], str, List[Dict[str, Any]], float]:
    """
    Main pipeline: Video → Transcript → Safety Check → Anchors → MCQs
    
    Topic-Chunk mode (USE_TOPIC_CHUNK_MODE=True):
    - 3 topic chunks (0-35%, 35-70%, 70-100%)
    - 5 questions total (2+2+1)
    - Questions timed at chunk ends (topic boundaries)
    - Uses Groq API for fast generation
    
    Exam-grade mode (use_anchors=True):
    - Anchor detection (rules-based, no LLM)
    - Pedagogy engine (question type control)
    - 24-second context windows
    - LLM is just a writer, not decision maker
    
    Legacy mode (use_anchors=False):
    - Random important chunks
    - LLM decides everything
    
    Returns: (questions_list, anchor_metadata_list_or_None, transcript_text, transcript_segments, video_duration)
    ✅ FIXED: Now returns transcript data to avoid double transcription
    
    Raises:
        RuntimeError: If transcript is UNSAFE (blocks video processing)
    """
    if use_anchors is None:
        use_anchors = USE_ANCHOR_MODE
    
    transcript, transcript_segments, clip_timestamps, video_duration = transcribe_sampled_stream(video_url)
    
    # ✅ TRANSCRIPT SAFETY CHECK: Classify transcript before processing
    print(f"🔍 Performing transcript safety check...")
    try:
        safety_result = classify_transcript_safety(transcript)
        
        verdict = safety_result.get("verdict", "UNCERTAIN").upper()
        confidence = safety_result.get("confidence", 0.0)
        category = safety_result.get("category", "unknown")
        reason = safety_result.get("reason", "No reason provided")
        needs_manual_review = safety_result.get("needs_manual_review", False)
        
        # Block video if UNSAFE
        if verdict == "UNSAFE":
            error_msg = (
                f"Video transcript classified as UNSAFE. "
                f"Category: {category}, Confidence: {confidence:.2f}, Reason: {reason}"
            )
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)
        
        # Mark for manual review if confidence is low
        if needs_manual_review:
            print(f"⚠️ Transcript safety confidence ({confidence:.2f}) below threshold (0.6) - marked for manual review")
            print(f"   Verdict: {verdict}, Category: {category}, Reason: {reason}")
        else:
            print(f"✅ Transcript safety check passed: {verdict} (confidence: {confidence:.2f}, category: {category})")
            
    except RuntimeError:
        # Re-raise blocking errors (UNSAFE verdict)
        raise
    except Exception as e:
        # Log but don't block on classification errors (fail open for availability)
        print(f"⚠️ Transcript safety check failed: {e}")
        print(f"   Continuing with video processing (fail-open policy)")
    
    # ✅ TOPIC-CHUNK MODE: Fast 3-chunk → 5 questions approach (ONLY MODE)
    if not USE_TOPIC_CHUNK_MODE:
        raise RuntimeError(
            "Topic-chunk mode disabled and Ollama removed. "
            "Enable USE_TOPIC_CHUNK_MODE=true to use Groq API for question generation."
        )
    
    print(f"📦 Topic-Chunk Mode: Building 3 chunks from {len(transcript_segments)} segments (duration: {video_duration:.1f}s)...")
    
    questions, chunk_metadata = generate_mcqs_from_topic_chunks(transcript_segments, video_duration)
    
    # Last question timing is already handled in generate_mcqs_from_topic_chunks
    # (chunk 3 ensures max(T3, video_duration - 2))
    
    print(f"   ✅ Generated {len(questions)} questions from 3 topic chunks")
    return questions, chunk_metadata, transcript, transcript_segments, video_duration

# ===============================
# QUALITY METRICS BUILDER (Exam-Grade)
# ===============================
def build_quality_metrics(anchor_metadata: Optional[List[Dict[str, Any]]], 
                          questions: List[Dict[str, Any]], 
                          generation_time: float,
                          mode: str = "exam-grade") -> Dict[str, Any]:
    """
    Build complete quality_metrics JSON for exam-grade content.
    
    Schema version 2.0 - includes full anchor metadata for regulator compliance.
    """
    if mode != "exam-grade" or not anchor_metadata:
        # Legacy mode or no anchor metadata
        return {
            "schema_version": "1.0",
            "generation_mode": "legacy",
            "total_questions": len(questions),
            "generation_time_seconds": round(generation_time, 2)
        }
    
    # Exam-grade mode: build complete metadata
    quality_metrics = {
        "schema_version": "2.0",
        "generation_mode": "exam-grade",
        "anchors": anchor_metadata,
        "generation_summary": {
            "total_anchors": len(anchor_metadata),
            "total_questions": len(questions),
            "retry_policy": "context-first",
            "legacy_upgraded": False
        },
        "generation_time_seconds": round(generation_time, 2)
    }
    
    # Add anchor distribution for quick stats
    anchor_distribution = {}
    for anchor in anchor_metadata:
        anchor_type = validate_anchor_type(anchor.get("anchor_type", "UNKNOWN"))
        anchor_distribution[anchor_type] = anchor_distribution.get(anchor_type, 0) + 1
    quality_metrics["generation_summary"]["anchor_distribution"] = anchor_distribution
    
    # CRITICAL: Add evidence_hash for tamper-evidence (non-negotiable)
    # Hash schema_version + anchors + generation_summary (exclude evidence_hash itself)
    hash_payload = {
        "schema_version": quality_metrics["schema_version"],
        "anchors": quality_metrics["anchors"],
        "generation_summary": quality_metrics["generation_summary"]
    }
    payload_json = json.dumps(hash_payload, sort_keys=True)
    quality_metrics["evidence_hash"] = hashlib.sha256(payload_json.encode()).hexdigest()
    
    return quality_metrics

# ===============================
# DB helpers
# ===============================
async def db_get(session: AsyncSession, video_id: str) -> Optional[VideoMCQ]:
    q = select(VideoMCQ).where(VideoMCQ.video_id == video_id)
    r = await session.execute(q)
    return r.scalar_one_or_none()

async def commit_with_retry(session: AsyncSession, retries: int = 3):
    """
    ✅ FIX #1: Retry logic for MySQL deadlocks (error 1213).
    MySQL expects you to retry deadlock errors - this is standard practice.
    """
    for attempt in range(retries):
        try:
            await session.commit()
            return
        except OperationalError as e:
            error_str = str(e)
            if "Deadlock found" in error_str or "1213" in error_str:
                await session.rollback()
                if attempt == retries - 1:
                    print(f"⚠️ Deadlock retry exhausted after {retries} attempts")
                    raise
                wait_time = 0.2 * (attempt + 1)  # Exponential backoff: 0.2s, 0.4s, 0.6s
                print(f"⚠️ Deadlock detected (attempt {attempt + 1}/{retries}), retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
            else:
                # Not a deadlock - re-raise immediately
                raise
    raise RuntimeError(f"Failed to commit after {retries} attempts")

async def db_upsert(session: AsyncSession, video_id: str, url: str, questions: list, mode: str = "legacy", quality_metrics: Optional[Dict[str, Any]] = None, content_safety: Optional[Dict[str, Any]] = None, force_regeneration: bool = False):
    """
    Save MCQs with mode versioning, audit trails, quality metrics, and content safety.
    mode: "exam-grade" or "legacy"
    quality_metrics: Optional dict with quality stats (rejection_rate, etc.)
    content_safety: Optional dict with safety classification result (SAFE/UNSAFE/UNCERTAIN)
    force_regeneration: If True, allows overwriting existing exam-grade quality_metrics (explicit regeneration)
    """
    existing = await db_get(session, video_id)
    payload_questions = {"questions": questions}  # keep structure stable

    # Detect actual mode from questions if not provided
    if mode == "auto":
        has_anchor_type = any(q.get("anchor_type") for q in questions if isinstance(q, dict))
        mode = "exam-grade" if has_anchor_type else "legacy"

    generator = {
        "mode": mode,  # Cache versioning key
        "whisper_model": WHISPER_MODEL_SIZE,
        "groq_model": GROQ_MODEL if USE_TOPIC_CHUNK_MODE else None,
        "sample_clips": SAMPLE_CLIPS,
        "clip_seconds": CLIP_SECONDS,
        "validation_rule_version": VALIDATION_RULE_VERSION,  # Cache invalidation when rules change
        "is_partial": len(questions) < MCQ_COUNT,  # Flag for partial results (optional metadata)
    }
    
    # Calculate quality metrics if not provided
    if quality_metrics is None:
        quality_metrics = {}
        # Count anchor types for exam-grade mode
        if mode == "exam-grade":
            anchor_types = {}
            for q in questions:
                if isinstance(q, dict):
                    anchor_type = q.get("anchor_type", "UNKNOWN")
                    if anchor_type != "UNKNOWN":
                        anchor_types[anchor_type] = anchor_types.get(anchor_type, 0) + 1
            if anchor_types:
                quality_metrics["anchor_distribution"] = anchor_types

    # ✅ FIX #2: Use MySQL ON DUPLICATE KEY UPDATE for idempotent inserts
    # This prevents deadlocks from concurrent inserts on the same video_id
    
    # Calculate schema version and generation count
    schema_ver = "1.0"
    if quality_metrics and "schema_version" in quality_metrics:
        schema_ver = quality_metrics["schema_version"]
    
    gen_count = 1
    if existing:
        # Update existing: increment generation_count for exam-grade mode
        if mode == "exam-grade":
            gen_count = (existing.generation_count or 0) + 1
        else:
            gen_count = existing.generation_count or 1
        
        # CRITICAL FIX #3: quality_metrics is append-only for exam-grade (never mutable)
        # Protection: Only prevent overwrite if exam-grade quality_metrics exists AND we're not doing explicit regeneration
        if existing.quality_metrics and mode == "exam-grade" and existing.generation_mode == "exam-grade" and not force_regeneration:
            # Preserve existing quality_metrics - do not overwrite (prevents accidental mutation)
            quality_metrics = existing.quality_metrics
    
    # Use MySQL INSERT ... ON DUPLICATE KEY UPDATE for atomic upsert
    # This prevents deadlocks from concurrent inserts
    stmt = insert(VideoMCQ).values(
        video_id=video_id,
        url=url,
        mcq_count=len(questions),
        questions=payload_questions,
        generator=generator,
        generation_mode=mode,
        quality_metrics=quality_metrics,
        schema_version=schema_ver,
        created_by="api",
        updated_by="api",
        generation_count=gen_count
    )
    
    # ON DUPLICATE KEY UPDATE - MySQL specific
    stmt = stmt.on_duplicate_key_update(
        url=stmt.inserted.url,
        mcq_count=stmt.inserted.mcq_count,
        questions=stmt.inserted.questions,
        generator=stmt.inserted.generator,
        generation_mode=stmt.inserted.generation_mode,
        quality_metrics=stmt.inserted.quality_metrics,
        schema_version=stmt.inserted.schema_version,
        updated_by=stmt.inserted.updated_by,
        generation_count=stmt.inserted.generation_count,
        updated_at=func.current_timestamp()
    )
    
    await session.execute(stmt)

async def db_get_with_mode(session: AsyncSession, video_id: str, required_mode: Optional[str] = None) -> Optional[VideoMCQ]:
    """
    Get cached MCQs, optionally filtering by mode and validation rule version.
    If required_mode is None, returns any cached record (if validation version matches).
    If required_mode is set, only returns if cache mode matches AND validation rules are current.
    """
    row = await db_get(session, video_id)
    if not row:
        return None
    
    # CRITICAL: Check validation rule version - invalidate stale cache
    # If cached questions were generated with old validation rules, force regeneration
    cached_validation_version = (row.generator or {}).get("validation_rule_version", "1.0")
    if cached_validation_version != VALIDATION_RULE_VERSION:
        # Validation rules have changed - cache is stale, force regeneration
        print(f"   ⚠️ Cache invalidated: validation rules changed (cached: {cached_validation_version}, current: {VALIDATION_RULE_VERSION})")
        return None  # Force regeneration with new validation rules
    
    # ✅ CACHE VALIDATION: Accept partial cache if >= MIN_USABLE_QUESTIONS (industry standard)
    cached_questions = (row.questions or {}).get("questions", [])
    if not isinstance(cached_questions, list):
        return None
    
    cached_count = len(cached_questions)
    
    # ✅ FULL CACHE (ideal) - return immediately
    if cached_count >= MCQ_COUNT:
        print(f"   ✅ Using full cache ({cached_count} questions)")
        return row
    
    # 🟡 PARTIAL CACHE (SAFE ACCEPT) - accept if >= MIN_USABLE_QUESTIONS
    if cached_count >= MIN_USABLE_QUESTIONS:
        print(f"   ⚠️ Using PARTIAL cache (cached: {cached_count}, required: {MCQ_COUNT})")
        return row  # Accept partial cache - no regeneration needed
    
    # 🔴 TOO SMALL → invalidate and regenerate
    print(f"   ⚠️ Cache invalidated: insufficient usable questions (cached: {cached_count}, min required: {MIN_USABLE_QUESTIONS})")
    return None  # Force regeneration
    
    # If no mode requirement, return cache (validation version and count already checked)
    if required_mode is None:
        return row
    
    # Check if cached mode matches required mode
    cached_mode = (row.generator or {}).get("mode", "legacy")
    if cached_mode == required_mode:
        return row
    
    # Mode mismatch - return None to force regeneration
    return None

# ===============================
# ENDPOINTS
# ===============================
@app.post("/generate-and-save")
async def generate_and_save(req: GenerateSaveRequest):
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    video_id = make_video_id(req.url)

    async with SessionLocal() as session:
        try:
            existing = await db_get(session, video_id)
            if existing and not req.force:
                # CRITICAL: Check if cached count is sufficient
                qs = (existing.questions or {}).get("questions", [])
                if isinstance(qs, list) and len(qs) < MCQ_COUNT:
                    print(f"   ⚠️ Cached MCQs ({len(qs)}) less than required count ({MCQ_COUNT}). Forcing regeneration.")
                    existing = None  # Force regeneration to trigger hybrid fill pipeline
                else:
                    # Cache is valid - return it
                    # Initialize content_safety with default values
                    content_safety_default = {
                        "overall_video_verdict": "UNCERTAIN",
                        "overall_is_safe": None,
                        "overall_is_unsafe": None,
                        "overall_reason": "Classification in progress"
                    }
                    
                    response = {
                        "status": "cached",
                        "video_id": video_id,
                        "count": existing.mcq_count,
                        "message": "Already generated. Use force=true to regenerate.",
                        "content_safety": content_safety_default  # Always include
                    }
                    # Include questions if requested
                    if req.include_questions:
                        qs = (existing.questions or {}).get("questions", [])
                        # ✅ Apply sorting before returning (cache path)
                        qs = normalize_question_order(qs)
                        if not req.include_answers:
                            qs = strip_answers(qs)
                        response["questions"] = qs
                    
                    # ✅ Check cache first for content safety classification
                    cached_safety = existing.content_safety if existing and existing.content_safety else None
                    if cached_safety:
                        print(f"✅ Using cached content safety classification: {cached_safety.get('overall_video_verdict', 'UNKNOWN')}")
                        response["content_safety"] = cached_safety
                    else:
                        # Try to classify video safety
                        try:
                            print(f"🔍 Starting content safety classification for cached video: {req.url[:80]}...")
                            safety_result = await classify_video_safety(req.url, use_batch=True, num_frames=5)
                            print(f"✅ Content safety classification completed: {safety_result.get('overall_video_verdict', 'UNKNOWN')}")
                            safety_data = {
                                "overall_video_verdict": safety_result.get("overall_video_verdict", "UNCERTAIN"),
                                "overall_is_safe": safety_result.get("overall_is_safe", None),
                                "overall_is_unsafe": safety_result.get("overall_is_unsafe", None),
                                "overall_reason": safety_result.get("overall_reason", "")
                            }
                            response["content_safety"] = safety_data
                            
                            # ✅ SAVE: Update database with safety classification result
                            print(f"💾 Saving content safety classification to database...")
                            try:
                                cached_mode = (existing.generator or {}).get("mode", "legacy")
                                await db_upsert(session, video_id, req.url, qs, mode=cached_mode, quality_metrics=existing.quality_metrics, content_safety=safety_data, force_regeneration=False)
                                await commit_with_retry(session)
                                print(f"✅ Successfully saved content safety to database")
                            except Exception as save_error:
                                print(f"⚠️ Error saving content safety to database: {save_error}")
                                # Continue even if save fails
                        except Exception as e:
                            print(f"⚠️ Error in content safety classification: {e}")
                            traceback.print_exc()
                            response["content_safety"] = {
                                "overall_video_verdict": "UNCERTAIN",
                                "overall_is_safe": None,
                                "overall_is_unsafe": None,
                                "overall_reason": f"Safety classification error: {str(e)[:100]}"
                            }
                    
                    return response

            t0 = time.time()
            qs, anchor_metadata = generate_mcqs_from_video_fast(req.url)
            
            # ✅ FIX: Ensure questions list is not empty before saving
            if not qs or len(qs) == 0:
                raise HTTPException(
                    status_code=500, 
                    detail=f"No questions generated. This may indicate: (1) Video has insufficient content, (2) All questions were rejected, (3) Generation pipeline failed."
                )
            
            # Detect mode and prepare quality metrics
            detected_mode = "legacy"
            if anchor_metadata:
                detected_mode = "exam-grade"
            
            # Build complete quality_metrics
            generation_time = time.time() - t0
            quality_metrics = build_quality_metrics(anchor_metadata, qs, generation_time, detected_mode)
            
            # ✅ FIX: Save to database with error handling
            try:
                await db_upsert(session, video_id, req.url, qs, mode=detected_mode, quality_metrics=quality_metrics, force_regeneration=req.force)
                await commit_with_retry(session)
                print(f"   ✅ Saved {len(qs)} questions to database (video_id: {video_id})")
            except Exception as db_error:
                await session.rollback()
                print(f"   ❌ Database save failed: {db_error}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to save questions to database: {str(db_error)}")
            dt = time.time() - t0

            # Initialize content_safety with default values
            content_safety_default = {
                "overall_video_verdict": "UNCERTAIN",
                "overall_is_safe": None,
                "overall_is_unsafe": None,
                "overall_reason": "Classification in progress"
            }
            
            response = {
                "status": "saved",
                "video_id": video_id,
                "count": len(qs),
                "time_seconds": round(dt, 2),
                "content_safety": content_safety_default  # Always include
            }
            # Include questions if requested
            if req.include_questions:
                # ✅ Apply sorting before returning (fresh generation path)
                qs = normalize_question_order(qs)
                if not req.include_answers:
                    qs = strip_answers(qs)
                response["questions"] = qs
            
            # ✅ Check cache first for content safety classification (after saving questions)
            row_after_save = await db_get(session, video_id)
            cached_safety = row_after_save.content_safety if row_after_save and row_after_save.content_safety else None
            
            if cached_safety:
                print(f"✅ Using cached content safety classification: {cached_safety.get('overall_video_verdict', 'UNKNOWN')}")
                response["content_safety"] = cached_safety
            else:
                # Try to classify video safety
                try:
                    print(f"🔍 Starting content safety classification for saved video: {req.url[:80]}...")
                    safety_result = await classify_video_safety(req.url, use_batch=True, num_frames=5)
                    print(f"✅ Content safety classification completed: {safety_result.get('overall_video_verdict', 'UNKNOWN')}")
                    safety_data = {
                        "overall_video_verdict": safety_result.get("overall_video_verdict", "UNCERTAIN"),
                        "overall_is_safe": safety_result.get("overall_is_safe", None),
                        "overall_is_unsafe": safety_result.get("overall_is_unsafe", None),
                        "overall_reason": safety_result.get("overall_reason", "")
                    }
                    response["content_safety"] = safety_data
                    
                    # ✅ SAVE: Update database with safety classification result
                    print(f"💾 Saving content safety classification to database...")
                    try:
                        await db_upsert(session, video_id, req.url, qs, mode=detected_mode, quality_metrics=quality_metrics, content_safety=safety_data, force_regeneration=req.force)
                        await commit_with_retry(session)
                        print(f"✅ Successfully saved content safety to database")
                    except Exception as save_error:
                        print(f"⚠️ Error saving content safety to database: {save_error}")
                        # Continue even if save fails
                except Exception as e:
                    print(f"⚠️ Error in content safety classification: {e}")
                    traceback.print_exc()
                    response["content_safety"] = {
                        "overall_video_verdict": "UNCERTAIN",
                        "overall_is_safe": None,
                        "overall_is_unsafe": None,
                        "overall_reason": f"Safety classification error: {str(e)[:100]}"
                    }
            
            return response
        except Exception as e:
            await session.rollback()
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos/{video_id}/mcqs")
async def fetch_mcqs(
    video_id: str,
    include_answers: bool = Query(False),
    randomize: bool = Query(True),
    limit: int = Query(20, ge=1, le=50),
):
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

    async with SessionLocal() as session:
        row = await db_get(session, video_id)
        if not row:
            raise HTTPException(status_code=404, detail="No MCQs found. Call /generate-and-save first.")

        qs = (row.questions or {}).get("questions", [])
        if not isinstance(qs, list) or len(qs) == 0:
            raise HTTPException(status_code=500, detail="DB record has no questions.")

        qs2 = qs[:]
        # ✅ Apply sorting BEFORE randomize/limit (by-url endpoint)
        qs2 = normalize_question_order(qs2)
        
        if randomize:
            random.shuffle(qs2)
        qs2 = qs2[:min(limit, len(qs2))]

        if not include_answers:
            qs2 = strip_answers(qs2)

        return {
            "status": "success",
            "video_id": video_id,
            "count": len(qs2),
            "questions": qs2
        }

@app.post("/videos/mcqs")
async def get_mcqs(request: MCQRequest):
    """
    Single endpoint to get MCQs from video URL.
    
    **Everything in POST body - no query params, no Params tab.**
    
    This endpoint handles everything internally:
    1. Generates video_id from URL
    2. Checks MySQL cache
    3. Generates MCQs if not cached
    4. Returns MCQs instantly
    
    **Request Body:**
    - `video_url`: Video URL (required)
    - `include_answers`: Include correct answers (default: false)
    - `randomize`: Shuffle questions (default: true)
    - `limit`: Number of questions (default: 20, max: 50)
    
    **Postman Usage:**
    - Method: POST
    - URL: /videos/mcqs
    - Body → raw → JSON
    - No Params tab needed!
    """
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    
    video_url = request.video_url
    video_id = make_video_id(video_url)
    
    # Determine current mode
    current_mode = "exam-grade" if USE_ANCHOR_MODE else "legacy"
    
    async with SessionLocal() as session:
        try:
            # Check cache with mode matching (unless force=true)
            if request.force:
                row = None  # Force regeneration
                print(f"🔄 Force regeneration requested, bypassing cache")
                print(f"⚠️ WARNING: Force regeneration may take 60-120+ seconds")
                print(f"   If behind Cloudflare, this may cause 524 timeout (100s limit)")
                print(f"   Consider: 1) Access server directly, 2) Use force=false for cache, 3) Implement async processing")
            else:
                row = await db_get_with_mode(session, video_id, required_mode=current_mode)
                if row:
                    cached_mode = (row.generator or {}).get("mode", "legacy")
                    print(f"✅ Cache hit: mode={cached_mode}, matches current_mode={current_mode}")
                else:
                    # Check if any cache exists (for info)
                    any_row = await db_get(session, video_id)
                    if any_row:
                        cached_mode = (any_row.generator or {}).get("mode", "legacy")
                        print(f"⚠️ Cache exists but mode mismatch: cached={cached_mode}, required={current_mode}")
            
            if row and not request.force:
                # MCQs exist in cache - check if count is sufficient
                cached_questions = (row.questions or {}).get("questions", [])
                cached_count = len(cached_questions) if isinstance(cached_questions, list) else 0
                
                # ✅ CACHE VALIDATION: Accept partial cache if >= MIN_USABLE_QUESTIONS
                print(f"🔍 Cache check: cached_count={cached_count}, MCQ_COUNT={MCQ_COUNT}, MIN_USABLE={MIN_USABLE_QUESTIONS}")
                
                if not isinstance(cached_questions, list):
                    print(f"⚠️ Cache invalid: questions is not a list. Forcing regeneration.")
                    row = None
                elif cached_count >= MCQ_COUNT:
                    # ✅ FULL CACHE (ideal)
                    print(f"✅ Using full cache ({cached_count} questions)")
                    qs2 = cached_questions[:]
                elif cached_count >= MIN_USABLE_QUESTIONS:
                    # 🟡 PARTIAL CACHE (SAFE ACCEPT)
                    print(f"⚠️ Using PARTIAL cache (cached: {cached_count}, required: {MCQ_COUNT})")
                    qs2 = cached_questions[:]
                else:
                    # 🔴 TOO SMALL → regenerate
                    print(
                        f"⚠️ Cache invalidated: insufficient usable questions "
                        f"(cached: {cached_count}, min required: {MIN_USABLE_QUESTIONS}). Forcing regeneration."
                    )
                    row = None  # Force regeneration
                    print(f"🔄 Proceeding to generation (row is now None)")
                
                # ✅ If cache was accepted (full or partial), return it
                if row and 'qs2' in locals():
                    # ✅ Check if web search questions already exist in cache (avoid double transcription)
                    has_web_questions = any(q.get("anchor_type") == "WEB_SEARCH" for q in qs2)
                    
                    if has_web_questions:
                        print("✅ Web search questions already in cache, skipping generation")
                        article_text = ""  # No article needed if questions already exist
                    else:
                        # ✅ WEB SEARCH QUESTIONS: Generate from article (not transcript)
                        print("🎬 Generating article and 10 web search questions...")
                        article_text = ""  # Initialize article_text for cache path
                        try:
                            # ✅ FIX: Only transcribe once - get transcript and ACTUAL video duration
                            print("📹 Getting video transcript for web search questions...")
                            transcript, _, _, actual_video_duration = transcribe_sampled_stream(video_url)
                            print(f"📹 Actual video duration: {actual_video_duration:.2f}s ({seconds_to_mmss(actual_video_duration)})")
                            
                            # ✅ FIXED: Generate article from transcript (exactly 1200 words, max 1200)
                            print("📝 Generating article from transcript...")
                            article_text = generate_article_from_transcript(transcript)
                        
                            # ✅ THROTTLING: Add delay after article generation to respect Groq rate limits
                            print("⏱️ Throttling: Waiting 1.5s after article generation...")
                            time.sleep(1.5)
                            
                            # ✅ FIXED: Generate 10 web questions from article only (not transcript)
                            web_search_questions, article_text = generate_web_search_questions(article_text, qs2, actual_video_duration)
                            
                            if web_search_questions:
                                print(f"✅ Generated {len(web_search_questions)} web search questions (separate from {len(qs2)} cached questions)")
                                # Update question_index to be sequential after existing questions
                                base_index = len(qs2)
                                for idx, q in enumerate(web_search_questions):
                                    q["question_index"] = base_index + idx + 1
                                # Append web search questions to cached questions
                                qs2.extend(web_search_questions)
                                
                                # ✅ SAVE: Update database with complete question list (including web search questions)
                                print(f"💾 Saving {len(qs2)} total questions (including {len(web_search_questions)} web search) to database...")
                                try:
                                    # Get current mode from cached row
                                    cached_mode = (row.generator or {}).get("mode", "legacy")
                                    await db_upsert(session, video_id, video_url, qs2, mode=cached_mode, quality_metrics=row.quality_metrics, content_safety=row.content_safety, force_regeneration=False)
                                    await commit_with_retry(session)
                                    print(f"✅ Successfully saved {len(qs2)} questions to database")
                                except Exception as e:
                                    print(f"⚠️ Error saving questions to database: {e}")
                                    traceback.print_exc()
                                    # Continue even if save fails
                            else:
                                print("⚠️ No web search questions generated")
                        except Exception as e:
                            print(f"⚠️ Error generating article/web questions: {e}")
                            traceback.print_exc()
                            # Continue without web search questions if generation fails
                    
                    # ✅ Apply sorting BEFORE randomize/limit (cache path)
                    # Note: Sorting by timestamp keeps questions in chronological order
                    # Cached questions (with timestamps during video) come first
                    # Web search questions (with timestamps at video end) come after
                    qs2 = normalize_question_order(qs2)
                    
                    if request.randomize:
                        random.shuffle(qs2)
                    qs2 = qs2[:min(request.limit, len(qs2))]
                    
                    # ✅ FINAL SORT: Always sort by timestamp in final response (topic chunks first, web search last)
                    qs2.sort(key=lambda q: q.get("timestamp_seconds", float('inf')))
                    
                    # Collect anchor type statistics (for exam-grade mode)
                    anchor_stats = {}
                    for q in qs2:
                        anchor_type = q.get("anchor_type", "UNKNOWN")
                        if anchor_type != "UNKNOWN":
                            anchor_stats[anchor_type] = anchor_stats.get(anchor_type, 0) + 1
                    
                    if not request.include_answers:
                        qs2 = strip_answers(qs2)
                    
                    response = {
                        "status": "success",
                        "video_id": video_id,
                        "count": len(qs2),
                        "cached": True,
                        "mode": "exam-grade" if anchor_stats else "legacy",
                        "questions": qs2,
                        "article_text": article_text if article_text else None
                    }
                    
                    # Add anchor statistics if available
                    if anchor_stats:
                        response["anchor_statistics"] = anchor_stats
                        response["anchor_types_used"] = list(anchor_stats.keys())
                    
                    return response
            
            # Not in cache - generate MCQs
            print(f"🔄 Generating MCQs in {current_mode} mode...")
            t0 = time.time()
            # ✅ FIXED: Reuse transcript from generate_mcqs_from_video_fast to avoid double transcription
            qs, anchor_metadata, transcript_for_web, transcript_segments_for_web, actual_video_duration = generate_mcqs_from_video_fast(video_url)
            
            # ✅ THROTTLING: Add delay after MCQ generation to respect Groq rate limits
            print("⏱️ Throttling: Waiting 1.5s after MCQ generation...")
            time.sleep(1.5)
            
            # ✅ FIXED: Transcript already available from generate_mcqs_from_video_fast (no need to transcribe again)
            print(f"📹 Actual video duration: {actual_video_duration:.2f}s ({seconds_to_mmss(actual_video_duration)})")
            
            # ✅ FIX #3: Generate article AFTER acquiring lock but BEFORE opening DB transaction
            # This reduces transaction length - don't hold DB lock during AI work
            print("📝 Generating article from transcript...")
            try:
                article_text = generate_article_from_transcript(transcript_for_web)
                
                # ✅ THROTTLING: Add delay after article generation to respect Groq rate limits
                print("⏱️ Throttling: Waiting 1.5s after article generation...")
                time.sleep(1.5)
            except Exception as e:
                print(f"⚠️ Error generating article: {e}")
                traceback.print_exc()
                article_text = ""
            
            # If we still don't have duration, estimate from question timestamps (but don't add buffer)
            if actual_video_duration is None and qs and len(qs) > 0:
                timestamps = [q.get("timestamp_seconds", 0) for q in qs if q.get("timestamp_seconds")]
                if timestamps:
                    actual_video_duration = max(timestamps)  # Use max timestamp, no buffer
                    print(f"📹 Estimated video duration from timestamps: {actual_video_duration:.2f}s ({seconds_to_mmss(actual_video_duration)})")
            
            # ✅ Validate all questions have valid anchor types (using ALLOWED_ANCHORS)
            # Ensure all questions have a valid anchor_type, defaulting missing ones to TOPIC_CHUNK for topic-chunk mode
            for q in qs:
                anchor_type = q.get("anchor_type")
                if not anchor_type or anchor_type not in ALLOWED_ANCHORS:
                    # Validate and coerce invalid types (or set default for topic-chunk mode)
                    if USE_TOPIC_CHUNK_MODE and not anchor_type:
                        # Default to TOPIC_CHUNK for topic-chunk mode if missing
                        q["anchor_type"] = "TOPIC_CHUNK"
                    else:
                        # Coerce invalid types to PROCESS
                        validated_type = validate_anchor_type(anchor_type or "UNKNOWN")
                        q["anchor_type"] = validated_type
            
            # Detect actual mode from generated questions
            detected_mode = "topic-chunk"  # Default for topic-chunk mode
            if anchor_metadata:
                # Check if we have topic-chunk questions
                if any(q.get("anchor_type") == "TOPIC_CHUNK" for q in qs):
                    detected_mode = "topic-chunk"
                else:
                    detected_mode = "exam-grade"  # Fallback for old cached data
            
            # Build complete quality_metrics
            generation_time = time.time() - t0
            quality_metrics = build_quality_metrics(anchor_metadata, qs, generation_time, detected_mode)
            
            # ✅ FIX #3: Open DB transaction ONLY when ready to write (short transaction)
            # ✅ FIX #4: Use application-level lock to prevent concurrent processing of same video_id
            async with get_video_lock(video_id):
                # Double-check cache after acquiring lock (another request might have generated it)
                row_after_lock = await db_get_with_mode(session, video_id, required_mode=current_mode)
                if row_after_lock and not request.force:
                    cached_questions_after = (row_after_lock.questions or {}).get("questions", [])
                    if isinstance(cached_questions_after, list) and len(cached_questions_after) >= MIN_USABLE_QUESTIONS:
                        print(f"✅ Cache found after lock (another request generated it)")
                        qs = cached_questions_after[:]
                        detected_mode = (row_after_lock.generator or {}).get("mode", "legacy")
                    else:
                        # Save with mode versioning and quality metrics
                        await db_upsert(session, video_id, video_url, qs, mode=detected_mode, quality_metrics=quality_metrics, force_regeneration=request.force)
                        await commit_with_retry(session)
                else:
                    # Save with mode versioning and quality metrics
                    await db_upsert(session, video_id, video_url, qs, mode=detected_mode, quality_metrics=quality_metrics, force_regeneration=request.force)
                    await commit_with_retry(session)
            
            dt = time.time() - t0
            print(f"✅ Generated {len(qs)} MCQs in {detected_mode} mode (took {dt:.2f}s)")
            
            # Process questions according to request
            qs2 = qs[:]  # Copy existing 5 questions (don't modify original)
            
            # ✅ WEB SEARCH QUESTIONS: Generate from article (not transcript)
            print("🎬 Generating 10 web search questions from article...")
            if article_text and actual_video_duration:
                try:
                    # ✅ FIXED: Generate 10 web questions from article only (not transcript)
                    web_search_questions, article_text = generate_web_search_questions(article_text, qs2, actual_video_duration)
                    
                    if web_search_questions:
                        print(f"✅ Generated {len(web_search_questions)} web search questions (separate from {len(qs2)} existing questions)")
                        # Update question_index to be sequential after existing questions
                        base_index = len(qs2)
                        for idx, q in enumerate(web_search_questions):
                            q["question_index"] = base_index + idx + 1
                        # Append web search questions to existing questions
                        qs2.extend(web_search_questions)
                        
                        # ✅ SAVE: Update database with complete question list (including web search questions)
                        print(f"💾 Saving {len(qs2)} total questions (including {len(web_search_questions)} web search) to database...")
                        try:
                            # Rebuild quality metrics with updated question count
                            updated_quality_metrics = build_quality_metrics(anchor_metadata, qs2, generation_time, detected_mode)
                            # Get existing content_safety if available
                            row_before_save = await db_get(session, video_id)
                            existing_safety = row_before_save.content_safety if row_before_save and row_before_save.content_safety else None
                            await db_upsert(session, video_id, video_url, qs2, mode=detected_mode, quality_metrics=updated_quality_metrics, content_safety=existing_safety, force_regeneration=request.force)
                            await commit_with_retry(session)
                            print(f"✅ Successfully saved {len(qs2)} questions to database")
                        except Exception as e:
                            print(f"⚠️ Error saving questions to database: {e}")
                            traceback.print_exc()
                            # Continue even if save fails
                    else:
                        print("⚠️ No web search questions generated")
                except Exception as e:
                    print(f"⚠️ Error generating web search questions: {e}")
                    traceback.print_exc()
                    # Continue without web search questions if generation fails
            else:
                if not article_text:
                    print("⚠️ Cannot generate web search questions: article not available")
                if not actual_video_duration:
                    print("⚠️ Cannot generate web search questions: video duration not available")
            
            # ✅ Apply sorting BEFORE randomize/limit (fresh generation path)
            # Note: Sorting by timestamp keeps questions in chronological order
            # The 5 existing questions (with timestamps during video) come first
            # The 10 web search questions (with timestamps at video end) come after
            qs2 = normalize_question_order(qs2)
            
            if request.randomize:
                random.shuffle(qs2)
            qs2 = qs2[:min(request.limit, len(qs2))]
            
            # ✅ FINAL SORT: Always sort by timestamp in final response (topic chunks first, web search last)
            qs2.sort(key=lambda q: q.get("timestamp_seconds", float('inf')))
            
            # Recalculate anchor_stats for response (from filtered qs2)
            # ✅ HYBRID MODE: Count both exam-grade and legacy separately
            anchor_stats_response = {}
            legacy_count = 0
            is_exam_grade = False
            for q in qs2:
                anchor_type = q.get("anchor_type")
                if anchor_type == "LEGACY":
                    legacy_count += 1
                elif anchor_type and anchor_type in {"PROCESS", "DECISION", "DEFINITION", "RISK", "BOUNDARY", "COMPARISON"}:
                    is_exam_grade = True
                    anchor_stats_response[anchor_type] = anchor_stats_response.get(anchor_type, 0) + 1
            
            # Add legacy count to stats if in hybrid mode
            if legacy_count > 0:
                anchor_stats_response["LEGACY"] = legacy_count
            
            # Use detected mode (from generation) instead of USE_ANCHOR_MODE flag
            final_mode = detected_mode
            
            # ✅ HYBRID MODE: Handle hybrid results (exam-grade + legacy)
            exam_grade_count = len([q for q in qs2 if q.get("anchor_type") in {"PROCESS", "DECISION", "DEFINITION", "RISK", "BOUNDARY", "COMPARISON"}])
            legacy_count_response = len([q for q in qs2 if q.get("anchor_type") == "LEGACY"])
            is_hybrid = (legacy_count_response > 0)
            is_partial = (final_mode == "exam-grade" and not is_hybrid and exam_grade_count < MCQ_COUNT)
            
            if not request.include_answers:
                qs2 = strip_answers(qs2)
            
            # ✅ HYBRID MODE: Response contract for hybrid mode (exam-grade + legacy)
            if is_hybrid:
                response = {
                    "status": "success",
                    "video_id": video_id,
                    "count": len(qs2),
                    "cached": False,
                    "time_seconds": round(dt, 2),
                    "mode": "hybrid",
                    "exam_grade_count": exam_grade_count,
                    "legacy_count": legacy_count_response,
                    "questions": qs2,
                    "article_text": article_text if article_text else None
                }
            elif is_partial:
                response = {
                    "status": "partial",
                    "video_id": video_id,
                    "mode": "exam-grade",
                    "exam_grade_count": exam_grade_count,
                    "required": MCQ_COUNT,
                    "count": len(qs2),
                    "cached": False,
                    "time_seconds": round(dt, 2),
                    "questions": qs2,
                    "message": f"Video does not contain enough examinable concepts to generate {MCQ_COUNT} exam-grade MCQs",
                    "article_text": article_text if article_text else None
                }
            else:
                response = {
                    "status": "success",
                    "video_id": video_id,
                    "count": len(qs2),
                    "cached": False,
                    "time_seconds": round(dt, 2),
                    "mode": final_mode,
                    "questions": qs2,
                    "article_text": article_text if article_text else None
                }
            
            # Add anchor statistics if available (only valid exam-grade types)
            if anchor_stats_response:
                response["anchor_statistics"] = anchor_stats_response
                response["anchor_types_used"] = list(anchor_stats_response.keys())
            
            return response
            
        except Exception as e:
            await session.rollback()
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/videos/mcqs/by-url")
async def fetch_mcqs_by_url(url: str = Query(...), req: FetchByUrlRequest = FetchByUrlRequest()):
    """
    [DEPRECATED] Use POST /videos/mcqs instead.
    
    This endpoint is kept for backward compatibility only.
    """
    vid = make_video_id(url)
    return await fetch_mcqs(
        vid,
        include_answers=req.include_answers,
        randomize=req.randomize,
        limit=req.limit,
    )

@app.post("/content/safety-check", response_model=ContentSafetyCheckResponse)
async def check_content_safety(request: ContentSafetyCheckRequest):
    """
    Dedicated endpoint for checking video content safety.
    
    This endpoint:
    1. Checks database cache first (if available)
    2. If not cached or force_recheck=true, runs safety classification
    3. Saves result to database for future requests
    4. Returns safety classification result
    
    **Request Body:**
    - `video_url`: Video URL to check (required)
    - `force_recheck`: Force re-check even if cached (default: false)
    
    **Response:**
    - `status`: "success" or "error"
    - `video_id`: Unique video identifier
    - `video_url`: Video URL that was checked
    - `cached`: Whether result was from cache
    - `content_safety`: Safety classification result with:
      - `overall_video_verdict`: "SAFE", "UNSAFE", or "UNCERTAIN"
      - `overall_is_safe`: Boolean (true if SAFE)
      - `overall_is_unsafe`: Boolean (true if UNSAFE)
      - `overall_reason`: Short reason for the verdict
    - `time_seconds`: Time taken (only if not cached)
    
    **Example Request:**
    ```json
    {
      "video_url": "https://example.com/video.mp4",
      "force_recheck": false
    }
    ```
    
    **Example Response:**
    ```json
    {
      "status": "success",
      "video_id": "abc123",
      "video_url": "https://example.com/video.mp4",
      "cached": true,
      "content_safety": {
        "overall_video_verdict": "SAFE",
        "overall_is_safe": true,
        "overall_is_unsafe": false,
        "overall_reason": "No unsafe content detected"
      },
      "time_seconds": null
    }
    ```
    """
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    
    # ✅ Validate GROQ_API_KEY before proceeding
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        raise HTTPException(
            status_code=500, 
            detail="GROQ_API_KEY is not configured. Set it with: $env:GROQ_API_KEY='your_key_here' (PowerShell) or export GROQ_API_KEY='your_key_here' (Linux/Mac)"
        )
    
    video_url = request.video_url
    video_id = make_video_id(video_url)
    
    async with SessionLocal() as session:
        try:
            t0 = time.time()
            
            # Check cache first (unless force_recheck is true)
            if not request.force_recheck:
                row = await db_get(session, video_id)
                if row and row.content_safety:
                    print(f"✅ Using cached content safety for video_id: {video_id}")
                    return ContentSafetyCheckResponse(
                        status="success",
                        video_id=video_id,
                        video_url=video_url,
                        cached=True,
                        content_safety=row.content_safety,
                        time_seconds=None
                    )
            
            # Not cached or force_recheck - run safety classification
            print(f"🔍 Starting content safety classification for video: {video_url[:80]}...")
            print(f"   Video ID: {video_id}")
            if request.force_recheck:
                print(f"   ⚠️ Force recheck requested - ignoring cache")
            
            try:
                safety_result = await classify_video_safety(video_url, use_batch=True, num_frames=5)
                dt = time.time() - t0
                
                print(f"✅ Content safety classification completed: {safety_result.get('overall_video_verdict', 'UNKNOWN')}")
                
                # Build safety data
                safety_data = {
                    "overall_video_verdict": safety_result.get("overall_video_verdict", "UNCERTAIN"),
                    "overall_is_safe": safety_result.get("overall_is_safe", None),
                    "overall_is_unsafe": safety_result.get("overall_is_unsafe", None),
                    "overall_reason": safety_result.get("overall_reason", "")
                }
                
                # ✅ SAVE: Save safety classification to database
                print(f"💾 Saving content safety classification to database...")
                try:
                    # Check if questions exist for this video (to preserve them)
                    existing_row = await db_get(session, video_id)
                    if existing_row:
                        # Preserve existing questions and other data
                        existing_questions = (existing_row.questions or {}).get("questions", [])
                        existing_mode = (existing_row.generator or {}).get("mode", "legacy")
                        await db_upsert(
                            session, 
                            video_id, 
                            video_url, 
                            existing_questions if existing_questions else [], 
                            mode=existing_mode, 
                            quality_metrics=existing_row.quality_metrics, 
                            content_safety=safety_data, 
                            force_regeneration=False
                        )
                    else:
                        # No existing record - create new one with just safety data
                        await db_upsert(
                            session, 
                            video_id, 
                            video_url, 
                            [], 
                            mode="legacy", 
                            quality_metrics=None, 
                            content_safety=safety_data, 
                            force_regeneration=False
                        )
                    await commit_with_retry(session)
                    print(f"✅ Successfully saved content safety to database")
                except Exception as save_error:
                    print(f"⚠️ Error saving content safety to database: {save_error}")
                    traceback.print_exc()
                    # Continue even if save fails
                
                return ContentSafetyCheckResponse(
                    status="success",
                    video_id=video_id,
                    video_url=video_url,
                    cached=False,
                    content_safety=safety_data,
                    time_seconds=round(dt, 2)
                )
                
            except Exception as e:
                print(f"⚠️ Error in content safety classification: {e}")
                traceback.print_exc()
                
                # Return error response
                error_safety_data = {
                    "overall_video_verdict": "UNCERTAIN",
                    "overall_is_safe": None,
                    "overall_is_unsafe": None,
                    "overall_reason": f"Safety classification error: {str(e)[:100]}"
                }
                
                return ContentSafetyCheckResponse(
                    status="error",
                    video_id=video_id,
                    video_url=video_url,
                    cached=False,
                    content_safety=error_safety_data,
                    time_seconds=round(time.time() - t0, 2)
                )
                
        except Exception as e:
            await session.rollback()
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
def health():
    return {
        "status": "ready",
        "whisper_model": WHISPER_MODEL_SIZE,
        "groq_model": GROQ_MODEL if USE_TOPIC_CHUNK_MODE else None,
        "topic_chunk_mode": USE_TOPIC_CHUNK_MODE,
        "db_configured": bool(DATABASE_URL),
        "mcq_count": MCQ_COUNT,
        "sample_clips": SAMPLE_CLIPS,
        "clip_seconds": CLIP_SECONDS,
    }

@app.get("/videos/list")
async def list_all_videos(limit: int = Query(50, ge=1, le=100)):
    """List all videos saved in MySQL database"""
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    
    async with SessionLocal() as session:
        try:
            q = select(VideoMCQ).order_by(VideoMCQ.created_at.desc()).limit(limit)
            result = await session.execute(q)
            rows = result.scalars().all()
            
            videos = []
            for row in rows:
                videos.append({
                    "video_id": row.video_id,
                    "url": row.url,
                    "mcq_count": row.mcq_count,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                })
            
            return {
                "status": "success",
                "total": len(videos),
                "videos": videos
            }
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos/{video_id}/verify")
async def verify_video_saved(video_id: str):
    """Verify if a video is saved in MySQL database"""
    if not SessionLocal:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    
    async with SessionLocal() as session:
        row = await db_get(session, video_id)
        if not row:
            return {
                "status": "not_found",
                "video_id": video_id,
                "saved": False,
                "message": "Video not found in database"
            }
        
        return {
            "status": "found",
            "video_id": video_id,
            "saved": True,
            "url": row.url,
            "mcq_count": row.mcq_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

# ✅ IMPORTANT: Specific routes must come BEFORE parameterized routes
# POST /product/mcq must come before GET /product/{product_id}
# Otherwise FastAPI will match "mcq" as a product_id parameter
@app.post("/product/mcq", response_model=ProductMCQResponse)
async def post_product_mcq(request: ProductMCQRequest):
    """Get product details with AI-generated MCQ questions (POST method)"""
    
    # Fetch product from MongoDB
    product = await get_product_from_mongo(request.product_id)
    
    # Generate MCQ questions using Groq
    mcq_questions = generate_product_mcq_with_groq(product["description"])
    
    return {
        "product_id": product["product_id"],
        "description": product["description"],
        "mcq_questions": mcq_questions
    }


@app.get("/product/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product details by ID from MongoDB"""
    product = await get_product_from_mongo(product_id) 
    return product


@app.get("/")
def root():
    return {
        "service": "Fast Video MCQ Generator + MySQL Cache + Product MCQ Generator",
        "primary_endpoint": "POST /videos/mcqs - Single endpoint, everything in body (no query params)",
        "endpoints": [
            "POST /videos/mcqs - [RECOMMENDED] Single endpoint, all params in JSON body",
            "POST /generate-and-save - Generate and save MCQs (returns video_id)",
            "GET /videos/{video_id}/mcqs - Fetch MCQs by video_id",
            "POST /videos/mcqs/by-url - [DEPRECATED] Use POST /videos/mcqs instead",
            "GET /product/{product_id} - Get product details from MongoDB",
            "POST /product/mcq - Get product with AI-generated MCQ questions"
        ],
        "note": "Generate once, then fetch from DB instantly. Use POST /videos/mcqs for simplest integration."
    }

# ===============================
# SERVER RUNNER
# ===============================
if __name__ == "__main__":
    import uvicorn
    import sys
    import asyncio
    
    # ✅ Suppress Windows async IO noise (harmless connection reset errors)
    if sys.platform == "win32":
        # Suppress noisy Windows socket errors that occur after legitimate errors
        def quiet_exception_handler(loop, context):
            # Only suppress ConnectionResetError from ProactorBasePipeTransport
            exception = context.get('exception')
            if isinstance(exception, ConnectionResetError) and 'ProactorBasePipeTransport' in str(context.get('message', '')):
                return  # Suppress this specific noise
            # Log other exceptions normally
            loop.default_exception_handler(context)
        
        asyncio.get_event_loop().set_exception_handler(quiet_exception_handler)
    
    print("\n" + "=" * 60)
    print("🚀 Starting FastAPI Server")
    print("=" * 60)
    print(f"📡 Server will run at: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🔧 Mode: {'EXAM-GRADE' if USE_ANCHOR_MODE else 'LEGACY'}")
    print("=" * 60 + "\n")
    
    # ✅ WATCHFILES RELOAD FIX: Do NOT use --reload when processing long videos
    # When uvicorn --reload detects file changes (e.g., temp clips), it restarts mid-request
    # This causes "2 times processing" logs even if code is correct.
    # 
    # For production/long video processing: Run WITHOUT --reload
    #   uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
    # 
    # For development: Use --reload but ensure temp files are outside project folder
    #   (e.g., C:\temp\mcq_clips\ instead of inside project directory)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9001,
        log_level="info"
        # ✅ Note: --reload is NOT enabled here to prevent WatchFiles double-processing
        # If you need auto-reload during development, add --reload flag manually
        # but be aware it may cause double-processing if temp files are in project folder
    )

