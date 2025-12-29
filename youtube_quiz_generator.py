"""
YouTube URL → MCQ Generator (FAST + UNIQUE, 100% FREE, Windows Safe)

Pipeline:
YouTube URL
→ YouTube Transcript API (auto-translate if needed)
→ Whisper (ONLY if captions unavailable)
→ Agent-03: Web Knowledge Enrichment
   ├─ Topic Extraction (Ollama llama3:8b)
   ├─ Topic Validation (remove generic words)
   ├─ Query Generation (Ollama llama3:8b)
   ├─ Controlled Web Search (approved domains only)
   ├─ Content Fetching & Cleaning
   └─ Knowledge Synthesis (Ollama llama3:8b)
→ Merged Context (Transcript + Enriched Knowledge)
→ Ollama Binary (direct execution, no HTTP)
→ 20 UNIQUE MCQs (valid JSON) 
"""

import os
import re
import json
import sys
import tempfile
import subprocess
import requests
import platform
import shutil
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

# ===============================
# ENVIRONMENT CONFIG
# ===============================
# Set CLOUD_ENV=true to disable Whisper fallback on cloud servers
# (Whisper requires yt-dlp which is blocked by YouTube on cloud VMs)
IS_CLOUD_ENV = os.environ.get("CLOUD_ENV", "false").lower() == "true"

# Set FAST_MODE=true to disable Agent-03 enrichment for faster processing (~30 seconds)
# When enabled: Skips web search enrichment, uses faster models, reduces retries
FAST_MODE = os.environ.get("FAST_MODE", "true").lower() == "true"  # Default: enabled for speed

# ===============================
# OLLAMA CONFIG (FAST + STABLE)
# ===============================
# Auto-detect Ollama path (OS-aware)
# First try PATH detection (most portable)
OLLAMA_CMD = shutil.which("ollama")

