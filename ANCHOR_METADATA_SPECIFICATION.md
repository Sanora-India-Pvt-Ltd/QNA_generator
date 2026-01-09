# 🔒 Anchor Metadata Format Specification (Locked)

**Version:** 1.0  
**Status:** FINAL - Do not modify without architecture review  
**Purpose:** Contract between Structure Engine and all downstream systems

---

## ✅ Design Principle

> **Anchors are content-facts. Learner performance is stored elsewhere.**

This separation is **critical** for GDPR / EU AI Act compliance.

---

## 📋 Anchor Object (Canonical Format)

### Complete Anchor Metadata Structure

```json
{
  "anchor_id": "a_003",
  "anchor_type": "BOUNDARY",
  "concept_summary": "Operation above 80°C causes overheating",
  "source": "video",
  "sentence_index": 42,
  "context_window": {
    "default_seconds": 24,
    "user_adjustable": true,
    "min_seconds": 12,
    "max_seconds": 40
  },
  "question": {
    "question_type": "scenario_boundary",
    "format": "mcq",
    "difficulty": "medium",
    "retry_variant_count": 2
  },
  "llm": {
    "generator_model": "qwen2.5:1.5b",
    "critic_model": "qwen2.5:1.5b",
    "generation_pass": 1
  }
}
```

---

## 🔑 Field Definitions

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `anchor_id` | string | Unique identifier for this anchor | `"a_003"` |
| `anchor_type` | string | Type of anchor (see Anchor Types below) | `"BOUNDARY"` |
| `concept_summary` | string | 1-2 sentence summary of the concept (max 200 chars) | `"Operation above 80°C causes overheating"` |
| `source` | string | Source of anchor: `"video"`, `"specification"`, or `"ai_text"` | `"video"` |
| `sentence_index` | number | Index of sentence in transcript (0-based) | `42` |

### Context Window Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context_window.default_seconds` | number | Default context window size (24 seconds) | `24` |
| `context_window.user_adjustable` | boolean | Whether user can adjust window size | `true` |
| `context_window.min_seconds` | number | Minimum allowed window size | `12` |
| `context_window.max_seconds` | number | Maximum allowed window size | `40` |

### Question Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `question.question_type` | string | Question type (see Pedagogy Types below) | `"scenario_boundary"` |
| `question.format` | string | Question format (always `"mcq"` for now) | `"mcq"` |
| `question.difficulty` | string | Difficulty level: `"easy"`, `"medium"`, `"hard"` | `"medium"` |
| `question.retry_variant_count` | number | Number of retry attempts for this anchor | `2` |

### LLM Metadata Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `llm.generator_model` | string | Model used for question generation | `"qwen2.5:1.5b"` |
| `llm.critic_model` | string | Model used for quality validation | `"qwen2.5:1.5b"` |
| `llm.generation_pass` | number | Generation pass number (1 = first attempt) | `1` |

---

## 🎯 Anchor Types

| Type | Description | Pedagogy Type | Example Use Case |
|------|-------------|---------------|------------------|
| `DEFINITION` | Terms, concepts, definitions | `paraphrase` | "What is X defined as?" |
| `PROCESS` | Sequences, steps, procedures | `ordering` | "What is the correct order of steps?" |
| `RISK` | Dangers, warnings, consequences | `consequence` | "What happens if X risk occurs?" |
| `BOUNDARY` | Exclusions, limitations | `exclusion` | "Which does NOT apply?" |
| `DECISION` | Scenario-based decisions | `scenario` | "In scenario X, what should you do?" |
| `DEFAULT` | Fallback for unrecognized anchors | `recall` | Generic recall question |

---

## 📚 Pedagogy Types

| Type | Description | Anchor Type Mapping |
|------|-------------|---------------------|
| `paraphrase` | Identify or restate definition | `DEFINITION` |
| `ordering` | Sequence/order questions | `PROCESS` |
| `consequence` | What happens if risk occurs | `RISK` |
| `exclusion` | "Which does NOT apply" | `BOUNDARY` |
| `scenario` | Scenario-based decision | `DECISION` |
| `recall` | Generic recall | `DEFAULT` |

---

## 🚫 What Anchors Must NEVER Include

Anchors describe **content**, not **people**. The following must **never** be stored in anchor metadata:

- ❌ User data
- ❌ Scoring outcomes
- ❌ Model confidence scores
- ❌ Personalization signals
- ❌ Learner performance data
- ❌ Raw transcript (too large, use `concept_summary` instead)
- ❌ Raw audio
- ❌ Embeddings
- ❌ Probabilities

**Why:** This separation is critical for GDPR / EU AI Act compliance. Learner performance is stored in a separate system.

---

## 📊 Quality Metrics Schema (Complete)

When anchors are stored in `quality_metrics`, the complete structure is:

```json
{
  "schema_version": "2.0",
  "generation_mode": "exam-grade",
  "anchors": [
    {
      "anchor_id": "a_003",
      "anchor_type": "BOUNDARY",
      "concept_summary": "Operation above 80°C causes overheating",
      "source": "video",
      "sentence_index": 42,
      "context_window": {
        "default_seconds": 24,
        "user_adjustable": true,
        "min_seconds": 12,
        "max_seconds": 40
      },
      "question": {
        "question_type": "scenario_boundary",
        "format": "mcq",
        "difficulty": "medium",
        "retry_variant_count": 2
      },
      "llm": {
        "generator_model": "qwen2.5:1.5b",
        "critic_model": "qwen2.5:1.5b",
        "generation_pass": 1
      }
    }
  ],
  "generation_summary": {
    "total_anchors": 7,
    "total_questions": 20,
    "retry_policy": "context-first",
    "legacy_upgraded": false,
    "anchor_distribution": {
      "DEFINITION": 5,
      "PROCESS": 6,
      "RISK": 4,
      "BOUNDARY": 3,
      "DECISION": 2
    }
  },
  "generation_time_seconds": 45.23
}
```

---

## 🔒 Locked Semantics

### `generation_count`

**Frozen Definition:**
- `generation_count` = number of **full regeneration cycles**
- **NOT** retries
- **NOT** partial updates
- Increments only when entire MCQ set is regenerated

**Why:** Avoids future confusion in audits.

---

## 📝 Implementation Notes

1. **Anchor IDs:** Format `a_{index:03d}` (e.g., `a_001`, `a_042`)
2. **Concept Summary:** Truncate to 200 characters max
3. **Sentence Index:** 0-based index in transcript sentence array
4. **Context Window:** Default 24 seconds, adjustable 12-40 seconds
5. **Difficulty:** Currently defaults to `"medium"`, can be enhanced with actual difficulty detection

---

## ✅ Validation Rules

1. `anchor_id` must be unique within a generation
2. `anchor_type` must be one of: `DEFINITION`, `PROCESS`, `RISK`, `BOUNDARY`, `DECISION`, `DEFAULT`
3. `concept_summary` must be 1-200 characters
4. `source` must be one of: `video`, `specification`, `ai_text`
5. `question.question_type` must match anchor type's pedagogy mapping
6. `context_window.default_seconds` must be 24 (exam-grade requirement)

---

## 🔄 Migration Notes

- Legacy content: `quality_metrics = NULL` or `schema_version = "1.0"`
- Exam-grade content: `schema_version = "2.0"` with full anchor metadata
- Migration does **NOT** retroactively upgrade old content
- Regeneration is the only path from legacy → exam-grade

---

**Last Updated:** 2024  
**Status:** FINAL - Locked for production use



