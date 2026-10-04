# GOOGLE PHOTOS: Smart Suggestions
**Updated Problem Statement, Product Definition & MVP Specification**
*Graduation Project*

## CORE PRODUCT IDEA
Turn unsuccessful photo searches into a guided memory-recovery journey using contextual, one-tap memory cues.

---

## 0. Executive Summary
Smart Suggestions is a fallback retrieval experience for Google Photos, designed to be implemented across both web and mobile platforms. When a user receives zero or poor-quality search results, the system should not force them to guess more keywords or type a detailed explanation. Instead, it should present a small set of contextual suggestions that help the user recognize what they remember and progressively narrow the search.

**PRODUCT PRINCIPLE:** Don't ask users to remember more. Help them remember through choices.

## 1. Background
As users accumulate thousands of photos and videos, search becomes an important way to retrieve specific memories. However, people often remember a photo through associations and contextual clues rather than precise searchable terms.

**EXAMPLE MEMORY:** "There was a photo from my Goa trip where I was sitting in a small cafe with my friends in the evening."

The user may remember the experience, but not the exact date, album, file name, or searchable terms that would identify the photo. This creates a gap between how humans remember photos and how search systems retrieve them.

## 2. Core Problem
When a user's initial search produces zero results or poor-quality results, Google Photos can become a dead end. The user knows the photo exists but does not know what additional keywords or information the system needs.

This forces the user to:
- Guess different keywords
- Repeat searches
- Think of details they may not remember
- Abandon search
- Manually scroll through a large photo library

**DEEPER PROBLEM:** Users remember photos through contextual associations, but they are expected to translate those memories into precise search terms.

## 3. User Pain

### 3.1 Search Guessing
Users repeatedly change keywords because they do not know which terms will produce the desired photo.
**VOICE OF THE CUSTOMER:** "I searched regarding my graduation project title and couldn't able to find out. And I gave up... Started scrolling." - Subbu

### 3.2 High Cognitive Load
Users may know additional things about the memory, but they may not know or remember them precisely enough to describe them in a sentence.
**EXAMPLE:** "I remember it was somewhere in Goa, maybe with friends, probably indoors." The user has useful clues, but converting those clues into an effective search query is difficult.

### 3.3 Search Abandonment
When search becomes unsuccessful, users often switch to manual scrolling. This becomes increasingly inefficient when users have thousands of photos.
**VOICE OF THE CUSTOMER:** "I didn't get what I want exactly. Later I scrolled and got it." - Sairam
**VOICE OF THE CUSTOMER:** "Even if I use search option the output is not accurate... Then I used scrolling for the photo exactly what I need." - Satish

## 4. Why a Chatbot Is Not the Ideal Fallback
A conversational AI may appear to be a natural solution: "Tell me more about the photo you're looking for." But this creates another problem. The user may not know the additional information, and typing a complete description adds effort.

**FAILURE MODE:** The system is effectively asking the user to solve the retrieval problem themselves.
Our user feedback supports this concern: users may reject a chatbot because it asks for more details that they cannot reliably provide.
**VOICE OF THE CUSTOMER:** "First option [Chatbot] asks for more details about the search which I may not be able to answer." - Person 6

## 5. Product Opportunity
The opportunity is to turn a failed search into a guided memory-recovery experience.

**CURRENT EXPERIENCE:** Search -> Poor / No Results -> Guess another keyword -> Search again -> Still unsuccessful -> Manual scrolling
**PROPOSED EXPERIENCE:** Search -> Poor / No Results -> Smart Suggestions -> One-tap memory cues -> Refined search -> Relevant results

Instead of asking the user to remember more information, the product helps the user recognize useful contextual possibilities.

## 6. Proposed Solution - Smart Suggestions
When the initial search produces zero or poor-quality results, Google Photos should proactively present a small set of contextual Smart Suggestions. These suggestions should not be random tags. They should be selected based on the original query, available photo attributes, likely missing context, and the amount by which a suggestion can reduce the search space.

### 6.1 Example
User searches: "Goa cafe photo"
**SYSTEM RESPONSE:** What do you remember about the photo? `[With friends]` `[Indoor]` `[Food]` `[Evening]`
The user selects "With friends" + "Indoor". The system then refines retrieval using the original query plus those contextual signals.
**REFINED RETRIEVAL:** Goa + cafe + friends + indoor

## 7. The Key Product Difference
The product is not simply an AI system that generates suggestion chips.