# If not in PATH, use OS-specific default paths
if not OLLAMA_CMD:
    if platform.system() == "Windows":
        # Windows default installation path
        windows_path = r"C:\Users\Hp\AppData\Local\Programs\Ollama\ollama.exe"
        if os.path.exists(windows_path):
            OLLAMA_CMD = windows_path
        else:
            # Try common Windows locations
            alt_paths = [
                os.path.expanduser(r"~\AppData\Local\Programs\Ollama\ollama.exe"),
                r"C:\Program Files\Ollama\ollama.exe",
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    OLLAMA_CMD = alt_path
                    break
    
    if not OLLAMA_CMD:
        # Linux/macOS default paths
        linux_paths = [
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
            os.path.expanduser("~/bin/ollama"),
        ]
        for linux_path in linux_paths:
            if os.path.exists(linux_path):
                OLLAMA_CMD = linux_path
                break

# Final check: raise error if Ollama not found
if not OLLAMA_CMD:
    raise RuntimeError(
        "Ollama not found. Please install Ollama from https://ollama.com\n"
        "Or ensure 'ollama' is in your PATH."
    )

OLLAMA_MODEL = "gemma2:2b"  # Fast model, good for MCQs. Alternatives: "llama3", "mistral"
OLLAMA_ENRICHMENT_MODEL = "gemma2:2b"  # Fast model for enrichment (faster than mistral:7b, avoids timeouts)
MAX_TRANSCRIPT_CHARS = 2000 if FAST_MODE else 3000   # Reduced for faster processing in fast mode
WHISPER_MODEL = "tiny" if FAST_MODE else "base"  # Faster model in fast mode

# ===============================
# AGENT-03: WEB SEARCH CONFIG
# ===============================
APPROVED_DOMAINS = [
    "wikipedia.org",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "radiologyinfo.org",
    "britannica.com",
    "edu",  # Educational institutions
    "gov",  # Government sites
    "org"   # Non-profit organizations (trusted ones)
]

GENERIC_WORDS = {
    "machine", "device", "system", "technology",
    "equipment", "tool", "process", "method",
    "thing", "stuff", "item", "object", "concept"
}

# ===============================
# AGENT-03: MODE CONFIGURATION
# ===============================
# Set to True to fetch ALL topics (no filtering) - good for research/exploration
# Set to False for strict exam-grade validation - good for production/exams
FETCH_ALL_TOPICS = False  # 🔥 Set to False for production (faster, exam-safe)

# ===============================
# YOUTUBE TRANSCRIPT FETCHER
# ===============================
class YouTubeTranscriptFetcher:
    def __init__(self):
        from youtube_transcript_api import YouTubeTranscriptApi
        self.api = YouTubeTranscriptApi

    def extract_video_id(self, url):
        parsed = urlparse(url)
        if parsed.hostname in ("www.youtube.com", "youtube.com"):
            return parse_qs(parsed.query)["v"][0]
        if parsed.hostname == "youtu.be":
            return parsed.path.lstrip("/").split("?")[0]
        raise ValueError("Invalid YouTube URL")

    def fetch(self, url):
        vid = self.extract_video_id(url)

        # 1️⃣ Try English transcript
        try:
            t = self.api.get_transcript(vid, languages=["en"])
            return " ".join(x["text"] for x in t)
        except:
            pass

        # 2️⃣ Try Hindi auto → translate to English
        try:
            t = self.api.get_transcript(vid, languages=["hi"])
            t = self.api.translate_transcript(t, "en")
            return " ".join(x["text"] for x in t)
        except:
            raise RuntimeError("Transcript unavailable or corrupted")

# ===============================
# WHISPER FALLBACK (LAST RESORT)
# ===============================
class WhisperAudioTranscriber:
    def __init__(self, model="base"):
        import yt_dlp, whisper
        self.yt_dlp = yt_dlp
        self.model = whisper.load_model(model)

    def download_audio(self, url):
        """Download audio from YouTube URL and return path to MP3 file"""
        # Use unique temp file to avoid conflicts
        temp_dir = tempfile.gettempdir()
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3",
            prefix="yt_audio_",
            dir=temp_dir,
            delete=False
        )
        temp_file.close()
        audio_path = temp_file.name

        opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path.replace(".mp3", ".%(ext)s"),
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
            "quiet": False,
            "no_warnings": True,
            "retries": 10,
            "fragment_retries": 10,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        # Optional: Add cookiefile if it exists (for Azure/Linux)
        cookie_paths = [
            "/home/azureuser/cookies.txt",
            os.path.expanduser("~/cookies.txt"),
            os.path.join(os.getcwd(), "cookies.txt")
        ]
        for cookie_path in cookie_paths:
            if os.path.exists(cookie_path):
                opts["cookiefile"] = cookie_path
                break

        try:
            with self.yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            
            # Verify file was created
            if not os.path.exists(audio_path):
                # Try alternative path (yt-dlp might add extension)
                alt_paths = [
                    audio_path.replace(".mp3", ".webm"),
                    audio_path.replace(".mp3", ".m4a"),
                    audio_path.replace(".mp3", ".opus"),
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        audio_path = alt_path
                        break
                else:
                    raise RuntimeError(f"Audio file not found after download: {audio_path}")
            
            return audio_path
        except Exception as e:
            # Clean up on error
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            raise RuntimeError(f"Failed to download audio: {str(e)}")

    def transcribe(self, url):
        """Transcribe audio from YouTube URL using Whisper"""
        audio_path = None
        try:
            audio_path = self.download_audio(url)
            if not os.path.exists(audio_path):
                raise RuntimeError(f"Audio file not found: {audio_path}")
            
            result = self.model.transcribe(audio_path)
            return result["text"]
        except Exception as e:
            raise RuntimeError(f"Whisper transcription failed: {str(e)}")
        finally:
            # Always clean up audio file
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass  # Ignore cleanup errors

# ===============================
# VIDEO URL TRANSCRIBER (S3/CDN/HTTPS)
# ===============================
class VideoURLTranscriber:
    """
    Transcribe videos from direct URLs (S3, CDN, HTTPS).
    Works with any HTTP/HTTPS video URL - no YouTube, no yt-dlp, no cookies.
    """
    def __init__(self, model=None):
        import whisper
        if model is None:
            model = WHISPER_MODEL  # Use global FAST_MODE setting
        self.model = whisper.load_model(model)

    def download_video(self, video_url: str) -> str:
        """Download video from URL and return path to local file"""
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp4",
            prefix="video_",
            delete=False
        )
        temp_file.close()
        video_path = temp_file.name

        try:
            # Download with streaming for large files
            response = requests.get(video_url, stream=True, timeout=120 if FAST_MODE else 300)
            response.raise_for_status()
            
            with open(video_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
            
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                raise RuntimeError(f"Downloaded file is empty or missing: {video_path}")
            
            return video_path
        except Exception as e:
            # Clean up on error
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except:
                    pass
            raise RuntimeError(f"Failed to download video from URL: {str(e)}")

    def extract_audio(self, video_path: str) -> str:
        """Extract audio from video using FFmpeg"""
        audio_path = video_path.replace(".mp4", ".mp3")
        
        # Try alternative extensions if .mp4 replacement doesn't work
        if not audio_path.endswith(".mp3"):
            audio_path = os.path.splitext(video_path)[0] + ".mp3"
        
        try:
            # Use FFmpeg to extract audio
            result = subprocess.run(
                [
                    "ffmpeg", "-y",  # -y: overwrite output file
                    "-i", video_path,
                    "-vn",  # No video
                    "-acodec", "libmp3lame",  # MP3 codec
                    "-ab", "192k",  # Audio bitrate
                    audio_path
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True,
                timeout=120 if FAST_MODE else 300
            )
            
            if not os.path.exists(audio_path):
                raise RuntimeError(f"Audio extraction failed: {audio_path}")
            
            return audio_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr.decode('utf-8', errors='ignore')}")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg:\n"
                "  Windows: Download from https://ffmpeg.org\n"
                "  Linux: sudo apt-get install ffmpeg\n"
                "  macOS: brew install ffmpeg"
            )

    def transcribe_from_url(self, video_url: str) -> str:
        """
        Transcribe video from URL (S3, CDN, HTTPS).
        
        Pipeline:
        1. Download video from URL
        2. Extract audio using FFmpeg
        3. Transcribe with Whisper
        4. Clean up temp files
        
        Args:
            video_url: HTTP/HTTPS URL to video file (e.g., S3 URL)
            
        Returns:
            Transcribed text string
        """
        video_path = None
        audio_path = None
        
        try:
            # Step 1: Download video
            video_path = self.download_video(video_url)
            
            # Step 2: Extract audio
            audio_path = self.extract_audio(video_path)
            
            # Step 3: Transcribe
            result = self.model.transcribe(audio_path)
            return result["text"]
            
        except Exception as e:
            raise RuntimeError(f"Video transcription failed: {str(e)}")
        finally:
            # Always clean up temp files
            for file_path in [audio_path, video_path]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass  # Ignore cleanup errors

