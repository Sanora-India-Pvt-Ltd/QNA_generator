# 🔄 Force Regeneration Guide - Fix Stale Cache

**Status:** Ready to use  
**Problem:** Cached MCQs generated before validation fixes showing quality issues  
**Solution:** Force regeneration with `force: true` parameter

---

## 🎯 Quick Fix (2 Steps)

### **Step 1: Force Regenerate**

**API Call:**
```json
POST /videos/mcqs
{
  "video_url": "YOUR_VIDEO_URL_HERE",
  "force": true
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/videos/mcqs \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://youtube.com/watch?v=abc123",
    "force": true
  }'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://localhost:8000/videos/mcqs",
    json={
        "video_url": "https://youtube.com/watch?v=abc123",
        "force": True
    }
)

data = response.json()
print(f"Generated {data['count']} questions in {data.get('time_seconds', 0)}s")
```

---

### **Step 2: Verify Output**

After regeneration, check the response:

✅ **Should See:**
- `"cached": false` (newly generated)
- `"mode": "exam-grade"`
- Questions with proper anchor alignment
- No nested option labels
- No incomplete stems

❌ **Should NOT See:**
- `"cached": true` (if you used `force: true`)
- PROCESS anchor → DEFINITION questions
- Options with "A.", "B.", "C.", "D." inside
- Questions ending with "will not be..."

---

## 🔍 What Happens During Force Regeneration

### **Process:**

1. **Request received** with `force: true`
2. **Cache bypassed** (even if exists)
3. **New generation** with current validation rules:
   - Strict PROCESS anchor validation
   - Incomplete stem rejection
   - Nested label rejection
   - Semantic deduplication
4. **New cache saved** with `validation_rule_version: "2.0"`
5. **Response returned** with fresh questions

### **Time:**
- First generation: 30-60 seconds
- Subsequent requests: Instant (from new cache)

---

## 📊 Before vs After

### **Before (Stale Cache):**

```json
{
  "cached": true,
  "mode": "exam-grade",
  "questions": [
    {
      "question": "What is the document oriented database...",
      "anchor_type": "PROCESS",  // ❌ WRONG
      "options": {
        "A": "B. Create account -> C. Use website"  // ❌ NESTED LABELS
      }
    },
    {
      "question": "then your performance will not be...",  // ❌ INCOMPLETE
      "anchor_type": "PROCESS"
    }
  ]
}
```

### **After (Force Regenerated):**

```json
{
  "cached": false,
  "mode": "exam-grade",
  "time_seconds": 45.23,
  "questions": [
    {
      "question": "What is the correct order of steps to create an account?",
      "anchor_type": "PROCESS",  // ✅ CORRECT
      "options": {
        "A": "Create an account on Reddit"  // ✅ CLEAN
      }
    },
    {
      "question": "What happens when you use MongoDB or Redis?",  // ✅ COMPLETE
      "anchor_type": "DECISION"
    }
  ]
}
```

---

## 🔄 Automatic Cache Invalidation (Future)

**Already Implemented:**

The system now includes `VALIDATION_RULE_VERSION = "2.0"` which:

- **Stores version** in each cached record
- **Checks version** on cache lookup
- **Invalidates automatically** if version mismatch

**Result:**
- Old cache (version 1.0) → Automatically regenerated
- New cache (version 2.0) → Served normally
- Future rule changes → Automatic invalidation

**No manual cleanup needed** for future rule changes!

---

## 🎯 When to Use Force Regeneration

### **Use `force: true` when:**

1. ✅ **Validation rules changed** (current situation)
2. ✅ **Model upgraded** (qwen2.5:1.5b → qwen2.5:3b)
3. ✅ **Testing new configurations**
4. ✅ **Quality issues reported** (regenerate to apply fixes)

### **Don't use `force: true` when:**

1. ❌ **Normal operation** (let cache work)
2. ❌ **High traffic** (wastes resources)
3. ❌ **Same video, multiple users** (cache is efficient)

---

## 📝 Batch Regeneration (Optional)

If you need to regenerate multiple videos:

```python
import requests

video_urls = [
    "https://youtube.com/watch?v=abc123",
    "https://youtube.com/watch?v=def456",
    "https://youtube.com/watch?v=ghi789",
]

for url in video_urls:
    response = requests.post(
        "http://localhost:8000/videos/mcqs",
        json={"video_url": url, "force": True}
    )
    data = response.json()
    print(f"{url}: {data['count']} questions in {data.get('time_seconds', 0)}s")
```

---

## ✅ Summary

**Problem:** Stale cache showing quality issues from before validation fixes

**Solution:**
1. ✅ Use `force: true` to regenerate existing videos
2. ✅ Automatic cache invalidation for future rule changes
3. ✅ New cache stored with validation version

**Result:**
- All quality issues fixed
- Future-proof cache invalidation
- No manual cleanup needed

---

**Ready to regenerate! Use `force: true` to update existing videos. 🚀**


