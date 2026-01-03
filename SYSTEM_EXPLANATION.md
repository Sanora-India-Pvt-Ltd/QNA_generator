# 🎓 Complete System Explanation: Video MCQ Generator

**What It Does | How It Works | Integration Guide**

---

## 📋 What This System Does

This is an **Exam-Grade MCQ (Multiple Choice Question) Generator** that:

1. **Takes a video URL** as input
2. **Automatically generates 20 exam-quality questions** from the video content
3. **Stores questions in database** for instant retrieval
4. **Returns questions** ready for your app/web to display

### Key Features

✅ **Smart Question Generation** - Finds important learning points automatically  
✅ **Exam-Grade Quality** - Questions are regulator-safe and audit-ready  
✅ **Fast Caching** - Generate once, fetch instantly forever  
✅ **Anti-Cheat** - Answers hidden by default  
✅ **Context-Aware** - Questions test video comprehension, not general knowledge  

---

## 🔄 How The System Works (Step-by-Step)

### **Main Flow: Video → Questions**

```
Video URL → Transcript → Anchors → Questions → Database → Your App
```

### **Detailed Process:**

#### **Step 1: Video Input**
- User/app sends video URL to API
- Example: `https://youtube.com/watch?v=abc123`

#### **Step 2: Transcript Generation**
- System samples 8 clips from video (12 seconds each)
- Uses **Whisper AI** to transcribe audio to text
- Creates full transcript of video content

#### **Step 3: Anchor Detection (Exam-Grade Mode)**
- **Rules-based detection** (NO AI) finds important points:
  - **DEFINITION** - "X is defined as..."
  - **PROCESS** - "Step 1, Step 2, then..."
  - **RISK** - "Warning: don't do X..."
  - **BOUNDARY** - "X applies except when..."
  - **DECISION** - "If X happens, you should..."

#### **Step 4: Question Generation**
- For each anchor, system:
  1. Builds 24-second context window around anchor
  2. Determines question type (paraphrase, ordering, scenario, etc.)
  3. Sends to **LLM** (Ollama) to write question wording
  4. Validates question quality (context-dependent, no vague references)
  5. Rejects bad questions and retries

#### **Step 5: Storage & Caching**
- Questions saved to MySQL database
- Includes complete metadata:
  - Anchor types used
  - Generation timestamp
  - Quality metrics
  - Evidence hash (tamper-proof)
- **video_id** = SHA1 hash of URL (deterministic)

#### **Step 6: Response**
- Returns questions in JSON format
- Includes metadata (anchor statistics, mode, etc.)
- **No answers by default** (anti-cheat)

---

## 🎯 What Your App/Web Will Do After Integration

### **User Experience Flow:**

```
1. User uploads/watches video
   ↓
2. App sends video URL to API
   ↓
3. API generates questions (or returns cached)
   ↓
4. App displays questions to user
   ↓
5. User answers questions
   ↓
6. App checks answers (if you have them)
   ↓
7. App shows results/feedback
```

---

## 📱 App/Web Integration Examples

### **Scenario 1: New Video (First Time)**

**App Action:**
```javascript
// User just uploaded a video
const videoUrl = "https://youtube.com/watch?v=abc123";

// Call API
const response = await fetch('http://your-api:8000/videos/mcqs', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    video_url: videoUrl,
    include_answers: false,  // Anti-cheat
    randomize: true,
    limit: 20
  })
});

const data = await response.json();
// data.cached = false (new generation)
// data.time_seconds = 45.23 (took 45 seconds)
// data.questions = [20 questions]
```

**What Happens:**
- API generates questions (takes 30-60 seconds)
- Questions saved to database
- App receives questions immediately

**User Sees:**
- Loading spinner: "Generating questions..."
- After 30-60 seconds: Questions appear

---

### **Scenario 2: Cached Video (Already Generated)**

**App Action:**
```javascript
// Same video URL
const response = await fetch('http://your-api:8000/videos/mcqs', {
  method: 'POST',
  body: JSON.stringify({
    video_url: videoUrl,
    include_answers: false,
    randomize: true,
    limit: 20
  })
});

const data = await response.json();
// data.cached = true (from cache!)
// data.questions = [20 questions] (instant)
```

**What Happens:**
- API checks database
- Finds existing questions
- Returns instantly (< 1 second)

**User Sees:**
- Questions appear **instantly** (no waiting!)

---

### **Scenario 3: Exam Mode Display**

**App Action:**
```javascript
const data = await response.json();

if (data.mode === "exam-grade") {
  // Show anchor statistics
  console.log("Anchor types:", data.anchor_types_used);
  // ["DEFINITION", "PROCESS", "RISK", "BOUNDARY", "DECISION"]
  
  // Show question with anchor type
  data.questions.forEach(q => {
    console.log(q.question);
    console.log("Type:", q.anchor_type);  // "DEFINITION", "PROCESS", etc.
    console.log("Options:", q.options);
  });
}
```

**What User Sees:**
- Questions organized by type
- Can show: "5 Definition questions, 6 Process questions..."
- Better learning experience

---

## 🎨 UI/UX Recommendations

### **Question Display**

```html
<!-- Example HTML structure -->
<div class="question-card">
  <div class="question-header">
    <span class="anchor-badge">DEFINITION</span>
    <span class="question-number">1 / 20</span>
  </div>
  
  <h3>What is the definition of machine learning?</h3>
  
  <div class="options">
    <button class="option">A) A type of database system</button>
    <button class="option">B) A method where computers learn from data</button>
    <button class="option">C) A programming language</button>
    <button class="option">D) A hardware component</button>
  </div>
  
  <button class="submit-answer">Submit Answer</button>
</div>
```

### **Loading States**

