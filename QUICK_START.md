# Quick Start Guide - Video MCQ Generator

Complete setup and run instructions for the Video MCQ Generator.

---

## 📋 Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **Ollama** - Local LLM for question generation
- **FFmpeg** - For audio/video processing
- **Internet connection** - For YouTube transcripts and web search

---

## 🚀 Installation Steps

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `youtube-transcript-api` - YouTube transcript fetching
- `openai-whisper` - Offline audio transcription
- `yt-dlp` - YouTube audio download (for Whisper fallback)
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `beautifulsoup4` - Web scraping
- `requests` - HTTP requests

### Step 2: Install Ollama

**Windows:**
1. Download from: https://ollama.com/download
2. Run the installer
3. Verify: Open PowerShell and run `ollama --version`

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

### Step 3: Pull Required Ollama Models

```bash
ollama pull gemma2:2b
ollama pull mistral:7b
```

**Verify models:**
```bash
ollama list
```

Expected output:
```
NAME           SIZE
gemma2:2b      ~2GB
mistral:7b     ~4GB
```

### Step 4: Install FFmpeg

**Windows:**
```powershell
# Option 1: Using winget
winget install ffmpeg

# Option 2: Using Chocolatey
choco install ffmpeg

# Option 3: Manual download from https://ffmpeg.org
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### Step 5: Start Ollama Service

**Windows:**
- Ollama runs automatically as a service (no action needed)

**Linux/macOS:**
```bash
ollama serve
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

---

## 🎯 Running the Application

### Option 1: CLI Mode (Command Line)

Generate MCQs from a YouTube URL:

```bash
python youtube_quiz_generator.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Example:**
```bash
python youtube_quiz_generator.py "https://youtu.be/CMre3PObLV0"
```

**Output:**
- Prints 20 questions to console
- Saves to `quiz_results.json`

---

### Option 2: REST API Mode (Recommended for Backend Integration)

#### Start the API Server

**Development mode (with auto-reload):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Python directly:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Access the API

- **API Base URL**: `http://localhost:8000`
- **Interactive Docs (Swagger)**: `http://localhost:8000/docs`
- **Alternative Docs (ReDoc)**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

---

## 📡 API Endpoints

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Video MCQ Generator API"
}
```

---

### 2. Generate Quiz from YouTube URL

```bash
curl -X POST "http://localhost:8000/generate-quiz" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }'
```

**Response:**
```json
{
  "questions": [
    {
      "question": "What is the primary purpose of machine learning?",
      "options": {
        "A": "To store large amounts of data",
        "B": "To enable computers to learn from data without explicit programming",
        "C": "To replace human programmers",
        "D": "To create graphical user interfaces"
      },
      "correct_answer": "B",
      "explanation": "Machine learning enables computers to learn patterns from data..."
    },
    // ... 19 more questions
  ]
}
```

---

### 3. Generate Quiz from Direct Video URL (S3, CDN, HTTPS)

```bash
curl -X POST "http://localhost:8000/generate-quiz-from-video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://sanora-india.s3.us-east-1.amazonaws.com/uploads/video.mp4"
  }'
```

**Perfect for:**
- S3 URLs
- CDN URLs
- Any HTTPS video URL
- Course videos stored on web servers

---

### 4. Generate Quiz from Multiple Course Videos

```bash
curl -X POST "http://localhost:8000/generate-course-quiz" \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "radiography_101",
    "video_urls": [
      "https://sanora-india.s3.us-east-1.amazonaws.com/uploads/video1.mp4",
      "https://sanora-india.s3.us-east-1.amazonaws.com/uploads/video2.mp4"
    ]
  }'
```

**Response:**
```json
{
  "course_id": "radiography_101",
  "results": [
    {
      "video_url": "https://...",
      "questions": [ /* 20 MCQs */ ]
    },
    {
      "video_url": "https://...",
      "questions": [ /* 20 MCQs */ ]
    }
  ]
}
```

---

## 🧪 Testing the API

### Python Example

```python
import requests

# Test health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Generate quiz from YouTube
response = requests.post(
    "http://localhost:8000/generate-quiz",
    json={"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"},
    timeout=600  # 10 minutes
)
data = response.json()
print(f"Generated {len(data['questions'])} questions")
```

### JavaScript Example

```javascript
const response = await fetch('http://localhost:8000/generate-quiz', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    youtube_url: 'https://www.youtube.com/watch?v=VIDEO_ID'
  })
});

const data = await response.json();
console.log(`Generated ${data.questions.length} questions`);
```

---

## ⚙️ Configuration

### Environment Variables

**For Cloud Deployment (Azure/Linux):**
```bash
export CLOUD_ENV=true  # Disables Whisper fallback (required on cloud)
```

**For Local Development:**
```bash
# No environment variables needed
# Whisper fallback is enabled by default
```

### Ollama Models

The code auto-detects Ollama installation. Models used:
- **MCQ Generation**: `gemma2:2b` (fast, good quality)
- **Knowledge Enrichment**: `mistral:7b` (better for synthesis)

To use different models, edit `youtube_quiz_generator.py`:
```python
OLLAMA_MODEL = "llama3:8b"  # Change MCQ model
OLLAMA_ENRICHMENT_MODEL = "llama3:8b"  # Change enrichment model
```

---

## 🔧 Troubleshooting

### "Ollama not found"

**Solution:**
1. Verify Ollama is installed: `ollama --version`
2. Ensure Ollama is in PATH or installed in default location
3. On Windows: Check `C:\Users\YourName\AppData\Local\Programs\Ollama\ollama.exe`
4. On Linux: Check `/usr/local/bin/ollama`

### "FFmpeg not found"

**Solution:**
1. Install FFmpeg (see Step 4 above)
2. Verify: `ffmpeg -version`
3. Ensure FFmpeg is in PATH

### "Model not found" (Ollama)

**Solution:**
```bash
ollama pull gemma2:2b
ollama pull mistral:7b
```

### "Port 8000 already in use"

**Solution:**
```bash
# Use a different port
uvicorn app.main:app --port 8001
```

### "Transcript unavailable" (Cloud)

**On cloud servers**, Whisper fallback is disabled. Solution:
1. Use videos with YouTube captions enabled
2. Or set `CLOUD_ENV=false` (not recommended - may fail)

### "Timeout errors"

**Solution:**
- Increase client timeout: `timeout=600` (10 minutes)
- For very long videos, consider chunking or async processing

---

## 📊 Processing Time

| Scenario | Typical Time |
|----------|--------------|
| Short video (< 10 min) with transcript | 2-3 minutes |
| Medium video (10-30 min) with transcript | 3-5 minutes |
| Long video (> 30 min) with transcript | 5-8 minutes |
| Video without transcript (Whisper) | 8-15 minutes |
| Video with Agent-03 enrichment | +1-3 minutes |

---

## ✅ Verification Checklist

Before running, verify:

- [ ] Python 3.9+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Ollama installed and running
- [ ] Models pulled (`ollama list` shows gemma2:2b and mistral:7b)
- [ ] FFmpeg installed (`ffmpeg -version` works)
- [ ] Ollama service running (`curl http://localhost:11434/api/tags`)

---

## 🎉 You're Ready!

**Quick Test:**
```bash
# Start API server
uvicorn app.main:app --reload

# In another terminal, test health
curl http://localhost:8000/health

# Generate quiz
curl -X POST "http://localhost:8000/generate-quiz" \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

For detailed API documentation, see `API_DOCUMENTATION.md`.
