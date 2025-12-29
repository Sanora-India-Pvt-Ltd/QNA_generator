# Agent-03 Mode Switch Documentation

## Overview

Agent-03 now supports **two modes** for topic validation:

1. **FETCH_ALL_MODE** (`FETCH_ALL_TOPICS = True`) - Fetches everything, no filtering
2. **STRICT_MODE** (`FETCH_ALL_TOPICS = False`) - Exam-grade safety with filtering

## Configuration

In `youtube_quiz_generator.py`, find this section:

```python
# ===============================
# AGENT-03: MODE CONFIGURATION
# ===============================
# Set to True to fetch ALL topics (no filtering) - good for research/exploration
# Set to False for strict exam-grade validation - good for production/exams
FETCH_ALL_TOPICS = True  # 🔥 Change to False for strict mode
```

## Mode Comparison

### FETCH_ALL_MODE (`FETCH_ALL_TOPICS = True`)

**Behavior**:
- ✅ Accepts ALL topics extracted by LLM
- ✅ Accepts single words (e.g., "machine", "scan", "image")
- ✅ Accepts generic words (e.g., "system", "technology")
- ✅ Accepts vague phrases (e.g., "this thing", "modern technology")
- ✅ No filtering or rejection

**Use Cases**:
- Research and exploration
- Internal tools
- Discovery mode
- When you want maximum coverage

**Output Example**:
```
🧠 Agent-03: Web Knowledge Enrichment [FETCH_ALL (no filtering)]
   ✓ LLM extracted 8 topics
   ✓ Validated 8 topics (from 8 extracted)
   📚 Enriching: machine
   📚 Enriching: scanning
   📚 Enriching: images
   ...
```

**Trade-offs**:
- ✅ Maximum coverage
- ✅ More web content fetched
- ⚠️ Lower precision (vague queries)
- ⚠️ More noise in enrichment

### STRICT_MODE (`FETCH_ALL_TOPICS = False`)

**Behavior**:
- ✅ Filters out generic words
- ✅ Requires 2+ words (except domain-specific terms)
- ✅ Rejects vague phrases
- ✅ Exam-grade quality

**Use Cases**:
- Production systems
- Exam/certification content
- High-quality MCQ generation
- When precision matters

**Output Example**:
```
🧠 Agent-03: Web Knowledge Enrichment [STRICT (exam-safe)]
   ✓ LLM extracted 8 topics
   ✓ Validated 3 topics (from 8 extracted)
   📚 Enriching: x-ray radiation
   📚 Enriching: medical imaging safety
   📚 Enriching: ionizing radiation risks
```

**Trade-offs**:
- ✅ High precision
- ✅ Clean enrichment
- ✅ Exam-grade quality
- ⚠️ May skip some topics
- ⚠️ Less coverage

## How It Works

### Topic Validation Logic

```python
def validate_topics(topics):
    if FETCH_ALL_TOPICS:
        # Accept everything, no filtering
        return all topics
    else:
        # Apply strict validation rules
        - Require 2+ words
        - Filter generic words
        - Filter vague phrases
        return validated topics
```

### Fallback Extraction

The fallback keyword extractor also respects the mode:
- **FETCH_ALL**: Includes generic word phrases
- **STRICT**: Filters out generic word phrases

## When to Use Each Mode

### Use FETCH_ALL_MODE When:
- ✅ Exploring new topics
- ✅ Research and discovery
- ✅ Internal tools
- ✅ You want maximum coverage
- ✅ Quality is less critical than coverage

### Use STRICT_MODE When:
- ✅ Production systems
- ✅ Exam/certification content
- ✅ High-quality MCQs required
- ✅ Precision matters
- ✅ You want clean, focused enrichment

## Example Scenarios

### Scenario 1: Technical Video (Both Modes)

**Transcript**: "X-ray radiation is used in medical imaging. Ionizing radiation poses health risks."

**FETCH_ALL_MODE**:
- Topics: `["x-ray", "radiation", "medical imaging", "ionizing radiation", "health risks"]`
- All 5 topics enriched

**STRICT_MODE**:
- Topics: `["x-ray radiation", "medical imaging", "ionizing radiation", "health risks"]`
- 4 topics enriched (single word "x-ray" filtered if not in whitelist)

### Scenario 2: Casual Video (Both Modes)

**Transcript**: "This machine is used for scanning images. The system is modern technology."

**FETCH_ALL_MODE**:
- Topics: `["machine", "scanning", "images", "system", "modern technology"]`
- All 5 topics enriched (may be vague)

**STRICT_MODE**:
- Topics: `["scanning images"]` (or empty if too generic)
- 1 topic enriched (or skipped if all too generic)

## Performance Impact

- **No performance difference** between modes
- Both modes use same LLM calls
- Both modes use same web search
- Only difference is topic filtering

## Switching Modes

Simply change the flag:

```python
# For research/exploration
FETCH_ALL_TOPICS = True

# For production/exams
FETCH_ALL_TOPICS = False
```

No other code changes needed!

## Recommendations

| Use Case | Recommended Mode |
|----------|------------------|
| Research / Exploration | ✅ FETCH_ALL |
| Internal Tools | ✅ FETCH_ALL |
| Production SaaS | ❌ STRICT |
| Exam / Certification | ❌ STRICT |
| High-Quality MCQs | ❌ STRICT |
| Maximum Coverage | ✅ FETCH_ALL |

## Summary

✅ **FETCH_ALL_MODE**: Maximum coverage, no filtering, research-friendly
✅ **STRICT_MODE**: Exam-grade quality, filtered topics, production-ready
✅ **Easy to switch**: Just change one flag
✅ **No performance impact**: Same speed, different filtering

Choose the mode that fits your use case!




