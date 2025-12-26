"""
YouTube URL → MCQ Generator (FAST + UNIQUE, 100% FREE, Windows Safe)

Pipeline:
YouTube URL
→ YouTube Transcript API (auto-translate if needed)
→ Whisper (ONLY if captions unavailable)
→ Ollama Binary (direct execution, no HTTP)
→ 20 UNIQUE MCQs (valid JSON)
"""

import os
import re
import json
import sys
import tempfile
import subprocess
from urllib.parse import urlparse, parse_qs

# ===============================
# OLLAMA CONFIG (FAST + STABLE)
# ===============================
OLLAMA_EXE = r"C:\Users\Hp\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_MODEL = "gemma2:2b"  # Fast model, good for MCQs. Alternatives: "llama3", "mistral"
MAX_TRANSCRIPT_CHARS = 4000   # speed-critical

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
        path = os.path.join(tempfile.gettempdir(), "yt_audio")

        opts = {
            "format": "bestaudio/best",
            "outtmpl": path + ".%(ext)s",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
            ],
            "quiet": True,
            "retries": 5,
            "fragment_retries": 5,

            # ✅ CORRECT js_runtimes FORMAT
            "js_runtimes": {
                "node": {}
            },

            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        }

        with self.yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        return path + ".mp3"

    def transcribe(self, url):
        audio = self.download_audio(url)
        result = self.model.transcribe(audio)
        os.remove(audio)
        return result["text"]

# ===============================
# CLEAN + SHRINK TRANSCRIPT
# ===============================
def clean_transcript(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:MAX_TRANSCRIPT_CHARS]

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
def generate_mcqs_with_ollama(transcript, max_retries=3):
    """Generate MCQs using Ollama binary directly - ensures exactly 20 questions with retries"""
    all_questions = []
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            needed = 20 - len(all_questions)
            if needed <= 0:
                break
            print(f"🔄 Retry {attempt}/{max_retries}: Generating {needed} more questions...")
            
            # Generate only the missing questions
            prompt = f"""Generate EXACTLY {needed} MORE unique multiple-choice questions from this transcript.

CRITICAL: These must be DIFFERENT from questions already generated. Each question must test a UNIQUE concept.

JSON FORMAT:
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

Generate EXACTLY {needed} NEW unique questions (JSON only):"""
        else:
            # First attempt - generate all 20
            prompt = f"""Generate EXACTLY 20 unique multiple-choice questions from this transcript.

REQUIREMENTS:
- EXACTLY 20 questions (no more, no less)
- Each question tests a DIFFERENT concept
- NO repeats - every question unique
- Output ONLY valid JSON

JSON FORMAT:
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

Generate EXACTLY 20 questions now (JSON only):"""
        
        print("🧠 Generating 20 UNIQUE MCQs using Ollama binary (local, free)")
        if attempt == 0:
            print("   This may take 1-3 minutes depending on transcript length...")
        
        # Call Ollama binary directly via subprocess
        try:
            # Use UTF-8 encoding to avoid Windows encoding issues
            result = subprocess.run(
                [OLLAMA_EXE, "run", OLLAMA_MODEL, prompt],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid chars instead of failing
                timeout=300,  # 5 minutes timeout
                check=False  # Don't raise on non-zero exit
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"Ollama failed with return code {result.returncode}\n"
                    f"Error: {result.stderr}\n"
                    f"Make sure Ollama is installed at: {OLLAMA_EXE}\n"
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
            
            # Check if we have enough
            if len(all_questions) >= 20:
                print(f"✓ SUCCESS: Generated exactly {len(all_questions)} unique questions (using first 20)")
                return all_questions[:20]
            
            # If we still need more and have retries left, continue
            if len(all_questions) < 20 and attempt < max_retries:
                continue
        
        except FileNotFoundError:
            if attempt < max_retries:
                print(f"⚠ Ollama not found, retrying...")
                continue
            raise RuntimeError(
                f"Ollama executable not found at: {OLLAMA_EXE}\n"
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
    
    # Final result
    if len(all_questions) >= 20:
        print(f"✓ SUCCESS: Generated {len(all_questions)} unique questions (using first 20)")
        return all_questions[:20]
    else:
        print(f"⚠ Final result: {len(all_questions)} unique questions (requested 20)")
        if len(all_questions) < 10:
            print("⚠ Too few questions. The model may be struggling. Try a different model or shorter transcript.")
        return all_questions

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
    except Exception:
        print("⚠ Transcript unavailable — using Whisper (slow)")
        transcript = WhisperAudioTranscriber().transcribe(url)

    transcript = clean_transcript(transcript)

    questions = generate_mcqs_with_ollama(transcript)

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
if __name__ == "__main__":
    main()
