# ✅ Hybrid Mode Setup - 10 Exam-Grade + 10 Legacy

**Status:** Ready to use  
**Configuration:** Environment variables  
**Goal:** 10 anchor-based exam-grade questions + 10 generic/legacy questions = 20 total

---

## 🚀 Quick Setup

### **Step 1: Set Environment Variables**

**Windows PowerShell:**
```powershell
$env:USE_HYBRID_MODE="true"
$env:EXAM_GRADE_COUNT="10"
$env:LEGACY_COUNT="10"
$env:USE_ANCHOR_MODE="true"
```

**Or in `.env` file:**
```bash
USE_HYBRID_MODE=true
EXAM_GRADE_COUNT=10
LEGACY_COUNT=10
USE_ANCHOR_MODE=true
MCQ_COUNT=20
```

---

### **Step 2: Restart Server**

```bash
uvicorn api_pg_mcq:app --host 0.0.0.0 --port 8000
```

**You should see:**
```
🔄 USE_HYBRID_MODE = True (10 exam-grade + 10 legacy)
```

---

### **Step 3: Make API Request**

```json
POST /videos/mcqs
{
  "video_url": "YOUR_VIDEO_URL"
}
```

---

## 📊 Expected Output

```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": false,
  "time_seconds": 45.23,
  "mode": "hybrid",
  "exam_grade_count": 10,
  "legacy_count": 10,
  "questions": [
    {
      "question": "What is the correct order of steps...",
      "anchor_type": "PROCESS",  // Exam-grade
      "options": {...},
      "correct_answer": "A"
    },
    // ... 9 more exam-grade questions
    {
      "question": "What is MongoDB?",
      "anchor_type": "LEGACY",  // Generic/legacy
      "options": {...},
      "correct_answer": "B"
    }
    // ... 9 more legacy questions
  ],
  "anchor_statistics": {
    "PROCESS": 4,
    "DECISION": 3,
    "DEFINITION": 2,
    "RISK": 1,
    "LEGACY": 10
  }
}
```

---

## ✅ Summary

**Configuration:**
- `USE_HYBRID_MODE=true` - Enable hybrid mode
- `EXAM_GRADE_COUNT=10` - Number of anchor-based questions
- `LEGACY_COUNT=10` - Number of generic/legacy questions

**Result:**
- 10 exam-grade questions (anchor-based)
- 10 legacy questions (generic)
- Total: 20 questions
- Clear mode distinction

**Ready to use! 🚀**



