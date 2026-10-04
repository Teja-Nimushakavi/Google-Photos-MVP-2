# System Architecture: Smart Suggestions MVP

## 1. System Overview
The Smart Suggestions MVP is a self-contained prototype designed to demonstrate the "fallback retrieval experience" across both **Web** and **Mobile** platforms. The system simulates a photo library search, detects when standard search yields poor or zero results, and dynamically generates one-tap contextual suggestions to help users refine their queries without typing.

The architecture is driven by the **K1–K15 semantic framework** (defined in the Master Prompt) which decomposes user memory fragments into structured, searchable dimensions — and an **information-gain estimation model** that selects the highest-value suggestion at each turn.

## 2. High-Level Architecture
The architecture follows a robust multimodal AI search pipeline (to understand semantics, feelings, and vibes) combined with our Smart Suggestions fallback engine and a multi-turn conversational state manager.

### 2.1 Client Layer (Web & Mobile)
- **Platforms:** Responsive Web Application and Mobile Application.
- **Responsibilities:**
  - Provide a Google Photos-style search input.
  - Display search results and generated multimodal answers.
  - Detect "poor result" states (based on backend confidence scores) and present the "Smart Suggestions" UI.
  - Allow users to multi-select suggestion chips or shuffle them.
  - Re-trigger search with refined contextual parameters.
  - Display the **user-facing natural-language query interpretation** (e.g., "Me on the road with my friends in the evening") and update it dynamically as constraints are added/removed.
  - Support **correction flows**: undo, remove constraint, change mind — without full page reload or search reset.
  - Support **recovery mode UI**: broadening options when refinement still fails.

### 2.2 Data Ingestion Pipeline
- **Responsibilities:**
  - **Feature Extraction (Vision Models):** Analyzes images to extract deeper semantics, objects, feelings, and vibes that cannot be captured by simple tags.
  - **Metadata Extraction (EXIF/GPS):** Extracts hard data like location, timestamp, and camera settings.

### 2.3 The Multimodal Embedding Layer
- **Responsibilities:**
  - Uses the **Gemini Embedding Model** to convert images (and their extracted features/vibes) into dense vector representations.

### 2.4 Hybrid Storage Index
- **Responsibilities:**
  - **Vector Database (Vectors):** Stores the multimodal embeddings for high-speed semantic similarity search.
  - **Cloud Spanner (Metadata/Labels):** Stores the structured metadata (EXIF, tags) for exact filtering.

### 2.5 Gemini Orchestration Agent
- **Responsibilities:**
  - Receives the user's complex search prompt.
  - **Intent Parsing:** Understands what the user is looking for, classifying query intent (K14: exact photo, collection, browsing, event, trip, etc.) and specificity level (K15: broad, moderate, specific, very specific).
  - **Semantic Decomposition:** Extracts K1–K6 primary dimensions and K7–K15 extended dimensions where useful.
  - **Confidence Assignment:** Assigns High/Medium/Low confidence to each attribute based on user language cues ("definitely" → High, "I think" → Medium, "maybe" → Low).
  - **Ambiguity Detection:** Identifies when a query has multiple valid interpretations (e.g., "road" → standing on road, road trip, driving).
  - **Contradiction Detection:** Flags logically conflicting inputs (e.g., "alone with friends").
  - **Negative Constraint Detection:** Recognizes "not with family" as K3 != Family.
  - **Search Tool Selection:** Decides whether to query the Vector Database, Cloud Spanner, or a combination of both.

### 2.6 Vector Search Retrieval & Hybrid Ranking Engine
- **Responsibilities:**
  - Computes Cosine Similarity between the Query Vector and Image Vectors.
  - Combines vector similarity scores with Spanner metadata filters to rank the final results.
  - Uses **confidence-weighted soft ranking**: uncertain attributes (Medium/Low confidence) become ranking signals rather than hard filters.
  - Evaluates result confidence to trigger "poor-result detection".
  - Supports **negative constraint filtering**: excludes results matching K11 constraints.

### 2.7 Multimodal Answer Generation (Gemini LLM)
- **Responsibilities:**
  - Reviews the top image content and context window to craft a text reply.
  - Returns the final answer and images to the user.

