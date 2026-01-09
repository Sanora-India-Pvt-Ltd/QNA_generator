# ✅ Multi-Question Per Anchor Implementation Plan

**Goal:** Generate 20 exam-grade questions from anchors only (no legacy padding)

**Strategy:** 2 questions per anchor × 10 anchors = 20 questions

---

## 🎯 Implementation Steps

### **1. Add COMPARISON Anchor Type** ✅
- Added to `detect_anchors()` function
- Patterns: vs, versus, compared to, difference between, unlike

### **2. Multi-Question Generation Per Anchor**
- Modify `generate_mcqs_ollama_from_anchors()` to generate 2 questions per anchor
- Calculate `target_per_anchor = min(2, MCQ_COUNT / len(anchors))`
- Loop through anchors, generate 2 questions each

### **3. Question Variants Per Anchor Type**
- Update `mcq_prompt_from_anchor()` to accept `variant` parameter
- Different question templates per anchor type:
  - DEFINITION: variant 0 = paraphrase, variant 1 = negative
  - PROCESS: variant 0 = order, variant 1 = missing step
  - DECISION: variant 0 = best choice, variant 1 = scenario
  - BOUNDARY: variant 0 = exception, variant 1 = condition
  - RISK: variant 0 = mistake, variant 1 = consequence
  - COMPARISON: variant 0 = difference, variant 1 = use case

### **4. Fix PROCESS Question Format**
- Reject questions with embedded options (A) B) C) D))
- Require standalone options without nested labels
- Ordering must be inferred, not embedded

---

## 📊 Expected Results

**For 10-15 min video:**
- Anchors detected: 10-14
- Questions per anchor: 2
- Total questions: 20-28
- Returned: 20 (top quality)

**For short video:**
- Anchors detected: 5-8
- Questions per anchor: 2
- Total questions: 10-16
- Returned: 10-16 (honest count)

---

## ✅ Next Steps

1. Implement multi-question loop in `generate_mcqs_ollama_from_anchors()`
2. Add variant parameter to `mcq_prompt_from_anchor()`
3. Create question templates per anchor type
4. Fix PROCESS question validation