# ===============================
# CLEAN + SHRINK TRANSCRIPT
# ===============================
def clean_transcript(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:MAX_TRANSCRIPT_CHARS]

# ===============================
# AGENT-03: WEB SEARCH KNOWLEDGE ENRICHMENT
# ===============================

def extract_topics_from_transcript(transcript):
    """Extract key topics from transcript using Ollama llama3:8b"""
    prompt = f"""Extract 5-8 key educational topics from this transcript.
Focus on specific, testable concepts (not generic words).

Output as a JSON array of topic strings only.
Example: ["x-ray radiation", "ionizing radiation safety", "medical imaging risks"]

TRANSCRIPT:
{transcript[:2000]}

Output JSON array only:"""

    try:
        result = subprocess.run(
            [OLLAMA_CMD, "run", OLLAMA_ENRICHMENT_MODEL, prompt],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
            check=False
        )
        
        if result.returncode != 0:
            print(f"   ⚠ LLM topic extraction failed (return code {result.returncode})")
            return []
        
        content = result.stdout.strip()
        
        # Debug logging (can be enabled for troubleshooting)
        # print(f"🧪 Raw LLM output: {content[:500]}")
        
        # Extract JSON array
        start = content.find("[")
        end = content.rfind("]")
        
        if start == -1 or end == -1:
            print(f"   ⚠ LLM output missing JSON brackets. Raw: {content[:200]}")
            return []
        
        topics = json.loads(content[start:end + 1])
        topics = topics if isinstance(topics, list) else []
        
        if topics:
            print(f"   ✓ LLM extracted {len(topics)} topics")
        else:
            print(f"   ⚠ LLM returned empty topic list")
        
        return topics
    except json.JSONDecodeError as e:
        print(f"   ⚠ JSON parsing failed: {e}")
        return []
    except Exception as e:
        print(f"   ⚠ Topic extraction error: {e}")
        return []

def fallback_topic_extraction(transcript):
    """Fallback: Extract topics using keyword matching when LLM fails"""
    # Common educational keywords/phrases that indicate testable topics
    keyword_patterns = [
        # Medical/Health
        r"\b(?:x-ray|xray|radiation|ionizing radiation|medical imaging|radiology|dose|exposure|safety)\b",
        r"\b(?:health risk|medical procedure|diagnostic|scan|imaging)\b",
        # Technology
        r"\b(?:machine learning|artificial intelligence|neural network|algorithm|data structure)\b",
        r"\b(?:programming|software|hardware|computer|network|security)\b",
        # Science
        r"\b(?:chemical|reaction|molecule|atom|element|compound)\b",
        r"\b(?:physics|force|energy|wave|particle|quantum)\b",
        # Business/Economics
        r"\b(?:marketing|seo|search engine|optimization|business strategy|economics)\b",
        # General educational
        r"\b(?:concept|principle|theory|method|technique|process|system)\b",
    ]
    
    found_topics = set()
    text_lower = transcript.lower()
    
    # Extract multi-word phrases that match patterns
    for pattern in keyword_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            # Get context around the match (2-3 words before/after)
            start = max(0, match.start() - 30)
            end = min(len(text_lower), match.end() + 30)
            context = text_lower[start:end]
            
            # Extract meaningful phrases
            words = context.split()
            if len(words) >= 2:
                # Try to form 2-3 word phrases
                for i in range(len(words) - 1):
                    phrase = " ".join(words[i:i+2])
                    if len(phrase) > 5:
                        # In FETCH_ALL mode, don't filter generic words
                        if FETCH_ALL_TOPICS or not any(gw in phrase for gw in GENERIC_WORDS):
                            found_topics.add(phrase)
                for i in range(len(words) - 2):
                    phrase = " ".join(words[i:i+3])
                    if len(phrase) > 8:
                        # In FETCH_ALL mode, don't filter generic words
                        if FETCH_ALL_TOPICS or not any(gw in phrase for gw in GENERIC_WORDS):
                            found_topics.add(phrase)
    
    topics = list(found_topics)[:8]  # Limit to 8 topics
    if topics:
        print(f"   ✓ Fallback extracted {len(topics)} topics from keywords")
    return topics