**CORE PRODUCT IDEA:** Smart Suggestions act as a bridge between human memory and photo retrieval.
Humans naturally remember: "That Goa cafe photo with my friends." The search system needs structured signals to find it. Smart Suggestions help the user convert associative memory into searchable contextual signals with minimal effort.

## 8. How Smart Suggestions Should Work
1. **Understand the initial query**
   Example: "Goa cafe photo". Identify possible dimensions such as location, place, activity, people, time and environment.
2. **Identify missing useful context**
   Determine what additional information could meaningfully narrow the search. For example: Who was there? Indoor or outdoor? What were you doing? What time was it? What type of photo was it?
3. **Generate high-value suggestions**
   Present 3-6 suggestions that are most likely to reduce the search space instead of displaying every possible category.
4. **User selects one or more suggestions**
   The user taps context such as "With friends" + "Indoor". No typing required.
5. **Refine retrieval**
   Combine the original query with the selected contextual signals.
6. **Re-rank results**
   Retrieve and rank the photos that best match the refined context.
7. **Continue refinement**
   If results are still not useful, provide another relevant set of suggestions without forcing the user to restart.

## 9. Core Semantic Model (K1–K15 Framework)

The Master Prompt defines a 15-dimension semantic framework that the AI uses internally to decompose every user query into structured, searchable attributes. This is the backbone of how Smart Suggestions understands and refines user memories.

### 9.1 Primary Dimensions (K1–K6)
| Dimension | Name | Purpose | Example Values |
|---|---|---|---|
| **K1** | Subject / Person | Who or what is the primary subject | Me, Friend, Family, Pet, Object, Group |
| **K2** | Location / Environment | Where the photo was taken | Beach, Road, Goa, Indoor, Outdoor, Home |
| **K3** | Companions | Who else was present | Friends, Family, Alone, Partner, Colleagues |
| **K4** | Time / Temporal Context | When the photo was taken | Morning, Evening, Sunset, Last year, 2023 |
| **K5** | Vibe / Context | Emotional or contextual tone | Calm, Happy, Celebration, Adventure, Fun |
| **K6** | Object / Visual Element | Important objects in the photo | Bike, Car, Cake, Guitar, Helmet, Food |

### 9.2 Extended Dimensions (K7–K15)
| Dimension | Name | Purpose | Example Values |
|---|---|---|---|
| **K7** | Activity | What was happening | Riding, Eating, Dancing, Swimming, Hiking |
| **K8** | Event | Named event or occasion | Birthday, Wedding, Graduation, Road trip |
| **K9** | Media Type | Type of content | Photo, Video, Screenshot, Document, GIF |
| **K10** | Relationship | Social relationship context | College friends, School friends, Siblings |
| **K11** | Negative Constraints | What is explicitly NOT present | K3 != Family, K6 != Car |
| **K12** | Confidence | Certainty level per attribute | High, Medium, Low |
| **K13** | Temporal Relation | Relative time references | After dinner, Before the beach photo |
| **K14** | Query Intent | What the user is trying to find | Exact photo, Collection, Browsing, Event |
| **K15** | Specificity Level | How specific the query is | Broad, Moderate, Specific, Very specific |

**CRITICAL RULE:** K1–K6 are NOT a fixed questionnaire. The system must never automatically ask K1 → K2 → K3 → K4 → K5 → K6. The next question is selected dynamically based on **expected retrieval value**.

### 9.3 Confidence Levels
Each semantic attribute carries a confidence level:
- **High:** "It was definitely Goa."
- **Medium:** "I think it was Goa."
- **Low:** "Maybe Goa or Kerala."

Uncertain memories should be used as **soft ranking signals**, not hard filters.

## 10. Smart Suggestion Categories
| Category | Example suggestions |
|---|---|
| **People** | With friends; With family; Alone; With children |
| **Environment** | Indoor; Outdoor; Beach; Cafe; Home; Office |
| **Activity / Context** | Celebration; Food; Travel; College; Work; Shopping |
| **Time** | Morning; Afternoon; Evening; Night; Last year |
| **Photo Type** | Group photo; Selfie; Document; Landscape; Food photo |

*Important principle: prioritize relevant suggestions rather than displaying every possible category.*

## 11. Information-Gain Based Suggestion Selection
When information is missing, the system estimates the expected value of asking about each candidate attribute using:

```
Expected Retrieval Improvement
× Probability User Can Answer
× Ease of Interaction
÷ Interaction Cost
```

