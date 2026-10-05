import json
import math
import os
import uuid
from typing import List, Optional, Dict
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
import chromadb
from groq import Groq

load_dotenv()

app = FastAPI(title="Smart Suggestions MVP Backend")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Paths Configuration for Deployment (e.g. Railway Volumes)
DATA_DIR = os.getenv("DATA_DIR", ".")
STATIC_DIR = os.path.join(DATA_DIR, "static")
JSON_PATH = os.path.join(DATA_DIR, "photos_dataset.json")
DB_PATH = os.path.join(DATA_DIR, "chroma_db")

# Serve static files (like downloaded images)
os.makedirs(STATIC_DIR, exist_ok=True)
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load dataset
try:
    with open(JSON_PATH, "r") as f:
        photos_db = json.load(f)
except FileNotFoundError:
    photos_db = []

# Gemini and Groq Clients
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key and api_key != "your_gemini_api_key_here" else None

groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

ACTIVE_LLM_PROVIDER = "gemini" # Can be 'gemini' or 'groq'

def call_llm_json(prompt: str, schema_class=None) -> str:
    """Helper to call LLM with two-way fallback between Gemini and Groq, returning a JSON string."""
    global ACTIVE_LLM_PROVIDER
    
    def try_gemini():
        if not client: raise Exception("Gemini client not initialized")
        config_args = {"response_mime_type": "application/json", "temperature": 0.0}
        if schema_class:
            config_args["response_schema"] = schema_class
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(**config_args),
        )
        return response.text
        
    def try_groq():
        if not groq_client: raise Exception("Groq client not initialized")
        groq_prompt = prompt + "\n\nRespond ONLY with valid JSON."
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": groq_prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return chat_completion.choices[0].message.content

    if ACTIVE_LLM_PROVIDER == "gemini":
        try:
            return try_gemini()
        except Exception as e:
            print(f"Gemini generation error: {e}. Switching to Groq.")
            ACTIVE_LLM_PROVIDER = "groq"
            return try_groq()
    else:
        try:
            return try_groq()
        except Exception as e:
            print(f"Groq generation error: {e}. Switching to Gemini.")
            ACTIVE_LLM_PROVIDER = "gemini"
            return try_gemini()

def call_llm_text(prompt: str) -> str:
    """Helper to call LLM with two-way fallback between Gemini and Groq, returning a string."""
    global ACTIVE_LLM_PROVIDER
    
    def try_gemini():
        if not client: raise Exception("Gemini client not initialized")
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=prompt,
        )
        return response.text
        
    def try_groq():
        if not groq_client: raise Exception("Groq client not initialized")
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
        )
        return chat_completion.choices[0].message.content

    if ACTIVE_LLM_PROVIDER == "gemini":
        try:
            return try_gemini()
        except Exception as e:
            print(f"Gemini text generation error: {e}. Switching to Groq.")
            ACTIVE_LLM_PROVIDER = "groq"
            return try_groq()
    else:
        try:
            return try_groq()
        except Exception as e:
            print(f"Groq text generation error: {e}. Switching to Gemini.")
            ACTIVE_LLM_PROVIDER = "gemini"
            return try_gemini()

# ChromaDB Client
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_or_create_collection(
    name="photos",
    metadata={"hnsw:space": "cosine"}
)


# ============================================================================
# DATA MODELS — K1–K15 Semantic Framework (from Master Prompt)
# ============================================================================

class QueryDecomposition(BaseModel):
    """Gemini-generated semantic decomposition of a user query into K-dimensions.
    Kept flat (no nesting) for Gemini structured output compatibility."""
    search_terms: Optional[str] = None
    # K1 — Subject / Person
    subject: Optional[str] = None
    subject_confidence: str = "unknown"
    # K2 — Location / Environment
    location: Optional[str] = None
    location_confidence: str = "unknown"
    # K3 — Companions
    companions: Optional[str] = None
    companions_confidence: str = "unknown"
    # K4 — Time / Temporal Context
    time_context: Optional[str] = None
    time_confidence: str = "unknown"
    # K5 — Vibe / Context
    vibe: Optional[str] = None
    vibe_confidence: str = "unknown"
    # K6 — Objects / Visual Elements
    objects: Optional[str] = None
    objects_confidence: str = "unknown"
    # K7 — Activity
    activity: Optional[str] = None
    activity_confidence: str = "unknown"
    # K8 — Event
    event: Optional[str] = None
    event_confidence: str = "unknown"
    # K9 — Media Type
    media_type: Optional[str] = None
    # K14 — Query Intent
    intent: str = "exact_retrieval"
    # K15 — Specificity Level
    specificity: str = "moderate"
    # Environment setting (for metadata matching, distinct from K2 geographic location)
    environment: Optional[str] = None
    # Photo type (for metadata matching)
    photo_type: Optional[str] = None
    # K11 — Negative constraints (e.g., "companions != Family")
    negative_constraints: Optional[List[str]] = []
    # Detected ambiguities
    ambiguities: Optional[List[str]] = []
    # Natural language interpretation for the user
    user_facing_query: str = ""
    # Tags redundant given the query (to exclude from suggestions)
    redundant_tags: Optional[List[str]] = []


class SemanticState(BaseModel):
    """Full session state maintained across multi-turn conversation."""
    session_id: str = ""
    raw_query: str = ""
    decomposition: QueryDecomposition = QueryDecomposition()
    selected_contexts: List[str] = []
    skipped_dimensions: List[str] = []
    turn_count: int = 0
    recovery_attempts: int = 0
    previous_result_count: int = -1
    is_recovery_mode: bool = False


