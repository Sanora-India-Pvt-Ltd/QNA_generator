# 🚀 Quick Start Guide

## ✅ Server Start (Fixed!)

### Method 1: Direct Python (Recommended)

```bash
python api_pg_mcq.py
```

**Expected Output:**
```
🔧 USE_ANCHOR_MODE = True (EXAM-GRADE)
🚀 Loading Whisper model...
✅ Whisper ready!
✅ Database connected and tables ready!

============================================================
🚀 Starting FastAPI Server
============================================================
📡 Server will run at: http://localhost:8000
📚 API Docs: http://localhost:8000/docs
🔧 Mode: EXAM-GRADE
============================================================

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Method 2: With Uvicorn (Alternative)

```bash
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000 --reload
```

**Benefits:**
- `--reload` enables auto-reload on code changes
- Better for development

---

## 🧪 Test Server

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "ready",
  "ollama_available": true,
  "whisper_model": "base",
  "db_configured": true
}
```

---

### 2. API Documentation

Open in browser:
```
http://localhost:8000/docs
```

Interactive Swagger UI with all endpoints!

---

### 3. Test MCQ Generation

**Postman / cURL:**

```bash
curl -X POST http://localhost:8000/videos/mcqs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "force": true,
    "include_answers": true,
    "limit": 5
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "mode": "exam-grade",
  "anchor_statistics": {...},
  "questions": [...]
}
```

---

## ⚙️ Configuration

### Environment Variables

**Windows PowerShell:**
```powershell
$env:USE_ANCHOR_MODE="true"
$env:DATABASE_URL="mysql+aiomysql://user:pass@host:port/db"
```

**Linux/Mac:**
```bash
export USE_ANCHOR_MODE=true
export DATABASE_URL="mysql+aiomysql://user:pass@host:port/db"
```

---

## 🔧 Troubleshooting

### Issue: Server exits immediately

**Fix:** Make sure `uvicorn` is installed:
```bash
pip install uvicorn
```

---

### Issue: Database connection fails

**Check:**
1. `DATABASE_URL` is set correctly
2. MySQL server is running
3. Credentials are correct

---

### Issue: Deprecation warnings

**Status:** ✅ Fixed! Using modern `lifespan` events instead of `on_event`

---

### Issue: Port already in use

**Fix:** Change port:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)
```

Or kill existing process:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

---

## 📋 Quick Checklist

- [ ] `USE_ANCHOR_MODE` set (if using exam-grade mode)
- [ ] `DATABASE_URL` configured
- [ ] MySQL server running
- [ ] Ollama installed and accessible
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] API docs accessible at `/docs`

---

## 🎯 Next Steps

1. **Start Server:**
   ```bash
   python api_pg_mcq.py
   ```

2. **Open API Docs:**
   ```
   http://localhost:8000/docs
   ```

3. **Test Endpoint:**
   - Use Postman or `/docs` interface
   - Send POST to `/videos/mcqs`
   - Check response for `mode: "exam-grade"`

---

## 🎉 Success Indicators

✅ Server runs without errors
✅ No deprecation warnings
✅ Health endpoint works
✅ API docs accessible
✅ MCQ generation works
✅ Response shows correct mode

**Your server is ready!** 🚀



