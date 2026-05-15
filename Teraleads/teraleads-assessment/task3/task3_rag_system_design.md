# Task 3: RAG System Design — Voice FAQ for Teraleads Dental

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VOICE FAQ PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │ INGESTION│───▶│ CHUNKING │───▶│ EMBEDDING│───▶│ VECTOR STORE │  │
│  │          │    │          │    │          │    │              │  │
│  │ PDFs     │    │ Semantic │    │ text-    │    │ pgvector     │  │
│  │ Website  │    │ (not     │    │ embed-   │    │ (PostgreSQL) │  │
│  │ Protocols│    │ page-    │    │ 3-large  │    │              │  │
│  └──────────┘    │ based)   │    └──────────┘    └──────┬───────┘  │
│                  └──────────┘                           │          │
│                                                         │          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │          │
│  │  VOICE   │───▶│  QUERY   │───▶│ HYBRID   │──────────┘          │
│  │  INPUT   │    │ ENRICH   │    │ RETRIEVAL│                     │
│  │  (ASR)   │    │          │    │ (dense + │                     │
│  └──────────┘    │ intent   │    │  sparse) │                     │
│                  │ class.   │    └─────┬────┘                     │
│                  │ entity   │          │                          │
│                  │ extract  │          ▼                          │
│                  └──────────┘    ┌──────────┐                     │
│                                  │RERANKING │                     │
│                                  │(Cohere / │                     │
│                                  │ BGE-rer.)│                     │
│                                  └─────┬────┘                     │
│                                        │                          │
│                                        ▼                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                    │
│  │  VOICE   │◀───│  VOICE   │◀───│ GENERATE │                    │
│  │  OUTPUT  │    │ RENDER   │    │ (LLM +   │                    │
│  │  (TTS)   │    │          │    │ citation)│                    │
│  └──────────┘    │ SSML     │    └──────────┘                    │
│                  │ prosody  │         │                          │
│                  │ pauses   │    ┌────▼──────┐                   │
│                  └──────────┘    │ GROUNDING  │                   │
│                                  │ & CITATION │                   │
│                                  └────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Choices

| Component                | Choice                                  | Rationale                                                                                                                                                                                           |
| ------------------------ | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Ingestion**            | Unstructured.io + custom PDF parser     | Handles PDFs, DOCX, HTML. Extracts tables and lists (common in treatment protocols).                                                                                                                |
| **Chunking strategy**    | Semantic chunking (not fixed-size)      | Dental knowledge has natural boundaries (one procedure per section). Semantic chunking respects these boundaries, producing coherent chunks that map 1:1 to retrievable facts.                      |
| **Embedding model**      | `text-embedding-3-large` (OpenAI)       | 3072 dimensions, strong on medical/technical text. Can be truncated to 256 dims for cheaper storage if needed.                                                                                      |
| **Vector store**         | `pgvector` on PostgreSQL                | Same DB as the CRM data. No new infrastructure. Supports hybrid search natively (via `pgvector` + `tsvector`).                                                                                      |
| **Retrieval**            | Hybrid (dense + sparse)                 | Dense captures semantic similarity ("How long does an implant take?" ≈ "implant procedure duration"). Sparse (BM25 via `tsvector`) captures keyword precision ("insurance" must match "insurance"). |
| **Reranking**            | Cohere Rerank 3 (or BGE-reranker-v2)    | Top-20 from hybrid → rerank to top-3. Eliminates false positives from embedding-only search.                                                                                                        |
| **Generation**           | GPT-4o-mini (low latency, cheap)        | Instruct-tuned, fast enough for real-time voice. System prompt enforces citation and scope.                                                                                                         |
| **Grounding / citation** | Inline citation markers in the prompt   | The LLM must output `[1]`, `[2]` referencing the retrieved chunks. The voice renderer converts these to "according to your practice's treatment guide..."                                           |
| **Voice rendering**      | SSML with `<break>` for citation pauses | Citations are spoken as natural phrases, not footnotes. Long answers are truncated at 12 seconds with a "would you like me to continue?" prompt.                                                    |

## Three Pushbacks to a PM

### Pushback 1: "One chunk per PDF page"

**PM says:** "Just split each PDF page into one chunk. It's simple."

**I'd say:** Dental PDFs have variable content density. A single page might contain a full treatment protocol (good chunk boundary) or a page break mid-sentence (bad chunk boundary). Semantic chunking groups by topic boundaries (e.g., "Extraction Procedure" vs "Post-Op Care"), which produces chunks that are actually retrievable as complete answers. A page-based approach would split "How long does recovery take?" across two chunks, neither of which contains the full answer.

**Recommendation:** Semantic chunking with a fallback to page-based only when semantic boundaries cannot be detected (e.g., scanned image PDFs).

### Pushback 2: "Let's use the LLM to answer everything, no retrieval"

**PM says:** "GPT-4 knows everything. Why do we need a vector database?"