class SuggestionOption(BaseModel):
    label: str
    value: str
    estimated_results: Optional[int] = None


class SmartSuggestion(BaseModel):
    question: str
    dimension: str
    options: List[SuggestionOption]
    information_gain_score: float = 0.0


class SearchResponse(BaseModel):
    results: List[dict]
    needs_refinement: bool
    suggestions: List[dict]
    refinement_question: Optional[str] = None
    # New fields from master prompt
    session_id: Optional[str] = None
    user_facing_query: Optional[str] = None
    semantic_state: Optional[dict] = None
    smart_suggestion: Optional[dict] = None
    active_constraints: List[dict] = []
    is_recovery_mode: bool = False
    recovery_options: List[dict] = []


class RefineRequest(BaseModel):
    session_id: str
    action: str  # "add", "remove", "not_sure", "correct", "reset_refinements"
    dimension: Optional[str] = None
    value: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str


class TrackingEvent(BaseModel):
    event_name: str
    properties: dict = {}


# ============================================================================
# SESSION STORE (in-memory for MVP)
# ============================================================================

sessions: Dict[str, SemanticState] = {}


def get_or_create_session(session_id: Optional[str] = None) -> SemanticState:
    """Retrieve an existing session or create a new one."""
    if session_id and session_id in sessions:
        return sessions[session_id]
    new_id = str(uuid.uuid4())
    state = SemanticState(session_id=new_id)
    sessions[new_id] = state
    return state


# ============================================================================
# SEMANTIC DECOMPOSITION — Gemini K1–K15 Extraction
# ============================================================================

def decompose_query(query: str) -> QueryDecomposition:
    """Extract K1–K15 semantic dimensions from a user query using Gemini.
    
    This replaces the old flat parse_query_with_gemini() with a richer
    decomposition that includes confidence levels, negative constraints,
    ambiguity detection, and a user-facing natural-language interpretation.
    """
    if not client or not query.strip():
        return QueryDecomposition(user_facing_query=query)

    prompt = f"""
    Analyze the following photo search query: "{query}"

    First, autocorrect any misspelled words. Then create search_terms with the corrected query plus relevant synonyms (e.g., for "flag", search_terms could be "flag, american flag, national symbol").

    Extract semantic dimensions following this framework:

    1. subject: The primary subject (e.g., Me, Friend, My dog, My bike). Can be a person, pet, or object.
       subject_confidence: "high" if explicitly stated, "medium" if implied, "low" if guessed, "unknown" if absent.

    2. location: Geographic place OR general setting (e.g., Goa, Beach, Home, Airport, Mountains).
       location_confidence: "high" for "definitely Goa", "medium" for "I think Goa", "low" for "maybe Goa or Kerala".

    3. companions: Who else was present (e.g., Friends, Family, Alone, Partner, Colleagues, Classmates).
       companions_confidence: same scale.

    4. time_context: When the photo was taken (e.g., Morning, Evening, Night, Sunset, Golden Hour, Last year).
       time_confidence: same scale.

    5. vibe: Emotional/contextual tone ONLY if explicitly mentioned (e.g., Calm, Happy, Fun, Celebration, Romantic).
       vibe_confidence: same scale. Do NOT infer emotions from visual appearance.

    6. objects: Important objects/visual elements (e.g., Bike, Car, Cake, Guitar, Laptop, Helmet).
       objects_confidence: same scale.

    7. activity: What was happening (e.g., Swimming, Eating, Dancing, Hiking, Shopping, Cooking, Driving).
       activity_confidence: same scale.

    8. event: Named event/occasion (e.g., Birthday, Wedding, Graduation, Festival, Road trip).
       event_confidence: same scale.

    9. media_type: Photo, Video, Screenshot, Document, Selfie. Set to null if not mentioned.

    10. intent: "exact_retrieval" (one specific photo), "collection" (set of photos), "browsing" (exploration).

    11. specificity: "broad" ("beach photos"), "moderate" ("beach photos with friends"), "specific" ("me with friends at Goa beach at sunset"), "very_specific" (very detailed query with multiple constraints).

    12. environment: The environment/setting (e.g., Indoor, Outdoor, Cafe, Beach, Nature, College Campus, Restaurant, Stadium, Gym).

    13. photo_type: Type of photo (e.g., Group photo, Selfie, Landscape, Document, Portrait, Screenshot, Pet photo).

    14. negative_constraints: Things explicitly NOT present. "not with family" → ["companions != Family"]. "no cars" → ["objects != Car"]. Return as list of strings.

    15. ambiguities: If the query has multiple valid interpretations, list them. E.g., ["road could mean standing on a road or a road trip"].

    16. user_facing_query: A clean natural language interpretation of the search. E.g., "Me on the road with my friends in the evening".

    17. redundant_tags: Tags too obvious given the query. E.g., for "Beach", ["Outdoor", "Nature"] are redundant.

    CRITICAL RULES:
    - Do NOT hallucinate or over-infer. Only extract what is explicitly stated or directly implied.
    - Do NOT force every dimension — leave as null if not mentioned.
    - If the query is just a specific object (e.g., "Laptop"), do NOT map it to broad categories like "Work" or "Indoor".
    - Do NOT convert uncertainty into certainty.
    - "not with friends" is a negative constraint, NOT "with family".
    - Context-specific synonym handling: If the query contains terms like "marks", "marks memo", "marks sheet", or "memo", strongly consider that they might refer to academic transcripts, report cards, or grade sheets (especially in an Indian context). For such queries, ensure `search_terms` includes synonyms like "marks sheet, mark sheet, report card, academic transcript, grade report, marks memo, certificate" and map `photo_type` and `media_type` to "Document".
    """

    try:
        response_text = call_llm_json(prompt, schema_class=QueryDecomposition)
        result = QueryDecomposition.model_validate_json(response_text)
        if not result.user_facing_query:
            result.user_facing_query = query
        return result
    except Exception as e:
        print(f"Decomposition error: {e}")
        return QueryDecomposition(search_terms=query, user_facing_query=query)