```javascript
// Show different messages based on cache status
if (data.cached) {
  showMessage("Questions loaded instantly! ✨");
} else {
  showMessage(`Generated ${data.count} questions in ${data.time_seconds}s`);
}
```

### **Anchor Type Badges**

```css
.anchor-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.anchor-badge.DEFINITION { background: #e3f2fd; }
.anchor-badge.PROCESS { background: #f3e5f5; }
.anchor-badge.RISK { background: #ffebee; }
.anchor-badge.BOUNDARY { background: #fff3e0; }
.anchor-badge.DECISION { background: #e8f5e9; }
```

---

## 🔌 API Endpoints Your App Will Use

### **Primary Endpoint (Recommended)**

```
POST /videos/mcqs
```

**Request:**
```json
{
  "video_url": "https://youtube.com/watch?v=abc123",
  "include_answers": false,
  "randomize": true,
  "limit": 20,
  "force": false
}
```

**Response:**
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
  "questions": [
    {
      "question": "What is the definition of...",
      "options": {
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      },
      "anchor_type": "DEFINITION"
    }
  ]
}
```

### **Alternative Endpoints**

1. **POST /generate-and-save** - Generate and save (returns video_id)
2. **GET /videos/{video_id}/mcqs** - Fetch by video_id (if you store it)

---

## 🎯 Key Features Your App Can Leverage

### **1. Anti-Cheat Protection**
- `include_answers: false` by default
- Answers never sent to frontend
- Your backend can verify answers separately

### **2. Randomization**
- `randomize: true` shuffles questions
- Different order each time
- Prevents memorization

### **3. Limit Control**
- `limit: 20` controls how many questions
- Can request 5, 10, 20, or up to 50
- Useful for quizzes vs full exams

### **4. Anchor Statistics**
- Know which types of questions were generated
- Can show: "5 Definition, 6 Process questions"
- Better learning analytics

### **5. Mode Detection**
- `mode: "exam-grade"` or `"legacy"`
- Can show badge: "Exam-Grade Questions"
- Different UI for different modes

---

## 🔄 Complete Integration Example

### **React/Next.js Example**

```javascript
import { useState, useEffect } from 'react';

function VideoQuiz({ videoUrl }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cached, setCached] = useState(false);
  
  useEffect(() => {
    async function fetchQuestions() {
      try {
        const response = await fetch('http://your-api:8000/videos/mcqs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            video_url: videoUrl,
            include_answers: false,
            randomize: true,
            limit: 20
          })
        });
        
        const data = await response.json();
        setQuestions(data.questions);
        setCached(data.cached);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching questions:', error);
        setLoading(false);
      }
    }
    
    fetchQuestions();
  }, [videoUrl]);
  
  if (loading) {
    return (
      <div>
        {cached ? (
          <p>Loading questions...</p>
        ) : (
          <p>Generating exam-grade questions... This may take 30-60 seconds.</p>
        )}
      </div>
    );
  }
  
  return (
    <div>
      <h2>Quiz ({questions.length} questions)</h2>
      {questions.map((q, idx) => (
        <div key={idx} className="question">
          <span className={`badge ${q.anchor_type}`}>{q.anchor_type}</span>
          <h3>{q.question}</h3>
          <div className="options">
            {Object.entries(q.options).map(([key, value]) => (
              <button key={key}>{key}) {value}</button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 📊 What Happens Behind The Scenes

### **Database Storage**

When questions are generated, they're stored with:

```sql
video_id: "a65d16d6fa55c086"  -- SHA1 hash of URL
url: "https://youtube.com/..."
questions: {JSON array of 20 questions}
generation_mode: "exam-grade"
quality_metrics: {
  schema_version: "2.0",
  anchors: [...],
  evidence_hash: "abc123..."
}
generation_count: 1
created_at: "2024-01-15 10:30:00"
```

### **Caching Logic**

1. **First Request:** Generate → Save → Return (30-60s)
2. **Subsequent Requests:** Check DB → Return cached (instant)
3. **Force Regeneration:** `force: true` → Regenerate → Update → Return

---

## 🎓 Educational Benefits

### **For Learners:**
- ✅ Questions test **video comprehension**, not general knowledge
- ✅ Questions are **answerable from 24-second context windows**
- ✅ Different question types (definition, process, risk, etc.)
- ✅ Randomized order prevents memorization

### **For Instructors:**
- ✅ Automatic question generation (saves hours)
- ✅ Exam-grade quality (regulator-safe)
- ✅ Complete audit trail
- ✅ Anchor statistics show coverage

### **For Platform:**
- ✅ Scalable (generate once, serve many)
- ✅ Fast (cached responses instant)
- ✅ Compliant (EU AI Act, GDPR ready)
- ✅ Defensible (complete evidence trail)

---

## 🚀 Next Steps for Integration

1. **Set up API endpoint** in your backend
2. **Create UI components** for question display
3. **Implement answer checking** (if you store answers separately)
4. **Add loading states** for generation vs cache
5. **Show anchor statistics** for better UX
6. **Handle errors** gracefully

---

## 📝 Summary

**What It Does:**
- Generates exam-quality MCQs from video URLs
- Caches questions for instant retrieval
- Provides complete metadata and audit trail

**How It Works:**
- Video → Transcript → Anchors → Questions → Database
- Rules-based anchor detection (no AI)
- LLM writes questions (doesn't decide)
- Quality validation ensures exam-grade

**What Your App Does:**
- Sends video URL to API
- Receives questions (cached or generated)
- Displays questions to users
- Handles user answers
- Shows results/feedback

**Result:**
- Fast, scalable, exam-grade question generation
- Ready for production use
- Regulator-compliant
- Great user experience

---

**System is production-ready! 🎉**