def validate_topics(topics):
    """
    Topic validation with two modes:
    - FETCH_ALL_TOPICS = True  → allow everything (research/exploration mode)
    - FETCH_ALL_TOPICS = False → strict exam-safe validation (production mode)
    """
    clean = set()
    
    for t in topics:
        if not isinstance(t, str):
            continue
        t = t.strip().lower()
        if not t:
            continue
        
        # 🔥 FETCH ALL MODE: Accept everything (no filtering)
        if FETCH_ALL_TOPICS:
            clean.add(t)
            continue
        
        # -------- STRICT MODE BELOW (Exam-grade safety) --------
        # Domain-specific single terms that are acceptable
        ACCEPTABLE_SINGLE_TERMS = {
            "x-ray", "xray", "seo", "ai", "ml", "api", "dna", "rna"
        }
        
        words = t.split()
        
        # Allow domain-specific single terms, otherwise require 2+ words
        if len(words) < 2:
            if t in ACCEPTABLE_SINGLE_TERMS:
                # Accept single term if it's domain-specific
                clean.add(t)
            continue  # Otherwise skip single words
        
        # Skip generic words
        if t in GENERIC_WORDS:
            continue
        
        # Skip if any word in the topic is generic (but allow if it's part of a compound term)
        has_generic = any(word in GENERIC_WORDS for word in words)
        if has_generic and len(words) == 2:
            # Allow 2-word phrases even if one word is generic (e.g., "machine learning")
            pass
        elif has_generic:
            continue
        
        clean.add(t)
    
    return list(clean)

def generate_search_queries(topic):
    """Generate intelligent web search queries using Ollama llama3:8b"""
    prompt = f"""Generate 4 high-quality educational web search queries for the topic: "{topic}"

Rules:
- Use clear academic phrasing
- Avoid vague wording
- Focus on explanation, risks, safety, and technical details
- Each query should be different

Output as JSON array of strings only.
Example: ["What is {topic}?", "How does {topic} work?", "{topic} health effects", "{topic} safety precautions"]

Output JSON array only:"""

    try:
        result = subprocess.run(
            [OLLAMA_CMD, "run", OLLAMA_ENRICHMENT_MODEL, prompt],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
            check=False
        )
        
        if result.returncode != 0:
            return []
        
        content = result.stdout.strip()
        start = content.find("[")
        end = content.rfind("]")
        
        if start == -1 or end == -1:
            return []
        
        queries = json.loads(content[start:end + 1])
        return queries if isinstance(queries, list) else []
    except Exception as e:
        print(f"⚠ Query generation failed for '{topic}': {e}")
        return []

def is_approved_domain(url):
    """Check if URL is from an approved domain"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Check exact matches
        for approved in APPROVED_DOMAINS:
            if approved in domain:
                return True
        
        # Check TLD matches
        if domain.endswith('.edu') or domain.endswith('.gov') or domain.endswith('.org'):
            return True
        
        return False
    except:
        return False

def fetch_clean_text(url, max_chars=4000):
    """Fetch and clean text content from a web page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "aside", "header", "iframe"]):
            tag.decompose()
        
        # Get text content
        text = soup.get_text(separator=" ")
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text[:max_chars]
    except Exception as e:
        print(f"⚠ Failed to fetch {url}: {e}")
        return ""

def search_wikipedia_direct(query):
    """Try Wikipedia API directly (more reliable)"""
    try:
        # Extract main topic from query
        topic = query.split()[0:3]  # First few words
        topic = " ".join(topic).lower()
        
        # Wikipedia API search
        api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(topic)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'content_urls' in data and 'desktop' in data['content_urls']:
                return [data['content_urls']['desktop']['page']]
    except:
        pass
    return []

def search_web_safely(query, max_results=2):
    """Perform controlled web search (approved domains only)"""
    results = []
    
    # Try Wikipedia API first (more reliable)
    wiki_results = search_wikipedia_direct(query)
    results.extend(wiki_results)
    
    if len(results) >= max_results:
        return results[:max_results]
    
    # Fallback: DuckDuckGo HTML search
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find result links (DuckDuckGo structure may vary)
        for link in soup.find_all('a', limit=20):
            href = link.get('href', '')
            if href and is_approved_domain(href):
                if href not in results:
                    results.append(href)
                    if len(results) >= max_results:
                        break
    except Exception as e:
        # Silently fail - Wikipedia might have worked
        pass
    
    return results[:max_results]

def synthesize_knowledge(topic, web_texts):
    """Synthesize web content into structured knowledge using Ollama llama3:8b"""
    combined_text = "\n\n---\n\n".join(web_texts[:3])  # Use up to 3 sources
    combined_text = combined_text[:3000]  # Limit input size
    
    prompt = f"""Summarize the following content into a clear, exam-ready explanation for the topic: "{topic}"

Rules:
- Educational tone
- Fact-based
- Avoid fluff
- 200-300 words
- Focus on key concepts that would be tested in an exam

CONTENT:
{combined_text}

Provide a concise, educational summary:"""

    try:
        result = subprocess.run(
            [OLLAMA_CMD, "run", OLLAMA_ENRICHMENT_MODEL, prompt],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
            check=False
        )
        
        if result.returncode != 0:
            return ""
        
        return result.stdout.strip()
    except Exception as e:
        print(f"⚠ Knowledge synthesis failed for '{topic}': {e}")
        return ""