# ============================================================================
# VECTOR SEARCH & CONFIDENCE-WEIGHTED RANKING
# ============================================================================

def build_search_text(decomposition: QueryDecomposition, selected_contexts: List[str]) -> str:
    """Build the embedding search text from the semantic state."""
    parts = []
    if decomposition.search_terms:
        parts.append(decomposition.search_terms)
    for field in [decomposition.subject, decomposition.location,
                  decomposition.companions, decomposition.time_context,
                  decomposition.vibe, decomposition.objects,
                  decomposition.activity, decomposition.event,
                  decomposition.environment]:
        if field:
            parts.append(field)
    parts.extend(selected_contexts)
    return " ".join(parts)


def perform_search(
    decomposition: QueryDecomposition,
    selected_contexts: List[str],
    raw_query: str
) -> List[dict]:
    """Execute vector search with confidence-weighted ranking.
    
    Key difference from the old search:
    - High confidence → hard filter (exclude non-matches)
    - Medium confidence → soft ranking boost (don't exclude, but boost matches)
    - Low/unknown confidence → ignore as filter (just use for embedding similarity)
    """
    search_text = build_search_text(decomposition, selected_contexts)

    # 1. Get query vector
    query_vector = None
    if search_text.strip() and client:
        try:
            emb_response = client.models.embed_content(
                model='gemini-embedding-2',
                contents=search_text,
            )
            query_vector = emb_response.embeddings[0].values
        except Exception as e:
            print(f"Embedding error: {e}")

    # 2. Query ChromaDB for candidates
    candidate_ids = []
    distances = {}
    if query_vector:
        try:
            chroma_results = collection.query(
                query_embeddings=[query_vector],
                n_results=100
            )
            if chroma_results and chroma_results["ids"] and len(chroma_results["ids"]) > 0:
                for pid, dist in zip(chroma_results["ids"][0], chroma_results["distances"][0]):
                    candidate_ids.append(pid)
                    distances[pid] = dist
        except Exception as e:
            print(f"ChromaDB query error: {e}")
            candidate_ids = [p["id"] for p in photos_db]
    else:
        candidate_ids = [p["id"] for p in photos_db]

    # 3. Filter and rank candidates
    photos_by_id = {p["id"]: p for p in photos_db}
    results = []

    for pid in candidate_ids:
        if pid not in photos_by_id:
            continue

        photo = photos_by_id[pid]
        meta = photo.get("metadata", {})
        match = True

        # Build search phrases for keyword matching
        search_phrases = []
        if decomposition.search_terms:
            search_phrases.extend([p.strip().lower() for p in decomposition.search_terms.split(',') if len(p.strip()) > 2])
        if decomposition.objects:
            search_phrases.extend([p.strip().lower() for p in decomposition.objects.split(',') if len(p.strip()) > 2])
        if len(raw_query.strip()) > 2:
            search_phrases.append(raw_query.strip().lower())
            
        if selected_contexts:
            for ctx in selected_contexts:
                if len(ctx.strip()) > 2:
                    search_phrases.append(ctx.strip().lower())

        caption_lower = photo.get("caption", "").lower()
        meta_str_lower = str(meta).lower()

        has_keyword_match = False
        for phrase in set(search_phrases):
            if phrase and (phrase in caption_lower or phrase in meta_str_lower):
                has_keyword_match = True
                break

        # --- Selected context chips (always hard filter) ---
        context_match = False
        if selected_contexts:
            for ctx in selected_contexts:
                if ctx.strip() and ctx.strip().lower() not in meta_str_lower:
                    match = False
                    break
                elif ctx.strip():
                    context_match = True

        # --- Vector distance threshold ---
        if pid in distances:
            dist = distances[pid]
            user_q = raw_query.strip().lower()
            is_exact = user_q and len(user_q) > 2 and (user_q in caption_lower or user_q in meta_str_lower)

            if is_exact or context_match:
                allowed_dist = 0.85
            elif has_keyword_match:
                allowed_dist = 0.75
            else:
                # Lower threshold for non-keyword matches to prevent irrelevant results
                allowed_dist = 0.50

            if dist > allowed_dist:
                match = False

        # --- CONFIDENCE-WEIGHTED HARD FILTERS (Master Prompt) ---
        # Only apply hard filters for HIGH confidence dimensions.
        # Medium confidence becomes a soft boost instead.

        if decomposition.location and decomposition.location_confidence == "high":
            loc_val = meta.get("location", "").lower()
            env_val = " ".join([e.lower() for e in meta.get("environment", [])])
            if decomposition.location.lower() not in loc_val and decomposition.location.lower() not in env_val:
                if not has_keyword_match:
                    match = False

        if decomposition.time_context and decomposition.time_confidence == "high":
            time_val = meta.get("time", "").lower()
            dec_time = decomposition.time_context.lower()
            # Map common words to metadata categories to avoid strict mismatch
            if dec_time in ["sunrise", "dawn", "early morning"]: dec_time = "morning"
            if dec_time in ["sunset", "dusk", "golden hour"]: dec_time = "evening"
            
            if dec_time not in time_val:
                if not has_keyword_match:
                    match = False

        # People: if user mentions companions, drop photos explicitly tagged "None"
        if decomposition.companions and decomposition.companions.lower() not in ["none", "unknown", "alone"]:
            photo_people = [p.lower() for p in meta.get("people", [])]
            if "none" in photo_people:
                match = False

        # --- NEGATIVE CONSTRAINTS (Master Prompt §14, §37) ---
        for constraint in (decomposition.negative_constraints or []):
            # Constraints are like "companions != Family" or "objects != Car"
            constraint_lower = constraint.lower()
            # Extract the value after "!=" and check if it appears in metadata
            if "!=" in constraint_lower:
                neg_value = constraint_lower.split("!=")[-1].strip()
                if neg_value and neg_value in meta_str_lower:
                    match = False
                    break

        # We moved the selected_contexts hard filter above the distance threshold.
        
        # --- HARD FILTER for specific media types (Screenshots/Documents/Selfies) ---
        # If the query explicitly asks for or implies a screenshot/document/selfie, strictly enforce it
        # to prevent irrelevant images (like nature/landscape) from showing up due to vector proximity.
        for field in [decomposition.photo_type, decomposition.media_type]:
            if field and field.lower() in ["screenshot", "document", "selfie"]:
                pt_list = [pt.lower() for pt in meta.get("photo_type", [])]
                if field.lower() not in pt_list:
                    match = False
                break

        # --- SOFT BOOST SCORING ---
        boost = 0.0
        if match:
            if has_keyword_match:
                boost += 0.15

            # Environment match
            if decomposition.environment:
                env_list = [e.lower() for e in meta.get("environment", [])]
                if any(decomposition.environment.lower() in e for e in env_list):
                    boost += 0.05

            # Companions match (soft)
            if decomposition.companions:
                people_list = [p.lower() for p in meta.get("people", [])]
                if any(decomposition.companions.lower() in p for p in people_list):
                    boost += 0.05 if decomposition.companions_confidence != "high" else 0.10

            # Activity match (soft)
            if decomposition.activity:
                act_list = [a.lower() for a in meta.get("activity", [])]
                if any(decomposition.activity.lower() in a for a in act_list):
                    boost += 0.05 if decomposition.activity_confidence != "high" else 0.10

            # Photo type match (soft)
            if decomposition.photo_type:
                pt_list = [pt.lower() for pt in meta.get("photo_type", [])]
                if any(decomposition.photo_type.lower() in pt for pt in pt_list):
                    boost += 0.05

            # Medium confidence location/time: use as soft boost instead of hard filter
            if decomposition.location and decomposition.location_confidence == "medium":
                if decomposition.location.lower() in meta.get("location", "").lower():
                    boost += 0.08

            if decomposition.time_context and decomposition.time_confidence == "medium":
                if decomposition.time_context.lower() in meta.get("time", "").lower():
                    boost += 0.08

        if match:
            photo_copy = photo.copy()
            if pid in distances:
                photo_copy["similarity_score"] = (1.0 - distances[pid]) + boost
            else:
                photo_copy["similarity_score"] = 1.0 + boost
            results.append(photo_copy)

    results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    return results


