

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
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from faster_whisper import WhisperModel

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field

from sqlalchemy import String, Text, Integer, BigInteger, func, select, TIMESTAMP
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ===============================
# CONFIG
# ===============================
DATABASE_URL = os.getenv("DATABASE_URL", "")  # mysql+aiomysql://...

# MCQ Writer Model: qwen2.5:3b (upgraded from 1.5b for improved exam-language quality)
# Architecture unchanged - only language quality improves
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
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

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
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

# Legacy Fill Mode - Allow filling remaining MCQs with legacy chunks if exam-grade generation < target
# Set ALLOW_LEGACY_FILL=false for strict exam-grade mode (may return < 20 questions)
# ✅ FIX 1: Default to False for exam-grade mode (strict, no legacy leakage)
ALLOW_LEGACY_FILL = os.getenv("ALLOW_LEGACY_FILL", "false").lower() == "true"

# Print mode on startup for debugging
print(f"🔧 USE_ANCHOR_MODE = {USE_ANCHOR_MODE} ({'EXAM-GRADE' if USE_ANCHOR_MODE else 'LEGACY'})")
print(f"🤖 OLLAMA_MODEL = {OLLAMA_MODEL} (MCQ Writer Model)")
print(f"✅ VALIDATION_RULE_VERSION = {VALIDATION_RULE_VERSION} (Cache invalidation)")
print(f"📊 ALLOW_LEGACY_FILL = {ALLOW_LEGACY_FILL} ({'Practice Mode (always 20)' if ALLOW_LEGACY_FILL else 'Exam Mode (strict)'})")
print(f"🔄 USE_HYBRID_MODE = {USE_HYBRID_MODE} ({f'{EXAM_GRADE_COUNT} exam-grade + {LEGACY_COUNT} legacy' if USE_HYBRID_MODE else 'Pure mode'})")
print(f"📹 SAMPLE_CLIPS = {SAMPLE_CLIPS}, CLIP_SECONDS = {CLIP_SECONDS} (Total: ~{SAMPLE_CLIPS * CLIP_SECONDS}s)")
print(f"📝 MIN_TRANSCRIPT_WORDS = {MIN_TRANSCRIPT_WORDS} (Quality gate)")
print(f"⏱️ FFPROBE_TIMEOUT = {FFPROBE_TIMEOUT}s, FFPROBE_RETRIES = {FFPROBE_RETRIES} (Video metadata)")
print(f"🎬 FFMPEG_TIMEOUT = {FFMPEG_TIMEOUT_PER_CLIP}s, FFMPEG_RETRIES = {FFMPEG_RETRIES} (Clip extraction)")

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
# ===============================
def find_ollama() -> str | None:
    p = shutil.which("ollama")
    if p:
        return p
    try:
        r = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            return "ollama"
    except Exception:
        pass
    return None

OLLAMA_EXE = find_ollama()
if not OLLAMA_EXE:
    print("⚠️ WARNING: Ollama not found. Install Ollama and ensure `ollama` is in PATH.")

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

def safe_json_extract(s: str) -> dict:
    s = s.strip().replace("```json", "").replace("```", "").strip()
    a = s.find("{")
    b = s.rfind("}")
    if a == -1 or b <= a:
        raise ValueError("No JSON object found in model output")
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
    anchor_type = anchor.get("type", "UNKNOWN")
    
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
        anchor_type = anchor.get("type", "UNKNOWN")
        return f"{anchor_type.title()} Concept"
    
    # Extract meaningful words (3+ characters, alphabetic)
    words = re.findall(r"[A-Za-z]{3,}", text)
    
    # Take first 6 words for concise title
    title_words = words[:6]
    
    if not title_words:
        # Fallback to anchor type if no words found
        anchor_type = anchor.get("type", "UNKNOWN")
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
        anchor_type = anchor.get("type", "UNKNOWN")
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
    anchor_type = anchor.get("type", "DEFAULT")
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

