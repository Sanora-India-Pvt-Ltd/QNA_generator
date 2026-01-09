# 🔧 Fixing 524 Timeout Error (Cloudflare)

## ❌ Problem

**Error 524: A timeout occurred**

**When:** Using `force: true` to regenerate MCQs

**Cause:** MCQ generation takes longer than Cloudflare's timeout (usually 100 seconds)

---

## 🧠 Why This Happens

### Normal Flow (With Cache):
```
Request → Check Cache → Return (fast, <1 second) ✅
```

### Force Flow (No Cache):
```
Request → Generate MCQs → Takes 60-120+ seconds → Cloudflare timeout ❌
```

**Generation Steps:**
1. Video transcription (Whisper) - 30-60s
2. Anchor detection - 1-2s
3. LLM MCQ generation (Ollama) - 30-60s per question
4. Total: 60-120+ seconds

**Cloudflare Default Timeout:** 100 seconds

---

## ✅ Solutions

### Solution 1: Increase Cloudflare Timeout (Recommended for Production)

**If you have Cloudflare Enterprise:**
1. Go to Cloudflare Dashboard
2. Rules → Cache Rules
3. Create rule for `/videos/mcqs` endpoint
4. Set timeout to 300 seconds (5 minutes)

**Or use Page Rules:**
- Pattern: `api.drishtifilmproductions.com/videos/mcqs`
- Setting: Cache Level → Bypass
- Edge Cache TTL → Respect Existing Headers

---

### Solution 2: Optimize Generation Time

**Quick Wins:**

1. **Reduce MCQ Count:**
   ```python
   MCQ_COUNT = 10  # Instead of 20
   ```

2. **Reduce Sample Clips:**
   ```python
   SAMPLE_CLIPS = 4  # Instead of 8
   ```

3. **Faster Whisper Model:**
   ```python
   WHISPER_MODEL_SIZE = "tiny"  # Instead of "base"
   ```

4. **Parallel Processing:**
   - Process multiple anchors in parallel
   - Use async LLM calls

---

### Solution 3: Async Background Processing (Best for Production)

**Pattern:**
1. Request returns immediately with `status: "processing"`
2. Background task generates MCQs
3. Client polls for status
4. When ready, fetch MCQs

**Implementation:**
- Use FastAPI BackgroundTasks
- Or use Celery/Redis for queue
- Store status in database

---

### Solution 4: Quick Response Pattern (Immediate Fix)

**Return immediately, process in background:**

```python
@app.post("/videos/mcqs")
async def get_mcqs(request: MCQRequest, background_tasks: BackgroundTasks):
    # Check cache first
    if row and not request.force:
        return cached_response
    
    # If force=true and will take long, return quick response
    if request.force:
        # Start background task
        background_tasks.add_task(generate_and_save_async, video_id, video_url)
        
        return {
            "status": "processing",
            "video_id": video_id,
            "message": "MCQs are being generated. Please check back in 60-90 seconds.",
            "check_endpoint": f"/videos/{video_id}/mcqs"
        }
```

---

## 🚀 Quick Fix (Immediate)

### Option A: Increase Timeout in Code

Add timeout handling:

```python
import asyncio
from fastapi import HTTPException

@app.post("/videos/mcqs")
async def get_mcqs(request: MCQRequest):
    # ... existing code ...
    
    if request.force:
        try:
            # Set timeout for generation
            qs = await asyncio.wait_for(
                asyncio.to_thread(generate_mcqs_from_video_fast, video_url),
                timeout=90.0  # 90 seconds max
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Generation timeout. Please try again or use cached version (force=false)."
            )
```

---

### Option B: Return Early for Force Requests

```python
@app.post("/videos/mcqs")
async def get_mcqs(request: MCQRequest):
    # ... check cache ...
    
    if request.force:
        # Return immediately, suggest polling
        return {
            "status": "processing",
            "video_id": video_id,
            "message": "Generation started. This may take 60-90 seconds.",
            "poll_endpoint": f"/videos/{video_id}/status",
            "suggestion": "Use force=false to get cached version, or poll status endpoint"
        }
```

---

## 🎯 Recommended Approach

### For Development/Testing:

1. **Use cached version** (don't use `force: true` unless necessary)
2. **Test locally** first (bypass Cloudflare)
3. **Use shorter videos** for testing

### For Production:

1. **Implement async processing** with status polling
2. **Increase Cloudflare timeout** (if Enterprise)
3. **Optimize generation** (reduce clips, faster models)
4. **Use background tasks** for long operations

---

## 🔍 Immediate Workaround

### Don't Use `force: true` Through Cloudflare

**Instead:**

1. **Access server directly** (bypass Cloudflare):
   ```
   http://your-server-ip:8000/videos/mcqs
   ```

2. **Or use cached version:**
   ```json
   {
     "video_url": "...",
     "force": false  // Use cache
   }
   ```

3. **Or generate once, then fetch:**
   ```bash
   # Step 1: Generate (direct access, no Cloudflare)
   POST http://server-ip:8000/generate-and-save
   
   # Step 2: Fetch (through Cloudflare, fast)
   POST http://api.drishtifilmproductions.com/videos/mcqs
   ```

---

## 📋 Quick Checklist

- [ ] Check if generation is actually needed (use cache if possible)
- [ ] Test locally first (bypass Cloudflare)
- [ ] Optimize generation time (reduce clips, faster models)
- [ ] Consider async processing for production
- [ ] Increase Cloudflare timeout (if Enterprise)
- [ ] Use direct server access for force operations

---

## 🎯 Best Practice

**For `force: true` requests:**

1. **Don't use through Cloudflare** - Access server directly
2. **Or implement async pattern** - Return immediately, process in background
3. **Or optimize generation** - Make it faster

**For normal requests:**

- Use `force: false` (default)
- Fast cache retrieval
- Works through Cloudflare ✅

---

## 💡 Summary

**524 Error = Generation takes too long**

**Solutions:**
1. ✅ Don't use `force: true` through Cloudflare
2. ✅ Access server directly for force operations
3. ✅ Use cached version when possible
4. ✅ Implement async processing (long-term)
5. ✅ Optimize generation time

**Quick Fix:** Use `force: false` or access server directly!