# ============================================================================
# INFORMATION-GAIN SUGGESTION ENGINE (Master Prompt §21–§22)
# ============================================================================

# Mapping from K-dimensions to photo metadata field names
DIMENSION_TO_META = {
    "companions": "people",
    "location": "location",
    "time": "time",
    "environment": "environment",
    "activity": "activity",
    "event": "activity",
    "photo_type": "photo_type",
}

# Answerability weights — how likely users can answer about each dimension
# (Master Prompt: people > location > event > environment > time > activity > photo_type > objects > vibe)
ANSWERABILITY = {
    "companions": 0.95,
    "location": 0.85,
    "event": 0.80,
    "environment": 0.75,
    "time": 0.70,
    "activity": 0.65,
    "photo_type": 0.60,
    "objects": 0.50,
    "vibe": 0.40,
}

# Question templates for each dimension (Master Prompt §75)
QUESTION_TEMPLATES = {
    "companions": "Who was with you?",
    "location": "Where was this taken?",
    "time": "What time of day was it?",
    "environment": "What was the setting like?",
    "activity": "What was happening?",
    "event": "Was this a specific event?",
    "photo_type": "What type of photo was it?",
}


def get_value_distribution(
    dimension: str,
    candidates: List[dict],
    all_photos: List[dict]
) -> Dict[str, int]:
    """Count the distribution of values for a dimension across a photo set.
    This is the foundation for result-aware suggestions (Master Prompt §22)."""
    meta_field = DIMENSION_TO_META.get(dimension, dimension)
    source = candidates if candidates else all_photos

    distribution: Dict[str, int] = {}
    for photo in source:
        meta = photo.get("metadata", {})
        val = meta.get(meta_field)
        if not val:
            continue

        if isinstance(val, list):
            for v in val:
                v_clean = v.strip()
                if v_clean and v_clean.lower() != "none":
                    distribution[v_clean] = distribution.get(v_clean, 0) + 1
        else:
            val_clean = str(val).strip()
            if val_clean and val_clean.lower() != "none":
                distribution[val_clean] = distribution.get(val_clean, 0) + 1

    return distribution