### 2.8 Smart Suggestions Engine (Fallback)
- **Responsibilities:**
  - Activated when the Vector Search Retrieval yields low cosine similarity or zero results.
  - Analyzes the parsed intent to identify missing contextual dimensions across the K1–K15 framework.
  - **Information-Gain Estimation:** For each missing dimension, computes: `(Expected Retrieval Improvement × Probability User Can Answer × Ease of Interaction) ÷ Interaction Cost`. Selects the ONE highest-value suggestion.
  - **Result-Aware Suggestions:** Uses the current search result distribution (e.g., 500 beach photos → 80 with user → 35 with friends → 10 at sunset) to pick the most discriminative question.
  - Dynamically generates high-value suggestion chips — never uses the same static suggestions for every query.
  - **Search Before Asking:** Always attempts retrieval first with available information. Only shows suggestions if results are insufficient.
  - Supports **"Not Sure" handling**: marks attribute as Unknown, moves to next useful discriminator, never re-asks.
  - Supports **multiple values** (AND/OR), **negative constraints**, and **uncertain alternatives**.

### 2.9 Conversational State Manager (NEW)
- **Responsibilities:**
  - Maintains the **explicit internal semantic search state** (K1–K15 with confidence levels) across the entire multi-turn session.
  - Maintains a parallel **user-facing natural-language query** for transparency.
  - **Correction Handling:** When user changes mind ("Actually family, not friends"), updates only the affected attribute and re-runs retrieval.
  - **Undo/Remove:** Supports "Remove evening", "Don't filter by location", "Go back" — modifying only the specified attribute.
  - **Multi-Turn Context:** Interprets subsequent user responses in the context of the ongoing conversation (e.g., if the system asks "What time?" and user responds "Actually it was with family", the system correctly targets K3 not K4).
  - **New Search Detection:** Detects when the user starts a completely new search ("Forget that. Find my family photos.") and resets the previous state.
  - Tracks **skipped/rejected questions** to avoid re-asking.
  - Maintains **ambiguity tracking** so the system knows which interpretations are still open.

### 2.10 Recovery Engine (NEW)
- **Responsibilities:**
  - Activated when refinement still fails to produce good results.
  - Diagnoses the failure cause: query too restrictive, interpretation wrong, user memory uncertain, or search term not visually discriminative.
  - Offers appropriate recovery options: Remove time / Remove location / Remove companion / Search similar objects / Search nearby dates / Try another interpretation.
  - **Success Stopping:** Stops showing suggestions when the result set is small enough, confidence is high enough, the user selects a result, or additional refinement has low expected value.

## 3. Data Model

### 3.1 Photo Entity (Hybrid Representation)
A photo record exists across both the Vector Database and Cloud Spanner.
```json
{
  "id": "photo_001",
  "url": "https://example.com/photos/photo_001.jpg",
  "metadata": {
    "location": "Goa",
    "timestamp": "2023-10-15T18:30:00Z"
  },
  "extracted_features": {
    "objects": ["table", "coffee", "laptop"],
    "vibe": "relaxed, warm, evening gathering",
    "activity": "sitting, chatting",
    "environment_type": "indoor",
    "embedding_vector": [0.12, -0.05, 0.88, "..."] 
  }
}
```

### 3.2 Suggestion Entity
The structured data returned to the client when the search needs refinement.
```json
{
  "question": "Who was with you?",
  "category": "K3_Companions",
  "options": [
    { "label": "Friends", "value": "friends", "estimated_results": 35 },
    { "label": "Family", "value": "family", "estimated_results": 12 },
    { "label": "Alone", "value": "alone", "estimated_results": 8 },
    { "label": "Not sure", "value": "unknown", "estimated_results": null }
  ],
  "information_gain_score": 0.82
}
```

### 3.3 Search State Entity (NEW)
The internal semantic state maintained across conversation turns.
```json
{
  "raw_query": "me in road",
  "intent": "exact_photo_retrieval",
  "specificity": "moderate",
  "semantic_state": {
    "K1": { "value": "Me", "confidence": "high" },
    "K2": { "value": "Road", "confidence": "high" },
    "K3": { "value": "Unknown", "confidence": null },
    "K4": { "value": "Unknown", "confidence": null },
    "K5": { "value": "Unknown", "confidence": null },
    "K6": { "value": "Unknown", "confidence": null },
    "K7": { "value": "Unknown", "confidence": null },
    "K8": { "value": "Unknown", "confidence": null },
    "K9": { "value": "Photo", "confidence": "high" }
  },
  "negative_constraints": [],
  "ambiguities": ["Road could mean road environment or road trip"],
  "skipped_dimensions": [],
  "user_facing_query": "Me on the road",
  "turn_count": 1
}
```

