# 🔄 Integration Flow: How Everything Works Together

## 📊 Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER'S APP/WEB FRONTEND                      │
│                                                                  │
│  User uploads/watches video                                     │
│         ↓                                                        │
│  App sends: POST /videos/mcqs                                   │
│  { video_url: "https://..." }                                    │
│         ↓                                                        │
│  [Loading State]                                                │
│         ↓                                                        │
│  Receives: { questions: [...], cached: true/false }            │
│         ↓                                                        │
│  Displays questions to user                                     │
│         ↓                                                        │
│  User answers → App checks → Shows results                      │
└─────────────────────────────────────────────────────────────────┘
                            ↕ HTTP Request/Response
┌─────────────────────────────────────────────────────────────────┐
│                    MCQ GENERATION API                           │
│                                                                  │
│  1. Receives video_url                                          │
│     ↓                                                            │
│  2. Generates video_id (SHA1 hash)                              │
│     ↓                                                            │
│  3. Checks MySQL database:                                      │
│     • If cached → Return instantly (< 1s)                      │
│     • If not cached → Generate (30-60s)                       │
│     ↓                                                            │
│  4. Generation Process:                                         │
│     a) Sample 8 video clips (12s each)                          │
│     b) Transcribe with Whisper AI                               │
│     c) Detect anchors (rules-based, no AI)                      │
│     d) Generate questions (LLM writes, rules validate)           │
│     e) Save to database                                         │
│     ↓                                                            │
│  5. Return JSON response with questions                         │
└─────────────────────────────────────────────────────────────────┘
                            ↕ Database Query
┌─────────────────────────────────────────────────────────────────┐
│                    MYSQL DATABASE                               │
│                                                                  │
│  Table: video_mcqs                                               │
│  • video_id (unique)                                             │
│  • url                                                           │
│  • questions (JSON)                                              │
│  • generation_mode ("exam-grade" or "legacy")                    │
│  • quality_metrics (complete metadata)                           │
│  • created_at, updated_at                                        │
│                                                                  │
│  Caching: Same video_id = instant return                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Real-World Example

### **Scenario: User Takes Quiz After Watching Video**

#### **Step 1: User Action**
```
User clicks "Take Quiz" button after watching video
```

#### **Step 2: App Makes API Call**
```javascript
// Your app code
const response = await fetch('http://api:8000/videos/mcqs', {
  method: 'POST',
  body: JSON.stringify({
    video_url: "https://youtube.com/watch?v=abc123",
    include_answers: false,
    randomize: true,
    limit: 20
  })
});
```

#### **Step 3: API Processing**

**First Time (Not Cached):**
```
1. API receives request
2. Generates video_id = "a65d16d6fa55c086"
3. Checks database → NOT FOUND
4. Starts generation:
   - Downloads video samples
   - Transcribes audio (Whisper)
   - Detects 20 anchors
   - Generates 20 questions (Ollama)
   - Validates quality
   - Saves to database
5. Returns response (takes 30-60 seconds)
```

**Second Time (Cached):**
```
1. API receives request
2. Generates video_id = "a65d16d6fa55c086"
3. Checks database → FOUND!
4. Returns cached questions instantly (< 1 second)
```

#### **Step 4: App Receives Response**
```json
{
  "status": "success",
  "video_id": "a65d16d6fa55c086",
  "count": 20,
  "cached": true,  // or false if first time
  "mode": "exam-grade",
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
    },
    // ... 19 more questions
  ]
}
```

#### **Step 5: App Displays Questions**
```
┌─────────────────────────────────────┐
│  Quiz: 20 Questions                 │
│  [DEFINITION] Question 1/20         │
│                                     │
│  What is the definition of...      │
│                                     │
│  ○ A) Option A                      │
│  ○ B) Option B                      │
│  ○ C) Option C                      │
│  ○ D) Option D                      │
│                                     │
│  [Next Question]                    │
└─────────────────────────────────────┘
```

#### **Step 6: User Answers**
```
User selects answer → App stores → Next question
```

#### **Step 7: Results**
```
App shows: "You got 15/20 correct!"
```

---

## 🔑 Key Points

