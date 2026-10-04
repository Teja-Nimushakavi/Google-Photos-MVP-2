# Implementation Plan: Smart Suggestions MVP

This document outlines the step-by-step implementation plan for building the Smart Suggestions MVP for Google Photos, targeting both Web and Mobile platforms. Updated to reflect the full **Master Prompt specification** including the K1–K15 semantic framework, information-gain suggestion selection, multi-turn state management, and recovery mode.

## Phase 1: Project Setup & Scaffolding (Days 1-2)
**Goal:** Initialize the monorepo structure and establish the core tech stack for both frontend and backend.
- [ ] **1.1 Setup Version Control:** Initialize a Git repository and define branching strategies.
- [ ] **1.2 Backend Initialization:** 
  - Set up a basic server (e.g., Python FastAPI or Node.js Express).
  - Integrate the Google GenAI SDK (Gemini) and configure API keys.
  - Configure CORS, routing, and environment variables.
- [ ] **1.3 Frontend Initialization (Cross-Platform):** 
  - Scaffold a React Native project using Expo (which supports compiling to both Web and Mobile).
  - Setup UI component libraries and styling frameworks.
- [ ] **1.4 CI/CD & Linting:** Configure ESLint, Prettier (for Frontend) and Ruff/Black (for Python Backend) to ensure code quality.

## Phase 2: Data Ingestion & Multimodal Storage (Days 3-4)
**Goal:** Build the actual pipeline for feature extraction and semantic vector storage.
- [x] **2.1 Feature Extraction Pipeline:** Set up Vision Models to extract deep semantic features (objects, vibes, feelings, activities, environment type) from the dataset of photos, combined with traditional Metadata Extraction (EXIF/GPS).
- [x] **2.2 Multimodal Embedding Generation:** Pass the images and extracted features through the Gemini Embedding Model to generate dense vectors.
- [x] **2.3 Hybrid Storage Setup:** Initialize a Vector Database (e.g., Pinecone/Milvus) for storing the embeddings, and Cloud Spanner (or equivalent relational DB) for exact metadata filtering.

## Phase 3: Core AI Search & Orchestration (Days 5-7)
**Goal:** Build the vector search logic, poor-result detection, and the context suggestion fallback engine.
- [x] **3.1 Gemini Orchestration Agent:**
  - Build the agent to receive natural language prompts, perform Intent Parsing, and determine search tool selection (Vector DB vs. Cloud Spanner).
- [x] **3.2 Vector Search & Hybrid Ranking:**
  - Implement the retrieval engine that computes cosine similarity between query vectors and image vectors.
  - Combine these similarity scores with hard Spanner metadata filters to rank the final results.
- [x] **3.3 Poor-Result Detection:**
  - Define the cosine similarity confidence threshold for "poor results".
  - Ensure the backend properly flags `needs_refinement = true` when similarity is too low.
- [x] **3.4 Smart Suggestions Engine (Fallback) & Multimodal Generation:**
  - Write robust Gemini prompts to dynamically generate highly relevant, non-redundant suggestion chips based on the remaining vector search space when retrieval fails.
  - Implement Multimodal Answer Generation to craft a text reply evaluating the top images.
- [x] **3.5 API Endpoints:**
  - Create the primary `GET /api/search` endpoint that handles the orchestration, vector search, and suggestion generation.

## Phase 3.5: K1–K15 Semantic Framework & Information-Gain Engine (Days 7-9) *(NEW)*
**Goal:** Implement the full semantic decomposition framework and intelligent suggestion selection from the Master Prompt.
- [ ] **3.5.1 Semantic Decomposition Module:**
  - Implement K1–K6 primary dimension extraction from user queries (Subject, Location, Companions, Time, Vibe, Object).
  - Implement K7–K15 extended dimension extraction (Activity, Event, Media Type, Relationship, Negative Constraints, Confidence, Temporal Relation, Query Intent, Specificity Level).
  - Build Gemini prompt templates that extract all dimensions with confidence levels from natural language input.
- [ ] **3.5.2 Confidence Assignment:**
  - Detect language cues for certainty: "definitely" → High, "I think" → Medium, "maybe" → Low.
  - Implement confidence-weighted soft ranking: Medium/Low confidence attributes become ranking signals, not hard filters.