def generate_mcqs_ollama_from_segments(segments: List[str]) -> List[Dict[str, Any]]:
    if not OLLAMA_EXE:
        raise RuntimeError("Ollama not found. Install Ollama and ensure `ollama` is on PATH.")

    all_cleaned: List[Dict[str, Any]] = []
    last_err = None
    max_rounds = max(3, MAX_RETRIES * 2)

    for round_idx in range(1, max_rounds + 1):
        missing = MCQ_COUNT - len(all_cleaned)
        if missing <= 0:
            return all_cleaned[:MCQ_COUNT]

        prompt = mcq_prompt_from_segments(segments, missing, start_index=len(all_cleaned) + 1)

        try:
            r = subprocess.run(
                [OLLAMA_EXE, "run", OLLAMA_MODEL],
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=OLLAMA_TIMEOUT,
            )

            if r.returncode != 0:
                last_err = f"Ollama returned code {r.returncode}: {r.stderr.decode('utf-8', errors='ignore')[:500]}"
                continue

            out = r.stdout.decode("utf-8", errors="ignore").strip()
            data = safe_json_extract(out)
            qs = data.get("questions", [])

            if not isinstance(qs, list):
                last_err = "Invalid JSON: `questions` is not a list"
                continue

            cleaned: List[Dict[str, Any]] = []
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

                cleaned.append({
                    "question": question_text,
                    "options": {"A": optA, "B": optB, "C": optC, "D": optD},
                    "correct_answer": ca
                })

            all_cleaned.extend(cleaned)
            all_cleaned = deduplicate_questions(all_cleaned)

            if len(all_cleaned) >= MCQ_COUNT:
                return all_cleaned[:MCQ_COUNT]

            last_err = f"After round {round_idx}, have {len(all_cleaned)} valid MCQs, need {MCQ_COUNT}"
            time.sleep(0.2 * round_idx)

        except subprocess.TimeoutExpired:
            last_err = f"Ollama timed out after {OLLAMA_TIMEOUT}s"
        except Exception as e:
            last_err = f"Ollama error: {e}"

    raise RuntimeError(last_err or "Failed to generate MCQs")