### **For Developers:**

1. **Single Endpoint:** Use `POST /videos/mcqs` for everything
2. **Caching:** First request slow (30-60s), subsequent instant
3. **No Answers:** Answers not included by default (anti-cheat)
4. **Video ID:** Deterministic hash, same URL = same ID

### **For Users:**

1. **First Time:** Wait 30-60 seconds for generation
2. **After That:** Questions appear instantly
3. **Quality:** Exam-grade questions, not random
4. **Context:** Questions test video comprehension

### **For Business:**

1. **Scalable:** Generate once, serve many users
2. **Fast:** Cached responses instant
3. **Compliant:** Regulator-ready, audit trail complete
4. **Cost-Effective:** No repeated generation

---

## 📱 Mobile App Integration

### **iOS (Swift) Example**

```swift
func fetchQuestions(videoUrl: String) async throws -> [Question] {
    let url = URL(string: "http://api:8000/videos/mcqs")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "video_url": videoUrl,
        "include_answers": false,
        "randomize": true,
        "limit": 20
    ]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    
    let (data, _) = try await URLSession.shared.data(for: request)
    let response = try JSONDecoder().decode(MCQResponse.self, from: data)
    
    return response.questions
}
```

### **Android (Kotlin) Example**

```kotlin
suspend fun fetchQuestions(videoUrl: String): List<Question> {
    val client = OkHttpClient()
    val json = JSONObject().apply {
        put("video_url", videoUrl)
        put("include_answers", false)
        put("randomize", true)
        put("limit", 20)
    }
    
    val request = Request.Builder()
        .url("http://api:8000/videos/mcqs")
        .post(json.toString().toRequestBody("application/json".toMediaType()))
        .build()
    
    val response = client.newCall(request).execute()
    val responseBody = response.body?.string()
    // Parse JSON and return questions
}
```

---

## 🌐 Web Integration

### **React Example (Already in SYSTEM_EXPLANATION.md)**

### **Vue.js Example**

```vue
<template>
  <div>
    <div v-if="loading">
      {{ cached ? 'Loading...' : 'Generating questions...' }}
    </div>
    <div v-else>
      <div v-for="(q, idx) in questions" :key="idx">
        <span :class="`badge ${q.anchor_type}`">{{ q.anchor_type }}</span>
        <h3>{{ q.question }}</h3>
        <div v-for="(option, key) in q.options" :key="key">
          <button @click="selectAnswer(idx, key)">
            {{ key }}) {{ option }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      questions: [],
      loading: true,
      cached: false
    }
  },
  async mounted() {
    const response = await fetch('http://api:8000/videos/mcqs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_url: this.$route.params.videoUrl,
        include_answers: false,
        randomize: true,
        limit: 20
      })
    })
    
    const data = await response.json()
    this.questions = data.questions
    this.cached = data.cached
    this.loading = false
  }
}
</script>
```

---

## 🎯 What Happens in Each Mode

### **Exam-Grade Mode (USE_ANCHOR_MODE=true)**

```
Video → Transcript → Anchor Detection → Questions → Database
         ↓              ↓                    ↓
      Whisper      Rules-based          LLM writes
      (AI)         (No AI)             (Writer only)
```

**Result:**
- Questions at specific learning points
- 24-second context windows
- Complete metadata
- Regulator-safe

### **Legacy Mode (USE_ANCHOR_MODE=false)**

```
Video → Transcript → Random Chunks → Questions → Database
         ↓              ↓                ↓
      Whisper      Importance      LLM decides
      (AI)         scoring         everything
```

**Result:**
- Questions from random important chunks
- No anchor metadata
- Faster but less structured

---

## ✅ Integration Checklist

- [ ] Set up API endpoint URL in your app
- [ ] Create HTTP client function
- [ ] Build question display component
- [ ] Add loading states (generating vs cached)
- [ ] Handle errors gracefully
- [ ] Implement answer checking (if needed)
- [ ] Show anchor type badges (exam-grade mode)
- [ ] Add randomization toggle
- [ ] Test with real video URLs
- [ ] Monitor API response times

---

**Ready to integrate! 🚀**