def calculate_entropy(distribution: Dict[str, int]) -> float:
    """Calculate Shannon entropy of a value distribution.
    Higher entropy = values are more evenly spread = asking this question
    will more effectively narrow the result space."""
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    entropy_val = 0.0
    for count in distribution.values():
        p = count / total
        if p > 0:
            entropy_val -= p * math.log2(p)
    return entropy_val


def is_dimension_filled(decomposition: QueryDecomposition, dimension: str) -> bool:
    """Check if a K-dimension already has a value from the user's query."""
    field_map = {
        "companions": decomposition.companions,
        "location": decomposition.location,
        "time": decomposition.time_context,
        "environment": decomposition.environment,
        "activity": decomposition.activity,
        "event": decomposition.event,
        "photo_type": decomposition.photo_type,
    }
    return bool(field_map.get(dimension))


def select_best_suggestion(
    decomposition: QueryDecomposition,
    candidates: List[dict],
    all_photos: List[dict],
    skipped_dimensions: List[str],
    selected_contexts: List[str],
    redundant_tags: List[str]
) -> Optional[SmartSuggestion]:
    """Use information-gain estimation to select the ONE best suggestion.
    
    Formula (Master Prompt §21):
        Score = (Expected Retrieval Improvement × Probability User Can Answer
                 × Ease of Interaction) ÷ Interaction Cost
    
    Simplified for MVP as: Score = Entropy × Answerability
    
    The dimension with the highest score is chosen. This ensures we ask the
    question that will most effectively narrow the result space while being
    something the user is likely to remember.
    """
    best_dimension = None
    best_score = -1.0
    best_distribution: Dict[str, int] = {}

    dimensions_to_check = ["companions", "location", "time", "environment", "activity", "event", "photo_type"]

    for dim in dimensions_to_check:
        # Skip dimensions that are already filled or that the user said "not sure" about
        if is_dimension_filled(decomposition, dim):
            continue
        if dim in skipped_dimensions:
            continue

        distribution = get_value_distribution(dim, candidates, all_photos)
        if not distribution:
            continue

        # Filter out redundant tags and already-selected contexts
        redundant_lower = [r.lower() for r in (redundant_tags or [])]
        selected_lower = [s.lower() for s in selected_contexts]
        filtered_dist = {
            k: v for k, v in distribution.items()
            if k.lower() not in redundant_lower and k.lower() not in selected_lower
        }

        if not filtered_dist or len(filtered_dist) < 2:
            continue

        # Score = entropy × answerability
        entropy_val = calculate_entropy(filtered_dist)
        answerability = ANSWERABILITY.get(dim, 0.5)
        score = entropy_val * answerability

        if score > best_score:
            best_score = score
            best_dimension = dim
            best_distribution = filtered_dist

    if not best_dimension or not best_distribution:
        return None

    # Build suggestion options (top values by frequency, max 6)
    sorted_values = sorted(best_distribution.items(), key=lambda x: x[1], reverse=True)
    options = [
        SuggestionOption(
            label=value.title(),
            value=value.lower(),
            estimated_results=count
        )
        for value, count in sorted_values[:6]
    ]

    # Always include "Not sure" — suggestions must be optional (Master Prompt §75)
    options.append(SuggestionOption(label="Not sure", value="__not_sure__"))

    question = QUESTION_TEMPLATES.get(best_dimension, f"What about the {best_dimension}?")

    return SmartSuggestion(
        question=question,
        dimension=best_dimension,
        options=options,
        information_gain_score=round(best_score, 3)
    )


def get_all_unique_tags(db: List[dict]) -> List[str]:
    tags = set()
    for p in db:
        m = p.get("metadata", {})
        for k in ['location', 'time', 'event', 'environment', 'activity', 'photo_type', 'people', 'objects']:
            v = m.get(k)
            if isinstance(v, list):
                tags.update([str(x).strip() for x in v if str(x).strip() and str(x).lower() != "none"])
            elif v and isinstance(v, str) and v.lower() != "none":
                tags.update([x.strip() for x in v.split(',') if x.strip()])
    return list(tags)