def enrich_knowledge_with_web_search(transcript):
    """Agent-03: Main function to enrich transcript with web knowledge"""
    mode_str = "FETCH_ALL (no filtering)" if FETCH_ALL_TOPICS else "STRICT (exam-safe)"
    print(f"\n🧠 Agent-03: Web Knowledge Enrichment [{mode_str}]")
    print("   Extracting topics from transcript...")
    
    # Step 1: Extract topics (LLM-first approach)
    topics = extract_topics_from_transcript(transcript)
    
    # Step 1b: Fallback to keyword-based extraction if LLM fails
    if not topics:
        print("   ⚠ LLM topic extraction failed, trying fallback extractor...")
        topics = fallback_topic_extraction(transcript)
        if not topics:
            print("   ⚠ No topics extracted (LLM + fallback both failed), skipping enrichment")
            print("   ℹ This is normal for very short, casual, or unclear transcripts")
            return ""
        print("   ✓ Fallback extraction succeeded")
    else:
        print(f"   ✓ LLM extracted {len(topics)} topics")
    
    # Step 2: Validate topics
    validated_topics = validate_topics(topics)
    if not validated_topics:
        print("   ⚠ No valid topics after validation, skipping enrichment")
        print("   ℹ Topics may be too generic or transcript too vague")
        return ""
    
    print(f"   ✓ Validated {len(validated_topics)} topics (from {len(topics)} extracted)")
    
    # Step 3-6: For each topic, generate queries, search, fetch, and synthesize
    enriched_knowledge = []
    
    for topic in validated_topics[:3]:  # Limit to top 3 topics to avoid timeout
        print(f"   📚 Enriching: {topic}")
        
        # Generate queries
        queries = generate_search_queries(topic)
        if not queries:
            continue
        
        # Search and fetch content
        web_texts = []
        for query in queries[:2]:  # Limit to 2 queries per topic
            urls = search_web_safely(query, max_results=1)
            for url in urls:
                text = fetch_clean_text(url)
                if text:
                    web_texts.append(text)
        
        if not web_texts:
            continue
        
        # Synthesize knowledge
        knowledge = synthesize_knowledge(topic, web_texts)
        if knowledge:
            enriched_knowledge.append(f"## {topic}\n{knowledge}")
    
    if not enriched_knowledge:
        print("   ⚠ No enriched knowledge generated")
        return ""
    
    result = "\n\n".join(enriched_knowledge)
    print(f"   ✓ Generated enriched knowledge ({len(result)} chars)")
    return result

# ===============================
# HARD DEDUP (FINAL GUARANTEE)
# ===============================
def deduplicate(questions):
    """Remove duplicate questions - ensures each question appears ONLY ONCE (no repeats)"""
    seen = set()
    unique = []

    for q in questions:
        if not isinstance(q, dict) or "question" not in q:
            continue
            
        # Normalize question text for better duplicate detection
        question_text = q.get("question", "").strip()
        if not question_text:
            continue
            
        # Create normalized key (lowercase, no punctuation, normalized spaces)
        normalized = question_text.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize spaces
        
        # Check for exact duplicates - each question must appear ONLY ONCE
        if normalized not in seen and normalized:
            seen.add(normalized)
            unique.append(q)
        # If duplicate found, skip it (don't add to unique list)

    return unique

# ===============================
# JSON REPAIR (HANDLE INCOMPLETE JSON)
# ===============================
def repair_json(json_str):
    """Try to repair incomplete or malformed JSON from Ollama"""
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Try to extract individual questions using regex
    questions = []
    # Pattern to match a complete question object
    pattern = r'\{\s*"question"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"options"\s*:\s*\{((?:\s*"[A-D]"\s*:\s*"(?:[^"\\]|\\.)*"\s*,?\s*)+)\}\s*,\s*"correct_answer"\s*:\s*"([A-D])"\s*,\s*"explanation"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}'
    
    for match in re.finditer(pattern, json_str, re.DOTALL):
        try:
            question_text = match.group(1)
            options_text = match.group(2)
            correct = match.group(3)
            explanation = match.group(4)
            
            # Parse options
            options = {}
            opt_pattern = r'"([A-D])"\s*:\s*"((?:[^"\\]|\\.)*)"'
            for opt_match in re.finditer(opt_pattern, options_text):
                options[opt_match.group(1)] = opt_match.group(2)
            
            if len(options) == 4 and question_text:
                questions.append({
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct,
                    "explanation": explanation
                })
        except:
            continue
    
    return questions

