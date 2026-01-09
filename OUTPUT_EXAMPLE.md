# API Output Format Examples

## 📤 POST /videos/mcqs Response

### ✅ Success Response (Exam-Grade Mode)

```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": false,
  "time_seconds": 45.23,
  "mode": "exam-grade",
  "anchor_statistics": {
    "DEFINITION": 5,
    "PROCESS": 6,
    "RISK": 4,
    "BOUNDARY": 3,
    "DECISION": 2
  },
  "anchor_types_used": [
    "DEFINITION",
    "PROCESS",
    "RISK",
    "BOUNDARY",
    "DECISION"
  ],
  "questions": [
    {
      "question": "What is the definition of machine learning?",
      "options": {
        "A": "A type of database system",
        "B": "A method where computers learn from data without explicit programming",
        "C": "A programming language",
        "D": "A hardware component"
      },
      "correct_answer": "B",
      "anchor_type": "DEFINITION"
    },
    {
      "question": "What is the correct sequence of steps in the training process?",
      "options": {
        "A": "Test, Train, Validate",
        "B": "Train, Validate, Test",
        "C": "Validate, Train, Test",
        "D": "Test, Validate, Train"
      },
      "correct_answer": "B",
      "anchor_type": "PROCESS"
    }
    // ... more questions
  ]
}
```

### ✅ Success Response (Cached - Exam-Grade Mode)

```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": true,
  "mode": "exam-grade",
  "anchor_statistics": {
    "DEFINITION": 5,
    "PROCESS": 6,
    "RISK": 4,
    "BOUNDARY": 3,
    "DECISION": 2
  },
  "anchor_types_used": [
    "DEFINITION",
    "PROCESS",
    "RISK",
    "BOUNDARY",
    "DECISION"
  ],
  "questions": [
    // ... questions (same format as above)
  ]
}
```

### ✅ Success Response (Legacy Mode)

```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": false,
  "time_seconds": 42.15,
  "mode": "legacy",
  "questions": [
    {
      "question": "What is machine learning?",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }
      // Note: No anchor_type in legacy mode
    }
    // ... more questions
  ]
}
```

### ✅ Success Response (Without Answers - Anti-Cheat)

```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": false,
  "time_seconds": 45.23,
  "mode": "exam-grade",
  "anchor_statistics": {
    "DEFINITION": 5,
    "PROCESS": 6
  },
  "questions": [
    {
      "question": "What is the definition of machine learning?",
      "options": {
        "A": "A type of database system",
        "B": "A method where computers learn from data",
        "C": "A programming language",
        "D": "A hardware component"
      }
      // Note: correct_answer removed (anti-cheat)
      // Note: anchor_type may also be removed for security
    }
  ]
}
```

---

## 📊 Response Fields Explained

### Main Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "success" for successful requests |
| `video_id` | string | 16-character hash identifier for the video |
| `count` | integer | Number of questions returned |
| `cached` | boolean | `true` if from cache, `false` if newly generated |
| `time_seconds` | float | Time taken to generate (only if `cached=false`) |
| `mode` | string | "exam-grade" or "legacy" |
| `questions` | array | List of MCQ objects |

### Exam-Grade Mode Fields

| Field | Type | Description |
|-------|------|-------------|
| `anchor_statistics` | object | Count of questions by anchor type |
| `anchor_types_used` | array | List of anchor types found in questions |

### Question Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | The question text |
| `options` | object | Options A, B, C, D |
| `correct_answer` | string | "A", "B", "C", or "D" (only if `include_answers=true`) |
| `anchor_type` | string | Anchor type: DEFINITION, PROCESS, RISK, BOUNDARY, DECISION (only in exam-grade mode) |

---

## 🔍 Anchor Types Explained

### DEFINITION
Questions that ask to identify or paraphrase definitions.
- Example: "What is X defined as?"
- Pedagogy: Paraphrase type

### PROCESS
Questions about sequences, steps, or procedures.
- Example: "What is the correct order of steps?"
- Pedagogy: Ordering type

### RISK
Questions about consequences or what happens if risks occur.
- Example: "What happens if X risk occurs?"
- Pedagogy: Consequence type

### BOUNDARY
Questions about what does NOT apply or is excluded.
- Example: "Which of the following does NOT apply?"
- Pedagogy: Exclusion type

### DECISION
Scenario-based questions asking what should be done.
- Example: "In scenario X, what should you do?"
- Pedagogy: Scenario type

---

## 📝 Example Usage in Postman

### Request
```
POST http://localhost:8000/videos/mcqs
Content-Type: application/json

{
  "video_url": "https://example.com/video.mp4",
  "include_answers": false,
  "randomize": true,
  "limit": 20
}
```

### Response (Exam-Grade Mode)
- Shows `mode: "exam-grade"`
- Includes `anchor_statistics` showing distribution
- Each question has `anchor_type` field
- Questions are answerable from 24-second context windows

### Response (Legacy Mode)
- Shows `mode: "legacy"`
- No anchor information
- Questions from random important chunks

---

## 🎯 Key Differences: Exam-Grade vs Legacy

| Feature | Exam-Grade Mode | Legacy Mode |
|---------|----------------|-------------|
| **Anchor Detection** | ✅ Rules-based | ❌ None |
| **Question Type Control** | ✅ Pedagogy engine | ❌ LLM decides |
| **Context Windows** | ✅ 24-second equivalent | ❌ Random chunks |
| **LLM Role** | Writer only | Decision maker |
| **Anchor Statistics** | ✅ Included | ❌ Not included |
| **Regulator-Safe** | ✅ Yes | ⚠️ Limited |

---

## ⚙️ Configuration

Set in environment or code:
```bash
USE_ANCHOR_MODE=true   # Exam-grade mode (default)
USE_ANCHOR_MODE=false  # Legacy mode
```



