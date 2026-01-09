# 📄 Regulator-Ready Explanation: "Exam-Grade" Learning Verification

**Document Status:** Production-Ready for Regulator Submissions  
**Use Cases:** Regulator submissions, university MoUs, audits, court explanations  
**Version:** 1.0

---

## What Does "Exam-Grade" Mean in This Platform?

The platform distinguishes between **legacy content generation** and **exam-grade learning verification**.

Exam-grade generation is defined by the following properties:

1. **Questions are generated only at pre-identified instructional anchor points** (definitions, decisions, boundaries, risks).

2. **Each anchor is timestamped and documented**, allowing independent review of *why* a question appears at that point.

3. **Learners are provided with context replay** before and after questions to ensure comprehension rather than recall.

4. **Artificial intelligence assists in drafting questions but does not determine outcomes**, pass/fail status, or rewards.

5. **All exam-grade content includes a generation lineage record**, including schema version, anchor usage, and regeneration count.

Legacy content is preserved but is not represented as exam-grade unless explicitly regenerated under the exam-grade pipeline.

This approach ensures transparency, fairness, repeatability, and auditability across jurisdictions.

---

## One-Line Regulator Summary

> **"Exam-grade means every question can be traced to a documented learning anchor, with context and retry support, and without automated decision-making."**

---

## Detailed Technical Explanation

### 1. Anchor-Based Question Generation

**What it means:**
- Questions are generated only at specific, pre-identified points in instructional content
- These points (called "anchors") are detected using rules-based algorithms, not AI
- Anchor types include: definitions, processes, risks, boundaries, and decision points

**Why it matters:**
- Ensures questions test specific, identifiable learning objectives
- Allows independent verification of question placement
- Prevents arbitrary or context-free question generation

**Regulatory compliance:**
- Provides audit trail for "why was this question asked here?"
- Enables content review without replaying entire video
- Supports fairness claims through documented pedagogy

---

### 2. Timestamped and Documented Anchors

**What it means:**
- Each anchor includes:
  - Anchor type (definition, process, risk, boundary, decision)
  - Concept summary (1-2 sentences)
  - Sentence index in transcript
  - Context window parameters (24-second default, adjustable 12-40 seconds)

**Why it matters:**
- Regulators can verify question placement without watching entire video
- Content owners can review and approve anchor selection
- Learners can understand why specific questions appear

**Regulatory compliance:**
- Provides deterministic, reviewable evidence
- Supports "explainability" requirements
- Enables independent audit

---

### 3. Context Replay Support

**What it means:**
- Each question is answerable from a specific 24-second context window
- Context windows are adjustable (12-40 seconds) to accommodate different learning needs
- Questions cannot be answered without viewing the context

**Why it matters:**
- Tests comprehension, not recall
- Prevents "Google-able" questions
- Ensures questions are grounded in specific instructional content

**Regulatory compliance:**
- Supports "fairness" claims (questions are answerable from provided context)
- Prevents external knowledge advantage
- Ensures questions test video content, not general knowledge

---

### 4. AI as Writer, Not Decision Maker

**What it means:**
- AI (LLM) is used only to draft question wording
- AI does not:
  - Determine pass/fail outcomes
  - Assign scores or grades
  - Make decisions about learner performance
  - Personalize content based on learner data

**Why it matters:**
- Maintains human oversight and control
- Prevents automated decision-making (EU AI Act requirement)
- Ensures questions are reviewed and validated

**Regulatory compliance:**
- Complies with EU AI Act Article 6 (prohibited practices)
- Supports "human-in-the-loop" requirements
- Avoids "high-risk AI system" classification for decision-making

---

### 5. Generation Lineage Record

**What it means:**
- Every exam-grade content set includes:
  - Schema version (currently 2.0)
  - Generation mode (exam-grade vs legacy)
  - Complete anchor metadata
  - Generation count (number of regeneration cycles)
  - Timestamp of generation

**Why it matters:**
- Provides complete audit trail
- Enables content versioning and rollback
- Supports reproducibility claims

**Regulatory compliance:**
- Meets documentation requirements
- Supports audit requests
- Enables content verification

---

## Legacy vs Exam-Grade: Key Differences

| Feature | Legacy Mode | Exam-Grade Mode |
|---------|-------------|-----------------|
| **Question Placement** | Random important chunks | Pre-identified anchors |
| **Anchor Detection** | None | Rules-based detection |
| **Question Type Control** | LLM decides | Pedagogy engine controls |
| **Context Windows** | Variable chunks | Fixed 24-second windows |
| **Quality Metrics** | Basic stats only | Complete anchor metadata |
| **Regulator Compliance** | Limited | Full audit trail |
| **Migration** | Cannot be upgraded retroactively | Must regenerate to upgrade |