def generate_zero_result_suggestions(query: str) -> Optional[SmartSuggestion]:
    """Generate broadening semantic suggestions when a search yields 0 results.
    First tries to find synonyms of the query from the existing metadata tags using Gemini.
    Falls back to closest vector tags if no synonyms are found."""
    
    unique_tags = get_all_unique_tags(photos_db)
    
    try:
        # 1. Ask Gemini to find synonyms from the available tags
        prompt = f"""
        The user searched for "{query}" but found 0 results.
        Here is a list of all available metadata tags in our database:
        {unique_tags}
        
        Please select up to 5 tags from this list that are SYNONYMS or strongly semantically related to "{query}".
        If none are related, return an empty list.
        Return ONLY a JSON list of strings.
        """
        
        prompt += '\nMake sure the response is a JSON object with a single key "tags" containing the list of strings. Example: {"tags": ["tag1", "tag2"]}'
        response_text = call_llm_json(prompt)
        parsed = json.loads(response_text)
        suggested_tags = parsed.get("tags", []) if isinstance(parsed, dict) else parsed
        
        if suggested_tags and len(suggested_tags) > 0:
            options = [SuggestionOption(label=str(t).title(), value=str(t).lower()) for t in suggested_tags[:5]]
            return SmartSuggestion(
                question="No exact matches. Did you mean one of these?",
                dimension="context",
                options=options,
                information_gain_score=1.0
            )
    except Exception as e:
        print(f"Zero result suggestion Gemini error: {e}")
        
    try:
        # 2. Fallback: Query ChromaDB for top closest photos
        emb_response = client.models.embed_content(
            model='gemini-embedding-2',
            contents=query,
        )
        query_vector = emb_response.embeddings[0].values
        
        chroma_results = collection.query(
            query_embeddings=[query_vector],
            n_results=10
        )
        
        suggested_tags_dict = {}
        if chroma_results and chroma_results["ids"] and len(chroma_results["ids"]) > 0:
            for pid in chroma_results["ids"][0]:
                photo = next((p for p in photos_db if p["id"] == pid), None)
                if photo:
                    m = photo.get('metadata', {})
                    for k in ['location', 'time', 'event', 'environment', 'activity', 'photo_type', 'people', 'objects']:
                        v = m.get(k)
                        tags = []
                        if isinstance(v, list):
                            tags.extend([str(x).strip() for x in v if str(x).strip() and str(x).lower() != "none"])
                        elif v and isinstance(v, str) and v.lower() != "none":
                            tags.extend([x.strip() for x in v.split(',') if x.strip()])
                            
                        for t in tags:
                            t_lower = t.lower()
                            if t_lower not in suggested_tags_dict:
                                suggested_tags_dict[t_lower] = t
                                
        if suggested_tags_dict:
            options = [SuggestionOption(label=str(t).title(), value=str(t).lower()) for t in list(suggested_tags_dict.values())[:5]]
            return SmartSuggestion(
                question="No exact matches. Try broadening your search:",
                dimension="context",
                options=options,
                information_gain_score=1.0
            )
    except Exception as e:
        print(f"Zero result suggestion Vector error: {e}")
        # Last resort fallback if Gemini API is rate-limited (429)
        import random
        if unique_tags:
            random_tags = random.sample(unique_tags, min(5, len(unique_tags)))
            options = [SuggestionOption(label=str(t).title(), value=str(t).lower()) for t in random_tags]
            return SmartSuggestion(
                question="No exact matches. Try one of these available tags:",
                dimension="context",
                options=options,
                information_gain_score=1.0
            )
        
    return None


# ============================================================================
# RECOVERY MODE (Master Prompt §83–§84)
# ============================================================================

def check_recovery_mode(state: SemanticState, current_result_count: int) -> tuple:
    """Diagnose whether refinement is failing and offer broadening options.
    
    Recovery triggers when:
    - 3+ turns with zero results, OR
    - 4+ turns with results not improving beyond 3
    """
    is_recovery = False
    recovery_options: List[dict] = []

    if state.turn_count >= 3 and current_result_count == 0:
        is_recovery = True
    elif (state.turn_count >= 4
          and 0 <= current_result_count <= 3
          and current_result_count <= state.previous_result_count):
        is_recovery = True

    if is_recovery:
        decomp = state.decomposition
        recovery_options.append({
            "label": "Other +",
            "action": "custom", "dimension": None, "value": "custom"
        })
        if decomp.location:
            recovery_options.append({
                "label": f"Remove location ({decomp.location})",
                "action": "remove", "dimension": "location", "value": decomp.location
            })
        if decomp.time_context:
            recovery_options.append({
                "label": f"Remove time ({decomp.time_context})",
                "action": "remove", "dimension": "time", "value": decomp.time_context
            })
        if decomp.companions:
            recovery_options.append({
                "label": f"Remove companion filter ({decomp.companions})",
                "action": "remove", "dimension": "companions", "value": decomp.companions
            })
        if state.selected_contexts:
            recovery_options.append({
                "label": "Remove all refinements",
                "action": "reset_refinements", "dimension": None, "value": None
            })
        if decomp.ambiguities:
            recovery_options.append({
                "label": "Try a different interpretation",
                "action": "reinterpret", "dimension": None, "value": None
            })

    return is_recovery, recovery_options


# ============================================================================
# ACTIVE CONSTRAINTS (for removable chips in the UI)
# ============================================================================

def build_active_constraints(
    decomposition: QueryDecomposition,
    selected_contexts: List[str]
) -> List[dict]:
    """Build the list of active search constraints for the frontend.
    These are displayed as removable chips so the user can undo without typing."""
    constraints = []

    dim_map = [
        ("subject", decomposition.subject, "Subject"),
        ("location", decomposition.location, "Location"),
        ("companions", decomposition.companions, "With"),
        ("time", decomposition.time_context, "Time"),
        ("vibe", decomposition.vibe, "Vibe"),
        ("objects", decomposition.objects, "Object"),
        ("activity", decomposition.activity, "Activity"),
        ("event", decomposition.event, "Event"),
        ("environment", decomposition.environment, "Setting"),
    ]

    for dim_key, value, label_prefix in dim_map:
        if value:
            constraints.append({
                "dimension": dim_key,
                "label": f"{label_prefix}: {value}",
                "value": value,
                "removable": True,
                "source": "query"
            })

    for ctx in selected_contexts:
        constraints.append({
            "dimension": "context",
            "label": ctx.title(),
            "value": ctx,
            "removable": True,
            "source": "chip"
        })

    return constraints


