# ✅ Cache Count Invalidation Fix - Always 20 Questions

**Status:** Implemented - Automatic cache invalidation when count < MCQ_COUNT  
**Date:** 2024  
**Problem:** Cached data with < 20 questions preventing fill logic from running

---

## 🎯 Problem Identified

### **Root Cause:**
- Old cache had only 3 questions
- Cache was being hit (mode matched)
- New fill logic never executed
- System returned 3 questions instead of 20

### **Evidence:**
```json
"cached": true  // ← Cache hit prevented fill logic
"count": 3      // ← Insufficient count
```

---

## ✅ Solution Implemented

### **1. Automatic Cache Invalidation in `db_get_with_mode()`**

**Location:** `api_pg_mcq.py` lines 1732-1736

**Logic:**
```python
# CRITICAL: Check if cached question count is sufficient
cached_questions = (row.questions or {}).get("questions", [])
if isinstance(cached_questions, list) and len(cached_questions) < MCQ_COUNT:
    print(f"   ⚠️ Cache invalidated: insufficient question count (cached: {len(cached_questions)}, required: {MCQ_COUNT})")
    return None  # Force regeneration to trigger hybrid fill pipeline
```

**Result:**
- Cache with < 20 questions → Automatically invalidated
- Forces regeneration → Triggers hybrid fill pipeline
- Always returns 20 questions

---

### **2. Cache Invalidation in `/videos/mcqs` Endpoint**

**Location:** `api_pg_mcq.py` lines 1902-1908

**Logic:**
```python
if row and not request.force:
    qs = (row.questions or {}).get("questions", [])
    if len(qs) < MCQ_COUNT:
        print(f"   ⚠️ Cached MCQs ({len(qs)}) less than required count ({MCQ_COUNT}). Forcing regeneration.")
        row = None  # Force regeneration to trigger hybrid fill pipeline
```

**Result:**
- Endpoint-level check ensures cache is invalidated
- Fallback if `db_get_with_mode()` check is bypassed

---

### **3. Cache Invalidation in `/generate-and-save` Endpoint**

**Location:** `api_pg_mcq.py` lines 1756-1769

**Logic:**
```python
if existing and not req.force:
    qs = (existing.questions or {}).get("questions", [])
    if isinstance(qs, list) and len(qs) < MCQ_COUNT:
        print(f"   ⚠️ Cached MCQs ({len(qs)}) less than required count ({MCQ_COUNT}). Forcing regeneration.")
        existing = None  # Force regeneration
```

**Result:**
- Consistent behavior across all endpoints
- No stale cache with insufficient questions

---

## 🔄 How It Works Now

### **Scenario 1: Old Cache (3 Questions)**

```
Request → Cache found → Count check → 3 < 20 → INVALIDATE → Regenerate → Fill to 20
```

**Result:**
- Cache automatically invalidated
- Hybrid fill pipeline triggered
- Returns 20 questions

---

### **Scenario 2: New Cache (20 Questions)**

```
Request → Cache found → Count check → 20 >= 20 → VALID → Return cached
```

**Result:**
- Cache served normally (fast)
- No regeneration needed

---

### **Scenario 3: Force Regeneration**

```
Request (force=true) → Bypass cache → Regenerate → Fill to 20 → Save
```

**Result:**
- Always regenerates
- New cache stored with 20 questions

---

## 📊 Expected Behavior

### **Before Fix:**
```json
{
  "cached": true,
  "count": 3,  // ❌ Insufficient
  "questions": [...]  // Only 3 questions
}
```

### **After Fix:**
```json
{
  "cached": false,  // ✅ Regenerated
  "count": 20,     // ✅ Full count
  "anchor_statistics": {
    "PROCESS": 1,
    "DECISION": 2,
    "LEGACY": 17    // ✅ Fill questions added
  }
}
```

---

## 🧪 Verification Steps

### **Step 1: Check Logs**

You should see:
```
⚠️ Cached MCQs (3) less than required count (20). Forcing regeneration.
⚠️ Only 3 exam-grade MCQs generated. Filling remaining using legacy mode.
✅ Total: 20 MCQs (3 exam-grade + 17 legacy fill)
```

### **Step 2: Check Response**

Response should include:
- `"cached": false` (regenerated)
- `"count": 20` (full count)
- `"anchor_statistics"` with `"LEGACY"` entries

---

## ✅ Benefits

### **Automatic:**
- ✅ No manual DB cleanup needed
- ✅ No `force=true` required
- ✅ Seamless user experience

### **Production-Ready:**
- ✅ Handles edge cases automatically
- ✅ Consistent behavior across endpoints
- ✅ No stale cache issues

### **User Experience:**
- ✅ Always returns 20 questions
- ✅ No incomplete quizzes
- ✅ Transparent regeneration

---

## 🔧 Configuration

### **Environment Variables:**

```bash
MCQ_COUNT=20              # Target question count
ALLOW_LEGACY_FILL=true     # Enable hybrid fill pipeline
```

### **Behavior:**

| Cached Count | Action |
|--------------|--------|
| < 20 | Auto-invalidate → Regenerate → Fill |
| = 20 | Return cached |
| > 20 | Return cached (first 20) |

---

## ✅ Summary

**Problem:** Cache with < 20 questions preventing fill logic from running

**Solution:**
1. ✅ **Automatic cache invalidation** when count < MCQ_COUNT
2. ✅ **Multi-level checks** (db_get_with_mode + endpoints)
3. ✅ **Hybrid fill pipeline** triggered automatically

**Result:**
- Always returns 20 questions
- No manual intervention needed
- Production-ready behavior

---

**System Status:**
- ✅ Cache invalidation: Automatic
- ✅ Fill pipeline: Triggered automatically
- ✅ Always 20 questions: Guaranteed

**Ready for production! 🚀**