# ===============================
# OLLAMA MCQ GENERATOR (DIRECT BINARY)
# ===============================
def generate_mcqs_with_ollama(transcript, max_retries=None):
    """Generate MCQs using Ollama binary directly - ensures EXACTLY 20 questions (not less, not more)"""
    if max_retries is None:
        max_retries = 3 if FAST_MODE else 10  # Fewer retries in fast mode
    
    all_questions = []
    TARGET_COUNT = 20  # EXACTLY 20 questions required
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            needed = TARGET_COUNT - len(all_questions)
            if needed <= 0:
                # We have enough, but need to trim to exactly 20
                if len(all_questions) > TARGET_COUNT:
                    print(f"✓ Trimming to exactly {TARGET_COUNT} questions (had {len(all_questions)})")
                    return all_questions[:TARGET_COUNT]
                elif len(all_questions) == TARGET_COUNT:
                    print(f"✓ SUCCESS: Generated exactly {TARGET_COUNT} questions")
                    return all_questions
            print(f"🔄 Retry {attempt}/{max_retries}: Need {needed} more questions (have {len(all_questions)}/{TARGET_COUNT})...")
            
            # Generate only the missing questions
            prompt = f"""Generate EXACTLY {needed} MORE unique multiple-choice questions from this transcript.

CRITICAL REQUIREMENTS:
- Generate EXACTLY {needed} questions (not {needed-1}, not {needed+1}, EXACTLY {needed})
- These must be COMPLETELY DIFFERENT from questions already generated
- Each question must test a UNIQUE concept
- Output ONLY valid JSON, no other text

JSON FORMAT (EXACTLY {needed} questions):
{{
  "questions": [
    {{
      "question": "Question text?",
      "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
      "correct_answer": "A",
      "explanation": "Brief explanation"
    }}
  ]
}}

TRANSCRIPT:
{transcript[:MAX_TRANSCRIPT_CHARS]}

Generate EXACTLY {needed} NEW unique questions. Output JSON only:"""
        else:
            # First attempt - generate all 20
            prompt = f"""Generate EXACTLY 20 unique multiple-choice questions from this transcript.

CRITICAL REQUIREMENTS:
- Generate EXACTLY 20 questions (not 19, not 21, EXACTLY 20)
- Each question tests a DIFFERENT concept
- NO repeats - every question must be unique
- Output ONLY valid JSON, no markdown, no explanations outside JSON

JSON FORMAT (EXACTLY 20 questions):
{{
  "questions": [
    {{
      "question": "Question text?",
      "options": {{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}},
      "correct_answer": "A",
      "explanation": "Brief explanation"
    }}
  ]
}}

TRANSCRIPT:
{transcript[:MAX_TRANSCRIPT_CHARS]}

Generate EXACTLY 20 questions. Output JSON only:"""
        
        print("🧠 Generating 20 UNIQUE MCQs using Ollama binary (local, free)")
        if attempt == 0:
            print("   This may take 1-3 minutes depending on transcript length...")
        
        # Call Ollama binary directly via subprocess
        try:
            # Use UTF-8 encoding to avoid encoding issues
            result = subprocess.run(
                [OLLAMA_CMD, "run", OLLAMA_MODEL, prompt],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid chars instead of failing
                timeout=90 if FAST_MODE else 300,  # Faster timeout in fast mode
                check=False  # Don't raise on non-zero exit
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"Ollama failed with return code {result.returncode}\n"
                    f"Error: {result.stderr}\n"
                    f"Make sure Ollama is installed at: {OLLAMA_CMD}\n"
                    f"And model is pulled: ollama pull {OLLAMA_MODEL}"
                )
            
            content = result.stdout
            
            # Clean and extract JSON from response
            # Remove markdown code blocks if present
            content = content.replace("```json", "").replace("```", "").strip()
            
            # Find JSON boundaries
            start = content.find("{")
            end = content.rfind("}")
            
            if start == -1 or end == -1:
                raise RuntimeError(f"No JSON returned by Ollama. Output: {content[:200]}")
            
            json_str = content[start:end + 1]
            
            # Try to fix common JSON issues
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Try parsing JSON
            data = None
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                print("⚠ JSON parsing issue, attempting recovery...")
                
                # Try to extract questions using regex pattern matching
                recovered_questions = repair_json(json_str)
                
                if len(recovered_questions) >= 5:  # If we got at least 5 valid questions
                    print(f"✓ Recovered {len(recovered_questions)} questions from partial JSON")
                    data = {"questions": recovered_questions}
                else:
                    # Last resort: try to fix the JSON by closing it properly
                    error_pos = e.pos if hasattr(e, 'pos') else len(json_str)
                    
                    # Find the last complete question and close the JSON
                    last_complete = json_str.rfind('}')
                    if last_complete > 0 and last_complete > error_pos - 100:
                        # Try to close the questions array and main object
                        fixed_json = json_str[:last_complete + 1]
                        # Count open brackets/braces
                        open_braces = fixed_json.count('{') - fixed_json.count('}')
                        open_brackets = fixed_json.count('[') - fixed_json.count(']')
                        
                        # Close brackets first, then braces
                        fixed_json += ']' * open_brackets
                        fixed_json += '}' * open_braces
                        
                        try:
                            data = json.loads(fixed_json)
                            print("✓ Fixed incomplete JSON by closing brackets")
                        except:
                            pass
                    
                    if data is None:
                        # Try one more time with the recovered questions
                        if len(recovered_questions) > 0:
                            print(f"⚠ Using {len(recovered_questions)} recovered questions (may be incomplete)")
                            data = {"questions": recovered_questions}
                        else:
                            raise RuntimeError(
                                f"JSON parsing failed. Ollama generated incomplete/malformed JSON.\n"
                                f"Error: {str(e)}\n"
                                f"Position: {error_pos}\n"
                                f"Try running again - Ollama responses can be inconsistent.\n"
                                f"Response preview: {json_str[max(0, error_pos-200):error_pos+200]}"
                            )
            
            # Remove duplicates - ensure each question appears ONLY ONCE
            new_questions = deduplicate(data.get("questions", []))
            
            # Ensure all questions have required fields with defaults
            for q in new_questions:
                if 'explanation' not in q:
                    q['explanation'] = 'No explanation provided'
                if 'options' not in q:
                    q['options'] = {}
                if 'correct_answer' not in q:
                    q['correct_answer'] = 'A'
                if 'question' not in q:
                    q['question'] = 'Question text missing'
            
            if len(new_questions) == 0:
                if attempt < max_retries:
                    continue  # Try again
                else:
                    raise RuntimeError("No valid questions generated after all retries.")
            
            # Combine with existing questions and remove duplicates
            all_questions.extend(new_questions)
            all_questions = deduplicate(all_questions)
            
            # Check if we have exactly 20
            if len(all_questions) == TARGET_COUNT:
                print(f"✓ SUCCESS: Generated exactly {TARGET_COUNT} unique questions")
                return all_questions
            elif len(all_questions) > TARGET_COUNT:
                print(f"✓ SUCCESS: Generated {len(all_questions)} questions, trimming to exactly {TARGET_COUNT}")
                return all_questions[:TARGET_COUNT]
            
            # If we still need more and have retries left, continue
            if len(all_questions) < TARGET_COUNT and attempt < max_retries:
                continue
        
        except FileNotFoundError:
            if attempt < max_retries:
                print(f"⚠ Ollama not found, retrying...")
                continue
            raise RuntimeError(
                f"Ollama executable not found at: {OLLAMA_CMD}\n"
                f"Make sure Ollama is installed. Download from: https://ollama.com"
            )
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"⚠ Timeout, retrying...")
                continue
            raise RuntimeError(
                f"Ollama request timed out after 5 minutes.\n"
                f"Try using a smaller model or shorter transcript."
            )
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠ Error on attempt {attempt + 1}: {str(e)}")
                continue
            else:
                raise
    
    # Final result - MUST have exactly 20
    if len(all_questions) == TARGET_COUNT:
        print(f"✓ SUCCESS: Generated exactly {TARGET_COUNT} unique questions")
        return all_questions
    elif len(all_questions) > TARGET_COUNT:
        print(f"✓ SUCCESS: Generated {len(all_questions)} questions, trimming to exactly {TARGET_COUNT}")
        return all_questions[:TARGET_COUNT]
    else:
        # CRITICAL: We MUST have exactly 20, raise error if we can't get it
        raise RuntimeError(
            f"❌ FAILED: Could not generate exactly {TARGET_COUNT} questions after {max_retries + 1} attempts.\n"
            f"   Generated: {len(all_questions)} questions\n"
            f"   Required: {TARGET_COUNT} questions\n"
            f"   Missing: {TARGET_COUNT - len(all_questions)} questions\n\n"
            f"   Possible solutions:\n"
            f"   1. Use a longer/more detailed video\n"
            f"   2. Try a different Ollama model (e.g., llama3:8b)\n"
            f"   3. Check if transcript is too short or unclear\n"
            f"   4. Increase max_retries in the code"
        )

