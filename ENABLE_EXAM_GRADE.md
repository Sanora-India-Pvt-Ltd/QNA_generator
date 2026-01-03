# 🎯 How to Enable Exam-Grade Mode

## ✅ Quick Setup (3 Steps)

### Step 1: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:USE_ANCHOR_MODE="true"
```

**Windows CMD:**
```cmd
set USE_ANCHOR_MODE=true
```

**Linux/Mac:**
```bash
export USE_ANCHOR_MODE=true
```

**Permanent (Windows):**
```powershell
[System.Environment]::SetEnvironmentVariable("USE_ANCHOR_MODE", "true", "User")
```

**Permanent (Linux/Mac):**
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export USE_ANCHOR_MODE=true
```

---

### Step 2: Restart Server

**IMPORTANT:** Server restart is mandatory after setting environment variable.

```bash
# Stop current server (Ctrl+C)
# Then restart:
python api_pg_mcq.py

# Or with uvicorn:
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
```

**Verify on startup:**
You should see:
```
🔧 USE_ANCHOR_MODE = True (EXAM-GRADE)
```

---

### Step 3: Test with Force Regeneration

**Use `force: true` to bypass cache and test exam-grade mode:**

```json
POST /videos/mcqs
{
  "video_url": "https://your-video-url.mp4",
  "force": true,
  "include_answers": true,
  "limit": 20
}
```

**Expected Response:**
```json
{
  "status": "success",
  "mode": "exam-grade",                    ← Should be "exam-grade"
  "anchor_statistics": {                    ← Should be present
    "DEFINITION": 5,
    "PROCESS": 6,
    "RISK": 4
  },
  "questions": [
    {
      "question": "...",
      "anchor_type": "DEFINITION",          ← Each question has anchor_type
      ...
    }
  ]
}
```

---

## 🔍 Verification Checklist

- [ ] Environment variable set: `USE_ANCHOR_MODE=true`
- [ ] Server restarted after setting variable
- [ ] Startup log shows: `USE_ANCHOR_MODE = True (EXAM-GRADE)`
- [ ] Request uses `"force": true` to bypass cache
- [ ] Response shows `"mode": "exam-grade"`
- [ ] Response includes `anchor_statistics`
- [ ] Questions have `anchor_type` field

---

## ⚠️ Common Issues

### Issue 1: Still showing "legacy" mode

**Cause:** Environment variable not set or server not restarted

**Fix:**
1. Check: `echo $USE_ANCHOR_MODE` (should show "true")
2. Restart server
3. Check startup log

---

### Issue 2: Cached data showing "legacy"

**Cause:** Old legacy MCQs in database

**Fix:**
- Use `"force": true` in request
- Or use a new video URL

---

### Issue 3: No anchors detected

**Cause:** Transcript doesn't contain anchor patterns

**Check logs:**
```
🔍 Exam-grade mode: Detecting anchors...
   Found 0 anchors
   ⚠️ No anchors detected, falling back to legacy mode
```

**Fix:**
- Video transcript might not have definition/process/risk patterns
- System will auto-fallback to legacy mode
- This is normal for some videos

---

### Issue 4: anchor_type missing in questions

**Cause:** Generation failed or anchor detection returned empty

**Check:**
- Server logs for warnings
- Verify anchors were detected (check logs)
- Check if `generate_mcqs_ollama_from_anchors()` is working

---

## 🧪 Test Script

```python
import requests
import json

# Test exam-grade mode
response = requests.post(
    "http://localhost:8000/videos/mcqs",
    json={
        "video_url": "https://your-video-url.mp4",
        "force": True,
        "include_answers": True,
        "limit": 5
    }
)

data = response.json()
print(f"Mode: {data.get('mode')}")
print(f"Anchor stats: {data.get('anchor_statistics', {})}")

# Check if questions have anchor_type
if data.get('questions'):
    first_q = data['questions'][0]
    print(f"First question anchor_type: {first_q.get('anchor_type', 'MISSING')}")
```

---

## 📊 Expected Behavior

### Exam-Grade Mode (USE_ANCHOR_MODE=true)

1. **Startup:** Shows `USE_ANCHOR_MODE = True (EXAM-GRADE)`
2. **Generation:** Logs show anchor detection
3. **Response:** 
   - `mode: "exam-grade"`
   - `anchor_statistics` present
   - Questions have `anchor_type`

### Legacy Mode (USE_ANCHOR_MODE=false or not set)

1. **Startup:** Shows `USE_ANCHOR_MODE = False (LEGACY)`
2. **Generation:** Uses random chunks
3. **Response:**
   - `mode: "legacy"`
   - No `anchor_statistics`
   - No `anchor_type` in questions

---

## 🎯 Quick Test

```bash
# 1. Set variable
export USE_ANCHOR_MODE=true

# 2. Restart server
python api_pg_mcq.py

# 3. Test (in another terminal)
curl -X POST http://localhost:8000/videos/mcqs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "force": true,
    "include_answers": true,
    "limit": 5
  }'
```

Look for `"mode": "exam-grade"` in response! ✅


