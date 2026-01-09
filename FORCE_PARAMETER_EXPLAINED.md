# 🔄 Force Parameter - Complete Guide

## 🎯 What is `force`?

The `force` parameter is a **cache bypass flag** that forces the system to regenerate MCQs even if they already exist in the database cache.

---

## 📋 Basic Usage

### Request Format

```json
POST /videos/mcqs
{
  "video_url": "https://example.com/video.mp4",
  "force": true,    ← Add this
  "include_answers": false,
  "randomize": true,
  "limit": 20
}
```

---

## 🔍 How It Works

### Without `force` (Default Behavior)

```
Request → Check Cache → Found? → Return Cached ✅
                      → Not Found? → Generate → Save → Return
```

**Example:**
```json
{
  "video_url": "https://example.com/video.mp4"
  // force not specified (defaults to false)
}
```

**Flow:**
1. Check database for cached MCQs
2. If found → Return cached MCQs immediately
3. If not found → Generate new MCQs → Save → Return

**Result:**
```json
{
  "cached": true,    ← From cache
  "mode": "legacy",  ← Old cached data
  ...
}
```

---

### With `force: true`

```
Request → Ignore Cache → Always Generate → Save → Return
```

**Example:**
```json
{
  "video_url": "https://example.com/video.mp4",
  "force": true      ← Bypass cache
}
```

**Flow:**
1. **Skip cache check completely**
2. Always generate fresh MCQs
3. Save new MCQs (overwrites old cache)
4. Return new MCQs

**Result:**
```json
{
  "cached": false,        ← Freshly generated
  "mode": "exam-grade",   ← New data with current mode
  "time_seconds": 45.23,  ← Generation time
  ...
}
```

---

## 🎯 Use Cases

### 1. **Testing Exam-Grade Mode**

**Problem:** Old legacy MCQs cached, want to test exam-grade mode

**Solution:**
```json
{
  "video_url": "same-url",
  "force": true
}
```

**Why:** Forces regeneration in current mode (exam-grade), ignoring old legacy cache

---

### 2. **Regenerating After Code Changes**

**Problem:** Updated MCQ generation logic, want fresh MCQs

**Solution:**
```json
{
  "video_url": "same-url",
  "force": true
}
```

**Why:** Generates with new logic, overwrites old cache

---

### 3. **Mode Switching**

**Problem:** Switched from legacy to exam-grade mode, want new MCQs

**Solution:**
```json
{
  "video_url": "same-url",
  "force": true
}
```

**Why:** Cache versioning handles this automatically, but `force` guarantees regeneration

---

### 4. **Development/Testing**

**Problem:** Testing different configurations, need fresh data each time

**Solution:**
```json
{
  "video_url": "test-video",
  "force": true
}
```

**Why:** Always generates fresh, no cache interference

---

## ⚖️ Force vs Cache Versioning

### Cache Versioning (Automatic)

**How it works:**
- Checks if cached mode matches current mode
- If mismatch → Auto-regenerates
- If match → Returns cached

**Example:**
- Cached: `mode: "legacy"`
- Current: `USE_ANCHOR_MODE=true` (exam-grade)
- Result: Auto-regenerates (no `force` needed)

---

### Force (Manual Override)

**How it works:**
- Completely bypasses cache
- Always regenerates
- Overwrites existing cache

**Example:**
- Cached: `mode: "exam-grade"`
- Current: `USE_ANCHOR_MODE=true` (exam-grade)
- `force: true` → Still regenerates (even though mode matches)

---

## 📊 Comparison Table

| Scenario | Without `force` | With `force: true` |
|----------|----------------|-------------------|
| **No cache** | Generate new | Generate new |
| **Cache exists (same mode)** | Return cached | **Regenerate** |
| **Cache exists (different mode)** | Auto-regenerate | **Regenerate** |
| **Testing** | May use old cache | **Always fresh** |

---

## 🔍 Code Logic

### In the Endpoint

```python
# Check cache with mode matching (unless force=true)
if request.force:
    row = None  # Force regeneration
    print(f"🔄 Force regeneration requested, bypassing cache")
else:
    row = await db_get_with_mode(session, video_id, required_mode=current_mode)
    # ... cache logic

if row and not request.force:
    # Return cached
    return cached_response

# Generate fresh (either no cache or force=true)
qs = generate_mcqs_from_video_fast(video_url)
# ... save and return
```

---

## ⚠️ Important Notes

### 1. **Performance Impact**

- `force: false` (default): Fast (uses cache)
- `force: true`: Slower (always generates)

**Recommendation:** Only use `force: true` when needed (testing, development)

---

### 2. **Cache Overwrite**

When `force: true`:
- Old cache is **overwritten**
- New cache is saved with current mode
- Previous cached data is lost

---

### 3. **Production Usage**

**Default (Recommended):**
```json
{
  "video_url": "...",
  "force": false  // or omit (defaults to false)
}
```

**Only use `force: true` for:**
- Testing
- Development
- Regenerating after code changes
- Troubleshooting

---

## 🧪 Examples

### Example 1: First Request (No Cache)

**Request:**
```json
{
  "video_url": "https://new-video.mp4",
  "force": false
}
```

**Result:**
- No cache exists
- Generates new MCQs
- Saves to cache
- Returns: `"cached": false`

---

### Example 2: Second Request (Cache Exists)

**Request:**
```json
{
  "video_url": "https://new-video.mp4",
  "force": false
}
```

**Result:**
- Cache exists
- Returns cached MCQs
- Returns: `"cached": true`

---

### Example 3: Force Regeneration

**Request:**
```json
{
  "video_url": "https://new-video.mp4",
  "force": true
}
```

**Result:**
- Ignores cache
- Generates fresh MCQs
- Overwrites cache
- Returns: `"cached": false`

---

## 🎯 Quick Reference

### When to Use `force: true`

✅ Testing exam-grade mode
✅ Regenerating after code changes
✅ Development/testing
✅ Troubleshooting cache issues
✅ Need fresh data every time

### When NOT to Use `force: true`

❌ Production (unless necessary)
❌ Normal API usage
❌ When cache is working fine
❌ Performance-critical scenarios

---

## 📝 Summary

**`force: true` = "Ignore cache, always regenerate"**

- **Default:** `force: false` (use cache when available)
- **With force:** `force: true` (bypass cache, always generate)
- **Use case:** Testing, development, troubleshooting
- **Impact:** Slower but guarantees fresh data

**Think of it as:** "I don't care about cache, give me fresh MCQs every time"