Prioritize attributes that:
- Strongly reduce ambiguity
- Are easy for users to answer
- Are likely to be remembered
- Match the current search context
- Are supported by current retrieval evidence

**Result-Aware Suggestions:** The suggestion system must use the current search result distribution. If retrieval identifies 500 beach photos, 80 likely containing the user, 35 with friends, and 10 around sunset — the engine should choose whichever question narrows results most effectively.

## 12. Trigger Condition
A key design change for the MVP is to avoid triggering Smart Suggestions only when there are zero results.

### 12.1 Zero Results
No photos match the initial query.

### 12.2 Poor Results
Photos are returned, but the results are unlikely to satisfy the user's intent. For example, a search for "My college farewell photo" may return dozens of college photos but none that feel relevant.

**DEFINITION:** Smart Suggestions are a recovery mechanism for unsuccessful retrieval, not only a zero-results mechanism.

## 13. Multi-Turn Conversation & State Management

### 13.1 Query State
The system maintains an explicit internal semantic search state (K1–K15) that updates after every user interaction. A parallel natural-language representation is maintained for user transparency.

**Example Internal State:**
```
Raw Query: "me in road"
Intent: Exact photo retrieval
K1: Me (Confidence: High)
K2: Road (Confidence: High)
K3: Unknown
K4: Unknown
...
Ambiguities: Road could mean road environment or road trip
```

**Example User-Facing Query:**
"Me on the road with my friends in the evening"

### 13.2 Correction Handling
- **User changes mind:** "Actually, I think I was with my family" → Update K3 = Family, remove Friends. Do NOT reset the entire query.
- **Single attribute correction:** "Actually it was morning" → Change only K4 = Morning, preserve all other constraints.
- **Undo/Remove:** "Remove evening" or "Don't filter by location" → Modify only the specified attribute.

### 13.3 "Not Sure" Handling
If a user selects "Not sure" for an attribute:
- Mark it Unknown
- Do not repeatedly ask about it
- Move to another useful discriminator
- Do not treat "Not sure" as a negative constraint

### 13.4 Multiple Values & Negative Constraints
- **AND:** "me with friends and family" → K3 = Friends AND Family
- **OR:** "friends or family" → K3 = Friends OR Family
- **Negative:** "not with my family" → K3 != Family (never infer unsupported positive alternatives)

## 14. Ambiguity & Interpretation Handling

### 14.1 Ambiguous Queries
"me on road" could mean standing on a road, road trip, driving, or photo near a road. The system should search broad interpretations first and ask for clarification only if ambiguity materially harms retrieval.

### 14.2 Contradictory Information
"me alone with my friends" → Do not silently choose. Ask: **Were you alone or with friends?** Options: Alone / With friends / Both-different photos / Not sure.

### 14.3 Object as Primary Memory
"the picture of my bike" — the bike may be K1 (primary subject) or K6 (secondary element), depending on intent. Compare: "photo of my bike" (centers bike) vs. "photo of me with my bike" (centers user).

## 15. Recovery Mode

### 15.1 Zero-Result Recovery
When results are weak or absent, the system determines:
- Is the query too restrictive?
- Is an interpretation likely wrong?
- Is user memory uncertain?
- Is the search term not visually discriminative?

Then offers appropriate recovery: **"No strong matches yet. Would you like to broaden the search?"**
Options: Remove time / Remove location / Remove companion / Search similar objects / Search nearby dates / Try another interpretation.

### 15.2 Success Stopping Conditions
Stop showing Smart Suggestions when:
- The intended photo is likely among the top results
- Result confidence is sufficiently high
- The result set is small enough to inspect
- The user selects a result
- The user asks to stop refining
- Additional information has low expected retrieval value

The system should always prefer **successful retrieval** over **complete metadata collection**.

## 16. Golden Rules (from Master Prompt §86)
1. Do not ask merely because information is missing
2. Ask only when the expected answer can improve retrieval
3. Search before asking whenever reasonable
4. Never invent user information
5. Never convert uncertainty into certainty
6. Allow multiple values
7. Allow negative constraints
8. Allow corrections without resetting the entire search
9. Support broad browsing and exact retrieval differently
10. Use search-result quality to choose the next suggestion
11. Treat user interaction as retrieval feedback
12. Do not repeatedly ask rejected or skipped questions
13. Stop refining when additional refinement has low value
14. Recover gracefully from zero results
15. The system should feel like an assistant, not a form
16. The user provides memory fragments; the AI performs the semantic structuring