## 4. System Data Flow

The following flow describes the system interaction during an unsuccessful search and subsequent refinement.

1. **Initial Search Request:** 
   - Client sends the complex search prompt.
2. **Orchestration & Semantic Decomposition:** 
   - Gemini Orchestration Agent parses intent, extracts K1–K15, assigns confidence levels, detects ambiguities, contradictions, and negative constraints.
   - State Manager creates the initial search state.
3. **Retrieval (Search Before Asking):**
   - Vector Search Retrieval computes cosine similarity and queries Cloud Spanner.
   - Uses confidence-weighted soft ranking for uncertain attributes.
   - Applies negative constraint filters.
   - Evaluates result set. If cosine similarities are below a confidence threshold, flags `needs_refinement = true`.
4. **Suggestion Generation (if needed):**
   - Smart Suggestions Engine runs information-gain estimation across missing dimensions.
   - Uses current result distribution for result-aware suggestions.
   - Selects the ONE highest-value question with concise selectable options.
   - Checks skipped dimensions to avoid re-asking.
5. **Initial Response:**
   - Backend returns results (or empty), the generated suggestion (question + chips), user-facing query interpretation, current search state metadata, and optionally a Multimodal Answer.
6. **User Interaction:**
   - User taps one or more chips, selects "Not sure", or provides a correction/undo.
7. **State Update & Refined Search:**
   - State Manager updates only the affected semantic attributes, preserves all other valid constraints.
   - If user corrects ("Actually family"), only K3 is updated. If user undoes ("Remove evening"), only K4 is reset.
   - Orchestration Agent re-runs retrieval with updated state.
8. **Re-Evaluation & Loop:**
   - System re-evaluates result quality. If refinement is still needed and has expected value, generates the next suggestion. If results are good enough → stop. If retrieval fails completely → enter Recovery Mode.
9. **Recovery Mode (if needed):**
   - Recovery Engine diagnoses failure and offers broadening options.
10. **New Search (if applicable):**
    - If user starts a new search, State Manager resets the previous state entirely.

## 5. Technology Stack Recommendations

- **Frontend (Web & Mobile):** React Native (Expo) or Next.js.
- **Backend:** Python (FastAPI) - mandatory for AI and vector operations.
- **AI / NLP Layer:** Google Gemini for Multimodal Embeddings, Orchestration, Answer Generation, Semantic Decomposition (K1–K15), and Smart Suggestion extraction. Vision Models for initial Feature Extraction.
- **Hybrid Storage Index:** 
  - **Cloud Spanner:** For scalable relational metadata/labels.
  - **Vector Database:** Pinecone, Milvus, or Qdrant for storing and searching Gemini embeddings based on cosine similarity.

## 6. Key Engineering Challenges
- **Multimodal Embedding Quality:** Ensuring the Gemini Embedding Model effectively captures abstract concepts like "vibes" and "feelings" from the Vision Models' extracted features.
- **Vector Search Thresholds:** Defining the cosine similarity threshold at which a result is considered "poor" and triggers the Smart Suggestions Fallback.
- **Information-Gain Estimation Accuracy:** Ensuring the system correctly estimates which question will most effectively narrow the result space, using live result distribution data.
- **Confidence-Weighted Ranking:** Implementing soft ranking where Low/Medium confidence attributes become ranking signals rather than hard filters that might exclude the intended photo.
- **Multi-Turn State Consistency:** Maintaining accurate K1–K15 state across multiple conversation turns, correctly interpreting corrections, undos, contradictions, and new searches without state corruption.
- **Ambiguity Resolution Without Over-Asking:** Searching broad interpretations first and only asking disambiguating questions when ambiguity materially harms retrieval quality.
- **Orchestration Latency:** Keeping the Gemini Orchestration Agent, Semantic Decomposition, Information-Gain Estimation, and Multimodal Answer Generation fast enough that the search experience feels instantaneous.
- **Recovery Mode Design:** Diagnosing *why* retrieval failed (too restrictive, wrong interpretation, non-visual term) and selecting the correct broadening strategy.