- [ ] **3.5.3 Information-Gain Estimation:**
  - For each missing dimension, compute: `(Expected Retrieval Improvement × Probability User Can Answer × Ease of Interaction) ÷ Interaction Cost`.
  - Use the current search result distribution to make suggestions **result-aware** (e.g., if 500 beach photos → 35 with friends → 10 at sunset, choose the most discriminative question).
  - Select the ONE highest-value suggestion per turn.
- [ ] **3.5.4 Dynamic Suggestion Generation:**
  - Ensure suggestions are context-specific (different suggestions for "beach" vs "birthday" vs "mountain trip").
  - Generate question text + selectable options dynamically, including "Not sure" where appropriate.
  - Always include "Not sure" or equivalent to keep suggestions optional.
- [ ] **3.5.5 Ambiguity Detection & Resolution:**
  - Detect queries with multiple valid interpretations (e.g., "road" → standing on road, road trip, driving).
  - Search broad interpretations first; only ask disambiguating questions if ambiguity materially harms retrieval.
- [ ] **3.5.6 Contradiction Detection:**
  - Detect logically conflicting inputs (e.g., "alone with friends").
  - Present clarification with clear options rather than silently choosing one interpretation.
- [ ] **3.5.7 Negative Constraint Handling:**
  - Parse "not with family" as K3 != Family, "no cars" as K6 != Car.
  - Ensure negative constraints never get converted into unsupported positive assumptions.
  - Apply negative constraints as exclusion filters in vector search and metadata filtering.

## Phase 4: Multi-Turn Conversational State Management (Days 9-11) *(NEW)*
**Goal:** Build the stateful conversation layer that tracks user refinements across multiple turns.
- [ ] **4.1 Search State Object:**
  - Define and implement the search state entity storing: raw query, intent, specificity, K1–K15 values with confidence, negative constraints, ambiguities, skipped dimensions, user-facing query, and turn count.
  - Ensure state persists across API calls within a session.
- [ ] **4.2 State Update Logic:**
  - When user selects a suggestion: update only the affected K-dimension.
  - When user corrects ("Actually family"): update K3 = Family, remove Friends. Preserve all other constraints.
  - When user undoes ("Remove evening"): reset only K4 to Unknown. Preserve everything else.
  - When user selects "Not sure": mark dimension as Unknown, add to skipped list. Never re-ask.
- [ ] **4.3 Multi-Turn Context Interpretation:**
  - If system asks "What time?" and user responds "Actually it was with family", correctly identify this as a correction to K3 (not K4) based on conversational context.
  - Interpret single-word responses (e.g., "friends") as updates to the active search, not new searches.
- [ ] **4.4 Multiple Values Support:**
  - "friends and family" → K3 = Friends AND Family (both must be present).
  - "friends or family" → K3 = Friends OR Family (either is acceptable).
  - Do not collapse multiple values into generic terms like "people".
- [ ] **4.5 New Search Detection:**
  - Detect explicit new search intents ("Forget that. Find my family photos.").
  - Reset the entire previous search state.
  - Do not accidentally carry over old filters.
- [ ] **4.6 User-Facing Query Maintenance:**
  - Maintain a natural-language representation of the current search (e.g., "Me on the road with my friends in the evening").
  - Update dynamically as constraints are added, modified, or removed.
  - Never expose technical fields (K1, K2, etc.) to the user.
- [ ] **4.7 API Endpoint Updates:**
  - Update `/api/search` to accept session state and return updated state.
  - Support `POST /api/refine` endpoint for chip selections, corrections, undos.
  - Support `POST /api/reset` for new search intent.

## Phase 5: Recovery Mode (Days 11-12) *(NEW)*
**Goal:** Implement graceful failure handling when refinement doesn't produce good results.
- [ ] **5.1 Failure Diagnosis:**
  - Detect when refinement cycles aren't improving results.
  - Classify failure cause: query too restrictive, interpretation likely wrong, user memory uncertain, search term not visually discriminative.
- [ ] **5.2 Broadening Options:**
  - Generate recovery suggestions: Remove time / Remove location / Remove companion / Search similar objects / Search nearby dates / Try another interpretation.
  - Present as a distinct UI state ("No strong matches yet. Would you like to broaden the search?").
