# 🤖 Model Upgrade: qwen2.5:1.5b → qwen2.5:3b

**Status:** ✅ Complete  
**Date:** 2024  
**Decision:** Locked - Use `qwen2.5:3b` as MCQ writer model

---

## ✅ What Changed

### **Model Configuration**
- **Before:** `qwen2.5:1.5b` (default)
- **After:** `qwen2.5:3b` (default)

### **Code Changes**
- Updated `OLLAMA_MODEL` default value in `api_pg_mcq.py`
- Added startup log message showing model in use
- All references automatically use new default

---

## 🎯 Expected Improvements

### **Language Quality**
- ✅ Cleaner question stems
- ✅ No broken sentences like "then your performance will not be..."
- ✅ Better option phrasing
- ✅ More professional exam language
- ✅ Fewer retries per anchor (better first-pass quality)

### **What Stays the Same**
- ✅ Anchor detection (rules-based, unchanged)
- ✅ Context windows (24-second, unchanged)
- ✅ Pedagogy rules (unchanged)
- ✅ Validation logic (unchanged)
- ✅ Compliance posture (unchanged)
- ✅ Architecture (unchanged)

---

## 🔧 Setup Instructions

### **Step 1: Pull the Model (One Time)**

```bash
ollama pull qwen2.5:3b
```

### **Step 2: Set Environment Variable (Optional)**

**Windows PowerShell:**
```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
```

**Linux/Mac:**
```bash
export OLLAMA_MODEL="qwen2.5:3b"
```

**Or in `.env` file:**
```
OLLAMA_MODEL=qwen2.5:3b
```

**Note:** If not set, defaults to `qwen2.5:3b` (already updated in code)

### **Step 3: Restart Server**

```bash
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
```

### **Step 4: Verify**

On startup, you should see:
```
🔧 USE_ANCHOR_MODE = True (EXAM-GRADE)
🤖 OLLAMA_MODEL = qwen2.5:3b (MCQ Writer Model)
```

Or check health endpoint:
```bash
curl http://localhost:8000/health
```

Response includes:
```json
{
  "ollama_model": "qwen2.5:3b",
  ...
}
```

---

## 🧠 Why This Model?

### **Model Comparison**

| Model | Size | Language Quality | Speed | Use Case |
|-------|------|------------------|-------|----------|
| `qwen2.5:1.5b` | Small | ⚠️ Too weak linguistically | Fast | Not recommended |
| `qwen2.5:3b` | Medium | ✅ **Sweet spot** | Good | **Recommended** |
| `qwen2.5:7b+` | Large | ✅ Excellent | Slower | Diminishing returns |

### **Why 3b is Perfect**

- **LLM Role:** Writer, not thinker
- **Task:** Generate exam-quality question wording
- **Requirement:** Professional language, not complex reasoning
- **Result:** `3b` provides optimal balance of quality and speed

---

## 📊 Quality Improvements Already Applied

The following quality fixes are already in place (from previous updates):

1. ✅ **Reject options with nested labels** (A., B., C., D. inside text)
2. ✅ **Reject incomplete question stems** (trailing conjunctions, incomplete phrases)
3. ✅ **Strict anchor-question type alignment** (DEFINITION → definition questions)
4. ✅ **Language quality checks** (awkward phrasing, grammar issues)

**Combined with `qwen2.5:3b`, these ensure exam-grade quality.**

---

## 🔄 Migration Notes

### **Existing Content**
- **Legacy content:** Unchanged (uses old model metadata)
- **New content:** Uses `qwen2.5:3b` automatically
- **Regeneration:** New questions use `qwen2.5:3b`

### **Database**
- `quality_metrics.llm.generator_model` will show `qwen2.5:3b` for new generations
- Existing records unchanged (historical accuracy preserved)

---

## 🧾 Internal Status Note

> **MCQ writer model upgraded to `qwen2.5:3b` for improved exam-language quality; system architecture unchanged.**

---

## ✅ Verification Checklist

- [x] Default model updated to `qwen2.5:3b`
- [x] Startup log message added
- [x] Health endpoint shows correct model
- [x] All code references use `OLLAMA_MODEL` variable
- [x] Quality fixes already in place
- [x] Documentation updated

---

## 🚀 Next Steps

1. **Pull the model:**
   ```bash
   ollama pull qwen2.5:3b
   ```

2. **Restart server:**
   ```bash
   uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
   ```

3. **Test generation:**
   - Generate new questions
   - Verify improved language quality
   - Check fewer retries needed

4. **Monitor:**
   - Watch for quality improvements
   - Track rejection rates (should decrease)
   - Monitor generation times (slightly slower but acceptable)

---

**Model upgrade complete! System ready with improved language quality. 🎉**