## 17. Master Decision Logic (from Master Prompt §87)
For every search turn, the system executes:
1. Understand the user's request
2. Determine search intent
3. Preserve the original query
4. Detect explicit information
5. Detect contextual information
6. Detect uncertainty
7. Detect contradictions
8. Detect negative constraints
9. Extract K1–K6
10. Extract optional semantic dimensions K7–K15 where useful
11. Assign confidence to each attribute
12. Build the internal semantic search state
13. Search using available information
14. Evaluate result relevance and ambiguity
15. Determine whether further refinement is necessary
16. If refinement is not necessary → Show results
17. If refinement is necessary → Generate candidate questions → Estimate expected retrieval value → Estimate answerability → Estimate interaction cost → Select ONE highest-value Smart Suggestion
18. Show the suggestion with concise selectable options
19. Interpret the user's response
20. Update only the affected semantic attributes
21. Preserve all other valid constraints
22. Re-run retrieval
23. Re-evaluate result quality
24. Repeat only while additional refinement provides meaningful value
25. If retrieval fails → Enter recovery mode
26. If user starts a new search → Reset the previous search state
27. Stop once successful retrieval is likely

## 18. MVP User Journey
1. **Search:** User enters "Goa cafe with friends".
2. **Retrieval:** System attempts to find relevant photos.
3. **Retrieval failure:** Results are empty or poor quality.
4. **Smart Suggestions:** "What do you remember about the photo?" with contextual chips.
5. **Selection:** User taps one or more suggestions.
6. **Refined retrieval:** System searches using original query + selected context.
7. **Results:** Relevant photos are displayed.
8. **Further refinement:** Additional contextual suggestions remain available if needed.

## 19. MVP Objective
**CORE HYPOTHESIS:** When a user's search is unsuccessful, providing relevant one-tap contextual memory cues can increase successful photo retrieval while reducing the effort required from the user.

The MVP is focused on proving the retrieval recovery experience, not rebuilding the entire Google Photos search infrastructure.

## 20. MVP Scope for Antigravity
- **Cross-Platform Support:** The project will be built for both Web and Mobile platforms to ensure a seamless experience across devices.
- **Search Interface:** Google Photos-style search input capable of handling complex natural language prompts.
- **Data Ingestion Pipeline:** Feature Extraction using Vision Models (to understand vibes, feelings, and objects) combined with Metadata Extraction (EXIF/GPS).
- **Multimodal Embedding & Storage:** Google Gemini Embedding Model mapped to a Hybrid Storage Index (Vector Database for embeddings, Cloud Spanner for metadata).
- **Retrieval Engine:** A Gemini Orchestration Agent that performs intent parsing and executes Vector Search Retrieval computing cosine similarities.
- **Poor-Result Detection:** A mechanism to identify when vector search cosine similarities fall below a confidence threshold (or yield zero results).
- **Smart Suggestions Engine (Fallback):** Generates contextual suggestion chips dynamically based on the K1–K15 semantic framework, information-gain estimation, and the remaining vector/search space. Must support multi-turn progressive refinement, contradiction resolution, negative constraints, and confidence-weighted soft ranking.
- **One-Tap Selection:** Allow users to select one or multiple suggestions or shuffle them.
- **Query Refinement:** Combine the original semantic query with selected contextual clues to re-calculate vector similarities. Maintain explicit internal search state (K1–K15) across turns.
- **Recovery Mode:** When refinement still fails, offer broadening options (remove constraints, try alternate interpretations, search nearby dates).
- **Multimodal Generation:** Generate a conversational response explaining the refined results.

## 21. Example MVP Scenario
**User remembers:** "I want that photo from my Goa trip where we were having food with friends."
- **INITIAL SEARCH:** Goa food friends
- **SEARCH RESULT:** No useful results
- **SMART SUGGESTIONS:** What else do you remember? `[Cafe]` `[Indoor]` `[Evening]` `[Group photo]`
- **User selects:** Cafe + Indoor
- **REFINED SEARCH:** Goa + food + friends + cafe + indoor
The system surfaces the most relevant photos. The user can find the photo without writing another sentence, guessing more keywords, starting a completely new search, or scrolling through thousands of photos.

## 22. Product Principle
**FROM SEARCH -> TO RECOGNITION:** Instead of asking "What else can you tell me?", the system asks "Which of these feels closer to what you remember?"
This changes the task from recalling precise information to recognizing useful possibilities. That is the key UX advantage of Smart Suggestions.