---

## Migration and Data Lineage

### Non-Destructive Migration

**What it means:**
- Legacy content (`generation_mode = "legacy"`) is preserved as-is
- Legacy content has `quality_metrics = NULL`
- Legacy content is **not** retroactively labeled as exam-grade

**Why it matters:**
- Maintains data integrity
- Prevents false claims about old content
- Ensures accurate audit trail

**Regulatory compliance:**
- Prevents retroactive "upgrading" without regeneration
- Maintains accurate historical records
- Supports compliance with data accuracy requirements

### Regeneration as Explicit Act

**What it means:**
- Legacy → exam-grade upgrade requires explicit regeneration
- Regeneration is triggered by:
  - Admin action
  - Content owner request
  - Scheduled batch job
- Regeneration is **never** automatic or silent

**Why it matters:**
- Ensures deliberate, auditable upgrades
- Prevents accidental downgrades
- Maintains clear data lineage

**Regulatory compliance:**
- Supports "explicit consent" requirements
- Enables audit of upgrade decisions
- Prevents silent background changes

---

## International Compliance

### EU AI Act Compliance

**Article 6 (Prohibited Practices):**
- ✅ AI does not determine outcomes or pass/fail
- ✅ No automated decision-making about learners
- ✅ Human oversight maintained

**Article 10 (High-Risk AI Systems):**
- ✅ System is not classified as "high-risk" for decision-making
- ✅ Used for content generation, not automated assessment

**Article 13 (Transparency):**
- ✅ Complete documentation of generation process
- ✅ Anchor metadata provides explainability
- ✅ Generation lineage record maintained

### GDPR Compliance

**Article 5 (Principles):**
- ✅ Data minimization: Only necessary anchor metadata stored
- ✅ Accuracy: Legacy content not retroactively upgraded
- ✅ Storage limitation: No raw transcripts or audio stored

**Article 25 (Data Protection by Design):**
- ✅ Separation of content (anchors) and learner data
- ✅ No personalization signals in anchor metadata
- ✅ Privacy-preserving architecture

---

## Audit Trail Requirements

### What Regulators Can Request

1. **Question Placement Justification:**
   - Anchor metadata shows why question appears at specific point
   - Concept summary explains learning objective
   - Context window shows answerable content

2. **Generation Process Documentation:**
   - Schema version shows system version
   - Generation count shows regeneration history
   - LLM metadata shows models used

3. **Content Lineage:**
   - Legacy vs exam-grade distinction is clear
   - Migration history is preserved
   - No retroactive upgrades

4. **Quality Assurance:**
   - Anchor distribution shows coverage
   - Retry counts show validation process
   - Generation time shows performance

---

## Marketing Claims (Regulator-Safe)

### ✅ Safe Claims

- "Questions are generated at pre-identified learning anchor points"
- "Each question is traceable to a documented instructional concept"
- "Questions are answerable from specific 24-second context windows"
- "AI assists in question drafting but does not make assessment decisions"
- "Complete generation lineage is maintained for audit purposes"

### ❌ Unsafe Claims (Do Not Use)

- "AI automatically grades learners" (false - AI does not grade)
- "Questions are personalized based on learner performance" (false - anchors are content-only)
- "All content is exam-grade" (false - legacy content exists)
- "Questions are automatically upgraded" (false - regeneration is explicit)

---

## One-Page Summary for Regulators

**Platform Name:** [Your Platform Name]  
**Feature:** Exam-Grade Learning Verification  
**Date:** [Current Date]

### What It Does

Generates multiple-choice questions from video content using anchor-based detection. Questions are placed only at pre-identified instructional points (definitions, processes, risks, boundaries, decisions). Each question is traceable to a documented anchor with context window support.

### How It Works

1. **Anchor Detection:** Rules-based detection of instructional points (no AI)
2. **Question Generation:** AI drafts question wording (AI is writer, not decision maker)
3. **Quality Validation:** Questions validated for context-dependency and anchor compliance
4. **Storage:** Complete anchor metadata stored for audit trail

### Regulatory Compliance

- ✅ **EU AI Act:** No automated decision-making, full transparency
- ✅ **GDPR:** Data minimization, content/learner separation
- ✅ **Audit Trail:** Complete generation lineage, no retroactive upgrades

### Key Differentiator

Legacy content is preserved separately. Only explicitly regenerated content is labeled as exam-grade. Migration is non-destructive and explicit.

---

## Contact for Regulatory Inquiries

**Technical Contact:** [Your ML Engineer]  
**Compliance Contact:** [Your Compliance Officer]  
**Documentation:** This document + `ANCHOR_METADATA_SPECIFICATION.md`

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Status:** Production-Ready for Regulator Use



