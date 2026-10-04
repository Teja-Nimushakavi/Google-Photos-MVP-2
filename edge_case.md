# Edge Cases & Corner Scenarios: Smart Suggestions MVP

This document outlines potential edge cases and corner scenarios based on the Smart Suggestions MVP architecture and implementation plan. Addressing these scenarios will ensure a robust, production-ready user experience.

## 1. Search & Retrieval Engine Scenarios

| Scenario | Description | Expected Behavior / Mitigation |
| :--- | :--- | :--- |
| **Gibberish / Unrecognized Queries** | User enters "asdfghjkl" yielding 0 results. NLP cannot extract any meaningful intent. | Fallback to a generic set of top-level suggestions (e.g., "Are you looking for: [People], [Places], [Time]?") or simply display "No matches found. Check spelling." without suggestions. |
| **Overly Specific Queries** | User searches "goa beach dinner friend evening dog guitar". 0 results, but almost all contextual dimensions are already present in the text. | The engine should recognize that adding *more* context won't help. Instead, provide chips that allow the user to *broaden* the search, or suggest removing keywords. |
| **Spelling Errors / Typos** | User types "goaa foot frend". If the Retrieval Engine lacks typo-tolerance, it triggers poor results. | The architecture recommends a search layer like Typesense/Meilisearch. If using an in-memory JSON DB, implement basic fuzzy matching before triggering the suggestion engine. |
| **Contradictory Keywords** | User types "indoor beach night morning". | The NLP parser should flag conflicting terms and perhaps prioritize the last typed term, or return 0 results with clarifying suggestion chips like `[Indoor]` vs `[Outdoor]`. |

## 2. Smart Suggestion Engine Scenarios

| Scenario | Description | Expected Behavior / Mitigation |
| :--- | :--- | :--- |
| **Redundant Suggestions** | User types "Goa cafe", and the engine suggests `[Cafe]` or `[Indoor]` (if the system hard-links cafe to indoor). | The Suggestion Engine must parse the query and prune any chips that semantically overlap with the user's initial input. |
| **The "Dead End" Suggestion** | The system suggests `[Evening]`. The user clicks it, but the combination of the query + `[Evening]` results in 0 photos. | Implement **Lookahead Filtering**: The backend must never suggest a chip unless it guarantees at least 1 result when combined with the current query. |
| **Mutually Exclusive Selections** | User is presented with `[Morning]` and `[Evening]`. They tap both. | Depending on the data model, time dimensions might be mutually exclusive. The UI should either toggle them (radio-button style) or the backend should treat them as an `OR` condition (`Morning OR Evening`). |
| **Diminishing Returns (Too Many Results)** | User selects a chip (e.g., `[Indoor]`), but it only reduces the search space from 5,000 to 4,900 photos. | Ensure the engine calculates the "information gain" of each chip. Only suggest chips that significantly narrow down the search space (e.g., drops results by 30-70%). |

## 3. Frontend & UI (Web & Mobile) Scenarios

| Scenario | Description | Expected Behavior / Mitigation |
| :--- | :--- | :--- |
| **Rapid Multi-Tap (Race Conditions)** | User taps 3 chips in rapid succession (e.g., `[Friends]`, `[Indoor]`, `[Food]`). | **Debounce** the API calls on the frontend. Show a loading state instantly on the first tap, queue the selections, and send a single API request after a short delay (e.g., 300ms). |
| **Screen Real Estate on Mobile** | As the user selects chips, they populate the search bar area. Too many selected chips push the photo grid off-screen on small mobile devices. | Implement a horizontally scrollable chip container or collapse selected chips into a summary view (e.g., `Goa + 3 filters`). |
| **Deselecting Chips** | User taps a selected chip to remove it. | The frontend must remove the chip from the context array, instantly show a loading state, and re-trigger the search API with the previous state. |
| **Empty State After Deselection** | User deselects a chip, reverting to the original query which had 0 results. | The UI should gracefully transition back to the initial "Poor Results" screen and re-display the original suggestion chips. |
| **Browser History / Back Button (Web)** | User clicks a chip, views results, and presses the browser back button. | The frontend should sync the selected context chips to the URL query parameters (e.g., `?q=goa&context=indoor,friends`) so the back button correctly restores the previous search state. |

## 4. System & Network Scenarios

| Scenario | Description | Expected Behavior / Mitigation |
| :--- | :--- | :--- |
| **Network Timeout on Refinement** | User taps a chip, but the network connection drops or the backend times out. | The UI should handle the error gracefully, revert the chip to its unselected state, and display a non-intrusive toast notification: "Network error. Please try again." |
| **Cold Start / Caching** | The dataset is large, and parsing context takes too long for the user. | Implement caching (e.g., Redis or simple in-memory LRU cache on the backend) for common queries so the suggestion chips are returned instantly (<100ms). |
| **Empty Dataset** | The user has just created an account and has 0 photos, but they try to search. | Bypass the Suggestion Engine entirely. Display a standard empty state: "You don't have any photos yet." |