def generate_flat_suggestions(smart_suggestion: Optional[SmartSuggestion]) -> List[dict]:
    """Convert SmartSuggestion to a flat chip list for backward compatibility
    with the existing frontend chip rendering."""
    options = []
    if smart_suggestion:
        options = [
            {
                "category": smart_suggestion.dimension,
                "label": opt.label,
                "value": opt.value,
            }
            for opt in smart_suggestion.options
        ]
    
    # Always add 'Other +' option
    options.append({
        "category": "custom",
        "label": "Other +",
        "value": "custom"
    })
    return options


# ============================================================================
# STATE UPDATE HELPERS
# ============================================================================

def rebuild_user_facing_query(decomp: QueryDecomposition, raw_query: str, selected_contexts: List[str] = None) -> str:
    """Rebuild the user-facing natural language query using the LLM to ensure grammar and completeness."""
    refinements = []
    if decomp.subject: refinements.append(f"subject: {decomp.subject}")
    if decomp.location: refinements.append(f"location: {decomp.location}")
    if decomp.environment: refinements.append(f"setting: {decomp.environment}")
    if decomp.companions: refinements.append(f"with: {decomp.companions}")
    if decomp.time_context: refinements.append(f"time: {decomp.time_context}")
    if decomp.event: refinements.append(f"event: {decomp.event}")
    if decomp.objects: refinements.append(f"objects: {decomp.objects}")
    if decomp.activity: refinements.append(f"activity: {decomp.activity}")
    if selected_contexts:
        for c in selected_contexts:
            refinements.append(f"context: {c}")
            
    if not refinements:
        return raw_query
        
    prompt = f"Given the original base query '{raw_query}' and the following active filters: {', '.join(refinements)}. Write a single, natural, and concise search query that combines the base query and the active filters. Do not include quotes or conversational text."
    
    try:
        text = call_llm_text(prompt)
        return text.strip().strip('"')
    except:
        parts = []
        if decomp.subject: parts.append(decomp.subject)
        if decomp.activity: parts.append(decomp.activity.lower())
        if decomp.location: parts.append(f"at {decomp.location}")
        if decomp.environment: parts.append(f"in a {decomp.environment.lower()} setting")
        if decomp.companions: parts.append(f"with {decomp.companions.lower()}")
        if decomp.time_context: parts.append(f"in the {decomp.time_context.lower()}")
        if decomp.event: parts.append(f"during {decomp.event}")
        if decomp.objects: parts.append(f"with {decomp.objects}")
        return " ".join(parts) if parts else raw_query


