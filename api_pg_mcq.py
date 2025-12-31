"""
FAST MCQ Generator + MySQL Cache

Primary Endpoint (RECOMMENDED):
POST /videos/mcqs -> Single endpoint, everything in JSON body (no query params)
  - Send video_url in body → get MCQs back
  - Handles generation + caching internally
  - No Params tab needed in Postman!

Other Endpoints:
1) POST /generate-and-save  -> generate MCQs ONCE and save to MySQL
2) GET  /videos/{video_id}/mcqs -> fetch instantly by video_id
3) POST /videos/mcqs/by-url -> [DEPRECATED] Use POST /videos/mcqs instead

Notes:
- Default fetch does NOT include correct_answer (anti-cheat)
- video_id is deterministic from URL (sha1)
- POST /videos/mcqs handles everything: cache check → generate if needed → return
"""

import os
import re
import json
import time
import shutil
import random
import hashlib
import subprocess
import traceback
from typing import List, Dict, Any, Optional

import numpy as np
from faster_whisper import WhisperModel

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sqlalchemy import String, Text, Integer, BigInteger, func, select, TIMESTAMP
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ===============================
# CONFIG
# ===============================
DATABASE_URL = os.getenv("DATABASE_URL", "")  # mysql+aiomysql://...

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

MCQ_COUNT = int(os.getenv("MCQ_COUNT", "20"))

IMPORTANT_POOL_SIZE = int(os.getenv("IMPORTANT_POOL_SIZE", "18"))
RANDOM_PICK_COUNT = int(os.getenv("RANDOM_PICK_COUNT", "8"))

CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "120"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "35"))

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

SAMPLE_CLIPS = int(os.getenv("SAMPLE_CLIPS", "8"))
CLIP_SECONDS = float(os.getenv("CLIP_SECONDS", "12"))

FFPROBE_TIMEOUT = int(os.getenv("FFPROBE_TIMEOUT", "15"))
FFMPEG_TIMEOUT_PER_CLIP = int(os.getenv("FFMPEG_TIMEOUT_PER_CLIP", "60"))

