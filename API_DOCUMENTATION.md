# YouTube MCQ Generator API - Backend Integration Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation & Setup](#installation--setup)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Schemas](#requestresponse-schemas)
6. [Integration Examples](#integration-examples)
7. [Error Handling](#error-handling)
8. [Performance & Limitations](#performance--limitations)
9. [Deployment Guide](#deployment-guide)
10. [Security Considerations](#security-considerations)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The **YouTube MCQ Generator API** is a REST API service that automatically generates **exactly 20 unique multiple-choice questions** from any YouTube video URL. The service uses:

- **YouTube Transcript API** for automatic transcript fetching (primary method)
- **Whisper** (offline) as fallback for videos without transcripts (local environments only)
- **Agent-03**: Web knowledge enrichment for enhanced question quality
- **Ollama** (local LLM) for question generation (100% free, no API keys)

### Key Features

✅ **Guaranteed 20 Questions**: Always returns exactly 20 unique MCQs  
✅ **No API Keys Required**: Uses local Ollama models (completely free)  
✅ **Automatic Transcript Fetching**: Works with YouTube's transcript API  
✅ **Knowledge Enrichment**: Agent-03 enhances questions with web knowledge  
✅ **Production Ready**: FastAPI with CORS, error handling, and validation  

### Pipeline Flow

```
YouTube URL
    ↓
YouTube Transcript API (PRIMARY - works everywhere)
    ↓
Whisper Fallback (ONLY if transcript unavailable AND not on cloud)
    ↓
Agent-03: Web Knowledge Enrichment
    ├─ Topic Extraction (Ollama)
    ├─ Topic Validation
    ├─ Web Search (Wikipedia, trusted domains)
    └─ Knowledge Synthesis
    ↓
Merged Context (Transcript + Enriched Knowledge)
    ↓
Ollama MCQ Generation
    ↓
20 Unique MCQs (JSON)
```

### ⚠️ Important: Cloud Environment Behavior

**Transcript Fetching Priority:**

1. **Primary**: YouTube Transcript API (works on all environments)
2. **Fallback**: Whisper (offline transcription) - **ONLY available on local machines**

**Why Whisper is disabled on cloud:**

- Whisper requires `yt-dlp` to download audio from YouTube
- YouTube blocks `yt-dlp` requests from cloud server IPs (Azure, AWS, Render, etc.)
- This is a platform constraint, not a code limitation

**Environment Control:**

Set `CLOUD_ENV=true` environment variable to disable Whisper fallback on cloud servers:

```bash
export CLOUD_ENV=true
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Behavior:**
- **Local machine** (no `CLOUD_ENV`): Full pipeline with Whisper fallback ✅
- **Cloud VM** (`CLOUD_ENV=true`): Transcript API only, clear error if unavailable ✅

**Error Response (Cloud):**
```json
{
  "detail": "Transcript unavailable. Whisper fallback is disabled on cloud servers. Please use a video with available captions."
}
```

This is **correct system behavior** - not a failure. The API will only work with videos that have YouTube captions enabled when running on cloud servers.

---

## System Requirements

### Server Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows Server
- **RAM**: Minimum 8 GB (16 GB recommended)
- **CPU**: 4+ cores recommended
- **Storage**: 10 GB free space (for Ollama models)
- **Python**: 3.9+ (3.11+ recommended)

### Software Dependencies

- **Ollama**: Must be installed and running
  - Download: https://ollama.com
  - Required models: `gemma2:2b`, `mistral:7b`
  - **Note**: The code auto-detects Ollama path (OS-aware). If Ollama is in PATH, it will be found automatically. Otherwise, it checks common installation paths for Windows/Linux/macOS.
- **FFmpeg**: Required for Whisper audio processing
  - Install: `apt-get install ffmpeg` (Linux) or download from https://ffmpeg.org

### Network Requirements

- **Port 8000**: API server (configurable)
- **Port 11434**: Ollama service (default, localhost only)
- **Internet Access**: Required for YouTube transcript fetching and web search

---

## Installation & Setup

### Step 1: Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download installer from https://ollama.com/download

**Verify Installation:**
```bash
ollama --version
```

### Step 2: Pull Required Models

```bash
ollama pull gemma2:2b
ollama pull mistral:7b
```

**Verify Models:**
```bash
ollama list
```

Expected output:
```
NAME           SIZE
gemma2:2b      ~2GB
mistral:7b     ~4GB
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `fastapi>=0.104.0`
- `uvicorn[standard]>=0.24.0`
- `pydantic>=2.0.0`
- `youtube-transcript-api>=0.6.1`
- `yt-dlp>=2023.12.30`
- `openai-whisper` (for offline transcription)
- `beautifulsoup4>=4.12.0`
- `requests>=2.31.0`

### Step 4: Start Ollama Service

**Linux (if not running as service):**
```bash
ollama serve
```

**Windows:**
Ollama runs automatically as a service.

**Verify Ollama is Running:**
```bash
curl http://localhost:11434/api/tags
```

### Step 5: Start API Server

**Development Mode:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production Mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Python Directly:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Step 6: Verify API is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "YouTube MCQ Generator API"
}
```

---

## API Endpoints

### Base URL

```
http://your-server-ip:8000
```

### Interactive Documentation

- **Swagger UI**: `http://your-server-ip:8000/docs`
- **ReDoc**: `http://your-server-ip:8000/redoc`

---

### POST `/generate-quiz`

Generate 20 unique MCQs from a YouTube video URL.

**Endpoint:** `POST /generate-quiz`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Supported URL Formats:**
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtu.be/VIDEO_ID?si=PARAMS` (query params are ignored)

**Response (200 OK):**
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
      "explanation": "Machine learning enables computers to learn patterns from data and make predictions without being explicitly programmed for each task."
    },
    // ... 19 more questions
  ]
}
```

**Response Guarantees:**
- ✅ Always returns **exactly 20 questions**
- ✅ All questions are **unique** (no duplicates)
- ✅ Each question has **4 options** (A, B, C, D)
- ✅ Each question has a **correct_answer** (A, B, C, or D)
- ✅ Each question has an **explanation** (string)

**Processing Time:**
- **Typical**: 2-5 minutes
- **With Whisper fallback**: 5-10 minutes
- **With Agent-03 enrichment**: Additional 1-3 minutes

**Error Responses:**

**400 Bad Request** - Invalid URL format:
```json
{
  "detail": "Invalid YouTube URL"
}
```

**500 Internal Server Error** - Generation failed:
```json
{
  "detail": "Quiz generation failed: Expected exactly 20 questions, but got 16"
}
```

**500 Internal Server Error** - Transcript unavailable:
```json
{
  "detail": "Quiz generation failed: Transcript unavailable or corrupted"
}
```

**500 Internal Server Error** - Whisper fallback disabled (cloud environment):
```json
{
  "detail": "Transcript unavailable. Whisper fallback is disabled on cloud servers. Please use a video with available captions."
}
```

**Note:** This error occurs when:
- Running on cloud server (`CLOUD_ENV=true`)
- Video has no YouTube captions available
- Whisper fallback is intentionally disabled (YouTube blocks yt-dlp on cloud IPs)

**Solution:** Use a video with YouTube captions enabled, or run on a local machine where Whisper fallback is available.

---

### GET `/health`

Health check endpoint to verify API is running.

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "YouTube MCQ Generator API"
}
```

**Use Cases:**
- Load balancer health checks
- Monitoring/alerting systems
- Service discovery

---

## Request/Response Schemas

### Request Schema

**QuizRequest:**
```typescript
{
  youtube_url: string (valid URL, required)
}
```

**Validation:**
- Must be a valid URL
- Must be a YouTube URL (youtube.com or youtu.be)

### Response Schema

**QuizResponse:**
```typescript
{
  questions: MCQ[]  // Array of exactly 20 MCQs
}
```

**MCQ:**
```typescript
{
  question: string,           // The question text
  options: {                  // Dictionary with 4 options
    "A": string,
    "B": string,
    "C": string,
    "D": string
  },
  correct_answer: "A" | "B" | "C" | "D",  // One of the four options
  explanation: string         // Explanation of the correct answer
}
```

---

## Integration Examples

### Python (requests)

```python
import requests
import json

API_BASE_URL = "http://your-server-ip:8000"

def generate_quiz(youtube_url: str):
    """Generate 20 MCQs from YouTube URL"""
    url = f"{API_BASE_URL}/generate-quiz"
    payload = {"youtube_url": youtube_url}
    
    try:
        response = requests.post(url, json=payload, timeout=600)  # 10 min timeout
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Generated {len(data['questions'])} questions")
        return data["questions"]
    except requests.exceptions.Timeout:
        print("❌ Request timed out (video may be too long)")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ API Error: {e.response.json()}")
        return None

# Usage
questions = generate_quiz("https://www.youtube.com/watch?v=VIDEO_ID")

if questions:
    for i, q in enumerate(questions, 1):
        print(f"\nQ{i}. {q['question']}")
        for option, text in q['options'].items():
            print(f"  {option}) {text}")
        print(f"✔ Answer: {q['correct_answer']}")
        print(f"ℹ {q['explanation']}")
```

### JavaScript (fetch) - Frontend Integration

```javascript
const API_BASE_URL = 'http://your-server-ip:8000';

async function generateQuiz(youtubeUrl) {
  try {
    const response = await fetch(`${API_BASE_URL}/generate-quiz`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        youtube_url: youtubeUrl
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Quiz generation failed');
    }

    const data = await response.json();
    console.log(`✅ Generated ${data.questions.length} questions`);
    return data.questions;
  } catch (error) {
    console.error('❌ Error:', error.message);
    throw error;
  }
}

// Usage in React/Vue/Angular
async function handleGenerateQuiz() {
  const youtubeUrl = document.getElementById('youtube-url').value;
  
  try {
    setLoading(true);
    const questions = await generateQuiz(youtubeUrl);
    setQuestions(questions);
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
}
```

### cURL

```bash
curl -X POST "http://your-server-ip:8000/generate-quiz" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
  }' \
  --max-time 600
```

### Node.js (axios)

```javascript
const axios = require('axios');

const API_BASE_URL = 'http://your-server-ip:8000';

async function generateQuiz(youtubeUrl) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/generate-quiz`,
      { youtube_url: youtubeUrl },
      { timeout: 600000 }  // 10 minutes
    );
    
    return response.data.questions;
  } catch (error) {
    if (error.response) {
      console.error('API Error:', error.response.data);
    } else {
      console.error('Network Error:', error.message);
    }
    throw error;
  }
}

// Usage
generateQuiz('https://www.youtube.com/watch?v=VIDEO_ID')
  .then(questions => {
    console.log(`Generated ${questions.length} questions`);
  })
  .catch(console.error);
```

### PHP

```php
<?php
function generateQuiz($youtubeUrl, $apiBaseUrl = 'http://your-server-ip:8000') {
    $ch = curl_init($apiBaseUrl . '/generate-quiz');
    
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => json_encode(['youtube_url' => $youtubeUrl]),
        CURLOPT_TIMEOUT => 600
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode === 200) {
        $data = json_decode($response, true);
        return $data['questions'];
    } else {
        $error = json_decode($response, true);
        throw new Exception($error['detail'] ?? 'Quiz generation failed');
    }
}

// Usage
try {
    $questions = generateQuiz('https://www.youtube.com/watch?v=VIDEO_ID');
    echo "Generated " . count($questions) . " questions\n";
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
?>
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful, 20 questions returned |
| 400 | Bad Request | Invalid URL format or missing required field |
| 500 | Internal Server Error | Quiz generation failed (see detail message) |

### Error Response Format

All errors return JSON in this format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

**1. Invalid YouTube URL:**
```json
{
  "detail": "Invalid YouTube URL"
}
```
**Solution:** Verify URL format is correct

**2. Transcript Unavailable:**
```json
{
  "detail": "Quiz generation failed: Transcript unavailable or corrupted"
}
```
**Solution:** Video may not have captions. The system will attempt Whisper fallback automatically.

**3. Timeout:**
```json
{
  "detail": "Quiz generation failed: Request timed out"
}
```
**Solution:** Video may be very long. Increase client timeout or use async processing.

**4. Ollama Not Running:**
```json
{
  "detail": "Quiz generation failed: Ollama service not available"
}
```
**Solution:** Ensure Ollama is installed and running (`ollama serve`)

**5. Insufficient Questions Generated:**
```json
{
  "detail": "Expected exactly 20 questions, but got 16"
}
```
**Solution:** This is rare. The system retries automatically. If it persists, the video content may be too short or unclear.

### Best Practices for Error Handling

```python
import requests
from requests.exceptions import Timeout, RequestException

def generate_quiz_safe(youtube_url: str, max_retries: int = 3):
    """Generate quiz with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_BASE_URL}/generate-quiz",
                json={"youtube_url": youtube_url},
                timeout=600
            )
            response.raise_for_status()
            return response.json()["questions"]
            
        except Timeout:
            if attempt < max_retries - 1:
                print(f"⏳ Timeout, retrying ({attempt + 1}/{max_retries})...")
                continue
            raise Exception("Request timed out after multiple retries")
            
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.json().get("detail", "Unknown error")
            if "transcript" in error_detail.lower():
                raise Exception("Video transcript unavailable")
            raise Exception(f"API error: {error_detail}")
            
        except RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    raise Exception("Failed after all retries")
```

---

## Performance & Limitations

### Processing Time

| Scenario | Typical Time | Notes |
|----------|--------------|-------|
| Short video (< 10 min) with transcript | 2-3 minutes | Fastest path |
| Medium video (10-30 min) with transcript | 3-5 minutes | Standard processing |
| Long video (> 30 min) with transcript | 5-8 minutes | May hit timeout limits |
| Video without transcript (Whisper) | 8-15 minutes | Audio processing is slow |
| Video with Agent-03 enrichment | +1-3 minutes | Additional web search time |

### Rate Limits

**Current Implementation:** No rate limiting (unlimited requests)

**Recommendation for Production:**
- Implement rate limiting (e.g., 10 requests/hour per IP)
- Use Redis for request queuing
- Consider async processing for long videos

### Resource Usage

**CPU:** High during processing (Ollama inference)  
**RAM:** 4-8 GB during processing (model loading)  
**Network:** Moderate (YouTube API, web search)  
**Storage:** 10+ GB (Ollama models)

### Limitations

1. **Video Length:** Very long videos (> 1 hour) may timeout
2. **Language:** Best results for English content (transcript translation available)
3. **Content Quality:** Poor audio quality affects Whisper accuracy
4. **Network Dependency:** Requires internet for YouTube API and web search
5. **Ollama Dependency:** Must have Ollama installed and running

### Scalability Recommendations

- **Horizontal Scaling:** Run multiple API instances behind load balancer
- **Caching:** Cache results for same YouTube URL (Redis)
- **Async Processing:** Use Celery/Redis Queue for long-running tasks
- **CDN:** Serve static documentation from CDN

---

## Deployment Guide

### Production Deployment (Linux)

#### Option 1: Systemd Service

Create `/etc/systemd/system/mcq-api.service`:

```ini
[Unit]
Description=YouTube MCQ Generator API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mcq-api
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable mcq-api
sudo systemctl start mcq-api
sudo systemctl status mcq-api
```

#### Option 2: Docker

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pull Ollama models
RUN ollama pull gemma2:2b && ollama pull mistral:7b

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Start Ollama and API
CMD ollama serve & uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Build and run:**
```bash
docker build -t mcq-generator-api .
docker run -d -p 8000:8000 --name mcq-api mcq-generator-api
```

#### Option 3: Azure App Service / AWS Elastic Beanstalk

1. **Create `Procfile`:**
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
```

2. **Configure environment variables:**
- `CLOUD_ENV=true` (required for cloud deployments - disables Whisper fallback)
- `OLLAMA_MODEL=gemma2:2b` (optional, defaults shown)
- `OLLAMA_ENRICHMENT_MODEL=mistral:7b` (optional, defaults shown)

**Note**: `OLLAMA_CMD` is auto-detected (OS-aware). The code will find Ollama if it's in PATH or installed in common locations.

3. **Deploy via Git or CI/CD pipeline**

### Nginx Reverse Proxy (Recommended)

**`/etc/nginx/sites-available/mcq-api`:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_connect_timeout 600s;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/mcq-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL/HTTPS Setup (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## Security Considerations

### 1. CORS Configuration

**Current (Development):**
```python
allow_origins=["*"]  # Allows all origins
```

**Production (Recommended):**
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://app.yourdomain.com"
]
```

### 2. API Key Authentication (Optional)

Add to `app/main.py`:
```python
from fastapi import Depends, HTTPException, Header

API_KEY = os.getenv("API_KEY", "your-secret-key")

def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

@app.post("/generate-quiz")
def generate_quiz(payload: QuizRequest, api_key: str = Depends(verify_api_key)):
    # ... existing code
```

### 3. Rate Limiting

Install `slowapi`:
```bash
pip install slowapi
```

Add to `app/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/generate-quiz")
@limiter.limit("10/hour")
def generate_quiz(payload: QuizRequest):
    # ... existing code
```

### 4. Input Validation

- ✅ Pydantic automatically validates URLs
- ✅ YouTube URL format is enforced
- ✅ Request size limits (configure in uvicorn)

### 5. Environment Variables

Store sensitive config in environment variables:
```bash
export CLOUD_ENV="true"  # Set to "true" on cloud servers (disables Whisper fallback)
export API_KEY="your-secret-key"
export OLLAMA_MODEL="gemma2:2b"  # Optional: override default model
```

**Note**: `OLLAMA_CMD` is auto-detected - no need to set it manually. The code will find Ollama automatically if it's in PATH or installed in common locations.

---

## Troubleshooting

### Issue: "Ollama service not available"

**Symptoms:**
- API returns 500 error
- Error message mentions Ollama

**Solutions:**
1. Check if Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Start Ollama:
   ```bash
   ollama serve
   ```
3. Verify models are installed:
   ```bash
   ollama list
   ```

### Issue: "Port 8000 already in use"

**Solutions:**
1. Find process using port:
   ```bash
   lsof -i :8000  # Linux/Mac
   netstat -ano | findstr :8000  # Windows
   ```
2. Kill process or use different port:
   ```bash
   uvicorn app.main:app --port 8001
   ```

### Issue: "Import errors"

**Symptoms:**
- `ModuleNotFoundError` when starting API

**Solutions:**
1. Verify virtual environment is activated
2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```
3. Check Python version:
   ```bash
   python --version  # Should be 3.9+
   ```

### Issue: "Timeout errors"

**Symptoms:**
- Request times out after 30-60 seconds
- Long videos fail

**Solutions:**
1. Increase client timeout:
   ```python
   requests.post(url, json=payload, timeout=600)  # 10 minutes
   ```
2. Increase uvicorn timeout:
   ```bash
   uvicorn app.main:app --timeout-keep-alive 600
   ```
3. Consider async processing for very long videos

### Issue: "Only 16 questions generated instead of 20"

**Symptoms:**
- API returns error about question count

**Solutions:**
1. This is rare - system retries automatically
2. If persistent, video content may be too short
3. Check logs for Ollama errors
4. Try a different video to verify system is working

### Issue: "Whisper transcription fails"

**Symptoms:**
- Error about audio processing
- FFmpeg errors

**Solutions:**
1. Verify FFmpeg is installed:
   ```bash
   ffmpeg -version
   ```
2. Install FFmpeg:
   ```bash
   apt-get install ffmpeg  # Linux
   # or download from https://ffmpeg.org
   ```
3. Check audio download permissions (yt-dlp)

---

## Support & Contact

For issues, questions, or feature requests:
- **GitHub Issues**: [Your repository URL]
- **Email**: [Your email]
- **Documentation**: See `/docs` endpoint for interactive API docs

---

## Changelog

### Version 1.0.0 (Current)
- ✅ Initial release
- ✅ FastAPI REST API
- ✅ Ollama integration (local LLM)
- ✅ Agent-03 knowledge enrichment
- ✅ Guaranteed 20 unique questions
- ✅ CORS support
- ✅ Health check endpoint

---

## License

[Your License Here]

---

**Last Updated:** [Current Date]  
**API Version:** 1.0.0