- [ ] **5.3 Success Stopping Logic:**
  - Stop showing suggestions when: result set is small enough to inspect, confidence is high enough, user selects a result, user asks to stop, or additional refinement has low expected value.
  - Prefer successful retrieval over complete metadata collection.

## Phase 6: Frontend Development (Days 12-16)
**Goal:** Build the cross-platform user interface and integrate it with the backend APIs.
- [x] **6.1 Layout & Navigation:** Build the core shell of the app (Search Bar at top, Photo Grid below).
- [x] **6.2 Search Integration:** Hook up the search input to call the backend API and render the resulting photos.
- [x] **6.3 Smart Suggestions UI:**
  - Create the suggestions container and chip components.
  - Implement logic to display chips when `needs_refinement` is triggered.
- [x] **6.4 Multi-Select & Refinement:**
  - Enable users to tap and select one or multiple context chips.
  - Automatically append selected chips to the search state and re-trigger the search API.
  - Update the photo grid with the refined results.
- [ ] **6.5 User-Facing Query Display (NEW):**
  - Display the natural-language interpretation of the current search prominently.
  - Update dynamically as user adds/removes/corrects constraints.
- [ ] **6.6 Correction & Undo UI (NEW):**
  - Allow users to tap on active constraint chips to remove them.
  - Support "Go back" action to undo the last refinement.
  - Visual distinction for active constraints vs. suggestion chips.
- [ ] **6.7 Recovery Mode UI (NEW):**
  - Distinct visual state when entering recovery mode.
  - Broadening option chips styled differently from normal suggestions.
  - Clear messaging: "No strong matches yet. Would you like to broaden the search?"
- [ ] **6.8 Confidence Indicators (NEW):**
  - Visual cues for uncertain attributes (e.g., "maybe Goa" shown differently from "Goa").
  - Optional: show result count estimates on suggestion chips.

## Phase 7: Testing, UX Polish & Deployment (Days 16-18)
**Goal:** Validate the MVP hypotheses and ensure a seamless experience on Web and Mobile.
- [ ] **7.1 End-to-End Testing:**
  - Test the "Failed Search → Smart Suggestions → Successful Retrieval" user journey.
  - Test multi-turn refinement flows: add constraint → correct → undo → new search.
  - Test edge cases: contradictory inputs, negative constraints, "not sure" chains, very vague queries ("that photo I liked").
  - Test recovery mode flows: too-restrictive query → broadening → successful retrieval.
  - Verify layout responsiveness across Web browsers and Mobile devices.
- [x] **7.2 UX Polish:**
  - Add micro-interactions (e.g., loading states, smooth transitions when chips are selected, empty states).
  - Ensure the "bridge between human memory and photo retrieval" feels natural and fast.
  - Ensure the system feels like an assistant, not a form (Golden Rule #15).
- [x] **7.3 Analytics & Metric Tracking:**
  - Implement basic event tracking for the primary success metrics: *Successful Retrieval Rate*, *Suggestion Engagement*, *Refinement Effort*, *Search Abandonment Rate*, *Zero-Result Recovery Rate*, *Top-Result Success*.
- [ ] **7.4 Golden Rules Validation (NEW):**
  - Verify the system never asks merely because information is missing.
  - Verify it searches before asking whenever reasonable.
  - Verify it never invents user information or converts uncertainty into certainty.
  - Verify it handles corrections without resetting the entire search.
  - Verify it stops refining when additional refinement has low value.
- [ ] **7.5 Final Deployment:**
  - Deploy Backend to a cloud provider (e.g., Render, Heroku).
  - Deploy Frontend Web to Vercel/Netlify.
  - Build Mobile binaries using Expo EAS (if required for demo).

## Summary of Milestones
- **Milestone 1:** Baseline search works over a mock dataset.
- **Milestone 2:** Backend dynamically suggests context chips on poor results.
- **Milestone 3:** K1–K15 semantic decomposition with information-gain based suggestion selection.
- **Milestone 4:** Multi-turn conversational state management with correction/undo/recovery.
- **Milestone 5:** Cross-platform Frontend allows one-tap refinement, correction, recovery, and successful retrieval.
- **Milestone 6:** Golden Rules validated — system feels like an intelligent assistant, not a form.