def fill_with_legacy_mcqs(
    transcript: str,
    existing_questions: List[Dict[str, Any]],
    target_count: int
) -> List[Dict[str, Any]]:
    """
    Fill remaining MCQs using legacy chunk-based generation.
    
    Production-grade fallback: Exam-grade first, legacy fill only if needed.
    Still applies deduplication and basic validation.
    
    This ensures we always return target_count questions while maintaining
    exam-grade integrity for anchor-based questions.
    """
    needed = target_count - len(existing_questions)
    if needed <= 0:
        return existing_questions
    
    print(f"   📊 Filling {needed} remaining MCQs using legacy chunk-based generation...")
    
    # Generate legacy MCQs from important chunks
    segments = pick_random_important_chunks(transcript)
    legacy_mcqs = generate_mcqs_ollama_from_segments(segments)
    
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
    if not OLLAMA_EXE:
        raise RuntimeError("Ollama not found. Install Ollama and ensure `ollama` is on PATH.")
    
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
        anchor_type = anchor.get("type", "DEFAULT")
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
        anchor_type = anchor.get("type", "DEFAULT")
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
                    r = subprocess.run(
                        [OLLAMA_EXE, "run", OLLAMA_MODEL],
                        input=prompt.encode("utf-8"),
                        capture_output=True,
                        timeout=OLLAMA_TIMEOUT,
                    )
                    
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
                            "anchor_type": anchor.get("type", "DEFAULT")  # Store anchor type for tracking
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
                            anchor_type_for_dedup = anchor.get("type", "DEFAULT")
                            
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
                                    "anchor_type": anchor.get("type", "DEFAULT"),
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
                                        "question_type": QUESTION_TYPE_MAP.get(anchor.get("type", "DEFAULT"), "recall"),
                                        "format": "mcq",
                                        "difficulty": "medium",  # Could be enhanced with actual difficulty detection
                                        "retry_variant_count": retries + 1,
                                        "questions_generated": 1  # Will be updated
                                    },
                                    "llm": {
                                        "generator_model": OLLAMA_MODEL,
                                        "critic_model": OLLAMA_MODEL,  # Same model used for both
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
def generate_mcqs_from_video_fast(video_url: str, use_anchors: Optional[bool] = None) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """
    Main pipeline: Video → Transcript → Anchors → MCQs
    
    Exam-grade mode (use_anchors=True):
    - Anchor detection (rules-based, no LLM)
    - Pedagogy engine (question type control)
    - 24-second context windows
    - LLM is just a writer, not decision maker
    
    Legacy mode (use_anchors=False):
    - Random important chunks
    - LLM decides everything
    
    Returns: (questions_list, anchor_metadata_list_or_None)
    """
    if use_anchors is None:
        use_anchors = USE_ANCHOR_MODE
    
    transcript, transcript_segments, clip_timestamps, video_duration = transcribe_sampled_stream(video_url)
    
    # ✅ CRITICAL FIX: Check segments first (source of truth), not word count
    # Segments matter for exam-grade, words are derived
    segment_count = len(transcript_segments)
    if segment_count < 8:  # Minimum segments for exam-grade MCQs
        word_count = len(transcript.split()) if transcript else 0
        raise RuntimeError(
            f"❌ Not enough speech segments for exam-grade MCQs: {segment_count} segments (minimum: 8). "
            f"Found {word_count} words from {len(clip_timestamps)} clips. "
            f"Video duration: {video_duration:.1f}s. "
            f"This may indicate: (1) Video has very little speech, (2) Speech is too fragmented, "
            f"(3) Audio quality issues. "
            f"Suggestions: (1) Use videos with clear, continuous speech, (2) Check audio track quality, "
            f"(3) Try increasing SAMPLE_CLIPS or CLIP_SECONDS."
        )
    
    # ✅ Secondary validation: Word count (for backward compatibility)
    word_count = len(transcript.split()) if transcript else 0
    min_words = required_min_words(video_duration)
    if word_count < min_words:
        # Warn but don't fail if we have segments
        print(f"⚠️ Warning: Transcript has {word_count} words (below threshold {min_words}), but {segment_count} segments found. Proceeding with segments.")
    
    # Also check character count as secondary validation
    if len(transcript) < 200:
        raise RuntimeError(
            f"Transcript too short: {len(transcript)} characters (minimum: 200). "
            f"Increase SAMPLE_CLIPS (current: {SAMPLE_CLIPS}) or CLIP_SECONDS (current: {CLIP_SECONDS})."
        )
    
    if use_anchors:
        # Exam-grade mode: Anchor detection from segments with exact timestamps
        print(f"🔍 Exam-grade mode: Detecting anchors from segments with exact timestamps ({len(transcript_segments)} segments, duration: {video_duration:.1f}s)...")
        
        # ✅ STEP 3: Detect anchors from segments (exact timestamps)
        anchors = detect_anchors_from_segments(transcript_segments)
        
        # ✅ FIX 4: Fail fast if insufficient anchors
        if len(anchors) < 10:
            raise RuntimeError(
                f"❌ Not enough examinable anchors found: {len(anchors)} anchors (minimum: 10). "
                f"Video is unsuitable for exam-grade MCQs. "
                f"Video duration: {video_duration:.1f}s. "
                f"Suggestions: (1) Use videos with clear educational content, (2) Ensure video has definitions, processes, and decision points, "
                f"(3) Check if video has sufficient speech segments."
            )
        
        # ✅ FIX 2: Use quota-based anchor selection (balanced coverage)
        anchors = pick_anchors_with_quota(anchors)
        
        # ✅ STEP 4: Anchors already have exact timestamps from segments
        # ✅ CRITICAL FIX: Build context from segments around anchor (not just anchor text)
        # This ensures questions are answerable from specific video context, reducing "answerable without context" rejections by ~60-70%
        for anchor in anchors:
            anchor_start = anchor.get("start", 0.0)
            anchor["timestamp_seconds"] = anchor_start  # Already exact from segment
            anchor["timestamp"] = seconds_to_mmss(anchor_start)  # MM:SS format
            anchor["timestamp_confidence"] = "exact"  # From Whisper segments
            
            # Build context from segments around anchor (24-second window)
            anchor["context"] = build_context_from_segments(anchor, transcript_segments, window_seconds=24.0)
        print(f"   Found {len(anchors)} anchors")
        if len(anchors) == 0:
            # ✅ FIX 4: Fail fast - no legacy fallback in exam-grade mode
            raise RuntimeError(
                f"❌ No examinable anchors detected in video. "
                f"Video duration: {video_duration:.1f}s. "
                f"This video is unsuitable for exam-grade MCQs. "
                f"Use videos with clear educational content containing definitions, processes, decisions, etc."
            )
        # Show anchor types
        anchor_types = {}
        for a in anchors:
            at = a.get("type", "UNKNOWN")
            anchor_types[at] = anchor_types.get(at, 0) + 1
        print(f"   Anchor types: {anchor_types}")
        questions, anchor_metadata = generate_mcqs_ollama_from_anchors(anchors, video_duration=video_duration, transcript_segments=transcript_segments)
        
        # ✅ HYBRID MODE: 10 exam-grade + 10 legacy questions
        # ✅ FIX 1: Respect ALLOW_LEGACY_FILL flag
        if USE_HYBRID_MODE and ALLOW_LEGACY_FILL:
            # Limit exam-grade questions to EXAM_GRADE_COUNT
            exam_grade_questions = questions[:EXAM_GRADE_COUNT]
            print(f"   ✅ Generated {len(exam_grade_questions)} exam-grade MCQs (target: {EXAM_GRADE_COUNT})")
            
            # Generate legacy questions to fill remaining
            legacy_needed = LEGACY_COUNT
            if len(exam_grade_questions) < EXAM_GRADE_COUNT:
                legacy_needed = MCQ_COUNT - len(exam_grade_questions)
            
            print(f"   📊 Generating {legacy_needed} legacy/generic MCQs...")
            segments = pick_random_important_chunks(transcript)
            legacy_questions = generate_mcqs_ollama_from_segments(segments)
            
            # Take only needed legacy questions and mark them
            legacy_questions = legacy_questions[:legacy_needed]
            
            # ✅ Add timestamps to legacy questions (distribute evenly across full video)
            for idx, q in enumerate(legacy_questions):
                q["anchor_type"] = "LEGACY"  # Mark as legacy
                # Distribute legacy questions evenly across full video (0% to 100%)
                timestamp_seconds = (idx / max(legacy_needed - 1, 1)) * video_duration if video_duration > 0 and legacy_needed > 1 else (idx * video_duration / max(legacy_needed, 1))
                q["timestamp_seconds"] = round(timestamp_seconds, 2)
                q["timestamp"] = seconds_to_mmss(timestamp_seconds)  # MM:SS format
            
            # Combine: exam-grade first, then legacy
            all_questions = exam_grade_questions + legacy_questions
            print(f"   ✅ Total: {len(exam_grade_questions)} exam-grade + {len(legacy_questions)} legacy = {len(all_questions)} MCQs")
            
            return all_questions[:MCQ_COUNT], anchor_metadata
        
        # ✅ PURE EXAM-GRADE MODE: No legacy fill, no padding, no mixing
        # If exam-grade < MCQ_COUNT → return fewer questions (academically correct)
        if len(questions) < MCQ_COUNT:
            print(f"   ⚠️ Only {len(questions)} exam-grade MCQs possible from this video (required: {MCQ_COUNT})")
            print(f"   ℹ️ Returning {len(questions)} exam-grade MCQs (no legacy padding)")
        
        # ✅ FIX 5: Remove legacy questions (hard rule - no legacy in exam-grade output)
        questions = [
            q for q in questions
            if q.get("anchor_type") not in {"LEGACY", "UNKNOWN", None}
        ]
        
        # CRITICAL: Validate no legacy contamination
        for q in questions:
            anchor_type = q.get("anchor_type", "UNKNOWN")
            if anchor_type not in {"PROCESS", "DECISION", "DEFINITION", "RISK", "BOUNDARY", "COMPARISON"}:
                raise RuntimeError(f"Invalid anchor_type '{anchor_type}' detected in exam-grade output")
        
        return questions[:MCQ_COUNT], anchor_metadata
    else:
        # Legacy mode: Random chunks
        segments = pick_random_important_chunks(transcript)
        questions = generate_mcqs_ollama_from_segments(segments)
        
        # ✅ Add timestamps to legacy questions (timestamp window, not exact)
        for idx, q in enumerate(questions):
            # Use clip timestamps if available, otherwise distribute evenly
            if clip_timestamps and len(clip_timestamps) > 0:
                clip_idx = min(int((idx / max(len(questions) - 1, 1)) * len(clip_timestamps)), len(clip_timestamps) - 1)
                clip_start = clip_timestamps[clip_idx]
                clip_end = clip_start + CLIP_SECONDS
            else:
                clip_start = (idx / max(len(questions) - 1, 1)) * video_duration if video_duration > 0 and len(questions) > 1 else (idx * video_duration / max(len(questions), 1))
                clip_end = clip_start + CLIP_SECONDS
            
            q["timestamp_seconds"] = round(clip_start, 2)  # Approximate
            q["timestamp"] = seconds_to_mmss(clip_start)  # MM:SS format
            q["timestamp_confidence"] = "approx"  # From clip, not exact segment
            q["timestamp_window"] = {
                "start": round(clip_start, 2),
                "end": round(min(video_duration, clip_end), 2),
                "confidence": "approx",
                "source": "ffmpeg_clip"
            }
        
        return questions, None

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
        anchor_type = anchor.get("anchor_type", "UNKNOWN")
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

async def db_upsert(session: AsyncSession, video_id: str, url: str, questions: list, mode: str = "legacy", quality_metrics: Optional[Dict[str, Any]] = None, force_regeneration: bool = False):
    """
    Save MCQs with mode versioning, audit trails, and quality metrics.
    mode: "exam-grade" or "legacy"
    quality_metrics: Optional dict with quality stats (rejection_rate, etc.)
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
        "ollama_model": OLLAMA_MODEL,
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

    if existing:
        # Update existing record
        
        # CRITICAL FIX #3: quality_metrics is append-only for exam-grade (never mutable)
        # Protection: Only prevent overwrite if exam-grade quality_metrics exists AND we're not doing explicit regeneration
        # Allow update for: new records, legacy mode, legacy->exam-grade upgrade, or explicit regeneration (force_regeneration=True)
        if existing.quality_metrics and mode == "exam-grade" and existing.generation_mode == "exam-grade" and not force_regeneration:
            # Preserve existing quality_metrics - do not overwrite (prevents accidental mutation)
            # Note: force_regeneration=True allows explicit regenerations to update quality_metrics
            pass  # quality_metrics remains unchanged
        else:
            # Allow update: this is either new content, legacy mode, upgrade, or explicit regeneration
            existing.quality_metrics = quality_metrics
        
        existing.url = url
        existing.mcq_count = len(questions)
        existing.questions = payload_questions
        existing.generator = generator
        existing.generation_mode = mode
        
        # CRITICAL FIX #1: generation_count = number of full regeneration cycles of exam-grade content
        # Increment ONLY when mode = exam-grade and regeneration is explicitly triggered
        if mode == "exam-grade":
            existing.generation_count = (existing.generation_count or 0) + 1
        # Do NOT increment for legacy saves, cache hits, or read paths
        
        existing.updated_by = "api"  # Can be enhanced with actual user/auth info
        
        # CRITICAL FIX #2: schema_version in DB must match quality_metrics.schema_version
        if quality_metrics and "schema_version" in quality_metrics:
            existing.schema_version = quality_metrics["schema_version"]
        else:
            existing.schema_version = "1.0"  # Fallback for legacy
    else:
        # Create new record
        # CRITICAL FIX #2: schema_version in DB must match quality_metrics.schema_version
        schema_ver = "1.0"
        if quality_metrics and "schema_version" in quality_metrics:
            schema_ver = quality_metrics["schema_version"]
        
        # CRITICAL FIX #1: generation_count = 1 for new exam-grade, 1 for legacy (initial generation)
        gen_count = 1
        
        row = VideoMCQ(
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
        session.add(row)

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
                    response = {
                        "status": "cached",
                        "video_id": video_id,
                        "count": existing.mcq_count,
                        "message": "Already generated. Use force=true to regenerate."
                    }
                    # Include questions if requested
                    if req.include_questions:
                        qs = (existing.questions or {}).get("questions", [])
                        # ✅ Apply sorting before returning (cache path)
                        qs = normalize_question_order(qs)
                        if not req.include_answers:
                            qs = strip_answers(qs)
                        response["questions"] = qs
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
                await session.commit()
                print(f"   ✅ Saved {len(qs)} questions to database (video_id: {video_id})")
            except Exception as db_error:
                await session.rollback()
                print(f"   ❌ Database save failed: {db_error}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to save questions to database: {str(db_error)}")
            dt = time.time() - t0

            response = {
                "status": "saved",
                "video_id": video_id,
                "count": len(qs),
                "time_seconds": round(dt, 2),
            }
            # Include questions if requested
            if req.include_questions:
                # ✅ Apply sorting before returning (fresh generation path)
                qs = normalize_question_order(qs)
                if not req.include_answers:
                    qs = strip_answers(qs)
                response["questions"] = qs
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
                    # ✅ Apply sorting BEFORE randomize/limit (cache path)
                    qs2 = normalize_question_order(qs2)
                    
                    if request.randomize:
                        random.shuffle(qs2)
                    qs2 = qs2[:min(request.limit, len(qs2))]
                    
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
                        "questions": qs2
                    }
                    
                    # Add anchor statistics if available
                    if anchor_stats:
                        response["anchor_statistics"] = anchor_stats
                        response["anchor_types_used"] = list(anchor_stats.keys())
                    
                    return response
            
            # Not in cache - generate MCQs
            print(f"🔄 Generating MCQs in {current_mode} mode...")
            t0 = time.time()
            qs, anchor_metadata = generate_mcqs_from_video_fast(video_url)
            
            # Get video duration for response (from first question timestamp or calculate)
            video_duration = None
            if qs and len(qs) > 0:
                # Estimate from timestamps if available
                timestamps = [q.get("timestamp_seconds", 0) for q in qs if q.get("timestamp_seconds")]
                if timestamps:
                    video_duration = max(timestamps) * 1.2  # Add 20% buffer
                else:
                    # Fallback: get duration from video URL
                    try:
                        video_duration = ffprobe_duration_seconds(video_url)
                    except:
                        pass
            
            # ✅ HYBRID MODE: Allow legacy in hybrid mode, but validate in pure exam-grade mode
            if not USE_HYBRID_MODE:
                # Pure exam-grade mode: NO legacy contamination
                if current_mode == "exam-grade" and any(q.get("anchor_type") == "LEGACY" for q in qs):
                    raise RuntimeError("Legacy MCQs are not allowed in pure exam-grade mode")
                
                # CRITICAL: Validate all questions have valid anchor types in pure exam-grade mode
                if current_mode == "exam-grade":
                    for q in qs:
                        anchor_type = q.get("anchor_type", "UNKNOWN")
                        if anchor_type not in {"PROCESS", "DECISION", "DEFINITION", "RISK", "BOUNDARY", "COMPARISON"}:
                            raise RuntimeError(f"Invalid anchor_type '{anchor_type}' detected in exam-grade output")
            
            # Detect actual mode from generated questions
            detected_mode = "legacy"
            if anchor_metadata:
                detected_mode = "exam-grade"
            
            # Build complete quality_metrics
            generation_time = time.time() - t0
            quality_metrics = build_quality_metrics(anchor_metadata, qs, generation_time, detected_mode)
            
            # Save with mode versioning and quality metrics
            # force_regeneration=True because this is an explicit generation (force param or cache miss)
            await db_upsert(session, video_id, video_url, qs, mode=detected_mode, quality_metrics=quality_metrics, force_regeneration=request.force)
            await session.commit()
            dt = time.time() - t0
            print(f"✅ Generated {len(qs)} MCQs in {detected_mode} mode (took {dt:.2f}s)")
            
            # Process questions according to request
            qs2 = qs[:]
            # ✅ Apply sorting BEFORE randomize/limit (fresh generation path)
            qs2 = normalize_question_order(qs2)
            
            if request.randomize:
                random.shuffle(qs2)
            qs2 = qs2[:min(request.limit, len(qs2))]
            
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
                    "questions": qs2
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
                    "message": f"Video does not contain enough examinable concepts to generate {MCQ_COUNT} exam-grade MCQs"
                }
            else:
                response = {
                    "status": "success",
                    "video_id": video_id,
                    "count": len(qs2),
                    "cached": False,
                    "time_seconds": round(dt, 2),
                    "mode": final_mode,
                    "questions": qs2
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

@app.get("/health")
def health():
    return {
        "status": "ready" if OLLAMA_EXE else "warning",
        "ollama_available": bool(OLLAMA_EXE),
        "whisper_model": WHISPER_MODEL_SIZE,
        "ollama_model": OLLAMA_MODEL,
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

@app.get("/")
def root():
    return {
        "service": "Fast Video MCQ Generator + MySQL Cache",
        "primary_endpoint": "POST /videos/mcqs - Single endpoint, everything in body (no query params)",
        "endpoints": [
            "POST /videos/mcqs - [RECOMMENDED] Single endpoint, all params in JSON body",
            "POST /generate-and-save - Generate and save MCQs (returns video_id)",
            "GET /videos/{video_id}/mcqs - Fetch MCQs by video_id",
            "POST /videos/mcqs/by-url - [DEPRECATED] Use POST /videos/mcqs instead"
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
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

