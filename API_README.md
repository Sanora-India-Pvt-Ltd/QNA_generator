# YouTube MCQ Generator REST API

Production-ready FastAPI REST API wrapper for the YouTube MCQ Generator pipeline.

## 🏗️ Architecture

```
mcq_api/
│
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── schemas.py           # Request/Response models (Pydantic)
│   └── services/
│       └── quiz_service.py  # Bridge to core logic
│
├── youtube_quiz_generator.py  # Core pipeline (unchanged)
├── requirements.txt
└── API_README.md
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
uvicorn app.main:app --reload
```

Or using Python directly:

```bash
python -m uvicorn app.main:app --reload
```

### 3. Access the API

- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Docs (Swagger)**: `http://127.0.0.1:8000/docs`
- **Alternative Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

## 📡 API Endpoints

### POST `/generate-quiz`

Generate 20 unique MCQs from a YouTube video URL.

**Request Body:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXX"
}
```

**Response (200 OK):**
```json
{
  "questions": [
    {
      "question": "What is ionizing radiation?",
      "options": {
        "A": "Non-harmful electromagnetic waves",
        "B": "Radiation that can remove electrons from atoms",
        "C": "Visible light spectrum",
        "D": "Sound waves"
      },
      "correct_answer": "B",
      "explanation": "Ionizing radiation has enough energy to remove electrons from atoms, which can cause cellular damage."
    },
    // ... 19 more questions
  ]
}
```

**Error Responses:**

- `500 Internal Server Error`: Quiz generation failed
  ```json
  {
    "detail": "Expected exactly 20 questions, but got 16"
  }
  ```

### GET `/health`

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "YouTube MCQ Generator API"
}
```

## 🔧 Usage Examples

### Python (requests)

```python
import requests

url = "http://127.0.0.1:8000/generate-quiz"
payload = {
    "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXX"
}

response = requests.post(url, json=payload)
data = response.json()

for i, q in enumerate(data["questions"], 1):
    print(f"Q{i}. {q['question']}")
    for option, text in q['options'].items():
        print(f"  {option}) {text}")
    print(f"✔ Answer: {q['correct_answer']}")
    print(f"ℹ {q['explanation']}\n")
```

### cURL

```bash
curl -X POST "http://127.0.0.1:8000/generate-quiz" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=XXXXXXXX"
  }'
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://127.0.0.1:8000/generate-quiz', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    youtube_url: 'https://www.youtube.com/watch?v=XXXXXXXX'
  })
});

const data = await response.json();
console.log(data.questions);
```

## 🏭 Production Deployment

### Using Uvicorn (Production)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t mcq-generator-api .
docker run -p 8000:8000 mcq-generator-api
```

### Environment Variables

You can configure the API using environment variables:

- `OLLAMA_EXE`: Path to Ollama executable (default: Windows path)
- `OLLAMA_MODEL`: Model for MCQ generation (default: `gemma2:2b`)
- `OLLAMA_ENRICHMENT_MODEL`: Model for enrichment (default: `llama3:8b`)
- `FETCH_ALL_TOPICS`: Agent-03 mode (default: `True`)

## 🔒 Security Considerations

1. **CORS**: Currently allows all origins (`allow_origins=["*"]`). In production, specify exact origins:
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

2. **Rate Limiting**: Consider adding rate limiting for production:
   ```bash
   pip install slowapi
   ```

3. **Authentication**: Add API key authentication if needed:
   ```python
   from fastapi import Depends, HTTPException, Header
   
   API_KEY = "your-secret-key"
   
   def verify_api_key(x_api_key: str = Header(...)):
       if x_api_key != API_KEY:
           raise HTTPException(status_code=403, detail="Invalid API key")
       return x_api_key
   
   @app.post("/generate-quiz")
   def generate_quiz(payload: QuizRequest, api_key: str = Depends(verify_api_key)):
       ...
   ```

## 📊 API Contract (For Backend Team)

### Endpoint
```
POST /generate-quiz
```

### Request Schema
```json
{
  "youtube_url": "string (valid URL)"
}
```

### Response Schema
```json
{
  "questions": [
    {
      "question": "string",
      "options": {
        "A": "string",
        "B": "string",
        "C": "string",
        "D": "string"
      },
      "correct_answer": "A|B|C|D",
      "explanation": "string"
    }
  ]
}
```

### Guarantees
- ✅ Always returns exactly **20 questions**
- ✅ All questions are **unique** (no duplicates)
- ✅ Each question has **4 options** (A, B, C, D)
- ✅ Each question has a **correct_answer** and **explanation**

### Processing Time
- **Typical**: 2-5 minutes (depends on video length and transcript availability)
- **With Whisper**: 5-10 minutes (slower, but works for videos without transcripts)
- **With Agent-03 enrichment**: Additional 1-3 minutes per topic

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Use a different port
uvicorn app.main:app --port 8001
```

### Import Errors

Make sure you're running from the project root:

```bash
cd "C:\Users\Hp\lll\youtube url"
uvicorn app.main:app --reload
```

### Ollama Not Found

Ensure Ollama is installed and the path in `youtube_quiz_generator.py` is correct:

```python
OLLAMA_EXE = r"C:\Users\Hp\AppData\Local\Programs\Ollama\ollama.exe"
```

## 🚀 Next Steps (Optional Enhancements)

- [ ] Add async background tasks for long-running videos
- [ ] Add Redis caching (same URL → reuse result)
- [ ] Add webhook callbacks instead of blocking requests
- [ ] Add `/metrics` endpoint for monitoring
- [ ] Add rate limiting middleware
- [ ] Add API key authentication
- [ ] Add request/response logging
- [ ] Add Docker Compose setup

## 📝 Notes

- The core `youtube_quiz_generator.py` logic remains **unchanged**
- All existing CLI functionality still works
- The API is a **thin wrapper** around the core logic
- Agent-03 web enrichment is **enabled by default**
- Mode can be controlled via `FETCH_ALL_TOPICS` flag in `youtube_quiz_generator.py`