RANDOM_SEED_ENV = os.getenv("RANDOM_SEED", "").strip()
RANDOM_SEED = int(RANDOM_SEED_ENV) if RANDOM_SEED_ENV.isdigit() else None

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
# FASTAPI
# ===============================
app = FastAPI(
    title="Fast Video MCQ Generator + MySQL Cache",
    version="4.0.0",
    description="Generate once -> save to MySQL -> fetch instantly"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global engine, SessionLocal
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set. DB endpoints will fail.")
        return

    engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    # Optional: auto-create table (works if DB user has rights)
    # Comment this if you prefer running SQL manually.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown_event():
    global engine
    if engine:
        await engine.dispose()

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
    """Single endpoint request - everything in body, no query params"""
    video_url: str = Field(..., description="Video URL to generate/fetch MCQs from")
    include_answers: bool = Field(default=False, description="Include correct answers (anti-cheat: default false)")
    randomize: bool = Field(default=True, description="Shuffle questions")
    limit: int = Field(default=20, ge=1, le=50, description="Number of questions to return")

# ===============================
# UTILS
# ===============================
def make_video_id(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]

def is_english(text: str) -> bool:
    if not text:
        return False
    english_chars = len(re.findall(r"[a-zA-Z0-9\s\.,!?;:\-()/%\[\]\"'&+=]", text))
    total_chars = len(re.findall(r"[^\s]", text))
    return total_chars > 0 and (english_chars / total_chars) >= 0.70

def deduplicate_questions(questions: list) -> list:
    seen = set()
    out = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qt = (q.get("question") or "").strip().lower()
        qt = re.sub(r"[^\w\s]", "", qt)
        if qt and qt not in seen:
            seen.add(qt)
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
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {r.stderr[:300]}")
    return float(r.stdout.strip())

def pick_sample_timestamps(duration: float, n: int) -> List[float]:
    if duration <= 0:
        return [0.0]
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

# ===============================
# stream clips -> whisper
# ===============================
def transcribe_sampled_stream(video_url: str) -> str:
    dur = ffprobe_duration_seconds(video_url)

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
    else:
        random.seed(time.time())

    timestamps = pick_sample_timestamps(dur, SAMPLE_CLIPS)

    all_text: List[str] = []
    for ss in timestamps:
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-rw_timeout", "15000000",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-ss", str(ss),
            "-t", str(CLIP_SECONDS),
            "-i", video_url,
            "-vn", "-ac", "1", "-ar", "16000",
            "-f", "s16le",
            "pipe:1"
        ]

        p = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            audio_bytes, _err = p.communicate(timeout=FFMPEG_TIMEOUT_PER_CLIP)
        except subprocess.TimeoutExpired:
            p.kill()
            continue

        if p.returncode != 0 or not audio_bytes:
            continue

        audio_np = (np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0)

        segments, _ = whisper_model.transcribe(
            audio_np,
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        clip_text = " ".join(seg.text for seg in segments).strip()
        if clip_text:
            all_text.append(clip_text)

    transcript = " ".join(all_text).strip()
    transcript = re.sub(r"\[.*?\]", "", transcript)
    transcript = re.sub(r"\s+", " ", transcript).strip()
    return transcript

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

# ===============================
# Ollama generation
# ===============================
def mcq_prompt_from_segments(segments: List[str], count: int, start_index: int = 1) -> str:
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

# ===============================
# pipeline
# ===============================
def generate_mcqs_from_video_fast(video_url: str) -> List[Dict[str, Any]]:
    transcript = transcribe_sampled_stream(video_url)
    if len(transcript) < 200:
        raise RuntimeError("Transcript too short. Increase SAMPLE_CLIPS or CLIP_SECONDS.")
    segments = pick_random_important_chunks(transcript)
    return generate_mcqs_ollama_from_segments(segments)

# ===============================
# DB helpers
# ===============================
async def db_get(session: AsyncSession, video_id: str) -> Optional[VideoMCQ]:
    q = select(VideoMCQ).where(VideoMCQ.video_id == video_id)
    r = await session.execute(q)
    return r.scalar_one_or_none()

async def db_upsert(session: AsyncSession, video_id: str, url: str, questions: list):
    existing = await db_get(session, video_id)
    payload_questions = {"questions": questions}  # keep structure stable

    generator = {
        "whisper_model": WHISPER_MODEL_SIZE,
        "ollama_model": OLLAMA_MODEL,
        "sample_clips": SAMPLE_CLIPS,
        "clip_seconds": CLIP_SECONDS,
    }

    if existing:
        existing.url = url
        existing.mcq_count = len(questions)
        existing.questions = payload_questions
        existing.generator = generator
    else:
        row = VideoMCQ(
            video_id=video_id,
            url=url,
            mcq_count=len(questions),
            questions=payload_questions,
            generator=generator
        )
        session.add(row)

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
                response = {
                    "status": "cached",
                    "video_id": video_id,
                    "count": existing.mcq_count,
                    "message": "Already generated. Use force=true to regenerate."
                }
                # Include questions if requested
                if req.include_questions:
                    qs = (existing.questions or {}).get("questions", [])
                    if not req.include_answers:
                        qs = strip_answers(qs)
                    response["questions"] = qs
                return response

            t0 = time.time()
            qs = generate_mcqs_from_video_fast(req.url)
            await db_upsert(session, video_id, req.url, qs)
            await session.commit()
            dt = time.time() - t0

            response = {
                "status": "saved",
                "video_id": video_id,
                "count": len(qs),
                "time_seconds": round(dt, 2),
            }
            # Include questions if requested
            if req.include_questions:
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
    
    async with SessionLocal() as session:
        try:
            # Check cache first
            row = await db_get(session, video_id)
            
            if row:
                # MCQs exist in cache - return them
                qs = (row.questions or {}).get("questions", [])
                if not isinstance(qs, list) or len(qs) == 0:
                    raise HTTPException(status_code=500, detail="DB record has no questions.")
                
                qs2 = qs[:]
                if request.randomize:
                    random.shuffle(qs2)
                qs2 = qs2[:min(request.limit, len(qs2))]
                
                if not request.include_answers:
                    qs2 = strip_answers(qs2)
                
                return {
                    "status": "success",
                    "video_id": video_id,
                    "count": len(qs2),
                    "cached": True,
                    "questions": qs2
                }
            
            # Not in cache - generate MCQs
            t0 = time.time()
            qs = generate_mcqs_from_video_fast(video_url)
            await db_upsert(session, video_id, video_url, qs)
            await session.commit()
            dt = time.time() - t0
            
            # Process questions according to request
            qs2 = qs[:]
            if request.randomize:
                random.shuffle(qs2)
            qs2 = qs2[:min(request.limit, len(qs2))]
            
            if not request.include_answers:
                qs2 = strip_answers(qs2)
            
            return {
                "status": "success",
                "video_id": video_id,
                "count": len(qs2),
                "cached": False,
                "time_seconds": round(dt, 2),
                "questions": qs2
            }
            
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