# ===============================
# MAIN
# ===============================
def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_quiz_generator.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    print("✓ FAST MODE ENABLED (No repetition)")

    fetcher = YouTubeTranscriptFetcher()

    try:
        print("Fetching transcript...")
        transcript = fetcher.fetch(url)
    except Exception as e:
        if IS_CLOUD_ENV:
            raise RuntimeError(
                "Transcript unavailable. Whisper fallback is disabled on cloud servers. "
                "Please use a video with available captions."
            )
        print("⚠ Transcript unavailable — using Whisper (slow)")
        transcript = WhisperAudioTranscriber().transcribe(url)

    transcript = clean_transcript(transcript)

    # Agent-03: Enrich knowledge with web search
    enriched_knowledge = enrich_knowledge_with_web_search(transcript)
    
    # Merge transcript with enriched knowledge
    if enriched_knowledge:
        enriched_context = f"{transcript}\n\n--- ENRICHED KNOWLEDGE ---\n\n{enriched_knowledge}"
        print("\n✓ Merging transcript with enriched knowledge...")
    else:
        enriched_context = transcript
        print("\n✓ Using transcript only (no enrichment)")

    questions = generate_mcqs_with_ollama(enriched_context)

    # Final validation: MUST have exactly 20 questions
    if len(questions) != 20:
        raise RuntimeError(
            f"❌ CRITICAL ERROR: Expected exactly 20 questions, but got {len(questions)}.\n"
            f"   This should not happen. Please report this issue."
        )

    print(f"\n✓ VALIDATED: Exactly {len(questions)} questions generated")
    print("\n" + "=" * 80)
    for i, q in enumerate(questions, 1):
        print(f"\nQ{i}. {q.get('question', 'N/A')}")
        options = q.get("options", {})
        for k, v in options.items():
            print(f"  {k}) {v}")
        correct_answer = q.get('correct_answer', 'N/A')
        print(f"✔ Answer: {correct_answer}")
        explanation = q.get('explanation', 'No explanation provided')
        if explanation and explanation != 'No explanation provided':
            print(f"ℹ {explanation}")

    with open("quiz_results.json", "w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, indent=2, ensure_ascii=False)

    print("\n✓ Saved to quiz_results.json")

# ===============================
# API WRAPPER FUNCTION (for FastAPI/REST API)
# ===============================
def generate_quiz_from_url(youtube_url: str):
    """
    Generate 20 unique MCQs from a YouTube URL.
    
    This is a clean wrapper function for API usage (no CLI prints, no file I/O).
    Returns the questions list directly.
    
    Args:
        youtube_url: YouTube video URL
        
    Returns:
        List of 20 MCQ dictionaries with keys: question, options, correct_answer, explanation
        
    Raises:
        RuntimeError: If exactly 20 questions cannot be generated
        Exception: For transcript fetching or processing errors
    """
    fetcher = YouTubeTranscriptFetcher()
    
    try:
        transcript = fetcher.fetch(youtube_url)
    except Exception as e:
        if IS_CLOUD_ENV:
            raise RuntimeError(
                "Transcript unavailable. Whisper fallback is disabled on cloud servers. "
                "Please use a video with available captions."
            )
        transcriber = WhisperAudioTranscriber(model=WHISPER_MODEL)
        transcript = transcriber.transcribe(youtube_url)
    
    transcript = clean_transcript(transcript)
    
    # Agent-03: Enrich knowledge with web search (skipped in FAST_MODE)
    if FAST_MODE:
        # Skip enrichment for faster processing (~30 seconds)
        enriched_context = transcript
    else:
        enriched_knowledge = enrich_knowledge_with_web_search(transcript)
        if enriched_knowledge:
            enriched_context = f"{transcript}\n\n--- ENRICHED KNOWLEDGE ---\n\n{enriched_knowledge}"
        else:
            enriched_context = transcript
    
    questions = generate_mcqs_with_ollama(enriched_context, max_retries=3 if FAST_MODE else 10)
    
    # Final validation: MUST have exactly 20 questions
    if len(questions) != 20:
        raise RuntimeError(
            f"Expected exactly 20 questions, but got {len(questions)}"
        )
    
    return questions


def generate_quiz_from_video_url(video_url: str):
    """
    Generate 20 unique MCQs from a direct video URL (S3, CDN, HTTPS).
    
    This function works with any HTTP/HTTPS video URL - no YouTube, no yt-dlp, no cookies.
    Perfect for course videos stored on S3, CDN, or any web server.
    
    Pipeline:
    1. Download video from URL
    2. Extract audio using FFmpeg
    3. Transcribe with Whisper
    4. Agent-03: Web knowledge enrichment
    5. Generate 20 unique MCQs using Ollama
    
    Args:
        video_url: HTTP/HTTPS URL to video file (e.g., S3 URL)
        
    Returns:
        List of 20 MCQ dictionaries with keys: question, options, correct_answer, explanation
        
    Raises:
        RuntimeError: If exactly 20 questions cannot be generated
        Exception: For video download, transcription, or processing errors
    """
    # Step 1: Transcribe video from URL
    transcriber = VideoURLTranscriber(model=WHISPER_MODEL)
    transcript = transcriber.transcribe_from_url(video_url)
    
    # Step 2: Clean transcript
    transcript = clean_transcript(transcript)
    
    # Step 3: Agent-03: Enrich knowledge with web search (skipped in FAST_MODE)
    if FAST_MODE:
        # Skip enrichment for faster processing (~30 seconds)
        enriched_context = transcript
    else:
        enriched_knowledge = enrich_knowledge_with_web_search(transcript)
        if enriched_knowledge:
            enriched_context = f"{transcript}\n\n--- ENRICHED KNOWLEDGE ---\n\n{enriched_knowledge}"
        else:
            enriched_context = transcript
    
    # Step 4: Generate MCQs
    questions = generate_mcqs_with_ollama(enriched_context, max_retries=3 if FAST_MODE else 10)
    
    # Step 6: Validate
    if len(questions) != 20:
        raise RuntimeError(
            f"Expected exactly 20 questions, but got {len(questions)}"
        )
    
    return questions


# ===============================
if __name__ == "__main__":
    main()