**I'd say:** GPT-4's training data cutoff means it doesn't know this practice's specific policies, insurance plans, or doctor preferences. Without retrieval, the model will hallucinate plausible-sounding but wrong answers ("Yes, we accept Cigna" when the practice doesn't). RAG grounds every answer in the practice's own documents. This is non-negotiable for a medical-adjacent use case.

**Recommendation:** RAG is mandatory. The LLM is the _reader_, not the _source_.

### Pushback 3: "We need citations as footnotes in the voice channel"

**PM says:** "Add [1], [2] at the end of each spoken answer like a research paper."

**I'd say:** Voice is ephemeral — you cannot scroll back to see a footnote. Instead, citations should be woven into the spoken response naturally: "According to your practice's treatment guide, implant procedures typically take 60 to 90 minutes." The citation is implicit in the phrasing. If the user asks "where did you get that?", the system can read the source document name.

**Recommendation:** Natural-language attribution, not footnotes. Store source metadata for the "tell me more" follow-up.

## Voice-Specific RAG Failure Modes

### 12-Second Answer Problem

Voice channels have a cognitive limit. Answers longer than ~12 seconds cause the caller to lose context or interrupt.

**Solution:** The generator monitors SSML duration (estimated via character count / speaking rate). If the answer exceeds ~12 seconds, it truncates after the first complete sentence and appends: _"That was a lot of information. Would you like me to continue, or would you like to ask something else?"_ If the user says "yes," the remaining chunks are streamed.

### Citation in a Voice Channel

Citations cannot be footnotes in audio.

**Solution:** Use natural-language attribution:

- _"According to your practice's treatment guide..."_
- _"Your insurance policy, uploaded on March 15, states..."_
- _"Dr. Smith's protocol for this procedure recommends..."_

The citation metadata is stored in the response object for logging and audit, but the voice output uses conversational phrasing.

### Medical Question Deflection

Some questions should not be answered by an AI: diagnosis, prognosis, prescription advice.

**Solution:** A classifier (or LLM guardrail) detects medical advice queries. The response is: _"That's a question for your dentist. I can help you book an appointment to discuss it."_ This is a hard-coded deflection, not a retrieved answer. The system logs the deflection for practice review.

## Evaluation Plan

### Offline Eval (Pre-Production)

| Metric                          | Method                                                                | Target   |
| ------------------------------- | --------------------------------------------------------------------- | -------- |
| **Faithfulness**                | LLM-as-judge (GPT-4o) compares answer to retrieved chunks. Score 1–5. | ≥4.5     |
| **Retrieval precision@k**       | Human-annotated relevance of top-3 retrieved chunks.                  | ≥0.85    |
| **Retrieval recall@k**          | Fraction of relevant chunks in top-10.                                | ≥0.80    |
| **Answer completeness**         | Human raters: "Does this answer fully address the question?"          | ≥90% yes |
| **Refusal rate (out-of-scope)** | % of out-of-scope questions correctly deflected.                      | 100%     |

**Dataset:** 200 QA pairs sourced from real dental practice FAQs, treatment protocols, and insurance documents. 50 adversarial (out-of-scope, PII, medical advice).

### Online Eval (Production Shadow)

| Metric                  | Method                                     | Target |
| ----------------------- | ------------------------------------------ | ------ |
| **User satisfaction**   | Post-call survey (1–5) or thumbs up/down.  | ≥4.0   |
| **Abandonment rate**    | % of calls where user hangs up during FAQ. | <15%   |
| **Escalation rate**     | % of FAQ calls transferred to human.       | <10%   |
| **Average handle time** | Duration of FAQ interaction.               | <90s   |

### Launch Guardrail

**Hard guard:** If faithfulness score drops below 4.0 for any rolling 1-hour window, auto-disable the FAQ feature and fall back to: _"I'm sorry, I'm having trouble answering that right now. Let me transfer you to our front desk."_ Notify the engineering team immediately.

## PHI / HIPAA-Adjacent Concerns

### At Ingest

- Scan all uploaded documents for PHI patterns (names, DOBs, SSNs, phone numbers) using a regex + NER pipeline.
- If PHI is detected, flag the document for human review. Do not index until reviewed.
- Strip metadata (author, creation date) from uploaded files — these may contain patient names in the `Author` field.

### At Retrieval Time

- The vector store is access-controlled at the practice level. Practice A's documents are never returned for Practice B's queries.
- No patient-specific data is stored in the vector index. The KB is limited to practice-level information (policies, protocols, insurance info).
- Query logs are anonymized after 30 days.

### In the Generated Answer

- The LLM system prompt includes: _"You must never generate patient-specific information (names, dates of birth, medical history). If a question asks about a specific patient, deflect: 'I can only answer general questions. Please contact your practice directly for personal information.'"_
- All generated answers are logged for audit. A periodic batch job scans logs for potential PHI leakage.
- The TTS audio is not stored. Only the text transcript is retained (with a 90-day retention policy).