def build_full_response(
    state: SemanticState,
    results: List[dict],
) -> SearchResponse:
    """Build the full SearchResponse from the current state and results."""
    is_recovery, recovery_options = check_recovery_mode(state, len(results))
    state.is_recovery_mode = is_recovery

    needs_refinement = True if len(results) == 0 else (len(results) != 1)

    smart_suggestion = None
    if len(results) == 0:
        smart_suggestion = generate_zero_result_suggestions(state.decomposition.user_facing_query or state.raw_query)
    elif needs_refinement and not is_recovery:
        smart_suggestion = select_best_suggestion(
            state.decomposition,
            results,
            photos_db,
            state.skipped_dimensions,
            state.selected_contexts,
            state.decomposition.redundant_tags or []
        )

    flat_suggestions = generate_flat_suggestions(smart_suggestion)
    active_constraints = build_active_constraints(
        state.decomposition, state.selected_contexts
    )

    state.previous_result_count = len(results)
    sessions[state.session_id] = state

    return SearchResponse(
        results=results,
        needs_refinement=needs_refinement,
        suggestions=flat_suggestions,
        refinement_question=smart_suggestion.question if smart_suggestion else None,
        session_id=state.session_id,
        user_facing_query=state.decomposition.user_facing_query or state.raw_query,
        semantic_state=state.decomposition.model_dump() if state.decomposition else None,
        smart_suggestion=smart_suggestion.model_dump() if smart_suggestion else None,
        active_constraints=active_constraints,
        is_recovery_mode=is_recovery,
        recovery_options=recovery_options,
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check():
    return {"status": "healthy", "gemini_enabled": client is not None}


@app.get("/api/photos")
def get_all_photos(limit: int = 300):
    import random
    shuffled = photos_db.copy()
    random.shuffle(shuffled)
    return {"results": shuffled[:limit]}


@app.get("/api/search", response_model=SearchResponse)
def search_photos(
    q: str = "",
    context: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Main search endpoint — enhanced with K1–K15 semantic decomposition,
    information-gain suggestions, confidence-weighted ranking, and recovery mode.
    
    Backward compatible: still accepts q + context query params.
    New: accepts session_id for multi-turn state management.
    """
    # Get or create session
    state = get_or_create_session(session_id)

    # If this is a new query, decompose fresh and reset session state
    if q.strip() and q.strip() != state.raw_query:
        state.raw_query = q
        state.decomposition = decompose_query(q)
        state.selected_contexts = []
        state.skipped_dimensions = []
        state.turn_count = 0
        state.recovery_attempts = 0
        state.previous_result_count = -1
        state.is_recovery_mode = False

    # Sync context chips from frontend
    context_filters = [c.strip() for c in context.split(',') if c.strip()] if context else []
    if context_filters != state.selected_contexts:
        state.selected_contexts = context_filters
        state.turn_count += 1

    # Search
    results = perform_search(state.decomposition, state.selected_contexts, state.raw_query)

    return build_full_response(state, results)


@app.post("/api/refine", response_model=SearchResponse)
def refine_search(request: RefineRequest):
    """Refine an existing search session.
    
    Supports actions from the Master Prompt:
    - "add": Select a suggestion chip (adds to selected_contexts)
    - "remove": Remove a constraint (undo a K-dimension or context chip)
    - "not_sure": Mark a dimension as skipped (never re-ask)
    - "correct": Change a K-dimension value
    - "reset_refinements": Remove all chip selections but keep the base query
    """
    if request.session_id not in sessions:
        return SearchResponse(
            results=[], needs_refinement=False, suggestions=[],
            refinement_question="Session expired. Please search again."
        )

    state = sessions[request.session_id]
    decomp = state.decomposition

    if request.action == "add" and request.value:
        dim = request.dimension
        dim_field_map = {
            "location": ("location", "location_confidence"),
            "companions": ("companions", "companions_confidence"),
            "time": ("time_context", "time_confidence"),
            "environment": ("environment", None),
            "activity": ("activity", "activity_confidence"),
            "event": ("event", "event_confidence"),
            "vibe": ("vibe", "vibe_confidence"),
            "objects": ("objects", "objects_confidence"),
            "subject": ("subject", "subject_confidence"),
        }
        if dim and dim in dim_field_map:
            val_field, conf_field = dim_field_map[dim]
            setattr(decomp, val_field, request.value)
            if conf_field:
                setattr(decomp, conf_field, "high")
        else:
            if request.value not in state.selected_contexts:
                state.selected_contexts.append(request.value)
                
        decomp.user_facing_query = rebuild_user_facing_query(decomp, state.raw_query, state.selected_contexts)
        state.turn_count += 1

    elif request.action == "remove" and request.dimension:
        dim = request.dimension
        if dim == "context" and request.value:
            # Remove a chip selection
            state.selected_contexts = [c for c in state.selected_contexts if c != request.value]
        else:
            # Remove a K-dimension value (undo)
            dim_field_map = {
                "location": ("location", "location_confidence"),
                "companions": ("companions", "companions_confidence"),
                "time": ("time_context", "time_confidence"),
                "environment": ("environment", None),
                "activity": ("activity", "activity_confidence"),
                "event": ("event", "event_confidence"),
                "vibe": ("vibe", "vibe_confidence"),
                "objects": ("objects", "objects_confidence"),
                "subject": ("subject", "subject_confidence"),
            }
            if dim in dim_field_map:
                val_field, conf_field = dim_field_map[dim]
                setattr(decomp, val_field, None)
                if conf_field:
                    setattr(decomp, conf_field, "unknown")

        decomp.user_facing_query = rebuild_user_facing_query(decomp, state.raw_query, state.selected_contexts)

        state.turn_count += 1

    elif request.action == "not_sure" and request.dimension:
        # Golden Rule #12: Do not repeatedly ask rejected or skipped questions
        if request.dimension not in state.skipped_dimensions:
            state.skipped_dimensions.append(request.dimension)
        state.turn_count += 1

    elif request.action == "correct" and request.dimension and request.value:
        # Master Prompt §31–§32: corrections update only the targeted dimension
        dim_field_map = {
            "companions": ("companions", "companions_confidence"),
            "location": ("location", "location_confidence"),
            "time": ("time_context", "time_confidence"),
            "activity": ("activity", "activity_confidence"),
            "event": ("event", "event_confidence"),
            "environment": ("environment", None),
            "vibe": ("vibe", "vibe_confidence"),
            "objects": ("objects", "objects_confidence"),
        }
        if request.dimension in dim_field_map:
            val_field, conf_field = dim_field_map[request.dimension]
            setattr(decomp, val_field, request.value)
            if conf_field:
                setattr(decomp, conf_field, "high")

        decomp.user_facing_query = rebuild_user_facing_query(decomp, state.raw_query, state.selected_contexts)

        state.turn_count += 1

    elif request.action == "reset_refinements":
        state.selected_contexts = []
        state.skipped_dimensions = []
        state.turn_count = 0
        state.is_recovery_mode = False

    elif request.action == "custom" and request.value:
        # Combine naturally using LLM
        base_q = state.decomposition.user_facing_query or state.raw_query
        prompt = f"Combine the existing search query: '{base_q}' with the new user refinement: '{request.value}'. Return ONLY the naturally combined short query string, choosing appropriate grammatical relationships (with, at, on, during, near, indoors, etc.) instead of blindly appending. Do not include quotes or extra text."
        try:
            combined_text = call_llm_text(prompt).strip().strip('"')
        except:
            combined_text = f"{base_q} {request.value}"
        
        new_decomp = decompose_query(combined_text)
        new_decomp.user_facing_query = combined_text
        state.decomposition = new_decomp
        state.raw_query = combined_text
        decomp = new_decomp
        state.turn_count += 1

    # Re-run search with updated state
    results = perform_search(decomp, state.selected_contexts, state.raw_query)

    return build_full_response(state, results)


@app.post("/api/reset")
def reset_session(request: ResetRequest):
    """Reset a search session completely."""
    if request.session_id in sessions:
        del sessions[request.session_id]
    return {"status": "reset", "session_id": request.session_id}


@app.post("/api/track")
def track_event(event: TrackingEvent):
    # In a real app, this would write to an analytics database.
    # For the MVP, we log to console.
    print(f"[ANALYTICS] {event.event_name} | {json.dumps(event.properties)}")
    return {"status": "success"}
