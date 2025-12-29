# Agent-03: Web Search Knowledge Enrichment

## Overview

Agent-03 enriches the YouTube transcript with verified web knowledge before generating MCQs. This ensures questions test **real-world knowledge** beyond just the video content.

## Pipeline Integration

```
YouTube URL
   ↓
Transcript (API → Whisper fallback)
   ↓
🧠 Agent-03: Web Knowledge Enrichment
   ├─ Topic Extraction (Ollama llama3:8b)
   ├─ Topic Validation (remove generic words)
   ├─ Query Generation (Ollama llama3:8b)
   ├─ Controlled Web Search (approved domains only)
   ├─ Content Fetching & Cleaning
   └─ Knowledge Synthesis (Ollama llama3:8b)
   ↓
Merged Context (Transcript + Enriched Knowledge)
   ↓
MCQ Generation (Ollama gemma2:2b)
   ↓
20 UNIQUE MCQs (JSON)
```

## Components

### 1. Topic Extraction
- Uses **Ollama llama3:8b** to extract 5-8 key educational topics from transcript
- Focuses on specific, testable concepts
- Output: JSON array of topic strings

### 2. Topic Validation
- Removes generic words: "machine", "device", "system", "technology", etc.
- Requires at least 2 words per topic
- Lowercases and trims all topics
- Removes duplicates

### 3. Query Generation
- Uses **Ollama llama3:8b** to generate 4 intelligent search queries per topic
- Academic phrasing, clear and specific
- Focuses on explanation, risks, safety, technical details

### 4. Controlled Web Search
- **Approved domains only:**
  - `wikipedia.org`
  - `who.int` (World Health Organization)
  - `cdc.gov` (Centers for Disease Control)
  - `nih.gov` (National Institutes of Health)
  - `radiologyinfo.org`
  - `britannica.com`
  - `.edu` (Educational institutions)
  - `.gov` (Government sites)
  - `.org` (Non-profit organizations)

- Uses DuckDuckGo HTML search (no API key needed)
- Filters results to approved domains only

### 5. Content Fetching & Cleaning
- Fetches web page content
- Removes: ads, nav bars, footers, scripts, styles, iframes
- Cleans whitespace
- Limits to 4000 characters per page

### 6. Knowledge Synthesis
- Uses **Ollama llama3:8b** to synthesize web content
- Creates exam-ready explanations (200-300 words)
- Educational tone, fact-based
- Combines up to 3 sources per topic

## Configuration

### Models Used
- **Topic Extraction**: `llama3:8b` (better accuracy)
- **Query Generation**: `llama3:8b` (better accuracy)
- **Knowledge Synthesis**: `llama3:8b` (better accuracy)
- **MCQ Generation: `gemma2:2b` (faster, good for MCQs)

### Limits
- Max 3 topics processed (to avoid timeout)
- Max 2 queries per topic
- Max 1 result per query
- Max 3 sources per synthesis
- 4000 chars per fetched page

## Usage

Agent-03 runs automatically when you execute:

```bash
python youtube_quiz_generator.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Expected Output

```
🧠 Agent-03: Web Knowledge Enrichment
   Extracting topics from transcript...
   ✓ Extracted 6 topics
   ✓ Validated 4 topics
   📚 Enriching: x-ray radiation
   📚 Enriching: ionizing radiation safety
   📚 Enriching: medical imaging risks
   ✓ Generated enriched knowledge (2847 chars)
✓ Merging transcript with enriched knowledge...
```

## Benefits

✅ **Exam-grade depth**: Questions test real-world knowledge, not just video content
✅ **Trustworthy sources**: Only approved educational/government sites
✅ **Offline-first**: Uses local Ollama models (no paid APIs)
✅ **Controlled**: No random blogs or SEO junk
✅ **Automatic**: Runs seamlessly in the pipeline

## Troubleshooting

### No topics extracted
- Transcript may be too short or unclear
- Try a longer video with more technical content

### No valid topics after validation
- Topics may be too generic
- Try a more specific/technical video

### Web search returns no results
- Approved domains may not have content for the topic
- Agent-03 will gracefully skip enrichment and use transcript only

### Timeout errors
- Reduce number of topics processed (currently max 3)
- Use faster Ollama models
- Check internet connection for web search

## Future Enhancements

- [ ] Caching: Avoid repeat searches for same topics
- [ ] More approved domains (medical journals, technical references)
- [ ] Wikipedia API direct integration (more reliable)
- [ ] Difficulty-level tagging based on enriched knowledge
- [ ] FastAPI agent separation for scalability