## 23. Product Hypothesis
**HYPOTHESIS:** If unsuccessful Google Photos searches are followed by contextually relevant, one-tap Smart Suggestions, users will be more likely to successfully retrieve the intended photo with fewer search attempts and less manual scrolling.

## 24. Primary Success Metric
**Successful Retrieval Rate:** Percentage of unsuccessful search sessions in which a user eventually finds the intended photo after using Smart Suggestions.
**WHY THIS METRIC MATTERS:** It directly measures whether the feature solves the retrieval problem rather than simply measuring whether users clicked the AI suggestions.

## 25. Supporting Metrics
| Metric | What it tells us |
|---|---|
| **Suggestion Engagement** | Whether users interact with Smart Suggestions after an unsuccessful search. |
| **Search Recovery Rate** | How often an unsuccessful search becomes successful after Smart Suggestions are used. |
| **Time to Retrieval** | Time from the initial unsuccessful search to successful photo retrieval. |
| **Refinement Effort** | Average number of suggestion selections required to find the photo. |
| **Search Abandonment Rate** | How often users leave without finding the intended photo. |
| **Manual Scrolling Rate** | How often users switch from search to manual scrolling after an unsuccessful search. |
| **Suggestion Acceptance Rate** | Percentage of Smart Suggestions selected by users. |
| **Refinement Effectiveness** | Average improvement in retrieval relevance after a suggestion. |
| **Zero-Result Recovery Rate** | Percentage of zero-result sessions that recover successfully through broadening or reinterpretation. |
| **Top-Result Success** | Percentage of searches where the intended photo appears among the highest-ranked results. |

## 26. What the MVP Should Prove
- **CURRENT EXPERIENCE:** Search -> Poor / No Results -> Guess another keyword -> Search again -> Still unsuccessful -> Manual scrolling
- **SMART SUGGESTIONS EXPERIENCE:** Search -> Poor / No Results -> Smart Suggestions -> Recognize contextual clue -> One-tap selection -> Refined retrieval -> Relevant results

The MVP should demonstrate whether the second flow can make failed search recoverable with less effort and less abandonment.

## 27. Final Problem Statement
**FINAL WORDING:** Google Photos users often remember photos through contextual associations - such as people, places, activities, environments, and moments - but may not know the precise keywords required to retrieve them. When a search produces zero or poor-quality results, users are forced to guess additional keywords, provide information they may not remember, or abandon search and manually scroll through their library. The product opportunity is to transform this failed-search moment into a guided retrieval experience through Smart Suggestions: contextually relevant, one-tap memory cues that help users express what they remember and progressively narrow the search space without requiring additional typing or precise recall. The MVP will test whether this approach can increase successful photo retrieval while reducing search effort, time to retrieval, and search abandonment.

## 28. One-Line Product Definition
**PRODUCT DEFINITION:** Smart Suggestions help users find the photos they remember by turning vague memories into simple, one-tap contextual clues.

## 29. Core Product Principle (from Master Prompt §88)
The feature should transform **vague human memory** into **structured semantic search** without requiring the user to understand how photo search works.

- The user should remember.
- The AI should interpret.
- The system should retrieve.

**Better memory understanding → Better semantic representation → Better query refinement → Better retrieval → Less user effort → Successful photo discovery.**

The ultimate experience should feel like: **"I don't need to remember the exact words. Google Photos helps me remember what I meant."**

## 30. Antigravity Build Framing
For the MVP implementation, the product should adopt the actual AI search architecture required to understand deep semantics and vibes.
- Build a Data Ingestion Pipeline integrating Vision Models and Gemini Embeddings for a curated photo dataset.
- Store the embeddings in a Vector Database alongside metadata in Cloud Spanner.
- Implement the Gemini Orchestration Agent for intent parsing and vector search retrieval.
- Start with the baseline multimodal vector search experience.
- Trigger the Smart Suggestions fallback for low cosine similarity retrieval scores.
- Generate suggestions dynamically from the query intent, K1–K15 semantic state, and missing high-value contextual vectors/dimensions using information-gain estimation.
- Allow multi-select chips, shuffling, and iterative refinement with full state management.
- Support correction, undo, negative constraints, multiple values, and recovery mode across multiple conversation turns.
- Track the retrieval outcome so the MVP can compare baseline multimodal search failures vs Smart Suggestions recovery.

**RECOMMENDED DEMO STORY:** Show a complex semantic search for a "vibe" or "feeling" where even the advanced vector search struggles due to missing context. Then show the Smart Suggestions fallback prompting the user with the right memory cues to successfully retrieve the exact photo.
